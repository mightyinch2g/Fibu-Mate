# FiBuMate_PATCH_MARKER: 20260609_DEBITOREN_SERIENBRIEF_RENDER_WRAPPER

import os
import re
import sys
import time
import html
import zipfile
import tempfile
import threading
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

APP_TITLE = "Debitoren-Serienbrief"
VAT_RATE = Decimal("0.19")

RE_BASE_COLUMNS = ["Mitgliedsnummer", "Mitglied", "Aktion", "Gesamtbetrag", "Auftragsnummer", "Rechnungsdatum", "ID", "Werbeträger"]
ST_COLUMNS = ["GP-Nummer", "Filiale von", "Kontengruppe", "Name 1", "Name 2", "Straße", "Postleitzahl", "Ort", "Umsatzsteuer-Id.Nr"]
PERIOD_COLUMNS = ["Leistungszeitraum", "Lieferdatum"]
PREVIEW_LIMIT = 750
PREVIEW_COLUMNS = ["Mitgliedsnummer", "Mitglied", "Aktion", "Gesamtbetrag", "Auftragsnummer", "Rechnungsdatum", "Werbeträger", "Leistungszeitraum", "Lieferdatum"]


def clean(value):
    if value is None:
        return ""
    try:
        if pd is not None and pd.isna(value):
            return ""
    except Exception:
        pass
    return " ".join(str(value).replace("\ufeff", "").replace("\xa0", " ").strip().split())


def dec_de(value):
    s = clean(value)
    if not s:
        return Decimal("0.00")
    s = s.replace("€", "").replace("EUR", "").replace(" ", "")
    neg = s.endswith("-")
    if neg:
        s = s[:-1]
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        out = Decimal(s)
        return -out if neg else out
    except InvalidOperation:
        return Decimal("0.00")


def fmt_amount(value):
    return f"{Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}".replace(".", ",")


