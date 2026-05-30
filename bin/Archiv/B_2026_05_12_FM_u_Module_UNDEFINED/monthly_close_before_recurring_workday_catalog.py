import json
import os
import shutil
import subprocess
import sys
import calendar
from datetime import date, datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

MODULE_TITLE = "Monatsabschluss"
STATUS_OPEN = "Offen"
STATUS_IN_PROGRESS = "In Bearbeitung"
STATUS_DONE = "Erledigt"
STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]
TEAMS = ["Hauptbuch", "Kreditoren", "Debitoren", "Controlling"]
DEADLINE_TYPES = ["keine", "intern", "gesetzlich"]
PRIORITIES = ["normal", "hoch", "kritisch"]
WARN_YELLOW_DAYS = 10
WARN_ORANGE_DAYS = 5

COLORS = {
    "bg": "#E8EEF5",
    "header": "#D3DEE9",
    "blue": "#004B93",
    "red": "#E30613",
    "orange": "#F59E0B",
    "yellow": "#FACC15",
    "green": "#16A34A",
    "dark_green": "#047857",
    "text": "#182431",
    "text2": "#445364",
    "line": "#91A3B5",
    "white": "#FFFFFF",
    "edit_bg": "#FEF3C7",
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


def due_date_for(period, day_next_month):
    next_key = add_month(period, 1)
    y, m = map(int, next_key.split("-"))
    day = max(1, min(int(day_next_month), calendar.monthrange(y, m)[1]))
    return f"{y:04d}-{m:02d}-{day:02d}"


def make_task_id(team, index):
    safe = team.lower().replace(" ", "_").replace("/", "_")
    return f"{safe}_{index:02d}"


def ensure_storage():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    PERIOD_DIR.mkdir(parents=True, exist_ok=True)
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({"teams": TEAMS, "warning_days": {"yellow": WARN_YELLOW_DAYS, "orange": WARN_ORANGE_DAYS}}, ensure_ascii=False, indent=2), encoding="utf-8")


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
        for idx, title in enumerate(names, start=1):
            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]
            tasks.append({
                "id": make_task_id(team, idx),
                "team": team,
                "title": title,
                "owner": team,
                "owner_user_key": "",
                "due_date": due_date_for(period, 10 if is_legal else min(20, 3 + idx * 2)),
                "deadline_type": "gesetzlich" if is_legal else "intern",
                "priority": "kritisch" if is_legal else "normal",
                "required": True,
                "status": STATUS_OPEN,
                "attachments": [],
                "comments": [],
                "done_at": None,
                "done_by": None,
            })
    return tasks


def period_path(period):
    return PERIOD_DIR / f"{period}.json"


def save_period(period, data):
    ensure_storage()
    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_period(period):
    ensure_storage()
    path = period_path(period)
    if not path.exists():
        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), "tasks": default_tasks(period)}
        save_period(period, data)
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    for t in data.get("tasks", []):
        t.setdefault("owner_user_key", "")
        t.setdefault("attachments", [])
        t.setdefault("comments", [])
        t.setdefault("status", STATUS_OPEN)
        t.setdefault("deadline_type", "intern")
        if t.get("deadline_type") not in DEADLINE_TYPES:
            t["deadline_type"] = "intern"
    return data


def ensure_period_window():
    ensure_storage()
    current = month_key()
    for offset in range(0, 3):
        load_period(add_month(current, offset))


