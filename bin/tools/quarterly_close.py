
import calendar
import json
import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from . import compliance_common as cc
except Exception:
    try:
        import compliance_common as cc
    except Exception:
        cc = None

# v0.434 Paket 1B: direkte, scharfe Modulschrift für Abschluss-/Stichtagsmodule.
# Der Bereichszoom aus Fibu_mate.py wird berücksichtigt, ohne Kopf-/Fußleisten nachzuskalieren.
def zfont(app, size=12, weight=None, underline=False, scale=1.0):
    try:
        scope_zoom = float(getattr(app, "current_scope_zoom", 1.0) or 1.0)
        final = max(9, int(round(float(size) * 1.28 * scope_zoom * float(scale))))
    except Exception:
        final = int(size)
    styles = []
    if weight:
        styles.append(weight)
    if underline:
        styles.append("underline")
    return tuple(["Segoe UI", final] + styles)


def apply_readable_fonts(widget, app, base_size=12):
    """Setzt direkte Tk-Fonts für neu erzeugte Modulwidgets nach."""
    try:
        try:
            cls = widget.winfo_class().lower()
        except Exception:
            cls = ""
        if cls in ("label", "button", "entry", "text", "listbox", "checkbutton", "radiobutton", "menubutton"):
            try:
                current = str(widget.cget("font") or "")
                widget.configure(font=zfont(app, base_size, "bold" if "bold" in current.lower() else None))
            except Exception:
                pass
        for child in widget.winfo_children():
            apply_readable_fonts(child, app, base_size)
    except Exception:
        pass
STATUS_OPEN = "Offen"
STATUS_IN_PROGRESS = "In Bearbeitung"
STATUS_DONE = "Erledigt"
STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]
TEAMS = ["Hauptbuch", "Zentralregulierung", "Debitoren", "Treasury"]
TEAM_ALIASES = {"Kreditoren": "Zentralregulierung", "Controlling": "Treasury"}
DEADLINE_TYPES = ["intern", "gesetzlich"]
PRIORITIES = ["normal", "hoch", "kritisch"]

DUE_CUTOFF = "closing_cutoff"
DUE_WORKDAY_NEXT = "workday_next_month"
DUE_DAY_CAL_MONTH = "day_calendar_month"
DUE_FIXED = "fixed_date"
# Legacy values for migration only
DUE_WORKDAY_MONTH = "workday_current_month"
DUE_END_CURRENT = "end_current_month"
DUE_LABEL_TO_VALUE = {
    "Abschluss-Stichtag": DUE_CUTOFF,
    "x. Werktag des Folgemonats": DUE_WORKDAY_NEXT,
    "x. Tag des Kalendermonats": DUE_DAY_CAL_MONTH,
    "Konkretes Datum": DUE_FIXED,
}
DUE_VALUE_TO_LABEL = {v: k for k, v in DUE_LABEL_TO_VALUE.items()}
WARN_YELLOW_DAYS = 10
WARN_ORANGE_DAYS = 5
MIN_PERIOD = "2026-Q2"
MIN_FISCAL_YEAR_PERIOD = "2025-2026"
FISCAL_YEAR_START_MONTH = 10


def fiscal_year_start_for_date(d=None):
    d = d or date.today()
    return d.year if d.month >= FISCAL_YEAR_START_MONTH else d.year - 1


def fiscal_year_end_quarter_key(start_year):
    return f"{start_year + 1:04d}-Q3"


def august_month_key(start_year):
    return f"{start_year + 1:04d}-08"


def august_cutoff_reached(start_year, today=None):
    today = today or date.today()
    cutoff = None
    try:
        synced = cc.get_deadline_cutoff('monthly', august_month_key(start_year)) if cc is not None and hasattr(cc, 'get_deadline_cutoff') else ''
        cutoff = parse_date(synced)
    except Exception:
        cutoff = None
    if not cutoff:
        y, m = map(int, august_month_key(start_year).split('-'))
        end = date(y, m, calendar.monthrange(y, m)[1])
        cur = end + timedelta(days=1)
        while not is_business_day(cur):
            cur += timedelta(days=1)
        cutoff = cur
    return today >= cutoff


def max_period_key(today=None):
    today = today or date.today()
    fy_start = fiscal_year_start_for_date(today)
    if august_cutoff_reached(fy_start, today):
        return fiscal_year_end_quarter_key(fy_start + 1)
    return fiscal_year_end_quarter_key(fy_start)


def bounded_current_period_key(today=None):
    today = today or date.today()
    current = quarter_key(today)
    if current < MIN_PERIOD:
        return MIN_PERIOD
    max_key = max_period_key(today)
    return min(current, max_key)


def period_allowed(period, today=None):
    return MIN_PERIOD <= period <= max_period_key(today)


def iter_allowed_periods(today=None):
    periods = []
    cur = MIN_PERIOD
    max_key = max_period_key(today)
    while cur <= max_key:
        periods.append(cur)
        cur = add_quarter(cur, 1)
    return periods
COLORS = {
    "bg": "#E8EEF5", "header": "#D3DEE9", "blue": "#004B93", "red": "#E30613",
    "orange": "#F59E0B", "yellow": "#FACC15", "green": "#16A34A", "dark_green": "#047857",
    "text": "#182431", "text2": "#445364", "line": "#91A3B5", "white": "#FFFFFF",
    "edit_bg": "#FEF3C7", "subtask_bg": "#F8FAFC"
}


def _base_dir() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name.lower() == "tools":
        return here.parent.parent / "Closing" / "QuarterlyClose"
    return here.parent / "bin" / "Closing" / "QuarterlyClose"


BASE_DIR = _base_dir()
PERIOD_DIR = BASE_DIR / "periods"
ATTACH_DIR = BASE_DIR / "attachments"
CONFIG_PATH = BASE_DIR / "quarterly_close_config.json"
CATALOG_PATH = BASE_DIR / "quarterly_close_task_catalog.json"
CLOSING_SCOPE = "Q"
INITIAL_TASK_IDS = {
    ('Hauptbuch', 'Bankabstimmung durchführen'): 'QM001',
    ('Hauptbuch', 'Rückstellungen prüfen'): 'QM002',
    ('Hauptbuch', 'Abgrenzungen buchen'): 'QM003',
    ('Hauptbuch', 'Sachkonten prüfen'): 'QM004',
    ('Zentralregulierung', 'Offene Posten prüfen'): 'QM005',
    ('Zentralregulierung', 'Lieferantenabstimmung durchführen'): 'QM006',
    ('Zentralregulierung', 'Rechnungsabgrenzung prüfen'): 'QM007',
    ('Zentralregulierung', 'Zahlungsläufe kontrollieren'): 'QM008',
    ('Debitoren', 'Offene Posten prüfen'): 'QM009',
    ('Debitoren', 'Mahnstatus prüfen'): 'QM010',
    ('Debitoren', 'Erlösabgrenzung prüfen'): 'QM011',
    ('Debitoren', 'Kundensalden abstimmen'): 'QM012',
    ('Treasury', 'Kostenstellen prüfen'): 'QM013',
    ('Treasury', 'Reporting vorbereiten'): 'QM014',
    ('Treasury', 'Konzernmeldung vorbereiten'): 'QM015',
    ('Treasury', 'Abweichungsanalyse erstellen'): 'QM016',
}

def quarter_key(d=None):
    d = d or date.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year:04d}-Q{q}"

def current_period_key():
    return bounded_current_period_key()


def add_quarter(key, delta):
    year_str, q_str = key.split("-Q"); year = int(year_str); quarter = int(q_str) + delta
    while quarter < 1:
        quarter += 4; year -= 1
    while quarter > 4:
        quarter -= 4; year += 1
    return f"{year:04d}-Q{quarter}"

def add_period(key, delta):
    return add_quarter(key, delta)

def period_label(key):
    y, q = key.split("-Q")
    return f"{q}. Quartal {y}"



def parse_date(value):
    value = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass
    return None


def format_date_de(value):
    d = value if isinstance(value, date) else parse_date(value)
    return d.strftime("%d.%m.%Y") if d else ""



def format_datetime_de(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y %H:%M")
    except Exception:
        d = parse_date(value)
        return d.strftime("%d.%m.%Y") if d else str(value)

def easter_sunday(year):
    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def bw_holidays(year):
    easter = easter_sunday(year)
    return {
        date(year, 1, 1), date(year, 1, 6), easter - timedelta(days=2), easter + timedelta(days=1),
        date(year, 5, 1), easter + timedelta(days=39), easter + timedelta(days=50), easter + timedelta(days=60),
        date(year, 10, 3), date(year, 11, 1), date(year, 12, 25), date(year, 12, 26)
    }


def is_business_day(d):
    return d.weekday() < 5 and d not in bw_holidays(d.year)


def nth_business_day(year, month, n):
    n = max(1, int(n or 1))
    current = date(year, month, 1)
    count = 0
    while True:
        if is_business_day(current):
            count += 1
            if count == n:
                return current
        current += timedelta(days=1)


def normalize_team_name(team):
    return TEAM_ALIASES.get(team, team)


def normalize_team_members(data):
    members = data.setdefault("team_members", {})
    for old, new in TEAM_ALIASES.items():
        if old in members:
            if new not in members or not members.get(new):
                members[new] = members.get(old, [])
            members.pop(old, None)
    for team in TEAMS:
        value = members.get(team, [])
        if isinstance(value, str):
            value = [v.strip() for v in value.replace(";", "\n").replace(",", "\n").splitlines() if v.strip()]
        members[team] = value
    return members


def set_team_members_text(data, team, text):
    normalize_team_members(data)[team] = [line.strip() for line in str(text or "").replace(";", "\n").replace(",", "\n").splitlines() if line.strip()]

def period_start(period):
    y, q = period.split("-Q")
    return date(int(y), (int(q) - 1) * 3 + 1, 1)

def period_end(period):
    start = period_start(period); end_month = start.month + 2
    return date(start.year, end_month, calendar.monthrange(start.year, end_month)[1])

def clamp_day_in_period(period, day):
    start = period_start(period)
    day = max(1, min(int(day or 1), calendar.monthrange(start.year, start.month)[1]))
    return date(start.year, start.month, day)


def first_business_day_after_period_end(period):
    cur = period_end(period) + timedelta(days=1)
    while not is_business_day(cur):
        cur += timedelta(days=1)
    return cur

def default_due_date(period):
    return period_end(period).strftime("%Y-%m-%d")

def resolve_due_date(task, data, period):
    mode = task.get("due_mode", DUE_CUTOFF)
    if mode == DUE_CUTOFF:
        return normalize_cutoff(data, period)
    if mode == DUE_WORKDAY_NEXT:
        next_period = add_quarter(period, 1); start = period_start(next_period)
        return nth_business_day(start.year, start.month, task.get("due_workday") or 1).strftime("%Y-%m-%d")
    if mode == DUE_DAY_CAL_MONTH:
        return clamp_day_in_period(period, task.get("due_day") or 1).strftime("%Y-%m-%d")
    if mode == DUE_FIXED:
        due = parse_date(task.get("due_fixed_date") or task.get("due_date"))
        return due.strftime("%Y-%m-%d") if due else normalize_cutoff(data, period)
    return normalize_cutoff(data, period)



def due_rule_text(task):
    mode = task.get("due_mode")
    if mode == DUE_CUTOFF:
        return "Abschluss-Stichtag"
    if mode == DUE_WORKDAY_NEXT:
        return f"{task.get('due_workday') or 1}. Werktag Folgemonat"
    if mode == DUE_DAY_CAL_MONTH:
        return f"{task.get('due_day') or 1}. Tag Kalendermonat"
    if mode == DUE_FIXED:
        return "Konkretes Datum"
    return ""


def due_display(task):
    rule = due_rule_text(task)
    return f"{format_date_de(task.get('due_date', ''))}\n{rule}" if rule else format_date_de(task.get("due_date", ""))


def make_task_id(team, index):
    safe = str(team).lower().replace(" ", "_").replace("/", "_")
    return f"{safe}_{index:02d}"


def ensure_storage():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PERIOD_DIR.mkdir(parents=True, exist_ok=True)
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({"teams": TEAMS, "warning_days": {"yellow": WARN_YELLOW_DAYS, "orange": WARN_ORANGE_DAYS}}, ensure_ascii=False, indent=2), encoding="utf-8")
    if not CATALOG_PATH.exists():
        CATALOG_PATH.write_text(json.dumps({"tasks": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def period_path(period):
    return PERIOD_DIR / f"{period}.json"



def deadline_cutoff_date(period):
    try:
        if cc is not None and hasattr(cc, 'get_deadline_cutoff'):
            return cc.get_deadline_cutoff('quarterly', period)
    except Exception:
        pass
    return ''


def default_cutoff_date(period):
    synced = deadline_cutoff_date(period)
    if synced:
        return synced
    return first_business_day_after_period_end(period).strftime("%Y-%m-%d")


def normalize_cutoff(data, period):
    synced = deadline_cutoff_date(period)
    cutoff = parse_date(synced) if synced else parse_date(data.get("closing_cutoff_date", ""))
    if not cutoff:
        cutoff = parse_date(default_cutoff_date(period))
    data["closing_cutoff_date"] = cutoff.strftime("%Y-%m-%d")
    return data["closing_cutoff_date"]


def all_subtasks_done(task):
    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]
    return bool(subtasks) and all(s.get("status") == STATUS_DONE for s in subtasks)


def sync_parent_status_from_subtasks(task):
    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]
    if subtasks:
        if all(s.get("status") == STATUS_DONE for s in subtasks):
            task["status"] = STATUS_DONE
            task.setdefault("done_at", datetime.now().isoformat(timespec="seconds"))
        elif task.get("status") == STATUS_DONE:
            task["status"] = STATUS_OPEN
            task["done_at"] = None
            task["done_by"] = None


def migrate_due_fields(task, data, period):
    mode = task.get("due_mode", DUE_CUTOFF)
    if mode == DUE_WORKDAY_NEXT:
        task["due_mode"] = DUE_WORKDAY_NEXT
    elif mode in (DUE_FIXED,):
        task["due_mode"] = DUE_FIXED
    elif mode in (DUE_WORKDAY_MONTH, DUE_END_CURRENT):
        task["due_mode"] = DUE_CUTOFF
    elif mode not in (DUE_CUTOFF, DUE_WORKDAY_NEXT, DUE_DAY_CAL_MONTH, DUE_FIXED):
        task["due_mode"] = DUE_CUTOFF
    if task.get("due_mode") == DUE_DAY_CAL_MONTH:
        task["due_day"] = int(task.get("due_day") or task.get("due_workday") or 1)


def normalize_task(task, data, period):
    task["team"] = normalize_team_name(task.get("team"))
    task.setdefault("task_uid", "")
    task.setdefault("owner_user_key", "")
    task.setdefault("attachments", [])
    task.setdefault("comments", [])
    task.setdefault("subtasks", [])
    task.setdefault("status", STATUS_OPEN)
    task.setdefault("deadline_type", "intern")
    task.setdefault("priority", "normal")
    task.setdefault("due_day", None)
    task.setdefault("due_workday", None)
    task.setdefault("recurring", False)
    task.setdefault("catalog_id", "")
    if task["deadline_type"] not in DEADLINE_TYPES:
        task["deadline_type"] = "intern"
    migrate_due_fields(task, data, period)
    task["due_date"] = resolve_due_date(task, data, period)
    for idx, sub in enumerate(task.get("subtasks", []), start=1):
        sub.setdefault("id", f"sub_{idx:02d}")
        sub.setdefault("title", "")
        sub.setdefault("status", STATUS_OPEN)
    sync_parent_status_from_subtasks(task)
    return task


def load_catalog():
    ensure_storage()
    try:
        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"tasks": []}
    data.setdefault("tasks", [])
    return data


