
from __future__ import annotations
import os
import re
import sqlite3
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MODULE_TITLE = "AFI-Upload über Copilot"
MODULE_VERSION = "1.2.0"
AUTOMATION_MODE = False
NETWORK_ROOT = r"G:\BUC\FM Anwendung"
DB_DIR = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "AFI_Copilot")
PROMPT_DB = os.path.join(DB_DIR, "afi_copilot_prompts.db")
DEFAULT_COSTCENTER_DB = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "MA_Kontierung_GJ2526_260623.xlsx")
DEFAULT_GENERAL_DB = os.path.join(NETWORK_ROOT, "Fibu_Mate_Doc", "Database", "Kontierungszuordnung_Generalübersicht.xlsx")
SUPPLIER_DEFAULTS = {
    "generic": {"label": "Weitere Lieferanten / generisch", "prompt": "Analysiere die Rechnung lieferantenunabhängig. Verwende die Kontierungsdatenbanken. Erstelle AFI-CSV-Zeilen nach den verbindlichen Vorgaben."},
    "enbw": {"label": "EnBW Charging", "prompt": "EnBW: Stromtanken je Nutzer/Fahrzeug plausibel kontieren. Kennzeichen und Name im TEXT ausgeben. Sachkonto bevorzugt Tanken Strom."},
    "dkv": {"label": "DKV", "prompt": "DKV: Positionen je Fahrzeug/Kennzeichen kontieren. Kraftstoff, Gebühren und sonstige Positionen über die Sachkontenlogik der Generalübersicht zuordnen."},
    "vodafone": {"label": "Vodafone Mobilfunk", "prompt": "Vodafone: Rufnummern über Telefonzuordnung kontieren. Bei gleicher Kostenstelle/Gesellschaft darf sinnvoll aggregiert werden. Rufnummernbezug im TEXT erhalten."},
    "kazenmaier": {"label": "Kazenmaier Bike Leasing", "prompt": "Kazenmaier: Bike-Leasing je Person/Auftrag kontieren. Auftragsnummer darf im TEXT stehen, ORDERID bleibt immer leer."},
    "telekom": {"label": "Telekom", "prompt": "Telekom: Rufnummern über Telefonzuordnung und Mitarbeiter/Kostenstellen-Datenbank kontieren. Sachkonto bevorzugt Telekom."},
    "deas": {"label": "DEAS", "prompt": "DEAS: Versicherung oder sonstige Leistung erkennen und passendes Sachkonto aus der Generalübersicht verwenden. Kostenstelle nur bei echter Zuordnung."},
    "vw_leasing": {"label": "VW-Leasing", "prompt": "VW-Leasing: Leasingpositionen je Fahrzeug/Kennzeichen bzw. Fahrer kontieren. Sachkonto bevorzugt VW-Leasing."},
    "vw_versicherungen": {"label": "VW-Versicherungen", "prompt": "VW-Versicherungen: Versicherungspositionen je Fahrzeug/Kennzeichen bzw. Fahrer kontieren. Sachkonto bevorzugt VW-Versicherungen."},
    "sonstige": {"label": "Sonstige", "prompt": "Sonstige Lieferanten: Kostenart aus Rechnung ableiten. Wenn keine Kostenart eindeutig ist, Sachkonto Sonstige verwenden. Kostenstelle nie erfinden."},
}
DEFAULT_GENERAL_PROMPT = """Du bist der AFI-Upload-Assistent für FiBu Mate.

Verarbeite die angehängte Rechnung zusammen mit diesen Kontierungsdatenbanken:
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

def _norm_key(value):
    return re.sub(r"[^a-z0-9a-zäöüß]+", "_", str(value or "").strip().casefold()).strip("_") or "supplier"

def _ensure_db():
    os.makedirs(DB_DIR, exist_ok=True)
    con = sqlite3.connect(PROMPT_DB)
    try:
        con.execute("create table if not exists settings (key text primary key, value text not null)")
        con.execute("create table if not exists general_prompt (id integer primary key check (id=1), prompt_text text not null, updated_at text, updated_by text)")
        con.execute("create table if not exists supplier_prompts (supplier_key text primary key, supplier_label text not null, prompt_text text not null, active integer not null default 1, updated_at text, updated_by text)")
        con.execute("insert or ignore into general_prompt(id,prompt_text,updated_at,updated_by) values (1,?,?,?)", (DEFAULT_GENERAL_PROMPT, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        for key, data in SUPPLIER_DEFAULTS.items():
            con.execute("insert or ignore into supplier_prompts(supplier_key,supplier_label,prompt_text,active,updated_at,updated_by) values (?,?,?,?,?,?)", (key, data["label"], data["prompt"], 1, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", "")))
        con.execute("insert or ignore into settings(key,value) values (?,?)", ("costcenter_db", DEFAULT_COSTCENTER_DB))
        con.execute("insert or ignore into settings(key,value) values (?,?)", ("general_db", DEFAULT_GENERAL_DB))
        con.commit()
    finally:
        con.close()

def _load_general_prompt():
    _ensure_db(); con = sqlite3.connect(PROMPT_DB)
    try:
        row = con.execute("select prompt_text from general_prompt where id=1").fetchone(); return row[0] if row else DEFAULT_GENERAL_PROMPT
    finally: con.close()

def _save_general_prompt(text):
    _ensure_db(); con = sqlite3.connect(PROMPT_DB)
    try:
        con.execute("insert into general_prompt(id,prompt_text,updated_at,updated_by) values(1,?,?,?) on conflict(id) do update set prompt_text=excluded.prompt_text, updated_at=excluded.updated_at, updated_by=excluded.updated_by", (text, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", ""))); con.commit()
    finally: con.close()

def _db_get_setting(key, default=""):
    _ensure_db(); con = sqlite3.connect(PROMPT_DB)
    try:
        row=con.execute("select value from settings where key=?", (key,)).fetchone(); return row[0] if row else default
    finally: con.close()

def _db_set_setting(key, value):
    _ensure_db(); con = sqlite3.connect(PROMPT_DB)
    try:
        con.execute("insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value", (key, value)); con.commit()
    finally: con.close()

def _load_suppliers():
    _ensure_db(); con = sqlite3.connect(PROMPT_DB)
    try:
        rows=con.execute("select supplier_key, supplier_label, prompt_text, active from supplier_prompts order by supplier_label").fetchall()
        return [{"key": r[0], "label": r[1], "prompt": r[2], "active": bool(r[3])} for r in rows]
    finally: con.close()

def _save_supplier(key, label, prompt, active=True):
    _ensure_db(); key=_norm_key(key or label); con=sqlite3.connect(PROMPT_DB)
    try:
        con.execute("insert into supplier_prompts(supplier_key,supplier_label,prompt_text,active,updated_at,updated_by) values(?,?,?,?,?,?) on conflict(supplier_key) do update set supplier_label=excluded.supplier_label, prompt_text=excluded.prompt_text, active=excluded.active, updated_at=excluded.updated_at, updated_by=excluded.updated_by", (key, label or key, prompt or "", 1 if active else 0, datetime.now().isoformat(timespec="seconds"), os.environ.get("USERNAME", ""))); con.commit()
    finally: con.close()

def _build_prompt(invoice, costcenter_db, general_db, supplier_label, supplier_prompt, general_prompt):
    return f"""{general_prompt.strip()}

