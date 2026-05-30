import calendar
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

STATUS_OPEN = "Offen"
STATUS_IN_PROGRESS = "In Bearbeitung"
STATUS_DONE = "Erledigt"
STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]
TEAMS = ["Hauptbuch", "Kreditoren", "Debitoren", "Controlling"]
DEADLINE_TYPES = ["keine", "intern", "gesetzlich"]
PRIORITIES = ["normal", "hoch", "kritisch"]
DUE_FIXED = "fixed_date"
DUE_WORKDAY_MONTH = "workday_current_month"
DUE_WORKDAY_NEXT = "workday_next_month"
DUE_LABEL_TO_VALUE = {
    "Konkretes Datum": DUE_FIXED,
    "x. Werktag des Monats": DUE_WORKDAY_MONTH,
    "x. Werktag des Folgemonats": DUE_WORKDAY_NEXT,
}
DUE_VALUE_TO_LABEL = {v: k for k, v in DUE_LABEL_TO_VALUE.items()}
WARN_YELLOW_DAYS = 10
WARN_ORANGE_DAYS = 5

COLORS = {
    "bg": "#E8EEF5", "header": "#D3DEE9", "blue": "#004B93", "red": "#E30613",
    "orange": "#F59E0B", "yellow": "#FACC15", "green": "#16A34A", "dark_green": "#047857",
    "text": "#182431", "text2": "#445364", "line": "#91A3B5", "white": "#FFFFFF", "edit_bg": "#FEF3C7"
}


def _base_dir() -> Path:
    here = Path(__file__).resolve()
    if here.parent.name.lower() == "tools":
        return here.parent.parent / "Closing" / "MonthlyClose"
    return here.parent / "bin" / "Closing" / "MonthlyClose"

BASE_DIR = _base_dir()
PERIOD_DIR = BASE_DIR / "periods"
ATTACH_DIR = BASE_DIR / "attachments"
CONFIG_PATH = BASE_DIR / "monthly_close_config.json"
CATALOG_PATH = BASE_DIR / "monthly_close_task_catalog.json"


def month_key(d=None):
    d = d or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def add_month(key, delta):
    year, month = map(int, key.split("-"))
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}-{month:02d}"


def period_label(key):
    names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
    y, m = map(int, key.split("-"))
    return f"{names[m - 1]} {y}"


def parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


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


def next_business_day(d):
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


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


def due_date_for(period, day_next_month):
    next_key = add_month(period, 1)
    y, m = map(int, next_key.split("-"))
    day = max(1, min(int(day_next_month), calendar.monthrange(y, m)[1]))
    return f"{y:04d}-{m:02d}-{day:02d}"


def resolve_due_date(task, period):
    mode = task.get("due_mode", DUE_FIXED)
    if mode == DUE_WORKDAY_MONTH:
        y, m = map(int, period.split("-"))
        return nth_business_day(y, m, task.get("due_workday") or 1).strftime("%Y-%m-%d")
    if mode == DUE_WORKDAY_NEXT:
        next_period = add_month(period, 1)
        y, m = map(int, next_period.split("-"))
        return nth_business_day(y, m, task.get("due_workday") or 1).strftime("%Y-%m-%d")
    due = parse_date(task.get("due_date", ""))
    return next_business_day(due).strftime("%Y-%m-%d") if due else ""


def due_rule_text(task):
    if task.get("due_mode") == DUE_WORKDAY_MONTH:
        return f"{task.get('due_workday') or 1}. Werktag Monat"
    if task.get("due_mode") == DUE_WORKDAY_NEXT:
        return f"{task.get('due_workday') or 1}. Werktag Folgemonat"
    return ""