def save_catalog(data):
    data.setdefault("tasks", [])
    CATALOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def default_tasks(period):
    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}
    examples = {
        "Hauptbuch": ["Bankabstimmung durchführen", "Rückstellungen prüfen", "Abgrenzungen buchen", "Sachkonten prüfen"],
        "Zentralregulierung": ["Offene Posten prüfen", "Lieferantenabstimmung durchführen", "Rechnungsabgrenzung prüfen", "Zahlungsläufe kontrollieren"],
        "Debitoren": ["Offene Posten prüfen", "Mahnstatus prüfen", "Erlösabgrenzung prüfen", "Kundensalden abstimmen"],
        "Treasury": ["Kostenstellen prüfen", "Reporting vorbereiten", "Konzernmeldung vorbereiten", "Abweichungsanalyse erstellen"],
    }
    tasks = []
    for team in TEAMS:
        names = examples[team]
        for idx, title in enumerate(names, 1):
            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]
            task_uid = INITIAL_TASK_IDS.get((team, title), "")
            task = {
                "id": make_task_id(team, idx), "task_uid": task_uid, "team": team, "title": title, "owner": team, "owner_user_key": "",
                "due_mode": DUE_CUTOFF, "due_day": None, "due_workday": 1,
                "deadline_type": "gesetzlich" if is_legal else "intern", "priority": "kritisch" if is_legal else "normal",
                "required": True, "recurring": False, "catalog_id": "", "status": STATUS_OPEN,
                "attachments": [], "comments": [], "subtasks": [], "done_at": None, "done_by": None,
            }
            task["due_date"] = resolve_due_date(task, data_stub, period)
            tasks.append(task)
    return tasks


def load_period(period):
    ensure_storage()
    path = period_path(period)
    if not path.exists():
        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), "closing_cutoff_date": default_cutoff_date(period), "team_members": {team: [] for team in TEAMS}, "tasks": default_tasks(period)}
        save_period(period, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("tasks", [])
    normalize_team_members(data)
    old_cutoff = data.get("closing_cutoff_date", "")
    normalize_cutoff(data, period)
    changed = old_cutoff != data.get("closing_cutoff_date", "")
    for task in data["tasks"]:
        old_team = task.get("team")
        normalize_task(task, data, period)
        changed = changed or old_team != task.get("team")
    if changed:
        save_period(period, data)
    return data


def save_period(period, data):
    ensure_storage()
    normalize_team_members(data)
    normalize_cutoff(data, period)
    for task in data.get("tasks", []):
        normalize_task(task, data, period)
    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def catalog_entry_to_task(entry, period, index):
    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}
    task = {
        "id": make_task_id(entry.get("team", "Team"), index), "team": normalize_team_name(entry.get("team")), "title": entry.get("title"),
        "owner": entry.get("owner", entry.get("team")), "owner_user_key": entry.get("owner_user_key", ""),
        "due_mode": entry.get("due_mode", DUE_CUTOFF), "due_day": entry.get("due_day"), "due_workday": entry.get("due_workday"), "due_fixed_date": entry.get("due_fixed_date", entry.get("due_date", "")),
        "deadline_type": entry.get("deadline_type", "intern"), "priority": entry.get("priority", "normal"),
        "required": entry.get("required", True), "recurring": True, "catalog_id": entry.get("catalog_id", ""),
        "status": STATUS_OPEN, "attachments": [], "comments": [], "subtasks": [], "done_at": None, "done_by": None,
    }
    task["due_date"] = resolve_due_date(task, data_stub, period)
    return task


def apply_catalog_to_period(period):
    data = load_period(period)
    catalog = load_catalog()
    changed = False
    tasks = data.setdefault("tasks", [])
    for entry in catalog.get("tasks", []):
        if not entry.get("recurring", True):
            continue
        start_period = entry.get("start_period", current_period_key())
        if period <= start_period:
            continue
        catalog_id = entry.get("catalog_id")
        existing = next((t for t in tasks if t.get("catalog_id") == catalog_id and not t.get("deleted")), None)
        if existing:
            keep = {"status": existing.get("status", STATUS_OPEN), "attachments": existing.get("attachments", []), "comments": existing.get("comments", []), "subtasks": existing.get("subtasks", []), "done_at": existing.get("done_at"), "done_by": existing.get("done_by")}
            existing.update(catalog_entry_to_task(entry, period, len([t for t in tasks if t.get("team") == entry.get("team")]) + 1))
            existing.update(keep)
            changed = True
        else:
            idx = len([t for t in tasks if t.get("team") == entry.get("team")]) + 1
            tasks.append(catalog_entry_to_task(entry, period, idx))
            changed = True
    if changed:
        save_period(period, data)
    return data

def cleanup_old_periods():
    ensure_storage()
    # v0.432: Alte/vorzeitige Periodendateien werden nicht gelöscht, aber nicht mehr angezeigt oder automatisch angelegt.
    return


def ensure_period_window():
    ensure_storage(); cleanup_old_periods()
    for p in iter_allowed_periods():
        load_period(p)
        apply_catalog_to_period(p)


def list_periods():
    ensure_period_window()
    allowed = set(iter_allowed_periods())
    return sorted(p.stem for p in PERIOD_DIR.glob("*.json") if p.stem in allowed)


def warning_level(task, today=None):
    if task.get("status") == STATUS_DONE or task.get("deadline_type") == "keine":
        return "done" if task.get("status") == STATUS_DONE else "none"
    due = parse_date(task.get("due_date", ""))
    if not due:
        return "none"
    today = today or date.today()
    days = (due - today).days
    if days < 0: return "overdue"
    if days == 0: return "today"
    if days <= WARN_ORANGE_DAYS: return "orange"
    if days <= WARN_YELLOW_DAYS: return "yellow"
    return "none"


def progress_color(percent):
    if percent >= 100: return COLORS["dark_green"]
    if percent >= 75: return COLORS["green"]
    if percent >= 50: return COLORS["yellow"]
    if percent >= 25: return COLORS["orange"]
    return COLORS["red"]


def calc_stats(tasks):
    visible = [t for t in tasks if not t.get("deleted")]
    total = len(visible)
    done = sum(1 for t in visible if t.get("status") == STATUS_DONE)
    in_progress = sum(1 for t in visible if t.get("status") == STATUS_IN_PROGRESS)
    open_count = total - done - in_progress
    overdue = sum(1 for t in visible if warning_level(t) == "overdue")
    critical = sum(1 for t in visible if warning_level(t) in ("overdue", "today", "orange") or (t.get("priority") == "kritisch" and t.get("deadline_type") != "keine"))
    percent = int(round((done / total) * 100)) if total else 0
    return {"total": total, "done": done, "in_progress": in_progress, "open": open_count, "overdue": overdue, "critical": critical, "percent": percent}


class QuarterlyCloseUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        ensure_period_window()
        self.period = current_period_key()
        self.data = apply_catalog_to_period(self.period)
        self.selected_team = None
        self.expanded_tasks = set()
        self.edit_mode = False
        self.tooltip = None
        self.frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.app.widget_items.append(self.frame)
        self.app.module_escape_handler = self.handle_escape
        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", width=self.canvas.winfo_width(), height=max(400, self.canvas.winfo_height() - 172))
        self.ensure_task_ids()
        self.render_dashboard()
        apply_readable_fonts(self.frame, self.app, 12)

    def handle_escape(self):
        if self.selected_team:
            self.selected_team = None
            self.render_dashboard()
            return True
        return False

    def can_edit(self):
        return self.role_rank_value() >= 3 and not self.is_period_closed()

    def user_choices(self):
        users = getattr(self.app, "user_data", {}).get("users", {})
        choices = [("", "Team / keine Person")]
        for key, data in sorted(users.items(), key=lambda item: item[1].get("display_name", item[0]).casefold()):
            choices.append((key, data.get("display_name", key)))
        return choices


    def _target_period_from_current(self):
        start = period_start(self.period); return f"{start.year:04d}-{start.month:02d}"
    def _target_periods_from(self, start_period, all_following):
        if not all_following: return [start_period]
        y, m = map(int, start_period.split("-")); out=[]
        for _ in range(24):
            out.append(f"{y:04d}-{m:02d}"); m += 1
            if m > 12: m = 1; y += 1
        return out
    def _target_period_end(self, period):
        y, m = map(int, period.split("-")); return date(y, m, calendar.monthrange(y, m)[1]).strftime("%Y-%m-%d")
    def _target_display(self, period):
        names=["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]; y,m=map(int, period.split("-")); return f"{names[m-1]} {y}"

    def is_standard_user(self):
        return self.role_rank_value() <= 2
    def can_complete_task(self, task):
        if self.is_period_closed(): return False
        if not self.is_standard_user(): return True
        return bool(getattr(self.app, "current_user_key", "") and task.get("owner_user_key") == getattr(self.app, "current_user_key", ""))

    def current_user_full_name(self):
        key = getattr(self.app, "current_user_key", "")
        data = getattr(self.app, "user_data", {}).get("users", {}).get(key, {}) if key else {}
        return data.get("full_name") or " ".join(x for x in [data.get("first_name", "").strip(), data.get("display_name", "").strip()] if x).strip() or getattr(self.app, "current_user_display", "") or key or ""

    def role_rank_value(self):
        role = self.app.my_role() if hasattr(self.app, "my_role") else "E1 - Standard"
        mapping = {"E1 - Standard": 1, "E2 - Erweitert": 2, "E3 - Administrator": 3, "E4 - System-Administrator": 4, "Standard": 1, "Administrator": 3, "System-Administrator": 4, "Wagnerm": 4}
        return mapping.get(role, 1)

    def ensure_close_metadata(self):
        self.data.setdefault("closed", False)
        self.data.setdefault("closed_at", None)
        self.data.setdefault("closed_by", "")
        self.data.setdefault("closed_by_key", "")
        self.data.setdefault("reopened_once", False)
        self.data.setdefault("close_events", [])
        self.data.setdefault("change_log", [])
        self.data.setdefault("reopen_email_log", [])

    def is_period_closed(self):
        self.ensure_close_metadata()
        return bool(self.data.get("closed"))

    def is_after_cutoff(self):
        cutoff = parse_date(self.data.get("closing_cutoff_date"))
        return bool(cutoff and date.today() > cutoff)

    def can_toggle_period_close(self):
        return self.role_rank_value() >= 3

    def require_unlocked(self, action="Diese Änderung"):
        if self.is_period_closed():
            messagebox.showwarning("Zeitraum geschlossen", f"{action} ist nicht möglich, weil der Zeitraum geschlossen ist. Bitte den Zeitraum zuerst wieder öffnen.")
            return False
        return True

    def log_period_event(self, action, reason="", extra=None):
        self.ensure_close_metadata()
        self.data.setdefault("close_events", []).append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "action": action,
            "user": self.current_user_full_name(),
            "user_key": getattr(self.app, "current_user_key", ""),
            "reason": reason,
            "extra": extra or {},
        })

    def log_change(self, action, task=None, field="", old="", new=""):
        self.ensure_close_metadata()
        after_reopen = bool(self.data.get("reopened_once")) and not self.data.get("closed")
        self.data.setdefault("change_log", []).append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user": self.current_user_full_name(),
            "user_key": getattr(self.app, "current_user_key", ""),
            "action": action,
            "task_uid": task.get("task_uid", "") if isinstance(task, dict) else "",
            "task_title": task.get("title", "") if isinstance(task, dict) else "",
            "field": field,
            "old": str(old) if old is not None else "",
            "new": str(new) if new is not None else "",
            "after_reopen": after_reopen,
        })

    def close_status_text(self):
        self.ensure_close_metadata()
        if self.data.get("closed"):
            return f"(zuletzt) abgeschlossen am {format_datetime_de(self.data.get('closed_at'))} durch {self.data.get('closed_by', '')}"
        events = self.data.get("close_events", [])
        reopen = next((e for e in reversed(events) if e.get("action") == "opened"), None)
        if reopen:
            return f"Wieder geöffnet am {format_datetime_de(reopen.get('timestamp'))} durch {reopen.get('user', '')}"
        return ""

    def e3_e4_recipients(self):
        recipients=[]
        users = getattr(self.app, "user_data", {}).get("users", {})
        opener = getattr(self.app, "current_user_key", "")
        for key, data in users.items():
            if key == opener:
                continue
            role = data.get("permission", "")
            rank = {"E1 - Standard":1,"E2 - Erweitert":2,"E3 - Administrator":3,"E4 - System-Administrator":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}.get(role, 1)
            if rank >= 3:
                recipients.append((key, data.get("email", ""), data.get("full_name") or " ".join(x for x in [data.get("first_name", "").strip(), data.get("display_name", key).strip()] if x).strip() or key))
        return recipients

    def auto_close_mail_enabled(self):
        try:
            return bool(self.app.auto_close_mail_enabled())
        except Exception:
            return True

    def send_period_close_email_auto(self):
        if not self.auto_close_mail_enabled():
            self.data.setdefault("close_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "sent": False, "skipped": True, "reason": "Auto-Mail deaktiviert"})
            return True
        recipients = self.e3_e4_recipients()
        missing = [name for key, email, name in recipients if not email]
        send_to = [(key, email, name) for key, email, name in recipients if email]
        if not send_to:
            self.data.setdefault("close_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "sent": False, "missing": missing, "error": "Keine Empfängeradresse"})
            messagebox.showwarning("Automatische E-Mail", "Der Zeitraum wurde abgeschlossen, aber es konnte keine Abschluss-Mail versendet werden, weil keine E3/E4-E-Mail-Adresse hinterlegt ist.")
            return False
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.To = ";".join(email for key, email, name in send_to)
            mail.Subject = f"Abschluss {self.close_type_label()}: {period_label(self.period)}"
            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} wurde von {self.current_user_full_name()} abgeschlossen.\n\n"
                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")
            mail.Send()
            self.data.setdefault("close_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "recipients": [email for _, email, _ in send_to], "missing": missing, "sent": True})
            return True
        except Exception as exc:
            self.data.setdefault("close_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": missing})
            messagebox.showwarning("Automatische E-Mail", f"Der Zeitraum wurde abgeschlossen, aber die Abschluss-Mail konnte nicht automatisch versendet werden:\n\n{exc}")
            return False

    def send_reopen_email_auto(self, reason):
        recipients = self.e3_e4_recipients()
        missing = [name for key, email, name in recipients if not email]
        send_to = [(key,email,name) for key,email,name in recipients if email]
        if not send_to:
            messagebox.showerror("Wiederöffnung", "Die Pflichtbenachrichtigung konnte nicht versendet werden, weil keine E-Mail-Adresse für E3/E4-Empfänger hinterlegt ist.")
            return False
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.To = ";".join(email for key,email,name in send_to)
            mail.Subject = f"Wiederöffnung {self.close_type_label()}: {period_label(self.period)}"
            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} wurde von {self.current_user_full_name()} wieder geöffnet.\n\n"
                         f"Begründung:\n{reason}\n\n"
                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")
            mail.Send()
            self.data.setdefault("reopen_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "recipients": [email for _,email,_ in send_to], "missing": missing, "sent": True})
            return True
        except Exception as exc:
            self.data.setdefault("reopen_email_log", []).append({"timestamp": datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": missing})
            messagebox.showerror("Wiederöffnung", f"Die Pflichtbenachrichtigung konnte nicht automatisch über Outlook versendet werden. Der Zeitraum wurde nicht geöffnet.\n\n{exc}")
            return False

    def ask_reopen_reason(self):
        result = {"reason": None}
        win = tk.Toplevel(self.root); win.title("Zeitraum öffnen"); win.configure(bg=COLORS["bg"]); win.geometry("560x300"); win.transient(self.root); win.grab_set()
        tk.Label(win, text="Begründung der Wiederöffnung", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=14, pady=(14,6))
        tk.Label(win, text="Bitte gib eine Begründung ein. Ohne Begründung kann der Zeitraum nicht wieder geöffnet werden.", bg=COLORS["bg"], fg=COLORS["text2"], wraplength=520, justify="left").pack(anchor="w", padx=14, pady=(0,8))
        txt = tk.Text(win, height=7, bg="white", fg=COLORS["text"], relief="solid", bd=1); txt.pack(fill="both", expand=True, padx=14, pady=(0,10))
        def ok():
            val = txt.get("1.0", "end").strip()
            if not val:
                messagebox.showwarning("Zeitraum öffnen", "Bitte eine Begründung eingeben."); return
            result["reason"] = val; win.destroy()
        footer=tk.Frame(win,bg=COLORS["bg"]); footer.pack(fill="x", padx=14, pady=(0,12))
        tk.Button(footer,text="Öffnen",command=ok,bg=COLORS["blue"],fg="white",bd=0,padx=14,pady=7).pack(side="right")
        tk.Button(footer,text="Abbrechen",command=win.destroy,bg=COLORS["header"],fg=COLORS["text"],bd=0,padx=14,pady=7).pack(side="right",padx=(0,8))
        win.wait_window(); return result["reason"]

    def toggle_period_close(self):
        self.ensure_close_metadata()
        if not self.can_toggle_period_close():
            messagebox.showwarning("Berechtigung", "Für diese Aktion ist mindestens E3 erforderlich."); return
        if self.data.get("closed"):
            reason = self.ask_reopen_reason()
            if not reason: return
            if not self.send_reopen_email_auto(reason): return
            self.data["closed"] = False
            self.data["reopened_once"] = True
            self.log_period_event("opened", reason=reason)
            self.save(); self.render_dashboard(); return
        if not self.is_after_cutoff():
            messagebox.showinfo("Zeitraum abschließen", "Abschluss erst nach Ablauf des Abschluss-Stichtags möglich."); return
        stats = calc_stats(self.tasks())
        msg = f"{period_label(self.period)} wirklich abschließen?\n\nNach dem Abschluss sind keine Änderungen mehr möglich."
        if stats.get("open") or stats.get("in_progress"):
            msg += f"\n\nHinweis: Es sind noch {stats.get('open',0)} Aufgaben offen und {stats.get('in_progress',0)} in Bearbeitung."
        if not messagebox.askyesno("Zeitraum abschließen", msg): return
        self.data["closed"] = True
        self.data["closed_at"] = datetime.now().isoformat(timespec="seconds")
        self.data["closed_by"] = self.current_user_full_name()
        self.data["closed_by_key"] = getattr(self.app, "current_user_key", "")
        self.log_period_event("closed")
        self.send_period_close_email_auto()
        self.save(); self.render_dashboard()

    def show_change_log(self):
        self.ensure_close_metadata()
        win=tk.Toplevel(self.root); win.title("Änderungsprotokoll"); win.configure(bg=COLORS["bg"]); win.geometry("1050x620")
        txt=tk.Text(win,bg="white",fg=COLORS["text"],wrap="word",font=zfont(self.app, 12)); txt.pack(fill="both",expand=True,padx=12,pady=12)
        txt.insert("end", f"Änderungsprotokoll {period_label(self.period)}\n\n")
        txt.insert("end", "Abschluss-/Wiederöffnungsprotokoll:\n")
        for e in self.data.get("close_events", []):
            txt.insert("end", f"- {format_datetime_de(e.get('timestamp'))} | {e.get('action')} | {e.get('user')} | {e.get('reason','')}\n")
        txt.insert("end", "\nÄnderungen:\n")
        for e in self.data.get("change_log", []):
            flag = " [nach Wiederöffnung]" if e.get("after_reopen") else ""
            txt.insert("end", f"- {format_datetime_de(e.get('timestamp'))} | {e.get('user')} | {e.get('action')} | {e.get('task_title')} | {e.get('field')}: {e.get('old')} -> {e.get('new')}{flag}\n")
        txt.config(state="disabled")

    def create_icon_button(self, parent, text, command, icon_key="lock", enabled=True, tooltip=""):
        photo = None
        try:
            photo = self.app.get_icon_photo(icon_key, 18, 18)
        except Exception:
            photo = None
        btn = tk.Button(parent, text=text, image=photo, compound="left" if photo else None, command=command if enabled else None, bg=COLORS["blue"] if enabled else "#CBD5E1", fg="white" if enabled else COLORS["text2"], bd=0, padx=10, pady=4, cursor="hand2" if enabled else "arrow", state="normal" if enabled else "disabled")
        if photo: btn.image = photo
        if tooltip:
            btn.bind("<Enter>", lambda e, b=btn: self.show_tooltip(b, tooltip)); btn.bind("<Leave>", lambda e: self.hide_tooltip())
        return btn
    def _counterpart_period_dir(self):
        return BASE_DIR.parent / "MonthlyClose" / "periods"
    def _load_target_period_data(self, period):
        path = self._counterpart_period_dir() / f"{period}.json"
        try: data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception: data = {}
        data.setdefault("period", period); data.setdefault("created_at", datetime.now().isoformat(timespec="seconds")); data.setdefault("closing_cutoff_date", self._target_period_end(period)); data.setdefault("team_members", {team: [] for team in TEAMS}); data.setdefault("tasks", [])
        return data
    def _save_target_period_data(self, period, data):
        d = self._counterpart_period_dir(); d.mkdir(parents=True, exist_ok=True); (d / f"{period}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    def _clone_task_for_counterpart(self, task, period):
        cloned = json.loads(json.dumps(task, ensure_ascii=False)); cloned["id"] = make_task_id(cloned.get("team", "Team"), int(datetime.now().strftime("%H%M%S%f")) % 1000000)
        cloned["status"] = STATUS_OPEN; cloned["done_at"] = None; cloned["done_by"] = None; cloned["attachments"] = []; cloned["comments"] = []; cloned["catalog_id"] = ""; cloned["recurring"] = bool(task.get("recurring", False)); cloned["transfer_source"] = f"{BASE_DIR.name}:{self.period}:{task.get('id','')}"; cloned["due_date"] = self._target_period_end(period)
        for sub in cloned.get("subtasks", []): sub["status"] = STATUS_OPEN
        return cloned
    def transfer_task_to_counterpart(self, task, target_period, all_following=False):
        periods = self._target_periods_from(target_period, all_following); source_key = f"{BASE_DIR.name}:{self.period}:{task.get('id','')}"; count = 0
        for period in periods:
            data = self._load_target_period_data(period); tasks = data.setdefault("tasks", []); existing = next((t for t in tasks if t.get("transfer_source") == source_key and not t.get("deleted")), None); cloned = self._clone_task_for_counterpart(task, period)
            if existing:
                keep = {"status": existing.get("status", STATUS_OPEN), "done_at": existing.get("done_at"), "done_by": existing.get("done_by"), "attachments": existing.get("attachments", []), "comments": existing.get("comments", [])}; existing.clear(); existing.update(cloned); existing.update(keep)
            else: tasks.append(cloned)
            self._save_target_period_data(period, data); count += 1
        messagebox.showinfo("Quartalsabschluss", f"Aufgabe wurde in {count} Monatsabschluss(e) übernommen.")
    def open_transfer_dialog(self, task):
            if not self.require_unlocked("Aufgabenübernahme ist nicht möglich"): return
            win = tk.Toplevel(self.root); win.title("In Monatsabschluss übernehmen"); win.configure(bg=COLORS["bg"]); win.transient(self.root); win.grab_set(); win.geometry("540x250")
            default_period = self._target_period_from_current(); mode_var = tk.StringVar(value="all")
            tk.Label(win, text="Aufgabe inklusive Unteraufgaben übernehmen", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=16, pady=(16, 10))
            tk.Radiobutton(win, text=f"In alle Monatsabschlusse ab {self._target_display(default_period)}", variable=mode_var, value="all", bg=COLORS["bg"], activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)
            tk.Radiobutton(win, text=f"In Monatsabschluss {self._target_display(default_period)}", variable=mode_var, value="single", bg=COLORS["bg"], activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)
            period_var = tk.StringVar(value=default_period); options = self._target_periods_from(default_period, True)
            menu = tk.OptionMenu(win, period_var, *options); menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0); menu.pack(anchor="w", padx=18, pady=(10, 0))
            btns = tk.Frame(win, bg=COLORS["bg"]); btns.pack(side="bottom", fill="x", padx=16, pady=14)
            tk.Button(btns, text="Übernehmen", command=lambda: (self.transfer_task_to_counterpart(task, period_var.get(), mode_var.get()=="all"), win.destroy()), bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="right", padx=6)
            tk.Button(btns, text="Abbrechen", command=win.destroy, bg=COLORS["line"], fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="right", padx=6)
    def propagate_team_members_to_related_periods(self):
        members = normalize_team_members(self.data)
        for period in list_periods():
            if period >= self.period:
                data = load_period(period); data["team_members"] = json.loads(json.dumps(members, ensure_ascii=False)); save_period(period, data)
        for period in self._target_periods_from(self._target_period_from_current(), True):
            data = self._load_target_period_data(period); data["team_members"] = json.loads(json.dumps(members, ensure_ascii=False)); self._save_target_period_data(period, data)

    def clear_frame(self):
        if hasattr(self.app, "active_scroll_canvas"):
            self.app.active_scroll_canvas = None
        for child in self.frame.winfo_children():
            child.destroy()

    def reload(self):
        self.data = apply_catalog_to_period(self.period)

    def save(self):
        self.ensure_close_metadata()
        self.ensure_task_ids()
        save_period(self.period, self.data)

    def tasks(self):
        return [t for t in self.data.get("tasks", []) if not t.get("deleted")]

    def team_tasks(self, team):
        return sorted(
            [t for t in self.tasks() if t.get("team") == team],
            key=lambda t: str(t.get("title", "")).casefold(),
        )

    def task_sort_key(self, task):
        return str(task.get("title", "")).casefold()

    def is_task_id_editor(self):
        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"
        return role in ("Administrator", "System-Administrator", "Wagnerm")

    def normalize_task_uid_value(self, value):
        raw = str(value or "").strip().upper().replace("[", "").replace("]", "").replace("AUFGABEN-ID", "").strip()
        raw = raw.replace(" ", "")
        if not raw:
            return ""
        for prefix in ("QMJ", "QM", "QJ", "MJ", "M", "Q", "J"):
            if raw.startswith(prefix):
                suffix = raw[len(prefix):]
                if suffix.isdigit():
                    return f"{prefix}{int(suffix):03d}"
                return raw
        if raw.isdigit():
            return f"{CLOSING_SCOPE}{int(raw):03d}"
        return raw

    def task_uid_display(self, task):
        uid = self.normalize_task_uid_value(task.get("task_uid", ""))
        return uid or ""

    def initial_uid_for_task(self, task):
        return INITIAL_TASK_IDS.get((normalize_team_name(task.get("team")), str(task.get("title") or "")), "")

    def all_period_files(self):
        ensure_storage()
        return sorted(PERIOD_DIR.glob("*.json"))

    def collect_used_task_uids(self, exclude_task=None):
        used = set()
        exclude_key = None
        if exclude_task:
            exclude_key = (self.normalize_task_uid_value(exclude_task.get("task_uid")), exclude_task.get("id"), exclude_task.get("title"), exclude_task.get("team"))
        for path in self.all_period_files():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for task in data.get("tasks", []):
                uid = self.normalize_task_uid_value(task.get("task_uid", ""))
                if not uid:
                    continue
                key = (uid, task.get("id"), task.get("title"), task.get("team"))
                if exclude_key and key == exclude_key:
                    continue
                used.add(uid)
        return used

    def next_free_task_uid(self):
        used = self.collect_used_task_uids()
        n = 1
        while True:
            candidate = f"{CLOSING_SCOPE}{n:03d}"
            if candidate not in used:
                return candidate
            n += 1

    def task_identity_key_for_initial_id(self, task):
        catalog_id = str(task.get("catalog_id") or "").strip()
        if catalog_id:
            return ("catalog", catalog_id)
        initial = self.initial_uid_for_task(task)
        if initial:
            return ("initial", initial)
        return ("local", normalize_team_name(task.get("team")), str(task.get("title") or "").strip().casefold())

    def ensure_task_ids(self):
        ensure_storage()
        known = {}
        used = set()
        for path in self.all_period_files():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            for task in data.get("tasks", []):
                uid = self.normalize_task_uid_value(task.get("task_uid", ""))
                initial_uid = self.initial_uid_for_task(task)
                if initial_uid and uid != initial_uid:
                    uid = initial_uid
                    task["task_uid"] = uid
                if uid:
                    known.setdefault(self.task_identity_key_for_initial_id(task), uid)
                    used.add(uid)
        next_num = 1
        def next_uid():
            nonlocal next_num
            while f"{CLOSING_SCOPE}{next_num:03d}" in used:
                next_num += 1
            uid = f"{CLOSING_SCOPE}{next_num:03d}"
            used.add(uid); next_num += 1
            return uid
        for path in self.all_period_files():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            changed = False
            for task in data.get("tasks", []):
                initial_uid = self.initial_uid_for_task(task)
                uid = self.normalize_task_uid_value(task.get("task_uid", ""))
                if initial_uid:
                    uid = initial_uid
                if not uid:
                    uid = known.setdefault(self.task_identity_key_for_initial_id(task), next_uid())
                if task.get("task_uid") != uid:
                    task["task_uid"] = uid; changed = True
                for idx, sub in enumerate([s for s in task.get("subtasks", []) if not s.get("deleted")], start=1):
                    sub_uid = f"{uid}-u{idx}"
                    if sub.get("task_uid") != sub_uid:
                        sub["task_uid"] = sub_uid; changed = True
            if changed:
                save_period(path.stem, data)
                if path.stem == self.period:
                    self.data = data

    def archive_task_uid_change(self, task, old_uid, new_uid):
        if not old_uid or old_uid == new_uid:
            return
        archive_path = BASE_DIR / "task_id_archive.json"
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {"entries": []}
        except Exception:
            archive = {"entries": []}
        archive.setdefault("entries", []).append({
            "old_task_uid": old_uid,
            "new_task_uid": new_uid,
            "title": task.get("title", ""),
            "team": task.get("team", ""),
            "deactivation_date": datetime.now().isoformat(timespec="seconds"),
            "changed_by": getattr(self.app, "current_user_display", "") or getattr(self.app, "current_user_key", ""),
        })
        archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")

    def task_match_key(self, task):
        uid = self.normalize_task_uid_value(task.get("task_uid", ""))
        if uid:
            return ("uid", uid)
        catalog_id = str(task.get("catalog_id") or "").strip()
        if catalog_id:
            return ("catalog", catalog_id)
        return ("task", str(task.get("id") or "").strip(), normalize_team_name(task.get("team")), str(task.get("title") or "").strip().casefold())

    def get_expand_key(self, task):
        return self.normalize_task_uid_value(task.get("task_uid", "")) or f"{task.get('id','')}|{task.get('team','')}|{task.get('title','')}"

    def ask_delegate_scope(self, item, parent_task=None):
        if parent_task is not None:
            return "current"
        result = {"scope": None}
        win = tk.Toplevel(self.root)
        win.title("Zuständigkeit ändern")
        win.configure(bg=COLORS["bg"])
        win.transient(self.root); win.grab_set(); win.geometry("500x205")
        tk.Label(win, text="Zuständigkeit ändern", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(win, text="Soll die Zuständigkeit nur für diesen Zeitraum oder permanent für alle Folgezeiträume geändert werden?", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), wraplength=455, justify="left").pack(anchor="w", padx=16, pady=(0, 12))
        frame = tk.Frame(win, bg=COLORS["bg"]); frame.pack(fill="x", padx=16)
        def choose(scope): result["scope"] = scope; win.destroy()
        tk.Button(frame, text="Nur dieser Zeitraum", command=lambda: choose("current"), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))
        tk.Button(frame, text="Permanent für Folgezeiträume", command=lambda: choose("permanent"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))
        tk.Button(frame, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")
        win.wait_window()
        return result["scope"]

    def apply_delegate_to_following_periods(self, task_uid, owner_name, owner_user_key):
        changed_periods = 0
        for period in self.following_periods():
            data = load_period(period)
            changed = False
            for task in data.get("tasks", []):
                if self.normalize_task_uid_value(task.get("task_uid")) == task_uid:
                    task["owner"] = owner_name
                    task["owner_user_key"] = owner_user_key
                    for sub in task.get("subtasks", []):
                        sub["owner"] = owner_name
                        sub["owner_user_key"] = owner_user_key
                    changed = True
            if changed:
                save_period(period, data)
                changed_periods += 1
        return changed_periods

    def close_type_label(self):
        scope = globals().get("CLOSING_SCOPE", "")
        return "Monatsabschluss" if scope == "M" else "Quartalsabschluss" if scope == "Q" else "Jahresabschluss" if scope == "J" else "Abschluss"

    def recipient_email_for_user(self, user_key):
        if not user_key:
            return ""
        try:
            return self.app.user_data.get("users", {}).get(user_key, {}).get("email", "")
        except Exception:
            return ""

    def send_delegation_email(self, user_key, recipient_name, task_title, scope):
        email = self.recipient_email_for_user(user_key)
        if not email:
            messagebox.showwarning("Delegierung", f"Für {recipient_name} ist keine E-Mail-Adresse in der Benutzerverwaltung hinterlegt. Die Delegierung wurde gespeichert, aber es konnte keine E-Mail vorbereitet werden.")
            return
        delegated_by = getattr(self.app, "current_user_display", "") or getattr(self.app, "current_user_key", "") or "FiBu Mate"
        period_text = period_label(self.period)
        close_type = self.close_type_label()
        if scope == "permanent":
            scope_text = "bis auf Weiteres"
        else:
            scope_text = f"für den Zeitraum {period_text}"
        subject = f"Delegierung {close_type}: {task_title}"
        body = (
            f"Hallo {recipient_name},\n\n"
            f"die Zuständigkeit der {close_type}-Aufgabe {task_title} wurde an dich von {delegated_by} {scope_text} delegiert.\n\n"
            "Bitte bestätige die Kenntnisnahme per Antwort.\n\n"
            "Vielen Dank :)"
        )
        try:
            webbrowser.open("mailto:" + quote(email) + "?subject=" + quote(subject) + "&body=" + quote(body))
        except Exception as exc:
            messagebox.showerror("Delegierung", f"Die E-Mail zur Delegierung konnte nicht vorbereitet werden:\n\n{exc}")

    def sync_current_as_template_to_following_periods(self):
        if not self.can_edit(): return
        following = self.following_periods()
        if not following:
            messagebox.showinfo("Vorlage verwenden", "Es sind keine Folgezeiträume vorhanden.")
            return
        if not messagebox.askyesno("Zeitraum als Vorlage verwenden", f"{period_label(self.period)} als Vorlage für alle Folgezeiträume verwenden?\n\nAufgabenstruktur, Zuständigkeiten, Fälligkeiten und Unteraufgaben werden anhand der Aufgaben-ID übertragen. Status, Kommentare und Anlagen bleiben bei bereits vorhandenen Aufgaben erhalten."):
            return
        self.ensure_task_ids()
        source = [json.loads(json.dumps(t, ensure_ascii=False)) for t in self.tasks()]
        source_by_uid = {self.normalize_task_uid_value(t.get("task_uid")): t for t in source if self.normalize_task_uid_value(t.get("task_uid"))}
        updated = 0
        for period in following:
            data = load_period(period)
            old_by_uid = {self.normalize_task_uid_value(t.get("task_uid")): t for t in data.get("tasks", []) if self.normalize_task_uid_value(t.get("task_uid"))}
            new_tasks = []
            for uid, task in source_by_uid.items():
                cloned = json.loads(json.dumps(task, ensure_ascii=False))
                old = old_by_uid.get(uid)
                if old:
                    for keep in ("status", "done_at", "done_by", "attachments", "comments"):
                        cloned[keep] = old.get(keep, cloned.get(keep))
                    old_subs = {self.normalize_task_uid_value(s.get("task_uid")): s for s in old.get("subtasks", [])}
                    for sub in cloned.get("subtasks", []):
                        old_sub = old_subs.get(self.normalize_task_uid_value(sub.get("task_uid")))
                        if old_sub:
                            for keep in ("status", "done_at", "done_by", "attachments", "comments"):
                                sub[keep] = old_sub.get(keep, sub.get(keep))
                cloned["due_date"] = resolve_due_date(cloned, data, period)
                new_tasks.append(cloned)
            data["tasks"] = new_tasks
            data["template_source_period"] = self.period
            data["template_updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_period(period, data)
            updated += 1
        self.reload()
        messagebox.showinfo("Vorlage verwenden", f"Folgezeiträume aktualisiert: {updated}")
        self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def _pdf_escape(self, text):
        return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def write_simple_pdf(self, path, title, rows):
        lines = [title, ""]
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))
        pages = []
        for start in range(0, len(lines), 42):
            chunk = lines[start:start+42]
            ops = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]
            for line in chunk:
                ops.append(f"({self._pdf_escape(line[:150])}) Tj")
                ops.append("T*")
            ops.append("ET")
            pages.append("\n".join(ops).encode("latin-1", "replace"))
        objects = []
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        kids = " ".join(f"{3+i*2} 0 R" for i in range(len(pages)))
        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
        for i, content in enumerate(pages):
            content_obj = 4 + i*2
            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 R >>".encode())
            objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
        pdf = bytearray(b"%PDF-1.4\n")
        offsets = []
        for idx, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf.extend(f"{idx} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
        for off in offsets:
            pdf.extend(f"{off:010d} 00000 n \n".encode())
        pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
        Path(path).write_bytes(bytes(pdf))

    def create_simple_pdf(self, title, rows):
        path = filedialog.asksaveasfilename(title="PDF speichern", defaultextension=".pdf", filetypes=[("PDF-Dateien", "*.pdf")], initialfile=title.replace(" ", "_").replace("/", "-") + ".pdf")
        if not path: return
        try:
            self.write_simple_pdf(path, title, rows)
            if messagebox.askyesno("PDF erstellt", "PDF wurde erstellt. Jetzt öffnen?"):
                try:
                    os.startfile(path)
                except Exception:
                    try: subprocess.Popen(["xdg-open", path])
                    except Exception: pass
        except Exception as exc:
            messagebox.showerror("PDF erstellen", f"PDF konnte nicht erstellt werden:\n\n{exc}")

    def create_close_report(self):
        self.ensure_close_metadata()
        with_signature = messagebox.askyesno("Abschlussbericht", f"Bericht {period_label(self.period)} mit Signatur- und Freigabefeld erstellen?\n\nJa = mit Signatur-/Freigabefeld\nNein = ohne Signatur-/Freigabefeld")
        default_name = f"Abschlussbericht_{self.close_type_label()}_{period_label(self.period).replace(' ', '_').replace('/', '-')}_{date.today().isoformat()}.pdf"
        path = filedialog.asksaveasfilename(title="Bericht-PDF speichern", defaultextension=".pdf", filetypes=[("PDF-Dateien", "*.pdf")], initialfile=default_name)
        if not path: return
        try:
            self.create_reportlab_pdf(path, with_signature)
        except Exception as exc:
            try:
                rows = self.build_report_rows()
                self.write_simple_pdf(path, f"Abschlussbericht {self.close_type_label()} {period_label(self.period)}", rows)
            except Exception as fallback_exc:
                messagebox.showerror("Abschlussbericht", f"Bericht konnte nicht erstellt werden:\n\n{exc}\n\nFallback fehlgeschlagen:\n{fallback_exc}")
                return
        if messagebox.askyesno("Bericht-PDF wurde erstellt", "Bericht-PDF wurde erstellt. Jetzt öffnen?"):
            try: os.startfile(path)
            except Exception:
                try: subprocess.Popen(["xdg-open", path])
                except Exception: pass

    def build_report_rows(self):
        rows = [["Abschnitt", "Information"]]
        rows.append(["Bericht", f"Abschlussbericht {self.close_type_label()} {period_label(self.period)}"])
        rows.append(["Status", "Abgeschlossen" if self.data.get("closed") else "Nicht abgeschlossen"])
        rows.append(["Abschluss-Stichtag", format_date_de(self.data.get("closing_cutoff_date"))])
        stats = calc_stats(self.tasks())
        rows.append(["Management Summary", f"{stats['done']} erledigt, {stats['open']} offen, {stats['in_progress']} in Bearbeitung, {stats['overdue']} überfällig"])
        for task in self.tasks():
            rows.append([task.get("task_uid", ""), f"{task.get('title','')} | {task.get('owner','')} | {due_rule_text(task)} {format_date_de(task.get('due_date'))} | {task.get('status','')}"])
            for c in task.get("comments", []): rows.append(["Kommentar", str(c)])
            for a in task.get("attachments", []): rows.append(["Anlage", str(a)])
        return rows

    def create_reportlab_pdf(self, path, with_signature=False):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4*cm, leftMargin=1.4*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
        styles = getSampleStyleSheet()
        dark_blue = colors.HexColor("#1F4E79")
        styles.add(ParagraphStyle(name="FMTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, textColor=dark_blue, spaceAfter=10))
        styles.add(ParagraphStyle(name="FMHead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, textColor=dark_blue, spaceBefore=10, spaceAfter=6))
        styles.add(ParagraphStyle(name="FMText", parent=styles["BodyText"], fontName="Helvetica", fontSize=11, leading=14))
        styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10))
        story=[]
        story.append(Paragraph(f"Abschlussbericht {self.close_type_label()} {period_label(self.period)}", styles["FMTitle"]))
        status = "Abgeschlossen" if self.data.get("closed") else "Nicht abgeschlossen"
        head = [["Berichtstyp", self.close_type_label()], ["Zeitraum", period_label(self.period)], ["Abschluss-Stichtag", format_date_de(self.data.get("closing_cutoff_date"))], ["Status", status], ["Erstellt durch", self.current_user_full_name()], ["Erstellt am", datetime.now().strftime("%d.%m.%Y %H:%M")]]
        if self.data.get("closed_at"): head.append(["Zuletzt abgeschlossen", f"{format_datetime_de(self.data.get('closed_at'))} durch {self.data.get('closed_by','')}"])
        t=Table(head, colWidths=[5*cm, 11*cm]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#D9EAF7")),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story += [t, Spacer(1,8)]
        stats=calc_stats(self.tasks())
        story.append(Paragraph("Management Summary", styles["FMHead"]))
        story.append(Paragraph(f"Gesamtaufgaben: {stats['total']} | Erledigt: {stats['done']} | Offen: {stats['open']} | In Bearbeitung: {stats['in_progress']} | Überfällig: {stats['overdue']} | Kritisch: {stats['critical']}", styles["FMText"]))
        story.append(Paragraph("Abschlussprotokoll", styles["FMHead"]))
        events=[["Zeitpunkt","Aktion","Benutzer","Begründung"]]+[[format_datetime_de(e.get("timestamp")), e.get("action",""), e.get("user",""), e.get("reason","")] for e in self.data.get("close_events", [])]
        story.append(Table(events, repeatRows=1, colWidths=[3.2*cm,2.5*cm,4*cm,6.3*cm], style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))
        story.append(Paragraph("Teamübersicht", styles["FMHead"]))
        team_rows=[["Team","Gesamt","Erledigt","Offen","In Bearbeitung","Unteraufgaben"]]
        for team in TEAMS:
            tasks=[t for t in self.tasks() if t.get("team")==team and not t.get("deleted")]
            subs_done=sum(sum(1 for s in t.get("subtasks",[]) if s.get("status")==STATUS_DONE and not s.get("deleted")) for t in tasks)
            subs_all=sum(sum(1 for s in t.get("subtasks",[]) if not s.get("deleted")) for t in tasks)
            team_rows.append([team,len(tasks),sum(1 for t in tasks if t.get("status")==STATUS_DONE),sum(1 for t in tasks if t.get("status")==STATUS_OPEN),sum(1 for t in tasks if t.get("status")==STATUS_IN_PROGRESS),f"{subs_done}/{subs_all}" if subs_all else ""])
        story.append(Table(team_rows, repeatRows=1, style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))
        story.append(Paragraph("Aufgaben und Aufgabengruppen", styles["FMHead"]))
        for i,task in enumerate(self.tasks(),1):
            is_group=bool([s for s in task.get("subtasks",[]) if not s.get("deleted")])
            label="Aufgabengruppe" if is_group else "Aufgabe"
            critical = task.get("deadline_type")=="gesetzlich" or task.get("priority")=="kritisch"
            story.append(Paragraph(f"{i}. {label}: {task.get('title','')} ({task.get('task_uid','')})", styles["FMHead" if critical else "FMText"]))
            story.append(Paragraph(f"Zuständigkeit: {task.get('owner','')} | Fälligkeit: {format_date_de(task.get('due_date'))} ({due_rule_text(task)}) | Status: {task.get('status','')} | Erledigt: {format_datetime_de(task.get('done_at'))}", styles["FMText"]))
            if 'z4' in task.get('title','').casefold() or 'zm-' in task.get('title','').casefold() or 'zm meldung' in task.get('title','').casefold() or 'z5a' in task.get('title','').casefold():
                txt = f"<b><i>{task.get('title','')} erfolgt am {format_datetime_de(task.get('done_at'))}.</i></b>" if task.get('status')==STATUS_DONE else f"<b><i>{task.get('title','')} wurde im Zeitraum nicht als erledigt markiert.</i></b>"
                story.append(Paragraph(txt, styles["FMText"]))
            comments=task.get("comments",[])
            if comments:
                story.append(Paragraph("Kommentare / Notizen", styles["FMText"]))
                for c in comments:
                    story.append(Paragraph(str(c), styles["Small"]))
            attachments=task.get("attachments",[])
            if attachments:
                rows=[["Anlagenname","Anlagenpfad"]]
                for a in attachments:
                    if isinstance(a,dict): rows.append([a.get("name") or Path(a.get("path","")).name, a.get("path","") + (f" [{a.get('created_at','')}]" if a.get('created_at') else "")])
                    else: rows.append([Path(str(a)).name, str(a)])
                story.append(Paragraph(f"Anlagen: {len(attachments)}", styles["FMText"])); story.append(Table(rows, style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])))
            for j,sub in enumerate([s for s in task.get("subtasks",[]) if not s.get("deleted")],1):
                story.append(Paragraph(f"{i}.{j} Aufgabe: {sub.get('title','')} ({sub.get('task_uid','')})", styles["FMText"]))
                story.append(Paragraph(f"Zuständigkeit: {sub.get('owner',task.get('owner',''))} | Status: {sub.get('status','')}", styles["Small"]))
        open_tasks=[t for t in self.tasks() if t.get("status")!=STATUS_DONE and not t.get("deleted")]
        story.append(Paragraph("Offene Punkte", styles["FMHead"]))
        if open_tasks:
            for tsk in open_tasks: story.append(Paragraph(f"- {tsk.get('title','')} ({tsk.get('task_uid','')}), zuständig: {tsk.get('owner','')}, Status: {tsk.get('status','')}", styles["FMText"]))
        else: story.append(Paragraph("Keine offenen Punkte.", styles["FMText"]))
        critical_tasks=[t for t in self.tasks() if (t.get("deadline_type")=="gesetzlich" or t.get("priority")=="kritisch" or warning_level(t) in ("overdue","today","orange")) and not t.get("deleted")]
        story.append(Paragraph("Kritische oder gesetzliche Fristen", styles["FMHead"]))
        for tsk in critical_tasks: story.append(Paragraph(f"- <b>{tsk.get('title','')}</b> | {format_date_de(tsk.get('due_date'))} | {tsk.get('status','')}", styles["FMText"]))
        changes=[c for c in self.data.get("change_log",[]) if c.get("after_reopen")]
        story.append(Paragraph("Nachträgliche Änderungen nach Wiederöffnung", styles["FMHead"]))
        if changes:
            rows=[["Zeitpunkt","Benutzer","Aufgabe","Feld","Alt","Neu"]]+[[format_datetime_de(c.get("timestamp")),c.get("user",""),c.get("task_title",""),c.get("field",""),c.get("old",""),c.get("new","")] for c in changes]
            story.append(Table(rows, repeatRows=1, colWidths=[2.7*cm,3*cm,3.5*cm,2.3*cm,2.2*cm,2.2*cm], style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#FDE68A")),("FONTSIZE",(0,0),(-1,-1),7)])))
        else: story.append(Paragraph("Keine nachträglichen Änderungen dokumentiert.", styles["FMText"]))
        if with_signature:
            story += [Spacer(1,18), Paragraph("Signatur- und Freigabefeld", styles["FMHead"]), Spacer(1,16), Paragraph("Erstellt durch: _______________________ Datum: ___________", styles["FMText"]), Spacer(1,14), Paragraph("Geprüft durch: ________________________ Datum: ___________", styles["FMText"]), Spacer(1,14), Paragraph("Freigegeben durch: ____________________ Datum: ___________", styles["FMText"])]
        version = getattr(self.app, "version_label_text", lambda: "")()
        footer = f"Bericht automatisch erstellt von {self.current_user_full_name()} am {datetime.now().strftime('%d.%m.%Y %H:%M')} mit FiBu Mate {version}."
        story.append(Spacer(1,10)); story.append(Paragraph(footer, styles["Small"]))
        doc.build(story)

    def create_task_id_report(self, task):
        uid = self.normalize_task_uid_value(task.get("task_uid"))
        rows = [["Zeitraum", "Aufgabe", "Zuständig", "Status", "Erledigt am", "Anlagen", "Kommentare"]]
        for path in self.all_period_files():
            try: data = json.loads(path.read_text(encoding="utf-8"))
            except Exception: continue
            for t in data.get("tasks", []):
                if self.normalize_task_uid_value(t.get("task_uid")) == uid:
                    rows.append([period_label(path.stem), t.get("title", ""), t.get("owner", ""), t.get("status", ""), format_date_de(t.get("done_at", "")), str(len(t.get("attachments", []))), str(len(t.get("comments", [])))])
        self.create_simple_pdf(f"Gesamtbericht Aufgaben-ID {uid}", rows)

    def task_match_key(self, task):
        catalog_id = str(task.get("catalog_id") or "").strip()
        if catalog_id:
            return ("catalog", catalog_id)
        return (
            "task",
            str(task.get("id") or "").strip(),
            normalize_team_name(task.get("team")),
            str(task.get("title") or "").strip().casefold(),
        )

    def find_task_index_exact(self, task):
        tasks = self.data.get("tasks", [])
        for idx, candidate in enumerate(tasks):
            if candidate is task:
                return idx
        key = self.task_match_key(task)
        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and self.task_match_key(candidate) == key]
        return matches[0] if len(matches) == 1 else None

    def following_periods(self):
        return [period for period in list_periods() if period > self.period]

    def remove_task_from_data_by_key(self, data, key):
        tasks = data.get("tasks", [])
        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and self.task_match_key(candidate) == key]
        if len(matches) == 1:
            tasks.pop(matches[0])
            data["tasks"] = tasks
            return "removed"
        if len(matches) > 1:
            return "ambiguous"
        return "missing"

    def ask_delete_scope(self, task):
        result = {"scope": None}
        win = tk.Toplevel(self.root)
        win.title("Aufgabe löschen")
        win.configure(bg=COLORS["bg"])
        win.transient(self.root)
        win.grab_set()
        win.geometry("520x245")
        tk.Label(win, text="Aufgabe löschen", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        msg = f"Welche Zeiträume sollen bereinigt werden?\n\n{task.get('title', '')}"
        if task.get("attachments"):
            msg += "\n\nHinweis: Anlagen-Dateien bleiben im Anlagenordner erhalten; nur die Referenz in der Aufgabe wird entfernt."
        tk.Label(win, text=msg, bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), justify="left", wraplength=480).pack(anchor="w", padx=16, pady=(0, 14))
        buttons = tk.Frame(win, bg=COLORS["bg"])
        buttons.pack(fill="x", padx=16, pady=(0, 16))
        def choose(scope):
            result["scope"] = scope
            win.destroy()
        tk.Button(buttons, text="Nur aktueller Zeitraum", command=lambda: choose("current"), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0, 7))
        tk.Button(buttons, text="Aktueller und alle folgenden Zeiträume", command=lambda: choose("following"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0, 7))
        tk.Button(buttons, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")
        win.wait_window()
        return result["scope"]

    def delete_from_following_periods(self, task_key):
        removed = 0
        ambiguous = 0
        for period in self.following_periods():
            data = load_period(period)
            result = self.remove_task_from_data_by_key(data, task_key)
            if result == "removed":
                save_period(period, data)
                removed += 1
            elif result == "ambiguous":
                ambiguous += 1
        return removed, ambiguous

    def cleanup_following_periods(self):
            if not self.require_unlocked("Vorlage für Folgezeiträume ist nicht möglich"): return
            return self.sync_current_as_template_to_following_periods()

    def draw_progress(self, parent, percent, width=260, height=20, bg=None):
        bg = bg or parent.cget("bg")
        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)
        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")
        fill_w = int(width * max(0, min(100, percent)) / 100)
        if fill_w: c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), outline=progress_color(percent))
        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], font=zfont(self.app, 11, "bold"))
        return c

    def render_period_controls(self, parent):
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill="x", padx=24, pady=(10, 4))
        tk.Button(row, text="< vorherige(r) Quartal", command=lambda: self.change_period(add_period(self.period, -1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(side="left")
        periods = list_periods(); labels = {period_label(k): k for k in periods}; selected = tk.StringVar(value=period_label(self.period))
        menu = tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: self.change_period(labels[label]))
        menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0); menu.pack(side="left", padx=10)
        tk.Button(row, text="nächste(r) Quartal >", command=lambda: self.change_period(add_period(self.period, 1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(side="left")
        tk.Frame(row, bg=COLORS["bg"]).pack(side="left", fill="x", expand=True)
        if self.can_edit(): self.render_edit_button(row)

    def render_edit_button(self, parent):
        photo = self.get_close_icon_photo("1486504369-change-edit-options-pencil-settings-tools-write_81307.ico", 28, 28)
        btn = tk.Button(
            parent,
            text="" if photo else "Bearbeiten",
            image=photo if photo else "",
            command=self.toggle_edit_mode,
            bg=parent.cget("bg"),
            activebackground=parent.cget("bg"),
            fg=COLORS["blue"],
            bd=0,
            highlightthickness=0,
            padx=2,
            pady=2,
            cursor="hand2",
        )
        if photo:
            btn.image = photo
        btn.pack(side="right", padx=(8, 0))
        btn.bind("<Enter>", lambda _e: self.show_tooltip(btn, "Bearbeiten"))
        btn.bind("<Leave>", lambda _e: self.hide_tooltip())

    def create_delegate_button(self, parent, item, parent_task=None):
        photo = self.get_close_icon_photo("1904671-arrow-arrow-right-change-direction-next-page-right_122521.ico", 14, 14)
        btn = tk.Button(
            parent,
            text="Delegieren",
            image=photo if photo else "",
            compound="left" if photo else "none",
            command=lambda it=item, pt=parent_task: self.show_delegate_popup(it, pt),
            bg=COLORS["white"],
            activebackground=COLORS["header"],
            fg=COLORS["blue"],
            bd=1,
            relief="solid",
            padx=5,
            pady=2,
            cursor="hand2",
            font=zfont(self.app, 10, "bold"),
        )
        if photo:
            btn.image = photo
        return btn

    def show_delegate_popup(self, item, parent_task=None):
        if not self.can_edit():
            messagebox.showwarning("FiBu Mate", "Keine Berechtigung zum Delegieren.")
            return
        task_for_team = parent_task or item
        choices = self.user_choices()
        labels = []
        label_to_choice = {}
        current_key = item.get("owner_user_key", "")
        current_label = None
        for key, display in choices:
            label = display if not key else f"{display} ({key})"
            labels.append(label)
            label_to_choice[label] = (key, display)
            if key == current_key:
                current_label = label
        if not labels:
            messagebox.showwarning("FiBu Mate", "Keine Benutzer für die Delegierung vorhanden.")
            return
        if current_label is None:
            current_label = labels[0]
        win = tk.Toplevel(self.root)
        win.title("Zuständigkeit delegieren")
        win.configure(bg=COLORS["bg"])
        win.transient(self.root)
        win.grab_set()
        win.geometry("460x190")
        tk.Label(win, text="Zuständigkeit delegieren", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(win, text="Bitte neue Zuständigkeit wählen.", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        selected = tk.StringVar(value=current_label)
        menu = tk.OptionMenu(win, selected, *labels)
        menu.config(bg=COLORS["white"], fg=COLORS["text"], bd=1, highlightthickness=0)
        menu.pack(fill="x", padx=16, pady=(0, 14))
        def apply_delegate():
            user_key, display_name = label_to_choice[selected.get()]
            scope = self.ask_delegate_scope(item, parent_task)
            if not scope:
                return
            fallback_team = task_for_team.get("team", item.get("team", "Team"))
            owner_name = display_name if user_key else fallback_team
            targets = [item]
            if parent_task is None:
                targets += [sub for sub in item.get("subtasks", []) if not sub.get("deleted")]
            for target in targets:
                target["owner_user_key"] = user_key
                target["owner"] = owner_name
            self.save()
            changed = 0
            if scope == "permanent" and parent_task is None:
                uid = self.normalize_task_uid_value(item.get("task_uid"))
                changed = self.apply_delegate_to_following_periods(uid, owner_name, user_key)
            if user_key:
                self.send_delegation_email(user_key, display_name, task_for_team.get("title", item.get("title", "")), scope)
            if self.selected_team:
                self.render_team_detail(self.selected_team)
            win.destroy()
            if scope == "permanent":
                messagebox.showinfo("Delegierung", f"Permanente Delegierung übertragen. Folgezeiträume aktualisiert: {changed}")
        footer = tk.Frame(win, bg=COLORS["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(footer, text="Übernehmen", command=apply_delegate, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")
        tk.Button(footer, text="Abbrechen", command=win.destroy, bg=COLORS["header"], fg=COLORS["text"], bd=0, padx=14, pady=7, cursor="hand2").pack(side="right", padx=(0, 8))

    def show_tooltip(self, widget, text):
        self.hide_tooltip(); self.tooltip = tk.Toplevel(widget); self.tooltip.wm_overrideredirect(True); self.tooltip.geometry(f"+{widget.winfo_rootx() + 12}+{widget.winfo_rooty() + 34}"); tk.Label(self.tooltip, text=text, bg="#111827", fg="white", font=zfont(self.app, 11), padx=6, pady=3).pack()

    def hide_tooltip(self):
        if self.tooltip:
            try: self.tooltip.destroy()
            except Exception: pass
        self.tooltip = None

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def render_edit_tools(self, parent, team=None):
        if not (self.can_edit() and self.edit_mode): return
        row = tk.Frame(parent, bg=COLORS["edit_bg"], bd=1, relief="solid"); row.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")).pack(side="left", padx=10, pady=7)
        if team:
            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: self.open_task_dialog(team), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)
            tk.Button(row, text="Aufgaben allen vorhandenen Perioden zuweisen", command=self.apply_current_tasks_to_all_periods, bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)
            tk.Button(row, text="Diesen Zeitraum als Vorlage für Folgequartale verwenden", command=self.cleanup_following_periods, bg=COLORS["red"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)

    def change_period(self, period):
        if not period_allowed(period):
            messagebox.showinfo("Quartalsabschluss", "Dieser Zeitraum liegt außerhalb der freigegebenen Zeitraumlogik ab Q2 2026 bzw. außerhalb des zulässigen Geschäftsjahres.")
            return
        self.period = period; self.reload(); self.selected_team = None; self.render_dashboard()

    def save_cutoff_from_entry(self, entry_var=None):
        messagebox.showinfo(
            "FiBu Mate",
            "Der Abschluss-Stichtag wird zentral in der Stichtags- & Zuständigkeitspflege gepflegt.\n\n"
            "Eine manuelle Änderung in der Zeitraumsübersicht ist nicht mehr möglich."
        )

    def render_dashboard(self):
        self.ensure_close_metadata()
        old_cutoff = self.data.get("closing_cutoff_date", "")
        normalize_cutoff(self.data, self.period)
        if old_cutoff != self.data.get("closing_cutoff_date", ""):
            save_period(self.period, self.data)
            self.data = load_period(self.period)
        self.selected_team = None; self.clear_frame(); self.render_period_controls(self.frame); self.render_edit_tools(self.frame)
        stats = calc_stats(self.tasks())
        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); top.pack(fill="x", padx=24, pady=(8, 10))
        title_row = tk.Frame(top, bg=COLORS["white"]); title_row.pack(fill="x", padx=14, pady=(6, 2))
        tk.Label(title_row, text=f"Quartalsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 24, "bold")).pack(side="left")
        cutoff_text = format_date_de(self.data.get("closing_cutoff_date")) or "nicht gepflegt"
        tk.Label(title_row, text="Abschluss-Stichtag", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 12, "bold")).pack(side="left", padx=(24, 6))
        tk.Label(title_row, text=cutoff_text, bg="#F8FAFC", fg=COLORS["text"], font=zfont(self.app, 12, "bold"), relief="solid", bd=1, padx=8, pady=3).pack(side="left")
        toggle_text = f"{period_label(self.period)} {'öffnen' if self.is_period_closed() else 'abschließen'}"
        enabled = self.can_toggle_period_close() and (self.is_period_closed() or self.is_after_cutoff())
        tooltip = "Abschluss erst nach Ablauf des Abschluss-Stichtags möglich" if self.can_toggle_period_close() and not self.is_period_closed() and not self.is_after_cutoff() else ""
        self.create_icon_button(title_row, toggle_text, self.toggle_period_close, "unlock" if self.is_period_closed() else "lock", enabled, tooltip).pack(side="left", padx=(8,0))
        report_text = "vorläufigen Abschlussbericht erstellen" if not self.is_after_cutoff() and not self.is_period_closed() else "Abschlussbericht erstellen"
        tk.Button(title_row, text=report_text, command=self.create_close_report, bg=COLORS["white"], fg=COLORS["blue"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", padx=(8, 0))
        tk.Button(title_row, text="Änderungsprotokoll anzeigen", command=self.show_change_log, bg=COLORS["white"], fg=COLORS["text"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", padx=(8,0))
        status_text = self.close_status_text()
        if status_text:
            tk.Label(top, text=status_text, bg=COLORS["white"], fg=COLORS["orange"] if not self.is_period_closed() else COLORS["dark_green"], font=zfont(self.app, 12, "bold")).pack(anchor="w", padx=14, pady=(2,0))
        tk.Label(top, text=f"Gesamt: {stats['done']} erledigt / {stats['in_progress']} in Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", padx=14)
        holder = tk.Frame(top, bg=COLORS["white"]); holder.pack(anchor="w", padx=14, pady=(8, 10)); self.draw_progress(holder, stats["percent"], width=520, height=24, bg=COLORS["white"]).pack(side="left")
        self.render_warnings(self.frame)
        cards = tk.Frame(self.frame, bg=COLORS["bg"]); cards.pack(fill="both", expand=True, padx=24, pady=8)
        for idx, team in enumerate(TEAMS): self.render_team_card(cards, team, idx)

    def render_warnings(self, parent):
        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", "yellow") and t.get("status") != STATUS_DONE]
        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid"); box.pack(fill="x", padx=24, pady=(0, 8))
        if warnings:
            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=zfont(self.app, 14, "bold")).pack(anchor="w", padx=12, pady=(8, 3))
            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:
                tk.Label(box, text=f"- {task['title']} | {task['team']} | fällig am {format_date_de(task.get('due_date'))} | {task.get('deadline_type')}", bg=box["bg"], fg=COLORS["text"], font=zfont(self.app, 12)).pack(anchor="w", padx=20, pady=1)
        else:
            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], fg=COLORS["dark_green"], font=zfont(self.app, 13, "bold")).pack(anchor="w", padx=12, pady=8)

    def next_relevant_task(self, tasks):
        open_tasks = [t for t in tasks if t.get("status") != STATUS_DONE and t.get("deadline_type") != "keine"]
        return sorted(open_tasks, key=lambda t: parse_date(t.get("due_date", "9999-12-31")) or date.max)[0] if open_tasks else None

    def bind_click_recursive(self, widget, command):
        widget.bind("<Button-1>", lambda _e: command()); widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            if isinstance(child, (tk.Entry, tk.Text, tk.Button)): continue
            self.bind_click_recursive(child, command)

    def save_team_members_from_widget(self, team, widget):
        set_team_members_text(self.data, team, widget.get("1.0", "end")); self.save(); self.propagate_team_members_to_related_periods(); self.reload(); self.render_dashboard()

    def render_team_members_on_card(self, card, team):
        names = normalize_team_members(self.data).get(team, [])
        if self.edit_mode and self.can_edit():
            edit_box = tk.Text(card, height=3, width=42, bg="#F8FAFC", fg=COLORS["text"], relief="solid", bd=1); edit_box.insert("1.0", "\n".join(names)); edit_box.pack(anchor="w", padx=18, pady=(0, 6))
            tk.Button(card, text="Namen speichern", command=lambda t=team, w=edit_box: self.save_team_members_from_widget(t, w), bg=COLORS["blue"], fg="white", bd=0, padx=8, pady=3).pack(anchor="w", padx=18, pady=(0, 10))
        elif names:
            tk.Label(card, text=" • ".join(names), bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 12), wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, 12))

    def render_team_card(self, parent, team, idx):
        row, col = divmod(idx, 2); tasks = self.team_tasks(team); stats = calc_stats(tasks)
        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, "orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")
        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == "orange" else COLORS["line"]
        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", highlightbackground=border, highlightcolor=border, highlightthickness=2); card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1); parent.grid_rowconfigure(row, weight=1)
        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 19, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(card, text=f"{stats['done']} / {stats['total']} erledigt | offen: {stats['open']} | in Bearbeitung: {stats['in_progress']} | kritisch: {stats['critical']}", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", padx=18)
        holder = tk.Frame(card, bg=COLORS["white"]); holder.pack(anchor="w", padx=18, pady=(10, 8)); self.draw_progress(holder, stats["percent"], width=420, height=26, bg=COLORS["white"]).pack()
        nxt = self.next_relevant_task(tasks); txt = "Nächste Frist: keine relevanten offenen Fristen" if not nxt else f"Nächste Frist: {format_date_de(nxt.get('due_date'))} | {nxt.get('title')}"
        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and warning_level(nxt) in ("overdue", "today", "orange") else COLORS["text2"], font=zfont(self.app, 12, "bold")).pack(anchor="w", padx=18, pady=(0, 5))
        self.render_team_members_on_card(card, team); self.bind_click_recursive(card, lambda t=team: self.render_team_detail(t))

    def render_team_detail(self, team):
        self.selected_team = team; self.clear_frame(); self.render_period_controls(self.frame); self.render_edit_tools(self.frame, team=team); stats = calc_stats(self.team_tasks(team))
        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); head.pack(fill="x", padx=24, pady=(8, 10))
        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(head, text=f"{team} | Quartalsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 21, "bold")).pack(anchor="w", padx=12)
        tk.Label(head, text=f"Fortschritt: {stats['done']} / {stats['total']} erledigt | {stats['percent']}%", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", padx=12)
        bar = tk.Frame(head, bg=COLORS["white"]); bar.pack(anchor="w", padx=12, pady=(6, 10)); self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()
        self.render_task_table(team)

    def toggle_subtasks_visibility(self, task_id):
        if task_id in self.expanded_tasks:
            self.expanded_tasks.remove(task_id)
        else:
            self.expanded_tasks.add(task_id)
        self.render_team_detail(self.selected_team)

    def normalize_documentation_fields(self, item):
        item.setdefault("attachments", [])
        item.setdefault("comments", [])
        doc = item.get("documentation")
        if isinstance(doc, str):
            item["documentation"] = {"name": os.path.basename(doc), "path": doc, "updated_at": ""} if doc else {}
        elif not isinstance(doc, dict):
            item["documentation"] = {}
        clean_attachments = []
        for att in item.get("attachments", []):
            if isinstance(att, str):
                clean_attachments.append({"name": os.path.basename(att), "path": att, "comment": "", "added_at": ""})
            elif isinstance(att, dict):
                att.setdefault("name", os.path.basename(att.get("path", "")) or att.get("name", "Anlage"))
                att.setdefault("path", "")
                att.setdefault("comment", "")
                clean_attachments.append(att)
        item["attachments"] = clean_attachments
        return item

    def due_display_inline(self, task):
        date_text = format_date_de(task.get("due_date", ""))
        rule = due_rule_text(task)
        return f"{date_text} - {rule}" if rule else date_text

    def find_subtask(self, task_id, subtask_id):
        task = self.find_task(task_id)
        if not task:
            return None, None
        for sub in task.get("subtasks", []):
            if sub.get("id") == subtask_id and not sub.get("deleted"):
                self.normalize_documentation_fields(sub)
                return task, sub
        return task, None

    def documentation_count(self, item):
        self.normalize_documentation_fields(item)
        return 1 if item.get("documentation", {}).get("path") else 0

    def attachment_count(self, item):
        self.normalize_documentation_fields(item)
        return len([a for a in item.get("attachments", []) if a.get("path")])

    def get_close_icon_photo(self, icon_file, max_w=24, max_h=24):
        try:
            from PIL import Image, ImageTk
        except Exception:
            return None
        if not hasattr(self, "_icon_cache"):
            self._icon_cache = {}
        cache_key = (icon_file, int(max_w), int(max_h))
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]
        icon_dir = Path(__file__).resolve().parent.parent / "Imgs" / "Icons" if Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / "bin" / "Imgs" / "Icons"
        path = icon_dir / icon_file
        if not path.exists():
            return None
        try:
            img = Image.open(path).convert("RGBA")
            ow, oh = img.size
            scale = min(1, max_w / max(1, ow), max_h / max(1, oh))
            img = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))
            photo = ImageTk.PhotoImage(img)
            self._icon_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    def create_attachment_button(self, parent, item, command):
        frame = tk.Frame(parent, bg=parent.cget("bg"))
        inner = tk.Frame(frame, bg=parent.cget("bg"))
        inner.place(relx=0.5, rely=0.5, anchor="center")
        photo = self.get_close_icon_photo("-attach-file_90371.ico", 18, 18)
        btn = tk.Button(inner, text="" if photo else "📎", image=photo, command=command, bg=parent.cget("bg"), fg=COLORS["blue"], bd=0, cursor="hand2", padx=0, pady=0)
        if photo:
            btn.image = photo
        btn.pack(side="left", padx=(0, 3))
        tk.Label(inner, text=str(self.attachment_count(item)), bg=parent.cget("bg"), fg=COLORS["blue"], font=zfont(self.app, 12, "bold")).pack(side="left")
        return frame

    def draw_documentation_icon(self, canvas, has_documentation):
        canvas.delete("all")
        icon_file = "fileinterfacesymboloftextpapersheet_79740.ico" if has_documentation else "addfileinterfacesymbolofpapersheetwithtextlinesandplussign_79821.ico"
        photo = self.get_close_icon_photo(icon_file, 22, 22)
        if photo:
            canvas.create_image(16, 12, image=photo)
            canvas.image = photo
            return
        color = COLORS["blue"]
        # Fallback ohne blaue Kachel: kleines Dokument-/Plus-Symbol nur als Liniengrafik.
        canvas.create_rectangle(8, 3, 22, 21, outline=color, width=2)
        canvas.create_line(18, 3, 22, 7, fill=color, width=2)
        if has_documentation:
            for y in (9, 13, 17):
                canvas.create_line(11, y, 20, y, fill=color, width=2, capstyle="round")
        else:
            canvas.create_line(15, 9, 15, 18, fill=color, width=2, capstyle="round")
            canvas.create_line(10, 13, 20, 13, fill=color, width=2, capstyle="round")

    def create_documentation_button(self, parent, item, title, parent_task=None):
        has_doc = bool(item.get("documentation", {}).get("path"))
        bg = parent.cget("bg")
        btn = tk.Canvas(parent, width=32, height=24, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self.draw_documentation_icon(btn, has_doc)
        btn.bind("<Button-1>", lambda _e, it=item, t=title, pt=parent_task: self.show_documentation_popup(it, t, pt))
        return btn

    def show_documentation_popup(self, item, title, parent_task=None):
        self.normalize_documentation_fields(item)
        win = tk.Toplevel(self.root)
        win.title(f"Dokumentation - {title}")
        win.configure(bg=COLORS["bg"])
        win.geometry("720x270")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="Dokumentation", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        body = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        doc = item.get("documentation", {})
        name_var = tk.StringVar(value=doc.get("name", "Noch keine Dokumentation hinterlegt"))
        path_var = tk.StringVar(value=doc.get("path", ""))

        row = tk.Frame(body, bg=COLORS["white"])
        row.pack(fill="x", padx=12, pady=(14, 6))
        open_button = tk.Button(row, text="Dokumentation öffnen", command=lambda: self.open_attachment(path_var.get()), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6, state="normal" if path_var.get() else "disabled")
        open_button.pack(side="left")
        tk.Label(row, textvariable=name_var, bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 12), anchor="w").pack(side="left", padx=(10, 6), fill="x", expand=True)

        def refresh_after_change():
            if self.selected_team:
                self.render_team_detail(self.selected_team)

        def choose_documentation():
            selected = filedialog.askopenfilename(title="Dokumentation auswählen")
            if not selected:
                return
            item["documentation"] = {"name": os.path.basename(selected), "path": selected, "updated_at": datetime.now().isoformat(timespec="seconds")}
            self.save()
            name_var.set(os.path.basename(selected))
            path_var.set(selected)
            refresh_after_change()
            win.destroy()

        def remove_documentation():
            if not path_var.get():
                return
            if not messagebox.askyesno("Dokumentation entfernen", "Dokumentation entfernen?", parent=win):
                return
            item["documentation"] = {}
            self.save()
            name_var.set("Noch keine Dokumentation hinterlegt")
            path_var.set("")
            refresh_after_change()
            win.destroy()

        if path_var.get():
            trash_photo = self.get_close_icon_photo("biggarbagebin_121980.ico", 20, 20)
            delete_btn = tk.Button(row, text="" if trash_photo else "🗑", image=trash_photo, command=remove_documentation, bg=COLORS["white"], fg=COLORS["red"], bd=0, padx=2, pady=2, cursor="hand2")
            if trash_photo:
                delete_btn.image = trash_photo
            delete_btn.pack(side="right", padx=(6, 0))

        change = tk.Label(body, text="Dokumentationspfad ändern" if path_var.get() else "Dokumentation anhängen", bg=COLORS["white"], fg=COLORS["blue"], font=zfont(self.app, 12, None, underline=True), cursor="hand2")
        change.pack(anchor="w", padx=12, pady=(4, 10))
        change.bind("<Button-1>", lambda _e: choose_documentation())
        tk.Label(body, text="Hinweis: Die Dokumentation ist für Aufgabenbeschreibungen bzw. Leitfäden vorgesehen. Ergebnisse und Bearbeitungskommentare bitte unter Anlagen pflegen.", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=660, justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        tk.Button(win, text="Schließen", command=win.destroy, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))

    def render_task_table(self, team):
        outer = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        scroll_canvas = tk.Canvas(outer, bg=COLORS["white"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)
        xscrollbar = tk.Scrollbar(outer, orient="horizontal", command=scroll_canvas.xview)
        table = tk.Frame(scroll_canvas, bg="#E4EAF1")  # dezente Spaltentrennlinien
        table_window = scroll_canvas.create_window((0, 0), window=table, anchor="nw")

        def update_scrollregion(_event=None):
            table.update_idletasks()
            target_width = max(scroll_canvas.winfo_width(), table.winfo_reqwidth())
            scroll_canvas.itemconfigure(table_window, width=max(1, target_width))
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        table.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<MouseWheel>", on_mousewheel)
        table.bind("<MouseWheel>", on_mousewheel)
        scroll_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)
        xscrollbar.pack(side="bottom", fill="x")
        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.app.active_scroll_canvas = scroll_canvas

        headers = ["Status", "Aufgabe", "Dokumentation", "Zuständig", "Fällig", "Fristart", "Priorität", "Wiederkehrend", "Anlagen", "Aktion"]
        if self.edit_mode and self.can_edit():
            headers.append("Bearbeiten")
        for col, h in enumerate(headers):
            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=zfont(self.app, 12, "bold"), padx=6, pady=6).grid(row=0, column=col, sticky="nsew")
        row_idx = 1
        for task in self.team_tasks(team):
            sync_parent_status_from_subtasks(task)
            self.normalize_documentation_fields(task)
            for sub in task.get("subtasks", []):
                self.normalize_documentation_fields(sub)
            row_idx = self.render_task_row(table, row_idx, task, headers)

        # Spaltenbreiten: Aufgabe und Zuständig etwas reduziert; Dokumentation schmal; Fristart/Priorität/Anlagen erhalten mehr Raum.
        min_sizes = {0: 46, 1: 560, 2: 92, 3: 225, 4: 220, 5: 105, 6: 105, 7: 120, 8: 100, 9: 88, 10: 150}
        stretch_cols = {1: 2, 4: 2, 5: 1, 6: 1, 8: 1}
        for col in range(len(headers)):
            table.grid_columnconfigure(col, minsize=min_sizes.get(col, 80), weight=stretch_cols.get(col, 0))
        update_scrollregion()


    def render_task_row(self, table, row_idx, task, headers):
        bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) in ("overdue", "today", "orange") else COLORS["white"]
        can_finish = not task.get("subtasks") or all_subtasks_done(task)
        can_complete = self.can_complete_task(task)
        btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=zfont(self.app, 15, "bold"), state="normal" if can_complete else "disabled")
        btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)
        if not can_complete:
            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Nur zuständige Person darf erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())
        elif task.get("subtasks") and not can_finish:
            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Bitte erst alle Unteraufgaben erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())

        task_cell = tk.Frame(table, bg=bg)
        task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)
        visible_subtasks = sorted([s for s in task.get("subtasks", []) if not s.get("deleted")], key=lambda s: str(s.get("title", "")).casefold())

        task_actions = tk.Frame(task_cell, bg=bg)
        task_actions.pack(side="right", padx=(6, 8), pady=3)
        tk.Button(task_actions, text="PDF", command=lambda t=task: self.create_task_id_report(t), bg=COLORS["white"], fg=COLORS["blue"], bd=1, padx=4, pady=2, cursor="hand2").pack(side="right", padx=(4, 0))
        if visible_subtasks:
            expand_key = self.get_expand_key(task)
            expanded = expand_key in self.expanded_tasks
            toggle_text = "Unteraufgaben einklappen v" if expanded else "Unteraufgaben ausklappen >"
            tk.Button(task_actions, text=toggle_text, command=lambda key=expand_key: self.toggle_subtasks_visibility(key), bg=bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, cursor="hand2").pack(side="right", padx=(0, 6))

        task_text = tk.Frame(task_cell, bg=bg)
        task_text.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=4)
        uid = self.task_uid_display(task)
        if uid:
            tk.Label(task_text, text=uid, bg=bg, fg=COLORS["blue"], font=zfont(self.app, 12, "bold"), anchor="w", justify="left").pack(anchor="w")
        tk.Label(task_text, text=str(task.get("title", "")), bg=bg, fg=COLORS["text"], font=zfont(self.app, 12), anchor="w", justify="left", wraplength=430).pack(anchor="w", fill="x", expand=True)

        doc_frame = tk.Frame(table, bg=bg)
        doc_frame.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)
        if visible_subtasks:
            tk.Label(doc_frame, text="", bg=bg).pack(padx=4, pady=3)
        else:
            self.create_documentation_button(doc_frame, task, task.get("title", "Aufgabe")).pack(padx=5, pady=3)

        owner_cell = tk.Frame(table, bg=bg)
        owner_cell.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)
        tk.Label(owner_cell, text=task.get("owner"), bg=bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=6, anchor="center", justify="center").pack(side="left", fill="x", expand=True)
        if self.can_edit():
            self.create_delegate_button(owner_cell, task).pack(side="right", padx=(2, 5), pady=3)

        values = [self.due_display_inline(task), task.get("deadline_type"), task.get("priority"), "Ja" if task.get("recurring") else "Nein"]
        aligns = [("w", "left"), ("center", "center"), ("center", "center"), ("center", "center")]
        for offset, val in enumerate(values):
            anchor, justify = aligns[offset]
            tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=6, anchor=anchor, justify=justify).grid(row=row_idx, column=4 + offset, sticky="nsew", padx=1, pady=1)
        self.create_attachment_button(table, task, lambda t=task: self.show_attachments(t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)
        status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))
        menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: self.set_status(t, value))
        menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0, state="normal" if can_complete else "disabled")
        menu.grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)
        if self.edit_mode and self.can_edit():
            action = tk.Frame(table, bg=bg); action.grid(row=row_idx, column=10, sticky="nsew", padx=1, pady=1)
            tk.Button(action, text="Bearbeiten", command=lambda t=task: self.open_task_dialog(task.get("team"), t), bg=COLORS["blue"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
            tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), bg=COLORS["red"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
        row_idx += 1

        if self.get_expand_key(task) in self.expanded_tasks:
            for sub in visible_subtasks:
                self.normalize_documentation_fields(sub)
                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]
                tk.Button(table, text="✓" if sub.get("status") == STATUS_DONE else "□", command=lambda t=task, s=sub: self.toggle_subtask(t, s), bg="#BBF7D0" if sub.get("status") == STATUS_DONE else sub_bg, fg=COLORS["dark_green"] if sub.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=zfont(self.app, 14, "bold"), state="normal" if can_complete else "disabled").grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)
                tk.Label(table, text="↳ " + sub.get("title", ""), bg=sub_bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=18, pady=5, anchor="w").grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)
                sub_doc = tk.Frame(table, bg=sub_bg); sub_doc.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)
                self.create_documentation_button(sub_doc, sub, sub.get("title", "Unteraufgabe"), parent_task=task).pack(padx=5, pady=2)
                sub_owner = tk.Frame(table, bg=sub_bg); sub_owner.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)
                tk.Label(sub_owner, text=sub.get("owner", task.get("owner", "")), bg=sub_bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=5, anchor="center", justify="center").pack(side="left", fill="x", expand=True)
                if self.can_edit():
                    self.create_delegate_button(sub_owner, sub, parent_task=task).pack(side="right", padx=(2, 5), pady=3)
                for col in (4, 5, 6, 7):
                    tk.Label(table, text="", bg=sub_bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=5).grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)
                self.create_attachment_button(table, sub, lambda s=sub, t=task: self.show_attachments(s, parent_task=t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)
                tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)
                if self.edit_mode and self.can_edit():
                    tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=10, sticky="nsew", padx=1, pady=1)
                row_idx += 1
        return row_idx

    def find_task(self, task_id):
        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not t.get("deleted")), None)

    def toggle_done(self, task):
            if not self.require_unlocked("Diese Änderung"): return
            real = self.find_task(task["id"])
            if not real: return
            if not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return
            if real.get("subtasks") and not all_subtasks_done(real): self.show_tooltip(self.root, "Bitte erst alle Unteraufgaben erledigen."); self.root.after(1600, self.hide_tooltip); return
            if real.get("status") == STATUS_DONE: real.update({"status": STATUS_OPEN, "done_at": None, "done_by": None})
            else:
                if real.get("deadline_type") == "gesetzlich" and not messagebox.askyesno("Quartalsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"): return
                real.update({"status": STATUS_DONE, "done_at": datetime.now().isoformat(timespec="seconds"), "done_by": getattr(self.app, "current_user_display", "") or ""})
            self.save(); self.render_team_detail(real["team"])

    def set_status(self, task, status):
            if not self.require_unlocked("Diese Änderung"): return
            real = self.find_task(task["id"])
            if not real: return
            if status == STATUS_DONE and not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return
            if status == STATUS_DONE and real.get("subtasks") and not all_subtasks_done(real): messagebox.showinfo("Quartalsabschluss", "Bitte erst alle Unteraufgaben erledigen."); self.render_team_detail(real["team"]); return
            if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not messagebox.askyesno("Quartalsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"): self.render_team_detail(real["team"]); return
            real["status"] = status; real["done_at"] = datetime.now().isoformat(timespec="seconds") if status == STATUS_DONE else None; real["done_by"] = getattr(self.app, "current_user_display", "") or "" if status == STATUS_DONE else None
            self.save(); self.render_team_detail(real["team"])

    def toggle_subtask(self, task, subtask):
            if not self.require_unlocked("Diese Änderung"): return
            real = self.find_task(task["id"])
            if not real: return
            if not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du kannst nur Unteraufgaben als erledigt markieren, wenn du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return
            for sub in real.get("subtasks", []):
                if sub.get("id") == subtask.get("id"): sub["status"] = STATUS_OPEN if sub.get("status") == STATUS_DONE else STATUS_DONE; break
            sync_parent_status_from_subtasks(real); self.save(); self.render_team_detail(real["team"])

    def next_task_index(self, team):
        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1

    def task_to_catalog_entry(self, task):
        catalog_id = task.get("catalog_id") or f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"; task["catalog_id"] = catalog_id
        return {k: task.get(k) for k in ["catalog_id", "team", "title", "owner", "owner_user_key", "due_date", "due_mode", "due_day", "due_workday", "due_fixed_date", "deadline_type", "priority", "required", "recurring"]} | {"start_period": self.period, "recurring": True}

    def upsert_catalog_entry(self, task):
        catalog = load_catalog(); entry = self.task_to_catalog_entry(task); tasks = catalog.setdefault("tasks", [])
        for idx, existing in enumerate(tasks):
            if existing.get("catalog_id") == entry["catalog_id"]: entry["start_period"] = existing.get("start_period", self.period); tasks[idx] = entry; break
        else: tasks.append(entry)
        save_catalog(catalog); return entry["catalog_id"]

    def remove_catalog_entry(self, catalog_id):
        if not catalog_id: return
        catalog = load_catalog(); catalog["tasks"] = [t for t in catalog.get("tasks", []) if t.get("catalog_id") != catalog_id]; save_catalog(catalog)

    def propagate_recurring_to_future_periods(self, catalog_id):
        if not catalog_id: return
        for period in list_periods():
            if period > self.period: apply_catalog_to_period(period)

    def open_task_dialog(self, team, task=None):
        if not self.can_edit(): return
        is_new = task is None
        win = tk.Toplevel(self.root); win.title("Aufgabe anlegen" if is_new else "Aufgabe bearbeiten"); win.configure(bg=COLORS["bg"]); win.geometry("760x590"); win.transient(self.root); win.grab_set()
        data = dict(task) if task else {"title": "", "owner": team, "owner_user_key": "", "deadline_type": "intern", "priority": "normal", "due_mode": DUE_CUTOFF, "due_day": 1, "due_workday": 1, "due_fixed_date": "", "recurring": False, "subtasks": []}
        normalize_task(data, self.data, self.period)
        notebook = ttk.Notebook(win); notebook.pack(fill="both", expand=True, padx=14, pady=14)
        form = tk.Frame(notebook, bg=COLORS["bg"]); subtab = tk.Frame(notebook, bg=COLORS["bg"])
        notebook.add(form, text="Aufgabe"); notebook.add(subtab, text="Unteraufgaben")
        uid_var = tk.StringVar(value=self.normalize_task_uid_value(data.get("task_uid")) or self.next_free_task_uid())
        title_var = tk.StringVar(value=data.get("title", "")); deadline_var = tk.StringVar(value=data.get("deadline_type", "intern") if data.get("deadline_type") in DEADLINE_TYPES else "intern"); priority_var = tk.StringVar(value=data.get("priority", "normal")); recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))
        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", DUE_CUTOFF), "Abschluss-Stichtag")); due_day_var = tk.StringVar(value=str(data.get("due_day") or 1)); due_workday_var = tk.StringVar(value=str(data.get("due_workday") or 1)); due_fixed_var = tk.StringVar(value=format_date_de(data.get("due_fixed_date") or data.get("due_date") or "")); calculated_var = tk.StringVar(value="")
        users = self.user_choices(); user_labels = {label: key for key, label in users}; current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, label in users if key == current_owner_key), data.get("owner", team)); owner_var = tk.StringVar(value=current_owner_label)
        uid_entry = tk.Entry(form, textvariable=uid_var, width=18, state="normal" if self.is_task_id_editor() else "readonly")
        widgets = [("Aufgaben-ID", uid_entry), ("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), ("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fristart", tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, priority_var, *PRIORITIES)), ("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, *DUE_LABEL_TO_VALUE.keys()))]
        for row, (label, widget) in enumerate(widgets):
            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")).grid(row=row, column=0, sticky="w", pady=7, padx=8); widget.grid(row=row, column=1, sticky="w", pady=7)
            try: widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)
            except Exception: pass
        day_label = tk.Label(form, text="Tag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")); day_entry = tk.Entry(form, textvariable=due_day_var, width=8)
        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")); workday_entry = tk.Entry(form, textvariable=due_workday_var, width=8)
        fixed_label = tk.Label(form, text="Konkretes Datum (TT.MM.JJJJ)", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")); fixed_entry = tk.Entry(form, textvariable=due_fixed_var, width=14)
        for r, lab, ent in [(6, day_label, day_entry), (7, workday_label, workday_entry), (8, fixed_label, fixed_entry)]: lab.grid(row=r, column=0, sticky="w", pady=7, padx=8); ent.grid(row=r, column=1, sticky="w", pady=7); ent.config(bg="white", fg=COLORS["text"], relief="solid", bd=1, highlightthickness=0)
        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold"), activebackground=COLORS["bg"]).grid(row=9, column=1, sticky="w", pady=7)
        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12, "bold")).grid(row=10, column=1, sticky="w", pady=(4, 10))
        def refresh_due_input_visibility(*_):
            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF)
            for lab, ent in [(day_label, day_entry), (workday_label, workday_entry), (fixed_label, fixed_entry)]: lab.grid_remove(); ent.grid_remove()
            if mode == DUE_DAY_CAL_MONTH: day_label.grid(); day_entry.grid()
            elif mode == DUE_WORKDAY_NEXT: workday_label.grid(); workday_entry.grid()
            elif mode == DUE_FIXED: fixed_label.grid(); fixed_entry.grid()
            preview = {"due_mode": mode, "due_day": due_day_var.get().strip() or 1, "due_workday": due_workday_var.get().strip() or 1, "due_fixed_date": due_fixed_var.get().strip()}
            calculated_var.set("Berechnetes Fälligkeitsdatum: " + (format_date_de(resolve_due_date(preview, self.data, self.period)) or "-"))
        for var in (due_mode_var, due_day_var, due_workday_var, due_fixed_var): var.trace_add("write", refresh_due_input_visibility)
        refresh_due_input_visibility()
        subtasks_work = [dict(s) for s in data.get("subtasks", []) if not s.get("deleted")]
        sub_list = tk.Frame(subtab, bg=COLORS["bg"]); sub_list.pack(fill="both", expand=True, padx=10, pady=10); new_sub_var = tk.StringVar()
        def render_subtasks_editor():
            for child in sub_list.winfo_children(): child.destroy()
            tk.Label(sub_list, text="Unteraufgaben", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 14, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
            for idx, sub in enumerate(subtasks_work, start=1):
                var = tk.StringVar(value=sub.get("title", "")); status_var = tk.BooleanVar(value=sub.get("status") == STATUS_DONE)
                var.trace_add("write", lambda *_args, i=idx-1, v=var: subtasks_work[i].update({"title": v.get()}))
                tk.Checkbutton(sub_list, variable=status_var, command=lambda i=idx-1, v=status_var: subtasks_work[i].update({"status": STATUS_DONE if v.get() else STATUS_OPEN}), bg=COLORS["bg"], activebackground=COLORS["bg"]).grid(row=idx, column=0, sticky="w", pady=3)
                tk.Entry(sub_list, textvariable=var, width=52, bg="white", fg=COLORS["text"], relief="solid", bd=1).grid(row=idx, column=1, sticky="w", pady=3, padx=6)
                tk.Button(sub_list, text="Löschen", command=lambda i=idx-1: delete_subtask(i), bg=COLORS["red"], fg="white", bd=0, padx=8).grid(row=idx, column=2, sticky="w", pady=3)
            row = len(subtasks_work) + 2
            tk.Entry(sub_list, textvariable=new_sub_var, width=52, bg="white", fg=COLORS["text"], relief="solid", bd=1).grid(row=row, column=1, sticky="w", pady=(12, 3), padx=6)
            tk.Button(sub_list, text="Unteraufgabe hinzufügen", command=add_subtask, bg=COLORS["blue"], fg="white", bd=0, padx=10, pady=5).grid(row=row, column=2, sticky="w", pady=(12, 3))
        def add_subtask():
            title = new_sub_var.get().strip()
            if title: subtasks_work.append({"id": f"sub_{len(subtasks_work)+1:02d}_{datetime.now().strftime('%H%M%S%f')}", "title": title, "status": STATUS_OPEN}); new_sub_var.set(""); render_subtasks_editor()
        def delete_subtask(idx):
            if 0 <= idx < len(subtasks_work): subtasks_work.pop(idx); render_subtasks_editor()
        render_subtasks_editor()
        if not is_new:
            tk.Button(form, text="Aufgabe mit Unteraufgaben in Monatsabschluss übernehmen", command=lambda: self.open_transfer_dialog(task), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7).grid(row=10, column=1, sticky="w", pady=(10, 4))
        def save_dialog():
            title_value = title_var.get().strip()
            if not title_value: messagebox.showwarning("Quartalsabschluss", "Bitte einen Aufgabennamen eingeben."); return
            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF); due_day = None; due_workday = None; due_fixed = ""
            try:
                if mode == DUE_DAY_CAL_MONTH: due_day = int(due_day_var.get().strip()); assert due_day > 0
                elif mode == DUE_WORKDAY_NEXT: due_workday = int(due_workday_var.get().strip()); assert due_workday > 0
                elif mode == DUE_FIXED:
                    fixed_date = parse_date(due_fixed_var.get().strip()); assert fixed_date; due_fixed = fixed_date.strftime("%Y-%m-%d")
            except Exception:
                messagebox.showwarning("Quartalsabschluss", "Bitte gültige Werte zur Fälligkeit eingeben."); return
            owner_label = owner_var.get(); owner_key = user_labels.get(owner_label, ""); owner_text = owner_label if owner_key else team
            payload = {"title": title_value, "owner": owner_text, "owner_user_key": owner_key, "due_mode": mode, "due_day": due_day, "due_workday": due_workday, "due_fixed_date": due_fixed, "deadline_type": deadline_var.get(), "priority": priority_var.get(), "recurring": bool(recurring_var.get()), "subtasks": [s for s in subtasks_work if s.get("title", "").strip()]}
            payload["due_date"] = resolve_due_date(payload, self.data, self.period)
            if is_new:
                real = {"id": make_task_id(team, self.next_task_index(team)), "team": team, "required": True, "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, "done_by": None, "catalog_id": "", **payload}; self.data.setdefault("tasks", []).append(real)
            else:
                real = self.find_task(task["id"])
                if not real: return
                self.archive_task_uid_change(real, self.normalize_task_uid_value(real.get("task_uid")), new_uid)
                real.update(payload)
            sync_parent_status_from_subtasks(real)
            if real.get("recurring"):
                catalog_id = self.upsert_catalog_entry(real); real["catalog_id"] = catalog_id; self.propagate_recurring_to_future_periods(catalog_id)
            else:
                if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))
                real["catalog_id"] = ""
            self.save(); win.destroy(); self.reload(); self.render_team_detail(team)
        buttons = tk.Frame(win, bg=COLORS["bg"]); buttons.pack(side="bottom", fill="x", pady=(0, 12), padx=14)
        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="right", padx=6)
        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="right", padx=6)

    def delete_task(self, task):
            if not self.require_unlocked("Diese Änderung"): return
            idx = self.find_task_index_exact(task)
            if idx is None:
                messagebox.showerror("Aufgabe löschen", "Die ausgewählte Aufgabe konnte nicht eindeutig identifiziert werden. Es wurde nichts gelöscht.")
                return
            real = self.data.get("tasks", [])[idx]
            scope = self.ask_delete_scope(real)
            if not scope:
                return
            task_key = self.task_match_key(real)
            team = real.get("team")
            title = real.get("title", "")
            self.data["tasks"].pop(idx)
            if scope == "following" and real.get("catalog_id"):
                self.remove_catalog_entry(real.get("catalog_id"))
            self.save()
            removed_future = 0
            ambiguous_future = 0
            if scope == "following":
                removed_future, ambiguous_future = self.delete_from_following_periods(task_key)
            info = f"Aufgabe wurde gelöscht:\n\n{title}"
            if scope == "following":
                info += f"\n\nEntfernt aus Folgezeiträumen: {removed_future}"
                if ambiguous_future:
                    info += f"\nNicht eindeutig erkannte Folgezeiträume übersprungen: {ambiguous_future}"
            messagebox.showinfo("Aufgabe löschen", info)
            self.reload()
            self.render_team_detail(team) if team else self.render_dashboard()

    def clone_task_for_period(self, task, target_period, index):
        data_stub = {"closing_cutoff_date": default_cutoff_date(target_period)}
        clone = {"id": make_task_id(task.get("team", "Team"), index), "team": task.get("team"), "title": task.get("title"), "owner": task.get("owner", task.get("team")), "owner_user_key": task.get("owner_user_key", ""), "due_mode": task.get("due_mode", DUE_CUTOFF), "due_day": task.get("due_day"), "due_workday": task.get("due_workday"), "due_fixed_date": task.get("due_fixed_date", ""), "deadline_type": task.get("deadline_type", "keine"), "priority": task.get("priority", "normal"), "required": task.get("required", True), "recurring": task.get("recurring", False), "catalog_id": task.get("catalog_id", ""), "status": STATUS_OPEN, "attachments": [], "comments": [], "subtasks": [dict(s, status=STATUS_OPEN) for s in task.get("subtasks", []) if not s.get("deleted")], "done_at": None, "done_by": None}
        clone["due_date"] = resolve_due_date(clone, data_stub, target_period); return clone

    def apply_current_tasks_to_all_periods(self):
            if not self.require_unlocked("Zuweisung an Perioden ist nicht möglich"): return
            if not self.can_edit(): return
            if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus {period_label(self.period)} wird auf alle vorhandenen Perioden übertragen.\n\nStatus, Anlagen, Kommentare und Erledigt-Infos werden in den Zielperioden zurückgesetzt.\n\nFortfahren?"): return
            source_tasks = [t for t in self.tasks()]
            for target in list_periods():
                grouped_index = {}; cloned = []
                for task in source_tasks:
                    team = task.get("team", "Team"); grouped_index[team] = grouped_index.get(team, 0) + 1; cloned.append(self.clone_task_for_period(task, target, grouped_index[team]))
                data = load_period(target); data["tasks"] = cloned; data["updated_from_period"] = self.period; data["updated_at"] = datetime.now().isoformat(timespec="seconds"); save_period(target, data)
            self.reload(); messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben wurden allen vorhandenen Perioden zugewiesen."); self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def show_attachments(self, task, parent_task=None):
        self.normalize_documentation_fields(task)
        item_title = task.get("title", "Aufgabe")
        win = tk.Toplevel(self.root)
        win.title(f"Anlagen - {item_title}")
        win.configure(bg=COLORS["bg"])
        win.geometry("860x560")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=item_title, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(win, text="Anlagen dienen zur Hinterlegung ausgearbeiteter Ergebnisse und Kommentare zur Bearbeitung. Dokumentationen/Leitfäden bitte in der Spalte Dokumentation pflegen.", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=820, justify="left").pack(anchor="w", padx=16, pady=(0, 8))

        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_columnconfigure(3, weight=2)

        def refresh():
            for child in list_frame.winfo_children():
                child.destroy()
            self.normalize_documentation_fields(task)
            headers = ["Anlagenpfad", "Öffnen", "Entfernen", "Bemerkung"]
            for c, h in enumerate(headers):
                tk.Label(list_frame, text=h, bg=COLORS["header"], fg=COLORS["text"], font=zfont(self.app, 11, "bold"), padx=6, pady=4).grid(row=0, column=c, sticky="nsew")
            if not task.get("attachments"):
                tk.Label(list_frame, text="Noch keine Anlage hinterlegt.", bg=COLORS["white"], fg=COLORS["text2"], padx=8, pady=8, anchor="w").grid(row=1, column=0, columnspan=4, sticky="ew")
                return
            for idx, att in enumerate(task.get("attachments", []), start=1):
                tk.Label(list_frame, text=att.get("path", ""), bg=COLORS["white"], fg=COLORS["text"], anchor="w", wraplength=330).grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, pady=3)
                tk.Button(list_frame, text="Entfernen", command=lambda a=att: remove_attachment(a), bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, pady=3)
                tk.Label(list_frame, text=att.get("comment", ""), bg=COLORS["white"], fg=COLORS["text2"], anchor="w", justify="left", wraplength=320).grid(row=idx, column=3, sticky="ew", padx=6, pady=3)

        def choose_path():
            selected = filedialog.askopenfilename(title="Anlage auswählen")
            if selected:
                path_var.set(selected)

        def add_or_update_attachment():
            path = path_var.get().strip()
            if not path or path == placeholder:
                messagebox.showwarning("Anlagen", "Bitte einen Pfad der Anlage wählen oder einfügen.")
                return
            self.normalize_documentation_fields(task)
            task.setdefault("attachments", []).append({
                "name": os.path.basename(path) or "Anlage",
                "path": path,
                "comment": comment_box.get("1.0", "end").strip(),
                "added_at": datetime.now().isoformat(timespec="seconds"),
            })
            self.save()
            refresh()
            path_var.set(placeholder)
            comment_box.delete("1.0", "end")
            if self.selected_team:
                self.render_team_detail(self.selected_team)

        def remove_attachment(att):
            if messagebox.askyesno("Anlage entfernen", f"Anlage entfernen?\n\n{att.get('name') or att.get('path')}"):
                task["attachments"] = [a for a in task.get("attachments", []) if a != att]
                self.save(); refresh()
                if self.selected_team:
                    self.render_team_detail(self.selected_team)

        form = tk.Frame(win, bg=COLORS["bg"])
        form.pack(fill="x", padx=16, pady=(0, 14))
        path_var = tk.StringVar()
        placeholder = "Bitte Pfad der Anlage wählen oder einfügen"
        path_var.set(placeholder)
        tk.Label(form, text="Anlagenpfad", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        tk.Button(form, text="Anlage auswählen", command=choose_path, bg=COLORS["blue"], fg="white", bd=0, padx=10, pady=5).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))
        entry = tk.Entry(form, textvariable=path_var, bg=COLORS["white"], fg=COLORS["text2"], relief="solid", bd=1, width=70)
        entry.grid(row=0, column=2, sticky="ew", pady=(0, 6))
        form.grid_columnconfigure(2, weight=1)
        def clear_placeholder(_event=None):
            if path_var.get() == placeholder:
                path_var.set("")
                entry.config(fg=COLORS["text"])
        entry.bind("<FocusIn>", clear_placeholder)

        tk.Label(form, text="Bemerkungen und Informationen:", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, "bold")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 4))
        comment_box = tk.Text(form, height=4, bg=COLORS["white"], fg=COLORS["text"], relief="solid", bd=1)
        comment_box.grid(row=2, column=0, columnspan=3, sticky="ew")
        tk.Button(form, text="Übernehmen", command=add_or_update_attachment, bg=COLORS["blue"], fg="white", bd=0, padx=16, pady=7).grid(row=3, column=2, sticky="e", pady=(8, 0))
        refresh()

    def open_attachment(self, path):
        if not path or not os.path.exists(path): messagebox.showwarning("Anlage", "Datei wurde nicht gefunden."); return
        try:
            if os.name == "nt": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as exc: messagebox.showerror("Anlage", str(exc))


def render(app):
    QuarterlyCloseUI(app)
