import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    Image = None
    ImageTk = None
    PIL_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except Exception:
    fitz = None
    PYMUPDF_AVAILABLE = False

# Reuse extraction logic from Nike - PDF zu Excel (do not modify that module)
try:
    from . import nike_pdf_to_excel as nike_parser
except Exception:
    try:
        import nike_pdf_to_excel as nike_parser
    except Exception:
        nike_parser = None

BLUE = "#004B93"
BG = "#E8EEF5"
HEADER = "#D3DEE9"
TEXT = "#182431"
TEXT2 = "#445364"
WHITE = "#FFFFFF"

ICON_DIR = Path(__file__).resolve().parent.parent / "Imgs" / "Icons" if Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / "bin" / "Imgs" / "Icons"
PDF_ICON = "ext_pdf_filetype_icon_176234.ico"
SEARCH_ICON = "1486503763-bigger-enlarge-search-magnifier-magnify-zoom_81256.ico"

MODULE_TITLE = "Rechnungen aus Ordner sammeln"
INVOICE_PATTERN = re.compile(r"6\d{9}")


def load_icon_photo(widget, icon_file, max_w=20, max_h=20):
    if not PIL_AVAILABLE:
        return None
    path = ICON_DIR / icon_file
    if not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        ow, oh = img.size
        scale = min(1, max_w / max(1, ow), max_h / max(1, oh))
        img = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def extract_invoice_from_text(value):
    if value is None:
        return ""
    text = str(value).strip().replace(" ", "").replace("\t", "").replace("\xa0", "")
    m = INVOICE_PATTERN.search(text)
    return m.group(0) if m else ""


def extract_invoice_from_pdf(pdf_path: str) -> str:
    if not pdf_path or not PYMUPDF_AVAILABLE or fitz is None:
        return ""
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return ""
    try:
        full_text = ""
        if nike_parser is not None and hasattr(nike_parser, "extract_text_from_document"):
            try:
                full_text = nike_parser.extract_text_from_document(doc)
            except Exception:
                full_text = ""
        if not full_text:
            parts = []
            for page in doc:
                try:
                    t = page.get_text("text")
                    if t:
                        parts.append(t)
                except Exception:
                    continue
            full_text = "\n".join(parts)
        if nike_parser is not None and hasattr(nike_parser, "parse_invoice_metadata"):
            try:
                _d, inv = nike_parser.parse_invoice_metadata(full_text)
                inv = extract_invoice_from_text(inv)
                if inv:
                    return inv
            except Exception:
                pass
        return extract_invoice_from_text(full_text)
    finally:
        try:
            doc.close()
        except Exception:
            pass


def parse_pasted_invoice_list(pasted: str):
    pasted = pasted or ""
    found = INVOICE_PATTERN.findall(str(pasted))
    out = []
    for x in found:
        if x and x not in out:
            out.append(x)
    return out