LIEFERANT / AUSGEWÄHLTER PROMPT:
{supplier_label}

LIEFERANTENSPEZIFISCHE REGELN:
{supplier_prompt.strip()}

ANGEHÄNGTE DATEIEN:
1. Rechnung: {os.path.basename(invoice)}
2. Mitarbeiter-/Kostenstellen-Datenbank: {os.path.basename(costcenter_db)}
3. Generalübersicht/Sachkonten/KFZ/Telefon: {os.path.basename(general_db)}

Bitte analysiere die drei angehängten Dateien vollständig und gib als Antwort die AFI-CSV nach den Regeln aus.
""".strip()

def _run_detached(command):
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)); return True
    except Exception: return False

def _open_teams_new_context():
    launched = _run_detached(["cmd", "/c", "start", "", "msteams:"])
    launched = _run_detached(["explorer.exe", "shell:AppsFolder\\MSTeams_8wekyb3d8bbwe!MSTeams"]) or launched
    try: webbrowser.open_new("https://teams.microsoft.com/v2/"); launched=True
    except Exception: pass
    return launched

def _focus_teams():
    script="$wshell = New-Object -ComObject wscript.shell; Start-Sleep -Milliseconds 1200; $wshell.AppActivate('Microsoft Teams') | Out-Null; $wshell.AppActivate('Teams') | Out-Null"
    return _run_detached(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])

def _ps_literal(value):
    return "'" + str(value or "").replace("'", "''") + "'"

def _set_clipboard_prompt_and_files(prompt, files):
    existing=[str(Path(f)) for f in files if f and Path(f).is_file()]
    if not existing:
        return False, "Keine gültigen Dateien für die Zwischenablage gefunden."
    temp=Path(os.environ.get("TEMP", str(Path.home()))) / f"afi_copilot_prompt_{datetime.now():%Y%m%d_%H%M%S_%f}.txt"
    temp.write_text(prompt or "", encoding="utf-8")
    file_literals=",".join(_ps_literal(f) for f in existing)
    script=f"""
