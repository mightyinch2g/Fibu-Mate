# FiBu Mate - Abschlusskalender unified wrapper
# Version: 0.436-unified-menu-protocol
# Erstellt am: 2026-06-09
# Zweck: Monatsabschluss, Quartalsabschluss und Jahresabschluss in einem Tool-Modul bündeln.
# Änderung 2026-06-24: Fälligkeitsart x. Tag nach Abschluss-Stichtag; vorläufiger Abschlussbericht nur E4.
# Änderungen: Einzelaufgaben-PDFs deaktiviert; Zeitraum-Protokoll nur E3/E4; Fortschritt inkl. Unteraufgaben.

import sys
import types

APP_VERSION = "0.522-documentation-count-real-files"
MODULE_TITLE = "Abschlusskalender"

_EMBEDDED_SOURCES = {'monthly_close': '## FiBuMate_PATCH_MARKER: 20260609_PROTOCOL_ONLY_SUBTASK_PROGRESS\n'
                  '## FiBuMate_PATCH_MARKER: 20260609_v0436_ABSCHLUSSKALENDER_UNIFIED_WRAPPED\n'
                  '## FiBuMate_PATCH_MARKER: 20260609_v0436_DREI_MODULE_OHNE_ID_ZUWEISUNG\n'
                  '\n'
                  'import calendar\n'
                  'import json\n'
                  'import os\n'
                  'import shutil\n'
                  'import subprocess\n'
                  'import sys\n'
                  'import webbrowser\n'
                  'from datetime import date, datetime, timedelta\n'
                  'from pathlib import Path\n'
                  'from urllib.parse import quote\n'
                  'import tkinter as tk\n'
                  'from tkinter import filedialog, messagebox, ttk\n'
                  '\n'
                  'try:\n'
                  '    from . import compliance_common as cc\n'
                  'except Exception:\n'
                  '    try:\n'
                  '        import compliance_common as cc\n'
                  '    except Exception:\n'
                  '        cc = None\n'
                  '\n'
                  '# v0.434 Paket 1B: direkte, scharfe Modulschrift für Abschluss-/Stichtagsmodule.\n'
                  '# Der Bereichszoom aus Fibu_mate.py wird berücksichtigt, ohne Kopf-/Fußleisten nachzuskalieren.\n'
                  'def zfont(app, size=12, weight=None, underline=False, scale=1.0):\n'
                  '    try:\n'
                  '        scope_zoom = float(getattr(app, "current_scope_zoom", 1.0) or 1.0)\n'
                  '        final = max(9, int(round(float(size) * 1.28 * scope_zoom * float(scale))))\n'
                  '    except Exception:\n'
                  '        final = int(size)\n'
                  '    styles = []\n'
                  '    if weight:\n'
                  '        styles.append(weight)\n'
                  '    if underline:\n'
                  '        styles.append("underline")\n'
                  '    return tuple(["Segoe UI", final] + styles)\n'
                  '\n'
                  '\n'
                  'def apply_readable_fonts(widget, app, base_size=12):\n'
                  '    """Setzt direkte Tk-Fonts für neu erzeugte Modulwidgets nach."""\n'
                  '    try:\n'
                  '        try:\n'
                  '            cls = widget.winfo_class().lower()\n'
                  '        except Exception:\n'
                  '            cls = ""\n'
                  '        if cls in ("label", "button", "entry", "text", "listbox", "checkbutton", "radiobutton", '
                  '"menubutton"):\n'
                  '            try:\n'
                  '                current = str(widget.cget("font") or "")\n'
                  '                widget.configure(font=zfont(app, base_size, "bold" if "bold" in current.lower() '
                  'else None))\n'
                  '            except Exception:\n'
                  '                pass\n'
                  '        for child in widget.winfo_children():\n'
                  '            apply_readable_fonts(child, app, base_size)\n'
                  '    except Exception:\n'
                  '        pass\n'
                  'STATUS_OPEN = "Offen"\n'
                  'STATUS_IN_PROGRESS = "In Bearbeitung"\n'
                  'STATUS_DONE = "Erledigt"\n'
                  'STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]\n'
                  'TEAMS = ["Hauptbuch", "Zentralregulierung", "Debitoren", "Treasury"]\n'
                  'TEAM_ALIASES = {"Kreditoren": "Zentralregulierung", "Controlling": "Treasury"}\n'
                  'DEADLINE_TYPES = ["intern", "gesetzlich"]\n'
                  'PRIORITIES = ["normal", "hoch", "kritisch"]\n'
                  '\n'
                  'DUE_CUTOFF = "closing_cutoff"\n'
                  'DUE_WORKDAY_NEXT = "workday_next_month"\n'
                  'DUE_DAY_NEXT_MONTH = "day_next_month"\n'
                  'DUE_DAY_CAL_MONTH = "day_calendar_month"\n'
                  'DUE_DAY_AFTER_CUTOFF = "day_after_cutoff"\n'
                  'DUE_FIXED = "fixed_date"\n'
                  '# Legacy values for migration only\n'
                  'DUE_WORKDAY_MONTH = "workday_current_month"\n'
                  'DUE_END_CURRENT = "end_current_month"\n'
                  'DUE_LABEL_TO_VALUE = {\n'
                  '    "Abschluss-Stichtag": DUE_CUTOFF,\n'
                  '    "x. Werktag des Folgemonats": DUE_WORKDAY_NEXT,\n'
                  '    "x. Tag des Folgemonats": DUE_DAY_NEXT_MONTH,\n'
                  '    "x. Tag des Kalendermonats": DUE_DAY_CAL_MONTH,\n'
                  '    "x. Tag nach Abschluss-Stichtag": DUE_DAY_AFTER_CUTOFF,\n'
                  '    "Konkretes Datum": DUE_FIXED,\n'
                  '}\n'
                  'DUE_VALUE_TO_LABEL = {v: k for k, v in DUE_LABEL_TO_VALUE.items()}\n'
                  'WARN_YELLOW_DAYS = 10\n'
                  'WARN_ORANGE_DAYS = 5\n'
                  'MIN_PERIOD = "2026-05"\n'
                  'MIN_FISCAL_YEAR_PERIOD = "2025-2026"\n'
                  'FISCAL_YEAR_START_MONTH = 10\n'
                  '\n'
                  '\n'
                  'def fiscal_year_start_for_date(d=None):\n'
                  '    d = d or date.today()\n'
                  '    return d.year if d.month >= FISCAL_YEAR_START_MONTH else d.year - 1\n'
                  '\n'
                  '\n'
                  'def fiscal_year_end_month_key(start_year):\n'
                  '    return f"{start_year + 1:04d}-09"\n'
                  '\n'
                  '\n'
                  'def august_month_key(start_year):\n'
                  '    return f"{start_year + 1:04d}-08"\n'
                  '\n'
                  '\n'
                  'def august_cutoff_reached(start_year, today=None):\n'
                  '    today = today or date.today()\n'
                  '    august = august_month_key(start_year)\n'
                  '    cutoff = None\n'
                  '    try:\n'
                  "        synced = cc.get_deadline_cutoff('monthly', august) if cc is not None and hasattr(cc, "
                  "'get_deadline_cutoff') else ''\n"
                  '        cutoff = parse_date(synced)\n'
                  '    except Exception:\n'
                  '        cutoff = None\n'
                  '    if not cutoff:\n'
                  '        cutoff = first_business_day_after_period_end(august)\n'
                  '    return today >= cutoff\n'
                  '\n'
                  '\n'
                  'def max_period_key(today=None):\n'
                  '    today = today or date.today()\n'
                  '    fy_start = fiscal_year_start_for_date(today)\n'
                  '    if august_cutoff_reached(fy_start, today):\n'
                  '        return fiscal_year_end_month_key(fy_start + 1)\n'
                  '    return fiscal_year_end_month_key(fy_start)\n'
                  '\n'
                  '\n'
                  'def bounded_current_period_key(today=None):\n'
                  '    today = today or date.today()\n'
                  '    current = month_key(today)\n'
                  '    if current < MIN_PERIOD:\n'
                  '        return MIN_PERIOD\n'
                  '    max_key = max_period_key(today)\n'
                  '    return min(current, max_key)\n'
                  '\n'
                  '\n'
                  'def period_allowed(period, today=None):\n'
                  '    return MIN_PERIOD <= period <= max_period_key(today)\n'
                  '\n'
                  '\n'
                  'def iter_allowed_periods(today=None):\n'
                  '    periods = []\n'
                  '    cur = MIN_PERIOD\n'
                  '    max_key = max_period_key(today)\n'
                  '    while cur <= max_key:\n'
                  '        periods.append(cur)\n'
                  '        cur = add_month(cur, 1)\n'
                  '    return periods\n'
                  'COLORS = {\n'
                  '    "bg": "#E8EEF5", "header": "#D3DEE9", "blue": "#004B93", "red": "#E30613",\n'
                  '    "orange": "#F59E0B", "yellow": "#FACC15", "green": "#16A34A", "dark_green": "#047857",\n'
                  '    "text": "#182431", "text2": "#445364", "line": "#91A3B5", "white": "#FFFFFF",\n'
                  '    "edit_bg": "#FEF3C7", "subtask_bg": "#EAF4FF"  # v0.436 unified: Unteraufgaben-Tabellenfarbe '
                  'ein klein wenig blauer.\n'
                  '}\n'
                  '\n'
                  '\n'
                  'def _base_dir() -> Path:\n'
                  '    here = Path(__file__).resolve()\n'
                  '    if here.parent.name.lower() == "tools":\n'
                  '        return here.parent.parent / "Closing" / "MonthlyClose"\n'
                  '    return here.parent / "bin" / "Closing" / "MonthlyClose"\n'
                  '\n'
                  '\n'
                  'BASE_DIR = _base_dir()\n'
                  'PERIOD_DIR = BASE_DIR / "periods"\n'
                  'ATTACH_DIR = BASE_DIR / "attachments"\n'
                  'CONFIG_PATH = BASE_DIR / "monthly_close_config.json"\n'
                  'CATALOG_PATH = BASE_DIR / "monthly_close_task_catalog.json"\n'
                  'CLOSING_SCOPE = "M"\n'
                  'INITIAL_TASK_IDS = {\n'
                  "    ('Hauptbuch', 'Bankabstimmung durchführen'): 'QM001',\n"
                  "    ('Hauptbuch', 'Rückstellungen prüfen'): 'QM002',\n"
                  "    ('Hauptbuch', 'Abgrenzungen buchen'): 'QM003',\n"
                  "    ('Hauptbuch', 'Sachkonten prüfen'): 'QM004',\n"
                  "    ('Zentralregulierung', 'Offene Posten prüfen'): 'QM005',\n"
                  "    ('Zentralregulierung', 'Lieferantenabstimmung durchführen'): 'QM006',\n"
                  "    ('Zentralregulierung', 'Rechnungsabgrenzung prüfen'): 'QM007',\n"
                  "    ('Zentralregulierung', 'Zahlungsläufe kontrollieren'): 'QM008',\n"
                  "    ('Debitoren', 'Offene Posten prüfen'): 'QM009',\n"
                  "    ('Debitoren', 'Mahnstatus prüfen'): 'QM010',\n"
                  "    ('Debitoren', 'Erlösabgrenzung prüfen'): 'QM011',\n"
                  "    ('Debitoren', 'Kundensalden abstimmen'): 'QM012',\n"
                  "    ('Treasury', 'Kostenstellen prüfen'): 'QM013',\n"
                  "    ('Treasury', 'Reporting vorbereiten'): 'QM014',\n"
                  "    ('Treasury', 'Konzernmeldung vorbereiten'): 'QM015',\n"
                  "    ('Treasury', 'Abweichungsanalyse erstellen'): 'QM016',\n"
                  '}\n'
                  '\n'
                  'def month_key(d=None):\n'
                  '    d = d or date.today()\n'
                  '    return f"{d.year:04d}-{d.month:02d}"\n'
                  '\n'
                  'def current_period_key():\n'
                  '    return bounded_current_period_key()\n'
                  '\n'
                  '\n'
                  'def add_month(key, delta):\n'
                  '    year, month = map(int, key.split("-"))\n'
                  '    month += delta\n'
                  '    while month < 1:\n'
                  '        month += 12; year -= 1\n'
                  '    while month > 12:\n'
                  '        month -= 12; year += 1\n'
                  '    return f"{year:04d}-{month:02d}"\n'
                  '\n'
                  'def add_period(key, delta):\n'
                  '    return add_month(key, delta)\n'
                  '\n'
                  'def period_label(key):\n'
                  '    names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", '
                  '"Oktober", "November", "Dezember"]\n'
                  '    y, m = map(int, key.split("-"))\n'
                  '    return f"{names[m - 1]} {y}"\n'
                  '\n'
                  '\n'
                  '\n'
                  'def parse_date(value):\n'
                  '    value = str(value or "").strip()\n'
                  '    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):\n'
                  '        try:\n'
                  '            return datetime.strptime(value, fmt).date()\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '    return None\n'
                  '\n'
                  '\n'
                  'def format_date_de(value):\n'
                  '    d = value if isinstance(value, date) else parse_date(value)\n'
                  '    return d.strftime("%d.%m.%Y") if d else ""\n'
                  '\n'
                  '\n'
                  '\n'
                  'def format_datetime_de(value):\n'
                  '    if not value:\n'
                  '        return ""\n'
                  '    try:\n'
                  '        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y %H:%M")\n'
                  '    except Exception:\n'
                  '        d = parse_date(value)\n'
                  '        return d.strftime("%d.%m.%Y") if d else str(value)\n'
                  '\n'
                  'def easter_sunday(year):\n'
                  '    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4\n'
                  '    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30\n'
                  '    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7\n'
                  '    m = (a + 11 * h + 22 * l) // 451\n'
                  '    month = (h + l - 7 * m + 114) // 31\n'
                  '    day = ((h + l - 7 * m + 114) % 31) + 1\n'
                  '    return date(year, month, day)\n'
                  '\n'
                  '\n'
                  'def bw_holidays(year):\n'
                  '    easter = easter_sunday(year)\n'
                  '    return {\n'
                  '        date(year, 1, 1), date(year, 1, 6), easter - timedelta(days=2), easter + '
                  'timedelta(days=1),\n'
                  '        date(year, 5, 1), easter + timedelta(days=39), easter + timedelta(days=50), easter + '
                  'timedelta(days=60),\n'
                  '        date(year, 10, 3), date(year, 11, 1), date(year, 12, 25), date(year, 12, 26)\n'
                  '    }\n'
                  '\n'
                  '\n'
                  'def is_business_day(d):\n'
                  '    return d.weekday() < 5 and d not in bw_holidays(d.year)\n'
                  '\n'
                  '\n'
                  'def nth_business_day(year, month, n):\n'
                  '    n = max(1, int(n or 1))\n'
                  '    current = date(year, month, 1)\n'
                  '    count = 0\n'
                  '    while True:\n'
                  '        if is_business_day(current):\n'
                  '            count += 1\n'
                  '            if count == n:\n'
                  '                return current\n'
                  '        current += timedelta(days=1)\n'
                  '\n'
                  '\n'
                  'def normalize_team_name(team):\n'
                  '    return TEAM_ALIASES.get(team, team)\n'
                  '\n'
                  '\n'
                  'def normalize_team_members(data):\n'
                  '    members = data.setdefault("team_members", {})\n'
                  '    for old, new in TEAM_ALIASES.items():\n'
                  '        if old in members:\n'
                  '            if new not in members or not members.get(new):\n'
                  '                members[new] = members.get(old, [])\n'
                  '            members.pop(old, None)\n'
                  '    for team in TEAMS:\n'
                  '        value = members.get(team, [])\n'
                  '        if isinstance(value, str):\n'
                  '            value = [v.strip() for v in value.replace(";", "\\n").replace(",", "\\n").splitlines() '
                  'if v.strip()]\n'
                  '        members[team] = value\n'
                  '    return members\n'
                  '\n'
                  '\n'
                  'def set_team_members_text(data, team, text):\n'
                  '    normalize_team_members(data)[team] = [line.strip() for line in str(text or "").replace(";", '
                  '"\\n").replace(",", "\\n").splitlines() if line.strip()]\n'
                  '\n'
                  'def period_start(period):\n'
                  '    y, m = map(int, period.split("-"))\n'
                  '    return date(y, m, 1)\n'
                  '\n'
                  'def period_end(period):\n'
                  '    start = period_start(period)\n'
                  '    return date(start.year, start.month, calendar.monthrange(start.year, start.month)[1])\n'
                  '\n'
                  'def clamp_day_in_period(period, day):\n'
                  '    start = period_start(period)\n'
                  '    day = max(1, min(int(day or 1), calendar.monthrange(start.year, start.month)[1]))\n'
                  '    return date(start.year, start.month, day)\n'
                  '\n'
                  '\n'
                  'def first_business_day_after_period_end(period):\n'
                  '    cur = period_end(period) + timedelta(days=1)\n'
                  '    while not is_business_day(cur):\n'
                  '        cur += timedelta(days=1)\n'
                  '    return cur\n'
                  '\n'
                  'def default_due_date(period):\n'
                  '    return period_end(period).strftime("%Y-%m-%d")\n'
                  '\n'
                  'def resolve_due_date(task, data, period):\n'
                  '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                  '    if mode == DUE_CUTOFF:\n'
                  '        return normalize_cutoff(data, period)\n'
                  '    if mode == DUE_WORKDAY_NEXT:\n'
                  '        next_period = add_month(period, 1)\n'
                  '        y, m = map(int, next_period.split("-"))\n'
                  '        return nth_business_day(y, m, task.get("due_workday") or 1).strftime("%Y-%m-%d")\n'
                  '    if mode == DUE_DAY_NEXT_MONTH:\n'
                  "        if 'add_month' in globals():\n"
                  '            next_period = add_month(period, 1)\n'
                  "        elif 'add_quarter' in globals():\n"
                  '            next_period = add_quarter(period, 1)\n'
                  '        else:\n'
                  '            next_period = add_period(period, 1)\n'
                  '        return clamp_day_in_period(next_period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                  '    if mode == DUE_DAY_CAL_MONTH:\n'
                  '        return clamp_day_in_period(period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                  '    if mode == DUE_DAY_AFTER_CUTOFF:\n'
                  '        cutoff = parse_date(normalize_cutoff(data, period))\n'
                  '        days_after = max(0, int(task.get("due_day") or 0))\n'
                  '        return (cutoff + timedelta(days=days_after)).strftime("%Y-%m-%d") if cutoff else '
                  'normalize_cutoff(data, period)\n'
                  '    if mode == DUE_FIXED:\n'
                  '        due = parse_date(task.get("due_fixed_date") or task.get("due_date"))\n'
                  '        return due.strftime("%Y-%m-%d") if due else normalize_cutoff(data, period)\n'
                  '    return normalize_cutoff(data, period)\n'
                  '\n'
                  '\n'
                  '\n'
                  'def due_rule_text(task):\n'
                  '    mode = task.get("due_mode")\n'
                  '    if mode == DUE_CUTOFF:\n'
                  '        return "Abschluss-Stichtag"\n'
                  '    if mode == DUE_WORKDAY_NEXT:\n'
                  '        return f"{task.get(\'due_workday\') or 1}. Werktag Folgemonat"\n'
                  '    if mode == DUE_DAY_NEXT_MONTH:\n'
                  '        return f"{task.get(\'due_day\') or 1}. Tag Folgemonat"\n'
                  '    if mode == DUE_DAY_CAL_MONTH:\n'
                  '        return f"{task.get(\'due_day\') or 1}. Tag Kalendermonat"\n'
                  '    if mode == DUE_FIXED:\n'
                  '        return "Konkretes Datum"\n'
                  '    return ""\n'
                  '\n'
                  '\n'
                  'def due_display(task):\n'
                  '    rule = due_rule_text(task)\n'
                  '    return f"{format_date_de(task.get(\'due_date\', \'\'))}\\n{rule}" if rule else '
                  'format_date_de(task.get("due_date", ""))\n'
                  '\n'
                  '\n'
                  'def make_task_id(team, index):\n'
                  "    safe = str(team).lower().replace(' ', '_').replace('/', '_')\n"
                  "    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in safe).strip('_') or 'task'\n"
                  '    return f"{safe}_{int(index or 1):02d}"\n'
                  '\n'
                  'def ensure_storage():\n'
                  '    BASE_DIR.mkdir(parents=True, exist_ok=True)\n'
                  '    PERIOD_DIR.mkdir(parents=True, exist_ok=True)\n'
                  '    ATTACH_DIR.mkdir(parents=True, exist_ok=True)\n'
                  '    if not CONFIG_PATH.exists():\n'
                  '        CONFIG_PATH.write_text(json.dumps({"teams": TEAMS, "warning_days": {"yellow": '
                  'WARN_YELLOW_DAYS, "orange": WARN_ORANGE_DAYS}}, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                  '    if not CATALOG_PATH.exists():\n'
                  '        CATALOG_PATH.write_text(json.dumps({"tasks": []}, ensure_ascii=False, indent=2), '
                  'encoding="utf-8")\n'
                  '\n'
                  '\n'
                  'def period_path(period):\n'
                  '    return PERIOD_DIR / f"{period}.json"\n'
                  '\n'
                  '\n'
                  '\n'
                  'def deadline_cutoff_date(period):\n'
                  '    try:\n'
                  "        if cc is not None and hasattr(cc, 'get_deadline_cutoff'):\n"
                  "            return cc.get_deadline_cutoff('monthly', period)\n"
                  '    except Exception:\n'
                  '        pass\n'
                  "    return ''\n"
                  '\n'
                  '\n'
                  'def default_cutoff_date(period):\n'
                  '    synced = deadline_cutoff_date(period)\n'
                  '    if synced:\n'
                  '        return synced\n'
                  '    return first_business_day_after_period_end(period).strftime("%Y-%m-%d")\n'
                  '\n'
                  '\n'
                  'def normalize_cutoff(data, period):\n'
                  '    synced = deadline_cutoff_date(period)\n'
                  '    cutoff = parse_date(synced) if synced else parse_date(data.get("closing_cutoff_date", ""))\n'
                  '    if not cutoff:\n'
                  '        cutoff = parse_date(default_cutoff_date(period))\n'
                  '    data["closing_cutoff_date"] = cutoff.strftime("%Y-%m-%d")\n'
                  '    return data["closing_cutoff_date"]\n'
                  '\n'
                  '\n'
                  'def all_subtasks_done(task):\n'
                  '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                  '    return bool(subtasks) and all(s.get("status") == STATUS_DONE for s in subtasks)\n'
                  '\n'
                  '\n'
                  'def sync_parent_status_from_subtasks(task):\n'
                  '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                  '    if subtasks:\n'
                  '        if all(s.get("status") == STATUS_DONE for s in subtasks):\n'
                  '            task["status"] = STATUS_DONE\n'
                  '            task.setdefault("done_at", datetime.now().isoformat(timespec="seconds"))\n'
                  '        elif task.get("status") == STATUS_DONE:\n'
                  '            task["status"] = STATUS_OPEN\n'
                  '            task["done_at"] = None\n'
                  '            task["done_by"] = None\n'
                  '\n'
                  '\n'
                  'def migrate_due_fields(task, data, period):\n'
                  '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                  '    if mode == DUE_WORKDAY_NEXT:\n'
                  '        task["due_mode"] = DUE_WORKDAY_NEXT\n'
                  '    elif mode in (DUE_FIXED,):\n'
                  '        task["due_mode"] = DUE_FIXED\n'
                  '    elif mode in (DUE_WORKDAY_MONTH, DUE_END_CURRENT):\n'
                  '        task["due_mode"] = DUE_CUTOFF\n'
                  '    elif mode not in (DUE_CUTOFF, DUE_WORKDAY_NEXT, DUE_DAY_NEXT_MONTH, DUE_DAY_CAL_MONTH, '
                  'DUE_DAY_AFTER_CUTOFF, DUE_FIXED):\n'
                  '        task["due_mode"] = DUE_CUTOFF\n'
                  '    if task.get("due_mode") in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF):\n'
                  '        task["due_day"] = int(task.get("due_day") or task.get("due_workday") or 1)\n'
                  '\n'
                  '\n'
                  'def normalize_task(task, data, period):\n'
                  '    task["team"] = normalize_team_name(task.get("team"))\n'
                  '    task.pop("task_uid", None)  # v0.436: Aufgaben-ID-Zuweisung vollständig entfernt.\n'
                  '    task.setdefault("owner_user_key", "")\n'
                  '    task.setdefault("attachments", [])\n'
                  '    task.setdefault("comments", [])\n'
                  '    task.setdefault("subtasks", [])\n'
                  '    task.setdefault("status", STATUS_OPEN)\n'
                  '    task.setdefault("deadline_type", "intern")\n'
                  '    task.setdefault("priority", "normal")\n'
                  '    task.setdefault("due_day", None)\n'
                  '    task.setdefault("due_workday", None)\n'
                  '    task.setdefault("recurring", False)\n'
                  '    task.setdefault("catalog_id", "")\n'
                  '    task.setdefault("booking_circle", "IDE")\n'
                  '    if task["deadline_type"] not in DEADLINE_TYPES:\n'
                  '        task["deadline_type"] = "intern"\n'
                  '    migrate_due_fields(task, data, period)\n'
                  '    task["due_date"] = resolve_due_date(task, data, period)\n'
                  '    for idx, sub in enumerate(task.get("subtasks", []), start=1):\n'
                  '        sub.setdefault("id", f"sub_{idx:02d}")\n'
                  '        sub.setdefault("title", "")\n'
                  '        sub.setdefault("status", STATUS_OPEN)\n'
                  '        sub.pop("task_uid", None)  # v0.436: Unteraufgaben-ID-Zuweisung entfernt.\n'
                  '    sync_parent_status_from_subtasks(task)\n'
                  '    return task\n'
                  '\n'
                  '\n'
                  'def load_catalog():\n'
                  '    ensure_storage()\n'
                  '    try:\n'
                  '        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))\n'
                  '    except Exception:\n'
                  '        data = {"tasks": []}\n'
                  '    data.setdefault("tasks", [])\n'
                  '    try:\n'
                  "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437') and "
                  "cc.sync_task_catalog_uids_v0437('monthly', data):\n"
                  '            save_catalog(data)\n'
                  '    except Exception:\n'
                  '        pass\n'
                  '    return data\n'
                  '\n'
                  '\n'
                  'def save_catalog(data):\n'
                  '    data.setdefault("tasks", [])\n'
                  '    try:\n'
                  "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437'):\n"
                  "            cc.sync_task_catalog_uids_v0437('monthly', data)\n"
                  '    except Exception:\n'
                  '        pass\n'
                  '    CATALOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                  '\n'
                  '\n'
                  'def default_tasks(period):\n'
                  '    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}\n'
                  '    examples = {\n'
                  '        "Hauptbuch": ["Bankabstimmung durchführen", "Rückstellungen prüfen", "Abgrenzungen buchen", '
                  '"Sachkonten prüfen"],\n'
                  '        "Zentralregulierung": ["Offene Posten prüfen", "Lieferantenabstimmung durchführen", '
                  '"Rechnungsabgrenzung prüfen", "Zahlungsläufe kontrollieren"],\n'
                  '        "Debitoren": ["Offene Posten prüfen", "Mahnstatus prüfen", "Erlösabgrenzung prüfen", '
                  '"Kundensalden abstimmen"],\n'
                  '        "Treasury": ["Kostenstellen prüfen", "Reporting vorbereiten", "Konzernmeldung vorbereiten", '
                  '"Abweichungsanalyse erstellen"],\n'
                  '    }\n'
                  '    tasks = []\n'
                  '    for team in TEAMS:\n'
                  '        names = examples[team]\n'
                  '        for idx, title in enumerate(names, 1):\n'
                  '            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]\n'
                  '            task = {\n'
                  '                "id": make_task_id(team, idx), "team": team, "title": title, "owner": team, '
                  '"owner_user_key": "",\n'
                  '                "due_mode": DUE_CUTOFF, "due_day": None, "due_workday": 1,\n'
                  '                "deadline_type": "gesetzlich" if is_legal else "intern", "priority": "kritisch" if '
                  'is_legal else "normal",\n'
                  '                "required": True, "recurring": False, "catalog_id": "", "status": STATUS_OPEN,\n'
                  '                "attachments": [], "comments": [], "subtasks": [], "done_at": None, "done_by": '
                  'None,\n'
                  '            }\n'
                  '            task["due_date"] = resolve_due_date(task, data_stub, period)\n'
                  '            tasks.append(task)\n'
                  '    return tasks\n'
                  '\n'
                  '\n'
                  'def load_period(period):\n'
                  '    ensure_storage()\n'
                  '    path = period_path(period)\n'
                  '    if not path.exists():\n'
                  '        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), '
                  '"closing_cutoff_date": default_cutoff_date(period), "team_members": {team: [] for team in TEAMS}, '
                  '"tasks": default_tasks(period)}\n'
                  '        save_period(period, data)\n'
                  '        return data\n'
                  '    data = json.loads(path.read_text(encoding="utf-8"))\n'
                  '    data.setdefault("tasks", [])\n'
                  '    normalize_team_members(data)\n'
                  '    old_cutoff = data.get("closing_cutoff_date", "")\n'
                  '    normalize_cutoff(data, period)\n'
                  '    changed = old_cutoff != data.get("closing_cutoff_date", "")\n'
                  '    for task in data["tasks"]:\n'
                  '        old_team = task.get("team")\n'
                  '        normalize_task(task, data, period)\n'
                  '        changed = changed or old_team != task.get("team")\n'
                  '    try:\n'
                  "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                  "            changed = cc.ensure_task_identity_for_period_v0437('monthly', period, data) or changed\n"
                  '    except Exception:\n'
                  '        pass\n'
                  '    if changed:\n'
                  '        save_period(period, data)\n'
                  '    return data\n'
                  '\n'
                  '\n'
                  'def save_period(period, data):\n'
                  '    ensure_storage()\n'
                  '    normalize_team_members(data)\n'
                  '    normalize_cutoff(data, period)\n'
                  '    for task in data.get("tasks", []):\n'
                  '        normalize_task(task, data, period)\n'
                  '    try:\n'
                  "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                  "            cc.ensure_task_identity_for_period_v0437('monthly', period, data)\n"
                  '    except Exception:\n'
                  '        pass\n'
                  '    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), '
                  'encoding="utf-8")\n'
                  '\n'
                  '\n'
                  'def catalog_entry_to_task(entry, period, index):\n'
                  '    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}\n'
                  '    task = {\n'
                  '        "id": make_task_id(entry.get("team", "Team"), index), "team": '
                  'normalize_team_name(entry.get("team")), "title": entry.get("title"),\n'
                  '        "owner": entry.get("owner", entry.get("team")), "owner_user_key": '
                  'entry.get("owner_user_key", ""),\n'
                  '        "due_mode": entry.get("due_mode", DUE_CUTOFF), "due_day": entry.get("due_day"), '
                  '"due_workday": entry.get("due_workday"), "due_fixed_date": entry.get("due_fixed_date", '
                  'entry.get("due_date", "")),\n'
                  '        "deadline_type": entry.get("deadline_type", "intern"), "priority": entry.get("priority", '
                  '"normal"),\n'
                  '        "required": entry.get("required", True), "recurring": True, "catalog_id": '
                  'entry.get("catalog_id", ""),\n'
                  '        "status": STATUS_OPEN, "attachments": [], "comments": [], "subtasks": [], "done_at": None, '
                  '"done_by": None,\n'
                  '    }\n'
                  '    task["due_date"] = resolve_due_date(task, data_stub, period)\n'
                  '    return task\n'
                  '\n'
                  '\n'
                  'def apply_catalog_to_period(period):\n'
                  '    data = load_period(period)\n'
                  '    catalog = load_catalog()\n'
                  '    changed = False\n'
                  '    tasks = data.setdefault("tasks", [])\n'
                  '    for entry in catalog.get("tasks", []):\n'
                  '        if not entry.get("recurring", True):\n'
                  '            continue\n'
                  '        start_period = entry.get("start_period", current_period_key())\n'
                  '        if period <= start_period:\n'
                  '            continue\n'
                  '        catalog_id = entry.get("catalog_id")\n'
                  '        existing = next((t for t in tasks if t.get("catalog_id") == catalog_id and not '
                  't.get("deleted")), None)\n'
                  '        if existing:\n'
                  '            keep = {"status": existing.get("status", STATUS_OPEN), "attachments": '
                  'existing.get("attachments", []), "comments": existing.get("comments", []), "subtasks": '
                  'existing.get("subtasks", []), "done_at": existing.get("done_at"), "done_by": '
                  'existing.get("done_by")}\n'
                  '            existing.update(catalog_entry_to_task(entry, period, len([t for t in tasks if '
                  't.get("team") == entry.get("team")]) + 1))\n'
                  '            existing.update(keep)\n'
                  '            changed = True\n'
                  '        else:\n'
                  '            idx = len([t for t in tasks if t.get("team") == entry.get("team")]) + 1\n'
                  '            tasks.append(catalog_entry_to_task(entry, period, idx))\n'
                  '            changed = True\n'
                  '    if changed:\n'
                  '        save_period(period, data)\n'
                  '    return data\n'
                  '\n'
                  'def cleanup_old_periods():\n'
                  '    ensure_storage()\n'
                  '    # v0.432: Alte/vorzeitige Periodendateien werden nicht gelöscht, aber nicht mehr angezeigt oder '
                  'automatisch angelegt.\n'
                  '    return\n'
                  '\n'
                  '\n'
                  'def ensure_period_window():\n'
                  '    ensure_storage(); cleanup_old_periods()\n'
                  '    for p in iter_allowed_periods():\n'
                  '        load_period(p)\n'
                  '        apply_catalog_to_period(p)\n'
                  '\n'
                  '\n'
                  'def list_periods():\n'
                  '    ensure_period_window()\n'
                  '    allowed = set(iter_allowed_periods())\n'
                  '    return sorted(p.stem for p in PERIOD_DIR.glob("*.json") if p.stem in allowed)\n'
                  '\n'
                  '\n'
                  'def warning_level(task, today=None):\n'
                  '    if task.get("status") == STATUS_DONE or task.get("deadline_type") == "keine":\n'
                  '        return "done" if task.get("status") == STATUS_DONE else "none"\n'
                  '    due = parse_date(task.get("due_date", ""))\n'
                  '    if not due:\n'
                  '        return "none"\n'
                  '    today = today or date.today()\n'
                  '    days = (due - today).days\n'
                  '    if days < 0: return "overdue"\n'
                  '    if days == 0: return "today"\n'
                  '    if days <= WARN_ORANGE_DAYS: return "orange"\n'
                  '    if days <= WARN_YELLOW_DAYS: return "yellow"\n'
                  '    return "none"\n'
                  '\n'
                  '\n'
                  'def progress_color(percent):\n'
                  '    if percent >= 100: return COLORS["dark_green"]\n'
                  '    if percent >= 75: return COLORS["green"]\n'
                  '    if percent >= 50: return COLORS["yellow"]\n'
                  '    if percent >= 25: return COLORS["orange"]\n'
                  '    return COLORS["red"]\n'
                  '\n'
                  '\n'
                  'def calc_stats(tasks):\n'
                  '    """Fortschritt inkl. Unteraufgaben berechnen.\n'
                  '    Hauptaufgaben und nicht gelöschte Unteraufgaben zählen als Fortschrittseinheiten.\n'
                  '    """\n'
                  '    visible = [t for t in tasks if not t.get("deleted")]\n'
                  '    units = []\n'
                  '    for task in visible:\n'
                  '        units.append(task)\n'
                  '        for sub in task.get("subtasks", []) or []:\n'
                  '            if not sub.get("deleted"):\n'
                  '                units.append(sub)\n'
                  '    total = len(units)\n'
                  '    done = sum(1 for item in units if item.get("status") == STATUS_DONE)\n'
                  '    in_progress = sum(1 for item in units if item.get("status") == STATUS_IN_PROGRESS)\n'
                  '    open_count = total - done - in_progress\n'
                  '    overdue = sum(1 for t in visible if warning_level(t) == "overdue")\n'
                  '    critical = sum(1 for t in visible if warning_level(t) in ("overdue", "today", "orange") or '
                  '(t.get("priority") == "kritisch" and t.get("deadline_type") != "keine"))\n'
                  '    sub_total = max(0, total - len(visible))\n'
                  '    sub_done = sum(1 for task in visible for sub in (task.get("subtasks", []) or []) if not '
                  'sub.get("deleted") and sub.get("status") == STATUS_DONE)\n'
                  '    percent = int(round((done / total) * 100)) if total else 0\n'
                  '    return {"total": total, "done": done, "in_progress": in_progress, "open": open_count, '
                  '"overdue": overdue, "critical": critical, "percent": percent, "task_total": len(visible), '
                  '"subtask_total": sub_total, "subtask_done": sub_done}\n'
                  '\n'
                  '\n'
                  'class MonthlyCloseUI:\n'
                  '    def __init__(self, app):\n'
                  '        self.app = app\n'
                  '        self.root = app.root\n'
                  '        self.canvas = app.canvas\n'
                  '        ensure_period_window()\n'
                  '        self.period = current_period_key()\n'
                  '        self.data = apply_catalog_to_period(self.period)\n'
                  '        self.selected_team = None\n'
                  '        self.expanded_tasks = set()\n'
                  '        self.edit_mode = False\n'
                  '        self.tooltip = None\n'
                  '        self._live_period_mtime = 0\n'
                  '        self._live_period_refresh_started = False\n'
                  '        self._live_period_popup_open = False\n'
                  '        self._live_period_notice_shown = False\n'
                  '        self._live_task_widgets = {}\n'
                  '        self._live_subtask_widgets = {}\n'
                  '        self.frame = tk.Frame(self.root, bg=COLORS["bg"])\n'
                  '        self.app.widget_items.append(self.frame)\n'
                  '        self.app.module_escape_handler = self.handle_escape\n'
                  '        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", '
                  'width=self.canvas.winfo_width(), height=max(400, self.canvas.winfo_height() - 172))\n'
                  '        self.strip_task_ids_all_periods()\n'
                  '        self.render_dashboard()\n'
                  '        apply_readable_fonts(self.frame, self.app, 12)\n'
                  '        self._live_period_mtime = self._period_file_mtime()\n'
                  '        self.bind_module_ctrl_mousewheel_guard()\n'
                  '        self._start_live_period_refresh()\n'
                  '\n'
                  '\n'
                  '\n'
                  '    def _period_file_mtime(self):\n'
                  '        try:\n'
                  '            path = period_path(self.period)\n'
                  '            return path.stat().st_mtime if path.exists() else 0\n'
                  '        except Exception:\n'
                  '            return 0\n'
                  '\n'
                  '    def _start_live_period_refresh(self):\n'
                  '        if getattr(self, "_live_period_refresh_started", False):\n'
                  '            return\n'
                  '        self._live_period_refresh_started = True\n'
                  '        try:\n'
                  '            self.root.after(3000, self._check_live_period_refresh)\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _task_live_key(self, task):\n'
                  '        try:\n'
                  '            return self.task_match_key(task)\n'
                  '        except Exception:\n'
                  '            return "|".join([str(task.get("team", "")), str(task.get("catalog_id", "")), '
                  'str(task.get("title", ""))])\n'
                  '\n'
                  '    def _subtask_live_key(self, task, subtask):\n'
                  '        return self._task_live_key(task) + "::sub::" + str(subtask.get("catalog_id") or '
                  'subtask.get("title") or subtask.get("id") or "")\n'
                  '\n'
                  '    def _visible_tasks_from_data(self, data, team=None):\n'
                  '        tasks = [t for t in data.get("tasks", []) if not t.get("deleted")]\n'
                  '        if team:\n'
                  '            tasks = [t for t in tasks if t.get("team") == team]\n'
                  '        return sorted(tasks, key=lambda t: str(t.get("title", "")).casefold())\n'
                  '\n'
                  '    def _live_structure_signature(self, data):\n'
                  '        sig = []\n'
                  '        for t in self._visible_tasks_from_data(data, None):\n'
                  '            subs = tuple((self._subtask_live_key(t, s), s.get("title", ""), s.get("owner", ""), '
                  's.get("owner_user_key", "")) for s in sorted([x for x in t.get("subtasks", []) if not '
                  'x.get("deleted")], key=lambda x: str(x.get("title", "")).casefold()))\n'
                  '            sig.append((self._task_live_key(t), t.get("team", ""), t.get("title", ""), '
                  't.get("owner", ""), t.get("owner_user_key", ""), t.get("due_date", ""), t.get("due_mode", ""), '
                  't.get("deadline_type", ""), t.get("priority", ""), bool(t.get("recurring")), subs))\n'
                  '        return tuple(sig)\n'
                  '\n'
                  '    def _live_status_signature(self, data):\n'
                  '        sig = []\n'
                  '        for t in self._visible_tasks_from_data(data, None):\n'
                  '            subs = tuple((self._subtask_live_key(t, s), s.get("status", STATUS_OPEN), '
                  's.get("done_at"), s.get("done_by"), len(s.get("attachments", [])), len(s.get("comments", []))) for '
                  's in sorted([x for x in t.get("subtasks", []) if not x.get("deleted")], key=lambda x: '
                  'str(x.get("title", "")).casefold()))\n'
                  '            sig.append((self._task_live_key(t), t.get("status", STATUS_OPEN), t.get("done_at"), '
                  't.get("done_by"), len(t.get("attachments", [])), len(t.get("comments", [])), subs))\n'
                  '        return tuple(sig)\n'
                  '\n'
                  '    def _widgets_recursive(self, widget):\n'
                  '        yield widget\n'
                  '        try:\n'
                  '            children = widget.winfo_children()\n'
                  '        except Exception:\n'
                  '            children = []\n'
                  '        for child in children:\n'
                  '            yield from self._widgets_recursive(child)\n'
                  '\n'
                  '    def _safe_config(self, widget, **kwargs):\n'
                  '        try:\n'
                  '            if widget is not None:\n'
                  '                widget.configure(**kwargs)\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _set_row_background(self, widgets, bg):\n'
                  '        for widget in widgets or []:\n'
                  '            for item in self._widgets_recursive(widget):\n'
                  '                try:\n'
                  '                    cls = item.winfo_class()\n'
                  '                except Exception:\n'
                  '                    cls = ""\n'
                  '                if cls in ("Frame", "Label", "Button", "Menubutton"):\n'
                  '                    self._safe_config(item, bg=bg)\n'
                  '\n'
                  '    def _register_live_task_widgets(self, table, row_idx, task, done_button, status_var, '
                  'status_menu):\n'
                  '        try:\n'
                  '            self._live_task_widgets[self._task_live_key(task)] = {"row_widgets": '
                  'list(table.grid_slaves(row=row_idx)), "done_button": done_button, "status_var": status_var, '
                  '"status_menu": status_menu}\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _register_live_subtask_widgets(self, table, row_idx, task, subtask, done_button):\n'
                  '        try:\n'
                  '            self._live_subtask_widgets[self._subtask_live_key(task, subtask)] = {"row_widgets": '
                  'list(table.grid_slaves(row=row_idx)), "done_button": done_button}\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _refresh_option_menu_commands(self, menu, status_var, task):\n'
                  '        try:\n'
                  '            menu_widget = menu["menu"]\n'
                  '            menu_widget.delete(0, "end")\n'
                  '            for status in STATUSES:\n'
                  '                menu_widget.add_command(label=status, command=tk._setit(status_var, status, lambda '
                  'value, t=task: self.set_status(t, value)))\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _apply_button_status(self, button, item, command, can_complete=True, subtask=False):\n'
                  '        try:\n'
                  '            status = item.get("status", STATUS_OPEN)\n'
                  '            bg = "#BBF7D0" if status == STATUS_DONE else (COLORS["subtask_bg"] if subtask else '
                  '("#FFF7ED" if warning_level(item) in ("overdue", "today", "orange") else COLORS["white"]))\n'
                  '            fg = COLORS["dark_green"] if status == STATUS_DONE else COLORS["text"]\n'
                  '            button.configure(text="✓" if status == STATUS_DONE else "□", bg=bg, fg=fg, '
                  'command=command, state="normal" if can_complete else "disabled")\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _apply_smooth_status_update(self, new_data):\n'
                  '        new_tasks = {self._task_live_key(t): t for t in self._visible_tasks_from_data(new_data, '
                  'self.selected_team)}\n'
                  '        self.data = new_data\n'
                  '        for key, task in new_tasks.items():\n'
                  '            entry = getattr(self, "_live_task_widgets", {}).get(key)\n'
                  '            if entry:\n'
                  '                bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if '
                  'warning_level(task) in ("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", '
                  '"IMS":"#FFF4CC", "SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), '
                  'COLORS["white"])\n'
                  '                self._set_row_background(entry.get("row_widgets"), bg)\n'
                  '                can_complete = self.can_complete_task(task) and (not task.get("subtasks") or '
                  'all_subtasks_done(task))\n'
                  '                self._apply_button_status(entry.get("done_button"), task, lambda t=task: '
                  'self.toggle_done(t), can_complete, False)\n'
                  '                try: entry.get("status_var").set(task.get("status", STATUS_OPEN))\n'
                  '                except Exception: pass\n'
                  '                self._safe_config(entry.get("status_menu"), bg=bg, state="normal" if can_complete '
                  'else "disabled")\n'
                  '                self._refresh_option_menu_commands(entry.get("status_menu"), '
                  'entry.get("status_var"), task)\n'
                  '            for sub in [s for s in task.get("subtasks", []) if not s.get("deleted")]:\n'
                  '                sentry = getattr(self, "_live_subtask_widgets", '
                  '{}).get(self._subtask_live_key(task, sub))\n'
                  '                if not sentry:\n'
                  '                    continue\n'
                  '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                  '                self._set_row_background(sentry.get("row_widgets"), sub_bg)\n'
                  '                self._apply_button_status(sentry.get("done_button"), sub, lambda t=task, s=sub: '
                  'self.toggle_subtask(t, s), self.can_complete_task(task), True)\n'
                  '\n'
                  '    def _current_scroll_fraction(self):\n'
                  '        try:\n'
                  '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                  '            return canvas.yview()[0] if canvas is not None else None\n'
                  '        except Exception:\n'
                  '            return None\n'
                  '\n'
                  '    def _restore_scroll_after_render(self, fraction):\n'
                  '        try:\n'
                  '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                  '            if canvas is not None and fraction is not None:\n'
                  '                self.root.after_idle(lambda c=canvas, f=fraction: c.yview_moveto(f))\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def _show_live_refresh_notice_once(self):\n'
                  '        if getattr(self, "_live_period_popup_open", False) or getattr(self, '
                  '"_live_period_notice_shown", False):\n'
                  '            return\n'
                  '        self._live_period_notice_shown = True\n'
                  '        self._live_period_popup_open = True\n'
                  '        try:\n'
                  '            messagebox.showinfo("Abschlusskalender", "Dieser Abschlusskalender wurde durch einen '
                  'anderen Benutzer aktualisiert. Die Ansicht wurde live neu geladen.")\n'
                  '        finally:\n'
                  '            self._live_period_popup_open = False\n'
                  '\n'
                  '    def _check_live_period_refresh(self):\n'
                  '        try:\n'
                  '            current_mtime = self._period_file_mtime()\n'
                  '            known_mtime = getattr(self, "_live_period_mtime", 0)\n'
                  '            if current_mtime and known_mtime and current_mtime != known_mtime:\n'
                  '                old_data = self.data\n'
                  '                new_data = load_period(self.period)\n'
                  '                old_structure = self._live_structure_signature(old_data)\n'
                  '                new_structure = self._live_structure_signature(new_data)\n'
                  '                old_status = self._live_status_signature(old_data)\n'
                  '                new_status = self._live_status_signature(new_data)\n'
                  '                self._live_period_mtime = current_mtime\n'
                  '                if old_structure == new_structure and old_status != new_status and '
                  'self.selected_team:\n'
                  '                    self._apply_smooth_status_update(new_data)\n'
                  '                elif old_structure == new_structure and old_status == new_status:\n'
                  '                    self.data = new_data\n'
                  '                else:\n'
                  '                    selected_team = self.selected_team\n'
                  '                    expanded = set(getattr(self, "expanded_tasks", set()))\n'
                  '                    was_edit_mode = bool(getattr(self, "edit_mode", False))\n'
                  '                    scroll_fraction = self._current_scroll_fraction()\n'
                  '                    self.data = new_data\n'
                  '                    self.expanded_tasks = expanded\n'
                  '                    if selected_team:\n'
                  '                        self.selected_team = selected_team\n'
                  '                        self.render_team_detail(selected_team)\n'
                  '                    else:\n'
                  '                        self.render_dashboard()\n'
                  '                    self._restore_scroll_after_render(scroll_fraction)\n'
                  '                    if was_edit_mode:\n'
                  '                        self._show_live_refresh_notice_once()\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '        try:\n'
                  '            self.root.after(3000, self._check_live_period_refresh)\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def handle_escape(self):\n'
                  '        if self.selected_team:\n'
                  '            self.selected_team = None\n'
                  '            self.render_dashboard()\n'
                  '            return True\n'
                  '        return False\n'
                  '\n'
                  '    def _module_ctrl_mousewheel_direction(self, event):\n'
                  '        try:\n'
                  '            if getattr(event, "num", None) == 4:\n'
                  '                return 1\n'
                  '            if getattr(event, "num", None) == 5:\n'
                  '                return -1\n'
                  '            delta = int(getattr(event, "delta", 0) or 0)\n'
                  '            return 1 if delta > 0 else (-1 if delta < 0 else 0)\n'
                  '        except Exception:\n'
                  '            return 0\n'
                  '\n'
                  '    def handle_module_ctrl_mousewheel(self, event=None):\n'
                  '        """v0.435: Strg+Mausrad im Abschlusskalender bleibt im aktuellen Kontext.\n'
                  '\n'
                  '        Hintergrund: Der globale Tool-Zoom kann das externe Tool neu laden und dadurch aus\n'
                  '        der Teamübersicht zurück ins Dashboard springen. Deshalb wird der Zoom hier lokal\n'
                  '        angewendet und die aktuell ausgewählte Teamansicht anschließend wiederhergestellt.\n'
                  '        """\n'
                  '        direction = self._module_ctrl_mousewheel_direction(event)\n'
                  '        if not direction:\n'
                  '            return "break"\n'
                  '        try:\n'
                  '            current = float(getattr(self.app, "current_scope_zoom", 1.0) or 1.0)\n'
                  '        except Exception:\n'
                  '            current = 1.0\n'
                  '        try:\n'
                  '            step = float(getattr(self.app, "GLOBAL_TEXT_ZOOM_STEP", 0.025) or 0.025)\n'
                  '        except Exception:\n'
                  '            step = 0.025\n'
                  '        new_zoom = max(0.70, min(1.80, current + (step * direction)))\n'
                  '        try:\n'
                  '            setattr(self.app, "current_scope_zoom", new_zoom)\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '        team = self.selected_team\n'
                  '        if team:\n'
                  '            try:\n'
                  '                self.render_team_detail(team)\n'
                  '            except Exception:\n'
                  '                apply_readable_fonts(self.frame, self.app, 12)\n'
                  '        else:\n'
                  '            try:\n'
                  '                self.render_dashboard()\n'
                  '            except Exception:\n'
                  '                apply_readable_fonts(self.frame, self.app, 12)\n'
                  '        return "break"\n'
                  '\n'
                  '    def bind_module_ctrl_mousewheel_guard(self, widget=None):\n'
                  '        """Bindet Strg+Mausrad auf alle Modulwidgets, damit der globale Handler nicht '
                  'navigiert."""\n'
                  '        widget = widget or self.frame\n'
                  '        try:\n'
                  '            for sequence in ("<Control-MouseWheel>", "<Control-Button-4>", "<Control-Button-5>"):\n'
                  '                widget.bind(sequence, self.handle_module_ctrl_mousewheel)\n'
                  '            for child in widget.winfo_children():\n'
                  '                self.bind_module_ctrl_mousewheel_guard(child)\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '\n'
                  '    def can_edit(self):\n'
                  '        return self.role_rank_value() >= 3 and not self.is_period_closed()\n'
                  '\n'
                  '    def user_choices(self):\n'
                  '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                  '        choices = [("", "Team / keine Person")]\n'
                  '        for key, data in sorted(users.items(), key=lambda item: item[1].get("display_name", '
                  'item[0]).casefold()):\n'
                  '            choices.append((key, data.get("display_name", key)))\n'
                  '        return choices\n'
                  '\n'
                  '\n'
                  '    def _target_period_from_current(self):\n'
                  '        y, m = map(int, self.period.split("-")); return f"{y}-Q{((m - 1) // 3) + 1}"\n'
                  '    def _target_periods_from(self, start_period, all_following):\n'
                  '        if not all_following: return [start_period]\n'
                  '        y, q = start_period.split("-Q"); y=int(y); q=int(q); out=[]\n'
                  '        for _ in range(12):\n'
                  '            out.append(f"{y}-Q{q}"); q += 1\n'
                  '            if q > 4: q = 1; y += 1\n'
                  '        return out\n'
                  '    def _target_period_end(self, period):\n'
                  '        y, q = period.split("-Q"); y=int(y); m=(int(q)-1)*3+3; return date(y, m, '
                  'calendar.monthrange(y, m)[1]).strftime("%Y-%m-%d")\n'
                  '    def _target_display(self, period):\n'
                  '        y, q = period.split("-Q"); return f"{q}. Quartal {y}"\n'
                  '\n'
                  '    def is_standard_user(self):\n'
                  '        return self.role_rank_value() <= 2\n'
                  '    def can_complete_task(self, task):\n'
                  '        if self.is_period_closed(): return False\n'
                  '        if not self.is_standard_user(): return True\n'
                  '        return bool(getattr(self.app, "current_user_key", "") and task.get("owner_user_key") == '
                  'getattr(self.app, "current_user_key", ""))\n'
                  '\n'
                  '    def current_user_full_name(self):\n'
                  '        key = getattr(self.app, "current_user_key", "")\n'
                  '        data = getattr(self.app, "user_data", {}).get("users", {}).get(key, {}) if key else {}\n'
                  '        return data.get("full_name") or " ".join(x for x in [data.get("first_name", "").strip(), '
                  'data.get("display_name", "").strip()] if x).strip() or getattr(self.app, "current_user_display", '
                  '"") or key or ""\n'
                  '\n'
                  '    def role_rank_value(self):\n'
                  '        role = self.app.my_role() if hasattr(self.app, "my_role") else "E1 - Standard"\n'
                  '        mapping = {"E1 - Standard": 1, "E2 - Erweitert": 2, "E3 - Administrator": 3, "E4 - '
                  'System-Administrator": 4, "Standard": 1, "Administrator": 3, "System-Administrator": 4, "Wagnerm": '
                  '4}\n'
                  '        return mapping.get(role, 1)\n'
                  '\n'
                  '    def ensure_close_metadata(self):\n'
                  '        self.data.setdefault("closed", False)\n'
                  '        self.data.setdefault("closed_at", None)\n'
                  '        self.data.setdefault("closed_by", "")\n'
                  '        self.data.setdefault("closed_by_key", "")\n'
                  '        self.data.setdefault("reopened_once", False)\n'
                  '        self.data.setdefault("close_events", [])\n'
                  '        self.data.setdefault("change_log", [])\n'
                  '        self.data.setdefault("reopen_email_log", [])\n'
                  '\n'
                  '    def is_period_closed(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        return bool(self.data.get("closed"))\n'
                  '\n'
                  '    def is_after_cutoff(self):\n'
                  '        cutoff = parse_date(self.data.get("closing_cutoff_date"))\n'
                  '        return bool(cutoff and date.today() > cutoff)\n'
                  '\n'
                  '    def can_toggle_period_close(self):\n'
                  '        return self.role_rank_value() >= 3\n'
                  '\n'
                  '    def require_unlocked(self, action="Diese Änderung"):\n'
                  '        if self.is_period_closed():\n'
                  '            messagebox.showwarning("Zeitraum geschlossen", f"{action} ist nicht möglich, weil der '
                  'Zeitraum geschlossen ist. Bitte den Zeitraum zuerst wieder öffnen.")\n'
                  '            return False\n'
                  '        return True\n'
                  '\n'
                  '    def log_period_event(self, action, reason="", extra=None):\n'
                  '        self.ensure_close_metadata()\n'
                  '        self.data.setdefault("close_events", []).append({\n'
                  '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                  '            "action": action,\n'
                  '            "user": self.current_user_full_name(),\n'
                  '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                  '            "reason": reason,\n'
                  '            "extra": extra or {},\n'
                  '        })\n'
                  '\n'
                  '    def log_change(self, action, task=None, field="", old="", new=""):\n'
                  '        self.ensure_close_metadata()\n'
                  '        after_reopen = bool(self.data.get("reopened_once")) and not self.data.get("closed")\n'
                  '        self.data.setdefault("change_log", []).append({\n'
                  '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                  '            "user": self.current_user_full_name(),\n'
                  '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                  '            "action": action,\n'
                  '            "task_title": task.get("title", "") if isinstance(task, dict) else "",\n'
                  '            "field": field,\n'
                  '            "old": str(old) if old is not None else "",\n'
                  '            "new": str(new) if new is not None else "",\n'
                  '            "after_reopen": after_reopen,\n'
                  '        })\n'
                  '\n'
                  '    def close_status_text(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        if self.data.get("closed"):\n'
                  '            return f"(zuletzt) abgeschlossen am {format_datetime_de(self.data.get(\'closed_at\'))} '
                  'durch {self.data.get(\'closed_by\', \'\')}"\n'
                  '        events = self.data.get("close_events", [])\n'
                  '        reopen = next((e for e in reversed(events) if e.get("action") == "opened"), None)\n'
                  '        if reopen:\n'
                  '            return f"Wieder geöffnet am {format_datetime_de(reopen.get(\'timestamp\'))} durch '
                  '{reopen.get(\'user\', \'\')}"\n'
                  '        return ""\n'
                  '\n'
                  '    def e3_e4_recipients(self):\n'
                  '        recipients=[]\n'
                  '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                  '        opener = getattr(self.app, "current_user_key", "")\n'
                  '        for key, data in users.items():\n'
                  '            if key == opener:\n'
                  '                continue\n'
                  '            role = data.get("permission", "")\n'
                  '            rank = {"E1 - Standard":1,"E2 - Erweitert":2,"E3 - Administrator":3,"E4 - '
                  'System-Administrator":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}.get(role, 1)\n'
                  '            if rank >= 3:\n'
                  '                recipients.append((key, data.get("email", ""), data.get("full_name") or " ".join(x '
                  'for x in [data.get("first_name", "").strip(), data.get("display_name", key).strip()] if x).strip() '
                  'or key))\n'
                  '        return recipients\n'
                  '\n'
                  '    def auto_close_mail_enabled(self):\n'
                  '        try:\n'
                  '            return bool(self.app.auto_close_mail_enabled())\n'
                  '        except Exception:\n'
                  '            return True\n'
                  '\n'
                  '    def send_period_close_email_auto(self):\n'
                  '        if not self.auto_close_mail_enabled():\n'
                  '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "sent": False, "skipped": True, "reason": "Auto-Mail '
                  'deaktiviert"})\n'
                  '            return True\n'
                  '        recipients = self.e3_e4_recipients()\n'
                  '        missing = [name for key, email, name in recipients if not email]\n'
                  '        send_to = [(key, email, name) for key, email, name in recipients if email]\n'
                  '        if not send_to:\n'
                  '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "sent": False, "missing": missing, "error": "Keine '
                  'Empfängeradresse"})\n'
                  '            messagebox.showwarning("Automatische E-Mail", "Der Zeitraum wurde abgeschlossen, aber '
                  'es konnte keine Abschluss-Mail versendet werden, weil keine E3/E4-E-Mail-Adresse hinterlegt ist.")\n'
                  '            return False\n'
                  '        try:\n'
                  '            import win32com.client\n'
                  '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                  '            mail = outlook.CreateItem(0)\n'
                  '            mail.To = ";".join(email for key, email, name in send_to)\n'
                  '            mail.Subject = f"Abschluss {self.close_type_label()}: {period_label(self.period)}"\n'
                  '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                  'wurde von {self.current_user_full_name()} abgeschlossen.\\n\\n"\n'
                  '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                  '            mail.Send()\n'
                  '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _, email, _ in send_to], '
                  '"missing": missing, "sent": True})\n'
                  '            return True\n'
                  '        except Exception as exc:\n'
                  '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                  'missing})\n'
                  '            messagebox.showwarning("Automatische E-Mail", f"Der Zeitraum wurde abgeschlossen, aber '
                  'die Abschluss-Mail konnte nicht automatisch versendet werden:\\n\\n{exc}")\n'
                  '            return False\n'
                  '\n'
                  '    def send_reopen_email_auto(self, reason):\n'
                  '        recipients = self.e3_e4_recipients()\n'
                  '        missing = [name for key, email, name in recipients if not email]\n'
                  '        send_to = [(key,email,name) for key,email,name in recipients if email]\n'
                  '        if not send_to:\n'
                  '            messagebox.showerror("Wiederöffnung", "Die Pflichtbenachrichtigung konnte nicht '
                  'versendet werden, weil keine E-Mail-Adresse für E3/E4-Empfänger hinterlegt ist.")\n'
                  '            return False\n'
                  '        try:\n'
                  '            import win32com.client\n'
                  '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                  '            mail = outlook.CreateItem(0)\n'
                  '            mail.To = ";".join(email for key,email,name in send_to)\n'
                  '            mail.Subject = f"Wiederöffnung {self.close_type_label()}: {period_label(self.period)}"\n'
                  '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                  'wurde von {self.current_user_full_name()} wieder geöffnet.\\n\\n"\n'
                  '                         f"Begründung:\\n{reason}\\n\\n"\n'
                  '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                  '            mail.Send()\n'
                  '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _,email,_ in send_to], '
                  '"missing": missing, "sent": True})\n'
                  '            return True\n'
                  '        except Exception as exc:\n'
                  '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                  'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                  'missing})\n'
                  '            messagebox.showerror("Wiederöffnung", f"Die Pflichtbenachrichtigung konnte nicht '
                  'automatisch über Outlook versendet werden. Der Zeitraum wurde nicht geöffnet.\\n\\n{exc}")\n'
                  '            return False\n'
                  '\n'
                  '    def ask_reopen_reason(self):\n'
                  '        result = {"reason": None}\n'
                  '        win = tk.Toplevel(self.root); win.title("Zeitraum öffnen"); win.configure(bg=COLORS["bg"]); '
                  'win.geometry("560x300"); win.transient(self.root); win.grab_set()\n'
                  '        tk.Label(win, text="Begründung der Wiederöffnung", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=14, pady=(14,6))\n'
                  '        tk.Label(win, text="Bitte gib eine Begründung ein. Ohne Begründung kann der Zeitraum nicht '
                  'wieder geöffnet werden.", bg=COLORS["bg"], fg=COLORS["text2"], wraplength=520, '
                  'justify="left").pack(anchor="w", padx=14, pady=(0,8))\n'
                  '        txt = tk.Text(win, height=7, bg="white", fg=COLORS["text"], relief="solid", bd=1); '
                  'txt.pack(fill="both", expand=True, padx=14, pady=(0,10))\n'
                  '        def ok():\n'
                  '            val = txt.get("1.0", "end").strip()\n'
                  '            if not val:\n'
                  '                messagebox.showwarning("Zeitraum öffnen", "Bitte eine Begründung eingeben."); '
                  'return\n'
                  '            result["reason"] = val; win.destroy()\n'
                  '        footer=tk.Frame(win,bg=COLORS["bg"]); footer.pack(fill="x", padx=14, pady=(0,12))\n'
                  '        '
                  'tk.Button(footer,text="Öffnen",command=ok,bg=COLORS["blue"],fg="white",bd=0,padx=14,pady=7).pack(side="right")\n'
                  '        '
                  'tk.Button(footer,text="Abbrechen",command=win.destroy,bg=COLORS["header"],fg=COLORS["text"],bd=0,padx=14,pady=7).pack(side="right",padx=(0,8))\n'
                  '        win.wait_window(); return result["reason"]\n'
                  '\n'
                  '    def toggle_period_close(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        if not self.can_toggle_period_close():\n'
                  '            messagebox.showwarning("Berechtigung", "Für diese Aktion ist mindestens E3 '
                  'erforderlich."); return\n'
                  '        if self.data.get("closed"):\n'
                  '            reason = self.ask_reopen_reason()\n'
                  '            if not reason: return\n'
                  '            if not self.send_reopen_email_auto(reason): return\n'
                  '            self.data["closed"] = False\n'
                  '            self.data["reopened_once"] = True\n'
                  '            self.log_period_event("opened", reason=reason)\n'
                  '            self.save(); self.render_dashboard(); return\n'
                  '        if not self.is_after_cutoff():\n'
                  '            messagebox.showinfo("Zeitraum abschließen", "Abschluss erst nach Ablauf des '
                  'Abschluss-Stichtags möglich."); return\n'
                  '        stats = calc_stats(self.tasks())\n'
                  '        msg = f"{period_label(self.period)} wirklich abschließen?\\n\\nNach dem Abschluss sind '
                  'keine Änderungen mehr möglich."\n'
                  '        if stats.get("open") or stats.get("in_progress"):\n'
                  '            msg += f"\\n\\nHinweis: Es sind noch {stats.get(\'open\',0)} Aufgaben offen und '
                  '{stats.get(\'in_progress\',0)} in Bearbeitung."\n'
                  '        if not messagebox.askyesno("Zeitraum abschließen", msg): return\n'
                  '        self.data["closed"] = True\n'
                  '        self.data["closed_at"] = datetime.now().isoformat(timespec="seconds")\n'
                  '        self.data["closed_by"] = self.current_user_full_name()\n'
                  '        self.data["closed_by_key"] = getattr(self.app, "current_user_key", "")\n'
                  '        self.log_period_event("closed")\n'
                  '        self.send_period_close_email_auto()\n'
                  '        self.save(); self.render_dashboard()\n'
                  '\n'
                  '    def show_change_log(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        win=tk.Toplevel(self.root); win.title("Änderungsprotokoll"); '
                  'win.configure(bg=COLORS["bg"]); win.geometry("1050x620")\n'
                  '        txt=tk.Text(win,bg="white",fg=COLORS["text"],wrap="word",font=zfont(self.app, 12)); '
                  'txt.pack(fill="both",expand=True,padx=12,pady=12)\n'
                  '        txt.insert("end", f"Änderungsprotokoll {period_label(self.period)}\\n\\n")\n'
                  '        txt.insert("end", "Abschluss-/Wiederöffnungsprotokoll:\\n")\n'
                  '        for e in self.data.get("close_events", []):\n'
                  '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | {e.get(\'action\')} '
                  '| {e.get(\'user\')} | {e.get(\'reason\',\'\')}\\n")\n'
                  '        txt.insert("end", "\\nÄnderungen:\\n")\n'
                  '        for e in self.data.get("change_log", []):\n'
                  '            flag = " [nach Wiederöffnung]" if e.get("after_reopen") else ""\n'
                  '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | {e.get(\'user\')} | '
                  "{e.get('action')} | {e.get('task_title')} | {e.get('field')}: {e.get('old')} -> "
                  '{e.get(\'new\')}{flag}\\n")\n'
                  '        txt.config(state="disabled")\n'
                  '\n'
                  '    def create_icon_button(self, parent, text, command, icon_key="lock", enabled=True, '
                  'tooltip=""):\n'
                  '        photo = None\n'
                  '        try:\n'
                  '            photo = self.app.get_icon_photo(icon_key, 18, 18)\n'
                  '        except Exception:\n'
                  '            photo = None\n'
                  '        btn = tk.Button(parent, text=text, image=photo, compound="left" if photo else None, '
                  'command=command if enabled else None, bg=COLORS["blue"] if enabled else "#CBD5E1", fg="white" if '
                  'enabled else COLORS["text2"], bd=0, padx=10, pady=4, cursor="hand2" if enabled else "arrow", '
                  'state="normal" if enabled else "disabled")\n'
                  '        if photo: btn.image = photo\n'
                  '        if tooltip:\n'
                  '            btn.bind("<Enter>", lambda e, b=btn: self.show_tooltip(b, tooltip)); '
                  'btn.bind("<Leave>", lambda e: self.hide_tooltip())\n'
                  '        return btn\n'
                  '    def _counterpart_period_dir(self):\n'
                  '        return BASE_DIR.parent / "QuarterlyClose" / "periods"\n'
                  '    def _load_target_period_data(self, period):\n'
                  '        path = self._counterpart_period_dir() / f"{period}.json"\n'
                  '        try: data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}\n'
                  '        except Exception: data = {}\n'
                  '        data.setdefault("period", period); data.setdefault("created_at", '
                  'datetime.now().isoformat(timespec="seconds")); data.setdefault("closing_cutoff_date", '
                  'self._target_period_end(period)); data.setdefault("team_members", {team: [] for team in TEAMS}); '
                  'data.setdefault("tasks", [])\n'
                  '        return data\n'
                  '    def _save_target_period_data(self, period, data):\n'
                  '        d = self._counterpart_period_dir(); d.mkdir(parents=True, exist_ok=True); (d / '
                  'f"{period}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                  '    def _clone_task_for_counterpart(self, task, period):\n'
                  '        cloned = json.loads(json.dumps(task, ensure_ascii=False)); cloned["id"] = '
                  'make_task_id(cloned.get("team", "Team"), int(datetime.now().strftime("%H%M%S%f")) % 1000000)\n'
                  '        cloned["status"] = STATUS_OPEN; cloned["done_at"] = None; cloned["done_by"] = None; '
                  'cloned["attachments"] = []; cloned["comments"] = []; cloned["catalog_id"] = ""; cloned["recurring"] '
                  '= bool(task.get("recurring", False)); cloned["transfer_source"] = '
                  'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; cloned["due_date"] = '
                  'self._target_period_end(period)\n'
                  '        for sub in cloned.get("subtasks", []): sub["status"] = STATUS_OPEN\n'
                  '        return cloned\n'
                  '    def transfer_task_to_counterpart(self, task, target_period, all_following=False):\n'
                  '        periods = self._target_periods_from(target_period, all_following); source_key = '
                  'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; count = 0\n'
                  '        for period in periods:\n'
                  '            data = self._load_target_period_data(period); tasks = data.setdefault("tasks", []); '
                  'existing = next((t for t in tasks if t.get("transfer_source") == source_key and not '
                  't.get("deleted")), None); cloned = self._clone_task_for_counterpart(task, period)\n'
                  '            if existing:\n'
                  '                keep = {"status": existing.get("status", STATUS_OPEN), "done_at": '
                  'existing.get("done_at"), "done_by": existing.get("done_by"), "attachments": '
                  'existing.get("attachments", []), "comments": existing.get("comments", [])}; existing.clear(); '
                  'existing.update(cloned); existing.update(keep)\n'
                  '            else: tasks.append(cloned)\n'
                  '            self._save_target_period_data(period, data); count += 1\n'
                  '        messagebox.showinfo("Monatsabschluss", f"Aufgabe wurde in {count} Quartalsabschluss(e) '
                  'übernommen.")\n'
                  '    def open_transfer_dialog(self, task):\n'
                  '            if not self.require_unlocked("Aufgabenübernahme ist nicht möglich"): return\n'
                  '            win = tk.Toplevel(self.root); win.title("In Quartalsabschluss übernehmen"); '
                  'win.configure(bg=COLORS["bg"]); win.transient(self.root); win.grab_set(); win.geometry("540x250")\n'
                  '            default_period = self._target_period_from_current(); mode_var = '
                  'tk.StringVar(value="all")\n'
                  '            tk.Label(win, text="Aufgabe inklusive Unteraufgaben übernehmen", bg=COLORS["bg"], '
                  'fg=COLORS["text"], font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=16, pady=(16, 10))\n'
                  '            tk.Radiobutton(win, text=f"In alle Quartalsabschlusse ab '
                  '{self._target_display(default_period)}", variable=mode_var, value="all", bg=COLORS["bg"], '
                  'activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)\n'
                  '            tk.Radiobutton(win, text=f"In Quartalsabschluss '
                  '{self._target_display(default_period)}", variable=mode_var, value="single", bg=COLORS["bg"], '
                  'activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)\n'
                  '            period_var = tk.StringVar(value=default_period); options = '
                  'self._target_periods_from(default_period, True)\n'
                  '            menu = tk.OptionMenu(win, period_var, *options); menu.config(bg="white", '
                  'fg=COLORS["text"], bd=1, highlightthickness=0); menu.pack(anchor="w", padx=18, pady=(10, 0))\n'
                  '            btns = tk.Frame(win, bg=COLORS["bg"]); btns.pack(side="bottom", fill="x", padx=16, '
                  'pady=14)\n'
                  '            tk.Button(btns, text="Übernehmen", command=lambda: '
                  '(self.transfer_task_to_counterpart(task, period_var.get(), mode_var.get()=="all"), win.destroy()), '
                  'bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                  '            tk.Button(btns, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                  'fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                  '    def propagate_team_members_to_related_periods(self):\n'
                  '        members = normalize_team_members(self.data)\n'
                  '        for period in list_periods():\n'
                  '            if period >= self.period:\n'
                  '                data = load_period(period); data["team_members"] = json.loads(json.dumps(members, '
                  'ensure_ascii=False)); save_period(period, data)\n'
                  '        for period in self._target_periods_from(self._target_period_from_current(), True):\n'
                  '            data = self._load_target_period_data(period); data["team_members"] = '
                  'json.loads(json.dumps(members, ensure_ascii=False)); self._save_target_period_data(period, data)\n'
                  '\n'
                  '    def clear_frame(self):\n'
                  '        if hasattr(self.app, "active_scroll_canvas"):\n'
                  '            self.app.active_scroll_canvas = None\n'
                  '        for child in self.frame.winfo_children():\n'
                  '            child.destroy()\n'
                  '\n'
                  '    def reload(self):\n'
                  '        self.data = apply_catalog_to_period(self.period)\n'
                  '\n'
                  '    def save(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        self.strip_task_ids_from_data(self.data)\n'
                  '        save_period(self.period, self.data)\n'
                  '        self._live_period_mtime = self._period_file_mtime()\n'
                  '\n'
                  '    def tasks(self):\n'
                  '        return [t for t in self.data.get("tasks", []) if not t.get("deleted")]\n'
                  '\n'
                  '    def team_tasks(self, team):\n'
                  '        return sorted(\n'
                  '            [t for t in self.tasks() if t.get("team") == team],\n'
                  '            key=lambda t: str(t.get("title", "")).casefold(),\n'
                  '        )\n'
                  '\n'
                  '    def task_sort_key(self, task):\n'
                  '        return str(task.get("title", "")).casefold()\n'
                  '\n'
                  '    def is_task_id_editor(self):\n'
                  '        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"\n'
                  '        return role in ("Administrator", "System-Administrator", "Wagnerm")\n'
                  '\n'
                  '    def normalize_task_uid_value(self, value):\n'
                  '        # v0.436: Aufgaben-ID-Zuweisung wurde vollständig entfernt.\n'
                  '        return ""\n'
                  '\n'
                  '    def task_uid_display(self, task):\n'
                  '        # v0.436: Es wird keine Aufgaben-ID mehr angezeigt.\n'
                  '        return ""\n'
                  '\n'
                  '    def initial_uid_for_task(self, task):\n'
                  '        return INITIAL_TASK_IDS.get((normalize_team_name(task.get("team")), str(task.get("title") '
                  'or "")), "")\n'
                  '\n'
                  '    def all_period_files(self):\n'
                  '        ensure_storage()\n'
                  '        return sorted(PERIOD_DIR.glob("*.json"))\n'
                  '\n'
                  '    def collect_used_task_uids(self, exclude_task=None):\n'
                  '        # v0.436: Keine Aufgaben-ID-Verwaltung mehr.\n'
                  '        return set()\n'
                  '\n'
                  '    def next_free_task_uid(self):\n'
                  '        # v0.436: Keine Aufgaben-ID-Zuweisung mehr.\n'
                  '        return ""\n'
                  '\n'
                  '    def task_identity_key_for_initial_id(self, task):\n'
                  '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                  '        if catalog_id:\n'
                  '            return ("catalog", catalog_id)\n'
                  '        initial = self.initial_uid_for_task(task)\n'
                  '        if initial:\n'
                  '            return ("initial", initial)\n'
                  '        return ("local", normalize_team_name(task.get("team")), str(task.get("title") or '
                  '"").strip().casefold())\n'
                  '\n'
                  '    def strip_task_ids_from_data(self, data):\n'
                  '        """Entfernt alte Aufgaben-ID-Felder aus geladenen/gespeicherten Daten, ohne andere Inhalte '
                  'zu verändern."""\n'
                  '        changed = False\n'
                  '        try:\n'
                  '            for task in data.get("tasks", []) or []:\n'
                  '                if "task_uid" in task:\n'
                  '                    task.pop("task_uid", None); changed = True\n'
                  '                for sub in task.get("subtasks", []) or []:\n'
                  '                    if "task_uid" in sub:\n'
                  '                        sub.pop("task_uid", None); changed = True\n'
                  '        except Exception:\n'
                  '            pass\n'
                  '        return changed\n'
                  '\n'
                  '    def strip_task_ids_all_periods(self):\n'
                  '        ensure_storage()\n'
                  '        for path in self.all_period_files():\n'
                  '            try:\n'
                  '                data = json.loads(path.read_text(encoding="utf-8"))\n'
                  '            except Exception:\n'
                  '                continue\n'
                  '            if self.strip_task_ids_from_data(data):\n'
                  '                try:\n'
                  '                    save_period(path.stem, data)\n'
                  '                    if path.stem == self.period:\n'
                  '                        self.data = data\n'
                  '                except Exception:\n'
                  '                    pass\n'
                  '\n'
                  '    def ensure_task_ids(self):\n'
                  '        # v0.436: Kompatibilitätsmethode; weist keine IDs mehr zu, sondern entfernt alte '
                  'ID-Felder.\n'
                  '        self.strip_task_ids_all_periods()\n'
                  '\n'
                  '    def archive_task_uid_change(self, task, old_uid, new_uid):\n'
                  '        # v0.436: ID-Historie deaktiviert.\n'
                  '        return False\n'
                  '\n'
                  '    def task_match_key(self, task):\n'
                  '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                  '        if catalog_id:\n'
                  '            return ("catalog", catalog_id)\n'
                  '        return ("task", str(task.get("id") or "").strip(), normalize_team_name(task.get("team")), '
                  'str(task.get("title") or "").strip().casefold())\n'
                  '\n'
                  '    def get_expand_key(self, task):\n'
                  '        return f"{task.get(\'id\',\'\')}|{task.get(\'team\',\'\')}|{task.get(\'title\',\'\')}"\n'
                  '\n'
                  '    def ask_delegate_scope(self, item, parent_task=None):\n'
                  '        if parent_task is not None:\n'
                  '            return "current"\n'
                  '        result = {"scope": None}\n'
                  '        win = tk.Toplevel(self.root)\n'
                  '        win.title("Zuständigkeit ändern")\n'
                  '        win.configure(bg=COLORS["bg"])\n'
                  '        win.transient(self.root); win.grab_set(); win.geometry("500x205")\n'
                  '        tk.Label(win, text="Zuständigkeit ändern", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                  '        tk.Label(win, text="Soll die Zuständigkeit nur für diesen Zeitraum oder permanent für alle '
                  'Folgezeiträume geändert werden?", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), '
                  'wraplength=455, justify="left").pack(anchor="w", padx=16, pady=(0, 12))\n'
                  '        frame = tk.Frame(win, bg=COLORS["bg"]); frame.pack(fill="x", padx=16)\n'
                  '        def choose(scope): result["scope"] = scope; win.destroy()\n'
                  '        tk.Button(frame, text="Nur dieser Zeitraum", command=lambda: choose("current"), '
                  'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))\n'
                  '        tk.Button(frame, text="Permanent für Folgezeiträume", command=lambda: choose("permanent"), '
                  'bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))\n'
                  '        tk.Button(frame, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                  'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                  '        win.wait_window()\n'
                  '        return result["scope"]\n'
                  '\n'
                  '    def apply_delegate_to_following_periods(self, task_key, owner_name, owner_user_key):\n'
                  '        changed_periods = 0\n'
                  '        for period in self.following_periods():\n'
                  '            data = load_period(period)\n'
                  '            changed = False\n'
                  '            for task in data.get("tasks", []):\n'
                  '                if self.task_match_key(task) == task_key:\n'
                  '                    task["owner"] = owner_name\n'
                  '                    task["owner_user_key"] = owner_user_key\n'
                  '                    for sub in task.get("subtasks", []):\n'
                  '                        sub["owner"] = owner_name\n'
                  '                        sub["owner_user_key"] = owner_user_key\n'
                  '                    changed = True\n'
                  '            if changed:\n'
                  '                self.strip_task_ids_from_data(data)\n'
                  '                save_period(period, data)\n'
                  '                changed_periods += 1\n'
                  '        return changed_periods\n'
                  '\n'
                  '    def close_type_label(self):\n'
                  '        scope = globals().get("CLOSING_SCOPE", "")\n'
                  '        return "Monatsabschluss" if scope == "M" else "Quartalsabschluss" if scope == "Q" else '
                  '"Jahresabschluss" if scope == "J" else "Abschluss"\n'
                  '\n'
                  '    def recipient_email_for_user(self, user_key):\n'
                  '        if not user_key:\n'
                  '            return ""\n'
                  '        try:\n'
                  '            return self.app.user_data.get("users", {}).get(user_key, {}).get("email", "")\n'
                  '        except Exception:\n'
                  '            return ""\n'
                  '\n'
                  '    def send_delegation_email(self, user_key, recipient_name, task_title, scope):\n'
                  '        email = self.recipient_email_for_user(user_key)\n'
                  '        if not email:\n'
                  '            messagebox.showwarning("Delegierung", f"Für {recipient_name} ist keine E-Mail-Adresse '
                  'in der Benutzerverwaltung hinterlegt. Die Delegierung wurde gespeichert, aber es konnte keine '
                  'E-Mail vorbereitet werden.")\n'
                  '            return\n'
                  '        delegated_by = getattr(self.app, "current_user_display", "") or getattr(self.app, '
                  '"current_user_key", "") or "FiBu Mate"\n'
                  '        period_text = period_label(self.period)\n'
                  '        close_type = self.close_type_label()\n'
                  '        if scope == "permanent":\n'
                  '            scope_text = "bis auf Weiteres"\n'
                  '        else:\n'
                  '            scope_text = f"für den Zeitraum {period_text}"\n'
                  '        subject = f"Delegierung {close_type}: {task_title}"\n'
                  '        body = (\n'
                  '            f"Hallo {recipient_name},\\n\\n"\n'
                  '            f"die Zuständigkeit der {close_type}-Aufgabe {task_title} wurde an dich von '
                  '{delegated_by} {scope_text} delegiert.\\n\\n"\n'
                  '            "Bitte bestätige die Kenntnisnahme per Antwort.\\n\\n"\n'
                  '            "Vielen Dank :)"\n'
                  '        )\n'
                  '        try:\n'
                  '            webbrowser.open("mailto:" + quote(email) + "?subject=" + quote(subject) + "&body=" + '
                  'quote(body))\n'
                  '        except Exception as exc:\n'
                  '            messagebox.showerror("Delegierung", f"Die E-Mail zur Delegierung konnte nicht '
                  'vorbereitet werden:\\n\\n{exc}")\n'
                  '\n'
                  '    def sync_current_as_template_to_following_periods(self):\n'
                  '        if not self.can_edit(): return\n'
                  '        following = self.following_periods()\n'
                  '        if not following:\n'
                  '            messagebox.showinfo("Vorlage verwenden", "Es sind keine Folgezeiträume vorhanden.")\n'
                  '            return\n'
                  '        msg = f"{period_label(self.period)} als Vorlage für alle Folgezeiträume '
                  'verwenden?\\n\\nAufgabenstruktur, Zuständigkeiten, Fälligkeiten und Unteraufgaben werden anhand von '
                  'Katalog-/Aufgabenschlüsseln übertragen. Status, Kommentare und Anlagen bleiben bei bereits '
                  'vorhandenen Aufgaben erhalten."\n'
                  '        if not messagebox.askyesno("Zeitraum als Vorlage verwenden", msg):\n'
                  '            return\n'
                  '        source = [json.loads(json.dumps(t, ensure_ascii=False)) for t in self.tasks()]\n'
                  '        updated = 0\n'
                  '        for period in following:\n'
                  '            data = load_period(period)\n'
                  '            old_by_key = {self.task_match_key(t): t for t in data.get("tasks", [])}\n'
                  '            new_tasks = []\n'
                  '            for src in source:\n'
                  '                key = self.task_match_key(src)\n'
                  '                old = old_by_key.get(key)\n'
                  '                new_task = json.loads(json.dumps(src, ensure_ascii=False))\n'
                  '                if old:\n'
                  '                    for keep in ("status", "attachments", "comments", "done_at", "done_by", '
                  '"documentation"):\n'
                  '                        if keep in old:\n'
                  '                            new_task[keep] = old.get(keep)\n'
                  '                    old_subs = {str(s.get("title", "")).strip().casefold(): s for s in '
                  'old.get("subtasks", [])}\n'
                  '                    for sub in new_task.get("subtasks", []):\n'
                  '                        old_sub = old_subs.get(str(sub.get("title", "")).strip().casefold())\n'
                  '                        if old_sub:\n'
                  '                            for keep in ("status", "attachments", "comments", "done_at", "done_by", '
                  '"documentation", "owner", "owner_user_key"):\n'
                  '                                if keep in old_sub:\n'
                  '                                    sub[keep] = old_sub.get(keep)\n'
                  '                new_tasks.append(new_task)\n'
                  '            data["tasks"] = new_tasks\n'
                  '            self.strip_task_ids_from_data(data)\n'
                  '            save_period(period, data)\n'
                  '            updated += 1\n'
                  '        messagebox.showinfo("Vorlage verwenden", f"Vorlage wurde auf {updated} Folgezeiträume '
                  'übertragen.")\n'
                  '\n'
                  '    def _pdf_escape(self, text):\n'
                  '        return str(text).replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")\n'
                  '\n'
                  '    def write_simple_pdf(self, path, title, rows):\n'
                  '        lines = [title, ""]\n'
                  '        for row in rows:\n'
                  '            lines.append(" | ".join(str(v) for v in row))\n'
                  '        pages = []\n'
                  '        for start in range(0, len(lines), 42):\n'
                  '            chunk = lines[start:start+42]\n'
                  '            ops = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]\n'
                  '            for line in chunk:\n'
                  '                ops.append(f"({self._pdf_escape(line[:150])}) Tj")\n'
                  '                ops.append("T*")\n'
                  '            ops.append("ET")\n'
                  '            pages.append("\\n".join(ops).encode("latin-1", "replace"))\n'
                  '        objects = []\n'
                  '        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")\n'
                  '        kids = " ".join(f"{3+i*2} 0 R" for i in range(len(pages)))\n'
                  '        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())\n'
                  '        for i, content in enumerate(pages):\n'
                  '            content_obj = 4 + i*2\n'
                  '            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << '
                  '/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 '
                  'R >>".encode())\n'
                  '            objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\\nstream\\n" + '
                  'content + b"\\nendstream")\n'
                  '        pdf = bytearray(b"%PDF-1.4\\n")\n'
                  '        offsets = []\n'
                  '        for idx, obj in enumerate(objects, 1):\n'
                  '            offsets.append(len(pdf))\n'
                  '            pdf.extend(f"{idx} 0 obj\\n".encode()); pdf.extend(obj); pdf.extend(b"\\nendobj\\n")\n'
                  '        xref = len(pdf)\n'
                  '        pdf.extend(f"xref\\n0 {len(objects)+1}\\n0000000000 65535 f \\n".encode())\n'
                  '        for off in offsets:\n'
                  '            pdf.extend(f"{off:010d} 00000 n \\n".encode())\n'
                  '        pdf.extend(f"trailer\\n<< /Size {len(objects)+1} /Root 1 0 R '
                  '>>\\nstartxref\\n{xref}\\n%%EOF".encode())\n'
                  '        Path(path).write_bytes(bytes(pdf))\n'
                  '\n'
                  '    def create_simple_pdf(self, title, rows):\n'
                  '        path = filedialog.asksaveasfilename(title="PDF speichern", defaultextension=".pdf", '
                  'filetypes=[("PDF-Dateien", "*.pdf")], initialfile=title.replace(" ", "_").replace("/", "-") + '
                  '".pdf")\n'
                  '        if not path: return\n'
                  '        try:\n'
                  '            self.write_simple_pdf(path, title, rows)\n'
                  '            if messagebox.askyesno("PDF erstellt", "PDF wurde erstellt. Jetzt öffnen?"):\n'
                  '                try:\n'
                  '                    os.startfile(path)\n'
                  '                except Exception:\n'
                  '                    try: subprocess.Popen(["xdg-open", path])\n'
                  '                    except Exception: pass\n'
                  '        except Exception as exc:\n'
                  '            messagebox.showerror("PDF erstellen", f"PDF konnte nicht erstellt werden:\\n\\n{exc}")\n'
                  '\n'
                  '    def create_close_report(self):\n'
                  '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                  '        if is_preliminary_report and self.role_rank_value() < 4:\n'
                  '            messagebox.showwarning("Keine Berechtigung", "Der vorläufige Abschlussbericht ist nur '
                  'für E4 exportierbar.")\n'
                  '            return\n'
                  '        if (not is_preliminary_report) and self.role_rank_value() < 3:\n'
                  '            messagebox.showwarning("Keine Berechtigung", "Der Protokoll-Bericht für ganze Zeiträume '
                  'ist nur für E3 und E4 exportierbar.")\n'
                  '            return\n'
                  '        self.ensure_close_metadata()\n'
                  '        with_signature = messagebox.askyesno("Abschlussbericht", f"Bericht '
                  '{period_label(self.period)} mit Signatur- und Freigabefeld erstellen?\\n\\nJa = mit '
                  'Signatur-/Freigabefeld\\nNein = ohne Signatur-/Freigabefeld")\n'
                  '        default_name = '
                  'f"Abschlussbericht_{self.close_type_label()}_{period_label(self.period).replace(\' \', '
                  '\'_\').replace(\'/\', \'-\')}_{date.today().isoformat()}.pdf"\n'
                  '        path = filedialog.asksaveasfilename(title="Bericht-PDF speichern", defaultextension=".pdf", '
                  'filetypes=[("PDF-Dateien", "*.pdf")], initialfile=default_name)\n'
                  '        if not path: return\n'
                  '        try:\n'
                  '            self.create_reportlab_pdf(path, with_signature)\n'
                  '        except Exception as exc:\n'
                  '            try:\n'
                  '                rows = self.build_report_rows()\n'
                  '                self.write_simple_pdf(path, f"Abschlussbericht {self.close_type_label()} '
                  '{period_label(self.period)}", rows)\n'
                  '            except Exception as fallback_exc:\n'
                  '                messagebox.showerror("Abschlussbericht", f"Bericht konnte nicht erstellt '
                  'werden:\\n\\n{exc}\\n\\nFallback fehlgeschlagen:\\n{fallback_exc}")\n'
                  '                return\n'
                  '        if messagebox.askyesno("Bericht-PDF wurde erstellt", "Bericht-PDF wurde erstellt. Jetzt '
                  'öffnen?"):\n'
                  '            try: os.startfile(path)\n'
                  '            except Exception:\n'
                  '                try: subprocess.Popen(["xdg-open", path])\n'
                  '                except Exception: pass\n'
                  '\n'
                  '    def build_report_rows(self):\n'
                  '        rows = []\n'
                  '        for task in self.tasks():\n'
                  '            rows.append([f"{task.get(\'title\',\'\')} | {task.get(\'owner\',\'\')} | '
                  '{due_rule_text(task)} {format_date_de(task.get(\'due_date\'))} | {task.get(\'status\',\'\')}"])\n'
                  '            for sub in task.get("subtasks", []) or []:\n'
                  '                if not sub.get("deleted"):\n'
                  '                    rows.append([f"  - {sub.get(\'title\',\'\')} | {sub.get(\'owner\', '
                  'task.get(\'owner\',\'\'))} | {sub.get(\'status\',\'\')}"])\n'
                  '        return rows\n'
                  '\n'
                  '    def create_reportlab_pdf(self, path, with_signature=False):\n'
                  '        from reportlab.lib import colors\n'
                  '        from reportlab.lib.pagesizes import A4\n'
                  '        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle\n'
                  '        from reportlab.lib.units import cm\n'
                  '        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, '
                  'PageBreak\n'
                  '        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4*cm, leftMargin=1.4*cm, '
                  'topMargin=1.2*cm, bottomMargin=1.2*cm)\n'
                  '        styles = getSampleStyleSheet()\n'
                  '        dark_blue = colors.HexColor("#1F4E79")\n'
                  '        styles.add(ParagraphStyle(name="FMTitle", parent=styles["Title"], '
                  'fontName="Helvetica-Bold", fontSize=16, textColor=dark_blue, spaceAfter=10))\n'
                  '        styles.add(ParagraphStyle(name="FMHead", parent=styles["Heading2"], '
                  'fontName="Helvetica-Bold", fontSize=13, textColor=dark_blue, spaceBefore=10, spaceAfter=6))\n'
                  '        styles.add(ParagraphStyle(name="FMText", parent=styles["BodyText"], fontName="Helvetica", '
                  'fontSize=11, leading=14))\n'
                  '        styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", '
                  'fontSize=8, leading=10))\n'
                  '        story=[]\n'
                  '        story.append(Paragraph(f"Abschlussbericht {self.close_type_label()} '
                  '{period_label(self.period)}", styles["FMTitle"]))\n'
                  '        status = "Abgeschlossen" if self.data.get("closed") else "Nicht abgeschlossen"\n'
                  '        head = [["Berichtstyp", self.close_type_label()], ["Zeitraum", period_label(self.period)], '
                  '["Abschluss-Stichtag", format_date_de(self.data.get("closing_cutoff_date"))], ["Status", status], '
                  '["Erstellt durch", self.current_user_full_name()], ["Erstellt am", '
                  'datetime.now().strftime("%d.%m.%Y %H:%M")]]\n'
                  '        if self.data.get("closed_at"): head.append(["Zuletzt abgeschlossen", '
                  'f"{format_datetime_de(self.data.get(\'closed_at\'))} durch {self.data.get(\'closed_by\',\'\')}"])\n'
                  '        t=Table(head, colWidths=[5*cm, 11*cm]); '
                  't.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#D9EAF7")),("VALIGN",(0,0),(-1,-1),"TOP")]))\n'
                  '        story += [t, Spacer(1,8)]\n'
                  '        stats=calc_stats(self.tasks())\n'
                  '        story.append(Paragraph("Management Summary", styles["FMHead"]))\n'
                  '        story.append(Paragraph(f"Gesamtaufgaben: {stats[\'total\']} | Erledigt: {stats[\'done\']} | '
                  "Offen: {stats['open']} | In Bearbeitung: {stats['in_progress']} | Überfällig: {stats['overdue']} | "
                  'Kritisch: {stats[\'critical\']}", styles["FMText"]))\n'
                  '        story.append(Paragraph("Abschlussprotokoll", styles["FMHead"]))\n'
                  '        '
                  'events=[["Zeitpunkt","Aktion","Benutzer","Begründung"]]+[[format_datetime_de(e.get("timestamp")), '
                  'e.get("action",""), e.get("user",""), e.get("reason","")] for e in self.data.get("close_events", '
                  '[])]\n'
                  '        story.append(Table(events, repeatRows=1, colWidths=[3.2*cm,2.5*cm,4*cm,6.3*cm], '
                  'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                  '        story.append(Paragraph("Teamübersicht", styles["FMHead"]))\n'
                  '        team_rows=[["Team","Gesamt","Erledigt","Offen","In Bearbeitung","Unteraufgaben"]]\n'
                  '        for team in TEAMS:\n'
                  '            tasks=[t for t in self.tasks() if t.get("team")==team and not t.get("deleted")]\n'
                  '            subs_done=sum(sum(1 for s in t.get("subtasks",[]) if s.get("status")==STATUS_DONE and '
                  'not s.get("deleted")) for t in tasks)\n'
                  '            subs_all=sum(sum(1 for s in t.get("subtasks",[]) if not s.get("deleted")) for t in '
                  'tasks)\n'
                  '            team_rows.append([team,len(tasks),sum(1 for t in tasks if '
                  't.get("status")==STATUS_DONE),sum(1 for t in tasks if t.get("status")==STATUS_OPEN),sum(1 for t in '
                  'tasks if t.get("status")==STATUS_IN_PROGRESS),f"{subs_done}/{subs_all}" if subs_all else ""])\n'
                  '        story.append(Table(team_rows, repeatRows=1, '
                  'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                  '        story.append(Paragraph("Aufgaben und Aufgabengruppen", styles["FMHead"]))\n'
                  '        for i,task in enumerate(self.tasks(),1):\n'
                  '            is_group=bool([s for s in task.get("subtasks",[]) if not s.get("deleted")])\n'
                  '            label="Aufgabengruppe" if is_group else "Aufgabe"\n'
                  '            critical = task.get("deadline_type")=="gesetzlich" or task.get("priority")=="kritisch"\n'
                  '            story.append(Paragraph(f"{i}. {label}: {task.get(\'title\',\'\')}", styles["FMHead" if '
                  'critical else "FMText"]))\n'
                  '            story.append(Paragraph(f"Zuständigkeit: {task.get(\'owner\',\'\')} | Fälligkeit: '
                  "{format_date_de(task.get('due_date'))} ({due_rule_text(task)}) | Status: {task.get('status','')} | "
                  'Erledigt: {format_datetime_de(task.get(\'done_at\'))}", styles["FMText"]))\n'
                  "            if 'z4' in task.get('title','').casefold() or 'zm-' in task.get('title','').casefold() "
                  "or 'zm meldung' in task.get('title','').casefold() or 'z5a' in task.get('title','').casefold():\n"
                  '                txt = f"<b><i>{task.get(\'title\',\'\')} erfolgt am '
                  '{format_datetime_de(task.get(\'done_at\'))}.</i></b>" if task.get(\'status\')==STATUS_DONE else '
                  'f"<b><i>{task.get(\'title\',\'\')} wurde im Zeitraum nicht als erledigt markiert.</i></b>"\n'
                  '                story.append(Paragraph(txt, styles["FMText"]))\n'
                  '            comments=task.get("comments",[])\n'
                  '            if comments:\n'
                  '                story.append(Paragraph("Kommentare / Notizen", styles["FMText"]))\n'
                  '                for c in comments:\n'
                  '                    story.append(Paragraph(str(c), styles["Small"]))\n'
                  '            attachments=task.get("attachments",[])\n'
                  '            if attachments:\n'
                  '                rows=[["Anlagenname","Anlagenpfad"]]\n'
                  '                for a in attachments:\n'
                  '                    if isinstance(a,dict): rows.append([a.get("name") or '
                  'Path(a.get("path","")).name, a.get("path","") + (f" [{a.get(\'created_at\',\'\')}]" if '
                  'a.get(\'created_at\') else "")])\n'
                  '                    else: rows.append([Path(str(a)).name, str(a)])\n'
                  '                story.append(Paragraph(f"Anlagen: {len(attachments)}", styles["FMText"])); '
                  'story.append(Table(rows, '
                  'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                  '            for j,sub in enumerate([s for s in task.get("subtasks",[]) if not '
                  's.get("deleted")],1):\n'
                  '                story.append(Paragraph(f"{i}.{j} Aufgabe: {sub.get(\'title\',\'\')}", '
                  'styles["FMText"]))\n'
                  '                story.append(Paragraph(f"Zuständigkeit: '
                  '{sub.get(\'owner\',task.get(\'owner\',\'\'))} | Status: {sub.get(\'status\',\'\')}", '
                  'styles["Small"]))\n'
                  '        open_tasks=[t for t in self.tasks() if t.get("status")!=STATUS_DONE and not '
                  't.get("deleted")]\n'
                  '        story.append(Paragraph("Offene Punkte", styles["FMHead"]))\n'
                  '        if open_tasks:\n'
                  '            for tsk in open_tasks: story.append(Paragraph(f"- {tsk.get(\'title\',\'\')}, zuständig: '
                  '{tsk.get(\'owner\',\'\')}, Status: {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                  '        else: story.append(Paragraph("Keine offenen Punkte.", styles["FMText"]))\n'
                  '        critical_tasks=[t for t in self.tasks() if (t.get("deadline_type")=="gesetzlich" or '
                  't.get("priority")=="kritisch" or warning_level(t) in ("overdue","today","orange")) and not '
                  't.get("deleted")]\n'
                  '        story.append(Paragraph("Kritische oder gesetzliche Fristen", styles["FMHead"]))\n'
                  '        for tsk in critical_tasks: story.append(Paragraph(f"- <b>{tsk.get(\'title\',\'\')}</b> | '
                  '{format_date_de(tsk.get(\'due_date\'))} | {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                  '        changes=[c for c in self.data.get("change_log",[]) if c.get("after_reopen")]\n'
                  '        story.append(Paragraph("Nachträgliche Änderungen nach Wiederöffnung", styles["FMHead"]))\n'
                  '        if changes:\n'
                  '            '
                  'rows=[["Zeitpunkt","Benutzer","Aufgabe","Feld","Alt","Neu"]]+[[format_datetime_de(c.get("timestamp")),c.get("user",""),c.get("task_title",""),c.get("field",""),c.get("old",""),c.get("new","")] '
                  'for c in changes]\n'
                  '            story.append(Table(rows, repeatRows=1, '
                  'colWidths=[2.7*cm,3*cm,3.5*cm,2.3*cm,2.2*cm,2.2*cm], '
                  'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#FDE68A")),("FONTSIZE",(0,0),(-1,-1),7)])))\n'
                  '        else: story.append(Paragraph("Keine nachträglichen Änderungen dokumentiert.", '
                  'styles["FMText"]))\n'
                  '        if with_signature:\n'
                  '            story += [Spacer(1,18), Paragraph("Signatur- und Freigabefeld", styles["FMHead"]), '
                  'Spacer(1,16), Paragraph("Erstellt durch: _______________________ Datum: ___________", '
                  'styles["FMText"]), Spacer(1,14), Paragraph("Geprüft durch: ________________________ Datum: '
                  '___________", styles["FMText"]), Spacer(1,14), Paragraph("Freigegeben durch: ____________________ '
                  'Datum: ___________", styles["FMText"])]\n'
                  '        version = getattr(self.app, "version_label_text", lambda: "")()\n'
                  '        footer = f"Bericht automatisch erstellt von {self.current_user_full_name()} am '
                  '{datetime.now().strftime(\'%d.%m.%Y %H:%M\')} mit FiBu Mate {version}."\n'
                  '        story.append(Spacer(1,10)); story.append(Paragraph(footer, styles["Small"]))\n'
                  '        doc.build(story)\n'
                  '\n'
                  '    def create_task_id_report(self, task):\n'
                  '        # v0.436: Einzelaufgaben-PDFs sind deaktiviert. Exportiert werden nur ganze Zeiträume als '
                  'Protokoll-Bericht.\n'
                  '        messagebox.showinfo("Protokoll-Bericht", "Einzelaufgaben-Berichte sind deaktiviert. Bitte '
                  'den Protokoll-Bericht für den gesamten Zeitraum exportieren.")\n'
                  '        return\n'
                  '\n'
                  '    def task_match_key(self, task):\n'
                  '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                  '        if catalog_id:\n'
                  '            return ("catalog", catalog_id)\n'
                  '        return (\n'
                  '            "task",\n'
                  '            str(task.get("id") or "").strip(),\n'
                  '            normalize_team_name(task.get("team")),\n'
                  '            str(task.get("title") or "").strip().casefold(),\n'
                  '        )\n'
                  '\n'
                  '    def find_task_index_exact(self, task):\n'
                  '        tasks = self.data.get("tasks", [])\n'
                  '        for idx, candidate in enumerate(tasks):\n'
                  '            if candidate is task:\n'
                  '                return idx\n'
                  '        key = self.task_match_key(task)\n'
                  '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                  'self.task_match_key(candidate) == key]\n'
                  '        return matches[0] if len(matches) == 1 else None\n'
                  '\n'
                  '    def following_periods(self):\n'
                  '        return [period for period in list_periods() if period > self.period]\n'
                  '\n'
                  '    def remove_task_from_data_by_key(self, data, key):\n'
                  '        tasks = data.get("tasks", [])\n'
                  '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                  'self.task_match_key(candidate) == key]\n'
                  '        if len(matches) == 1:\n'
                  '            tasks.pop(matches[0])\n'
                  '            data["tasks"] = tasks\n'
                  '            return "removed"\n'
                  '        if len(matches) > 1:\n'
                  '            return "ambiguous"\n'
                  '        return "missing"\n'
                  '\n'
                  '    def ask_delete_scope(self, task):\n'
                  '        result = {"scope": None}\n'
                  '        win = tk.Toplevel(self.root)\n'
                  '        win.title("Aufgabe löschen")\n'
                  '        win.configure(bg=COLORS["bg"])\n'
                  '        win.transient(self.root)\n'
                  '        win.grab_set()\n'
                  '        win.geometry("520x245")\n'
                  '        tk.Label(win, text="Aufgabe löschen", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                  '        msg = f"Welche Zeiträume sollen bereinigt werden?\\n\\n{task.get(\'title\', \'\')}"\n'
                  '        if task.get("attachments"):\n'
                  '            msg += "\\n\\nHinweis: Anlagen-Dateien bleiben im Anlagenordner erhalten; nur die '
                  'Referenz in der Aufgabe wird entfernt."\n'
                  '        tk.Label(win, text=msg, bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), '
                  'justify="left", wraplength=480).pack(anchor="w", padx=16, pady=(0, 14))\n'
                  '        buttons = tk.Frame(win, bg=COLORS["bg"])\n'
                  '        buttons.pack(fill="x", padx=16, pady=(0, 16))\n'
                  '        def choose(scope):\n'
                  '            result["scope"] = scope\n'
                  '            win.destroy()\n'
                  '        tk.Button(buttons, text="Nur aktueller Zeitraum", command=lambda: choose("current"), '
                  'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0, 7))\n'
                  '        tk.Button(buttons, text="Aktueller und alle folgenden Zeiträume", command=lambda: '
                  'choose("following"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, '
                  'cursor="hand2").pack(fill="x", pady=(0, 7))\n'
                  '        tk.Button(buttons, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                  'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                  '        win.wait_window()\n'
                  '        return result["scope"]\n'
                  '\n'
                  '    def delete_from_following_periods(self, task_key):\n'
                  '        removed = 0\n'
                  '        ambiguous = 0\n'
                  '        for period in self.following_periods():\n'
                  '            data = load_period(period)\n'
                  '            result = self.remove_task_from_data_by_key(data, task_key)\n'
                  '            if result == "removed":\n'
                  '                save_period(period, data)\n'
                  '                removed += 1\n'
                  '            elif result == "ambiguous":\n'
                  '                ambiguous += 1\n'
                  '        return removed, ambiguous\n'
                  '\n'
                  '    def cleanup_following_periods(self):\n'
                  '            if not self.require_unlocked("Vorlage für Folgezeiträume ist nicht möglich"): return\n'
                  '            return self.sync_current_as_template_to_following_periods()\n'
                  '\n'
                  '    def draw_progress(self, parent, percent, width=260, height=20, bg=None):\n'
                  '        bg = bg or parent.cget("bg")\n'
                  '        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)\n'
                  '        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")\n'
                  '        fill_w = int(width * max(0, min(100, percent)) / 100)\n'
                  '        if fill_w: c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), '
                  'outline=progress_color(percent))\n'
                  '        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], '
                  'font=zfont(self.app, 11, "bold"))\n'
                  '        return c\n'
                  '\n'
                  '    def render_period_controls(self, parent):\n'
                  '        row = tk.Frame(parent, bg=COLORS["bg"])\n'
                  '        row.pack(fill="x", padx=24, pady=(10, 4))\n'
                  '        tk.Button(row, text="< vorherige(r) Monat", command=lambda: '
                  'self.change_period(add_period(self.period, -1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                  'pady=6, font=zfont(self.app, 10, "bold")).pack(side="left")\n'
                  '        periods = list_periods(); labels = {period_label(k): k for k in periods}; selected = '
                  'tk.StringVar(value=period_label(self.period))\n'
                  '        menu = tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: '
                  'self.change_period(labels[label]))\n'
                  '        menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0); '
                  'menu.pack(side="left", padx=10)\n'
                  '        tk.Button(row, text="nächste(r) Monat >", command=lambda: '
                  'self.change_period(add_period(self.period, 1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                  'pady=6, font=zfont(self.app, 10, "bold")).pack(side="left")\n'
                  '        tk.Frame(row, bg=COLORS["bg"]).pack(side="left", fill="x", expand=True)\n'
                  '        if self.can_edit(): self.render_edit_button(row)\n'
                  '\n'
                  '    def render_edit_button(self, parent):\n'
                  '        photo = '
                  'self.get_close_icon_photo("1486504369-change-edit-options-pencil-settings-tools-write_81307.ico", '
                  '28, 28)\n'
                  '        btn = tk.Button(\n'
                  '            parent,\n'
                  '            text="" if photo else "Bearbeiten",\n'
                  '            image=photo if photo else "",\n'
                  '            command=self.toggle_edit_mode,\n'
                  '            bg=parent.cget("bg"),\n'
                  '            activebackground=parent.cget("bg"),\n'
                  '            fg=COLORS["blue"],\n'
                  '            bd=0,\n'
                  '            highlightthickness=0,\n'
                  '            padx=2,\n'
                  '            pady=2,\n'
                  '            cursor="hand2",\n'
                  '        )\n'
                  '        if photo:\n'
                  '            btn.image = photo\n'
                  '        btn.pack(side="right", padx=(8, 0))\n'
                  '        btn.bind("<Enter>", lambda _e: self.show_tooltip(btn, "Bearbeiten"))\n'
                  '        btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                  '\n'
                  '    def create_delegate_button(self, parent, item, parent_task=None):\n'
                  '        photo = '
                  'self.get_close_icon_photo("1904671-arrow-arrow-right-change-direction-next-page-right_122521.ico", '
                  '14, 14)\n'
                  '        btn = tk.Button(\n'
                  '            parent,\n'
                  '            text="Delegieren",\n'
                  '            image=photo if photo else "",\n'
                  '            compound="left" if photo else "none",\n'
                  '            command=lambda it=item, pt=parent_task: self.show_delegate_popup(it, pt),\n'
                  '            bg=COLORS["white"],\n'
                  '            activebackground=COLORS["header"],\n'
                  '            fg=COLORS["blue"],\n'
                  '            bd=1,\n'
                  '            relief="solid",\n'
                  '            padx=5,\n'
                  '            pady=2,\n'
                  '            cursor="hand2",\n'
                  '            font=zfont(self.app, 10, "bold"),\n'
                  '        )\n'
                  '        if photo:\n'
                  '            btn.image = photo\n'
                  '        return btn\n'
                  '\n'
                  '    def show_delegate_popup(self, item, parent_task=None):\n'
                  '        if not self.can_edit():\n'
                  '            messagebox.showwarning("FiBu Mate", "Keine Berechtigung zum Delegieren.")\n'
                  '            return\n'
                  '        task_for_team = parent_task or item\n'
                  '        choices = self.user_choices()\n'
                  '        labels = []\n'
                  '        label_to_choice = {}\n'
                  '        current_key = item.get("owner_user_key", "")\n'
                  '        current_label = None\n'
                  '        for key, display in choices:\n'
                  '            label = display if not key else f"{display} ({key})"\n'
                  '            labels.append(label)\n'
                  '            label_to_choice[label] = (key, display)\n'
                  '            if key == current_key:\n'
                  '                current_label = label\n'
                  '        if not labels:\n'
                  '            messagebox.showwarning("FiBu Mate", "Keine Benutzer für die Delegierung vorhanden.")\n'
                  '            return\n'
                  '        if current_label is None:\n'
                  '            current_label = labels[0]\n'
                  '        win = tk.Toplevel(self.root)\n'
                  '        win.title("Zuständigkeit delegieren")\n'
                  '        win.configure(bg=COLORS["bg"])\n'
                  '        win.transient(self.root)\n'
                  '        win.grab_set()\n'
                  '        win.geometry("460x190")\n'
                  '        tk.Label(win, text="Zuständigkeit delegieren", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                  '        tk.Label(win, text="Bitte neue Zuständigkeit wählen.", bg=COLORS["bg"], fg=COLORS["text2"], '
                  'font=zfont(self.app, 12), wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(0, 10))\n'
                  '        selected = tk.StringVar(value=current_label)\n'
                  '        menu = tk.OptionMenu(win, selected, *labels)\n'
                  '        menu.config(bg=COLORS["white"], fg=COLORS["text"], bd=1, highlightthickness=0)\n'
                  '        menu.pack(fill="x", padx=16, pady=(0, 14))\n'
                  '        def apply_delegate():\n'
                  '            user_key, display_name = label_to_choice[selected.get()]\n'
                  '            scope = self.ask_delegate_scope(item, parent_task)\n'
                  '            if not scope:\n'
                  '                return\n'
                  '            fallback_team = task_for_team.get("team", item.get("team", "Team"))\n'
                  '            owner_name = display_name if user_key else fallback_team\n'
                  '            targets = [item]\n'
                  '            if parent_task is None:\n'
                  '                targets += [sub for sub in item.get("subtasks", []) if not sub.get("deleted")]\n'
                  '            for target in targets:\n'
                  '                target["owner_user_key"] = user_key\n'
                  '                target["owner"] = owner_name\n'
                  '            self.save()\n'
                  '            changed = 0\n'
                  '            if scope == "permanent" and parent_task is None:\n'
                  '                task_key = self.task_match_key(item)\n'
                  '                changed = self.apply_delegate_to_following_periods(task_key, owner_name, user_key)\n'
                  '            if user_key:\n'
                  '                self.send_delegation_email(user_key, display_name, task_for_team.get("title", '
                  'item.get("title", "")), scope)\n'
                  '            if self.selected_team:\n'
                  '                self.render_team_detail(self.selected_team)\n'
                  '            win.destroy()\n'
                  '            if scope == "permanent":\n'
                  '                messagebox.showinfo("Delegierung", f"Permanente Delegierung übertragen. '
                  'Folgezeiträume aktualisiert: {changed}")\n'
                  '        footer = tk.Frame(win, bg=COLORS["bg"])\n'
                  '        footer.pack(fill="x", padx=16, pady=(0, 14))\n'
                  '        tk.Button(footer, text="Übernehmen", command=apply_delegate, bg=COLORS["blue"], fg="white", '
                  'bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")\n'
                  '        tk.Button(footer, text="Abbrechen", command=win.destroy, bg=COLORS["header"], '
                  'fg=COLORS["text"], bd=0, padx=14, pady=7, cursor="hand2").pack(side="right", padx=(0, 8))\n'
                  '\n'
                  '    def show_tooltip(self, widget, text):\n'
                  '        self.hide_tooltip(); self.tooltip = tk.Toplevel(widget); '
                  'self.tooltip.wm_overrideredirect(True); self.tooltip.geometry(f"+{widget.winfo_rootx() + '
                  '12}+{widget.winfo_rooty() + 34}"); tk.Label(self.tooltip, text=text, bg="#111827", fg="white", '
                  'font=zfont(self.app, 11), padx=6, pady=3).pack()\n'
                  '\n'
                  '    def hide_tooltip(self):\n'
                  '        if self.tooltip:\n'
                  '            try: self.tooltip.destroy()\n'
                  '            except Exception: pass\n'
                  '        self.tooltip = None\n'
                  '\n'
                  '    def toggle_edit_mode(self):\n'
                  '        self.edit_mode = not self.edit_mode\n'
                  '        self.render_team_detail(self.selected_team) if self.selected_team else '
                  'self.render_dashboard()\n'
                  '\n'
                  '    def render_edit_tools(self, parent, team=None):\n'
                  '        if not (self.can_edit() and self.edit_mode): return\n'
                  '        row = tk.Frame(parent, bg=COLORS["edit_bg"], bd=1, relief="solid"); row.pack(fill="x", '
                  'padx=24, pady=(0, 8))\n'
                  '        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")).pack(side="left", padx=10, pady=7)\n'
                  '        if team:\n'
                  '            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: '
                  'self.open_task_dialog(team), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5, '
                  'font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                  '            tk.Button(row, text="Aufgaben allen vorhandenen Perioden zuweisen", '
                  'command=self.apply_current_tasks_to_all_periods, bg=COLORS["orange"], fg="white", bd=0, padx=12, '
                  'pady=5, font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                  '            tk.Button(row, text="Diesen Zeitraum als Vorlage für Folgemonate verwenden", '
                  'command=self.cleanup_following_periods, bg=COLORS["red"], fg="white", bd=0, padx=12, pady=5, '
                  'font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                  '\n'
                  '    def change_period(self, period):\n'
                  '        if not period_allowed(period):\n'
                  '            messagebox.showinfo("Monatsabschluss", "Dieser Zeitraum liegt außerhalb der '
                  'freigegebenen Zeitraumlogik ab Mai 2026 bzw. außerhalb des zulässigen Geschäftsjahres.")\n'
                  '            return\n'
                  '        self.period = period; self.reload(); self.selected_team = None; self.render_dashboard()\n'
                  '\n'
                  '    def save_cutoff_from_entry(self, entry_var=None):\n'
                  '        messagebox.showinfo(\n'
                  '            "FiBu Mate",\n'
                  '            "Der Abschluss-Stichtag wird zentral in der Stichtagspflege gepflegt.\\n\\n"\n'
                  '            "Eine manuelle Änderung in der Zeitraumsübersicht ist nicht mehr möglich."\n'
                  '        )\n'
                  '\n'
                  '    def render_dashboard(self):\n'
                  '        self.ensure_close_metadata()\n'
                  '        old_cutoff = self.data.get("closing_cutoff_date", "")\n'
                  '        normalize_cutoff(self.data, self.period)\n'
                  '        if old_cutoff != self.data.get("closing_cutoff_date", ""):\n'
                  '            save_period(self.period, self.data)\n'
                  '            self.data = load_period(self.period)\n'
                  '        self.selected_team = None; self.clear_frame(); self.render_period_controls(self.frame); '
                  'self.render_edit_tools(self.frame)\n'
                  '        stats = calc_stats(self.tasks())\n'
                  '        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); top.pack(fill="x", '
                  'padx=24, pady=(8, 10))\n'
                  '        title_row = tk.Frame(top, bg=COLORS["white"]); title_row.pack(fill="x", padx=14, pady=(6, '
                  '2))\n'
                  '        tk.Label(title_row, text=f"Monatsabschluss {period_label(self.period)}", '
                  'bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 24, "bold")).pack(side="left")\n'
                  '        cutoff_text = format_date_de(self.data.get("closing_cutoff_date")) or "nicht gepflegt"\n'
                  '        tk.Label(title_row, text="Abschluss-Stichtag", bg=COLORS["white"], fg=COLORS["text2"], '
                  'font=zfont(self.app, 12, "bold")).pack(side="left", padx=(24, 6))\n'
                  '        tk.Label(title_row, text=cutoff_text, bg="#F8FAFC", fg=COLORS["text"], font=zfont(self.app, '
                  '12, "bold"), relief="solid", bd=1, padx=8, pady=3).pack(side="left")\n'
                  '        toggle_text = f"{period_label(self.period)} {\'öffnen\' if self.is_period_closed() else '
                  '\'abschließen\'}"\n'
                  '        enabled = self.can_toggle_period_close() and (self.is_period_closed() or '
                  'self.is_after_cutoff())\n'
                  '        tooltip = "Abschluss erst nach Ablauf des Abschluss-Stichtags möglich" if '
                  'self.can_toggle_period_close() and not self.is_period_closed() and not self.is_after_cutoff() else '
                  '""\n'
                  '        self.create_icon_button(title_row, toggle_text, self.toggle_period_close, "unlock" if '
                  'self.is_period_closed() else "lock", enabled, tooltip).pack(side="left", padx=(8,0))\n'
                  '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                  '        report_text = "vorläufigen Abschlussbericht erstellen" if is_preliminary_report else '
                  '"Abschlussbericht erstellen"\n'
                  '        if (self.role_rank_value() >= 4 if is_preliminary_report else self.role_rank_value() >= '
                  '3):\n'
                  '            tk.Button(title_row, text=report_text, command=self.create_close_report, '
                  'bg=COLORS["white"], fg=COLORS["blue"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                  'padx=(8, 0))\n'
                  '        tk.Button(title_row, text="Änderungsprotokoll anzeigen", command=self.show_change_log, '
                  'bg=COLORS["white"], fg=COLORS["text"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                  'padx=(8,0))\n'
                  '        status_text = self.close_status_text()\n'
                  '        if status_text:\n'
                  '            tk.Label(top, text=status_text, bg=COLORS["white"], fg=COLORS["orange"] if not '
                  'self.is_period_closed() else COLORS["dark_green"], font=zfont(self.app, 12, '
                  '"bold")).pack(anchor="w", padx=14, pady=(2,0))\n'
                  '        tk.Label(top, text=f"Gesamt: {stats[\'done\']} erledigt / {stats[\'in_progress\']} in '
                  "Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} "
                  'überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", '
                  'padx=14)\n'
                  '        holder = tk.Frame(top, bg=COLORS["white"]); holder.pack(anchor="w", padx=14, pady=(8, 10)); '
                  'self.draw_progress(holder, stats["percent"], width=520, height=24, '
                  'bg=COLORS["white"]).pack(side="left")\n'
                  '        self.render_warnings(self.frame)\n'
                  '        cards = tk.Frame(self.frame, bg=COLORS["bg"]); cards.pack(fill="both", expand=True, '
                  'padx=24, pady=8)\n'
                  '        for idx, team in enumerate(TEAMS): self.render_team_card(cards, team, idx)\n'
                  '        self.bind_module_ctrl_mousewheel_guard()\n'
                  '\n'
                  '    def render_warnings(self, parent):\n'
                  '        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", '
                  '"yellow") and t.get("status") != STATUS_DONE]\n'
                  '        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid"); '
                  'box.pack(fill="x", padx=24, pady=(0, 8))\n'
                  '        if warnings:\n'
                  '            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} '
                  'Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=zfont(self.app, 14, "bold")).pack(anchor="w", '
                  'padx=12, pady=(8, 3))\n'
                  '            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:\n'
                  '                tk.Label(box, text=f"- {task[\'title\']} | {task[\'team\']} | fällig am '
                  '{format_date_de(task.get(\'due_date\'))} | {task.get(\'deadline_type\')}", bg=box["bg"], '
                  'fg=COLORS["text"], font=zfont(self.app, 12)).pack(anchor="w", padx=20, pady=1)\n'
                  '        else:\n'
                  '            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], '
                  'fg=COLORS["dark_green"], font=zfont(self.app, 13, "bold")).pack(anchor="w", padx=12, pady=8)\n'
                  '\n'
                  '    def next_relevant_task(self, tasks):\n'
                  '        open_tasks = [t for t in tasks if t.get("status") != STATUS_DONE and t.get("deadline_type") '
                  '!= "keine"]\n'
                  '        return sorted(open_tasks, key=lambda t: parse_date(t.get("due_date", "9999-12-31")) or '
                  'date.max)[0] if open_tasks else None\n'
                  '\n'
                  '    def bind_click_recursive(self, widget, command):\n'
                  '        widget.bind("<Button-1>", lambda _e: command()); widget.configure(cursor="hand2")\n'
                  '        for child in widget.winfo_children():\n'
                  '            if isinstance(child, (tk.Entry, tk.Text, tk.Button)): continue\n'
                  '            self.bind_click_recursive(child, command)\n'
                  '\n'
                  '    def save_team_members_from_widget(self, team, widget):\n'
                  '        set_team_members_text(self.data, team, widget.get("1.0", "end")); self.save(); '
                  'self.propagate_team_members_to_related_periods(); self.reload(); self.render_dashboard()\n'
                  '\n'
                  '    def render_team_members_on_card(self, card, team):\n'
                  '        names = normalize_team_members(self.data).get(team, [])\n'
                  '        if self.edit_mode and self.can_edit():\n'
                  '            edit_box = tk.Text(card, height=3, width=42, bg="#F8FAFC", fg=COLORS["text"], '
                  'relief="solid", bd=1); edit_box.insert("1.0", "\\n".join(names)); edit_box.pack(anchor="w", '
                  'padx=18, pady=(0, 6))\n'
                  '            tk.Button(card, text="Namen speichern", command=lambda t=team, w=edit_box: '
                  'self.save_team_members_from_widget(t, w), bg=COLORS["blue"], fg="white", bd=0, padx=8, '
                  'pady=3).pack(anchor="w", padx=18, pady=(0, 10))\n'
                  '        elif names:\n'
                  '            tk.Label(card, text=" • ".join(names), bg=COLORS["white"], fg=COLORS["text2"], '
                  'font=zfont(self.app, 12), wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, 12))\n'
                  '\n'
                  '    def render_team_card(self, parent, team, idx):\n'
                  '        row, col = divmod(idx, 2); tasks = self.team_tasks(team); stats = calc_stats(tasks)\n'
                  '        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, '
                  '"orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")\n'
                  '        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == '
                  '"orange" else COLORS["line"]\n'
                  '        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", '
                  'highlightbackground=border, highlightcolor=border, highlightthickness=2); card.grid(row=row, '
                  'column=col, padx=12, pady=12, sticky="nsew")\n'
                  '        parent.grid_columnconfigure(col, weight=1); parent.grid_rowconfigure(row, weight=1)\n'
                  '        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 19, '
                  '"bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                  '        tk.Label(card, text=f"{stats[\'done\']} / {stats[\'total\']} erledigt | offen: '
                  '{stats[\'open\']} | in Bearbeitung: {stats[\'in_progress\']} | kritisch: {stats[\'critical\']}", '
                  'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", padx=18)\n'
                  '        holder = tk.Frame(card, bg=COLORS["white"]); holder.pack(anchor="w", padx=18, pady=(10, '
                  '8)); self.draw_progress(holder, stats["percent"], width=420, height=26, bg=COLORS["white"]).pack()\n'
                  '        nxt = self.next_relevant_task(tasks); txt = "Nächste Frist: keine relevanten offenen '
                  'Fristen" if not nxt else f"Nächste Frist: {format_date_de(nxt.get(\'due_date\'))} | '
                  '{nxt.get(\'title\')}"\n'
                  '        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and warning_level(nxt) '
                  'in ("overdue", "today", "orange") else COLORS["text2"], font=zfont(self.app, 12, '
                  '"bold")).pack(anchor="w", padx=18, pady=(0, 5))\n'
                  '        self.render_team_members_on_card(card, team); self.bind_click_recursive(card, lambda '
                  't=team: self.render_team_detail(t))\n'
                  '\n'
                  '    def render_team_detail(self, team):\n'
                  '        self.selected_team = team; self.clear_frame(); self.render_period_controls(self.frame); '
                  'self.render_edit_tools(self.frame, team=team); stats = calc_stats(self.team_tasks(team))\n'
                  '        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); head.pack(fill="x", '
                  'padx=24, pady=(8, 10))\n'
                  '        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], '
                  'fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))\n'
                  '        tk.Label(head, text=f"{team} | Monatsabschluss {period_label(self.period)}", '
                  'bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 21, "bold")).pack(anchor="w", padx=12)\n'
                  '        tk.Label(head, text=f"Fortschritt: {stats[\'done\']} / {stats[\'total\']} erledigt | '
                  '{stats[\'percent\']}%", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, '
                  '13)).pack(anchor="w", padx=12)\n'
                  '        bar = tk.Frame(head, bg=COLORS["white"]); bar.pack(anchor="w", padx=12, pady=(6, 10)); '
                  'self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()\n'
                  '        self.render_task_table(team)\n'
                  '        self.bind_module_ctrl_mousewheel_guard()\n'
                  '\n'
                  '    def toggle_subtasks_visibility(self, task_id):\n'
                  '        if task_id in self.expanded_tasks:\n'
                  '            self.expanded_tasks.remove(task_id)\n'
                  '        else:\n'
                  '            self.expanded_tasks.add(task_id)\n'
                  '        self.render_team_detail(self.selected_team)\n'
                  '\n'
                  '    def normalize_documentation_fields(self, item):\n'
                  '        item.setdefault("attachments", [])\n'
                  '        item.setdefault("comments", [])\n'
                  '        doc = item.get("documentation")\n'
                  '        if isinstance(doc, str):\n'
                  '            item["documentation"] = {"name": os.path.basename(doc), "path": doc, "updated_at": ""} '
                  'if doc else {}\n'
                  '        elif not isinstance(doc, dict):\n'
                  '            item["documentation"] = {}\n'
                  '        clean_attachments = []\n'
                  '        for att in item.get("attachments", []):\n'
                  '            if isinstance(att, str):\n'
                  '                clean_attachments.append({"name": os.path.basename(att), "path": att, "comment": '
                  '"", "added_at": ""})\n'
                  '            elif isinstance(att, dict):\n'
                  '                att.setdefault("name", os.path.basename(att.get("path", "")) or att.get("name", '
                  '"Anlage"))\n'
                  '                att.setdefault("path", "")\n'
                  '                att.setdefault("comment", "")\n'
                  '                clean_attachments.append(att)\n'
                  '        item["attachments"] = clean_attachments\n'
                  '        return item\n'
                  '\n'
                  '    def due_display_inline(self, task):\n'
                  '        date_text = format_date_de(task.get("due_date", ""))\n'
                  '        rule = due_rule_text(task)\n'
                  '        return f"{date_text} - {rule}" if rule else date_text\n'
                  '\n'
                  '    def find_subtask(self, task_id, subtask_id):\n'
                  '        task = self.find_task(task_id)\n'
                  '        if not task:\n'
                  '            return None, None\n'
                  '        for sub in task.get("subtasks", []):\n'
                  '            if sub.get("id") == subtask_id and not sub.get("deleted"):\n'
                  '                self.normalize_documentation_fields(sub)\n'
                  '                return task, sub\n'
                  '        return task, None\n'
                  '\n'
                  '    def documentation_count(self, item):\n'
                  '        self.normalize_documentation_fields(item)\n'
                  '        return 1 if item.get("documentation", {}).get("path") else 0\n'
                  '\n'
                  '    def attachment_count(self, item):\n'
                  '        self.normalize_documentation_fields(item)\n'
                  '        return len([a for a in item.get("attachments", []) if a.get("path")])\n'
                  '\n'
                  '    def get_close_icon_photo(self, icon_file, max_w=24, max_h=24):\n'
                  '        try:\n'
                  '            from PIL import Image, ImageTk\n'
                  '        except Exception:\n'
                  '            return None\n'
                  '        if not hasattr(self, "_icon_cache"):\n'
                  '            self._icon_cache = {}\n'
                  '        cache_key = (icon_file, int(max_w), int(max_h))\n'
                  '        if cache_key in self._icon_cache:\n'
                  '            return self._icon_cache[cache_key]\n'
                  '        icon_dir = Path(__file__).resolve().parent.parent / "Imgs" / "Icons" if '
                  'Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / '
                  '"bin" / "Imgs" / "Icons"\n'
                  '        path = icon_dir / icon_file\n'
                  '        if not path.exists():\n'
                  '            return None\n'
                  '        try:\n'
                  '            img = Image.open(path).convert("RGBA")\n'
                  '            ow, oh = img.size\n'
                  '            scale = min(1, max_w / max(1, ow), max_h / max(1, oh))\n'
                  '            img = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))\n'
                  '            photo = ImageTk.PhotoImage(img)\n'
                  '            self._icon_cache[cache_key] = photo\n'
                  '            return photo\n'
                  '        except Exception:\n'
                  '            return None\n'
                  '\n'
                  '    def create_attachment_button(self, parent, item, command):\n'
                  '        frame = tk.Frame(parent, bg=parent.cget("bg"))\n'
                  '        inner = tk.Frame(frame, bg=parent.cget("bg"))\n'
                  '        inner.place(relx=0.5, rely=0.5, anchor="center")\n'
                  '        photo = self.get_close_icon_photo("-attach-file_90371.ico", 18, 18)\n'
                  '        btn = tk.Button(inner, text="" if photo else "📎", image=photo, command=command, '
                  'bg=parent.cget("bg"), fg=COLORS["blue"], bd=0, cursor="hand2", padx=0, pady=0)\n'
                  '        if photo:\n'
                  '            btn.image = photo\n'
                  '        btn.pack(side="left", padx=(0, 3))\n'
                  '        tk.Label(inner, text=str(self.attachment_count(item)), bg=parent.cget("bg"), '
                  'fg=COLORS["blue"], font=zfont(self.app, 12, "bold")).pack(side="left")\n'
                  '        return frame\n'
                  '\n'
                  '    def draw_documentation_icon(self, canvas, has_documentation):\n'
                  '        canvas.delete("all")\n'
                  '        icon_file = "fileinterfacesymboloftextpapersheet_79740.ico" if has_documentation else '
                  '"addfileinterfacesymbolofpapersheetwithtextlinesandplussign_79821.ico"\n'
                  '        photo = self.get_close_icon_photo(icon_file, 22, 22)\n'
                  '        if photo:\n'
                  '            canvas.create_image(16, 12, image=photo)\n'
                  '            canvas.image = photo\n'
                  '            return\n'
                  '        color = COLORS["blue"]\n'
                  '        # Fallback ohne blaue Kachel: kleines Dokument-/Plus-Symbol nur als Liniengrafik.\n'
                  '        canvas.create_rectangle(8, 3, 22, 21, outline=color, width=2)\n'
                  '        canvas.create_line(18, 3, 22, 7, fill=color, width=2)\n'
                  '        if has_documentation:\n'
                  '            for y in (9, 13, 17):\n'
                  '                canvas.create_line(11, y, 20, y, fill=color, width=2, capstyle="round")\n'
                  '        else:\n'
                  '            canvas.create_line(15, 9, 15, 18, fill=color, width=2, capstyle="round")\n'
                  '            canvas.create_line(10, 13, 20, 13, fill=color, width=2, capstyle="round")\n'
                  '\n'
                  '    def create_documentation_button(self, parent, item, title, parent_task=None):\n'
                  '        has_doc = bool(item.get("documentation", {}).get("path"))\n'
                  '        bg = parent.cget("bg")\n'
                  '        btn = tk.Canvas(parent, width=32, height=24, bg=bg, highlightthickness=0, bd=0, '
                  'cursor="hand2")\n'
                  '        self.draw_documentation_icon(btn, has_doc)\n'
                  '        btn.bind("<Button-1>", lambda _e, it=item, t=title, pt=parent_task: '
                  'self.show_documentation_popup(it, t, pt))\n'
                  '        return btn\n'
                  '\n'
                  '    def show_documentation_popup(self, item, title, parent_task=None):\n'
                  '        self.normalize_documentation_fields(item)\n'
                  '        win = tk.Toplevel(self.root)\n'
                  '        win.title(f"Dokumentation - {title}")\n'
                  '        win.configure(bg=COLORS["bg"])\n'
                  '        win.geometry("720x270")\n'
                  '        win.transient(self.root)\n'
                  '        win.grab_set()\n'
                  '        tk.Label(win, text="Dokumentation", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(14, 8))\n'
                  '        body = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                  '        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))\n'
                  '        doc = item.get("documentation", {})\n'
                  '        name_var = tk.StringVar(value=doc.get("name", "Noch keine Dokumentation hinterlegt"))\n'
                  '        path_var = tk.StringVar(value=doc.get("path", ""))\n'
                  '\n'
                  '        row = tk.Frame(body, bg=COLORS["white"])\n'
                  '        row.pack(fill="x", padx=12, pady=(14, 6))\n'
                  '        open_button = tk.Button(row, text="Dokumentation öffnen", command=lambda: '
                  'self.open_attachment(path_var.get()), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6, '
                  'state="normal" if path_var.get() else "disabled")\n'
                  '        open_button.pack(side="left")\n'
                  '        tk.Label(row, textvariable=name_var, bg=COLORS["white"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12), anchor="w").pack(side="left", padx=(10, 6), fill="x", expand=True)\n'
                  '\n'
                  '        def refresh_after_change():\n'
                  '            if self.selected_team:\n'
                  '                self.render_team_detail(self.selected_team)\n'
                  '\n'
                  '        def choose_documentation():\n'
                  '            selected = filedialog.askopenfilename(title="Dokumentation auswählen")\n'
                  '            if not selected:\n'
                  '                return\n'
                  '            item["documentation"] = {"name": os.path.basename(selected), "path": selected, '
                  '"updated_at": datetime.now().isoformat(timespec="seconds")}\n'
                  '            self.save()\n'
                  '            name_var.set(os.path.basename(selected))\n'
                  '            path_var.set(selected)\n'
                  '            refresh_after_change()\n'
                  '            win.destroy()\n'
                  '\n'
                  '        def remove_documentation():\n'
                  '            if not path_var.get():\n'
                  '                return\n'
                  '            if not messagebox.askyesno("Dokumentation entfernen", "Dokumentation entfernen?", '
                  'parent=win):\n'
                  '                return\n'
                  '            item["documentation"] = {}\n'
                  '            self.save()\n'
                  '            name_var.set("Noch keine Dokumentation hinterlegt")\n'
                  '            path_var.set("")\n'
                  '            refresh_after_change()\n'
                  '            win.destroy()\n'
                  '\n'
                  '        if path_var.get():\n'
                  '            trash_photo = self.get_close_icon_photo("biggarbagebin_121980.ico", 20, 20)\n'
                  '            delete_btn = tk.Button(row, text="" if trash_photo else "🗑", image=trash_photo, '
                  'command=remove_documentation, bg=COLORS["white"], fg=COLORS["red"], bd=0, padx=2, pady=2, '
                  'cursor="hand2")\n'
                  '            if trash_photo:\n'
                  '                delete_btn.image = trash_photo\n'
                  '            delete_btn.pack(side="right", padx=(6, 0))\n'
                  '\n'
                  '        change = tk.Label(body, text="Dokumentationspfad ändern" if path_var.get() else '
                  '"Dokumentation anhängen", bg=COLORS["white"], fg=COLORS["blue"], font=zfont(self.app, 12, None, '
                  'underline=True), cursor="hand2")\n'
                  '        change.pack(anchor="w", padx=12, pady=(4, 10))\n'
                  '        change.bind("<Button-1>", lambda _e: choose_documentation())\n'
                  '        tk.Label(body, text="Hinweis: Die Dokumentation ist für Aufgabenbeschreibungen bzw. '
                  'Leitfäden vorgesehen. Ergebnisse und Bearbeitungskommentare bitte unter Anlagen pflegen.", '
                  'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=660, '
                  'justify="left").pack(anchor="w", padx=12, pady=(0, 10))\n'
                  '        tk.Button(win, text="Schließen", command=win.destroy, bg=COLORS["blue"], fg="white", bd=0, '
                  'padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))\n'
                  '\n'
                  '    def render_task_table(self, team):\n'
                  '        outer = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")\n'
                  '        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))\n'
                  '\n'
                  '        scroll_canvas = tk.Canvas(outer, bg=COLORS["white"], highlightthickness=0, bd=0)\n'
                  '        scrollbar = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)\n'
                  '        xscrollbar = tk.Scrollbar(outer, orient="horizontal", command=scroll_canvas.xview)\n'
                  '        table = tk.Frame(scroll_canvas, bg="#E4EAF1")  # dezente Spaltentrennlinien\n'
                  '        table_window = scroll_canvas.create_window((0, 0), window=table, anchor="nw")\n'
                  '\n'
                  '        def update_scrollregion(_event=None):\n'
                  '            table.update_idletasks()\n'
                  '            target_width = max(scroll_canvas.winfo_width(), table.winfo_reqwidth())\n'
                  '            scroll_canvas.itemconfigure(table_window, width=max(1, target_width))\n'
                  '            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))\n'
                  '\n'
                  '        def on_mousewheel(event):\n'
                  '            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")\n'
                  '            return "break"\n'
                  '\n'
                  '        table.bind("<Configure>", update_scrollregion)\n'
                  '        scroll_canvas.bind("<Configure>", update_scrollregion)\n'
                  '        scroll_canvas.bind("<MouseWheel>", on_mousewheel)\n'
                  '        table.bind("<MouseWheel>", on_mousewheel)\n'
                  '        scroll_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)\n'
                  '        xscrollbar.pack(side="bottom", fill="x")\n'
                  '        scroll_canvas.pack(side="left", fill="both", expand=True)\n'
                  '        scrollbar.pack(side="right", fill="y")\n'
                  '        self.app.active_scroll_canvas = scroll_canvas\n'
                  '        self._live_task_widgets = {}\n'
                  '        self._live_subtask_widgets = {}\n'
                  '\n'
                  '        headers = ["Status", "Aufgabe", "Dokumentation", "Zuständig", "Fällig", "Fristart", '
                  '"Priorität", "Wiederkehrend", "Anlagen", "Aktion"]\n'
                  '        if self.edit_mode and self.can_edit():\n'
                  '            headers.append("Bearbeiten")\n'
                  '        for col, h in enumerate(headers):\n'
                  '            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=zfont(self.app, '
                  '12, "bold"), padx=6, pady=6).grid(row=0, column=col, sticky="nsew")\n'
                  '        row_idx = 1\n'
                  '        for task in self.team_tasks(team):\n'
                  '            sync_parent_status_from_subtasks(task)\n'
                  '            self.normalize_documentation_fields(task)\n'
                  '            for sub in task.get("subtasks", []):\n'
                  '                self.normalize_documentation_fields(sub)\n'
                  '            row_idx = self.render_task_row(table, row_idx, task, headers)\n'
                  '\n'
                  '        # Spaltenbreiten: Aufgabe und Zuständig etwas reduziert; Dokumentation schmal; '
                  'Fristart/Priorität/Anlagen erhalten mehr Raum.\n'
                  '        min_sizes = {0: 46, 1: 560, 2: 92, 3: 225, 4: 220, 5: 105, 6: 105, 7: 120, 8: 100, 9: 88, '
                  '10: 150}\n'
                  '        stretch_cols = {1: 2, 4: 2, 5: 1, 6: 1, 8: 1}\n'
                  '        for col in range(len(headers)):\n'
                  '            table.grid_columnconfigure(col, minsize=min_sizes.get(col, 80), '
                  'weight=stretch_cols.get(col, 0))\n'
                  '        update_scrollregion()\n'
                  '\n'
                  '\n'
                  '    def render_task_row(self, table, row_idx, task, headers):\n'
                  '        current_row_idx = row_idx\n'
                  '        bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) '
                  'in ("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", "IMS":"#FFF4CC", '
                  '"SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), COLORS["white"])\n'
                  '        can_finish = not task.get("subtasks") or all_subtasks_done(task)\n'
                  '        can_complete = self.can_complete_task(task)\n'
                  '        btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", '
                  'command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else '
                  'bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, '
                  'font=zfont(self.app, 15, "bold"), state="normal" if can_complete else "disabled")\n'
                  '        btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                  '        if not can_complete:\n'
                  '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Nur zuständige Person darf '
                  'erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                  '        elif task.get("subtasks") and not can_finish:\n'
                  '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Bitte erst alle '
                  'Unteraufgaben erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                  '\n'
                  '        task_cell = tk.Frame(table, bg=bg)\n'
                  '        task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                  '        visible_subtasks = sorted([s for s in task.get("subtasks", []) if not s.get("deleted")], '
                  'key=lambda s: str(s.get("title", "")).casefold())\n'
                  '\n'
                  '        task_actions = tk.Frame(task_cell, bg=bg)\n'
                  '        task_actions.pack(side="right", padx=(6, 8), pady=3)\n'
                  '        if visible_subtasks:\n'
                  '            expand_key = self.get_expand_key(task)\n'
                  '            expanded = expand_key in self.expanded_tasks\n'
                  '            toggle_text = "Unteraufgaben einklappen v" if expanded else "Unteraufgaben ausklappen '
                  '>"\n'
                  '            tk.Button(task_actions, text=toggle_text, command=lambda key=expand_key: '
                  'self.toggle_subtasks_visibility(key), bg=bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, '
                  'cursor="hand2", font=zfont(self.app, 10, "bold")).pack(side="right", padx=(0, 6))\n'
                  '\n'
                  '        task_text = tk.Frame(task_cell, bg=bg)\n'
                  '        task_text.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=4)\n'
                  '        tk.Label(task_text, text=str(task.get("title", "")), bg=bg, fg=COLORS["text"], '
                  'font=zfont(self.app, 12), anchor="w", justify="left", wraplength=430).pack(anchor="w", fill="x", '
                  'expand=True)\n'
                  '\n'
                  '        doc_frame = tk.Frame(table, bg=bg)\n'
                  '        doc_frame.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)\n'
                  '        # v0.520: Dokumentations-Button auch bei Aufgabengruppen anzeigen.\n'
                  '        self.create_documentation_button(doc_frame, task, task.get("title", '
                  '"Aufgabe")).pack(padx=5, pady=3)\n'
                  '\n'
                  '        owner_cell = tk.Frame(table, bg=bg)\n'
                  '        owner_cell.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)\n'
                  '        tk.Label(owner_cell, text=task.get("owner"), bg=bg, fg=COLORS["text"], font=zfont(self.app, '
                  '12), padx=6, pady=6, anchor="center", justify="center").pack(side="left", fill="x", expand=True)\n'
                  '        if self.can_edit():\n'
                  '            self.create_delegate_button(owner_cell, task).pack(side="right", padx=(2, 5), pady=3)\n'
                  '\n'
                  '        values = [self.due_display_inline(task), task.get("deadline_type"), task.get("priority"), '
                  '"Ja" if task.get("recurring") else "Nein"]\n'
                  '        aligns = [("w", "left"), ("center", "center"), ("center", "center"), ("center", "center")]\n'
                  '        for offset, val in enumerate(values):\n'
                  '            anchor, justify = aligns[offset]\n'
                  '            tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, '
                  'pady=6, anchor=anchor, justify=justify).grid(row=row_idx, column=4 + offset, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '        self.create_attachment_button(table, task, lambda t=task: '
                  'self.show_attachments(t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)\n'
                  '        status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))\n'
                  '        menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: '
                  'self.set_status(t, value))\n'
                  '        menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0, state="normal" if '
                  'can_complete else "disabled")\n'
                  '        menu.grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)\n'
                  '        self._register_live_task_widgets(table, current_row_idx, task, btn, status_var, menu)\n'
                  '        if self.edit_mode and self.can_edit():\n'
                  '            action = tk.Frame(table, bg=bg); action.grid(row=row_idx, column=10, sticky="nsew", '
                  'padx=1, pady=1)\n'
                  '            tk.Button(action, text="Bearbeiten", command=lambda t=task: '
                  'self.open_task_dialog(task.get("team"), t), bg=COLORS["blue"], fg="white", bd=0, padx=6, pady=3, '
                  'font=zfont(self.app, 10, "bold")).pack(side="left", padx=2, pady=3)\n'
                  '            tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), '
                  'bg=COLORS["red"], fg="white", bd=0, padx=6, pady=3, font=zfont(self.app, 10, '
                  '"bold")).pack(side="left", padx=2, pady=3)\n'
                  '        row_idx += 1\n'
                  '\n'
                  '        if self.get_expand_key(task) in self.expanded_tasks:\n'
                  '            for sub in visible_subtasks:\n'
                  '                self.normalize_documentation_fields(sub)\n'
                  '                sub.setdefault("subtasks", [])\n'
                  '                visible_sub_subtasks = [c for c in sub.get("subtasks", []) or [] if not '
                  'c.get("deleted") and str(c.get("title", "")).strip()]\n'
                  '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                  '                sub_row_idx = row_idx\n'
                  '                sub_btn = tk.Button(table, text="✓" if sub.get("status") == STATUS_DONE else "□", '
                  'command=lambda t=task, s=sub: self.toggle_subtask(t, s), bg="#BBF7D0" if sub.get("status") == '
                  'STATUS_DONE else sub_bg, fg=COLORS["dark_green"] if sub.get("status") == STATUS_DONE else '
                  'COLORS["text"], bd=0, font=zfont(self.app, 14, "bold"), state="normal" if can_complete else '
                  '"disabled")\n'
                  '                sub_btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                  '                sub_task_cell = tk.Frame(table, bg=sub_bg)\n'
                  '                sub_task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                  '                sub_action = tk.Frame(sub_task_cell, bg=sub_bg)\n'
                  '                sub_action.pack(side="right", padx=(6, 8), pady=3)\n'
                  '                if visible_sub_subtasks:\n'
                  '                    sub_expand_key = '
                  'f"subsub|{task.get(\'id\',\'\')}|{sub.get(\'id\',\'\')}|{sub.get(\'title\',\'\')}"\n'
                  '                    sub_expanded = sub_expand_key in self.expanded_tasks\n'
                  '                    sub_toggle_text = "Unter-Unteraufgaben einklappen v" if sub_expanded else '
                  '"Unter-Unteraufgaben ausklappen >"\n'
                  '                    tk.Button(sub_action, text=sub_toggle_text, command=lambda key=sub_expand_key: '
                  'self.toggle_subtasks_visibility(key), bg=sub_bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, '
                  'cursor="hand2", font=zfont(self.app, 10, "bold")).pack(side="right", padx=(0, 4))\n'
                  '                tk.Label(sub_task_cell, text="↳ " + sub.get("title", ""), bg=sub_bg, '
                  'fg=COLORS["text"], font=zfont(self.app, 12), padx=18, pady=5, anchor="w", '
                  'justify="left").pack(side="left", fill="both", expand=True)\n'
                  '                sub_doc = tk.Frame(table, bg=sub_bg); sub_doc.grid(row=row_idx, column=2, '
                  'sticky="nsew", padx=1, pady=1)\n'
                  '                self.create_documentation_button(sub_doc, sub, sub.get("title", "Unteraufgabe"), '
                  'parent_task=task).pack(padx=5, pady=2)\n'
                  '                sub_owner = tk.Frame(table, bg=sub_bg); sub_owner.grid(row=row_idx, column=3, '
                  'sticky="nsew", padx=1, pady=1)\n'
                  '                tk.Label(sub_owner, text=sub.get("owner", task.get("owner", "")), bg=sub_bg, '
                  'fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=5, anchor="center", '
                  'justify="center").pack(side="left", fill="x", expand=True)\n'
                  '                if self.can_edit():\n'
                  '                    self.create_delegate_button(sub_owner, sub, '
                  'parent_task=task).pack(side="right", padx=(2, 5), pady=3)\n'
                  '                for col in (4, 5, 6, 7):\n'
                  '                    tk.Label(table, text="", bg=sub_bg, fg=COLORS["text"], font=zfont(self.app, '
                  '12), padx=6, pady=5).grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)\n'
                  '                self.create_attachment_button(table, sub, lambda s=sub, t=task: '
                  'self.show_attachments(s, parent_task=t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '                tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=9, sticky="nsew", '
                  'padx=1, pady=1)\n'
                  '                if self.edit_mode and self.can_edit():\n'
                  '                    tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=10, sticky="nsew", '
                  'padx=1, pady=1)\n'
                  '                self._register_live_subtask_widgets(table, sub_row_idx, task, sub, sub_btn)\n'
                  '                row_idx += 1\n'
                  '                if visible_sub_subtasks and sub_expand_key in self.expanded_tasks:\n'
                  '                    for child in visible_sub_subtasks:\n'
                  '                        child_bg = "#E0F2FE" if child.get("status") == STATUS_DONE else "#F0F9FF"\n'
                  '                        child_btn = tk.Button(table, text="✓" if child.get("status") == STATUS_DONE '
                  'else "□", command=lambda t=task, s=sub, c=child: self.toggle_sub_subtask(t, s, c), bg="#BAE6FD" if '
                  'child.get("status") == STATUS_DONE else child_bg, fg=COLORS["dark_green"] if child.get("status") == '
                  'STATUS_DONE else COLORS["text"], bd=0, font=zfont(self.app, 13, "bold"), state="normal" if '
                  'can_complete else "disabled")\n'
                  '                        child_btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                  '                        tk.Label(table, text="↳ ↳ " + child.get("title", ""), bg=child_bg, '
                  'fg=COLORS["text"], font=zfont(self.app, 11), padx=34, pady=4, anchor="w", '
                  'justify="left").grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                  '                        for col in (2, 4, 5, 6, 7, 8, 9):\n'
                  '                            tk.Label(table, text="", bg=child_bg, fg=COLORS["text"], '
                  'font=zfont(self.app, 11), padx=6, pady=4).grid(row=row_idx, column=col, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '                        owner_text = child.get("owner") or sub.get("owner") or task.get("owner", '
                  '"")\n'
                  '                        tk.Label(table, text=owner_text, bg=child_bg, fg=COLORS["text2"], '
                  'font=zfont(self.app, 11), padx=6, pady=4, anchor="center", justify="center").grid(row=row_idx, '
                  'column=3, sticky="nsew", padx=1, pady=1)\n'
                  '                        if self.edit_mode and self.can_edit():\n'
                  '                            tk.Label(table, text="", bg=child_bg).grid(row=row_idx, column=10, '
                  'sticky="nsew", padx=1, pady=1)\n'
                  '                        row_idx += 1\n'
                  '        return row_idx\n'
                  '\n'
                  '    def find_task(self, task_id):\n'
                  '        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not '
                  't.get("deleted")), None)\n'
                  '\n'
                  '    def toggle_done(self, task):\n'
                  '            if not self.require_unlocked("Diese Änderung"): return\n'
                  '            real = self.find_task(task["id"])\n'
                  '            if not real: return\n'
                  '            if not self.can_complete_task(real): messagebox.showwarning("Monatsabschluss", "Du '
                  'kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); '
                  'self.render_team_detail(real.get("team")); return\n'
                  '            if real.get("subtasks") and not all_subtasks_done(real): self.show_tooltip(self.root, '
                  '"Bitte erst alle Unteraufgaben erledigen."); self.root.after(1600, self.hide_tooltip); return\n'
                  '            if real.get("status") == STATUS_DONE: real.update({"status": STATUS_OPEN, "done_at": '
                  'None, "done_by": None})\n'
                  '            else:\n'
                  '                if real.get("deadline_type") == "gesetzlich" and not '
                  'messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                  'markieren?"): return\n'
                  '                real.update({"status": STATUS_DONE, "done_at": '
                  'datetime.now().isoformat(timespec="seconds"), "done_by": getattr(self.app, "current_user_display", '
                  '"") or ""})\n'
                  '            self.save(); self.render_team_detail(real["team"])\n'
                  '\n'
                  '    def set_status(self, task, status):\n'
                  '            if not self.require_unlocked("Diese Änderung"): return\n'
                  '            real = self.find_task(task["id"])\n'
                  '            if not real: return\n'
                  '            if status == STATUS_DONE and not self.can_complete_task(real): '
                  'messagebox.showwarning("Monatsabschluss", "Du kannst nur Aufgaben als erledigt markieren, für die '
                  'du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return\n'
                  '            if status == STATUS_DONE and real.get("subtasks") and not all_subtasks_done(real): '
                  'messagebox.showinfo("Monatsabschluss", "Bitte erst alle Unteraufgaben erledigen."); '
                  'self.render_team_detail(real["team"]); return\n'
                  '            if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not '
                  'messagebox.askyesno("Monatsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                  'markieren?"): self.render_team_detail(real["team"]); return\n'
                  '            real["status"] = status; real["done_at"] = datetime.now().isoformat(timespec="seconds") '
                  'if status == STATUS_DONE else None; real["done_by"] = getattr(self.app, "current_user_display", "") '
                  'or "" if status == STATUS_DONE else None\n'
                  '            self.save(); self.render_team_detail(real["team"])\n'
                  '\n'
                  '    def toggle_subtask(self, task, subtask):\n'
                  '            if not self.require_unlocked("Diese Änderung"): return\n'
                  '            real = self.find_task(task["id"])\n'
                  '            if not real: return\n'
                  '            if not self.can_complete_task(real): messagebox.showwarning("Monatsabschluss", "Du '
                  'kannst nur Unteraufgaben als erledigt markieren, wenn du selbst als zuständig eingetragen bist."); '
                  'self.render_team_detail(real.get("team")); return\n'
                  '            for sub in real.get("subtasks", []):\n'
                  '                if sub.get("id") == subtask.get("id"): sub["status"] = STATUS_OPEN if '
                  'sub.get("status") == STATUS_DONE else STATUS_DONE; break\n'
                  '            sync_parent_status_from_subtasks(real); self.save(); '
                  'self.render_team_detail(real["team"])\n'
                  '\n'
                  '    def next_task_index(self, team):\n'
                  '        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1\n'
                  '\n'
                  '    def task_to_catalog_entry(self, task):\n'
                  '        catalog_id = task.get("catalog_id") or '
                  'f"rec_{datetime.now().strftime(\'%Y%m%d%H%M%S%f\')}"; task["catalog_id"] = catalog_id\n'
                  '        return {k: task.get(k) for k in ["catalog_id", "team", "title", "owner", "owner_user_key", '
                  '"due_date", "due_mode", "due_day", "due_workday", "due_fixed_date", "deadline_type", "priority", '
                  '"required", "recurring"]} | {"start_period": self.period, "recurring": True}\n'
                  '\n'
                  '    def upsert_catalog_entry(self, task):\n'
                  '        catalog = load_catalog(); entry = self.task_to_catalog_entry(task); tasks = '
                  'catalog.setdefault("tasks", [])\n'
                  '        for idx, existing in enumerate(tasks):\n'
                  '            if existing.get("catalog_id") == entry["catalog_id"]: entry["start_period"] = '
                  'existing.get("start_period", self.period); tasks[idx] = entry; break\n'
                  '        else: tasks.append(entry)\n'
                  '        save_catalog(catalog); return entry["catalog_id"]\n'
                  '\n'
                  '    def remove_catalog_entry(self, catalog_id):\n'
                  '        if not catalog_id: return\n'
                  '        catalog = load_catalog(); catalog["tasks"] = [t for t in catalog.get("tasks", []) if '
                  't.get("catalog_id") != catalog_id]; save_catalog(catalog)\n'
                  '\n'
                  '    def propagate_recurring_to_future_periods(self, catalog_id):\n'
                  '        if not catalog_id: return\n'
                  '        for period in list_periods():\n'
                  '            if period > self.period: apply_catalog_to_period(period)\n'
                  '\n'
                  '    def open_task_dialog(self, team, task=None):\n'
                  '        if not self.can_edit(): return\n'
                  '        is_new = task is None\n'
                  '        win = tk.Toplevel(self.root); win.title("Aufgabe anlegen" if is_new else "Aufgabe '
                  'bearbeiten"); win.configure(bg=COLORS["bg"]); win.geometry("760x590"); win.transient(self.root); '
                  'win.grab_set()\n'
                  '        data = dict(task) if task else {"title": "", "owner": team, "owner_user_key": "", '
                  '"deadline_type": "intern", "priority": "normal", "due_mode": DUE_CUTOFF, "due_day": 1, '
                  '"due_workday": 1, "due_fixed_date": "", "recurring": False, "subtasks": [], "booking_circle": '
                  '"IDE"}\n'
                  '        normalize_task(data, self.data, self.period)\n'
                  '        popup_body_container = tk.Frame(win, bg=COLORS["bg"]); '
                  'popup_body_container.pack(fill="both", expand=True, padx=0, pady=0)\n'
                  '        popup_body_canvas = tk.Canvas(popup_body_container, bg=COLORS["bg"], highlightthickness=0, '
                  'bd=0)\n'
                  '        popup_body_scrollbar = tk.Scrollbar(popup_body_container, orient="vertical", '
                  'command=popup_body_canvas.yview)\n'
                  '        popup_body = tk.Frame(popup_body_canvas, bg=COLORS["bg"])\n'
                  '        popup_body_window = popup_body_canvas.create_window((0, 0), window=popup_body, '
                  'anchor="nw")\n'
                  '        def _popup_update_scrollregion(_event=None):\n'
                  '            try:\n'
                  '                popup_body_canvas.itemconfigure(popup_body_window, width=max(1, '
                  'popup_body_canvas.winfo_width() - 2))\n'
                  '                popup_body_canvas.configure(scrollregion=popup_body_canvas.bbox("all"))\n'
                  '            except Exception:\n'
                  '                pass\n'
                  '        popup_body.bind("<Configure>", _popup_update_scrollregion)\n'
                  '        popup_body_canvas.bind("<Configure>", _popup_update_scrollregion)\n'
                  '        popup_body_canvas.configure(yscrollcommand=popup_body_scrollbar.set)\n'
                  '        popup_body_canvas.pack(side="left", fill="both", expand=True, padx=14, pady=14)\n'
                  '        popup_body_scrollbar.pack(side="right", fill="y", pady=14)\n'
                  '        def _popup_mousewheel(event):\n'
                  '            try:\n'
                  '                if getattr(event, "num", None) == 4:\n'
                  '                    popup_body_canvas.yview_scroll(-3, "units")\n'
                  '                elif getattr(event, "num", None) == 5:\n'
                  '                    popup_body_canvas.yview_scroll(3, "units")\n'
                  '                else:\n'
                  '                    delta = int(getattr(event, "delta", 0) or 0)\n'
                  '                    popup_body_canvas.yview_scroll(int(-delta / 120), "units")\n'
                  '                return "break"\n'
                  '            except Exception:\n'
                  '                return "break"\n'
                  '        def _popup_bind_mousewheel(widget):\n'
                  '            try:\n'
                  '                widget.bind("<MouseWheel>", _popup_mousewheel, add=False)\n'
                  '                widget.bind("<Button-4>", _popup_mousewheel, add=False)\n'
                  '                widget.bind("<Button-5>", _popup_mousewheel, add=False)\n'
                  '                for child in widget.winfo_children():\n'
                  '                    _popup_bind_mousewheel(child)\n'
                  '            except Exception:\n'
                  '                pass\n'
                  '        notebook = ttk.Notebook(popup_body); notebook.pack(fill="both", expand=True, padx=0, '
                  'pady=0)\n'
                  '        form = tk.Frame(notebook, bg=COLORS["bg"]); subtab = tk.Frame(notebook, bg=COLORS["bg"])\n'
                  '        notebook.add(form, text="Aufgabe"); notebook.add(subtab, text="Unteraufgaben")\n'
                  '        title_var = tk.StringVar(value=data.get("title", "")); deadline_var = '
                  'tk.StringVar(value=data.get("deadline_type", "intern") if data.get("deadline_type") in '
                  'DEADLINE_TYPES else "intern"); priority_var = tk.StringVar(value=data.get("priority", "normal")); '
                  'recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))\n'
                  '        due_frequency_var = tk.StringVar(value=str(data.get("due_frequency") or ("Monat" if '
                  'CLOSING_SCOPE == "M" else "Quartal" if CLOSING_SCOPE == "Q" else "Jahr")))\n'
                  '        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", DUE_CUTOFF), '
                  '"Abschluss-Stichtag")); due_day_var = tk.StringVar(value=str(data.get("due_day") or 1)); '
                  'due_workday_var = tk.StringVar(value=str(data.get("due_workday") or 1)); due_fixed_var = '
                  'tk.StringVar(value=format_date_de(data.get("due_fixed_date") or data.get("due_date") or "")); '
                  'calculated_var = tk.StringVar(value="")\n'
                  '        users = self.user_choices(); user_labels = {label: key for key, label in users}; '
                  'current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, '
                  'label in users if key == current_owner_key), data.get("owner", team)); owner_var = '
                  'tk.StringVar(value=current_owner_label)\n'
                  '        booking_circle_var = tk.StringVar(value=data.get("booking_circle", "IDE") if '
                  'data.get("booking_circle", "IDE") in ("IDE", "IDG", "IMS", "SPI", "IHB") else "IDE")\n'
                  '        widgets = [("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), '
                  '("Buchungskreis", tk.OptionMenu(form, booking_circle_var, "IDE", "IDG", "IMS", "SPI", "IHB")), '
                  '("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fälligkeitsturnus", tk.OptionMenu(form, due_frequency_var, "Monat", "Quartal", "Jahr")), ("Fristart", '
                  'tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, '
                  'priority_var, *PRIORITIES)), ("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, '
                  '*DUE_LABEL_TO_VALUE.keys()))]\n'
                  '        for row, (label, widget) in enumerate(widgets):\n'
                  '            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 12, '
                  '"bold")).grid(row=row, column=0, sticky="w", pady=7, padx=8); widget.grid(row=row, column=1, '
                  'sticky="w", pady=7)\n'
                  '            try:\n'
                  '                widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0, font=zfont(self.app, 12, "bold"))\n'
                  '                if str(widget.winfo_class()).lower() == "menubutton":\n'
                  '                    widget.config(width=24, padx=8, pady=4)\n'
                  '                    try: widget["menu"].config(font=zfont(self.app, 12))\n'
                  '                    except Exception: pass\n'
                  '            except Exception: pass\n'
                  '        day_label = tk.Label(form, text="Tag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")); day_entry = tk.Entry(form, textvariable=due_day_var, width=8)\n'
                  '        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")); workday_entry = tk.Entry(form, textvariable=due_workday_var, '
                  'width=8)\n'
                  '        fixed_label = tk.Label(form, text="Konkretes Datum (TT.MM.JJJJ)", bg=COLORS["bg"], '
                  'fg=COLORS["text"], font=zfont(self.app, 12, "bold")); fixed_entry = tk.Entry(form, '
                  'textvariable=due_fixed_var, width=14)\n'
                  '        for r, lab, ent in [(7, day_label, day_entry), (8, workday_label, workday_entry), (9, '
                  'fixed_label, fixed_entry)]: lab.grid(row=r, column=0, sticky="w", pady=7, padx=8); ent.grid(row=r, '
                  'column=1, sticky="w", pady=7); ent.config(bg="white", fg=COLORS["text"], relief="solid", bd=1, '
                  'highlightthickness=0)\n'
                  '        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], '
                  'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), activebackground=COLORS["bg"]).grid(row=9, '
                  'column=1, sticky="w", pady=7)\n'
                  '        # Fälligkeitsturnus wird ab v0.541 zwischen Zuständig und Fristart angezeigt.\n'
                  '        # Doppeltes Turnus-Dropdown entfernt.\n'
                  '        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], '
                  'font=zfont(self.app, 12, "bold")).grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 10), padx=8)\n'
                  '        def refresh_due_input_visibility(*_):\n'
                  '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF)\n'
                  '            for lab, ent in [(day_label, day_entry), (workday_label, workday_entry), (fixed_label, '
                  'fixed_entry)]: lab.grid_remove(); ent.grid_remove()\n'
                  '            if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): '
                  'day_label.grid(); day_entry.grid()\n'
                  '            elif mode == DUE_WORKDAY_NEXT: workday_label.grid(); workday_entry.grid()\n'
                  '            elif mode == DUE_FIXED: fixed_label.grid(); fixed_entry.grid()\n'
                  '            preview = {"due_mode": mode, "due_day": due_day_var.get().strip() or 1, "due_workday": '
                  'due_workday_var.get().strip() or 1, "due_fixed_date": due_fixed_var.get().strip()}\n'
                  '            calculated_var.set("Berechnetes Fälligkeitsdatum: " + '
                  '(format_date_de(resolve_due_date(preview, self.data, self.period)) or "-"))\n'
                  '        for var in (due_mode_var, due_day_var, due_workday_var, due_fixed_var): '
                  'var.trace_add("write", refresh_due_input_visibility)\n'
                  '        refresh_due_input_visibility()\n'
                  '        subtasks_work = [dict(s) for s in data.get("subtasks", []) if not s.get("deleted")]\n'
                  '        sub_list = tk.Frame(subtab, bg=COLORS["bg"]); sub_list.pack(fill="both", expand=True, '
                  'padx=10, pady=10); new_sub_var = tk.StringVar()\n'
                  '        def open_sub_subtask_popup(parent_index):\n'
                  '            if parent_index < 0 or parent_index >= len(subtasks_work):\n'
                  '                return\n'
                  '            parent_sub = subtasks_work[parent_index]\n'
                  '            parent_sub.setdefault("subtasks", [])\n'
                  '            win2 = tk.Toplevel(win)\n'
                  '            win2.title("Unter-Unteraufgaben erstellen")\n'
                  '            win2.configure(bg=COLORS["bg"])\n'
                  '            win2.geometry("760x520")\n'
                  '            win2.transient(win)\n'
                  '            win2.grab_set()\n'
                  '            tk.Label(win2, text="Unter-Unteraufgaben erstellen", bg=COLORS["bg"], '
                  'fg=COLORS["text"], font=zfont(self.app, 18, "bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                  '            tk.Label(win2, text="Unteraufgabe: " + str(parent_sub.get("title", "")), '
                  'bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 13), wraplength=710, '
                  'justify="left").pack(anchor="w", padx=18, pady=(0, 12))\n'
                  '            list_box = tk.Frame(win2, bg=COLORS["white"], bd=1, relief="solid")\n'
                  '            list_box.pack(fill="both", expand=True, padx=18, pady=(0, 10))\n'
                  '            new_child_var = tk.StringVar()\n'
                  '\n'
                  '            def refresh_children():\n'
                  '                for child_widget in list_box.winfo_children():\n'
                  '                    child_widget.destroy()\n'
                  '                tk.Label(list_box, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=0, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '                tk.Label(list_box, text="Unter-Unteraufgabe", bg=COLORS["header"], '
                  'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=1, '
                  'sticky="nsew", padx=1, pady=1)\n'
                  '                tk.Label(list_box, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=2, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '                list_box.grid_columnconfigure(1, weight=1)\n'
                  '                children = parent_sub.setdefault("subtasks", [])\n'
                  '                if not children:\n'
                  '                    tk.Label(list_box, text="Noch keine Unter-Unteraufgaben vorhanden.", '
                  'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 12), padx=10, pady=10, '
                  'anchor="w").grid(row=1, column=0, columnspan=3, sticky="ew")\n'
                  '                for cidx, child in enumerate(children, start=1):\n'
                  '                    child.setdefault("id", '
                  'f"subsub_{cidx:02d}_{datetime.now().strftime(\'%H%M%S%f\')}")\n'
                  '                    child.setdefault("status", STATUS_OPEN)\n'
                  '                    cvar = tk.StringVar(value=child.get("title", ""))\n'
                  '                    cstatus = tk.BooleanVar(value=child.get("status") == STATUS_DONE)\n'
                  '                    def _write_title(*_args, i=cidx-1, v=cvar):\n'
                  '                        parent_sub.setdefault("subtasks", [])[i]["title"] = v.get()\n'
                  '                    cvar.trace_add("write", _write_title)\n'
                  '                    def _write_status(i=cidx-1, v=cstatus):\n'
                  '                        parent_sub.setdefault("subtasks", [])[i]["status"] = STATUS_DONE if v.get() '
                  'else STATUS_OPEN\n'
                  '                    tk.Checkbutton(list_box, variable=cstatus, command=_write_status, '
                  'bg=COLORS["white"], activebackground=COLORS["white"]).grid(row=cidx, column=0, sticky="nsew", '
                  'padx=1, pady=1)\n'
                  '                    tk.Entry(list_box, textvariable=cvar, bg="white", fg=COLORS["text"], '
                  'relief="solid", bd=1, font=zfont(self.app, 13), width=54).grid(row=cidx, column=1, sticky="ew", '
                  'padx=6, pady=5, ipady=4)\n'
                  '                    tk.Button(list_box, text="Löschen", command=lambda i=cidx-1: delete_child(i), '
                  'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=7, font=zfont(self.app, 12, '
                  '"bold")).grid(row=cidx, column=2, sticky="w", padx=6, pady=5)\n'
                  '\n'
                  '            def add_child():\n'
                  '                title = new_child_var.get().strip()\n'
                  '                if not title:\n'
                  '                    messagebox.showwarning("Unter-Unteraufgaben", "Bitte zuerst einen Namen für die '
                  'Unter-Unteraufgabe eingeben.", parent=win2)\n'
                  '                    return\n'
                  '                parent_sub.setdefault("subtasks", []).append({"id": '
                  'f"subsub_{len(parent_sub.get(\'subtasks\', []))+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", '
                  '"title": title, "status": STATUS_OPEN})\n'
                  '                new_child_var.set("")\n'
                  '                refresh_children()\n'
                  '\n'
                  '            def delete_child(child_index):\n'
                  '                try:\n'
                  '                    parent_sub.setdefault("subtasks", []).pop(child_index)\n'
                  '                except Exception:\n'
                  '                    pass\n'
                  '                refresh_children()\n'
                  '\n'
                  '            add_box = tk.Frame(win2, bg=COLORS["bg"])\n'
                  '            add_box.pack(fill="x", padx=18, pady=(0, 10))\n'
                  '            tk.Label(add_box, text="Neue Unter-Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")).pack(anchor="w")\n'
                  '            entry_row = tk.Frame(add_box, bg=COLORS["bg"])\n'
                  '            entry_row.pack(fill="x", pady=(5, 0))\n'
                  '            tk.Entry(entry_row, textvariable=new_child_var, bg="white", fg=COLORS["text"], '
                  'relief="solid", bd=1, font=zfont(self.app, 13), width=58).pack(side="left", fill="x", expand=True, '
                  'ipady=5)\n'
                  '            tk.Button(entry_row, text="Hinzufügen", command=add_child, bg=COLORS["blue"], '
                  'fg="white", bd=0, padx=16, pady=9, font=zfont(self.app, 12, "bold")).pack(side="left", padx=(10, '
                  '0))\n'
                  '            footer2 = tk.Frame(win2, bg=COLORS["bg"])\n'
                  '            footer2.pack(fill="x", padx=18, pady=(0, 14))\n'
                  '            def close_child_popup():\n'
                  '                refresh_subtasks_editor()\n'
                  '                win2.destroy()\n'
                  '            tk.Button(footer2, text="Übernehmen und schließen", command=close_child_popup, '
                  'bg=COLORS["blue"], fg="white", bd=0, padx=18, pady=9, font=zfont(self.app, 12, '
                  '"bold")).pack(side="right")\n'
                  '            tk.Button(footer2, text="Abbrechen", command=win2.destroy, bg=COLORS["line"], '
                  'fg=COLORS["text"], bd=0, padx=18, pady=9, font=zfont(self.app, 12, "bold")).pack(side="right", '
                  'padx=(0, 10))\n'
                  '            refresh_children()\n'
                  '\n'
                  '        def refresh_subtasks_editor():\n'
                  '            for child in sub_list.winfo_children(): child.destroy()\n'
                  '            tk.Label(sub_list, text="Unteraufgaben", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 15, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))\n'
                  '            tk.Label(sub_list, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=0, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '            tk.Label(sub_list, text="Unteraufgabe", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=1, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '            tk.Label(sub_list, text="Unter-Unteraufgaben", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=2, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '            tk.Label(sub_list, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=3, sticky="nsew", padx=1, '
                  'pady=1)\n'
                  '            sub_list.grid_columnconfigure(1, weight=1)\n'
                  '            row = 2\n'
                  '            for idx, sub in enumerate(subtasks_work):\n'
                  '                sub.setdefault("subtasks", [])\n'
                  '                var = tk.StringVar(value=sub.get("title", "")); status_var = '
                  'tk.BooleanVar(value=sub.get("status") == STATUS_DONE)\n'
                  '                var.trace_add("write", lambda *_args, i=idx, v=var: '
                  'subtasks_work[i].update({"title": v.get()}))\n'
                  '                tk.Checkbutton(sub_list, variable=status_var, command=lambda i=idx, v=status_var: '
                  'subtasks_work[i].update({"status": STATUS_DONE if v.get() else STATUS_OPEN}), bg=COLORS["bg"], '
                  'activebackground=COLORS["bg"]).grid(row=row, column=0, sticky="nsew", pady=4, padx=1)\n'
                  '                tk.Entry(sub_list, textvariable=var, width=52, bg="white", fg=COLORS["text"], '
                  'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=row, column=1, sticky="ew", pady=4, '
                  'padx=6, ipady=4)\n'
                  '                count = len([c for c in sub.get("subtasks", []) or [] if str(c.get("title", '
                  '"")).strip()])\n'
                  '                tk.Button(sub_list, text=f"Unter-Unteraufgaben erstellen ({count})", command=lambda '
                  'i=idx: open_sub_subtask_popup(i), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=8, '
                  'font=zfont(self.app, 12, "bold")).grid(row=row, column=2, sticky="w", pady=4, padx=6)\n'
                  '                tk.Button(sub_list, text="Löschen", command=lambda i=idx: delete_subtask(i), '
                  'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=8, font=zfont(self.app, 12, '
                  '"bold")).grid(row=row, column=3, sticky="w", pady=4, padx=6)\n'
                  '                row += 1\n'
                  '            add_row = row + 1\n'
                  '            tk.Label(sub_list, text="Neue Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")).grid(row=add_row, column=0, columnspan=2, sticky="w", pady=(14, '
                  '4), padx=6)\n'
                  '            tk.Entry(sub_list, textvariable=new_sub_var, width=52, bg="white", fg=COLORS["text"], '
                  'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=add_row+1, column=1, sticky="ew", pady=(2, '
                  '4), padx=6, ipady=4)\n'
                  '            tk.Button(sub_list, text="Unteraufgabe hinzufügen", command=add_subtask, '
                  'bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=9, font=zfont(self.app, 12, '
                  '"bold")).grid(row=add_row+1, column=2, sticky="w", pady=(2, 4), padx=6)\n'
                  '\n'
                  '        def render_subtasks_editor():\n'
                  '            refresh_subtasks_editor()\n'
                  '\n'
                  '        def add_subtask():\n'
                  '            title = new_sub_var.get().strip()\n'
                  '            if title: subtasks_work.append({"id": '
                  'f"sub_{len(subtasks_work)+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", "title": title, '
                  '"status": STATUS_OPEN}); new_sub_var.set(""); render_subtasks_editor()\n'
                  '        def delete_subtask(idx):\n'
                  '            if 0 <= idx < len(subtasks_work): subtasks_work.pop(idx); render_subtasks_editor()\n'
                  '        render_subtasks_editor()\n'
                  '        _popup_bind_mousewheel(win)\n'
                  '        _popup_update_scrollregion()\n'
                  '        if False and not is_new:\n'
                  '            tk.Button(form, text="Aufgabe mit Unteraufgaben in Quartalsabschluss übernehmen", '
                  'command=lambda: self.open_transfer_dialog(task), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                  'pady=7).grid(row=10, column=1, sticky="w", pady=(10, 4))\n'
                  '        def save_dialog():\n'
                  '            title_value = title_var.get().strip()\n'
                  '            if not title_value: messagebox.showwarning("Monatsabschluss", "Bitte einen '
                  'Aufgabennamen eingeben."); return\n'
                  '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF); due_day = None; '
                  'due_workday = None; due_fixed = ""\n'
                  '            try:\n'
                  '                if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): due_day = '
                  'int(due_day_var.get().strip()); assert due_day > 0\n'
                  '                elif mode == DUE_WORKDAY_NEXT: due_workday = int(due_workday_var.get().strip()); '
                  'assert due_workday > 0\n'
                  '                elif mode == DUE_FIXED:\n'
                  '                    fixed_date = parse_date(due_fixed_var.get().strip()); assert fixed_date; '
                  'due_fixed = fixed_date.strftime("%Y-%m-%d")\n'
                  '            except Exception:\n'
                  '                messagebox.showwarning("Monatsabschluss", "Bitte gültige Werte zur Fälligkeit '
                  'eingeben."); return\n'
                  '            owner_label = owner_var.get(); owner_key = user_labels.get(owner_label, ""); owner_text '
                  '= owner_label if owner_key else team\n'
                  '            payload = {"title": title_value, "booking_circle": booking_circle_var.get(), "owner": '
                  'owner_text, "owner_user_key": owner_key, "due_mode": mode, "due_day": due_day, "due_workday": '
                  'due_workday, "due_fixed_date": due_fixed, "deadline_type": deadline_var.get(), "priority": '
                  'priority_var.get(), "recurring": bool(recurring_var.get()), "due_frequency": '
                  'due_frequency_var.get(), "subtasks": [s for s in subtasks_work if s.get("title", "").strip()]}\n'
                  '            payload["due_date"] = resolve_due_date(payload, self.data, self.period)\n'
                  '            if is_new:\n'
                  '                real = {"id": make_task_id(team, self.next_task_index(team)), "team": team, '
                  '"required": True, "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, '
                  '"done_by": None, "catalog_id": "", **payload}; self.data.setdefault("tasks", []).append(real)\n'
                  '            else:\n'
                  '                real = self.find_task(task["id"])\n'
                  '                if not real: return\n'
                  '                real.update(payload)\n'
                  '            sync_parent_status_from_subtasks(real)\n'
                  '            if real.get("recurring"):\n'
                  '                catalog_id = self.upsert_catalog_entry(real); real["catalog_id"] = catalog_id; '
                  'self.propagate_recurring_to_future_periods(catalog_id)\n'
                  '            else:\n'
                  '                if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))\n'
                  '                real["catalog_id"] = ""\n'
                  '            self.save(); win.destroy(); self.reload(); self.render_team_detail(team)\n'
                  '        buttons = tk.Frame(win, bg=COLORS["bg"]); buttons.pack(side="bottom", fill="x", pady=(0, '
                  '12), padx=14)\n'
                  '        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", '
                  'bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", padx=6)\n'
                  '        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                  'fg=COLORS["text"], bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", '
                  'padx=6)\n'
                  '        _popup_bind_mousewheel(win)\n'
                  '        _popup_update_scrollregion()\n'
                  '\n'
                  '    def delete_task(self, task):\n'
                  '            if not self.require_unlocked("Diese Änderung"): return\n'
                  '            idx = self.find_task_index_exact(task)\n'
                  '            if idx is None:\n'
                  '                messagebox.showerror("Aufgabe löschen", "Die ausgewählte Aufgabe konnte nicht '
                  'eindeutig identifiziert werden. Es wurde nichts gelöscht.")\n'
                  '                return\n'
                  '            real = self.data.get("tasks", [])[idx]\n'
                  '            scope = self.ask_delete_scope(real)\n'
                  '            if not scope:\n'
                  '                return\n'
                  '            task_key = self.task_match_key(real)\n'
                  '            team = real.get("team")\n'
                  '            title = real.get("title", "")\n'
                  '            self.data["tasks"].pop(idx)\n'
                  '            if scope == "following" and real.get("catalog_id"):\n'
                  '                self.remove_catalog_entry(real.get("catalog_id"))\n'
                  '            self.save()\n'
                  '            removed_future = 0\n'
                  '            ambiguous_future = 0\n'
                  '            if scope == "following":\n'
                  '                removed_future, ambiguous_future = self.delete_from_following_periods(task_key)\n'
                  '            info = f"Aufgabe wurde gelöscht:\\n\\n{title}"\n'
                  '            if scope == "following":\n'
                  '                info += f"\\n\\nEntfernt aus Folgezeiträumen: {removed_future}"\n'
                  '                if ambiguous_future:\n'
                  '                    info += f"\\nNicht eindeutig erkannte Folgezeiträume übersprungen: '
                  '{ambiguous_future}"\n'
                  '            messagebox.showinfo("Aufgabe löschen", info)\n'
                  '            self.reload()\n'
                  '            self.render_team_detail(team) if team else self.render_dashboard()\n'
                  '\n'
                  '    def clone_task_for_period(self, task, target_period, index):\n'
                  '        data_stub = {"closing_cutoff_date": default_cutoff_date(target_period)}\n'
                  '        clone = {"id": make_task_id(task.get("team", "Team"), index), "team": task.get("team"), '
                  '"title": task.get("title"), "owner": task.get("owner", task.get("team")), "owner_user_key": '
                  'task.get("owner_user_key", ""), "due_mode": task.get("due_mode", DUE_CUTOFF), "due_day": '
                  'task.get("due_day"), "due_workday": task.get("due_workday"), "due_fixed_date": '
                  'task.get("due_fixed_date", ""), "deadline_type": task.get("deadline_type", "keine"), "priority": '
                  'task.get("priority", "normal"), "required": task.get("required", True), "recurring": '
                  'task.get("recurring", False), "catalog_id": task.get("catalog_id", ""), "status": STATUS_OPEN, '
                  '"attachments": [], "comments": [], "subtasks": [dict(s, status=STATUS_OPEN) for s in '
                  'task.get("subtasks", []) if not s.get("deleted")], "done_at": None, "done_by": None}\n'
                  '        clone["due_date"] = resolve_due_date(clone, data_stub, target_period); return clone\n'
                  '\n'
                  '    def apply_current_tasks_to_all_periods(self):\n'
                  '            if not self.require_unlocked("Zuweisung an Perioden ist nicht möglich"): return\n'
                  '            if not self.can_edit(): return\n'
                  '            if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus '
                  '{period_label(self.period)} wird auf alle vorhandenen Perioden übertragen.\\n\\nStatus, Anlagen, '
                  'Kommentare und Erledigt-Infos werden in den Zielperioden zurückgesetzt.\\n\\nFortfahren?"): return\n'
                  '            source_tasks = [t for t in self.tasks()]\n'
                  '            for target in list_periods():\n'
                  '                grouped_index = {}; cloned = []\n'
                  '                for task in source_tasks:\n'
                  '                    team = task.get("team", "Team"); grouped_index[team] = grouped_index.get(team, '
                  '0) + 1; cloned.append(self.clone_task_for_period(task, target, grouped_index[team]))\n'
                  '                data = load_period(target); data["tasks"] = cloned; data["updated_from_period"] = '
                  'self.period; data["updated_at"] = datetime.now().isoformat(timespec="seconds"); save_period(target, '
                  'data)\n'
                  '            self.reload(); messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben wurden allen '
                  'vorhandenen Perioden zugewiesen."); self.render_team_detail(self.selected_team) if '
                  'self.selected_team else self.render_dashboard()\n'
                  '\n'
                  '    def show_attachments(self, task, parent_task=None):\n'
                  '        self.normalize_documentation_fields(task)\n'
                  '        item_title = task.get("title", "Aufgabe")\n'
                  '        win = tk.Toplevel(self.root)\n'
                  '        win.title(f"Anlagen - {item_title}")\n'
                  '        win.configure(bg=COLORS["bg"])\n'
                  '        win.geometry("860x560")\n'
                  '        win.transient(self.root)\n'
                  '        win.grab_set()\n'
                  '\n'
                  '        tk.Label(win, text=item_title, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, 16, '
                  '"bold")).pack(anchor="w", padx=16, pady=(14, 4))\n'
                  '        tk.Label(win, text="Anlagen dienen zur Hinterlegung ausgearbeiteter Ergebnisse und '
                  'Kommentare zur Bearbeitung. Dokumentationen/Leitfäden bitte in der Spalte Dokumentation pflegen.", '
                  'bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=820, '
                  'justify="left").pack(anchor="w", padx=16, pady=(0, 8))\n'
                  '\n'
                  '        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                  '        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))\n'
                  '        list_frame.grid_columnconfigure(0, weight=1)\n'
                  '        list_frame.grid_columnconfigure(3, weight=2)\n'
                  '\n'
                  '        def refresh():\n'
                  '            for child in list_frame.winfo_children():\n'
                  '                child.destroy()\n'
                  '            self.normalize_documentation_fields(task)\n'
                  '            headers = ["Anlagenpfad", "Öffnen", "Entfernen", "Bemerkung"]\n'
                  '            for c, h in enumerate(headers):\n'
                  '                tk.Label(list_frame, text=h, bg=COLORS["header"], fg=COLORS["text"], '
                  'font=zfont(self.app, 11, "bold"), padx=6, pady=4).grid(row=0, column=c, sticky="nsew")\n'
                  '            if not task.get("attachments"):\n'
                  '                tk.Label(list_frame, text="Noch keine Anlage hinterlegt.", bg=COLORS["white"], '
                  'fg=COLORS["text2"], padx=8, pady=8, anchor="w").grid(row=1, column=0, columnspan=4, sticky="ew")\n'
                  '                return\n'
                  '            for idx, att in enumerate(task.get("attachments", []), start=1):\n'
                  '                tk.Label(list_frame, text=att.get("path", ""), bg=COLORS["white"], '
                  'fg=COLORS["text"], anchor="w", wraplength=330).grid(row=idx, column=0, sticky="ew", padx=6, '
                  'pady=3)\n'
                  '                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): '
                  'self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, '
                  'pady=3)\n'
                  '                tk.Button(list_frame, text="Entfernen", command=lambda a=att: remove_attachment(a), '
                  'bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, pady=3)\n'
                  '                tk.Label(list_frame, text=att.get("comment", ""), bg=COLORS["white"], '
                  'fg=COLORS["text2"], anchor="w", justify="left", wraplength=320).grid(row=idx, column=3, '
                  'sticky="ew", padx=6, pady=3)\n'
                  '\n'
                  '        def choose_path():\n'
                  '            selected = filedialog.askopenfilename(title="Anlage auswählen")\n'
                  '            if selected:\n'
                  '                path_var.set(selected)\n'
                  '\n'
                  '        def add_or_update_attachment():\n'
                  '            path = path_var.get().strip()\n'
                  '            if not path or path == placeholder:\n'
                  '                messagebox.showwarning("Anlagen", "Bitte einen Pfad der Anlage wählen oder '
                  'einfügen.")\n'
                  '                return\n'
                  '            self.normalize_documentation_fields(task)\n'
                  '            task.setdefault("attachments", []).append({\n'
                  '                "name": os.path.basename(path) or "Anlage",\n'
                  '                "path": path,\n'
                  '                "comment": comment_box.get("1.0", "end").strip(),\n'
                  '                "added_at": datetime.now().isoformat(timespec="seconds"),\n'
                  '            })\n'
                  '            self.save()\n'
                  '            refresh()\n'
                  '            path_var.set(placeholder)\n'
                  '            comment_box.delete("1.0", "end")\n'
                  '            if self.selected_team:\n'
                  '                self.render_team_detail(self.selected_team)\n'
                  '\n'
                  '        def remove_attachment(att):\n'
                  '            if messagebox.askyesno("Anlage entfernen", f"Anlage entfernen?\\n\\n{att.get(\'name\') '
                  'or att.get(\'path\')}"):\n'
                  '                task["attachments"] = [a for a in task.get("attachments", []) if a != att]\n'
                  '                self.save(); refresh()\n'
                  '                if self.selected_team:\n'
                  '                    self.render_team_detail(self.selected_team)\n'
                  '\n'
                  '        form = tk.Frame(win, bg=COLORS["bg"])\n'
                  '        form.pack(fill="x", padx=16, pady=(0, 14))\n'
                  '        path_var = tk.StringVar()\n'
                  '        placeholder = "Bitte Pfad der Anlage wählen oder einfügen"\n'
                  '        path_var.set(placeholder)\n'
                  '        tk.Label(form, text="Anlagenpfad", bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, '
                  '12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                  '        tk.Button(form, text="Anlage auswählen", command=choose_path, bg=COLORS["blue"], '
                  'fg="white", bd=0, padx=10, pady=5).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                  '        entry = tk.Entry(form, textvariable=path_var, bg=COLORS["white"], fg=COLORS["text2"], '
                  'relief="solid", bd=1, width=70)\n'
                  '        entry.grid(row=0, column=2, sticky="ew", pady=(0, 6))\n'
                  '        form.grid_columnconfigure(2, weight=1)\n'
                  '        def clear_placeholder(_event=None):\n'
                  '            if path_var.get() == placeholder:\n'
                  '                path_var.set("")\n'
                  '                entry.config(fg=COLORS["text"])\n'
                  '        entry.bind("<FocusIn>", clear_placeholder)\n'
                  '\n'
                  '        tk.Label(form, text="Bemerkungen und Informationen:", bg=COLORS["bg"], fg=COLORS["text"], '
                  'font=zfont(self.app, 12, "bold")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 4))\n'
                  '        comment_box = tk.Text(form, height=4, bg=COLORS["white"], fg=COLORS["text"], '
                  'relief="solid", bd=1)\n'
                  '        comment_box.grid(row=2, column=0, columnspan=3, sticky="ew")\n'
                  '        tk.Button(form, text="Übernehmen", command=add_or_update_attachment, bg=COLORS["blue"], '
                  'fg="white", bd=0, padx=16, pady=7).grid(row=3, column=2, sticky="e", pady=(8, 0))\n'
                  '        refresh()\n'
                  '\n'
                  '    def open_attachment(self, path):\n'
                  '        if not path or not os.path.exists(path): messagebox.showwarning("Anlage", "Datei wurde '
                  'nicht gefunden."); return\n'
                  '        try:\n'
                  '            if os.name == "nt": os.startfile(path)\n'
                  '            elif sys.platform == "darwin": subprocess.Popen(["open", path])\n'
                  '            else: subprocess.Popen(["xdg-open", path])\n'
                  '        except Exception as exc: messagebox.showerror("Anlage", str(exc))\n'
                  '\n'
                  '\n'
                  'def render(app):\n'
                  '    MonthlyCloseUI(app)\n',
 'quarterly_close': '## FiBuMate_PATCH_MARKER: 20260609_PROTOCOL_ONLY_SUBTASK_PROGRESS\n'
                    '## FiBuMate_PATCH_MARKER: 20260609_v0436_ABSCHLUSSKALENDER_UNIFIED_WRAPPED\n'
                    '## FiBuMate_PATCH_MARKER: 20260609_v0436_DREI_MODULE_OHNE_ID_ZUWEISUNG\n'
                    '\n'
                    'import calendar\n'
                    'import json\n'
                    'import os\n'
                    'import shutil\n'
                    'import subprocess\n'
                    'import sys\n'
                    'import webbrowser\n'
                    'from datetime import date, datetime, timedelta\n'
                    'from pathlib import Path\n'
                    'from urllib.parse import quote\n'
                    'import tkinter as tk\n'
                    'from tkinter import filedialog, messagebox, ttk\n'
                    '\n'
                    'try:\n'
                    '    from . import compliance_common as cc\n'
                    'except Exception:\n'
                    '    try:\n'
                    '        import compliance_common as cc\n'
                    '    except Exception:\n'
                    '        cc = None\n'
                    '\n'
                    '# v0.434 Paket 1B: direkte, scharfe Modulschrift für Abschluss-/Stichtagsmodule.\n'
                    '# Der Bereichszoom aus Fibu_mate.py wird berücksichtigt, ohne Kopf-/Fußleisten nachzuskalieren.\n'
                    'def zfont(app, size=12, weight=None, underline=False, scale=1.0):\n'
                    '    try:\n'
                    '        scope_zoom = float(getattr(app, "current_scope_zoom", 1.0) or 1.0)\n'
                    '        final = max(9, int(round(float(size) * 1.28 * scope_zoom * float(scale))))\n'
                    '    except Exception:\n'
                    '        final = int(size)\n'
                    '    styles = []\n'
                    '    if weight:\n'
                    '        styles.append(weight)\n'
                    '    if underline:\n'
                    '        styles.append("underline")\n'
                    '    return tuple(["Segoe UI", final] + styles)\n'
                    '\n'
                    '\n'
                    'def apply_readable_fonts(widget, app, base_size=12):\n'
                    '    """Setzt direkte Tk-Fonts für neu erzeugte Modulwidgets nach."""\n'
                    '    try:\n'
                    '        try:\n'
                    '            cls = widget.winfo_class().lower()\n'
                    '        except Exception:\n'
                    '            cls = ""\n'
                    '        if cls in ("label", "button", "entry", "text", "listbox", "checkbutton", "radiobutton", '
                    '"menubutton"):\n'
                    '            try:\n'
                    '                current = str(widget.cget("font") or "")\n'
                    '                widget.configure(font=zfont(app, base_size, "bold" if "bold" in current.lower() '
                    'else None))\n'
                    '            except Exception:\n'
                    '                pass\n'
                    '        for child in widget.winfo_children():\n'
                    '            apply_readable_fonts(child, app, base_size)\n'
                    '    except Exception:\n'
                    '        pass\n'
                    'STATUS_OPEN = "Offen"\n'
                    'STATUS_IN_PROGRESS = "In Bearbeitung"\n'
                    'STATUS_DONE = "Erledigt"\n'
                    'STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]\n'
                    'TEAMS = ["Hauptbuch", "Zentralregulierung", "Debitoren", "Treasury"]\n'
                    'TEAM_ALIASES = {"Kreditoren": "Zentralregulierung", "Controlling": "Treasury"}\n'
                    'DEADLINE_TYPES = ["intern", "gesetzlich"]\n'
                    'PRIORITIES = ["normal", "hoch", "kritisch"]\n'
                    '\n'
                    'DUE_CUTOFF = "closing_cutoff"\n'
                    'DUE_WORKDAY_NEXT = "workday_next_month"\n'
                    'DUE_DAY_NEXT_MONTH = "day_next_month"\n'
                    'DUE_DAY_CAL_MONTH = "day_calendar_month"\n'
                    'DUE_DAY_AFTER_CUTOFF = "day_after_cutoff"\n'
                    'DUE_FIXED = "fixed_date"\n'
                    '# Legacy values for migration only\n'
                    'DUE_WORKDAY_MONTH = "workday_current_month"\n'
                    'DUE_END_CURRENT = "end_current_month"\n'
                    'DUE_LABEL_TO_VALUE = {\n'
                    '    "Abschluss-Stichtag": DUE_CUTOFF,\n'
                    '    "x. Werktag des Folgemonats": DUE_WORKDAY_NEXT,\n'
                    '    "x. Tag des Folgemonats": DUE_DAY_NEXT_MONTH,\n'
                    '    "x. Tag des Kalendermonats": DUE_DAY_CAL_MONTH,\n'
                    '    "x. Tag nach Abschluss-Stichtag": DUE_DAY_AFTER_CUTOFF,\n'
                    '    "Konkretes Datum": DUE_FIXED,\n'
                    '}\n'
                    'DUE_VALUE_TO_LABEL = {v: k for k, v in DUE_LABEL_TO_VALUE.items()}\n'
                    'WARN_YELLOW_DAYS = 10\n'
                    'WARN_ORANGE_DAYS = 5\n'
                    'MIN_PERIOD = "2026-Q2"\n'
                    'MIN_FISCAL_YEAR_PERIOD = "2025-2026"\n'
                    'FISCAL_YEAR_START_MONTH = 10\n'
                    '\n'
                    '\n'
                    'def fiscal_year_start_for_date(d=None):\n'
                    '    d = d or date.today()\n'
                    '    return d.year if d.month >= FISCAL_YEAR_START_MONTH else d.year - 1\n'
                    '\n'
                    '\n'
                    'def fiscal_year_end_quarter_key(start_year):\n'
                    '    return f"{start_year + 1:04d}-Q3"\n'
                    '\n'
                    '\n'
                    'def august_month_key(start_year):\n'
                    '    return f"{start_year + 1:04d}-08"\n'
                    '\n'
                    '\n'
                    'def august_cutoff_reached(start_year, today=None):\n'
                    '    today = today or date.today()\n'
                    '    cutoff = None\n'
                    '    try:\n'
                    "        synced = cc.get_deadline_cutoff('monthly', august_month_key(start_year)) if cc is not "
                    "None and hasattr(cc, 'get_deadline_cutoff') else ''\n"
                    '        cutoff = parse_date(synced)\n'
                    '    except Exception:\n'
                    '        cutoff = None\n'
                    '    if not cutoff:\n'
                    "        y, m = map(int, august_month_key(start_year).split('-'))\n"
                    '        end = date(y, m, calendar.monthrange(y, m)[1])\n'
                    '        cur = end + timedelta(days=1)\n'
                    '        while not is_business_day(cur):\n'
                    '            cur += timedelta(days=1)\n'
                    '        cutoff = cur\n'
                    '    return today >= cutoff\n'
                    '\n'
                    '\n'
                    'def max_period_key(today=None):\n'
                    '    today = today or date.today()\n'
                    '    fy_start = fiscal_year_start_for_date(today)\n'
                    '    if august_cutoff_reached(fy_start, today):\n'
                    '        return fiscal_year_end_quarter_key(fy_start + 1)\n'
                    '    return fiscal_year_end_quarter_key(fy_start)\n'
                    '\n'
                    '\n'
                    'def bounded_current_period_key(today=None):\n'
                    '    today = today or date.today()\n'
                    '    current = quarter_key(today)\n'
                    '    if current < MIN_PERIOD:\n'
                    '        return MIN_PERIOD\n'
                    '    max_key = max_period_key(today)\n'
                    '    return min(current, max_key)\n'
                    '\n'
                    '\n'
                    'def period_allowed(period, today=None):\n'
                    '    return MIN_PERIOD <= period <= max_period_key(today)\n'
                    '\n'
                    '\n'
                    'def iter_allowed_periods(today=None):\n'
                    '    periods = []\n'
                    '    cur = MIN_PERIOD\n'
                    '    max_key = max_period_key(today)\n'
                    '    while cur <= max_key:\n'
                    '        periods.append(cur)\n'
                    '        cur = add_quarter(cur, 1)\n'
                    '    return periods\n'
                    'COLORS = {\n'
                    '    "bg": "#E8EEF5", "header": "#D3DEE9", "blue": "#004B93", "red": "#E30613",\n'
                    '    "orange": "#F59E0B", "yellow": "#FACC15", "green": "#16A34A", "dark_green": "#047857",\n'
                    '    "text": "#182431", "text2": "#445364", "line": "#91A3B5", "white": "#FFFFFF",\n'
                    '    "edit_bg": "#FEF3C7", "subtask_bg": "#EAF4FF"  # v0.436 unified: Unteraufgaben-Tabellenfarbe '
                    'ein klein wenig blauer.\n'
                    '}\n'
                    '\n'
                    '\n'
                    'def _base_dir() -> Path:\n'
                    '    here = Path(__file__).resolve()\n'
                    '    if here.parent.name.lower() == "tools":\n'
                    '        return here.parent.parent / "Closing" / "QuarterlyClose"\n'
                    '    return here.parent / "bin" / "Closing" / "QuarterlyClose"\n'
                    '\n'
                    '\n'
                    'BASE_DIR = _base_dir()\n'
                    'PERIOD_DIR = BASE_DIR / "periods"\n'
                    'ATTACH_DIR = BASE_DIR / "attachments"\n'
                    'CONFIG_PATH = BASE_DIR / "quarterly_close_config.json"\n'
                    'CATALOG_PATH = BASE_DIR / "quarterly_close_task_catalog.json"\n'
                    'CLOSING_SCOPE = "Q"\n'
                    'INITIAL_TASK_IDS = {\n'
                    "    ('Hauptbuch', 'Bankabstimmung durchführen'): 'QM001',\n"
                    "    ('Hauptbuch', 'Rückstellungen prüfen'): 'QM002',\n"
                    "    ('Hauptbuch', 'Abgrenzungen buchen'): 'QM003',\n"
                    "    ('Hauptbuch', 'Sachkonten prüfen'): 'QM004',\n"
                    "    ('Zentralregulierung', 'Offene Posten prüfen'): 'QM005',\n"
                    "    ('Zentralregulierung', 'Lieferantenabstimmung durchführen'): 'QM006',\n"
                    "    ('Zentralregulierung', 'Rechnungsabgrenzung prüfen'): 'QM007',\n"
                    "    ('Zentralregulierung', 'Zahlungsläufe kontrollieren'): 'QM008',\n"
                    "    ('Debitoren', 'Offene Posten prüfen'): 'QM009',\n"
                    "    ('Debitoren', 'Mahnstatus prüfen'): 'QM010',\n"
                    "    ('Debitoren', 'Erlösabgrenzung prüfen'): 'QM011',\n"
                    "    ('Debitoren', 'Kundensalden abstimmen'): 'QM012',\n"
                    "    ('Treasury', 'Kostenstellen prüfen'): 'QM013',\n"
                    "    ('Treasury', 'Reporting vorbereiten'): 'QM014',\n"
                    "    ('Treasury', 'Konzernmeldung vorbereiten'): 'QM015',\n"
                    "    ('Treasury', 'Abweichungsanalyse erstellen'): 'QM016',\n"
                    '}\n'
                    '\n'
                    'def quarter_key(d=None):\n'
                    '    d = d or date.today()\n'
                    '    q = (d.month - 1) // 3 + 1\n'
                    '    return f"{d.year:04d}-Q{q}"\n'
                    '\n'
                    'def current_period_key():\n'
                    '    return bounded_current_period_key()\n'
                    '\n'
                    '\n'
                    'def add_quarter(key, delta):\n'
                    '    year_str, q_str = key.split("-Q"); year = int(year_str); quarter = int(q_str) + delta\n'
                    '    while quarter < 1:\n'
                    '        quarter += 4; year -= 1\n'
                    '    while quarter > 4:\n'
                    '        quarter -= 4; year += 1\n'
                    '    return f"{year:04d}-Q{quarter}"\n'
                    '\n'
                    'def add_period(key, delta):\n'
                    '    return add_quarter(key, delta)\n'
                    '\n'
                    'def period_label(key):\n'
                    '    y, q = key.split("-Q")\n'
                    '    return f"{q}. Quartal {y}"\n'
                    '\n'
                    '\n'
                    '\n'
                    'def parse_date(value):\n'
                    '    value = str(value or "").strip()\n'
                    '    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):\n'
                    '        try:\n'
                    '            return datetime.strptime(value, fmt).date()\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '    return None\n'
                    '\n'
                    '\n'
                    'def format_date_de(value):\n'
                    '    d = value if isinstance(value, date) else parse_date(value)\n'
                    '    return d.strftime("%d.%m.%Y") if d else ""\n'
                    '\n'
                    '\n'
                    '\n'
                    'def format_datetime_de(value):\n'
                    '    if not value:\n'
                    '        return ""\n'
                    '    try:\n'
                    '        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y %H:%M")\n'
                    '    except Exception:\n'
                    '        d = parse_date(value)\n'
                    '        return d.strftime("%d.%m.%Y") if d else str(value)\n'
                    '\n'
                    'def easter_sunday(year):\n'
                    '    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4\n'
                    '    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30\n'
                    '    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7\n'
                    '    m = (a + 11 * h + 22 * l) // 451\n'
                    '    month = (h + l - 7 * m + 114) // 31\n'
                    '    day = ((h + l - 7 * m + 114) % 31) + 1\n'
                    '    return date(year, month, day)\n'
                    '\n'
                    '\n'
                    'def bw_holidays(year):\n'
                    '    easter = easter_sunday(year)\n'
                    '    return {\n'
                    '        date(year, 1, 1), date(year, 1, 6), easter - timedelta(days=2), easter + '
                    'timedelta(days=1),\n'
                    '        date(year, 5, 1), easter + timedelta(days=39), easter + timedelta(days=50), easter + '
                    'timedelta(days=60),\n'
                    '        date(year, 10, 3), date(year, 11, 1), date(year, 12, 25), date(year, 12, 26)\n'
                    '    }\n'
                    '\n'
                    '\n'
                    'def is_business_day(d):\n'
                    '    return d.weekday() < 5 and d not in bw_holidays(d.year)\n'
                    '\n'
                    '\n'
                    'def nth_business_day(year, month, n):\n'
                    '    n = max(1, int(n or 1))\n'
                    '    current = date(year, month, 1)\n'
                    '    count = 0\n'
                    '    while True:\n'
                    '        if is_business_day(current):\n'
                    '            count += 1\n'
                    '            if count == n:\n'
                    '                return current\n'
                    '        current += timedelta(days=1)\n'
                    '\n'
                    '\n'
                    'def normalize_team_name(team):\n'
                    '    return TEAM_ALIASES.get(team, team)\n'
                    '\n'
                    '\n'
                    'def normalize_team_members(data):\n'
                    '    members = data.setdefault("team_members", {})\n'
                    '    for old, new in TEAM_ALIASES.items():\n'
                    '        if old in members:\n'
                    '            if new not in members or not members.get(new):\n'
                    '                members[new] = members.get(old, [])\n'
                    '            members.pop(old, None)\n'
                    '    for team in TEAMS:\n'
                    '        value = members.get(team, [])\n'
                    '        if isinstance(value, str):\n'
                    '            value = [v.strip() for v in value.replace(";", "\\n").replace(",", '
                    '"\\n").splitlines() if v.strip()]\n'
                    '        members[team] = value\n'
                    '    return members\n'
                    '\n'
                    '\n'
                    'def set_team_members_text(data, team, text):\n'
                    '    normalize_team_members(data)[team] = [line.strip() for line in str(text or "").replace(";", '
                    '"\\n").replace(",", "\\n").splitlines() if line.strip()]\n'
                    '\n'
                    'def period_start(period):\n'
                    '    y, q = period.split("-Q")\n'
                    '    return date(int(y), (int(q) - 1) * 3 + 1, 1)\n'
                    '\n'
                    'def period_end(period):\n'
                    '    start = period_start(period); end_month = start.month + 2\n'
                    '    return date(start.year, end_month, calendar.monthrange(start.year, end_month)[1])\n'
                    '\n'
                    'def clamp_day_in_period(period, day):\n'
                    '    start = period_start(period)\n'
                    '    day = max(1, min(int(day or 1), calendar.monthrange(start.year, start.month)[1]))\n'
                    '    return date(start.year, start.month, day)\n'
                    '\n'
                    '\n'
                    'def first_business_day_after_period_end(period):\n'
                    '    cur = period_end(period) + timedelta(days=1)\n'
                    '    while not is_business_day(cur):\n'
                    '        cur += timedelta(days=1)\n'
                    '    return cur\n'
                    '\n'
                    'def default_due_date(period):\n'
                    '    return period_end(period).strftime("%Y-%m-%d")\n'
                    '\n'
                    'def resolve_due_date(task, data, period):\n'
                    '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                    '    if mode == DUE_CUTOFF:\n'
                    '        return normalize_cutoff(data, period)\n'
                    '    if mode == DUE_WORKDAY_NEXT:\n'
                    '        next_period = add_quarter(period, 1); start = period_start(next_period)\n'
                    '        return nth_business_day(start.year, start.month, task.get("due_workday") or '
                    '1).strftime("%Y-%m-%d")\n'
                    '    if mode == DUE_DAY_NEXT_MONTH:\n'
                    "        if 'add_month' in globals():\n"
                    '            next_period = add_month(period, 1)\n'
                    "        elif 'add_quarter' in globals():\n"
                    '            next_period = add_quarter(period, 1)\n'
                    '        else:\n'
                    '            next_period = add_period(period, 1)\n'
                    '        return clamp_day_in_period(next_period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                    '    if mode == DUE_DAY_CAL_MONTH:\n'
                    '        return clamp_day_in_period(period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                    '    if mode == DUE_DAY_AFTER_CUTOFF:\n'
                    '        cutoff = parse_date(normalize_cutoff(data, period))\n'
                    '        days_after = max(0, int(task.get("due_day") or 0))\n'
                    '        return (cutoff + timedelta(days=days_after)).strftime("%Y-%m-%d") if cutoff else '
                    'normalize_cutoff(data, period)\n'
                    '    if mode == DUE_FIXED:\n'
                    '        due = parse_date(task.get("due_fixed_date") or task.get("due_date"))\n'
                    '        return due.strftime("%Y-%m-%d") if due else normalize_cutoff(data, period)\n'
                    '    return normalize_cutoff(data, period)\n'
                    '\n'
                    '\n'
                    '\n'
                    'def due_rule_text(task):\n'
                    '    mode = task.get("due_mode")\n'
                    '    if mode == DUE_CUTOFF:\n'
                    '        return "Abschluss-Stichtag"\n'
                    '    if mode == DUE_WORKDAY_NEXT:\n'
                    '        return f"{task.get(\'due_workday\') or 1}. Werktag Folgemonat"\n'
                    '    if mode == DUE_DAY_NEXT_MONTH:\n'
                    '        return f"{task.get(\'due_day\') or 1}. Tag Folgemonat"\n'
                    '    if mode == DUE_DAY_CAL_MONTH:\n'
                    '        return f"{task.get(\'due_day\') or 1}. Tag Kalendermonat"\n'
                    '    if mode == DUE_FIXED:\n'
                    '        return "Konkretes Datum"\n'
                    '    return ""\n'
                    '\n'
                    '\n'
                    'def due_display(task):\n'
                    '    rule = due_rule_text(task)\n'
                    '    return f"{format_date_de(task.get(\'due_date\', \'\'))}\\n{rule}" if rule else '
                    'format_date_de(task.get("due_date", ""))\n'
                    '\n'
                    '\n'
                    'def make_task_id(team, index):\n'
                    "    safe = str(team).lower().replace(' ', '_').replace('/', '_')\n"
                    "    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in safe).strip('_') or 'task'\n"
                    '    return f"{safe}_{int(index or 1):02d}"\n'
                    '\n'
                    'def ensure_storage():\n'
                    '    BASE_DIR.mkdir(parents=True, exist_ok=True)\n'
                    '    PERIOD_DIR.mkdir(parents=True, exist_ok=True)\n'
                    '    ATTACH_DIR.mkdir(parents=True, exist_ok=True)\n'
                    '    if not CONFIG_PATH.exists():\n'
                    '        CONFIG_PATH.write_text(json.dumps({"teams": TEAMS, "warning_days": {"yellow": '
                    'WARN_YELLOW_DAYS, "orange": WARN_ORANGE_DAYS}}, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                    '    if not CATALOG_PATH.exists():\n'
                    '        CATALOG_PATH.write_text(json.dumps({"tasks": []}, ensure_ascii=False, indent=2), '
                    'encoding="utf-8")\n'
                    '\n'
                    '\n'
                    'def period_path(period):\n'
                    '    return PERIOD_DIR / f"{period}.json"\n'
                    '\n'
                    '\n'
                    '\n'
                    'def deadline_cutoff_date(period):\n'
                    '    try:\n'
                    "        if cc is not None and hasattr(cc, 'get_deadline_cutoff'):\n"
                    "            return cc.get_deadline_cutoff('quarterly', period)\n"
                    '    except Exception:\n'
                    '        pass\n'
                    "    return ''\n"
                    '\n'
                    '\n'
                    'def default_cutoff_date(period):\n'
                    '    synced = deadline_cutoff_date(period)\n'
                    '    if synced:\n'
                    '        return synced\n'
                    '    return first_business_day_after_period_end(period).strftime("%Y-%m-%d")\n'
                    '\n'
                    '\n'
                    'def normalize_cutoff(data, period):\n'
                    '    synced = deadline_cutoff_date(period)\n'
                    '    cutoff = parse_date(synced) if synced else parse_date(data.get("closing_cutoff_date", ""))\n'
                    '    if not cutoff:\n'
                    '        cutoff = parse_date(default_cutoff_date(period))\n'
                    '    data["closing_cutoff_date"] = cutoff.strftime("%Y-%m-%d")\n'
                    '    return data["closing_cutoff_date"]\n'
                    '\n'
                    '\n'
                    'def all_subtasks_done(task):\n'
                    '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                    '    return bool(subtasks) and all(s.get("status") == STATUS_DONE for s in subtasks)\n'
                    '\n'
                    '\n'
                    'def sync_parent_status_from_subtasks(task):\n'
                    '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                    '    if subtasks:\n'
                    '        if all(s.get("status") == STATUS_DONE for s in subtasks):\n'
                    '            task["status"] = STATUS_DONE\n'
                    '            task.setdefault("done_at", datetime.now().isoformat(timespec="seconds"))\n'
                    '        elif task.get("status") == STATUS_DONE:\n'
                    '            task["status"] = STATUS_OPEN\n'
                    '            task["done_at"] = None\n'
                    '            task["done_by"] = None\n'
                    '\n'
                    '\n'
                    'def migrate_due_fields(task, data, period):\n'
                    '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                    '    if mode == DUE_WORKDAY_NEXT:\n'
                    '        task["due_mode"] = DUE_WORKDAY_NEXT\n'
                    '    elif mode in (DUE_FIXED,):\n'
                    '        task["due_mode"] = DUE_FIXED\n'
                    '    elif mode in (DUE_WORKDAY_MONTH, DUE_END_CURRENT):\n'
                    '        task["due_mode"] = DUE_CUTOFF\n'
                    '    elif mode not in (DUE_CUTOFF, DUE_WORKDAY_NEXT, DUE_DAY_NEXT_MONTH, DUE_DAY_CAL_MONTH, '
                    'DUE_DAY_AFTER_CUTOFF, DUE_FIXED):\n'
                    '        task["due_mode"] = DUE_CUTOFF\n'
                    '    if task.get("due_mode") in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF):\n'
                    '        task["due_day"] = int(task.get("due_day") or task.get("due_workday") or 1)\n'
                    '\n'
                    '\n'
                    'def normalize_task(task, data, period):\n'
                    '    task["team"] = normalize_team_name(task.get("team"))\n'
                    '    task.pop("task_uid", None)  # v0.436: Aufgaben-ID-Zuweisung vollständig entfernt.\n'
                    '    task.setdefault("owner_user_key", "")\n'
                    '    task.setdefault("attachments", [])\n'
                    '    task.setdefault("comments", [])\n'
                    '    task.setdefault("subtasks", [])\n'
                    '    task.setdefault("status", STATUS_OPEN)\n'
                    '    task.setdefault("deadline_type", "intern")\n'
                    '    task.setdefault("priority", "normal")\n'
                    '    task.setdefault("due_day", None)\n'
                    '    task.setdefault("due_workday", None)\n'
                    '    task.setdefault("recurring", False)\n'
                    '    task.setdefault("catalog_id", "")\n'
                    '    task.setdefault("booking_circle", "IDE")\n'
                    '    if task["deadline_type"] not in DEADLINE_TYPES:\n'
                    '        task["deadline_type"] = "intern"\n'
                    '    migrate_due_fields(task, data, period)\n'
                    '    task["due_date"] = resolve_due_date(task, data, period)\n'
                    '    for idx, sub in enumerate(task.get("subtasks", []), start=1):\n'
                    '        sub.setdefault("id", f"sub_{idx:02d}")\n'
                    '        sub.setdefault("title", "")\n'
                    '        sub.setdefault("status", STATUS_OPEN)\n'
                    '        sub.pop("task_uid", None)  # v0.436: Unteraufgaben-ID-Zuweisung entfernt.\n'
                    '    sync_parent_status_from_subtasks(task)\n'
                    '    return task\n'
                    '\n'
                    '\n'
                    'def load_catalog():\n'
                    '    ensure_storage()\n'
                    '    try:\n'
                    '        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))\n'
                    '    except Exception:\n'
                    '        data = {"tasks": []}\n'
                    '    data.setdefault("tasks", [])\n'
                    '    try:\n'
                    "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437') and "
                    "cc.sync_task_catalog_uids_v0437('quarterly', data):\n"
                    '            save_catalog(data)\n'
                    '    except Exception:\n'
                    '        pass\n'
                    '    return data\n'
                    '\n'
                    '\n'
                    'def save_catalog(data):\n'
                    '    data.setdefault("tasks", [])\n'
                    '    try:\n'
                    "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437'):\n"
                    "            cc.sync_task_catalog_uids_v0437('quarterly', data)\n"
                    '    except Exception:\n'
                    '        pass\n'
                    '    CATALOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                    '\n'
                    '\n'
                    'def default_tasks(period):\n'
                    '    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}\n'
                    '    examples = {\n'
                    '        "Hauptbuch": ["Bankabstimmung durchführen", "Rückstellungen prüfen", "Abgrenzungen '
                    'buchen", "Sachkonten prüfen"],\n'
                    '        "Zentralregulierung": ["Offene Posten prüfen", "Lieferantenabstimmung durchführen", '
                    '"Rechnungsabgrenzung prüfen", "Zahlungsläufe kontrollieren"],\n'
                    '        "Debitoren": ["Offene Posten prüfen", "Mahnstatus prüfen", "Erlösabgrenzung prüfen", '
                    '"Kundensalden abstimmen"],\n'
                    '        "Treasury": ["Kostenstellen prüfen", "Reporting vorbereiten", "Konzernmeldung '
                    'vorbereiten", "Abweichungsanalyse erstellen"],\n'
                    '    }\n'
                    '    tasks = []\n'
                    '    for team in TEAMS:\n'
                    '        names = examples[team]\n'
                    '        for idx, title in enumerate(names, 1):\n'
                    '            is_legal = title in ["Konzernmeldung vorbereiten", "Rechnungsabgrenzung prüfen"]\n'
                    '            task = {\n'
                    '                "id": make_task_id(team, idx), "team": team, "title": title, "owner": team, '
                    '"owner_user_key": "",\n'
                    '                "due_mode": DUE_CUTOFF, "due_day": None, "due_workday": 1,\n'
                    '                "deadline_type": "gesetzlich" if is_legal else "intern", "priority": "kritisch" '
                    'if is_legal else "normal",\n'
                    '                "required": True, "recurring": False, "catalog_id": "", "status": STATUS_OPEN,\n'
                    '                "attachments": [], "comments": [], "subtasks": [], "done_at": None, "done_by": '
                    'None,\n'
                    '            }\n'
                    '            task["due_date"] = resolve_due_date(task, data_stub, period)\n'
                    '            tasks.append(task)\n'
                    '    return tasks\n'
                    '\n'
                    '\n'
                    'def load_period(period):\n'
                    '    ensure_storage()\n'
                    '    path = period_path(period)\n'
                    '    if not path.exists():\n'
                    '        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), '
                    '"closing_cutoff_date": default_cutoff_date(period), "team_members": {team: [] for team in TEAMS}, '
                    '"tasks": default_tasks(period)}\n'
                    '        save_period(period, data)\n'
                    '        return data\n'
                    '    data = json.loads(path.read_text(encoding="utf-8"))\n'
                    '    data.setdefault("tasks", [])\n'
                    '    normalize_team_members(data)\n'
                    '    old_cutoff = data.get("closing_cutoff_date", "")\n'
                    '    normalize_cutoff(data, period)\n'
                    '    changed = old_cutoff != data.get("closing_cutoff_date", "")\n'
                    '    for task in data["tasks"]:\n'
                    '        old_team = task.get("team")\n'
                    '        normalize_task(task, data, period)\n'
                    '        changed = changed or old_team != task.get("team")\n'
                    '    try:\n'
                    "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                    "            changed = cc.ensure_task_identity_for_period_v0437('quarterly', period, data) or "
                    'changed\n'
                    '    except Exception:\n'
                    '        pass\n'
                    '    if changed:\n'
                    '        save_period(period, data)\n'
                    '    return data\n'
                    '\n'
                    '\n'
                    'def save_period(period, data):\n'
                    '    ensure_storage()\n'
                    '    normalize_team_members(data)\n'
                    '    normalize_cutoff(data, period)\n'
                    '    for task in data.get("tasks", []):\n'
                    '        normalize_task(task, data, period)\n'
                    '    try:\n'
                    "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                    "            cc.ensure_task_identity_for_period_v0437('quarterly', period, data)\n"
                    '    except Exception:\n'
                    '        pass\n'
                    '    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), '
                    'encoding="utf-8")\n'
                    '\n'
                    '\n'
                    'def catalog_entry_to_task(entry, period, index):\n'
                    '    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}\n'
                    '    task = {\n'
                    '        "id": make_task_id(entry.get("team", "Team"), index), "team": '
                    'normalize_team_name(entry.get("team")), "title": entry.get("title"),\n'
                    '        "owner": entry.get("owner", entry.get("team")), "owner_user_key": '
                    'entry.get("owner_user_key", ""),\n'
                    '        "due_mode": entry.get("due_mode", DUE_CUTOFF), "due_day": entry.get("due_day"), '
                    '"due_workday": entry.get("due_workday"), "due_fixed_date": entry.get("due_fixed_date", '
                    'entry.get("due_date", "")),\n'
                    '        "deadline_type": entry.get("deadline_type", "intern"), "priority": entry.get("priority", '
                    '"normal"),\n'
                    '        "required": entry.get("required", True), "recurring": True, "catalog_id": '
                    'entry.get("catalog_id", ""),\n'
                    '        "status": STATUS_OPEN, "attachments": [], "comments": [], "subtasks": [], "done_at": '
                    'None, "done_by": None,\n'
                    '    }\n'
                    '    task["due_date"] = resolve_due_date(task, data_stub, period)\n'
                    '    return task\n'
                    '\n'
                    '\n'
                    'def apply_catalog_to_period(period):\n'
                    '    data = load_period(period)\n'
                    '    catalog = load_catalog()\n'
                    '    changed = False\n'
                    '    tasks = data.setdefault("tasks", [])\n'
                    '    for entry in catalog.get("tasks", []):\n'
                    '        if not entry.get("recurring", True):\n'
                    '            continue\n'
                    '        start_period = entry.get("start_period", current_period_key())\n'
                    '        if period <= start_period:\n'
                    '            continue\n'
                    '        catalog_id = entry.get("catalog_id")\n'
                    '        existing = next((t for t in tasks if t.get("catalog_id") == catalog_id and not '
                    't.get("deleted")), None)\n'
                    '        if existing:\n'
                    '            keep = {"status": existing.get("status", STATUS_OPEN), "attachments": '
                    'existing.get("attachments", []), "comments": existing.get("comments", []), "subtasks": '
                    'existing.get("subtasks", []), "done_at": existing.get("done_at"), "done_by": '
                    'existing.get("done_by")}\n'
                    '            existing.update(catalog_entry_to_task(entry, period, len([t for t in tasks if '
                    't.get("team") == entry.get("team")]) + 1))\n'
                    '            existing.update(keep)\n'
                    '            changed = True\n'
                    '        else:\n'
                    '            idx = len([t for t in tasks if t.get("team") == entry.get("team")]) + 1\n'
                    '            tasks.append(catalog_entry_to_task(entry, period, idx))\n'
                    '            changed = True\n'
                    '    if changed:\n'
                    '        save_period(period, data)\n'
                    '    return data\n'
                    '\n'
                    'def cleanup_old_periods():\n'
                    '    ensure_storage()\n'
                    '    # v0.432: Alte/vorzeitige Periodendateien werden nicht gelöscht, aber nicht mehr angezeigt '
                    'oder automatisch angelegt.\n'
                    '    return\n'
                    '\n'
                    '\n'
                    'def ensure_period_window():\n'
                    '    ensure_storage(); cleanup_old_periods()\n'
                    '    for p in iter_allowed_periods():\n'
                    '        load_period(p)\n'
                    '        apply_catalog_to_period(p)\n'
                    '\n'
                    '\n'
                    'def list_periods():\n'
                    '    ensure_period_window()\n'
                    '    allowed = set(iter_allowed_periods())\n'
                    '    return sorted(p.stem for p in PERIOD_DIR.glob("*.json") if p.stem in allowed)\n'
                    '\n'
                    '\n'
                    'def warning_level(task, today=None):\n'
                    '    if task.get("status") == STATUS_DONE or task.get("deadline_type") == "keine":\n'
                    '        return "done" if task.get("status") == STATUS_DONE else "none"\n'
                    '    due = parse_date(task.get("due_date", ""))\n'
                    '    if not due:\n'
                    '        return "none"\n'
                    '    today = today or date.today()\n'
                    '    days = (due - today).days\n'
                    '    if days < 0: return "overdue"\n'
                    '    if days == 0: return "today"\n'
                    '    if days <= WARN_ORANGE_DAYS: return "orange"\n'
                    '    if days <= WARN_YELLOW_DAYS: return "yellow"\n'
                    '    return "none"\n'
                    '\n'
                    '\n'
                    'def progress_color(percent):\n'
                    '    if percent >= 100: return COLORS["dark_green"]\n'
                    '    if percent >= 75: return COLORS["green"]\n'
                    '    if percent >= 50: return COLORS["yellow"]\n'
                    '    if percent >= 25: return COLORS["orange"]\n'
                    '    return COLORS["red"]\n'
                    '\n'
                    '\n'
                    'def calc_stats(tasks):\n'
                    '    """Fortschritt inkl. Unteraufgaben berechnen.\n'
                    '    Hauptaufgaben und nicht gelöschte Unteraufgaben zählen als Fortschrittseinheiten.\n'
                    '    """\n'
                    '    visible = [t for t in tasks if not t.get("deleted")]\n'
                    '    units = []\n'
                    '    for task in visible:\n'
                    '        units.append(task)\n'
                    '        for sub in task.get("subtasks", []) or []:\n'
                    '            if not sub.get("deleted"):\n'
                    '                units.append(sub)\n'
                    '    total = len(units)\n'
                    '    done = sum(1 for item in units if item.get("status") == STATUS_DONE)\n'
                    '    in_progress = sum(1 for item in units if item.get("status") == STATUS_IN_PROGRESS)\n'
                    '    open_count = total - done - in_progress\n'
                    '    overdue = sum(1 for t in visible if warning_level(t) == "overdue")\n'
                    '    critical = sum(1 for t in visible if warning_level(t) in ("overdue", "today", "orange") or '
                    '(t.get("priority") == "kritisch" and t.get("deadline_type") != "keine"))\n'
                    '    sub_total = max(0, total - len(visible))\n'
                    '    sub_done = sum(1 for task in visible for sub in (task.get("subtasks", []) or []) if not '
                    'sub.get("deleted") and sub.get("status") == STATUS_DONE)\n'
                    '    percent = int(round((done / total) * 100)) if total else 0\n'
                    '    return {"total": total, "done": done, "in_progress": in_progress, "open": open_count, '
                    '"overdue": overdue, "critical": critical, "percent": percent, "task_total": len(visible), '
                    '"subtask_total": sub_total, "subtask_done": sub_done}\n'
                    '\n'
                    '\n'
                    'class QuarterlyCloseUI:\n'
                    '    def __init__(self, app):\n'
                    '        self.app = app\n'
                    '        self.root = app.root\n'
                    '        self.canvas = app.canvas\n'
                    '        ensure_period_window()\n'
                    '        self.period = current_period_key()\n'
                    '        self.data = apply_catalog_to_period(self.period)\n'
                    '        self.selected_team = None\n'
                    '        self.expanded_tasks = set()\n'
                    '        self.edit_mode = False\n'
                    '        self.tooltip = None\n'
                    '        self._live_period_mtime = 0\n'
                    '        self._live_period_refresh_started = False\n'
                    '        self._live_period_popup_open = False\n'
                    '        self._live_period_notice_shown = False\n'
                    '        self._live_task_widgets = {}\n'
                    '        self._live_subtask_widgets = {}\n'
                    '        self.frame = tk.Frame(self.root, bg=COLORS["bg"])\n'
                    '        self.app.widget_items.append(self.frame)\n'
                    '        self.app.module_escape_handler = self.handle_escape\n'
                    '        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", '
                    'width=self.canvas.winfo_width(), height=max(400, self.canvas.winfo_height() - 172))\n'
                    '        self.strip_task_ids_all_periods()\n'
                    '        self.render_dashboard()\n'
                    '        apply_readable_fonts(self.frame, self.app, 12)\n'
                    '        self._live_period_mtime = self._period_file_mtime()\n'
                    '        self.bind_module_ctrl_mousewheel_guard()\n'
                    '        self._start_live_period_refresh()\n'
                    '\n'
                    '\n'
                    '\n'
                    '    def _period_file_mtime(self):\n'
                    '        try:\n'
                    '            path = period_path(self.period)\n'
                    '            return path.stat().st_mtime if path.exists() else 0\n'
                    '        except Exception:\n'
                    '            return 0\n'
                    '\n'
                    '    def _start_live_period_refresh(self):\n'
                    '        if getattr(self, "_live_period_refresh_started", False):\n'
                    '            return\n'
                    '        self._live_period_refresh_started = True\n'
                    '        try:\n'
                    '            self.root.after(3000, self._check_live_period_refresh)\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _task_live_key(self, task):\n'
                    '        try:\n'
                    '            return self.task_match_key(task)\n'
                    '        except Exception:\n'
                    '            return "|".join([str(task.get("team", "")), str(task.get("catalog_id", "")), '
                    'str(task.get("title", ""))])\n'
                    '\n'
                    '    def _subtask_live_key(self, task, subtask):\n'
                    '        return self._task_live_key(task) + "::sub::" + str(subtask.get("catalog_id") or '
                    'subtask.get("title") or subtask.get("id") or "")\n'
                    '\n'
                    '    def _visible_tasks_from_data(self, data, team=None):\n'
                    '        tasks = [t for t in data.get("tasks", []) if not t.get("deleted")]\n'
                    '        if team:\n'
                    '            tasks = [t for t in tasks if t.get("team") == team]\n'
                    '        return sorted(tasks, key=lambda t: str(t.get("title", "")).casefold())\n'
                    '\n'
                    '    def _live_structure_signature(self, data):\n'
                    '        sig = []\n'
                    '        for t in self._visible_tasks_from_data(data, None):\n'
                    '            subs = tuple((self._subtask_live_key(t, s), s.get("title", ""), s.get("owner", ""), '
                    's.get("owner_user_key", "")) for s in sorted([x for x in t.get("subtasks", []) if not '
                    'x.get("deleted")], key=lambda x: str(x.get("title", "")).casefold()))\n'
                    '            sig.append((self._task_live_key(t), t.get("team", ""), t.get("title", ""), '
                    't.get("owner", ""), t.get("owner_user_key", ""), t.get("due_date", ""), t.get("due_mode", ""), '
                    't.get("deadline_type", ""), t.get("priority", ""), bool(t.get("recurring")), subs))\n'
                    '        return tuple(sig)\n'
                    '\n'
                    '    def _live_status_signature(self, data):\n'
                    '        sig = []\n'
                    '        for t in self._visible_tasks_from_data(data, None):\n'
                    '            subs = tuple((self._subtask_live_key(t, s), s.get("status", STATUS_OPEN), '
                    's.get("done_at"), s.get("done_by"), len(s.get("attachments", [])), len(s.get("comments", []))) '
                    'for s in sorted([x for x in t.get("subtasks", []) if not x.get("deleted")], key=lambda x: '
                    'str(x.get("title", "")).casefold()))\n'
                    '            sig.append((self._task_live_key(t), t.get("status", STATUS_OPEN), t.get("done_at"), '
                    't.get("done_by"), len(t.get("attachments", [])), len(t.get("comments", [])), subs))\n'
                    '        return tuple(sig)\n'
                    '\n'
                    '    def _widgets_recursive(self, widget):\n'
                    '        yield widget\n'
                    '        try:\n'
                    '            children = widget.winfo_children()\n'
                    '        except Exception:\n'
                    '            children = []\n'
                    '        for child in children:\n'
                    '            yield from self._widgets_recursive(child)\n'
                    '\n'
                    '    def _safe_config(self, widget, **kwargs):\n'
                    '        try:\n'
                    '            if widget is not None:\n'
                    '                widget.configure(**kwargs)\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _set_row_background(self, widgets, bg):\n'
                    '        for widget in widgets or []:\n'
                    '            for item in self._widgets_recursive(widget):\n'
                    '                try:\n'
                    '                    cls = item.winfo_class()\n'
                    '                except Exception:\n'
                    '                    cls = ""\n'
                    '                if cls in ("Frame", "Label", "Button", "Menubutton"):\n'
                    '                    self._safe_config(item, bg=bg)\n'
                    '\n'
                    '    def _register_live_task_widgets(self, table, row_idx, task, done_button, status_var, '
                    'status_menu):\n'
                    '        try:\n'
                    '            self._live_task_widgets[self._task_live_key(task)] = {"row_widgets": '
                    'list(table.grid_slaves(row=row_idx)), "done_button": done_button, "status_var": status_var, '
                    '"status_menu": status_menu}\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _register_live_subtask_widgets(self, table, row_idx, task, subtask, done_button):\n'
                    '        try:\n'
                    '            self._live_subtask_widgets[self._subtask_live_key(task, subtask)] = {"row_widgets": '
                    'list(table.grid_slaves(row=row_idx)), "done_button": done_button}\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _refresh_option_menu_commands(self, menu, status_var, task):\n'
                    '        try:\n'
                    '            menu_widget = menu["menu"]\n'
                    '            menu_widget.delete(0, "end")\n'
                    '            for status in STATUSES:\n'
                    '                menu_widget.add_command(label=status, command=tk._setit(status_var, status, '
                    'lambda value, t=task: self.set_status(t, value)))\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _apply_button_status(self, button, item, command, can_complete=True, subtask=False):\n'
                    '        try:\n'
                    '            status = item.get("status", STATUS_OPEN)\n'
                    '            bg = "#BBF7D0" if status == STATUS_DONE else (COLORS["subtask_bg"] if subtask else '
                    '("#FFF7ED" if warning_level(item) in ("overdue", "today", "orange") else COLORS["white"]))\n'
                    '            fg = COLORS["dark_green"] if status == STATUS_DONE else COLORS["text"]\n'
                    '            button.configure(text="✓" if status == STATUS_DONE else "□", bg=bg, fg=fg, '
                    'command=command, state="normal" if can_complete else "disabled")\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _apply_smooth_status_update(self, new_data):\n'
                    '        new_tasks = {self._task_live_key(t): t for t in self._visible_tasks_from_data(new_data, '
                    'self.selected_team)}\n'
                    '        self.data = new_data\n'
                    '        for key, task in new_tasks.items():\n'
                    '            entry = getattr(self, "_live_task_widgets", {}).get(key)\n'
                    '            if entry:\n'
                    '                bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if '
                    'warning_level(task) in ("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", '
                    '"IMS":"#FFF4CC", "SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), '
                    'COLORS["white"])\n'
                    '                self._set_row_background(entry.get("row_widgets"), bg)\n'
                    '                can_complete = self.can_complete_task(task) and (not task.get("subtasks") or '
                    'all_subtasks_done(task))\n'
                    '                self._apply_button_status(entry.get("done_button"), task, lambda t=task: '
                    'self.toggle_done(t), can_complete, False)\n'
                    '                try: entry.get("status_var").set(task.get("status", STATUS_OPEN))\n'
                    '                except Exception: pass\n'
                    '                self._safe_config(entry.get("status_menu"), bg=bg, state="normal" if can_complete '
                    'else "disabled")\n'
                    '                self._refresh_option_menu_commands(entry.get("status_menu"), '
                    'entry.get("status_var"), task)\n'
                    '            for sub in [s for s in task.get("subtasks", []) if not s.get("deleted")]:\n'
                    '                sentry = getattr(self, "_live_subtask_widgets", '
                    '{}).get(self._subtask_live_key(task, sub))\n'
                    '                if not sentry:\n'
                    '                    continue\n'
                    '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                    '                self._set_row_background(sentry.get("row_widgets"), sub_bg)\n'
                    '                self._apply_button_status(sentry.get("done_button"), sub, lambda t=task, s=sub: '
                    'self.toggle_subtask(t, s), self.can_complete_task(task), True)\n'
                    '\n'
                    '    def _current_scroll_fraction(self):\n'
                    '        try:\n'
                    '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                    '            return canvas.yview()[0] if canvas is not None else None\n'
                    '        except Exception:\n'
                    '            return None\n'
                    '\n'
                    '    def _restore_scroll_after_render(self, fraction):\n'
                    '        try:\n'
                    '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                    '            if canvas is not None and fraction is not None:\n'
                    '                self.root.after_idle(lambda c=canvas, f=fraction: c.yview_moveto(f))\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def _show_live_refresh_notice_once(self):\n'
                    '        if getattr(self, "_live_period_popup_open", False) or getattr(self, '
                    '"_live_period_notice_shown", False):\n'
                    '            return\n'
                    '        self._live_period_notice_shown = True\n'
                    '        self._live_period_popup_open = True\n'
                    '        try:\n'
                    '            messagebox.showinfo("Abschlusskalender", "Dieser Abschlusskalender wurde durch einen '
                    'anderen Benutzer aktualisiert. Die Ansicht wurde live neu geladen.")\n'
                    '        finally:\n'
                    '            self._live_period_popup_open = False\n'
                    '\n'
                    '    def _check_live_period_refresh(self):\n'
                    '        try:\n'
                    '            current_mtime = self._period_file_mtime()\n'
                    '            known_mtime = getattr(self, "_live_period_mtime", 0)\n'
                    '            if current_mtime and known_mtime and current_mtime != known_mtime:\n'
                    '                old_data = self.data\n'
                    '                new_data = load_period(self.period)\n'
                    '                old_structure = self._live_structure_signature(old_data)\n'
                    '                new_structure = self._live_structure_signature(new_data)\n'
                    '                old_status = self._live_status_signature(old_data)\n'
                    '                new_status = self._live_status_signature(new_data)\n'
                    '                self._live_period_mtime = current_mtime\n'
                    '                if old_structure == new_structure and old_status != new_status and '
                    'self.selected_team:\n'
                    '                    self._apply_smooth_status_update(new_data)\n'
                    '                elif old_structure == new_structure and old_status == new_status:\n'
                    '                    self.data = new_data\n'
                    '                else:\n'
                    '                    selected_team = self.selected_team\n'
                    '                    expanded = set(getattr(self, "expanded_tasks", set()))\n'
                    '                    was_edit_mode = bool(getattr(self, "edit_mode", False))\n'
                    '                    scroll_fraction = self._current_scroll_fraction()\n'
                    '                    self.data = new_data\n'
                    '                    self.expanded_tasks = expanded\n'
                    '                    if selected_team:\n'
                    '                        self.selected_team = selected_team\n'
                    '                        self.render_team_detail(selected_team)\n'
                    '                    else:\n'
                    '                        self.render_dashboard()\n'
                    '                    self._restore_scroll_after_render(scroll_fraction)\n'
                    '                    if was_edit_mode:\n'
                    '                        self._show_live_refresh_notice_once()\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '        try:\n'
                    '            self.root.after(3000, self._check_live_period_refresh)\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def handle_escape(self):\n'
                    '        if self.selected_team:\n'
                    '            self.selected_team = None\n'
                    '            self.render_dashboard()\n'
                    '            return True\n'
                    '        return False\n'
                    '\n'
                    '    def _module_ctrl_mousewheel_direction(self, event):\n'
                    '        try:\n'
                    '            if getattr(event, "num", None) == 4:\n'
                    '                return 1\n'
                    '            if getattr(event, "num", None) == 5:\n'
                    '                return -1\n'
                    '            delta = int(getattr(event, "delta", 0) or 0)\n'
                    '            return 1 if delta > 0 else (-1 if delta < 0 else 0)\n'
                    '        except Exception:\n'
                    '            return 0\n'
                    '\n'
                    '    def handle_module_ctrl_mousewheel(self, event=None):\n'
                    '        """v0.435: Strg+Mausrad im Abschlusskalender bleibt im aktuellen Kontext.\n'
                    '\n'
                    '        Hintergrund: Der globale Tool-Zoom kann das externe Tool neu laden und dadurch aus\n'
                    '        der Teamübersicht zurück ins Dashboard springen. Deshalb wird der Zoom hier lokal\n'
                    '        angewendet und die aktuell ausgewählte Teamansicht anschließend wiederhergestellt.\n'
                    '        """\n'
                    '        direction = self._module_ctrl_mousewheel_direction(event)\n'
                    '        if not direction:\n'
                    '            return "break"\n'
                    '        try:\n'
                    '            current = float(getattr(self.app, "current_scope_zoom", 1.0) or 1.0)\n'
                    '        except Exception:\n'
                    '            current = 1.0\n'
                    '        try:\n'
                    '            step = float(getattr(self.app, "GLOBAL_TEXT_ZOOM_STEP", 0.025) or 0.025)\n'
                    '        except Exception:\n'
                    '            step = 0.025\n'
                    '        new_zoom = max(0.70, min(1.80, current + (step * direction)))\n'
                    '        try:\n'
                    '            setattr(self.app, "current_scope_zoom", new_zoom)\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '        team = self.selected_team\n'
                    '        if team:\n'
                    '            try:\n'
                    '                self.render_team_detail(team)\n'
                    '            except Exception:\n'
                    '                apply_readable_fonts(self.frame, self.app, 12)\n'
                    '        else:\n'
                    '            try:\n'
                    '                self.render_dashboard()\n'
                    '            except Exception:\n'
                    '                apply_readable_fonts(self.frame, self.app, 12)\n'
                    '        return "break"\n'
                    '\n'
                    '    def bind_module_ctrl_mousewheel_guard(self, widget=None):\n'
                    '        """Bindet Strg+Mausrad auf alle Modulwidgets, damit der globale Handler nicht '
                    'navigiert."""\n'
                    '        widget = widget or self.frame\n'
                    '        try:\n'
                    '            for sequence in ("<Control-MouseWheel>", "<Control-Button-4>", '
                    '"<Control-Button-5>"):\n'
                    '                widget.bind(sequence, self.handle_module_ctrl_mousewheel)\n'
                    '            for child in widget.winfo_children():\n'
                    '                self.bind_module_ctrl_mousewheel_guard(child)\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '\n'
                    '    def can_edit(self):\n'
                    '        return self.role_rank_value() >= 3 and not self.is_period_closed()\n'
                    '\n'
                    '    def user_choices(self):\n'
                    '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                    '        choices = [("", "Team / keine Person")]\n'
                    '        for key, data in sorted(users.items(), key=lambda item: item[1].get("display_name", '
                    'item[0]).casefold()):\n'
                    '            choices.append((key, data.get("display_name", key)))\n'
                    '        return choices\n'
                    '\n'
                    '\n'
                    '    def _target_period_from_current(self):\n'
                    '        start = period_start(self.period); return f"{start.year:04d}-{start.month:02d}"\n'
                    '    def _target_periods_from(self, start_period, all_following):\n'
                    '        if not all_following: return [start_period]\n'
                    '        y, m = map(int, start_period.split("-")); out=[]\n'
                    '        for _ in range(24):\n'
                    '            out.append(f"{y:04d}-{m:02d}"); m += 1\n'
                    '            if m > 12: m = 1; y += 1\n'
                    '        return out\n'
                    '    def _target_period_end(self, period):\n'
                    '        y, m = map(int, period.split("-")); return date(y, m, calendar.monthrange(y, '
                    'm)[1]).strftime("%Y-%m-%d")\n'
                    '    def _target_display(self, period):\n'
                    '        '
                    'names=["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]; '
                    'y,m=map(int, period.split("-")); return f"{names[m-1]} {y}"\n'
                    '\n'
                    '    def is_standard_user(self):\n'
                    '        return self.role_rank_value() <= 2\n'
                    '    def can_complete_task(self, task):\n'
                    '        if self.is_period_closed(): return False\n'
                    '        if not self.is_standard_user(): return True\n'
                    '        return bool(getattr(self.app, "current_user_key", "") and task.get("owner_user_key") == '
                    'getattr(self.app, "current_user_key", ""))\n'
                    '\n'
                    '    def current_user_full_name(self):\n'
                    '        key = getattr(self.app, "current_user_key", "")\n'
                    '        data = getattr(self.app, "user_data", {}).get("users", {}).get(key, {}) if key else {}\n'
                    '        return data.get("full_name") or " ".join(x for x in [data.get("first_name", "").strip(), '
                    'data.get("display_name", "").strip()] if x).strip() or getattr(self.app, "current_user_display", '
                    '"") or key or ""\n'
                    '\n'
                    '    def role_rank_value(self):\n'
                    '        role = self.app.my_role() if hasattr(self.app, "my_role") else "E1 - Standard"\n'
                    '        mapping = {"E1 - Standard": 1, "E2 - Erweitert": 2, "E3 - Administrator": 3, "E4 - '
                    'System-Administrator": 4, "Standard": 1, "Administrator": 3, "System-Administrator": 4, '
                    '"Wagnerm": 4}\n'
                    '        return mapping.get(role, 1)\n'
                    '\n'
                    '    def ensure_close_metadata(self):\n'
                    '        self.data.setdefault("closed", False)\n'
                    '        self.data.setdefault("closed_at", None)\n'
                    '        self.data.setdefault("closed_by", "")\n'
                    '        self.data.setdefault("closed_by_key", "")\n'
                    '        self.data.setdefault("reopened_once", False)\n'
                    '        self.data.setdefault("close_events", [])\n'
                    '        self.data.setdefault("change_log", [])\n'
                    '        self.data.setdefault("reopen_email_log", [])\n'
                    '\n'
                    '    def is_period_closed(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        return bool(self.data.get("closed"))\n'
                    '\n'
                    '    def is_after_cutoff(self):\n'
                    '        cutoff = parse_date(self.data.get("closing_cutoff_date"))\n'
                    '        return bool(cutoff and date.today() > cutoff)\n'
                    '\n'
                    '    def can_toggle_period_close(self):\n'
                    '        return self.role_rank_value() >= 3\n'
                    '\n'
                    '    def require_unlocked(self, action="Diese Änderung"):\n'
                    '        if self.is_period_closed():\n'
                    '            messagebox.showwarning("Zeitraum geschlossen", f"{action} ist nicht möglich, weil der '
                    'Zeitraum geschlossen ist. Bitte den Zeitraum zuerst wieder öffnen.")\n'
                    '            return False\n'
                    '        return True\n'
                    '\n'
                    '    def log_period_event(self, action, reason="", extra=None):\n'
                    '        self.ensure_close_metadata()\n'
                    '        self.data.setdefault("close_events", []).append({\n'
                    '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                    '            "action": action,\n'
                    '            "user": self.current_user_full_name(),\n'
                    '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                    '            "reason": reason,\n'
                    '            "extra": extra or {},\n'
                    '        })\n'
                    '\n'
                    '    def log_change(self, action, task=None, field="", old="", new=""):\n'
                    '        self.ensure_close_metadata()\n'
                    '        after_reopen = bool(self.data.get("reopened_once")) and not self.data.get("closed")\n'
                    '        self.data.setdefault("change_log", []).append({\n'
                    '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                    '            "user": self.current_user_full_name(),\n'
                    '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                    '            "action": action,\n'
                    '            "task_title": task.get("title", "") if isinstance(task, dict) else "",\n'
                    '            "field": field,\n'
                    '            "old": str(old) if old is not None else "",\n'
                    '            "new": str(new) if new is not None else "",\n'
                    '            "after_reopen": after_reopen,\n'
                    '        })\n'
                    '\n'
                    '    def close_status_text(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        if self.data.get("closed"):\n'
                    '            return f"(zuletzt) abgeschlossen am '
                    '{format_datetime_de(self.data.get(\'closed_at\'))} durch {self.data.get(\'closed_by\', \'\')}"\n'
                    '        events = self.data.get("close_events", [])\n'
                    '        reopen = next((e for e in reversed(events) if e.get("action") == "opened"), None)\n'
                    '        if reopen:\n'
                    '            return f"Wieder geöffnet am {format_datetime_de(reopen.get(\'timestamp\'))} durch '
                    '{reopen.get(\'user\', \'\')}"\n'
                    '        return ""\n'
                    '\n'
                    '    def e3_e4_recipients(self):\n'
                    '        recipients=[]\n'
                    '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                    '        opener = getattr(self.app, "current_user_key", "")\n'
                    '        for key, data in users.items():\n'
                    '            if key == opener:\n'
                    '                continue\n'
                    '            role = data.get("permission", "")\n'
                    '            rank = {"E1 - Standard":1,"E2 - Erweitert":2,"E3 - Administrator":3,"E4 - '
                    'System-Administrator":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}.get(role, 1)\n'
                    '            if rank >= 3:\n'
                    '                recipients.append((key, data.get("email", ""), data.get("full_name") or " '
                    '".join(x for x in [data.get("first_name", "").strip(), data.get("display_name", key).strip()] if '
                    'x).strip() or key))\n'
                    '        return recipients\n'
                    '\n'
                    '    def auto_close_mail_enabled(self):\n'
                    '        try:\n'
                    '            return bool(self.app.auto_close_mail_enabled())\n'
                    '        except Exception:\n'
                    '            return True\n'
                    '\n'
                    '    def send_period_close_email_auto(self):\n'
                    '        if not self.auto_close_mail_enabled():\n'
                    '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "sent": False, "skipped": True, "reason": '
                    '"Auto-Mail deaktiviert"})\n'
                    '            return True\n'
                    '        recipients = self.e3_e4_recipients()\n'
                    '        missing = [name for key, email, name in recipients if not email]\n'
                    '        send_to = [(key, email, name) for key, email, name in recipients if email]\n'
                    '        if not send_to:\n'
                    '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "sent": False, "missing": missing, "error": "Keine '
                    'Empfängeradresse"})\n'
                    '            messagebox.showwarning("Automatische E-Mail", "Der Zeitraum wurde abgeschlossen, aber '
                    'es konnte keine Abschluss-Mail versendet werden, weil keine E3/E4-E-Mail-Adresse hinterlegt '
                    'ist.")\n'
                    '            return False\n'
                    '        try:\n'
                    '            import win32com.client\n'
                    '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                    '            mail = outlook.CreateItem(0)\n'
                    '            mail.To = ";".join(email for key, email, name in send_to)\n'
                    '            mail.Subject = f"Abschluss {self.close_type_label()}: {period_label(self.period)}"\n'
                    '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                    'wurde von {self.current_user_full_name()} abgeschlossen.\\n\\n"\n'
                    '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                    '            mail.Send()\n'
                    '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _, email, _ in send_to], '
                    '"missing": missing, "sent": True})\n'
                    '            return True\n'
                    '        except Exception as exc:\n'
                    '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                    'missing})\n'
                    '            messagebox.showwarning("Automatische E-Mail", f"Der Zeitraum wurde abgeschlossen, '
                    'aber die Abschluss-Mail konnte nicht automatisch versendet werden:\\n\\n{exc}")\n'
                    '            return False\n'
                    '\n'
                    '    def send_reopen_email_auto(self, reason):\n'
                    '        recipients = self.e3_e4_recipients()\n'
                    '        missing = [name for key, email, name in recipients if not email]\n'
                    '        send_to = [(key,email,name) for key,email,name in recipients if email]\n'
                    '        if not send_to:\n'
                    '            messagebox.showerror("Wiederöffnung", "Die Pflichtbenachrichtigung konnte nicht '
                    'versendet werden, weil keine E-Mail-Adresse für E3/E4-Empfänger hinterlegt ist.")\n'
                    '            return False\n'
                    '        try:\n'
                    '            import win32com.client\n'
                    '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                    '            mail = outlook.CreateItem(0)\n'
                    '            mail.To = ";".join(email for key,email,name in send_to)\n'
                    '            mail.Subject = f"Wiederöffnung {self.close_type_label()}: '
                    '{period_label(self.period)}"\n'
                    '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                    'wurde von {self.current_user_full_name()} wieder geöffnet.\\n\\n"\n'
                    '                         f"Begründung:\\n{reason}\\n\\n"\n'
                    '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                    '            mail.Send()\n'
                    '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _,email,_ in send_to], '
                    '"missing": missing, "sent": True})\n'
                    '            return True\n'
                    '        except Exception as exc:\n'
                    '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                    'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                    'missing})\n'
                    '            messagebox.showerror("Wiederöffnung", f"Die Pflichtbenachrichtigung konnte nicht '
                    'automatisch über Outlook versendet werden. Der Zeitraum wurde nicht geöffnet.\\n\\n{exc}")\n'
                    '            return False\n'
                    '\n'
                    '    def ask_reopen_reason(self):\n'
                    '        result = {"reason": None}\n'
                    '        win = tk.Toplevel(self.root); win.title("Zeitraum öffnen"); '
                    'win.configure(bg=COLORS["bg"]); win.geometry("560x300"); win.transient(self.root); '
                    'win.grab_set()\n'
                    '        tk.Label(win, text="Begründung der Wiederöffnung", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=14, pady=(14,6))\n'
                    '        tk.Label(win, text="Bitte gib eine Begründung ein. Ohne Begründung kann der Zeitraum '
                    'nicht wieder geöffnet werden.", bg=COLORS["bg"], fg=COLORS["text2"], wraplength=520, '
                    'justify="left").pack(anchor="w", padx=14, pady=(0,8))\n'
                    '        txt = tk.Text(win, height=7, bg="white", fg=COLORS["text"], relief="solid", bd=1); '
                    'txt.pack(fill="both", expand=True, padx=14, pady=(0,10))\n'
                    '        def ok():\n'
                    '            val = txt.get("1.0", "end").strip()\n'
                    '            if not val:\n'
                    '                messagebox.showwarning("Zeitraum öffnen", "Bitte eine Begründung eingeben."); '
                    'return\n'
                    '            result["reason"] = val; win.destroy()\n'
                    '        footer=tk.Frame(win,bg=COLORS["bg"]); footer.pack(fill="x", padx=14, pady=(0,12))\n'
                    '        '
                    'tk.Button(footer,text="Öffnen",command=ok,bg=COLORS["blue"],fg="white",bd=0,padx=14,pady=7).pack(side="right")\n'
                    '        '
                    'tk.Button(footer,text="Abbrechen",command=win.destroy,bg=COLORS["header"],fg=COLORS["text"],bd=0,padx=14,pady=7).pack(side="right",padx=(0,8))\n'
                    '        win.wait_window(); return result["reason"]\n'
                    '\n'
                    '    def toggle_period_close(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        if not self.can_toggle_period_close():\n'
                    '            messagebox.showwarning("Berechtigung", "Für diese Aktion ist mindestens E3 '
                    'erforderlich."); return\n'
                    '        if self.data.get("closed"):\n'
                    '            reason = self.ask_reopen_reason()\n'
                    '            if not reason: return\n'
                    '            if not self.send_reopen_email_auto(reason): return\n'
                    '            self.data["closed"] = False\n'
                    '            self.data["reopened_once"] = True\n'
                    '            self.log_period_event("opened", reason=reason)\n'
                    '            self.save(); self.render_dashboard(); return\n'
                    '        if not self.is_after_cutoff():\n'
                    '            messagebox.showinfo("Zeitraum abschließen", "Abschluss erst nach Ablauf des '
                    'Abschluss-Stichtags möglich."); return\n'
                    '        stats = calc_stats(self.tasks())\n'
                    '        msg = f"{period_label(self.period)} wirklich abschließen?\\n\\nNach dem Abschluss sind '
                    'keine Änderungen mehr möglich."\n'
                    '        if stats.get("open") or stats.get("in_progress"):\n'
                    '            msg += f"\\n\\nHinweis: Es sind noch {stats.get(\'open\',0)} Aufgaben offen und '
                    '{stats.get(\'in_progress\',0)} in Bearbeitung."\n'
                    '        if not messagebox.askyesno("Zeitraum abschließen", msg): return\n'
                    '        self.data["closed"] = True\n'
                    '        self.data["closed_at"] = datetime.now().isoformat(timespec="seconds")\n'
                    '        self.data["closed_by"] = self.current_user_full_name()\n'
                    '        self.data["closed_by_key"] = getattr(self.app, "current_user_key", "")\n'
                    '        self.log_period_event("closed")\n'
                    '        self.send_period_close_email_auto()\n'
                    '        self.save(); self.render_dashboard()\n'
                    '\n'
                    '    def show_change_log(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        win=tk.Toplevel(self.root); win.title("Änderungsprotokoll"); '
                    'win.configure(bg=COLORS["bg"]); win.geometry("1050x620")\n'
                    '        txt=tk.Text(win,bg="white",fg=COLORS["text"],wrap="word",font=zfont(self.app, 12)); '
                    'txt.pack(fill="both",expand=True,padx=12,pady=12)\n'
                    '        txt.insert("end", f"Änderungsprotokoll {period_label(self.period)}\\n\\n")\n'
                    '        txt.insert("end", "Abschluss-/Wiederöffnungsprotokoll:\\n")\n'
                    '        for e in self.data.get("close_events", []):\n'
                    '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | '
                    '{e.get(\'action\')} | {e.get(\'user\')} | {e.get(\'reason\',\'\')}\\n")\n'
                    '        txt.insert("end", "\\nÄnderungen:\\n")\n'
                    '        for e in self.data.get("change_log", []):\n'
                    '            flag = " [nach Wiederöffnung]" if e.get("after_reopen") else ""\n'
                    '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | {e.get(\'user\')} '
                    "| {e.get('action')} | {e.get('task_title')} | {e.get('field')}: {e.get('old')} -> "
                    '{e.get(\'new\')}{flag}\\n")\n'
                    '        txt.config(state="disabled")\n'
                    '\n'
                    '    def create_icon_button(self, parent, text, command, icon_key="lock", enabled=True, '
                    'tooltip=""):\n'
                    '        photo = None\n'
                    '        try:\n'
                    '            photo = self.app.get_icon_photo(icon_key, 18, 18)\n'
                    '        except Exception:\n'
                    '            photo = None\n'
                    '        btn = tk.Button(parent, text=text, image=photo, compound="left" if photo else None, '
                    'command=command if enabled else None, bg=COLORS["blue"] if enabled else "#CBD5E1", fg="white" if '
                    'enabled else COLORS["text2"], bd=0, padx=10, pady=4, cursor="hand2" if enabled else "arrow", '
                    'state="normal" if enabled else "disabled")\n'
                    '        if photo: btn.image = photo\n'
                    '        if tooltip:\n'
                    '            btn.bind("<Enter>", lambda e, b=btn: self.show_tooltip(b, tooltip)); '
                    'btn.bind("<Leave>", lambda e: self.hide_tooltip())\n'
                    '        return btn\n'
                    '    def _counterpart_period_dir(self):\n'
                    '        return BASE_DIR.parent / "MonthlyClose" / "periods"\n'
                    '    def _load_target_period_data(self, period):\n'
                    '        path = self._counterpart_period_dir() / f"{period}.json"\n'
                    '        try: data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}\n'
                    '        except Exception: data = {}\n'
                    '        data.setdefault("period", period); data.setdefault("created_at", '
                    'datetime.now().isoformat(timespec="seconds")); data.setdefault("closing_cutoff_date", '
                    'self._target_period_end(period)); data.setdefault("team_members", {team: [] for team in TEAMS}); '
                    'data.setdefault("tasks", [])\n'
                    '        return data\n'
                    '    def _save_target_period_data(self, period, data):\n'
                    '        d = self._counterpart_period_dir(); d.mkdir(parents=True, exist_ok=True); (d / '
                    'f"{period}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                    '    def _clone_task_for_counterpart(self, task, period):\n'
                    '        cloned = json.loads(json.dumps(task, ensure_ascii=False)); cloned["id"] = '
                    'make_task_id(cloned.get("team", "Team"), int(datetime.now().strftime("%H%M%S%f")) % 1000000)\n'
                    '        cloned["status"] = STATUS_OPEN; cloned["done_at"] = None; cloned["done_by"] = None; '
                    'cloned["attachments"] = []; cloned["comments"] = []; cloned["catalog_id"] = ""; '
                    'cloned["recurring"] = bool(task.get("recurring", False)); cloned["transfer_source"] = '
                    'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; cloned["due_date"] = '
                    'self._target_period_end(period)\n'
                    '        for sub in cloned.get("subtasks", []): sub["status"] = STATUS_OPEN\n'
                    '        return cloned\n'
                    '    def transfer_task_to_counterpart(self, task, target_period, all_following=False):\n'
                    '        periods = self._target_periods_from(target_period, all_following); source_key = '
                    'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; count = 0\n'
                    '        for period in periods:\n'
                    '            data = self._load_target_period_data(period); tasks = data.setdefault("tasks", []); '
                    'existing = next((t for t in tasks if t.get("transfer_source") == source_key and not '
                    't.get("deleted")), None); cloned = self._clone_task_for_counterpart(task, period)\n'
                    '            if existing:\n'
                    '                keep = {"status": existing.get("status", STATUS_OPEN), "done_at": '
                    'existing.get("done_at"), "done_by": existing.get("done_by"), "attachments": '
                    'existing.get("attachments", []), "comments": existing.get("comments", [])}; existing.clear(); '
                    'existing.update(cloned); existing.update(keep)\n'
                    '            else: tasks.append(cloned)\n'
                    '            self._save_target_period_data(period, data); count += 1\n'
                    '        messagebox.showinfo("Quartalsabschluss", f"Aufgabe wurde in {count} Monatsabschluss(e) '
                    'übernommen.")\n'
                    '    def open_transfer_dialog(self, task):\n'
                    '            if not self.require_unlocked("Aufgabenübernahme ist nicht möglich"): return\n'
                    '            win = tk.Toplevel(self.root); win.title("In Monatsabschluss übernehmen"); '
                    'win.configure(bg=COLORS["bg"]); win.transient(self.root); win.grab_set(); '
                    'win.geometry("540x250")\n'
                    '            default_period = self._target_period_from_current(); mode_var = '
                    'tk.StringVar(value="all")\n'
                    '            tk.Label(win, text="Aufgabe inklusive Unteraufgaben übernehmen", bg=COLORS["bg"], '
                    'fg=COLORS["text"], font=zfont(self.app, 15, "bold")).pack(anchor="w", padx=16, pady=(16, 10))\n'
                    '            tk.Radiobutton(win, text=f"In alle Monatsabschlusse ab '
                    '{self._target_display(default_period)}", variable=mode_var, value="all", bg=COLORS["bg"], '
                    'activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)\n'
                    '            tk.Radiobutton(win, text=f"In Monatsabschluss '
                    '{self._target_display(default_period)}", variable=mode_var, value="single", bg=COLORS["bg"], '
                    'activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)\n'
                    '            period_var = tk.StringVar(value=default_period); options = '
                    'self._target_periods_from(default_period, True)\n'
                    '            menu = tk.OptionMenu(win, period_var, *options); menu.config(bg="white", '
                    'fg=COLORS["text"], bd=1, highlightthickness=0); menu.pack(anchor="w", padx=18, pady=(10, 0))\n'
                    '            btns = tk.Frame(win, bg=COLORS["bg"]); btns.pack(side="bottom", fill="x", padx=16, '
                    'pady=14)\n'
                    '            tk.Button(btns, text="Übernehmen", command=lambda: '
                    '(self.transfer_task_to_counterpart(task, period_var.get(), mode_var.get()=="all"), '
                    'win.destroy()), bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                    '            tk.Button(btns, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                    'fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                    '    def propagate_team_members_to_related_periods(self):\n'
                    '        members = normalize_team_members(self.data)\n'
                    '        for period in list_periods():\n'
                    '            if period >= self.period:\n'
                    '                data = load_period(period); data["team_members"] = json.loads(json.dumps(members, '
                    'ensure_ascii=False)); save_period(period, data)\n'
                    '        for period in self._target_periods_from(self._target_period_from_current(), True):\n'
                    '            data = self._load_target_period_data(period); data["team_members"] = '
                    'json.loads(json.dumps(members, ensure_ascii=False)); self._save_target_period_data(period, data)\n'
                    '\n'
                    '    def clear_frame(self):\n'
                    '        if hasattr(self.app, "active_scroll_canvas"):\n'
                    '            self.app.active_scroll_canvas = None\n'
                    '        for child in self.frame.winfo_children():\n'
                    '            child.destroy()\n'
                    '\n'
                    '    def reload(self):\n'
                    '        self.data = apply_catalog_to_period(self.period)\n'
                    '\n'
                    '    def save(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        self.strip_task_ids_from_data(self.data)\n'
                    '        save_period(self.period, self.data)\n'
                    '        self._live_period_mtime = self._period_file_mtime()\n'
                    '\n'
                    '    def tasks(self):\n'
                    '        return [t for t in self.data.get("tasks", []) if not t.get("deleted")]\n'
                    '\n'
                    '    def team_tasks(self, team):\n'
                    '        return sorted(\n'
                    '            [t for t in self.tasks() if t.get("team") == team],\n'
                    '            key=lambda t: str(t.get("title", "")).casefold(),\n'
                    '        )\n'
                    '\n'
                    '    def task_sort_key(self, task):\n'
                    '        return str(task.get("title", "")).casefold()\n'
                    '\n'
                    '    def is_task_id_editor(self):\n'
                    '        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"\n'
                    '        return role in ("Administrator", "System-Administrator", "Wagnerm")\n'
                    '\n'
                    '    def normalize_task_uid_value(self, value):\n'
                    '        # v0.436: Aufgaben-ID-Zuweisung wurde vollständig entfernt.\n'
                    '        return ""\n'
                    '\n'
                    '    def task_uid_display(self, task):\n'
                    '        # v0.436: Es wird keine Aufgaben-ID mehr angezeigt.\n'
                    '        return ""\n'
                    '\n'
                    '    def initial_uid_for_task(self, task):\n'
                    '        return INITIAL_TASK_IDS.get((normalize_team_name(task.get("team")), str(task.get("title") '
                    'or "")), "")\n'
                    '\n'
                    '    def all_period_files(self):\n'
                    '        ensure_storage()\n'
                    '        return sorted(PERIOD_DIR.glob("*.json"))\n'
                    '\n'
                    '    def collect_used_task_uids(self, exclude_task=None):\n'
                    '        # v0.436: Keine Aufgaben-ID-Verwaltung mehr.\n'
                    '        return set()\n'
                    '\n'
                    '    def next_free_task_uid(self):\n'
                    '        # v0.436: Keine Aufgaben-ID-Zuweisung mehr.\n'
                    '        return ""\n'
                    '\n'
                    '    def task_identity_key_for_initial_id(self, task):\n'
                    '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                    '        if catalog_id:\n'
                    '            return ("catalog", catalog_id)\n'
                    '        initial = self.initial_uid_for_task(task)\n'
                    '        if initial:\n'
                    '            return ("initial", initial)\n'
                    '        return ("local", normalize_team_name(task.get("team")), str(task.get("title") or '
                    '"").strip().casefold())\n'
                    '\n'
                    '    def strip_task_ids_from_data(self, data):\n'
                    '        """Entfernt alte Aufgaben-ID-Felder aus geladenen/gespeicherten Daten, ohne andere '
                    'Inhalte zu verändern."""\n'
                    '        changed = False\n'
                    '        try:\n'
                    '            for task in data.get("tasks", []) or []:\n'
                    '                if "task_uid" in task:\n'
                    '                    task.pop("task_uid", None); changed = True\n'
                    '                for sub in task.get("subtasks", []) or []:\n'
                    '                    if "task_uid" in sub:\n'
                    '                        sub.pop("task_uid", None); changed = True\n'
                    '        except Exception:\n'
                    '            pass\n'
                    '        return changed\n'
                    '\n'
                    '    def strip_task_ids_all_periods(self):\n'
                    '        ensure_storage()\n'
                    '        for path in self.all_period_files():\n'
                    '            try:\n'
                    '                data = json.loads(path.read_text(encoding="utf-8"))\n'
                    '            except Exception:\n'
                    '                continue\n'
                    '            if self.strip_task_ids_from_data(data):\n'
                    '                try:\n'
                    '                    save_period(path.stem, data)\n'
                    '                    if path.stem == self.period:\n'
                    '                        self.data = data\n'
                    '                except Exception:\n'
                    '                    pass\n'
                    '\n'
                    '    def ensure_task_ids(self):\n'
                    '        # v0.436: Kompatibilitätsmethode; weist keine IDs mehr zu, sondern entfernt alte '
                    'ID-Felder.\n'
                    '        self.strip_task_ids_all_periods()\n'
                    '\n'
                    '    def archive_task_uid_change(self, task, old_uid, new_uid):\n'
                    '        # v0.436: ID-Historie deaktiviert.\n'
                    '        return False\n'
                    '\n'
                    '    def task_match_key(self, task):\n'
                    '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                    '        if catalog_id:\n'
                    '            return ("catalog", catalog_id)\n'
                    '        return ("task", str(task.get("id") or "").strip(), normalize_team_name(task.get("team")), '
                    'str(task.get("title") or "").strip().casefold())\n'
                    '\n'
                    '    def get_expand_key(self, task):\n'
                    '        return f"{task.get(\'id\',\'\')}|{task.get(\'team\',\'\')}|{task.get(\'title\',\'\')}"\n'
                    '\n'
                    '    def ask_delegate_scope(self, item, parent_task=None):\n'
                    '        if parent_task is not None:\n'
                    '            return "current"\n'
                    '        result = {"scope": None}\n'
                    '        win = tk.Toplevel(self.root)\n'
                    '        win.title("Zuständigkeit ändern")\n'
                    '        win.configure(bg=COLORS["bg"])\n'
                    '        win.transient(self.root); win.grab_set(); win.geometry("500x205")\n'
                    '        tk.Label(win, text="Zuständigkeit ändern", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                    '        tk.Label(win, text="Soll die Zuständigkeit nur für diesen Zeitraum oder permanent für '
                    'alle Folgezeiträume geändert werden?", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, '
                    '12), wraplength=455, justify="left").pack(anchor="w", padx=16, pady=(0, 12))\n'
                    '        frame = tk.Frame(win, bg=COLORS["bg"]); frame.pack(fill="x", padx=16)\n'
                    '        def choose(scope): result["scope"] = scope; win.destroy()\n'
                    '        tk.Button(frame, text="Nur dieser Zeitraum", command=lambda: choose("current"), '
                    'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))\n'
                    '        tk.Button(frame, text="Permanent für Folgezeiträume", command=lambda: '
                    'choose("permanent"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, '
                    'cursor="hand2").pack(fill="x", pady=(0,6))\n'
                    '        tk.Button(frame, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                    'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                    '        win.wait_window()\n'
                    '        return result["scope"]\n'
                    '\n'
                    '    def apply_delegate_to_following_periods(self, task_key, owner_name, owner_user_key):\n'
                    '        changed_periods = 0\n'
                    '        for period in self.following_periods():\n'
                    '            data = load_period(period)\n'
                    '            changed = False\n'
                    '            for task in data.get("tasks", []):\n'
                    '                if self.task_match_key(task) == task_key:\n'
                    '                    task["owner"] = owner_name\n'
                    '                    task["owner_user_key"] = owner_user_key\n'
                    '                    for sub in task.get("subtasks", []):\n'
                    '                        sub["owner"] = owner_name\n'
                    '                        sub["owner_user_key"] = owner_user_key\n'
                    '                    changed = True\n'
                    '            if changed:\n'
                    '                self.strip_task_ids_from_data(data)\n'
                    '                save_period(period, data)\n'
                    '                changed_periods += 1\n'
                    '        return changed_periods\n'
                    '\n'
                    '    def close_type_label(self):\n'
                    '        scope = globals().get("CLOSING_SCOPE", "")\n'
                    '        return "Monatsabschluss" if scope == "M" else "Quartalsabschluss" if scope == "Q" else '
                    '"Jahresabschluss" if scope == "J" else "Abschluss"\n'
                    '\n'
                    '    def recipient_email_for_user(self, user_key):\n'
                    '        if not user_key:\n'
                    '            return ""\n'
                    '        try:\n'
                    '            return self.app.user_data.get("users", {}).get(user_key, {}).get("email", "")\n'
                    '        except Exception:\n'
                    '            return ""\n'
                    '\n'
                    '    def send_delegation_email(self, user_key, recipient_name, task_title, scope):\n'
                    '        email = self.recipient_email_for_user(user_key)\n'
                    '        if not email:\n'
                    '            messagebox.showwarning("Delegierung", f"Für {recipient_name} ist keine E-Mail-Adresse '
                    'in der Benutzerverwaltung hinterlegt. Die Delegierung wurde gespeichert, aber es konnte keine '
                    'E-Mail vorbereitet werden.")\n'
                    '            return\n'
                    '        delegated_by = getattr(self.app, "current_user_display", "") or getattr(self.app, '
                    '"current_user_key", "") or "FiBu Mate"\n'
                    '        period_text = period_label(self.period)\n'
                    '        close_type = self.close_type_label()\n'
                    '        if scope == "permanent":\n'
                    '            scope_text = "bis auf Weiteres"\n'
                    '        else:\n'
                    '            scope_text = f"für den Zeitraum {period_text}"\n'
                    '        subject = f"Delegierung {close_type}: {task_title}"\n'
                    '        body = (\n'
                    '            f"Hallo {recipient_name},\\n\\n"\n'
                    '            f"die Zuständigkeit der {close_type}-Aufgabe {task_title} wurde an dich von '
                    '{delegated_by} {scope_text} delegiert.\\n\\n"\n'
                    '            "Bitte bestätige die Kenntnisnahme per Antwort.\\n\\n"\n'
                    '            "Vielen Dank :)"\n'
                    '        )\n'
                    '        try:\n'
                    '            webbrowser.open("mailto:" + quote(email) + "?subject=" + quote(subject) + "&body=" + '
                    'quote(body))\n'
                    '        except Exception as exc:\n'
                    '            messagebox.showerror("Delegierung", f"Die E-Mail zur Delegierung konnte nicht '
                    'vorbereitet werden:\\n\\n{exc}")\n'
                    '\n'
                    '    def sync_current_as_template_to_following_periods(self):\n'
                    '        if not self.can_edit(): return\n'
                    '        following = self.following_periods()\n'
                    '        if not following:\n'
                    '            messagebox.showinfo("Vorlage verwenden", "Es sind keine Folgezeiträume vorhanden.")\n'
                    '            return\n'
                    '        msg = f"{period_label(self.period)} als Vorlage für alle Folgezeiträume '
                    'verwenden?\\n\\nAufgabenstruktur, Zuständigkeiten, Fälligkeiten und Unteraufgaben werden anhand '
                    'von Katalog-/Aufgabenschlüsseln übertragen. Status, Kommentare und Anlagen bleiben bei bereits '
                    'vorhandenen Aufgaben erhalten."\n'
                    '        if not messagebox.askyesno("Zeitraum als Vorlage verwenden", msg):\n'
                    '            return\n'
                    '        source = [json.loads(json.dumps(t, ensure_ascii=False)) for t in self.tasks()]\n'
                    '        updated = 0\n'
                    '        for period in following:\n'
                    '            data = load_period(period)\n'
                    '            old_by_key = {self.task_match_key(t): t for t in data.get("tasks", [])}\n'
                    '            new_tasks = []\n'
                    '            for src in source:\n'
                    '                key = self.task_match_key(src)\n'
                    '                old = old_by_key.get(key)\n'
                    '                new_task = json.loads(json.dumps(src, ensure_ascii=False))\n'
                    '                if old:\n'
                    '                    for keep in ("status", "attachments", "comments", "done_at", "done_by", '
                    '"documentation"):\n'
                    '                        if keep in old:\n'
                    '                            new_task[keep] = old.get(keep)\n'
                    '                    old_subs = {str(s.get("title", "")).strip().casefold(): s for s in '
                    'old.get("subtasks", [])}\n'
                    '                    for sub in new_task.get("subtasks", []):\n'
                    '                        old_sub = old_subs.get(str(sub.get("title", "")).strip().casefold())\n'
                    '                        if old_sub:\n'
                    '                            for keep in ("status", "attachments", "comments", "done_at", '
                    '"done_by", "documentation", "owner", "owner_user_key"):\n'
                    '                                if keep in old_sub:\n'
                    '                                    sub[keep] = old_sub.get(keep)\n'
                    '                new_tasks.append(new_task)\n'
                    '            data["tasks"] = new_tasks\n'
                    '            self.strip_task_ids_from_data(data)\n'
                    '            save_period(period, data)\n'
                    '            updated += 1\n'
                    '        messagebox.showinfo("Vorlage verwenden", f"Vorlage wurde auf {updated} Folgezeiträume '
                    'übertragen.")\n'
                    '\n'
                    '    def _pdf_escape(self, text):\n'
                    '        return str(text).replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")\n'
                    '\n'
                    '    def write_simple_pdf(self, path, title, rows):\n'
                    '        lines = [title, ""]\n'
                    '        for row in rows:\n'
                    '            lines.append(" | ".join(str(v) for v in row))\n'
                    '        pages = []\n'
                    '        for start in range(0, len(lines), 42):\n'
                    '            chunk = lines[start:start+42]\n'
                    '            ops = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]\n'
                    '            for line in chunk:\n'
                    '                ops.append(f"({self._pdf_escape(line[:150])}) Tj")\n'
                    '                ops.append("T*")\n'
                    '            ops.append("ET")\n'
                    '            pages.append("\\n".join(ops).encode("latin-1", "replace"))\n'
                    '        objects = []\n'
                    '        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")\n'
                    '        kids = " ".join(f"{3+i*2} 0 R" for i in range(len(pages)))\n'
                    '        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())\n'
                    '        for i, content in enumerate(pages):\n'
                    '            content_obj = 4 + i*2\n'
                    '            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << '
                    '/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} '
                    '0 R >>".encode())\n'
                    '            objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\\nstream\\n" + '
                    'content + b"\\nendstream")\n'
                    '        pdf = bytearray(b"%PDF-1.4\\n")\n'
                    '        offsets = []\n'
                    '        for idx, obj in enumerate(objects, 1):\n'
                    '            offsets.append(len(pdf))\n'
                    '            pdf.extend(f"{idx} 0 obj\\n".encode()); pdf.extend(obj); pdf.extend(b"\\nendobj\\n")\n'
                    '        xref = len(pdf)\n'
                    '        pdf.extend(f"xref\\n0 {len(objects)+1}\\n0000000000 65535 f \\n".encode())\n'
                    '        for off in offsets:\n'
                    '            pdf.extend(f"{off:010d} 00000 n \\n".encode())\n'
                    '        pdf.extend(f"trailer\\n<< /Size {len(objects)+1} /Root 1 0 R '
                    '>>\\nstartxref\\n{xref}\\n%%EOF".encode())\n'
                    '        Path(path).write_bytes(bytes(pdf))\n'
                    '\n'
                    '    def create_simple_pdf(self, title, rows):\n'
                    '        path = filedialog.asksaveasfilename(title="PDF speichern", defaultextension=".pdf", '
                    'filetypes=[("PDF-Dateien", "*.pdf")], initialfile=title.replace(" ", "_").replace("/", "-") + '
                    '".pdf")\n'
                    '        if not path: return\n'
                    '        try:\n'
                    '            self.write_simple_pdf(path, title, rows)\n'
                    '            if messagebox.askyesno("PDF erstellt", "PDF wurde erstellt. Jetzt öffnen?"):\n'
                    '                try:\n'
                    '                    os.startfile(path)\n'
                    '                except Exception:\n'
                    '                    try: subprocess.Popen(["xdg-open", path])\n'
                    '                    except Exception: pass\n'
                    '        except Exception as exc:\n'
                    '            messagebox.showerror("PDF erstellen", f"PDF konnte nicht erstellt '
                    'werden:\\n\\n{exc}")\n'
                    '\n'
                    '    def create_close_report(self):\n'
                    '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                    '        if is_preliminary_report and self.role_rank_value() < 4:\n'
                    '            messagebox.showwarning("Keine Berechtigung", "Der vorläufige Abschlussbericht ist nur '
                    'für E4 exportierbar.")\n'
                    '            return\n'
                    '        if (not is_preliminary_report) and self.role_rank_value() < 3:\n'
                    '            messagebox.showwarning("Keine Berechtigung", "Der Protokoll-Bericht für ganze '
                    'Zeiträume ist nur für E3 und E4 exportierbar.")\n'
                    '            return\n'
                    '        self.ensure_close_metadata()\n'
                    '        with_signature = messagebox.askyesno("Abschlussbericht", f"Bericht '
                    '{period_label(self.period)} mit Signatur- und Freigabefeld erstellen?\\n\\nJa = mit '
                    'Signatur-/Freigabefeld\\nNein = ohne Signatur-/Freigabefeld")\n'
                    '        default_name = '
                    'f"Abschlussbericht_{self.close_type_label()}_{period_label(self.period).replace(\' \', '
                    '\'_\').replace(\'/\', \'-\')}_{date.today().isoformat()}.pdf"\n'
                    '        path = filedialog.asksaveasfilename(title="Bericht-PDF speichern", '
                    'defaultextension=".pdf", filetypes=[("PDF-Dateien", "*.pdf")], initialfile=default_name)\n'
                    '        if not path: return\n'
                    '        try:\n'
                    '            self.create_reportlab_pdf(path, with_signature)\n'
                    '        except Exception as exc:\n'
                    '            try:\n'
                    '                rows = self.build_report_rows()\n'
                    '                self.write_simple_pdf(path, f"Abschlussbericht {self.close_type_label()} '
                    '{period_label(self.period)}", rows)\n'
                    '            except Exception as fallback_exc:\n'
                    '                messagebox.showerror("Abschlussbericht", f"Bericht konnte nicht erstellt '
                    'werden:\\n\\n{exc}\\n\\nFallback fehlgeschlagen:\\n{fallback_exc}")\n'
                    '                return\n'
                    '        if messagebox.askyesno("Bericht-PDF wurde erstellt", "Bericht-PDF wurde erstellt. Jetzt '
                    'öffnen?"):\n'
                    '            try: os.startfile(path)\n'
                    '            except Exception:\n'
                    '                try: subprocess.Popen(["xdg-open", path])\n'
                    '                except Exception: pass\n'
                    '\n'
                    '    def build_report_rows(self):\n'
                    '        rows = []\n'
                    '        for task in self.tasks():\n'
                    '            rows.append([f"{task.get(\'title\',\'\')} | {task.get(\'owner\',\'\')} | '
                    '{due_rule_text(task)} {format_date_de(task.get(\'due_date\'))} | {task.get(\'status\',\'\')}"])\n'
                    '            for sub in task.get("subtasks", []) or []:\n'
                    '                if not sub.get("deleted"):\n'
                    '                    rows.append([f"  - {sub.get(\'title\',\'\')} | {sub.get(\'owner\', '
                    'task.get(\'owner\',\'\'))} | {sub.get(\'status\',\'\')}"])\n'
                    '        return rows\n'
                    '\n'
                    '    def create_reportlab_pdf(self, path, with_signature=False):\n'
                    '        from reportlab.lib import colors\n'
                    '        from reportlab.lib.pagesizes import A4\n'
                    '        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle\n'
                    '        from reportlab.lib.units import cm\n'
                    '        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, '
                    'PageBreak\n'
                    '        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4*cm, leftMargin=1.4*cm, '
                    'topMargin=1.2*cm, bottomMargin=1.2*cm)\n'
                    '        styles = getSampleStyleSheet()\n'
                    '        dark_blue = colors.HexColor("#1F4E79")\n'
                    '        styles.add(ParagraphStyle(name="FMTitle", parent=styles["Title"], '
                    'fontName="Helvetica-Bold", fontSize=16, textColor=dark_blue, spaceAfter=10))\n'
                    '        styles.add(ParagraphStyle(name="FMHead", parent=styles["Heading2"], '
                    'fontName="Helvetica-Bold", fontSize=13, textColor=dark_blue, spaceBefore=10, spaceAfter=6))\n'
                    '        styles.add(ParagraphStyle(name="FMText", parent=styles["BodyText"], fontName="Helvetica", '
                    'fontSize=11, leading=14))\n'
                    '        styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", '
                    'fontSize=8, leading=10))\n'
                    '        story=[]\n'
                    '        story.append(Paragraph(f"Abschlussbericht {self.close_type_label()} '
                    '{period_label(self.period)}", styles["FMTitle"]))\n'
                    '        status = "Abgeschlossen" if self.data.get("closed") else "Nicht abgeschlossen"\n'
                    '        head = [["Berichtstyp", self.close_type_label()], ["Zeitraum", '
                    'period_label(self.period)], ["Abschluss-Stichtag", '
                    'format_date_de(self.data.get("closing_cutoff_date"))], ["Status", status], ["Erstellt durch", '
                    'self.current_user_full_name()], ["Erstellt am", datetime.now().strftime("%d.%m.%Y %H:%M")]]\n'
                    '        if self.data.get("closed_at"): head.append(["Zuletzt abgeschlossen", '
                    'f"{format_datetime_de(self.data.get(\'closed_at\'))} durch '
                    '{self.data.get(\'closed_by\',\'\')}"])\n'
                    '        t=Table(head, colWidths=[5*cm, 11*cm]); '
                    't.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#D9EAF7")),("VALIGN",(0,0),(-1,-1),"TOP")]))\n'
                    '        story += [t, Spacer(1,8)]\n'
                    '        stats=calc_stats(self.tasks())\n'
                    '        story.append(Paragraph("Management Summary", styles["FMHead"]))\n'
                    '        story.append(Paragraph(f"Gesamtaufgaben: {stats[\'total\']} | Erledigt: {stats[\'done\']} '
                    "| Offen: {stats['open']} | In Bearbeitung: {stats['in_progress']} | Überfällig: "
                    '{stats[\'overdue\']} | Kritisch: {stats[\'critical\']}", styles["FMText"]))\n'
                    '        story.append(Paragraph("Abschlussprotokoll", styles["FMHead"]))\n'
                    '        '
                    'events=[["Zeitpunkt","Aktion","Benutzer","Begründung"]]+[[format_datetime_de(e.get("timestamp")), '
                    'e.get("action",""), e.get("user",""), e.get("reason","")] for e in self.data.get("close_events", '
                    '[])]\n'
                    '        story.append(Table(events, repeatRows=1, colWidths=[3.2*cm,2.5*cm,4*cm,6.3*cm], '
                    'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                    '        story.append(Paragraph("Teamübersicht", styles["FMHead"]))\n'
                    '        team_rows=[["Team","Gesamt","Erledigt","Offen","In Bearbeitung","Unteraufgaben"]]\n'
                    '        for team in TEAMS:\n'
                    '            tasks=[t for t in self.tasks() if t.get("team")==team and not t.get("deleted")]\n'
                    '            subs_done=sum(sum(1 for s in t.get("subtasks",[]) if s.get("status")==STATUS_DONE and '
                    'not s.get("deleted")) for t in tasks)\n'
                    '            subs_all=sum(sum(1 for s in t.get("subtasks",[]) if not s.get("deleted")) for t in '
                    'tasks)\n'
                    '            team_rows.append([team,len(tasks),sum(1 for t in tasks if '
                    't.get("status")==STATUS_DONE),sum(1 for t in tasks if t.get("status")==STATUS_OPEN),sum(1 for t '
                    'in tasks if t.get("status")==STATUS_IN_PROGRESS),f"{subs_done}/{subs_all}" if subs_all else ""])\n'
                    '        story.append(Table(team_rows, repeatRows=1, '
                    'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                    '        story.append(Paragraph("Aufgaben und Aufgabengruppen", styles["FMHead"]))\n'
                    '        for i,task in enumerate(self.tasks(),1):\n'
                    '            is_group=bool([s for s in task.get("subtasks",[]) if not s.get("deleted")])\n'
                    '            label="Aufgabengruppe" if is_group else "Aufgabe"\n'
                    '            critical = task.get("deadline_type")=="gesetzlich" or '
                    'task.get("priority")=="kritisch"\n'
                    '            story.append(Paragraph(f"{i}. {label}: {task.get(\'title\',\'\')}", styles["FMHead" '
                    'if critical else "FMText"]))\n'
                    '            story.append(Paragraph(f"Zuständigkeit: {task.get(\'owner\',\'\')} | Fälligkeit: '
                    "{format_date_de(task.get('due_date'))} ({due_rule_text(task)}) | Status: {task.get('status','')} "
                    '| Erledigt: {format_datetime_de(task.get(\'done_at\'))}", styles["FMText"]))\n'
                    "            if 'z4' in task.get('title','').casefold() or 'zm-' in "
                    "task.get('title','').casefold() or 'zm meldung' in task.get('title','').casefold() or 'z5a' in "
                    "task.get('title','').casefold():\n"
                    '                txt = f"<b><i>{task.get(\'title\',\'\')} erfolgt am '
                    '{format_datetime_de(task.get(\'done_at\'))}.</i></b>" if task.get(\'status\')==STATUS_DONE else '
                    'f"<b><i>{task.get(\'title\',\'\')} wurde im Zeitraum nicht als erledigt markiert.</i></b>"\n'
                    '                story.append(Paragraph(txt, styles["FMText"]))\n'
                    '            comments=task.get("comments",[])\n'
                    '            if comments:\n'
                    '                story.append(Paragraph("Kommentare / Notizen", styles["FMText"]))\n'
                    '                for c in comments:\n'
                    '                    story.append(Paragraph(str(c), styles["Small"]))\n'
                    '            attachments=task.get("attachments",[])\n'
                    '            if attachments:\n'
                    '                rows=[["Anlagenname","Anlagenpfad"]]\n'
                    '                for a in attachments:\n'
                    '                    if isinstance(a,dict): rows.append([a.get("name") or '
                    'Path(a.get("path","")).name, a.get("path","") + (f" [{a.get(\'created_at\',\'\')}]" if '
                    'a.get(\'created_at\') else "")])\n'
                    '                    else: rows.append([Path(str(a)).name, str(a)])\n'
                    '                story.append(Paragraph(f"Anlagen: {len(attachments)}", styles["FMText"])); '
                    'story.append(Table(rows, '
                    'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                    '            for j,sub in enumerate([s for s in task.get("subtasks",[]) if not '
                    's.get("deleted")],1):\n'
                    '                story.append(Paragraph(f"{i}.{j} Aufgabe: {sub.get(\'title\',\'\')}", '
                    'styles["FMText"]))\n'
                    '                story.append(Paragraph(f"Zuständigkeit: '
                    '{sub.get(\'owner\',task.get(\'owner\',\'\'))} | Status: {sub.get(\'status\',\'\')}", '
                    'styles["Small"]))\n'
                    '        open_tasks=[t for t in self.tasks() if t.get("status")!=STATUS_DONE and not '
                    't.get("deleted")]\n'
                    '        story.append(Paragraph("Offene Punkte", styles["FMHead"]))\n'
                    '        if open_tasks:\n'
                    '            for tsk in open_tasks: story.append(Paragraph(f"- {tsk.get(\'title\',\'\')}, '
                    'zuständig: {tsk.get(\'owner\',\'\')}, Status: {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                    '        else: story.append(Paragraph("Keine offenen Punkte.", styles["FMText"]))\n'
                    '        critical_tasks=[t for t in self.tasks() if (t.get("deadline_type")=="gesetzlich" or '
                    't.get("priority")=="kritisch" or warning_level(t) in ("overdue","today","orange")) and not '
                    't.get("deleted")]\n'
                    '        story.append(Paragraph("Kritische oder gesetzliche Fristen", styles["FMHead"]))\n'
                    '        for tsk in critical_tasks: story.append(Paragraph(f"- <b>{tsk.get(\'title\',\'\')}</b> | '
                    '{format_date_de(tsk.get(\'due_date\'))} | {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                    '        changes=[c for c in self.data.get("change_log",[]) if c.get("after_reopen")]\n'
                    '        story.append(Paragraph("Nachträgliche Änderungen nach Wiederöffnung", styles["FMHead"]))\n'
                    '        if changes:\n'
                    '            '
                    'rows=[["Zeitpunkt","Benutzer","Aufgabe","Feld","Alt","Neu"]]+[[format_datetime_de(c.get("timestamp")),c.get("user",""),c.get("task_title",""),c.get("field",""),c.get("old",""),c.get("new","")] '
                    'for c in changes]\n'
                    '            story.append(Table(rows, repeatRows=1, '
                    'colWidths=[2.7*cm,3*cm,3.5*cm,2.3*cm,2.2*cm,2.2*cm], '
                    'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#FDE68A")),("FONTSIZE",(0,0),(-1,-1),7)])))\n'
                    '        else: story.append(Paragraph("Keine nachträglichen Änderungen dokumentiert.", '
                    'styles["FMText"]))\n'
                    '        if with_signature:\n'
                    '            story += [Spacer(1,18), Paragraph("Signatur- und Freigabefeld", styles["FMHead"]), '
                    'Spacer(1,16), Paragraph("Erstellt durch: _______________________ Datum: ___________", '
                    'styles["FMText"]), Spacer(1,14), Paragraph("Geprüft durch: ________________________ Datum: '
                    '___________", styles["FMText"]), Spacer(1,14), Paragraph("Freigegeben durch: ____________________ '
                    'Datum: ___________", styles["FMText"])]\n'
                    '        version = getattr(self.app, "version_label_text", lambda: "")()\n'
                    '        footer = f"Bericht automatisch erstellt von {self.current_user_full_name()} am '
                    '{datetime.now().strftime(\'%d.%m.%Y %H:%M\')} mit FiBu Mate {version}."\n'
                    '        story.append(Spacer(1,10)); story.append(Paragraph(footer, styles["Small"]))\n'
                    '        doc.build(story)\n'
                    '\n'
                    '    def create_task_id_report(self, task):\n'
                    '        # v0.436: Einzelaufgaben-PDFs sind deaktiviert. Exportiert werden nur ganze Zeiträume als '
                    'Protokoll-Bericht.\n'
                    '        messagebox.showinfo("Protokoll-Bericht", "Einzelaufgaben-Berichte sind deaktiviert. Bitte '
                    'den Protokoll-Bericht für den gesamten Zeitraum exportieren.")\n'
                    '        return\n'
                    '\n'
                    '    def task_match_key(self, task):\n'
                    '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                    '        if catalog_id:\n'
                    '            return ("catalog", catalog_id)\n'
                    '        return (\n'
                    '            "task",\n'
                    '            str(task.get("id") or "").strip(),\n'
                    '            normalize_team_name(task.get("team")),\n'
                    '            str(task.get("title") or "").strip().casefold(),\n'
                    '        )\n'
                    '\n'
                    '    def find_task_index_exact(self, task):\n'
                    '        tasks = self.data.get("tasks", [])\n'
                    '        for idx, candidate in enumerate(tasks):\n'
                    '            if candidate is task:\n'
                    '                return idx\n'
                    '        key = self.task_match_key(task)\n'
                    '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                    'self.task_match_key(candidate) == key]\n'
                    '        return matches[0] if len(matches) == 1 else None\n'
                    '\n'
                    '    def following_periods(self):\n'
                    '        return [period for period in list_periods() if period > self.period]\n'
                    '\n'
                    '    def remove_task_from_data_by_key(self, data, key):\n'
                    '        tasks = data.get("tasks", [])\n'
                    '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                    'self.task_match_key(candidate) == key]\n'
                    '        if len(matches) == 1:\n'
                    '            tasks.pop(matches[0])\n'
                    '            data["tasks"] = tasks\n'
                    '            return "removed"\n'
                    '        if len(matches) > 1:\n'
                    '            return "ambiguous"\n'
                    '        return "missing"\n'
                    '\n'
                    '    def ask_delete_scope(self, task):\n'
                    '        result = {"scope": None}\n'
                    '        win = tk.Toplevel(self.root)\n'
                    '        win.title("Aufgabe löschen")\n'
                    '        win.configure(bg=COLORS["bg"])\n'
                    '        win.transient(self.root)\n'
                    '        win.grab_set()\n'
                    '        win.geometry("520x245")\n'
                    '        tk.Label(win, text="Aufgabe löschen", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                    '        msg = f"Welche Zeiträume sollen bereinigt werden?\\n\\n{task.get(\'title\', \'\')}"\n'
                    '        if task.get("attachments"):\n'
                    '            msg += "\\n\\nHinweis: Anlagen-Dateien bleiben im Anlagenordner erhalten; nur die '
                    'Referenz in der Aufgabe wird entfernt."\n'
                    '        tk.Label(win, text=msg, bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 12), '
                    'justify="left", wraplength=480).pack(anchor="w", padx=16, pady=(0, 14))\n'
                    '        buttons = tk.Frame(win, bg=COLORS["bg"])\n'
                    '        buttons.pack(fill="x", padx=16, pady=(0, 16))\n'
                    '        def choose(scope):\n'
                    '            result["scope"] = scope\n'
                    '            win.destroy()\n'
                    '        tk.Button(buttons, text="Nur aktueller Zeitraum", command=lambda: choose("current"), '
                    'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0, '
                    '7))\n'
                    '        tk.Button(buttons, text="Aktueller und alle folgenden Zeiträume", command=lambda: '
                    'choose("following"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, '
                    'cursor="hand2").pack(fill="x", pady=(0, 7))\n'
                    '        tk.Button(buttons, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                    'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                    '        win.wait_window()\n'
                    '        return result["scope"]\n'
                    '\n'
                    '    def delete_from_following_periods(self, task_key):\n'
                    '        removed = 0\n'
                    '        ambiguous = 0\n'
                    '        for period in self.following_periods():\n'
                    '            data = load_period(period)\n'
                    '            result = self.remove_task_from_data_by_key(data, task_key)\n'
                    '            if result == "removed":\n'
                    '                save_period(period, data)\n'
                    '                removed += 1\n'
                    '            elif result == "ambiguous":\n'
                    '                ambiguous += 1\n'
                    '        return removed, ambiguous\n'
                    '\n'
                    '    def cleanup_following_periods(self):\n'
                    '            if not self.require_unlocked("Vorlage für Folgezeiträume ist nicht möglich"): return\n'
                    '            return self.sync_current_as_template_to_following_periods()\n'
                    '\n'
                    '    def draw_progress(self, parent, percent, width=260, height=20, bg=None):\n'
                    '        bg = bg or parent.cget("bg")\n'
                    '        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)\n'
                    '        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")\n'
                    '        fill_w = int(width * max(0, min(100, percent)) / 100)\n'
                    '        if fill_w: c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), '
                    'outline=progress_color(percent))\n'
                    '        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], '
                    'font=zfont(self.app, 11, "bold"))\n'
                    '        return c\n'
                    '\n'
                    '    def render_period_controls(self, parent):\n'
                    '        row = tk.Frame(parent, bg=COLORS["bg"])\n'
                    '        row.pack(fill="x", padx=24, pady=(10, 4))\n'
                    '        tk.Button(row, text="< vorherige(r) Quartal", command=lambda: '
                    'self.change_period(add_period(self.period, -1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                    'pady=6).pack(side="left")\n'
                    '        periods = list_periods(); labels = {period_label(k): k for k in periods}; selected = '
                    'tk.StringVar(value=period_label(self.period))\n'
                    '        menu = tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: '
                    'self.change_period(labels[label]))\n'
                    '        menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0); '
                    'menu.pack(side="left", padx=10)\n'
                    '        tk.Button(row, text="nächste(r) Quartal >", command=lambda: '
                    'self.change_period(add_period(self.period, 1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                    'pady=6).pack(side="left")\n'
                    '        tk.Frame(row, bg=COLORS["bg"]).pack(side="left", fill="x", expand=True)\n'
                    '        if self.can_edit(): self.render_edit_button(row)\n'
                    '\n'
                    '    def render_edit_button(self, parent):\n'
                    '        photo = '
                    'self.get_close_icon_photo("1486504369-change-edit-options-pencil-settings-tools-write_81307.ico", '
                    '28, 28)\n'
                    '        btn = tk.Button(\n'
                    '            parent,\n'
                    '            text="" if photo else "Bearbeiten",\n'
                    '            image=photo if photo else "",\n'
                    '            command=self.toggle_edit_mode,\n'
                    '            bg=parent.cget("bg"),\n'
                    '            activebackground=parent.cget("bg"),\n'
                    '            fg=COLORS["blue"],\n'
                    '            bd=0,\n'
                    '            highlightthickness=0,\n'
                    '            padx=2,\n'
                    '            pady=2,\n'
                    '            cursor="hand2",\n'
                    '        )\n'
                    '        if photo:\n'
                    '            btn.image = photo\n'
                    '        btn.pack(side="right", padx=(8, 0))\n'
                    '        btn.bind("<Enter>", lambda _e: self.show_tooltip(btn, "Bearbeiten"))\n'
                    '        btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                    '\n'
                    '    def create_delegate_button(self, parent, item, parent_task=None):\n'
                    '        photo = '
                    'self.get_close_icon_photo("1904671-arrow-arrow-right-change-direction-next-page-right_122521.ico", '
                    '14, 14)\n'
                    '        btn = tk.Button(\n'
                    '            parent,\n'
                    '            text="Delegieren",\n'
                    '            image=photo if photo else "",\n'
                    '            compound="left" if photo else "none",\n'
                    '            command=lambda it=item, pt=parent_task: self.show_delegate_popup(it, pt),\n'
                    '            bg=COLORS["white"],\n'
                    '            activebackground=COLORS["header"],\n'
                    '            fg=COLORS["blue"],\n'
                    '            bd=1,\n'
                    '            relief="solid",\n'
                    '            padx=5,\n'
                    '            pady=2,\n'
                    '            cursor="hand2",\n'
                    '            font=zfont(self.app, 10, "bold"),\n'
                    '        )\n'
                    '        if photo:\n'
                    '            btn.image = photo\n'
                    '        return btn\n'
                    '\n'
                    '    def show_delegate_popup(self, item, parent_task=None):\n'
                    '        if not self.can_edit():\n'
                    '            messagebox.showwarning("FiBu Mate", "Keine Berechtigung zum Delegieren.")\n'
                    '            return\n'
                    '        task_for_team = parent_task or item\n'
                    '        choices = self.user_choices()\n'
                    '        labels = []\n'
                    '        label_to_choice = {}\n'
                    '        current_key = item.get("owner_user_key", "")\n'
                    '        current_label = None\n'
                    '        for key, display in choices:\n'
                    '            label = display if not key else f"{display} ({key})"\n'
                    '            labels.append(label)\n'
                    '            label_to_choice[label] = (key, display)\n'
                    '            if key == current_key:\n'
                    '                current_label = label\n'
                    '        if not labels:\n'
                    '            messagebox.showwarning("FiBu Mate", "Keine Benutzer für die Delegierung vorhanden.")\n'
                    '            return\n'
                    '        if current_label is None:\n'
                    '            current_label = labels[0]\n'
                    '        win = tk.Toplevel(self.root)\n'
                    '        win.title("Zuständigkeit delegieren")\n'
                    '        win.configure(bg=COLORS["bg"])\n'
                    '        win.transient(self.root)\n'
                    '        win.grab_set()\n'
                    '        win.geometry("460x190")\n'
                    '        tk.Label(win, text="Zuständigkeit delegieren", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                    '        tk.Label(win, text="Bitte neue Zuständigkeit wählen.", bg=COLORS["bg"], '
                    'fg=COLORS["text2"], font=zfont(self.app, 12), wraplength=420, justify="left").pack(anchor="w", '
                    'padx=16, pady=(0, 10))\n'
                    '        selected = tk.StringVar(value=current_label)\n'
                    '        menu = tk.OptionMenu(win, selected, *labels)\n'
                    '        menu.config(bg=COLORS["white"], fg=COLORS["text"], bd=1, highlightthickness=0)\n'
                    '        menu.pack(fill="x", padx=16, pady=(0, 14))\n'
                    '        def apply_delegate():\n'
                    '            user_key, display_name = label_to_choice[selected.get()]\n'
                    '            scope = self.ask_delegate_scope(item, parent_task)\n'
                    '            if not scope:\n'
                    '                return\n'
                    '            fallback_team = task_for_team.get("team", item.get("team", "Team"))\n'
                    '            owner_name = display_name if user_key else fallback_team\n'
                    '            targets = [item]\n'
                    '            if parent_task is None:\n'
                    '                targets += [sub for sub in item.get("subtasks", []) if not sub.get("deleted")]\n'
                    '            for target in targets:\n'
                    '                target["owner_user_key"] = user_key\n'
                    '                target["owner"] = owner_name\n'
                    '            self.save()\n'
                    '            changed = 0\n'
                    '            if scope == "permanent" and parent_task is None:\n'
                    '                task_key = self.task_match_key(item)\n'
                    '                changed = self.apply_delegate_to_following_periods(task_key, owner_name, '
                    'user_key)\n'
                    '            if user_key:\n'
                    '                self.send_delegation_email(user_key, display_name, task_for_team.get("title", '
                    'item.get("title", "")), scope)\n'
                    '            if self.selected_team:\n'
                    '                self.render_team_detail(self.selected_team)\n'
                    '            win.destroy()\n'
                    '            if scope == "permanent":\n'
                    '                messagebox.showinfo("Delegierung", f"Permanente Delegierung übertragen. '
                    'Folgezeiträume aktualisiert: {changed}")\n'
                    '        footer = tk.Frame(win, bg=COLORS["bg"])\n'
                    '        footer.pack(fill="x", padx=16, pady=(0, 14))\n'
                    '        tk.Button(footer, text="Übernehmen", command=apply_delegate, bg=COLORS["blue"], '
                    'fg="white", bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")\n'
                    '        tk.Button(footer, text="Abbrechen", command=win.destroy, bg=COLORS["header"], '
                    'fg=COLORS["text"], bd=0, padx=14, pady=7, cursor="hand2").pack(side="right", padx=(0, 8))\n'
                    '\n'
                    '    def show_tooltip(self, widget, text):\n'
                    '        self.hide_tooltip(); self.tooltip = tk.Toplevel(widget); '
                    'self.tooltip.wm_overrideredirect(True); self.tooltip.geometry(f"+{widget.winfo_rootx() + '
                    '12}+{widget.winfo_rooty() + 34}"); tk.Label(self.tooltip, text=text, bg="#111827", fg="white", '
                    'font=zfont(self.app, 11), padx=6, pady=3).pack()\n'
                    '\n'
                    '    def hide_tooltip(self):\n'
                    '        if self.tooltip:\n'
                    '            try: self.tooltip.destroy()\n'
                    '            except Exception: pass\n'
                    '        self.tooltip = None\n'
                    '\n'
                    '    def toggle_edit_mode(self):\n'
                    '        self.edit_mode = not self.edit_mode\n'
                    '        self.render_team_detail(self.selected_team) if self.selected_team else '
                    'self.render_dashboard()\n'
                    '\n'
                    '    def render_edit_tools(self, parent, team=None):\n'
                    '        if not (self.can_edit() and self.edit_mode): return\n'
                    '        row = tk.Frame(parent, bg=COLORS["edit_bg"], bd=1, relief="solid"); row.pack(fill="x", '
                    'padx=24, pady=(0, 8))\n'
                    '        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).pack(side="left", padx=10, pady=7)\n'
                    '        if team:\n'
                    '            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: '
                    'self.open_task_dialog(team), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5, '
                    'font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                    '            tk.Button(row, text="Aufgaben allen vorhandenen Perioden zuweisen", '
                    'command=self.apply_current_tasks_to_all_periods, bg=COLORS["orange"], fg="white", bd=0, padx=12, '
                    'pady=5, font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                    '            tk.Button(row, text="Diesen Zeitraum als Vorlage für Folgequartale verwenden", '
                    'command=self.cleanup_following_periods, bg=COLORS["red"], fg="white", bd=0, padx=12, '
                    'pady=5).pack(side="left", padx=8)\n'
                    '\n'
                    '    def change_period(self, period):\n'
                    '        if not period_allowed(period):\n'
                    '            messagebox.showinfo("Quartalsabschluss", "Dieser Zeitraum liegt außerhalb der '
                    'freigegebenen Zeitraumlogik ab Q2 2026 bzw. außerhalb des zulässigen Geschäftsjahres.")\n'
                    '            return\n'
                    '        self.period = period; self.reload(); self.selected_team = None; self.render_dashboard()\n'
                    '\n'
                    '    def save_cutoff_from_entry(self, entry_var=None):\n'
                    '        messagebox.showinfo(\n'
                    '            "FiBu Mate",\n'
                    '            "Der Abschluss-Stichtag wird zentral in der Stichtagspflege gepflegt.\\n\\n"\n'
                    '            "Eine manuelle Änderung in der Zeitraumsübersicht ist nicht mehr möglich."\n'
                    '        )\n'
                    '\n'
                    '    def render_dashboard(self):\n'
                    '        self.ensure_close_metadata()\n'
                    '        old_cutoff = self.data.get("closing_cutoff_date", "")\n'
                    '        normalize_cutoff(self.data, self.period)\n'
                    '        if old_cutoff != self.data.get("closing_cutoff_date", ""):\n'
                    '            save_period(self.period, self.data)\n'
                    '            self.data = load_period(self.period)\n'
                    '        self.selected_team = None; self.clear_frame(); self.render_period_controls(self.frame); '
                    'self.render_edit_tools(self.frame)\n'
                    '        stats = calc_stats(self.tasks())\n'
                    '        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); top.pack(fill="x", '
                    'padx=24, pady=(8, 10))\n'
                    '        title_row = tk.Frame(top, bg=COLORS["white"]); title_row.pack(fill="x", padx=14, pady=(6, '
                    '2))\n'
                    '        tk.Label(title_row, text=f"Quartalsabschluss {period_label(self.period)}", '
                    'bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 24, "bold")).pack(side="left")\n'
                    '        cutoff_text = format_date_de(self.data.get("closing_cutoff_date")) or "nicht gepflegt"\n'
                    '        tk.Label(title_row, text="Abschluss-Stichtag", bg=COLORS["white"], fg=COLORS["text2"], '
                    'font=zfont(self.app, 12, "bold")).pack(side="left", padx=(24, 6))\n'
                    '        tk.Label(title_row, text=cutoff_text, bg="#F8FAFC", fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), relief="solid", bd=1, padx=8, pady=3).pack(side="left")\n'
                    '        toggle_text = f"{period_label(self.period)} {\'öffnen\' if self.is_period_closed() else '
                    '\'abschließen\'}"\n'
                    '        enabled = self.can_toggle_period_close() and (self.is_period_closed() or '
                    'self.is_after_cutoff())\n'
                    '        tooltip = "Abschluss erst nach Ablauf des Abschluss-Stichtags möglich" if '
                    'self.can_toggle_period_close() and not self.is_period_closed() and not self.is_after_cutoff() '
                    'else ""\n'
                    '        self.create_icon_button(title_row, toggle_text, self.toggle_period_close, "unlock" if '
                    'self.is_period_closed() else "lock", enabled, tooltip).pack(side="left", padx=(8,0))\n'
                    '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                    '        report_text = "vorläufigen Abschlussbericht erstellen" if is_preliminary_report else '
                    '"Abschlussbericht erstellen"\n'
                    '        if (self.role_rank_value() >= 4 if is_preliminary_report else self.role_rank_value() >= '
                    '3):\n'
                    '            tk.Button(title_row, text=report_text, command=self.create_close_report, '
                    'bg=COLORS["white"], fg=COLORS["blue"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                    'padx=(8, 0))\n'
                    '        tk.Button(title_row, text="Änderungsprotokoll anzeigen", command=self.show_change_log, '
                    'bg=COLORS["white"], fg=COLORS["text"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                    'padx=(8,0))\n'
                    '        status_text = self.close_status_text()\n'
                    '        if status_text:\n'
                    '            tk.Label(top, text=status_text, bg=COLORS["white"], fg=COLORS["orange"] if not '
                    'self.is_period_closed() else COLORS["dark_green"], font=zfont(self.app, 12, '
                    '"bold")).pack(anchor="w", padx=14, pady=(2,0))\n'
                    '        tk.Label(top, text=f"Gesamt: {stats[\'done\']} erledigt / {stats[\'in_progress\']} in '
                    "Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} "
                    'überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", '
                    'padx=14)\n'
                    '        holder = tk.Frame(top, bg=COLORS["white"]); holder.pack(anchor="w", padx=14, pady=(8, '
                    '10)); self.draw_progress(holder, stats["percent"], width=520, height=24, '
                    'bg=COLORS["white"]).pack(side="left")\n'
                    '        self.render_warnings(self.frame)\n'
                    '        cards = tk.Frame(self.frame, bg=COLORS["bg"]); cards.pack(fill="both", expand=True, '
                    'padx=24, pady=8)\n'
                    '        for idx, team in enumerate(TEAMS): self.render_team_card(cards, team, idx)\n'
                    '        self.bind_module_ctrl_mousewheel_guard()\n'
                    '\n'
                    '    def render_warnings(self, parent):\n'
                    '        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", '
                    '"yellow") and t.get("status") != STATUS_DONE]\n'
                    '        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid"); '
                    'box.pack(fill="x", padx=24, pady=(0, 8))\n'
                    '        if warnings:\n'
                    '            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} '
                    'Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=zfont(self.app, 14, "bold")).pack(anchor="w", '
                    'padx=12, pady=(8, 3))\n'
                    '            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:\n'
                    '                tk.Label(box, text=f"- {task[\'title\']} | {task[\'team\']} | fällig am '
                    '{format_date_de(task.get(\'due_date\'))} | {task.get(\'deadline_type\')}", bg=box["bg"], '
                    'fg=COLORS["text"], font=zfont(self.app, 12)).pack(anchor="w", padx=20, pady=1)\n'
                    '        else:\n'
                    '            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], '
                    'fg=COLORS["dark_green"], font=zfont(self.app, 13, "bold")).pack(anchor="w", padx=12, pady=8)\n'
                    '\n'
                    '    def next_relevant_task(self, tasks):\n'
                    '        open_tasks = [t for t in tasks if t.get("status") != STATUS_DONE and '
                    't.get("deadline_type") != "keine"]\n'
                    '        return sorted(open_tasks, key=lambda t: parse_date(t.get("due_date", "9999-12-31")) or '
                    'date.max)[0] if open_tasks else None\n'
                    '\n'
                    '    def bind_click_recursive(self, widget, command):\n'
                    '        widget.bind("<Button-1>", lambda _e: command()); widget.configure(cursor="hand2")\n'
                    '        for child in widget.winfo_children():\n'
                    '            if isinstance(child, (tk.Entry, tk.Text, tk.Button)): continue\n'
                    '            self.bind_click_recursive(child, command)\n'
                    '\n'
                    '    def save_team_members_from_widget(self, team, widget):\n'
                    '        set_team_members_text(self.data, team, widget.get("1.0", "end")); self.save(); '
                    'self.propagate_team_members_to_related_periods(); self.reload(); self.render_dashboard()\n'
                    '\n'
                    '    def render_team_members_on_card(self, card, team):\n'
                    '        names = normalize_team_members(self.data).get(team, [])\n'
                    '        if self.edit_mode and self.can_edit():\n'
                    '            edit_box = tk.Text(card, height=3, width=42, bg="#F8FAFC", fg=COLORS["text"], '
                    'relief="solid", bd=1); edit_box.insert("1.0", "\\n".join(names)); edit_box.pack(anchor="w", '
                    'padx=18, pady=(0, 6))\n'
                    '            tk.Button(card, text="Namen speichern", command=lambda t=team, w=edit_box: '
                    'self.save_team_members_from_widget(t, w), bg=COLORS["blue"], fg="white", bd=0, padx=8, '
                    'pady=3).pack(anchor="w", padx=18, pady=(0, 10))\n'
                    '        elif names:\n'
                    '            tk.Label(card, text=" • ".join(names), bg=COLORS["white"], fg=COLORS["text2"], '
                    'font=zfont(self.app, 12), wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, '
                    '12))\n'
                    '\n'
                    '    def render_team_card(self, parent, team, idx):\n'
                    '        row, col = divmod(idx, 2); tasks = self.team_tasks(team); stats = calc_stats(tasks)\n'
                    '        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, '
                    '"orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")\n'
                    '        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == '
                    '"orange" else COLORS["line"]\n'
                    '        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", '
                    'highlightbackground=border, highlightcolor=border, highlightthickness=2); card.grid(row=row, '
                    'column=col, padx=12, pady=12, sticky="nsew")\n'
                    '        parent.grid_columnconfigure(col, weight=1); parent.grid_rowconfigure(row, weight=1)\n'
                    '        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 19, '
                    '"bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                    '        tk.Label(card, text=f"{stats[\'done\']} / {stats[\'total\']} erledigt | offen: '
                    '{stats[\'open\']} | in Bearbeitung: {stats[\'in_progress\']} | kritisch: {stats[\'critical\']}", '
                    'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 13)).pack(anchor="w", padx=18)\n'
                    '        holder = tk.Frame(card, bg=COLORS["white"]); holder.pack(anchor="w", padx=18, pady=(10, '
                    '8)); self.draw_progress(holder, stats["percent"], width=420, height=26, '
                    'bg=COLORS["white"]).pack()\n'
                    '        nxt = self.next_relevant_task(tasks); txt = "Nächste Frist: keine relevanten offenen '
                    'Fristen" if not nxt else f"Nächste Frist: {format_date_de(nxt.get(\'due_date\'))} | '
                    '{nxt.get(\'title\')}"\n'
                    '        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and '
                    'warning_level(nxt) in ("overdue", "today", "orange") else COLORS["text2"], font=zfont(self.app, '
                    '12, "bold")).pack(anchor="w", padx=18, pady=(0, 5))\n'
                    '        self.render_team_members_on_card(card, team); self.bind_click_recursive(card, lambda '
                    't=team: self.render_team_detail(t))\n'
                    '\n'
                    '    def render_team_detail(self, team):\n'
                    '        self.selected_team = team; self.clear_frame(); self.render_period_controls(self.frame); '
                    'self.render_edit_tools(self.frame, team=team); stats = calc_stats(self.team_tasks(team))\n'
                    '        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); '
                    'head.pack(fill="x", padx=24, pady=(8, 10))\n'
                    '        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], '
                    'fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))\n'
                    '        tk.Label(head, text=f"{team} | Quartalsabschluss {period_label(self.period)}", '
                    'bg=COLORS["white"], fg=COLORS["text"], font=zfont(self.app, 21, "bold")).pack(anchor="w", '
                    'padx=12)\n'
                    '        tk.Label(head, text=f"Fortschritt: {stats[\'done\']} / {stats[\'total\']} erledigt | '
                    '{stats[\'percent\']}%", bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, '
                    '13)).pack(anchor="w", padx=12)\n'
                    '        bar = tk.Frame(head, bg=COLORS["white"]); bar.pack(anchor="w", padx=12, pady=(6, 10)); '
                    'self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()\n'
                    '        self.render_task_table(team)\n'
                    '        self.bind_module_ctrl_mousewheel_guard()\n'
                    '\n'
                    '    def toggle_subtasks_visibility(self, task_id):\n'
                    '        if task_id in self.expanded_tasks:\n'
                    '            self.expanded_tasks.remove(task_id)\n'
                    '        else:\n'
                    '            self.expanded_tasks.add(task_id)\n'
                    '        self.render_team_detail(self.selected_team)\n'
                    '\n'
                    '    def normalize_documentation_fields(self, item):\n'
                    '        item.setdefault("attachments", [])\n'
                    '        item.setdefault("comments", [])\n'
                    '        doc = item.get("documentation")\n'
                    '        if isinstance(doc, str):\n'
                    '            item["documentation"] = {"name": os.path.basename(doc), "path": doc, "updated_at": '
                    '""} if doc else {}\n'
                    '        elif not isinstance(doc, dict):\n'
                    '            item["documentation"] = {}\n'
                    '        clean_attachments = []\n'
                    '        for att in item.get("attachments", []):\n'
                    '            if isinstance(att, str):\n'
                    '                clean_attachments.append({"name": os.path.basename(att), "path": att, "comment": '
                    '"", "added_at": ""})\n'
                    '            elif isinstance(att, dict):\n'
                    '                att.setdefault("name", os.path.basename(att.get("path", "")) or att.get("name", '
                    '"Anlage"))\n'
                    '                att.setdefault("path", "")\n'
                    '                att.setdefault("comment", "")\n'
                    '                clean_attachments.append(att)\n'
                    '        item["attachments"] = clean_attachments\n'
                    '        return item\n'
                    '\n'
                    '    def due_display_inline(self, task):\n'
                    '        date_text = format_date_de(task.get("due_date", ""))\n'
                    '        rule = due_rule_text(task)\n'
                    '        return f"{date_text} - {rule}" if rule else date_text\n'
                    '\n'
                    '    def find_subtask(self, task_id, subtask_id):\n'
                    '        task = self.find_task(task_id)\n'
                    '        if not task:\n'
                    '            return None, None\n'
                    '        for sub in task.get("subtasks", []):\n'
                    '            if sub.get("id") == subtask_id and not sub.get("deleted"):\n'
                    '                self.normalize_documentation_fields(sub)\n'
                    '                return task, sub\n'
                    '        return task, None\n'
                    '\n'
                    '    def documentation_count(self, item):\n'
                    '        self.normalize_documentation_fields(item)\n'
                    '        return 1 if item.get("documentation", {}).get("path") else 0\n'
                    '\n'
                    '    def attachment_count(self, item):\n'
                    '        self.normalize_documentation_fields(item)\n'
                    '        return len([a for a in item.get("attachments", []) if a.get("path")])\n'
                    '\n'
                    '    def get_close_icon_photo(self, icon_file, max_w=24, max_h=24):\n'
                    '        try:\n'
                    '            from PIL import Image, ImageTk\n'
                    '        except Exception:\n'
                    '            return None\n'
                    '        if not hasattr(self, "_icon_cache"):\n'
                    '            self._icon_cache = {}\n'
                    '        cache_key = (icon_file, int(max_w), int(max_h))\n'
                    '        if cache_key in self._icon_cache:\n'
                    '            return self._icon_cache[cache_key]\n'
                    '        icon_dir = Path(__file__).resolve().parent.parent / "Imgs" / "Icons" if '
                    'Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / '
                    '"bin" / "Imgs" / "Icons"\n'
                    '        path = icon_dir / icon_file\n'
                    '        if not path.exists():\n'
                    '            return None\n'
                    '        try:\n'
                    '            img = Image.open(path).convert("RGBA")\n'
                    '            ow, oh = img.size\n'
                    '            scale = min(1, max_w / max(1, ow), max_h / max(1, oh))\n'
                    '            img = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))\n'
                    '            photo = ImageTk.PhotoImage(img)\n'
                    '            self._icon_cache[cache_key] = photo\n'
                    '            return photo\n'
                    '        except Exception:\n'
                    '            return None\n'
                    '\n'
                    '    def create_attachment_button(self, parent, item, command):\n'
                    '        frame = tk.Frame(parent, bg=parent.cget("bg"))\n'
                    '        inner = tk.Frame(frame, bg=parent.cget("bg"))\n'
                    '        inner.place(relx=0.5, rely=0.5, anchor="center")\n'
                    '        photo = self.get_close_icon_photo("-attach-file_90371.ico", 18, 18)\n'
                    '        btn = tk.Button(inner, text="" if photo else "📎", image=photo, command=command, '
                    'bg=parent.cget("bg"), fg=COLORS["blue"], bd=0, cursor="hand2", padx=0, pady=0)\n'
                    '        if photo:\n'
                    '            btn.image = photo\n'
                    '        btn.pack(side="left", padx=(0, 3))\n'
                    '        tk.Label(inner, text=str(self.attachment_count(item)), bg=parent.cget("bg"), '
                    'fg=COLORS["blue"], font=zfont(self.app, 12, "bold")).pack(side="left")\n'
                    '        return frame\n'
                    '\n'
                    '    def draw_documentation_icon(self, canvas, has_documentation):\n'
                    '        canvas.delete("all")\n'
                    '        icon_file = "fileinterfacesymboloftextpapersheet_79740.ico" if has_documentation else '
                    '"addfileinterfacesymbolofpapersheetwithtextlinesandplussign_79821.ico"\n'
                    '        photo = self.get_close_icon_photo(icon_file, 22, 22)\n'
                    '        if photo:\n'
                    '            canvas.create_image(16, 12, image=photo)\n'
                    '            canvas.image = photo\n'
                    '            return\n'
                    '        color = COLORS["blue"]\n'
                    '        # Fallback ohne blaue Kachel: kleines Dokument-/Plus-Symbol nur als Liniengrafik.\n'
                    '        canvas.create_rectangle(8, 3, 22, 21, outline=color, width=2)\n'
                    '        canvas.create_line(18, 3, 22, 7, fill=color, width=2)\n'
                    '        if has_documentation:\n'
                    '            for y in (9, 13, 17):\n'
                    '                canvas.create_line(11, y, 20, y, fill=color, width=2, capstyle="round")\n'
                    '        else:\n'
                    '            canvas.create_line(15, 9, 15, 18, fill=color, width=2, capstyle="round")\n'
                    '            canvas.create_line(10, 13, 20, 13, fill=color, width=2, capstyle="round")\n'
                    '\n'
                    '    def create_documentation_button(self, parent, item, title, parent_task=None):\n'
                    '        has_doc = bool(item.get("documentation", {}).get("path"))\n'
                    '        bg = parent.cget("bg")\n'
                    '        btn = tk.Canvas(parent, width=32, height=24, bg=bg, highlightthickness=0, bd=0, '
                    'cursor="hand2")\n'
                    '        self.draw_documentation_icon(btn, has_doc)\n'
                    '        btn.bind("<Button-1>", lambda _e, it=item, t=title, pt=parent_task: '
                    'self.show_documentation_popup(it, t, pt))\n'
                    '        return btn\n'
                    '\n'
                    '    def show_documentation_popup(self, item, title, parent_task=None):\n'
                    '        self.normalize_documentation_fields(item)\n'
                    '        win = tk.Toplevel(self.root)\n'
                    '        win.title(f"Dokumentation - {title}")\n'
                    '        win.configure(bg=COLORS["bg"])\n'
                    '        win.geometry("720x270")\n'
                    '        win.transient(self.root)\n'
                    '        win.grab_set()\n'
                    '        tk.Label(win, text="Dokumentation", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(14, 8))\n'
                    '        body = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                    '        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))\n'
                    '        doc = item.get("documentation", {})\n'
                    '        name_var = tk.StringVar(value=doc.get("name", "Noch keine Dokumentation hinterlegt"))\n'
                    '        path_var = tk.StringVar(value=doc.get("path", ""))\n'
                    '\n'
                    '        row = tk.Frame(body, bg=COLORS["white"])\n'
                    '        row.pack(fill="x", padx=12, pady=(14, 6))\n'
                    '        open_button = tk.Button(row, text="Dokumentation öffnen", command=lambda: '
                    'self.open_attachment(path_var.get()), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6, '
                    'state="normal" if path_var.get() else "disabled")\n'
                    '        open_button.pack(side="left")\n'
                    '        tk.Label(row, textvariable=name_var, bg=COLORS["white"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12), anchor="w").pack(side="left", padx=(10, 6), fill="x", expand=True)\n'
                    '\n'
                    '        def refresh_after_change():\n'
                    '            if self.selected_team:\n'
                    '                self.render_team_detail(self.selected_team)\n'
                    '\n'
                    '        def choose_documentation():\n'
                    '            selected = filedialog.askopenfilename(title="Dokumentation auswählen")\n'
                    '            if not selected:\n'
                    '                return\n'
                    '            item["documentation"] = {"name": os.path.basename(selected), "path": selected, '
                    '"updated_at": datetime.now().isoformat(timespec="seconds")}\n'
                    '            self.save()\n'
                    '            name_var.set(os.path.basename(selected))\n'
                    '            path_var.set(selected)\n'
                    '            refresh_after_change()\n'
                    '            win.destroy()\n'
                    '\n'
                    '        def remove_documentation():\n'
                    '            if not path_var.get():\n'
                    '                return\n'
                    '            if not messagebox.askyesno("Dokumentation entfernen", "Dokumentation entfernen?", '
                    'parent=win):\n'
                    '                return\n'
                    '            item["documentation"] = {}\n'
                    '            self.save()\n'
                    '            name_var.set("Noch keine Dokumentation hinterlegt")\n'
                    '            path_var.set("")\n'
                    '            refresh_after_change()\n'
                    '            win.destroy()\n'
                    '\n'
                    '        if path_var.get():\n'
                    '            trash_photo = self.get_close_icon_photo("biggarbagebin_121980.ico", 20, 20)\n'
                    '            delete_btn = tk.Button(row, text="" if trash_photo else "🗑", image=trash_photo, '
                    'command=remove_documentation, bg=COLORS["white"], fg=COLORS["red"], bd=0, padx=2, pady=2, '
                    'cursor="hand2")\n'
                    '            if trash_photo:\n'
                    '                delete_btn.image = trash_photo\n'
                    '            delete_btn.pack(side="right", padx=(6, 0))\n'
                    '\n'
                    '        change = tk.Label(body, text="Dokumentationspfad ändern" if path_var.get() else '
                    '"Dokumentation anhängen", bg=COLORS["white"], fg=COLORS["blue"], font=zfont(self.app, 12, None, '
                    'underline=True), cursor="hand2")\n'
                    '        change.pack(anchor="w", padx=12, pady=(4, 10))\n'
                    '        change.bind("<Button-1>", lambda _e: choose_documentation())\n'
                    '        tk.Label(body, text="Hinweis: Die Dokumentation ist für Aufgabenbeschreibungen bzw. '
                    'Leitfäden vorgesehen. Ergebnisse und Bearbeitungskommentare bitte unter Anlagen pflegen.", '
                    'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=660, '
                    'justify="left").pack(anchor="w", padx=12, pady=(0, 10))\n'
                    '        tk.Button(win, text="Schließen", command=win.destroy, bg=COLORS["blue"], fg="white", '
                    'bd=0, padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))\n'
                    '\n'
                    '    def render_task_table(self, team):\n'
                    '        outer = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")\n'
                    '        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))\n'
                    '\n'
                    '        scroll_canvas = tk.Canvas(outer, bg=COLORS["white"], highlightthickness=0, bd=0)\n'
                    '        scrollbar = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)\n'
                    '        xscrollbar = tk.Scrollbar(outer, orient="horizontal", command=scroll_canvas.xview)\n'
                    '        table = tk.Frame(scroll_canvas, bg="#E4EAF1")  # dezente Spaltentrennlinien\n'
                    '        table_window = scroll_canvas.create_window((0, 0), window=table, anchor="nw")\n'
                    '\n'
                    '        def update_scrollregion(_event=None):\n'
                    '            table.update_idletasks()\n'
                    '            target_width = max(scroll_canvas.winfo_width(), table.winfo_reqwidth())\n'
                    '            scroll_canvas.itemconfigure(table_window, width=max(1, target_width))\n'
                    '            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))\n'
                    '\n'
                    '        def on_mousewheel(event):\n'
                    '            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")\n'
                    '            return "break"\n'
                    '\n'
                    '        table.bind("<Configure>", update_scrollregion)\n'
                    '        scroll_canvas.bind("<Configure>", update_scrollregion)\n'
                    '        scroll_canvas.bind("<MouseWheel>", on_mousewheel)\n'
                    '        table.bind("<MouseWheel>", on_mousewheel)\n'
                    '        scroll_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)\n'
                    '        xscrollbar.pack(side="bottom", fill="x")\n'
                    '        scroll_canvas.pack(side="left", fill="both", expand=True)\n'
                    '        scrollbar.pack(side="right", fill="y")\n'
                    '        self.app.active_scroll_canvas = scroll_canvas\n'
                    '        self._live_task_widgets = {}\n'
                    '        self._live_subtask_widgets = {}\n'
                    '\n'
                    '        headers = ["Status", "Aufgabe", "Dokumentation", "Zuständig", "Fällig", "Fristart", '
                    '"Priorität", "Wiederkehrend", "Anlagen", "Aktion"]\n'
                    '        if self.edit_mode and self.can_edit():\n'
                    '            headers.append("Bearbeiten")\n'
                    '        for col, h in enumerate(headers):\n'
                    '            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=zfont(self.app, '
                    '12, "bold"), padx=6, pady=6).grid(row=0, column=col, sticky="nsew")\n'
                    '        row_idx = 1\n'
                    '        for task in self.team_tasks(team):\n'
                    '            sync_parent_status_from_subtasks(task)\n'
                    '            self.normalize_documentation_fields(task)\n'
                    '            for sub in task.get("subtasks", []):\n'
                    '                self.normalize_documentation_fields(sub)\n'
                    '            row_idx = self.render_task_row(table, row_idx, task, headers)\n'
                    '\n'
                    '        # Spaltenbreiten: Aufgabe und Zuständig etwas reduziert; Dokumentation schmal; '
                    'Fristart/Priorität/Anlagen erhalten mehr Raum.\n'
                    '        min_sizes = {0: 46, 1: 560, 2: 92, 3: 225, 4: 220, 5: 105, 6: 105, 7: 120, 8: 100, 9: 88, '
                    '10: 150}\n'
                    '        stretch_cols = {1: 2, 4: 2, 5: 1, 6: 1, 8: 1}\n'
                    '        for col in range(len(headers)):\n'
                    '            table.grid_columnconfigure(col, minsize=min_sizes.get(col, 80), '
                    'weight=stretch_cols.get(col, 0))\n'
                    '        update_scrollregion()\n'
                    '\n'
                    '\n'
                    '    def render_task_row(self, table, row_idx, task, headers):\n'
                    '        current_row_idx = row_idx\n'
                    '        bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) '
                    'in ("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", "IMS":"#FFF4CC", '
                    '"SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), COLORS["white"])\n'
                    '        can_finish = not task.get("subtasks") or all_subtasks_done(task)\n'
                    '        can_complete = self.can_complete_task(task)\n'
                    '        btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", '
                    'command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE '
                    'else bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, '
                    'font=zfont(self.app, 15, "bold"), state="normal" if can_complete else "disabled")\n'
                    '        btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                    '        if not can_complete:\n'
                    '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Nur zuständige Person '
                    'darf erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                    '        elif task.get("subtasks") and not can_finish:\n'
                    '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Bitte erst alle '
                    'Unteraufgaben erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                    '\n'
                    '        task_cell = tk.Frame(table, bg=bg)\n'
                    '        task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                    '        visible_subtasks = sorted([s for s in task.get("subtasks", []) if not s.get("deleted")], '
                    'key=lambda s: str(s.get("title", "")).casefold())\n'
                    '\n'
                    '        task_actions = tk.Frame(task_cell, bg=bg)\n'
                    '        task_actions.pack(side="right", padx=(6, 8), pady=3)\n'
                    '        if visible_subtasks:\n'
                    '            expand_key = self.get_expand_key(task)\n'
                    '            expanded = expand_key in self.expanded_tasks\n'
                    '            toggle_text = "Unteraufgaben einklappen v" if expanded else "Unteraufgaben ausklappen '
                    '>"\n'
                    '            tk.Button(task_actions, text=toggle_text, command=lambda key=expand_key: '
                    'self.toggle_subtasks_visibility(key), bg=bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, '
                    'cursor="hand2", font=zfont(self.app, 10, "bold")).pack(side="right", padx=(0, 6))\n'
                    '\n'
                    '        task_text = tk.Frame(task_cell, bg=bg)\n'
                    '        task_text.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=4)\n'
                    '        tk.Label(task_text, text=str(task.get("title", "")), bg=bg, fg=COLORS["text"], '
                    'font=zfont(self.app, 12), anchor="w", justify="left", wraplength=430).pack(anchor="w", fill="x", '
                    'expand=True)\n'
                    '\n'
                    '        doc_frame = tk.Frame(table, bg=bg)\n'
                    '        doc_frame.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)\n'
                    '        # v0.520: Dokumentations-Button auch bei Aufgabengruppen anzeigen.\n'
                    '        self.create_documentation_button(doc_frame, task, task.get("title", '
                    '"Aufgabe")).pack(padx=5, pady=3)\n'
                    '\n'
                    '        owner_cell = tk.Frame(table, bg=bg)\n'
                    '        owner_cell.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)\n'
                    '        tk.Label(owner_cell, text=task.get("owner"), bg=bg, fg=COLORS["text"], '
                    'font=zfont(self.app, 12), padx=6, pady=6, anchor="center", justify="center").pack(side="left", '
                    'fill="x", expand=True)\n'
                    '        if self.can_edit():\n'
                    '            self.create_delegate_button(owner_cell, task).pack(side="right", padx=(2, 5), '
                    'pady=3)\n'
                    '\n'
                    '        values = [self.due_display_inline(task), task.get("deadline_type"), task.get("priority"), '
                    '"Ja" if task.get("recurring") else "Nein"]\n'
                    '        aligns = [("w", "left"), ("center", "center"), ("center", "center"), ("center", '
                    '"center")]\n'
                    '        for offset, val in enumerate(values):\n'
                    '            anchor, justify = aligns[offset]\n'
                    '            tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=zfont(self.app, 12), padx=6, '
                    'pady=6, anchor=anchor, justify=justify).grid(row=row_idx, column=4 + offset, sticky="nsew", '
                    'padx=1, pady=1)\n'
                    '        self.create_attachment_button(table, task, lambda t=task: '
                    'self.show_attachments(t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)\n'
                    '        status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))\n'
                    '        menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: '
                    'self.set_status(t, value))\n'
                    '        menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0, state="normal" if '
                    'can_complete else "disabled")\n'
                    '        menu.grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)\n'
                    '        self._register_live_task_widgets(table, current_row_idx, task, btn, status_var, menu)\n'
                    '        if self.edit_mode and self.can_edit():\n'
                    '            action = tk.Frame(table, bg=bg); action.grid(row=row_idx, column=10, sticky="nsew", '
                    'padx=1, pady=1)\n'
                    '            tk.Button(action, text="Bearbeiten", command=lambda t=task: '
                    'self.open_task_dialog(task.get("team"), t), bg=COLORS["blue"], fg="white", bd=0, padx=6, pady=3, '
                    'font=zfont(self.app, 10, "bold")).pack(side="left", padx=2, pady=3)\n'
                    '            tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), '
                    'bg=COLORS["red"], fg="white", bd=0, padx=6, pady=3, font=zfont(self.app, 10, '
                    '"bold")).pack(side="left", padx=2, pady=3)\n'
                    '        row_idx += 1\n'
                    '\n'
                    '        if self.get_expand_key(task) in self.expanded_tasks:\n'
                    '            for sub in visible_subtasks:\n'
                    '                self.normalize_documentation_fields(sub)\n'
                    '                sub.setdefault("subtasks", [])\n'
                    '                visible_sub_subtasks = [c for c in sub.get("subtasks", []) or [] if not '
                    'c.get("deleted") and str(c.get("title", "")).strip()]\n'
                    '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                    '                sub_row_idx = row_idx\n'
                    '                sub_btn = tk.Button(table, text="✓" if sub.get("status") == STATUS_DONE else "□", '
                    'command=lambda t=task, s=sub: self.toggle_subtask(t, s), bg="#BBF7D0" if sub.get("status") == '
                    'STATUS_DONE else sub_bg, fg=COLORS["dark_green"] if sub.get("status") == STATUS_DONE else '
                    'COLORS["text"], bd=0, font=zfont(self.app, 14, "bold"), state="normal" if can_complete else '
                    '"disabled")\n'
                    '                sub_btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                    '                sub_task_cell = tk.Frame(table, bg=sub_bg)\n'
                    '                sub_task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                    '                sub_action = tk.Frame(sub_task_cell, bg=sub_bg)\n'
                    '                sub_action.pack(side="right", padx=(6, 8), pady=3)\n'
                    '                if visible_sub_subtasks:\n'
                    '                    sub_expand_key = '
                    'f"subsub|{task.get(\'id\',\'\')}|{sub.get(\'id\',\'\')}|{sub.get(\'title\',\'\')}"\n'
                    '                    sub_expanded = sub_expand_key in self.expanded_tasks\n'
                    '                    sub_toggle_text = "Unter-Unteraufgaben einklappen v" if sub_expanded else '
                    '"Unter-Unteraufgaben ausklappen >"\n'
                    '                    tk.Button(sub_action, text=sub_toggle_text, command=lambda '
                    'key=sub_expand_key: self.toggle_subtasks_visibility(key), bg=sub_bg, fg=COLORS["blue"], bd=0, '
                    'padx=4, pady=4, cursor="hand2", font=zfont(self.app, 10, "bold")).pack(side="right", padx=(0, '
                    '4))\n'
                    '                tk.Label(sub_task_cell, text="↳ " + sub.get("title", ""), bg=sub_bg, '
                    'fg=COLORS["text"], font=zfont(self.app, 12), padx=18, pady=5, anchor="w", '
                    'justify="left").pack(side="left", fill="both", expand=True)\n'
                    '                sub_doc = tk.Frame(table, bg=sub_bg); sub_doc.grid(row=row_idx, column=2, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '                self.create_documentation_button(sub_doc, sub, sub.get("title", "Unteraufgabe"), '
                    'parent_task=task).pack(padx=5, pady=2)\n'
                    '                sub_owner = tk.Frame(table, bg=sub_bg); sub_owner.grid(row=row_idx, column=3, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '                tk.Label(sub_owner, text=sub.get("owner", task.get("owner", "")), bg=sub_bg, '
                    'fg=COLORS["text"], font=zfont(self.app, 12), padx=6, pady=5, anchor="center", '
                    'justify="center").pack(side="left", fill="x", expand=True)\n'
                    '                if self.can_edit():\n'
                    '                    self.create_delegate_button(sub_owner, sub, '
                    'parent_task=task).pack(side="right", padx=(2, 5), pady=3)\n'
                    '                for col in (4, 5, 6, 7):\n'
                    '                    tk.Label(table, text="", bg=sub_bg, fg=COLORS["text"], font=zfont(self.app, '
                    '12), padx=6, pady=5).grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)\n'
                    '                self.create_attachment_button(table, sub, lambda s=sub, t=task: '
                    'self.show_attachments(s, parent_task=t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '                tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=9, sticky="nsew", '
                    'padx=1, pady=1)\n'
                    '                if self.edit_mode and self.can_edit():\n'
                    '                    tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=10, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '                self._register_live_subtask_widgets(table, sub_row_idx, task, sub, sub_btn)\n'
                    '                row_idx += 1\n'
                    '                if visible_sub_subtasks and sub_expand_key in self.expanded_tasks:\n'
                    '                    for child in visible_sub_subtasks:\n'
                    '                        child_bg = "#E0F2FE" if child.get("status") == STATUS_DONE else '
                    '"#F0F9FF"\n'
                    '                        child_btn = tk.Button(table, text="✓" if child.get("status") == '
                    'STATUS_DONE else "□", command=lambda t=task, s=sub, c=child: self.toggle_sub_subtask(t, s, c), '
                    'bg="#BAE6FD" if child.get("status") == STATUS_DONE else child_bg, fg=COLORS["dark_green"] if '
                    'child.get("status") == STATUS_DONE else COLORS["text"], bd=0, font=zfont(self.app, 13, "bold"), '
                    'state="normal" if can_complete else "disabled")\n'
                    '                        child_btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                    '                        tk.Label(table, text="↳ ↳ " + child.get("title", ""), bg=child_bg, '
                    'fg=COLORS["text"], font=zfont(self.app, 11), padx=34, pady=4, anchor="w", '
                    'justify="left").grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                    '                        for col in (2, 4, 5, 6, 7, 8, 9):\n'
                    '                            tk.Label(table, text="", bg=child_bg, fg=COLORS["text"], '
                    'font=zfont(self.app, 11), padx=6, pady=4).grid(row=row_idx, column=col, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '                        owner_text = child.get("owner") or sub.get("owner") or task.get("owner", '
                    '"")\n'
                    '                        tk.Label(table, text=owner_text, bg=child_bg, fg=COLORS["text2"], '
                    'font=zfont(self.app, 11), padx=6, pady=4, anchor="center", justify="center").grid(row=row_idx, '
                    'column=3, sticky="nsew", padx=1, pady=1)\n'
                    '                        if self.edit_mode and self.can_edit():\n'
                    '                            tk.Label(table, text="", bg=child_bg).grid(row=row_idx, column=10, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '                        row_idx += 1\n'
                    '        return row_idx\n'
                    '\n'
                    '    def find_task(self, task_id):\n'
                    '        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not '
                    't.get("deleted")), None)\n'
                    '\n'
                    '    def toggle_done(self, task):\n'
                    '            if not self.require_unlocked("Diese Änderung"): return\n'
                    '            real = self.find_task(task["id"])\n'
                    '            if not real: return\n'
                    '            if not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du '
                    'kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); '
                    'self.render_team_detail(real.get("team")); return\n'
                    '            if real.get("subtasks") and not all_subtasks_done(real): self.show_tooltip(self.root, '
                    '"Bitte erst alle Unteraufgaben erledigen."); self.root.after(1600, self.hide_tooltip); return\n'
                    '            if real.get("status") == STATUS_DONE: real.update({"status": STATUS_OPEN, "done_at": '
                    'None, "done_by": None})\n'
                    '            else:\n'
                    '                if real.get("deadline_type") == "gesetzlich" and not '
                    'messagebox.askyesno("Quartalsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                    'markieren?"): return\n'
                    '                real.update({"status": STATUS_DONE, "done_at": '
                    'datetime.now().isoformat(timespec="seconds"), "done_by": getattr(self.app, '
                    '"current_user_display", "") or ""})\n'
                    '            self.save(); self.render_team_detail(real["team"])\n'
                    '\n'
                    '    def set_status(self, task, status):\n'
                    '            if not self.require_unlocked("Diese Änderung"): return\n'
                    '            real = self.find_task(task["id"])\n'
                    '            if not real: return\n'
                    '            if status == STATUS_DONE and not self.can_complete_task(real): '
                    'messagebox.showwarning("Quartalsabschluss", "Du kannst nur Aufgaben als erledigt markieren, für '
                    'die du selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); '
                    'return\n'
                    '            if status == STATUS_DONE and real.get("subtasks") and not all_subtasks_done(real): '
                    'messagebox.showinfo("Quartalsabschluss", "Bitte erst alle Unteraufgaben erledigen."); '
                    'self.render_team_detail(real["team"]); return\n'
                    '            if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not '
                    'messagebox.askyesno("Quartalsabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                    'markieren?"): self.render_team_detail(real["team"]); return\n'
                    '            real["status"] = status; real["done_at"] = '
                    'datetime.now().isoformat(timespec="seconds") if status == STATUS_DONE else None; real["done_by"] '
                    '= getattr(self.app, "current_user_display", "") or "" if status == STATUS_DONE else None\n'
                    '            self.save(); self.render_team_detail(real["team"])\n'
                    '\n'
                    '    def toggle_subtask(self, task, subtask):\n'
                    '            if not self.require_unlocked("Diese Änderung"): return\n'
                    '            real = self.find_task(task["id"])\n'
                    '            if not real: return\n'
                    '            if not self.can_complete_task(real): messagebox.showwarning("Quartalsabschluss", "Du '
                    'kannst nur Unteraufgaben als erledigt markieren, wenn du selbst als zuständig eingetragen '
                    'bist."); self.render_team_detail(real.get("team")); return\n'
                    '            for sub in real.get("subtasks", []):\n'
                    '                if sub.get("id") == subtask.get("id"): sub["status"] = STATUS_OPEN if '
                    'sub.get("status") == STATUS_DONE else STATUS_DONE; break\n'
                    '            sync_parent_status_from_subtasks(real); self.save(); '
                    'self.render_team_detail(real["team"])\n'
                    '\n'
                    '    def next_task_index(self, team):\n'
                    '        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1\n'
                    '\n'
                    '    def task_to_catalog_entry(self, task):\n'
                    '        catalog_id = task.get("catalog_id") or '
                    'f"rec_{datetime.now().strftime(\'%Y%m%d%H%M%S%f\')}"; task["catalog_id"] = catalog_id\n'
                    '        return {k: task.get(k) for k in ["catalog_id", "team", "title", "owner", '
                    '"owner_user_key", "due_date", "due_mode", "due_day", "due_workday", "due_fixed_date", '
                    '"deadline_type", "priority", "required", "recurring"]} | {"start_period": self.period, '
                    '"recurring": True}\n'
                    '\n'
                    '    def upsert_catalog_entry(self, task):\n'
                    '        catalog = load_catalog(); entry = self.task_to_catalog_entry(task); tasks = '
                    'catalog.setdefault("tasks", [])\n'
                    '        for idx, existing in enumerate(tasks):\n'
                    '            if existing.get("catalog_id") == entry["catalog_id"]: entry["start_period"] = '
                    'existing.get("start_period", self.period); tasks[idx] = entry; break\n'
                    '        else: tasks.append(entry)\n'
                    '        save_catalog(catalog); return entry["catalog_id"]\n'
                    '\n'
                    '    def remove_catalog_entry(self, catalog_id):\n'
                    '        if not catalog_id: return\n'
                    '        catalog = load_catalog(); catalog["tasks"] = [t for t in catalog.get("tasks", []) if '
                    't.get("catalog_id") != catalog_id]; save_catalog(catalog)\n'
                    '\n'
                    '    def propagate_recurring_to_future_periods(self, catalog_id):\n'
                    '        if not catalog_id: return\n'
                    '        for period in list_periods():\n'
                    '            if period > self.period: apply_catalog_to_period(period)\n'
                    '\n'
                    '    def open_task_dialog(self, team, task=None):\n'
                    '        if not self.can_edit(): return\n'
                    '        is_new = task is None\n'
                    '        win = tk.Toplevel(self.root); win.title("Aufgabe anlegen" if is_new else "Aufgabe '
                    'bearbeiten"); win.configure(bg=COLORS["bg"]); win.geometry("760x590"); win.transient(self.root); '
                    'win.grab_set()\n'
                    '        data = dict(task) if task else {"title": "", "owner": team, "owner_user_key": "", '
                    '"deadline_type": "intern", "priority": "normal", "due_mode": DUE_CUTOFF, "due_day": 1, '
                    '"due_workday": 1, "due_fixed_date": "", "recurring": False, "subtasks": [], "booking_circle": '
                    '"IDE"}\n'
                    '        normalize_task(data, self.data, self.period)\n'
                    '        popup_body_container = tk.Frame(win, bg=COLORS["bg"]); '
                    'popup_body_container.pack(fill="both", expand=True, padx=0, pady=0)\n'
                    '        popup_body_canvas = tk.Canvas(popup_body_container, bg=COLORS["bg"], '
                    'highlightthickness=0, bd=0)\n'
                    '        popup_body_scrollbar = tk.Scrollbar(popup_body_container, orient="vertical", '
                    'command=popup_body_canvas.yview)\n'
                    '        popup_body = tk.Frame(popup_body_canvas, bg=COLORS["bg"])\n'
                    '        popup_body_window = popup_body_canvas.create_window((0, 0), window=popup_body, '
                    'anchor="nw")\n'
                    '        def _popup_update_scrollregion(_event=None):\n'
                    '            try:\n'
                    '                popup_body_canvas.itemconfigure(popup_body_window, width=max(1, '
                    'popup_body_canvas.winfo_width() - 2))\n'
                    '                popup_body_canvas.configure(scrollregion=popup_body_canvas.bbox("all"))\n'
                    '            except Exception:\n'
                    '                pass\n'
                    '        popup_body.bind("<Configure>", _popup_update_scrollregion)\n'
                    '        popup_body_canvas.bind("<Configure>", _popup_update_scrollregion)\n'
                    '        popup_body_canvas.configure(yscrollcommand=popup_body_scrollbar.set)\n'
                    '        popup_body_canvas.pack(side="left", fill="both", expand=True, padx=14, pady=14)\n'
                    '        popup_body_scrollbar.pack(side="right", fill="y", pady=14)\n'
                    '        def _popup_mousewheel(event):\n'
                    '            try:\n'
                    '                if getattr(event, "num", None) == 4:\n'
                    '                    popup_body_canvas.yview_scroll(-3, "units")\n'
                    '                elif getattr(event, "num", None) == 5:\n'
                    '                    popup_body_canvas.yview_scroll(3, "units")\n'
                    '                else:\n'
                    '                    delta = int(getattr(event, "delta", 0) or 0)\n'
                    '                    popup_body_canvas.yview_scroll(int(-delta / 120), "units")\n'
                    '                return "break"\n'
                    '            except Exception:\n'
                    '                return "break"\n'
                    '        def _popup_bind_mousewheel(widget):\n'
                    '            try:\n'
                    '                widget.bind("<MouseWheel>", _popup_mousewheel, add=False)\n'
                    '                widget.bind("<Button-4>", _popup_mousewheel, add=False)\n'
                    '                widget.bind("<Button-5>", _popup_mousewheel, add=False)\n'
                    '                for child in widget.winfo_children():\n'
                    '                    _popup_bind_mousewheel(child)\n'
                    '            except Exception:\n'
                    '                pass\n'
                    '        notebook = ttk.Notebook(popup_body); notebook.pack(fill="both", expand=True, padx=0, '
                    'pady=0)\n'
                    '        form = tk.Frame(notebook, bg=COLORS["bg"]); subtab = tk.Frame(notebook, bg=COLORS["bg"])\n'
                    '        notebook.add(form, text="Aufgabe"); notebook.add(subtab, text="Unteraufgaben")\n'
                    '        title_var = tk.StringVar(value=data.get("title", "")); deadline_var = '
                    'tk.StringVar(value=data.get("deadline_type", "intern") if data.get("deadline_type") in '
                    'DEADLINE_TYPES else "intern"); priority_var = tk.StringVar(value=data.get("priority", "normal")); '
                    'recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))\n'
                    '        due_frequency_var = tk.StringVar(value=str(data.get("due_frequency") or ("Monat" if '
                    'CLOSING_SCOPE == "M" else "Quartal" if CLOSING_SCOPE == "Q" else "Jahr")))\n'
                    '        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", '
                    'DUE_CUTOFF), "Abschluss-Stichtag")); due_day_var = tk.StringVar(value=str(data.get("due_day") or '
                    '1)); due_workday_var = tk.StringVar(value=str(data.get("due_workday") or 1)); due_fixed_var = '
                    'tk.StringVar(value=format_date_de(data.get("due_fixed_date") or data.get("due_date") or "")); '
                    'calculated_var = tk.StringVar(value="")\n'
                    '        users = self.user_choices(); user_labels = {label: key for key, label in users}; '
                    'current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, '
                    'label in users if key == current_owner_key), data.get("owner", team)); owner_var = '
                    'tk.StringVar(value=current_owner_label)\n'
                    '        booking_circle_var = tk.StringVar(value=data.get("booking_circle", "IDE") if '
                    'data.get("booking_circle", "IDE") in ("IDE", "IDG", "IMS", "SPI", "IHB") else "IDE")\n'
                    '        widgets = [("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), '
                    '("Buchungskreis", tk.OptionMenu(form, booking_circle_var, "IDE", "IDG", "IMS", "SPI", "IHB")), '
                    '("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fälligkeitsturnus", tk.OptionMenu(form, due_frequency_var, "Monat", "Quartal", "Jahr")), ("Fristart", '
                    'tk.OptionMenu(form, deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, '
                    'priority_var, *PRIORITIES)), ("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, '
                    '*DUE_LABEL_TO_VALUE.keys()))]\n'
                    '        for row, (label, widget) in enumerate(widgets):\n'
                    '            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, '
                    '12, "bold")).grid(row=row, column=0, sticky="w", pady=7, padx=8); widget.grid(row=row, column=1, '
                    'sticky="w", pady=7)\n'
                    '            try: widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)\n'
                    '            except Exception: pass\n'
                    '        day_label = tk.Label(form, text="Tag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")); day_entry = tk.Entry(form, textvariable=due_day_var, width=8)\n'
                    '        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")); workday_entry = tk.Entry(form, textvariable=due_workday_var, '
                    'width=8)\n'
                    '        fixed_label = tk.Label(form, text="Konkretes Datum (TT.MM.JJJJ)", bg=COLORS["bg"], '
                    'fg=COLORS["text"], font=zfont(self.app, 12, "bold")); fixed_entry = tk.Entry(form, '
                    'textvariable=due_fixed_var, width=14)\n'
                    '        for r, lab, ent in [(7, day_label, day_entry), (8, workday_label, workday_entry), (9, '
                    'fixed_label, fixed_entry)]: lab.grid(row=r, column=0, sticky="w", pady=7, padx=8); '
                    'ent.grid(row=r, column=1, sticky="w", pady=7); ent.config(bg="white", fg=COLORS["text"], '
                    'relief="solid", bd=1, highlightthickness=0)\n'
                    '        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], '
                    'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), activebackground=COLORS["bg"]).grid(row=9, '
                    'column=1, sticky="w", pady=7)\n'
                    '        tk.Label(form, text="Fälligkeitsturnus", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).grid(row=10, column=0, sticky="w", pady=7, padx=8)\n'
                    '        tk.OptionMenu(form, due_frequency_var, "Monat", "Quartal", "Jahr").grid(row=10, column=1, '
                    'sticky="w", pady=7)\n'
                    '        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], '
                    'font=zfont(self.app, 12, "bold")).grid(row=11, column=0, columnspan=2, sticky="w", pady=(10, 10), padx=8)\n'
                    '        def refresh_due_input_visibility(*_):\n'
                    '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF)\n'
                    '            for lab, ent in [(day_label, day_entry), (workday_label, workday_entry), '
                    '(fixed_label, fixed_entry)]: lab.grid_remove(); ent.grid_remove()\n'
                    '            if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): '
                    'day_label.grid(); day_entry.grid()\n'
                    '            elif mode == DUE_WORKDAY_NEXT: workday_label.grid(); workday_entry.grid()\n'
                    '            elif mode == DUE_FIXED: fixed_label.grid(); fixed_entry.grid()\n'
                    '            preview = {"due_mode": mode, "due_day": due_day_var.get().strip() or 1, '
                    '"due_workday": due_workday_var.get().strip() or 1, "due_fixed_date": '
                    'due_fixed_var.get().strip()}\n'
                    '            calculated_var.set("Berechnetes Fälligkeitsdatum: " + '
                    '(format_date_de(resolve_due_date(preview, self.data, self.period)) or "-"))\n'
                    '        for var in (due_mode_var, due_day_var, due_workday_var, due_fixed_var): '
                    'var.trace_add("write", refresh_due_input_visibility)\n'
                    '        refresh_due_input_visibility()\n'
                    '        subtasks_work = [dict(s) for s in data.get("subtasks", []) if not s.get("deleted")]\n'
                    '        sub_list = tk.Frame(subtab, bg=COLORS["bg"]); sub_list.pack(fill="both", expand=True, '
                    'padx=10, pady=10); new_sub_var = tk.StringVar()\n'
                    '        def open_sub_subtask_popup(parent_index):\n'
                    '            if parent_index < 0 or parent_index >= len(subtasks_work):\n'
                    '                return\n'
                    '            parent_sub = subtasks_work[parent_index]\n'
                    '            parent_sub.setdefault("subtasks", [])\n'
                    '            win2 = tk.Toplevel(win)\n'
                    '            win2.title("Unter-Unteraufgaben erstellen")\n'
                    '            win2.configure(bg=COLORS["bg"])\n'
                    '            win2.geometry("760x520")\n'
                    '            win2.transient(win)\n'
                    '            win2.grab_set()\n'
                    '            tk.Label(win2, text="Unter-Unteraufgaben erstellen", bg=COLORS["bg"], '
                    'fg=COLORS["text"], font=zfont(self.app, 18, "bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                    '            tk.Label(win2, text="Unteraufgabe: " + str(parent_sub.get("title", "")), '
                    'bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 13), wraplength=710, '
                    'justify="left").pack(anchor="w", padx=18, pady=(0, 12))\n'
                    '            list_box = tk.Frame(win2, bg=COLORS["white"], bd=1, relief="solid")\n'
                    '            list_box.pack(fill="both", expand=True, padx=18, pady=(0, 10))\n'
                    '            new_child_var = tk.StringVar()\n'
                    '\n'
                    '            def refresh_children():\n'
                    '                for child_widget in list_box.winfo_children():\n'
                    '                    child_widget.destroy()\n'
                    '                tk.Label(list_box, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=0, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '                tk.Label(list_box, text="Unter-Unteraufgabe", bg=COLORS["header"], '
                    'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=1, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '                tk.Label(list_box, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=2, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '                list_box.grid_columnconfigure(1, weight=1)\n'
                    '                children = parent_sub.setdefault("subtasks", [])\n'
                    '                if not children:\n'
                    '                    tk.Label(list_box, text="Noch keine Unter-Unteraufgaben vorhanden.", '
                    'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 12), padx=10, pady=10, '
                    'anchor="w").grid(row=1, column=0, columnspan=3, sticky="ew")\n'
                    '                for cidx, child in enumerate(children, start=1):\n'
                    '                    child.setdefault("id", '
                    'f"subsub_{cidx:02d}_{datetime.now().strftime(\'%H%M%S%f\')}")\n'
                    '                    child.setdefault("status", STATUS_OPEN)\n'
                    '                    cvar = tk.StringVar(value=child.get("title", ""))\n'
                    '                    cstatus = tk.BooleanVar(value=child.get("status") == STATUS_DONE)\n'
                    '                    def _write_title(*_args, i=cidx-1, v=cvar):\n'
                    '                        parent_sub.setdefault("subtasks", [])[i]["title"] = v.get()\n'
                    '                    cvar.trace_add("write", _write_title)\n'
                    '                    def _write_status(i=cidx-1, v=cstatus):\n'
                    '                        parent_sub.setdefault("subtasks", [])[i]["status"] = STATUS_DONE if '
                    'v.get() else STATUS_OPEN\n'
                    '                    tk.Checkbutton(list_box, variable=cstatus, command=_write_status, '
                    'bg=COLORS["white"], activebackground=COLORS["white"]).grid(row=cidx, column=0, sticky="nsew", '
                    'padx=1, pady=1)\n'
                    '                    tk.Entry(list_box, textvariable=cvar, bg="white", fg=COLORS["text"], '
                    'relief="solid", bd=1, font=zfont(self.app, 13), width=54).grid(row=cidx, column=1, sticky="ew", '
                    'padx=6, pady=5, ipady=4)\n'
                    '                    tk.Button(list_box, text="Löschen", command=lambda i=cidx-1: delete_child(i), '
                    'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=7, font=zfont(self.app, 12, '
                    '"bold")).grid(row=cidx, column=2, sticky="w", padx=6, pady=5)\n'
                    '\n'
                    '            def add_child():\n'
                    '                title = new_child_var.get().strip()\n'
                    '                if not title:\n'
                    '                    messagebox.showwarning("Unter-Unteraufgaben", "Bitte zuerst einen Namen für '
                    'die Unter-Unteraufgabe eingeben.", parent=win2)\n'
                    '                    return\n'
                    '                parent_sub.setdefault("subtasks", []).append({"id": '
                    'f"subsub_{len(parent_sub.get(\'subtasks\', []))+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", '
                    '"title": title, "status": STATUS_OPEN})\n'
                    '                new_child_var.set("")\n'
                    '                refresh_children()\n'
                    '\n'
                    '            def delete_child(child_index):\n'
                    '                try:\n'
                    '                    parent_sub.setdefault("subtasks", []).pop(child_index)\n'
                    '                except Exception:\n'
                    '                    pass\n'
                    '                refresh_children()\n'
                    '\n'
                    '            add_box = tk.Frame(win2, bg=COLORS["bg"])\n'
                    '            add_box.pack(fill="x", padx=18, pady=(0, 10))\n'
                    '            tk.Label(add_box, text="Neue Unter-Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).pack(anchor="w")\n'
                    '            entry_row = tk.Frame(add_box, bg=COLORS["bg"])\n'
                    '            entry_row.pack(fill="x", pady=(5, 0))\n'
                    '            tk.Entry(entry_row, textvariable=new_child_var, bg="white", fg=COLORS["text"], '
                    'relief="solid", bd=1, font=zfont(self.app, 13), width=58).pack(side="left", fill="x", '
                    'expand=True, ipady=5)\n'
                    '            tk.Button(entry_row, text="Hinzufügen", command=add_child, bg=COLORS["blue"], '
                    'fg="white", bd=0, padx=16, pady=9, font=zfont(self.app, 12, "bold")).pack(side="left", padx=(10, '
                    '0))\n'
                    '            footer2 = tk.Frame(win2, bg=COLORS["bg"])\n'
                    '            footer2.pack(fill="x", padx=18, pady=(0, 14))\n'
                    '            def close_child_popup():\n'
                    '                refresh_subtasks_editor()\n'
                    '                win2.destroy()\n'
                    '            tk.Button(footer2, text="Übernehmen und schließen", command=close_child_popup, '
                    'bg=COLORS["blue"], fg="white", bd=0, padx=18, pady=9, font=zfont(self.app, 12, '
                    '"bold")).pack(side="right")\n'
                    '            tk.Button(footer2, text="Abbrechen", command=win2.destroy, bg=COLORS["line"], '
                    'fg=COLORS["text"], bd=0, padx=18, pady=9, font=zfont(self.app, 12, "bold")).pack(side="right", '
                    'padx=(0, 10))\n'
                    '            refresh_children()\n'
                    '\n'
                    '        def refresh_subtasks_editor():\n'
                    '            for child in sub_list.winfo_children(): child.destroy()\n'
                    '            tk.Label(sub_list, text="Unteraufgaben", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 15, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))\n'
                    '            tk.Label(sub_list, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=0, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '            tk.Label(sub_list, text="Unteraufgabe", bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=1, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '            tk.Label(sub_list, text="Unter-Unteraufgaben", bg=COLORS["header"], '
                    'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=2, '
                    'sticky="nsew", padx=1, pady=1)\n'
                    '            tk.Label(sub_list, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=3, sticky="nsew", padx=1, '
                    'pady=1)\n'
                    '            sub_list.grid_columnconfigure(1, weight=1)\n'
                    '            row = 2\n'
                    '            for idx, sub in enumerate(subtasks_work):\n'
                    '                sub.setdefault("subtasks", [])\n'
                    '                var = tk.StringVar(value=sub.get("title", "")); status_var = '
                    'tk.BooleanVar(value=sub.get("status") == STATUS_DONE)\n'
                    '                var.trace_add("write", lambda *_args, i=idx, v=var: '
                    'subtasks_work[i].update({"title": v.get()}))\n'
                    '                tk.Checkbutton(sub_list, variable=status_var, command=lambda i=idx, v=status_var: '
                    'subtasks_work[i].update({"status": STATUS_DONE if v.get() else STATUS_OPEN}), bg=COLORS["bg"], '
                    'activebackground=COLORS["bg"]).grid(row=row, column=0, sticky="nsew", pady=4, padx=1)\n'
                    '                tk.Entry(sub_list, textvariable=var, width=52, bg="white", fg=COLORS["text"], '
                    'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=row, column=1, sticky="ew", pady=4, '
                    'padx=6, ipady=4)\n'
                    '                count = len([c for c in sub.get("subtasks", []) or [] if str(c.get("title", '
                    '"")).strip()])\n'
                    '                tk.Button(sub_list, text=f"Unter-Unteraufgaben erstellen ({count})", '
                    'command=lambda i=idx: open_sub_subtask_popup(i), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                    'pady=8, font=zfont(self.app, 12, "bold")).grid(row=row, column=2, sticky="w", pady=4, padx=6)\n'
                    '                tk.Button(sub_list, text="Löschen", command=lambda i=idx: delete_subtask(i), '
                    'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=8, font=zfont(self.app, 12, '
                    '"bold")).grid(row=row, column=3, sticky="w", pady=4, padx=6)\n'
                    '                row += 1\n'
                    '            add_row = row + 1\n'
                    '            tk.Label(sub_list, text="Neue Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).grid(row=add_row, column=0, columnspan=2, sticky="w", pady=(14, '
                    '4), padx=6)\n'
                    '            tk.Entry(sub_list, textvariable=new_sub_var, width=52, bg="white", fg=COLORS["text"], '
                    'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=add_row+1, column=1, sticky="ew", '
                    'pady=(2, 4), padx=6, ipady=4)\n'
                    '            tk.Button(sub_list, text="Unteraufgabe hinzufügen", command=add_subtask, '
                    'bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=9, font=zfont(self.app, 12, '
                    '"bold")).grid(row=add_row+1, column=2, sticky="w", pady=(2, 4), padx=6)\n'
                    '\n'
                    '        def render_subtasks_editor():\n'
                    '            refresh_subtasks_editor()\n'
                    '\n'
                    '        def add_subtask():\n'
                    '            title = new_sub_var.get().strip()\n'
                    '            if title: subtasks_work.append({"id": '
                    'f"sub_{len(subtasks_work)+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", "title": title, '
                    '"status": STATUS_OPEN}); new_sub_var.set(""); render_subtasks_editor()\n'
                    '        def delete_subtask(idx):\n'
                    '            if 0 <= idx < len(subtasks_work): subtasks_work.pop(idx); render_subtasks_editor()\n'
                    '        render_subtasks_editor()\n'
                    '        if not is_new:\n'
                    '            tk.Button(form, text="Aufgabe mit Unteraufgaben in Monatsabschluss übernehmen", '
                    'command=lambda: self.open_transfer_dialog(task), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                    'pady=7).grid(row=10, column=1, sticky="w", pady=(10, 4))\n'
                    '        def save_dialog():\n'
                    '            title_value = title_var.get().strip()\n'
                    '            if not title_value: messagebox.showwarning("Quartalsabschluss", "Bitte einen '
                    'Aufgabennamen eingeben."); return\n'
                    '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF); due_day = None; '
                    'due_workday = None; due_fixed = ""\n'
                    '            try:\n'
                    '                if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): due_day '
                    '= int(due_day_var.get().strip()); assert due_day > 0\n'
                    '                elif mode == DUE_WORKDAY_NEXT: due_workday = int(due_workday_var.get().strip()); '
                    'assert due_workday > 0\n'
                    '                elif mode == DUE_FIXED:\n'
                    '                    fixed_date = parse_date(due_fixed_var.get().strip()); assert fixed_date; '
                    'due_fixed = fixed_date.strftime("%Y-%m-%d")\n'
                    '            except Exception:\n'
                    '                messagebox.showwarning("Quartalsabschluss", "Bitte gültige Werte zur Fälligkeit '
                    'eingeben."); return\n'
                    '            owner_label = owner_var.get(); owner_key = user_labels.get(owner_label, ""); '
                    'owner_text = owner_label if owner_key else team\n'
                    '            payload = {"title": title_value, "booking_circle": booking_circle_var.get(), "owner": '
                    'owner_text, "owner_user_key": owner_key, "due_mode": mode, "due_day": due_day, "due_workday": '
                    'due_workday, "due_fixed_date": due_fixed, "deadline_type": deadline_var.get(), "priority": '
                    'priority_var.get(), "recurring": bool(recurring_var.get()), "due_frequency": '
                    'due_frequency_var.get(), "subtasks": [s for s in subtasks_work if s.get("title", "").strip()]}\n'
                    '            payload["due_date"] = resolve_due_date(payload, self.data, self.period)\n'
                    '            if is_new:\n'
                    '                real = {"id": make_task_id(team, self.next_task_index(team)), "team": team, '
                    '"required": True, "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, '
                    '"done_by": None, "catalog_id": "", **payload}; self.data.setdefault("tasks", []).append(real)\n'
                    '            else:\n'
                    '                real = self.find_task(task["id"])\n'
                    '                if not real: return\n'
                    '                real.update(payload)\n'
                    '            sync_parent_status_from_subtasks(real)\n'
                    '            if real.get("recurring"):\n'
                    '                catalog_id = self.upsert_catalog_entry(real); real["catalog_id"] = catalog_id; '
                    'self.propagate_recurring_to_future_periods(catalog_id)\n'
                    '            else:\n'
                    '                if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))\n'
                    '                real["catalog_id"] = ""\n'
                    '            self.save(); win.destroy(); self.reload(); self.render_team_detail(team)\n'
                    '        buttons = tk.Frame(win, bg=COLORS["bg"]); buttons.pack(side="bottom", fill="x", pady=(0, '
                    '12), padx=14)\n'
                    '        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", '
                    'bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", padx=6)\n'
                    '        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                    'fg=COLORS["text"], bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", '
                    'padx=6)\n'
                    '        _popup_bind_mousewheel(win)\n'
                    '        _popup_update_scrollregion()\n'
                    '\n'
                    '    def delete_task(self, task):\n'
                    '            if not self.require_unlocked("Diese Änderung"): return\n'
                    '            idx = self.find_task_index_exact(task)\n'
                    '            if idx is None:\n'
                    '                messagebox.showerror("Aufgabe löschen", "Die ausgewählte Aufgabe konnte nicht '
                    'eindeutig identifiziert werden. Es wurde nichts gelöscht.")\n'
                    '                return\n'
                    '            real = self.data.get("tasks", [])[idx]\n'
                    '            scope = self.ask_delete_scope(real)\n'
                    '            if not scope:\n'
                    '                return\n'
                    '            task_key = self.task_match_key(real)\n'
                    '            team = real.get("team")\n'
                    '            title = real.get("title", "")\n'
                    '            self.data["tasks"].pop(idx)\n'
                    '            if scope == "following" and real.get("catalog_id"):\n'
                    '                self.remove_catalog_entry(real.get("catalog_id"))\n'
                    '            self.save()\n'
                    '            removed_future = 0\n'
                    '            ambiguous_future = 0\n'
                    '            if scope == "following":\n'
                    '                removed_future, ambiguous_future = self.delete_from_following_periods(task_key)\n'
                    '            info = f"Aufgabe wurde gelöscht:\\n\\n{title}"\n'
                    '            if scope == "following":\n'
                    '                info += f"\\n\\nEntfernt aus Folgezeiträumen: {removed_future}"\n'
                    '                if ambiguous_future:\n'
                    '                    info += f"\\nNicht eindeutig erkannte Folgezeiträume übersprungen: '
                    '{ambiguous_future}"\n'
                    '            messagebox.showinfo("Aufgabe löschen", info)\n'
                    '            self.reload()\n'
                    '            self.render_team_detail(team) if team else self.render_dashboard()\n'
                    '\n'
                    '    def clone_task_for_period(self, task, target_period, index):\n'
                    '        data_stub = {"closing_cutoff_date": default_cutoff_date(target_period)}\n'
                    '        clone = {"id": make_task_id(task.get("team", "Team"), index), "team": task.get("team"), '
                    '"title": task.get("title"), "owner": task.get("owner", task.get("team")), "owner_user_key": '
                    'task.get("owner_user_key", ""), "due_mode": task.get("due_mode", DUE_CUTOFF), "due_day": '
                    'task.get("due_day"), "due_workday": task.get("due_workday"), "due_fixed_date": '
                    'task.get("due_fixed_date", ""), "deadline_type": task.get("deadline_type", "keine"), "priority": '
                    'task.get("priority", "normal"), "required": task.get("required", True), "recurring": '
                    'task.get("recurring", False), "catalog_id": task.get("catalog_id", ""), "status": STATUS_OPEN, '
                    '"attachments": [], "comments": [], "subtasks": [dict(s, status=STATUS_OPEN) for s in '
                    'task.get("subtasks", []) if not s.get("deleted")], "done_at": None, "done_by": None}\n'
                    '        clone["due_date"] = resolve_due_date(clone, data_stub, target_period); return clone\n'
                    '\n'
                    '    def apply_current_tasks_to_all_periods(self):\n'
                    '            if not self.require_unlocked("Zuweisung an Perioden ist nicht möglich"): return\n'
                    '            if not self.can_edit(): return\n'
                    '            if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus '
                    '{period_label(self.period)} wird auf alle vorhandenen Perioden übertragen.\\n\\nStatus, Anlagen, '
                    'Kommentare und Erledigt-Infos werden in den Zielperioden zurückgesetzt.\\n\\nFortfahren?"): '
                    'return\n'
                    '            source_tasks = [t for t in self.tasks()]\n'
                    '            for target in list_periods():\n'
                    '                grouped_index = {}; cloned = []\n'
                    '                for task in source_tasks:\n'
                    '                    team = task.get("team", "Team"); grouped_index[team] = '
                    'grouped_index.get(team, 0) + 1; cloned.append(self.clone_task_for_period(task, target, '
                    'grouped_index[team]))\n'
                    '                data = load_period(target); data["tasks"] = cloned; data["updated_from_period"] = '
                    'self.period; data["updated_at"] = datetime.now().isoformat(timespec="seconds"); '
                    'save_period(target, data)\n'
                    '            self.reload(); messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben wurden allen '
                    'vorhandenen Perioden zugewiesen."); self.render_team_detail(self.selected_team) if '
                    'self.selected_team else self.render_dashboard()\n'
                    '\n'
                    '    def show_attachments(self, task, parent_task=None):\n'
                    '        self.normalize_documentation_fields(task)\n'
                    '        item_title = task.get("title", "Aufgabe")\n'
                    '        win = tk.Toplevel(self.root)\n'
                    '        win.title(f"Anlagen - {item_title}")\n'
                    '        win.configure(bg=COLORS["bg"])\n'
                    '        win.geometry("860x560")\n'
                    '        win.transient(self.root)\n'
                    '        win.grab_set()\n'
                    '\n'
                    '        tk.Label(win, text=item_title, bg=COLORS["bg"], fg=COLORS["text"], font=zfont(self.app, '
                    '16, "bold")).pack(anchor="w", padx=16, pady=(14, 4))\n'
                    '        tk.Label(win, text="Anlagen dienen zur Hinterlegung ausgearbeiteter Ergebnisse und '
                    'Kommentare zur Bearbeitung. Dokumentationen/Leitfäden bitte in der Spalte Dokumentation '
                    'pflegen.", bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 11), wraplength=820, '
                    'justify="left").pack(anchor="w", padx=16, pady=(0, 8))\n'
                    '\n'
                    '        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                    '        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))\n'
                    '        list_frame.grid_columnconfigure(0, weight=1)\n'
                    '        list_frame.grid_columnconfigure(3, weight=2)\n'
                    '\n'
                    '        def refresh():\n'
                    '            for child in list_frame.winfo_children():\n'
                    '                child.destroy()\n'
                    '            self.normalize_documentation_fields(task)\n'
                    '            headers = ["Anlagenpfad", "Öffnen", "Entfernen", "Bemerkung"]\n'
                    '            for c, h in enumerate(headers):\n'
                    '                tk.Label(list_frame, text=h, bg=COLORS["header"], fg=COLORS["text"], '
                    'font=zfont(self.app, 11, "bold"), padx=6, pady=4).grid(row=0, column=c, sticky="nsew")\n'
                    '            if not task.get("attachments"):\n'
                    '                tk.Label(list_frame, text="Noch keine Anlage hinterlegt.", bg=COLORS["white"], '
                    'fg=COLORS["text2"], padx=8, pady=8, anchor="w").grid(row=1, column=0, columnspan=4, sticky="ew")\n'
                    '                return\n'
                    '            for idx, att in enumerate(task.get("attachments", []), start=1):\n'
                    '                tk.Label(list_frame, text=att.get("path", ""), bg=COLORS["white"], '
                    'fg=COLORS["text"], anchor="w", wraplength=330).grid(row=idx, column=0, sticky="ew", padx=6, '
                    'pady=3)\n'
                    '                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): '
                    'self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, '
                    'pady=3)\n'
                    '                tk.Button(list_frame, text="Entfernen", command=lambda a=att: '
                    'remove_attachment(a), bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, '
                    'pady=3)\n'
                    '                tk.Label(list_frame, text=att.get("comment", ""), bg=COLORS["white"], '
                    'fg=COLORS["text2"], anchor="w", justify="left", wraplength=320).grid(row=idx, column=3, '
                    'sticky="ew", padx=6, pady=3)\n'
                    '\n'
                    '        def choose_path():\n'
                    '            selected = filedialog.askopenfilename(title="Anlage auswählen")\n'
                    '            if selected:\n'
                    '                path_var.set(selected)\n'
                    '\n'
                    '        def add_or_update_attachment():\n'
                    '            path = path_var.get().strip()\n'
                    '            if not path or path == placeholder:\n'
                    '                messagebox.showwarning("Anlagen", "Bitte einen Pfad der Anlage wählen oder '
                    'einfügen.")\n'
                    '                return\n'
                    '            self.normalize_documentation_fields(task)\n'
                    '            task.setdefault("attachments", []).append({\n'
                    '                "name": os.path.basename(path) or "Anlage",\n'
                    '                "path": path,\n'
                    '                "comment": comment_box.get("1.0", "end").strip(),\n'
                    '                "added_at": datetime.now().isoformat(timespec="seconds"),\n'
                    '            })\n'
                    '            self.save()\n'
                    '            refresh()\n'
                    '            path_var.set(placeholder)\n'
                    '            comment_box.delete("1.0", "end")\n'
                    '            if self.selected_team:\n'
                    '                self.render_team_detail(self.selected_team)\n'
                    '\n'
                    '        def remove_attachment(att):\n'
                    '            if messagebox.askyesno("Anlage entfernen", f"Anlage '
                    'entfernen?\\n\\n{att.get(\'name\') or att.get(\'path\')}"):\n'
                    '                task["attachments"] = [a for a in task.get("attachments", []) if a != att]\n'
                    '                self.save(); refresh()\n'
                    '                if self.selected_team:\n'
                    '                    self.render_team_detail(self.selected_team)\n'
                    '\n'
                    '        form = tk.Frame(win, bg=COLORS["bg"])\n'
                    '        form.pack(fill="x", padx=16, pady=(0, 14))\n'
                    '        path_var = tk.StringVar()\n'
                    '        placeholder = "Bitte Pfad der Anlage wählen oder einfügen"\n'
                    '        path_var.set(placeholder)\n'
                    '        tk.Label(form, text="Anlagenpfad", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                    '        tk.Button(form, text="Anlage auswählen", command=choose_path, bg=COLORS["blue"], '
                    'fg="white", bd=0, padx=10, pady=5).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                    '        entry = tk.Entry(form, textvariable=path_var, bg=COLORS["white"], fg=COLORS["text2"], '
                    'relief="solid", bd=1, width=70)\n'
                    '        entry.grid(row=0, column=2, sticky="ew", pady=(0, 6))\n'
                    '        form.grid_columnconfigure(2, weight=1)\n'
                    '        def clear_placeholder(_event=None):\n'
                    '            if path_var.get() == placeholder:\n'
                    '                path_var.set("")\n'
                    '                entry.config(fg=COLORS["text"])\n'
                    '        entry.bind("<FocusIn>", clear_placeholder)\n'
                    '\n'
                    '        tk.Label(form, text="Bemerkungen und Informationen:", bg=COLORS["bg"], fg=COLORS["text"], '
                    'font=zfont(self.app, 12, "bold")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 4))\n'
                    '        comment_box = tk.Text(form, height=4, bg=COLORS["white"], fg=COLORS["text"], '
                    'relief="solid", bd=1)\n'
                    '        comment_box.grid(row=2, column=0, columnspan=3, sticky="ew")\n'
                    '        tk.Button(form, text="Übernehmen", command=add_or_update_attachment, bg=COLORS["blue"], '
                    'fg="white", bd=0, padx=16, pady=7).grid(row=3, column=2, sticky="e", pady=(8, 0))\n'
                    '        refresh()\n'
                    '\n'
                    '    def open_attachment(self, path):\n'
                    '        if not path or not os.path.exists(path): messagebox.showwarning("Anlage", "Datei wurde '
                    'nicht gefunden."); return\n'
                    '        try:\n'
                    '            if os.name == "nt": os.startfile(path)\n'
                    '            elif sys.platform == "darwin": subprocess.Popen(["open", path])\n'
                    '            else: subprocess.Popen(["xdg-open", path])\n'
                    '        except Exception as exc: messagebox.showerror("Anlage", str(exc))\n'
                    '\n'
                    '\n'
                    'def render(app):\n'
                    '    QuarterlyCloseUI(app)\n',
 'yearly_close': '## FiBuMate_PATCH_MARKER: 20260609_PROTOCOL_ONLY_SUBTASK_PROGRESS\n'
                 '## FiBuMate_PATCH_MARKER: 20260609_v0436_ABSCHLUSSKALENDER_UNIFIED_WRAPPED\n'
                 '## FiBuMate_PATCH_MARKER: 20260609_v0436_DREI_MODULE_OHNE_ID_ZUWEISUNG\n'
                 '\n'
                 'import calendar\n'
                 'import json\n'
                 'import os\n'
                 'import shutil\n'
                 'import subprocess\n'
                 'import sys\n'
                 'import webbrowser\n'
                 'from datetime import date, datetime, timedelta\n'
                 'from pathlib import Path\n'
                 'from urllib.parse import quote\n'
                 'import tkinter as tk\n'
                 'from tkinter import filedialog, messagebox, ttk\n'
                 '\n'
                 'try:\n'
                 '    from . import compliance_common as cc\n'
                 'except Exception:\n'
                 '    try:\n'
                 '        import compliance_common as cc\n'
                 '    except Exception:\n'
                 '        cc = None\n'
                 '\n'
                 '## v0.434: einheitliche Modulschrift / Bereichszoom analog Monatsabschluss.\n'
                 '\n'
                 'def zfont(app, size=12, weight=None, underline=False, scale=1.0):\n'
                 '    try:\n'
                 '        scope_zoom = float(getattr(app, "current_scope_zoom", 1.0) or 1.0)\n'
                 '        final = max(9, int(round(float(size) * 1.28 * scope_zoom * float(scale))))\n'
                 '    except Exception:\n'
                 '        final = int(size)\n'
                 '    styles = []\n'
                 '    if weight:\n'
                 '        styles.append(weight)\n'
                 '    if underline:\n'
                 '        styles.append("underline")\n'
                 '    return tuple(["Segoe UI", final] + styles)\n'
                 '\n'
                 'def apply_readable_fonts(widget, app, base_size=12):\n'
                 '    "Setzt direkte Tk-Fonts für neu erzeugte Modulwidgets nach."\n'
                 '    try:\n'
                 '        try:\n'
                 '            cls = widget.winfo_class().lower()\n'
                 '        except Exception:\n'
                 '            cls = ""\n'
                 '        if cls in ("label", "button", "entry", "text", "listbox", "checkbutton", "radiobutton", '
                 '"menubutton"):\n'
                 '            try:\n'
                 '                current = str(widget.cget("font") or "")\n'
                 '                widget.configure(font=zfont(app, base_size, "bold" if "bold" in current.lower() else '
                 'None))\n'
                 '            except Exception:\n'
                 '                pass\n'
                 '        for child in widget.winfo_children():\n'
                 '            apply_readable_fonts(child, app, base_size)\n'
                 '    except Exception:\n'
                 '        pass\n'
                 'STATUS_OPEN = "Offen"\n'
                 'STATUS_IN_PROGRESS = "In Bearbeitung"\n'
                 'STATUS_DONE = "Erledigt"\n'
                 'STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_DONE]\n'
                 'TEAMS = ["Hauptbuch", "Zentralregulierung", "Debitoren", "Treasury"]\n'
                 'TEAM_ALIASES = {"Kreditoren": "Zentralregulierung", "Controlling": "Treasury"}\n'
                 'DEADLINE_TYPES = ["intern", "gesetzlich"]\n'
                 'PRIORITIES = ["normal", "hoch", "kritisch"]\n'
                 '\n'
                 'DUE_CUTOFF = "closing_cutoff"\n'
                 'DUE_WORKDAY_NEXT = "workday_next_month"\n'
                 'DUE_DAY_NEXT_MONTH = "day_next_month"\n'
                 'DUE_DAY_CAL_MONTH = "day_calendar_month"\n'
                 'DUE_DAY_AFTER_CUTOFF = "day_after_cutoff"\n'
                 'DUE_FIXED = "fixed_date"\n'
                 '# Legacy values for migration only\n'
                 'DUE_WORKDAY_MONTH = "workday_current_month"\n'
                 'DUE_END_CURRENT = "end_current_month"\n'
                 'DUE_LABEL_TO_VALUE = {\n'
                 '    "Abschluss-Stichtag": DUE_CUTOFF,\n'
                 '    "x. Werktag des Folgemonats": DUE_WORKDAY_NEXT,\n'
                 '    "x. Tag des Folgemonats": DUE_DAY_NEXT_MONTH,\n'
                 '    "x. Tag des Kalendermonats": DUE_DAY_CAL_MONTH,\n'
                 '    "x. Tag nach Abschluss-Stichtag": DUE_DAY_AFTER_CUTOFF,\n'
                 '    "Konkretes Datum": DUE_FIXED,\n'
                 '}\n'
                 'DUE_VALUE_TO_LABEL = {v: k for k, v in DUE_LABEL_TO_VALUE.items()}\n'
                 'WARN_YELLOW_DAYS = 10\n'
                 'WARN_ORANGE_DAYS = 5\n'
                 'MIN_PERIOD = "2025-2026"\n'
                 'MIN_MONTH_PERIOD = "2026-05"\n'
                 'FISCAL_YEAR_START_MONTH = 10\n'
                 '\n'
                 '\n'
                 'def fiscal_year_start_for_date(d=None):\n'
                 '    d = d or date.today()\n'
                 '    return d.year if d.month >= FISCAL_YEAR_START_MONTH else d.year - 1\n'
                 '\n'
                 '\n'
                 'def fiscal_year_key_for_start(start_year):\n'
                 '    return f"{start_year:04d}-{start_year + 1:04d}"\n'
                 '\n'
                 '\n'
                 'def august_month_key(start_year):\n'
                 '    return f"{start_year + 1:04d}-08"\n'
                 '\n'
                 '\n'
                 'def august_cutoff_reached(start_year, today=None):\n'
                 '    today = today or date.today()\n'
                 '    cutoff = None\n'
                 '    try:\n'
                 "        synced = cc.get_deadline_cutoff('monthly', august_month_key(start_year)) if cc is not None "
                 "and hasattr(cc, 'get_deadline_cutoff') else ''\n"
                 '        cutoff = parse_date(synced)\n'
                 '    except Exception:\n'
                 '        cutoff = None\n'
                 '    if not cutoff:\n'
                 "        y, m = map(int, august_month_key(start_year).split('-'))\n"
                 '        end = date(y, m, calendar.monthrange(y, m)[1])\n'
                 '        cur = end + timedelta(days=1)\n'
                 '        while not is_business_day(cur):\n'
                 '            cur += timedelta(days=1)\n'
                 '        cutoff = cur\n'
                 '    return today >= cutoff\n'
                 '\n'
                 '\n'
                 'def max_period_key(today=None):\n'
                 '    today = today or date.today()\n'
                 '    fy_start = fiscal_year_start_for_date(today)\n'
                 '    if august_cutoff_reached(fy_start, today):\n'
                 '        return fiscal_year_key_for_start(fy_start + 1)\n'
                 '    return fiscal_year_key_for_start(fy_start)\n'
                 '\n'
                 '\n'
                 'def bounded_current_period_key(today=None):\n'
                 '    today = today or date.today()\n'
                 '    current = fiscal_year_key(today)\n'
                 '    if current < MIN_PERIOD:\n'
                 '        return MIN_PERIOD\n'
                 '    max_key = max_period_key(today)\n'
                 '    return min(current, max_key)\n'
                 '\n'
                 '\n'
                 'def period_allowed(period, today=None):\n'
                 '    return MIN_PERIOD <= period <= max_period_key(today)\n'
                 '\n'
                 '\n'
                 'def iter_allowed_periods(today=None):\n'
                 '    periods = []\n'
                 '    cur = MIN_PERIOD\n'
                 '    max_key = max_period_key(today)\n'
                 '    while cur <= max_key:\n'
                 '        periods.append(cur)\n'
                 '        cur = add_year(cur, 1)\n'
                 '    return periods\n'
                 'COLORS = {\n'
                 '    "bg": "#E8EEF5", "header": "#D3DEE9", "blue": "#004B93", "red": "#E30613",\n'
                 '    "orange": "#F59E0B", "yellow": "#FACC15", "green": "#16A34A", "dark_green": "#047857",\n'
                 '    "text": "#182431", "text2": "#445364", "line": "#91A3B5", "white": "#FFFFFF",\n'
                 '    "edit_bg": "#FEF3C7", "subtask_bg": "#EAF4FF"  # v0.436 unified: Unteraufgaben-Tabellenfarbe ein '
                 'klein wenig blauer.\n'
                 '}\n'
                 '\n'
                 '\n'
                 'def _base_dir() -> Path:\n'
                 '    here = Path(__file__).resolve()\n'
                 '    if here.parent.name.lower() == "tools":\n'
                 '        return here.parent.parent / "Closing" / "YearlyClose"\n'
                 '    return here.parent / "bin" / "Closing" / "YearlyClose"\n'
                 '\n'
                 '\n'
                 'BASE_DIR = _base_dir()\n'
                 'PERIOD_DIR = BASE_DIR / "periods"\n'
                 'ATTACH_DIR = BASE_DIR / "attachments"\n'
                 'CONFIG_PATH = BASE_DIR / "yearly_close_config.json"\n'
                 'CATALOG_PATH = BASE_DIR / "yearly_close_task_catalog.json"\n'
                 'CLOSING_SCOPE = "J"\n'
                 'INITIAL_TASK_IDS = {}\n'
                 '\n'
                 'def fiscal_year_key(d=None):\n'
                 '    d = d or date.today()\n'
                 '    start_year = d.year if d.month >= 10 else d.year - 1\n'
                 '    return f"{start_year}-{start_year + 1}"\n'
                 '\n'
                 'def current_period_key():\n'
                 '    return bounded_current_period_key()\n'
                 '\n'
                 '\n'
                 'def add_year(key, delta):\n'
                 '    y1, y2 = map(int, key.split("-"))\n'
                 '    return f"{y1 + delta}-{y2 + delta}"\n'
                 '\n'
                 'def add_period(key, delta):\n'
                 '    return add_year(key, delta)\n'
                 '\n'
                 'def period_label(key):\n'
                 '    return f"Geschäftsjahr {key}"\n'
                 '\n'
                 'def parse_date(value):\n'
                 '    value = str(value or "").strip()\n'
                 '    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):\n'
                 '        try:\n'
                 '            return datetime.strptime(value, fmt).date()\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '    return None\n'
                 '\n'
                 '\n'
                 'def format_date_de(value):\n'
                 '    d = value if isinstance(value, date) else parse_date(value)\n'
                 '    return d.strftime("%d.%m.%Y") if d else ""\n'
                 '\n'
                 '\n'
                 '\n'
                 'def format_datetime_de(value):\n'
                 '    if not value:\n'
                 '        return ""\n'
                 '    try:\n'
                 '        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y %H:%M")\n'
                 '    except Exception:\n'
                 '        d = parse_date(value)\n'
                 '        return d.strftime("%d.%m.%Y") if d else str(value)\n'
                 '\n'
                 'def easter_sunday(year):\n'
                 '    a = year % 19; b = year // 100; c = year % 100; d = b // 4; e = b % 4\n'
                 '    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30\n'
                 '    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7\n'
                 '    m = (a + 11 * h + 22 * l) // 451\n'
                 '    month = (h + l - 7 * m + 114) // 31\n'
                 '    day = ((h + l - 7 * m + 114) % 31) + 1\n'
                 '    return date(year, month, day)\n'
                 '\n'
                 '\n'
                 'def bw_holidays(year):\n'
                 '    easter = easter_sunday(year)\n'
                 '    return {\n'
                 '        date(year, 1, 1), date(year, 1, 6), easter - timedelta(days=2), easter + timedelta(days=1),\n'
                 '        date(year, 5, 1), easter + timedelta(days=39), easter + timedelta(days=50), easter + '
                 'timedelta(days=60),\n'
                 '        date(year, 10, 3), date(year, 11, 1), date(year, 12, 25), date(year, 12, 26)\n'
                 '    }\n'
                 '\n'
                 '\n'
                 'def is_business_day(d):\n'
                 '    return d.weekday() < 5 and d not in bw_holidays(d.year)\n'
                 '\n'
                 '\n'
                 'def nth_business_day(year, month, n):\n'
                 '    n = max(1, int(n or 1))\n'
                 '    current = date(year, month, 1)\n'
                 '    count = 0\n'
                 '    while True:\n'
                 '        if is_business_day(current):\n'
                 '            count += 1\n'
                 '            if count == n:\n'
                 '                return current\n'
                 '        current += timedelta(days=1)\n'
                 '\n'
                 '\n'
                 'def normalize_team_name(team):\n'
                 '    return TEAM_ALIASES.get(team, team)\n'
                 '\n'
                 '\n'
                 'def normalize_team_members(data):\n'
                 '    members = data.setdefault("team_members", {})\n'
                 '    for old, new in TEAM_ALIASES.items():\n'
                 '        if old in members:\n'
                 '            if new not in members or not members.get(new):\n'
                 '                members[new] = members.get(old, [])\n'
                 '            members.pop(old, None)\n'
                 '    for team in TEAMS:\n'
                 '        value = members.get(team, [])\n'
                 '        if isinstance(value, str):\n'
                 '            value = [v.strip() for v in value.replace(";", "\\n").replace(",", "\\n").splitlines() '
                 'if v.strip()]\n'
                 '        members[team] = value\n'
                 '    return members\n'
                 '\n'
                 '\n'
                 'def set_team_members_text(data, team, text):\n'
                 '    normalize_team_members(data)[team] = [line.strip() for line in str(text or "").replace(";", '
                 '"\\n").replace(",", "\\n").splitlines() if line.strip()]\n'
                 '\n'
                 'def period_start(period):\n'
                 '    y1, _ = map(int, period.split("-"))\n'
                 '    return date(y1, 10, 1)\n'
                 '\n'
                 'def period_end(period):\n'
                 '    _, y2 = map(int, period.split("-"))\n'
                 '    return date(y2, 9, 30)\n'
                 '\n'
                 'def clamp_day_in_period(period, day):\n'
                 '    start = period_start(period)\n'
                 '    day = max(1, min(int(day or 1), calendar.monthrange(start.year, start.month)[1]))\n'
                 '    return date(start.year, start.month, day)\n'
                 '\n'
                 '\n'
                 'def first_business_day_after_period_end(period):\n'
                 '    cur = period_end(period) + timedelta(days=1)\n'
                 '    while not is_business_day(cur):\n'
                 '        cur += timedelta(days=1)\n'
                 '    return cur\n'
                 '\n'
                 'def default_due_date(period):\n'
                 '    return period_end(period).strftime("%Y-%m-%d")\n'
                 '\n'
                 'def resolve_due_date(task, data, period):\n'
                 '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                 '    if mode == DUE_CUTOFF:\n'
                 '        return normalize_cutoff(data, period)\n'
                 '    if mode == DUE_WORKDAY_NEXT:\n'
                 '        next_period = add_month(period, 1)\n'
                 '        y, m = map(int, next_period.split("-"))\n'
                 '        return nth_business_day(y, m, task.get("due_workday") or 1).strftime("%Y-%m-%d")\n'
                 '    if mode == DUE_DAY_NEXT_MONTH:\n'
                 "        if 'add_month' in globals():\n"
                 '            next_period = add_month(period, 1)\n'
                 "        elif 'add_quarter' in globals():\n"
                 '            next_period = add_quarter(period, 1)\n'
                 '        else:\n'
                 '            next_period = add_period(period, 1)\n'
                 '        return clamp_day_in_period(next_period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                 '    if mode == DUE_DAY_CAL_MONTH:\n'
                 '        return clamp_day_in_period(period, task.get("due_day") or 1).strftime("%Y-%m-%d")\n'
                 '    if mode == DUE_DAY_AFTER_CUTOFF:\n'
                 '        cutoff = parse_date(normalize_cutoff(data, period))\n'
                 '        days_after = max(0, int(task.get("due_day") or 0))\n'
                 '        return (cutoff + timedelta(days=days_after)).strftime("%Y-%m-%d") if cutoff else '
                 'normalize_cutoff(data, period)\n'
                 '    if mode == DUE_FIXED:\n'
                 '        due = parse_date(task.get("due_fixed_date") or task.get("due_date"))\n'
                 '        return due.strftime("%Y-%m-%d") if due else normalize_cutoff(data, period)\n'
                 '    return normalize_cutoff(data, period)\n'
                 '\n'
                 '\n'
                 '\n'
                 'def due_rule_text(task):\n'
                 '    mode = task.get("due_mode")\n'
                 '    if mode == DUE_CUTOFF:\n'
                 '        return "Abschluss-Stichtag"\n'
                 '    if mode == DUE_WORKDAY_NEXT:\n'
                 '        return f"{task.get(\'due_workday\') or 1}. Werktag Folgemonat"\n'
                 '    if mode == DUE_DAY_NEXT_MONTH:\n'
                 '        return f"{task.get(\'due_day\') or 1}. Tag Folgemonat"\n'
                 '    if mode == DUE_DAY_CAL_MONTH:\n'
                 '        return f"{task.get(\'due_day\') or 1}. Tag Kalendermonat"\n'
                 '    if mode == DUE_FIXED:\n'
                 '        return "Konkretes Datum"\n'
                 '    return ""\n'
                 '\n'
                 '\n'
                 'def due_display(task):\n'
                 '    rule = due_rule_text(task)\n'
                 '    return f"{format_date_de(task.get(\'due_date\', \'\'))}\\n{rule}" if rule else '
                 'format_date_de(task.get("due_date", ""))\n'
                 '\n'
                 '\n'
                 'def make_task_id(team, index):\n'
                 "    safe = str(team).lower().replace(' ', '_').replace('/', '_')\n"
                 "    safe = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in safe).strip('_') or 'task'\n"
                 '    return f"{safe}_{int(index or 1):02d}"\n'
                 '\n'
                 'def ensure_storage():\n'
                 '    BASE_DIR.mkdir(parents=True, exist_ok=True)\n'
                 '    PERIOD_DIR.mkdir(parents=True, exist_ok=True)\n'
                 '    ATTACH_DIR.mkdir(parents=True, exist_ok=True)\n'
                 '    if not CONFIG_PATH.exists():\n'
                 '        CONFIG_PATH.write_text(json.dumps({"teams": TEAMS, "warning_days": {"yellow": '
                 'WARN_YELLOW_DAYS, "orange": WARN_ORANGE_DAYS}}, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                 '    if not CATALOG_PATH.exists():\n'
                 '        CATALOG_PATH.write_text(json.dumps({"tasks": []}, ensure_ascii=False, indent=2), '
                 'encoding="utf-8")\n'
                 '\n'
                 '\n'
                 'def period_path(period):\n'
                 '    return PERIOD_DIR / f"{period}.json"\n'
                 '\n'
                 '\n'
                 '\n'
                 'def deadline_cutoff_date(period):\n'
                 '    try:\n'
                 "        if cc is not None and hasattr(cc, 'get_deadline_cutoff'):\n"
                 "            return cc.get_deadline_cutoff('yearly', period)\n"
                 '    except Exception:\n'
                 '        pass\n'
                 "    return ''\n"
                 '\n'
                 '\n'
                 'def default_cutoff_date(period):\n'
                 '    synced = deadline_cutoff_date(period)\n'
                 '    if synced:\n'
                 '        return synced\n'
                 '    return first_business_day_after_period_end(period).strftime("%Y-%m-%d")\n'
                 '\n'
                 '\n'
                 'def normalize_cutoff(data, period):\n'
                 '    synced = deadline_cutoff_date(period)\n'
                 '    cutoff = parse_date(synced) if synced else parse_date(data.get("closing_cutoff_date", ""))\n'
                 '    if not cutoff:\n'
                 '        cutoff = parse_date(default_cutoff_date(period))\n'
                 '    data["closing_cutoff_date"] = cutoff.strftime("%Y-%m-%d")\n'
                 '    return data["closing_cutoff_date"]\n'
                 '\n'
                 '\n'
                 'def all_subtasks_done(task):\n'
                 '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                 '    return bool(subtasks) and all(s.get("status") == STATUS_DONE for s in subtasks)\n'
                 '\n'
                 '\n'
                 'def sync_parent_status_from_subtasks(task):\n'
                 '    subtasks = [s for s in task.get("subtasks", []) if not s.get("deleted")]\n'
                 '    if subtasks:\n'
                 '        if all(s.get("status") == STATUS_DONE for s in subtasks):\n'
                 '            task["status"] = STATUS_DONE\n'
                 '            task.setdefault("done_at", datetime.now().isoformat(timespec="seconds"))\n'
                 '        elif task.get("status") == STATUS_DONE:\n'
                 '            task["status"] = STATUS_OPEN\n'
                 '            task["done_at"] = None\n'
                 '            task["done_by"] = None\n'
                 '\n'
                 '\n'
                 'def migrate_due_fields(task, data, period):\n'
                 '    mode = task.get("due_mode", DUE_CUTOFF)\n'
                 '    if mode == DUE_WORKDAY_NEXT:\n'
                 '        task["due_mode"] = DUE_WORKDAY_NEXT\n'
                 '    elif mode in (DUE_FIXED,):\n'
                 '        task["due_mode"] = DUE_FIXED\n'
                 '    elif mode in (DUE_WORKDAY_MONTH, DUE_END_CURRENT):\n'
                 '        task["due_mode"] = DUE_CUTOFF\n'
                 '    elif mode not in (DUE_CUTOFF, DUE_WORKDAY_NEXT, DUE_DAY_NEXT_MONTH, DUE_DAY_CAL_MONTH, '
                 'DUE_DAY_AFTER_CUTOFF, DUE_FIXED):\n'
                 '        task["due_mode"] = DUE_CUTOFF\n'
                 '    if task.get("due_mode") in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF):\n'
                 '        task["due_day"] = int(task.get("due_day") or task.get("due_workday") or 1)\n'
                 '\n'
                 '\n'
                 'def normalize_task(task, data, period):\n'
                 '    task["team"] = normalize_team_name(task.get("team"))\n'
                 '    task.pop("task_uid", None)  # v0.436: Aufgaben-ID-Zuweisung vollständig entfernt.\n'
                 '    task.setdefault("owner_user_key", "")\n'
                 '    task.setdefault("attachments", [])\n'
                 '    task.setdefault("comments", [])\n'
                 '    task.setdefault("subtasks", [])\n'
                 '    task.setdefault("status", STATUS_OPEN)\n'
                 '    task.setdefault("deadline_type", "intern")\n'
                 '    task.setdefault("priority", "normal")\n'
                 '    task.setdefault("due_day", None)\n'
                 '    task.setdefault("due_workday", None)\n'
                 '    task.setdefault("recurring", False)\n'
                 '    task.setdefault("catalog_id", "")\n'
                 '    task.setdefault("booking_circle", "IDE")\n'
                 '    if task["deadline_type"] not in DEADLINE_TYPES:\n'
                 '        task["deadline_type"] = "intern"\n'
                 '    migrate_due_fields(task, data, period)\n'
                 '    task["due_date"] = resolve_due_date(task, data, period)\n'
                 '    for idx, sub in enumerate(task.get("subtasks", []), start=1):\n'
                 '        sub.setdefault("id", f"sub_{idx:02d}")\n'
                 '        sub.setdefault("title", "")\n'
                 '        sub.setdefault("status", STATUS_OPEN)\n'
                 '        sub.pop("task_uid", None)  # v0.436: Unteraufgaben-ID-Zuweisung entfernt.\n'
                 '    sync_parent_status_from_subtasks(task)\n'
                 '    return task\n'
                 '\n'
                 '\n'
                 'def load_catalog():\n'
                 '    ensure_storage()\n'
                 '    try:\n'
                 '        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))\n'
                 '    except Exception:\n'
                 '        data = {"tasks": []}\n'
                 '    data.setdefault("tasks", [])\n'
                 '    try:\n'
                 "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437') and "
                 "cc.sync_task_catalog_uids_v0437('yearly', data):\n"
                 '            save_catalog(data)\n'
                 '    except Exception:\n'
                 '        pass\n'
                 '    return data\n'
                 '\n'
                 '\n'
                 'def save_catalog(data):\n'
                 '    data.setdefault("tasks", [])\n'
                 '    try:\n'
                 "        if cc is not None and hasattr(cc, 'sync_task_catalog_uids_v0437'):\n"
                 "            cc.sync_task_catalog_uids_v0437('yearly', data)\n"
                 '    except Exception:\n'
                 '        pass\n'
                 '    CATALOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                 '\n'
                 '\n'
                 'def default_tasks(period):\n'
                 '    return []\n'
                 '\n'
                 'def load_period(period):\n'
                 '    ensure_storage()\n'
                 '    path = period_path(period)\n'
                 '    if not path.exists():\n'
                 '        data = {"period": period, "created_at": datetime.now().isoformat(timespec="seconds"), '
                 '"closing_cutoff_date": default_cutoff_date(period), "team_members": {team: [] for team in TEAMS}, '
                 '"tasks": default_tasks(period)}\n'
                 '        save_period(period, data)\n'
                 '        return data\n'
                 '    data = json.loads(path.read_text(encoding="utf-8"))\n'
                 '    data.setdefault("tasks", [])\n'
                 '    normalize_team_members(data)\n'
                 '    old_cutoff = data.get("closing_cutoff_date", "")\n'
                 '    normalize_cutoff(data, period)\n'
                 '    changed = old_cutoff != data.get("closing_cutoff_date", "")\n'
                 '    for task in data["tasks"]:\n'
                 '        old_team = task.get("team")\n'
                 '        normalize_task(task, data, period)\n'
                 '        changed = changed or old_team != task.get("team")\n'
                 '    try:\n'
                 "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                 "            changed = cc.ensure_task_identity_for_period_v0437('yearly', period, data) or changed\n"
                 '    except Exception:\n'
                 '        pass\n'
                 '    if changed:\n'
                 '        save_period(period, data)\n'
                 '    return data\n'
                 '\n'
                 '\n'
                 'def save_period(period, data):\n'
                 '    ensure_storage()\n'
                 '    normalize_team_members(data)\n'
                 '    normalize_cutoff(data, period)\n'
                 '    for task in data.get("tasks", []):\n'
                 '        normalize_task(task, data, period)\n'
                 '    try:\n'
                 "        if cc is not None and hasattr(cc, 'ensure_task_identity_for_period_v0437'):\n"
                 "            cc.ensure_task_identity_for_period_v0437('yearly', period, data)\n"
                 '    except Exception:\n'
                 '        pass\n'
                 '    period_path(period).write_text(json.dumps(data, ensure_ascii=False, indent=2), '
                 'encoding="utf-8")\n'
                 '\n'
                 '\n'
                 'def catalog_entry_to_task(entry, period, index):\n'
                 '    data_stub = {"closing_cutoff_date": default_cutoff_date(period)}\n'
                 '    task = {\n'
                 '        "id": make_task_id(entry.get("team", "Team"), index), "team": '
                 'normalize_team_name(entry.get("team")), "title": entry.get("title"),\n'
                 '        "owner": entry.get("owner", entry.get("team")), "owner_user_key": '
                 'entry.get("owner_user_key", ""),\n'
                 '        "due_mode": entry.get("due_mode", DUE_CUTOFF), "due_day": entry.get("due_day"), '
                 '"due_workday": entry.get("due_workday"), "due_fixed_date": entry.get("due_fixed_date", '
                 'entry.get("due_date", "")),\n'
                 '        "deadline_type": entry.get("deadline_type", "intern"), "priority": entry.get("priority", '
                 '"normal"),\n'
                 '        "required": entry.get("required", True), "recurring": True, "catalog_id": '
                 'entry.get("catalog_id", ""),\n'
                 '        "status": STATUS_OPEN, "attachments": [], "comments": [], "subtasks": [], "done_at": None, '
                 '"done_by": None,\n'
                 '    }\n'
                 '    task["due_date"] = resolve_due_date(task, data_stub, period)\n'
                 '    return task\n'
                 '\n'
                 '\n'
                 'def apply_catalog_to_period(period):\n'
                 '    data = load_period(period)\n'
                 '    catalog = load_catalog()\n'
                 '    changed = False\n'
                 '    tasks = data.setdefault("tasks", [])\n'
                 '    for entry in catalog.get("tasks", []):\n'
                 '        if not entry.get("recurring", True):\n'
                 '            continue\n'
                 '        start_period = entry.get("start_period", current_period_key())\n'
                 '        if period <= start_period:\n'
                 '            continue\n'
                 '        catalog_id = entry.get("catalog_id")\n'
                 '        existing = next((t for t in tasks if t.get("catalog_id") == catalog_id and not '
                 't.get("deleted")), None)\n'
                 '        if existing:\n'
                 '            keep = {"status": existing.get("status", STATUS_OPEN), "attachments": '
                 'existing.get("attachments", []), "comments": existing.get("comments", []), "subtasks": '
                 'existing.get("subtasks", []), "done_at": existing.get("done_at"), "done_by": '
                 'existing.get("done_by")}\n'
                 '            existing.update(catalog_entry_to_task(entry, period, len([t for t in tasks if '
                 't.get("team") == entry.get("team")]) + 1))\n'
                 '            existing.update(keep)\n'
                 '            changed = True\n'
                 '        else:\n'
                 '            idx = len([t for t in tasks if t.get("team") == entry.get("team")]) + 1\n'
                 '            tasks.append(catalog_entry_to_task(entry, period, idx))\n'
                 '            changed = True\n'
                 '    if changed:\n'
                 '        save_period(period, data)\n'
                 '    return data\n'
                 '\n'
                 'def cleanup_old_periods():\n'
                 '    ensure_storage()\n'
                 '    # v0.432: Alte/vorzeitige Periodendateien werden nicht gelöscht, aber nicht mehr angezeigt oder '
                 'automatisch angelegt.\n'
                 '    return\n'
                 '\n'
                 '\n'
                 'def ensure_period_window():\n'
                 '    ensure_storage(); cleanup_old_periods()\n'
                 '    for p in iter_allowed_periods():\n'
                 '        load_period(p)\n'
                 '        apply_catalog_to_period(p)\n'
                 '\n'
                 '\n'
                 'def list_periods():\n'
                 '    ensure_period_window()\n'
                 '    allowed = set(iter_allowed_periods())\n'
                 '    return sorted(p.stem for p in PERIOD_DIR.glob("*.json") if p.stem in allowed)\n'
                 '\n'
                 '\n'
                 'def warning_level(task, today=None):\n'
                 '    if task.get("status") == STATUS_DONE or task.get("deadline_type") == "keine":\n'
                 '        return "done" if task.get("status") == STATUS_DONE else "none"\n'
                 '    due = parse_date(task.get("due_date", ""))\n'
                 '    if not due:\n'
                 '        return "none"\n'
                 '    today = today or date.today()\n'
                 '    days = (due - today).days\n'
                 '    if days < 0: return "overdue"\n'
                 '    if days == 0: return "today"\n'
                 '    if days <= WARN_ORANGE_DAYS: return "orange"\n'
                 '    if days <= WARN_YELLOW_DAYS: return "yellow"\n'
                 '    return "none"\n'
                 '\n'
                 '\n'
                 'def progress_color(percent):\n'
                 '    if percent >= 100: return COLORS["dark_green"]\n'
                 '    if percent >= 75: return COLORS["green"]\n'
                 '    if percent >= 50: return COLORS["yellow"]\n'
                 '    if percent >= 25: return COLORS["orange"]\n'
                 '    return COLORS["red"]\n'
                 '\n'
                 '\n'
                 'def calc_stats(tasks):\n'
                 '    """Fortschritt inkl. Unteraufgaben berechnen.\n'
                 '    Hauptaufgaben und nicht gelöschte Unteraufgaben zählen als Fortschrittseinheiten.\n'
                 '    """\n'
                 '    visible = [t for t in tasks if not t.get("deleted")]\n'
                 '    units = []\n'
                 '    for task in visible:\n'
                 '        units.append(task)\n'
                 '        for sub in task.get("subtasks", []) or []:\n'
                 '            if not sub.get("deleted"):\n'
                 '                units.append(sub)\n'
                 '    total = len(units)\n'
                 '    done = sum(1 for item in units if item.get("status") == STATUS_DONE)\n'
                 '    in_progress = sum(1 for item in units if item.get("status") == STATUS_IN_PROGRESS)\n'
                 '    open_count = total - done - in_progress\n'
                 '    overdue = sum(1 for t in visible if warning_level(t) == "overdue")\n'
                 '    critical = sum(1 for t in visible if warning_level(t) in ("overdue", "today", "orange") or '
                 '(t.get("priority") == "kritisch" and t.get("deadline_type") != "keine"))\n'
                 '    sub_total = max(0, total - len(visible))\n'
                 '    sub_done = sum(1 for task in visible for sub in (task.get("subtasks", []) or []) if not '
                 'sub.get("deleted") and sub.get("status") == STATUS_DONE)\n'
                 '    percent = int(round((done / total) * 100)) if total else 0\n'
                 '    return {"total": total, "done": done, "in_progress": in_progress, "open": open_count, "overdue": '
                 'overdue, "critical": critical, "percent": percent, "task_total": len(visible), "subtask_total": '
                 'sub_total, "subtask_done": sub_done}\n'
                 '\n'
                 '\n'
                 'class YearlyCloseUI:\n'
                 '    def __init__(self, app):\n'
                 '        self.app = app\n'
                 '        self.root = app.root\n'
                 '        self.canvas = app.canvas\n'
                 '        ensure_period_window()\n'
                 '        self.period = current_period_key()\n'
                 '        self.data = apply_catalog_to_period(self.period)\n'
                 '        self.selected_team = None\n'
                 '        self.expanded_tasks = set()\n'
                 '        self.edit_mode = False\n'
                 '        self.tooltip = None\n'
                 '        self._live_period_mtime = 0\n'
                 '        self._live_period_refresh_started = False\n'
                 '        self._live_period_popup_open = False\n'
                 '        self._live_period_notice_shown = False\n'
                 '        self._live_task_widgets = {}\n'
                 '        self._live_subtask_widgets = {}\n'
                 '        self.frame = tk.Frame(self.root, bg=COLORS["bg"])\n'
                 '        self.app.widget_items.append(self.frame)\n'
                 '        self.app.module_escape_handler = self.handle_escape\n'
                 '        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", '
                 'width=self.canvas.winfo_width(), height=max(400, self.canvas.winfo_height() - 172))\n'
                 '        self.strip_task_ids_all_periods()\n'
                 '        self.render_dashboard()\n'
                 '        apply_readable_fonts(self.frame, self.app, 12)\n'
                 '        self.bind_module_ctrl_mousewheel_guard()  \n'
                 '\n'
                 '\n'
                 '    def _period_file_mtime(self):\n'
                 '        try:\n'
                 '            path = period_path(self.period)\n'
                 '            return path.stat().st_mtime if path.exists() else 0\n'
                 '        except Exception:\n'
                 '            return 0\n'
                 '\n'
                 '    def _start_live_period_refresh(self):\n'
                 '        if getattr(self, "_live_period_refresh_started", False):\n'
                 '            return\n'
                 '        self._live_period_refresh_started = True\n'
                 '        try:\n'
                 '            self.root.after(3000, self._check_live_period_refresh)\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _task_live_key(self, task):\n'
                 '        try:\n'
                 '            return self.task_match_key(task)\n'
                 '        except Exception:\n'
                 '            return "|".join([str(task.get("team", "")), str(task.get("catalog_id", "")), '
                 'str(task.get("title", ""))])\n'
                 '\n'
                 '    def _subtask_live_key(self, task, subtask):\n'
                 '        return self._task_live_key(task) + "::sub::" + str(subtask.get("catalog_id") or '
                 'subtask.get("title") or subtask.get("id") or "")\n'
                 '\n'
                 '    def _visible_tasks_from_data(self, data, team=None):\n'
                 '        tasks = [t for t in data.get("tasks", []) if not t.get("deleted")]\n'
                 '        if team:\n'
                 '            tasks = [t for t in tasks if t.get("team") == team]\n'
                 '        return sorted(tasks, key=lambda t: str(t.get("title", "")).casefold())\n'
                 '\n'
                 '    def _live_structure_signature(self, data):\n'
                 '        sig = []\n'
                 '        for t in self._visible_tasks_from_data(data, None):\n'
                 '            subs = tuple((self._subtask_live_key(t, s), s.get("title", ""), s.get("owner", ""), '
                 's.get("owner_user_key", "")) for s in sorted([x for x in t.get("subtasks", []) if not '
                 'x.get("deleted")], key=lambda x: str(x.get("title", "")).casefold()))\n'
                 '            sig.append((self._task_live_key(t), t.get("team", ""), t.get("title", ""), '
                 't.get("owner", ""), t.get("owner_user_key", ""), t.get("due_date", ""), t.get("due_mode", ""), '
                 't.get("deadline_type", ""), t.get("priority", ""), bool(t.get("recurring")), subs))\n'
                 '        return tuple(sig)\n'
                 '\n'
                 '    def _live_status_signature(self, data):\n'
                 '        sig = []\n'
                 '        for t in self._visible_tasks_from_data(data, None):\n'
                 '            subs = tuple((self._subtask_live_key(t, s), s.get("status", STATUS_OPEN), '
                 's.get("done_at"), s.get("done_by"), len(s.get("attachments", [])), len(s.get("comments", []))) for s '
                 'in sorted([x for x in t.get("subtasks", []) if not x.get("deleted")], key=lambda x: '
                 'str(x.get("title", "")).casefold()))\n'
                 '            sig.append((self._task_live_key(t), t.get("status", STATUS_OPEN), t.get("done_at"), '
                 't.get("done_by"), len(t.get("attachments", [])), len(t.get("comments", [])), subs))\n'
                 '        return tuple(sig)\n'
                 '\n'
                 '    def _widgets_recursive(self, widget):\n'
                 '        yield widget\n'
                 '        try:\n'
                 '            children = widget.winfo_children()\n'
                 '        except Exception:\n'
                 '            children = []\n'
                 '        for child in children:\n'
                 '            yield from self._widgets_recursive(child)\n'
                 '\n'
                 '    def _safe_config(self, widget, **kwargs):\n'
                 '        try:\n'
                 '            if widget is not None:\n'
                 '                widget.configure(**kwargs)\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _set_row_background(self, widgets, bg):\n'
                 '        for widget in widgets or []:\n'
                 '            for item in self._widgets_recursive(widget):\n'
                 '                try:\n'
                 '                    cls = item.winfo_class()\n'
                 '                except Exception:\n'
                 '                    cls = ""\n'
                 '                if cls in ("Frame", "Label", "Button", "Menubutton"):\n'
                 '                    self._safe_config(item, bg=bg)\n'
                 '\n'
                 '    def _register_live_task_widgets(self, table, row_idx, task, done_button, status_var, '
                 'status_menu):\n'
                 '        try:\n'
                 '            self._live_task_widgets[self._task_live_key(task)] = {"row_widgets": '
                 'list(table.grid_slaves(row=row_idx)), "done_button": done_button, "status_var": status_var, '
                 '"status_menu": status_menu}\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _register_live_subtask_widgets(self, table, row_idx, task, subtask, done_button):\n'
                 '        try:\n'
                 '            self._live_subtask_widgets[self._subtask_live_key(task, subtask)] = {"row_widgets": '
                 'list(table.grid_slaves(row=row_idx)), "done_button": done_button}\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _refresh_option_menu_commands(self, menu, status_var, task):\n'
                 '        try:\n'
                 '            menu_widget = menu["menu"]\n'
                 '            menu_widget.delete(0, "end")\n'
                 '            for status in STATUSES:\n'
                 '                menu_widget.add_command(label=status, command=tk._setit(status_var, status, lambda '
                 'value, t=task: self.set_status(t, value)))\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _apply_button_status(self, button, item, command, can_complete=True, subtask=False):\n'
                 '        try:\n'
                 '            status = item.get("status", STATUS_OPEN)\n'
                 '            bg = "#BBF7D0" if status == STATUS_DONE else (COLORS["subtask_bg"] if subtask else '
                 '("#FFF7ED" if warning_level(item) in ("overdue", "today", "orange") else COLORS["white"]))\n'
                 '            fg = COLORS["dark_green"] if status == STATUS_DONE else COLORS["text"]\n'
                 '            button.configure(text="✓" if status == STATUS_DONE else "□", bg=bg, fg=fg, '
                 'command=command, state="normal" if can_complete else "disabled")\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _apply_smooth_status_update(self, new_data):\n'
                 '        new_tasks = {self._task_live_key(t): t for t in self._visible_tasks_from_data(new_data, '
                 'self.selected_team)}\n'
                 '        self.data = new_data\n'
                 '        for key, task in new_tasks.items():\n'
                 '            entry = getattr(self, "_live_task_widgets", {}).get(key)\n'
                 '            if entry:\n'
                 '                bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if '
                 'warning_level(task) in ("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", '
                 '"IMS":"#FFF4CC", "SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), '
                 'COLORS["white"])\n'
                 '                self._set_row_background(entry.get("row_widgets"), bg)\n'
                 '                can_complete = self.can_complete_task(task) and (not task.get("subtasks") or '
                 'all_subtasks_done(task))\n'
                 '                self._apply_button_status(entry.get("done_button"), task, lambda t=task: '
                 'self.toggle_done(t), can_complete, False)\n'
                 '                try: entry.get("status_var").set(task.get("status", STATUS_OPEN))\n'
                 '                except Exception: pass\n'
                 '                self._safe_config(entry.get("status_menu"), bg=bg, state="normal" if can_complete '
                 'else "disabled")\n'
                 '                self._refresh_option_menu_commands(entry.get("status_menu"), '
                 'entry.get("status_var"), task)\n'
                 '            for sub in [s for s in task.get("subtasks", []) if not s.get("deleted")]:\n'
                 '                sentry = getattr(self, "_live_subtask_widgets", {}).get(self._subtask_live_key(task, '
                 'sub))\n'
                 '                if not sentry:\n'
                 '                    continue\n'
                 '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                 '                self._set_row_background(sentry.get("row_widgets"), sub_bg)\n'
                 '                self._apply_button_status(sentry.get("done_button"), sub, lambda t=task, s=sub: '
                 'self.toggle_subtask(t, s), self.can_complete_task(task), True)\n'
                 '\n'
                 '    def _current_scroll_fraction(self):\n'
                 '        try:\n'
                 '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                 '            return canvas.yview()[0] if canvas is not None else None\n'
                 '        except Exception:\n'
                 '            return None\n'
                 '\n'
                 '    def _restore_scroll_after_render(self, fraction):\n'
                 '        try:\n'
                 '            canvas = getattr(self.app, "active_scroll_canvas", None)\n'
                 '            if canvas is not None and fraction is not None:\n'
                 '                self.root.after_idle(lambda c=canvas, f=fraction: c.yview_moveto(f))\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def _show_live_refresh_notice_once(self):\n'
                 '        if getattr(self, "_live_period_popup_open", False) or getattr(self, '
                 '"_live_period_notice_shown", False):\n'
                 '            return\n'
                 '        self._live_period_notice_shown = True\n'
                 '        self._live_period_popup_open = True\n'
                 '        try:\n'
                 '            messagebox.showinfo("Abschlusskalender", "Dieser Abschlusskalender wurde durch einen '
                 'anderen Benutzer aktualisiert. Die Ansicht wurde live neu geladen.")\n'
                 '        finally:\n'
                 '            self._live_period_popup_open = False\n'
                 '\n'
                 '    def _check_live_period_refresh(self):\n'
                 '        try:\n'
                 '            current_mtime = self._period_file_mtime()\n'
                 '            known_mtime = getattr(self, "_live_period_mtime", 0)\n'
                 '            if current_mtime and known_mtime and current_mtime != known_mtime:\n'
                 '                old_data = self.data\n'
                 '                new_data = load_period(self.period)\n'
                 '                old_structure = self._live_structure_signature(old_data)\n'
                 '                new_structure = self._live_structure_signature(new_data)\n'
                 '                old_status = self._live_status_signature(old_data)\n'
                 '                new_status = self._live_status_signature(new_data)\n'
                 '                self._live_period_mtime = current_mtime\n'
                 '                if old_structure == new_structure and old_status != new_status and '
                 'self.selected_team:\n'
                 '                    self._apply_smooth_status_update(new_data)\n'
                 '                elif old_structure == new_structure and old_status == new_status:\n'
                 '                    self.data = new_data\n'
                 '                else:\n'
                 '                    selected_team = self.selected_team\n'
                 '                    expanded = set(getattr(self, "expanded_tasks", set()))\n'
                 '                    was_edit_mode = bool(getattr(self, "edit_mode", False))\n'
                 '                    scroll_fraction = self._current_scroll_fraction()\n'
                 '                    self.data = new_data\n'
                 '                    self.expanded_tasks = expanded\n'
                 '                    if selected_team:\n'
                 '                        self.selected_team = selected_team\n'
                 '                        self.render_team_detail(selected_team)\n'
                 '                    else:\n'
                 '                        self.render_dashboard()\n'
                 '                    self._restore_scroll_after_render(scroll_fraction)\n'
                 '                    if was_edit_mode:\n'
                 '                        self._show_live_refresh_notice_once()\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '        try:\n'
                 '            self.root.after(3000, self._check_live_period_refresh)\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def handle_escape(self):\n'
                 '        if self.selected_team:\n'
                 '            self.selected_team = None\n'
                 '            self.render_dashboard()\n'
                 '            return True\n'
                 '        return False\n'
                 '\n'
                 '    def _module_ctrl_mousewheel_direction(self, event):\n'
                 '        try:\n'
                 '            if getattr(event, "num", None) == 4:\n'
                 '                return 1\n'
                 '            if getattr(event, "num", None) == 5:\n'
                 '                return -1\n'
                 '            delta = int(getattr(event, "delta", 0) or 0)\n'
                 '            return 1 if delta > 0 else (-1 if delta < 0 else 0)\n'
                 '        except Exception:\n'
                 '            return 0\n'
                 '\n'
                 '    def handle_module_ctrl_mousewheel(self, event=None):\n'
                 '        """v0.435: Strg+Mausrad im Abschlusskalender bleibt im aktuellen Kontext.\n'
                 '\n'
                 '        Hintergrund: Der globale Tool-Zoom kann das externe Tool neu laden und dadurch aus\n'
                 '        der Teamübersicht zurück ins Dashboard springen. Deshalb wird der Zoom hier lokal\n'
                 '        angewendet und die aktuell ausgewählte Teamansicht anschließend wiederhergestellt.\n'
                 '        """\n'
                 '        direction = self._module_ctrl_mousewheel_direction(event)\n'
                 '        if not direction:\n'
                 '            return "break"\n'
                 '        try:\n'
                 '            current = float(getattr(self.app, "current_scope_zoom", 1.0) or 1.0)\n'
                 '        except Exception:\n'
                 '            current = 1.0\n'
                 '        try:\n'
                 '            step = float(getattr(self.app, "GLOBAL_TEXT_ZOOM_STEP", 0.025) or 0.025)\n'
                 '        except Exception:\n'
                 '            step = 0.025\n'
                 '        new_zoom = max(0.70, min(1.80, current + (step * direction)))\n'
                 '        try:\n'
                 '            setattr(self.app, "current_scope_zoom", new_zoom)\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '        team = self.selected_team\n'
                 '        if team:\n'
                 '            try:\n'
                 '                self.render_team_detail(team)\n'
                 '            except Exception:\n'
                 '                apply_readable_fonts(self.frame, self.app, 12)\n'
                 '        else:\n'
                 '            try:\n'
                 '                self.render_dashboard()\n'
                 '            except Exception:\n'
                 '                apply_readable_fonts(self.frame, self.app, 12)\n'
                 '        return "break"\n'
                 '\n'
                 '    def bind_module_ctrl_mousewheel_guard(self, widget=None):\n'
                 '        """Bindet Strg+Mausrad auf alle Modulwidgets, damit der globale Handler nicht navigiert."""\n'
                 '        widget = widget or self.frame\n'
                 '        try:\n'
                 '            for sequence in ("<Control-MouseWheel>", "<Control-Button-4>", "<Control-Button-5>"):\n'
                 '                widget.bind(sequence, self.handle_module_ctrl_mousewheel)\n'
                 '            for child in widget.winfo_children():\n'
                 '                self.bind_module_ctrl_mousewheel_guard(child)\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '\n'
                 '    def can_edit(self):\n'
                 '        return self.role_rank_value() >= 3 and not self.is_period_closed()\n'
                 '\n'
                 '    def user_choices(self):\n'
                 '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                 '        choices = [("", "Team / keine Person")]\n'
                 '        for key, data in sorted(users.items(), key=lambda item: item[1].get("display_name", '
                 'item[0]).casefold()):\n'
                 '            choices.append((key, data.get("display_name", key)))\n'
                 '        return choices\n'
                 '\n'
                 '\n'
                 '    def _target_period_from_current(self):\n'
                 '        y, m = map(int, self.period.split("-")); return f"{y}-Q{((m - 1) // 3) + 1}"\n'
                 '    def _target_periods_from(self, start_period, all_following):\n'
                 '        if not all_following: return [start_period]\n'
                 '        y, q = start_period.split("-Q"); y=int(y); q=int(q); out=[]\n'
                 '        for _ in range(12):\n'
                 '            out.append(f"{y}-Q{q}"); q += 1\n'
                 '            if q > 4: q = 1; y += 1\n'
                 '        return out\n'
                 '    def _target_period_end(self, period):\n'
                 '        y, q = period.split("-Q"); y=int(y); m=(int(q)-1)*3+3; return date(y, m, '
                 'calendar.monthrange(y, m)[1]).strftime("%Y-%m-%d")\n'
                 '    def _target_display(self, period):\n'
                 '        y, q = period.split("-Q"); return f"{q}. Quartal {y}"\n'
                 '\n'
                 '    def is_standard_user(self):\n'
                 '        return self.role_rank_value() <= 2\n'
                 '    def can_complete_task(self, task):\n'
                 '        if self.is_period_closed(): return False\n'
                 '        if not self.is_standard_user(): return True\n'
                 '        return bool(getattr(self.app, "current_user_key", "") and task.get("owner_user_key") == '
                 'getattr(self.app, "current_user_key", ""))\n'
                 '\n'
                 '    def current_user_full_name(self):\n'
                 '        key = getattr(self.app, "current_user_key", "")\n'
                 '        data = getattr(self.app, "user_data", {}).get("users", {}).get(key, {}) if key else {}\n'
                 '        return data.get("full_name") or " ".join(x for x in [data.get("first_name", "").strip(), '
                 'data.get("display_name", "").strip()] if x).strip() or getattr(self.app, "current_user_display", "") '
                 'or key or ""\n'
                 '\n'
                 '    def role_rank_value(self):\n'
                 '        role = self.app.my_role() if hasattr(self.app, "my_role") else "E1 - Standard"\n'
                 '        mapping = {"E1 - Standard": 1, "E2 - Erweitert": 2, "E3 - Administrator": 3, "E4 - '
                 'System-Administrator": 4, "Standard": 1, "Administrator": 3, "System-Administrator": 4, "Wagnerm": '
                 '4}\n'
                 '        return mapping.get(role, 1)\n'
                 '\n'
                 '    def ensure_close_metadata(self):\n'
                 '        self.data.setdefault("closed", False)\n'
                 '        self.data.setdefault("closed_at", None)\n'
                 '        self.data.setdefault("closed_by", "")\n'
                 '        self.data.setdefault("closed_by_key", "")\n'
                 '        self.data.setdefault("reopened_once", False)\n'
                 '        self.data.setdefault("close_events", [])\n'
                 '        self.data.setdefault("change_log", [])\n'
                 '        self.data.setdefault("reopen_email_log", [])\n'
                 '\n'
                 '    def is_period_closed(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        return bool(self.data.get("closed"))\n'
                 '\n'
                 '    def is_after_cutoff(self):\n'
                 '        cutoff = parse_date(self.data.get("closing_cutoff_date"))\n'
                 '        return bool(cutoff and date.today() > cutoff)\n'
                 '\n'
                 '    def can_toggle_period_close(self):\n'
                 '        return self.role_rank_value() >= 3\n'
                 '\n'
                 '    def require_unlocked(self, action="Diese Änderung"):\n'
                 '        if self.is_period_closed():\n'
                 '            messagebox.showwarning("Zeitraum geschlossen", f"{action} ist nicht möglich, weil der '
                 'Zeitraum geschlossen ist. Bitte den Zeitraum zuerst wieder öffnen.")\n'
                 '            return False\n'
                 '        return True\n'
                 '\n'
                 '    def log_period_event(self, action, reason="", extra=None):\n'
                 '        self.ensure_close_metadata()\n'
                 '        self.data.setdefault("close_events", []).append({\n'
                 '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                 '            "action": action,\n'
                 '            "user": self.current_user_full_name(),\n'
                 '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                 '            "reason": reason,\n'
                 '            "extra": extra or {},\n'
                 '        })\n'
                 '\n'
                 '    def log_change(self, action, task=None, field="", old="", new=""):\n'
                 '        self.ensure_close_metadata()\n'
                 '        after_reopen = bool(self.data.get("reopened_once")) and not self.data.get("closed")\n'
                 '        self.data.setdefault("change_log", []).append({\n'
                 '            "timestamp": datetime.now().isoformat(timespec="seconds"),\n'
                 '            "user": self.current_user_full_name(),\n'
                 '            "user_key": getattr(self.app, "current_user_key", ""),\n'
                 '            "action": action,\n'
                 '            "task_title": task.get("title", "") if isinstance(task, dict) else "",\n'
                 '            "field": field,\n'
                 '            "old": str(old) if old is not None else "",\n'
                 '            "new": str(new) if new is not None else "",\n'
                 '            "after_reopen": after_reopen,\n'
                 '        })\n'
                 '\n'
                 '    def close_status_text(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        if self.data.get("closed"):\n'
                 '            return f"(zuletzt) abgeschlossen am {format_datetime_de(self.data.get(\'closed_at\'))} '
                 'durch {self.data.get(\'closed_by\', \'\')}"\n'
                 '        events = self.data.get("close_events", [])\n'
                 '        reopen = next((e for e in reversed(events) if e.get("action") == "opened"), None)\n'
                 '        if reopen:\n'
                 '            return f"Wieder geöffnet am {format_datetime_de(reopen.get(\'timestamp\'))} durch '
                 '{reopen.get(\'user\', \'\')}"\n'
                 '        return ""\n'
                 '\n'
                 '    def e3_e4_recipients(self):\n'
                 '        recipients=[]\n'
                 '        users = getattr(self.app, "user_data", {}).get("users", {})\n'
                 '        opener = getattr(self.app, "current_user_key", "")\n'
                 '        for key, data in users.items():\n'
                 '            if key == opener:\n'
                 '                continue\n'
                 '            role = data.get("permission", "")\n'
                 '            rank = {"E1 - Standard":1,"E2 - Erweitert":2,"E3 - Administrator":3,"E4 - '
                 'System-Administrator":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}.get(role, 1)\n'
                 '            if rank >= 3:\n'
                 '                recipients.append((key, data.get("email", ""), data.get("full_name") or " ".join(x '
                 'for x in [data.get("first_name", "").strip(), data.get("display_name", key).strip()] if x).strip() '
                 'or key))\n'
                 '        return recipients\n'
                 '\n'
                 '    def auto_close_mail_enabled(self):\n'
                 '        try:\n'
                 '            return bool(self.app.auto_close_mail_enabled())\n'
                 '        except Exception:\n'
                 '            return True\n'
                 '\n'
                 '    def send_period_close_email_auto(self):\n'
                 '        if not self.auto_close_mail_enabled():\n'
                 '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "sent": False, "skipped": True, "reason": "Auto-Mail '
                 'deaktiviert"})\n'
                 '            return True\n'
                 '        recipients = self.e3_e4_recipients()\n'
                 '        missing = [name for key, email, name in recipients if not email]\n'
                 '        send_to = [(key, email, name) for key, email, name in recipients if email]\n'
                 '        if not send_to:\n'
                 '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "sent": False, "missing": missing, "error": "Keine '
                 'Empfängeradresse"})\n'
                 '            messagebox.showwarning("Automatische E-Mail", "Der Zeitraum wurde abgeschlossen, aber es '
                 'konnte keine Abschluss-Mail versendet werden, weil keine E3/E4-E-Mail-Adresse hinterlegt ist.")\n'
                 '            return False\n'
                 '        try:\n'
                 '            import win32com.client\n'
                 '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                 '            mail = outlook.CreateItem(0)\n'
                 '            mail.To = ";".join(email for key, email, name in send_to)\n'
                 '            mail.Subject = f"Abschluss {self.close_type_label()}: {period_label(self.period)}"\n'
                 '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                 'wurde von {self.current_user_full_name()} abgeschlossen.\\n\\n"\n'
                 '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                 '            mail.Send()\n'
                 '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _, email, _ in send_to], '
                 '"missing": missing, "sent": True})\n'
                 '            return True\n'
                 '        except Exception as exc:\n'
                 '            self.data.setdefault("close_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                 'missing})\n'
                 '            messagebox.showwarning("Automatische E-Mail", f"Der Zeitraum wurde abgeschlossen, aber '
                 'die Abschluss-Mail konnte nicht automatisch versendet werden:\\n\\n{exc}")\n'
                 '            return False\n'
                 '\n'
                 '    def send_reopen_email_auto(self, reason):\n'
                 '        recipients = self.e3_e4_recipients()\n'
                 '        missing = [name for key, email, name in recipients if not email]\n'
                 '        send_to = [(key,email,name) for key,email,name in recipients if email]\n'
                 '        if not send_to:\n'
                 '            messagebox.showerror("Wiederöffnung", "Die Pflichtbenachrichtigung konnte nicht '
                 'versendet werden, weil keine E-Mail-Adresse für E3/E4-Empfänger hinterlegt ist.")\n'
                 '            return False\n'
                 '        try:\n'
                 '            import win32com.client\n'
                 '            outlook = win32com.client.Dispatch("Outlook.Application")\n'
                 '            mail = outlook.CreateItem(0)\n'
                 '            mail.To = ";".join(email for key,email,name in send_to)\n'
                 '            mail.Subject = f"Wiederöffnung {self.close_type_label()}: {period_label(self.period)}"\n'
                 '            mail.Body = (f"Der Zeitraum {period_label(self.period)} im {self.close_type_label()} '
                 'wurde von {self.current_user_full_name()} wieder geöffnet.\\n\\n"\n'
                 '                         f"Begründung:\\n{reason}\\n\\n"\n'
                 '                         "Diese Benachrichtigung wurde automatisch durch FiBu Mate versendet.")\n'
                 '            mail.Send()\n'
                 '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "recipients": [email for _,email,_ in send_to], '
                 '"missing": missing, "sent": True})\n'
                 '            return True\n'
                 '        except Exception as exc:\n'
                 '            self.data.setdefault("reopen_email_log", []).append({"timestamp": '
                 'datetime.now().isoformat(timespec="seconds"), "error": str(exc), "sent": False, "missing": '
                 'missing})\n'
                 '            messagebox.showerror("Wiederöffnung", f"Die Pflichtbenachrichtigung konnte nicht '
                 'automatisch über Outlook versendet werden. Der Zeitraum wurde nicht geöffnet.\\n\\n{exc}")\n'
                 '            return False\n'
                 '\n'
                 '    def ask_reopen_reason(self):\n'
                 '        result = {"reason": None}\n'
                 '        win = tk.Toplevel(self.root); win.title("Zeitraum öffnen"); win.configure(bg=COLORS["bg"]); '
                 'win.geometry("560x300"); win.transient(self.root); win.grab_set()\n'
                 '        tk.Label(win, text="Begründung der Wiederöffnung", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(14,6))\n'
                 '        tk.Label(win, text="Bitte gib eine Begründung ein. Ohne Begründung kann der Zeitraum nicht '
                 'wieder geöffnet werden.", bg=COLORS["bg"], fg=COLORS["text2"], wraplength=520, '
                 'justify="left").pack(anchor="w", padx=14, pady=(0,8))\n'
                 '        txt = tk.Text(win, height=7, bg="white", fg=COLORS["text"], relief="solid", bd=1); '
                 'txt.pack(fill="both", expand=True, padx=14, pady=(0,10))\n'
                 '        def ok():\n'
                 '            val = txt.get("1.0", "end").strip()\n'
                 '            if not val:\n'
                 '                messagebox.showwarning("Zeitraum öffnen", "Bitte eine Begründung eingeben."); '
                 'return\n'
                 '            result["reason"] = val; win.destroy()\n'
                 '        footer=tk.Frame(win,bg=COLORS["bg"]); footer.pack(fill="x", padx=14, pady=(0,12))\n'
                 '        '
                 'tk.Button(footer,text="Öffnen",command=ok,bg=COLORS["blue"],fg="white",bd=0,padx=14,pady=7).pack(side="right")\n'
                 '        '
                 'tk.Button(footer,text="Abbrechen",command=win.destroy,bg=COLORS["header"],fg=COLORS["text"],bd=0,padx=14,pady=7).pack(side="right",padx=(0,8))\n'
                 '        win.wait_window(); return result["reason"]\n'
                 '\n'
                 '    def toggle_period_close(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        if not self.can_toggle_period_close():\n'
                 '            messagebox.showwarning("Berechtigung", "Für diese Aktion ist mindestens E3 '
                 'erforderlich."); return\n'
                 '        if self.data.get("closed"):\n'
                 '            reason = self.ask_reopen_reason()\n'
                 '            if not reason: return\n'
                 '            if not self.send_reopen_email_auto(reason): return\n'
                 '            self.data["closed"] = False\n'
                 '            self.data["reopened_once"] = True\n'
                 '            self.log_period_event("opened", reason=reason)\n'
                 '            self.save(); self.render_dashboard(); return\n'
                 '        if not self.is_after_cutoff():\n'
                 '            messagebox.showinfo("Zeitraum abschließen", "Abschluss erst nach Ablauf des '
                 'Abschluss-Stichtags möglich."); return\n'
                 '        stats = calc_stats(self.tasks())\n'
                 '        msg = f"{period_label(self.period)} wirklich abschließen?\\n\\nNach dem Abschluss sind keine '
                 'Änderungen mehr möglich."\n'
                 '        if stats.get("open") or stats.get("in_progress"):\n'
                 '            msg += f"\\n\\nHinweis: Es sind noch {stats.get(\'open\',0)} Aufgaben offen und '
                 '{stats.get(\'in_progress\',0)} in Bearbeitung."\n'
                 '        if not messagebox.askyesno("Zeitraum abschließen", msg): return\n'
                 '        self.data["closed"] = True\n'
                 '        self.data["closed_at"] = datetime.now().isoformat(timespec="seconds")\n'
                 '        self.data["closed_by"] = self.current_user_full_name()\n'
                 '        self.data["closed_by_key"] = getattr(self.app, "current_user_key", "")\n'
                 '        self.log_period_event("closed")\n'
                 '        self.send_period_close_email_auto()\n'
                 '        self.save(); self.render_dashboard()\n'
                 '\n'
                 '    def show_change_log(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        win=tk.Toplevel(self.root); win.title("Änderungsprotokoll"); win.configure(bg=COLORS["bg"]); '
                 'win.geometry("1050x620")\n'
                 '        txt=tk.Text(win,bg="white",fg=COLORS["text"],wrap="word",font=("Segoe UI",10)); '
                 'txt.pack(fill="both",expand=True,padx=12,pady=12)\n'
                 '        txt.insert("end", f"Änderungsprotokoll {period_label(self.period)}\\n\\n")\n'
                 '        txt.insert("end", "Abschluss-/Wiederöffnungsprotokoll:\\n")\n'
                 '        for e in self.data.get("close_events", []):\n'
                 '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | {e.get(\'action\')} | '
                 '{e.get(\'user\')} | {e.get(\'reason\',\'\')}\\n")\n'
                 '        txt.insert("end", "\\nÄnderungen:\\n")\n'
                 '        for e in self.data.get("change_log", []):\n'
                 '            flag = " [nach Wiederöffnung]" if e.get("after_reopen") else ""\n'
                 '            txt.insert("end", f"- {format_datetime_de(e.get(\'timestamp\'))} | {e.get(\'user\')} | '
                 "{e.get('action')} | {e.get('task_title')} | {e.get('field')}: {e.get('old')} -> "
                 '{e.get(\'new\')}{flag}\\n")\n'
                 '        txt.config(state="disabled")\n'
                 '\n'
                 '    def create_icon_button(self, parent, text, command, icon_key="lock", enabled=True, tooltip=""):\n'
                 '        photo = None\n'
                 '        try:\n'
                 '            photo = self.app.get_icon_photo(icon_key, 18, 18)\n'
                 '        except Exception:\n'
                 '            photo = None\n'
                 '        btn = tk.Button(parent, text=text, image=photo, compound="left" if photo else None, '
                 'command=command if enabled else None, bg=COLORS["blue"] if enabled else "#CBD5E1", fg="white" if '
                 'enabled else COLORS["text2"], bd=0, padx=10, pady=4, cursor="hand2" if enabled else "arrow", '
                 'state="normal" if enabled else "disabled")\n'
                 '        if photo: btn.image = photo\n'
                 '        if tooltip:\n'
                 '            btn.bind("<Enter>", lambda e, b=btn: self.show_tooltip(b, tooltip)); btn.bind("<Leave>", '
                 'lambda e: self.hide_tooltip())\n'
                 '        return btn\n'
                 '    def _counterpart_period_dir(self):\n'
                 '        return BASE_DIR.parent / "QuarterlyClose" / "periods"\n'
                 '    def _load_target_period_data(self, period):\n'
                 '        path = self._counterpart_period_dir() / f"{period}.json"\n'
                 '        try: data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}\n'
                 '        except Exception: data = {}\n'
                 '        data.setdefault("period", period); data.setdefault("created_at", '
                 'datetime.now().isoformat(timespec="seconds")); data.setdefault("closing_cutoff_date", '
                 'self._target_period_end(period)); data.setdefault("team_members", {team: [] for team in TEAMS}); '
                 'data.setdefault("tasks", [])\n'
                 '        return data\n'
                 '    def _save_target_period_data(self, period, data):\n'
                 '        d = self._counterpart_period_dir(); d.mkdir(parents=True, exist_ok=True); (d / '
                 'f"{period}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")\n'
                 '    def _clone_task_for_counterpart(self, task, period):\n'
                 '        cloned = json.loads(json.dumps(task, ensure_ascii=False)); cloned["id"] = '
                 'make_task_id(cloned.get("team", "Team"), int(datetime.now().strftime("%H%M%S%f")) % 1000000)\n'
                 '        cloned["status"] = STATUS_OPEN; cloned["done_at"] = None; cloned["done_by"] = None; '
                 'cloned["attachments"] = []; cloned["comments"] = []; cloned["catalog_id"] = ""; cloned["recurring"] '
                 '= bool(task.get("recurring", False)); cloned["transfer_source"] = '
                 'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; cloned["due_date"] = '
                 'self._target_period_end(period)\n'
                 '        for sub in cloned.get("subtasks", []): sub["status"] = STATUS_OPEN\n'
                 '        return cloned\n'
                 '    def transfer_task_to_counterpart(self, task, target_period, all_following=False):\n'
                 '        periods = self._target_periods_from(target_period, all_following); source_key = '
                 'f"{BASE_DIR.name}:{self.period}:{task.get(\'id\',\'\')}"; count = 0\n'
                 '        for period in periods:\n'
                 '            data = self._load_target_period_data(period); tasks = data.setdefault("tasks", []); '
                 'existing = next((t for t in tasks if t.get("transfer_source") == source_key and not '
                 't.get("deleted")), None); cloned = self._clone_task_for_counterpart(task, period)\n'
                 '            if existing:\n'
                 '                keep = {"status": existing.get("status", STATUS_OPEN), "done_at": '
                 'existing.get("done_at"), "done_by": existing.get("done_by"), "attachments": '
                 'existing.get("attachments", []), "comments": existing.get("comments", [])}; existing.clear(); '
                 'existing.update(cloned); existing.update(keep)\n'
                 '            else: tasks.append(cloned)\n'
                 '            self._save_target_period_data(period, data); count += 1\n'
                 '        messagebox.showinfo("Jahresabschluss", f"Aufgabe wurde in {count} Quartalsabschluss(e) '
                 'übernommen.")\n'
                 '    def open_transfer_dialog(self, task):\n'
                 '            if not self.require_unlocked("Aufgabenübernahme ist nicht möglich"): return\n'
                 '            win = tk.Toplevel(self.root); win.title("In Quartalsabschluss übernehmen"); '
                 'win.configure(bg=COLORS["bg"]); win.transient(self.root); win.grab_set(); win.geometry("540x250")\n'
                 '            default_period = self._target_period_from_current(); mode_var = '
                 'tk.StringVar(value="all")\n'
                 '            tk.Label(win, text="Aufgabe inklusive Unteraufgaben übernehmen", bg=COLORS["bg"], '
                 'fg=COLORS["text"], font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=16, pady=(16, 10))\n'
                 '            tk.Radiobutton(win, text=f"In alle Quartalsabschlusse ab '
                 '{self._target_display(default_period)}", variable=mode_var, value="all", bg=COLORS["bg"], '
                 'activebackground=COLORS["bg"]).pack(anchor="w", padx=18, pady=4)\n'
                 '            tk.Radiobutton(win, text=f"In Quartalsabschluss {self._target_display(default_period)}", '
                 'variable=mode_var, value="single", bg=COLORS["bg"], activebackground=COLORS["bg"]).pack(anchor="w", '
                 'padx=18, pady=4)\n'
                 '            period_var = tk.StringVar(value=default_period); options = '
                 'self._target_periods_from(default_period, True)\n'
                 '            menu = tk.OptionMenu(win, period_var, *options); menu.config(bg="white", '
                 'fg=COLORS["text"], bd=1, highlightthickness=0); menu.pack(anchor="w", padx=18, pady=(10, 0))\n'
                 '            btns = tk.Frame(win, bg=COLORS["bg"]); btns.pack(side="bottom", fill="x", padx=16, '
                 'pady=14)\n'
                 '            tk.Button(btns, text="Übernehmen", command=lambda: '
                 '(self.transfer_task_to_counterpart(task, period_var.get(), mode_var.get()=="all"), win.destroy()), '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                 '            tk.Button(btns, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                 'fg=COLORS["text"], bd=0, padx=14, pady=8).pack(side="right", padx=6)\n'
                 '    def propagate_team_members_to_related_periods(self):\n'
                 '        members = normalize_team_members(self.data)\n'
                 '        for period in list_periods():\n'
                 '            if period >= self.period:\n'
                 '                data = load_period(period); data["team_members"] = json.loads(json.dumps(members, '
                 'ensure_ascii=False)); save_period(period, data)\n'
                 '        for period in self._target_periods_from(self._target_period_from_current(), True):\n'
                 '            data = self._load_target_period_data(period); data["team_members"] = '
                 'json.loads(json.dumps(members, ensure_ascii=False)); self._save_target_period_data(period, data)\n'
                 '\n'
                 '    def clear_frame(self):\n'
                 '        if hasattr(self.app, "active_scroll_canvas"):\n'
                 '            self.app.active_scroll_canvas = None\n'
                 '        for child in self.frame.winfo_children():\n'
                 '            child.destroy()\n'
                 '\n'
                 '    def reload(self):\n'
                 '        self.data = apply_catalog_to_period(self.period)\n'
                 '\n'
                 '    def save(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        self.strip_task_ids_from_data(self.data)\n'
                 '        save_period(self.period, self.data)\n'
                 '        self._live_period_mtime = self._period_file_mtime()\n'
                 '\n'
                 '    def tasks(self):\n'
                 '        return [t for t in self.data.get("tasks", []) if not t.get("deleted")]\n'
                 '\n'
                 '    def team_tasks(self, team):\n'
                 '        return sorted(\n'
                 '            [t for t in self.tasks() if t.get("team") == team],\n'
                 '            key=lambda t: str(t.get("title", "")).casefold(),\n'
                 '        )\n'
                 '\n'
                 '    def task_sort_key(self, task):\n'
                 '        return str(task.get("title", "")).casefold()\n'
                 '\n'
                 '    def is_task_id_editor(self):\n'
                 '        role = self.app.my_role() if hasattr(self.app, "my_role") else "Standard"\n'
                 '        return role in ("Administrator", "System-Administrator", "Wagnerm")\n'
                 '\n'
                 '    def normalize_task_uid_value(self, value):\n'
                 '        # v0.436: Aufgaben-ID-Zuweisung wurde vollständig entfernt.\n'
                 '        return ""\n'
                 '\n'
                 '    def task_uid_display(self, task):\n'
                 '        # v0.436: Es wird keine Aufgaben-ID mehr angezeigt.\n'
                 '        return ""\n'
                 '\n'
                 '    def initial_uid_for_task(self, task):\n'
                 '        return INITIAL_TASK_IDS.get((normalize_team_name(task.get("team")), str(task.get("title") or '
                 '"")), "")\n'
                 '\n'
                 '    def all_period_files(self):\n'
                 '        ensure_storage()\n'
                 '        return sorted(PERIOD_DIR.glob("*.json"))\n'
                 '\n'
                 '    def collect_used_task_uids(self, exclude_task=None):\n'
                 '        # v0.436: Keine Aufgaben-ID-Verwaltung mehr.\n'
                 '        return set()\n'
                 '\n'
                 '    def next_free_task_uid(self):\n'
                 '        # v0.436: Keine Aufgaben-ID-Zuweisung mehr.\n'
                 '        return ""\n'
                 '\n'
                 '    def task_identity_key_for_initial_id(self, task):\n'
                 '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                 '        if catalog_id:\n'
                 '            return ("catalog", catalog_id)\n'
                 '        initial = self.initial_uid_for_task(task)\n'
                 '        if initial:\n'
                 '            return ("initial", initial)\n'
                 '        return ("local", normalize_team_name(task.get("team")), str(task.get("title") or '
                 '"").strip().casefold())\n'
                 '\n'
                 '    def strip_task_ids_from_data(self, data):\n'
                 '        """Entfernt alte Aufgaben-ID-Felder aus geladenen/gespeicherten Daten, ohne andere Inhalte '
                 'zu verändern."""\n'
                 '        changed = False\n'
                 '        try:\n'
                 '            for task in data.get("tasks", []) or []:\n'
                 '                if "task_uid" in task:\n'
                 '                    task.pop("task_uid", None); changed = True\n'
                 '                for sub in task.get("subtasks", []) or []:\n'
                 '                    if "task_uid" in sub:\n'
                 '                        sub.pop("task_uid", None); changed = True\n'
                 '        except Exception:\n'
                 '            pass\n'
                 '        return changed\n'
                 '\n'
                 '    def strip_task_ids_all_periods(self):\n'
                 '        ensure_storage()\n'
                 '        for path in self.all_period_files():\n'
                 '            try:\n'
                 '                data = json.loads(path.read_text(encoding="utf-8"))\n'
                 '            except Exception:\n'
                 '                continue\n'
                 '            if self.strip_task_ids_from_data(data):\n'
                 '                try:\n'
                 '                    save_period(path.stem, data)\n'
                 '                    if path.stem == self.period:\n'
                 '                        self.data = data\n'
                 '                except Exception:\n'
                 '                    pass\n'
                 '\n'
                 '    def ensure_task_ids(self):\n'
                 '        # v0.436: Kompatibilitätsmethode; weist keine IDs mehr zu, sondern entfernt alte ID-Felder.\n'
                 '        self.strip_task_ids_all_periods()\n'
                 '\n'
                 '    def archive_task_uid_change(self, task, old_uid, new_uid):\n'
                 '        # v0.436: ID-Historie deaktiviert.\n'
                 '        return False\n'
                 '\n'
                 '    def task_match_key(self, task):\n'
                 '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                 '        if catalog_id:\n'
                 '            return ("catalog", catalog_id)\n'
                 '        return ("task", str(task.get("id") or "").strip(), normalize_team_name(task.get("team")), '
                 'str(task.get("title") or "").strip().casefold())\n'
                 '\n'
                 '    def get_expand_key(self, task):\n'
                 '        return f"{task.get(\'id\',\'\')}|{task.get(\'team\',\'\')}|{task.get(\'title\',\'\')}"\n'
                 '\n'
                 '    def ask_delegate_scope(self, item, parent_task=None):\n'
                 '        if parent_task is not None:\n'
                 '            return "current"\n'
                 '        result = {"scope": None}\n'
                 '        win = tk.Toplevel(self.root)\n'
                 '        win.title("Zuständigkeit ändern")\n'
                 '        win.configure(bg=COLORS["bg"])\n'
                 '        win.transient(self.root); win.grab_set(); win.geometry("500x205")\n'
                 '        tk.Label(win, text="Zuständigkeit ändern", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe '
                 'UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                 '        tk.Label(win, text="Soll die Zuständigkeit nur für diesen Zeitraum oder permanent für alle '
                 'Folgezeiträume geändert werden?", bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10), '
                 'wraplength=455, justify="left").pack(anchor="w", padx=16, pady=(0, 12))\n'
                 '        frame = tk.Frame(win, bg=COLORS["bg"]); frame.pack(fill="x", padx=16)\n'
                 '        def choose(scope): result["scope"] = scope; win.destroy()\n'
                 '        tk.Button(frame, text="Nur dieser Zeitraum", command=lambda: choose("current"), '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))\n'
                 '        tk.Button(frame, text="Permanent für Folgezeiträume", command=lambda: choose("permanent"), '
                 'bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0,6))\n'
                 '        tk.Button(frame, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                 'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                 '        win.wait_window()\n'
                 '        return result["scope"]\n'
                 '\n'
                 '    def apply_delegate_to_following_periods(self, task_key, owner_name, owner_user_key):\n'
                 '        changed_periods = 0\n'
                 '        for period in self.following_periods():\n'
                 '            data = load_period(period)\n'
                 '            changed = False\n'
                 '            for task in data.get("tasks", []):\n'
                 '                if self.task_match_key(task) == task_key:\n'
                 '                    task["owner"] = owner_name\n'
                 '                    task["owner_user_key"] = owner_user_key\n'
                 '                    for sub in task.get("subtasks", []):\n'
                 '                        sub["owner"] = owner_name\n'
                 '                        sub["owner_user_key"] = owner_user_key\n'
                 '                    changed = True\n'
                 '            if changed:\n'
                 '                self.strip_task_ids_from_data(data)\n'
                 '                save_period(period, data)\n'
                 '                changed_periods += 1\n'
                 '        return changed_periods\n'
                 '\n'
                 '    def close_type_label(self):\n'
                 '        scope = globals().get("CLOSING_SCOPE", "")\n'
                 '        return "Monatsabschluss" if scope == "M" else "Quartalsabschluss" if scope == "Q" else '
                 '"Jahresabschluss" if scope == "J" else "Abschluss"\n'
                 '\n'
                 '    def recipient_email_for_user(self, user_key):\n'
                 '        if not user_key:\n'
                 '            return ""\n'
                 '        try:\n'
                 '            return self.app.user_data.get("users", {}).get(user_key, {}).get("email", "")\n'
                 '        except Exception:\n'
                 '            return ""\n'
                 '\n'
                 '    def send_delegation_email(self, user_key, recipient_name, task_title, scope):\n'
                 '        email = self.recipient_email_for_user(user_key)\n'
                 '        if not email:\n'
                 '            messagebox.showwarning("Delegierung", f"Für {recipient_name} ist keine E-Mail-Adresse in '
                 'der Benutzerverwaltung hinterlegt. Die Delegierung wurde gespeichert, aber es konnte keine E-Mail '
                 'vorbereitet werden.")\n'
                 '            return\n'
                 '        delegated_by = getattr(self.app, "current_user_display", "") or getattr(self.app, '
                 '"current_user_key", "") or "FiBu Mate"\n'
                 '        period_text = period_label(self.period)\n'
                 '        close_type = self.close_type_label()\n'
                 '        if scope == "permanent":\n'
                 '            scope_text = "bis auf Weiteres"\n'
                 '        else:\n'
                 '            scope_text = f"für den Zeitraum {period_text}"\n'
                 '        subject = f"Delegierung {close_type}: {task_title}"\n'
                 '        body = (\n'
                 '            f"Hallo {recipient_name},\\n\\n"\n'
                 '            f"die Zuständigkeit der {close_type}-Aufgabe {task_title} wurde an dich von '
                 '{delegated_by} {scope_text} delegiert.\\n\\n"\n'
                 '            "Bitte bestätige die Kenntnisnahme per Antwort.\\n\\n"\n'
                 '            "Vielen Dank :)"\n'
                 '        )\n'
                 '        try:\n'
                 '            webbrowser.open("mailto:" + quote(email) + "?subject=" + quote(subject) + "&body=" + '
                 'quote(body))\n'
                 '        except Exception as exc:\n'
                 '            messagebox.showerror("Delegierung", f"Die E-Mail zur Delegierung konnte nicht '
                 'vorbereitet werden:\\n\\n{exc}")\n'
                 '\n'
                 '    def sync_current_as_template_to_following_periods(self):\n'
                 '        if not self.can_edit(): return\n'
                 '        following = self.following_periods()\n'
                 '        if not following:\n'
                 '            messagebox.showinfo("Vorlage verwenden", "Es sind keine Folgezeiträume vorhanden.")\n'
                 '            return\n'
                 '        msg = f"{period_label(self.period)} als Vorlage für alle Folgezeiträume '
                 'verwenden?\\n\\nAufgabenstruktur, Zuständigkeiten, Fälligkeiten und Unteraufgaben werden anhand von '
                 'Katalog-/Aufgabenschlüsseln übertragen. Status, Kommentare und Anlagen bleiben bei bereits '
                 'vorhandenen Aufgaben erhalten."\n'
                 '        if not messagebox.askyesno("Zeitraum als Vorlage verwenden", msg):\n'
                 '            return\n'
                 '        source = [json.loads(json.dumps(t, ensure_ascii=False)) for t in self.tasks()]\n'
                 '        updated = 0\n'
                 '        for period in following:\n'
                 '            data = load_period(period)\n'
                 '            old_by_key = {self.task_match_key(t): t for t in data.get("tasks", [])}\n'
                 '            new_tasks = []\n'
                 '            for src in source:\n'
                 '                key = self.task_match_key(src)\n'
                 '                old = old_by_key.get(key)\n'
                 '                new_task = json.loads(json.dumps(src, ensure_ascii=False))\n'
                 '                if old:\n'
                 '                    for keep in ("status", "attachments", "comments", "done_at", "done_by", '
                 '"documentation"):\n'
                 '                        if keep in old:\n'
                 '                            new_task[keep] = old.get(keep)\n'
                 '                    old_subs = {str(s.get("title", "")).strip().casefold(): s for s in '
                 'old.get("subtasks", [])}\n'
                 '                    for sub in new_task.get("subtasks", []):\n'
                 '                        old_sub = old_subs.get(str(sub.get("title", "")).strip().casefold())\n'
                 '                        if old_sub:\n'
                 '                            for keep in ("status", "attachments", "comments", "done_at", "done_by", '
                 '"documentation", "owner", "owner_user_key"):\n'
                 '                                if keep in old_sub:\n'
                 '                                    sub[keep] = old_sub.get(keep)\n'
                 '                new_tasks.append(new_task)\n'
                 '            data["tasks"] = new_tasks\n'
                 '            self.strip_task_ids_from_data(data)\n'
                 '            save_period(period, data)\n'
                 '            updated += 1\n'
                 '        messagebox.showinfo("Vorlage verwenden", f"Vorlage wurde auf {updated} Folgezeiträume '
                 'übertragen.")\n'
                 '\n'
                 '    def _pdf_escape(self, text):\n'
                 '        return str(text).replace("\\\\", "\\\\\\\\").replace("(", "\\\\(").replace(")", "\\\\)")\n'
                 '\n'
                 '    def write_simple_pdf(self, path, title, rows):\n'
                 '        lines = [title, ""]\n'
                 '        for row in rows:\n'
                 '            lines.append(" | ".join(str(v) for v in row))\n'
                 '        pages = []\n'
                 '        for start in range(0, len(lines), 42):\n'
                 '            chunk = lines[start:start+42]\n'
                 '            ops = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]\n'
                 '            for line in chunk:\n'
                 '                ops.append(f"({self._pdf_escape(line[:150])}) Tj")\n'
                 '                ops.append("T*")\n'
                 '            ops.append("ET")\n'
                 '            pages.append("\\n".join(ops).encode("latin-1", "replace"))\n'
                 '        objects = []\n'
                 '        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")\n'
                 '        kids = " ".join(f"{3+i*2} 0 R" for i in range(len(pages)))\n'
                 '        objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())\n'
                 '        for i, content in enumerate(pages):\n'
                 '            content_obj = 4 + i*2\n'
                 '            objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << '
                 '/Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_obj} 0 '
                 'R >>".encode())\n'
                 '            objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\\nstream\\n" + '
                 'content + b"\\nendstream")\n'
                 '        pdf = bytearray(b"%PDF-1.4\\n")\n'
                 '        offsets = []\n'
                 '        for idx, obj in enumerate(objects, 1):\n'
                 '            offsets.append(len(pdf))\n'
                 '            pdf.extend(f"{idx} 0 obj\\n".encode()); pdf.extend(obj); pdf.extend(b"\\nendobj\\n")\n'
                 '        xref = len(pdf)\n'
                 '        pdf.extend(f"xref\\n0 {len(objects)+1}\\n0000000000 65535 f \\n".encode())\n'
                 '        for off in offsets:\n'
                 '            pdf.extend(f"{off:010d} 00000 n \\n".encode())\n'
                 '        pdf.extend(f"trailer\\n<< /Size {len(objects)+1} /Root 1 0 R '
                 '>>\\nstartxref\\n{xref}\\n%%EOF".encode())\n'
                 '        Path(path).write_bytes(bytes(pdf))\n'
                 '\n'
                 '    def create_simple_pdf(self, title, rows):\n'
                 '        path = filedialog.asksaveasfilename(title="PDF speichern", defaultextension=".pdf", '
                 'filetypes=[("PDF-Dateien", "*.pdf")], initialfile=title.replace(" ", "_").replace("/", "-") + '
                 '".pdf")\n'
                 '        if not path: return\n'
                 '        try:\n'
                 '            self.write_simple_pdf(path, title, rows)\n'
                 '            if messagebox.askyesno("PDF erstellt", "PDF wurde erstellt. Jetzt öffnen?"):\n'
                 '                try:\n'
                 '                    os.startfile(path)\n'
                 '                except Exception:\n'
                 '                    try: subprocess.Popen(["xdg-open", path])\n'
                 '                    except Exception: pass\n'
                 '        except Exception as exc:\n'
                 '            messagebox.showerror("PDF erstellen", f"PDF konnte nicht erstellt werden:\\n\\n{exc}")\n'
                 '\n'
                 '    def create_close_report(self):\n'
                 '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                 '        if is_preliminary_report and self.role_rank_value() < 4:\n'
                 '            messagebox.showwarning("Keine Berechtigung", "Der vorläufige Abschlussbericht ist nur '
                 'für E4 exportierbar.")\n'
                 '            return\n'
                 '        if (not is_preliminary_report) and self.role_rank_value() < 3:\n'
                 '            messagebox.showwarning("Keine Berechtigung", "Der Protokoll-Bericht für ganze Zeiträume '
                 'ist nur für E3 und E4 exportierbar.")\n'
                 '            return\n'
                 '        self.ensure_close_metadata()\n'
                 '        with_signature = messagebox.askyesno("Abschlussbericht", f"Bericht '
                 '{period_label(self.period)} mit Signatur- und Freigabefeld erstellen?\\n\\nJa = mit '
                 'Signatur-/Freigabefeld\\nNein = ohne Signatur-/Freigabefeld")\n'
                 '        default_name = '
                 'f"Abschlussbericht_{self.close_type_label()}_{period_label(self.period).replace(\' \', '
                 '\'_\').replace(\'/\', \'-\')}_{date.today().isoformat()}.pdf"\n'
                 '        path = filedialog.asksaveasfilename(title="Bericht-PDF speichern", defaultextension=".pdf", '
                 'filetypes=[("PDF-Dateien", "*.pdf")], initialfile=default_name)\n'
                 '        if not path: return\n'
                 '        try:\n'
                 '            self.create_reportlab_pdf(path, with_signature)\n'
                 '        except Exception as exc:\n'
                 '            try:\n'
                 '                rows = self.build_report_rows()\n'
                 '                self.write_simple_pdf(path, f"Abschlussbericht {self.close_type_label()} '
                 '{period_label(self.period)}", rows)\n'
                 '            except Exception as fallback_exc:\n'
                 '                messagebox.showerror("Abschlussbericht", f"Bericht konnte nicht erstellt '
                 'werden:\\n\\n{exc}\\n\\nFallback fehlgeschlagen:\\n{fallback_exc}")\n'
                 '                return\n'
                 '        if messagebox.askyesno("Bericht-PDF wurde erstellt", "Bericht-PDF wurde erstellt. Jetzt '
                 'öffnen?"):\n'
                 '            try: os.startfile(path)\n'
                 '            except Exception:\n'
                 '                try: subprocess.Popen(["xdg-open", path])\n'
                 '                except Exception: pass\n'
                 '\n'
                 '    def build_report_rows(self):\n'
                 '        rows = []\n'
                 '        for task in self.tasks():\n'
                 '            rows.append([f"{task.get(\'title\',\'\')} | {task.get(\'owner\',\'\')} | '
                 '{due_rule_text(task)} {format_date_de(task.get(\'due_date\'))} | {task.get(\'status\',\'\')}"])\n'
                 '            for sub in task.get("subtasks", []) or []:\n'
                 '                if not sub.get("deleted"):\n'
                 '                    rows.append([f"  - {sub.get(\'title\',\'\')} | {sub.get(\'owner\', '
                 'task.get(\'owner\',\'\'))} | {sub.get(\'status\',\'\')}"])\n'
                 '        return rows\n'
                 '\n'
                 '    def create_reportlab_pdf(self, path, with_signature=False):\n'
                 '        from reportlab.lib import colors\n'
                 '        from reportlab.lib.pagesizes import A4\n'
                 '        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle\n'
                 '        from reportlab.lib.units import cm\n'
                 '        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, '
                 'PageBreak\n'
                 '        doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=1.4*cm, leftMargin=1.4*cm, '
                 'topMargin=1.2*cm, bottomMargin=1.2*cm)\n'
                 '        styles = getSampleStyleSheet()\n'
                 '        dark_blue = colors.HexColor("#1F4E79")\n'
                 '        styles.add(ParagraphStyle(name="FMTitle", parent=styles["Title"], fontName="Helvetica-Bold", '
                 'fontSize=16, textColor=dark_blue, spaceAfter=10))\n'
                 '        styles.add(ParagraphStyle(name="FMHead", parent=styles["Heading2"], '
                 'fontName="Helvetica-Bold", fontSize=13, textColor=dark_blue, spaceBefore=10, spaceAfter=6))\n'
                 '        styles.add(ParagraphStyle(name="FMText", parent=styles["BodyText"], fontName="Helvetica", '
                 'fontSize=11, leading=14))\n'
                 '        styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", '
                 'fontSize=8, leading=10))\n'
                 '        story=[]\n'
                 '        story.append(Paragraph(f"Abschlussbericht {self.close_type_label()} '
                 '{period_label(self.period)}", styles["FMTitle"]))\n'
                 '        status = "Abgeschlossen" if self.data.get("closed") else "Nicht abgeschlossen"\n'
                 '        head = [["Berichtstyp", self.close_type_label()], ["Zeitraum", period_label(self.period)], '
                 '["Abschluss-Stichtag", format_date_de(self.data.get("closing_cutoff_date"))], ["Status", status], '
                 '["Erstellt durch", self.current_user_full_name()], ["Erstellt am", datetime.now().strftime("%d.%m.%Y '
                 '%H:%M")]]\n'
                 '        if self.data.get("closed_at"): head.append(["Zuletzt abgeschlossen", '
                 'f"{format_datetime_de(self.data.get(\'closed_at\'))} durch {self.data.get(\'closed_by\',\'\')}"])\n'
                 '        t=Table(head, colWidths=[5*cm, 11*cm]); '
                 't.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.HexColor("#D9EAF7")),("VALIGN",(0,0),(-1,-1),"TOP")]))\n'
                 '        story += [t, Spacer(1,8)]\n'
                 '        stats=calc_stats(self.tasks())\n'
                 '        story.append(Paragraph("Management Summary", styles["FMHead"]))\n'
                 '        story.append(Paragraph(f"Gesamtaufgaben: {stats[\'total\']} | Erledigt: {stats[\'done\']} | '
                 "Offen: {stats['open']} | In Bearbeitung: {stats['in_progress']} | Überfällig: {stats['overdue']} | "
                 'Kritisch: {stats[\'critical\']}", styles["FMText"]))\n'
                 '        story.append(Paragraph("Abschlussprotokoll", styles["FMHead"]))\n'
                 '        '
                 'events=[["Zeitpunkt","Aktion","Benutzer","Begründung"]]+[[format_datetime_de(e.get("timestamp")), '
                 'e.get("action",""), e.get("user",""), e.get("reason","")] for e in self.data.get("close_events", '
                 '[])]\n'
                 '        story.append(Table(events, repeatRows=1, colWidths=[3.2*cm,2.5*cm,4*cm,6.3*cm], '
                 'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                 '        story.append(Paragraph("Teamübersicht", styles["FMHead"]))\n'
                 '        team_rows=[["Team","Gesamt","Erledigt","Offen","In Bearbeitung","Unteraufgaben"]]\n'
                 '        for team in TEAMS:\n'
                 '            tasks=[t for t in self.tasks() if t.get("team")==team and not t.get("deleted")]\n'
                 '            subs_done=sum(sum(1 for s in t.get("subtasks",[]) if s.get("status")==STATUS_DONE and '
                 'not s.get("deleted")) for t in tasks)\n'
                 '            subs_all=sum(sum(1 for s in t.get("subtasks",[]) if not s.get("deleted")) for t in '
                 'tasks)\n'
                 '            team_rows.append([team,len(tasks),sum(1 for t in tasks if '
                 't.get("status")==STATUS_DONE),sum(1 for t in tasks if t.get("status")==STATUS_OPEN),sum(1 for t in '
                 'tasks if t.get("status")==STATUS_IN_PROGRESS),f"{subs_done}/{subs_all}" if subs_all else ""])\n'
                 '        story.append(Table(team_rows, repeatRows=1, '
                 'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9EAF7")),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                 '        story.append(Paragraph("Aufgaben und Aufgabengruppen", styles["FMHead"]))\n'
                 '        for i,task in enumerate(self.tasks(),1):\n'
                 '            is_group=bool([s for s in task.get("subtasks",[]) if not s.get("deleted")])\n'
                 '            label="Aufgabengruppe" if is_group else "Aufgabe"\n'
                 '            critical = task.get("deadline_type")=="gesetzlich" or task.get("priority")=="kritisch"\n'
                 '            story.append(Paragraph(f"{i}. {label}: {task.get(\'title\',\'\')}", styles["FMHead" if '
                 'critical else "FMText"]))\n'
                 '            story.append(Paragraph(f"Zuständigkeit: {task.get(\'owner\',\'\')} | Fälligkeit: '
                 "{format_date_de(task.get('due_date'))} ({due_rule_text(task)}) | Status: {task.get('status','')} | "
                 'Erledigt: {format_datetime_de(task.get(\'done_at\'))}", styles["FMText"]))\n'
                 "            if 'z4' in task.get('title','').casefold() or 'zm-' in task.get('title','').casefold() "
                 "or 'zm meldung' in task.get('title','').casefold() or 'z5a' in task.get('title','').casefold():\n"
                 '                txt = f"<b><i>{task.get(\'title\',\'\')} erfolgt am '
                 '{format_datetime_de(task.get(\'done_at\'))}.</i></b>" if task.get(\'status\')==STATUS_DONE else '
                 'f"<b><i>{task.get(\'title\',\'\')} wurde im Zeitraum nicht als erledigt markiert.</i></b>"\n'
                 '                story.append(Paragraph(txt, styles["FMText"]))\n'
                 '            comments=task.get("comments",[])\n'
                 '            if comments:\n'
                 '                story.append(Paragraph("Kommentare / Notizen", styles["FMText"]))\n'
                 '                for c in comments:\n'
                 '                    story.append(Paragraph(str(c), styles["Small"]))\n'
                 '            attachments=task.get("attachments",[])\n'
                 '            if attachments:\n'
                 '                rows=[["Anlagenname","Anlagenpfad"]]\n'
                 '                for a in attachments:\n'
                 '                    if isinstance(a,dict): rows.append([a.get("name") or '
                 'Path(a.get("path","")).name, a.get("path","") + (f" [{a.get(\'created_at\',\'\')}]" if '
                 'a.get(\'created_at\') else "")])\n'
                 '                    else: rows.append([Path(str(a)).name, str(a)])\n'
                 '                story.append(Paragraph(f"Anlagen: {len(attachments)}", styles["FMText"])); '
                 'story.append(Table(rows, '
                 'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),8)])))\n'
                 '            for j,sub in enumerate([s for s in task.get("subtasks",[]) if not s.get("deleted")],1):\n'
                 '                story.append(Paragraph(f"{i}.{j} Aufgabe: {sub.get(\'title\',\'\')}", '
                 'styles["FMText"]))\n'
                 '                story.append(Paragraph(f"Zuständigkeit: '
                 '{sub.get(\'owner\',task.get(\'owner\',\'\'))} | Status: {sub.get(\'status\',\'\')}", '
                 'styles["Small"]))\n'
                 '        open_tasks=[t for t in self.tasks() if t.get("status")!=STATUS_DONE and not '
                 't.get("deleted")]\n'
                 '        story.append(Paragraph("Offene Punkte", styles["FMHead"]))\n'
                 '        if open_tasks:\n'
                 '            for tsk in open_tasks: story.append(Paragraph(f"- {tsk.get(\'title\',\'\')}, zuständig: '
                 '{tsk.get(\'owner\',\'\')}, Status: {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                 '        else: story.append(Paragraph("Keine offenen Punkte.", styles["FMText"]))\n'
                 '        critical_tasks=[t for t in self.tasks() if (t.get("deadline_type")=="gesetzlich" or '
                 't.get("priority")=="kritisch" or warning_level(t) in ("overdue","today","orange")) and not '
                 't.get("deleted")]\n'
                 '        story.append(Paragraph("Kritische oder gesetzliche Fristen", styles["FMHead"]))\n'
                 '        for tsk in critical_tasks: story.append(Paragraph(f"- <b>{tsk.get(\'title\',\'\')}</b> | '
                 '{format_date_de(tsk.get(\'due_date\'))} | {tsk.get(\'status\',\'\')}", styles["FMText"]))\n'
                 '        changes=[c for c in self.data.get("change_log",[]) if c.get("after_reopen")]\n'
                 '        story.append(Paragraph("Nachträgliche Änderungen nach Wiederöffnung", styles["FMHead"]))\n'
                 '        if changes:\n'
                 '            '
                 'rows=[["Zeitpunkt","Benutzer","Aufgabe","Feld","Alt","Neu"]]+[[format_datetime_de(c.get("timestamp")),c.get("user",""),c.get("task_title",""),c.get("field",""),c.get("old",""),c.get("new","")] '
                 'for c in changes]\n'
                 '            story.append(Table(rows, repeatRows=1, '
                 'colWidths=[2.7*cm,3*cm,3.5*cm,2.3*cm,2.2*cm,2.2*cm], '
                 'style=TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#FDE68A")),("FONTSIZE",(0,0),(-1,-1),7)])))\n'
                 '        else: story.append(Paragraph("Keine nachträglichen Änderungen dokumentiert.", '
                 'styles["FMText"]))\n'
                 '        if with_signature:\n'
                 '            story += [Spacer(1,18), Paragraph("Signatur- und Freigabefeld", styles["FMHead"]), '
                 'Spacer(1,16), Paragraph("Erstellt durch: _______________________ Datum: ___________", '
                 'styles["FMText"]), Spacer(1,14), Paragraph("Geprüft durch: ________________________ Datum: '
                 '___________", styles["FMText"]), Spacer(1,14), Paragraph("Freigegeben durch: ____________________ '
                 'Datum: ___________", styles["FMText"])]\n'
                 '        version = getattr(self.app, "version_label_text", lambda: "")()\n'
                 '        footer = f"Bericht automatisch erstellt von {self.current_user_full_name()} am '
                 '{datetime.now().strftime(\'%d.%m.%Y %H:%M\')} mit FiBu Mate {version}."\n'
                 '        story.append(Spacer(1,10)); story.append(Paragraph(footer, styles["Small"]))\n'
                 '        doc.build(story)\n'
                 '\n'
                 '    def create_task_id_report(self, task):\n'
                 '        # v0.436: Einzelaufgaben-PDFs sind deaktiviert. Exportiert werden nur ganze Zeiträume als '
                 'Protokoll-Bericht.\n'
                 '        messagebox.showinfo("Protokoll-Bericht", "Einzelaufgaben-Berichte sind deaktiviert. Bitte '
                 'den Protokoll-Bericht für den gesamten Zeitraum exportieren.")\n'
                 '        return\n'
                 '\n'
                 '    def task_match_key(self, task):\n'
                 '        catalog_id = str(task.get("catalog_id") or "").strip()\n'
                 '        if catalog_id:\n'
                 '            return ("catalog", catalog_id)\n'
                 '        return (\n'
                 '            "task",\n'
                 '            str(task.get("id") or "").strip(),\n'
                 '            normalize_team_name(task.get("team")),\n'
                 '            str(task.get("title") or "").strip().casefold(),\n'
                 '        )\n'
                 '\n'
                 '    def find_task_index_exact(self, task):\n'
                 '        tasks = self.data.get("tasks", [])\n'
                 '        for idx, candidate in enumerate(tasks):\n'
                 '            if candidate is task:\n'
                 '                return idx\n'
                 '        key = self.task_match_key(task)\n'
                 '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                 'self.task_match_key(candidate) == key]\n'
                 '        return matches[0] if len(matches) == 1 else None\n'
                 '\n'
                 '    def following_periods(self):\n'
                 '        return [period for period in list_periods() if period > self.period]\n'
                 '\n'
                 '    def remove_task_from_data_by_key(self, data, key):\n'
                 '        tasks = data.get("tasks", [])\n'
                 '        matches = [idx for idx, candidate in enumerate(tasks) if not candidate.get("deleted") and '
                 'self.task_match_key(candidate) == key]\n'
                 '        if len(matches) == 1:\n'
                 '            tasks.pop(matches[0])\n'
                 '            data["tasks"] = tasks\n'
                 '            return "removed"\n'
                 '        if len(matches) > 1:\n'
                 '            return "ambiguous"\n'
                 '        return "missing"\n'
                 '\n'
                 '    def ask_delete_scope(self, task):\n'
                 '        result = {"scope": None}\n'
                 '        win = tk.Toplevel(self.root)\n'
                 '        win.title("Aufgabe löschen")\n'
                 '        win.configure(bg=COLORS["bg"])\n'
                 '        win.transient(self.root)\n'
                 '        win.grab_set()\n'
                 '        win.geometry("520x245")\n'
                 '        tk.Label(win, text="Aufgabe löschen", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", '
                 '14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                 '        msg = f"Welche Zeiträume sollen bereinigt werden?\\n\\n{task.get(\'title\', \'\')}"\n'
                 '        if task.get("attachments"):\n'
                 '            msg += "\\n\\nHinweis: Anlagen-Dateien bleiben im Anlagenordner erhalten; nur die '
                 'Referenz in der Aufgabe wird entfernt."\n'
                 '        tk.Label(win, text=msg, bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 10), '
                 'justify="left", wraplength=480).pack(anchor="w", padx=16, pady=(0, 14))\n'
                 '        buttons = tk.Frame(win, bg=COLORS["bg"])\n'
                 '        buttons.pack(fill="x", padx=16, pady=(0, 16))\n'
                 '        def choose(scope):\n'
                 '            result["scope"] = scope\n'
                 '            win.destroy()\n'
                 '        tk.Button(buttons, text="Nur aktueller Zeitraum", command=lambda: choose("current"), '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x", pady=(0, 7))\n'
                 '        tk.Button(buttons, text="Aktueller und alle folgenden Zeiträume", command=lambda: '
                 'choose("following"), bg=COLORS["orange"], fg="white", bd=0, padx=12, pady=7, '
                 'cursor="hand2").pack(fill="x", pady=(0, 7))\n'
                 '        tk.Button(buttons, text="Abbrechen", command=lambda: choose(None), bg=COLORS["header"], '
                 'fg=COLORS["text"], bd=0, padx=12, pady=7, cursor="hand2").pack(fill="x")\n'
                 '        win.wait_window()\n'
                 '        return result["scope"]\n'
                 '\n'
                 '    def delete_from_following_periods(self, task_key):\n'
                 '        removed = 0\n'
                 '        ambiguous = 0\n'
                 '        for period in self.following_periods():\n'
                 '            data = load_period(period)\n'
                 '            result = self.remove_task_from_data_by_key(data, task_key)\n'
                 '            if result == "removed":\n'
                 '                save_period(period, data)\n'
                 '                removed += 1\n'
                 '            elif result == "ambiguous":\n'
                 '                ambiguous += 1\n'
                 '        return removed, ambiguous\n'
                 '\n'
                 '    def cleanup_following_periods(self):\n'
                 '            if not self.require_unlocked("Vorlage für Folgezeiträume ist nicht möglich"): return\n'
                 '            return self.sync_current_as_template_to_following_periods()\n'
                 '\n'
                 '    def draw_progress(self, parent, percent, width=260, height=20, bg=None):\n'
                 '        bg = bg or parent.cget("bg")\n'
                 '        c = tk.Canvas(parent, width=width, height=height, bg=bg, highlightthickness=0)\n'
                 '        c.create_rectangle(0, 0, width, height, fill="#D6DCE4", outline="#C2CAD5")\n'
                 '        fill_w = int(width * max(0, min(100, percent)) / 100)\n'
                 '        if fill_w: c.create_rectangle(0, 0, fill_w, height, fill=progress_color(percent), '
                 'outline=progress_color(percent))\n'
                 '        c.create_text(width / 2, height / 2, text=f"{percent}%", fill=COLORS["text"], font=("Segoe '
                 'UI", 9, "bold"))\n'
                 '        return c\n'
                 '\n'
                 '    def render_period_controls(self, parent):\n'
                 '        row = tk.Frame(parent, bg=COLORS["bg"])\n'
                 '        row.pack(fill="x", padx=24, pady=(10, 4))\n'
                 '        tk.Button(row, text="< vorherige(r) Monat", command=lambda: '
                 'self.change_period(add_period(self.period, -1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                 'pady=6, font=zfont(self.app, 10, "bold")).pack(side="left")\n'
                 '        periods = list_periods(); labels = {period_label(k): k for k in periods}; selected = '
                 'tk.StringVar(value=period_label(self.period))\n'
                 '        menu = tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: '
                 'self.change_period(labels[label]))\n'
                 '        menu.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0); '
                 'menu.pack(side="left", padx=10)\n'
                 '        tk.Button(row, text="nächstes Geschäftsjahr >", command=lambda: '
                 'self.change_period(add_period(self.period, 1)), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                 'pady=6).pack(side="left")\n'
                 '        tk.Frame(row, bg=COLORS["bg"]).pack(side="left", fill="x", expand=True)\n'
                 '        if self.can_edit(): self.render_edit_button(row)\n'
                 '\n'
                 '    def render_edit_button(self, parent):\n'
                 '        photo = '
                 'self.get_close_icon_photo("1486504369-change-edit-options-pencil-settings-tools-write_81307.ico", '
                 '28, 28)\n'
                 '        btn = tk.Button(\n'
                 '            parent,\n'
                 '            text="" if photo else "Bearbeiten",\n'
                 '            image=photo if photo else "",\n'
                 '            command=self.toggle_edit_mode,\n'
                 '            bg=parent.cget("bg"),\n'
                 '            activebackground=parent.cget("bg"),\n'
                 '            fg=COLORS["blue"],\n'
                 '            bd=0,\n'
                 '            highlightthickness=0,\n'
                 '            padx=2,\n'
                 '            pady=2,\n'
                 '            cursor="hand2",\n'
                 '        )\n'
                 '        if photo:\n'
                 '            btn.image = photo\n'
                 '        btn.pack(side="right", padx=(8, 0))\n'
                 '        btn.bind("<Enter>", lambda _e: self.show_tooltip(btn, "Bearbeiten"))\n'
                 '        btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                 '\n'
                 '    def create_delegate_button(self, parent, item, parent_task=None):\n'
                 '        photo = '
                 'self.get_close_icon_photo("1904671-arrow-arrow-right-change-direction-next-page-right_122521.ico", '
                 '14, 14)\n'
                 '        btn = tk.Button(\n'
                 '            parent,\n'
                 '            text="Delegieren",\n'
                 '            image=photo if photo else "",\n'
                 '            compound="left" if photo else "none",\n'
                 '            command=lambda it=item, pt=parent_task: self.show_delegate_popup(it, pt),\n'
                 '            bg=COLORS["white"],\n'
                 '            activebackground=COLORS["header"],\n'
                 '            fg=COLORS["blue"],\n'
                 '            bd=1,\n'
                 '            relief="solid",\n'
                 '            padx=5,\n'
                 '            pady=2,\n'
                 '            cursor="hand2",\n'
                 '            font=("Segoe UI", 8, "bold"),\n'
                 '        )\n'
                 '        if photo:\n'
                 '            btn.image = photo\n'
                 '        return btn\n'
                 '\n'
                 '    def show_delegate_popup(self, item, parent_task=None):\n'
                 '        if not self.can_edit():\n'
                 '            messagebox.showwarning("FiBu Mate", "Keine Berechtigung zum Delegieren.")\n'
                 '            return\n'
                 '        task_for_team = parent_task or item\n'
                 '        choices = self.user_choices()\n'
                 '        labels = []\n'
                 '        label_to_choice = {}\n'
                 '        current_key = item.get("owner_user_key", "")\n'
                 '        current_label = None\n'
                 '        for key, display in choices:\n'
                 '            label = display if not key else f"{display} ({key})"\n'
                 '            labels.append(label)\n'
                 '            label_to_choice[label] = (key, display)\n'
                 '            if key == current_key:\n'
                 '                current_label = label\n'
                 '        if not labels:\n'
                 '            messagebox.showwarning("FiBu Mate", "Keine Benutzer für die Delegierung vorhanden.")\n'
                 '            return\n'
                 '        if current_label is None:\n'
                 '            current_label = labels[0]\n'
                 '        win = tk.Toplevel(self.root)\n'
                 '        win.title("Zuständigkeit delegieren")\n'
                 '        win.configure(bg=COLORS["bg"])\n'
                 '        win.transient(self.root)\n'
                 '        win.grab_set()\n'
                 '        win.geometry("460x190")\n'
                 '        tk.Label(win, text="Zuständigkeit delegieren", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))\n'
                 '        tk.Label(win, text="Bitte neue Zuständigkeit wählen.", bg=COLORS["bg"], fg=COLORS["text2"], '
                 'font=("Segoe UI", 10), wraplength=420, justify="left").pack(anchor="w", padx=16, pady=(0, 10))\n'
                 '        selected = tk.StringVar(value=current_label)\n'
                 '        menu = tk.OptionMenu(win, selected, *labels)\n'
                 '        menu.config(bg=COLORS["white"], fg=COLORS["text"], bd=1, highlightthickness=0)\n'
                 '        menu.pack(fill="x", padx=16, pady=(0, 14))\n'
                 '        def apply_delegate():\n'
                 '            user_key, display_name = label_to_choice[selected.get()]\n'
                 '            scope = self.ask_delegate_scope(item, parent_task)\n'
                 '            if not scope:\n'
                 '                return\n'
                 '            fallback_team = task_for_team.get("team", item.get("team", "Team"))\n'
                 '            owner_name = display_name if user_key else fallback_team\n'
                 '            targets = [item]\n'
                 '            if parent_task is None:\n'
                 '                targets += [sub for sub in item.get("subtasks", []) if not sub.get("deleted")]\n'
                 '            for target in targets:\n'
                 '                target["owner_user_key"] = user_key\n'
                 '                target["owner"] = owner_name\n'
                 '            self.save()\n'
                 '            changed = 0\n'
                 '            if scope == "permanent" and parent_task is None:\n'
                 '                task_key = self.task_match_key(item)\n'
                 '                changed = self.apply_delegate_to_following_periods(task_key, owner_name, user_key)\n'
                 '            if user_key:\n'
                 '                self.send_delegation_email(user_key, display_name, task_for_team.get("title", '
                 'item.get("title", "")), scope)\n'
                 '            if self.selected_team:\n'
                 '                self.render_team_detail(self.selected_team)\n'
                 '            win.destroy()\n'
                 '            if scope == "permanent":\n'
                 '                messagebox.showinfo("Delegierung", f"Permanente Delegierung übertragen. '
                 'Folgezeiträume aktualisiert: {changed}")\n'
                 '        footer = tk.Frame(win, bg=COLORS["bg"])\n'
                 '        footer.pack(fill="x", padx=16, pady=(0, 14))\n'
                 '        tk.Button(footer, text="Übernehmen", command=apply_delegate, bg=COLORS["blue"], fg="white", '
                 'bd=0, padx=14, pady=7, cursor="hand2").pack(side="right")\n'
                 '        tk.Button(footer, text="Abbrechen", command=win.destroy, bg=COLORS["header"], '
                 'fg=COLORS["text"], bd=0, padx=14, pady=7, cursor="hand2").pack(side="right", padx=(0, 8))\n'
                 '\n'
                 '    def show_tooltip(self, widget, text):\n'
                 '        self.hide_tooltip(); self.tooltip = tk.Toplevel(widget); '
                 'self.tooltip.wm_overrideredirect(True); self.tooltip.geometry(f"+{widget.winfo_rootx() + '
                 '12}+{widget.winfo_rooty() + 34}"); tk.Label(self.tooltip, text=text, bg="#111827", fg="white", '
                 'font=("Segoe UI", 9), padx=6, pady=3).pack()\n'
                 '\n'
                 '    def hide_tooltip(self):\n'
                 '        if self.tooltip:\n'
                 '            try: self.tooltip.destroy()\n'
                 '            except Exception: pass\n'
                 '        self.tooltip = None\n'
                 '\n'
                 '    def toggle_edit_mode(self):\n'
                 '        self.edit_mode = not self.edit_mode\n'
                 '        self.render_team_detail(self.selected_team) if self.selected_team else '
                 'self.render_dashboard()\n'
                 '\n'
                 '    def render_edit_tools(self, parent, team=None):\n'
                 '        if not (self.can_edit() and self.edit_mode): return\n'
                 '        row = tk.Frame(parent, bg=COLORS["edit_bg"], bd=1, relief="solid"); row.pack(fill="x", '
                 'padx=24, pady=(0, 8))\n'
                 '        tk.Label(row, text="Bearbeitungsmodus aktiv", bg=COLORS["edit_bg"], fg=COLORS["text"], '
                 'font=("Segoe UI", 10, "bold")).pack(side="left", padx=10, pady=7)\n'
                 '        if team:\n'
                 '            tk.Button(row, text="+ Aufgabe hinzufügen", command=lambda: self.open_task_dialog(team), '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=5, font=zfont(self.app, 10, '
                 '"bold")).pack(side="left", padx=8)\n'
                 '            tk.Button(row, text="Aufgaben allen vorhandenen Perioden zuweisen", '
                 'command=self.apply_current_tasks_to_all_periods, bg=COLORS["orange"], fg="white", bd=0, padx=12, '
                 'pady=5, font=zfont(self.app, 10, "bold")).pack(side="left", padx=8)\n'
                 '            tk.Button(row, text="Diesen Zeitraum als Vorlage für Folgegeschäftsjahre verwenden", '
                 'command=self.cleanup_following_periods, bg=COLORS["red"], fg="white", bd=0, padx=12, '
                 'pady=5).pack(side="left", padx=8)\n'
                 '\n'
                 '    def change_period(self, period):\n'
                 '        if not period_allowed(period):\n'
                 '            messagebox.showinfo("Jahresabschluss", "Dieses Geschäftsjahr liegt außerhalb der '
                 'freigegebenen Zeitraumlogik. Folge-Geschäftsjahre werden erst ab dem Abschluss-Stichtag August '
                 'freigegeben.")\n'
                 '            return\n'
                 '        self.period = period; self.reload(); self.selected_team = None; self.render_dashboard()\n'
                 '\n'
                 '    def save_cutoff_from_entry(self, entry_var=None):\n'
                 '        messagebox.showinfo(\n'
                 '            "FiBu Mate",\n'
                 '            "Der Abschluss-Stichtag wird zentral in der Stichtagspflege gepflegt.\\n\\n"\n'
                 '            "Eine manuelle Änderung in der Zeitraumsübersicht ist nicht mehr möglich."\n'
                 '        )\n'
                 '\n'
                 '    def render_dashboard(self):\n'
                 '        self.ensure_close_metadata()\n'
                 '        old_cutoff = self.data.get("closing_cutoff_date", "")\n'
                 '        normalize_cutoff(self.data, self.period)\n'
                 '        if old_cutoff != self.data.get("closing_cutoff_date", ""):\n'
                 '            save_period(self.period, self.data)\n'
                 '            self.data = load_period(self.period)\n'
                 '        self.selected_team = None; self.clear_frame(); self.render_period_controls(self.frame); '
                 'self.render_edit_tools(self.frame)\n'
                 '        stats = calc_stats(self.tasks())\n'
                 '        top = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); top.pack(fill="x", '
                 'padx=24, pady=(8, 10))\n'
                 '        title_row = tk.Frame(top, bg=COLORS["white"]); title_row.pack(fill="x", padx=14, pady=(6, '
                 '2))\n'
                 '        tk.Label(title_row, text=f"Jahresabschluss {period_label(self.period)}", bg=COLORS["white"], '
                 'fg=COLORS["text"], font=("Segoe UI", 22, "bold")).pack(side="left")\n'
                 '        cutoff_text = format_date_de(self.data.get("closing_cutoff_date")) or "nicht gepflegt"\n'
                 '        tk.Label(title_row, text="Abschluss-Stichtag", bg=COLORS["white"], fg=COLORS["text2"], '
                 'font=("Segoe UI", 10, "bold")).pack(side="left", padx=(24, 6))\n'
                 '        tk.Label(title_row, text=cutoff_text, bg="#F8FAFC", fg=COLORS["text"], font=("Segoe UI", 10, '
                 '"bold"), relief="solid", bd=1, padx=8, pady=3).pack(side="left")\n'
                 '        toggle_text = f"{period_label(self.period)} {\'öffnen\' if self.is_period_closed() else '
                 '\'abschließen\'}"\n'
                 '        enabled = self.can_toggle_period_close() and (self.is_period_closed() or '
                 'self.is_after_cutoff())\n'
                 '        tooltip = "Abschluss erst nach Ablauf des Abschluss-Stichtags möglich" if '
                 'self.can_toggle_period_close() and not self.is_period_closed() and not self.is_after_cutoff() else '
                 '""\n'
                 '        self.create_icon_button(title_row, toggle_text, self.toggle_period_close, "unlock" if '
                 'self.is_period_closed() else "lock", enabled, tooltip).pack(side="left", padx=(8,0))\n'
                 '        is_preliminary_report = not self.is_after_cutoff() and not self.is_period_closed()\n'
                 '        report_text = "vorläufigen Abschlussbericht erstellen" if is_preliminary_report else '
                 '"Abschlussbericht erstellen"\n'
                 '        if (self.role_rank_value() >= 4 if is_preliminary_report else self.role_rank_value() >= 3):\n'
                 '            tk.Button(title_row, text=report_text, command=self.create_close_report, '
                 'bg=COLORS["white"], fg=COLORS["blue"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                 'padx=(8, 0))\n'
                 '        tk.Button(title_row, text="Änderungsprotokoll anzeigen", command=self.show_change_log, '
                 'bg=COLORS["white"], fg=COLORS["text"], bd=1, padx=10, pady=4, cursor="hand2").pack(side="left", '
                 'padx=(8,0))\n'
                 '        status_text = self.close_status_text()\n'
                 '        if status_text:\n'
                 '            tk.Label(top, text=status_text, bg=COLORS["white"], fg=COLORS["orange"] if not '
                 'self.is_period_closed() else COLORS["dark_green"], font=("Segoe UI", 10, "bold")).pack(anchor="w", '
                 'padx=14, pady=(2,0))\n'
                 '        tk.Label(top, text=f"Gesamt: {stats[\'done\']} erledigt / {stats[\'in_progress\']} in '
                 "Bearbeitung / {stats['open']} offen / {stats['critical']} kritisch / {stats['overdue']} "
                 'überfällig", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", '
                 'padx=14)\n'
                 '        holder = tk.Frame(top, bg=COLORS["white"]); holder.pack(anchor="w", padx=14, pady=(8, 10)); '
                 'self.draw_progress(holder, stats["percent"], width=520, height=24, '
                 'bg=COLORS["white"]).pack(side="left")\n'
                 '        self.render_warnings(self.frame)\n'
                 '        cards = tk.Frame(self.frame, bg=COLORS["bg"]); cards.pack(fill="both", expand=True, padx=24, '
                 'pady=8)\n'
                 '        for idx, team in enumerate(TEAMS): self.render_team_card(cards, team, idx)\n'
                 '        self._live_period_mtime = self._period_file_mtime()\n'
                 '        self.bind_module_ctrl_mousewheel_guard()\n'
                 '        self._start_live_period_refresh()\n'
                 '\n'
                 '    def render_warnings(self, parent):\n'
                 '        warnings = [t for t in self.tasks() if warning_level(t) in ("overdue", "today", "orange", '
                 '"yellow") and t.get("status") != STATUS_DONE]\n'
                 '        box = tk.Frame(parent, bg="#FFF7ED" if warnings else "#ECFDF5", bd=1, relief="solid"); '
                 'box.pack(fill="x", padx=24, pady=(0, 8))\n'
                 '        if warnings:\n'
                 '            tk.Label(box, text=f"⚠ Fristwarnungen im ausgewählten Zeitraum: {len(warnings)} '
                 'Aufgabe(n)", bg=box["bg"], fg=COLORS["red"], font=("Segoe UI", 12, "bold")).pack(anchor="w", '
                 'padx=12, pady=(8, 3))\n'
                 '            for task in sorted(warnings, key=lambda t: t.get("due_date", ""))[:5]:\n'
                 '                tk.Label(box, text=f"- {task[\'title\']} | {task[\'team\']} | fällig am '
                 '{format_date_de(task.get(\'due_date\'))} | {task.get(\'deadline_type\')}", bg=box["bg"], '
                 'fg=COLORS["text"], font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=1)\n'
                 '        else:\n'
                 '            tk.Label(box, text="✓ Keine kritischen Fristen im aktuellen Zeitraum", bg=box["bg"], '
                 'fg=COLORS["dark_green"], font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=8)\n'
                 '\n'
                 '    def next_relevant_task(self, tasks):\n'
                 '        open_tasks = [t for t in tasks if t.get("status") != STATUS_DONE and t.get("deadline_type") '
                 '!= "keine"]\n'
                 '        return sorted(open_tasks, key=lambda t: parse_date(t.get("due_date", "9999-12-31")) or '
                 'date.max)[0] if open_tasks else None\n'
                 '\n'
                 '    def bind_click_recursive(self, widget, command):\n'
                 '        widget.bind("<Button-1>", lambda _e: command()); widget.configure(cursor="hand2")\n'
                 '        for child in widget.winfo_children():\n'
                 '            if isinstance(child, (tk.Entry, tk.Text, tk.Button)): continue\n'
                 '            self.bind_click_recursive(child, command)\n'
                 '\n'
                 '    def save_team_members_from_widget(self, team, widget):\n'
                 '        set_team_members_text(self.data, team, widget.get("1.0", "end")); self.save(); '
                 'self.propagate_team_members_to_related_periods(); self.reload(); self.render_dashboard()\n'
                 '\n'
                 '    def render_team_members_on_card(self, card, team):\n'
                 '        names = normalize_team_members(self.data).get(team, [])\n'
                 '        if self.edit_mode and self.can_edit():\n'
                 '            edit_box = tk.Text(card, height=3, width=42, bg="#F8FAFC", fg=COLORS["text"], '
                 'relief="solid", bd=1); edit_box.insert("1.0", "\\n".join(names)); edit_box.pack(anchor="w", padx=18, '
                 'pady=(0, 6))\n'
                 '            tk.Button(card, text="Namen speichern", command=lambda t=team, w=edit_box: '
                 'self.save_team_members_from_widget(t, w), bg=COLORS["blue"], fg="white", bd=0, padx=8, '
                 'pady=3).pack(anchor="w", padx=18, pady=(0, 10))\n'
                 '        elif names:\n'
                 '            tk.Label(card, text=" • ".join(names), bg=COLORS["white"], fg=COLORS["text2"], '
                 'font=("Segoe UI", 10), wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, 12))\n'
                 '\n'
                 '    def render_team_card(self, parent, team, idx):\n'
                 '        row, col = divmod(idx, 2); tasks = self.team_tasks(team); stats = calc_stats(tasks)\n'
                 '        warn = max([warning_level(t) for t in tasks], key=lambda x: {"overdue": 4, "today": 3, '
                 '"orange": 2, "yellow": 1, "none": 0, "done": 0}.get(x, 0), default="none")\n'
                 '        border = COLORS["red"] if warn in ("overdue", "today") else COLORS["orange"] if warn == '
                 '"orange" else COLORS["line"]\n'
                 '        card = tk.Frame(parent, bg=COLORS["white"], bd=2, relief="solid", '
                 'highlightbackground=border, highlightcolor=border, highlightthickness=2); card.grid(row=row, '
                 'column=col, padx=12, pady=12, sticky="nsew")\n'
                 '        parent.grid_columnconfigure(col, weight=1); parent.grid_rowconfigure(row, weight=1)\n'
                 '        tk.Label(card, text=team, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 17, '
                 '"bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                 '        tk.Label(card, text=f"{stats[\'done\']} / {stats[\'total\']} erledigt | offen: '
                 '{stats[\'open\']} | in Bearbeitung: {stats[\'in_progress\']} | kritisch: {stats[\'critical\']}", '
                 'bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 11)).pack(anchor="w", padx=18)\n'
                 '        holder = tk.Frame(card, bg=COLORS["white"]); holder.pack(anchor="w", padx=18, pady=(10, 8)); '
                 'self.draw_progress(holder, stats["percent"], width=420, height=26, bg=COLORS["white"]).pack()\n'
                 '        nxt = self.next_relevant_task(tasks); txt = "Nächste Frist: keine relevanten offenen '
                 'Fristen" if not nxt else f"Nächste Frist: {format_date_de(nxt.get(\'due_date\'))} | '
                 '{nxt.get(\'title\')}"\n'
                 '        tk.Label(card, text=txt, bg=COLORS["white"], fg=COLORS["red"] if nxt and warning_level(nxt) '
                 'in ("overdue", "today", "orange") else COLORS["text2"], font=("Segoe UI", 10, '
                 '"bold")).pack(anchor="w", padx=18, pady=(0, 5))\n'
                 '        self.render_team_members_on_card(card, team); self.bind_click_recursive(card, lambda t=team: '
                 'self.render_team_detail(t))\n'
                 '\n'
                 '    def render_team_detail(self, team):\n'
                 '        self.selected_team = team; self.clear_frame(); self.render_period_controls(self.frame); '
                 'self.render_edit_tools(self.frame, team=team); stats = calc_stats(self.team_tasks(team))\n'
                 '        head = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid"); head.pack(fill="x", '
                 'padx=24, pady=(8, 10))\n'
                 '        tk.Button(head, text="< Zur Übersicht", command=self.render_dashboard, bg=COLORS["blue"], '
                 'fg="white", bd=0, padx=12, pady=6).pack(anchor="w", padx=12, pady=(10, 4))\n'
                 '        tk.Label(head, text=f"{team} | Jahresabschluss {period_label(self.period)}", '
                 'bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 19, "bold")).pack(anchor="w", padx=12)\n'
                 '        tk.Label(head, text=f"Fortschritt: {stats[\'done\']} / {stats[\'total\']} erledigt | '
                 '{stats[\'percent\']}%", bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", '
                 '11)).pack(anchor="w", padx=12)\n'
                 '        bar = tk.Frame(head, bg=COLORS["white"]); bar.pack(anchor="w", padx=12, pady=(6, 10)); '
                 'self.draw_progress(bar, stats["percent"], width=480, height=22, bg=COLORS["white"]).pack()\n'
                 '        self.render_task_table(team)\n'
                 '        self.bind_module_ctrl_mousewheel_guard()\n'
                 '\n'
                 '    def toggle_subtasks_visibility(self, task_id):\n'
                 '        if task_id in self.expanded_tasks:\n'
                 '            self.expanded_tasks.remove(task_id)\n'
                 '        else:\n'
                 '            self.expanded_tasks.add(task_id)\n'
                 '        self.render_team_detail(self.selected_team)\n'
                 '\n'
                 '    def normalize_documentation_fields(self, item):\n'
                 '        item.setdefault("attachments", [])\n'
                 '        item.setdefault("comments", [])\n'
                 '        doc = item.get("documentation")\n'
                 '        if isinstance(doc, str):\n'
                 '            item["documentation"] = {"name": os.path.basename(doc), "path": doc, "updated_at": ""} '
                 'if doc else {}\n'
                 '        elif not isinstance(doc, dict):\n'
                 '            item["documentation"] = {}\n'
                 '        clean_attachments = []\n'
                 '        for att in item.get("attachments", []):\n'
                 '            if isinstance(att, str):\n'
                 '                clean_attachments.append({"name": os.path.basename(att), "path": att, "comment": "", '
                 '"added_at": ""})\n'
                 '            elif isinstance(att, dict):\n'
                 '                att.setdefault("name", os.path.basename(att.get("path", "")) or att.get("name", '
                 '"Anlage"))\n'
                 '                att.setdefault("path", "")\n'
                 '                att.setdefault("comment", "")\n'
                 '                clean_attachments.append(att)\n'
                 '        item["attachments"] = clean_attachments\n'
                 '        return item\n'
                 '\n'
                 '    def due_display_inline(self, task):\n'
                 '        date_text = format_date_de(task.get("due_date", ""))\n'
                 '        rule = due_rule_text(task)\n'
                 '        return f"{date_text} - {rule}" if rule else date_text\n'
                 '\n'
                 '    def find_subtask(self, task_id, subtask_id):\n'
                 '        task = self.find_task(task_id)\n'
                 '        if not task:\n'
                 '            return None, None\n'
                 '        for sub in task.get("subtasks", []):\n'
                 '            if sub.get("id") == subtask_id and not sub.get("deleted"):\n'
                 '                self.normalize_documentation_fields(sub)\n'
                 '                return task, sub\n'
                 '        return task, None\n'
                 '\n'
                 '    def documentation_count(self, item):\n'
                 '        self.normalize_documentation_fields(item)\n'
                 '        return 1 if item.get("documentation", {}).get("path") else 0\n'
                 '\n'
                 '    def attachment_count(self, item):\n'
                 '        self.normalize_documentation_fields(item)\n'
                 '        return len([a for a in item.get("attachments", []) if a.get("path")])\n'
                 '\n'
                 '    def get_close_icon_photo(self, icon_file, max_w=24, max_h=24):\n'
                 '        try:\n'
                 '            from PIL import Image, ImageTk\n'
                 '        except Exception:\n'
                 '            return None\n'
                 '        if not hasattr(self, "_icon_cache"):\n'
                 '            self._icon_cache = {}\n'
                 '        cache_key = (icon_file, int(max_w), int(max_h))\n'
                 '        if cache_key in self._icon_cache:\n'
                 '            return self._icon_cache[cache_key]\n'
                 '        icon_dir = Path(__file__).resolve().parent.parent / "Imgs" / "Icons" if '
                 'Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / "bin" '
                 '/ "Imgs" / "Icons"\n'
                 '        path = icon_dir / icon_file\n'
                 '        if not path.exists():\n'
                 '            return None\n'
                 '        try:\n'
                 '            img = Image.open(path).convert("RGBA")\n'
                 '            ow, oh = img.size\n'
                 '            scale = min(1, max_w / max(1, ow), max_h / max(1, oh))\n'
                 '            img = img.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))\n'
                 '            photo = ImageTk.PhotoImage(img)\n'
                 '            self._icon_cache[cache_key] = photo\n'
                 '            return photo\n'
                 '        except Exception:\n'
                 '            return None\n'
                 '\n'
                 '    def create_attachment_button(self, parent, item, command):\n'
                 '        frame = tk.Frame(parent, bg=parent.cget("bg"))\n'
                 '        inner = tk.Frame(frame, bg=parent.cget("bg"))\n'
                 '        inner.place(relx=0.5, rely=0.5, anchor="center")\n'
                 '        photo = self.get_close_icon_photo("-attach-file_90371.ico", 18, 18)\n'
                 '        btn = tk.Button(inner, text="" if photo else "📎", image=photo, command=command, '
                 'bg=parent.cget("bg"), fg=COLORS["blue"], bd=0, cursor="hand2", padx=0, pady=0)\n'
                 '        if photo:\n'
                 '            btn.image = photo\n'
                 '        btn.pack(side="left", padx=(0, 3))\n'
                 '        tk.Label(inner, text=str(self.attachment_count(item)), bg=parent.cget("bg"), '
                 'fg=COLORS["blue"], font=("Segoe UI", 10, "bold")).pack(side="left")\n'
                 '        return frame\n'
                 '\n'
                 '    def draw_documentation_icon(self, canvas, has_documentation):\n'
                 '        canvas.delete("all")\n'
                 '        icon_file = "fileinterfacesymboloftextpapersheet_79740.ico" if has_documentation else '
                 '"addfileinterfacesymbolofpapersheetwithtextlinesandplussign_79821.ico"\n'
                 '        photo = self.get_close_icon_photo(icon_file, 22, 22)\n'
                 '        if photo:\n'
                 '            canvas.create_image(16, 12, image=photo)\n'
                 '            canvas.image = photo\n'
                 '            return\n'
                 '        color = COLORS["blue"]\n'
                 '        # Fallback ohne blaue Kachel: kleines Dokument-/Plus-Symbol nur als Liniengrafik.\n'
                 '        canvas.create_rectangle(8, 3, 22, 21, outline=color, width=2)\n'
                 '        canvas.create_line(18, 3, 22, 7, fill=color, width=2)\n'
                 '        if has_documentation:\n'
                 '            for y in (9, 13, 17):\n'
                 '                canvas.create_line(11, y, 20, y, fill=color, width=2, capstyle="round")\n'
                 '        else:\n'
                 '            canvas.create_line(15, 9, 15, 18, fill=color, width=2, capstyle="round")\n'
                 '            canvas.create_line(10, 13, 20, 13, fill=color, width=2, capstyle="round")\n'
                 '\n'
                 '    def create_documentation_button(self, parent, item, title, parent_task=None):\n'
                 '        has_doc = bool(item.get("documentation", {}).get("path"))\n'
                 '        bg = parent.cget("bg")\n'
                 '        btn = tk.Canvas(parent, width=32, height=24, bg=bg, highlightthickness=0, bd=0, '
                 'cursor="hand2")\n'
                 '        self.draw_documentation_icon(btn, has_doc)\n'
                 '        btn.bind("<Button-1>", lambda _e, it=item, t=title, pt=parent_task: '
                 'self.show_documentation_popup(it, t, pt))\n'
                 '        return btn\n'
                 '\n'
                 '    def show_documentation_popup(self, item, title, parent_task=None):\n'
                 '        self.normalize_documentation_fields(item)\n'
                 '        win = tk.Toplevel(self.root)\n'
                 '        win.title(f"Dokumentation - {title}")\n'
                 '        win.configure(bg=COLORS["bg"])\n'
                 '        win.geometry("720x270")\n'
                 '        win.transient(self.root)\n'
                 '        win.grab_set()\n'
                 '        tk.Label(win, text="Dokumentation", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", '
                 '14, "bold")).pack(anchor="w", padx=16, pady=(14, 8))\n'
                 '        body = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                 '        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))\n'
                 '        doc = item.get("documentation", {})\n'
                 '        name_var = tk.StringVar(value=doc.get("name", "Noch keine Dokumentation hinterlegt"))\n'
                 '        path_var = tk.StringVar(value=doc.get("path", ""))\n'
                 '\n'
                 '        row = tk.Frame(body, bg=COLORS["white"])\n'
                 '        row.pack(fill="x", padx=12, pady=(14, 6))\n'
                 '        open_button = tk.Button(row, text="Dokumentation öffnen", command=lambda: '
                 'self.open_attachment(path_var.get()), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=6, '
                 'state="normal" if path_var.get() else "disabled")\n'
                 '        open_button.pack(side="left")\n'
                 '        tk.Label(row, textvariable=name_var, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe '
                 'UI", 10), anchor="w").pack(side="left", padx=(10, 6), fill="x", expand=True)\n'
                 '\n'
                 '        def refresh_after_change():\n'
                 '            if self.selected_team:\n'
                 '                self.render_team_detail(self.selected_team)\n'
                 '\n'
                 '        def choose_documentation():\n'
                 '            selected = filedialog.askopenfilename(title="Dokumentation auswählen")\n'
                 '            if not selected:\n'
                 '                return\n'
                 '            item["documentation"] = {"name": os.path.basename(selected), "path": selected, '
                 '"updated_at": datetime.now().isoformat(timespec="seconds")}\n'
                 '            self.save()\n'
                 '            name_var.set(os.path.basename(selected))\n'
                 '            path_var.set(selected)\n'
                 '            refresh_after_change()\n'
                 '            win.destroy()\n'
                 '\n'
                 '        def remove_documentation():\n'
                 '            if not path_var.get():\n'
                 '                return\n'
                 '            if not messagebox.askyesno("Dokumentation entfernen", "Dokumentation entfernen?", '
                 'parent=win):\n'
                 '                return\n'
                 '            item["documentation"] = {}\n'
                 '            self.save()\n'
                 '            name_var.set("Noch keine Dokumentation hinterlegt")\n'
                 '            path_var.set("")\n'
                 '            refresh_after_change()\n'
                 '            win.destroy()\n'
                 '\n'
                 '        if path_var.get():\n'
                 '            trash_photo = self.get_close_icon_photo("biggarbagebin_121980.ico", 20, 20)\n'
                 '            delete_btn = tk.Button(row, text="" if trash_photo else "🗑", image=trash_photo, '
                 'command=remove_documentation, bg=COLORS["white"], fg=COLORS["red"], bd=0, padx=2, pady=2, '
                 'cursor="hand2")\n'
                 '            if trash_photo:\n'
                 '                delete_btn.image = trash_photo\n'
                 '            delete_btn.pack(side="right", padx=(6, 0))\n'
                 '\n'
                 '        change = tk.Label(body, text="Dokumentationspfad ändern" if path_var.get() else '
                 '"Dokumentation anhängen", bg=COLORS["white"], fg=COLORS["blue"], font=("Segoe UI", 10, "underline"), '
                 'cursor="hand2")\n'
                 '        change.pack(anchor="w", padx=12, pady=(4, 10))\n'
                 '        change.bind("<Button-1>", lambda _e: choose_documentation())\n'
                 '        tk.Label(body, text="Hinweis: Die Dokumentation ist für Aufgabenbeschreibungen bzw. '
                 'Leitfäden vorgesehen. Ergebnisse und Bearbeitungskommentare bitte unter Anlagen pflegen.", '
                 'bg=COLORS["white"], fg=COLORS["text2"], font=("Segoe UI", 9), wraplength=660, '
                 'justify="left").pack(anchor="w", padx=12, pady=(0, 10))\n'
                 '        tk.Button(win, text="Schließen", command=win.destroy, bg=COLORS["blue"], fg="white", bd=0, '
                 'padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))\n'
                 '\n'
                 '    def render_task_table(self, team):\n'
                 '        outer = tk.Frame(self.frame, bg=COLORS["white"], bd=1, relief="solid")\n'
                 '        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))\n'
                 '\n'
                 '        scroll_canvas = tk.Canvas(outer, bg=COLORS["white"], highlightthickness=0, bd=0)\n'
                 '        scrollbar = tk.Scrollbar(outer, orient="vertical", command=scroll_canvas.yview)\n'
                 '        xscrollbar = tk.Scrollbar(outer, orient="horizontal", command=scroll_canvas.xview)\n'
                 '        table = tk.Frame(scroll_canvas, bg="#E4EAF1")  # dezente Spaltentrennlinien\n'
                 '        table_window = scroll_canvas.create_window((0, 0), window=table, anchor="nw")\n'
                 '\n'
                 '        def update_scrollregion(_event=None):\n'
                 '            table.update_idletasks()\n'
                 '            target_width = max(scroll_canvas.winfo_width(), table.winfo_reqwidth())\n'
                 '            scroll_canvas.itemconfigure(table_window, width=max(1, target_width))\n'
                 '            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))\n'
                 '\n'
                 '        def on_mousewheel(event):\n'
                 '            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")\n'
                 '            return "break"\n'
                 '\n'
                 '        table.bind("<Configure>", update_scrollregion)\n'
                 '        scroll_canvas.bind("<Configure>", update_scrollregion)\n'
                 '        scroll_canvas.bind("<MouseWheel>", on_mousewheel)\n'
                 '        table.bind("<MouseWheel>", on_mousewheel)\n'
                 '        scroll_canvas.configure(yscrollcommand=scrollbar.set, xscrollcommand=xscrollbar.set)\n'
                 '        xscrollbar.pack(side="bottom", fill="x")\n'
                 '        scroll_canvas.pack(side="left", fill="both", expand=True)\n'
                 '        scrollbar.pack(side="right", fill="y")\n'
                 '        self.app.active_scroll_canvas = scroll_canvas\n'
                 '        self._live_task_widgets = {}\n'
                 '        self._live_subtask_widgets = {}\n'
                 '\n'
                 '        headers = ["Status", "Aufgabe", "Dokumentation", "Zuständig", "Fällig", "Fristart", '
                 '"Priorität", "Wiederkehrend", "Anlagen", "Aktion"]\n'
                 '        if self.edit_mode and self.can_edit():\n'
                 '            headers.append("Bearbeiten")\n'
                 '        for col, h in enumerate(headers):\n'
                 '            tk.Label(table, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe UI", 10, '
                 '"bold"), padx=6, pady=6).grid(row=0, column=col, sticky="nsew")\n'
                 '        row_idx = 1\n'
                 '        for task in self.team_tasks(team):\n'
                 '            sync_parent_status_from_subtasks(task)\n'
                 '            self.normalize_documentation_fields(task)\n'
                 '            for sub in task.get("subtasks", []):\n'
                 '                self.normalize_documentation_fields(sub)\n'
                 '            row_idx = self.render_task_row(table, row_idx, task, headers)\n'
                 '\n'
                 '        # Spaltenbreiten: Aufgabe und Zuständig etwas reduziert; Dokumentation schmal; '
                 'Fristart/Priorität/Anlagen erhalten mehr Raum.\n'
                 '        min_sizes = {0: 46, 1: 560, 2: 92, 3: 225, 4: 220, 5: 105, 6: 105, 7: 120, 8: 100, 9: 88, '
                 '10: 150}\n'
                 '        stretch_cols = {1: 2, 4: 2, 5: 1, 6: 1, 8: 1}\n'
                 '        for col in range(len(headers)):\n'
                 '            table.grid_columnconfigure(col, minsize=min_sizes.get(col, 80), '
                 'weight=stretch_cols.get(col, 0))\n'
                 '        update_scrollregion()\n'
                 '\n'
                 '\n'
                 '    def render_task_row(self, table, row_idx, task, headers):\n'
                 '        current_row_idx = row_idx\n'
                 '        bg = "#ECFDF5" if task.get("status") == STATUS_DONE else "#FFF7ED" if warning_level(task) in '
                 '("overdue", "today", "orange") else {"IDE":"#FFFFFF", "IDG":"#FBE4E6", "IMS":"#FFF4CC", '
                 '"SPI":"#D6E0F0", "IHB":"#E2F2E6"}.get(task.get("booking_circle", "IDE"), COLORS["white"])\n'
                 '        can_finish = not task.get("subtasks") or all_subtasks_done(task)\n'
                 '        can_complete = self.can_complete_task(task)\n'
                 '        btn = tk.Button(table, text="✓" if task.get("status") == STATUS_DONE else "□", '
                 'command=lambda t=task: self.toggle_done(t), bg="#BBF7D0" if task.get("status") == STATUS_DONE else '
                 'bg, fg=COLORS["dark_green"] if task.get("status") == STATUS_DONE else COLORS["text"], bd=0, '
                 'font=("Segoe UI", 13, "bold"), state="normal" if can_complete else "disabled")\n'
                 '        btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                 '        if not can_complete:\n'
                 '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Nur zuständige Person darf '
                 'erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                 '        elif task.get("subtasks") and not can_finish:\n'
                 '            btn.bind("<Enter>", lambda _e, b=btn: self.show_tooltip(b, "Bitte erst alle '
                 'Unteraufgaben erledigen.")); btn.bind("<Leave>", lambda _e: self.hide_tooltip())\n'
                 '\n'
                 '        task_cell = tk.Frame(table, bg=bg)\n'
                 '        task_cell.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)\n'
                 '        visible_subtasks = sorted([s for s in task.get("subtasks", []) if not s.get("deleted")], '
                 'key=lambda s: str(s.get("title", "")).casefold())\n'
                 '\n'
                 '        task_actions = tk.Frame(task_cell, bg=bg)\n'
                 '        task_actions.pack(side="right", padx=(6, 8), pady=3)\n'
                 '        if visible_subtasks:\n'
                 '            expand_key = self.get_expand_key(task)\n'
                 '            expanded = expand_key in self.expanded_tasks\n'
                 '            toggle_text = "Unteraufgaben einklappen v" if expanded else "Unteraufgaben ausklappen '
                 '>"\n'
                 '            tk.Button(task_actions, text=toggle_text, command=lambda key=expand_key: '
                 'self.toggle_subtasks_visibility(key), bg=bg, fg=COLORS["blue"], bd=0, padx=4, pady=4, '
                 'cursor="hand2", font=zfont(self.app, 10, "bold")).pack(side="right", padx=(0, 6))\n'
                 '\n'
                 '        task_text = tk.Frame(task_cell, bg=bg)\n'
                 '        task_text.pack(side="left", fill="both", expand=True, padx=(6, 4), pady=4)\n'
                 '        tk.Label(task_text, text=str(task.get("title", "")), bg=bg, fg=COLORS["text"], '
                 'font=zfont(self.app, 12), anchor="w", justify="left", wraplength=430).pack(anchor="w", fill="x", '
                 'expand=True)\n'
                 '\n'
                 '        doc_frame = tk.Frame(table, bg=bg)\n'
                 '        doc_frame.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)\n'
                 '        # v0.520: Dokumentations-Button auch bei Aufgabengruppen anzeigen.\n'
                 '        self.create_documentation_button(doc_frame, task, task.get("title", "Aufgabe")).pack(padx=5, '
                 'pady=3)\n'
                 '\n'
                 '        owner_cell = tk.Frame(table, bg=bg)\n'
                 '        owner_cell.grid(row=row_idx, column=3, sticky="nsew", padx=1, pady=1)\n'
                 '        tk.Label(owner_cell, text=task.get("owner"), bg=bg, fg=COLORS["text"], font=("Segoe UI", '
                 '10), padx=6, pady=6, anchor="center", justify="center").pack(side="left", fill="x", expand=True)\n'
                 '        if self.can_edit():\n'
                 '            self.create_delegate_button(owner_cell, task).pack(side="right", padx=(2, 5), pady=3)\n'
                 '\n'
                 '        values = [self.due_display_inline(task), task.get("deadline_type"), task.get("priority"), '
                 '"Ja" if task.get("recurring") else "Nein"]\n'
                 '        aligns = [("w", "left"), ("center", "center"), ("center", "center"), ("center", "center")]\n'
                 '        for offset, val in enumerate(values):\n'
                 '            anchor, justify = aligns[offset]\n'
                 '            tk.Label(table, text=val, bg=bg, fg=COLORS["text"], font=("Segoe UI", 10), padx=6, '
                 'pady=6, anchor=anchor, justify=justify).grid(row=row_idx, column=4 + offset, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '        self.create_attachment_button(table, task, lambda t=task: '
                 'self.show_attachments(t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)\n'
                 '        status_var = tk.StringVar(value=task.get("status", STATUS_OPEN))\n'
                 '        menu = tk.OptionMenu(table, status_var, *STATUSES, command=lambda value, t=task: '
                 'self.set_status(t, value))\n'
                 '        menu.config(bg=bg, fg=COLORS["text"], bd=0, highlightthickness=0, state="normal" if '
                 'can_complete else "disabled")\n'
                 '        menu.grid(row=row_idx, column=9, sticky="nsew", padx=1, pady=1)\n'
                 '        self._register_live_task_widgets(table, current_row_idx, task, btn, status_var, menu)\n'
                 '        if self.edit_mode and self.can_edit():\n'
                 '            action = tk.Frame(table, bg=bg); action.grid(row=row_idx, column=10, sticky="nsew", '
                 'padx=1, pady=1)\n'
                 '            tk.Button(action, text="Bearbeiten", command=lambda t=task: '
                 'self.open_task_dialog(task.get("team"), t), bg=COLORS["blue"], fg="white", bd=0, padx=6, pady=3, '
                 'font=zfont(self.app, 10, "bold")).pack(side="left", padx=2, pady=3)\n'
                 '            tk.Button(action, text="Löschen", command=lambda t=task: self.delete_task(t), '
                 'bg=COLORS["red"], fg="white", bd=0, padx=6, pady=3, font=zfont(self.app, 10, '
                 '"bold")).pack(side="left", padx=2, pady=3)\n'
                 '        row_idx += 1\n'
                 '\n'
                 '        if self.get_expand_key(task) in self.expanded_tasks:\n'
                 '            for sub in visible_subtasks:\n'
                 '                self.normalize_documentation_fields(sub)\n'
                 '                sub_bg = "#ECFDF5" if sub.get("status") == STATUS_DONE else COLORS["subtask_bg"]\n'
                 '                sub_row_idx = row_idx\n'
                 '                sub_btn = tk.Button(table, text="✓" if sub.get("status") == STATUS_DONE else "□", '
                 'command=lambda t=task, s=sub: self.toggle_subtask(t, s), bg="#BBF7D0" if sub.get("status") == '
                 'STATUS_DONE else sub_bg, fg=COLORS["dark_green"] if sub.get("status") == STATUS_DONE else '
                 'COLORS["text"], bd=0, font=zfont(self.app, 14, "bold"), state="normal" if can_complete else '
                 '"disabled")\n'
                 '                sub_btn.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1)\n'
                 '                tk.Label(table, text="↳ " + sub.get("title", ""), bg=sub_bg, fg=COLORS["text"], '
                 'font=("Segoe UI", 10), padx=18, pady=5, anchor="w").grid(row=row_idx, column=1, sticky="nsew", '
                 'padx=1, pady=1)\n'
                 '                sub_doc = tk.Frame(table, bg=sub_bg); sub_doc.grid(row=row_idx, column=2, '
                 'sticky="nsew", padx=1, pady=1)\n'
                 '                self.create_documentation_button(sub_doc, sub, sub.get("title", "Unteraufgabe"), '
                 'parent_task=task).pack(padx=5, pady=2)\n'
                 '                sub_owner = tk.Frame(table, bg=sub_bg); sub_owner.grid(row=row_idx, column=3, '
                 'sticky="nsew", padx=1, pady=1)\n'
                 '                tk.Label(sub_owner, text=sub.get("owner", task.get("owner", "")), bg=sub_bg, '
                 'fg=COLORS["text"], font=("Segoe UI", 10), padx=6, pady=5, anchor="center", '
                 'justify="center").pack(side="left", fill="x", expand=True)\n'
                 '                if self.can_edit():\n'
                 '                    self.create_delegate_button(sub_owner, sub, parent_task=task).pack(side="right", '
                 'padx=(2, 5), pady=3)\n'
                 '                for col in (4, 5, 6, 7):\n'
                 '                    tk.Label(table, text="", bg=sub_bg, fg=COLORS["text"], font=("Segoe UI", 10), '
                 'padx=6, pady=5).grid(row=row_idx, column=col, sticky="nsew", padx=1, pady=1)\n'
                 '                self.create_attachment_button(table, sub, lambda s=sub, t=task: '
                 'self.show_attachments(s, parent_task=t)).grid(row=row_idx, column=8, sticky="nsew", padx=1, pady=1)\n'
                 '                tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=9, sticky="nsew", '
                 'padx=1, pady=1)\n'
                 '                if self.edit_mode and self.can_edit():\n'
                 '                    tk.Label(table, text="", bg=sub_bg).grid(row=row_idx, column=10, sticky="nsew", '
                 'padx=1, pady=1)\n'
                 '                self._register_live_subtask_widgets(table, sub_row_idx, task, sub, sub_btn)\n'
                 '                row_idx += 1\n'
                 '        return row_idx\n'
                 '\n'
                 '    def find_task(self, task_id):\n'
                 '        return next((t for t in self.data.get("tasks", []) if t.get("id") == task_id and not '
                 't.get("deleted")), None)\n'
                 '\n'
                 '    def toggle_done(self, task):\n'
                 '            if not self.require_unlocked("Diese Änderung"): return\n'
                 '            real = self.find_task(task["id"])\n'
                 '            if not real: return\n'
                 '            if not self.can_complete_task(real): messagebox.showwarning("Jahresabschluss", "Du '
                 'kannst nur Aufgaben als erledigt markieren, für die du selbst als zuständig eingetragen bist."); '
                 'self.render_team_detail(real.get("team")); return\n'
                 '            if real.get("subtasks") and not all_subtasks_done(real): self.show_tooltip(self.root, '
                 '"Bitte erst alle Unteraufgaben erledigen."); self.root.after(1600, self.hide_tooltip); return\n'
                 '            if real.get("status") == STATUS_DONE: real.update({"status": STATUS_OPEN, "done_at": '
                 'None, "done_by": None})\n'
                 '            else:\n'
                 '                if real.get("deadline_type") == "gesetzlich" and not '
                 'messagebox.askyesno("Jahresabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                 'markieren?"): return\n'
                 '                real.update({"status": STATUS_DONE, "done_at": '
                 'datetime.now().isoformat(timespec="seconds"), "done_by": getattr(self.app, "current_user_display", '
                 '"") or ""})\n'
                 '            self.save(); self.render_team_detail(real["team"])\n'
                 '\n'
                 '    def set_status(self, task, status):\n'
                 '            if not self.require_unlocked("Diese Änderung"): return\n'
                 '            real = self.find_task(task["id"])\n'
                 '            if not real: return\n'
                 '            if status == STATUS_DONE and not self.can_complete_task(real): '
                 'messagebox.showwarning("Jahresabschluss", "Du kannst nur Aufgaben als erledigt markieren, für die du '
                 'selbst als zuständig eingetragen bist."); self.render_team_detail(real.get("team")); return\n'
                 '            if status == STATUS_DONE and real.get("subtasks") and not all_subtasks_done(real): '
                 'messagebox.showinfo("Jahresabschluss", "Bitte erst alle Unteraufgaben erledigen."); '
                 'self.render_team_detail(real["team"]); return\n'
                 '            if status == STATUS_DONE and real.get("deadline_type") == "gesetzlich" and not '
                 'messagebox.askyesno("Jahresabschluss", "Gesetzliche Frist: Aufgabe wirklich als erledigt '
                 'markieren?"): self.render_team_detail(real["team"]); return\n'
                 '            real["status"] = status; real["done_at"] = datetime.now().isoformat(timespec="seconds") '
                 'if status == STATUS_DONE else None; real["done_by"] = getattr(self.app, "current_user_display", "") '
                 'or "" if status == STATUS_DONE else None\n'
                 '            self.save(); self.render_team_detail(real["team"])\n'
                 '\n'
                 '    def toggle_subtask(self, task, subtask):\n'
                 '            if not self.require_unlocked("Diese Änderung"): return\n'
                 '            real = self.find_task(task["id"])\n'
                 '            if not real: return\n'
                 '            if not self.can_complete_task(real): messagebox.showwarning("Jahresabschluss", "Du '
                 'kannst nur Unteraufgaben als erledigt markieren, wenn du selbst als zuständig eingetragen bist."); '
                 'self.render_team_detail(real.get("team")); return\n'
                 '            for sub in real.get("subtasks", []):\n'
                 '                if sub.get("id") == subtask.get("id"): sub["status"] = STATUS_OPEN if '
                 'sub.get("status") == STATUS_DONE else STATUS_DONE; break\n'
                 '            sync_parent_status_from_subtasks(real); self.save(); '
                 'self.render_team_detail(real["team"])\n'
                 '\n'
                 '    def next_task_index(self, team):\n'
                 '        return len([t for t in self.data.get("tasks", []) if t.get("team") == team]) + 1\n'
                 '\n'
                 '    def task_to_catalog_entry(self, task):\n'
                 '        catalog_id = task.get("catalog_id") or f"rec_{datetime.now().strftime(\'%Y%m%d%H%M%S%f\')}"; '
                 'task["catalog_id"] = catalog_id\n'
                 '        return {k: task.get(k) for k in ["catalog_id", "team", "title", "owner", "owner_user_key", '
                 '"due_date", "due_mode", "due_day", "due_workday", "due_fixed_date", "deadline_type", "priority", '
                 '"required", "recurring"]} | {"start_period": self.period, "recurring": True}\n'
                 '\n'
                 '    def upsert_catalog_entry(self, task):\n'
                 '        catalog = load_catalog(); entry = self.task_to_catalog_entry(task); tasks = '
                 'catalog.setdefault("tasks", [])\n'
                 '        for idx, existing in enumerate(tasks):\n'
                 '            if existing.get("catalog_id") == entry["catalog_id"]: entry["start_period"] = '
                 'existing.get("start_period", self.period); tasks[idx] = entry; break\n'
                 '        else: tasks.append(entry)\n'
                 '        save_catalog(catalog); return entry["catalog_id"]\n'
                 '\n'
                 '    def remove_catalog_entry(self, catalog_id):\n'
                 '        if not catalog_id: return\n'
                 '        catalog = load_catalog(); catalog["tasks"] = [t for t in catalog.get("tasks", []) if '
                 't.get("catalog_id") != catalog_id]; save_catalog(catalog)\n'
                 '\n'
                 '    def propagate_recurring_to_future_periods(self, catalog_id):\n'
                 '        if not catalog_id: return\n'
                 '        for period in list_periods():\n'
                 '            if period > self.period: apply_catalog_to_period(period)\n'
                 '\n'
                 '    def open_task_dialog(self, team, task=None):\n'
                 '        if not self.can_edit(): return\n'
                 '        is_new = task is None\n'
                 '        win = tk.Toplevel(self.root); win.title("Aufgabe anlegen" if is_new else "Aufgabe '
                 'bearbeiten"); win.configure(bg=COLORS["bg"]); win.geometry("760x590"); win.transient(self.root); '
                 'win.grab_set()\n'
                 '        data = dict(task) if task else {"title": "", "owner": team, "owner_user_key": "", '
                 '"deadline_type": "intern", "priority": "normal", "due_mode": DUE_CUTOFF, "due_day": 1, '
                 '"due_workday": 1, "due_fixed_date": "", "recurring": False, "subtasks": [], "booking_circle": '
                 '"IDE"}\n'
                 '        normalize_task(data, self.data, self.period)\n'
                 '        popup_body_container = tk.Frame(win, bg=COLORS["bg"]); '
                 'popup_body_container.pack(fill="both", expand=True, padx=0, pady=0)\n'
                 '        popup_body_canvas = tk.Canvas(popup_body_container, bg=COLORS["bg"], highlightthickness=0, '
                 'bd=0)\n'
                 '        popup_body_scrollbar = tk.Scrollbar(popup_body_container, orient="vertical", '
                 'command=popup_body_canvas.yview)\n'
                 '        popup_body = tk.Frame(popup_body_canvas, bg=COLORS["bg"])\n'
                 '        popup_body_window = popup_body_canvas.create_window((0, 0), window=popup_body, anchor="nw")\n'
                 '        def _popup_update_scrollregion(_event=None):\n'
                 '            try:\n'
                 '                popup_body_canvas.itemconfigure(popup_body_window, width=max(1, '
                 'popup_body_canvas.winfo_width() - 2))\n'
                 '                popup_body_canvas.configure(scrollregion=popup_body_canvas.bbox("all"))\n'
                 '            except Exception:\n'
                 '                pass\n'
                 '        popup_body.bind("<Configure>", _popup_update_scrollregion)\n'
                 '        popup_body_canvas.bind("<Configure>", _popup_update_scrollregion)\n'
                 '        popup_body_canvas.configure(yscrollcommand=popup_body_scrollbar.set)\n'
                 '        popup_body_canvas.pack(side="left", fill="both", expand=True, padx=14, pady=14)\n'
                 '        popup_body_scrollbar.pack(side="right", fill="y", pady=14)\n'
                 '        def _popup_mousewheel(event):\n'
                 '            try:\n'
                 '                if getattr(event, "num", None) == 4:\n'
                 '                    popup_body_canvas.yview_scroll(-3, "units")\n'
                 '                elif getattr(event, "num", None) == 5:\n'
                 '                    popup_body_canvas.yview_scroll(3, "units")\n'
                 '                else:\n'
                 '                    delta = int(getattr(event, "delta", 0) or 0)\n'
                 '                    popup_body_canvas.yview_scroll(int(-delta / 120), "units")\n'
                 '                return "break"\n'
                 '            except Exception:\n'
                 '                return "break"\n'
                 '        def _popup_bind_mousewheel(widget):\n'
                 '            try:\n'
                 '                widget.bind("<MouseWheel>", _popup_mousewheel, add=False)\n'
                 '                widget.bind("<Button-4>", _popup_mousewheel, add=False)\n'
                 '                widget.bind("<Button-5>", _popup_mousewheel, add=False)\n'
                 '                for child in widget.winfo_children():\n'
                 '                    _popup_bind_mousewheel(child)\n'
                 '            except Exception:\n'
                 '                pass\n'
                 '        notebook = ttk.Notebook(popup_body); notebook.pack(fill="both", expand=True, padx=0, '
                 'pady=0)\n'
                 '        form = tk.Frame(notebook, bg=COLORS["bg"]); subtab = tk.Frame(notebook, bg=COLORS["bg"])\n'
                 '        notebook.add(form, text="Aufgabe"); notebook.add(subtab, text="Unteraufgaben")\n'
                 '        title_var = tk.StringVar(value=data.get("title", "")); deadline_var = '
                 'tk.StringVar(value=data.get("deadline_type", "intern") if data.get("deadline_type") in '
                 'DEADLINE_TYPES else "intern"); priority_var = tk.StringVar(value=data.get("priority", "normal")); '
                 'recurring_var = tk.BooleanVar(value=bool(data.get("recurring")))\n'
                 '        due_frequency_var = tk.StringVar(value=str(data.get("due_frequency") or ("Monat" if '
                 'CLOSING_SCOPE == "M" else "Quartal" if CLOSING_SCOPE == "Q" else "Jahr")))\n'
                 '        due_mode_var = tk.StringVar(value=DUE_VALUE_TO_LABEL.get(data.get("due_mode", DUE_CUTOFF), '
                 '"Abschluss-Stichtag")); due_day_var = tk.StringVar(value=str(data.get("due_day") or 1)); '
                 'due_workday_var = tk.StringVar(value=str(data.get("due_workday") or 1)); due_fixed_var = '
                 'tk.StringVar(value=format_date_de(data.get("due_fixed_date") or data.get("due_date") or "")); '
                 'calculated_var = tk.StringVar(value="")\n'
                 '        users = self.user_choices(); user_labels = {label: key for key, label in users}; '
                 'current_owner_key = data.get("owner_user_key", ""); current_owner_label = next((label for key, label '
                 'in users if key == current_owner_key), data.get("owner", team)); owner_var = '
                 'tk.StringVar(value=current_owner_label)\n'
                 '        booking_circle_var = tk.StringVar(value=data.get("booking_circle", "IDE") if '
                 'data.get("booking_circle", "IDE") in ("IDE", "IDG", "IMS", "SPI", "IHB") else "IDE")\n'
                 '        widgets = [("Aufgabenname", tk.Entry(form, textvariable=title_var, width=52)), '
                 '("Buchungskreis", tk.OptionMenu(form, booking_circle_var, "IDE", "IDG", "IMS", "SPI", "IHB")), '
                 '("Zuständig", tk.OptionMenu(form, owner_var, *user_labels.keys())), ("Fälligkeitsturnus", tk.OptionMenu(form, due_frequency_var, "Monat", "Quartal", "Jahr")), ("Fristart", tk.OptionMenu(form, '
                 'deadline_var, *DEADLINE_TYPES)), ("Priorität", tk.OptionMenu(form, priority_var, *PRIORITIES)), '
                 '("Fälligkeitsart", tk.OptionMenu(form, due_mode_var, *DUE_LABEL_TO_VALUE.keys()))]\n'
                 '        for row, (label, widget) in enumerate(widgets):\n'
                 '            tk.Label(form, text=label, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, '
                 '"bold")).grid(row=row, column=0, sticky="w", pady=7, padx=8); widget.grid(row=row, column=1, '
                 'sticky="w", pady=7)\n'
                 '            try: widget.config(bg="white", fg=COLORS["text"], bd=1, highlightthickness=0)\n'
                 '            except Exception: pass\n'
                 '        day_label = tk.Label(form, text="Tag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe '
                 'UI", 10, "bold")); day_entry = tk.Entry(form, textvariable=due_day_var, width=8)\n'
                 '        workday_label = tk.Label(form, text="Werktag-Nr.", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=("Segoe UI", 10, "bold")); workday_entry = tk.Entry(form, textvariable=due_workday_var, '
                 'width=8)\n'
                 '        fixed_label = tk.Label(form, text="Konkretes Datum (TT.MM.JJJJ)", bg=COLORS["bg"], '
                 'fg=COLORS["text"], font=("Segoe UI", 10, "bold")); fixed_entry = tk.Entry(form, '
                 'textvariable=due_fixed_var, width=14)\n'
                 '        for r, lab, ent in [(7, day_label, day_entry), (8, workday_label, workday_entry), (9, '
                 'fixed_label, fixed_entry)]: lab.grid(row=r, column=0, sticky="w", pady=7, padx=8); ent.grid(row=r, '
                 'column=1, sticky="w", pady=7); ent.config(bg="white", fg=COLORS["text"], relief="solid", bd=1, '
                 'highlightthickness=0)\n'
                 '        tk.Checkbutton(form, text="Wiederkehrend", variable=recurring_var, bg=COLORS["bg"], '
                 'fg=COLORS["text"], font=("Segoe UI", 10, "bold"), activebackground=COLORS["bg"]).grid(row=9, '
                 'column=1, sticky="w", pady=7)\n'
                 '        tk.Label(form, text="Fälligkeitsturnus", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold")).grid(row=10, column=0, sticky="w", pady=7, padx=8)\n'
                 '        tk.OptionMenu(form, due_frequency_var, "Monat", "Quartal", "Jahr").grid(row=10, column=1, '
                 'sticky="w", pady=7)\n'
                 '        tk.Label(form, textvariable=calculated_var, bg=COLORS["bg"], fg=COLORS["text2"], '
                 'font=("Segoe UI", 10, "bold")).grid(row=10, column=1, sticky="w", pady=(4, 10))\n'
                 '        def refresh_due_input_visibility(*_):\n'
                 '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF)\n'
                 '            for lab, ent in [(day_label, day_entry), (workday_label, workday_entry), (fixed_label, '
                 'fixed_entry)]: lab.grid_remove(); ent.grid_remove()\n'
                 '            if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): '
                 'day_label.grid(); day_entry.grid()\n'
                 '            elif mode == DUE_WORKDAY_NEXT: workday_label.grid(); workday_entry.grid()\n'
                 '            elif mode == DUE_FIXED: fixed_label.grid(); fixed_entry.grid()\n'
                 '            preview = {"due_mode": mode, "due_day": due_day_var.get().strip() or 1, "due_workday": '
                 'due_workday_var.get().strip() or 1, "due_fixed_date": due_fixed_var.get().strip()}\n'
                 '            calculated_var.set("Berechnetes Fälligkeitsdatum: " + '
                 '(format_date_de(resolve_due_date(preview, self.data, self.period)) or "-"))\n'
                 '        for var in (due_mode_var, due_day_var, due_workday_var, due_fixed_var): '
                 'var.trace_add("write", refresh_due_input_visibility)\n'
                 '        refresh_due_input_visibility()\n'
                 '        subtasks_work = [dict(s) for s in data.get("subtasks", []) if not s.get("deleted")]\n'
                 '        sub_list = tk.Frame(subtab, bg=COLORS["bg"]); sub_list.pack(fill="both", expand=True, '
                 'padx=10, pady=10); new_sub_var = tk.StringVar()\n'
                 '        def open_sub_subtask_popup(parent_index):\n'
                 '            if parent_index < 0 or parent_index >= len(subtasks_work):\n'
                 '                return\n'
                 '            parent_sub = subtasks_work[parent_index]\n'
                 '            parent_sub.setdefault("subtasks", [])\n'
                 '            win2 = tk.Toplevel(win)\n'
                 '            win2.title("Unter-Unteraufgaben erstellen")\n'
                 '            win2.configure(bg=COLORS["bg"])\n'
                 '            win2.geometry("760x520")\n'
                 '            win2.transient(win)\n'
                 '            win2.grab_set()\n'
                 '            tk.Label(win2, text="Unter-Unteraufgaben erstellen", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=zfont(self.app, 18, "bold")).pack(anchor="w", padx=18, pady=(16, 4))\n'
                 '            tk.Label(win2, text="Unteraufgabe: " + str(parent_sub.get("title", "")), '
                 'bg=COLORS["bg"], fg=COLORS["text2"], font=zfont(self.app, 13), wraplength=710, '
                 'justify="left").pack(anchor="w", padx=18, pady=(0, 12))\n'
                 '            list_box = tk.Frame(win2, bg=COLORS["white"], bd=1, relief="solid")\n'
                 '            list_box.pack(fill="both", expand=True, padx=18, pady=(0, 10))\n'
                 '            new_child_var = tk.StringVar()\n'
                 '\n'
                 '            def refresh_children():\n'
                 '                for child_widget in list_box.winfo_children():\n'
                 '                    child_widget.destroy()\n'
                 '                tk.Label(list_box, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=0, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '                tk.Label(list_box, text="Unter-Unteraufgabe", bg=COLORS["header"], '
                 'fg=COLORS["text"], font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=1, '
                 'sticky="nsew", padx=1, pady=1)\n'
                 '                tk.Label(list_box, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=0, column=2, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '                list_box.grid_columnconfigure(1, weight=1)\n'
                 '                children = parent_sub.setdefault("subtasks", [])\n'
                 '                if not children:\n'
                 '                    tk.Label(list_box, text="Noch keine Unter-Unteraufgaben vorhanden.", '
                 'bg=COLORS["white"], fg=COLORS["text2"], font=zfont(self.app, 12), padx=10, pady=10, '
                 'anchor="w").grid(row=1, column=0, columnspan=3, sticky="ew")\n'
                 '                for cidx, child in enumerate(children, start=1):\n'
                 '                    child.setdefault("id", '
                 'f"subsub_{cidx:02d}_{datetime.now().strftime(\'%H%M%S%f\')}")\n'
                 '                    child.setdefault("status", STATUS_OPEN)\n'
                 '                    cvar = tk.StringVar(value=child.get("title", ""))\n'
                 '                    cstatus = tk.BooleanVar(value=child.get("status") == STATUS_DONE)\n'
                 '                    def _write_title(*_args, i=cidx-1, v=cvar):\n'
                 '                        parent_sub.setdefault("subtasks", [])[i]["title"] = v.get()\n'
                 '                    cvar.trace_add("write", _write_title)\n'
                 '                    def _write_status(i=cidx-1, v=cstatus):\n'
                 '                        parent_sub.setdefault("subtasks", [])[i]["status"] = STATUS_DONE if v.get() '
                 'else STATUS_OPEN\n'
                 '                    tk.Checkbutton(list_box, variable=cstatus, command=_write_status, '
                 'bg=COLORS["white"], activebackground=COLORS["white"]).grid(row=cidx, column=0, sticky="nsew", '
                 'padx=1, pady=1)\n'
                 '                    tk.Entry(list_box, textvariable=cvar, bg="white", fg=COLORS["text"], '
                 'relief="solid", bd=1, font=zfont(self.app, 13), width=54).grid(row=cidx, column=1, sticky="ew", '
                 'padx=6, pady=5, ipady=4)\n'
                 '                    tk.Button(list_box, text="Löschen", command=lambda i=cidx-1: delete_child(i), '
                 'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=7, font=zfont(self.app, 12, '
                 '"bold")).grid(row=cidx, column=2, sticky="w", padx=6, pady=5)\n'
                 '\n'
                 '            def add_child():\n'
                 '                title = new_child_var.get().strip()\n'
                 '                if not title:\n'
                 '                    messagebox.showwarning("Unter-Unteraufgaben", "Bitte zuerst einen Namen für die '
                 'Unter-Unteraufgabe eingeben.", parent=win2)\n'
                 '                    return\n'
                 '                parent_sub.setdefault("subtasks", []).append({"id": '
                 'f"subsub_{len(parent_sub.get(\'subtasks\', []))+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", '
                 '"title": title, "status": STATUS_OPEN})\n'
                 '                new_child_var.set("")\n'
                 '                refresh_children()\n'
                 '\n'
                 '            def delete_child(child_index):\n'
                 '                try:\n'
                 '                    parent_sub.setdefault("subtasks", []).pop(child_index)\n'
                 '                except Exception:\n'
                 '                    pass\n'
                 '                refresh_children()\n'
                 '\n'
                 '            add_box = tk.Frame(win2, bg=COLORS["bg"])\n'
                 '            add_box.pack(fill="x", padx=18, pady=(0, 10))\n'
                 '            tk.Label(add_box, text="Neue Unter-Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold")).pack(anchor="w")\n'
                 '            entry_row = tk.Frame(add_box, bg=COLORS["bg"])\n'
                 '            entry_row.pack(fill="x", pady=(5, 0))\n'
                 '            tk.Entry(entry_row, textvariable=new_child_var, bg="white", fg=COLORS["text"], '
                 'relief="solid", bd=1, font=zfont(self.app, 13), width=58).pack(side="left", fill="x", expand=True, '
                 'ipady=5)\n'
                 '            tk.Button(entry_row, text="Hinzufügen", command=add_child, bg=COLORS["blue"], '
                 'fg="white", bd=0, padx=16, pady=9, font=zfont(self.app, 12, "bold")).pack(side="left", padx=(10, '
                 '0))\n'
                 '            footer2 = tk.Frame(win2, bg=COLORS["bg"])\n'
                 '            footer2.pack(fill="x", padx=18, pady=(0, 14))\n'
                 '            def close_child_popup():\n'
                 '                refresh_subtasks_editor()\n'
                 '                win2.destroy()\n'
                 '            tk.Button(footer2, text="Übernehmen und schließen", command=close_child_popup, '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=18, pady=9, font=zfont(self.app, 12, '
                 '"bold")).pack(side="right")\n'
                 '            tk.Button(footer2, text="Abbrechen", command=win2.destroy, bg=COLORS["line"], '
                 'fg=COLORS["text"], bd=0, padx=18, pady=9, font=zfont(self.app, 12, "bold")).pack(side="right", '
                 'padx=(0, 10))\n'
                 '            refresh_children()\n'
                 '\n'
                 '        def refresh_subtasks_editor():\n'
                 '            for child in sub_list.winfo_children(): child.destroy()\n'
                 '            tk.Label(sub_list, text="Unteraufgaben", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=zfont(self.app, 15, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))\n'
                 '            tk.Label(sub_list, text="Status", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=0, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '            tk.Label(sub_list, text="Unteraufgabe", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=1, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '            tk.Label(sub_list, text="Unter-Unteraufgaben", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=2, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '            tk.Label(sub_list, text="Aktion", bg=COLORS["header"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold"), padx=8, pady=7).grid(row=1, column=3, sticky="nsew", padx=1, '
                 'pady=1)\n'
                 '            sub_list.grid_columnconfigure(1, weight=1)\n'
                 '            row = 2\n'
                 '            for idx, sub in enumerate(subtasks_work):\n'
                 '                sub.setdefault("subtasks", [])\n'
                 '                var = tk.StringVar(value=sub.get("title", "")); status_var = '
                 'tk.BooleanVar(value=sub.get("status") == STATUS_DONE)\n'
                 '                var.trace_add("write", lambda *_args, i=idx, v=var: '
                 'subtasks_work[i].update({"title": v.get()}))\n'
                 '                tk.Checkbutton(sub_list, variable=status_var, command=lambda i=idx, v=status_var: '
                 'subtasks_work[i].update({"status": STATUS_DONE if v.get() else STATUS_OPEN}), bg=COLORS["bg"], '
                 'activebackground=COLORS["bg"]).grid(row=row, column=0, sticky="nsew", pady=4, padx=1)\n'
                 '                tk.Entry(sub_list, textvariable=var, width=52, bg="white", fg=COLORS["text"], '
                 'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=row, column=1, sticky="ew", pady=4, padx=6, '
                 'ipady=4)\n'
                 '                count = len([c for c in sub.get("subtasks", []) or [] if str(c.get("title", '
                 '"")).strip()])\n'
                 '                tk.Button(sub_list, text=f"Unter-Unteraufgaben erstellen ({count})", command=lambda '
                 'i=idx: open_sub_subtask_popup(i), bg=COLORS["blue"], fg="white", bd=0, padx=12, pady=8, '
                 'font=zfont(self.app, 12, "bold")).grid(row=row, column=2, sticky="w", pady=4, padx=6)\n'
                 '                tk.Button(sub_list, text="Löschen", command=lambda i=idx: delete_subtask(i), '
                 'bg=COLORS["red"], fg="white", bd=0, padx=12, pady=8, font=zfont(self.app, 12, "bold")).grid(row=row, '
                 'column=3, sticky="w", pady=4, padx=6)\n'
                 '                row += 1\n'
                 '            add_row = row + 1\n'
                 '            tk.Label(sub_list, text="Neue Unteraufgabe", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=zfont(self.app, 12, "bold")).grid(row=add_row, column=0, columnspan=2, sticky="w", pady=(14, '
                 '4), padx=6)\n'
                 '            tk.Entry(sub_list, textvariable=new_sub_var, width=52, bg="white", fg=COLORS["text"], '
                 'relief="solid", bd=1, font=zfont(self.app, 13)).grid(row=add_row+1, column=1, sticky="ew", pady=(2, '
                 '4), padx=6, ipady=4)\n'
                 '            tk.Button(sub_list, text="Unteraufgabe hinzufügen", command=add_subtask, '
                 'bg=COLORS["blue"], fg="white", bd=0, padx=14, pady=9, font=zfont(self.app, 12, '
                 '"bold")).grid(row=add_row+1, column=2, sticky="w", pady=(2, 4), padx=6)\n'
                 '\n'
                 '        def render_subtasks_editor():\n'
                 '            refresh_subtasks_editor()\n'
                 '\n'
                 '        def add_subtask():\n'
                 '            title = new_sub_var.get().strip()\n'
                 '            if title: subtasks_work.append({"id": '
                 'f"sub_{len(subtasks_work)+1:02d}_{datetime.now().strftime(\'%H%M%S%f\')}", "title": title, "status": '
                 'STATUS_OPEN}); new_sub_var.set(""); render_subtasks_editor()\n'
                 '        def delete_subtask(idx):\n'
                 '            if 0 <= idx < len(subtasks_work): subtasks_work.pop(idx); render_subtasks_editor()\n'
                 '        render_subtasks_editor()\n'
                 '        _popup_bind_mousewheel(win)\n'
                 '        _popup_update_scrollregion()\n'
                 '        if False and not is_new:\n'
                 '            tk.Button(form, text="Aufgabe mit Unteraufgaben in Quartalsabschluss übernehmen", '
                 'command=lambda: self.open_transfer_dialog(task), bg=COLORS["blue"], fg="white", bd=0, padx=12, '
                 'pady=7).grid(row=10, column=1, sticky="w", pady=(10, 4))\n'
                 '        def save_dialog():\n'
                 '            title_value = title_var.get().strip()\n'
                 '            if not title_value: messagebox.showwarning("Jahresabschluss", "Bitte einen Aufgabennamen '
                 'eingeben."); return\n'
                 '            mode = DUE_LABEL_TO_VALUE.get(due_mode_var.get(), DUE_CUTOFF); due_day = None; '
                 'due_workday = None; due_fixed = ""\n'
                 '            try:\n'
                 '                if mode in (DUE_DAY_CAL_MONTH, DUE_DAY_NEXT_MONTH, DUE_DAY_AFTER_CUTOFF): due_day = '
                 'int(due_day_var.get().strip()); assert due_day > 0\n'
                 '                elif mode == DUE_WORKDAY_NEXT: due_workday = int(due_workday_var.get().strip()); '
                 'assert due_workday > 0\n'
                 '                elif mode == DUE_FIXED:\n'
                 '                    fixed_date = parse_date(due_fixed_var.get().strip()); assert fixed_date; '
                 'due_fixed = fixed_date.strftime("%Y-%m-%d")\n'
                 '            except Exception:\n'
                 '                messagebox.showwarning("Jahresabschluss", "Bitte gültige Werte zur Fälligkeit '
                 'eingeben."); return\n'
                 '            owner_label = owner_var.get(); owner_key = user_labels.get(owner_label, ""); owner_text '
                 '= owner_label if owner_key else team\n'
                 '            payload = {"title": title_value, "booking_circle": booking_circle_var.get(), "owner": '
                 'owner_text, "owner_user_key": owner_key, "due_mode": mode, "due_day": due_day, "due_workday": '
                 'due_workday, "due_fixed_date": due_fixed, "deadline_type": deadline_var.get(), "priority": '
                 'priority_var.get(), "recurring": bool(recurring_var.get()), "due_frequency": '
                 'due_frequency_var.get(), "subtasks": [s for s in subtasks_work if s.get("title", "").strip()]}\n'
                 '            payload["due_date"] = resolve_due_date(payload, self.data, self.period)\n'
                 '            if is_new:\n'
                 '                real = {"id": make_task_id(team, self.next_task_index(team)), "team": team, '
                 '"required": True, "status": STATUS_OPEN, "attachments": [], "comments": [], "done_at": None, '
                 '"done_by": None, "catalog_id": "", **payload}; self.data.setdefault("tasks", []).append(real)\n'
                 '            else:\n'
                 '                real = self.find_task(task["id"])\n'
                 '                if not real: return\n'
                 '                real.update(payload)\n'
                 '            sync_parent_status_from_subtasks(real)\n'
                 '            if real.get("recurring"):\n'
                 '                catalog_id = self.upsert_catalog_entry(real); real["catalog_id"] = catalog_id; '
                 'self.propagate_recurring_to_future_periods(catalog_id)\n'
                 '            else:\n'
                 '                if real.get("catalog_id"): self.remove_catalog_entry(real.get("catalog_id"))\n'
                 '                real["catalog_id"] = ""\n'
                 '            self.save(); win.destroy(); self.reload(); self.render_team_detail(team)\n'
                 '        buttons = tk.Frame(win, bg=COLORS["bg"]); buttons.pack(side="bottom", fill="x", pady=(0, '
                 '12), padx=14)\n'
                 '        tk.Button(buttons, text="Speichern", command=save_dialog, bg=COLORS["blue"], fg="white", '
                 'bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", padx=6)\n'
                 '        tk.Button(buttons, text="Abbrechen", command=win.destroy, bg=COLORS["line"], '
                 'fg=COLORS["text"], bd=0, padx=14, pady=8, font=zfont(self.app, 12, "bold")).pack(side="right", '
                 'padx=6)\n'
                 '        _popup_bind_mousewheel(win)\n'
                 '        _popup_update_scrollregion()\n'
                 '\n'
                 '    def delete_task(self, task):\n'
                 '            if not self.require_unlocked("Diese Änderung"): return\n'
                 '            idx = self.find_task_index_exact(task)\n'
                 '            if idx is None:\n'
                 '                messagebox.showerror("Aufgabe löschen", "Die ausgewählte Aufgabe konnte nicht '
                 'eindeutig identifiziert werden. Es wurde nichts gelöscht.")\n'
                 '                return\n'
                 '            real = self.data.get("tasks", [])[idx]\n'
                 '            scope = self.ask_delete_scope(real)\n'
                 '            if not scope:\n'
                 '                return\n'
                 '            task_key = self.task_match_key(real)\n'
                 '            team = real.get("team")\n'
                 '            title = real.get("title", "")\n'
                 '            self.data["tasks"].pop(idx)\n'
                 '            if scope == "following" and real.get("catalog_id"):\n'
                 '                self.remove_catalog_entry(real.get("catalog_id"))\n'
                 '            self.save()\n'
                 '            removed_future = 0\n'
                 '            ambiguous_future = 0\n'
                 '            if scope == "following":\n'
                 '                removed_future, ambiguous_future = self.delete_from_following_periods(task_key)\n'
                 '            info = f"Aufgabe wurde gelöscht:\\n\\n{title}"\n'
                 '            if scope == "following":\n'
                 '                info += f"\\n\\nEntfernt aus Folgezeiträumen: {removed_future}"\n'
                 '                if ambiguous_future:\n'
                 '                    info += f"\\nNicht eindeutig erkannte Folgezeiträume übersprungen: '
                 '{ambiguous_future}"\n'
                 '            messagebox.showinfo("Aufgabe löschen", info)\n'
                 '            self.reload()\n'
                 '            self.render_team_detail(team) if team else self.render_dashboard()\n'
                 '\n'
                 '    def clone_task_for_period(self, task, target_period, index):\n'
                 '        data_stub = {"closing_cutoff_date": default_cutoff_date(target_period)}\n'
                 '        clone = {"id": make_task_id(task.get("team", "Team"), index), "team": task.get("team"), '
                 '"title": task.get("title"), "owner": task.get("owner", task.get("team")), "owner_user_key": '
                 'task.get("owner_user_key", ""), "due_mode": task.get("due_mode", DUE_CUTOFF), "due_day": '
                 'task.get("due_day"), "due_workday": task.get("due_workday"), "due_fixed_date": '
                 'task.get("due_fixed_date", ""), "deadline_type": task.get("deadline_type", "keine"), "priority": '
                 'task.get("priority", "normal"), "required": task.get("required", True), "recurring": '
                 'task.get("recurring", False), "catalog_id": task.get("catalog_id", ""), "status": STATUS_OPEN, '
                 '"attachments": [], "comments": [], "subtasks": [dict(s, status=STATUS_OPEN) for s in '
                 'task.get("subtasks", []) if not s.get("deleted")], "done_at": None, "done_by": None}\n'
                 '        clone["due_date"] = resolve_due_date(clone, data_stub, target_period); return clone\n'
                 '\n'
                 '    def apply_current_tasks_to_all_periods(self):\n'
                 '            if not self.require_unlocked("Zuweisung an Perioden ist nicht möglich"): return\n'
                 '            if not self.can_edit(): return\n'
                 '            if not messagebox.askyesno("Aufgaben übertragen", f"Die Aufgabenstruktur aus '
                 '{period_label(self.period)} wird auf alle vorhandenen Perioden übertragen.\\n\\nStatus, Anlagen, '
                 'Kommentare und Erledigt-Infos werden in den Zielperioden zurückgesetzt.\\n\\nFortfahren?"): return\n'
                 '            source_tasks = [t for t in self.tasks()]\n'
                 '            for target in list_periods():\n'
                 '                grouped_index = {}; cloned = []\n'
                 '                for task in source_tasks:\n'
                 '                    team = task.get("team", "Team"); grouped_index[team] = grouped_index.get(team, '
                 '0) + 1; cloned.append(self.clone_task_for_period(task, target, grouped_index[team]))\n'
                 '                data = load_period(target); data["tasks"] = cloned; data["updated_from_period"] = '
                 'self.period; data["updated_at"] = datetime.now().isoformat(timespec="seconds"); save_period(target, '
                 'data)\n'
                 '            self.reload(); messagebox.showinfo("Aufgaben übertragen", "Die Aufgaben wurden allen '
                 'vorhandenen Perioden zugewiesen."); self.render_team_detail(self.selected_team) if '
                 'self.selected_team else self.render_dashboard()\n'
                 '\n'
                 '    def show_attachments(self, task, parent_task=None):\n'
                 '        self.normalize_documentation_fields(task)\n'
                 '        item_title = task.get("title", "Aufgabe")\n'
                 '        win = tk.Toplevel(self.root)\n'
                 '        win.title(f"Anlagen - {item_title}")\n'
                 '        win.configure(bg=COLORS["bg"])\n'
                 '        win.geometry("860x560")\n'
                 '        win.transient(self.root)\n'
                 '        win.grab_set()\n'
                 '\n'
                 '        tk.Label(win, text=item_title, bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 14, '
                 '"bold")).pack(anchor="w", padx=16, pady=(14, 4))\n'
                 '        tk.Label(win, text="Anlagen dienen zur Hinterlegung ausgearbeiteter Ergebnisse und '
                 'Kommentare zur Bearbeitung. Dokumentationen/Leitfäden bitte in der Spalte Dokumentation pflegen.", '
                 'bg=COLORS["bg"], fg=COLORS["text2"], font=("Segoe UI", 9), wraplength=820, '
                 'justify="left").pack(anchor="w", padx=16, pady=(0, 8))\n'
                 '\n'
                 '        list_frame = tk.Frame(win, bg=COLORS["white"], bd=1, relief="solid")\n'
                 '        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))\n'
                 '        list_frame.grid_columnconfigure(0, weight=1)\n'
                 '        list_frame.grid_columnconfigure(3, weight=2)\n'
                 '\n'
                 '        def refresh():\n'
                 '            for child in list_frame.winfo_children():\n'
                 '                child.destroy()\n'
                 '            self.normalize_documentation_fields(task)\n'
                 '            headers = ["Anlagenpfad", "Öffnen", "Entfernen", "Bemerkung"]\n'
                 '            for c, h in enumerate(headers):\n'
                 '                tk.Label(list_frame, text=h, bg=COLORS["header"], fg=COLORS["text"], font=("Segoe '
                 'UI", 9, "bold"), padx=6, pady=4).grid(row=0, column=c, sticky="nsew")\n'
                 '            if not task.get("attachments"):\n'
                 '                tk.Label(list_frame, text="Noch keine Anlage hinterlegt.", bg=COLORS["white"], '
                 'fg=COLORS["text2"], padx=8, pady=8, anchor="w").grid(row=1, column=0, columnspan=4, sticky="ew")\n'
                 '                return\n'
                 '            for idx, att in enumerate(task.get("attachments", []), start=1):\n'
                 '                tk.Label(list_frame, text=att.get("path", ""), bg=COLORS["white"], '
                 'fg=COLORS["text"], anchor="w", wraplength=330).grid(row=idx, column=0, sticky="ew", padx=6, pady=3)\n'
                 '                tk.Button(list_frame, text="Öffnen", command=lambda p=att.get("path"): '
                 'self.open_attachment(p), bg=COLORS["blue"], fg="white", bd=0).grid(row=idx, column=1, padx=4, '
                 'pady=3)\n'
                 '                tk.Button(list_frame, text="Entfernen", command=lambda a=att: remove_attachment(a), '
                 'bg=COLORS["red"], fg="white", bd=0).grid(row=idx, column=2, padx=4, pady=3)\n'
                 '                tk.Label(list_frame, text=att.get("comment", ""), bg=COLORS["white"], '
                 'fg=COLORS["text2"], anchor="w", justify="left", wraplength=320).grid(row=idx, column=3, sticky="ew", '
                 'padx=6, pady=3)\n'
                 '\n'
                 '        def choose_path():\n'
                 '            selected = filedialog.askopenfilename(title="Anlage auswählen")\n'
                 '            if selected:\n'
                 '                path_var.set(selected)\n'
                 '\n'
                 '        def add_or_update_attachment():\n'
                 '            path = path_var.get().strip()\n'
                 '            if not path or path == placeholder:\n'
                 '                messagebox.showwarning("Anlagen", "Bitte einen Pfad der Anlage wählen oder '
                 'einfügen.")\n'
                 '                return\n'
                 '            self.normalize_documentation_fields(task)\n'
                 '            task.setdefault("attachments", []).append({\n'
                 '                "name": os.path.basename(path) or "Anlage",\n'
                 '                "path": path,\n'
                 '                "comment": comment_box.get("1.0", "end").strip(),\n'
                 '                "added_at": datetime.now().isoformat(timespec="seconds"),\n'
                 '            })\n'
                 '            self.save()\n'
                 '            refresh()\n'
                 '            path_var.set(placeholder)\n'
                 '            comment_box.delete("1.0", "end")\n'
                 '            if self.selected_team:\n'
                 '                self.render_team_detail(self.selected_team)\n'
                 '\n'
                 '        def remove_attachment(att):\n'
                 '            if messagebox.askyesno("Anlage entfernen", f"Anlage entfernen?\\n\\n{att.get(\'name\') '
                 'or att.get(\'path\')}"):\n'
                 '                task["attachments"] = [a for a in task.get("attachments", []) if a != att]\n'
                 '                self.save(); refresh()\n'
                 '                if self.selected_team:\n'
                 '                    self.render_team_detail(self.selected_team)\n'
                 '\n'
                 '        form = tk.Frame(win, bg=COLORS["bg"])\n'
                 '        form.pack(fill="x", padx=16, pady=(0, 14))\n'
                 '        path_var = tk.StringVar()\n'
                 '        placeholder = "Bitte Pfad der Anlage wählen oder einfügen"\n'
                 '        path_var.set(placeholder)\n'
                 '        tk.Label(form, text="Anlagenpfad", bg=COLORS["bg"], fg=COLORS["text"], font=("Segoe UI", 10, '
                 '"bold")).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                 '        tk.Button(form, text="Anlage auswählen", command=choose_path, bg=COLORS["blue"], fg="white", '
                 'bd=0, padx=10, pady=5).grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 6))\n'
                 '        entry = tk.Entry(form, textvariable=path_var, bg=COLORS["white"], fg=COLORS["text2"], '
                 'relief="solid", bd=1, width=70)\n'
                 '        entry.grid(row=0, column=2, sticky="ew", pady=(0, 6))\n'
                 '        form.grid_columnconfigure(2, weight=1)\n'
                 '        def clear_placeholder(_event=None):\n'
                 '            if path_var.get() == placeholder:\n'
                 '                path_var.set("")\n'
                 '                entry.config(fg=COLORS["text"])\n'
                 '        entry.bind("<FocusIn>", clear_placeholder)\n'
                 '\n'
                 '        tk.Label(form, text="Bemerkungen und Informationen:", bg=COLORS["bg"], fg=COLORS["text"], '
                 'font=("Segoe UI", 10, "bold")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 4))\n'
                 '        comment_box = tk.Text(form, height=4, bg=COLORS["white"], fg=COLORS["text"], relief="solid", '
                 'bd=1)\n'
                 '        comment_box.grid(row=2, column=0, columnspan=3, sticky="ew")\n'
                 '        tk.Button(form, text="Übernehmen", command=add_or_update_attachment, bg=COLORS["blue"], '
                 'fg="white", bd=0, padx=16, pady=7).grid(row=3, column=2, sticky="e", pady=(8, 0))\n'
                 '        refresh()\n'
                 '\n'
                 '    def open_attachment(self, path):\n'
                 '        if not path or not os.path.exists(path): messagebox.showwarning("Anlage", "Datei wurde nicht '
                 'gefunden."); return\n'
                 '        try:\n'
                 '            if os.name == "nt": os.startfile(path)\n'
                 '            elif sys.platform == "darwin": subprocess.Popen(["open", path])\n'
                 '            else: subprocess.Popen(["xdg-open", path])\n'
                 '        except Exception as exc: messagebox.showerror("Anlage", str(exc))\n'
                 '\n'
                 '\n'
                 'def render(app):\n'
                 '    YearlyCloseUI(app)\n'}
_MODULE_CACHE = {}


def _module_package_name():
    pkg = globals().get('__package__')
    return pkg or 'bin.tools'


def _load_embedded_module(module_key: str):
    if module_key in _MODULE_CACHE:
        return _MODULE_CACHE[module_key]
    if module_key not in _EMBEDDED_SOURCES:
        raise KeyError(f"Unbekannter Abschlussmodul-Schlüssel: {module_key}")
    full_name = f"{_module_package_name()}._embedded_{module_key}"
    mod = types.ModuleType(full_name)
    mod.__file__ = __file__
    mod.__package__ = _module_package_name()
    mod.__loader__ = globals().get('__loader__')
    sys.modules[full_name] = mod
    exec(compile(_EMBEDDED_SOURCES[module_key], f"<{module_key} embedded in abschlusskalender.py>", 'exec'), mod.__dict__)
    _MODULE_CACHE[module_key] = mod
    return mod


def infer_module_key(app=None):
    tool_id = str(getattr(app, 'current_tool_id', '') or '').lower() if app is not None else ''
    title = str(getattr(app, 'current_tool_title', '') or getattr(app, 'current_title', '') or '').lower() if app is not None else ''
    page = str(getattr(app, 'current_page', '') or '').lower() if app is not None else ''
    blob = f"{tool_id} {title} {page}"
    if 'quarterly_close' in blob or 'quartal' in blob or 'quarter' in blob:
        return 'quarterly_close'
    if 'yearly_close' in blob or 'jahres' in blob or 'yearly' in blob or 'jahr' in blob:
        return 'yearly_close'
    return 'monthly_close'


# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_SQLITE_SHARED_TASK_DB_V0509
# Datum: 2026-07-14
# Zweck:
# - Abschlusskalender-Aufgaben werden zentral in SQLite gespeichert.
# - Mehrere Benutzer greifen auf dieselbe Datenbank unter G:\BUC\FM Anwendung\Fibu_Mate_Doc\Database zu.
# - Bestehende lokale JSON-Aufgaben, insbesondere der aktuelle Stand von Wagnerm, werden beim ersten Laden in SQLite übernommen.
# - JSON-Dateien bleiben nur noch Migrations-/Fallback-Quelle; fuehrend ist SQLite.
# ------------------------------------------------------------------
SQLITE_SHARED_TASK_DB_PATCH_VERSION = "0.509-sqlite-shared-closing-tasks"

import os as _fm509_os
import sqlite3 as _fm509_sqlite3
import threading as _fm509_threading
from pathlib import Path as _fm509_Path

_FM509_SQLITE_LOCK = _fm509_threading.RLock()
_FM509_DB_SCHEMA_VERSION = 1


def _fm509_sqlite_db_path():
    raw = str(_fm509_os.environ.get('FIBUMATE_CLOSING_SQLITE_PATH', '') or '').strip()
    if raw:
        return _fm509_Path(raw)
    return _fm509_Path(r'G:\BUC\FM Anwendung\Fibu_Mate_Doc\Database\abschlusskalender.sqlite3')


def _fm509_fallback_db_path(mod):
    try:
        return mod.BASE_DIR.parent.parent / 'Database' / 'abschlusskalender.sqlite3'
    except Exception:
        return _fm509_Path('abschlusskalender.sqlite3')


def _fm509_effective_db_path(mod):
    path = _fm509_sqlite_db_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        fb = _fm509_fallback_db_path(mod)
        try:
            fb.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return fb


def _fm509_connect(mod):
    con = _fm509_sqlite3.connect(str(_fm509_effective_db_path(mod)), timeout=20, isolation_level=None)
    con.row_factory = _fm509_sqlite3.Row
    try:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('PRAGMA synchronous=NORMAL')
        con.execute('PRAGMA busy_timeout=20000')
        con.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    return con


def _fm509_init_db(mod):
    with _FM509_SQLITE_LOCK:
        con = _fm509_connect(mod)
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS closing_catalogs (
                scope TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS closing_periods (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT '',
                source TEXT DEFAULT 'sqlite',
                PRIMARY KEY(scope, period)
            );
            CREATE TABLE IF NOT EXISTS closing_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT,
                period TEXT,
                timestamp TEXT,
                user_display TEXT,
                user_key TEXT,
                action TEXT,
                task_title TEXT,
                team TEXT,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                details_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_closing_periods_scope_period ON closing_periods(scope, period);
            CREATE INDEX IF NOT EXISTS idx_closing_audit_scope_period ON closing_audit_log(scope, period, timestamp);
            """)
            con.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)', ('schema_version', str(_FM509_DB_SCHEMA_VERSION)))
        finally:
            con.close()


def _fm509_scope(mod):
    return str(getattr(mod, 'CLOSING_SCOPE', '') or '').strip() or 'M'


def _fm509_now(mod):
    try:
        return mod.datetime.now().isoformat(timespec='seconds')
    except Exception:
        from datetime import datetime
        return datetime.now().isoformat(timespec='seconds')


def _fm509_json_loads(mod, text, default=None):
    try:
        return mod.json.loads(text) if text else (default if default is not None else {})
    except Exception:
        return default if default is not None else {}


def _fm509_json_dumps(mod, data):
    return mod.json.dumps(data, ensure_ascii=False, indent=2)


def _fm509_task_key(task):
    if not isinstance(task, dict):
        return ''
    cat = str(task.get('catalog_id') or '').strip()
    if cat:
        return 'catalog|' + cat
    tid = str(task.get('id') or '').strip()
    team = str(task.get('team') or '').strip().casefold()
    title = str(task.get('title') or '').strip().casefold()
    return '|'.join(['task', tid, team, title])


def _fm509_task_has_user_data(task):
    if not isinstance(task, dict):
        return False
    if task.get('status') not in ('', None, 'Offen'):
        return True
    for key in ('owner_user_key','done_at','done_by','documentation'):
        if task.get(key):
            return True
    return bool(task.get('attachments') or task.get('comments') or task.get('subtasks'))


def _fm509_merge_period_data(mod, db_data, local_data):
    if not isinstance(local_data, dict):
        return db_data, False
    if not isinstance(db_data, dict):
        return local_data, True
    changed = False
    db_data.setdefault('tasks', [])
    db_tasks = db_data.get('tasks', []) or []
    by_key = {_fm509_task_key(t): i for i, t in enumerate(db_tasks) if _fm509_task_key(t)}
    for lt in (local_data.get('tasks', []) or []):
        key = _fm509_task_key(lt)
        if not key:
            continue
        if key not in by_key:
            db_tasks.append(lt)
            by_key[key] = len(db_tasks) - 1
            changed = True
        else:
            idx = by_key[key]
            if _fm509_task_has_user_data(lt) and not _fm509_task_has_user_data(db_tasks[idx]):
                db_tasks[idx] = lt
                changed = True
    db_data['tasks'] = db_tasks
    local_members = local_data.get('team_members') or {}
    db_members = db_data.get('team_members') or {}
    try:
        db_has_members = any(db_members.values()) if isinstance(db_members, dict) else False
    except Exception:
        db_has_members = False
    if local_members and not db_has_members:
        db_data['team_members'] = local_members
        changed = True
    for k in ('period','created_at','closing_cutoff_date'):
        if local_data.get(k) and not db_data.get(k):
            db_data[k] = local_data.get(k)
            changed = True
    return db_data, changed


def _fm509_read_json_file(path):
    try:
        if path and path.exists():
            return path.read_text(encoding='utf-8')
    except Exception:
        pass
    return ''


def _fm509_upsert_period(mod, period, data, source='sqlite'):
    _fm509_init_db(mod)
    scope = _fm509_scope(mod)
    with _FM509_SQLITE_LOCK:
        con = _fm509_connect(mod)
        try:
            con.execute('BEGIN IMMEDIATE')
            con.execute('''INSERT INTO closing_periods(scope, period, data_json, updated_at, updated_by, source)
                           VALUES(?,?,?,?,?,?)
                           ON CONFLICT(scope,period) DO UPDATE SET
                           data_json=excluded.data_json, updated_at=excluded.updated_at,
                           updated_by=excluded.updated_by, source=excluded.source''',
                        (scope, period, _fm509_json_dumps(mod, data), _fm509_now(mod), '', source))
            con.execute('COMMIT')
        except Exception:
            try:
                con.execute('ROLLBACK')
            except Exception:
                pass
            raise
        finally:
            con.close()


def _fm509_load_period_from_db(mod, period):
    _fm509_init_db(mod)
    scope = _fm509_scope(mod)
    con = _fm509_connect(mod)
    try:
        row = con.execute('SELECT data_json FROM closing_periods WHERE scope=? AND period=?', (scope, period)).fetchone()
        return _fm509_json_loads(mod, row['data_json'], None) if row else None
    finally:
        con.close()


def _fm509_patch_module_storage(module_key, mod):
    if getattr(mod, '_fm509_sqlite_patch_done', False):
        return mod
    _fm509_init_db(mod)
    orig_period_path = getattr(mod, 'period_path', None)
    orig_load_period = getattr(mod, 'load_period', None)
    orig_load_catalog = getattr(mod, 'load_catalog', None)

    def sqlite_period_path(period):
        return _fm509_effective_db_path(mod).with_name(f"abschlusskalender_{_fm509_scope(mod)}_{period}.sqlite_marker")

    def sqlite_load_catalog():
        _fm509_init_db(mod)
        scope = _fm509_scope(mod)
        con = _fm509_connect(mod)
        try:
            row = con.execute('SELECT data_json FROM closing_catalogs WHERE scope=?', (scope,)).fetchone()
        finally:
            con.close()
        if row:
            return _fm509_json_loads(mod, row['data_json'], {'tasks': []}) or {'tasks': []}
        data = orig_load_catalog() if callable(orig_load_catalog) else {'tasks': []}
        sqlite_save_catalog(data)
        return data

    def sqlite_save_catalog(data):
        _fm509_init_db(mod)
        scope = _fm509_scope(mod)
        with _FM509_SQLITE_LOCK:
            con = _fm509_connect(mod)
            try:
                con.execute('BEGIN IMMEDIATE')
                con.execute('''INSERT INTO closing_catalogs(scope, data_json, updated_at, updated_by)
                               VALUES(?,?,?,?)
                               ON CONFLICT(scope) DO UPDATE SET data_json=excluded.data_json,
                               updated_at=excluded.updated_at, updated_by=excluded.updated_by''',
                            (scope, _fm509_json_dumps(mod, data or {'tasks': []}), _fm509_now(mod), ''))
                con.execute('COMMIT')
            except Exception:
                try:
                    con.execute('ROLLBACK')
                except Exception:
                    pass
                raise
            finally:
                con.close()

    def sqlite_load_period(period):
        data = _fm509_load_period_from_db(mod, period)
        local_data = None
        try:
            local_path = orig_period_path(period) if callable(orig_period_path) else None
            text = _fm509_read_json_file(local_path)
            local_data = _fm509_json_loads(mod, text, None) if text else None
        except Exception:
            local_data = None
        if data is None:
            if local_data is not None:
                data = local_data
            elif callable(orig_load_period):
                data = orig_load_period(period)
            else:
                data = {'period': period, 'tasks': []}
            _fm509_upsert_period(mod, period, data, source='json-migration')
        elif local_data is not None:
            data, changed = _fm509_merge_period_data(mod, data, local_data)
            if changed:
                _fm509_upsert_period(mod, period, data, source='json-merged')
        try:
            data.setdefault('tasks', [])
            if hasattr(mod, 'normalize_team_members'):
                mod.normalize_team_members(data)
            if hasattr(mod, 'normalize_cutoff'):
                mod.normalize_cutoff(data, period)
            for task in data.get('tasks', []):
                if hasattr(mod, 'normalize_task'):
                    mod.normalize_task(task, data, period)
        except Exception:
            pass
        return data

    def sqlite_save_period(period, data):
        try:
            if hasattr(mod, 'normalize_team_members'):
                mod.normalize_team_members(data)
            if hasattr(mod, 'normalize_cutoff'):
                mod.normalize_cutoff(data, period)
            for task in data.get('tasks', []):
                if hasattr(mod, 'normalize_task'):
                    mod.normalize_task(task, data, period)
        except Exception:
            pass
        _fm509_upsert_period(mod, period, data, source='sqlite')

    def sqlite_ensure_storage():
        _fm509_init_db(mod)
        try:
            mod.ATTACH_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def sqlite_ensure_period_window():
        sqlite_ensure_storage()
        try:
            periods = mod.iter_allowed_periods()
        except Exception:
            periods = []
        for p in periods:
            sqlite_load_period(p)
            try:
                mod.apply_catalog_to_period(p)
            except Exception:
                pass

    def sqlite_list_periods():
        try:
            sqlite_ensure_period_window()
        except Exception:
            pass
        allowed = set(mod.iter_allowed_periods()) if hasattr(mod, 'iter_allowed_periods') else set()
        con = _fm509_connect(mod)
        try:
            rows = con.execute('SELECT period FROM closing_periods WHERE scope=? ORDER BY period', (_fm509_scope(mod),)).fetchall()
            values = [r['period'] for r in rows]
        finally:
            con.close()
        if allowed:
            values = [v for v in values if v in allowed]
        return sorted(values or list(allowed))

    mod.period_path = sqlite_period_path
    mod.load_period = sqlite_load_period
    mod.save_period = sqlite_save_period
    mod.load_catalog = sqlite_load_catalog
    mod.save_catalog = sqlite_save_catalog
    mod.ensure_storage = sqlite_ensure_storage
    mod.ensure_period_window = sqlite_ensure_period_window
    mod.list_periods = sqlite_list_periods
    mod.SQLITE_SHARED_TASK_DB_PATCH_VERSION = SQLITE_SHARED_TASK_DB_PATCH_VERSION
    mod.SQLITE_SHARED_TASK_DB_PATH = str(_fm509_effective_db_path(mod))
    mod._fm509_sqlite_patch_done = True
    return mod


# Finale Loader-Uebersteuerung fuer SQLite + bestehende Audit/Layout/Progress-Patches.
def _load_embedded_module(module_key: str):
    if module_key in _MODULE_CACHE:
        return _MODULE_CACHE[module_key]
    if module_key not in _EMBEDDED_SOURCES:
        raise KeyError(f"Unbekannter Abschlussmodul-Schluessel: {module_key}")
    full_name = f"{_module_package_name()}._embedded_{module_key}"
    mod = types.ModuleType(full_name)
    mod.__file__ = __file__
    mod.__package__ = _module_package_name()
    mod.__loader__ = globals().get('__loader__')
    sys.modules[full_name] = mod
    exec(compile(_EMBEDDED_SOURCES[module_key], f"<{module_key} embedded in abschlusskalender.py>", 'exec'), mod.__dict__)
    try:
        _apply_audit_patches(module_key, mod)
    except Exception:
        pass
    try:
        _apply_layout_patches(module_key, mod)
    except Exception:
        pass
    try:
        _apply_progress_controls_patches(module_key, mod)
    except Exception:
        pass
    try:
        _fm509_patch_module_storage(module_key, mod)
    except Exception:
        pass
    _MODULE_CACHE[module_key] = mod
    return mod

def render(app):
    module_key = infer_module_key(app)
    module = _load_embedded_module(module_key)
    if not hasattr(module, 'render'):
        raise RuntimeError(f"Eingebettetes Modul {module_key} besitzt keine render(app)-Funktion")
    return module.render(app)


def render_monthly(app):
    return _load_embedded_module('monthly_close').render(app)


def render_quarterly(app):
    return _load_embedded_module('quarterly_close').render(app)


def render_yearly(app):
    return _load_embedded_module('yearly_close').render(app)


def selftest_static():
    result = {}
    for key, source in _EMBEDDED_SOURCES.items():
        compile(source, f"<{key} selftest>", 'exec')
        result[key] = {
            'compiled': True,
            'has_render': 'def render(app)' in source,
            'subtask_color_bluer': '#EAF4FF' in source,
            'subtask_progress': 'subtask_total' in source and 'units.append(sub)' in source,
            'no_task_pdf_button': 'create_task_id_report(t)' not in source,
            'period_report_e3_e4_only': 'role_rank_value() < 3' in source,
            'source_chars': len(source),
        }
    return result



# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_LIVE_AUDIT_OVERVIEW_V0458
# Datum: 2026-07-13
# Zweck:
# - Live-Audit-Log fuer Monats-, Quartals- und Jahresabschluss.
# - Fachliche Aenderungen werden strukturiert protokolliert.
# - Buttons "Aenderungsprotokoll anzeigen" werden zur "Audit Uebersicht".
# - Die bisherige show_change_log-Aktion oeffnet nun die Audit-Uebersicht.
# - Vorlaeufiger Stand: Basis-Audit, Live-Ansicht, Filter/Suche und CSV-Export.
# ------------------------------------------------------------------
AUDIT_PATCH_VERSION = "0.458-live-audit-overview"


def _audit_safe_deepcopy(mod, value):
    try:
        return mod.json.loads(mod.json.dumps(value, ensure_ascii=False))
    except Exception:
        try:
            import copy
            return copy.deepcopy(value)
        except Exception:
            return value


def _audit_scope_label(mod):
    scope = str(getattr(mod, 'CLOSING_SCOPE', '') or '')
    if scope == 'M':
        return 'Monatsabschluss'
    if scope == 'Q':
        return 'Quartalsabschluss'
    if scope == 'J':
        return 'Jahresabschluss'
    return 'Abschlusskalender'


def _audit_log_path(mod):
    try:
        base = mod.BASE_DIR.parent / 'AuditLog'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'abschlusskalender_audit_log.json'
    except Exception:
        return mod.Path('abschlusskalender_audit_log.json')


def _audit_read_log(mod):
    path = _audit_log_path(mod)
    try:
        if path.exists():
            data = mod.json.loads(path.read_text(encoding='utf-8'))
            entries = data.get('entries', []) if isinstance(data, dict) else []
            return entries if isinstance(entries, list) else []
    except Exception:
        pass
    return []


def _audit_write_log(mod, entries):
    path = _audit_log_path(mod)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + '.tmp')
        payload = {'version': AUDIT_PATCH_VERSION, 'entries': list(entries or [])}
        tmp.write_text(mod.json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
        return True
    except Exception:
        return False


def _audit_user(ui):
    try:
        return ui.current_user_full_name()
    except Exception:
        return getattr(ui.app, 'current_user_display', '') or getattr(ui.app, 'current_user_key', '') or ''


def _audit_task_key(task):
    if not isinstance(task, dict):
        return ''
    return str(task.get('id') or task.get('catalog_id') or (str(task.get('team','')) + '|' + str(task.get('title','')))).strip()


def _audit_task_title(task):
    return str((task or {}).get('title', '') or '')


def _audit_make_entry(mod, ui, action, object_type='period', object_id='', task=None, field='', old='', new='', details=None):
    now = mod.datetime.now().isoformat(timespec='seconds')
    try:
        version = ui.app.version_label_text()
    except Exception:
        version = ''
    return {
        'id': 'AUD' + mod.datetime.now().strftime('%Y%m%d%H%M%S%f'),
        'timestamp': now,
        'user_key': str(getattr(ui.app, 'current_user_key', '') or ''),
        'user_display': _audit_user(ui),
        'module': 'abschlusskalender',
        'calendar_type': _audit_scope_label(mod),
        'period': str(getattr(ui, 'period', '') or ''),
        'period_label': mod.period_label(getattr(ui, 'period', '')) if hasattr(mod, 'period_label') else str(getattr(ui, 'period', '')),
        'object_type': object_type,
        'object_id': str(object_id or ''),
        'task_title': _audit_task_title(task) if task else '',
        'team': str((task or {}).get('team', '') or ''),
        'action': action,
        'field_name': str(field or ''),
        'old_value': '' if old is None else str(old),
        'new_value': '' if new is None else str(new),
        'details_json': details or {},
        'app_version': version,
        'audit_patch_version': AUDIT_PATCH_VERSION,
    }


def _audit_append_entries(mod, ui, entries):
    entries = [e for e in entries if isinstance(e, dict)]
    if not entries:
        return
    try:
        ui.data.setdefault('audit_log', []).extend(entries)
    except Exception:
        pass
    log = _audit_read_log(mod)
    log.extend(entries)
    # Begrenzung gegen unkontrolliertes Wachstum im vorlaeufigen Stand.
    if len(log) > 20000:
        log = log[-20000:]
    _audit_write_log(mod, log)


def _audit_tasks_by_key(data):
    out = {}
    for t in (data or {}).get('tasks', []) or []:
        if isinstance(t, dict):
            out[_audit_task_key(t)] = t
    return out


def _audit_subtasks_by_key(task):
    out = {}
    for s in (task or {}).get('subtasks', []) or []:
        if isinstance(s, dict):
            key = str(s.get('id') or s.get('title') or '')
            out[key] = s
    return out


def _audit_diff_data(mod, ui, before, after):
    entries = []
    before = before or {}
    after = after or {}
    # Periodenstatus / Abschluss / Wiederöffnung
    for field, label in [('closed', 'closed'), ('closing_cutoff_date', 'closing_cutoff_date')]:
        if before.get(field) != after.get(field):
            action = 'period_closed' if field == 'closed' and after.get(field) else 'period_reopened' if field == 'closed' else 'period_field_changed'
            entries.append(_audit_make_entry(mod, ui, action, 'period', getattr(ui, 'period', ''), None, label, before.get(field, ''), after.get(field, '')))
    # close_events Wachstum separat protokollieren
    old_events = before.get('close_events', []) or []
    new_events = after.get('close_events', []) or []
    if len(new_events) > len(old_events):
        for ev in new_events[len(old_events):]:
            entries.append(_audit_make_entry(mod, ui, 'period_event', 'period', getattr(ui, 'period', ''), None, str((ev or {}).get('action', 'event')), '', '', ev))
    b_tasks = _audit_tasks_by_key(before)
    a_tasks = _audit_tasks_by_key(after)
    for key, task in a_tasks.items():
        if key not in b_tasks:
            entries.append(_audit_make_entry(mod, ui, 'task_created', 'task', key, task, '', '', task.get('title',''), {'task': task}))
            continue
        old = b_tasks[key]
        fields = ['status', 'owner', 'owner_user_key', 'due_date', 'due_mode', 'due_day', 'due_workday', 'deadline_type', 'priority', 'recurring', 'title', 'team']
        for f in fields:
            if old.get(f) != task.get(f):
                action = 'status_changed' if f == 'status' else 'field_changed'
                entries.append(_audit_make_entry(mod, ui, action, 'task', key, task, f, old.get(f, ''), task.get(f, '')))
        # attachments/comments
        for arr_name, action_name in [('attachments', 'attachments_changed'), ('comments', 'comments_changed')]:
            o = old.get(arr_name, []) or []
            n = task.get(arr_name, []) or []
            if len(o) != len(n):
                entries.append(_audit_make_entry(mod, ui, action_name, 'task', key, task, arr_name, len(o), len(n)))
        # subtasks
        b_sub = _audit_subtasks_by_key(old)
        a_sub = _audit_subtasks_by_key(task)
        for skey, sub in a_sub.items():
            obj_id = key + '::' + skey
            if skey not in b_sub:
                entries.append(_audit_make_entry(mod, ui, 'subtask_created', 'subtask', obj_id, task, 'title', '', sub.get('title',''), {'subtask': sub}))
                continue
            old_sub = b_sub[skey]
            for f in ['status', 'title', 'owner', 'owner_user_key']:
                if old_sub.get(f) != sub.get(f):
                    action = 'subtask_status_changed' if f == 'status' else 'subtask_field_changed'
                    entries.append(_audit_make_entry(mod, ui, action, 'subtask', obj_id, task, f, old_sub.get(f,''), sub.get(f,''), {'subtask_title': sub.get('title','')}))
        for skey, sub in b_sub.items():
            if skey not in a_sub:
                entries.append(_audit_make_entry(mod, ui, 'subtask_deleted', 'subtask', key + '::' + skey, task, 'title', sub.get('title',''), ''))
    for key, task in b_tasks.items():
        if key not in a_tasks:
            entries.append(_audit_make_entry(mod, ui, 'task_deleted', 'task', key, task, 'title', task.get('title',''), ''))
    return entries


def _audit_filter_entries(entries, period='', user='', action='', search=''):
    period = str(period or '').strip().casefold()
    user = str(user or '').strip().casefold()
    action = str(action or '').strip().casefold()
    search = str(search or '').strip().casefold()
    out = []
    for e in entries:
        if period and period not in str(e.get('period','')).casefold() and period not in str(e.get('period_label','')).casefold():
            continue
        if user and user not in str(e.get('user_display','')).casefold() and user not in str(e.get('user_key','')).casefold():
            continue
        if action and action not in str(e.get('action','')).casefold():
            continue
        if search:
            blob = ' '.join(str(e.get(k,'')) for k in ['calendar_type','period','period_label','task_title','team','action','field_name','old_value','new_value','user_display'])
            if search not in blob.casefold():
                continue
        out.append(e)
    return out


def _audit_export_csv(mod, ui, entries):
    try:
        path = mod.filedialog.asksaveasfilename(title='Audit-Log als CSV exportieren', defaultextension='.csv', filetypes=[('CSV-Dateien', '*.csv'), ('Alle Dateien', '*.*')], initialfile='Abschlusskalender_Audit_' + mod.datetime.now().strftime('%Y_%m_%d') + '.csv')
        if not path:
            return
        import csv
        fields = ['timestamp','user_display','calendar_type','period','task_title','team','action','field_name','old_value','new_value','app_version']
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=';')
            writer.writeheader()
            for e in entries:
                writer.writerow({k: e.get(k,'') for k in fields})
        mod.messagebox.showinfo('Audit Übersicht', 'Audit-CSV wurde erstellt:\n' + path)
    except Exception as exc:
        try:
            mod.messagebox.showerror('Audit Übersicht', 'CSV-Export fehlgeschlagen:\n' + str(exc))
        except Exception:
            pass


def _audit_show_overview(mod, ui):
    win = mod.tk.Toplevel(ui.root)
    win.title('Audit Übersicht - ' + _audit_scope_label(mod))
    win.configure(bg=mod.COLORS['bg'])
    win.geometry('1220x720')
    try:
        win.transient(ui.root)
    except Exception:
        pass
    filter_frame = mod.tk.Frame(win, bg=mod.COLORS['bg'])
    filter_frame.pack(fill='x', padx=12, pady=(12, 6))
    mod.tk.Label(filter_frame, text='Audit Übersicht', bg=mod.COLORS['bg'], fg=mod.COLORS['blue'], font=mod.zfont(ui.app, 15, 'bold')).grid(row=0, column=0, sticky='w', padx=(0, 16))
    period_var = mod.tk.StringVar(value=str(getattr(ui, 'period', '')))
    user_var = mod.tk.StringVar(value='')
    action_var = mod.tk.StringVar(value='')
    search_var = mod.tk.StringVar(value='')
    labels = [('Zeitraum', period_var, 12), ('Benutzer', user_var, 18), ('Aktion', action_var, 18), ('Suche', search_var, 26)]
    for i, (lbl, var, width) in enumerate(labels, start=1):
        box = mod.tk.Frame(filter_frame, bg=mod.COLORS['bg']); box.grid(row=0, column=i, sticky='w', padx=(0, 10))
        mod.tk.Label(box, text=lbl, bg=mod.COLORS['bg'], fg=mod.COLORS['text2'], font=mod.zfont(ui.app, 9)).pack(anchor='w')
        ent = mod.tk.Entry(box, textvariable=var, width=width, bg='white', fg=mod.COLORS['text'], relief='solid', bd=1)
        ent.pack(anchor='w', ipady=3)
    btn_frame = mod.tk.Frame(filter_frame, bg=mod.COLORS['bg']); btn_frame.grid(row=0, column=5, sticky='e')
    table_frame = mod.tk.Frame(win, bg=mod.COLORS['bg'])
    table_frame.pack(fill='both', expand=True, padx=12, pady=(0, 8))
    cols = ('timestamp','calendar','period','user','action','task','field','old','new')
    tree = mod.ttk.Treeview(table_frame, columns=cols, show='headings', height=18)
    headings = {'timestamp':'Zeitpunkt','calendar':'Kalender','period':'Zeitraum','user':'Benutzer','action':'Aktion','task':'Aufgabe','field':'Feld','old':'Alt','new':'Neu'}
    widths = {'timestamp':145,'calendar':130,'period':95,'user':150,'action':160,'task':240,'field':110,'old':160,'new':160}
    for c in cols:
        tree.heading(c, text=headings[c])
        tree.column(c, width=widths[c], stretch=(c in ('task','old','new')))
    ys = mod.ttk.Scrollbar(table_frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=ys.set)
    tree.pack(side='left', fill='both', expand=True)
    ys.pack(side='right', fill='y')
    detail = mod.tk.Text(win, height=7, bg='white', fg=mod.COLORS['text'], relief='solid', bd=1, wrap='word')
    detail.pack(fill='x', padx=12, pady=(0, 12))
    state = {'entries': []}

    def load_filtered():
        entries = _audit_read_log(mod)
        # Auch lokale Periodendaten einbeziehen, falls Netzwerkdatei nicht alles enthaelt.
        try:
            entries += list((ui.data or {}).get('audit_log', []) or [])
        except Exception:
            pass
        # Deduplizieren nach id
        seen = set(); unique = []
        for e in reversed(entries):
            eid = e.get('id') or mod.json.dumps(e, ensure_ascii=False, sort_keys=True)
            if eid in seen:
                continue
            seen.add(eid); unique.append(e)
        unique = list(reversed(unique))
        filtered = _audit_filter_entries(unique, period_var.get(), user_var.get(), action_var.get(), search_var.get())
        return sorted(filtered, key=lambda e: str(e.get('timestamp','')), reverse=True)

    def refresh():
        state['entries'] = load_filtered()
        tree.delete(*tree.get_children())
        for idx, e in enumerate(state['entries'][:2000]):
            tree.insert('', 'end', iid=str(idx), values=(e.get('timestamp',''), e.get('calendar_type',''), e.get('period_label') or e.get('period',''), e.get('user_display',''), e.get('action',''), e.get('task_title',''), e.get('field_name',''), e.get('old_value',''), e.get('new_value','')))
        try:
            detail.delete('1.0', 'end')
            detail.insert('1.0', f"{len(state['entries'])} Audit-Eintraege geladen. Live-Aktualisierung alle 3 Sekunden. Filter wirken auf Zeitraum, Benutzer, Aktion und Freitextsuche.")
        except Exception:
            pass
    def show_detail(event=None):
        sel = tree.selection()
        if not sel:
            return
        try:
            e = state['entries'][int(sel[0])]
        except Exception:
            return
        detail.config(state='normal')
        detail.delete('1.0', 'end')
        lines = [
            f"Zeitpunkt: {e.get('timestamp','')}",
            f"Benutzer: {e.get('user_display','')} ({e.get('user_key','')})",
            f"Kalender: {e.get('calendar_type','')} | Zeitraum: {e.get('period_label') or e.get('period','')}",
            f"Aktion: {e.get('action','')} | Feld: {e.get('field_name','')}",
            f"Aufgabe: {e.get('task_title','')} | Team: {e.get('team','')}",
            f"Alt: {e.get('old_value','')}",
            f"Neu: {e.get('new_value','')}",
            "Details: " + mod.json.dumps(e.get('details_json', {}), ensure_ascii=False)
        ]
        detail.insert('1.0', '\n'.join(lines))
    def live_tick():
        try:
            if win.winfo_exists():
                refresh()
                win.after(3000, live_tick)
        except Exception:
            pass
    tree.bind('<<TreeviewSelect>>', show_detail)
    mod.tk.Button(btn_frame, text='Aktualisieren', command=refresh, bg=mod.COLORS['blue'], fg='white', bd=0, padx=12, pady=5).pack(side='left', padx=(0,6))
    mod.tk.Button(btn_frame, text='CSV Export', command=lambda: _audit_export_csv(mod, ui, state['entries']), bg=mod.COLORS['header'], fg=mod.COLORS['text'], bd=0, padx=12, pady=5).pack(side='left')
    for var in (period_var, user_var, action_var, search_var):
        try:
            var.trace_add('write', lambda *_: refresh())
        except Exception:
            pass
    refresh()
    try:
        win.after(3000, live_tick)
    except Exception:
        pass


def _audit_patch_button_text(mod):
    try:
        if getattr(mod, '_audit_button_patch_done', False):
            return
        orig_init = mod.tk.Button.__init__
        def patched_init(self, master=None, cnf=None, **kw):
            cnf = cnf or {}
            try:
                txt = str(kw.get('text', cnf.get('text', '')) or '')
                if 'Änderungsprotokoll' in txt or 'Aenderungsprotokoll' in txt:
                    if 'text' in kw:
                        kw['text'] = 'Audit Übersicht'
                    else:
                        cnf['text'] = 'Audit Übersicht'
            except Exception:
                pass
            return orig_init(self, master, cnf, **kw)
        mod.tk.Button.__init__ = patched_init
        mod._audit_button_patch_done = True
    except Exception:
        pass


def _audit_patch_ui_class(mod, cls):
    if cls is None or getattr(cls, '_audit_patch_done_v0458', False):
        return
    orig_init = getattr(cls, '__init__', None)
    orig_save = getattr(cls, 'save', None)
    if callable(orig_init):
        def init_wrapper(self, *args, **kwargs):
            orig_init(self, *args, **kwargs)
            try:
                self._audit_snapshot = _audit_safe_deepcopy(mod, getattr(self, 'data', {}))
            except Exception:
                self._audit_snapshot = {}
        cls.__init__ = init_wrapper
    if callable(orig_save):
        def save_wrapper(self, *args, **kwargs):
            before = getattr(self, '_audit_snapshot', None)
            if before is None:
                before = _audit_safe_deepcopy(mod, getattr(self, 'data', {}))
            entries = _audit_diff_data(mod, self, before, getattr(self, 'data', {}))
            if entries:
                _audit_append_entries(mod, self, entries)
            result = orig_save(self, *args, **kwargs)
            try:
                self._audit_snapshot = _audit_safe_deepcopy(mod, getattr(self, 'data', {}))
            except Exception:
                pass
            return result
        cls.save = save_wrapper
    def show_audit_overview(self):
        return _audit_show_overview(mod, self)
    cls.show_audit_overview = show_audit_overview
    cls.show_change_log = show_audit_overview
    cls._audit_patch_done_v0458 = True


def _apply_audit_patches(module_key, mod):
    try:
        _audit_patch_button_text(mod)
        for name in ('MonthlyCloseUI', 'QuarterlyCloseUI', 'YearlyCloseUI'):
            _audit_patch_ui_class(mod, getattr(mod, name, None))
        mod.AUDIT_PATCH_VERSION = AUDIT_PATCH_VERSION
    except Exception:
        pass
    return mod

# Finale Loader-Uebersteuerung fuer Audit-Patch v0.458.
def _load_embedded_module(module_key: str):
    if module_key in _MODULE_CACHE:
        return _MODULE_CACHE[module_key]
    if module_key not in _EMBEDDED_SOURCES:
        raise KeyError(f"Unbekannter Abschlussmodul-Schluessel: {module_key}")
    full_name = f"{_module_package_name()}._embedded_{module_key}"
    mod = types.ModuleType(full_name)
    mod.__file__ = __file__
    mod.__package__ = _module_package_name()
    mod.__loader__ = globals().get('__loader__')
    sys.modules[full_name] = mod
    exec(compile(_EMBEDDED_SOURCES[module_key], f"<{module_key} embedded in abschlusskalender.py>", 'exec'), mod.__dict__)
    _apply_audit_patches(module_key, mod)
    _MODULE_CACHE[module_key] = mod
    return mod




# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_DASHBOARD_LAYOUT_CRITICAL_DEADLINE_V0459
# Datum: 2026-07-13
# Zweck:
# - Team-Kacheln zeigen nur noch die naechste kritische bzw. gesetzliche offene Frist.
# - Gesamt-Fortschrittsbalken und Team-Fortschrittsbalken nutzen die volle verfuegbare Breite der Kachel/Schaltflaeche.
# - Baut auf dem vorlaeufigen Audit-Stand v0.458 auf.
# ------------------------------------------------------------------
DASHBOARD_LAYOUT_PATCH_VERSION = "0.459-critical-deadline-full-progress"


def _layout_patch_full_width_progress(mod, ui, parent, percent, height=24, bg=None):
    bg = bg or parent.cget('bg')
    c = mod.tk.Canvas(parent, height=height, bg=bg, highlightthickness=0)
    def redraw(event=None):
        try:
            width = max(120, int(getattr(event, 'width', 0) or c.winfo_width() or parent.winfo_width() or 420))
            c.delete('all')
            c.configure(width=width, height=height)
            c.create_rectangle(0, 0, width, height, fill='#D6DCE4', outline='#C2CAD5')
            fill_w = int(width * max(0, min(100, int(percent or 0))) / 100)
            if fill_w:
                col = mod.progress_color(int(percent or 0))
                c.create_rectangle(0, 0, fill_w, height, fill=col, outline=col)
            c.create_text(width / 2, height / 2, text=f"{int(percent or 0)}%", fill=mod.COLORS['text'], font=mod.zfont(ui.app, 11, 'bold'))
        except Exception:
            pass
    c.bind('<Configure>', redraw)
    try:
        parent.bind('<Configure>', lambda e: redraw())
        parent.after_idle(redraw)
    except Exception:
        redraw()
    return c


def _layout_patch_ui_class(mod, cls):
    if cls is None or getattr(cls, '_layout_patch_done_v0459', False):
        return

    def draw_progress(self, parent, percent, width=260, height=20, bg=None):
        try:
            parent.pack_configure(fill='x')
        except Exception:
            pass
        return _layout_patch_full_width_progress(mod, self, parent, percent, height=height, bg=bg)

    def next_relevant_task(self, tasks):
        candidates = []
        for t in tasks or []:
            try:
                if t.get('status') == mod.STATUS_DONE:
                    continue
                if bool(t.get('deleted')):
                    continue
                is_critical = str(t.get('priority', '')).casefold() == 'kritisch'
                is_legal = str(t.get('deadline_type', '')).casefold() == 'gesetzlich'
                if not (is_critical or is_legal):
                    continue
                candidates.append(t)
            except Exception:
                pass
        try:
            return sorted(candidates, key=lambda t: mod.parse_date(t.get('due_date', '9999-12-31')) or mod.date.max)[0] if candidates else None
        except Exception:
            return candidates[0] if candidates else None

    def render_team_card(self, parent, team, idx):
        row, col = divmod(idx, 2)
        tasks = self.team_tasks(team)
        stats = mod.calc_stats(tasks)
        warn = max([mod.warning_level(t) for t in tasks], key=lambda x: {'overdue': 4, 'today': 3, 'orange': 2, 'yellow': 1, 'none': 0, 'done': 0}.get(x, 0), default='none')
        border = mod.COLORS['red'] if warn in ('overdue', 'today') else mod.COLORS['orange'] if warn == 'orange' else mod.COLORS['line']
        card = mod.tk.Frame(parent, bg=mod.COLORS['white'], bd=2, relief='solid', highlightbackground=border, highlightcolor=border, highlightthickness=2)
        card.grid(row=row, column=col, padx=12, pady=12, sticky='nsew')
        parent.grid_columnconfigure(col, weight=1)
        parent.grid_rowconfigure(row, weight=1)
        mod.tk.Label(card, text=team, bg=mod.COLORS['white'], fg=mod.COLORS['text'], font=mod.zfont(self.app, 19, 'bold')).pack(anchor='w', padx=18, pady=(16, 4))
        mod.tk.Label(card, text=f"{stats['done']} / {stats['total']} erledigt | offen: {stats['open']} | in Bearbeitung: {stats['in_progress']} | kritisch: {stats['critical']}", bg=mod.COLORS['white'], fg=mod.COLORS['text2'], font=mod.zfont(self.app, 13)).pack(anchor='w', padx=18)
        holder = mod.tk.Frame(card, bg=mod.COLORS['white'])
        holder.pack(fill='x', padx=18, pady=(10, 8))
        self.draw_progress(holder, stats['percent'], width=420, height=26, bg=mod.COLORS['white']).pack(fill='x')
        nxt = self.next_relevant_task(tasks)
        txt = 'Nächste kritische/gesetzliche Frist: keine offene kritische oder gesetzliche Frist' if not nxt else f"Nächste kritische/gesetzliche Frist: {mod.format_date_de(nxt.get('due_date'))} | {nxt.get('title')}"
        fg = mod.COLORS['red'] if nxt and (mod.warning_level(nxt) in ('overdue','today','orange') or str(nxt.get('priority','')).casefold() == 'kritisch' or str(nxt.get('deadline_type','')).casefold() == 'gesetzlich') else mod.COLORS['text2']
        mod.tk.Label(card, text=txt, bg=mod.COLORS['white'], fg=fg, font=mod.zfont(self.app, 12, 'bold')).pack(anchor='w', padx=18, pady=(0, 5))
        self.render_team_members_on_card(card, team)
        self.bind_click_recursive(card, lambda t=team: self.render_team_detail(t))

    cls.draw_progress = draw_progress
    cls.next_relevant_task = next_relevant_task
    cls.render_team_card = render_team_card
    cls._layout_patch_done_v0459 = True


def _apply_layout_patches(module_key, mod):
    try:
        for name in ('MonthlyCloseUI', 'QuarterlyCloseUI', 'YearlyCloseUI'):
            _layout_patch_ui_class(mod, getattr(mod, name, None))
        mod.DASHBOARD_LAYOUT_PATCH_VERSION = DASHBOARD_LAYOUT_PATCH_VERSION
    except Exception:
        pass
    return mod

# Finale Loader-Uebersteuerung fuer Audit + Layout-Patch v0.459.
def _load_embedded_module(module_key: str):
    if module_key in _MODULE_CACHE:
        return _MODULE_CACHE[module_key]
    if module_key not in _EMBEDDED_SOURCES:
        raise KeyError(f"Unbekannter Abschlussmodul-Schluessel: {module_key}")
    full_name = f"{_module_package_name()}._embedded_{module_key}"
    mod = types.ModuleType(full_name)
    mod.__file__ = __file__
    mod.__package__ = _module_package_name()
    mod.__loader__ = globals().get('__loader__')
    sys.modules[full_name] = mod
    exec(compile(_EMBEDDED_SOURCES[module_key], f"<{module_key} embedded in abschlusskalender.py>", 'exec'), mod.__dict__)
    try:
        _apply_audit_patches(module_key, mod)
    except Exception:
        pass
    _apply_layout_patches(module_key, mod)
    _MODULE_CACHE[module_key] = mod
    return mod




# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_PROGRESS_CONTROLS_ROBUST_V0460
# Datum: 2026-07-13
# Zweck:
# - Gesamt-Fortschrittsbalken in der Zeitraum-Uebersicht ueber nahezu volle Kartenbreite ziehen.
# - Team-Fortschrittsbalken bleiben vollbreit.
# - Zeitraum-/Monats-Umschaltflaechen robust in grosser Darstellung halten, auch nach Interaktion.
# - Baut auf v0.459 und Audit v0.458 auf.
# ------------------------------------------------------------------
PROGRESS_CONTROLS_PATCH_VERSION = "0.460-progress-controls-robust"


def _pc_patch_full_width_progress(mod, ui, parent, percent, width=260, height=20, bg=None):
    bg = bg or parent.cget('bg')
    try:
        # Wichtig: falls der Fortschrittsbalken in einem zuvor nur links verankerten Holder steckt,
        # wird der Holder nachtraeglich auf volle Breite gezogen.
        parent.pack_configure(fill='x', expand=True)
    except Exception:
        pass
    # Gesamtbalken wird im Original mit width >= 500 aufgerufen; Team-Balken mit ca. 420.
    is_total_bar = int(width or 0) >= 500
    c = mod.tk.Canvas(parent, height=height, bg=bg, highlightthickness=0, bd=0)
    def target_width(event=None):
        try:
            if is_total_bar:
                root_w = int(ui.canvas.winfo_width() or 0)
                # orientiert sich an der lila Markierung: fast gesamte Inhaltsbreite ab linkem Kartenrand.
                return max(520, root_w - 96)
            current = int(getattr(event, 'width', 0) or parent.winfo_width() or c.winfo_width() or width or 420)
            return max(220, current)
        except Exception:
            return int(width or 420)
    def redraw(event=None):
        try:
            w = target_width(event)
            c.delete('all')
            c.configure(width=w, height=height)
            c.create_rectangle(0, 0, w, height, fill='#D6DCE4', outline='#C2CAD5')
            fill_w = int(w * max(0, min(100, int(percent or 0))) / 100)
            if fill_w:
                col = mod.progress_color(int(percent or 0))
                c.create_rectangle(0, 0, fill_w, height, fill=col, outline=col)
            c.create_text(w / 2, height / 2, text=f"{int(percent or 0)}%", fill=mod.COLORS['text'], font=mod.zfont(ui.app, 11, 'bold'))
        except Exception:
            pass
    c.bind('<Configure>', redraw)
    try:
        parent.bind('<Configure>', lambda e: redraw(e), add='+')
        parent.after_idle(redraw)
    except Exception:
        redraw()
    return c


def _pc_patch_ui_class(mod, cls):
    if cls is None or getattr(cls, '_pc_patch_done_v0460', False):
        return

    def draw_progress(self, parent, percent, width=260, height=20, bg=None):
        return _pc_patch_full_width_progress(mod, self, parent, percent, width=width, height=height, bg=bg)

    def render_period_controls(self, parent):
        row = mod.tk.Frame(parent, bg=mod.COLORS['bg'], height=52)
        row.pack(fill='x', padx=24, pady=(10, 4))
        try:
            row.pack_propagate(False)
        except Exception:
            pass
        btn_font = mod.zfont(self.app, 11)
        nav_bg = mod.COLORS['white']
        def fixed_btn(text, command, width_chars=19):
            b = mod.tk.Button(row, text=text, command=command, bg=nav_bg, fg=mod.COLORS['text'], bd=1, relief='solid', padx=10, pady=8, width=width_chars, height=1, font=btn_font, cursor='hand2')
            b.pack(side='left', padx=(0, 10), pady=(2, 2), ipady=2)
            return b
        fixed_btn('< vorherige(r) Monat', lambda: self.change_period(mod.add_period(self.period, -1)), 19)
        periods = mod.list_periods()
        labels = {mod.period_label(k): k for k in periods}
        selected = mod.tk.StringVar(value=mod.period_label(self.period))
        menu = mod.tk.OptionMenu(row, selected, *labels.keys(), command=lambda label: self.change_period(labels[label]))
        menu.config(bg=nav_bg, fg=mod.COLORS['text'], bd=1, relief='solid', highlightthickness=0, width=12, height=1, font=btn_font, padx=8, pady=7)
        menu.pack(side='left', padx=(0, 10), pady=(2, 2), ipady=2)
        try:
            menu['menu'].configure(font=btn_font)
        except Exception:
            pass
        fixed_btn('nächste(r) Monat >', lambda: self.change_period(mod.add_period(self.period, 1)), 19)
        mod.tk.Frame(row, bg=mod.COLORS['bg']).pack(side='left', fill='x', expand=True)
        if self.can_edit():
            self.render_edit_button(row)
        try:
            self.bind_module_ctrl_mousewheel_guard(row)
        except Exception:
            pass

    # Bewusst nur render_period_controls und draw_progress final uebersteuern.
    # render_team_card aus v0.459 bleibt aktiv, damit nur kritische/gesetzliche Fristen angezeigt werden.
    cls.draw_progress = draw_progress
    cls.render_period_controls = render_period_controls
    cls._pc_patch_done_v0460 = True


def _apply_progress_controls_patches(module_key, mod):
    try:
        for name in ('MonthlyCloseUI', 'QuarterlyCloseUI', 'YearlyCloseUI'):
            _pc_patch_ui_class(mod, getattr(mod, name, None))
        mod.PROGRESS_CONTROLS_PATCH_VERSION = PROGRESS_CONTROLS_PATCH_VERSION
    except Exception:
        pass
    return mod

# Finale Loader-Uebersteuerung fuer Audit + Layout + robuste Progress/Controls-Patches v0.460.
def _load_embedded_module(module_key: str):
    if module_key in _MODULE_CACHE:
        return _MODULE_CACHE[module_key]
    if module_key not in _EMBEDDED_SOURCES:
        raise KeyError(f"Unbekannter Abschlussmodul-Schluessel: {module_key}")
    full_name = f"{_module_package_name()}._embedded_{module_key}"
    mod = types.ModuleType(full_name)
    mod.__file__ = __file__
    mod.__package__ = _module_package_name()
    mod.__loader__ = globals().get('__loader__')
    sys.modules[full_name] = mod
    exec(compile(_EMBEDDED_SOURCES[module_key], f"<{module_key} embedded in abschlusskalender.py>", 'exec'), mod.__dict__)
    try:
        _apply_audit_patches(module_key, mod)
    except Exception:
        pass
    try:
        _apply_layout_patches(module_key, mod)
    except Exception:
        pass
    _apply_progress_controls_patches(module_key, mod)
    _MODULE_CACHE[module_key] = mod
    return mod



# Finale SQLite-Loader-Klammer v0.509: nach allen Audit/Layout/Progress-Overrides anwenden.
_FM509_PREV_LOAD_EMBEDDED_MODULE_FINAL = _load_embedded_module
def _load_embedded_module(module_key: str):
    mod = _FM509_PREV_LOAD_EMBEDDED_MODULE_FINAL(module_key)
    try:
        _fm509_patch_module_storage(module_key, mod)
        _MODULE_CACHE[module_key] = mod
    except Exception:
        pass
    return mod


# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_SQLITE_PERFORMANCE_OWNER_FIX_V0510
# Datum: 2026-07-14
# ------------------------------------------------------------------
SQLITE_PERFORMANCE_OWNER_PATCH_VERSION = "0.510-sqlite-performance-owner-persistence"
_FM510_PERIOD_CACHE = {}
_FM510_CATALOG_CACHE = {}

def _fm510_clone_for_cache(mod, data):
    try: return mod.json.loads(mod.json.dumps(data, ensure_ascii=False))
    except Exception: return data

def _fm510_period_row(mod, period):
    try:
        _fm509_init_db(mod); con = _fm509_connect(mod)
        try: return con.execute('SELECT data_json, updated_at FROM closing_periods WHERE scope=? AND period=?', (_fm509_scope(mod), period)).fetchone()
        finally: con.close()
    except Exception: return None

def _fm510_period_updated_ts(mod, period):
    row = _fm510_period_row(mod, period)
    if not row: return 0
    value = str(row['updated_at'] or '')
    try: return mod.datetime.fromisoformat(value).timestamp()
    except Exception: return float(abs(hash(value)) % 1000000000) if value else 0

def _fm510_normalize_period_data(mod, period, data):
    try:
        data.setdefault('tasks', [])
        if hasattr(mod, 'normalize_team_members'): mod.normalize_team_members(data)
        if hasattr(mod, 'normalize_cutoff'): mod.normalize_cutoff(data, period)
        for task in data.get('tasks', []) or []:
            if hasattr(mod, 'normalize_task'): mod.normalize_task(task, data, period)
    except Exception: pass
    return data

def _fm510_patch_module(module_key, mod):
    if getattr(mod, '_fm510_perf_patch_done', False): return mod
    prev_load_period = getattr(mod, 'load_period', None)
    prev_save_period = getattr(mod, 'save_period', None)
    prev_load_catalog = getattr(mod, 'load_catalog', None)
    prev_save_catalog = getattr(mod, 'save_catalog', None)
    prev_catalog_entry_to_task = getattr(mod, 'catalog_entry_to_task', None)

    def fast_load_catalog():
        scope = _fm509_scope(mod)
        try:
            _fm509_init_db(mod); con = _fm509_connect(mod)
            try: row = con.execute('SELECT data_json, updated_at FROM closing_catalogs WHERE scope=?', (scope,)).fetchone()
            finally: con.close()
            if row:
                sig = row['updated_at']; cached = _FM510_CATALOG_CACHE.get(scope)
                if cached and cached[0] == sig: return _fm510_clone_for_cache(mod, cached[1])
                data = _fm509_json_loads(mod, row['data_json'], {'tasks': []}) or {'tasks': []}
                _FM510_CATALOG_CACHE[scope] = (sig, _fm510_clone_for_cache(mod, data)); return data
        except Exception: pass
        return (prev_load_catalog() if callable(prev_load_catalog) else {'tasks': []}) or {'tasks': []}

    def fast_save_catalog(data):
        result = prev_save_catalog(data) if callable(prev_save_catalog) else None
        try: _FM510_CATALOG_CACHE.pop(_fm509_scope(mod), None)
        except Exception: pass
        return result

    def fast_load_period(period):
        key = (_fm509_scope(mod), period); row = _fm510_period_row(mod, period)
        if row:
            sig = row['updated_at']; cached = _FM510_PERIOD_CACHE.get(key)
            if cached and cached[0] == sig: return _fm510_clone_for_cache(mod, cached[1])
            data = _fm509_json_loads(mod, row['data_json'], {'period': period, 'tasks': []}) or {'period': period, 'tasks': []}
            data = _fm510_normalize_period_data(mod, period, data)
            _FM510_PERIOD_CACHE[key] = (sig, _fm510_clone_for_cache(mod, data)); return data
        data = prev_load_period(period) if callable(prev_load_period) else {'period': period, 'tasks': []}
        row2 = _fm510_period_row(mod, period); sig2 = row2['updated_at'] if row2 else str(_fm509_now(mod))
        _FM510_PERIOD_CACHE[key] = (sig2, _fm510_clone_for_cache(mod, data)); return data

    def fast_save_period(period, data):
        result = prev_save_period(period, data) if callable(prev_save_period) else None
        try:
            row = _fm510_period_row(mod, period); sig = row['updated_at'] if row else str(_fm509_now(mod))
            _FM510_PERIOD_CACHE[(_fm509_scope(mod), period)] = (sig, _fm510_clone_for_cache(mod, data))
        except Exception: pass
        return result

    def fast_ensure_period_window():
        try: _fm509_init_db(mod)
        except Exception: pass

    def fast_list_periods():
        try:
            allowed = list(mod.iter_allowed_periods())
            if allowed: return sorted(allowed)
        except Exception: pass
        try:
            con = _fm509_connect(mod)
            try: return [r['period'] for r in con.execute('SELECT period FROM closing_periods WHERE scope=? ORDER BY period', (_fm509_scope(mod),)).fetchall()]
            finally: con.close()
        except Exception: return []

    def keep_owner_apply_catalog_to_period(period):
        data = fast_load_period(period); catalog = fast_load_catalog(); changed = False; tasks = data.setdefault('tasks', [])
        for entry in catalog.get('tasks', []) or []:
            if not entry.get('recurring', True): continue
            start_period = entry.get('start_period', mod.current_period_key() if hasattr(mod, 'current_period_key') else period)
            if period <= start_period: continue
            catalog_id = entry.get('catalog_id')
            existing = next((t for t in tasks if t.get('catalog_id') == catalog_id and not t.get('deleted')), None)
            if existing:
                keep = {
                    'status': existing.get('status', getattr(mod, 'STATUS_OPEN', 'Offen')),
                    'attachments': existing.get('attachments', []), 'comments': existing.get('comments', []),
                    'subtasks': existing.get('subtasks', []), 'done_at': existing.get('done_at'), 'done_by': existing.get('done_by'),
                    'owner': existing.get('owner', entry.get('owner', entry.get('team'))),
                    'owner_user_key': existing.get('owner_user_key', entry.get('owner_user_key', '')),
                    'documentation': existing.get('documentation', '')}
                idx = len([t for t in tasks if t.get('team') == entry.get('team')]) + 1
                new_task = prev_catalog_entry_to_task(entry, period, idx) if callable(prev_catalog_entry_to_task) else dict(entry)
                existing.update(new_task); existing.update(keep)
                old_sub_by_title = {str(s.get('title','')).strip().casefold(): s for s in (keep.get('subtasks') or []) if isinstance(s, dict)}
                for sub in existing.get('subtasks', []) or []:
                    old = old_sub_by_title.get(str(sub.get('title','')).strip().casefold())
                    if old:
                        sub['owner'] = old.get('owner', sub.get('owner', keep.get('owner','')))
                        sub['owner_user_key'] = old.get('owner_user_key', sub.get('owner_user_key', keep.get('owner_user_key','')))
                        sub['status'] = old.get('status', sub.get('status'))
                changed = True
            else:
                idx = len([t for t in tasks if t.get('team') == entry.get('team')]) + 1
                tasks.append(prev_catalog_entry_to_task(entry, period, idx) if callable(prev_catalog_entry_to_task) else dict(entry)); changed = True
        if changed: fast_save_period(period, data)
        return data

    def sqlite_period_mtime(self):
        try: return _fm510_period_updated_ts(mod, self.period)
        except Exception: return 0

    mod.load_period = fast_load_period; mod.save_period = fast_save_period
    mod.load_catalog = fast_load_catalog; mod.save_catalog = fast_save_catalog
    mod.ensure_period_window = fast_ensure_period_window; mod.list_periods = fast_list_periods
    mod.apply_catalog_to_period = keep_owner_apply_catalog_to_period
    for cls_name in ('MonthlyCloseUI','QuarterlyCloseUI','YearlyCloseUI'):
        cls = getattr(mod, cls_name, None)
        if cls is not None:
            try: cls._period_file_mtime = sqlite_period_mtime
            except Exception: pass
    mod.SQLITE_PERFORMANCE_OWNER_PATCH_VERSION = SQLITE_PERFORMANCE_OWNER_PATCH_VERSION
    mod._fm510_perf_patch_done = True
    return mod

try:
    _FM510_PREV_LOAD_EMBEDDED_MODULE_FINAL = _load_embedded_module
    def _load_embedded_module(module_key: str):
        mod = _FM510_PREV_LOAD_EMBEDDED_MODULE_FINAL(module_key)
        try:
            _fm510_patch_module(module_key, mod)
            _MODULE_CACHE[module_key] = mod
        except Exception: pass
        return mod
except Exception: pass


# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_OWNER_OVERRIDE_PERSISTENCE_V0511
# Datum: 2026-07-14
# Zweck:
# - Zuständigkeitsänderungen bleiben dauerhaft erhalten, auch wenn Katalog/Defaults neu abgeglichen werden.
# - Eigene SQLite-Override-Tabelle je Scope/Periode/Aufgabe.
# - Treffer über catalog_id, id, Team+Titel und Titel-Fallback.
# ------------------------------------------------------------------
OWNER_OVERRIDE_PATCH_VERSION = "0.511-owner-override-persistence"


def _fm511_owner_norm(value):
    return ' '.join(str(value or '').strip().split()).casefold()


def _fm511_owner_keys(task):
    keys = []
    try:
        catalog_id = str(task.get('catalog_id') or '').strip()
        if catalog_id:
            keys.append('catalog|' + catalog_id)
        task_id = str(task.get('id') or '').strip()
        if task_id:
            keys.append('id|' + task_id)
        title = _fm511_owner_norm(task.get('title'))
        team = _fm511_owner_norm(task.get('team'))
        if title and team:
            keys.append('title_team|' + team + '|' + title)
        if title:
            keys.append('title|' + title)
    except Exception:
        pass
    out = []
    for key in keys:
        if key and key not in out:
            out.append(key)
    return out


def _fm511_owner_primary_key(task):
    keys = _fm511_owner_keys(task)
    return keys[0] if keys else ''


def _fm511_sub_override_map(task):
    out = {}
    try:
        for sub in task.get('subtasks', []) or []:
            if not isinstance(sub, dict):
                continue
            keys = []
            sid = str(sub.get('id') or '').strip()
            if sid:
                keys.append('id|' + sid)
            title = _fm511_owner_norm(sub.get('title'))
            if title:
                keys.append('title|' + title)
            for key in keys:
                out[key] = {
                    'owner': sub.get('owner', task.get('owner', '')),
                    'owner_user_key': sub.get('owner_user_key', task.get('owner_user_key', '')),
                    'status': sub.get('status'),
                }
    except Exception:
        pass
    return out


def _fm511_init_owner_override_db(mod):
    try:
        _fm509_init_db(mod)
        con = _fm509_connect(mod)
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS closing_task_owner_overrides (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                task_key TEXT NOT NULL,
                title_norm TEXT,
                team_norm TEXT,
                owner TEXT,
                owner_user_key TEXT,
                sub_overrides_json TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(scope, period, task_key)
            );
            CREATE INDEX IF NOT EXISTS idx_closing_task_owner_overrides_lookup
                ON closing_task_owner_overrides(scope, period, title_norm, team_norm);
            """)
        finally:
            con.close()
    except Exception:
        pass


def _fm511_store_owner_overrides(mod, period, data):
    try:
        _fm511_init_owner_override_db(mod)
        scope = _fm509_scope(mod)
        now = _fm509_now(mod)
        con = _fm509_connect(mod)
        try:
            con.execute('BEGIN IMMEDIATE')
            for task in data.get('tasks', []) or []:
                if not isinstance(task, dict) or task.get('deleted'):
                    continue
                key = _fm511_owner_primary_key(task)
                if not key:
                    continue
                title_norm = _fm511_owner_norm(task.get('title'))
                team_norm = _fm511_owner_norm(task.get('team'))
                sub_json = mod.json.dumps(_fm511_sub_override_map(task), ensure_ascii=False)
                con.execute('''INSERT INTO closing_task_owner_overrides
                    (scope, period, task_key, title_norm, team_norm, owner, owner_user_key, sub_overrides_json, updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(scope, period, task_key) DO UPDATE SET
                    title_norm=excluded.title_norm,
                    team_norm=excluded.team_norm,
                    owner=excluded.owner,
                    owner_user_key=excluded.owner_user_key,
                    sub_overrides_json=excluded.sub_overrides_json,
                    updated_at=excluded.updated_at''',
                    (scope, period, key, title_norm, team_norm, task.get('owner',''), task.get('owner_user_key',''), sub_json, now))
            con.execute('COMMIT')
        except Exception:
            try: con.execute('ROLLBACK')
            except Exception: pass
            raise
        finally:
            con.close()
    except Exception:
        pass


def _fm511_load_owner_overrides(mod, period):
    rows = []
    try:
        _fm511_init_owner_override_db(mod)
        con = _fm509_connect(mod)
        try:
            rows = con.execute('SELECT * FROM closing_task_owner_overrides WHERE scope=? AND period=?', (_fm509_scope(mod), period)).fetchall()
        finally:
            con.close()
    except Exception:
        rows = []
    by_key = {}; by_title_team = {}; by_title = {}
    for row in rows:
        try:
            item = {
                'owner': row['owner'] or '',
                'owner_user_key': row['owner_user_key'] or '',
                'sub_overrides': _fm509_json_loads(mod, row['sub_overrides_json'], {}) or {},
            }
            key = row['task_key']; by_key[key] = item
            tn = row['title_norm'] or ''; team = row['team_norm'] or ''
            if tn and team:
                by_title_team[(team, tn)] = item
            if tn:
                by_title[tn] = item
        except Exception:
            pass
    return by_key, by_title_team, by_title


def _fm511_apply_owner_overrides(mod, period, data):
    changed = False
    try:
        by_key, by_title_team, by_title = _fm511_load_owner_overrides(mod, period)
        if not (by_key or by_title_team or by_title):
            return False
        for task in data.get('tasks', []) or []:
            if not isinstance(task, dict) or task.get('deleted'):
                continue
            override = None
            for key in _fm511_owner_keys(task):
                if key in by_key:
                    override = by_key[key]; break
            if override is None:
                title = _fm511_owner_norm(task.get('title')); team = _fm511_owner_norm(task.get('team'))
                override = by_title_team.get((team, title)) or by_title.get(title)
            if not override:
                continue
            old_state = (task.get('owner',''), task.get('owner_user_key',''))
            if override.get('owner'):
                task['owner'] = override.get('owner')
            task['owner_user_key'] = override.get('owner_user_key','')
            changed = changed or old_state != (task.get('owner',''), task.get('owner_user_key',''))
            sub_overrides = override.get('sub_overrides') or {}
            for sub in task.get('subtasks', []) or []:
                if not isinstance(sub, dict):
                    continue
                candidates = []
                sid = str(sub.get('id') or '').strip()
                if sid: candidates.append('id|' + sid)
                title = _fm511_owner_norm(sub.get('title'))
                if title: candidates.append('title|' + title)
                sub_ov = None
                for c in candidates:
                    if c in sub_overrides:
                        sub_ov = sub_overrides[c]; break
                if sub_ov:
                    old = (sub.get('owner',''), sub.get('owner_user_key',''), sub.get('status'))
                    if sub_ov.get('owner'):
                        sub['owner'] = sub_ov.get('owner')
                    sub['owner_user_key'] = sub_ov.get('owner_user_key','')
                    if sub_ov.get('status'):
                        sub['status'] = sub_ov.get('status')
                    changed = changed or old != (sub.get('owner',''), sub.get('owner_user_key',''), sub.get('status'))
    except Exception:
        pass
    return changed


def _fm511_patch_module_owner_overrides(module_key, mod):
    if getattr(mod, '_fm511_owner_override_patch_done', False):
        return mod
    prev_load_period = getattr(mod, 'load_period', None)
    prev_save_period = getattr(mod, 'save_period', None)
    prev_apply_catalog = getattr(mod, 'apply_catalog_to_period', None)

    def load_period_with_owner_overrides(period):
        data = prev_load_period(period) if callable(prev_load_period) else {'period': period, 'tasks': []}
        if _fm511_apply_owner_overrides(mod, period, data):
            try:
                if callable(prev_save_period):
                    prev_save_period(period, data)
            except Exception:
                pass
        return data

    def save_period_with_owner_overrides(period, data):
        _fm511_store_owner_overrides(mod, period, data)
        return prev_save_period(period, data) if callable(prev_save_period) else None

    def apply_catalog_with_owner_overrides(period):
        data = prev_apply_catalog(period) if callable(prev_apply_catalog) else load_period_with_owner_overrides(period)
        if _fm511_apply_owner_overrides(mod, period, data):
            try:
                save_period_with_owner_overrides(period, data)
            except Exception:
                pass
        return data

    mod.load_period = load_period_with_owner_overrides
    mod.save_period = save_period_with_owner_overrides
    mod.apply_catalog_to_period = apply_catalog_with_owner_overrides
    mod.OWNER_OVERRIDE_PATCH_VERSION = OWNER_OVERRIDE_PATCH_VERSION
    mod._fm511_owner_override_patch_done = True
    return mod

try:
    _FM511_PREV_LOAD_EMBEDDED_MODULE_OWNER = _load_embedded_module
    def _load_embedded_module(module_key: str):
        mod = _FM511_PREV_LOAD_EMBEDDED_MODULE_OWNER(module_key)
        try:
            _fm511_patch_module_owner_overrides(module_key, mod)
            _MODULE_CACHE[module_key] = mod
        except Exception:
            pass
        return mod
except Exception:
    pass


# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_TASK_STATE_PERSISTENCE_V0512
# Datum: 2026-07-14
# Zweck:
# - Saemtliche Nutzer-Aenderungen an Monatsabschluss-Aufgaben dauerhaft in SQLite sichern.
# - Nicht nur Zuständigkeit, sondern kompletter Aufgabenstand wird je Periode/Task als Override gespeichert.
# - Katalog-/Aufgabenpool-Abgleich darf gespeicherte Nutzeränderungen nicht mehr zurücksetzen.
# ------------------------------------------------------------------
TASK_STATE_PERSISTENCE_PATCH_VERSION = "0.512-task-state-persistence"


def _fm512_norm(value):
    return ' '.join(str(value or '').strip().split()).casefold()


def _fm512_task_keys(task):
    keys = []
    try:
        catalog_id = str(task.get('catalog_id') or '').strip()
        if catalog_id:
            keys.append('catalog|' + catalog_id)
        task_id = str(task.get('id') or '').strip()
        if task_id:
            keys.append('id|' + task_id)
        title = _fm512_norm(task.get('title'))
        team = _fm512_norm(task.get('team'))
        if title and team:
            keys.append('title_team|' + team + '|' + title)
        if title:
            keys.append('title|' + title)
    except Exception:
        pass
    out = []
    for key in keys:
        if key and key not in out:
            out.append(key)
    return out


def _fm512_primary_task_key(task):
    keys = _fm512_task_keys(task)
    return keys[0] if keys else ''


def _fm512_clone(mod, value):
    try:
        return mod.json.loads(mod.json.dumps(value, ensure_ascii=False))
    except Exception:
        try:
            import copy
            return copy.deepcopy(value)
        except Exception:
            return value


def _fm512_init_task_state_db(mod):
    try:
        _fm509_init_db(mod)
        con = _fm509_connect(mod)
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS closing_task_user_state (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                task_key TEXT NOT NULL,
                title_norm TEXT,
                team_norm TEXT,
                task_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(scope, period, task_key)
            );
            CREATE INDEX IF NOT EXISTS idx_closing_task_user_state_lookup
                ON closing_task_user_state(scope, period, title_norm, team_norm);
            """)
        finally:
            con.close()
    except Exception:
        pass


def _fm512_store_task_state(mod, period, data):
    try:
        _fm512_init_task_state_db(mod)
        scope = _fm509_scope(mod)
        now = _fm509_now(mod)
        con = _fm509_connect(mod)
        try:
            con.execute('BEGIN IMMEDIATE')
            for task in data.get('tasks', []) or []:
                if not isinstance(task, dict):
                    continue
                key = _fm512_primary_task_key(task)
                if not key:
                    continue
                title_norm = _fm512_norm(task.get('title'))
                team_norm = _fm512_norm(task.get('team'))
                payload = mod.json.dumps(task, ensure_ascii=False, indent=2)
                con.execute('''INSERT INTO closing_task_user_state
                    (scope, period, task_key, title_norm, team_norm, task_json, updated_at)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(scope, period, task_key) DO UPDATE SET
                    title_norm=excluded.title_norm,
                    team_norm=excluded.team_norm,
                    task_json=excluded.task_json,
                    updated_at=excluded.updated_at''',
                    (scope, period, key, title_norm, team_norm, payload, now))
            con.execute('COMMIT')
        except Exception:
            try:
                con.execute('ROLLBACK')
            except Exception:
                pass
            raise
        finally:
            con.close()
    except Exception:
        pass


def _fm512_load_task_state(mod, period):
    rows = []
    try:
        _fm512_init_task_state_db(mod)
        con = _fm509_connect(mod)
        try:
            rows = con.execute('SELECT task_key, title_norm, team_norm, task_json FROM closing_task_user_state WHERE scope=? AND period=?', (_fm509_scope(mod), period)).fetchall()
        finally:
            con.close()
    except Exception:
        rows = []
    by_key = {}
    by_title_team = {}
    by_title = {}
    for row in rows:
        try:
            task = _fm509_json_loads(mod, row['task_json'], None)
            if not isinstance(task, dict):
                continue
            item = _fm512_clone(mod, task)
            key = row['task_key']
            by_key[key] = item
            title_norm = row['title_norm'] or _fm512_norm(item.get('title'))
            team_norm = row['team_norm'] or _fm512_norm(item.get('team'))
            if title_norm and team_norm:
                by_title_team[(team_norm, title_norm)] = item
            if title_norm:
                by_title[title_norm] = item
        except Exception:
            pass
    return by_key, by_title_team, by_title


def _fm512_apply_task_state(mod, period, data):
    changed = False
    try:
        by_key, by_title_team, by_title = _fm512_load_task_state(mod, period)
        if not (by_key or by_title_team or by_title):
            return False
        tasks = data.setdefault('tasks', [])
        matched_ids = set()
        for idx, task in enumerate(list(tasks)):
            if not isinstance(task, dict):
                continue
            override = None
            override_key = None
            for key in _fm512_task_keys(task):
                if key in by_key:
                    override = by_key[key]
                    override_key = key
                    break
            if override is None:
                title = _fm512_norm(task.get('title'))
                team = _fm512_norm(task.get('team'))
                override = by_title_team.get((team, title)) or by_title.get(title)
            if not override:
                continue
            before = mod.json.dumps(task, ensure_ascii=False, sort_keys=True)
            # Vollständiger Nutzerstand gewinnt gegen Katalog-Defaults.
            merged = _fm512_clone(mod, override)
            # Technische Kernfelder absichern, falls alte Overrides unvollständig waren.
            if not merged.get('catalog_id') and task.get('catalog_id'):
                merged['catalog_id'] = task.get('catalog_id')
            if not merged.get('id') and task.get('id'):
                merged['id'] = task.get('id')
            tasks[idx] = merged
            after = mod.json.dumps(merged, ensure_ascii=False, sort_keys=True)
            changed = changed or before != after
            key_for_match = override_key or _fm512_primary_task_key(merged)
            if key_for_match:
                matched_ids.add(key_for_match)
        # Nutzerseitig neu angelegte Aufgaben, die nicht im Katalog existieren, wieder ergänzen.
        existing_keys = set()
        for task in tasks:
            if isinstance(task, dict):
                existing_keys.update(_fm512_task_keys(task))
        for key, task in by_key.items():
            if key not in existing_keys and not task.get('deleted'):
                tasks.append(_fm512_clone(mod, task))
                existing_keys.update(_fm512_task_keys(task))
                changed = True
    except Exception:
        pass
    return changed


def _fm512_patch_module_task_state(module_key, mod):
    if getattr(mod, '_fm512_task_state_patch_done', False):
        return mod
    prev_load_period = getattr(mod, 'load_period', None)
    prev_save_period = getattr(mod, 'save_period', None)
    prev_apply_catalog = getattr(mod, 'apply_catalog_to_period', None)

    def load_period_with_task_state(period):
        data = prev_load_period(period) if callable(prev_load_period) else {'period': period, 'tasks': []}
        if _fm512_apply_task_state(mod, period, data):
            try:
                if callable(prev_save_period):
                    prev_save_period(period, data)
            except Exception:
                pass
        return data

    def save_period_with_task_state(period, data):
        result = prev_save_period(period, data) if callable(prev_save_period) else None
        # Nach dem echten Speichern sichern wir denselben Stand zusätzlich als Nutzer-Override.
        _fm512_store_task_state(mod, period, data)
        return result

    def apply_catalog_with_task_state(period):
        data = prev_apply_catalog(period) if callable(prev_apply_catalog) else load_period_with_task_state(period)
        if _fm512_apply_task_state(mod, period, data):
            try:
                save_period_with_task_state(period, data)
            except Exception:
                pass
        return data

    mod.load_period = load_period_with_task_state
    mod.save_period = save_period_with_task_state
    mod.apply_catalog_to_period = apply_catalog_with_task_state
    mod.TASK_STATE_PERSISTENCE_PATCH_VERSION = TASK_STATE_PERSISTENCE_PATCH_VERSION
    mod._fm512_task_state_patch_done = True
    return mod

try:
    _FM512_PREV_LOAD_EMBEDDED_MODULE_TASK_STATE = _load_embedded_module
    def _load_embedded_module(module_key: str):
        mod = _FM512_PREV_LOAD_EMBEDDED_MODULE_TASK_STATE(module_key)
        try:
            _fm512_patch_module_task_state(module_key, mod)
            _MODULE_CACHE[module_key] = mod
        except Exception:
            pass
        return mod
except Exception:
    pass


# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_CLEAN_SQLITE_ONLY_LIVE_STORAGE_V0513
# Datum: 2026-07-15
# Zweck:
# - Finale Bereinigung Speicherlogik: SQLite ist die einzige fuehrende Datenquelle.
# - Keine JSON-Migration, keine lokalen Fallback-Dateien, keine Override-Tabellenlogik als fuehrender Stand.
# - Live-Stand wird je Scope/Periode vollstaendig in closing_periods.data_json gespeichert.
# - Aufgabenpool wird nur aus closing_catalogs geladen/gespeichert.
# - Katalogabgleich ergaenzt nur fehlende recurring Aufgaben, ueberschreibt aber niemals bestehende Live-Aufgaben.
# ------------------------------------------------------------------
CLEAN_SQLITE_ONLY_PATCH_VERSION = "0.513-clean-sqlite-only-live-storage"
_FM513_PERIOD_CACHE = {}
_FM513_CATALOG_CACHE = {}


def _fm513_db_path(mod):
    raw = str(_fm509_os.environ.get('FIBUMATE_CLOSING_SQLITE_PATH', '') or '').strip()
    if raw:
        return _fm509_Path(raw)
    return _fm509_Path(r'G:\BUC\FM Anwendung\Fibu_Mate_Doc\Database\abschlusskalender.sqlite3')


def _fm513_connect(mod):
    path = _fm513_db_path(mod)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = _fm509_sqlite3.connect(str(path), timeout=30, isolation_level=None)
    con.row_factory = _fm509_sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')
    con.execute('PRAGMA busy_timeout=30000')
    con.execute('PRAGMA foreign_keys=ON')
    return con


def _fm513_init_db(mod):
    with _FM509_SQLITE_LOCK:
        con = _fm513_connect(mod)
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS closing_catalogs (
                scope TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS closing_periods (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                data_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT DEFAULT '',
                source TEXT DEFAULT 'clean-sqlite-live',
                PRIMARY KEY(scope, period)
            );
            CREATE TABLE IF NOT EXISTS closing_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT,
                period TEXT,
                timestamp TEXT,
                user_display TEXT,
                user_key TEXT,
                action TEXT,
                task_title TEXT,
                team TEXT,
                field_name TEXT,
                old_value TEXT,
                new_value TEXT,
                details_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_closing_periods_scope_period ON closing_periods(scope, period);
            CREATE INDEX IF NOT EXISTS idx_closing_audit_scope_period ON closing_audit_log(scope, period, timestamp);
            """)
            con.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)', ('schema_version', '513'))
            con.execute('INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)', ('storage_mode', CLEAN_SQLITE_ONLY_PATCH_VERSION))
        finally:
            con.close()


def _fm513_scope(mod):
    return str(getattr(mod, 'CLOSING_SCOPE', '') or '').strip() or 'M'


def _fm513_now(mod):
    try:
        return mod.datetime.now().isoformat(timespec='seconds')
    except Exception:
        from datetime import datetime
        return datetime.now().isoformat(timespec='seconds')


def _fm513_clone(mod, value):
    try:
        return mod.json.loads(mod.json.dumps(value, ensure_ascii=False))
    except Exception:
        return value


def _fm513_json_dumps(mod, value):
    return mod.json.dumps(value, ensure_ascii=False, indent=2)


def _fm513_json_loads(mod, value, default=None):
    try:
        return mod.json.loads(value) if value else (default if default is not None else {})
    except Exception:
        return default if default is not None else {}


def _fm513_task_match_key(task):
    try:
        catalog_id = str(task.get('catalog_id') or '').strip()
        if catalog_id:
            return 'catalog|' + catalog_id
        task_id = str(task.get('id') or '').strip()
        if task_id:
            return 'id|' + task_id
        title = ' '.join(str(task.get('title') or '').split()).casefold()
        team = ' '.join(str(task.get('team') or '').split()).casefold()
        return 'title_team|' + team + '|' + title
    except Exception:
        return ''


def _fm513_empty_period_data(mod, period):
    # Keine Datei-Migration. Nur Programm-Defaults als initialer frischer Live-Stand.
    data = {'period': period, 'created_at': _fm513_now(mod), 'tasks': [], 'team_members': {}}
    try:
        data['closing_cutoff_date'] = mod.default_cutoff_date(period)
    except Exception:
        pass
    try:
        defaults = mod.default_tasks(period)
        if isinstance(defaults, list):
            data['tasks'] = defaults
    except Exception:
        data['tasks'] = []
    try:
        if hasattr(mod, 'normalize_team_members'):
            mod.normalize_team_members(data)
        if hasattr(mod, 'normalize_cutoff'):
            mod.normalize_cutoff(data, period)
        for task in data.get('tasks', []) or []:
            if hasattr(mod, 'normalize_task'):
                mod.normalize_task(task, data, period)
    except Exception:
        pass
    return data


def _fm513_normalize_period(mod, period, data):
    if not isinstance(data, dict):
        data = {'period': period, 'tasks': []}
    data.setdefault('period', period)
    data.setdefault('tasks', [])
    try:
        if hasattr(mod, 'normalize_team_members'):
            mod.normalize_team_members(data)
        if hasattr(mod, 'normalize_cutoff'):
            mod.normalize_cutoff(data, period)
        for task in data.get('tasks', []) or []:
            if hasattr(mod, 'normalize_task'):
                mod.normalize_task(task, data, period)
    except Exception:
        pass
    return data


def _fm513_upsert_period(mod, period, data, source='clean-sqlite-live'):
    _fm513_init_db(mod)
    scope = _fm513_scope(mod)
    data = _fm513_normalize_period(mod, period, data)
    payload = _fm513_json_dumps(mod, data)
    now = _fm513_now(mod)
    with _FM509_SQLITE_LOCK:
        con = _fm513_connect(mod)
        try:
            con.execute('BEGIN IMMEDIATE')
            con.execute('''INSERT INTO closing_periods(scope, period, data_json, updated_at, updated_by, source)
                           VALUES(?,?,?,?,?,?)
                           ON CONFLICT(scope,period) DO UPDATE SET
                           data_json=excluded.data_json,
                           updated_at=excluded.updated_at,
                           updated_by=excluded.updated_by,
                           source=excluded.source''',
                        (scope, period, payload, now, '', source))
            con.execute('COMMIT')
            _FM513_PERIOD_CACHE[(scope, period)] = (now, _fm513_clone(mod, data))
        except Exception:
            try:
                con.execute('ROLLBACK')
            except Exception:
                pass
            raise
        finally:
            con.close()


def _fm513_db_period_row(mod, period):
    _fm513_init_db(mod)
    con = _fm513_connect(mod)
    try:
        return con.execute('SELECT data_json, updated_at FROM closing_periods WHERE scope=? AND period=?', (_fm513_scope(mod), period)).fetchone()
    finally:
        con.close()


def _fm513_patch_module(module_key, mod):
    if getattr(mod, '_fm513_clean_sqlite_only_patch_done', False):
        return mod
    old_catalog_entry_to_task = getattr(mod, 'catalog_entry_to_task', None)

    def clean_load_catalog():
        _fm513_init_db(mod)
        scope = _fm513_scope(mod)
        con = _fm513_connect(mod)
        try:
            row = con.execute('SELECT data_json, updated_at FROM closing_catalogs WHERE scope=?', (scope,)).fetchone()
        finally:
            con.close()
        if row:
            sig = row['updated_at']
            cached = _FM513_CATALOG_CACHE.get(scope)
            if cached and cached[0] == sig:
                return _fm513_clone(mod, cached[1])
            data = _fm513_json_loads(mod, row['data_json'], {'tasks': []}) or {'tasks': []}
            data.setdefault('tasks', [])
            _FM513_CATALOG_CACHE[scope] = (sig, _fm513_clone(mod, data))
            return data
        data = {'tasks': []}
        clean_save_catalog(data)
        return data

    def clean_save_catalog(data):
        _fm513_init_db(mod)
        scope = _fm513_scope(mod)
        data = data if isinstance(data, dict) else {'tasks': []}
        data.setdefault('tasks', [])
        now = _fm513_now(mod)
        with _FM509_SQLITE_LOCK:
            con = _fm513_connect(mod)
            try:
                con.execute('BEGIN IMMEDIATE')
                con.execute('''INSERT INTO closing_catalogs(scope, data_json, updated_at, updated_by)
                               VALUES(?,?,?,?)
                               ON CONFLICT(scope) DO UPDATE SET
                               data_json=excluded.data_json,
                               updated_at=excluded.updated_at,
                               updated_by=excluded.updated_by''',
                            (scope, _fm513_json_dumps(mod, data), now, ''))
                con.execute('COMMIT')
                _FM513_CATALOG_CACHE[scope] = (now, _fm513_clone(mod, data))
            except Exception:
                try:
                    con.execute('ROLLBACK')
                except Exception:
                    pass
                raise
            finally:
                con.close()

    def clean_load_period(period):
        scope = _fm513_scope(mod)
        row = _fm513_db_period_row(mod, period)
        if row:
            sig = row['updated_at']
            cached = _FM513_PERIOD_CACHE.get((scope, period))
            if cached and cached[0] == sig:
                return _fm513_clone(mod, cached[1])
            data = _fm513_json_loads(mod, row['data_json'], {'period': period, 'tasks': []})
            data = _fm513_normalize_period(mod, period, data)
            _FM513_PERIOD_CACHE[(scope, period)] = (sig, _fm513_clone(mod, data))
            return data
        data = _fm513_empty_period_data(mod, period)
        _fm513_upsert_period(mod, period, data, source='initial-clean-sqlite-live')
        return data

    def clean_save_period(period, data):
        _fm513_upsert_period(mod, period, data, source='clean-sqlite-live')

    def clean_ensure_storage():
        _fm513_init_db(mod)
        try:
            if hasattr(mod, 'ATTACH_DIR'):
                mod.ATTACH_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def clean_ensure_period_window():
        # Keine Vorab-Migration und kein Voll-Laden aller Perioden.
        _fm513_init_db(mod)

    def clean_list_periods():
        try:
            allowed = list(mod.iter_allowed_periods()) if hasattr(mod, 'iter_allowed_periods') else []
        except Exception:
            allowed = []
        try:
            _fm513_init_db(mod)
            con = _fm513_connect(mod)
            try:
                rows = con.execute('SELECT period FROM closing_periods WHERE scope=? ORDER BY period', (_fm513_scope(mod),)).fetchall()
                db_periods = [r['period'] for r in rows]
            finally:
                con.close()
        except Exception:
            db_periods = []
        out = []
        for p in (allowed + db_periods):
            if p not in out:
                out.append(p)
        return sorted(out)

    def clean_apply_catalog_to_period(period):
        # Katalog darf nur fehlende recurring Aufgaben ergaenzen, nie vorhandene Live-Aufgaben ueberschreiben.
        data = clean_load_period(period)
        catalog = clean_load_catalog()
        tasks = data.setdefault('tasks', [])
        existing_keys = set(_fm513_task_match_key(t) for t in tasks if isinstance(t, dict) and not t.get('deleted'))
        changed = False
        for entry in catalog.get('tasks', []) or []:
            if not isinstance(entry, dict) or not entry.get('recurring', True):
                continue
            try:
                start_period = entry.get('start_period', mod.current_period_key() if hasattr(mod, 'current_period_key') else period)
                if period <= start_period:
                    continue
            except Exception:
                pass
            key = _fm513_task_match_key(entry)
            if key and key in existing_keys:
                continue
            try:
                team = entry.get('team')
                idx = len([t for t in tasks if t.get('team') == team]) + 1
                new_task = old_catalog_entry_to_task(entry, period, idx) if callable(old_catalog_entry_to_task) else dict(entry)
                tasks.append(new_task)
                existing_keys.add(_fm513_task_match_key(new_task))
                changed = True
            except Exception:
                pass
        if changed:
            clean_save_period(period, data)
        return data

    def clean_period_path(period):
        # Kompatibilitaet fuer Alt-Code: keine Speicherfunktion mehr.
        return _fm513_db_path(mod).with_name(f"abschlusskalender_{_fm513_scope(mod)}_{period}.sqlite_only")

    def clean_period_mtime(self):
        try:
            row = _fm513_db_period_row(mod, self.period)
            value = str(row['updated_at'] or '') if row else ''
            if value:
                return mod.datetime.fromisoformat(value).timestamp()
        except Exception:
            try:
                return float(abs(hash(value)) % 1000000000)
            except Exception:
                pass
        return 0

    mod.load_catalog = clean_load_catalog
    mod.save_catalog = clean_save_catalog
    mod.load_period = clean_load_period
    mod.save_period = clean_save_period
    mod.ensure_storage = clean_ensure_storage
    mod.ensure_period_window = clean_ensure_period_window
    mod.list_periods = clean_list_periods
    mod.apply_catalog_to_period = clean_apply_catalog_to_period
    mod.period_path = clean_period_path
    mod.CLEAN_SQLITE_ONLY_PATCH_VERSION = CLEAN_SQLITE_ONLY_PATCH_VERSION
    mod.SQLITE_SHARED_TASK_DB_PATH = str(_fm513_db_path(mod))
    for cls_name in ('MonthlyCloseUI', 'QuarterlyCloseUI', 'YearlyCloseUI'):
        cls = getattr(mod, cls_name, None)
        if cls is not None:
            try:
                cls._period_file_mtime = clean_period_mtime
            except Exception:
                pass
    mod._fm513_clean_sqlite_only_patch_done = True
    return mod

try:
    _FM513_PREV_LOAD_EMBEDDED_MODULE_CLEAN_SQLITE = _load_embedded_module
    def _load_embedded_module(module_key: str):
        mod = _FM513_PREV_LOAD_EMBEDDED_MODULE_CLEAN_SQLITE(module_key)
        try:
            _fm513_patch_module(module_key, mod)
            _MODULE_CACHE[module_key] = mod
        except Exception:
            pass
        return mod
except Exception:
    pass



# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_RELATIONAL_SHARED_SQLITE_V0514
# Eine zentrale SQLite auf G:, keine JSON-/Fallback-/Default-Aufgaben.
# Aufgaben werden einzeln mit Revision gespeichert; DELETE-Journal statt WAL.
# ------------------------------------------------------------------
RELATIONAL_SHARED_SQLITE_PATCH_VERSION = "0.514-relational-shared-sqlite"

import uuid as _fm514_uuid
import copy as _fm514_copy

class ClosingStorageConflictError(RuntimeError):
    pass


def _fm514_db_path():
    # Absichtlich kein Environment-/Lokalfallback: genau eine gemeinsame Live-Datenbank.
    return _fm509_Path(r"G:\BUC\FM Anwendung\Fibu_Mate_Doc\Database\abschlusskalender.sqlite3")


def _fm514_connect():
    path = _fm514_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = _fm509_sqlite3.connect(str(path), timeout=30, isolation_level=None)
    con.row_factory = _fm509_sqlite3.Row
    con.execute("PRAGMA journal_mode=DELETE")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA busy_timeout=30000")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA locking_mode=NORMAL")
    return con


def _fm514_init_db():
    with _FM509_SQLITE_LOCK:
        con = _fm514_connect()
        try:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS closing_live_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS closing_live_periods (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                revision INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL DEFAULT '',
                PRIMARY KEY(scope, period)
            );
            CREATE TABLE IF NOT EXISTS closing_live_tasks (
                task_pk TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                task_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                revision INTEGER NOT NULL DEFAULT 1,
                deleted INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL DEFAULT '',
                UNIQUE(scope, period, task_id),
                FOREIGN KEY(scope, period) REFERENCES closing_live_periods(scope, period) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS closing_live_catalogs (
                scope TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL DEFAULT '{"tasks": []}',
                revision INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS closing_live_audit (
                revision INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                period TEXT NOT NULL DEFAULT '',
                task_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                old_json TEXT NOT NULL DEFAULT '',
                new_json TEXT NOT NULL DEFAULT '',
                changed_at TEXT NOT NULL,
                changed_by TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS closing_live_locks (
                scope TEXT NOT NULL,
                period TEXT NOT NULL,
                task_id TEXT NOT NULL,
                locked_by TEXT NOT NULL,
                locked_at TEXT NOT NULL,
                heartbeat_at TEXT NOT NULL,
                PRIMARY KEY(scope, period, task_id)
            );
            CREATE INDEX IF NOT EXISTS idx_closing_live_tasks_period
                ON closing_live_tasks(scope, period, deleted, updated_at);
            CREATE INDEX IF NOT EXISTS idx_closing_live_audit_period
                ON closing_live_audit(scope, period, revision);
            """)
            con.execute("INSERT OR REPLACE INTO closing_live_meta(key,value) VALUES('schema_version','514')")
            con.execute("INSERT OR REPLACE INTO closing_live_meta(key,value) VALUES('storage_mode',?)", (RELATIONAL_SHARED_SQLITE_PATCH_VERSION,))
        finally:
            con.close()


def _fm514_now(mod):
    return mod.datetime.now().isoformat(timespec='microseconds')


def _fm514_user(mod):
    return str(getattr(mod, '_fm514_current_user_key', '') or '')


def _fm514_scope(mod):
    return str(getattr(mod, 'CLOSING_SCOPE', '') or 'M')


def _fm514_dumps(mod, value):
    return mod.json.dumps(value, ensure_ascii=False, sort_keys=True)


def _fm514_loads(mod, value, default):
    try:
        out = mod.json.loads(value) if value else _fm514_copy.deepcopy(default)
        return out
    except Exception:
        return _fm514_copy.deepcopy(default)


def _fm514_public_task(task):
    return {k: _fm514_copy.deepcopy(v) for k, v in dict(task or {}).items() if not str(k).startswith('_fm514_')}


def _fm514_task_id(task):
    value = str((task or {}).get('id') or '').strip()
    if not value:
        value = 'task_' + _fm514_uuid.uuid4().hex
        task['id'] = value
    return value


def _fm514_period_payload(data):
    hidden = {'tasks', '_fm514_task_revisions', '_fm514_task_baseline', '_fm514_loaded_task_ids',
              '_fm514_period_revision', '_fm514_period_baseline'}
    return {k: _fm514_copy.deepcopy(v) for k, v in dict(data or {}).items() if k not in hidden and not str(k).startswith('_fm514_')}


def _fm514_ensure_period(con, mod, period):
    scope = _fm514_scope(mod)
    row = con.execute("SELECT revision,payload_json FROM closing_live_periods WHERE scope=? AND period=?", (scope, period)).fetchone()
    if row:
        return row
    now = _fm514_now(mod)
    # Wirklich leerer Start: keine default_tasks() und keine JSON-Migration.
    payload = {'period': period, 'created_at': now, 'team_members': {}}
    try:
        payload['closing_cutoff_date'] = mod.default_cutoff_date(period)
    except Exception:
        pass
    con.execute("INSERT INTO closing_live_periods(scope,period,payload_json,revision,updated_at,updated_by) VALUES(?,?,?,1,?,?)",
                (scope, period, _fm514_dumps(mod,payload), now, _fm514_user(mod)))
    con.execute("INSERT INTO closing_live_audit(scope,period,action,new_json,changed_at,changed_by) VALUES(?,?,?,?,?,?)",
                (scope, period, 'period_created', _fm514_dumps(mod,payload), now, _fm514_user(mod)))
    return con.execute("SELECT revision,payload_json FROM closing_live_periods WHERE scope=? AND period=?", (scope, period)).fetchone()


def _fm514_load_period(mod, period):
    _fm514_init_db()
    scope = _fm514_scope(mod)
    con = _fm514_connect()
    try:
        con.execute('BEGIN')
        prow = _fm514_ensure_period(con, mod, period)
        rows = con.execute("SELECT task_id,payload_json,revision FROM closing_live_tasks WHERE scope=? AND period=? AND deleted=0 ORDER BY task_id", (scope,period)).fetchall()
        con.execute('COMMIT')
    except Exception:
        try: con.execute('ROLLBACK')
        except Exception: pass
        raise
    finally:
        con.close()
    data = _fm514_loads(mod, prow['payload_json'], {'period':period})
    data.setdefault('period', period)
    data.setdefault('team_members', {})
    tasks=[]; revs={}; baseline={}
    for row in rows:
        task=_fm514_loads(mod,row['payload_json'],{})
        task['id']=row['task_id']
        try:
            mod.normalize_task(task,data,period)
        except Exception:
            pass
        tasks.append(task); revs[row['task_id']]=int(row['revision']); baseline[row['task_id']]=_fm514_dumps(mod,_fm514_public_task(task))
    data['tasks']=tasks
    data['_fm514_task_revisions']=revs
    data['_fm514_task_baseline']=baseline
    data['_fm514_loaded_task_ids']=list(revs)
    data['_fm514_period_revision']=int(prow['revision'])
    data['_fm514_period_baseline']=_fm514_dumps(mod,_fm514_period_payload(data))
    return data


def _fm514_save_period(mod, period, data):
    _fm514_init_db()
    scope=_fm514_scope(mod); now=_fm514_now(mod); user=_fm514_user(mod)
    incoming_tasks=[t for t in data.get('tasks',[]) if isinstance(t,dict) and not t.get('deleted')]
    base_revs=dict(data.get('_fm514_task_revisions') or {})
    base_payloads=dict(data.get('_fm514_task_baseline') or {})
    loaded_ids=set(data.get('_fm514_loaded_task_ids') or base_revs.keys())
    conflicts=[]
    con=_fm514_connect()
    try:
        con.execute('BEGIN IMMEDIATE')
        prow=_fm514_ensure_period(con,mod,period)
        # Perioden-Metadaten nur bei eigener Änderung aktualisieren.
        meta=_fm514_period_payload(data); meta_json=_fm514_dumps(mod,meta)
        if meta_json != str(data.get('_fm514_period_baseline') or ''):
            expected=int(data.get('_fm514_period_revision') or prow['revision'])
            cur=con.execute("UPDATE closing_live_periods SET payload_json=?,revision=revision+1,updated_at=?,updated_by=? WHERE scope=? AND period=? AND revision=?",
                            (meta_json,now,user,scope,period,expected))
            if cur.rowcount != 1: conflicts.append('Periodenkopfdaten')
        incoming_ids=set()
        for task in incoming_tasks:
            tid=_fm514_task_id(task); incoming_ids.add(tid)
            public=_fm514_public_task(task); payload=_fm514_dumps(mod,public)
            if tid in base_payloads and payload == base_payloads[tid]:
                continue  # unverändert: niemals fremde Änderung überschreiben
            row=con.execute("SELECT payload_json,revision FROM closing_live_tasks WHERE scope=? AND period=? AND task_id=? AND deleted=0",(scope,period,tid)).fetchone()
            if row is None:
                task_pk=_fm514_uuid.uuid4().hex
                con.execute("INSERT INTO closing_live_tasks(task_pk,scope,period,task_id,payload_json,revision,deleted,updated_at,updated_by) VALUES(?,?,?,?,?,1,0,?,?)",
                            (task_pk,scope,period,tid,payload,now,user))
                con.execute("INSERT INTO closing_live_audit(scope,period,task_id,action,new_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",
                            (scope,period,tid,'task_created',payload,now,user))
            else:
                expected=int(base_revs.get(tid,-1))
                cur=con.execute("UPDATE closing_live_tasks SET payload_json=?,revision=revision+1,updated_at=?,updated_by=? WHERE scope=? AND period=? AND task_id=? AND revision=? AND deleted=0",
                                (payload,now,user,scope,period,tid,expected))
                if cur.rowcount != 1:
                    conflicts.append(str(public.get('title') or tid)); continue
                con.execute("INSERT INTO closing_live_audit(scope,period,task_id,action,old_json,new_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?,?)",
                            (scope,period,tid,'task_updated',row['payload_json'],payload,now,user))
        # Echte Löschungen, ebenfalls revisionsgeschützt.
        for tid in loaded_ids-incoming_ids:
            expected=int(base_revs.get(tid,-1))
            row=con.execute("SELECT payload_json FROM closing_live_tasks WHERE scope=? AND period=? AND task_id=? AND revision=? AND deleted=0",(scope,period,tid,expected)).fetchone()
            if not row:
                conflicts.append(tid); continue
            con.execute("UPDATE closing_live_tasks SET deleted=1,revision=revision+1,updated_at=?,updated_by=? WHERE scope=? AND period=? AND task_id=? AND revision=?",
                        (now,user,scope,period,tid,expected))
            con.execute("INSERT INTO closing_live_audit(scope,period,task_id,action,old_json,changed_at,changed_by) VALUES(?,?,?,?,?,?,?)",
                        (scope,period,tid,'task_deleted',row['payload_json'],now,user))
        if conflicts:
            con.execute('ROLLBACK')
            raise ClosingStorageConflictError('Zwischenzeitlich geänderte Datensätze: ' + ', '.join(conflicts))
        con.execute('COMMIT')
    except Exception:
        try: con.execute('ROLLBACK')
        except Exception: pass
        raise
    finally:
        con.close()
    fresh=_fm514_load_period(mod,period)
    data.clear(); data.update(fresh)
    return data


def _fm514_period_revision(mod,period):
    try:
        _fm514_init_db(); con=_fm514_connect()
        try:
            row=con.execute("SELECT COALESCE(MAX(revision),0) r FROM closing_live_tasks WHERE scope=? AND period=?",(_fm514_scope(mod),period)).fetchone()
            prow=con.execute("SELECT revision FROM closing_live_periods WHERE scope=? AND period=?",(_fm514_scope(mod),period)).fetchone()
            return float((int(prow['revision']) if prow else 0)*1000000000 + int(row['r'] or 0))
        finally: con.close()
    except Exception:
        return 0.0


def _fm514_load_catalog(mod):
    _fm514_init_db(); scope=_fm514_scope(mod); con=_fm514_connect()
    try:
        row=con.execute("SELECT payload_json,revision FROM closing_live_catalogs WHERE scope=?",(scope,)).fetchone()
        if not row: return {'tasks':[], '_fm514_catalog_revision':0}
        data=_fm514_loads(mod,row['payload_json'],{'tasks':[]}); data.setdefault('tasks',[]); data['_fm514_catalog_revision']=int(row['revision']); return data
    finally: con.close()


def _fm514_save_catalog(mod,data):
    _fm514_init_db(); scope=_fm514_scope(mod); now=_fm514_now(mod); user=_fm514_user(mod)
    clean={k:_fm514_copy.deepcopy(v) for k,v in dict(data or {}).items() if not str(k).startswith('_fm514_')}; clean.setdefault('tasks',[])
    con=_fm514_connect()
    try:
        con.execute('BEGIN IMMEDIATE')
        current=con.execute("SELECT revision FROM closing_live_catalogs WHERE scope=?",(scope,)).fetchone()
        expected=int(data.get('_fm514_catalog_revision') or 0)
        if current:
            if int(current['revision']) != expected: raise ClosingStorageConflictError('Aufgabenpool wurde zwischenzeitlich geändert.')
            con.execute("UPDATE closing_live_catalogs SET payload_json=?,revision=revision+1,updated_at=?,updated_by=? WHERE scope=?",(_fm514_dumps(mod,clean),now,user,scope))
        else:
            con.execute("INSERT INTO closing_live_catalogs(scope,payload_json,revision,updated_at,updated_by) VALUES(?,?,1,?,?)",(scope,_fm514_dumps(mod,clean),now,user))
        con.execute('COMMIT')
    except Exception:
        try: con.execute('ROLLBACK')
        except Exception: pass
        raise
    finally: con.close()


def _fm514_apply_catalog(mod,period):
    # Nur fehlende wiederkehrende Aufgaben für neue Perioden ergänzen; nie Bestandswerte überschreiben.
    data=_fm514_load_period(mod,period); catalog=_fm514_load_catalog(mod); tasks=data.setdefault('tasks',[])
    existing_catalog={str(t.get('catalog_id') or '') for t in tasks if t.get('catalog_id')}
    changed=False
    for entry in catalog.get('tasks',[]):
        if not isinstance(entry,dict) or not entry.get('recurring',True): continue
        cid=str(entry.get('catalog_id') or '')
        if not cid or cid in existing_catalog: continue
        if period <= str(entry.get('start_period') or period): continue
        try:
            task=mod.catalog_entry_to_task(entry,period,len(tasks)+1)
        except Exception:
            task=dict(entry); task['id']='task_'+_fm514_uuid.uuid4().hex
        tasks.append(task); existing_catalog.add(cid); changed=True
    if changed: _fm514_save_period(mod,period,data)
    return data


def _fm514_patch_module(module_key,mod):
    if getattr(mod,'_fm514_patch_done',False): return mod
    mod.load_period=lambda period:_fm514_load_period(mod,period)
    mod.save_period=lambda period,data:_fm514_save_period(mod,period,data)
    mod.load_catalog=lambda:_fm514_load_catalog(mod)
    mod.save_catalog=lambda data:_fm514_save_catalog(mod,data)
    mod.apply_catalog_to_period=lambda period:_fm514_apply_catalog(mod,period)
    mod.ensure_storage=lambda:_fm514_init_db()
    mod.ensure_period_window=lambda:_fm514_init_db()
    def list_periods():
        try: return list(mod.iter_allowed_periods())
        except Exception: return []
    mod.list_periods=list_periods
    mod.period_path=lambda period:_fm514_db_path()
    mod.RELATIONAL_SHARED_SQLITE_PATCH_VERSION=RELATIONAL_SHARED_SQLITE_PATCH_VERSION
    mod.SQLITE_SHARED_TASK_DB_PATH=str(_fm514_db_path())
    for cls_name in ('MonthlyCloseUI','QuarterlyCloseUI','YearlyCloseUI'):
        cls=getattr(mod,cls_name,None)
        if cls is None: continue
        # Alte Perioden-JSON-Dateien werden nicht mehr gescannt oder bereinigt.
        cls.strip_task_ids_all_periods=lambda self: None
        cls.all_period_files=lambda self: []
        cls._period_file_mtime=lambda self:_fm514_period_revision(mod,self.period)
        old_init=cls.__init__
        def wrapped_init(self,app,_old=old_init):
            mod._fm514_current_user_key=str(getattr(app,'current_user_key','') or '')
            return _old(self,app)
        cls.__init__=wrapped_init
        old_save=getattr(cls,'save',None)
        if old_save:
            def wrapped_save(self,_old=old_save):
                try:
                    return _old(self)
                except ClosingStorageConflictError as exc:
                    try: mod.messagebox.showwarning('Abschlusskalender',str(exc)+'\n\nDer aktuelle Live-Stand wird neu geladen.')
                    except Exception: pass
                    self.data=_fm514_load_period(mod,self.period)
                    raise
                except Exception as exc:
                    try: mod.messagebox.showerror('Abschlusskalender','Speichern in der zentralen Datenbank fehlgeschlagen:\n\n'+str(exc))
                    except Exception: pass
                    raise
            cls.save=wrapped_save
    mod._fm514_patch_done=True
    return mod

# 0.514: alte JSON-Migration bereits vor dem finalen Loader deaktivieren.
try:
    _fm509_migrate_local_storage = lambda mod: None
except Exception:
    pass

_FM514_PREV_LOAD_EMBEDDED_MODULE=_load_embedded_module
def _load_embedded_module(module_key: str):
    mod=_FM514_PREV_LOAD_EMBEDDED_MODULE(module_key)
    # Keine stille Fehlerunterdrückung: Speicherinitialisierung muss eindeutig aktiv sein.
    mod=_fm514_patch_module(module_key,mod)
    _MODULE_CACHE[module_key]=mod
    return mod



# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_LIVE_REFRESH_LOCK_FIX_V0515
# - global monotone Audit-Revision instead of MAX(task.revision)
# - schema/journal initialization once per process and database path
# - normal reads and 3-second refresh perform SELECT only
# - dashboard and team detail both refresh from the shared live state
# - temporary SQLite lock during polling skips one cycle without blocking UI
# ------------------------------------------------------------------
LIVE_REFRESH_LOCK_FIX_PATCH_VERSION = "0.515-live-refresh-lock-fix"
_FM515_INITIALIZED_PATHS = set()
_FM515_INIT_LOCK = _FM509_SQLITE_LOCK
_FM515_ORIGINAL_INIT_DB = _fm514_init_db


def _fm515_connect():
    """Normal connection without journal/schema writes.

    The journal mode is configured once by _fm515_init_db. Every subsequent
    connection is a short reader/writer connection only.
    """
    path = _fm514_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = _fm509_sqlite3.connect(str(path), timeout=5, isolation_level=None)
    con.row_factory = _fm509_sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA locking_mode=NORMAL")
    return con


def _fm515_init_db():
    path_key = str(_fm514_db_path()).casefold()
    if path_key in _FM515_INITIALIZED_PATHS:
        return
    with _FM515_INIT_LOCK:
        if path_key in _FM515_INITIALIZED_PATHS:
            return
        # Only this first initialization may set journal mode and create schema.
        con = _fm509_sqlite3.connect(str(_fm514_db_path()), timeout=30, isolation_level=None)
        try:
            con.execute("PRAGMA busy_timeout=30000")
            con.execute("PRAGMA journal_mode=DELETE")
            con.execute("PRAGMA synchronous=FULL")
            con.execute("PRAGMA locking_mode=NORMAL")
        finally:
            con.close()
        # Original schema creation now uses _fm515_connect and therefore does
        # not switch journal mode again.
        _FM515_ORIGINAL_INIT_DB()
        _FM515_INITIALIZED_PATHS.add(path_key)


def _fm515_period_revision(mod, period):
    """Read-only, globally monotone live marker for one scope/period."""
    try:
        if str(_fm514_db_path()).casefold() not in _FM515_INITIALIZED_PATHS:
            _fm515_init_db()
        con = _fm509_sqlite3.connect(str(_fm514_db_path()), timeout=1, isolation_level=None)
        con.row_factory = _fm509_sqlite3.Row
        try:
            con.execute("PRAGMA busy_timeout=1000")
            row = con.execute(
                "SELECT COALESCE(MAX(revision),0) AS revision "
                "FROM closing_live_audit WHERE scope=? AND period=?",
                (_fm514_scope(mod), period),
            ).fetchone()
            return float(int(row['revision'] or 0)) if row else 0.0
        finally:
            con.close()
    except _fm509_sqlite3.OperationalError as exc:
        # Polling must never block or display a lock error. Skip this cycle.
        if 'locked' in str(exc).lower() or 'busy' in str(exc).lower():
            return 0.0
        return 0.0
    except Exception:
        return 0.0


def _fm515_patch_module(module_key, mod):
    mod = _fm514_patch_module(module_key, mod)
    if getattr(mod, '_fm515_live_refresh_lock_fix_done', False):
        return mod

    for cls_name in ('MonthlyCloseUI', 'QuarterlyCloseUI', 'YearlyCloseUI'):
        cls = getattr(mod, cls_name, None)
        if cls is None:
            continue

        # The existing refresh renderer already distinguishes dashboard from
        # selected-team detail. Supplying a correct monotone marker makes both
        # branches update reliably.
        cls._period_file_mtime = lambda self, _m=mod: _fm515_period_revision(_m, self.period)

        old_check = getattr(cls, '_check_live_period_refresh', None)
        if old_check and not getattr(old_check, '_fm515_wrapped', False):
            def checked_refresh(self, _old=old_check):
                try:
                    return _old(self)
                except _fm509_sqlite3.OperationalError as exc:
                    # A momentary SMB/SQLite lock is non-fatal for live polling.
                    if 'locked' not in str(exc).lower() and 'busy' not in str(exc).lower():
                        raise
                    try:
                        self.root.after(3000, self._check_live_period_refresh)
                    except Exception:
                        pass
                    return None
            checked_refresh._fm515_wrapped = True
            cls._check_live_period_refresh = checked_refresh

    mod.LIVE_REFRESH_LOCK_FIX_PATCH_VERSION = LIVE_REFRESH_LOCK_FIX_PATCH_VERSION
    mod._fm515_live_refresh_lock_fix_done = True
    return mod


# Replace globals used dynamically by all 0.514 load/save helpers.
_fm514_connect = _fm515_connect
_fm514_init_db = _fm515_init_db
_fm514_period_revision = _fm515_period_revision

_FM515_PREV_LOAD_EMBEDDED_MODULE = _load_embedded_module
def _load_embedded_module(module_key: str):
    mod = _FM515_PREV_LOAD_EMBEDDED_MODULE(module_key)
    mod = _fm515_patch_module(module_key, mod)
    _MODULE_CACHE[module_key] = mod
    return mod



# ------------------------------------------------------------------
# ABSCHLUSSKALENDER_NETWORK_LOCK_STARTUP_FIX_V0518
# Datum: 2026-07-15
# Zweck:
# - Beim Modulstart keine Journal-/Schema-Schreiboperation auf bestehender DB.
# - Bestehendes Schema nur lesend ueber sqlite_master pruefen.
# - Kurzzeitige SMB-/SQLite-Sperren beim Laden kontrolliert wiederholen.
# - Modulstart zeigt erst nach ausgeschöpften Wiederholungen einen Fehler.
# ------------------------------------------------------------------
NETWORK_LOCK_STARTUP_FIX_VERSION = "0.518-network-lock-startup-fix"
_FM518_REQUIRED_TABLES = {
    'closing_live_meta','closing_live_periods','closing_live_tasks',
    'closing_live_catalogs','closing_live_audit','closing_live_locks'
}


def _fm518_is_lock_error(exc):
    text=str(exc or '').casefold()
    return 'database is locked' in text or 'database is busy' in text or 'locked' in text or 'busy' in text


def _fm518_schema_ready():
    path=_fm514_db_path()
    if not path.exists(): return False
    con=_fm509_sqlite3.connect(str(path),timeout=2,isolation_level=None)
    try:
        con.execute('PRAGMA busy_timeout=2000')
        names={str(r[0]) for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        return _FM518_REQUIRED_TABLES.issubset(names)
    finally:
        con.close()


def _fm518_create_schema_once():
    """Creates schema only for a genuinely new database; never changes journal mode."""
    path=_fm514_db_path(); path.parent.mkdir(parents=True,exist_ok=True)
    con=_fm509_sqlite3.connect(str(path),timeout=30,isolation_level=None)
    try:
        con.execute('PRAGMA busy_timeout=30000')
        con.execute('PRAGMA foreign_keys=ON')
        con.executescript("""
        CREATE TABLE IF NOT EXISTS closing_live_meta (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS closing_live_periods (
            scope TEXT NOT NULL,period TEXT NOT NULL,payload_json TEXT NOT NULL DEFAULT '{}',
            revision INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL,updated_by TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(scope,period));
        CREATE TABLE IF NOT EXISTS closing_live_tasks (
            task_pk TEXT PRIMARY KEY,scope TEXT NOT NULL,period TEXT NOT NULL,task_id TEXT NOT NULL,
            payload_json TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,deleted INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,updated_by TEXT NOT NULL DEFAULT '',UNIQUE(scope,period,task_id),
            FOREIGN KEY(scope,period) REFERENCES closing_live_periods(scope,period) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS closing_live_catalogs (
            scope TEXT PRIMARY KEY,payload_json TEXT NOT NULL DEFAULT '{"tasks": []}',revision INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,updated_by TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS closing_live_audit (
            revision INTEGER PRIMARY KEY AUTOINCREMENT,scope TEXT NOT NULL,period TEXT NOT NULL DEFAULT '',
            task_id TEXT NOT NULL DEFAULT '',action TEXT NOT NULL,old_json TEXT NOT NULL DEFAULT '',
            new_json TEXT NOT NULL DEFAULT '',changed_at TEXT NOT NULL,changed_by TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS closing_live_locks (
            scope TEXT NOT NULL,period TEXT NOT NULL,task_id TEXT NOT NULL,locked_by TEXT NOT NULL,
            locked_at TEXT NOT NULL,heartbeat_at TEXT NOT NULL,PRIMARY KEY(scope,period,task_id));
        CREATE INDEX IF NOT EXISTS idx_closing_live_tasks_period ON closing_live_tasks(scope,period,deleted,updated_at);
        CREATE INDEX IF NOT EXISTS idx_closing_live_audit_period ON closing_live_audit(scope,period,revision);
        """)
        con.execute("INSERT OR IGNORE INTO closing_live_meta(key,value) VALUES('schema_version','518')")
        con.execute("INSERT OR IGNORE INTO closing_live_meta(key,value) VALUES('storage_mode','0.518-network-lock-startup-fix')")
    finally:
        con.close()


def _fm518_init_db():
    path_key=str(_fm514_db_path()).casefold()
    if path_key in _FM515_INITIALIZED_PATHS: return
    with _FM515_INIT_LOCK:
        if path_key in _FM515_INITIALIZED_PATHS: return
        import time as _time
        last=None
        for attempt in range(10):
            try:
                if _fm518_schema_ready():
                    _FM515_INITIALIZED_PATHS.add(path_key); return
                _fm518_create_schema_once()
                if _fm518_schema_ready():
                    _FM515_INITIALIZED_PATHS.add(path_key); return
            except _fm509_sqlite3.OperationalError as exc:
                last=exc
                if not _fm518_is_lock_error(exc): raise
            _time.sleep(min(0.25*(attempt+1),1.5))
        raise _fm509_sqlite3.OperationalError('Abschlusskalender-Datenbank ist nach mehreren Leseversuchen weiterhin gesperrt: '+str(last or 'database is locked'))


def _fm518_retry_read(fn,*args,**kwargs):
    import time as _time
    last=None
    for attempt in range(10):
        try: return fn(*args,**kwargs)
        except _fm509_sqlite3.OperationalError as exc:
            last=exc
            if not _fm518_is_lock_error(exc): raise
            _time.sleep(min(0.2*(attempt+1),1.25))
    raise _fm509_sqlite3.OperationalError('Abschlusskalender konnte nach mehreren Versuchen nicht gelesen werden: '+str(last or 'database is locked'))


# Existing helpers resolve globals dynamically.
_FM518_RAW_LOAD_PERIOD=_fm514_load_period
_FM518_RAW_LOAD_CATALOG=_fm514_load_catalog
_fm514_init_db=_fm518_init_db

def _fm518_load_period(mod,period):
    return _fm518_retry_read(_FM518_RAW_LOAD_PERIOD,mod,period)

def _fm518_load_catalog(mod):
    return _fm518_retry_read(_FM518_RAW_LOAD_CATALOG,mod)


def _fm518_patch_module(module_key,mod):
    mod=_fm515_patch_module(module_key,mod)
    if getattr(mod,'_fm518_network_lock_startup_fix_done',False): return mod
    mod.load_period=lambda period:_fm518_load_period(mod,period)
    mod.load_catalog=lambda:_fm518_load_catalog(mod)
    mod.ensure_storage=lambda:_fm518_init_db()
    mod.ensure_period_window=lambda:_fm518_init_db()
    mod.NETWORK_LOCK_STARTUP_FIX_VERSION=NETWORK_LOCK_STARTUP_FIX_VERSION
    mod._fm518_network_lock_startup_fix_done=True
    return mod


_FM518_PREV_LOAD_EMBEDDED_MODULE=_load_embedded_module
def _load_embedded_module(module_key:str):
    mod=_FM518_PREV_LOAD_EMBEDDED_MODULE(module_key)
    mod=_fm518_patch_module(module_key,mod)
    _MODULE_CACHE[module_key]=mod
    return mod



# ABSCHLUSSKALENDER_DEADLINE_BOOKINGCIRCLE_MAIL_V0519
DEADLINE_BOOKINGCIRCLE_MAIL_VERSION = "0.519"

def _fm519_due(mod, task):
    try: return mod.parse_date(task.get("due_date"))
    except Exception: return None

def _fm519_alert_task(mod, task, today=None):
    today = today or mod.date.today(); due = _fm519_due(mod, task)
    return bool(task.get("status") != mod.STATUS_DONE and due and
                (task.get("priority") == "kritisch" or task.get("deadline_type") == "gesetzlich") and
                (due - today).days <= 7)

def _fm519_user(ui, key):
    return ((getattr(ui.app, "user_data", {}) or {}).get("users", {}) or {}).get(key, {}) or {}

def _fm519_name(ui, key):
    u=_fm519_user(ui,key)
    return u.get("full_name") or " ".join(x for x in (u.get("first_name", "").strip(), u.get("display_name", key).strip()) if x).strip() or key

def _fm519_audit(ui, action, details, task=None):
    try: ui.app.log_audit_event("Info", "Abschlusskalender", action, details, "Info", ui.period, str((task or {}).get("id", "")), True)
    except Exception: pass

def _fm519_send_outlook(ui, to_email, subject, html_body):
    sender_key=str(getattr(ui.app,"current_user_key","") or "")
    sender_email=str(_fm519_user(ui,sender_key).get("email","") or "").strip()
    if not to_email: return False, "Keine Empfängeradresse hinterlegt."
    if not sender_email: return False, "Für den versendenden Benutzer ist keine E-Mail-Adresse hinterlegt."
    try:
        import win32com.client
        outlook=win32com.client.Dispatch("Outlook.Application")
        account=None
        for item in outlook.Session.Accounts:
            try:
                if str(item.SmtpAddress or "").strip().casefold()==sender_email.casefold(): account=item; break
            except Exception: pass
        if account is None: return False, "Das persönliche Outlook-Konto ist im klassischen Outlook-Profil nicht verfügbar: "+sender_email
        mail=outlook.CreateItem(0)
        try: mail._oleobj_.Invoke(*(64209,0,8,0,account))
        except Exception:
            try: mail.SendUsingAccount=account
            except Exception: pass
        mail.To=to_email; mail.Subject=subject; mail.HTMLBody=html_body; mail.Send()
        return True, ""
    except Exception as exc: return False, str(exc)

def _fm519_table(mod, tasks):
    import html
    head=("Team","Aufgabe","Buchungskreis","Fälligkeit","Priorität","Status")
    rows=[]
    for t in sorted(tasks,key=lambda x:(str(x.get("due_date","")),str(x.get("team","")),str(x.get("title","")))):
        vals=(t.get("team",""),t.get("title",""),t.get("booking_circle","IDE"),mod.format_date_de(t.get("due_date","")),t.get("priority",""),t.get("status",""))
        rows.append("<tr>"+"".join('<td style="border:1px solid #CBD5E1;padding:6px 8px">'+html.escape(str(v))+"</td>" for v in vals)+"</tr>")
    return '<table style="border-collapse:collapse;font-family:Segoe UI,Arial;font-size:10.5pt"><tr style="background:#DCE6F4">'+"".join('<th style="border:1px solid #94A3B8;padding:6px 8px;text-align:left">'+h+"</th>" for h in head)+"</tr>"+"".join(rows)+"</table>"

def _fm519_remind(mod, ui):
    groups={}
    for task in ui.tasks():
        if task.get("status") == mod.STATUS_DONE: continue
        key=str(task.get("owner_user_key") or "").strip()
        if key: groups.setdefault(key,[]).append(task)
    if not groups: mod.messagebox.showinfo("Nutzer erinnern","Im aktuellen Zeitraum sind keine zugewiesenen offenen Aufgaben vorhanden."); return
    valid=[]; missing=[]
    for key,tasks in groups.items():
        email=str(_fm519_user(ui,key).get("email","") or "").strip()
        (valid if email else missing).append((key,email,tasks) if email else _fm519_name(ui,key))
    text=f"Empfänger mit E-Mail-Adresse: {len(valid)}\nOffene Aufgaben: {sum(len(v[2]) for v in valid)}"
    if missing: text += "\nOhne E-Mail-Adresse: "+", ".join(missing)
    if not mod.messagebox.askyesno("Nutzer erinnern",text+"\n\nJetzt automatisch über das klassische Outlook versenden?"): return
    sent=0; errors=[]; sender=_fm519_name(ui,str(getattr(ui.app,"current_user_key","") or ""))
    for key,email,tasks in valid:
        first=_fm519_user(ui,key).get("first_name") or _fm519_name(ui,key)
        subject=f"FiBu Mate – Erinnerung an offene Aufgaben im {ui.close_type_label()} {mod.period_label(ui.period)}"
        body=f"<p>Hallo {first},</p><p>im aktuellen {ui.close_type_label()} sind dir noch folgende offene Aufgaben zugewiesen:</p>"+_fm519_table(mod,tasks)+f"<p>Bitte prüfe die Aufgaben und aktualisiere den Bearbeitungsstand direkt in FiBu Mate.</p><p>Vielen Dank und freundliche Grüße<br>{sender}<br>FiBu Mate</p>"
        ok,err=_fm519_send_outlook(ui,email,subject,body)
        _fm519_audit(ui,"Aufgabenerinnerung versendet" if ok else "Aufgabenerinnerung fehlgeschlagen",f"Empfänger: {email}; Aufgaben: {len(tasks)}; Fehler: {err}")
        sent += int(ok)
        if not ok: errors.append(_fm519_name(ui,key)+": "+err)
    for name in missing: _fm519_audit(ui,"Aufgabenerinnerung nicht versendet","Keine E-Mail-Adresse: "+name)
    result=f"Automatisch versendete Erinnerungen: {sent}"
    if missing: result += "\nOhne E-Mail-Adresse: "+", ".join(missing)
    if errors: result += "\n\nFehler:\n"+"\n".join(errors)
    (mod.messagebox.showwarning if missing or errors else mod.messagebox.showinfo)("Nutzer erinnern",result)

def _fm519_popup(mod, ui):
    key=str(getattr(ui.app,"current_user_key","") or "")
    tasks=[t for t in ui.tasks() if str(t.get("owner_user_key") or "")==key and _fm519_alert_task(mod,t)]
    if not tasks: return
    lines=[]
    for t in sorted(tasks,key=lambda x:str(x.get("due_date",""))):
        due=_fm519_due(mod,t); delta=(due-mod.date.today()).days
        when=("überfällig seit "+mod.format_date_de(due)) if delta<0 else ("heute fällig" if delta==0 else mod.format_date_de(due))
        lines.append("• "+when+" | "+str(t.get("team",""))+" | "+str(t.get("title",""))+" | "+str(t.get("booking_circle","IDE")))
    mod.messagebox.showwarning("Offene kritische oder gesetzliche Fristen","Folgende dir zugewiesene Aufgaben sind innerhalb der nächsten 7 Tage fällig oder bereits überfällig:\n\n"+"\n".join(lines))

def _fm519_rank(ui):
    try: return int(ui.role_rank_value())
    except Exception:
        try: return int(ui.app.role_rank(ui.app.my_role()))
        except Exception: return 1

def _fm519_patch_class(mod, cls):
    if cls is None or getattr(cls,"_fm519_done",False): return
    old_init=cls.__init__; old_dashboard=cls.render_dashboard
    def init(self,*a,**k):
        old_init(self,*a,**k)
        try: self.root.after(250,lambda:_fm519_popup(mod,self))
        except Exception: pass
    def next_relevant_task(self,tasks):
        items=[t for t in tasks if _fm519_alert_task(mod,t)]
        return min(items,key=lambda t:_fm519_due(mod,t)) if items else None
    def dashboard(self,*a,**k):
        result=old_dashboard(self,*a,**k)
        if _fm519_rank(self)>=3:
            try:
                def find(w):
                    for c in w.winfo_children():
                        try:
                            if isinstance(c,mod.tk.Button) and str(c.cget("text"))=="Audit Übersicht": return c
                        except Exception: pass
                        hit=find(c)
                        if hit:return hit
                audit=find(self.frame)
                if audit: mod.tk.Button(audit.master,text="Nutzer erinnern",command=lambda:_fm519_remind(mod,self),bg=mod.COLORS["white"],fg=mod.COLORS["blue"],bd=1,padx=10,pady=4,cursor="hand2").pack(side="left",padx=(8,0))
            except Exception: pass
        return result
    def delegation(self,user_key,recipient_name,task_title,scope):
        email=self.recipient_email_for_user(user_key)
        if not email:
            _fm519_audit(self,"Delegationsmail nicht versendet","Keine E-Mail-Adresse für "+str(recipient_name))
            mod.messagebox.showwarning("Delegierung",f"Für {recipient_name} ist keine E-Mail-Adresse hinterlegt. Die Delegierung wurde gespeichert, aber es konnte keine Benachrichtigung versendet werden.")
            return False
        scope_text="bis auf Weiteres" if scope=="permanent" else "für den Zeitraum "+mod.period_label(self.period)
        sender=_fm519_name(self,str(getattr(self.app,"current_user_key","") or ""))
        subject=f"Delegierung {self.close_type_label()}: {task_title}"
        body=f"<p>Hallo {recipient_name},</p><p>die Zuständigkeit der Aufgabe <b>{task_title}</b> im {self.close_type_label()} wurde von {sender} {scope_text} an dich delegiert.</p><p>Bitte prüfe die Aufgabe direkt in FiBu Mate.</p><p>Vielen Dank und freundliche Grüße<br>{sender}<br>FiBu Mate</p>"
        ok,err=_fm519_send_outlook(self,email,subject,body)
        _fm519_audit(self,"Delegationsmail versendet" if ok else "Delegationsmail fehlgeschlagen",f"Empfänger: {email}; Aufgabe: {task_title}; Fehler: {err}")
        if not ok: mod.messagebox.showwarning("Delegierung","Die Delegierung wurde gespeichert, aber die automatische Outlook-Benachrichtigung konnte nicht versendet werden:\n\n"+err)
        return ok
    cls.__init__=init; cls.next_relevant_task=next_relevant_task; cls.render_dashboard=dashboard; cls.send_delegation_email=delegation; cls._fm519_done=True

def _fm519_patch_module(module_key,mod):
    mod=_fm518_patch_module(module_key,mod)
    for name in ("MonthlyCloseUI","QuarterlyCloseUI","YearlyCloseUI"): _fm519_patch_class(mod,getattr(mod,name,None))
    mod.DEADLINE_BOOKINGCIRCLE_MAIL_VERSION=DEADLINE_BOOKINGCIRCLE_MAIL_VERSION
    return mod

_FM519_PREV_LOAD_EMBEDDED_MODULE=_load_embedded_module
def _load_embedded_module(module_key:str):
    mod=_FM519_PREV_LOAD_EMBEDDED_MODULE(module_key); mod=_fm519_patch_module(module_key,mod); _MODULE_CACHE[module_key]=mod; return mod

if __name__ == '__main__':
    import json
    print(json.dumps(selftest_static(), ensure_ascii=False, indent=2))


# ------------------------------------------------------------------
# FiBu Mate Abschlusskalender - Multi-Dokumentationen FINAL 2026-07-20
# Version 0.520
# Zweck:
# - Mehrere Dokumentationen pro Aufgabe/Unteraufgabe.
# - Dokumentationsdateien werden in einen FiBu-Mate-Dokumentationsordner kopiert.
# - Neue Dokumentationen werden automatisch in alle Folgezeitraeume uebernommen.
# - Entfernen wirkt analog im aktuellen und in allen Folgezeitraeumen.
# ------------------------------------------------------------------

APP_VERSION = "0.522-documentation-count-real-files"
DOCUMENTATION_MULTI_VERSION = "0.520"


def _fm520_patch_class(mod, cls):
    if cls is None or getattr(cls, "_fm520_multi_documentation", False):
        return

    def _now(self):
        try:
            return mod.datetime.now().isoformat(timespec="seconds")
        except Exception:
            from datetime import datetime as _dt
            return _dt.now().isoformat(timespec="seconds")

    def _user(self):
        try:
            return self.current_user_full_name()
        except Exception:
            return str(getattr(getattr(self, "app", None), "current_user_display", "") or getattr(getattr(self, "app", None), "current_user_key", "") or "")

    def _norm_doc(self, raw):
        import os
        if isinstance(raw, str):
            path = raw.strip()
            return {"name": os.path.basename(path), "path": path, "source_path": path, "created_at": "", "created_by": "", "note": "", "doc_id": ""} if path else None
        if isinstance(raw, dict):
            path = str(raw.get("path", "") or "").strip()
            # Leere Legacy-Dokumentationsobjekte oder reine Platzhalter-Namen dürfen nicht als Dokumentation zählen.
            if not path:
                return None
            name = str(raw.get("name", "") or "").strip() or os.path.basename(path)
            out = dict(raw)
            out["name"] = name
            out["path"] = path
            out.setdefault("source_path", raw.get("source_path", path))
            out.setdefault("created_at", raw.get("updated_at", ""))
            out.setdefault("created_by", "")
            out.setdefault("note", "")
            out.setdefault("doc_id", "")
            return out
        return None

    def normalize_documentation_fields(self, item):
        import os
        item.setdefault("attachments", [])
        item.setdefault("comments", [])
        docs = []
        for raw in item.get("documentations", []) if isinstance(item.get("documentations", []), list) else []:
            doc = _norm_doc(self, raw)
            if doc and (doc.get("path") or doc.get("name")):
                docs.append(doc)
        legacy = _norm_doc(self, item.get("documentation"))
        if legacy and not any((d.get("doc_id") and legacy.get("doc_id") and d.get("doc_id") == legacy.get("doc_id")) or (d.get("path") and d.get("path") == legacy.get("path")) for d in docs):
            docs.insert(0, legacy)
        seen = set()
        clean_docs = []
        for doc in docs:
            key = doc.get("doc_id") or doc.get("path") or (doc.get("name"), doc.get("source_path"))
            if key in seen:
                continue
            seen.add(key)
            clean_docs.append(doc)
        item["documentations"] = clean_docs
        item["documentation"] = clean_docs[0] if clean_docs else {}
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

    def documentation_count(self, item):
        self.normalize_documentation_fields(item)
        return len([d for d in item.get("documentations", []) if isinstance(d, dict) and str(d.get("path", "") or "").strip()])

    def _task_key(self, task):
        try:
            return self.task_match_key(task)
        except Exception:
            return ("task", str(task.get("id", "")), str(task.get("team", "")), str(task.get("title", "")).strip().casefold())

    def _sub_key(self, subtask):
        return str(subtask.get("catalog_id") or subtask.get("id") or subtask.get("title") or "").strip().casefold()

    def _find_target(self, data, task_key, sub_key=None):
        for task in data.get("tasks", []) or []:
            if task.get("deleted"):
                continue
            if _task_key(self, task) != task_key:
                continue
            if sub_key:
                for sub in task.get("subtasks", []) or []:
                    if not sub.get("deleted") and _sub_key(self, sub) == sub_key:
                        return sub
                return None
            return task
        return None

    def _doc_root(self):
        try:
            scope = self.close_type_label().replace(" ", "_")
        except Exception:
            scope = str(getattr(mod, "CLOSING_SCOPE", "Abschluss") or "Abschluss")
        try:
            root = mod.BASE_DIR.parent / "Dokumentationen" / scope
        except Exception:
            root = mod.Path("Dokumentationen") / scope
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _safe_name(self, value):
        import re
        safe = re.sub(r"[^A-Za-z0-9_.() äöüÄÖÜß-]+", "_", str(value or "Dokumentation")).strip(" ._")
        return safe[:150] or "Dokumentation"

    def _copy_doc(self, source_path, title):
        import hashlib, os, shutil
        src = mod.Path(str(source_path or "").strip())
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(str(source_path))
        folder = _doc_root(self) / str(getattr(self, "period", "")) / _safe_name(self, title)[:60]
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / _safe_name(self, src.name)
        if target.exists():
            target = folder / f"{target.stem}_{hashlib.sha1((str(src)+_now(self)).encode('utf-8', errors='ignore')).hexdigest()[:8]}{target.suffix}"
        copied = shutil.copy2(str(src), str(target))
        return {"doc_id": hashlib.sha1(str(copied).casefold().encode("utf-8", errors="ignore")).hexdigest(), "name": os.path.basename(copied), "path": str(copied), "source_path": str(src), "created_at": _now(self), "created_by": _user(self), "note": "", "period_added": str(getattr(self, "period", ""))}

    def _add_doc(self, item, doc):
        self.normalize_documentation_fields(item)
        docs = item.setdefault("documentations", [])
        key = doc.get("doc_id") or doc.get("path")
        for existing in docs:
            if key and (existing.get("doc_id") == key or existing.get("path") == doc.get("path")):
                return False
        docs.append(dict(doc))
        item["documentation"] = docs[0] if docs else {}
        return True

    def _remove_doc(self, item, doc):
        self.normalize_documentation_fields(item)
        doc_id = doc.get("doc_id") or ""
        path = doc.get("path") or ""
        before = len(item.get("documentations", []))
        item["documentations"] = [d for d in item.get("documentations", []) if not ((doc_id and d.get("doc_id") == doc_id) or (path and d.get("path") == path))]
        item["documentation"] = item["documentations"][0] if item.get("documentations") else {}
        return before != len(item.get("documentations", []))

    def _propagate(self, item, docs, parent_task=None, remove=False):
        if not docs:
            return 0
        task_key = _task_key(self, parent_task or item)
        sub_key = _sub_key(self, item) if parent_task is not None else None
        changed_periods = 0
        try:
            periods = list(self.following_periods())
        except Exception:
            periods = []
        for period in periods:
            try:
                data = mod.load_period(period)
                target = _find_target(self, data, task_key, sub_key)
                if not target:
                    continue
                changed = False
                for doc in docs:
                    changed = (_remove_doc(self, target, doc) if remove else _add_doc(self, target, doc)) or changed
                if changed:
                    mod.save_period(period, data)
                    changed_periods += 1
            except Exception:
                pass
        return changed_periods

    def create_documentation_button(self, parent, item, title, parent_task=None):
        bg = parent.cget("bg")
        frame = mod.tk.Frame(parent, bg=bg)
        frame.pack_propagate(True)
        inner = mod.tk.Frame(frame, bg=bg)
        inner.pack(anchor="center", expand=True, pady=2)
        count = self.documentation_count(item)
        try:
            photo = self.get_close_icon_photo("fileinterfacesymboloftextpapersheet_79740.ico", 18, 18)
        except Exception:
            photo = None
        if photo:
            btn = mod.tk.Button(
                inner,
                text=f"  {count}",
                image=photo,
                compound="left",
                command=lambda: self.show_documentation_popup(item, title, parent_task),
                bg=mod.COLORS.get("white", "#FFFFFF"),
                fg=mod.COLORS["blue"],
                activebackground=mod.COLORS.get("white", "#FFFFFF"),
                activeforeground=mod.COLORS["blue"],
                bd=1,
                relief="solid",
                cursor="hand2",
                padx=5,
                pady=3,
                font=mod.zfont(self.app, 11, "bold"),
            )
            btn.image = photo
        else:
            btn = mod.tk.Button(
                inner,
                text=f"📄  {count}",
                command=lambda: self.show_documentation_popup(item, title, parent_task),
                bg=mod.COLORS.get("white", "#FFFFFF"),
                fg=mod.COLORS["blue"],
                activebackground=mod.COLORS.get("white", "#FFFFFF"),
                activeforeground=mod.COLORS["blue"],
                bd=1,
                relief="solid",
                cursor="hand2",
                padx=5,
                pady=3,
                font=mod.zfont(self.app, 11, "bold"),
            )
        btn.pack(side="left")
        return frame

    def show_documentation_popup(self, item, title, parent_task=None):
        self.normalize_documentation_fields(item)
        win = mod.tk.Toplevel(self.root)
        win.title(f"Dokumentationen - {title}")
        win.configure(bg=mod.COLORS["bg"])
        win.geometry("820x520")
        win.transient(self.root)
        win.grab_set()
        mod.tk.Label(win, text="Dokumentationen", bg=mod.COLORS["bg"], fg=mod.COLORS["text"], font=mod.zfont(self.app, 16, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        body = mod.tk.Frame(win, bg=mod.COLORS["white"], bd=1, relief="solid")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        list_frame = mod.tk.Frame(body, bg=mod.COLORS["white"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        def refresh():
            if getattr(self, "selected_team", None):
                self.render_team_detail(self.selected_team)

        def redraw():
            for child in list_frame.winfo_children():
                child.destroy()
            docs = [d for d in item.get("documentations", []) if d.get("path") or d.get("name")]
            if not docs:
                mod.tk.Label(list_frame, text="Noch keine Dokumentation hinterlegt.", bg=mod.COLORS["white"], fg=mod.COLORS["text2"], font=mod.zfont(self.app, 12)).pack(anchor="w", pady=8)
                return
            for idx, doc in enumerate(docs, start=1):
                row = mod.tk.Frame(list_frame, bg=mod.COLORS["white"], bd=1, relief="solid")
                row.pack(fill="x", pady=(0, 6))
                label = f"{idx}. {doc.get('name','Dokumentation')}"
                if doc.get("created_at"):
                    label += f" | {mod.format_datetime_de(doc.get('created_at'))}"
                if doc.get("created_by"):
                    label += f" | {doc.get('created_by')}"
                mod.tk.Label(row, text=label, bg=mod.COLORS["white"], fg=mod.COLORS["text"], font=mod.zfont(self.app, 11, "bold"), anchor="w").pack(side="left", padx=8, pady=7, fill="x", expand=True)
                mod.tk.Button(row, text="Oeffnen", command=lambda p=doc.get("path", ""): self.open_attachment(p), bg=mod.COLORS["blue"], fg="white", bd=0, padx=8, pady=4, state="normal" if doc.get("path") else "disabled").pack(side="left", padx=(0, 6), pady=5)
                def remove_current(d=doc):
                    if not mod.messagebox.askyesno("Dokumentation entfernen", "Dokumentation aus aktuellem und allen Folgezeitraeumen entfernen?\n\nDie Datei im Dokumentationsordner wird nicht geloescht."):
                        return
                    _remove_doc(self, item, d)
                    affected = _propagate(self, item, [d], parent_task=parent_task, remove=True)
                    self.save()
                    redraw()
                    refresh()
                    mod.messagebox.showinfo("Dokumentation", f"Dokumentation entfernt. Folgezeitraeume aktualisiert: {affected}")
                mod.tk.Button(row, text="Entfernen", command=remove_current, bg="#FEE2E2", fg=mod.COLORS["red"], bd=0, padx=8, pady=4).pack(side="left", padx=(0, 8), pady=5)

        def choose_docs():
            selected = mod.filedialog.askopenfilenames(title="Dokumentationen auswaehlen")
            if not selected:
                return
            added = []
            for source in selected:
                try:
                    doc = _copy_doc(self, source, title)
                    if _add_doc(self, item, doc):
                        added.append(doc)
                except Exception as exc:
                    mod.messagebox.showerror("Dokumentation", f"Dokumentation konnte nicht kopiert werden:\n\n{source}\n\n{exc}")
            if added:
                self.save()
                affected = _propagate(self, item, added, parent_task=parent_task, remove=False)
                redraw()
                refresh()
                mod.messagebox.showinfo("Dokumentation", f"{len(added)} Dokumentation(en) hinzugefuegt und in {affected} Folgezeitraum/Folgezeitraeume uebernommen.")

        button_row = mod.tk.Frame(body, bg=mod.COLORS["white"])
        button_row.pack(fill="x", padx=12, pady=(0, 8))
        mod.tk.Button(button_row, text="Dokumentation(en) hinzufuegen", command=choose_docs, bg=mod.COLORS["blue"], fg="white", bd=0, padx=12, pady=7).pack(side="left")
        mod.tk.Label(body, text="Hinweis: Dokumentationen werden in den FiBu-Mate-Dokumentationsordner kopiert und automatisch fuer dieselbe Aufgabe in alle Folgezeitraeume uebernommen. Entfernen wirkt ebenfalls in den Folgezeitraeumen; die kopierte Datei bleibt erhalten.", bg=mod.COLORS["white"], fg=mod.COLORS["text2"], font=mod.zfont(self.app, 11), wraplength=760, justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        redraw()
        mod.tk.Button(win, text="Schliessen", command=win.destroy, bg=mod.COLORS["blue"], fg="white", bd=0, padx=14, pady=7).pack(anchor="e", padx=16, pady=(0, 14))

    old_sync = getattr(cls, "sync_current_as_template_to_following_periods", None)
    def sync_current_as_template_to_following_periods(self):
        result = old_sync(self) if old_sync else None
        try:
            for task in self.tasks():
                self.normalize_documentation_fields(task)
                if task.get("documentations"):
                    _propagate(self, task, list(task.get("documentations", [])), None, False)
                for sub in task.get("subtasks", []) or []:
                    self.normalize_documentation_fields(sub)
                    if sub.get("documentations"):
                        _propagate(self, sub, list(sub.get("documentations", [])), task, False)
        except Exception:
            pass
        return result

    cls.normalize_documentation_fields = normalize_documentation_fields
    cls.documentation_count = documentation_count
    cls.create_documentation_button = create_documentation_button
    cls.show_documentation_popup = show_documentation_popup
    cls.sync_current_as_template_to_following_periods = sync_current_as_template_to_following_periods
    cls._fm520_multi_documentation = True


# v0.520: Dokumentationssymbol in allen Abschlusskalendern wiederhergestellt.
DOCUMENTATION_ICON_RESTORE_VERSION = "0.520-documentation-icon-restored"
DOCUMENTATION_BUTTON_VISIBLE_VERSION = "0.521-documentation-button-visible"
DOCUMENTATION_COUNT_REAL_FILES_VERSION = "0.522-documentation-count-real-files"

def _fm520_patch_module(module_key, mod):
    for name in ("MonthlyCloseUI", "QuarterlyCloseUI", "YearlyCloseUI"):
        _fm520_patch_class(mod, getattr(mod, name, None))
    mod.DOCUMENTATION_MULTI_VERSION = DOCUMENTATION_MULTI_VERSION
    return mod

_FM520_PREV_LOAD_EMBEDDED_MODULE = _load_embedded_module

def _load_embedded_module(module_key: str):
    mod = _FM520_PREV_LOAD_EMBEDDED_MODULE(module_key)
    mod = _fm520_patch_module(module_key, mod)
    _MODULE_CACHE[module_key] = mod
    return mod


# ------------------------------------------------------------------
# Abschlusskalender - Fälligkeitsturnus + robuste Scrollposition FINAL 2026-07-20
# Version 0.524
# ------------------------------------------------------------------
CALENDAR_FREQUENCY_SCROLL_RETENTION_VERSION = "0.524-frequency-scroll-retention"

def _fm524_default_due_frequency(mod):
    scope = str(getattr(mod, "CLOSING_SCOPE", "M") or "M")
    return "Monat" if scope == "M" else "Quartal" if scope == "Q" else "Jahr"

def _fm524_norm_due_frequency(value, mod):
    raw = str(value or "").strip().casefold()
    mp = {"m":"Monat","monat":"Monat","monatlich":"Monat","q":"Quartal","quartal":"Quartal","quartalsweise":"Quartal","quartalsabschluss":"Quartal","j":"Jahr","jahr":"Jahr","jährlich":"Jahr","jaehrlich":"Jahr","jahresabschluss":"Jahr"}
    return mp.get(raw, _fm524_default_due_frequency(mod))

def _fm524_period_parts(period):
    s = str(period or "")
    try:
        if "-Q" in s:
            y, q = s.split("-Q", 1); return int(y), int(q), None
        if "-" in s:
            y, m = s.split("-", 1); return int(y), None, int(m)
    except Exception:
        pass
    return 0, None, None

def _fm524_is_task_relevant(mod, ui, task):
    freq = _fm524_norm_due_frequency(task.get("due_frequency"), mod)
    scope = str(getattr(mod, "CLOSING_SCOPE", "M") or "M")
    _y, q, m = _fm524_period_parts(getattr(ui, "period", ""))
    fy_end_month = int(getattr(mod, "FISCAL_YEAR_START_MONTH", 10) or 10) - 1
    if fy_end_month <= 0: fy_end_month = 12
    fy_end_quarter = ((fy_end_month - 1) // 3) + 1
    if freq == "Monat": return scope == "M"
    if freq == "Quartal": return (m in (3,6,9,12)) if scope == "M" else scope == "Q"
    if freq == "Jahr": return (m == fy_end_month) if scope == "M" else ((q == fy_end_quarter) if scope == "Q" else scope == "J")
    return True

def _fm524_find_scroll_canvas(ui):
    candidates=[]
    try:
        c=getattr(getattr(ui,"app",None),"active_scroll_canvas",None)
        if c is not None: candidates.append(c)
    except Exception: pass
    def walk(w):
        try:
            for ch in w.winfo_children():
                try:
                    if ch.winfo_class().lower()=="canvas" and hasattr(ch,"yview"):
                        candidates.append(ch)
                except Exception: pass
                walk(ch)
        except Exception: pass
    try: walk(getattr(ui,"frame",None))
    except Exception: pass
    for c in candidates:
        try:
            if c.winfo_exists():
                first,last=c.yview()
                if float(last)-float(first)<0.999: return c
        except Exception: pass
    return candidates[0] if candidates else None

def _fm524_scroll_fraction(ui):
    try:
        c=_fm524_find_scroll_canvas(ui)
        return c.yview()[0] if c is not None else None
    except Exception:
        return None

def _fm524_restore_scroll_fraction(ui, fraction):
    if fraction is None: return
    def run():
        try:
            c=_fm524_find_scroll_canvas(ui)
            if c is not None and c.winfo_exists():
                c.update_idletasks(); c.yview_moveto(float(fraction))
        except Exception: pass
    try:
        ui.root.after_idle(run); ui.root.after(25, run); ui.root.after(100, run); ui.root.after(250, run)
    except Exception: run()

def _fm524_patch_module(module_key, mod):
    if getattr(mod, "_fm524_frequency_scroll_patched", False): return mod
    old_normalize=getattr(mod,"normalize_task",None)
    if old_normalize:
        def normalize_task(task,data,period):
            result=old_normalize(task,data,period)
            try: result["due_frequency"]=_fm524_norm_due_frequency(result.get("due_frequency"),mod)
            except Exception: pass
            return result
        mod.normalize_task=normalize_task
    old_catalog=getattr(mod,"catalog_entry_to_task",None)
    if old_catalog:
        def catalog_entry_to_task(entry,period,index):
            task=old_catalog(entry,period,index)
            try: task["due_frequency"]=_fm524_norm_due_frequency(entry.get("due_frequency"),mod)
            except Exception: pass
            return task
        mod.catalog_entry_to_task=catalog_entry_to_task
    for name in ("MonthlyCloseUI","QuarterlyCloseUI","YearlyCloseUI"):
        cls=getattr(mod,name,None)
        if cls is None or getattr(cls,"_fm524_frequency_scroll_patched",False): continue
        old_tasks=getattr(cls,"tasks",None)
        if old_tasks:
            def tasks(self,_old=old_tasks,_mod=mod):
                result=[]
                for t in _old(self):
                    try:
                        t["due_frequency"]=_fm524_norm_due_frequency(t.get("due_frequency"),_mod)
                        if _fm524_is_task_relevant(_mod,self,t): result.append(t)
                    except Exception:
                        result.append(t)
                return result
            cls.tasks=tasks
        def toggle_subtasks_visibility(self, task_id):
            fraction=_fm524_scroll_fraction(self)
            if task_id in self.expanded_tasks: self.expanded_tasks.remove(task_id)
            else: self.expanded_tasks.add(task_id)
            self.render_team_detail(self.selected_team)
            _fm524_restore_scroll_fraction(self, fraction)
        cls.toggle_subtasks_visibility=toggle_subtasks_visibility
        old_ttc=getattr(cls,"task_to_catalog_entry",None)
        if old_ttc:
            def task_to_catalog_entry(self,task,_old=old_ttc,_mod=mod):
                out=_old(self,task)
                try: out["due_frequency"]=_fm524_norm_due_frequency(task.get("due_frequency"),_mod)
                except Exception: pass
                return out
            cls.task_to_catalog_entry=task_to_catalog_entry
        old_clone=getattr(cls,"clone_task_for_period",None)
        if old_clone:
            def clone_task_for_period(self,task,target_period,index,_old=old_clone,_mod=mod):
                clone=_old(self,task,target_period,index)
                try: clone["due_frequency"]=_fm524_norm_due_frequency(task.get("due_frequency"),_mod)
                except Exception: pass
                return clone
            cls.clone_task_for_period=clone_task_for_period
        cls._fm524_frequency_scroll_patched=True
    mod._fm524_frequency_scroll_patched=True
    return mod

_FM524_PREV_LOAD_EMBEDDED_MODULE = _load_embedded_module

def _load_embedded_module(module_key: str):
    mod=_FM524_PREV_LOAD_EMBEDDED_MODULE(module_key)
    mod=_fm524_patch_module(module_key,mod)
    _MODULE_CACHE[module_key]=mod
    return mod


# ---------------------------------------------------------------------------
# FM536 - Monatsabschluss als einziger Abschlusskalender, Unter-Unteraufgaben
# Datum: 2026-07-20
# Zweck: Quartals-/Jahresabschluss-Einstiege werden auf den Monatsabschluss umgeleitet.
# ---------------------------------------------------------------------------
APP_VERSION = "0.540-readable-calendar-buttons"
_FM536_PREV_LOAD_EMBEDDED_MODULE = _load_embedded_module

def _load_embedded_module(module_key: str):
    if module_key in ('quarterly_close', 'yearly_close'):
        module_key = 'monthly_close'
    mod = _FM536_PREV_LOAD_EMBEDDED_MODULE(module_key)
    _MODULE_CACHE[module_key] = mod
    return mod

def render_quarterly(app):
    return render_monthly(app)

def render_yearly(app):
    return render_monthly(app)


# v0.537: Unter-Unteraufgaben werden über ein eigenes Popup bearbeitet; Popups lesbarer gestaltet.
SUBSUBTASK_POPUP_READABLE_VERSION = "0.537-subsubtask-popup-readable"


# v0.538: Aufgaben-/Unteraufgaben-Popup scrollt lokal; Mausrad bewegt nicht das Hauptfenster.
TASK_POPUP_LOCAL_SCROLL_VERSION = "0.538-task-popup-local-scroll"


# ---------------------------------------------------------------------------
# FM539 - Unter-Unteraufgaben in Kalenderansicht auf-/zuklappbar
# Datum: 2026-07-20
# Zweck: Unter-Unteraufgaben erscheinen analog zu Unteraufgaben unterhalb der Unteraufgabe und sind farblich abgesetzt.
# ---------------------------------------------------------------------------
SUBSUBTASK_EXPAND_ROWS_VERSION = "0.539-subsubtask-expand-rows"

def _fm539_child_tasks_done(subtask):
    try:
        children = [c for c in subtask.get("subtasks", []) or [] if not c.get("deleted") and str(c.get("title", "")).strip()]
        return bool(children) and all(c.get("status") == STATUS_DONE for c in children)
    except Exception:
        return True

def _fm539_patch_class(cls):
    if not cls or getattr(cls, "_fm539_subsub_expand_patched", False):
        return
    old_toggle_subtask = getattr(cls, "toggle_subtask", None)
    if old_toggle_subtask:
        def toggle_subtask(self, task, subtask, _old=old_toggle_subtask):
            try:
                # Eine Unteraufgabe mit offenen Unter-Unteraufgaben darf nicht direkt abgeschlossen werden.
                if subtask.get("subtasks") and subtask.get("status") != STATUS_DONE and not _fm539_child_tasks_done(subtask):
                    messagebox.showinfo("Abschlusskalender", "Bitte erst alle Unter-Unteraufgaben dieser Unteraufgabe erledigen.")
                    return
            except Exception:
                pass
            return _old(self, task, subtask)
        cls.toggle_subtask = toggle_subtask
    def toggle_sub_subtask(self, task, subtask, child):
        if not self.require_unlocked("Diese Änderung"):
            return
        real = self.find_task(task.get("id"))
        if not real:
            return
        if not self.can_complete_task(real):
            messagebox.showwarning("Abschlusskalender", "Du kannst nur Unter-Unteraufgaben als erledigt markieren, wenn du selbst als zuständig eingetragen bist.")
            self.render_team_detail(real.get("team"))
            return
        target_sub = None
        for sub in real.get("subtasks", []) or []:
            if sub.get("id") == subtask.get("id") or sub.get("title") == subtask.get("title"):
                target_sub = sub
                break
        if target_sub is None:
            return
        target_sub.setdefault("subtasks", [])
        target_child = None
        for c in target_sub.get("subtasks", []) or []:
            if c.get("id") == child.get("id") or c.get("title") == child.get("title"):
                target_child = c
                break
        if target_child is None:
            return
        target_child["status"] = STATUS_OPEN if target_child.get("status") == STATUS_DONE else STATUS_DONE
        children = [c for c in target_sub.get("subtasks", []) or [] if not c.get("deleted") and str(c.get("title", "")).strip()]
        if children:
            if all(c.get("status") == STATUS_DONE for c in children):
                target_sub["status"] = STATUS_DONE
            elif target_sub.get("status") == STATUS_DONE:
                target_sub["status"] = STATUS_OPEN
        sync_parent_status_from_subtasks(real)
        self.save()
        self.render_team_detail(real.get("team"))
    cls.toggle_sub_subtask = toggle_sub_subtask
    cls._fm539_subsub_expand_patched = True

_FM539_PREV_LOAD_EMBEDDED_MODULE = _load_embedded_module

def _load_embedded_module(module_key: str):
    mod = _FM539_PREV_LOAD_EMBEDDED_MODULE(module_key)
    for _cls_name in ("MonthlyCloseUI", "QuarterlyCloseUI", "YearlyCloseUI"):
        _fm539_patch_class(getattr(mod, _cls_name, None))
    _MODULE_CACHE[module_key] = mod
    return mod


# v0.540: Buttons im Abschlusskalender lesbarer an Unter-Unteraufgaben-Aufklappbutton angeglichen.
READABLE_CALENDAR_BUTTONS_VERSION = "0.540-readable-calendar-buttons"


# v0.541: Aufgabenpopup - Fälligkeitsturnus korrekt positioniert; Dropdowntexte vergrößert.
TASK_POPUP_DUE_FREQUENCY_LAYOUT_VERSION = "0.541-task-popup-due-frequency-layout"
APP_VERSION = "0.541-task-popup-due-frequency-layout"
