import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
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

MODULE_TITLE = "Nike - Rechnungs-PDFs in Sammelordner"
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


def collect_pdf_files(src_folder: str, recursive: bool):
    """Sammelt PDF-Dateien robust und case-insensitive."""
    base = Path(src_folder)
    if not base.exists() or not base.is_dir():
        return []

    def is_pdf_file(p: Path) -> bool:
        try:
            return p.is_file() and p.suffix.casefold() == ".pdf"
        except Exception:
            return False

    if recursive:
        pdfs = [p for p in base.rglob("*") if is_pdf_file(p)]
    else:
        pdfs = [p for p in base.iterdir() if is_pdf_file(p)]

    return sorted(pdfs, key=lambda p: str(p).casefold())


def collect_zip_files(src_folder: str, recursive: bool):
    """Sammelt ZIP-Dateien robust und case-insensitive."""
    base = Path(src_folder)
    if not base.exists() or not base.is_dir():
        return []

    def is_zip_file(p: Path) -> bool:
        try:
            return p.is_file() and p.suffix.casefold() == ".zip"
        except Exception:
            return False

    if recursive:
        zips = [p for p in base.rglob("*") if is_zip_file(p)]
    else:
        zips = [p for p in base.iterdir() if is_zip_file(p)]

    return sorted(zips, key=lambda p: str(p).casefold())