Add-Type -AssemblyName System.Windows.Forms
$prompt = Get-Content -LiteralPath {_ps_literal(str(temp))} -Raw -Encoding UTF8
$files = New-Object System.Collections.Specialized.StringCollection
[void]$files.AddRange([string[]]@({file_literals}))
$data = New-Object System.Windows.Forms.DataObject
$data.SetData([System.Windows.Forms.DataFormats]::UnicodeText, $true, $prompt)
$data.SetData([System.Windows.Forms.DataFormats]::Text, $true, $prompt)
$data.SetFileDropList($files)
[System.Windows.Forms.Clipboard]::SetDataObject($data, $true)
"""
    try:
        cp=subprocess.run(["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", script], capture_output=True, text=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if cp.returncode == 0:
            return True, f"Zwischenablage enthält Prompt und {len(existing)} Dateien."
        return False, (cp.stderr or cp.stdout or "PowerShell-Clipboard fehlgeschlagen.")[-800:]
    except Exception as exc:
        return False, str(exc)

class AFICopilotUI:
    def __init__(self, app, automation=False):
        self.app=app; self.root=app.root; self.canvas=app.canvas; self.bg=getattr(app, "BG", "#E8EEF5"); self.automation=automation
        _ensure_db()
        self.invoice_var=tk.StringVar(); self.costcenter_var=tk.StringVar(value=_db_get_setting("costcenter_db", DEFAULT_COSTCENTER_DB)); self.general_db_var=tk.StringVar(value=_db_get_setting("general_db", DEFAULT_GENERAL_DB))
        suppliers=_load_suppliers(); self.supplier_label_var=tk.StringVar(value=(suppliers[0]["label"] if suppliers else "Weitere Lieferanten / generisch")); self.status_var=tk.StringVar(value="Bereit")
        self.prompt_preview=None; self.general_text=None; self.supplier_list=None; self.supplier_text=None; self.supplier_key_var=tk.StringVar(); self.supplier_name_var=tk.StringVar(); self.db_open=False; self.db_frame=None; self.db_toggle_button=None
    def _supplier_by_label(self,label):
        suppliers=_load_suppliers()
        for item in suppliers:
            if item["label"]==label: return item
        return suppliers[0] if suppliers else {"key":"generic","label":"Weitere Lieferanten / generisch","prompt":""}
    def render(self):
        try:
            self.canvas.delete("all"); self.app.draw_background(); self.app.draw_header("AFI-Upload über Copilot" + (" - Auto" if self.automation else " - stabil")); self.app.draw_path_bar()
        except Exception: pass
        width=max(1100,self.canvas.winfo_width()-60); height=max(690,self.canvas.winfo_height()-175)
        frame=tk.Frame(self.canvas,bg=self.bg); self.canvas.create_window(30,132,window=frame,anchor="nw",width=width,height=height); frame.rowconfigure(0,weight=1); frame.columnconfigure(0,weight=1)
        nb=ttk.Notebook(frame); nb.grid(row=0,column=0,sticky="nsew"); main=tk.Frame(nb,bg=self.bg); prompts=tk.Frame(nb,bg=self.bg); nb.add(main,text="Verarbeitung"); nb.add(prompts,text="Prompts & Lieferanten"); self._render_main(main); self._render_prompts(prompts)
    def _toggle_db(self):
        self.db_open=not self.db_open
        if self.db_frame: self.db_frame.grid() if self.db_open else self.db_frame.grid_remove()
        if self.db_toggle_button: self.db_toggle_button.configure(text="Datenbankpfade ausblenden ▲" if self.db_open else "Datenbankpfade anzeigen ▼")
    def _render_main(self,parent):
        parent.columnconfigure(1,weight=1); parent.rowconfigure(6,weight=1)
        tk.Label(parent,text="Rechnung",bg=self.bg).grid(row=0,column=0,sticky="w",padx=10,pady=8); tk.Entry(parent,textvariable=self.invoice_var).grid(row=0,column=1,sticky="ew",padx=8,pady=8); tk.Button(parent,text="Auswählen",command=self.pick_invoice).grid(row=0,column=2,padx=8,pady=8)
        self.db_toggle_button=tk.Button(parent,text="Datenbankpfade anzeigen ▼",command=self._toggle_db,bg="#D9E2F3"); self.db_toggle_button.grid(row=1,column=0,columnspan=3,sticky="w",padx=10,pady=(0,4))
        self.db_frame=tk.Frame(parent,bg=self.bg); self.db_frame.grid(row=2,column=0,columnspan=3,sticky="ew",padx=10,pady=(0,6)); self.db_frame.columnconfigure(1,weight=1)
        tk.Label(self.db_frame,text="Datenbank 1: Mitarbeiter/Kostenstelle",bg=self.bg).grid(row=0,column=0,sticky="w",pady=3); tk.Entry(self.db_frame,textvariable=self.costcenter_var).grid(row=0,column=1,sticky="ew",padx=8,pady=3); tk.Button(self.db_frame,text="Ändern",command=lambda:self.pick_db(self.costcenter_var,"costcenter_db")).grid(row=0,column=2,padx=8,pady=3)
        tk.Label(self.db_frame,text="Datenbank 2: Generalübersicht",bg=self.bg).grid(row=1,column=0,sticky="w",pady=3); tk.Entry(self.db_frame,textvariable=self.general_db_var).grid(row=1,column=1,sticky="ew",padx=8,pady=3); tk.Button(self.db_frame,text="Ändern",command=lambda:self.pick_db(self.general_db_var,"general_db")).grid(row=1,column=2,padx=8,pady=3); self.db_frame.grid_remove()
        tk.Label(parent,text="Lieferant",bg=self.bg).grid(row=3,column=0,sticky="w",padx=10,pady=4); labels=[x["label"] for x in _load_suppliers() if x.get("active")]; ttk.Combobox(parent,textvariable=self.supplier_label_var,values=labels,state="readonly").grid(row=3,column=1,sticky="ew",padx=8,pady=4)
        btn_text="Neue Teams/Copilot-Instanz starten" if self.automation else "Teams/Copilot starten und Zwischenablage vorbereiten"; tk.Button(parent,text=btn_text,command=self.prepare,bg="#0F6CBD",fg="white",padx=12,pady=6).grid(row=4,column=0,columnspan=3,sticky="w",padx=10,pady=10); tk.Label(parent,textvariable=self.status_var,bg=self.bg,fg="#44536A").grid(row=4,column=1,columnspan=2,sticky="e",padx=10)
        tk.Label(parent,text="Ablauf: Zwischenablage enthält Prompt + drei Dateien. Teams/Copilot öffnen, Modell 'tiefere Analyse' wählen und STRG+V einfügen.",bg=self.bg,fg="#44536A",anchor="w",justify="left",wraplength=950).grid(row=5,column=0,columnspan=3,sticky="ew",padx=10)
        self.prompt_preview=tk.Text(parent,wrap="word",height=16,font=("Consolas",10)); self.prompt_preview.grid(row=6,column=0,columnspan=3,sticky="nsew",padx=10,pady=8); tk.Label(parent,text=f"Prompt-Datenbank: {PROMPT_DB}",bg=self.bg,fg="#44536A",anchor="w").grid(row=7,column=0,columnspan=3,sticky="ew",padx=10,pady=(0,8))
    def _render_prompts(self,parent):
        parent.rowconfigure(1,weight=1); parent.columnconfigure(0,weight=1); top=tk.Frame(parent,bg=self.bg); top.grid(row=0,column=0,sticky="ew",padx=10,pady=8); tk.Button(top,text="Speichern",command=self.save_prompts,bg="#0F6CBD",fg="white",padx=12).pack(side="right"); tk.Button(top,text="Lieferant neu/anlegen",command=self.new_supplier,padx=10).pack(side="right",padx=8)
        pane=ttk.Panedwindow(parent,orient="horizontal"); pane.grid(row=1,column=0,sticky="nsew",padx=10,pady=8); left=tk.Frame(pane,bg=self.bg); right=tk.Frame(pane,bg=self.bg); pane.add(left,weight=1); pane.add(right,weight=2)
        left.rowconfigure(1,weight=1); left.columnconfigure(0,weight=1); tk.Label(left,text="Generalprompt",bg=self.bg,font=("Segoe UI",10,"bold")).grid(row=0,column=0,sticky="w"); self.general_text=tk.Text(left,wrap="word",font=("Consolas",10)); self.general_text.grid(row=1,column=0,sticky="nsew"); self.general_text.insert("1.0",_load_general_prompt())
        right.columnconfigure(1,weight=1); right.rowconfigure(4,weight=1); tk.Label(right,text="Lieferantenprompts",bg=self.bg,font=("Segoe UI",10,"bold")).grid(row=0,column=0,columnspan=2,sticky="w"); self.supplier_list=tk.Listbox(right,height=10); self.supplier_list.grid(row=1,column=0,rowspan=4,sticky="nsew",padx=(0,8))
        for item in _load_suppliers(): self.supplier_list.insert("end",item["label"])
        self.supplier_list.bind("<<ListboxSelect>>",self.load_selected_supplier); tk.Label(right,text="Schlüssel",bg=self.bg).grid(row=1,column=1,sticky="w"); tk.Entry(right,textvariable=self.supplier_key_var).grid(row=1,column=2,sticky="ew"); tk.Label(right,text="Name",bg=self.bg).grid(row=2,column=1,sticky="w"); tk.Entry(right,textvariable=self.supplier_name_var).grid(row=2,column=2,sticky="ew"); tk.Label(right,text="Prompt",bg=self.bg).grid(row=3,column=1,columnspan=2,sticky="w"); self.supplier_text=tk.Text(right,wrap="word",font=("Consolas",10)); self.supplier_text.grid(row=4,column=1,columnspan=2,sticky="nsew")
        if self.supplier_list.size(): self.supplier_list.selection_set(0); self.load_selected_supplier()
    def pick_invoice(self):
        path=filedialog.askopenfilename(title="Rechnung auswählen",filetypes=[("Rechnungen","*.pdf *.xlsx *.xlsm *.csv *.docx"),("Alle Dateien","*.*")])
        if path: self.invoice_var.set(path)
    def pick_db(self,var,key):
        path=filedialog.askopenfilename(title="Datenbank auswählen",filetypes=[("Excel","*.xlsx *.xlsm"),("Alle Dateien","*.*")])
        if path: var.set(path); _db_set_setting(key,path)
    def load_selected_supplier(self,event=None):
        sel=self.supplier_list.curselection() if self.supplier_list else []
        if not sel: return
        item=self._supplier_by_label(self.supplier_list.get(sel[0])); self.supplier_key_var.set(item["key"]); self.supplier_name_var.set(item["label"]); self.supplier_text.delete("1.0","end"); self.supplier_text.insert("1.0",item["prompt"])
    def new_supplier(self):
        self.supplier_key_var.set("neuer_lieferant"); self.supplier_name_var.set("Neuer Lieferant"); self.supplier_text.delete("1.0","end"); self.supplier_text.insert("1.0","Lieferantenspezifische Regeln hier erfassen.")
    def save_prompts(self):
        _save_general_prompt(self.general_text.get("1.0","end-1c")); _save_supplier(self.supplier_key_var.get(),self.supplier_name_var.get(),self.supplier_text.get("1.0","end-1c"),True); messagebox.showinfo(MODULE_TITLE,"Prompts wurden zentral gespeichert.\n\n"+PROMPT_DB); self.render()
    def prepare(self):
        invoice=self.invoice_var.get().strip(); costcenter=self.costcenter_var.get().strip(); general=self.general_db_var.get().strip(); missing=[p for p in (invoice,costcenter,general) if not p or not os.path.exists(p)]
        if missing: messagebox.showwarning(MODULE_TITLE,"Bitte Rechnung und beide Datenbanken prüfen. Nicht gefunden:\n"+"\n".join(missing)); return
        item=self._supplier_by_label(self.supplier_label_var.get()); prompt=_build_prompt(invoice,costcenter,general,item["label"],item["prompt"],_load_general_prompt())
        self.prompt_preview.delete("1.0","end"); self.prompt_preview.insert("1.0",prompt); ok,msg=_set_clipboard_prompt_and_files(prompt,[invoice,costcenter,general])
        if not ok:
            self.root.clipboard_clear(); self.root.clipboard_append(prompt); self.root.update(); messagebox.showwarning(MODULE_TITLE,"Prompt + Dateien konnten nicht gemeinsam in die Zwischenablage gelegt werden.\n\n"+msg+"\n\nFallback: Nur Prompt wurde kopiert.")
        _open_teams_new_context(); _focus_teams()
        if self.automation: self._attempt_automation()
        else:
            self.status_var.set(msg if ok else "Fallback: nur Prompt kopiert."); messagebox.showinfo(MODULE_TITLE,"Teams/Copilot wurde geöffnet.\n\nZwischenablage: "+msg+"\n\nWeitere Schritte:\n1. Copilot öffnen\n2. Modell 'tiefere Analyse' wählen\n3. STRG+V einfügen\n4. Prüfen, ob Prompt und alle drei Dateien übernommen wurden\n5. Absenden")
    def _attempt_automation(self):
        script="$wshell = New-Object -ComObject wscript.shell; Start-Sleep -Seconds 2; $wshell.AppActivate('Microsoft Teams') | Out-Null; Start-Sleep -Milliseconds 700; $wshell.SendKeys('^v')"
        _run_detached(["powershell","-NoProfile","-ExecutionPolicy","Bypass","-Command",script]); self.status_var.set("Teams/Copilot geöffnet; kombinierte Zwischenablage wurde per STRG+V eingefügt. Bitte Modellwahl und Anhänge prüfen."); messagebox.showinfo(MODULE_TITLE,"Automationsversuch gestartet.\n\nBitte kontrollieren:\n1. Copilot geöffnet\n2. Modell 'tiefere Analyse' gewählt\n3. Prompt eingefügt\n4. alle drei Dateien angehängt\n5. absenden")

def render(app):
    ui=AFICopilotUI(app, automation=AUTOMATION_MODE); app._afi_copilot_ui=ui; ui.render()
