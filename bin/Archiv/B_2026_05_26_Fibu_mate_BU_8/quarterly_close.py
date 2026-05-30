
import calendar
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

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

def quarter_key(d=None):
    d = d or date.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year:04d}-Q{q}"

def current_period_key():
    return max(quarter_key(), MIN_PERIOD)

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


def default_cutoff_date(period):
    return period_end(period).strftime("%Y-%m-%d")


def normalize_cutoff(data, period):
    cutoff = parse_date(data.get("closing_cutoff_date", ""))
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
        names = examples[team] + ["Unbenannte Aufgabe 1", "Unbenannte Aufgabe 2", "Unbenannte Aufgabe 3"]
        for idx, title in enumerate(names, 1):
            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]
            task = {
                "id": make_task_id(team, idx), "team": team, "title": title, "owner": team, "owner_user_key": "",
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
    normalize_cutoff(data, period)
    changed = False
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
    for path in PERIOD_DIR.glob("*.json"):
        if path.stem < MIN_PERIOD:
            try: path.unlink()
            except Exception: pass

def ensure_period_window():
    ensure_storage(); cleanup_old_periods(); current = current_period_key()
    for offset in range(0, 3):
        p = add_quarter(current, offset); load_period(p); apply_catalog_to_period(p)

def list_periods():
    ensure_period_window()
    return sorted(p.stem for p in PERIOD_DIR.glob("*.json") if p.stem >= MIN_PERIOD)



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
        self.render_dashboard()

    def handle_escape(self):
        if self.selected_team:
            self.selected_team = None
            self.render_dashboard()
            return True
        return False

    def can_edit(self):
        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"
        return {"Standard": 1, "Administrator": 2, "Wagnerm": 3, "System-Administrator": 3}.get(role, 1) >= 2

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
        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"
        return role == "Standard"
    def can_complete_task(self, task):
        if not self.is_standard_user(): return True
        return bool(getattr(self.app, "current_user_key", "") and task.get("owner_user_key") == getattr(self.app, "current_user_key", ""))
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
        win = tk.Toplevel(self.root); win.title("In Monatsabschluss übernehmen"); win.configure(bg=COLORS["bg"]); win.transient(self.root); win.grab_set(); win.geometry("540x250")
        default_period = self._target_period_from_current(); mode_var = tk.StringVar(value="all")
        tk.Label(win, text="Aufgabe inklusive Unteraufgaben übernehmen", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 10))
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
        tk.Label(win, text="Aufgabe löschen", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        msg = f"Welche Zeiträume sollen bereinigt werden?\n\n{task.get('title', '')}"
        if task.get("attachments"):
            msg += "\n\nHinweis: Anlagen-Dateien bleiben im Anlagenordner erhalten; nur die Referenz in der Aufgabe wird entfernt."
        tk.Label(win, text=msg, bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10), justify="left", wraplength=480).pack(anchor="w", padx=16, pady=(0, 14))
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
        if not self.can_edit():
            return
        following = self.following_periods()
        if not following:
            messagebox.showinfo("Folgezeiträume bereinigen", "Es sind keine folgenden Zeiträume vorhanden.")
            return
        if not messagebox.askyesno(
            "Alle Folgezeiträume bereinigen",
            "Alle Folgezeiträume an den aktuellen Aufgabenbestand anpassen?\n\nAufgaben, die im aktuellen Zeitraum nicht mehr vorhanden sind, werden aus folgenden Zeiträumen entfernt.\n\nFortfahren?",
        ):
            return
        current_keys = {self.task_match_key(task) for task in self.tasks()}
        cleaned_periods = 0
        removed = 0
        for period in following:
            data = load_period(period)
            old_tasks = data.get("tasks", [])
            new_tasks = [task for task in old_tasks if task.get("deleted") or self.task_match_key(task) in current_keys]
            if len(new_tasks) != len(old_tasks):
                data["tasks"] = new_tasks
                data["cleaned_from_period"] = self.period
                data["cleaned_at"] = datetime.now().isoformat(timespec="seconds")
                save_period(period, data)
                cleaned_periods += 1
                removed += len(old_tasks) - len(new_tasks)
        self.reload()
        messagebox.showinfo("Alle Folgezeiträume bereinigen", f"Bereinigung abgeschlossen.\n\nBereinigte Zeiträume: {cleaned_periods}\nEntfernte Aufgaben: {removed}")
        self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def draw_progress(self, parent, percent, width=260, height=20, bg=None):
        bg = bg or parent.cget("bg")
        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)
        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")
        fill_w = int(width * max(0, min(100, percent)) / 100)
        if fill_w: c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), outline=progress_color(percent))
        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], font=("Segoe UI", 9, "bold"))
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
            font=("Segoe UI", 8, "bold"),
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
        tk.Label(win, text="Zuständigkeit delegieren", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        tk.Label(win, text="Die Delegierung gilt nur für den aktuell geöffneten Zeitraum.", bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(0, 10))
        selected = tk.StringVar(value=current_label)
        menu = tk.OptionMenu(win, selected, *labels)
        menu.config(bg=COLORS["white"], fg=COLORS["text"], bd=1, highlightthickness=0)
        menu.pack(fill="x", padx=16, pady=(0, 14))

        def apply_delegate():
            user_key, display_name = label_to_choice[selected.get()]
            fallback_team = task_for_team.get("team", item.get("team", "Team"))
            owner_name = display_name if user_key else fallback_team
            targets = [item]
            if parent_task is None:
                targets += [sub for sub in item.get("subtasks", []) if not sub.get("deleted")]
            for target in targets:
                target["owner_user_key"] = user_key
                target["owner"] = owner_name
            self.save()
            if self.selected_team:
                self.render_team_detail(self.selected_team)
            win.destroy()

        footer = tk.Frame(win, bg=COLORS["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 14))
        tk.Button(footer, text="Übernehmen", command=apply_delegate, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")
        tk.Button(footer, text="Abbrechen", command=win.destroy, bg=COLORS["header"], fg=COLORS["text"], bd=0, padx=14, pady=7, cursor="hand2").pack(side="right", padx=(0, 8))

    def show_tooltip(self, widget, text):
        self.hide_tooltip(); self.tooltip = tk.Toplevel(widget); self.tooltip.wm_overrideredirect(True); self.tooltip.geometry(f"+{widget.winfo_rootx() + 12}+{widget.winfo_rooty() + 34}"); tk.Label(self.tooltip, text=text, bg="#111827", fg="white", font=("Segoe UI", 9), padx=6, pady=3).pack()

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
        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=7)
        if team:
            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: self.open_task_dialog(team), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)
            tk.Button(row, text="Aufgaben allen vorhandenen Perioden zuweisen", command=self.apply_current_tasks_to_all_periods, bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)
            tk.Button(row, text="Alle Folgezeiträume bereinigen", command=self.cleanup_following_periods, bg=COLORS["red"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)

    def change_period(self, period):
        if period < MIN_PERIOD:
            messagebox.showinfo("Quartalsabschluss", "Der Quartalsabschluss kann nicht weiter zurück als Q2 2026 geöffnet werden.")
            return
        self.period = period; self.reload(); self.selected_team = None; self.render_dashboard()

    def save_cutoff_from_entry(self, entry_var):
        d = parse_date(entry_var.get())
        if not d:
            messagebox.showwarning("Quartalsabschluss", "Bitte einen gültigen Abschluss-Stichtag im Format TT.MM.JJJJ eingeben.")
            return
        self.data["closing_cutoff_date"] = d.strftime("%Y-%m-%d")
        for task in self.data.get("tasks", []):
            if task.get("due_mode") == DUE_CUTOFF:
                task["due_date"] = d.strftime("%Y-%m-%d")
        self.save(); self.reload(); self.render_dashboard()

    def render_dashboard(self):
        self.selected_team = None; self.clear_frame(); self.render_period_controls(self.frame); self.render_edit_tools(self.frame)
        stats = calc_stats(self.tasks())
        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); top.pack(fill="x", padx=24, pady=(8, 10))
        title_row = tk.Frame(top, bg=COLORS["white"]); title_row.pack(fill="x", padx=14, pady=(6, 2))
        tk.Label(title_row, text=f"Quartalsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(side="left")
        cutoff_var = tk.StringVar(value=format_date_de(self.data.get("closing_cutoff_date")))
        tk.Label(title_row, text="Abschluss-Stichtag", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=(24, 6))
        cutoff_entry = tk.Entry(title_row, textvariable=cutoff_var, width=12, bg="#F8FAFC", fg=COLORS["text"], relief="solid", bd=1)
        cutoff_entry.pack(side="left")
        tk.Button(title_row, text="Speichern", command=lambda: self.save_cutoff_from_entry(cutoff_var), bg=COLORS["blue"], fg="white", bd=0, padx=10, pady=4).pack(side="left", padx=6)
        tk.Label(top, text=f"Gesamt: {stats['done']} erledigt / {stats['in_progress']} in Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=14)
        holder = tk.Frame(top, bg=COLORS["white"]); holder.pack(anchor="w", padx=14, pady=(8, 10)); self.draw_progress(holder, stats["percent"], width=520, height=24, bg=COLORS["white"]).pack(side="left")
        self.render_warnings(self.frame)
        cards = tk.Frame(self.frame, bg=COLORS["bg"]); cards.pack(fill="both", expand=True, padx=24, pady=8)
        for idx, team in enumerate(TEAMS): self.render_team_card(cards, team, idx)

    def render_warnings(self, parent):
        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", "yellow") and t.get("status") != STATUS_DONE]
        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid"); box.pack(fill="x", padx=24, pady=(0, 8))
        if warnings:
            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 3))
            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:
                tk.Label(box, text=f"- {task['title']} | {task['team']} | fällig am {format_date_de(task.get('due_date'))} | {task.get('deadline_type')}", bg=box["bg"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=1)
        else:
            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], fg=COLORS["dark_green"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)

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
            tk.Label(card, text=" • ".join(names), bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 10), wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, 12))

    def render_team_card(self, parent, team, idx):
        row, col = divmod(idx, 2); tasks = self.team_tasks(team); stats = calc_stats(tasks)
        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, "orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")
        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == "orange" else COLORS["line"]
        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", highlightbackground=border, highlightcolor=border, highlightthickness=2); card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1); parent.grid_rowconfigure(row, weight=1)
        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(card, text=f"{stats['done']} / {stats['total']} erledigt | offen: {stats['open']} | in Bearbeitung: {stats['in_progress']} | kritisch: {stats['critical']}", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=18)
        holder = tk.Frame(card, bg=COLORS["white"]); holder.pack(anchor="w", padx=18, pady=(10, 8)); self.draw_progress(holder, stats["percent"], width=420, height=26, bg=COLORS["white"]).pack()
        nxt = self.next_relevant_task(tasks); txt = "Nächste Frist: keine relevanten offenen Fristen" if not nxt else f"Nächste Frist: {format_date_de(nxt.get('due_date'))} | {nxt.get('title')}"
        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and warning_level(nxt) in ("overdue", "today", "orange") else COLORS["text2"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(0, 5))
        self.render_team_members_on_card(card, team); self.bind_click_recursive(card, lambda t=team: self.render_team_detail(t))

    def render_team_detail(self, team):
        self.selected_team = team; self.clear_frame(); self.render_period_controls(self.frame); self.render_edit_tools(self.frame, team=team); stats = calc_stats(self.team_tasks(team))
        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); head.pack(fill="x", padx=24, pady=(8, 10))
        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(head, text=f"{team} | Quartalsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=12)
        tk.Label(head, text=f"Fortschritt: {stats['done']} / {stats['total']} erledigt | {stats['percent']}%", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=12)
        bar = tk.Frame(head, bg=COLORS["white"]); bar.pack(anchor="w", padx=12, pady=(6, 10)); self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()
        self.render_task_table(team)

    def toggle_subtasks_visibility(self, task_id):
        if task_id in self.expanded_tasks:
            self.expanded_tasks.remove(task_id)
        else:
            self.expanded_tasks.add(task_id)
        if self.selected_team:
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
        tk.Label(inner, text=str(self.attachment_count(item)), bg=parent.cget("bg"), fg=COLORS["blue"], font=("Segoe UI", 10, "bold")).pack(side="left")
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
        tk.Label(win, text="Dokumentation", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        body = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        doc = item.get("documentation", {})
        name_var = tk.StringVar(value=doc.get("name", "Noch keine Dokumentation hinterlegt"))
        path_var = tk.StringVar(value=doc.get("path", ""))

        row = tk.Frame(body, bg=COLORS["white"])
        row.pack(fill="x", padx=12, pady=(14, 6))
        open_button = tk.Button(row, text="Dokumentation öffnen", command=lambda: self.open_attachment(path_var.get()), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6, state="normal" if path_var.get() else "disabled")
        open_button.pack(side="left")
        tk.Label(row, textvariable=name_var, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 10), anchor="w").pack(side="left", padx=(10, 6), fill="x", expand=True)

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

        change = tk.Label(body, text="Dokumentationspfad ändern" if path_var.get() else "Dokumentation anhängen", bg=COLORS["white"], fg=COLORS["blue"], font=("Segoe UI", 10, "underline"), cursor="hand2")
        change.pack(anchor="w", padx=12, pady=(4, 10))
        change.bind("<Button-1>", lambda _e: choose_documentation())
        tk.Label(body, text="Hinweis: Die Dokumentation ist für Aufgabenbeschreibungen bzw. Leitfäden vorgesehen. Ergebnisse und Bearbeitungskommentare bitte unter Anlagen pflegen.", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 9), wraplength=660, justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        tk.Button(win, text="Schließen", command=win.destroy, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))

    def render_task_table(self, team):
        outer = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        scroll_canvas = tk.Canvas(outer, bg=COLORS["white"], highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)
        table = tk.Frame(scroll_canvas, bg="#E4EAF1")  # dezente Spaltentrennlinien
        table_window = scroll_canvas.create_window((0, 0), window=table, anchor="nw")

        def update_scrollregion(_event=None):
            scroll_canvas.itemconfigure(table_window, width=max(1, scroll_canvas.winfo_width()))
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        def on_mousewheel(event):
            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        table.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<MouseWheel>", on_mousewheel)
        table.bind("<MouseWheel>", on_mousewheel)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.app.active_scroll_canvas = scroll_canvas

        headers = ["Status", "Aufgabe", "Dokumentation", "Zuständig", "Fällig", "Fristart", "Priorität", "Wiederkehrend", "Anlagen", "Aktion"]
        if self.edit_mode and self.can_edit():
            headers.append("Bearbeiten")
        for col, h in enumerate(headers):
            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), padx=6, pady=6).grid(row=0, column=col, sticky="nsew")
        row_idx = 1
        for task in self.team_tasks(team):
            sync_parent_status_from_subtasks(task)
            self.normalize_documentation_fields(task)
            for sub in task.get("subtasks", []):
                self.normalize_documentation_fields(sub)
            row_idx = self.render_task_row(table, row_idx, task, headers)

        # Spaltenbreiten: Aufgabe und Zuständig etwas reduziert; Dokumentation schmal; Fristart/Priorität/Anlagen erhalten mehr Raum.
        min_sizes = {0: 46, 1: 330, 2: 92, 3: 225, 4: 220, 5: 105, 6: 105, 7: 120, 8: 100, 9: 88, 10: 150}
        stretch_cols = {1: 2, 4: 2, 5: 1, 6: 1, 8: 1}
        for col in range(len(headers)):
            table.grid_columnconfigure(col, minsize=min_sizes.get(col, 80), weight=stretch_cols.get(col, 0))
        update_scrollregion()


    def render_task_row(self, table, row_idx, task, headers):
        bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) in ("overdue", "today", "orange") else COLORS["white"]
        can_finish = not task.get("subtasks") or all_subtasks_done(task)
        can_complete = self.can_complete_task(task)
        btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=("Segoe UI", 13, "bold"), state="normal" if can_complete else "disabled")
        btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)
        if not can_complete:
            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Nur zuständige Person darf erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())
        elif task.get("subtasks") and not can_finish:
            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Bitte erst alle Unteraufgaben erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())

        task_cell = tk.Frame(table, bg=bg)
        task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)
        tk.Label(task_cell, text=task.get("title"), bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=6, anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        visible_subtasks = sorted([s for s in task.get("subtasks", []) if not s.get("deleted")], key=lambda s: str(s.get("title", "")).casefold())
        if visible_subtasks:
            expanded = task.get("id") in self.expanded_tasks
            toggle_text = "Unteraufgaben einklappen v" if expanded else "Unteraufgaben ausklappen >"
            tk.Button(task_cell, text=toggle_text, command=lambda t=task: self.toggle_subtasks_visibility(t.get("id")), bg=bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, cursor="hand2").pack(side="right", padx=(4, 8))

        doc_frame = tk.Frame(table, bg=bg)
        doc_frame.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)
        if visible_subtasks:
            tk.Label(doc_frame, text="", bg=bg).pack(padx=4, pady=3)
        else:
            self.create_documentation_button(doc_frame, task, task.get("title", "Aufgabe")).pack(padx=5, pady=3)

        owner_cell = tk.Frame(table, bg=bg)
        owner_cell.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)
        tk.Label(owner_cell, text=task.get("owner"), bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=6, anchor="center", justify="center").pack(side="left", fill="x", expand=True)
        if self.can_edit():
            self.create_delegate_button(owner_cell, task).pack(side="right", padx=(2, 5), pady=3)

        values = [self.due_display_inline(task), task.get("deadline_type"), task.get("priority"), "Ja" if task.get("recurring") else "Nein"]
        aligns = [("w", "left"), ("center", "center"), ("center", "center"), ("center", "center")]
        for offset, val in enumerate(values):
            anchor, justify = aligns[offset]
            tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=6, anchor=anchor, justify=justify).grid(row=row_idx, column=4 + offset, sticky="nsew", padx=1, pady=1)
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

        if task.get("id") in self.expanded_tasks:
            for sub in visible_subtasks:
                self.normalize_documentation_fields(sub)
                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]
                tk.Button(table, text="✓" if sub.get("status") == STATUS_DONE else "□", command=lambda t=task, s=sub: self.toggle_subtask(t, s), bg="#BBF7D0" if sub.get("status") == STATUS_DONE else sub_bg, fg=COLORS["dark_green"] if sub.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=("Segoe UI", 12, "bold"), state="normal" if can_complete else "disabled").grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)
                tk.Label(table, text="↳ " + sub.get("title", ""), bg=sub_bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=18, pady=5, anchor="w").grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)
                sub_doc = tk.Frame(table, bg=sub_bg); sub_doc.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)
                self.create_documentation_button(sub_doc, sub, sub.get("title", "Unteraufgabe"), parent_task=task).pack(padx=5, pady=2)
                sub_owner = tk.Frame(table, bg=sub_bg); sub_owner.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)
                tk.Label(sub_owner, text=sub.get("owner", task.get("owner", "")), bg=sub_bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=5, anchor="center", justify="center").pack(side="left", fill="x", expand=True)
                if self.can_edit():
                    self.create_delegate_button(sub_owner, sub, parent_task=task).pack(side="right", padx=(2, 5), pady=3)
                for col in (4, 5, 6, 7):
                    tk.Label(table, text="", bg=sub_bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=5).grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)
                self.create_attachment_button(table, sub, lambda s=sub, t=task: self.show_attachments(s, parent_task=t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)
                tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)
                if self.edit_mode and self.can_edit():
                    tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=10, sticky="nsew", padx=1, pady=1)
                row_idx += 1
        return row_idx

    def find_task(self, task_id):
        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not t.get("deleted")), None)

    def toggle_done(self, task):
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
        real = self.find_task(task["id"])
        if not real: return
        if status == STATUS_DONE and not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return
        if status == STATUS_DONE and real.get("subtasks") and not all_subtasks_done(real): messagebox.showinfo("Quartalsabschluss", "Bitte erst alle Unteraufgaben erledigen."); self.render_team_detail(real["team"]); return
        if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not messagebox.askyesno("Quartalsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"): self.render_team_detail(real["team"]); return
        real["status"] = status; real["done_at"] = datetime.now().isoformat(timespec="seconds") if status == STATUS_DONE else None; real["done_by"] = getattr(self.app, "current_user_display", "") or "" if status == STATUS_DONE else None
        self.save(); self.render_team_detail(real["team"])

    def toggle_subtask(self, task, subtask):
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
        title_var = tk.StringVar(value=data.get("title", "")); deadline_var = tk.StringVar(value=data.get("deadline_type", "intern") if data.get("deadline_type") in DEADLINE_TYPES else "intern"); priority_var = tk.StringVar(value=data.get("priority", "normal")); recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))
        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", DUE_CUTOFF), "Abschluss-Stichtag")); due_day_var = tk.StringVar(value=str(data.get("due_day") or 1)); due_workday_var = tk.StringVar(value=str(data.get("due_workday") or 1)); due_fixed_var = tk.StringVar(value=format_date_de(data.get("due_fixed_date") or data.get("due_date") or "")); calculated_var = tk.StringVar(value="")
        users = self.user_choices(); user_labels = {label: key for key, label in users}; current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, label in users if key == current_owner_key), data.get("owner", team)); owner_var = tk.StringVar(value=current_owner_label)
        widgets = [("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), ("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fristart", tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, priority_var, *PRIORITIES)), ("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, *DUE_LABEL_TO_VALUE.keys()))]
        for row, (label, widget) in enumerate(widgets):
            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=7, padx=8); widget.grid(row=row, column=1, sticky="w", pady=7)
            try: widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)
            except Exception: pass
        day_label = tk.Label(form, text="Tag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")); day_entry = tk.Entry(form, textvariable=due_day_var, width=8)
        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")); workday_entry = tk.Entry(form, textvariable=due_workday_var, width=8)
        fixed_label = tk.Label(form, text="Konkretes Datum (TT.MM.JJJJ)", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")); fixed_entry = tk.Entry(form, textvariable=due_fixed_var, width=14)
        for r, lab, ent in [(5, day_label, day_entry), (6, workday_label, workday_entry), (7, fixed_label, fixed_entry)]: lab.grid(row=r, column=0, sticky="w", pady=7, padx=8); ent.grid(row=r, column=1, sticky="w", pady=7); ent.config(bg="white", fg=COLORS["text"], relief="solid", bd=1, highlightthickness=0)
        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), activebackground=COLORS["bg"]).grid(row=8, column=1, sticky="w", pady=7)
        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10, "bold")).grid(row=9, column=1, sticky="w", pady=(4, 10))
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
            tk.Label(sub_list, text="Unteraufgaben", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))
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

        tk.Label(win, text=item_title, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(win, text="Anlagen dienen zur Hinterlegung ausgearbeiteter Ergebnisse und Kommentare zur Bearbeitung. Dokumentationen/Leitfäden bitte in der Spalte Dokumentation pflegen.", bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 9), wraplength=820, justify="left").pack(anchor="w", padx=16, pady=(0, 8))

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
                tk.Label(list_frame, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe UI", 9, "bold"), padx=6, pady=4).grid(row=0, column=c, sticky="nsew")
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
        tk.Label(form, text="Anlagenpfad", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        tk.Button(form, text="Anlage auswählen", command=choose_path, bg=COLORS["blue"], fg="white", bd=0, padx=10, pady=5).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))
        entry = tk.Entry(form, textvariable=path_var, bg=COLORS["white"], fg=COLORS["text2"], relief="solid", bd=1, width=70)
        entry.grid(row=0, column=2, sticky="ew", pady=(0, 6))
        form.grid_columnconfigure(2, weight=1)
        def clear_placeholder(_event=None):
            if path_var.get() == placeholder:
                path_var.set("")
                entry.config(fg=COLORS["text"])
        entry.bind("<FocusIn>", clear_placeholder)

        tk.Label(form, text="Bemerkungen und Informationen:", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 4))
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