def safe_zip_member_name(member_name: str) -> str:
    """Erzeugt einen ungefährlichen flachen Dateinamen aus einem ZIP-Pfad."""
    name = str(member_name or "").replace("\\", "/").split("/")[-1].strip()
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    return name or "zip_pdf.pdf"


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
                "FiBu Mate durchsucht PDF-Dateien im Quellordner, Unterordnern und zusätzlich PDF-Dateien innerhalb von ZIP-Dateien. "
                "Treffer werden flach in den Zielordner kopiert."
            ),
            bg=BG,
            fg=TEXT2,
            font=("Segoe UI", 11),
            wraplength=max(520, self.canvas.winfo_width() - 120),
            justify="left",
        ).pack(anchor="w", pady=(0, 18))

        form = tk.Frame(outer, bg=WHITE, bd=1, relief="solid")
        form.pack(fill="x", pady=(0, 12))

        self.path_row(form, 0, "Quellordner PDFs/ZIPs", self.src_var, self.select_src, icon_file=SEARCH_ICON)
        self.path_row(form, 1, "Zielordner Kopie", self.dst_var, self.select_dst, icon_file=PDF_ICON)

        opt = tk.Frame(form, bg=WHITE)
        opt.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))
        tk.Checkbutton(opt, text="Unterordner einbeziehen (rekursiv) – auch für ZIP-Dateien", variable=self.include_subfolders, bg=WHITE, fg=TEXT, activebackground=WHITE).pack(side="left")

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

        self.progress = ttk.Progressbar(outer, orient="horizontal", mode="determinate", length=520)
        self.progress.pack(fill="x", pady=(4, 8))

        tk.Label(outer, textvariable=self.status_var, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).pack(anchor="w")
        self.set_busy(False)

    def path_row(self, parent, row, label, variable, command, icon_file=None):
        parent.grid_columnconfigure(1, weight=1)
        tk.Label(parent, text=label, bg=WHITE, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", padx=12, pady=10)
        entry = tk.Entry(parent, textvariable=variable, bg="#F8FAFC", fg=TEXT, relief="solid", bd=1)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 10), pady=10)
        photo = load_icon_photo(parent, icon_file or PDF_ICON, 18, 18)
        btn = tk.Button(parent, text="Auswählen", image=photo, compound="left" if photo else None, command=command, bg=HEADER, fg=TEXT, bd=0, padx=12, pady=6, cursor="hand2")
        btn.image = photo
        btn.grid(row=row, column=2, sticky="e", padx=12, pady=10)

    def select_src(self):
        path = filedialog.askdirectory(title="Quellordner mit PDFs/ZIPs auswählen")
        if path:
            self.src_var.set(path)

    def select_dst(self):
        path = filedialog.askdirectory(title="Zielordner auswählen")
        if path:
            self.dst_var.set(path)
            self.last_dst = path
            self.set_busy(False)

    def open_dst(self):
        open_file(self.last_dst or self.dst_var.get().strip())

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

    def _copy_bytes_flat(self, content: bytes, original_name: str, dst_dir: Path) -> str:
        dst_dir.mkdir(parents=True, exist_ok=True)
        safe_name = safe_zip_member_name(original_name)
        if not safe_name.casefold().endswith(".pdf"):
            safe_name += ".pdf"
        target = dst_dir / safe_name
        if not target.exists():
            target.write_bytes(content)
            return str(target)
        stem, suf = target.stem, target.suffix
        for i in range(2, 9999):
            alt = dst_dir / f"{stem}__{i}{suf}"
            if not alt.exists():
                alt.write_bytes(content)
                return str(alt)
        target.write_bytes(content)
        return str(target)

    def _worker(self, src_folder, dst_folder, invoices, recursive):
        try:
            wanted = set(invoices)
            base = Path(src_folder)
            pdfs = collect_pdf_files(str(base), recursive)
            zips = collect_zip_files(str(base), recursive)
            total_regular = len(pdfs)
            total_zip_archives = len(zips)
            total_zip_pdfs = 0

            dst_dir = Path(dst_folder)
            found = set()
            copied = []

            if total_regular == 0 and total_zip_archives == 0:
                self.queue.put(("error", "Im Quellordner wurden keine PDF- oder ZIP-Dateien gefunden."))
                return

            for idx, p in enumerate(pdfs, start=1):
                if idx == 1 or idx % 25 == 0 or idx == total_regular:
                    self.queue.put(("progress", 5 + int(idx / max(1, total_regular + total_zip_archives) * 45), f"Analysiere PDF {idx}/{total_regular}: {p.name}"))
                inv = extract_invoice_from_pdf(str(p))
                if inv and inv in wanted and inv not in found:
                    found.add(inv)
                    try:
                        copied.append(self._copy_flat(p, dst_dir))
                    except Exception:
                        pass
                    if len(found) == len(wanted):
                        break

            if len(found) < len(wanted):
                with tempfile.TemporaryDirectory(prefix="fibu_mate_pdfcollector_") as temp_dir:
                    temp_base = Path(temp_dir)
                    for zip_idx, zip_path in enumerate(zips, start=1):
                        if len(found) == len(wanted):
                            break
                        self.queue.put(("progress", 55 + int(zip_idx / max(1, total_zip_archives) * 35), f"Prüfe ZIP {zip_idx}/{total_zip_archives}: {zip_path.name}"))
                        try:
                            with zipfile.ZipFile(str(zip_path), "r") as archive:
                                members = [m for m in archive.infolist() if not m.is_dir() and str(m.filename).casefold().endswith(".pdf")]
                                total_zip_pdfs += len(members)
                                for member_idx, member in enumerate(members, start=1):
                                    if len(found) == len(wanted):
                                        break
                                    try:
                                        pdf_bytes = archive.read(member)
                                    except Exception:
                                        continue
                                    safe_name = safe_zip_member_name(member.filename)
                                    temp_pdf = temp_base / f"zip_{zip_idx}_{member_idx}_{safe_name}"
                                    try:
                                        temp_pdf.write_bytes(pdf_bytes)
                                    except Exception:
                                        continue
                                    inv = extract_invoice_from_pdf(str(temp_pdf))
                                    if inv and inv in wanted and inv not in found:
                                        found.add(inv)
                                        try:
                                            copied.append(self._copy_bytes_flat(pdf_bytes, safe_name, dst_dir))
                                        except Exception:
                                            pass
                        except zipfile.BadZipFile:
                            continue
                        except Exception:
                            continue

            missing = [x for x in invoices if x not in found]
            self.queue.put(("done", {
                "requested": len(invoices),
                "pdf_total": total_regular + total_zip_pdfs,
                "pdf_regular_total": total_regular,
                "zip_total": total_zip_archives,
                "zip_pdf_total": total_zip_pdfs,
                "found_invoices": len(found),
                "missing_invoices": len(missing),
                "missing_list": missing,
                "copied_files": copied,
                "dst": dst_folder,
                "recursive": bool(recursive),
            }))
        except Exception as exc:
            self.queue.put(("error", str(exc)))

    def show_missing_invoices_popup(self, missing_list):
        if not missing_list:
            return
        rows = [str(x).strip() for x in missing_list if str(x).strip()]
        if not rows:
            return
        table_text = "Rechnungsnummer\n" + "\n".join(rows)

        popup = tk.Toplevel(self.root)
        popup.title("Fehlende PDFs - Rechnungsnummern")
        popup.configure(bg=BG)
        popup.geometry("520x420")
        popup.minsize(420, 300)
        try:
            popup.transient(self.root)
            popup.grab_set()
        except Exception:
            pass

        outer = tk.Frame(popup, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=16)
        tk.Label(outer, text="Für folgende Rechnungsnummern wurde keine PDF gefunden:", bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold"), anchor="w", justify="left").pack(fill="x", pady=(0, 8))
        tk.Label(outer, text="Die Liste ist tabellarisch aufgebaut und kann direkt in Excel eingefügt werden.", bg=BG, fg=TEXT2, font=("Segoe UI", 10), anchor="w", justify="left").pack(fill="x", pady=(0, 10))

        text_frame = tk.Frame(outer, bg=WHITE, bd=1, relief="solid")
        text_frame.pack(fill="both", expand=True)
        yscroll = tk.Scrollbar(text_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")
        txt = tk.Text(text_frame, wrap="none", bg="#F8FAFC", fg=TEXT, relief="flat", bd=0, height=12, yscrollcommand=yscroll.set, font=("Consolas", 10))
        txt.pack(side="left", fill="both", expand=True)
        yscroll.config(command=txt.yview)
        txt.insert("1.0", table_text)
        txt.tag_add("sel", "1.0", "end")
        txt.focus_set()

        btns = tk.Frame(outer, bg=BG)
        btns.pack(fill="x", pady=(12, 0))

        def copy_to_clipboard():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(table_text)
                self.status_var.set(f"{len(rows)} fehlende Rechnungsnummern wurden in die Zwischenablage kopiert.")
            except Exception:
                pass

        tk.Button(btns, text="In Zwischenablage kopieren", command=copy_to_clipboard, bg=BLUE, fg="white", bd=0, padx=14, pady=8, cursor="hand2", font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Button(btns, text="Schließen", command=popup.destroy, bg=HEADER, fg=TEXT, bd=0, padx=14, pady=8, cursor="hand2", font=("Segoe UI", 10, "bold")).pack(side="right")
        copy_to_clipboard()

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
- davon direkt im Ordner: {payload.get('pdf_regular_total', payload['pdf_total'])}
- davon aus ZIP-Dateien: {payload.get('zip_pdf_total', 0)}
ZIP-Dateien geprüft: {payload.get('zip_total', 0)}
Rechnungsnummern gefunden: {payload['found_invoices']}
Fehlend: {payload['missing_invoices']}
Dateien kopiert: {len(payload['copied_files'])}

Zielordner:
{payload['dst']}"""
                    if payload.get("missing_invoices") and payload.get("missing_list"):
                        msg += "\n\nDie fehlenden Rechnungsnummern werden anschließend in einer kopierbaren Excel-Liste angezeigt."
                    messagebox.showinfo(MODULE_TITLE, msg)
                    if payload.get("missing_invoices") and payload.get("missing_list"):
                        self.show_missing_invoices_popup(payload.get("missing_list", []))
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
