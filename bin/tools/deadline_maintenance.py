import json
import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

MODULE_TITLE = "Stichtags- & Zuständigkeitspflege"

# ---- Feiertage BW + Ranges ----

def easter_sunday(y: int) -> date:
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(y, month, day)


def bw_holidays_named(year: int):
    easter = easter_sunday(year)
    return [
        (date(year, 1, 1), "Neujahr"),
        (date(year, 1, 6), "Heilige Drei Könige"),
        (easter - timedelta(days=2), "Karfreitag"),
        (easter + timedelta(days=1), "Ostermontag"),
        (date(year, 5, 1), "Tag der Arbeit"),
        (easter + timedelta(days=39), "Christi Himmelfahrt"),
        (easter + timedelta(days=50), "Pfingstmontag"),
        (easter + timedelta(days=60), "Fronleichnam"),
        (date(year, 10, 3), "Tag der Deutschen Einheit"),
        (date(year, 11, 1), "Allerheiligen"),
        (date(year, 12, 25), "1. Weihnachtstag"),
        (date(year, 12, 26), "2. Weihnachtstag"),
    ]


def fmt_date(d):
    return d.strftime("%d.%m.%Y") if isinstance(d, date) else ""


def parse_date(s: str):
    s = (s or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def is_business_day_bw(d: date):
    return d.weekday() < 5 and d not in {x[0] for x in bw_holidays_named(d.year)}

def first_business_day_after(d: date):
    cur = d + timedelta(days=1)
    while not is_business_day_bw(cur):
        cur += timedelta(days=1)
    return cur

def default_cutoff_for_period(kind: str, period: str):
    _s, end = period_bounds(kind, period)
    return fmt_date(first_business_day_after(end)) if end else ""

def fiscal_year_start_for_date(d=None):
    d = d or date.today()
    return d.year if d.month >= 10 else d.year - 1

def fiscal_year_label(start_year: int):
    return f"GJ {start_year}/{start_year + 1}"

def fiscal_month_keys(start_year: int):
    return [f"{start_year:04d}-{m:02d}" for m in range(10, 13)] + [f"{start_year + 1:04d}-{m:02d}" for m in range(1, 10)]

def fiscal_quarter_keys(start_year: int):
    return [f"{start_year:04d}-Q4", f"{start_year + 1:04d}-Q1", f"{start_year + 1:04d}-Q2", f"{start_year + 1:04d}-Q3"]

def period_bounds(kind: str, key: str):
    if kind == 'monthly':
        y, m = map(int, key.split('-'))
        return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
    if kind == 'quarterly':
        y, q = key.split('-Q'); y = int(y); q = int(q)
        m1 = (q - 1) * 3 + 1
        start = date(y, m1, 1)
        m3 = m1 + 2
        end = date(y, m3, calendar.monthrange(y, m3)[1])
        return start, end
    if kind == 'yearly':
        y1, y2 = map(int, key.split('-'))
        return date(y1, 10, 1), date(y2, 9, 30)
    return None, None


def holidays_for_period(start: date, end: date):
    hol = []
    for y in range(start.year, end.year + 1):
        hol.extend(bw_holidays_named(y))
    hol = [(d, n) for d, n in hol if start <= d <= end]
    hol.sort(key=lambda x: x[0])

    out = []
    # Ostern Range
    for y in range(start.year, end.year + 1):
        eas = easter_sunday(y)
        gf = eas - timedelta(days=2)
        em = eas + timedelta(days=1)
        if start <= gf and em <= end:
            out.append(f"Ostern ({fmt_date(gf)}–{fmt_date(em)})")
            hol = [(d,n) for d,n in hol if d not in (gf, em)]

    # Weihnachten Range
    for y in range(start.year, end.year + 1):
        c1 = date(y, 12, 25)
        c2 = date(y, 12, 26)
        if start <= c1 and c2 <= end:
            out.append(f"Weihnachten ({fmt_date(c1)}–{fmt_date(c2)})")
            hol = [(d,n) for d,n in hol if d not in (c1, c2)]

    for d, n in hol:
        out.append(f"{n} ({fmt_date(d)})")
    return "; ".join(out)


# ---- Storage ----

def storage_dir():
    base = cc.bin_dir() / "Deadlines" / "years"
    base.mkdir(parents=True, exist_ok=True)
    return base


def year_file(year: int):
    return storage_dir() / f"deadlines_{year:04d}.json"


def _default_record():
    return {
        "dekade_close": "",          # Pflichtfeld
        "report18": "",              # Datum
        "recon08": "",               # Datum
        "close_month": "",           # Datum
    }


def default_year_data(year: int):
    months = {key: _default_record() for key in fiscal_month_keys(year)}
    quarters = {key: _default_record() for key in fiscal_quarter_keys(year)}
    years = {f"{year:04d}-{year+1:04d}": _default_record()}
    return {"fiscal_year_start": year, "label": fiscal_year_label(year), "monthly": months, "quarterly": quarters, "yearly": years}


def load_year(year: int):
    return cc.json_load(year_file(year), default_year_data(year))


def save_year(year: int, data):
    cc.json_save(year_file(year), data)


# ---- Propagation in Close-Period-Files ----

def closing_base_dir():
    return cc.bin_dir() / "Closing"


def period_file(module_dir: str, period: str):
    return closing_base_dir() / module_dir / "periods" / f"{period}.json"


def apply_to_period_file(module_dir: str, period: str, rec: dict):
    p = period_file(module_dir, period)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return False
    # Federführend: closing_cutoff_date übernehmen
    dek = parse_date(rec.get('dekade_close'))
    if dek:
        data['closing_cutoff_date'] = dek.strftime('%Y-%m-%d')
    # Zusatzfelder optional in Close-JSON ablegen (für spätere Anzeige/Logik)
    for k in ('report18','recon08','close_month'):
        v = rec.get(k, '')
        if v:
            d = parse_date(v)
            data[k] = d.strftime('%Y-%m-%d') if d else v
        else:
            data.pop(k, None)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return True


def propagate(year_data):
    count = 0
    for period, rec in year_data.get('monthly', {}).items():
        if apply_to_period_file('MonthlyClose', period, rec):
            count += 1
        if apply_to_tax_reporting_period(period, rec):
            count += 1
    for period, rec in year_data.get('quarterly', {}).items():
        if apply_to_period_file('QuarterlyClose', period, rec):
            count += 1
    for period, rec in year_data.get('yearly', {}).items():
        if apply_to_period_file('YearlyClose', period, rec):
            count += 1
    return count


def apply_to_tax_reporting_period(period: str, rec: dict):
    try:
        p = cc.tax_period_path(period)
        if not p.exists():
            return False
        data = json.loads(p.read_text(encoding='utf-8'))
        changed = False
        due = parse_date(rec.get('dekade_close')) or parse_date(default_cutoff_for_period('monthly', period))
        due_iso = due.strftime('%Y-%m-%d') if due else ''
        for report in data.get('reports', []):
            if report.get('sync_with_calendar', False) and due_iso and report.get('due_date') != due_iso:
                report['due_date'] = due_iso
                report.setdefault('history', []).append({'timestamp': cc.now_iso(), 'user': 'System', 'action': 'Fälligkeit aus Stichtagspflege synchronisiert', 'new_due_date': due_iso})
                changed = True
        if changed:
            cc.json_save(p, data)
        return changed
    except Exception:
        return False

class DeadlineMaintenanceUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        self.year = fiscal_year_start_for_date()
        self.data = load_year(self.year)
        self._saved_snapshot = json.dumps(self.data, sort_keys=True, ensure_ascii=False)

        self.frame = tk.Frame(self.root, bg=cc.BG)
        self.app.widget_items.append(self.frame)
        self.canvas.create_window(0, 132, window=self.frame, anchor="nw",
                                  width=self.canvas.winfo_width(), height=max(420, self.canvas.winfo_height() - 172))
        self.render()
        try:
            self.app.register_unsaved_changes_provider(self.has_unsaved_changes, self.save_all, self.discard_changes)
        except Exception:
            pass

    def can_open(self):
        return cc.can_admin(self.app)

    def render(self):
        for w in self.frame.winfo_children():
            w.destroy()

        if not self.can_open():
            tk.Label(self.frame, text="Keine Berechtigung: Dieses Modul ist nur für E3/E4 freigeschaltet.",
                     bg=cc.BG, fg=cc.TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=24, pady=24)
            return

        top = tk.Frame(self.frame, bg=cc.BG)
        top.pack(fill="x", padx=24, pady=(14, 8))
        tk.Label(top, text=MODULE_TITLE, bg=cc.BG, fg=cc.TEXT, font=("Segoe UI", 18, "bold")).pack(side="left")

        year_box = ttk.Combobox(top, values=[str(self.year-1), str(self.year), str(self.year+1)], state="readonly", width=8)
        year_box.set(str(self.year))
        year_box.pack(side="left", padx=10)

        def switch_year(_=None):
            try:
                self.year = int(year_box.get())
            except Exception:
                self.year = fiscal_year_start_for_date()
            self.data = load_year(self.year)
            self.render()
        year_box.bind("<<ComboboxSelected>>", switch_year)

        tk.Button(top, text="Export Excel", command=self.export_excel, bg=cc.WHITE, fg=cc.BLUE, bd=1, padx=12).pack(side="right")
        tk.Button(top, text="Speichern + Übernehmen", command=self.save_all, bg=cc.BLUE, fg="white", bd=0, padx=12).pack(side="right", padx=8)

        nb = ttk.Notebook(self.frame)
        nb.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        tab_m = tk.Frame(nb, bg=cc.BG)
        tab_q = tk.Frame(nb, bg=cc.BG)
        tab_y = tk.Frame(nb, bg=cc.BG)
        nb.add(tab_m, text="Monatsabschluss")
        nb.add(tab_q, text="Quartalsabschluss")
        nb.add(tab_y, text="Jahresabschluss")

        self._build_period_tab(tab_m, 'monthly')
        self._build_period_tab(tab_q, 'quarterly')
        self._build_period_tab(tab_y, 'yearly')
        try:
            cc.install_entry_grid_navigation(nb)
        except Exception:
            pass

    def _build_period_tab(self, parent, kind):
        data = self.data.get(kind, {})
        canvas = tk.Canvas(parent, bg=cc.BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=cc.BG)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def upd(_=None):
            canvas.itemconfigure(win, width=max(1, canvas.winfo_width() - 2))
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", upd)
        canvas.bind("<Configure>", upd)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        headers = ["Zeitraum", "Dekadenabschluss (TT.MM.JJJJ)", "Bericht ab 18 Uhr (Datum)", "Kontenabstimmung / Berichtsprüfung ab 8:00 (Datum)", "Abschluss lfd. Buchungsmonat (Datum)"]
        for c, h in enumerate(headers):
            tk.Label(inner, text=h, bg=cc.HEADER, fg=cc.TEXT, font=("Segoe UI", 9, "bold"), padx=6, pady=6).grid(row=0, column=c, sticky="nsew", padx=1, pady=1)

        self._row_vars = getattr(self, '_row_vars', {})
        self._row_vars[kind] = {}

        for r, period in enumerate(sorted(data.keys()), 1):
            rec = data[period]
            v_dek = tk.StringVar(value=rec.get('dekade_close', ''))
            v_r18 = tk.StringVar(value=rec.get('report18', ''))
            v_r08 = tk.StringVar(value=rec.get('recon08', ''))
            v_cm  = tk.StringVar(value=rec.get('close_month', ''))
            self._row_vars[kind][period] = (v_dek, v_r18, v_r08, v_cm)

            tk.Label(inner, text=period, bg=cc.WHITE, fg=cc.TEXT, padx=6, pady=5, anchor="w").grid(row=r, column=0, sticky="nsew", padx=1, pady=1)
            tk.Entry(inner, textvariable=v_dek, bg=cc.WHITE, width=16).grid(row=r, column=1, sticky="nsew", padx=1, pady=1)
            tk.Entry(inner, textvariable=v_r18, bg=cc.WHITE, width=16).grid(row=r, column=2, sticky="nsew", padx=1, pady=1)
            tk.Entry(inner, textvariable=v_r08, bg=cc.WHITE, width=22).grid(row=r, column=3, sticky="nsew", padx=1, pady=1)
            tk.Entry(inner, textvariable=v_cm, bg=cc.WHITE, width=20).grid(row=r, column=4, sticky="nsew", padx=1, pady=1)

    def save_all(self):
        changed_periods = []
        for kind, per_map in getattr(self, '_row_vars', {}).items():
            for period, (v_dek, v_r18, v_r08, v_cm) in per_map.items():
                if v_dek.get().strip() and not parse_date(v_dek.get()):
                    messagebox.showwarning(MODULE_TITLE, f"Ungültiges Dekadenabschluss-Datum: {v_dek.get()} ({period})")
                    return
                for label, vv in [("Bericht ab 18 Uhr", v_r18), ("Kontenabstimmung", v_r08), ("Abschluss Monat", v_cm)]:
                    if vv.get().strip() and not parse_date(vv.get()):
                        messagebox.showwarning(MODULE_TITLE, f"Ungültiges Datum ({label}): {vv.get()} ({period})")
                        return
                rec = self.data[kind][period]
                old = dict(rec)
                rec['dekade_close'] = v_dek.get().strip() or default_cutoff_for_period(kind, period)
                rec['report18'] = v_r18.get().strip()
                rec['recon08'] = v_r08.get().strip()
                rec['close_month'] = v_cm.get().strip()
                v_dek.set(rec['dekade_close'])
                if old != rec:
                    changed_periods.append(f"{kind}:{period}")
        save_year(self.year, self.data)
        propagated = propagate(self.data)
        self._saved_snapshot = self._current_snapshot()
        cc.log_audit(self.app, "Aufgabe geändert", MODULE_TITLE, "Stichtage gespeichert und übernommen", f"{fiscal_year_label(self.year)}; Perioden: {', '.join(changed_periods) if changed_periods else 'keine Feldänderung'}; synchronisierte Dateien: {propagated}", "Info", period=fiscal_year_label(self.year), public=True)
        messagebox.showinfo(MODULE_TITLE, "Gespeichert. Änderungen wurden in Monats-/Quartals-/Jahresabschluss und Steuermeldungs-Cockpit übernommen.")

    def _current_snapshot(self):
        data_copy = json.loads(json.dumps(self.data, ensure_ascii=False))
        for kind, per_map in getattr(self, '_row_vars', {}).items():
            for period, (v_dek, v_r18, v_r08, v_cm) in per_map.items():
                rec = data_copy.get(kind, {}).setdefault(period, _default_record())
                rec['dekade_close'] = v_dek.get().strip() or default_cutoff_for_period(kind, period)
                rec['report18'] = v_r18.get().strip()
                rec['recon08'] = v_r08.get().strip()
                rec['close_month'] = v_cm.get().strip()
        return json.dumps(data_copy, sort_keys=True, ensure_ascii=False)

    def has_unsaved_changes(self):
        try:
            return self._current_snapshot() != getattr(self, '_saved_snapshot', '')
        except Exception:
            return False

    def discard_changes(self):
        self.data = load_year(self.year)
        self._saved_snapshot = json.dumps(self.data, sort_keys=True, ensure_ascii=False)
        self.render()

    def export_excel(self):
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile=f"Fristen_{self.year}.xlsx")
        if not path:
            return
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = Workbook(); wb.remove(wb.active)

        def add_sheet(name: str, kind: str):
            ws = wb.create_sheet(name[:31])
            headers = [
                "Zeitraum",
                "Dekadenabschluss",
                "Bericht wird gerechnet ab 18 Uhr",
                "Kontenabstimmung / Berichtsprüfung ab 8:00 Uhr",
                "Abschluss lfd. Buchungsmonat",
                "Feiertage im Zeitraum (BW)",
            ]
            ws.append(headers)
            fill = PatternFill("solid", fgColor="D3DEE9")
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.fill = fill
                cell.alignment = Alignment(wrap_text=True, vertical="top")

            for period in sorted(self.data.get(kind, {}).keys()):
                rec = self.data[kind][period]
                dek = parse_date(rec.get('dekade_close'))
                if not dek:
                    continue
                r18 = parse_date(rec.get('report18')) or dek
                r08 = parse_date(rec.get('recon08')) or dek
                cm  = parse_date(rec.get('close_month')) or dek

                start, end = period_bounds(kind, period)
                hol = holidays_for_period(start, end) if start and end else ""

                ws.append([
                    period,
                    fmt_date(dek),
                    f"{fmt_date(r18)} 18:00" if r18 else "",
                    f"{fmt_date(r08)} 08:00" if r08 else "",
                    fmt_date(cm),
                    hol,
                ])

        add_sheet("Monat", 'monthly')
        add_sheet("Quartal", 'quarterly')
        add_sheet("Jahr", 'yearly')

        wb.save(path)
        cc.log_audit(self.app, "PDF-Bericht erstellt", MODULE_TITLE, Path(path).name, path, "Info", period=str(self.year), public=True)
        if messagebox.askyesno(MODULE_TITLE, "Excel öffnen?"):
            cc.open_path(path)


def render(app):
    DeadlineMaintenanceUI(app)