def open_file(path: str):
    if not path:
        return
    try:
        if os.name == "nt":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class InvoicePDFCollectorUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.include_subfolders = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Bitte Rechnungsnummern einfügen und Ordner auswählen.")
        self.last_dst = ""

        self.worker = None
        self.queue = queue.Queue()

        self.frame = tk.Frame(self.root, bg=BG)
        self.app.widget_items.append(self.frame)
        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", width=self.canvas.winfo_width(), height=max(420, self.canvas.winfo_height() - 172))
        self.render()

    def render(self):
        for child in self.frame.winfo_children():
            child.destroy()

        outer = tk.Frame(self.frame, bg=BG)
        outer.pack(fill="both", expand=True, padx=36, pady=24)

        tk.Label(outer, text=MODULE_TITLE, bg=BG, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(
            outer,
            text=(
                "Füge eine Excel-Spalte mit Rechnungsnummern (10-stellig, beginnend mit 6) per Copy/Paste ein. "
                "FiBu Mate durchsucht den Quellordner inkl. Unterordner (rekursiv), liest die Rechnungsnummer aus dem PDF-Inhalt "
                "(Logik wie im Modul 'Nike - PDF zu Excel') und kopiert Treffer flach in den Zielordner."
            ),
            bg=BG,
            fg=TEXT2,
            font=("Segoe UI", 11),
            wraplength=max(520, self.canvas.winfo_width() - 120),
            justify="left",
        ).pack(anchor="w", pady=(0, 18))

        form = tk.Frame(outer, bg=WHITE, bd=1, relief="solid")
        form.pack(fill="x", pady=(0, 12))

        self.path_row(form, 0, "Quellordner PDFs", self.src_var, self.select_src, icon_file=SEARCH_ICON)
        self.path_row(form, 1, "Zielordner Kopie", self.dst_var, self.select_dst, icon_file=PDF_ICON)

        opt = tk.Frame(form, bg=WHITE)
        opt.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))
        tk.Checkbutton(opt, text="Unterordner einbeziehen (rekursiv) – empfohlen", variable=self.include_subfolders, bg=WHITE, fg=TEXT, activebackground=WHITE).pack(side="left")

        paste_box = tk.Frame(outer, bg=WHITE, bd=1, relief="solid")
        paste_box.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(paste_box, text="Rechnungsnummern (Excel-Spalte einfügen)", bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        self.text = tk.Text(paste_box, height=10, wrap="none", bg="#F8FAFC", fg=TEXT, relief="solid", bd=1)
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        controls = tk.Frame(outer, bg=BG)
        controls.pack(fill="x", pady=(4, 12))

        self.run_button = tk.Button(controls, text="Suchen + Kopieren", command=self.run, bg=BLUE, fg="white", bd=0, padx=18, pady=9, cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.run_button.pack(side="left", padx=(0, 10))

        self.open_button = tk.Button(controls, text="Zielordner öffnen", command=self.open_dst, bg=HEADER, fg=TEXT, bd=0, padx=18, pady=9, cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.open_button.pack(side="left")

        self.progress = ttk.Progressbar(outer, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(6, 10))
        tk.Label(outer, textvariable=self.status_var, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).pack(anchor="w")

        self.set_busy(False)

    def path_row(self, parent, row, label, variable, command, icon_file=None):
        # Auswählen + Icon links, dann Label, dann Pfad
        photo = load_icon_photo(parent, icon_file or PDF_ICON, 18, 18)
        btn = tk.Button(parent, text="Auswählen", command=command, bg=BLUE, fg="white", bd=0, padx=12, pady=6, cursor="hand2",
                        compound="left" if photo else "none", image=photo if photo else "", anchor="center")
        if photo:
            btn.image = photo
        btn.grid(row=row, column=0, padx=(12, 8), pady=10, sticky="w")

        tk.Label(parent, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold"), width=18, anchor="w").grid(row=row, column=1, padx=(0, 10), pady=10, sticky="w")
        tk.Entry(parent, textvariable=variable, bg="#F8FAFC", fg=TEXT, relief="solid", bd=1, width=90).grid(row=row, column=2, padx=(0, 12), pady=10, sticky="ew")
        parent.grid_columnconfigure(2, weight=1)

    def select_src(self):
        path = filedialog.askdirectory(title="Quellordner mit PDFs auswählen")
        if path:
            self.src_var.set(path)

    def select_dst(self):
        path = filedialog.askdirectory(title="Zielordner auswählen")
        if path:
            self.dst_var.set(path)
            self.last_dst = path

    def open_dst(self):
        p = self.last_dst or self.dst_var.get().strip()
        if p and os.path.isdir(p):
            open_file(p)

    def export_available(self):
        p = self.last_dst or self.dst_var.get().strip()
        return bool(p and os.path.isdir(p))

    def set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.run_button.config(state=state, cursor="arrow" if busy else "hand2")
        open_state = "normal" if (not busy and self.export_available()) else "disabled"
        self.open_button.config(state=open_state, cursor="hand2" if open_state == "normal" else "arrow")

    def set_progress(self, value, status):
        self.progress["value"] = max(0, min(100, int(value)))
        self.status_var.set(status)

    def run(self):
        if self.worker and self.worker.is_alive():
            return

        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        invoices = parse_pasted_invoice_list(self.text.get("1.0", "end"))

        if not src or not os.path.isdir(src):
            messagebox.showwarning(MODULE_TITLE, "Bitte einen gültigen Quellordner auswählen.")
            return
        if not dst or not os.path.isdir(dst):
            messagebox.showwarning(MODULE_TITLE, "Bitte einen gültigen Zielordner auswählen.")
            return
        if not invoices:
            messagebox.showwarning(MODULE_TITLE, "Keine gültigen Rechnungsnummern gefunden (10-stellig, beginnend mit 6).")
            return
        if not PYMUPDF_AVAILABLE:
            messagebox.showwarning(MODULE_TITLE, "PyMuPDF ist nicht verfügbar. Bitte installieren: python -m pip install pymupdf")
            return

        self.last_dst = dst
        self.set_busy(True)
        self.set_progress(3, f"Starte… {len(invoices)} Rechnungsnummern geladen.")

        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except Exception:
                break

        self.worker = threading.Thread(target=self._worker, args=(src, dst, invoices, bool(self.include_subfolders.get())), daemon=True)
        self.worker.start()
        self.root.after(120, self.process_queue)

    def _copy_flat(self, src_path: Path, dst_dir: Path) -> str:
        dst_dir.mkdir(parents=True, exist_ok=True)
        target = dst_dir / src_path.name
        if not target.exists():
            shutil.copy2(str(src_path), str(target))
            return str(target)
        stem, suf = src_path.stem, src_path.suffix
        for i in range(2, 9999):
            alt = dst_dir / f"{stem}__{i}{suf}"
            if not alt.exists():
                shutil.copy2(str(src_path), str(alt))
                return str(alt)
        shutil.copy2(str(src_path), str(target))
        return str(target)

    def _worker(self, src_folder, dst_folder, invoices, recursive):
        try:
            wanted = set(invoices)
            base = Path(src_folder)
            pdfs = list(base.rglob("*.pdf") if recursive else base.glob("*.pdf"))
            total = len(pdfs)
            if total == 0:
                self.queue.put(("error", "Im Quellordner wurden keine PDF-Dateien gefunden."))
                return

            dst_dir = Path(dst_folder)
            found = set()
            copied = []

            for idx, p in enumerate(pdfs, start=1):
                if idx == 1 or idx % 25 == 0 or idx == total:
                    self.queue.put(("progress", 5 + int(idx / max(1, total) * 75), f"Analysiere PDF {idx}/{total}: {p.name}"))

                inv = extract_invoice_from_pdf(str(p))
                if inv and inv in wanted and inv not in found:
                    found.add(inv)
                    try:
                        copied.append(self._copy_flat(p, dst_dir))
                    except Exception:
                        pass
                    if len(found) == len(wanted):
                        break

            missing = [x for x in invoices if x not in found]
            self.queue.put(("done", {
                "requested": len(invoices),
                "pdf_total": total,
                "found_invoices": len(found),
                "missing_invoices": len(missing),
                "missing_list": missing,
                "copied_files": copied,
                "dst": dst_folder,
                "recursive": bool(recursive),
            }))
        except Exception as exc:
            self.queue.put(("error", str(exc)))

    def process_queue(self):
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]
                if kind == "progress":
                    self.set_progress(item[1], item[2])
                elif kind == "done":
                    payload = item[1]
                    note = "inkl. Unterordner" if payload.get("recursive") else "ohne Unterordner"
                    self.set_progress(100, f"Fertig ({note}): {payload['found_invoices']}/{payload['requested']} Rechnungsnummern gefunden. Dateien kopiert: {len(payload['copied_files'])}.")
                    self.set_busy(False)

                    msg = f"""Fertig ({note}).

Rechnungsnummern (gewünscht): {payload['requested']}
PDFs geprüft: {payload['pdf_total']}
Rechnungsnummern gefunden: {payload['found_invoices']}
Fehlend: {payload['missing_invoices']}
Dateien kopiert: {len(payload['copied_files'])}

Zielordner:
{payload['dst']}"""

                    if payload.get("missing_invoices") and payload.get("missing_list") and payload["missing_invoices"] <= 15:
                        msg += f"""

Fehlende Rechnungsnummern:
{', '.join(payload['missing_list'])}"""

                    messagebox.showinfo(MODULE_TITLE, msg)
                    return
                elif kind == "error":
                    self.set_progress(0, "Fehler beim Suchen/Kopieren.")
                    self.set_busy(False)
                    messagebox.showerror(MODULE_TITLE, item[1])
                    return
        except queue.Empty:
            pass

        if self.worker and self.worker.is_alive():
            self.root.after(120, self.process_queue)
        else:
            self.set_busy(False)


def render(app):
    InvoicePDFCollectorUI(app)