def due_display(task):
    rule = due_rule_text(task)
    return f"{task.get('due_date', '')}\n{rule}" if rule else task.get("due_date", "")


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
    examples = {
        "Hauptbuch": ["Bankabstimmung durchführen", "Rückstellungen prüfen", "Abgrenzungen buchen", "Sachkonten prüfen"],
        "Kreditoren": ["Offene Posten prüfen", "Lieferantenabstimmung durchführen", "Rechnungsabgrenzung prüfen", "Zahlungsläufe kontrollieren"],
        "Debitoren": ["Offene Posten prüfen", "Mahnstatus prüfen", "Erlösabgrenzung prüfen", "Kundensalden abstimmen"],
        "Controlling": ["Kostenstellen prüfen", "Reporting vorbereiten", "Konzernmeldung vorbereiten", "Abweichungsanalyse erstellen"],
    }
    tasks = []
    for team in TEAMS:
        names = examples[team] + ["Unbenannte Aufgabe 1", "Unbenannte Aufgabe 2", "Unbenannte Aufgabe 3"]
        for idx, title in enumerate(names, 1):
            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]
            task = {
                "id": make_task_id(team, idx), "team": team, "title": title, "owner": team, "owner_user_key": "",
                "due_date": due_date_for(period, 10 if is_legal else min(20, 3 + idx * 2)), "due_mode": DUE_FIXED, "due_workday": None,
                "deadline_type": "gesetzlich" if is_legal else "intern", "priority": "kritisch" if is_legal else "normal",
                "required": True, "recurring": False, "catalog_id": "", "status": STATUS_OPEN,
                "attachments": [], "comments": [], "done_at": None, "done_by": None,
            }
            tasks.append(task)
    return tasks


def normalize_task(task, period):
    task.setdefault("owner_user_key", "")
    task.setdefault("attachments", [])
    task.setdefault("comments", [])
    task.setdefault("status", STATUS_OPEN)
    task.setdefault("deadline_type", "intern")
    task.setdefault("priority", "normal")
    task.setdefault("due_mode", DUE_FIXED)
    task.setdefault("due_workday", None)
    task.setdefault("recurring", False)
    task.setdefault("catalog_id", "")
    if task["deadline_type"] not in DEADLINE_TYPES:
        task["deadline_type"] = "intern"
    if task["due_mode"] not in (DUE_FIXED, DUE_WORKDAY_MONTH, DUE_WORKDAY_NEXT):
        task["due_mode"] = DUE_FIXED
    if task["due_mode"] != DUE_FIXED:
        task["due_date"] = resolve_due_date(task, period)
    return task