def date_text(value):
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%d.%m.%Y")
        except Exception:
            pass
    s = clean(value)
    if not s:
        return ""
    m = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", s)
    if m:
        return m.group(0)
    m = re.search(r"\d{4}-\d{1,2}-\d{1,2}", s)
    if m:
        try:
            return datetime.strptime(m.group(0), "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            pass
    return s


def period_text(value):
    s = clean(value)
    if not s:
        return ""
    found = re.findall(r"\d{1,2}\.\d{1,2}\.\d{4}|\d{4}-\d{1,2}-\d{1,2}", s)
    if found:
        return " - ".join(date_text(x) for x in found[:2])
    return date_text(s) or s


def member_digits(value):
    return re.sub(r"\D", "", clean(value))


def member6(value):
    d = member_digits(value)
    return d[:6] if len(d) >= 6 else d


def is_branch_no(value):
    return len(member_digits(value)) == 9


def invoice_no_from_order(order_no):
    s = clean(order_no)
    m = re.match(r"^(81)(?:/.*)?/(\d+)\s*$", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}", False
    return s, True


def safe_filename(value):
    s = clean(value) or "ohne_name"
    s = re.sub(r'[<>:"/\\|?*]+', "_", s)
    s = re.sub(r"\s+", "_", s).strip("._")
    return s[:150] or "ohne_name"


def read_excel_data(path):
    if pd is None:
        raise RuntimeError("pandas/openpyxl ist nicht verfügbar. Bitte installieren: python -m pip install pandas openpyxl")
    re_df = pd.read_excel(path, sheet_name="MG_RE", engine="openpyxl", dtype=str).fillna("")
    st_df = pd.read_excel(path, sheet_name="MG_STAMMDT", engine="openpyxl", dtype=str).fillna("")
    re_df.columns = [clean(c) for c in re_df.columns]
    st_df.columns = [clean(c) for c in st_df.columns]
    missing_re = [c for c in RE_BASE_COLUMNS if c not in re_df.columns]
    missing_st = [c for c in ST_COLUMNS if c not in st_df.columns]
    if missing_re:
        raise RuntimeError("Im Blatt MG_RE fehlen Spalten: " + ", ".join(missing_re))
    if missing_st:
        raise RuntimeError("Im Blatt MG_STAMMDT fehlen Spalten: " + ", ".join(missing_st))
    if not any(c in re_df.columns for c in PERIOD_COLUMNS):
        raise RuntimeError("Im Blatt MG_RE fehlt die Spalte Leistungszeitraum/Lieferdatum.")
    return re_df, st_df


def build_st_index(st_df):
    idx = {}
    for _, row in st_df.iterrows():
        gp = member_digits(row.get("GP-Nummer", ""))
        if gp:
            idx[gp] = row.to_dict()
    return idx


def st_value(row, col):
    return clean(row.get(col, "")) if row else ""


def st_name(row):
    n1 = st_value(row, "Name 1")
    n2 = st_value(row, "Name 2")
    return clean(f"{n1} {n2}") if n2 else n1


def st_city(row):
    return clean(f"{st_value(row, 'Postleitzahl')} {st_value(row, 'Ort')}") if row else ""


def get_period_column(re_row):
    for c in PERIOD_COLUMNS:
        if c in re_row:
            return c
    return "Lieferdatum"


def data_for_invoice(re_row, st_idx):
    raw_no = clean(re_row.get("Mitgliedsnummer", ""))
    invoice_member = member6(raw_no)
    service_no = member_digits(raw_no) if is_branch_no(raw_no) else invoice_member

    invoice_st = st_idx.get(invoice_member, {})
    service_st = st_idx.get(service_no, invoice_st)

    netto = dec_de(re_row.get("Gesamtbetrag", ""))
    mwst = (netto * VAT_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    brutto = (netto + mwst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inv_no, nonstandard = invoice_no_from_order(re_row.get("Auftragsnummer", ""))
    period_col = get_period_column(re_row)

    replacements = {
        "[Name Mitglied]": st_name(invoice_st) or clean(re_row.get("Mitglied", "")),
        "[Straße Mitglied]": st_value(invoice_st, "Straße"),
        "[PLZ + Stadt Mitglied]": st_city(invoice_st),
        "[UST-ID Mitglied]": st_value(invoice_st, "Umsatzsteuer-Id.Nr"),
        "[Name Filiale]": st_name(service_st) or st_name(invoice_st) or clean(re_row.get("Mitglied", "")),
        "[Straße Filiale]": st_value(service_st, "Straße") or st_value(invoice_st, "Straße"),
        "[PLZ + Stadt Filiale]": st_city(service_st) or st_city(invoice_st),
        "[Rechnungsnr. Ermittelt aus Auftragsnr.]": inv_no,
        "[Rechnungsdatum TT.MM.JJJJ]": date_text(re_row.get("Rechnungsdatum", "")),
        "[5XXXXX]": invoice_member,
        "[Name Aktion]": clean(re_row.get("Aktion", "")),
        "[Betrag Netto]": fmt_amount(netto),
        "[Betr. MwSt]": fmt_amount(mwst),
        "[Betrag Brutto]": fmt_amount(brutto),
        "[Lieferdatum TT.MM.JJJJ]": period_text(re_row.get(period_col, "")),
        "[Leistungszeitraum]": period_text(re_row.get(period_col, "")),
        "[81/XXXXXX/XXXXXXX/4564537]": clean(re_row.get("Auftragsnummer", "")),
        "__invoice_no__": inv_no,
        "__member__": invoice_member,
        "__file_member__": service_no if is_branch_no(raw_no) else invoice_member,
        "__nonstandard_order__": nonstandard,
    }
    return replacements


def replace_in_text_nodes(xml, replacements):
    """Split-sicherer Platzhalterersatz in Word-XML ohne Umbruch-/Run-Struktur zu zerstören.

    Wichtig: Nicht den kompletten Absatz in den ersten w:t-Run schreiben.
    Stattdessen wird nur der konkrete Platzhalterbereich ersetzt. Dadurch bleiben vorhandene
    Word-Umbrüche (<w:br/>), Absätze, Runs und Formatierungen des Textblocks erhalten.
    """
    text_pattern = re.compile(r'(<w:t[^>]*>)(.*?)(</w:t>)', re.S)
    para_pattern = re.compile(r'(<w:p[\s\S]*?</w:p>)')
    repl_items = [(k, str(v)) for k, v in replacements.items() if not str(k).startswith("__")]
    repl_items.sort(key=lambda kv: len(kv[0]), reverse=True)

    def process_para(match):
        para = match.group(1)
        nodes = list(text_pattern.finditer(para))
        if not nodes:
            return para

        node_texts = [html.unescape(n.group(2)) for n in nodes]
        starts = []
        full = ""
        for t in node_texts:
            starts.append(len(full))
            full += t

        if not any(ph in full for ph, _ in repl_items):
            return para

        for placeholder, value in repl_items:
            search_from = 0
            while True:
                pos = full.find(placeholder, search_from)
                if pos < 0:
                    break
                pos_end = pos + len(placeholder)

                # Betroffene Textknoten bestimmen.
                covered = []
                for i, t in enumerate(node_texts):
                    node_start = starts[i]
                    node_end = node_start + len(t)
                    if node_end > pos and node_start < pos_end:
                        covered.append(i)
                if not covered:
                    search_from = pos_end
                    continue

                first = covered[0]
                for i in covered:
                    t = node_texts[i]
                    node_start = starts[i]
                    local_start = max(0, pos - node_start)
                    local_end = min(len(t), pos_end - node_start)
                    before = t[:local_start]
                    after = t[local_end:]
                    if i == first:
                        node_texts[i] = before + value + after
                    else:
                        node_texts[i] = before + after

                # Full/Startpositionen nach jeder Ersetzung neu aufbauen.
                starts = []
                full = ""
                for t in node_texts:
                    starts.append(len(full))
                    full += t
                search_from = pos + len(value)

        out = []
        last = 0
        for n, new_text in zip(nodes, node_texts):
            out.append(para[last:n.start()])
            out.append(n.group(1) + html.escape(new_text, quote=False) + n.group(3))
            last = n.end()
        out.append(para[last:])
        return "".join(out)

    return para_pattern.sub(process_para, xml)

def fill_docx(template_path, out_path, replacements):
    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.startswith("word/") and item.filename.endswith(".xml"):
                    try:
                        xml = data.decode("utf-8")
                        xml = replace_in_text_nodes(xml, replacements)
                        data = xml.encode("utf-8")
                    except Exception:
                        pass
                zout.writestr(item, data)


def docx_unresolved_placeholders(path):
    found = set()
    with zipfile.ZipFile(path, "r") as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                try:
                    xml = z.read(name).decode("utf-8")
                except Exception:
                    continue
                texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.S)
                full = html.unescape("".join(texts))
                found.update(re.findall(r"\[[^\]]+\]", full))
    return sorted(found)


def export_pdf_with_word(docx_path, pdf_path):
    word = None
    doc = None
    try:
        import win32com.client
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(str(docx_path)))
        doc.SaveAs(os.path.abspath(str(pdf_path)), FileFormat=17)
        doc.Close(False)
        word.Quit()
        return True, ""
    except Exception as exc:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        return False, str(exc)


def export_pdfs_with_word_batch(pairs, cancel_event=None, progress_callback=None):
    """Exportiert mehrere DOCX-Dateien mit nur einer Word-Instanz als PDF."""
    word = None
    pdf_done = 0
    pdf_failed = []
    try:
        import win32com.client
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        for docx_path, pdf_path in pairs:
            if cancel_event is not None and cancel_event.is_set():
                break
            doc = None
            ok = False
            err_text = ""
            try:
                doc = word.Documents.Open(os.path.abspath(str(docx_path)))
                doc.SaveAs(os.path.abspath(str(pdf_path)), FileFormat=17)
                doc.Close(False)
                doc = None
                pdf_done += 1
                ok = True
            except Exception as exc:
                err_text = str(exc)
                pdf_failed.append(f"{Path(docx_path).name}: {exc}")
                try:
                    if doc is not None:
                        doc.Close(False)
                except Exception:
                    pass
            if progress_callback:
                progress_callback(pdf_done, docx_path, pdf_path, ok, err_text)
    except Exception as exc:
        pdf_failed.append(str(exc))
    finally:
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
    return pdf_done, pdf_failed
def render_pdf_first_page_to_image(pdf_path, max_width=950, max_height=1200):
    if Image is None:
        return None, "Pillow ist nicht verfügbar."
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        page = doc.load_page(0)
        rect = page.rect
        zoom = min(max_width / max(1, rect.width), max_height / max(1, rect.height), 2.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img, ""
    except Exception as exc:
        return None, str(exc)


class DebitorenSerienbriefApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1420x820")
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.attributes("-zoomed", True)
            except Exception:
                pass
        self.root.minsize(1120, 680)
        self.bg = "#E8EEF5"
        self.font = ("Segoe UI", 10)
        self.font_small = ("Segoe UI", 9)
        self.re_df = None
        self.st_df = None
        self.st_idx = {}
        self.selected_row_indices = set()
        self.column_filters = {}
        self.drag_start_iid = None
        self.cancel_event = threading.Event()
        self.export_running = False
        self.brief_image_ref = None
        self._build()

    def _build(self):
        self.root.configure(bg=self.bg)
        main = tk.Frame(self.root, bg=self.bg)
        main.pack(fill="both", expand=True, padx=12, pady=12)
        main.columnconfigure(0, weight=1, uniform="halves")
        main.columnconfigure(1, weight=1, uniform="halves")
        main.rowconfigure(0, weight=1)
        self.left = tk.Frame(main, bg=self.bg)
        self.right = tk.Frame(main, bg=self.bg)
        self.left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._build_left()
        self._build_right()

    def _build_left(self):
        self.left.columnconfigure(1, weight=1)
        here = Path(__file__).resolve().parent
        self.excel_var = tk.StringVar(value=str(here / "Prospekt März 2026 Rechnungen.xlsm") if (here / "Prospekt März 2026 Rechnungen.xlsm").exists() else "")
        self.template_var = tk.StringVar(value=str(here / "Vorlage_Rechnung_ohne_Bildbeleg_Legendiert.docx") if (here / "Vorlage_Rechnung_ohne_Bildbeleg_Legendiert.docx").exists() else "")
        self.output_var = tk.StringVar(value=str(here / "Ausgabe"))
        self.export_filtered_var = tk.BooleanVar(value=False)
        self.only_selection_var = tk.BooleanVar(value=False)
        self.count_var = tk.StringVar(value="Auswahl: 0 Zeilen")
        self.word_progress_var = tk.StringVar(value="0/0 Word-Dateien erzeugt")
        self.pdf_progress_var = tk.StringVar(value="0/0 PDF-Dateien erzeugt")

        tk.Label(self.left, text=APP_TITLE, bg=self.bg, font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        self._path_row(1, "Excel-Datenbasis", self.excel_var, self._browse_excel)
        self._path_row(2, "Word-Vorlage", self.template_var, self._browse_template)
        self._path_row(3, "Ausgabeordner", self.output_var, self._browse_output)

        opts = tk.LabelFrame(self.left, text="Ausgabeumfang", bg=self.bg, font=self.font_small)
        opts.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 6))
        tk.Checkbutton(opts, text="Alle Rechnungen nach gesetzten Filtern", variable=self.export_filtered_var, bg=self.bg, font=self.font_small, command=self._on_options_changed).grid(row=0, column=0, sticky="w", padx=8, pady=4)
        tk.Checkbutton(opts, text="Alle Rechnungen nach Markierung in Vorschau", variable=self.only_selection_var, bg=self.bg, font=self.font_small, command=self._on_options_changed).grid(row=1, column=0, sticky="w", padx=8, pady=4)
        tk.Button(opts, text="Auswahl aufheben", command=self.clear_selection, font=self.font_small).grid(row=0, column=1, rowspan=2, padx=12, pady=4)

        tk.Label(self.left, textvariable=self.count_var, bg="#DDE7F3", anchor="w", font=("Segoe UI", 10, "bold")).grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6, 6))

        actions = tk.Frame(self.left, bg=self.bg)
        actions.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(6, 6))
        actions.columnconfigure(1, weight=1)
        tk.Button(actions, text="Daten laden / Vorschau aktualisieren", command=self.load_data, font=self.font_small).grid(row=0, column=0, sticky="w")
        self.export_btn = tk.Button(actions, text="Serienbriefe erstellen", command=self.start_export, font=("Segoe UI", 10, "bold"), bg="#CFEAD6", activebackground="#BDE3C7")
        self.export_btn.grid(row=0, column=2, sticky="e")

        prog = tk.LabelFrame(self.left, text="Export-Fortschritt", bg=self.bg, font=self.font_small)
        prog.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(8, 6))
        prog.columnconfigure(0, weight=1)
        self.word_progress = ttk.Progressbar(prog, orient="horizontal", mode="determinate")
        self.pdf_progress = ttk.Progressbar(prog, orient="horizontal", mode="determinate")
        tk.Label(prog, textvariable=self.word_progress_var, bg=self.bg, font=self.font_small).grid(row=0, column=0, sticky="w", padx=6, pady=(5, 0))
        self.word_progress.grid(row=1, column=0, sticky="ew", padx=6, pady=3)
        tk.Label(prog, textvariable=self.pdf_progress_var, bg=self.bg, font=self.font_small).grid(row=2, column=0, sticky="w", padx=6, pady=(5, 0))
        self.pdf_progress.grid(row=3, column=0, sticky="ew", padx=6, pady=3)
        self.cancel_btn = tk.Button(prog, text="Abbrechen", command=self.cancel_export, font=self.font_small, state="disabled")
        self.cancel_btn.grid(row=0, column=1, rowspan=4, padx=8, pady=6, sticky="ns")

        info = tk.LabelFrame(self.left, text="Hinweise", bg=self.bg, font=self.font_small)
        info.grid(row=8, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        self.left.rowconfigure(8, weight=1)
        self.log_text = tk.Text(info, height=10, font=("Consolas", 9), wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)
        self._log("MG_RE ist die Standardvorschau. Auswahl bleibt erhalten, bis 'Auswahl aufheben' gedrückt wird.")

    def _path_row(self, row, label, var, command):
        tk.Label(self.left, text=label, bg=self.bg, font=self.font_small).grid(row=row, column=0, sticky="w", pady=3)
        tk.Entry(self.left, textvariable=var, font=self.font_small).grid(row=row, column=1, sticky="ew", padx=4, pady=3)
        tk.Button(self.left, text="…", command=command, width=3, font=self.font_small).grid(row=row, column=2, pady=3)

    def _build_right(self):
        self.right.rowconfigure(0, weight=1)
        self.right.columnconfigure(0, weight=1)
        self.tabs = ttk.Notebook(self.right)
        self.tabs.grid(row=0, column=0, sticky="nsew")
        self.tab_excel = tk.Frame(self.tabs, bg="white")
        self.tab_brief = tk.Frame(self.tabs, bg="white")
        self.tabs.add(self.tab_excel, text="Excel-Vorschau MG_RE")
        self.tabs.add(self.tab_brief, text="Ausgabe-Vorschau Brief")
        self._build_excel_preview()
        self._build_brief_preview()

    def _build_excel_preview(self):
        self.tab_excel.rowconfigure(1, weight=1)
        self.tab_excel.columnconfigure(0, weight=1)
        top = tk.Frame(self.tab_excel, bg="white")
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        tk.Label(top, text="Suche:", bg="white", font=self.font_small).grid(row=0, column=0, padx=4, pady=4)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *args: self.refresh_excel_preview())
        tk.Entry(top, textvariable=self.filter_var, font=self.font_small).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        tk.Button(top, text="Spaltenfilter zurücksetzen", command=self.clear_column_filters, font=self.font_small).grid(row=0, column=2, padx=4, pady=4)
        tk.Label(top, text="Maus ziehen = Bereich/Zeilen wählen | Klick auf Spaltenkopf = Auswahlfilter", bg="white", fg="#4A6074", font=self.font_small).grid(row=0, column=3, padx=4, pady=4)
        self.preview_status_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self.preview_status_var, bg="white", fg="#7A4B00", font=self.font_small).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 4))
        holder = tk.Frame(self.tab_excel, bg="white")
        holder.grid(row=1, column=0, sticky="nsew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        self.excel_tree = ttk.Treeview(holder, show="headings", selectmode="extended")
        vs = ttk.Scrollbar(holder, orient="vertical", command=self.excel_tree.yview)
        hs = ttk.Scrollbar(holder, orient="horizontal", command=self.excel_tree.xview)
        self.excel_tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.excel_tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.excel_tree.bind("<ButtonPress-1>", self._tree_press)
        self.excel_tree.bind("<B1-Motion>", self._tree_drag)
        self.excel_tree.bind("<ButtonRelease-1>", self._tree_release)
        self.excel_tree.bind("<<TreeviewSelect>>", lambda e: self._sync_tree_selection())

    def _build_brief_preview(self):
        self.tab_brief.rowconfigure(1, weight=1)
        self.tab_brief.columnconfigure(0, weight=1)
        toolbar = tk.Frame(self.tab_brief, bg="white")
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        tk.Button(toolbar, text="Brief-Vorschau aktualisieren", command=self.refresh_brief_preview, font=self.font_small).grid(row=0, column=0, sticky="w", padx=6, pady=5)
        tk.Label(toolbar, text="Die echte Vorschau wird aus Performancegründen nur auf Knopfdruck gerendert.", bg="white", fg="#4A6074", font=self.font_small).grid(row=0, column=1, sticky="w", padx=8, pady=5)
        self.brief_canvas = tk.Canvas(self.tab_brief, bg="white", highlightthickness=0)
        vs = ttk.Scrollbar(self.tab_brief, orient="vertical", command=self.brief_canvas.yview)
        hs = ttk.Scrollbar(self.tab_brief, orient="horizontal", command=self.brief_canvas.xview)
        self.brief_canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.brief_canvas.grid(row=1, column=0, sticky="nsew")
        vs.grid(row=1, column=1, sticky="ns")
        hs.grid(row=2, column=0, sticky="ew")
        self.show_brief_preview_placeholder()

    def _browse_excel(self):
        p = filedialog.askopenfilename(title="Excel-Datenbasis", filetypes=[("Excel", "*.xlsx *.xlsm *.xls"), ("Alle Dateien", "*.*")])
        if p:
            self.excel_var.set(p)
            self.load_data()

    def _browse_template(self):
        p = filedialog.askopenfilename(title="Word-Vorlage", filetypes=[("Word", "*.docx"), ("Alle Dateien", "*.*")])
        if p:
            self.template_var.set(p)
            self.show_brief_preview_placeholder("Word-Vorlage geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

    def _browse_output(self):
        p = filedialog.askdirectory(title="Ausgabeordner")
        if p:
            self.output_var.set(p)

    def _log(self, txt):
        self.log_text.insert("end", f"{datetime.now():%H:%M:%S}  {txt}\n")
        self.log_text.see("end")

    def load_data(self):
        try:
            path = self.excel_var.get().strip()
            if not os.path.isfile(path):
                messagebox.showwarning(APP_TITLE, "Bitte eine gültige Excel-Datei auswählen.")
                return
            self.re_df, self.st_df = read_excel_data(path)
            self.st_idx = build_st_index(self.st_df)
            self.selected_row_indices.clear()
            self.refresh_excel_preview()
            self.show_brief_preview_placeholder("Daten geladen.\nBitte 'Brief-Vorschau aktualisieren' klicken, um den ersten zu erstellenden Brief zu rendern.")
            self._log(f"Daten geladen: {len(self.re_df)} RE-Zeilen, {len(self.st_df)} ST-Zeilen.")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def displayed_df(self, exclude_filter_col=None):
        if self.re_df is None:
            return None
        df = self.re_df.copy()
        f = clean(self.filter_var.get()).lower()
        if f:
            mask = df.apply(lambda row: any(f in clean(v).lower() for v in row.values), axis=1)
            df = df[mask]
        for col, allowed in self.column_filters.items():
            if exclude_filter_col is not None and col == exclude_filter_col:
                continue
            if allowed is not None and col in df.columns:
                df = df[df[col].map(clean).isin(allowed)]
        return df

    def clear_column_filters(self):
        self.column_filters.clear()
        self.refresh_excel_preview()
        self.show_brief_preview_placeholder("Spaltenfilter geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

    def _open_column_filter(self, column):
        if self.re_df is None or column not in self.re_df.columns:
            return
        df = self.displayed_df(exclude_filter_col=column)
        if df is None:
            return
        values = sorted({clean(v) for v in df[column].tolist()}, key=lambda x: (x == "", x.lower()))
        if not values:
            values = [""]
        current = self.column_filters.get(column)
        selected_initial = set(values) if current is None else set(current)

        win = tk.Toplevel(self.root)
        win.title(f"Filter: {column}")
        win.geometry("360x520")
        win.transient(self.root)
        win.grab_set()
        win.update_idletasks()
        width, height = 360, 520
        x = max(0, self.root.winfo_x() + (self.root.winfo_width() - width) // 2)
        y = max(0, self.root.winfo_y() + (self.root.winfo_height() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(3, weight=1)

        tk.Label(win, text=f"Auswahlfilter für: {column}", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        search_var = tk.StringVar()
        tk.Entry(win, textvariable=search_var, font=self.font_small).grid(row=1, column=0, sticky="ew", padx=8, pady=4)

        btns = tk.Frame(win)
        btns.grid(row=2, column=0, sticky="ew", padx=8, pady=4)
        btns.columnconfigure(2, weight=1)

        holder = tk.Frame(win)
        holder.grid(row=3, column=0, sticky="nsew", padx=8, pady=4)
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        canvas = tk.Canvas(holder, highlightthickness=0)
        vs = ttk.Scrollbar(holder, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vs.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")

        vars_by_value = {}
        visible_values = []

        def label_for_value(v):
            return "(Leer)" if v == "" else v

        def rebuild_list(*_):
            for child in inner.winfo_children():
                child.destroy()
            visible_values.clear()
            term = clean(search_var.get()).lower()
            filtered_values = [v for v in values if term in label_for_value(v).lower()]
            for i, value in enumerate(filtered_values):
                visible_values.append(value)
                if value not in vars_by_value:
                    vars_by_value[value] = tk.BooleanVar(value=value in selected_initial)
                tk.Checkbutton(inner, text=label_for_value(value), variable=vars_by_value[value], anchor="w", justify="left").grid(row=i, column=0, sticky="w", padx=2, pady=1)

        def select_visible(state):
            for value in visible_values:
                vars_by_value[value].set(state)

        def clear_filter():
            if column in self.column_filters:
                del self.column_filters[column]
            win.destroy()
            self.refresh_excel_preview()
            self.show_brief_preview_placeholder("Spaltenfilter geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

        def apply_filter():
            selected = {v for v, var in vars_by_value.items() if var.get()}
            # Nicht geladene/unsichtbare Werte behalten ihren aktuellen Status.
            for v in values:
                if v not in vars_by_value and v in selected_initial:
                    selected.add(v)
            if len(selected) == len(values):
                self.column_filters.pop(column, None)
            else:
                self.column_filters[column] = selected
            win.destroy()
            self.refresh_excel_preview()
            self.show_brief_preview_placeholder("Spaltenfilter geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

        tk.Button(btns, text="Alle auswählen", command=lambda: select_visible(True), font=self.font_small).grid(row=0, column=0, padx=(0, 4))
        tk.Button(btns, text="Keine auswählen", command=lambda: select_visible(False), font=self.font_small).grid(row=0, column=1, padx=(0, 4))
        tk.Button(btns, text="Filter löschen", command=clear_filter, font=self.font_small).grid(row=0, column=3, padx=(4, 0))

        bottom = tk.Frame(win)
        bottom.grid(row=4, column=0, sticky="ew", padx=8, pady=8)
        bottom.columnconfigure(0, weight=1)
        tk.Button(bottom, text="OK", command=apply_filter, bg="#CFEAD6", activebackground="#BDE3C7", font=self.font_small).grid(row=0, column=1, padx=4)
        tk.Button(bottom, text="Abbrechen", command=win.destroy, font=self.font_small).grid(row=0, column=2, padx=4)

        search_var.trace_add("write", rebuild_list)
        rebuild_list()

    def refresh_excel_preview(self):
        if self.re_df is None:
            return
        df = self.displayed_df()
        if df is None:
            return
        cols = [c for c in PREVIEW_COLUMNS if c in df.columns]
        if not cols:
            cols = list(df.columns)
        shown_df = df.head(PREVIEW_LIMIT)
        self.excel_tree.delete(*self.excel_tree.get_children())
        display_cols = ["#"] + cols
        self.excel_tree["columns"] = display_cols
        self.excel_tree.heading("#", text="#")
        self.excel_tree.column("#", width=46, minwidth=38, stretch=False, anchor="e")
        for c in cols:
            suffix = " ▼" if c in self.column_filters else ""
            self.excel_tree.heading(c, text=f"{c}{suffix}", command=lambda col=c: self._open_column_filter(col))
            self.excel_tree.column(c, width=max(90, min(240, len(c) * 9)), stretch=False)
        for idx, row in shown_df.iterrows():
            iid = str(idx)
            # Excel-Zeilennummer: +2, da Zeile 1 die Spaltenüberschriften enthält.
            row_number = str(int(idx) + 2) if str(idx).isdigit() else str(idx)
            values = [row_number] + [clean(row.get(c, "")) for c in cols]
            self.excel_tree.insert("", "end", iid=iid, values=values)
            if idx in self.selected_row_indices:
                self.excel_tree.selection_add(iid)
        if hasattr(self, "preview_status_var"):
            extra = "" if len(df) <= PREVIEW_LIMIT else f" — angezeigt werden aus Performancegründen die ersten {PREVIEW_LIMIT}. Bitte Filter nutzen."
            active = f" | aktive Spaltenfilter: {len(self.column_filters)}" if self.column_filters else ""
            self.preview_status_var.set(f"Excel-Vorschau: {len(shown_df)} von {len(df)} gefilterten Zeilen{active}{extra}")
        self._update_selection_info()

    def _tree_press(self, event):
        iid = self.excel_tree.identify_row(event.y)
        self.drag_start_iid = iid
        if iid:
            self.excel_tree.selection_set(iid)
            self._sync_tree_selection()

    def _tree_drag(self, event):
        if not self.drag_start_iid:
            return
        iid = self.excel_tree.identify_row(event.y)
        if not iid:
            return
        children = list(self.excel_tree.get_children())
        try:
            a, b = children.index(self.drag_start_iid), children.index(iid)
        except ValueError:
            return
        lo, hi = sorted((a, b))
        self.excel_tree.selection_set(children[lo:hi+1])
        self._sync_tree_selection()

    def _tree_release(self, event):
        self._sync_tree_selection()
        self.show_brief_preview_placeholder("Auswahl geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

    def _sync_tree_selection(self):
        self.selected_row_indices = {int(i) for i in self.excel_tree.selection() if str(i).isdigit()}
        self._update_selection_info()

    def clear_selection(self):
        self.selected_row_indices.clear()
        self.excel_tree.selection_remove(self.excel_tree.selection())
        self._update_selection_info()
        self.show_brief_preview_placeholder("Auswahl/Optionen geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

    def _eligible_indices(self):
        if self.re_df is None:
            return []
        idxs = []
        if self.export_filtered_var.get():
            df = self.displayed_df()
            if df is not None:
                idxs.extend(list(df.index))
        if self.only_selection_var.get():
            idxs.extend([i for i in self.selected_row_indices if i in self.re_df.index])
        # Doppelte entfernen, Reihenfolge aus MG_RE beibehalten.
        selected = set(idxs)
        return [i for i in self.re_df.index if i in selected]
    def _on_options_changed(self):
        self._update_selection_info()
        self.show_brief_preview_placeholder("Auswahl/Optionen geändert.\nBitte 'Brief-Vorschau aktualisieren' klicken.")

    def _update_selection_info(self):
        hint = "" if (self.export_filtered_var.get() or self.only_selection_var.get()) else " | keine Ausgabeoption gewählt"
        self.count_var.set(f"Auswahl: {len(self.selected_row_indices)} markierte Zeilen | Ausgabe nach Optionen: {len(self._eligible_indices())} Rechnungen{hint}")

    def first_preview_index(self):
        idxs = self._eligible_indices()
        if idxs:
            return idxs[0]
        if self.re_df is not None and len(self.re_df.index):
            return self.re_df.index[0]
        return None

    def show_brief_preview_placeholder(self, message=None):
        if not hasattr(self, "brief_canvas") or self.brief_canvas is None:
            return
        self.brief_canvas.delete("all")
        self.brief_canvas.configure(scrollregion=(0, 0, 0, 0))
        text = message or "Brief-Vorschau noch nicht geladen.\nBitte 'Brief-Vorschau aktualisieren' klicken."
        self.brief_canvas.create_text(20, 20, anchor="nw", text=text, font=self.font, fill="#4A6074")

    def refresh_brief_preview(self):
        self.brief_canvas.delete("all")
        if self.re_df is None or not self.st_idx:
            self.brief_canvas.create_text(20, 20, anchor="nw", text="Bitte zuerst Daten laden.", font=self.font)
            return
        template = self.template_var.get().strip()
        if not os.path.isfile(template):
            self.brief_canvas.create_text(20, 20, anchor="nw", text="Bitte eine gültige Word-Vorlage auswählen.", font=self.font)
            return
        idx = self.first_preview_index()
        if idx is None:
            self.brief_canvas.create_text(20, 20, anchor="nw", text="Keine Vorschauzeile verfügbar.", font=self.font)
            return
        try:
            tmp = Path(tempfile.gettempdir()) / "debitoren_serienbrief_preview"
            tmp.mkdir(parents=True, exist_ok=True)
            repl = data_for_invoice(self.re_df.loc[idx].to_dict(), self.st_idx)
            docx_path = tmp / "preview.docx"
            pdf_path = tmp / "preview.pdf"
            fill_docx(template, docx_path, repl)
            unresolved = docx_unresolved_placeholders(docx_path)
            ok, err = export_pdf_with_word(docx_path, pdf_path)
            if not ok or not pdf_path.exists():
                detail = f"\n\nNoch offene Platzhalter im DOCX: {', '.join(unresolved)}" if unresolved else ""
                self.brief_canvas.create_text(20, 20, anchor="nw", text=f"Echte Brief-Vorschau konnte nicht gerendert werden.\nWord-COM/PDF-Export ist für die Vorschau erforderlich.\n\nDetails: {err}{detail}", font=self.font, fill="#8A3B00")
                return
            if ImageTk is None:
                self.brief_canvas.create_text(20, 20, anchor="nw", text="Pillow ist für die Bildvorschau nicht verfügbar.", font=self.font, fill="#8A3B00")
                return
            img, render_err = render_pdf_first_page_to_image(pdf_path)
            if img is None:
                self.brief_canvas.create_text(20, 20, anchor="nw", text=f"PDF wurde erzeugt, aber nicht als Bild gerendert.\nBitte ggf. installieren: python -m pip install pymupdf pillow\n\nDetails: {render_err}", font=self.font, fill="#8A3B00")
                return
            self.brief_image_ref = ImageTk.PhotoImage(img)
            self.brief_canvas.create_image(20, 20, image=self.brief_image_ref, anchor="nw")
            self.brief_canvas.configure(scrollregion=self.brief_canvas.bbox("all"))
            if unresolved:
                self.brief_canvas.create_text(20, img.height + 35, anchor="nw", text="Noch offene Platzhalter: " + ", ".join(unresolved), font=self.font, fill="red")
        except Exception as exc:
            self.brief_canvas.create_text(20, 20, anchor="nw", text=f"Vorschaufehler: {exc}", font=self.font, fill="red")

    def set_progress(self, word_done, pdf_done, total):
        self.word_progress["maximum"] = total
        self.pdf_progress["maximum"] = total
        self.word_progress["value"] = word_done
        self.pdf_progress["value"] = pdf_done
        self.word_progress_var.set(f"{word_done}/{total} Word-Dateien erzeugt")
        self.pdf_progress_var.set(f"{pdf_done}/{total} PDF-Dateien erzeugt")

    def cancel_export(self):
        if self.export_running:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self._log("Abbruch angefordert. Der aktuelle Vorgang wird noch beendet.")

    def start_export(self):
        if self.export_running:
            return
        self.cancel_event.clear()
        self.export_running = True
        self.export_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
        self.set_progress(0, 0, max(1, len(self._eligible_indices())))
        self._log(f"Export gestartet: {len(self._eligible_indices())} Rechnungen nach aktueller Auswahl/Option.")
        threading.Thread(target=self.export_letters, daemon=True).start()

    def export_letters(self):
        try:
            if self.re_df is None or not self.st_idx:
                self.root.after(0, lambda: messagebox.showwarning(APP_TITLE, "Bitte zuerst Daten laden."))
                return
            template = self.template_var.get().strip()
            if not os.path.isfile(template):
                self.root.after(0, lambda: messagebox.showwarning(APP_TITLE, "Bitte eine gültige Word-Vorlage auswählen."))
                return
            out_dir = Path(self.output_var.get().strip())
            out_dir.mkdir(parents=True, exist_ok=True)
            idxs = self._eligible_indices()
            total = len(idxs)
            if total == 0:
                self.root.after(0, lambda: messagebox.showwarning(APP_TITLE, "Keine Rechnungen für die Ausgabe nach aktueller Auswahl/Filterung oder keine Ausgabeoption gewählt."))
                return

            word_done = 0
            pdf_done = 0
            nonstandard = []
            unresolved_notes = []
            pdf_failed = []
            pdf_pairs = []
            self.root.after(0, lambda: self.set_progress(0, 0, total))

            # Phase 1: Word-Dateien erzeugen — ohne Word-COM, daher schnell und abbrechbar.
            for idx in idxs:
                if self.cancel_event.is_set():
                    break
                row = self.re_df.loc[idx].to_dict()
                repl = data_for_invoice(row, self.st_idx)
                inv_no = safe_filename(repl.get("__invoice_no__", "Rechnung"))
                mem = safe_filename(repl.get("__file_member__", repl.get("__member__", "Mitglied")))
                base = f"RE_{inv_no}_{mem}"
                docx_out = out_dir / f"{base}.docx"
                pdf_out = out_dir / f"{base}.pdf"
                fill_docx(template, docx_out, repl)
                word_done += 1
                self.root.after(0, lambda path=str(docx_out): self._log(f"Word erstellt: {path}"))
                pdf_pairs.append((docx_out, pdf_out))
                unresolved = docx_unresolved_placeholders(docx_out)
                if unresolved:
                    unresolved_notes.append(f"{docx_out.name}: {', '.join(unresolved)}")
                if repl.get("__nonstandard_order__"):
                    nonstandard.append(f"Zeile {idx+2}: {clean(row.get('Auftragsnummer',''))}")
                self.root.after(0, lambda wd=word_done, pd=pdf_done, t=total: self.set_progress(wd, pd, t))

            # Phase 2: PDF-Dateien mit nur einer Word-Instanz als Batch erzeugen.
            if not self.cancel_event.is_set() and pdf_pairs:
                def pdf_progress(done_count, docx_path=None, pdf_path=None, ok=False, err_text=""):
                    self.root.after(0, lambda wd=word_done, pd=done_count, t=total: self.set_progress(wd, pd, t))
                    if pdf_path is not None:
                        if ok:
                            self.root.after(0, lambda path=str(pdf_path): self._log(f"PDF erstellt: {path}"))
                        else:
                            self.root.after(0, lambda path=str(pdf_path), err=err_text: self._log(f"PDF-Fehler: {path} | {err}"))
                pdf_done, pdf_failed = export_pdfs_with_word_batch(pdf_pairs, self.cancel_event, pdf_progress)
                self.root.after(0, lambda wd=word_done, pd=pdf_done, t=total: self.set_progress(wd, pd, t))

            cancelled = self.cancel_event.is_set()
            def done():
                msg = f"{'Abgebrochen. ' if cancelled else ''}Erzeugt: {word_done}/{total} Word-Dateien und {pdf_done}/{total} PDF-Dateien.\nOrdner:\n{out_dir}"
                if pdf_failed:
                    msg += "\n\nPDF-Fehler:\n" + "\n".join(pdf_failed[:10])
                if nonstandard:
                    msg += "\n\nAuftragsnummern ohne Normalformat wurden unverändert übernommen:\n" + "\n".join(nonstandard[:20])
                if unresolved_notes:
                    msg += "\n\nNoch offene Platzhalter:\n" + "\n".join(unresolved_notes[:10])
                messagebox.showinfo(APP_TITLE, msg)
                self._log(msg.replace("\n", " | "))
            self.root.after(0, done)
        except Exception as exc:
            self.root.after(0, lambda: messagebox.showerror(APP_TITLE, str(exc)))
        finally:
            def finish_state():
                self.export_running = False
                self.export_btn.configure(state="normal")
                self.cancel_btn.configure(state="disabled")
                self.cancel_event.clear()
            self.root.after(0, finish_state)

def main():
    root = tk.Tk()
    app = DebitorenSerienbriefApp(root)
    try:
        if app.excel_var.get() and os.path.isfile(app.excel_var.get()):
            app.load_data()
    except Exception:
        pass
    root.mainloop()


if __name__ == "__main__":
    main()



def render(app):
    """FiBu-Mate-Integration: öffnet den Debitoren-Serienbrief als eigenes Tool-Fenster.
    Die bestehende Serienbrief-Logik bleibt unverändert; der Wrapper sorgt dafür, dass
    das Modul aus dem FiBu-Mate-Menü heraus gestartet werden kann.
    """
    parent = getattr(app, "root", None)
    win = tk.Toplevel(parent) if parent is not None else tk.Tk()
    DebitorenSerienbriefApp(win)
    try:
        win.transient(parent)
    except Exception:
        pass
    try:
        win.focus_set()
    except Exception:
        pass
    return win
