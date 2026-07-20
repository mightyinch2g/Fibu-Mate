
from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MODULE_TITLE = "AFI-Upload über Copilot Auto"
MODULE_VERSION = "1.4.0"
AUTOMATION_MODE = True

NETWORK_ROOT = r"G:\BUC\FM Anwendung"
DB_DIR = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "AFI_Copilot")
PROMPT_DB = os.path.join(DB_DIR, "afi_copilot_prompts.db")

DEFAULT_COSTCENTER_DB = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "MA_Kontierung_GJ2526_260623.xlsx")
DEFAULT_GENERAL_DB = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "Kontierungszuordnung_Generalübersicht.xlsx")
ONEDRIVE_RELATIVE_UPLOAD_ROOT = os.path.join("FiBu Mate", "AFI Copilot Uploads")

SUPPLIER_DEFAULTS = {
    "generic": ("Weitere Lieferanten / generisch", "Analysiere die Rechnung lieferantenunabhängig. Verwende die Kontierungsdatenbanken. Erstelle AFI-CSV-Zeilen nach den verbindlichen Vorgaben."),
    "enbw": ("EnBW Charging", "EnBW: Stromtanken je Nutzer/Fahrzeug kontieren. Kennzeichen und Name im TEXT ausgeben. Sachkonto bevorzugt Tanken Strom."),
    "dkv": ("DKV", "DKV: Positionen je Fahrzeug/Kennzeichen kontieren. Kraftstoff/Gebühren/Sonstiges über Sachkontenlogik zuordnen."),
    "vodafone": ("Vodafone Mobilfunk", "Vodafone: Rufnummern über Telefonzuordnung kontieren. Bei gleicher Kostenstelle/Gesellschaft darf sinnvoll aggregiert werden."),
    "kazenmaier": ("Kazenmaier Bike Leasing", "Kazenmaier: Bike-Leasing je Person/Auftrag kontieren. Auftragsnummer darf im TEXT stehen, ORDERID bleibt immer leer."),
    "telekom": ("Telekom", "Telekom: Rufnummern über Telefonzuordnung und Mitarbeiter/Kostenstellen-Datenbank kontieren. Sachkonto bevorzugt Telekom."),
    "deas": ("DEAS", "DEAS: Versicherung oder sonstige Leistung erkennen und passendes Sachkonto aus der Generalübersicht verwenden."),
    "vw_leasing": ("VW-Leasing", "VW-Leasing: Leasingpositionen je Fahrzeug/Kennzeichen bzw. Fahrer kontieren. Sachkonto bevorzugt VW-Leasing."),
    "vw_versicherungen": ("VW-Versicherungen", "VW-Versicherungen: Versicherungspositionen je Fahrzeug/Kennzeichen bzw. Fahrer kontieren. Sachkonto bevorzugt VW-Versicherungen."),
    "sonstige": ("Sonstige", "Sonstige Lieferanten: Kostenart aus Rechnung ableiten. Wenn keine Kostenart eindeutig ist, Sachkonto Sonstige verwenden. Kostenstelle nie erfinden."),
}

DEFAULT_GENERAL_PROMPT = """Du bist der AFI-Upload-Assistent für FiBu Mate.

Verarbeite die bereitgestellten OneDrive-Dateien zusammen mit diesen Kontierungsdatenbanken:
1. Mitarbeiter-/Kostenstellen-Datenbank
2. Generalübersicht mit Sachkonten, Kennzeichen, Rufnummern und Gesellschaften

Erzeuge die Antwort als CSV für den SAP-AFI-Upload.
Die CSV muss exakt diese Spalten in dieser Reihenfolge haben:
TEXT;PRICE;PRICE_UNIT;QUANTITY;UNIT;NET_VALUE;TAX_CODE;GL_ACCOUNT;COSTCENTER;ORDERID

Verbindliche Regeln:
- Gib zuerst ausschließlich den CSV-Inhalt aus, keine Markdown-Codeblöcke.
- Trennzeichen ist Semikolon.
- Dezimalformat deutsch mit vier Nachkommastellen, z. B. 123,4500.
- PRICE_UNIT ist immer 1.
- QUANTITY ist immer 1.
- UNIT ist immer ST.
- ORDERID bleibt immer leer.
- TEXT maximal 120 Zeichen.
- GL_ACCOUNT muss aus der Sachkontenlogik der Generalübersicht kommen.
- Wenn keine konkrete Kostenart eindeutig ist, verwende das Sachkonto Sonstige aus der Generalübersicht.
- COSTCENTER darf nur aus echter Zuordnung stammen: Name, Kennzeichen, Rufnummer, Mitarbeiter/Kostenstellen-Datenbank oder Weiterberechnungslogik.
- Es gibt keinen COSTCENTER-Fallback. Wenn keine Kostenstelle ermittelbar ist, muss COSTCENTER leer bleiben.
- Wenn Warnungen bestehen, schreibe nach der CSV einen separaten Abschnitt "WARNUNGEN:". Warnungen gehören nicht in die CSV-Zeilen.
- CSV muss auch bei Warnungen fachlich prüfbar erzeugt werden.
"""


