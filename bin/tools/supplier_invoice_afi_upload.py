
import csv
import os
import sys
import re
import threading
import unicodedata
from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except Exception:
    Image = ImageDraw = ImageFont = ImageTk = None

MODULE_TITLE = "Lieferanten-Rechnung zu AFI-Upload"
UPLOAD_COLUMNS = ["TEXT", "PRICE", "PRICE_UNIT", "QUANTITY", "UNIT", "NET_VALUE", "TAX_CODE", "GL_ACCOUNT", "COSTCENTER", "ORDERID"]
TAX_ORDER = {"VD": 0, "V2": 1, "V0": 2, "VX": 9}
SOURCE_COST_KEYWORDS = [
    "Energiekosten", "Grundgebühr", "Grundgebuehr", "Blockiergebühr", "Blockiergebuehr", "Kartenkosten",
    "Service", "Maut", "Gebühr", "Gebuehr", "Kosten", "Netto", "Net Amount", "Net Value", "Nettobetrag",
]


def _desktop_path():
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _clean(value):
    return " ".join(str(value or "").replace("\ufeff", "").strip().split())


def _norm(value):
    text = _clean(value).upper()
    text = (text.replace("Ä", "AE").replace("Ö", "OE").replace("Ü", "UE")
                .replace("ẞ", "SS").replace("ß", "SS"))
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]", "", text)


def _read_csv(path):
    encodings = ["utf-8-sig", "cp1252", "latin1"]
    last = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                sample = f.read(8192)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                except Exception:
                    dialect = csv.excel
                    dialect.delimiter = ";"
                reader = csv.DictReader(f, dialect=dialect)
                rows = [{str(k or "").replace("\ufeff", "").strip(): v for k, v in row.items()} for row in reader]
                headers = [str(x or "").replace("\ufeff", "").strip() for x in (reader.fieldnames or [])]
                return headers, rows
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV konnte nicht gelesen werden: {last}")


def _read_table_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _read_csv(path)
    if ext in (".xlsx", ".xls"):
        try:
            import pandas as pd
            engine = "openpyxl" if ext == ".xlsx" else "xlrd"
            df = pd.read_excel(path, engine=engine, dtype=str)
            df = df.fillna("")
            headers = [str(c) for c in df.columns]
            rows = df.to_dict(orient="records")
            return headers, rows
        except Exception as exc:
            raise RuntimeError(f"Excel-Datei konnte nicht gelesen werden: {exc}")
    raise RuntimeError("Für die Berechnung werden aktuell CSV- oder Excel-Dateien benötigt.")


def _dec(value):
    s = _clean(value)
    if not s:
        return Decimal("0.00")
    s = s.replace("€", "").replace("EUR", "").replace("%", "").replace(" ", "")
    neg = s.endswith("-")
    if neg:
        s = s[:-1]
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        d = Decimal(s)
        return -d if neg else d
    except InvalidOperation:
        return Decimal("0.00")


def _fmt(value):
    d = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}".replace(".", ",")


def _tax_code_from_rate(rate):
    r = Decimal(rate)
    if abs(r - Decimal("19.00")) <= Decimal("0.50"):
        return "VD"
    if abs(r - Decimal("7.00")) <= Decimal("0.50"):
        return "V2"
    if abs(r - Decimal("0.00")) <= Decimal("0.50"):
        return "V0"
    return "VX"