def list_periods():
    ensure_period_window()
    return sorted(p.stem for p in PERIOD_DIR.glob("*.json"))


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def warning_level(task, today=None):
    if task.get("status") == STATUS_DONE:
        return "done"
    if task.get("deadline_type") == "keine":
        return "none"
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
    if percent >= 100:
        return COLORS["dark_green"]
    if percent >= 75:
        return COLORS["green"]
    if percent >= 50:
        return COLORS["yellow"]
    if percent >= 25:
        return COLORS["orange"]
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
        self.data = load_period(self.period)
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
        self.data = load_period(self.period)

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
        # Statusmeldungen wurden bewusst entfernt. Der Bereich bleibt nur als ruhiger Spacer.
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
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None

    def toggle_edit_mode(self):
        self.edit_mode = not self.edit_mode
        if self.selected_team:
            self.render_team_detail(self.selected_team)
        else:
            self.render_dashboard()

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
        all_stats = calc_stats(self.tasks())
        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")
        top.pack(fill="x", padx=24, pady=(8, 10))
        tk.Label(top, text=f"Monatsabschluss {period_label(self.period)}", bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=14, pady=(6, 2))
        tk.Label(top, text=f"Gesamt: {all_stats['done']} erledigt / {all_stats['in_progress']} in Bearbeitung / {all_stats['open']} offen / {all_stats['critical']} kritisch / {all_stats['overdue']} überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=14)
        holder = tk.Frame(top, bg=COLORS["white"])
        holder.pack(anchor="w", padx=14, pady=(8, 10))
        self.draw_progress(holder, all_stats["percent"], width=520, height=24, bg=COLORS["white"]).pack(side="left")
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
        if not open_tasks:
            return None
        return sorted(open_tasks, key=lambda t: (parse_date(t.get("due_date", "9999-12-31")) or date.max, 0 if t.get("deadline_type") == "gesetzlich" else 1))[0]

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
        tasks = self.team_tasks(team)
        stats = calc_stats(tasks)
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
        headers = ["Status", "Aufgabe", "Zuständig", "Fällig", "Fristart", "Priorität", "Anlagen", "Aktion"]
        if self.edit_mode and self.can_edit():
            headers.append("Bearbeiten")
        for col, h in enumerate(headers):
            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"), padx=8, pady=6).grid(row=0, column=col, sticky="nsew")
        for idx, task in enumerate(self.team_tasks(team), start=1):
            bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) in ("overdue", "today", "orange") else COLORS["white"]
            status_btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=("Segoe UI", 13, "bold"))
            status_btn.grid(row=idx, column=0, sticky="nsew", padx=1, pady=1)
            values = [task.get("title"), task.get("owner"), task.get("due_date"), task.get("deadline_type"), task.get("priority")]
            for col, val in enumerate(values, start=1):
                tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=8, pady=6, anchor="w").grid(row=idx, column=col, sticky="nsew", padx=1, pady=1)
            tk.Button(table, text=f"📎 {len(task.get('attachments', []))}", command=lambda t=task: self.show_attachments(t), bg=bg, fg=COLORS["blue"], bd=0).grid(row=idx, column=6, sticky="nsew", padx=1, pady=1)
            status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))
            menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: self.set_status(t, value))
            menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0)
            menu.grid(row=idx, column=7, sticky="nsew", padx=1, pady=1)
            if self.edit_mode and self.can_edit():
                action = tk.Frame(table, bg=bg)
                action.grid(row=idx, column=8, sticky="nsew", padx=1, pady=1)
                tk.Button(action, text="Bearbeiten", command=lambda t=task: self.open_task_dialog(team, t), bg=COLORS["blue"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
                tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), bg=COLORS["red"], fg="white", bd=0, padx=6).pack(side="left", padx=2, pady=3)
        for col in range(len(headers)):
            table.grid_columnconfigure(col, weight=1 if col in (1, 2) else 0)

    def find_task(self, task_id):
        for task in self.data.get("tasks", []):
            if task.get("id") == task_id and not task.get("deleted"):
                return task
        return None

    def toggle_done(self, task):
        real = self.find_task(task["id"])
        if not real:
            return
        if real.get("status") == STATUS_DONE:
            real["status"] = STATUS_OPEN
            real["done_at"] = None
            real["done_by"] = None
        else:
            if real.get("deadline_type") == "gesetzlich":
                if not messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"):
                    return
            real["status"] = STATUS_DONE
            real["done_at"] = datetime.now().isoformat(timespec="seconds")
            real["done_by"] = getattr(self.app, "current_user_display", "") or ""
        self.save()
        self.render_team_detail(real["team"])

    def set_status(self, task, status):
        real = self.find_task(task["id"])
        if not real:
            return
        if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich":
            if not messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt markieren?"):
                self.render_team_detail(real["team"])
                return
        real["status"] = status
        if status == STATUS_DONE:
            real["done_at"] = datetime.now().isoformat(timespec="seconds")
            real["done_by"] = getattr(self.app, "current_user_display", "") or ""
        else:
            real["done_at"] = None
            real["done_by"] = None
        self.save()
        self.render_team_detail(real["team"])

    def next_task_index(self, team):
        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1

    def open_task_dialog(self, team, task=None):
        if not self.can_edit():
            return
        is_new = task is None
        win = tk.Toplevel(self.root)
        win.title("Aufgabe anlegen" if is_new else "Aufgabe bearbeiten")
        win.configure(bg=COLORS["bg"])
        win.geometry("560x390")
        win.transient(self.root)
        win.grab_set()
        data = task or {"title": "", "owner": team, "owner_user_key": "", "due_date": due_date_for(self.period, 10), "deadline_type": "keine", "priority": "normal"}
        form = tk.Frame(win, bg=COLORS["bg"])
        form.pack(fill="both", expand=True, padx=18, pady=18)
        title_var = tk.StringVar(value=data.get("title", ""))
        due_var = tk.StringVar(value=data.get("due_date", due_date_for(self.period, 10)))
        deadline_var = tk.StringVar(value=data.get("deadline_type", "keine" if data.get("deadline_type") not in DEADLINE_TYPES else data.get("deadline_type")))
        priority_var = tk.StringVar(value=data.get("priority", "normal"))
        users = self.user_choices()
        user_labels = {label: key for key, label in users}
        current_owner_key = data.get("owner_user_key", "")
        current_owner_label = next((label for key, label in users if key == current_owner_key), data.get("owner", team))
        owner_var = tk.StringVar(value=current_owner_label)
        fields = [
            ("Aufgabenname", tk.Entry(form, textvariable=title_var, width=46)),
            ("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())),
            ("Fällig (YYYY-MM-DD)", tk.Entry(form, textvariable=due_var, width=18)),
            ("Fristart", tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)),
            ("Priorität", tk.OptionMenu(form, priority_var, *PRIORITIES)),
        ]
        for row, (label, widget) in enumerate(fields):
            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8)
            widget.grid(row=row, column=1, sticky="w", pady=8)
            try:
                widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)
            except Exception:
                pass

        def save_dialog():
            title = title_var.get().strip()
            due = due_var.get().strip()
            if not title:
                messagebox.showwarning("Monatsabschluss", "Bitte einen Aufgabennamen eingeben.")
                return
            if due and not parse_date(due):
                messagebox.showwarning("Monatsabschluss", "Bitte ein gültiges Fälligkeitsdatum im Format YYYY-MM-DD eingeben.")
                return
            owner_label = owner_var.get()
            owner_key = user_labels.get(owner_label, "")
            owner_text = owner_label if owner_key else team
            payload = {
                "title": title,
                "owner": owner_text,
                "owner_user_key": owner_key,
                "due_date": due,
                "deadline_type": deadline_var.get(),
                "priority": priority_var.get(),
            }
            if is_new:
                new_task = {
                    "id": make_task_id(team, self.next_task_index(team)),
                    "team": team,
                    "required": True,
                    "status": STATUS_OPEN,
                    "attachments": [],
                    "comments": [],
                    "done_at": None,
                    "done_by": None,
                    **payload,
                }
                self.data.setdefault("tasks", []).append(new_task)
            else:
                real = self.find_task(task["id"])
                if real:
                    real.update(payload)
            self.save()
            win.destroy()
            self.render_team_detail(team)

        buttons = tk.Frame(form, bg=COLORS["bg"])
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(18, 0))
        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="left", padx=6)
        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="left", padx=6)

    def delete_task(self, task):
        real = self.find_task(task["id"])
        if not real:
            return
        msg = f"Aufgabe wirklich löschen?\n\n{real.get('title')}"
        if real.get("attachments"):
            msg += "\n\nDiese Aufgabe hat Anlagen. Die Dateien bleiben im Anlagenordner erhalten, die Referenz wird aus der Aufgabe entfernt."
        if not messagebox.askyesno("Aufgabe löschen", msg):
            return
        self.data["tasks"] = [t for t in self.data.get("tasks", []) if t.get("id") != real.get("id")]
        self.save()
        self.render_team_detail(real["team"])

    def clone_task_for_period(self, task, target_period, index):
        due = parse_date(task.get("due_date", ""))
        day = due.day if due else 10
        return {
            "id": make_task_id(task.get("team", "Team"), index),
            "team": task.get("team"),
            "title": task.get("title"),
            "owner": task.get("owner", task.get("team")),
            "owner_user_key": task.get("owner_user_key", ""),
            "due_date": due_date_for(target_period, day),
            "deadline_type": task.get("deadline_type", "keine"),
            "priority": task.get("priority", "normal"),
            "required": task.get("required", True),
            "status": STATUS_OPEN,
            "attachments": [],
            "comments": [],
            "done_at": None,
            "done_by": None,
        }

    def apply_current_tasks_to_all_months(self):
        if not self.can_edit():
            return
        if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus {period_label(self.period)} wird auf alle vorhandenen Monate übertragen.\n\nStatus, Anlagen, Kommentare und Erledigt-Infos werden in den Zielmonaten zurückgesetzt.\n\nFortfahren?"):
            return
        source_tasks = [t for t in self.tasks()]
        for target in list_periods():
            grouped_index = {}
            cloned = []
            for task in source_tasks:
                team = task.get("team", "Team")
                grouped_index[team] = grouped_index.get(team, 0) + 1
                cloned.append(self.clone_task_for_period(task, target, grouped_index[team]))
            data = load_period(target)
            data["tasks"] = cloned
            data["updated_from_period"] = self.period
            data["updated_at"] = datetime.now().isoformat(timespec="seconds")
            save_period(target, data)
        self.reload()
        messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben dieses Monats wurden allen vorhandenen Monaten zugewiesen.")
        if self.selected_team:
            self.render_team_detail(self.selected_team)
        else:
            self.render_dashboard()

    def show_attachments(self, task):
        win = tk.Toplevel(self.root)
        win.title(f"Anlagen - {task.get('title')}")
        win.configure(bg=COLORS["bg"])
        win.geometry("720x420")
        win.transient(self.root)
        task_id = task["id"]

        def refresh():
            for child in list_frame.winfo_children():
                child.destroy()
            real = self.find_task(task_id)
            if not real:
                return
            for idx, att in enumerate(real.get("attachments", [])):
                tk.Label(list_frame, text=att.get("name"), bg=COLORS["white"], fg=COLORS["text"], anchor="w").grid(row=idx, column=0, sticky="ew", padx=6, pady=3)
                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, pady=3)
                tk.Button(list_frame, text="Entfernen", command=lambda a=att: remove_attachment(a), bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, pady=3)

        def add_attachment():
            file_path = filedialog.askopenfilename(title="Anlage auswählen")
            if not file_path:
                return
            real = self.find_task(task_id)
            if not real:
                return
            dest_dir = ATTACH_DIR / self.period / real["team"] / real["id"]
            dest_dir.mkdir(parents=True, exist_ok=True)
            src = Path(file_path)
            dest = dest_dir / src.name
            counter = 1
            while dest.exists():
                dest = dest_dir / f"{src.stem}_{counter}{src.suffix}"
                counter += 1
            shutil.copy2(src, dest)
            real.setdefault("attachments", []).append({"name": dest.name, "path": str(dest), "original_path": str(src), "added_at": datetime.now().isoformat(timespec="seconds")})
            self.save()
            refresh()
            self.render_team_detail(real["team"])

        def remove_attachment(att):
            real = self.find_task(task_id)
            if real and messagebox.askyesno("Anlage entfernen", f"Anlage entfernen?\n\n{att.get('name')}"):
                real["attachments"] = [a for a in real.get("attachments", []) if a != att]
                self.save()
                refresh()
                self.render_team_detail(real["team"])

        tk.Label(win, text=task.get("title"), bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(14, 6))
        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")
        list_frame.pack(fill="both", expand=True, padx=16, pady=8)
        list_frame.grid_columnconfigure(0, weight=1)
        tk.Button(win, text="Anlage hinzufügen", command=add_attachment, bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(anchor="e", padx=16, pady=(0, 14))
        refresh()

    def open_attachment(self, path):
        if not path or not os.path.exists(path):
            messagebox.showwarning("Anlage", "Datei wurde nicht gefunden.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            messagebox.showerror("Anlage", str(exc))


def render(app):
    MonthlyCloseUI(app)