def _connect():
    os.makedirs(DB_DIR, exist_ok=True)
    return sqlite3.connect(PROMPT_DB)


def _norm_key(value):
    return re.sub(r"[^a-z0-9äöüß]+", "_", str(value or "").strip().casefold()).strip("_") or "supplier"


def _ensure_db():
    con = _connect()
    try:
        con.execute("create table if not exists settings (key text primary key, value text not null)")
        con.execute("create table if not exists general_prompt (id integer primary key check (id=1), prompt_text text not null, updated_at text, updated_by text)")
        con.execute("create table if not exists supplier_prompts (supplier_key text primary key, supplier_label text not null, prompt_text text not null, active integer not null default 1, updated_at text, updated_by text)")
        con.execute("insert or ignore into general_prompt(id,prompt_text,updated_at,updated_by) values (1,?,?,?)", (DEFAULT_GENERAL_PROMPT, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        for key, (label, prompt) in SUPPLIER_DEFAULTS.items():
            con.execute("insert or ignore into supplier_prompts(supplier_key,supplier_label,prompt_text,active,updated_at,updated_by) values (?,?,?,?,?,?)", (key, label, prompt, 1, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        con.execute("insert or ignore into settings(key,value) values (?,?)", ("costcenter_db", DEFAULT_COSTCENTER_DB))
        con.execute("insert or ignore into settings(key,value) values (?,?)", ("general_db", DEFAULT_GENERAL_DB))
        con.commit()
    finally:
        con.close()


def _get_setting(key: str, default: str = "") -> str:
    _ensure_db()
    con = _connect()
    try:
        row = con.execute("select value from settings where key=?", (key,)).fetchone()
        return row[0] if row else default
    finally:
        con.close()


def _set_setting(key: str, value: str) -> None:
    _ensure_db()
    con = _connect()
    try:
        con.execute("insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value", (key, value))
        con.commit()
    finally:
        con.close()


def _load_general_prompt() -> str:
    _ensure_db()
    con = _connect()
    try:
        row = con.execute("select prompt_text from general_prompt where id=1").fetchone()
        return row[0] if row else DEFAULT_GENERAL_PROMPT
    finally:
        con.close()


def _save_general_prompt(text: str) -> None:
    _ensure_db()
    con = _connect()
    try:
        con.execute("insert into general_prompt(id,prompt_text,updated_at,updated_by) values(1,?,?,?) on conflict(id) do update set prompt_text=excluded.prompt_text, updated_at=excluded.updated_at, updated_by=excluded.updated_by", (text, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        con.commit()
    finally:
        con.close()


def _load_suppliers():
    _ensure_db()
    con = _connect()
    try:
        rows = con.execute("select supplier_key, supplier_label, prompt_text, active from supplier_prompts order by supplier_label").fetchall()
        return [{"key": r[0], "label": r[1], "prompt": r[2], "active": bool(r[3])} for r in rows]
    finally:
        con.close()


def _save_supplier(key: str, label: str, prompt: str, active: bool = True) -> None:
    _ensure_db()
    con = _connect()
    try:
        con.execute("insert into supplier_prompts(supplier_key,supplier_label,prompt_text,active,updated_at,updated_by) values(?,?,?,?,?,?) on conflict(supplier_key) do update set supplier_label=excluded.supplier_label, prompt_text=excluded.prompt_text, active=excluded.active, updated_at=excluded.updated_at, updated_by=excluded.updated_by", (_norm_key(key or label), label or key, prompt or "", 1 if active else 0, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        con.commit()
    finally:
        con.close()


def _sanitize_name(value: str) -> str:
    value = Path(str(value or "rechnung")).stem
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return value[:80] or "rechnung"


def _candidate_onedrive_roots():
    result = []
    for key in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
        value = os.environ.get(key)
        if value and Path(value).exists():
            result.append(Path(value))
    # Remove duplicates while preserving order.
    unique = []
    seen = set()
    for path in result:
        real = str(path.resolve()).casefold()
        if real not in seen:
            unique.append(path)
            seen.add(real)
    return unique


def _default_onedrive_upload_root() -> Path | None:
    stored = _get_setting("onedrive_upload_root", "")
    if stored:
        return Path(os.path.expandvars(stored))
    roots = _candidate_onedrive_roots()
    if roots:
        preferred = roots[0] / ONEDRIVE_RELATIVE_UPLOAD_ROOT
        _set_setting("onedrive_upload_root", str(preferred))
        return preferred
    return None


def _ensure_onedrive_upload_root(parent_widget=None) -> Path:
    root = _default_onedrive_upload_root()
    if root is None:
        chosen = filedialog.askdirectory(title="OneDrive-Zielordner für AFI Copilot Uploads auswählen", parent=parent_widget)
        if not chosen:
            raise RuntimeError("Kein OneDrive-Zielordner ausgewählt.")
        root = Path(chosen) / ONEDRIVE_RELATIVE_UPLOAD_ROOT if Path(chosen).name != "AFI Copilot Uploads" else Path(chosen)
        _set_setting("onedrive_upload_root", str(root))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _copy_to_onedrive_session(invoice: str, costcenter_db: str, general_db: str, parent_widget=None):
    upload_root = _ensure_onedrive_upload_root(parent_widget)
    session_name = f"{datetime.now():%Y_%m_%d_%H%M%S}_{_sanitize_name(invoice)}"
    session_dir = upload_root / session_name
    session_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in (invoice, costcenter_db, general_db):
        source_path = Path(source)
        if not source_path.is_file():
            raise FileNotFoundError(str(source_path))
        target = session_dir / source_path.name
        if source_path.resolve() != target.resolve():
            shutil.copy2(source_path, target)
        copied.append(target)
    return session_dir, copied


def _build_prompt(invoice, costcenter_db, general_db, supplier_label, supplier_prompt, general_prompt, onedrive_session_dir, onedrive_files):
    file_lines = "\n".join(f"{idx}. {path.name}: {path}" for idx, path in enumerate(onedrive_files, 1))
    return f"""{general_prompt.strip()}

LIEFERANT / AUSGEWÄHLTER PROMPT:
{supplier_label}

LIEFERANTENSPEZIFISCHE REGELN:
{supplier_prompt.strip()}

ONEDRIVE-DATEIEN / VERBINDLICHE QUELLEN:
Die folgenden Dateien wurden in meinen persönlichen OneDrive-Ordner kopiert.
Verwende ausdrücklich diese OneDrive-Dateien als Quellen für die Erstellung der AFI-Upload-CSV.

OneDrive-Session-Ordner:
{onedrive_session_dir}

Dateien:
{file_lines}

WICHTIG:
- Analysiere die Rechnung aus dem OneDrive-Session-Ordner.
- Verwende die Mitarbeiter-/Kostenstellen-Datenbank aus demselben OneDrive-Session-Ordner.
- Verwende die Generalübersicht mit Sachkonten, Kennzeichen, Rufnummern und Gesellschaften aus demselben OneDrive-Session-Ordner.
- Wenn Copilot die Dateien nicht automatisch als Quelle erkennt, fordere mich auf, genau diese drei Dateien aus diesem OneDrive-Ordner als Cloud-Dateien hinzuzufügen.

Bitte gib als Antwort die AFI-CSV nach den Regeln aus.
""".strip()


def _run_detached(command):
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception:
        return False


def _open_copilot():
    opened = False
    for url in ("https://m365.cloud.microsoft/chat", "https://teams.microsoft.com/v2/", "msteams:"):
        try:
            webbrowser.open_new(url)
            opened = True
            break
        except Exception:
            pass
    if not opened:
        opened = _run_detached(["cmd", "/c", "start", "", "msteams:"])
    return opened


def _copy_text_to_clipboard(root, text: str):
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()


class AFICopilotUI:
    def __init__(self, app, automation=False):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        self.bg = getattr(app, "BG", "#E8EEF5")
        self.automation = automation
        _ensure_db()
        suppliers = _load_suppliers()
        self.invoice_var = tk.StringVar()
        self.costcenter_var = tk.StringVar(value=_get_setting("costcenter_db", DEFAULT_COSTCENTER_DB))
        self.general_db_var = tk.StringVar(value=_get_setting("general_db", DEFAULT_GENERAL_DB))
        self.onedrive_root_var = tk.StringVar(value=str(_default_onedrive_upload_root() or "%OneDriveCommercial%\\FiBu Mate\\AFI Copilot Uploads"))
        self.supplier_label_var = tk.StringVar(value=(suppliers[0]["label"] if suppliers else "Weitere Lieferanten / generisch"))
        self.status_var = tk.StringVar(value="Bereit")
        self.prompt_preview = None
        self.general_text = None
        self.supplier_list = None
        self.supplier_text = None
        self.supplier_key_var = tk.StringVar()
        self.supplier_name_var = tk.StringVar()
        self.db_frame = None
        self.db_toggle_button = None
        self.db_open = False

    def _supplier_by_label(self, label):
        suppliers = _load_suppliers()
        for item in suppliers:
            if item["label"] == label:
                return item
        return suppliers[0] if suppliers else {"key": "generic", "label": "Weitere Lieferanten / generisch", "prompt": ""}

    def render(self):
        try:
            self.canvas.delete("all")
            self.app.draw_background()
            self.app.draw_header("AFI-Upload über Copilot" + (" - Auto" if self.automation else " - stabil"))
            self.app.draw_path_bar()
        except Exception:
            pass
        width = max(1100, self.canvas.winfo_width() - 60)
        height = max(690, self.canvas.winfo_height() - 175)
        frame = tk.Frame(self.canvas, bg=self.bg)
        self.canvas.create_window(30, 132, window=frame, anchor="nw", width=width, height=height)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        nb = ttk.Notebook(frame)
        nb.grid(row=0, column=0, sticky="nsew")
        main = tk.Frame(nb, bg=self.bg)
        prompts = tk.Frame(nb, bg=self.bg)
        nb.add(main, text="Verarbeitung")
        nb.add(prompts, text="Prompts & Lieferanten")
        self._render_main(main)
        self._render_prompts(prompts)

    def _toggle_db_paths(self):
        self.db_open = not self.db_open
        if self.db_frame:
            self.db_frame.grid() if self.db_open else self.db_frame.grid_remove()
        if self.db_toggle_button:
            self.db_toggle_button.configure(text="Datenbank-/OneDrive-Pfade ausblenden ▲" if self.db_open else "Datenbank-/OneDrive-Pfade anzeigen ▼")

    def _render_main(self, parent):
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(6, weight=1)
        tk.Label(parent, text="Rechnung", bg=self.bg).grid(row=0, column=0, sticky="w", padx=10, pady=8)
        tk.Entry(parent, textvariable=self.invoice_var).grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        tk.Button(parent, text="Auswählen", command=self.pick_invoice).grid(row=0, column=2, padx=8, pady=8)
        self.db_toggle_button = tk.Button(parent, text="Datenbank-/OneDrive-Pfade anzeigen ▼", command=self._toggle_db_paths, bg="#D9E2F3")
        self.db_toggle_button.grid(row=1, column=0, columnspan=3, sticky="w", padx=10, pady=(0, 4))
        self.db_frame = tk.Frame(parent, bg=self.bg)
        self.db_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 6))
        self.db_frame.columnconfigure(1, weight=1)
        rows = [
            ("Datenbank 1: Mitarbeiter/Kostenstelle", self.costcenter_var, lambda: self.pick_db(self.costcenter_var, "costcenter_db")),
            ("Datenbank 2: Generalübersicht", self.general_db_var, lambda: self.pick_db(self.general_db_var, "general_db")),
            ("OneDrive Upload-Ziel", self.onedrive_root_var, self.pick_onedrive_root),
        ]
        for idx, (label, var, command) in enumerate(rows):
            tk.Label(self.db_frame, text=label, bg=self.bg).grid(row=idx, column=0, sticky="w", pady=3)
            tk.Entry(self.db_frame, textvariable=var).grid(row=idx, column=1, sticky="ew", padx=8, pady=3)
            tk.Button(self.db_frame, text="Ändern", command=command).grid(row=idx, column=2, padx=8, pady=3)
        self.db_frame.grid_remove()
        tk.Label(parent, text="Lieferant", bg=self.bg).grid(row=3, column=0, sticky="w", padx=10, pady=4)
        labels = [x["label"] for x in _load_suppliers() if x.get("active")]
        ttk.Combobox(parent, textvariable=self.supplier_label_var, values=labels, state="readonly").grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        tk.Button(parent, text="Copilot öffnen", command=self.prepare, bg="#0F6CBD", fg="white", padx=12, pady=6).grid(row=4, column=0, columnspan=3, sticky="w", padx=10, pady=10)
        tk.Label(parent, textvariable=self.status_var, bg=self.bg, fg="#44536A").grid(row=4, column=1, columnspan=2, sticky="e", padx=10)
        tk.Label(parent, text="Ablauf: Dateien werden in OneDrive kopiert, der Prompt mit OneDrive-Pfaden wird in die Zwischenablage gelegt, danach wird Copilot geöffnet.", bg=self.bg, fg="#44536A", anchor="w", justify="left", wraplength=950).grid(row=5, column=0, columnspan=3, sticky="ew", padx=10)
        self.prompt_preview = tk.Text(parent, wrap="word", height=16, font=("Consolas", 10))
        self.prompt_preview.grid(row=6, column=0, columnspan=3, sticky="nsew", padx=10, pady=8)
        tk.Label(parent, text=f"Prompt-Datenbank: {PROMPT_DB}", bg=self.bg, fg="#44536A", anchor="w").grid(row=7, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 8))

    def _render_prompts(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        top = tk.Frame(parent, bg=self.bg)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        tk.Button(top, text="Speichern", command=self.save_prompts, bg="#0F6CBD", fg="white", padx=12).pack(side="right")
        tk.Button(top, text="Lieferant neu/anlegen", command=self.new_supplier, padx=10).pack(side="right", padx=8)
        pane = ttk.Panedwindow(parent, orient="horizontal")
        pane.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        left = tk.Frame(pane, bg=self.bg)
        right = tk.Frame(pane, bg=self.bg)
        pane.add(left, weight=1)
        pane.add(right, weight=2)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        tk.Label(left, text="Generalprompt", bg=self.bg, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.general_text = tk.Text(left, wrap="word", font=("Consolas", 10))
        self.general_text.grid(row=1, column=0, sticky="nsew")
        self.general_text.insert("1.0", _load_general_prompt())
        right.columnconfigure(1, weight=1)
        right.rowconfigure(4, weight=1)
        tk.Label(right, text="Lieferantenprompts", bg=self.bg, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self.supplier_list = tk.Listbox(right, height=10)
        self.supplier_list.grid(row=1, column=0, rowspan=4, sticky="nsew", padx=(0, 8))
        for item in _load_suppliers():
            self.supplier_list.insert("end", item["label"])
        self.supplier_list.bind("<<ListboxSelect>>", self.load_selected_supplier)
        tk.Label(right, text="Schlüssel", bg=self.bg).grid(row=1, column=1, sticky="w")
        tk.Entry(right, textvariable=self.supplier_key_var).grid(row=1, column=2, sticky="ew")
        tk.Label(right, text="Name", bg=self.bg).grid(row=2, column=1, sticky="w")
        tk.Entry(right, textvariable=self.supplier_name_var).grid(row=2, column=2, sticky="ew")
        tk.Label(right, text="Prompt", bg=self.bg).grid(row=3, column=1, columnspan=2, sticky="w")
        self.supplier_text = tk.Text(right, wrap="word", font=("Consolas", 10))
        self.supplier_text.grid(row=4, column=1, columnspan=2, sticky="nsew")
        if self.supplier_list.size():
            self.supplier_list.selection_set(0)
            self.load_selected_supplier()

    def pick_invoice(self):
        path = filedialog.askopenfilename(title="Rechnung auswählen", filetypes=[("Rechnungen", "*.pdf *.xlsx *.xlsm *.csv *.docx"), ("Alle Dateien", "*.*")])
        if path:
            self.invoice_var.set(path)

    def pick_db(self, var, key):
        path = filedialog.askopenfilename(title="Datenbank auswählen", filetypes=[("Excel", "*.xlsx *.xlsm"), ("Alle Dateien", "*.*")])
        if path:
            var.set(path)
            _set_setting(key, path)

    def pick_onedrive_root(self):
        path = filedialog.askdirectory(title="OneDrive Upload-Ziel auswählen")
        if path:
            self.onedrive_root_var.set(path)
            _set_setting("onedrive_upload_root", path)
            Path(path).mkdir(parents=True, exist_ok=True)

    def load_selected_supplier(self, event=None):
        sel = self.supplier_list.curselection() if self.supplier_list else []
        if not sel:
            return
        item = self._supplier_by_label(self.supplier_list.get(sel[0]))
        self.supplier_key_var.set(item["key"])
        self.supplier_name_var.set(item["label"])
        self.supplier_text.delete("1.0", "end")
        self.supplier_text.insert("1.0", item["prompt"])

    def new_supplier(self):
        self.supplier_key_var.set("neuer_lieferant")
        self.supplier_name_var.set("Neuer Lieferant")
        self.supplier_text.delete("1.0", "end")
        self.supplier_text.insert("1.0", "Lieferantenspezifische Regeln hier erfassen.")

    def save_prompts(self):
        _save_general_prompt(self.general_text.get("1.0", "end-1c"))
        _save_supplier(self.supplier_key_var.get(), self.supplier_name_var.get(), self.supplier_text.get("1.0", "end-1c"))
        messagebox.showinfo(MODULE_TITLE, "Prompts wurden zentral gespeichert.\n\n" + PROMPT_DB)
        self.render()

    def prepare(self):
        invoice = self.invoice_var.get().strip()
        costcenter = self.costcenter_var.get().strip()
        general = self.general_db_var.get().strip()
        missing = [p for p in (invoice, costcenter, general) if not p or not os.path.exists(p)]
        if missing:
            messagebox.showwarning(MODULE_TITLE, "Bitte Rechnung und beide Datenbanken prüfen. Nicht gefunden:\n" + "\n".join(missing))
            return
        try:
            # Persist UI value before session creation. Allows manual override.
            if self.onedrive_root_var.get().strip():
                _set_setting("onedrive_upload_root", self.onedrive_root_var.get().strip())
            session_dir, copied_files = _copy_to_onedrive_session(invoice, costcenter, general, self.root)
        except Exception as exc:
            messagebox.showerror(MODULE_TITLE, "OneDrive-Ablage konnte nicht erstellt werden:\n\n" + str(exc))
            return
        item = self._supplier_by_label(self.supplier_label_var.get())
        prompt = _build_prompt(invoice, costcenter, general, item["label"], item["prompt"], _load_general_prompt(), session_dir, copied_files)
        self.prompt_preview.delete("1.0", "end")
        self.prompt_preview.insert("1.0", prompt)
        _copy_text_to_clipboard(self.root, prompt)
        _open_copilot()
        self.status_var.set("Dateien nach OneDrive kopiert. Prompt wurde in die Zwischenablage gelegt.")
        messagebox.showinfo(MODULE_TITLE, "Copilot wurde geöffnet.\n\nDie drei Dateien wurden nach OneDrive kopiert:\n" + str(session_dir) + "\n\nDer Prompt mit den OneDrive-Pfaden wurde in die Zwischenablage gelegt.")


def render(app):
    ui = AFICopilotUI(app, automation=AUTOMATION_MODE)
    app._afi_copilot_ui = ui
    ui.render()