def load_period(period):
    ensure_storage()
    path = period_path(period)
    if not path.exists():
        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), "tasks": default_tasks(period)}
        save_period(period, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("tasks", [])
    for task in data["tasks"]:
        normalize_task(task, period)
    return data


def save_period(period, data):
    ensure_storage()
    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def catalog_entry_to_task(entry, period, index):
    task = {
        "id": make_task_id(entry.get("team", "Team"), index), "team": entry.get("team"), "title": entry.get("title"),
        "owner": entry.get("owner", entry.get("team")), "owner_user_key": entry.get("owner_user_key", ""),
        "due_mode": entry.get("due_mode", DUE_FIXED), "due_workday": entry.get("due_workday"),
        "deadline_type": entry.get("deadline_type", "keine"), "priority": entry.get("priority", "normal"),
        "required": entry.get("required", True), "recurring": True, "catalog_id": entry.get("catalog_id", ""),
        "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, "done_by": None,
    }
    if task["due_mode"] == DUE_FIXED:
        src_due = parse_date(entry.get("due_date", ""))
        task["due_date"] = due_date_for(period, src_due.day if src_due else 10)
    else:
        task["due_date"] = resolve_due_date(task, period)
    return task


def apply_catalog_to_period(period):
    data = load_period(period)
    catalog = load_catalog()
    changed = False
    tasks = data.setdefault("tasks", [])
    for entry in catalog.get("tasks", []):
        if not entry.get("recurring", True):
            continue
        start_period = entry.get("start_period", month_key())
        if period <= start_period:
            continue
        catalog_id = entry.get("catalog_id")
        existing = next((t for t in tasks if t.get("catalog_id") == catalog_id and not t.get("deleted")), None)
        if existing:
            keep = {"status": existing.get("status", STATUS_OPEN), "attachments": existing.get("attachments", []), "comments": existing.get("comments", []), "done_at": existing.get("done_at"), "done_by": existing.get("done_by")}
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


def ensure_period_window():
    ensure_storage()
    current = month_key()
    for offset in range(0, 3):
        p = add_month(current, offset)
        load_period(p)
        apply_catalog_to_period(p)


def list_periods():
    ensure_period_window()
    return sorted(p.stem for p in PERIOD_DIR.glob("*.json"))


def warning_level(task, today=None):
    if task.get("status") == STATUS_DONE or task.get("deadline_type") == "keine":
        return "done" if task.get("status") == STATUS_DONE else "none"
    due = parse_date(task.get("due_date", ""))
    if not due:
        return "none"
    today = today or date.today()
    days = (due - today).days
    if days < 0:
        return "overdue"
    if days == 0:
        return "today"
    if days <= WARN_ORANGE_DAYS:
        return "orange"
    if days <= WARN_YELLOW_DAYS:
        return "yellow"
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


class MonthlyCloseUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        ensure_period_window()
        self.period = month_key()
        self.data = apply_catalog_to_period(self.period)
        self.selected_team = None
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
        return {"Standard": 1, "Administrator": 2, "Wagnerm": 3}.get(role, 1) >= 2

    def user_choices(self):
        users = getattr(self.app, "user_data", {}).get("users", {})
        choices = [("", "Team / keine Person")]
        for key, data in sorted(users.items(), key=lambda item: item[1].get("display_name", item[0]).casefold()):
            choices.append((key, data.get("display_name", key)))
        return choices

    def clear_frame(self):
        for child in self.frame.winfo_children():
            child.destroy()

    def reload(self):
        self.data = apply_catalog_to_period(self.period)

    def save(self):
        save_period(self.period, self.data)

    def tasks(self):
        return [t for t in self.data.get("tasks", []) if not t.get("deleted")]

    def team_tasks(self, team):
        return [t for t in self.tasks() if t.get("team") == team]

    def draw_progress(self, parent, percent, width=260, height=20, bg=None):
        bg = bg or parent.cget("bg")
        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)
        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")
        fill_w = int(width * max(0, min(100, percent)) / 100)
        if fill_w:
            c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), outline=progress_color(percent))
        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], font=("Segoe UI", 9, "bold"))
        return c

    def render_period_controls(self, parent):
        row = tk.Frame(parent, bg=COLORS["bg"])
        row.pack(fill="x", padx=24, pady=(10, 4))
        tk.Button(row, text="< vorheriger Monat", command=lambda: self.change_period(add_month(self.period, -1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(side="left")
        periods = list_periods()
        labels = {period_label(k): k for k in periods}
        selected = tk.StringVar(value=period_label(self.period))
        menu = tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: self.change_period(labels[label]))
        menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)
        menu.pack(side="left", padx=10)
        tk.Button(row, text="nächster Monat >", command=lambda: self.change_period(add_month(self.period, 1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(side="left")
        tk.Frame(row, bg=COLORS["bg"]).pack(side="left", fill="x", expand=True)
        if self.can_edit():
            self.render_edit_button(row)

    def render_edit_button(self, parent):
        btn = tk.Canvas(parent, width=30, height=30, bg=COLORS["blue"] if not self.edit_mode else COLORS["orange"], highlightthickness=0, bd=0, cursor="hand2")
        btn.pack(side="right", padx=(8, 0))
        btn.create_line(9, 21, 21, 9, fill="white", width=3)
        btn.create_polygon(20, 8, 23, 5, 25, 7, 22, 10, fill="white", outline="white")
        btn.create_line(8, 22, 13, 21, fill="white", width=2)
        btn.bind("<Button-1>", lambda _e: self.toggle_edit_mode())
        btn.bind("<Enter>", lambda _e: self.show_tooltip(btn, "Bearbeiten"))
        btn.bind("<Leave>", lambda _e: self.hide_tooltip())

    def show_tooltip(self, widget, text):
        self.hide_tooltip()
        self.tooltip = tk.Toplevel(widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.geometry(f"+{widget.winfo_rootx() + 12}+{widget.winfo_rooty() + 34}")
        tk.Label(self.tooltip, text=text, bg="#111827", fg="white", font=("Segoe UI", 9), padx=6, pady=3).pack()

    def hide_tooltip(self):
        if self.tooltip:
            try: self.tooltip.destroy()
            except Exception: pass
            self.tooltip = None

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def render_edit_tools(self, parent, team=None):
        if not (self.can_edit() and self.edit_mode):
            return
        row = tk.Frame(parent, bg=COLORS["edit_bg"], bd=1, relief="solid")
        row.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=7)
        if team:
            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: self.open_task_dialog(team), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)
        tk.Button(row, text="Aufgaben dieses Monats allen Monaten zuweisen", command=self.apply_current_tasks_to_all_months, bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=5).pack(side="left", padx=8)

    def change_period(self, period):
        self.period = period
        self.reload()
        self.selected_team = None
        self.render_dashboard()

    def render_dashboard(self):
        self.selected_team = None
        self.clear_frame()
        self.render_period_controls(self.frame)
        self.render_edit_tools(self.frame)
        stats = calc_stats(self.tasks())
        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        top.pack(fill="x", padx=24, pady=(8, 10))
        tk.Label(top, text=f"Monatsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=14, pady=(6, 2))
        tk.Label(top, text=f"Gesamt: {stats['done']} erledigt / {stats['in_progress']} in Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=14)
        holder = tk.Frame(top, bg=COLORS["white"])
        holder.pack(anchor="w", padx=14, pady=(8, 10))
        self.draw_progress(holder, stats["percent"], width=520, height=24, bg=COLORS["white"]).pack(side="left")
        self.render_warnings(self.frame)
        cards = tk.Frame(self.frame, bg=COLORS["bg"])
        cards.pack(fill="both", expand=True, padx=24, pady=8)
        for idx, team in enumerate(TEAMS):
            self.render_team_card(cards, team, idx)

    def render_warnings(self, parent):
        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", "yellow") and t.get("status") != STATUS_DONE]
        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid")
        box.pack(fill="x", padx=24, pady=(0, 8))
        if warnings:
            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 3))
            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:
                tk.Label(box, text=f"- {task['title']} | {task['team']} | fällig am {task.get('due_date')} | {task.get('deadline_type')}", bg=box["bg"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=1)
        else:
            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], fg=COLORS["dark_green"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)

    def next_relevant_task(self, tasks):
        open_tasks = [t for t in tasks if t.get("status") != STATUS_DONE and t.get("deadline_type") != "keine"]
        return sorted(open_tasks, key=lambda t: parse_date(t.get("due_date", "9999-12-31")) or date.max)[0] if open_tasks else None

    def bind_click_recursive(self, widget, command):
        widget.bind("<Button-1>", lambda _e: command())
        widget.configure(cursor="hand2")
        for child in widget.winfo_children():
            self.bind_click_recursive(child, command)

    def render_team_card(self, parent, team, idx):
        row, col = divmod(idx, 2)
        tasks = self.team_tasks(team)
        stats = calc_stats(tasks)
        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, "orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")
        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == "orange" else COLORS["line"]
        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", highlightbackground=border, highlightcolor=border, highlightthickness=2)
        card.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(card, text=f"{stats['done']} / {stats['total']} erledigt   |   offen: {stats['open']}   |   in Bearbeitung: {stats['in_progress']}   |   kritisch: {stats['critical']}", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=18)
        holder = tk.Frame(card, bg=COLORS["white"])
        holder.pack(anchor="w", padx=18, pady=(10, 8))
        self.draw_progress(holder, stats["percent"], width=420, height=26, bg=COLORS["white"]).pack()
        nxt = self.next_relevant_task(tasks)
        txt = "Nächste Frist: keine relevanten offenen Fristen" if not nxt else f"Nächste Frist: {nxt.get('due_date')} | {nxt.get('title')}"
        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and warning_level(nxt) in ("overdue", "today", "orange") else COLORS["text2"], font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(0, 14))
        self.bind_click_recursive(card, lambda t=team: self.render_team_detail(t))

    def render_team_detail(self, team):
        self.selected_team = team
        self.clear_frame()
        self.render_period_controls(self.frame)
        self.render_edit_tools(self.frame, team=team)
        stats = calc_stats(self.team_tasks(team))
        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        head.pack(fill="x", padx=24, pady=(8, 10))
        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))
        tk.Label(head, text=f"{team} | Monatsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=12)
        tk.Label(head, text=f"Fortschritt: {stats['done']} / {stats['total']} erledigt | {stats['percent']}%", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=12)
        bar = tk.Frame(head, bg=COLORS["white"])
        bar.pack(anchor="w", padx=12, pady=(6, 10))
        self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()
        self.render_task_table(team)

    def render_task_table(self, team):
        table = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        table.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        headers = ["Status", "Aufgabe", "Zuständig", "Fällig", "Fristart", "Priorität", "Wiederkehrend", "Anlagen", "Aktion"]
        if self.edit_mode and self.can_edit():
            headers.append("Bearbeiten")
        for col, h in enumerate(headers):
            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), padx=8, pady=6).grid(row=0, column=col, sticky="nsew")
        for idx, task in enumerate(self.team_tasks(team), 1):
            bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) in ("overdue", "today", "orange") else COLORS["white"]
            tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=("Segoe UI", 13, "bold")).grid(row=idx, column=0, sticky="nsew", padx=1, pady=1)
            values = [task.get("title"), task.get("owner"), due_display(task), task.get("deadline_type"), task.get("priority"), "Ja" if task.get("recurring") else "Nein"]
            for col, val in enumerate(values, 1):
                tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=8, pady=6, anchor="w", justify="left").grid(row=idx, column=col, sticky="nsew", padx=1, pady=1)
            tk.Button(table, text=f"📎 {len(task.get('attachments', []))}", command=lambda t=task: self.show_attachments(t), bg=bg, fg=COLORS["blue"], bd=0).grid(row=idx, column=7, sticky="nsew", padx=1, pady=1)
            status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))
            menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: self.set_status(t, value))
            menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0)
            menu.grid(row=idx, column=8, sticky="nsew", padx=1, pady=1)
            if self.edit_mode and self.can_edit():
                action = tk.Frame(table, bg=bg)
                action.grid(row=idx, column=9, sticky="nsew", padx=1, pady=1)
                tk.Button(action, text="Bearbeiten", command=lambda t=task: self.open_task_dialog(team, t), bg=COLORS["blue"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
                tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), bg=COLORS["red"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
        for col in range(len(headers)):
            table.grid_columnconfigure(col, weight=1 if col in (1, 2, 3) else 0)

    def find_task(self, task_id):
        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not t.get("deleted")), None)

    def toggle_done(self, task):
        real = self.find_task(task["id"])
        if not real: return
        if real.get("status") == STATUS_DONE:
            real.update({"status": STATUS_OPEN, "done_at": None, "done_by": None})
        else:
            if real.get("deadline_type") == "gesetzlich" and not messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"):
                return
            real.update({"status": STATUS_DONE, "done_at": datetime.now().isoformat(timespec="seconds"), "done_by": getattr(self.app, "current_user_display", "") or ""})
        self.save(); self.render_team_detail(real["team"])

    def set_status(self, task, status):
        real = self.find_task(task["id"])
        if not real: return
        if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"):
            self.render_team_detail(real["team"]); return
        real["status"] = status
        real["done_at"] = datetime.now().isoformat(timespec="seconds") if status == STATUS_DONE else None
        real["done_by"] = getattr(self.app, "current_user_display", "") or "" if status == STATUS_DONE else None
        self.save(); self.render_team_detail(real["team"])

    def next_task_index(self, team):
        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1

    def task_to_catalog_entry(self, task):
        catalog_id = task.get("catalog_id") or f"rec_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        task["catalog_id"] = catalog_id
        return {k: task.get(k) for k in ["catalog_id", "team", "title", "owner", "owner_user_key", "due_date", "due_mode", "due_workday", "deadline_type", "priority", "required", "recurring"]} | {"start_period": self.period, "recurring": True}

    def upsert_catalog_entry(self, task):
        catalog = load_catalog(); entry = self.task_to_catalog_entry(task); tasks = catalog.setdefault("tasks", [])
        for idx, existing in enumerate(tasks):
            if existing.get("catalog_id") == entry["catalog_id"]:
                entry["start_period"] = existing.get("start_period", self.period); tasks[idx] = entry; break
        else:
            tasks.append(entry)
        save_catalog(catalog); return entry["catalog_id"]

    def remove_catalog_entry(self, catalog_id):
        if not catalog_id: return
        catalog = load_catalog(); catalog["tasks"] = [t for t in catalog.get("tasks", []) if t.get("catalog_id") != catalog_id]; save_catalog(catalog)

    def propagate_recurring_to_future_months(self, catalog_id):
        if not catalog_id: return
        for period in list_periods():
            if period > self.period: apply_catalog_to_period(period)

    def open_task_dialog(self, team, task=None):
        if not self.can_edit(): return
        is_new = task is None
        win = tk.Toplevel(self.root); win.title("Aufgabe anlegen" if is_new else "Aufgabe bearbeiten"); win.configure(bg=COLORS["bg"]); win.geometry("650x510"); win.transient(self.root); win.grab_set()
        data = task or {"title": "", "owner": team, "owner_user_key": "", "due_date": due_date_for(self.period, 10), "deadline_type": "keine", "priority": "normal", "due_mode": DUE_FIXED, "due_workday": None, "recurring": False}
        form = tk.Frame(win, bg=COLORS["bg"]); form.pack(fill="both", expand=True, padx=18, pady=18)
        title_var = tk.StringVar(value=data.get("title", "")); due_var = tk.StringVar(value=data.get("due_date", due_date_for(self.period, 10)))
        deadline_var = tk.StringVar(value=data.get("deadline_type", "keine") if data.get("deadline_type") in DEADLINE_TYPES else "keine")
        priority_var = tk.StringVar(value=data.get("priority", "normal")); recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))
        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", DUE_FIXED), "Konkretes Datum")); due_workday_var = tk.StringVar(value=str(data.get("due_workday") or "")); calculated_var = tk.StringVar(value="")
        users = self.user_choices(); user_labels = {label: key for key, label in users}
        current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, label in users if key == current_owner_key), data.get("owner", team)); owner_var = tk.StringVar(value=current_owner_label)
        static_widgets = [("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), ("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fristart", tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, priority_var, *PRIORITIES)), ("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, *DUE_LABEL_TO_VALUE.keys()))]
        for row, (label, widget) in enumerate(static_widgets):
            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=7)
            widget.grid(row=row, column=1, sticky="w", pady=7)
            try: widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)
            except Exception: pass
        due_date_label = tk.Label(form, text="Konkretes Datum (YYYY-MM-DD)", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"))
        due_date_entry = tk.Entry(form, textvariable=due_var, width=18)
        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"))
        workday_entry = tk.Entry(form, textvariable=due_workday_var, width=8)
        due_date_label.grid(row=5, column=0, sticky="w", pady=7); due_date_entry.grid(row=5, column=1, sticky="w", pady=7)
        workday_label.grid(row=6, column=0, sticky="w", pady=7); workday_entry.grid(row=6, column=1, sticky="w", pady=7)
        for widget in (due_date_entry, workday_entry): widget.config(bg="white", fg=COLORS["text"], relief="solid", bd=1, highlightthickness=0)
        def refresh_due_input_visibility():
            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_FIXED)
            if mode == DUE_FIXED:
                due_date_label.grid(); due_date_entry.grid(); workday_label.grid_remove(); workday_entry.grid_remove()
            else:
                due_date_label.grid_remove(); due_date_entry.grid_remove(); workday_label.grid(); workday_entry.grid()
        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), activebackground=COLORS["bg"]).grid(row=7, column=1, sticky="w", pady=7)
        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10, "bold")).grid(row=8, column=1, sticky="w", pady=(4, 10))
        def update_calculated(*_):
            refresh_due_input_visibility(); mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_FIXED)
            preview = {"due_mode": mode, "due_date": due_var.get().strip(), "due_workday": due_workday_var.get().strip() or 1}
            calculated_var.set("Berechnetes Fälligkeitsdatum: " + (resolve_due_date(preview, self.period) or "-"))
        for var in (due_mode_var, due_var, due_workday_var): var.trace_add("write", update_calculated)
        update_calculated()
        def save_dialog():
            title = title_var.get().strip(); mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_FIXED)
            if not title: messagebox.showwarning("Monatsabschluss", "Bitte einen Aufgabennamen eingeben."); return
            workday_value = None
            if mode != DUE_FIXED:
                try:
                    workday_value = int(due_workday_var.get().strip()); assert workday_value > 0
                except Exception:
                    messagebox.showwarning("Monatsabschluss", "Bitte eine gültige positive Werktag-Nummer eingeben."); return
            elif due_var.get().strip() and not parse_date(due_var.get().strip()):
                messagebox.showwarning("Monatsabschluss", "Bitte ein gültiges Fälligkeitsdatum im Format YYYY-MM-DD eingeben."); return
            owner_label = owner_var.get(); owner_key = user_labels.get(owner_label, ""); owner_text = owner_label if owner_key else team
            payload = {"title": title, "owner": owner_text, "owner_user_key": owner_key, "due_mode": mode, "due_workday": workday_value, "deadline_type": deadline_var.get(), "priority": priority_var.get(), "recurring": bool(recurring_var.get())}
            payload["due_date"] = resolve_due_date({**payload, "due_date": due_var.get().strip()}, self.period)
            if is_new:
                real = {"id": make_task_id(team, self.next_task_index(team)), "team": team, "required": True, "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, "done_by": None, "catalog_id": "", **payload}
                self.data.setdefault("tasks", []).append(real)
            else:
                real = self.find_task(task["id"])
                if not real: return
                real.update(payload)
            if real.get("recurring"):
                catalog_id = self.upsert_catalog_entry(real); real["catalog_id"] = catalog_id; self.propagate_recurring_to_future_months(catalog_id)
            else:
                if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))
                real["catalog_id"] = ""
            self.save(); win.destroy(); self.reload(); self.render_team_detail(team)
        buttons = tk.Frame(form, bg=COLORS["bg"]); buttons.grid(row=9, column=0, columnspan=2, sticky="e", pady=(18, 0))
        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="left", padx=6)
        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="left", padx=6)

    def delete_task(self, task):
        real = self.find_task(task["id"])
        if not real: return
        msg = f"Aufgabe wirklich löschen?\n\n{real.get('title')}"
        if real.get("attachments"): msg += "\n\nDiese Aufgabe hat Anlagen. Die Dateien bleiben im Anlagenordner erhalten, die Referenz wird aus der Aufgabe entfernt."
        if not messagebox.askyesno("Aufgabe löschen", msg): return
        if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))
        self.data["tasks"] = [t for t in self.data.get("tasks", []) if t.get("id") != real.get("id")]
        self.save(); self.render_team_detail(real["team"])

    def clone_task_for_period(self, task, target_period, index):
        clone = {"id": make_task_id(task.get("team", "Team"), index), "team": task.get("team"), "title": task.get("title"), "owner": task.get("owner", task.get("team")), "owner_user_key": task.get("owner_user_key", ""), "due_mode": task.get("due_mode", DUE_FIXED), "due_workday": task.get("due_workday"), "deadline_type": task.get("deadline_type", "keine"), "priority": task.get("priority", "normal"), "required": task.get("required", True), "recurring": task.get("recurring", False), "catalog_id": task.get("catalog_id", ""), "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, "done_by": None}
        if clone["due_mode"] == DUE_FIXED:
            due = parse_date(task.get("due_date", "")); clone["due_date"] = due_date_for(target_period, due.day if due else 10)
        else:
            clone["due_date"] = resolve_due_date(clone, target_period)
        return clone

    def apply_current_tasks_to_all_months(self):
        if not self.can_edit(): return
        if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus {period_label(self.period)} wird auf alle vorhandenen Monate übertragen.\n\nStatus, Anlagen, Kommentare und Erledigt-Infos werden in den Zielmonaten zurückgesetzt.\n\nFortfahren?"): return
        source_tasks = [t for t in self.tasks()]
        for target in list_periods():
            grouped_index = {}; cloned = []
            for task in source_tasks:
                team = task.get("team", "Team"); grouped_index[team] = grouped_index.get(team, 0) + 1
                cloned.append(self.clone_task_for_period(task, target, grouped_index[team]))
            data = load_period(target); data["tasks"] = cloned; data["updated_from_period"] = self.period; data["updated_at"] = datetime.now().isoformat(timespec="seconds"); save_period(target, data)
        self.reload(); messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben dieses Monats wurden allen vorhandenen Monaten zugewiesen.")
        self.render_team_detail(self.selected_team) if self.selected_team else self.render_dashboard()

    def show_attachments(self, task):
        win = tk.Toplevel(self.root); win.title(f"Anlagen - {task.get('title')}"); win.configure(bg=COLORS["bg"]); win.geometry("720x420"); win.transient(self.root); task_id = task["id"]
        def refresh():
            for child in list_frame.winfo_children(): child.destroy()
            real = self.find_task(task_id)
            if not real: return
            for idx, att in enumerate(real.get("attachments", [])):
                tk.Label(list_frame, text=att.get("name"), bg=COLORS["white"], fg=COLORS["text"], anchor="w").grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, pady=3)
                tk.Button(list_frame, text="Entfernen", command=lambda a=att: remove_attachment(a), bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, pady=3)
        def add_attachment():
            file_path = filedialog.askopenfilename(title="Anlage auswählen")
            if not file_path: return
            real = self.find_task(task_id)
            if not real: return
            dest_dir = ATTACH_DIR / self.period / real["team"] / real["id"]; dest_dir.mkdir(parents=True, exist_ok=True)
            src = Path(file_path); dest = dest_dir / src.name; counter = 1
            while dest.exists(): dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"; counter += 1
            shutil.copy2(src, dest); real.setdefault("attachments", []).append({"name": dest.name, "path": str(dest), "original_path": str(src), "added_at": datetime.now().isoformat(timespec="seconds")})
            self.save(); refresh(); self.render_team_detail(real["team"])
        def remove_attachment(att):
            real = self.find_task(task_id)
            if real and messagebox.askyesno("Anlage entfernen", f"Anlage entfernen?\n\n{att.get('name')}"):
                real["attachments"] = [a for a in real.get("attachments", []) if a != att]; self.save(); refresh(); self.render_team_detail(real["team"])
        tk.Label(win, text=task.get("title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid"); list_frame.pack(fill="both", expand=True, padx=16, pady=8); list_frame.grid_columnconfigure(0, weight=1)
        tk.Button(win, text="Anlage hinzufügen", command=add_attachment, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(anchor="e", padx=16, pady=(0, 14)); refresh()

    def open_attachment(self, path):
        if not path or not os.path.exists(path): messagebox.showwarning("Anlage", "Datei wurde nicht gefunden."); return
        try:
            if os.name == "nt": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as exc: messagebox.showerror("Anlage", str(exc))


def render(app):
    MonthlyCloseUI(app)
