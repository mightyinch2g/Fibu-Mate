
import csv
import os
import re
import threading
import unicodedata
from collections import OrderedDict, defaultdict
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import tkinter as tk
from tkinter import filedialog, messagebox

DEFAULT_TEMPLATE_PATH = r"G:\BUC\Sachkonten-Kreditoren\Team Hauptbuch - Einzelordner\Vorlagen Jäger\Allg. Vorlagen\Kontierungsvorlagen\Upload-Dateien AFI\Vorlage Upload-Datei_ENBW.csv"
MODULE_TITLE = "EnBW - Strom-Tanken Upload-Erstellung"
UPLOAD_COLUMNS = ["TEXT", "PRICE", "PRICE_UNIT", "QUANTITY", "UNIT", "NET_VALUE", "TAX_CODE", "GL_ACCOUNT", "COSTCENTER", "ORDERID"]
TAX_ORDER = {"VD": 0, "V2": 1, "V0": 2, "VX": 9}


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
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                except Exception:
                    dialect = csv.excel
                    dialect.delimiter = ";"
                reader = csv.DictReader(f, dialect=dialect)
                rows = list(reader)
                fieldnames = [str(x or "").replace("\ufeff", "").strip() for x in (reader.fieldnames or [])]
                fixed = []
                for row in rows:
                    fixed.append({str(k or "").replace("\ufeff", "").strip(): v for k, v in row.items()})
                return fieldnames, fixed
        except Exception as exc:
            last = exc
    raise RuntimeError(f"CSV konnte nicht gelesen werden: {last}")


def _dec(value):
    """Liest Beträge mit allen verfügbaren Nachkommastellen ein.
    Gerundet wird erst unmittelbar beim CSV-Export bzw. bei reinen Anzeige-/Vergleichswerten.
    """
    s = _clean(value)
    if not s:
        return Decimal("0.00")
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0.00")


def _fmt(value):
    d = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}".replace(".", ",")


def _find_col(headers, preferred_names, fallback_index=None):
    normalized = {_norm(h): h for h in headers}
    for name in preferred_names:
        key = _norm(name)
        if key in normalized:
            return normalized[key]
    if fallback_index is not None and 0 <= fallback_index < len(headers):
        return headers[fallback_index]
    return None