def _tax_code_from_net_vat(net, vat):
    net = Decimal(net)
    vat = Decimal(vat or "0.00")
    if net == 0:
        return "V0" if vat == 0 else "VX"
    rate = (vat / net * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _tax_code_from_rate(rate)


def _score_header(header, keywords):
    h = _norm(header)
    score = 0
    for kw, weight in keywords:
        if _norm(kw) in h:
            score += weight
    return score


def _guess_column(headers, keywords):
    best = ""
    best_score = 0
    for h in headers:
        s = _score_header(h, keywords)
        if s > best_score:
            best = h
            best_score = s
    return best


def _guess_net_columns(headers):
    found = []
    for h in headers:
        nh = _norm(h)
        has_net = any(_norm(k) in nh for k in ["Netto", "Nettobetrag", "NetAmount", "NetValue", "ExclVAT"])
        has_bad = any(_norm(k) in nh for k in ["Mehrwertsteuer", "MwSt", "Umsatzsteuer", "VAT", "Tax", "Brutto", "Gross"])
        if has_net and not has_bad:
            found.append(h)
    return found


def guess_columns(headers):
    return {
        "key": _guess_column(headers, [("Kennzeichen", 10), ("KFZ", 9), ("Fahrzeug", 6), ("Vehicle", 6), ("License", 6), ("Objekt", 5), ("Referenz", 5), ("Identifikation", 4)]),
        "full_name": _guess_column(headers, [("Fahrername", 10), ("Fahrer", 8), ("Mitarbeiter", 7), ("Nutzer", 7), ("Name", 6), ("Driver", 6), ("User", 5)]),
        "first": _guess_column(headers, [("Vorname", 10), ("First", 7), ("Given", 6)]),
        "last": _guess_column(headers, [("Nachname", 10), ("Last", 7), ("Surname", 7), ("Familienname", 6)]),
        # Steuersatz ist ein Prozentwert (z. B. 0, 7, 19), nicht der Steuerbetrag.
        "vat_amount": _guess_column(headers, [("Mehrwertsteuersatz", 12), ("Steuersatz", 11), ("Tax Rate", 10), ("VAT Rate", 10), ("USt Satz", 10), ("MwSt Satz", 9), ("Rate", 5)]),
        "gross": _guess_column(headers, [("Brutto", 10), ("Gross", 8), ("Amount incl", 8), ("incl VAT", 8)]),
    }


def _related_column(headers, net_col, kind):
    base = _norm(net_col)
    base = re.sub(r"NETTO|NETAMOUNT|NETVALUE|NETTBETRAG", "", base)
    candidates = []
    for h in headers:
        nh = _norm(h)
        s = 0
        if base and base in nh:
            s += 5
        if kind == "gross" and any(x in nh for x in ["BRUTTO", "GROSS", "INCLVAT"]):
            s += 10
        if kind == "vat" and any(x in nh for x in ["MEHRWERTSTEUERSATZ", "STEUERSATZ", "TAXRATE", "VATRATE", "USTSATZ", "MWSTSATZ", "RATE"]):
            s += 10
        if kind == "vat" and any(x in nh for x in ["STEUERBETRAG", "TAXAMOUNT", "MEHRWERTSTEUERBETRAG"]):
            s -= 20
        if s:
            candidates.append((s, h))
    return sorted(candidates, reverse=True)[0][1] if candidates else ""


def suggested_sources(headers):
    guessed = guess_columns(headers)
    nets = _guess_net_columns(headers)
    result = []
    for idx, net in enumerate(nets, 1):
        label = re.sub(r"\s*\(?Euro\)?\s*", "", net, flags=re.I).strip() or f"Quelle {idx}"
        result.append({
            "active": True,
            "label": label,
            "net": net,
            "tax_mode": "vat",
            "vat_amount": _related_column(headers, net, "vat") or guessed.get("vat_amount", ""),
            "gross": _related_column(headers, net, "gross") or guessed.get("gross", ""),
            "manual_rate": "19",
            "name_mode": "full",
            "full_name": guessed.get("full_name", ""),
            "first": guessed.get("first", ""),
            "last": guessed.get("last", ""),
            "key": guessed.get("key", ""),
        })
    if not result:
        result.append(default_source(1, headers))
    return result


def default_source(idx, headers):
    guessed = guess_columns(headers)
    return {
        "active": True,
        "label": f"Berechnungsquelle {idx}",
        "net": "",
        "tax_mode": "vat",
        "vat_amount": guessed.get("vat_amount", ""),
        "gross": guessed.get("gross", ""),
        "manual_rate": "19",
        "name_mode": "full",
        "full_name": guessed.get("full_name", ""),
        "first": guessed.get("first", ""),
        "last": guessed.get("last", ""),
        "key": guessed.get("key", ""),
    }


def _driver_from_row(row, src):
    first = _clean(row.get(src.get("first", ""), "")) if src.get("first") else ""
    last = _clean(row.get(src.get("last", ""), "")) if src.get("last") else ""
    full = _clean(row.get(src.get("full_name", ""), "")) if src.get("full_name") else ""
    return _clean(f"{first} {last}") or last or full


def _fallback_name_from_row(row):
    """Sucht bei fehlender Fahrer-/Kennzeichenzuordnung automatisch andere Spalten mit 'Name' im Titel.
    Kostenpositionen werden dadurch nicht verworfen, wenn eine direkte Zuordnung fehlt.
    """
    for col, value in row.items():
        if "NAME" in _norm(col):
            cleaned = _clean(value)
            if cleaned:
                return cleaned
    return ""


def _load_template_entries(template_path):
    headers, rows = _read_csv(template_path)
    required = ["TEXT", "GL_ACCOUNT", "COSTCENTER", "ORDERID"]
    missing = [c for c in required if c not in headers]
    if missing:
        raise RuntimeError("Die Vorlage enthält nicht alle erwarteten AFI-Spalten: " + ", ".join(missing))
    entries = []
    for row in rows:
        text = _clean(row.get("TEXT", ""))
        if not text:
            continue
        entries.append({
            "TEXT": text,
            "NORM_TEXT": _norm(text),
            "GL_ACCOUNT": _clean(row.get("GL_ACCOUNT", "")),
            "COSTCENTER": _clean(row.get("COSTCENTER", "")),
            "ORDERID": _clean(row.get("ORDERID", "")),
        })
    return entries


def _unique_match(candidates):
    unique = []
    seen = set()
    for c in candidates:
        key = (c.get("TEXT"), c.get("GL_ACCOUNT"), c.get("COSTCENTER"), c.get("ORDERID"))
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique[0] if len(unique) == 1 else None


def _resolve_template(key, driver, entries):
    nkey = _norm(key)
    ndriver = _norm(driver)
    last = _norm(_clean(driver).split()[-1] if _clean(driver).split() else "")
    if nkey:
        m = _unique_match([e for e in entries if nkey in e["NORM_TEXT"]])
        if m:
            return m, "Schlüssel"
    if ndriver:
        m = _unique_match([e for e in entries if ndriver in e["NORM_TEXT"]])
        if m:
            return m, "Name"
    if last:
        m = _unique_match([e for e in entries if last in e["NORM_TEXT"]])
        if m:
            return m, "Nachname"
    return {}, ""


def create_supplier_upload_csv(template_path, invoice_path, export_path, config):
    headers, rows = _read_table_file(invoice_path)
    entries = _load_template_entries(template_path)
    global_prefix = _clean(config.get("global_prefix", "Tanken Strom")) or "Tanken Strom"
    sources = [s for s in config.get("sources", []) if s.get("active", True) and s.get("net")]
    if not sources:
        raise RuntimeError("Bitte mindestens eine aktive Berechnungsquelle mit Nettopreis-Spalte auswählen.")

    groups = OrderedDict()
    warnings_missing = []
    warnings_tax = []
    warnings_empty_assignment = []
    warnings_name_fallback = []
    invoice_net_raw_total = Decimal("0.00")
    unique_drivers = set()
    unique_keys = set()

    def add_group(src, key, driver, tax, amount):
        # Fachlogik: Alle aktiven Berechnungsquellen werden pro Fahrer > Fahrzeug/Schlüssel > Steuersatz zusammengefasst.
        group_key = (_norm(driver), _norm(key), tax)
        if group_key not in groups:
            groups[group_key] = {"source": src, "key": key, "driver": driver, "tax": tax, "amount": Decimal("0.00")}
        groups[group_key]["amount"] += amount

    for src in sources:
        for idx, row in enumerate(rows):
            net = _dec(row.get(src.get("net", ""), ""))
            if net == 0:
                continue
            driver = _driver_from_row(row, src)
            key = _clean(row.get(src.get("key", ""), "")) if src.get("key") else ""
            if not key and driver:
                key = driver
            if not key or not driver:
                fallback_name = _fallback_name_from_row(row)
                if fallback_name:
                    if not driver:
                        driver = fallback_name
                    if not key:
                        key = fallback_name
            if not key and not driver:
                # Keine Kostenposition darf wegen fehlender Zuordnung verloren gehen.
                # Für solche Fälle wird eine technische Bezeichnung erzeugt und die Kontierung bleibt leer.
                fallback_name = f"UNZUORDENBAR Zeile {idx + 2}"
                driver = fallback_name
                key = fallback_name
                warnings_empty_assignment.append(f"{src.get('label', '')}: Zeile {idx + 2} ohne Fahrer/Schlüssel; als '{fallback_name}' exportiert")
            if driver:
                unique_drivers.add(_norm(driver))
            if key:
                unique_keys.add(_norm(key))
            tax_mode = src.get("tax_mode", "vat")
            vat = Decimal("0.00")
            if tax_mode == "gross":
                gross = _dec(row.get(src.get("gross", ""), ""))
                vat = gross - net if gross else Decimal("0.00")
                tax = _tax_code_from_net_vat(net, vat) if gross else "VX"
            elif tax_mode == "manual":
                tax = _tax_code_from_rate(_dec(src.get("manual_rate", "19")))
            else:
                rate_value = _dec(row.get(src.get("vat_amount", ""), ""))
                tax = _tax_code_from_rate(rate_value)
                vat = rate_value
            if tax == "VX":
                warnings_tax.append(f"{src.get('label', '')} / {key} / {driver}: Netto {_fmt(net)}, Steuersatz {_fmt(vat)} %")
            invoice_net_raw_total += net
            add_group(src, key, driver, tax, net)

    resolved = {}
    for gkey, g in groups.items():
        info, how = _resolve_template(g["key"], g["driver"], entries)
        resolved[gkey] = info
        if not info:
            warnings_missing.append(f"{g['key']} / {g['driver']}")
        elif how in ("Name", "Nachname") and _norm(g["key"]) not in info.get("NORM_TEXT", ""):
            warnings_name_fallback.append(f"{g['key']} / {g['driver']}: Kontierung per {how} übernommen")

    ordered_groups = sorted(groups.items(), key=lambda kv: (_norm(kv[1]["key"]), _norm(kv[1]["driver"]), TAX_ORDER.get(kv[1]["tax"], 9), _norm(kv[1]["source"].get("label", ""))))
    target_net_total = invoice_net_raw_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    export_net_before = sum(g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for _, g in ordered_groups)
    rounding_adjustments = []
    diff = target_net_total - export_net_before
    if diff != 0 and ordered_groups:
        candidates = [g for _, g in ordered_groups if g["tax"] in ("VD", "V2") and g["amount"] != 0] or [g for _, g in ordered_groups if g["amount"] != 0]
        if candidates:
            target = max(candidates, key=lambda g: abs(g["amount"]))
            before = target["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            target["amount"] += diff
            after = target["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rounding_adjustments.append(f"Netto-Rundungsausgleich {diff:+.2f} EUR auf {target['key']} / {target['driver']}: {before:.2f} -> {after:.2f}".replace(".", ","))

    os.makedirs(os.path.dirname(os.path.abspath(export_path)) or ".", exist_ok=True)
    with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=UPLOAD_COLUMNS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for gkey, g in ordered_groups:
            amount = g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            info = resolved.get(gkey, {})
            parts = [global_prefix]
            if g["key"]:
                parts.append(g["key"])
            if g["driver"] and _norm(g["driver"]) != _norm(g["key"]):
                parts.append(g["driver"])
            writer.writerow({
                "TEXT": _clean(" ".join(parts)),
                "PRICE": _fmt(amount),
                "PRICE_UNIT": "1",
                "QUANTITY": "1",
                "UNIT": "ST",
                "NET_VALUE": _fmt(amount),
                "TAX_CODE": g["tax"],
                "GL_ACCOUNT": info.get("GL_ACCOUNT", ""),
                "COSTCENTER": info.get("COSTCENTER", ""),
                "ORDERID": info.get("ORDERID", ""),
            })

    export_net_total = sum(g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for _, g in ordered_groups)
    return {
        "rows": len(ordered_groups),
        "export_path": export_path,
        "invoice_net_raw_total": _fmt(invoice_net_raw_total),
        "export_net_total": _fmt(export_net_total),
        "net_rounding_difference": _fmt(export_net_total - target_net_total),
        "unique_drivers": len([x for x in unique_drivers if x]),
        "unique_keys": len([x for x in unique_keys if x]),
        "missing_template": warnings_missing,
        "unknown_tax": warnings_tax,
        "empty_assignment": warnings_empty_assignment,
        "name_fallback_matches": warnings_name_fallback,
        "rounding_adjustments": rounding_adjustments,
    }


class SourceRow:
    def __init__(self, parent, module, idx, headers, initial=None):
        self.module = module
        self.headers = headers
        self.idx = idx
        self.vars = {}
        self.frame = tk.LabelFrame(parent, text=f"Berechnungsquelle {idx}", bg=module.bg, font=module.font_small)
        self.initial = initial or default_source(idx, headers)
        self._build()
        self.set_values(self.initial)

    def _make_searchable(self, cb, values):
        cb["values"] = values
        def on_key(event):
            typed = cb.get().lower()
            if not typed:
                cb["values"] = values
                return
            cb["values"] = [v for v in values if typed in str(v).lower()]
        cb.bind("<KeyRelease>", on_key)

    def _combo(self, row, col, key, label="", width=36, colspan=1):
        if label:
            tk.Label(self.frame, text=label, bg=self.module.bg, font=self.module.font_small).grid(row=row, column=col, sticky="w", padx=5, pady=3)
            col += 1
        var = tk.StringVar()
        cb = ttk.Combobox(self.frame, textvariable=var, values=[""] + self.headers, state="normal", width=width, font=self.module.font_small)
        self._make_searchable(cb, [""] + self.headers)
        cb.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=5, pady=3)
        cb.bind("<<ComboboxSelected>>", lambda e: self.module.on_mapping_changed())
        cb.bind("<FocusOut>", lambda e: self.module.on_mapping_changed())
        self.vars[key] = var
        return cb

    def _build(self):
        for c in range(6):
            self.frame.columnconfigure(c, weight=1)
        self.vars["active"] = tk.BooleanVar(value=True)
        tk.Checkbutton(self.frame, text="Aktiv", variable=self.vars["active"], bg=self.module.bg, command=self.module.on_mapping_changed).grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self._combo(0, 1, "net", "Nettopreis", width=42, colspan=2)
        tk.Label(self.frame, text="Kostenbeschreibung", bg=self.module.bg, font=self.module.font_small).grid(row=0, column=4, sticky="w", padx=5, pady=3)
        kosten_cb = ttk.Combobox(self.frame, textvariable=self.module.global_prefix_var, values=COST_TYPE_OPTIONS, state="normal", width=26, font=self.module.font_small)
        kosten_cb.grid(row=0, column=5, sticky="ew", padx=5, pady=3)
        kosten_cb.bind("<<ComboboxSelected>>", lambda e: self.module.on_mapping_changed())
        kosten_cb.bind("<FocusOut>", lambda e: self.module.on_mapping_changed())

        sep1 = tk.Frame(self.frame, height=1, bg="#B8C3CF")
        sep1.grid(row=1, column=0, columnspan=6, sticky="ew", padx=5, pady=(6, 3))
        tk.Label(self.frame, text="1. Steuerberechnung", bg=self.module.bg, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, columnspan=6, sticky="w", padx=5, pady=(2, 4))
        self.vars["tax_mode"] = tk.StringVar(value="vat")
        tk.Radiobutton(self.frame, text="Bruttopreis", variable=self.vars["tax_mode"], value="gross", bg=self.module.bg, command=self.module.on_mapping_changed).grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self._combo(3, 1, "gross", width=44, colspan=5)
        tk.Radiobutton(self.frame, text="Steuersatz %", variable=self.vars["tax_mode"], value="vat", bg=self.module.bg, command=self.module.on_mapping_changed).grid(row=4, column=0, sticky="w", padx=5, pady=2)
        self._combo(4, 1, "vat_amount", width=44, colspan=5)
        tk.Radiobutton(self.frame, text="Steuersatz % manuell", variable=self.vars["tax_mode"], value="manual", bg=self.module.bg, command=self.module.on_mapping_changed).grid(row=5, column=0, sticky="w", padx=5, pady=2)
        self.vars["manual_rate"] = tk.StringVar(value="19")
        manual_cb = ttk.Combobox(self.frame, textvariable=self.vars["manual_rate"], values=["19", "7", "0"], state="normal", width=16, font=self.module.font_small)
        manual_cb.grid(row=5, column=1, sticky="w", padx=5, pady=2)
        manual_cb.bind("<<ComboboxSelected>>", lambda e: self.module.on_mapping_changed())
        manual_cb.bind("<FocusOut>", lambda e: self.module.on_mapping_changed())

        sep2 = tk.Frame(self.frame, height=1, bg="#B8C3CF")
        sep2.grid(row=6, column=0, columnspan=6, sticky="ew", padx=5, pady=(6, 3))
        tk.Label(self.frame, text="2. KST-Zuordnung", bg=self.module.bg, font=("Segoe UI", 9, "bold")).grid(row=7, column=0, columnspan=6, sticky="w", padx=5, pady=(2, 4))
        self._combo(8, 0, "key", "Kennzeichen / Zuordnungsschlüssel", width=44, colspan=5)
        self._combo(9, 0, "last", "Nachname", width=44, colspan=5)
        self._combo(10, 0, "first", "Vorname", width=44, colspan=5)

    def grid(self, **kwargs):
        self.frame.grid(**kwargs)

    def destroy(self):
        self.frame.destroy()

    def set_values(self, data):
        for k, var in self.vars.items():
            if isinstance(var, tk.BooleanVar):
                var.set(bool(data.get(k, var.get())))
            else:
                var.set(str(data.get(k, var.get() if hasattr(var, 'get') else "")))

    def get(self):
        out = {}
        for k, var in self.vars.items():
            out[k] = var.get()
        out["label"] = out.get("net") or f"Berechnungsquelle {self.idx}"
        return out

    def selected_columns(self):
        cols = []
        for k in ["net", "gross", "vat_amount", "last", "first", "key"]:
            v = self.vars.get(k)
            if v and v.get():
                cols.append(v.get())
        return cols

class SupplierUploadUI:
    def __init__(self, app):
        self.app = app
        self.canvas = app.canvas
        self.bg = getattr(app, "BG", "#E8EEF5") if hasattr(app, "BG") else "#E8EEF5"
        self.font = ("Segoe UI", 10)
        self.font_small = ("Segoe UI", 9)
        self.sources = []
        self.headers = []
        self.rows = []
        self.preview_tree = None
        self.preview_text = None
        self.selected_cell = ""
        self.image_ref = None
        self.preview_canvas = None
        self.preview_canvas_image = None
        self.preview_base_image = None
        self.preview_zoom = 1.0
        self.preview_offset = [0, 0]
        self.preview_drag_start = None
        self.table_font_size = 9
        self.hide_empty_columns_var = None
        self.preview_headers = []
        self.preview_rows = []
        self.preview_path = ""

    def render(self):
        try:
            self.canvas.delete("all")
            self.app.draw_background(); self.app.draw_header(MODULE_TITLE); self.app.draw_path_bar()
        except Exception:
            pass
        w = max(1120, self.canvas.winfo_width() - 120)
        h = max(560, self.canvas.winfo_height() - 205)
        main = tk.Frame(self.canvas, bg=self.bg, width=w, height=h)
        main.grid_propagate(False)
        main.pack_propagate(False)
        # Inhalt startet unter Kopf/Breadcrumb; die Modulüberschrift bleibt innerhalb des Kopfbereichs frei.
        self.canvas.create_window(60, 148, window=main, anchor="nw", width=w, height=h)
        main.columnconfigure(0, weight=1, uniform="afi_halves")
        main.columnconfigure(1, weight=1, uniform="afi_halves")
        main.rowconfigure(1, weight=1)
        tk.Label(main, text=MODULE_TITLE, bg=self.bg, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        left = tk.Frame(main, bg=self.bg, width=int(w * 0.50), height=max(320, h-74))
        right = tk.Frame(main, bg=self.bg, width=int(w * 0.50), height=max(320, h-74))
        left.grid_propagate(False); right.grid_propagate(False)
        left.pack_propagate(False); right.pack_propagate(False)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        main.rowconfigure(2, weight=0)
        self.footer_var = tk.StringVar(value="Nettobetrag der ausgewählten Spalten: 0,00 | individuelle Fahrer: 0 | individuelle Kennzeichen: 0")
        tk.Label(main, textvariable=self.footer_var, bg="#DDE7F3", font=("Segoe UI", 10, "bold"), anchor="w").grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        parent.columnconfigure(1, weight=1)
        self.template_var = tk.StringVar()
        self.invoice_var = tk.StringVar(value=_desktop_path())
        self.export_var = tk.StringVar(value=os.path.join(_desktop_path(), "Lieferanten_AFI_Upload.csv"))
        self.global_prefix_var = tk.StringVar(value="Tanken Strom")
        self.status_var = tk.StringVar(value="Bitte Rechnung und KST-Zuordnungsdokument auswählen und Rechnung analysieren.")
        self.suggestion_var = tk.StringVar(value="")

        def path_row(r, label, var, save=False):
            tk.Label(parent, text=label, bg=self.bg, font=self.font_small).grid(row=r, column=0, sticky="w", pady=3)
            tk.Entry(parent, textvariable=var, font=self.font_small).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
            def browse():
                if save:
                    p = filedialog.asksaveasfilename(title=label, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
                else:
                    p = filedialog.askopenfilename(title=label, filetypes=[("Dokumente", "*.csv *.xlsx *.xls *.pdf *.docx"), ("Alle Dateien", "*.*")])
                if p:
                    var.set(p)
                    if var is self.invoice_var:
                        self.load_preview(p)
            tk.Button(parent, text="…", command=browse, font=self.font_small, width=3).grid(row=r, column=2, pady=3)

        path_row(0, "KST-Zuordnungsdokument", self.template_var)
        path_row(1, "Rechnung / Dokument", self.invoice_var)
        path_row(2, "Export-CSV", self.export_var, save=True)
        tk.Label(parent, text="Kostenbeschreibung", bg=self.bg, font=self.font_small).grid(row=3, column=0, sticky="w", pady=3)
        ttk.Combobox(parent, textvariable=self.global_prefix_var, values=COST_TYPE_OPTIONS, state="normal", font=self.font_small).grid(row=3, column=1, sticky="ew", padx=4, pady=3)
        tk.Button(parent, text="Rechnung analysieren", command=self.analyze_invoice, font=self.font_small).grid(row=4, column=0, sticky="w", pady=(6, 3))
        tk.Button(parent, text="+ Berechnungsquelle", command=self.add_empty_source, font=self.font_small).grid(row=4, column=1, sticky="w", pady=(6, 3))
        tk.Button(parent, text="AFI-Upload-Datei erstellen", command=self.run_export, font=("Segoe UI", 10, "bold"), bg="#CFEAD6", activebackground="#BDE3C7").grid(row=4, column=1, columnspan=2, sticky="e", padx=(80, 0), pady=(6, 3))
        tk.Label(parent, textvariable=self.suggestion_var, bg=self.bg, fg="#7A4B00", font=self.font_small, wraplength=520, justify="left").grid(row=5, column=0, columnspan=3, sticky="ew")

        self.sources_canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0)
        self.sources_inner = tk.Frame(self.sources_canvas, bg=self.bg)
        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.sources_canvas.yview)
        self.sources_canvas.configure(yscrollcommand=yscroll.set)
        self.sources_canvas.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(6, 0))
        yscroll.grid(row=6, column=2, sticky="ns", pady=(6, 0))
        parent.rowconfigure(6, weight=1)
        self.sources_window = self.sources_canvas.create_window((0, 0), window=self.sources_inner, anchor="nw")
        self.sources_canvas.bind("<Configure>", lambda e: self.sources_canvas.itemconfigure(self.sources_window, width=max(100, e.width - 4)))
        self.sources_inner.bind("<Configure>", lambda e: self.sources_canvas.configure(scrollregion=self.sources_canvas.bbox("all")))
        tk.Label(parent, textvariable=self.status_var, bg=self.bg, font=self.font_small, wraplength=540, justify="left").grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6, 0))

    def _build_right(self, parent):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        header = tk.Frame(parent, bg=self.bg)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="Dokumentenvorschau", bg=self.bg, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.hide_empty_columns_var = tk.BooleanVar(value=True)
        tk.Checkbutton(header, text="Leere Spalten ausblenden", variable=self.hide_empty_columns_var, bg=self.bg, font=self.font_small, command=self.refresh_table_preview).grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.preview_frame = tk.Frame(parent, bg="white", relief="sunken", bd=1)
        self.preview_frame.grid(row=1, column=0, sticky="nsew")
        self.preview_frame.grid_propagate(False)
        self.preview_frame.pack_propagate(False)
        self.highlight_var = tk.StringVar(value="Markierte Spalten: -")
        tk.Label(parent, textvariable=self.highlight_var, bg="#FFF4C2", anchor="w", font=self.font_small).grid(row=2, column=0, sticky="ew", pady=(4, 0))

    def clear_sources(self):
        for s in self.sources:
            s.destroy()
        self.sources = []

    def add_source(self, data=None):
        row = SourceRow(self.sources_inner, self, len(self.sources) + 1, self.headers, data)
        row.grid(row=len(self.sources), column=0, sticky="ew", padx=2, pady=4)
        self.sources_inner.columnconfigure(0, weight=1)
        self.sources.append(row)
        self.on_mapping_changed()

    def add_empty_source(self):
        self.add_source(default_source(len(self.sources) + 1, self.headers))

    def analyze_invoice(self):
        path = self.invoice_var.get().strip()
        if not os.path.isfile(path):
            messagebox.showwarning(MODULE_TITLE, "Bitte eine gültige Rechnung auswählen.")
            return
        try:
            ext = os.path.splitext(path)[1].lower()
            self.clear_sources()
            if ext == ".pdf":
                self.headers, self.rows = ["PDF"], []
                self.load_preview(path)
                self.suggestion_var.set("PDF erkannt: Beträge werden beim Export aus Fahrzeug-/TOTAL-Blöcken gelesen. Berechnungsquellen sind hierfür nicht erforderlich.")
                self.status_var.set("PDF-Rechnung analysiert. Bitte Kostenbeschreibung und KST-Zuordnungsdokument prüfen.")
                return
            self.headers, self.rows = _read_table_file(path)
            suggestions = suggested_sources(self.headers)
            # Gewünscht: nur eine Quelle anlegen, aber auf weitere vermutete Quellen hinweisen.
            self.add_source(suggestions[0])
            if len(suggestions) > 1:
                names = ", ".join(s.get("label", "") for s in suggestions[1:])
                self.suggestion_var.set(f"Weitere mögliche Berechnungsquellen erkannt: {names}. Bei Bedarf über '+ Berechnungsquelle' hinzufügen und Spalten manuell setzen.")
            else:
                self.suggestion_var.set("")
            self.load_preview(path)
            self.status_var.set("Rechnung analysiert. Bitte Berechnungsquelle prüfen/ergänzen.")
        except Exception as exc:
            messagebox.showerror(MODULE_TITLE, str(exc))

    def selected_columns(self):
        cols = []
        for src in self.sources:
            cols.extend(src.selected_columns())
        return [c for i, c in enumerate(cols) if c and c not in cols[:i]]

    def on_mapping_changed(self):
        self.update_footer()
        self.update_highlight()

    def update_footer(self):
        if not self.rows:
            self.footer_var.set("Nettobetrag der ausgewählten Spalten: 0,00 | individuelle Fahrer: 0 | individuelle Kennzeichen: 0")
            return
        total = Decimal("0.00")
        drivers = set(); keys = set()
        for src_row in self.sources:
            src = src_row.get()
            if not src.get("active") or not src.get("net"):
                continue
            for row in self.rows:
                amount = _dec(row.get(src.get("net"), ""))
                if amount == 0:
                    continue
                total += amount
                d = _driver_from_row(row, src)
                k = _clean(row.get(src.get("key", ""), "")) if src.get("key") else ""
                if d: drivers.add(_norm(d))
                if k: keys.add(_norm(k))
        self.footer_var.set(f"Nettobetrag der ausgewählten Spalten: {_fmt(total)} | individuelle Fahrer: {len([d for d in drivers if d])} | individuelle Kennzeichen: {len([k for k in keys if k])}")

    def update_highlight(self):
        cols = self.selected_columns()
        self.highlight_var.set("Markierte Spalten: " + (", ".join(cols) if cols else "-"))
        if self.preview_tree:
            display_cols = list(self.preview_tree["columns"])
            for col in display_cols:
                label = col
                clean_col = col[2:] if col.startswith("★ ") else col
                if clean_col in cols and not col.startswith("★ "):
                    self.preview_tree.heading(col, text="★ " + clean_col)
                elif clean_col not in cols:
                    self.preview_tree.heading(col, text=clean_col)

    def _filtered_preview_headers(self, headers, rows):
        out = list(headers)
        if self.hide_empty_columns_var is not None and self.hide_empty_columns_var.get():
            out = [h for h in out if any(_clean(row.get(h, "")) for row in rows)]
        return out

    def refresh_table_preview(self):
        if self.preview_path and self.preview_headers:
            self.load_table_preview(self.preview_path, self.preview_headers, self.preview_rows)

    def load_preview(self, path):
        self.preview_path = path
        for w in self.preview_frame.winfo_children():
            w.destroy()
        self.preview_tree = None
        ext = os.path.splitext(path)[1].lower()
        if ext in (".csv", ".xlsx", ".xls"):
            self.load_table_preview(path)
        else:
            self.preview_headers = []
            self.preview_rows = []
            self.load_image_preview(path)

    def load_table_preview(self, path, headers=None, rows=None):
        try:
            if headers is None or rows is None:
                headers, rows = _read_table_file(path)
                self.preview_headers = headers
                self.preview_rows = rows
            headers = self._filtered_preview_headers(headers, rows)
        except Exception as exc:
            tk.Label(self.preview_frame, text=str(exc), bg="white", fg="red").pack(fill="both", expand=True)
            return
        # Eigene, begrenzte Vorschaufläche: keine Geometrieausdehnung aus dem rechten Vorschaufenster heraus.
        holder = tk.Frame(self.preview_frame, bg="white")
        holder.place(relx=0, rely=0, relwidth=1, relheight=1)
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)
        style = ttk.Style(holder)
        try:
            style.configure("AfiPreview.Treeview", font=("Segoe UI", self.table_font_size), rowheight=max(18, self.table_font_size + 10))
            style.configure("AfiPreview.Treeview.Heading", font=("Segoe UI", self.table_font_size, "bold"))
        except Exception:
            pass
        tree = ttk.Treeview(holder, columns=headers, show="headings", style="AfiPreview.Treeview")
        vs = ttk.Scrollbar(holder, orient="vertical", command=tree.yview)
        hs = ttk.Scrollbar(holder, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        for h in headers:
            tree.heading(h, text=h)
            tree.column(h, width=max(90, min(220, len(h) * 8)), stretch=False)
        for row in rows[:500]:
            tree.insert("", "end", values=[_clean(row.get(h, "")) for h in headers])
        self.preview_tree = tree
        def on_select(event=None):
            item = tree.focus()
            if not item:
                return
            vals = tree.item(item, "values")
            self.selected_cell = "\t".join(str(v) for v in vals)
        def copy(event=None):
            holder.clipboard_clear(); holder.clipboard_append(self.selected_cell)
            return "break"
        def wheel(event):
            # Mausrad bleibt innerhalb der Vorschau: vertikal, mit Shift horizontal, mit Ctrl Tabellenzoom.
            delta = -1 if event.delta > 0 else 1
            if event.state & 0x0004:
                self.table_font_size = max(7, min(16, self.table_font_size + (-delta)))
                try:
                    style.configure("AfiPreview.Treeview", font=("Segoe UI", self.table_font_size), rowheight=max(18, self.table_font_size + 10))
                    style.configure("AfiPreview.Treeview.Heading", font=("Segoe UI", self.table_font_size, "bold"))
                    for col in headers:
                        tree.column(col, width=max(80, min(320, int(tree.column(col, 'width') * (1.08 if delta < 0 else 0.92)))))
                except Exception:
                    pass
            elif event.state & 0x0001:
                tree.xview_scroll(delta * 3, "units")
            else:
                tree.yview_scroll(delta * 3, "units")
            return "break"
        tree.bind("<<TreeviewSelect>>", on_select)
        tree.bind("<Control-c>", copy)
        tree.bind("<MouseWheel>", wheel)
        tree.bind("<Button-4>", lambda e: (tree.yview_scroll(-3, "units"), "break"))
        tree.bind("<Button-5>", lambda e: (tree.yview_scroll(3, "units"), "break"))
        self.update_highlight()

    def _render_preview_image(self):
        if not self.preview_canvas or self.preview_base_image is None or ImageTk is None:
            return
        cw = max(1, self.preview_canvas.winfo_width())
        ch = max(1, self.preview_canvas.winfo_height())
        bw, bh = self.preview_base_image.size
        scale = self.preview_zoom
        zw, zh = max(1, int(bw * scale)), max(1, int(bh * scale))
        img = self.preview_base_image.resize((zw, zh))
        # Begrenzen: Bild darf nicht aus dem Vorschaufenster herausgezogen werden.
        if zw <= cw:
            self.preview_offset[0] = (cw - zw) // 2
        else:
            self.preview_offset[0] = min(0, max(cw - zw, self.preview_offset[0]))
        if zh <= ch:
            self.preview_offset[1] = (ch - zh) // 2
        else:
            self.preview_offset[1] = min(0, max(ch - zh, self.preview_offset[1]))
        self.image_ref = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(self.preview_offset[0], self.preview_offset[1], image=self.image_ref, anchor="nw")

    def load_image_preview(self, path):
        if Image is None or ImageTk is None:
            tk.Label(self.preview_frame, text="Bildvorschau nicht verfügbar (Pillow nicht geladen).", bg="white").pack(fill="both", expand=True)
            return
        ext = os.path.splitext(path)[1].lower()
        text = os.path.basename(path)
        try:
            if ext == ".pdf":
                try:
                    import PyPDF2
                    with open(path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        text = (reader.pages[0].extract_text() or "PDF-Vorschau")[:1400]
                except Exception:
                    text = "PDF-Bildvorschau: Text konnte nicht extrahiert werden."
            elif ext == ".docx":
                try:
                    import docx
                    doc = docx.Document(path)
                    text = "\n".join(p.text for p in doc.paragraphs[:40])[:1400] or "Word-Dokument"
                except Exception:
                    text = "Word-Bildvorschau: Text konnte nicht extrahiert werden."
            img = Image.new("RGB", (760, 520), "white")
            draw = ImageDraw.Draw(img)
            draw.rectangle((10, 10, 750, 510), outline="#B0B0B0")
            draw.text((24, 24), os.path.basename(path), fill="#1F4E79")
            y = 62
            for line in text.splitlines()[:24]:
                draw.text((24, y), line[:110], fill="black")
                y += 18
            self.preview_base_image = img
            self.preview_zoom = 1.0
            self.preview_offset = [0, 0]
            self.preview_canvas = tk.Canvas(self.preview_frame, bg="white", highlightthickness=0)
            self.preview_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
            def on_wheel(event):
                factor = 1.1 if event.delta > 0 else 0.9
                old_zoom = self.preview_zoom
                self.preview_zoom = max(0.25, min(4.0, self.preview_zoom * factor))
                if old_zoom != 0:
                    mx, my = event.x, event.y
                    self.preview_offset[0] = int(mx - (mx - self.preview_offset[0]) * (self.preview_zoom / old_zoom))
                    self.preview_offset[1] = int(my - (my - self.preview_offset[1]) * (self.preview_zoom / old_zoom))
                self._render_preview_image()
                return "break"
            def on_press(event):
                self.preview_drag_start = (event.x, event.y, self.preview_offset[0], self.preview_offset[1])
                return "break"
            def on_drag(event):
                if not self.preview_drag_start:
                    return "break"
                sx, sy, ox, oy = self.preview_drag_start
                self.preview_offset = [ox + event.x - sx, oy + event.y - sy]
                self._render_preview_image()
                return "break"
            self.preview_canvas.bind("<Configure>", lambda e: self._render_preview_image())
            self.preview_canvas.bind("<MouseWheel>", on_wheel)
            self.preview_canvas.bind("<ButtonPress-1>", on_press)
            self.preview_canvas.bind("<B1-Motion>", on_drag)
            self._render_preview_image()
        except Exception as exc:
            tk.Label(self.preview_frame, text=f"Vorschaufehler: {exc}", bg="white", fg="red").pack(fill="both", expand=True)

    def _open_file(self, path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess; subprocess.Popen(["open", path])
            else:
                import subprocess; subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror(MODULE_TITLE, f"Datei konnte nicht geöffnet werden:\n{exc}")

    def _show_export_done_dialog(self, result):
        invoice_name = os.path.basename(self.invoice_var.get().strip()) or "Rechnungs-Dokument"
        dialog = tk.Toplevel(self.app.root)
        dialog.title(MODULE_TITLE)
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        frm = tk.Frame(dialog, bg=self.bg, padx=18, pady=16)
        frm.pack(fill="both", expand=True)
        tk.Label(frm, text=f"Bitte die erstellte AFI-Upload-Datei für \"{invoice_name}\" prüfen.", bg=self.bg, font=("Segoe UI", 10, "bold"), wraplength=520, justify="left").pack(anchor="w", pady=(0, 12))
        tk.Label(frm, text=f"Datei: {result.get('export_path', '')}", bg=self.bg, font=self.font_small, wraplength=520, justify="left").pack(anchor="w", pady=(0, 12))
        btns = tk.Frame(frm, bg=self.bg)
        btns.pack(anchor="e")
        def open_and_close():
            dialog.grab_release()
            dialog.destroy()
            self._open_file(result.get("export_path", ""))
        tk.Button(btns, text="AFI-Upload zur Prüfung öffnen", command=open_and_close, bg="#CFEAD6", activebackground="#BDE3C7", font=self.font_small).pack(side="left", padx=(0, 8))
        tk.Button(btns, text="Nicht jetzt", command=lambda: (dialog.grab_release(), dialog.destroy()), font=self.font_small).pack(side="left")
        dialog.update_idletasks()
        x = self.app.root.winfo_rootx() + max(40, (self.app.root.winfo_width() - dialog.winfo_width()) // 2)
        y = self.app.root.winfo_rooty() + max(40, (self.app.root.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")

    def run_export(self):
        template_path = self.template_var.get().strip()
        invoice_path = self.invoice_var.get().strip()
        export_path = self.export_var.get().strip()
        if not os.path.isfile(template_path):
            messagebox.showwarning(MODULE_TITLE, "Bitte ein gültiges KST-Zuordnungsdokument auswählen.")
            return
        if not os.path.isfile(invoice_path):
            messagebox.showwarning(MODULE_TITLE, "Bitte eine gültige Rechnung auswählen.")
            return
        if not export_path.lower().endswith(".csv"):
            export_path += ".csv"; self.export_var.set(export_path)
        config = {"global_prefix": self.global_prefix_var.get(), "sources": [s.get() for s in self.sources]}
        self.status_var.set("Export läuft…")
        def worker():
            try:
                result = create_supplier_upload_csv(template_path, invoice_path, export_path, config)
                def done():
                    self.status_var.set(f"Export erstellt: {result['rows']} Zeilen → {result['export_path']} | Netto: {result['export_net_total']} | Fahrer: {result['unique_drivers']} | Kennzeichen: {result['unique_keys']}")
                    critical = []
                    if result.get("missing_template"):
                        critical.append("Keine eindeutige Kontierung gefunden:\n" + "\n".join(result["missing_template"][:40]))
                    if result.get("empty_assignment"):
                        critical.append("Zeilen ohne Fahrer/Schlüssel:\n" + "\n".join(result["empty_assignment"][:30]))
                    if result.get("unknown_tax"):
                        critical.append("Nicht eindeutig erkannte Steuersätze:\n" + "\n".join(result["unknown_tax"][:30]))
                    if critical:
                        messagebox.showwarning(MODULE_TITLE, "\n\n".join(critical))
                self.app.root.after(0, done)
            except Exception as exc:
                self.app.root.after(0, lambda: (self.status_var.set("Fehler beim Export."), messagebox.showerror(MODULE_TITLE, str(exc))))
        threading.Thread(target=worker, daemon=True).start()


def render(app):
    SupplierUploadUI(app).render()

# FLEXIBLE_KST_ZUORDNUNG_V1
# Überschreibt die bisherigen Vorlagenfunktionen zur Laufzeit. Dadurch bleibt die alte UI-Struktur kompatibel,
# aber fachlich wird keine AFI-/Kontierungsvorlage mehr benötigt, sondern ein flexibles KST-Zuordnungsdokument.
COST_TYPE_OPTIONS = ["Tanken Strom", "Tanken", "Versicherung", "Leasing", "Mobilfunk/Festnetz", "Sonstige (bitte eingeben)"]
VALID_NET_TAX_RATES = {Decimal("0"), Decimal("7"), Decimal("19")}
FOREIGN_GROSS_TAX_CODE = "V0"
ENBW_BLOCKING_GL_ACCOUNT = "427010"


def _detect_header_row(raw_df):
    header_keywords = ["kennzeichen", "rufnummer", "telefon", "msisdn", "fahrer", "name", "vorname", "nachname", "kostenstelle", "costcenter", "kst", "sachkonto", "gl_account", "innenauftrag", "ia", "orderid", "netto", "brutto", "mehrwert", "steuer", "betrag", "positionstyp", "organisationseinheit"]
    best_idx, best_score = 0, -1
    for i in range(min(25, len(raw_df))):
        vals = [_clean(v) for v in raw_df.iloc[i].tolist()]
        joined = " ".join(vals).lower()
        score = sum(1 for v in vals if v) + sum(5 for kw in header_keywords if kw in joined)
        if score > best_score:
            best_idx, best_score = i, score
    return best_idx


def _dedupe_headers(headers):
    out, seen = [], {}
    for idx, h in enumerate(headers):
        base = _clean(h) or f"Spalte_{idx+1}"
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return out


def _read_excel_flexible(path):
    try:
        import pandas as pd
        ext = os.path.splitext(path)[1].lower()
        engine = "openpyxl" if ext in (".xlsx", ".xlsm") else "xlrd"
        raw = pd.read_excel(path, engine=engine, dtype=str, header=None).fillna("")
        if raw.empty:
            return [], []
        header_idx = _detect_header_row(raw)
        headers = _dedupe_headers([_clean(v) for v in raw.iloc[header_idx].tolist()])
        df = raw.iloc[header_idx + 1:].copy()
        df.columns = headers
        df = df[df.apply(lambda r: any(_clean(v) for v in r.values), axis=1)]
        return headers, df.fillna("").to_dict(orient="records")
    except Exception as exc:
        raise RuntimeError(f"Excel-Datei konnte nicht gelesen werden: {exc}")


def _extract_docx_text(path):
    try:
        import zipfile, html as _html
        parts = []
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                if name.startswith("word/") and name.endswith(".xml"):
                    xml = z.read(name).decode("utf-8", errors="ignore")
                    xml = re.sub(r"<w:tab\s*/>", "\t", xml)
                    xml = re.sub(r"</w:p>", "\n", xml)
                    texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, flags=re.S)
                    if texts:
                        parts.append(_html.unescape(" ".join(texts)))
        return "\n".join(parts)
    except Exception as exc:
        raise RuntimeError(f"DOCX-Datei konnte nicht gelesen werden: {exc}")


def _extract_pdf_text(path):
    errors = []
    try:
        import PyPDF2
        chunks = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                chunks.append(page.extract_text() or "")
        text = "\n".join(chunks)
        if _clean(text):
            return text
    except Exception as exc:
        errors.append(str(exc))
    try:
        import fitz
        doc = fitz.open(path)
        chunks = [page.get_text("text") for page in doc]
        doc.close()
        text = "\n".join(chunks)
        if _clean(text):
            return text
    except Exception as exc:
        errors.append(str(exc))
    raise RuntimeError("PDF-Text konnte nicht extrahiert werden: " + " | ".join(errors))


def _read_table_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _read_csv(path)
    if ext in (".xlsx", ".xlsm", ".xls"):
        return _read_excel_flexible(path)
    if ext == ".docx":
        text = _extract_docx_text(path)
        return ["TEXT"], [{"TEXT": line} for line in text.splitlines() if _clean(line)]
    if ext == ".pdf":
        text = _extract_pdf_text(path)
        return ["TEXT"], [{"TEXT": line} for line in text.splitlines() if _clean(line)]
    raise RuntimeError("Für die Berechnung werden CSV-, Excel-, PDF- oder DOCX-Dateien benötigt.")


def _cost_type(label):
    n = _norm(label)
    if "TANKENSTROM" in n or ("TANKEN" in n and "STROM" in n): return "TANKEN_STROM"
    if "TANKEN" in n: return "TANKEN"
    if "VERSICHER" in n: return "VERSICHERUNG"
    if "LEAS" in n: return "LEASING"
    if "MOBIL" in n or "FESTNETZ" in n or "TELEFON" in n or "VODAFONE" in n: return "MOBILFUNK"
    return "SONSTIGE"


def _digits_only(value):
    return re.sub(r"\D", "", _clean(value))


def _is_gl_account(value):
    return bool(re.fullmatch(r"4\d{5}", _digits_only(value)))


def _is_costcenter(value):
    d = _digits_only(value)
    return bool(re.fullmatch(r"\d{6,7}", d)) and not _is_gl_account(value)


def _extract_identifier(text):
    s = _clean(text)
    m = re.search(r"\b0\d{2,5}[\s/\-]?\d{3,10}\b", s)
    if m: return m.group(0), "PHONE"
    m = re.search(r"\b[A-ZÄÖÜ]{1,3}[\s\-]{1,2}[A-ZÄÖÜ]{1,3}[\s\-]?\d{1,5}[A-ZÄÖÜ]?\b", s, flags=re.I)
    if m: return m.group(0), "PLATE"
    m = re.search(r"\bKFZ\s+[A-Z0-9]{6,}\b", s, flags=re.I)
    if m: return m.group(0), "KEY"
    m = re.search(r"\b[A-Z0-9]{3,}-[A-Z0-9]{3,}(?:-[A-Z0-9]{3,})*\b", s, flags=re.I)
    if m: return m.group(0), "KEY"
    return "", ""


def _split_name(value):
    s = _clean(value)
    if not s: return "", "", ""
    if "," in s:
        last, first = [x.strip() for x in s.split(",", 1)]
        return _clean(f"{first} {last}"), first, last
    parts = s.split()
    if len(parts) == 1: return s, "", parts[0]
    return s, " ".join(parts[:-1]), parts[-1]


def _find_value_by_header(row, headers, keywords, validator=None, exclude=None):
    exclude = exclude or []
    candidates = []
    for h in headers:
        nh = _norm(h)
        if any(_norm(x) in nh for x in exclude):
            continue
        score = sum(weight for kw, weight in keywords if _norm(kw) in nh)
        if score:
            val = _clean(row.get(h, ""))
            if val and (validator is None or validator(val)):
                candidates.append((score, h, val))
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2]
    return ""


def _extract_any_gl(row, headers):
    for h in headers:
        val = _clean(row.get(h, ""))
        if _is_gl_account(val): return _digits_only(val)
    m = re.search(r"\b4\d{5}\b", " ".join(_clean(row.get(h, "")) for h in headers))
    return m.group(0) if m else ""


def _assignment_entry_from_row(row, headers):
    joined = " ".join(_clean(row.get(h, "")) for h in headers)
    identifier = _find_value_by_header(row, headers, [("Kennzeichen",12),("Rufnummer",12),("Telefon",10),("MSISDN",10),("Lademedium",6),("Schlüssel",6)])
    id_type = ""
    if identifier:
        found, id_type = _extract_identifier(identifier)
        identifier = found or identifier
    if not identifier:
        identifier, id_type = _extract_identifier(joined)
    first = _find_value_by_header(row, headers, [("Vorname",10),("First",8)])
    last = _find_value_by_header(row, headers, [("Nachname",10),("Surname",8),("Last",8)])
    full = _find_value_by_header(row, headers, [("TEXT",12),("Fahrer",10),("Name",8),("Mitarbeiter",7),("Nutzer",7)], exclude=["Vorname","Nachname","Sachkonto"])
    if not full and (first or last): full = _clean(f"{first} {last}")
    if full and (not first or not last):
        _, sf, sl = _split_name(full)
        first = first or sf; last = last or sl
    gl_default = _find_value_by_header(row, headers, [("GL_ACCOUNT",12),("Sachkonto",10),("Konto",6)], validator=_is_gl_account, exclude=["Versicherung","Tanken","Strom","Mobil","Telefon","Leasing"])
    gl_tanken_strom = _find_value_by_header(row, headers, [("Tanken Strom",14),("Strom Sachkonto",12),("Laden Sachkonto",10),("Energie Sachkonto",8)], validator=_is_gl_account)
    gl_tanken = _find_value_by_header(row, headers, [("Tanken Sachkonto",14),("Tank Sachkonto",12),("Kraftstoff",8)], validator=_is_gl_account, exclude=["Strom"])
    gl_versicherung = _find_value_by_header(row, headers, [("Versicherung Sachkonto",14),("Versicherung",10)], validator=_is_gl_account)
    gl_leasing = _find_value_by_header(row, headers, [("Leasing Sachkonto",14),("Leasing",10),("Sachkonto",4)], validator=_is_gl_account)
    gl_mobilfunk = _find_value_by_header(row, headers, [("Mobilfunk",12),("Festnetz",12),("Telefon",10),("Vodafone",10),("GL_ACCOUNT",5),("Sachkonto",4)], validator=_is_gl_account)
    gl_default = gl_default or _extract_any_gl(row, headers)
    cc_default = _find_value_by_header(row, headers, [("COSTCENTER",12),("Kostenstelle",12),("KST",12)], validator=_is_costcenter, exclude=["Tanken","Strom","Versicherung","Leasing","Mobil","Telefon","IA","Innenauftrag","ORDER"])
    cc_tanken_strom = _find_value_by_header(row, headers, [("Tanken Strom",14),("Strom KST",12),("Laden KST",10)], validator=_is_costcenter)
    cc_tanken = _find_value_by_header(row, headers, [("Tanken KST",14),("Tank KST",12),("Tanken Kostenstelle",12)], validator=_is_costcenter, exclude=["Strom"])
    cc_versicherung = _find_value_by_header(row, headers, [("Versicherung KST",14),("Versicherung Kostenstelle",12)], validator=_is_costcenter)
    cc_leasing = _find_value_by_header(row, headers, [("Leasing KST",14),("Leasing Kostenstelle",12)], validator=_is_costcenter)
    cc_mobilfunk = _find_value_by_header(row, headers, [("Mobilfunk",12),("Festnetz",12),("Telefon",10),("Vodafone",10)], validator=_is_costcenter)
    orderid = _find_value_by_header(row, headers, [("ORDERID",12),("Innenauftrag",12),("IA",10),("Auftrag",7)], validator=_is_costcenter)
    return {
        "identifier": _clean(identifier), "identifier_norm": _norm(identifier), "identifier_type": id_type,
        "full_name": _clean(full), "first": _clean(first), "last": _clean(last),
        "name_norm": _norm(_clean(f"{first} {last}") or full), "last_norm": _norm(last),
        "gl_default": _digits_only(gl_default), "gl_tanken_strom": _digits_only(gl_tanken_strom), "gl_tanken": _digits_only(gl_tanken), "gl_versicherung": _digits_only(gl_versicherung), "gl_leasing": _digits_only(gl_leasing), "gl_mobilfunk": _digits_only(gl_mobilfunk),
        "cc_default": _digits_only(cc_default), "cc_tanken_strom": _digits_only(cc_tanken_strom), "cc_tanken": _digits_only(cc_tanken), "cc_versicherung": _digits_only(cc_versicherung), "cc_leasing": _digits_only(cc_leasing), "cc_mobilfunk": _digits_only(cc_mobilfunk),
        "orderid": _digits_only(orderid), "raw": joined
    }


def load_assignment_entries(assignment_path):
    headers, rows = _read_table_file(assignment_path)
    entries = []
    for row in rows:
        e = _assignment_entry_from_row(row, headers)
        if e.get("identifier") or e.get("full_name") or e.get("gl_default") or e.get("cc_default"):
            entries.append(e)
    if not entries:
        raise RuntimeError("Im KST-Zuordnungsdokument konnten keine verwertbaren Zuordnungen erkannt werden.")
    return entries


def _select_assignment_values(entry, cost_type, text_label=""):
    if "BLOCKIER" in _norm(text_label): gl = ENBW_BLOCKING_GL_ACCOUNT
    elif cost_type == "TANKEN_STROM": gl = entry.get("gl_tanken_strom") or entry.get("gl_tanken") or entry.get("gl_default")
    elif cost_type == "TANKEN": gl = entry.get("gl_tanken") or entry.get("gl_default")
    elif cost_type == "VERSICHERUNG": gl = entry.get("gl_versicherung") or entry.get("gl_default")
    elif cost_type == "LEASING": gl = entry.get("gl_leasing") or entry.get("gl_default")
    elif cost_type == "MOBILFUNK": gl = entry.get("gl_mobilfunk") or entry.get("gl_default")
    else: gl = entry.get("gl_default")
    if cost_type == "TANKEN_STROM": cc = entry.get("cc_tanken_strom") or entry.get("cc_tanken") or entry.get("cc_default")
    elif cost_type == "TANKEN": cc = entry.get("cc_tanken") or entry.get("cc_default")
    elif cost_type == "VERSICHERUNG": cc = entry.get("cc_versicherung") or entry.get("cc_default")
    elif cost_type == "LEASING": cc = entry.get("cc_leasing") or entry.get("cc_default")
    elif cost_type == "MOBILFUNK": cc = entry.get("cc_mobilfunk") or entry.get("cc_default")
    else: cc = entry.get("cc_default")
    return gl or "", cc or "", entry.get("orderid", "") or ""


def resolve_assignment(key, driver, entries):
    nkey, ndriver = _norm(key), _norm(driver)
    parts = _clean(driver).split(); last = _norm(parts[-1]) if parts else ""
    candidates = []
    for e in entries:
        score, how = 0, []
        eid = e.get("identifier_norm", "")
        if nkey and eid and (nkey == eid or nkey in eid or eid in nkey): score += 100; how.append("Schlüssel")
        if ndriver and e.get("name_norm") and (ndriver == e.get("name_norm") or ndriver in e.get("name_norm") or e.get("name_norm") in ndriver): score += 30; how.append("Name")
        if last and e.get("last_norm") and last == e.get("last_norm"): score += 20; how.append("Nachname")
        if score: candidates.append((score, "+".join(how), e))
    if not candidates: return {}, ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    best_score = candidates[0][0]
    best = [c for c in candidates if c[0] == best_score]
    if len(best) > 1 and best_score < 100: return {}, "mehrdeutig"
    return best[0][2], best[0][1]


def _amount_and_tax_from_values(net, gross, rate):
    rate = Decimal(rate or "0.00")
    if rate in VALID_NET_TAX_RATES:
        return Decimal(net), _tax_code_from_rate(rate), False
    if Decimal(gross or "0.00") != 0:
        return Decimal(gross), FOREIGN_GROSS_TAX_CODE, True
    return Decimal(net) * (Decimal("1.00") + rate / Decimal("100")), FOREIGN_GROSS_TAX_CODE, True


def _parse_pdf_invoice_positions(path, global_prefix):
    text = _extract_pdf_text(path)
    compact = " ".join(text.replace("\n", " ").split())
    positions = []
    pattern = re.compile(r"VEHICLE:\s*(?P<vehicle>.*?)\s+CARD NO\.:.*?(?P<body>.*?)(?=VEHICLE:|Umsatzsteuerstatistik|Statistica|Distinta|$)", re.I)
    for m in pattern.finditer(compact):
        vehicle, body = _clean(m.group("vehicle")), m.group("body")
        rate_m = re.search(r"(?:USt|IVA)\s*\(%\):\s*(\d{1,2},\d{2}|\d{1,2})", compact[:m.start()], re.I)
        rate = _dec(rate_m.group(1)) if rate_m else Decimal("19")
        total_m = re.search(r"TOTAL:\s*(.*?)(?=VEHICLE:|Umsatzsteuerstatistik|Statistica|Distinta|Übertrag|EUR Übertrag|$)", body, re.I)
        if not total_m: continue
        nums = re.findall(r"-?\d{1,3}(?:\.\d{3})*,\d{2,3}|-?\d+,\d{1,3}|-?\d+", total_m.group(1))
        vals = [_dec(x) for x in nums]
        if len(vals) < 3: continue
        amount, tax, foreign = _amount_and_tax_from_values(vals[-3], vals[-1], rate)
        if amount != 0:
            positions.append({"key": vehicle, "driver": vehicle, "amount": amount, "tax": tax, "foreign_gross": foreign, "source_label": global_prefix})
    if not positions:
        raise RuntimeError("Aus der PDF konnten keine Fahrzeug-/TOTAL-Positionen erkannt werden.")
    return positions


def create_supplier_upload_csv(assignment_path, invoice_path, export_path, config):
    assignment_entries = load_assignment_entries(assignment_path)
    global_prefix = _clean(config.get("global_prefix", "Tanken Strom")) or "Tanken Strom"
    cost_type = _cost_type(global_prefix)
    ext = os.path.splitext(invoice_path)[1].lower()
    groups = OrderedDict(); warnings_missing=[]; warnings_tax=[]; warnings_empty_assignment=[]; warnings_name_fallback=[]; warnings_foreign_gross=[]; warnings_enbw_split=[]
    invoice_total = Decimal("0.00"); unique_drivers=set(); unique_keys=set()
    def add_group(source_label, key, driver, tax, amount, force_text=None):
        # Fachregel: Alle normalen Berechnungsquellen werden je Fahrzeug/Fahrer/Kennzeichen und Steuersatz kombiniert.
        # Nur fachliche Sonderzeilen mit force_text, insbesondere Blockiergebuehren, bleiben separat.
        grouping_label = force_text or global_prefix
        group_key = (_norm(grouping_label), _norm(driver), _norm(key), tax)
        if group_key not in groups:
            groups[group_key] = {"source_label": grouping_label, "key": key, "driver": driver, "tax": tax, "amount": Decimal("0.00"), "force_text": force_text or ""}
        groups[group_key]["amount"] += Decimal(amount)
    if ext == ".pdf":
        for pos in _parse_pdf_invoice_positions(invoice_path, global_prefix):
            add_group(pos["source_label"], pos["key"], pos["driver"], pos["tax"], pos["amount"])
            invoice_total += Decimal(pos["amount"])
            if pos.get("foreign_gross"): warnings_foreign_gross.append(f"{pos['key']}: abweichender/ausländischer Steuersatz -> Bruttobetrag mit V0 verwendet")
    else:
        headers, rows = _read_table_file(invoice_path)
        sources = [s for s in config.get("sources", []) if s.get("active", True) and s.get("net")]
        if not sources: raise RuntimeError("Bitte mindestens eine aktive Berechnungsquelle mit Betragsspalte auswählen.")
        for src in sources:
            src_label = _clean(src.get("label") or src.get("net") or global_prefix)
            is_blocking = "BLOCKIER" in _norm(src_label) or "BLOCKIER" in _norm(src.get("net", ""))
            for idx, row in enumerate(rows):
                net = _dec(row.get(src.get("net", ""), ""))
                if net == 0: continue
                driver = _driver_from_row(row, src)
                key = _clean(row.get(src.get("key", ""), "")) if src.get("key") else ""
                if not key and driver: key = driver
                if not key or not driver:
                    fb = _fallback_name_from_row(row)
                    if fb:
                        driver = driver or fb; key = key or fb
                if not key and not driver:
                    driver = key = f"UNZUORDENBAR Zeile {idx+2}"; warnings_empty_assignment.append(f"{src_label}: Zeile {idx+2} ohne Fahrer/Schlüssel")
                tax_mode = src.get("tax_mode", "vat")
                if tax_mode == "manual":
                    rate = _dec(src.get("manual_rate", "19")); gross = net * (Decimal("1.00") + rate/Decimal("100"))
                elif tax_mode == "gross":
                    gross = _dec(row.get(src.get("gross", ""), "")); tax = _tax_code_from_net_vat(net, gross-net) if gross else "VX"; amount = net; foreign = False
                    if tax == "VX": warnings_tax.append(f"{src_label} / {key} / {driver}: Steuer nicht eindeutig")
                    rate = Decimal("19")
                    # gross-mode bleibt netto-basiert, falls kein abweichender Steuersatz ermittelbar ist.
                    amount, tax, foreign = amount, tax, foreign
                    invoice_total += amount
                    if is_blocking and ("BLOCKIERGEBUEHR" in _norm(row.get("Positionstyp", "")) or "BLOCKIER" in _norm(src.get("net", ""))):
                        split = "IDG" if _norm(row.get("Organisationseinheit", "")) == "IDG" else "IDE"
                        add_group(f"Blockiergebühren {split}", f"Blockiergebühren {split}", f"Blockiergebühren {split}", tax, amount, force_text=f"Blockiergebühren {split}"); warnings_enbw_split.append(f"Blockiergebühr {split}: Zeile {idx+2}, Betrag {_fmt(amount)}")
                    else:
                        add_group(src_label, key, driver, tax, amount)
                    continue
                else:
                    rate = _dec(row.get(src.get("vat_amount", ""), "")) if src.get("vat_amount") else Decimal("19")
                    gross = _dec(row.get(src.get("gross", ""), "")) if src.get("gross") else Decimal("0.00")
                    if not gross and rate not in VALID_NET_TAX_RATES:
                        gross = net * (Decimal("1.00") + rate/Decimal("100"))
                amount, tax, foreign = _amount_and_tax_from_values(net, gross, rate)
                if foreign: warnings_foreign_gross.append(f"{src_label} / {key}: Steuersatz {_fmt(rate)} % -> Bruttobetrag {_fmt(amount)} mit V0 verwendet")
                invoice_total += amount
                if driver: unique_drivers.add(_norm(driver))
                if key: unique_keys.add(_norm(key))
                if is_blocking and ("BLOCKIERGEBUEHR" in _norm(row.get("Positionstyp", "")) or "BLOCKIER" in _norm(src.get("net", ""))):
                    split = "IDG" if _norm(row.get("Organisationseinheit", "")) == "IDG" else "IDE"
                    add_group(f"Blockiergebühren {split}", f"Blockiergebühren {split}", f"Blockiergebühren {split}", tax, amount, force_text=f"Blockiergebühren {split}"); warnings_enbw_split.append(f"Blockiergebühr {split}: Zeile {idx+2}, Betrag {_fmt(amount)}")
                else:
                    add_group(src_label, key, driver, tax, amount)
    resolved = {}
    ordered_groups = sorted(groups.items(), key=lambda kv: (_norm(kv[1].get("force_text") or kv[1]["key"]), _norm(kv[1]["driver"]), TAX_ORDER.get(kv[1]["tax"],9)))
    for gkey, g in ordered_groups:
        if "BLOCKIERGEBUEHREN" in _norm(g.get("force_text") or g.get("source_label")):
            info, how = resolve_assignment(g["key"], g["driver"], assignment_entries)
            gl, cc, orderid = ENBW_BLOCKING_GL_ACCOUNT, "", ""
            if info:
                _, cc, orderid = _select_assignment_values(info, cost_type, g.get("force_text") or g.get("source_label"))
            resolved[gkey] = {"GL_ACCOUNT": gl, "COSTCENTER": cc, "ORDERID": orderid}
            if not cc: warnings_missing.append(f"{g.get('force_text') or g['key']} / {g['driver']}: keine KST gefunden")
            continue
        info, how = resolve_assignment(g["key"], g["driver"], assignment_entries)
        if not info:
            resolved[gkey] = {"GL_ACCOUNT":"", "COSTCENTER":"", "ORDERID":""}; warnings_missing.append(f"{g['key']} / {g['driver']}: {'mehrdeutige Zuordnung' if how=='mehrdeutig' else 'keine Zuordnung'}")
        else:
            gl, cc, orderid = _select_assignment_values(info, cost_type, g.get("source_label", global_prefix))
            resolved[gkey] = {"GL_ACCOUNT":gl, "COSTCENTER":cc, "ORDERID":orderid}
            if not gl or not cc: warnings_missing.append(f"{g['key']} / {g['driver']}: Sachkonto/KST unvollständig (Sachkonto='{gl}', KST='{cc}')")
            elif how in ("Name","Nachname"): warnings_name_fallback.append(f"{g['key']} / {g['driver']}: Kontierung per {how} übernommen")
    target_total = invoice_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    os.makedirs(os.path.dirname(os.path.abspath(export_path)) or ".", exist_ok=True)
    with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=UPLOAD_COLUMNS, delimiter=";", extrasaction="ignore"); writer.writeheader()
        for gkey, g in ordered_groups:
            amount = g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP); info = resolved.get(gkey,{})
            if g.get("force_text"): out_text = g["force_text"]
            else:
                parts = [g.get("source_label") or global_prefix]
                if g["key"]: parts.append(g["key"])
                if g["driver"] and _norm(g["driver"]) != _norm(g["key"]): parts.append(g["driver"])
                out_text = _clean(" ".join(parts))
            writer.writerow({"TEXT": out_text, "PRICE": _fmt(amount), "PRICE_UNIT":"1", "QUANTITY":"1", "UNIT":"ST", "NET_VALUE": _fmt(amount), "TAX_CODE": g["tax"], "GL_ACCOUNT": info.get("GL_ACCOUNT",""), "COSTCENTER": info.get("COSTCENTER",""), "ORDERID": info.get("ORDERID","")})
    export_total = sum(g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for _, g in ordered_groups)
    return {"rows":len(ordered_groups), "export_path":export_path, "invoice_net_raw_total":_fmt(invoice_total), "export_net_total":_fmt(export_total), "net_rounding_difference":_fmt(export_total-target_total), "unique_drivers":len([x for x in unique_drivers if x]), "unique_keys":len([x for x in unique_keys if x]), "missing_template":warnings_missing, "unknown_tax":warnings_tax, "empty_assignment":warnings_empty_assignment, "name_fallback_matches":warnings_name_fallback, "rounding_adjustments":[], "foreign_gross":warnings_foreign_gross, "enbw_blocking_split":warnings_enbw_split}

# UMLAUT_ASCII_OUTPUT_PATCH_V1
# Ausgabe-Patch: fachliche Ausgabetexte werden ohne deutsche Umlaute geschrieben.
# Beispiel: Mueller, Goetz, Pruefung, Gebuehr, Gross, Strasse.
def _ascii_umlauts(value):
    text = str(value or "")
    replacements = {
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ẞ": "SS",
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text

# Falls create_supplier_upload_csv durch den flexiblen KST-Patch definiert wurde,
# wird die Funktion hier gekapselt. Dadurch bleiben Berechnung/Matching unveraendert,
# aber die fertige Export-CSV enthaelt keine Umlaute mehr.
_create_supplier_upload_csv_before_ascii_patch = create_supplier_upload_csv

def create_supplier_upload_csv(assignment_path, invoice_path, export_path, config):
    result = _create_supplier_upload_csv_before_ascii_patch(assignment_path, invoice_path, export_path, config)
    try:
        if export_path and os.path.isfile(export_path):
            with open(export_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f, delimiter=";")
                fieldnames = reader.fieldnames or []
                rows = []
                for row in reader:
                    converted = {}
                    for key, value in row.items():
                        converted[key] = _ascii_umlauts(value)
                    rows.append(converted)
            with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
    except Exception:
        # Export nicht blockieren, falls nachtraegliche ASCII-Umsetzung fehlschlaegt.
        pass

    # Umlaute werden nur in der geschriebenen Export-CSV ersetzt.
    # Meldungen und interne Rueckgaben bleiben fachlich lesbar.
    return result

# DKV_FOREIGN_TAX_SPLIT_FIX_V1
# Fix: Bei DKV-PDFs muss pro VEHICLE-Block der zuletzt vor dem Block genannte Steuersatz gelten.
# Dadurch wird z. B. HN-I 8589 Deutschland mit 19% separat von HN-I 8589 Italien mit 22% behandelt.
def _parse_pdf_invoice_positions(path, global_prefix):
    text = _extract_pdf_text(path)
    compact = " ".join(text.replace("\n", " ").split())
    positions = []

    vehicle_pattern = re.compile(
        r"VEHICLE:\s*(?P<vehicle>.*?)\s+CARD NO\.:.*?(?P<body>.*?)(?=VEHICLE:|Umsatzsteuerstatistik|Statistica|Distinta|$)",
        re.I,
    )
    tax_pattern = re.compile(r"(?:USt|IVA)\s*\(%\):\s*(\d{1,2},\d{2}|\d{1,2})", re.I)

    for m in vehicle_pattern.finditer(compact):
        vehicle = _clean(m.group("vehicle"))
        body = m.group("body")

        # Wichtig: nicht den ersten Steuersatz im Dokument nehmen, sondern den letzten vor diesem Fahrzeugblock.
        previous_rates = list(tax_pattern.finditer(compact[:m.start()]))
        rate = _dec(previous_rates[-1].group(1)) if previous_rates else Decimal("19")

        total_m = re.search(
            r"TOTAL:\s*(.*?)(?=VEHICLE:|Umsatzsteuerstatistik|Statistica|Distinta|Übertrag|EUR Übertrag|$)",
            body,
            re.I,
        )
        if not total_m:
            continue

        nums = re.findall(r"-?\d{1,3}(?:\.\d{3})*,\d{2,3}|-?\d+,\d{1,3}|-?\d+", total_m.group(1))
        vals = [_dec(x) for x in nums]
        if len(vals) < 3:
            continue

        # DKV-TOTAL-Ende: ... Gesamtwert netto, USt/IVA, Gesamtwert brutto.
        net_amount = vals[-3]
        gross_amount = vals[-1]
        amount, tax, foreign = _amount_and_tax_from_values(net_amount, gross_amount, rate)
        if amount == 0:
            continue

        positions.append({
            "key": vehicle,
            "driver": vehicle,
            "amount": amount,
            "tax": tax,
            "foreign_gross": foreign,
            "source_label": global_prefix,
            "tax_rate": rate,
        })

    if not positions:
        raise RuntimeError("Aus der PDF konnten keine Fahrzeug-/TOTAL-Positionen erkannt werden.")
    return positions

# UI_PREVIEW_PATH_BUKRS_EXPORTNAME_PATCH_V2
# UI-Erweiterung: Buchungskreis, Standardpfade, nummerierte Arbeitsschritte,
# echte Bildvorschau fuer Rechnung/Export und automatischer Exportdateiname.
import datetime as _fm_dt

KST_ASSIGNMENT_DEFAULT_DIR = r"G:\BUC\FM Anwendung\Datenbasen\KST_Zuordnungen_AFI"
AFI_EXPORT_DEFAULT_DIR = r"G:\BUC\FM Anwendung\Dateiausgabe\AFI-Upload-Export"
BOOKING_CIRCLE_OPTIONS = ["IDE", "IDG", "IMS"]


def _fm_downloads_path():
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _fm_safe_name_part(value):
    value = _ascii_umlauts(_clean(value)) if '_ascii_umlauts' in globals() else _clean(value)
    value = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return value or "Unbekannt"


def _fm_short_vendor(path):
    n = _norm(os.path.basename(path))
    for label, needles in [
        ("DKV", ["DKV"]), ("EnBW", ["ENBW", "NBW"]), ("Vodafone", ["VODAFONE"]),
        ("Telekom", ["TELEKOM", "DTAG", "TMOBILE", "T-MOBILE"]), ("VW", ["VW", "VOLKSWAGEN", "LEASING"]),
    ]:
        if any(x in n for x in needles):
            return label
    stem = os.path.splitext(os.path.basename(path or "Rechnung"))[0]
    parts = [x for x in re.split(r"[_\-\s]+", stem) if x]
    return parts[0][:20] if parts else "Rechnung"


def _fm_export_filename(bukrs, invoice_path, cost_desc):
    return f"{_fm_safe_name_part(bukrs or 'IDE')}_{_fm_safe_name_part(_fm_short_vendor(invoice_path))}_{_fm_safe_name_part(cost_desc or 'Kosten')}_{_fm_dt.datetime.now():%Y_%m_%d}.csv"


def _fm_update_export_path(self, force=False):
    if not hasattr(self, 'export_var'):
        return
    current = self.export_var.get().strip() if self.export_var.get() else ""
    invoice = self.invoice_var.get().strip() if hasattr(self, 'invoice_var') else ""
    cost = self.global_prefix_var.get() if hasattr(self, 'global_prefix_var') else "Kosten"
    bukrs = self.booking_circle_var.get() if hasattr(self, 'booking_circle_var') else "IDE"
    new_path = os.path.join(AFI_EXPORT_DEFAULT_DIR, _fm_export_filename(bukrs, invoice, cost))
    if force or not current or current.startswith(AFI_EXPORT_DEFAULT_DIR) or os.path.dirname(current) in ("", _desktop_path()):
        self.export_var.set(new_path)


def _fm_make_placeholder_image(title, lines=None):
    if Image is None or ImageDraw is None:
        return None
    img = Image.new("RGB", (1100, 720), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default() if ImageFont else None
    draw.rectangle((8, 8, 1092, 712), outline="#AAB7C4")
    draw.rectangle((8, 8, 1092, 38), fill="#DDE7F3", outline="#AAB7C4")
    draw.text((18, 18), _clean(title), fill="#1F4E79", font=font)
    y = 58
    for line in (lines or [])[:34]:
        draw.text((18, y), _clean(line)[:150], fill="black", font=font)
        y += 18
    return img


def _fm_table_image_from_rows(title, headers, rows, max_rows=45, max_cols=10):
    if Image is None or ImageDraw is None:
        return None
    headers = list(headers or [])[:max_cols]
    rows = list(rows or [])[:max_rows]
    font = ImageFont.load_default() if ImageFont else None
    cell_h = 23
    widths = []
    for h in headers:
        width_len = min(max([len(_clean(h))] + [len(_clean(r.get(h, ""))) for r in rows]), 36)
        widths.append(max(95, min(250, width_len * 7 + 18)))
    w = max(1100, min(2800, sum(widths) + 2))
    hgt = max(720, (len(rows)+3)*cell_h + 25)
    img = Image.new("RGB", (w, hgt), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((0,0,w,28), fill="#DDE7F3", outline="#AAB7C4")
    draw.text((8,8), _clean(title), fill="#1F4E79", font=font)
    y = 32; x = 0
    for i, h in enumerate(headers):
        draw.rectangle((x,y,x+widths[i],y+cell_h), fill="#EAF1F8", outline="#AAB7C4")
        draw.text((x+4,y+5), _clean(h)[:36], fill="black", font=font)
        x += widths[i]
    y += cell_h
    for ridx, row in enumerate(rows):
        x = 0; fill = "#FFFFFF" if ridx % 2 == 0 else "#F7F9FB"
        for i, h in enumerate(headers):
            draw.rectangle((x,y,x+widths[i],y+cell_h), fill=fill, outline="#D6DEE8")
            draw.text((x+4,y+5), _clean(row.get(h, ""))[:36], fill="black", font=font)
            x += widths[i]
        y += cell_h
    return img


def _fm_pdf_first_page_image(path):
    if Image is None:
        return None
    try:
        import fitz
        doc = fitz.open(path)
        page = doc[0]
        zoom = min(2.0, 1400 / max(1, page.rect.width))
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return img
    except Exception:
        return None


def _fm_invoice_image(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return _fm_pdf_first_page_image(path) or _fm_make_placeholder_image(os.path.basename(path), ["PDF konnte nicht als Bild gerendert werden."])
    if ext in (".csv", ".xlsx", ".xls", ".xlsm"):
        try:
            headers, rows = _read_table_file(path)
            return _fm_table_image_from_rows(os.path.basename(path), headers, rows)
        except Exception as exc:
            return _fm_make_placeholder_image(os.path.basename(path), [f"Tabellenbild konnte nicht erstellt werden: {exc}"])
    if ext == ".docx":
        try:
            lines = _extract_docx_text(path).splitlines()
        except Exception as exc:
            lines = [f"DOCX konnte nicht gelesen werden: {exc}"]
        return _fm_make_placeholder_image(os.path.basename(path), lines)
    return _fm_make_placeholder_image(os.path.basename(path), ["Keine Vorschau verfuegbar."])


def _fm_export_image(path):
    if path and os.path.isfile(path):
        try:
            headers, rows = _read_csv(path)
            return _fm_table_image_from_rows(os.path.basename(path), headers, rows)
        except Exception as exc:
            return _fm_make_placeholder_image("AFI-Upload-Export", [f"Exportvorschau konnte nicht gelesen werden: {exc}"])
    return _fm_make_placeholder_image("AFI-Upload-Export", ["Noch kein Export erstellt.", "Nach Erstellung wird die AFI-CSV hier als Bildvorschau angezeigt."])


def _fm_set_image(frame, img):
    for child in frame.winfo_children():
        child.destroy()
    if img is None or ImageTk is None:
        tk.Label(frame, text="Bildvorschau nicht verfuegbar.", bg="white").pack(fill="both", expand=True)
        return
    canvas = tk.Canvas(frame, bg="white", highlightthickness=0)
    canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
    state = {"img": img, "zoom": 1.0, "offset": [0,0], "ref": None, "drag": None}
    def render():
        cw = max(1, canvas.winfo_width()); ch = max(1, canvas.winfo_height())
        bw, bh = state["img"].size
        zw, zh = max(1, int(bw*state["zoom"])), max(1, int(bh*state["zoom"]))
        pic = state["img"].resize((zw, zh))
        if zw <= cw: state["offset"][0] = (cw-zw)//2
        else: state["offset"][0] = min(0, max(cw-zw, state["offset"][0]))
        if zh <= ch: state["offset"][1] = (ch-zh)//2
        else: state["offset"][1] = min(0, max(ch-zh, state["offset"][1]))
        state["ref"] = ImageTk.PhotoImage(pic)
        canvas.delete("all")
        canvas.create_image(state["offset"][0], state["offset"][1], image=state["ref"], anchor="nw")
    def wheel(e):
        old = state["zoom"]
        state["zoom"] = max(0.25, min(4.0, state["zoom"] * (1.1 if e.delta > 0 else 0.9)))
        if old:
            state["offset"][0] = int(e.x - (e.x-state["offset"][0]) * state["zoom"] / old)
            state["offset"][1] = int(e.y - (e.y-state["offset"][1]) * state["zoom"] / old)
        render(); return "break"
    def press(e):
        state["drag"] = (e.x, e.y, state["offset"][0], state["offset"][1]); return "break"
    def drag(e):
        sx, sy, ox, oy = state["drag"] or (e.x,e.y,state["offset"][0],state["offset"][1])
        state["offset"] = [ox+e.x-sx, oy+e.y-sy]
        render(); return "break"
    canvas.bind("<Configure>", lambda e: render())
    canvas.bind("<MouseWheel>", wheel)
    canvas.bind("<ButtonPress-1>", press)
    canvas.bind("<B1-Motion>", drag)
    frame._fm_image_ref = state
    render()


def _fm_browse(self, label, var, save=False, role=""):
    if save:
        path = filedialog.asksaveasfilename(title=label, initialdir=os.path.dirname(var.get()) or AFI_EXPORT_DEFAULT_DIR, initialfile=os.path.basename(var.get()), defaultextension=".csv", filetypes=[("CSV", "*.csv")])
    else:
        start = var.get() if os.path.isdir(var.get()) else os.path.dirname(var.get())
        path = filedialog.askopenfilename(title=label, initialdir=start or None, filetypes=[("Dokumente", "*.csv *.xlsx *.xls *.xlsm *.pdf *.docx"), ("Alle Dateien", "*.*")])
    if path:
        var.set(path)
        if role == "invoice":
            _fm_update_export_path(self, force=True)
            self.load_preview(path)


def _fm_build_left(self, parent):
    parent.columnconfigure(1, weight=1)
    self.booking_circle_var = tk.StringVar(value="IDE")
    self.template_var = tk.StringVar(value=KST_ASSIGNMENT_DEFAULT_DIR)
    self.invoice_var = tk.StringVar(value=_fm_downloads_path())
    self.export_var = tk.StringVar()
    self.global_prefix_var = tk.StringVar(value="Tanken Strom")
    self.status_var = tk.StringVar(value="Bitte Rechnung und KST-Zuordnungsdokument auswaehlen und Rechnung analysieren.")
    self.suggestion_var = tk.StringVar(value="")
    _fm_update_export_path(self, force=True)

    def path_row(r, label, var, save=False, role=""):
        tk.Label(parent, text=label, bg=self.bg, font=self.font_small).grid(row=r, column=0, sticky="w", pady=3)
        tk.Entry(parent, textvariable=var, font=self.font_small).grid(row=r, column=1, sticky="ew", padx=4, pady=3)
        tk.Button(parent, text="…", command=lambda: _fm_browse(self, label, var, save, role), font=self.font_small, width=3).grid(row=r, column=2, pady=3)

    tk.Label(parent, text="Buchungskreis", bg=self.bg, font=self.font_small).grid(row=0, column=0, sticky="w", pady=3)
    cb_bukrs = ttk.Combobox(parent, textvariable=self.booking_circle_var, values=BOOKING_CIRCLE_OPTIONS, state="readonly", font=self.font_small)
    cb_bukrs.grid(row=0, column=1, sticky="ew", padx=4, pady=3)
    cb_bukrs.bind("<<ComboboxSelected>>", lambda e: _fm_update_export_path(self, force=True))
    path_row(1, "KST-Zuordnungsdokument", self.template_var, False, "template")
    path_row(2, "Rechnung / Dokument", self.invoice_var, False, "invoice")
    path_row(3, "Export-CSV", self.export_var, True, "export")
    tk.Label(parent, text="Kostenbeschreibung", bg=self.bg, font=self.font_small).grid(row=4, column=0, sticky="w", pady=3)
    cb_cost = ttk.Combobox(parent, textvariable=self.global_prefix_var, values=COST_TYPE_OPTIONS, state="normal", font=self.font_small)
    cb_cost.grid(row=4, column=1, sticky="ew", padx=4, pady=3)
    cb_cost.bind("<<ComboboxSelected>>", lambda e: (_fm_update_export_path(self, True), self.on_mapping_changed()))
    cb_cost.bind("<FocusOut>", lambda e: (_fm_update_export_path(self, True), self.on_mapping_changed()))
    actions = tk.Frame(parent, bg=self.bg); actions.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(6,3)); actions.columnconfigure(6, weight=1)
    tk.Label(actions, text="1.", bg=self.bg, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=(0,4))
    self.analyze_btn = tk.Button(actions, text="Rechnung analysieren", command=self.analyze_invoice, font=self.font_small); self.analyze_btn.grid(row=0, column=1)
    tk.Label(actions, text="2.", bg=self.bg, font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=(14,4))
    self.add_source_btn = tk.Button(actions, text="+ Berechnungsquelle", command=self.add_empty_source, font=self.font_small); self.add_source_btn.grid(row=0, column=3)
    tk.Button(actions, text="AFI-Upload-Datei erstellen", command=self.run_export, font=("Segoe UI", 10, "bold"), bg="#CFEAD6", activebackground="#BDE3C7").grid(row=0, column=7, sticky="e")
    tk.Label(parent, textvariable=self.suggestion_var, bg=self.bg, fg="#7A4B00", font=self.font_small, wraplength=520, justify="left").grid(row=6, column=0, columnspan=3, sticky="ew")
    self.sources_canvas = tk.Canvas(parent, bg=self.bg, highlightthickness=0)
    self.sources_inner = tk.Frame(self.sources_canvas, bg=self.bg)
    yscroll = ttk.Scrollbar(parent, orient="vertical", command=self.sources_canvas.yview)
    self.sources_canvas.configure(yscrollcommand=yscroll.set)
    self.sources_canvas.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(6,0)); yscroll.grid(row=7, column=2, sticky="ns", pady=(6,0)); parent.rowconfigure(7, weight=1)
    self.sources_window = self.sources_canvas.create_window((0,0), window=self.sources_inner, anchor="nw")
    self.sources_canvas.bind("<Configure>", lambda e: self.sources_canvas.itemconfigure(self.sources_window, width=max(100, e.width-4)))
    self.sources_inner.bind("<Configure>", lambda e: self.sources_canvas.configure(scrollregion=self.sources_canvas.bbox("all")))
    tk.Label(parent, textvariable=self.status_var, bg=self.bg, font=self.font_small, wraplength=540, justify="left").grid(row=8, column=0, columnspan=3, sticky="ew", pady=(6,0))


def _fm_build_right(self, parent):
    parent.rowconfigure(1, weight=1); parent.columnconfigure(0, weight=1)
    tk.Label(parent, text="Dokumentenvorschau", bg=self.bg, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
    self.preview_notebook = ttk.Notebook(parent); self.preview_notebook.grid(row=1, column=0, sticky="nsew")
    self.invoice_preview_frame = tk.Frame(self.preview_notebook, bg="white"); self.export_preview_frame = tk.Frame(self.preview_notebook, bg="white")
    self.preview_notebook.add(self.invoice_preview_frame, text="Vorschau Rechnung"); self.preview_notebook.add(self.export_preview_frame, text="AFI-Upload-Export")
    self.preview_frame = self.invoice_preview_frame
    self.highlight_var = tk.StringVar(value="")
    tk.Label(parent, textvariable=self.highlight_var, bg="#FFF4C2", anchor="w", font=self.font_small).grid(row=2, column=0, sticky="ew", pady=(4,0))
    self.load_export_preview("")


def _fm_load_preview(self, path):
    self.preview_path = path
    _fm_set_image(self.invoice_preview_frame if hasattr(self, 'invoice_preview_frame') else self.preview_frame, _fm_invoice_image(path))


def _fm_load_export_preview(self, path=""):
    _fm_set_image(self.export_preview_frame if hasattr(self, 'export_preview_frame') else self.preview_frame, _fm_export_image(path))


def _fm_analyze_invoice(self):
    path = self.invoice_var.get().strip()
    if not os.path.isfile(path):
        messagebox.showwarning(MODULE_TITLE, "Bitte eine gueltige Rechnung auswaehlen."); return
    try:
        self.clear_sources(); ext = os.path.splitext(path)[1].lower(); self.load_preview(path); _fm_update_export_path(self, True)
        if ext == ".pdf":
            self.headers, self.rows = ["PDF"], []
            self.suggestion_var.set("PDF erkannt: Berechnungsquellen sind nicht erforderlich. Die Positionen werden aus Fahrzeug-/TOTAL-Bloecken gelesen.")
            self.status_var.set("PDF-Rechnung analysiert. Bitte Kostenbeschreibung und KST-Zuordnungsdokument pruefen.")
            if hasattr(self, 'add_source_btn'): self.add_source_btn.configure(state="disabled")
            return
        if hasattr(self, 'add_source_btn'): self.add_source_btn.configure(state="normal")
        self.headers, self.rows = _read_table_file(path)
        suggestions = suggested_sources(self.headers); self.add_source(suggestions[0])
        if len(suggestions) > 1:
            self.suggestion_var.set("Weitere moegliche Berechnungsquellen erkannt: " + ", ".join(s.get("label", "") for s in suggestions[1:]) + ". Bei Bedarf ueber '+ Berechnungsquelle' hinzufuegen.")
        else: self.suggestion_var.set("")
        self.status_var.set("Rechnung analysiert. Bitte Berechnungsquelle pruefen/ergaenzen.")
    except Exception as exc:
        messagebox.showerror(MODULE_TITLE, str(exc))


def _fm_add_empty_source(self):
    if hasattr(self, 'add_source_btn') and str(self.add_source_btn.cget('state')) == 'disabled': return
    self.add_source(default_source(len(self.sources)+1, self.headers))


def _fm_on_mapping_changed(self):
    try: _fm_update_export_path(self, True)
    except Exception: pass
    try: self.update_footer(); self.update_highlight()
    except Exception: pass


def _fm_run_export(self):
    template_path = self.template_var.get().strip(); invoice_path = self.invoice_var.get().strip(); _fm_update_export_path(self, False); export_path = self.export_var.get().strip()
    if not os.path.isfile(template_path): messagebox.showwarning(MODULE_TITLE, "Bitte ein gueltiges KST-Zuordnungsdokument auswaehlen."); return
    if not os.path.isfile(invoice_path): messagebox.showwarning(MODULE_TITLE, "Bitte eine gueltige Rechnung auswaehlen."); return
    if not export_path.lower().endswith(".csv"): export_path += ".csv"; self.export_var.set(export_path)
    config = {"global_prefix": self.global_prefix_var.get(), "sources": [s.get() for s in self.sources], "booking_circle": self.booking_circle_var.get() if hasattr(self, 'booking_circle_var') else "IDE"}
    self.status_var.set("Export laeuft…")
    def worker():
        try:
            result = create_supplier_upload_csv(template_path, invoice_path, export_path, config)
            def done():
                self.status_var.set(f"Export erstellt: {result['rows']} Zeilen -> {result['export_path']} | Netto: {result['export_net_total']} | Fahrer: {result['unique_drivers']} | Kennzeichen: {result['unique_keys']}")
                self.load_export_preview(result.get('export_path', export_path))
                if hasattr(self, 'preview_notebook'): self.preview_notebook.select(self.export_preview_frame)
                critical=[]
                if result.get("missing_template"): critical.append("Keine eindeutige Kontierung gefunden:\n"+"\n".join(result["missing_template"][:40]))
                if result.get("empty_assignment"): critical.append("Zeilen ohne Fahrer/Schluessel:\n"+"\n".join(result["empty_assignment"][:30]))
                if result.get("unknown_tax"): critical.append("Nicht eindeutig erkannte Steuersaetze:\n"+"\n".join(result["unknown_tax"][:30]))
                if result.get("foreign_gross"): critical.append("Abweichende/auslaendische Steuersaetze als Brutto mit V0 gebucht:\n"+"\n".join(result["foreign_gross"][:30]))
                if result.get("enbw_blocking_split"): critical.append("EnBW-Blockiergebuehren wurden nach IDE/IDG separat ausgewiesen:\n"+"\n".join(result["enbw_blocking_split"][:30]))
                if critical: messagebox.showwarning(MODULE_TITLE, "\n\n".join(critical))
                self._show_export_done_dialog(result)
            self.app.root.after(0, done)
        except Exception as exc:
            self.app.root.after(0, lambda: (self.status_var.set("Fehler beim Export."), messagebox.showerror(MODULE_TITLE, str(exc))))
    threading.Thread(target=worker, daemon=True).start()

SupplierUploadUI._build_left = _fm_build_left
SupplierUploadUI._build_right = _fm_build_right
SupplierUploadUI.load_preview = _fm_load_preview
SupplierUploadUI.load_export_preview = _fm_load_export_preview
SupplierUploadUI.analyze_invoice = _fm_analyze_invoice
SupplierUploadUI.add_empty_source = _fm_add_empty_source
SupplierUploadUI.on_mapping_changed = _fm_on_mapping_changed
SupplierUploadUI.run_export = _fm_run_export

# TEXT_COST_DESCRIPTION_PATCH_V1
# Fachregel: In der AFI-Spalte TEXT steht die ausgewaehlte Kostenbeschreibung,
# nicht der Spalten-/Berechnungsquellenname. Ausnahme: Blockiergebuehren bleiben separat ausgewiesen.
def _apply_text_cost_description_rule(export_path, config):
    if not export_path or not os.path.isfile(export_path):
        return
    global_prefix = _clean((config or {}).get("global_prefix", "")) or "Tanken Strom"
    sources = (config or {}).get("sources", []) or []
    prefixes = []
    for src in sources:
        label = _clean(src.get("label") or src.get("net") or "")
        net = _clean(src.get("net") or "")
        for candidate in (label, net):
            if candidate and candidate not in prefixes and _norm(candidate) != _norm(global_prefix):
                prefixes.append(candidate)
    # Laengere Praefixe zuerst, damit spezifische Spaltennamen vor kurzen Teilnamen ersetzt werden.
    prefixes.sort(key=len, reverse=True)
    with open(export_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    if "TEXT" not in fieldnames:
        return
    for row in rows:
        text_value = _clean(row.get("TEXT", ""))
        if not text_value:
            continue
        # Blockiergebuehren/Blockiergebühren sind fachlich eigene Sammelzeilen und bleiben unveraendert.
        if "BLOCKIERGEBUEHR" in _norm(text_value) or "BLOCKIERGEBUEHREN" in _norm(text_value):
            row["TEXT"] = _ascii_umlauts(text_value) if '_ascii_umlauts' in globals() else text_value
            continue
        replaced = False
        for prefix in prefixes:
            if _norm(text_value) == _norm(prefix) or text_value.startswith(prefix + " "):
                suffix = text_value[len(prefix):].strip()
                row["TEXT"] = _clean((global_prefix + " " + suffix).strip())
                replaced = True
                break
        if not replaced:
            # Falls kein expliziter Quellenpraefix gefunden wurde, aber der TEXT noch nicht mit der Kostenbeschreibung beginnt,
            # wird kein aggressives Abschneiden vorgenommen. So bleiben Sonder-/Fallbacktexte stabil.
            row["TEXT"] = text_value
        if '_ascii_umlauts' in globals():
            row["TEXT"] = _ascii_umlauts(row["TEXT"])
    with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

_create_supplier_upload_csv_before_text_cost_patch = create_supplier_upload_csv

def create_supplier_upload_csv(assignment_path, invoice_path, export_path, config):
    result = _create_supplier_upload_csv_before_text_cost_patch(assignment_path, invoice_path, export_path, config)
    try:
        _apply_text_cost_description_rule(export_path, config)
    except Exception:
        # Export nicht blockieren, falls reine TEXT-Nachbearbeitung fehlschlaegt.
        pass
    return result