def _tax_code(net, vat):
    net = Decimal(net)
    vat = Decimal(vat)
    if net == 0:
        return "V0" if vat == 0 else "VX"
    rate = (vat / net * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if abs(rate - Decimal("19.00")) <= Decimal("0.50"):
        return "VD"
    if abs(rate - Decimal("7.00")) <= Decimal("0.50"):
        return "V2"
    if abs(rate - Decimal("0.00")) <= Decimal("0.50"):
        return "V0"
    return "VX"


def _tax_code_from_explicit_rate(value):
    rate = _dec(value)
    if abs(rate - Decimal("19.00")) <= Decimal("0.50"):
        return "VD"
    if abs(rate - Decimal("7.00")) <= Decimal("0.50"):
        return "V2"
    if abs(rate - Decimal("0.00")) <= Decimal("0.50"):
        return "V0"
    return ""


def _driver_from_invoice(row, first_col, last_col):
    first = _clean(row.get(first_col, ""))
    last = _clean(row.get(last_col, ""))
    return _clean(f"{first} {last}")


def _plate_variants(value):
    """Erzeugt robuste Kennzeichen-Schlüssel.
    Exakte Kennzeichen bleiben führend; Fallbacks werden nur bei eindeutiger Zuordnung verwendet.
    Die Zwischenkennung wird bewusst nur entfernt, wenn sie exakt 'I' ist
    (z. B. HN-I 5454E <-> HN-5454E). Andere Gruppen wie SK/JN/X bleiben erhalten.
    """
    raw = _clean(value).upper()
    n = _norm(raw)
    variants = []
    if n:
        variants.append(n)
    m = re.match(r"^([A-Z]{1,3})(I)(\d.*)$", n)
    if m:
        variants.append(m.group(1) + m.group(3))
    m2 = re.match(r"^([A-ZÄÖÜ]{1,3})[-\s]+(I)[-\s]+(\d.*)$", raw)
    if m2:
        variants.append(_norm(m2.group(1) + m2.group(3)))
    more = []
    for v in variants:
        if v.endswith("E"):
            more.append(v[:-1])
        else:
            more.append(v + "E")
    variants.extend(more)
    out = []
    for v in variants:
        if v and v not in out:
            out.append(v)
    return out


def _split_template_text(text):
    """Zerlegt 'Tanken Strom <Kennzeichen> <Fahrer>' robust in Kennzeichen/Fahrer."""
    body = re.sub(r"^Tanken\s+Strom\s+", "", _clean(text), flags=re.I).strip()
    tokens = body.split()
    if not tokens:
        return "", ""
    plate_tokens = []
    stop_index = None
    for idx, token in enumerate(tokens):
        plate_tokens.append(token)
        if any(ch.isdigit() for ch in token):
            stop_index = idx
            break
    if stop_index is None:
        return tokens[0], " ".join(tokens[1:]).strip()
    return " ".join(plate_tokens).strip(), " ".join(tokens[stop_index + 1:]).strip()


def _load_template_map(template_path, invoice_plates):
    _, rows = _read_csv(template_path)
    exact_map = {}
    variant_index = defaultdict(list)
    driver_index = defaultdict(list)
    duplicates = set()
    for row in rows:
        text = _clean(row.get("TEXT", ""))
        template_plate, driver_template = _split_template_text(text)
        exact_key = _norm(template_plate)
        if not exact_key:
            continue
        info = {
            "TEXT": text,
            "template_plate": _clean(template_plate),
            "template_driver": _clean(driver_template),
            "GL_ACCOUNT": _clean(row.get("GL_ACCOUNT", "")),
            "COSTCENTER": _clean(row.get("COSTCENTER", "")),
            "ORDERID": _clean(row.get("ORDERID", "")),
            "matched_key": exact_key,
        }
        if exact_key in exact_map:
            duplicates.add(exact_key)
        exact_map[exact_key] = info
        for variant in _plate_variants(template_plate):
            variant_index[variant].append(info)
        if driver_template:
            full_key = _norm(driver_template)
            if full_key:
                driver_index[full_key].append(info)
            parts = _clean(driver_template).split()
            if parts:
                driver_index[_norm(parts[-1])].append(info)
    return exact_map, variant_index, driver_index, duplicates


def _resolve_template_info(plate, exact_map, variant_index):
    pnorm = _norm(plate)
    if pnorm in exact_map:
        return exact_map[pnorm], None
    for variant in _plate_variants(plate):
        candidates = variant_index.get(variant, [])
        unique = []
        seen = set()
        for c in candidates:
            key = c.get("matched_key") or _norm(c.get("template_plate", ""))
            if key not in seen:
                unique.append(c)
                seen.add(key)
        if len(unique) == 1:
            info = dict(unique[0])
            return info, f"{plate}: robust zugeordnet zu Vorlage-Kennzeichen {info.get('template_plate', '')}"
        if len(unique) > 1:
            return None, f"{plate}: keine eindeutige robuste Kennzeichen-Zuordnung ({len(unique)} Treffer in Vorlage)"
    return None, None


def _driver_template_hits(driver, driver_index):
    """Findet eindeutige Vorlagenzeilen zum Fahrer: zuerst voller Name, dann Nachname."""
    keys = []
    full_key = _norm(driver)
    if full_key:
        keys.append(full_key)
    parts = _clean(driver).split()
    if parts:
        last_key = _norm(parts[-1])
        if last_key and last_key not in keys:
            keys.append(last_key)
    hits = []
    seen = set()
    for key in keys:
        for hit in driver_index.get(key, []):
            hit_key = hit.get("matched_key") or _norm(hit.get("template_plate", ""))
            if hit_key and hit_key not in seen:
                hits.append(hit)
                seen.add(hit_key)
    return hits


def _first_existing_value(row, columns):
    for col in columns:
        if col and _clean(row.get(col, "")):
            return _clean(row.get(col, ""))
    return ""


def create_upload_csv(template_path, invoice_path, export_path):
    headers, inv_rows = _read_csv(invoice_path)
    col_net = _find_col(headers, ["Energiekosten Netto (Euro)"], 37)       # AL
    col_vat = _find_col(headers, ["Energiekosten Mehrwertsteuerbetrag (Euro)"], 38)  # AM
    col_tax_rate = _find_col(headers, ["Mehrwertsteuersatz"], 7)
    col_fee = _find_col(headers, ["Grundgebühr je Nutzer Netto (Euro)"], 49)  # AX bevorzugt per Name
    col_plate = _find_col(headers, ["Fahrzeug Kennzeichen"], 54)          # BC
    col_last = _find_col(headers, ["Fahrer Nachname"], 52)                # BA
    col_first = _find_col(headers, ["Fahrer Vorname"], 53)                # BB
    col_fee_gross = _find_col(headers, ["Grundgebühr je Nutzer Brutto (Euro)"], 48)
    col_block_net = _find_col(headers, ["Blockiergebühr Netto (Euro)"], 33)
    col_block_vat = _find_col(headers, ["Blockiergebühr Mehrwertsteuerbetrag (Euro)"], 34)
    col_fee_rfid = _find_col(headers, ["Identifikation Grundgebühr je Nutzer (RFID)"], 46)
    col_fee_remote = _find_col(headers, ["Identifikation Grundgebühr je Nutzer (Remote)"], 47)
    col_profile = _find_col(headers, ["Profilname"], 61)
    col_driver_label = _find_col(headers, ["Fahrer Bezeichnung"], 51)

    required = [("Nettobetrag", col_net), ("MwSt-Betrag", col_vat), ("Nachname", col_last), ("Vorname", col_first)]
    missing = [name for name, col in required if not col]
    if missing:
        raise RuntimeError("Pflichtspalten fehlen in der Rechnung: " + ", ".join(missing))

    invoice_plates = []
    for r in inv_rows:
        for candidate_col in [col_plate, col_fee_rfid, col_fee_remote, col_profile, col_driver_label]:
            value = _clean(r.get(candidate_col, "")) if candidate_col else ""
            if value:
                invoice_plates.append(value)
    template_map, template_variant_index, template_driver_index, duplicate_template_plates = _load_template_map(template_path, invoice_plates)

    groups = OrderedDict()
    plate_order = []
    driver_order = defaultdict(list)
    warnings_name = []
    warnings_missing = OrderedDict()
    warnings_tax = []
    warnings_plate_fuzzy = []
    warnings_driver_other_plate = []
    warnings_name_fallback = []
    warnings_duplicate_fee = []
    warnings_block_fee = []
    warnings_rounding_adjustment = []
    fee_seen_by_name = set()
    invoice_net_raw_total = Decimal("0.00")

    def ensure_group(plate, driver, tax):
        pnorm = _norm(plate)
        dnorm = _norm(driver)
        key = (pnorm, dnorm, tax)
        if pnorm not in plate_order:
            plate_order.append(pnorm)
        if dnorm not in driver_order[pnorm]:
            driver_order[pnorm].append(dnorm)
        if key not in groups:
            groups[key] = {"plate": plate, "driver": driver, "tax": tax, "amount": Decimal("0.00")}
        return groups[key]

    for r in inv_rows:
        raw_plate = _clean(r.get(col_plate, "")) if col_plate else ""
        driver = _driver_from_invoice(r, col_first, col_last)
        fallback_identifier = _first_existing_value(r, [col_fee_rfid, col_fee_remote, col_profile, col_driver_label])
        if not driver:
            driver = _first_existing_value(r, [col_profile, col_fee_remote, col_driver_label, col_fee_rfid])
        plate = raw_plate or fallback_identifier
        if not plate and not driver:
            continue

        net = _dec(r.get(col_net, ""))
        vat = _dec(r.get(col_vat, ""))
        if net != 0:
            invoice_net_raw_total += net
            if not plate:
                plate = driver
            tax = _tax_code(net, vat)
            if tax == "VX" and col_tax_rate:
                explicit_tax = _tax_code_from_explicit_rate(r.get(col_tax_rate, ""))
                if explicit_tax:
                    tax = explicit_tax
            if tax == "VX":
                warnings_tax.append(f"{plate} / {driver}: Netto {_fmt(net)}, MwSt {_fmt(vat)}")
            ensure_group(plate, driver, tax)["amount"] += net

        # Blockiergebühren sind eigene Rechnungsbeträge und werden zusätzlich einmalig dem Fahrzeug/Fahrer zugerechnet.
        block_net = _dec(r.get(col_block_net, "")) if col_block_net else Decimal("0.00")
        block_vat = _dec(r.get(col_block_vat, "")) if col_block_vat else Decimal("0.00")
        if block_net != 0:
            invoice_net_raw_total += block_net
            if not plate:
                plate = driver or fallback_identifier
            if not driver:
                driver = plate
            block_tax = _tax_code(block_net, block_vat)
            if block_tax == "VX" and col_tax_rate:
                explicit_tax = _tax_code_from_explicit_rate(r.get(col_tax_rate, ""))
                if explicit_tax:
                    block_tax = explicit_tax
            if block_tax == "VX":
                warnings_tax.append(f"{plate} / {driver}: Blockiergebühr Netto {_fmt(block_net)}, MwSt {_fmt(block_vat)}")
            ensure_group(plate, driver, block_tax)["amount"] += block_net
            msg = f"{plate} / {driver}: Blockiergebühr Netto {_fmt(block_net)} zugeordnet"
            if msg not in warnings_block_fee:
                warnings_block_fee.append(msg)

        if col_fee:
            fee = _dec(r.get(col_fee, ""))
            # Falls Netto leer, aber Brutto vorhanden: Grundgebühr immer 19%; Netto aus Brutto ableiten.
            if fee == 0 and col_fee_gross:
                gross = _dec(r.get(col_fee_gross, ""))
                if gross != 0:
                    fee = (gross / Decimal("1.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if fee != 0:
                if not plate:
                    plate = driver or fallback_identifier
                if not driver:
                    driver = plate
                fee_name_key = _norm(driver or plate)
                if fee_name_key in fee_seen_by_name:
                    msg = f"{driver or plate}: Grundgebühr mehrfach in Rechnung gefunden; weitere Grundgebühr nicht erneut zugewiesen"
                    if msg not in warnings_duplicate_fee:
                        warnings_duplicate_fee.append(msg)
                else:
                    fee_seen_by_name.add(fee_name_key)
                    invoice_net_raw_total += fee
                    ensure_group(plate, driver, "VD")["amount"] += fee

    # Template-/Namensprüfung je Kennzeichen/Fahrer-Kombination
    resolved_template_cache = {}
    for g in groups.values():
        pnorm = _norm(g["plate"])
        info, fuzzy_msg = _resolve_template_info(g["plate"], template_map, template_variant_index)
        resolved_template_cache[pnorm] = info or {}
        if fuzzy_msg and fuzzy_msg not in warnings_plate_fuzzy:
            warnings_plate_fuzzy.append(fuzzy_msg)

        if not info:
            warnings_missing[pnorm] = g["plate"]
            driver_hits = _driver_template_hits(g["driver"], template_driver_index)
            for hit in driver_hits:
                hit_plate = hit.get("template_plate", "")
                if _norm(hit_plate) != pnorm:
                    msg = f"{g['driver']}: in Vorlage auf {hit_plate} geführt; Rechnung meldet {g['plate']}"
                    if msg not in warnings_driver_other_plate:
                        warnings_driver_other_plate.append(msg)
            if len(driver_hits) == 1:
                fallback_info = dict(driver_hits[0])
                fallback_info["match_type"] = "Name"
                resolved_template_cache[pnorm] = fallback_info
                msg = f"{g['plate']}: Kontierung per Fahrername '{g['driver']}' aus Vorlage-Kennzeichen {fallback_info.get('template_plate', '')} übernommen"
                if msg not in warnings_name_fallback:
                    warnings_name_fallback.append(msg)
            elif len(driver_hits) > 1:
                msg = f"{g['plate']} / {g['driver']}: keine eindeutige Namenszuordnung ({len(driver_hits)} Vorlage-Treffer)"
                if msg not in warnings_name_fallback:
                    warnings_name_fallback.append(msg)
            continue

        tdriver = _clean(info.get("template_driver", ""))
        invoice_driver_norm = _norm(g["driver"])
        invoice_last_norm = _norm(_clean(g["driver"]).split()[-1] if _clean(g["driver"]).split() else "")
        template_driver_norm = _norm(tdriver)
        if tdriver and template_driver_norm not in (invoice_driver_norm, invoice_last_norm):
            msg = f"{g['plate']}: Rechnung = {g['driver']} | Vorlage = {tdriver}"
            if msg not in warnings_name:
                warnings_name.append(msg)

    ordered_groups = sorted(
        [g for g in groups.values() if g["amount"] != 0],
        key=lambda g: (
            plate_order.index(_norm(g["plate"])) if _norm(g["plate"]) in plate_order else 999999,
            driver_order[_norm(g["plate"])].index(_norm(g["driver"])) if _norm(g["driver"]) in driver_order[_norm(g["plate"])] else 999999,
            TAX_ORDER.get(g["tax"], 9),
        ),
    )

    # Finaler Netto-Rundungsausgleich: intern wurde mit allen verfügbaren Nachkommastellen gerechnet.
    # Da die CSV nur 2 Nachkommastellen enthalten darf, wird die Summe der gerundeten Exportzeilen
    # auf die gerundete Rechnungs-Netto-Gesamtsumme abgestimmt.
    target_net_total = invoice_net_raw_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    export_net_before_adjustment = sum(g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for g in ordered_groups if g["amount"] != 0)
    net_adjustment = target_net_total - export_net_before_adjustment
    if net_adjustment != Decimal("0.00") and ordered_groups:
        adjustment_candidates = [g for g in ordered_groups if g.get("tax") == "VD" and g.get("amount", Decimal("0.00")) != 0]
        if not adjustment_candidates:
            adjustment_candidates = [g for g in ordered_groups if g.get("amount", Decimal("0.00")) != 0]
        if adjustment_candidates:
            target_group = max(adjustment_candidates, key=lambda g: abs(g.get("amount", Decimal("0.00"))))
            before_amount = target_group["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            target_group["amount"] += net_adjustment
            after_amount = target_group["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            warnings_rounding_adjustment.append(
                f"Netto-Rundungsausgleich {net_adjustment:+.2f} EUR auf {target_group.get('plate', '')} / {target_group.get('driver', '')}: {before_amount:.2f} -> {after_amount:.2f}".replace(".", ",")
            )

    os.makedirs(os.path.dirname(os.path.abspath(export_path)) or ".", exist_ok=True)
    with open(export_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=UPLOAD_COLUMNS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for g in ordered_groups:
            info = resolved_template_cache.get(_norm(g["plate"]), {})
            if not info:
                info, _ = _resolve_template_info(g["plate"], template_map, template_variant_index)
                info = info or {}
            amount = g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            text_value = f"Tanken Strom {g['plate']}" if _norm(g.get("plate", "")) == _norm(g.get("driver", "")) else f"Tanken Strom {g['plate']} {g['driver']}"
            writer.writerow({
                "TEXT": text_value,
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

    export_net_total = sum(g["amount"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for g in ordered_groups if g["amount"] != 0)
    return {
        "rows": len(ordered_groups),
        "export_path": export_path,
        "invoice_net_raw_total": _fmt(invoice_net_raw_total),
        "export_net_total": _fmt(export_net_total),
        "net_rounding_difference": _fmt(export_net_total - invoice_net_raw_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "net_rounding_adjustments": warnings_rounding_adjustment,
        "name_differences": warnings_name,
        "missing_plates": list(warnings_missing.values()),
        "unknown_tax": warnings_tax,
        "plate_fuzzy_matches": warnings_plate_fuzzy,
        "driver_other_plate": warnings_driver_other_plate,
        "name_fallback_matches": warnings_name_fallback,
        "duplicate_fee_skipped": warnings_duplicate_fee,
        "block_fee_assigned": warnings_block_fee,
        "duplicate_template_plates": list(duplicate_template_plates),
    }


def render(app):
    canvas = app.canvas
    try:
        canvas.delete("all")
        app.draw_background()
        app.draw_header(MODULE_TITLE)
        app.draw_path_bar()
    except Exception:
        pass

    bg = getattr(app, "BG", "#E8EEF5") if hasattr(app, "BG") else "#E8EEF5"
    frame = tk.Frame(canvas, bg=bg)
    w = max(900, canvas.winfo_width() - 160)
    canvas.create_window(80, 185, window=frame, anchor="nw", width=w)

    font_title = ("Segoe UI", 14, "bold")
    font = ("Segoe UI", 10)
    font_small = ("Segoe UI", 9)

    tk.Label(frame, text=MODULE_TITLE, bg=bg, font=font_title).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))

    template_var = tk.StringVar(value=DEFAULT_TEMPLATE_PATH)
    invoice_var = tk.StringVar(value=_desktop_path())
    export_var = tk.StringVar(value=os.path.join(_desktop_path(), "EnBW_AFI_Upload.csv"))
    status_var = tk.StringVar(value="Bereit. Bitte Vorlage, Rechnung und Exportdatei prüfen.")

    def row(label, var, r, mode):
        tk.Label(frame, text=label, bg=bg, font=font).grid(row=r, column=0, sticky="w", pady=6)
        e = tk.Entry(frame, textvariable=var, font=font)
        e.grid(row=r, column=1, sticky="ew", padx=(12, 8), pady=6)
        def browse():
            if mode == "open":
                p = filedialog.askopenfilename(title=label, filetypes=[("CSV-Dateien", "*.csv"), ("Alle Dateien", "*.*")])
            else:
                p = filedialog.asksaveasfilename(title=label, defaultextension=".csv", filetypes=[("CSV-Dateien", "*.csv")])
            if p:
                var.set(p)
        tk.Button(frame, text="Auswählen…", command=browse, font=font).grid(row=r, column=2, sticky="ew", pady=6)

    frame.columnconfigure(1, weight=1)
    row("Upload-Vorlage", template_var, 1, "open")
    row("EnBW-Rechnung", invoice_var, 2, "open")
    row("Export-CSV", export_var, 3, "save")

    info = (
        "Logik: Export bleibt SAP-uploadfähig mit Spalten A-J. PRICE = NET_VALUE. "
        "Zuordnung nach normalisiertem Kennzeichen. Namensabweichungen/fehlende Kennzeichen werden per Popup gemeldet; der Export wird trotzdem erzeugt."
    )
    tk.Label(frame, text=info, bg=bg, font=font_small, justify="left", wraplength=w-40).grid(row=4, column=0, columnspan=3, sticky="w", pady=(14, 10))
    tk.Label(frame, textvariable=status_var, bg=bg, font=font_small, justify="left", wraplength=w-40).grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))

    def run_export():
        template_path = template_var.get().strip()
        invoice_path = invoice_var.get().strip()
        export_path = export_var.get().strip()
        if not os.path.isfile(template_path):
            messagebox.showwarning(MODULE_TITLE, "Die Upload-Vorlage wurde nicht gefunden.")
            return
        if not os.path.isfile(invoice_path):
            messagebox.showwarning(MODULE_TITLE, "Die EnBW-Rechnungsdatei wurde nicht gefunden.")
            return
        if not export_path.lower().endswith(".csv"):
            export_path += ".csv"
            export_var.set(export_path)
        status_var.set("Export läuft…")
        def worker():
            try:
                result = create_upload_csv(template_path, invoice_path, export_path)
                def done():
                    status_var.set(f"Export erstellt: {result['rows']} Zeilen → {result['export_path']}")
                    parts = [f"Export wurde erstellt.\n\nZeilen: {result['rows']}\nDatei: {result['export_path']}"]
                    if result["name_differences"]:
                        parts.append("\nNamensabweichungen:\n" + "\n".join(result["name_differences"][:30]))
                        if len(result["name_differences"]) > 30:
                            parts.append(f"… weitere {len(result['name_differences'])-30} Abweichungen")
                    if result["missing_plates"]:
                        parts.append("\nKennzeichen nicht in Vorlage gefunden:\n" + "\n".join(result["missing_plates"][:30]))
                        if len(result["missing_plates"]) > 30:
                            parts.append(f"… weitere {len(result['missing_plates'])-30} Kennzeichen")
                    if result.get("plate_fuzzy_matches"):
                        parts.append("\nRobuste Kennzeichen-Zuordnungen:\n" + "\n".join(result["plate_fuzzy_matches"][:30]))
                    if result.get("driver_other_plate"):
                        parts.append("\nFahrer in Vorlage auf anderem Kennzeichen gefunden:\n" + "\n".join(result["driver_other_plate"][:30]))
                    if result.get("name_fallback_matches"):
                        parts.append("\nKontierung per Fahrername übernommen:\n" + "\n".join(result["name_fallback_matches"][:30]))
                    if result.get("duplicate_fee_skipped"):
                        parts.append("\nMehrfache Grundgebühren nicht erneut zugewiesen:\n" + "\n".join(result["duplicate_fee_skipped"][:30]))
                    if result.get("block_fee_assigned"):
                        parts.append("\nBlockiergebühren zugeordnet:\n" + "\n".join(result["block_fee_assigned"][:30]))
                    if result["unknown_tax"]:
                        parts.append("\nNicht eindeutig erkannte Steuersätze:\n" + "\n".join(result["unknown_tax"][:20]))
                    messagebox.showinfo(MODULE_TITLE, "\n".join(parts))
                app.root.after(0, done)
            except Exception as exc:
                app.root.after(0, lambda: (status_var.set("Fehler beim Export."), messagebox.showerror(MODULE_TITLE, str(exc))))
        threading.Thread(target=worker, daemon=True).start()

    tk.Button(frame, text="Export-CSV erstellen", command=run_export, font=("Segoe UI", 11, "bold"), bg="#CFEAD6", activebackground="#BDE3C7").grid(row=5, column=0, sticky="w", pady=(12, 4))
