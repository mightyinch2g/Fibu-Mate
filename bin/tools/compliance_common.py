
import json, os, subprocess, re, webbrowser
from pathlib import Path
from datetime import datetime, date, timedelta
from urllib.parse import quote
BG="#E8EEF5"; HEADER="#D3DEE9"; BLUE="#004B93"; RED="#E30613"; ORANGE="#F59E0B"; GREEN="#16A34A"; DARK_GREEN="#047857"; TEXT="#182431"; TEXT2="#445364"; WHITE="#FFFFFF"; GREY="#B9C3CF"
ROLE_E1="E1 - Standard"; ROLE_E2="E2 - Erweitert"; ROLE_E3="E3 - Administrator"; ROLE_E4="E4 - System-Administrator"
ROLE_RANK={ROLE_E1:1,ROLE_E2:2,ROLE_E3:3,ROLE_E4:4,"E1":1,"E2":2,"E3":3,"E4":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}
EVENT_ORDER=["Aufgabe geändert","Aufgabe gelöscht","Aufgaben-ID geändert","Fälligkeit geändert","Zuständigkeit geändert","Nachweis hinzugefügt/geändert/entfernt","PDF-Bericht erstellt","Excel-Bericht erstellt","Benutzer angelegt","Berechtigung geändert","Auto-Mail ein-/ausgeschaltet","fehlgeschlagener E-Mail-Versand","Benutzer gelöscht","Benutzer geändert"]
CRITICAL_EVENTS={"Zeitraum wieder geöffnet","Änderungen nach Wiederöffnung","fehlgeschlagener Pflicht-E-Mail","Nachweis nach Abschluss geändert"}
def script_dir():
    here=Path(__file__).resolve(); return here.parent.parent if here.parent.name.lower()=="tools" else here.parent
def bin_dir():
    base = script_dir()
    return base if base.name.lower() == "bin" else base/"bin"
def legacy_bin_dir_v0431():
    """Fallback auf den früher versehentlich verwendeten bin/bin-Pfad."""
    base = script_dir()
    return base/"bin" if base.name.lower() == "bin" else base/"bin"/"bin"

def ensure_dirs():
    base=bin_dir()/"Compliance"
    for p in [base,base/"TaxReporting"/"periods",base/"Audit"/"archive",base/"Documentation"/"exports",bin_dir()/"Deadlines"/"years"]: p.mkdir(parents=True,exist_ok=True)
    return base
def json_load(path, default):
    path=Path(path)
    try:
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(default,ensure_ascii=False,indent=2),encoding="utf-8"); return json.loads(json.dumps(default))
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return json.loads(json.dumps(default))
def json_save(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
def now_iso(): return datetime.now().isoformat(timespec="seconds")
def current_month_key(d=None): d=d or date.today(); return f"{d.year:04d}-{d.month:02d}"
def add_month(key,delta):
    y,m=map(int,key.split('-')); m+=delta
    while m<1: m+=12; y-=1
    while m>12: m-=12; y+=1
    return f"{y:04d}-{m:02d}"
def period_label(key):
    names=["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
    try: y,m=map(int,key.split('-')); return f"{names[m-1]} {str(y)[-2:]}"
    except Exception: return str(key)
def user_key(app): return getattr(app,"current_user_key","") or ""
def user_name(app):
    u=getattr(app,"user_data",{}).get("users",{}).get(user_key(app),{})
    return u.get("full_name") or u.get("display_name") or user_key(app) or "System"
def role(app):
    try: return app.my_role()
    except Exception: return getattr(app,"user_data",{}).get("users",{}).get(user_key(app),{}).get("permission",ROLE_E1)
def role_rank(app): return ROLE_RANK.get(role(app),1)
def can_admin(app): return role_rank(app)>=3
def can_system(app): return role_rank(app)>=4
def users(app): return getattr(app,"user_data",{}).get("users",{})
def user_display(app,key):
    u=users(app).get(key,{})
    return u.get("full_name") or u.get("display_name") or key or ""
def user_email(app,key): return users(app).get(key,{}).get("email","")
def user_options(app):
    return sorted([(u.get("full_name") or u.get("display_name") or k,k) for k,u in users(app).items()], key=lambda x:x[0].casefold())
def audit_path(): return ensure_dirs()/"Audit"/"audit_log.json"
def load_audit(): d=json_load(audit_path(),{"entries":[]}); d.setdefault("entries",[]); return d
def save_audit(d): d.setdefault("entries",[]); json_save(audit_path(),d)
def log_audit(app=None,event_type="Info",module="FiBu Mate",title="",details="",risk="Info",period="",related_id="",public=True):
    d=load_audit(); e={"timestamp":now_iso(),"event_type":event_type,"module":module,"title":title or event_type,"details":details,"risk":risk,"period":period,"related_id":related_id,"user_key":user_key(app) if app else "","user_name":user_name(app) if app else "System","public":bool(public),"archived":False}
    d["entries"].insert(0,e); save_audit(d); return e
def archive_audit_entries(entries,app=None,note="Manuelle Archivierung"):
    p=ensure_dirs()/"Audit"/"archive"/f"audit_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"; json_save(p,{"archived_at":now_iso(),"archived_by":user_name(app) if app else "System","note":note,"entries":entries}); return p
def tax_config_path(): return ensure_dirs()/"TaxReporting"/"tax_reporting_config.json"
def tax_period_path(period): return ensure_dirs()/"TaxReporting"/"periods"/f"{period}.json"
TAX_GROUP_MEMBER_IDS = {'ZM', 'Z4', 'Z5A', 'TAX'}
TAX_GROUP_MEMBER_TITLES = {'ZM', 'Z4', 'Z5A', 'TAX'}
TAX_GROUP_SHARED_TITLE = 'Tax'
TAX_GROUP_SHARED_TEAM = 'Steuermeldung'
TAX_GROUP_SHARED_DEFAULT_UID = 'TAX001'

def _tax_alias_key(value):
    return str(value or '').strip().upper()

def is_tax_group_member(type_id='', title=''):
    return _tax_alias_key(type_id) in TAX_GROUP_MEMBER_IDS or _tax_alias_key(title) in TAX_GROUP_MEMBER_TITLES

def tax_group_shared_uid_from_cfg(cfg=None):
    cfg = cfg or {}
    for rt in cfg.get('report_types', []) or []:
        if is_tax_group_member(rt.get('id'), rt.get('title')):
            uid = str(rt.get('task_uid', '') or '').strip()
            if uid:
                return uid
    return TAX_GROUP_SHARED_DEFAULT_UID

def normalize_tax_config(cfg):
    cfg = cfg or {}
    cfg.setdefault('report_types', [])
    cfg.setdefault('next_task_uid', 1)
    changed = False
    shared_uid = tax_group_shared_uid_from_cfg(cfg)
    shared_owner = next((str(rt.get('owner_user_key', '') or '').strip() for rt in cfg.get('report_types', []) if is_tax_group_member(rt.get('id'), rt.get('title')) and str(rt.get('owner_user_key', '') or '').strip()), '')
    shared_reviewer = next((str(rt.get('reviewer_user_key', '') or '').strip() for rt in cfg.get('report_types', []) if is_tax_group_member(rt.get('id'), rt.get('title')) and str(rt.get('reviewer_user_key', '') or '').strip()), '')
    shared_sync = any(bool(rt.get('sync_with_calendar', False)) for rt in cfg.get('report_types', []) if is_tax_group_member(rt.get('id'), rt.get('title')))
    for rt in cfg.get('report_types', []):
        before = dict(rt)
        rt.setdefault('task_uid', rt.get('id', ''))
        rt.setdefault('active', True)
        rt.setdefault('evidence_required', True)
        rt.setdefault('approval_required', True)
        rt.setdefault('four_eye', False)
        rt.setdefault('owner_user_key', '')
        rt.setdefault('reviewer_user_key', '')
        rt.setdefault('sync_with_calendar', False)
        if is_tax_group_member(rt.get('id'), rt.get('title')):
            rt['task_uid'] = shared_uid
            rt['owner_user_key'] = shared_owner
            rt['reviewer_user_key'] = shared_reviewer
            rt['sync_with_calendar'] = shared_sync if shared_sync else bool(rt.get('sync_with_calendar', True))
            rt['responsibility_title'] = TAX_GROUP_SHARED_TITLE
            rt['responsibility_team'] = TAX_GROUP_SHARED_TEAM
        if rt != before:
            changed = True
    return cfg, changed

def default_tax_config():
    return {"report_types":[{"id":"ZM","title":"ZM","task_uid":TAX_GROUP_SHARED_DEFAULT_UID,"active":True,"evidence_required":True,"approval_required":False,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True,"responsibility_title":TAX_GROUP_SHARED_TITLE,"responsibility_team":TAX_GROUP_SHARED_TEAM},{"id":"Z4","title":"Z4","task_uid":TAX_GROUP_SHARED_DEFAULT_UID,"active":True,"evidence_required":True,"approval_required":False,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True,"responsibility_title":TAX_GROUP_SHARED_TITLE,"responsibility_team":TAX_GROUP_SHARED_TEAM},{"id":"Z5a","title":"Z5a","task_uid":TAX_GROUP_SHARED_DEFAULT_UID,"active":True,"evidence_required":True,"approval_required":False,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True,"responsibility_title":TAX_GROUP_SHARED_TITLE,"responsibility_team":TAX_GROUP_SHARED_TEAM}],"warning_days":{"yellow":10,"orange":5},"next_task_uid":1}
def load_tax_config():
    d=json_load(tax_config_path(),default_tax_config()); d, _changed = normalize_tax_config(d)
    return d
def save_tax_config(d):
    d, _changed = normalize_tax_config(d)
    json_save(tax_config_path(),d)
def next_tax_task_uid(cfg):
    ex={r.get('task_uid','') for r in cfg.get('report_types',[])}; n=int(cfg.get('next_task_uid',1) or 1)
    while True:
        uid=f"TAX{n:03d}"; n+=1
        if uid not in ex: cfg['next_task_uid']=n; return uid
def default_due(period):
    synced = get_deadline_cutoff('monthly', period) if 'get_deadline_cutoff' in globals() else ''
    if synced:
        return synced
    import calendar
    y, m = map(int, period.split('-'))
    end = date(y, m, calendar.monthrange(y, m)[1])
    return default_closing_cutoff_after_period_end(end)
def ensure_tax_period(period):
    cfg = load_tax_config(); cfg, cfg_changed = normalize_tax_config(cfg)
    if cfg_changed:
        save_tax_config(cfg)
    d = json_load(tax_period_path(period), {"period":period,"created_at":now_iso(),"reports":[]}); d.setdefault("reports",[]); ex={r.get('type_id'):r for r in d['reports']}; ch=False
    for rt in cfg.get('report_types',[]):
        if not rt.get('active',True): continue
        rid=rt.get('id') or rt.get('title')
        if rid not in ex:
            d['reports'].append({"type_id":rid,"title":rt.get('title',rid),"period":period,"status":"Offen","due_date":default_due(period),"owner_user_key":rt.get('owner_user_key',''),"reviewer_user_key":rt.get('reviewer_user_key',''),"reported_at":"","approved_at":"","comments":[],"attachments":[],"history":[],"evidence_required":rt.get('evidence_required',True),"approval_required":rt.get('approval_required',True),"four_eye":rt.get('four_eye',False),"sync_with_calendar":rt.get('sync_with_calendar',False),"task_uid":rt.get('task_uid','')}); ch=True
    cfg_map = {(rt.get('id') or rt.get('title')): rt for rt in cfg.get('report_types',[])}
    for report in d.get('reports',[]) or []:
        rt = cfg_map.get(report.get('type_id'))
        if rt:
            for key, value in [('owner_user_key', rt.get('owner_user_key','')), ('reviewer_user_key', rt.get('reviewer_user_key','')), ('sync_with_calendar', bool(rt.get('sync_with_calendar',False))), ('task_uid', rt.get('task_uid','')), ('evidence_required', bool(rt.get('evidence_required',True))), ('approval_required', bool(rt.get('approval_required',True))), ('four_eye', bool(rt.get('four_eye',False)))]:
                if report.get(key) != value:
                    report[key] = value; ch = True
    if sync_tax_period_with_deadlines(period, d):
        ch = True
    if ch: json_save(tax_period_path(period),d)
    return d
def save_tax_period(period,data): json_save(tax_period_path(period),data)
def all_tax_periods(): ensure_dirs(); return sorted(p.stem for p in (ensure_dirs()/"TaxReporting"/"periods").glob("*.json")) or [current_month_key()]
def doc_manual_path(): return ensure_dirs()/"Documentation"/"manual_documents.json"
def docs_load_manual(): d=json_load(doc_manual_path(),{"documents":[]}); d.setdefault("documents",[]); return d
def docs_save_manual(d): json_save(doc_manual_path(),d)
def path_status(path): return "Fehlt" if not path else ("Vorhanden" if Path(path).exists() else "Pfad ungültig")
def open_path(path):
    try:
        if os.name=="nt": os.startfile(path)
        else: subprocess.Popen(["xdg-open",path])
    except Exception: pass
def send_assignment_mail(app,to_user_key,subject,body):
    email=user_email(app,to_user_key)
    if not email: log_audit(app,"fehlgeschlagener E-Mail-Versand","FiBu Mate",subject,f"Keine E-Mail für {to_user_key}","Mittel",public=False); return False
    webbrowser.open(f"mailto:{quote(email)}?subject={quote(subject)}&body={quote(body)}"); return True
def and_search_tokens(query):
    q=str(query or '').casefold().replace('*',' ').replace(';',','); q=re.sub(r'\s*,\s*und\s+',',',q); q=re.sub(r'\s+und\s+',',',q)
    return [p.strip() for p in q.split(',') if p.strip()]
def and_match(blob,query):
    toks=and_search_tokens(query); b=str(blob or '').casefold(); return (not toks) or all(t in b for t in toks)
def row_match(row,query): return and_match(' '.join(str(v) for v in (row.values() if isinstance(row,dict) else row)),query)
def write_simple_pdf(path,title,rows): Path(path).write_text(title+'\n\n'+'\n'.join(' | '.join(map(str,r)) for r in rows),encoding='utf-8')
def export_excel(path,headers,rows):
    from openpyxl import Workbook
    wb=Workbook(); ws=wb.active; ws.title='Export'; ws.append(headers)
    for r in rows: ws.append(list(r))
    wb.save(path)


# ---- FiBu Mate gemeinsame Stichtags-/Audit-/Tabellen-Hilfen BU31 ----
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
        date(year, 10, 3), date(year, 11, 1), date(year, 12, 25), date(year, 12, 26),
    }

def is_business_day_bw(d):
    return d.weekday() < 5 and d not in bw_holidays(d.year)

def first_business_day_after(d):
    cur = d + timedelta(days=1)
    while not is_business_day_bw(cur):
        cur += timedelta(days=1)
    return cur

def first_business_day_next_month(year, month):
    if month >= 12:
        y, m = year + 1, 1
    else:
        y, m = year, month + 1
    cur = date(y, m, 1)
    while not is_business_day_bw(cur):
        cur += timedelta(days=1)
    return cur

def default_closing_cutoff_after_period_end(period_end):
    return first_business_day_after(period_end).strftime('%Y-%m-%d')

def audit_entry_long_text(e):
    return (
        f"Zeitpunkt: {e.get('timestamp','')}\n"
        f"Ereignis: {e.get('event_type','')}\n"
        f"Modul: {e.get('module','')}\n"
        f"Risiko: {e.get('risk','')}\n"
        f"Zeitraum: {e.get('period','')}\n"
        f"Benutzer: {e.get('user_name','')} ({e.get('user_key','')})\n\n"
        f"Titel:\n{e.get('title','')}\n\n"
        f"Details:\n{e.get('details','')}\n\n"
        f"Referenz-ID: {e.get('related_id','')}"
    )

def install_entry_grid_navigation(root):
    def _grid_entries(master):
        out = []
        for w in master.winfo_children():
            try:
                if w.winfo_class() in ('Entry', 'TEntry', 'TCombobox'):
                    info = w.grid_info()
                    if info:
                        out.append((int(info.get('row', 0)), int(info.get('column', 0)), w))
            except Exception:
                pass
        return sorted(out)
    def move(widget, dx=0, dy=0):
        try:
            info = widget.grid_info()
            row = int(info.get('row', 0)); col = int(info.get('column', 0))
            for r, c, w in _grid_entries(widget.master):
                if r == row + dy and c == col + dx:
                    w.focus_set(); return 'break'
        except Exception:
            pass
        return None
    def bind_one(w):
        try:
            if w.winfo_class() in ('Entry', 'TEntry', 'TCombobox'):
                w.bind('<Right>', lambda e: move(e.widget, dx=1), add='+')
                w.bind('<Left>', lambda e: move(e.widget, dx=-1), add='+')
                w.bind('<Down>', lambda e: move(e.widget, dy=1), add='+')
                w.bind('<Up>', lambda e: move(e.widget, dy=-1), add='+')
                w.bind('<Tab>', lambda e: move(e.widget, dx=1), add='+')
                w.bind('<Shift-Tab>', lambda e: move(e.widget, dx=-1), add='+')
                w.bind('<ISO_Left_Tab>', lambda e: move(e.widget, dx=-1), add='+')
        except Exception:
            pass
        for ch in getattr(w, 'winfo_children', lambda: [])():
            bind_one(ch)
    bind_one(root)


# ---- BU32: zentrale Stichtagspflege-Synchronisation ----
def _parse_deadline_date(value):
    value = str(value or '').strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass
    return None

def _deadline_iso(value):
    d = _parse_deadline_date(value)
    return d.strftime('%Y-%m-%d') if d else ''

def deadline_year_file(year: int):
    return bin_dir() / 'Deadlines' / 'years' / f'deadlines_{int(year):04d}.json'

def legacy_deadline_year_file_v0431(year: int):
    return legacy_bin_dir_v0431() / 'Deadlines' / 'years' / f'deadlines_{int(year):04d}.json'

def deadline_fiscal_year_start(kind: str, period: str):
    try:
        kind = str(kind or '').strip().lower()
        period = str(period or '').strip()
        if kind in ('monthly', 'm'):
            y, m = map(int, period.split('-'))
            return y if m >= 10 else y - 1
        if kind in ('quarterly', 'q'):
            y_s, q_s = period.split('-Q')
            y = int(y_s); q = int(q_s)
            return y if q == 4 else y - 1
        if kind in ('yearly', 'j', 'y'):
            return int(period.split('-')[0])
    except Exception:
        pass
    d = date.today()
    return d.year if d.month >= 10 else d.year - 1

def deadline_kind_name(kind: str):
    k = str(kind or '').strip().lower()
    if k in ('m', 'month', 'monthly'):
        return 'monthly'
    if k in ('q', 'quarter', 'quarterly'):
        return 'quarterly'
    if k in ('j', 'y', 'year', 'yearly'):
        return 'yearly'
    return k

def load_deadline_year_for_period(kind: str, period: str):
    year = deadline_fiscal_year_start(kind, period)
    paths = [deadline_year_file(year)]
    try:
        legacy = legacy_deadline_year_file_v0431(year)
        if legacy not in paths:
            paths.append(legacy)
    except Exception:
        pass
    for path in paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def get_deadline_record(kind: str, period: str):
    data = load_deadline_year_for_period(kind, period)
    k = deadline_kind_name(kind)
    return data.get(k, {}).get(str(period), {}) if isinstance(data, dict) else {}

def get_deadline_cutoff(kind: str, period: str):
    rec = get_deadline_record(kind, period)
    return _deadline_iso(rec.get('dekade_close'))

def apply_deadline_cutoff_to_close_data(kind: str, period: str, data: dict):
    cutoff = get_deadline_cutoff(kind, period)
    if not cutoff or not isinstance(data, dict):
        return False
    changed = data.get('closing_cutoff_date') != cutoff
    data['closing_cutoff_date'] = cutoff
    for task in data.get('tasks', []) or []:
        if task.get('due_mode') == 'closing_cutoff' and task.get('due_date') != cutoff:
            task['due_date'] = cutoff
            changed = True
    return changed

def sync_tax_period_with_deadlines(period: str, data: dict):
    cutoff = get_deadline_cutoff('monthly', period)
    if not cutoff or not isinstance(data, dict):
        return False
    changed = False
    for report in data.get('reports', []) or []:
        if report.get('sync_with_calendar', False) and report.get('due_date') != cutoff:
            report['due_date'] = cutoff
            report.setdefault('history', []).append({
                'timestamp': now_iso(),
                'user': 'System',
                'action': 'Fälligkeit aus Stichtagspflege synchronisiert',
                'new_due_date': cutoff,
            })
            changed = True
    return changed


# ---- BU33b: Abschlusskalender-Stichtagssynchronisation ----
def deadline_period_file_path(module_dir: str, period: str):
    return bin_dir() / 'Closing' / module_dir / 'periods' / f'{period}.json'

def update_close_period_file_from_deadline(module_dir: str, period: str, cutoff_iso: str, extra_fields=None):
    """Aktualisiert eine bestehende Abschluss-Periodendatei und alle Aufgaben mit Abschluss-Stichtag."""
    p = deadline_period_file_path(module_dir, period)
    if not p.exists() or not cutoff_iso:
        return False
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return False
    changed = data.get('closing_cutoff_date') != cutoff_iso
    data['closing_cutoff_date'] = cutoff_iso
    for k, v in (extra_fields or {}).items():
        if v:
            if data.get(k) != v:
                data[k] = v
                changed = True
        elif k in data:
            data.pop(k, None)
            changed = True
    for task in data.get('tasks', []) or []:
        if task.get('due_mode') == 'closing_cutoff' and task.get('due_date') != cutoff_iso:
            task['due_date'] = cutoff_iso
            changed = True
    if changed:
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return changed


def format_deadline_cutoff_de(kind: str, period: str):
    """Liefert den gepflegten Abschluss-Stichtag im Format TT.MM.JJJJ für Anzeigen."""
    value = get_deadline_cutoff(kind, period) if 'get_deadline_cutoff' in globals() else ''
    d = _parse_deadline_date(value) if '_parse_deadline_date' in globals() else None
    return d.strftime('%d.%m.%Y') if d else ''

# ---- v0.432 Korrektur: globale Anzeigeformate und angelegte Zeitraumlogik ----
MIN_MONTH_PERIOD = '2026-05'
MIN_QUARTER_PERIOD = '2026-Q2'
MIN_YEAR_PERIOD = '2025-2026'
FISCAL_YEAR_START_MONTH = 10


def parse_date_de(value):
    value = str(value or '').strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except Exception:
            pass
    return None


def format_date_de(value):
    d = value if isinstance(value, date) else parse_date_de(value)
    return d.strftime('%d.%m.%Y') if d else ''


def fiscal_year_start_for_date_v0432(d=None):
    d = d or date.today()
    return d.year if d.month >= FISCAL_YEAR_START_MONTH else d.year - 1


def fiscal_year_key_v0432(start_year: int):
    return f"{start_year:04d}-{start_year + 1:04d}"


def format_fiscal_year_v0432(key_or_start):
    try:
        if isinstance(key_or_start, int):
            return f"{key_or_start:04d}/{key_or_start + 1:04d}"
        y1, y2 = map(int, str(key_or_start).split('-'))
        return f"{y1:04d}/{y2:04d}"
    except Exception:
        return str(key_or_start or '')


def month_key_v0432(d=None):
    d = d or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def quarter_key_v0432(d=None):
    d = d or date.today()
    q = (d.month - 1) // 3 + 1
    return f"{d.year:04d}-Q{q}"


def add_quarter_v0432(key: str, delta: int):
    y_s, q_s = str(key).split('-Q')
    y = int(y_s); q = int(q_s) + delta
    while q < 1:
        q += 4; y -= 1
    while q > 4:
        q -= 4; y += 1
    return f"{y:04d}-Q{q}"


def add_year_v0432(key: str, delta: int):
    y1, y2 = map(int, str(key).split('-'))
    return f"{y1 + delta:04d}-{y2 + delta:04d}"


def august_month_key_v0432(fy_start: int):
    return f"{fy_start + 1:04d}-08"


def august_cutoff_reached_v0432(fy_start: int, today=None):
    today = today or date.today()
    august = august_month_key_v0432(fy_start)
    cutoff = parse_date_de(get_deadline_cutoff('monthly', august)) if 'get_deadline_cutoff' in globals() else None
    if not cutoff:
        import calendar
        y, m = map(int, august.split('-'))
        cutoff = first_business_day_after(date(y, m, calendar.monthrange(y, m)[1]))
    return today >= cutoff


def max_month_period_v0432(today=None):
    today = today or date.today()
    fy = fiscal_year_start_for_date_v0432(today)
    return f"{fy + 2:04d}-09" if august_cutoff_reached_v0432(fy, today) else f"{fy + 1:04d}-09"


def max_quarter_period_v0432(today=None):
    today = today or date.today()
    fy = fiscal_year_start_for_date_v0432(today)
    return f"{fy + 2:04d}-Q3" if august_cutoff_reached_v0432(fy, today) else f"{fy + 1:04d}-Q3"


def max_year_period_v0432(today=None):
    today = today or date.today()
    fy = fiscal_year_start_for_date_v0432(today)
    return fiscal_year_key_v0432(fy + 1) if august_cutoff_reached_v0432(fy, today) else fiscal_year_key_v0432(fy)


def format_period_display(period: str, kind: str = ''):
    period = str(period or '').strip()
    kind = str(kind or '').lower()
    try:
        if kind in ('monthly', 'm') or re.fullmatch(r'\d{4}-\d{2}', period):
            y, m = map(int, period.split('-'))
            return f"{m:02d}/{str(y)[-2:]}"
        if kind in ('quarterly', 'q') or re.fullmatch(r'\d{4}-Q[1-4]', period):
            y_s, q_s = period.split('-Q')
            return f"Q{int(q_s)}/{str(int(y_s))[-2:]}"
        if kind in ('yearly', 'y', 'j') or re.fullmatch(r'\d{4}-\d{4}', period):
            return format_fiscal_year_v0432(period)
    except Exception:
        pass
    return period


def closing_period_dir_for_kind_v0432(kind: str):
    k = str(kind or '').lower()
    if k in ('monthly', 'm'):
        return bin_dir() / 'Closing' / 'MonthlyClose' / 'periods'
    if k in ('quarterly', 'q'):
        return bin_dir() / 'Closing' / 'QuarterlyClose' / 'periods'
    if k in ('yearly', 'y', 'j'):
        return bin_dir() / 'Closing' / 'YearlyClose' / 'periods'
    return None


def theoretical_periods_for_kind_v0432(kind: str, today=None, only_started=False):
    today = today or date.today()
    k = str(kind or '').lower()
    out = []
    if k in ('monthly', 'm'):
        cur = MIN_MONTH_PERIOD
        max_key = min(month_key_v0432(today), max_month_period_v0432(today)) if only_started else max_month_period_v0432(today)
        while cur <= max_key:
            out.append(cur); cur = add_month(cur, 1)
        return out
    if k in ('quarterly', 'q'):
        cur = MIN_QUARTER_PERIOD
        max_key = min(quarter_key_v0432(today), max_quarter_period_v0432(today)) if only_started else max_quarter_period_v0432(today)
        while cur <= max_key:
            out.append(cur); cur = add_quarter_v0432(cur, 1)
        return out
    if k in ('yearly', 'y', 'j'):
        cur = MIN_YEAR_PERIOD
        max_key = min(fiscal_year_key_v0432(fiscal_year_start_for_date_v0432(today)), max_year_period_v0432(today)) if only_started else max_year_period_v0432(today)
        while cur <= max_key:
            out.append(cur); cur = add_year_v0432(cur, 1)
        return out
    return []


def existing_periods_for_kind_v0432(kind: str, today=None, only_started=False, create_current_if_missing=False):
    allowed = theoretical_periods_for_kind_v0432(kind, today, only_started=only_started)
    allowed_set = set(allowed)
    folder = closing_period_dir_for_kind_v0432(kind)
    existing = []
    if folder and folder.exists():
        existing = sorted(p.stem for p in folder.glob('*.json') if p.stem in allowed_set)
    if create_current_if_missing and not existing and allowed:
        existing = [current_period_for_kind_v0432(kind, today)]
    return existing


def current_period_for_kind_v0432(kind: str, today=None):
    today = today or date.today()
    k = str(kind or '').lower()
    if k in ('monthly', 'm'):
        return min(max(month_key_v0432(today), MIN_MONTH_PERIOD), max_month_period_v0432(today))
    if k in ('quarterly', 'q'):
        return min(max(quarter_key_v0432(today), MIN_QUARTER_PERIOD), max_quarter_period_v0432(today))
    if k in ('yearly', 'y', 'j'):
        return min(max(fiscal_year_key_v0432(fiscal_year_start_for_date_v0432(today)), MIN_YEAR_PERIOD), max_year_period_v0432(today))
    return month_key_v0432(today)


def allowed_periods_for_kind_v0432(kind: str, today=None, only_started=False, existing_only=True):
    if existing_only:
        existing = existing_periods_for_kind_v0432(kind, today, only_started=only_started)
        if existing:
            return existing
    return theoretical_periods_for_kind_v0432(kind, today, only_started=only_started)


def period_allowed_v0432(kind: str, period: str, today=None, only_started=False, existing_only=True):
    return str(period) in set(allowed_periods_for_kind_v0432(kind, today, only_started=only_started, existing_only=existing_only))


def all_tax_periods():
    ensure_dirs()
    allowed = set(allowed_periods_for_kind_v0432('monthly', existing_only=False))
    return sorted(p.stem for p in (ensure_dirs()/"TaxReporting"/"periods").glob("*.json") if p.stem in allowed) or [current_period_for_kind_v0432('monthly')]


# ---- v0.432 Korrektur Paket 2: finale Anzeigeformat-Helfer ----
def parse_date_de(value):
    value = str(value or '').strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except Exception:
            pass
    return None

def format_date_de(value):
    d = value if isinstance(value, date) else parse_date_de(value)
    return d.strftime('%d.%m.%Y') if d else ''

def format_fiscal_year_v0432(key_or_start):
    try:
        if isinstance(key_or_start, int):
            return f"{key_or_start:04d}/{key_or_start + 1:04d}"
        y1, y2 = map(int, str(key_or_start).split('-'))
        return f"{y1:04d}/{y2:04d}"
    except Exception:
        return str(key_or_start or '')

def detect_period_kind(period: str):
    period = str(period or '').strip()
    if re.fullmatch(r'\d{4}-\d{2}', period): return 'monthly'
    if re.fullmatch(r'\d{4}-Q[1-4]', period): return 'quarterly'
    if re.fullmatch(r'\d{4}-\d{4}', period): return 'yearly'
    return ''

def format_period_display(period: str, kind: str = ''):
    period = str(period or '').strip(); kind = str(kind or '').lower()
    try:
        if kind in ('monthly','m') or re.fullmatch(r'\d{4}-\d{2}', period):
            y, m = map(int, period.split('-')); return f"{m:02d}/{str(y)[-2:]}"
        if kind in ('quarterly','q') or re.fullmatch(r'\d{4}-Q[1-4]', period):
            y, q = period.split('-Q'); return f"Q{int(q)}/{str(int(y))[-2:]}"
        if kind in ('yearly','y','j') or re.fullmatch(r'\d{4}-\d{4}', period):
            return format_fiscal_year_v0432(period)
    except Exception:
        pass
    return period

def format_any_period_display(period: str):
    return format_period_display(period, detect_period_kind(period))


# ---- v0.432 Korrektur Paket 2: finale Audit-Detailanzeige ----
def audit_entry_long_text(e):
    return (
        f"Zeitpunkt: {format_date_de(e.get('timestamp',''))}\n"
        f"Ereignis: {e.get('event_type','')}\n"
        f"Modul: {e.get('module','')}\n"
        f"Risiko: {e.get('risk','')}\n"
        f"Zeitraum: {format_any_period_display(e.get('period',''))}\n"
        f"Benutzer: {e.get('user_name','')} ({e.get('user_key','')})\n\n"
        f"Titel:\n{e.get('title','')}\n\n"
        f"Details:\n{e.get('details','')}\n\n"
        f"Referenz-ID: {e.get('related_id','')}"
    )


# ---- v0.435: Zuständigkeitspflege und modulübergreifend eindeutige Aufgaben-IDs ----
def responsibility_catalog_path():
    return ensure_dirs() / 'responsibility_catalog.json'

def load_responsibility_catalog():
    d = json_load(responsibility_catalog_path(), {'items': [], 'next': {'monthly': 1, 'quarterly': 1, 'yearly': 1, 'tax': 1}})
    d.setdefault('items', []); d.setdefault('next', {'monthly': 1, 'quarterly': 1, 'yearly': 1, 'tax': 1})
    return d

def save_responsibility_catalog_data(data):
    data.setdefault('items', []); data.setdefault('next', {'monthly': 1, 'quarterly': 1, 'yearly': 1, 'tax': 1})
    json_save(responsibility_catalog_path(), data)

def responsibility_prefix(kind):
    return {'monthly':'M', 'quarterly':'Q', 'yearly':'J', 'tax':'TAX'}.get(str(kind or '').lower(), 'A')

def next_responsibility_task_uid(cat, kind):
    prefix = responsibility_prefix(kind)
    used = {str(i.get('task_uid','')).strip() for i in cat.get('items', []) if str(i.get('task_uid','')).strip()}
    n = int(cat.setdefault('next', {}).get(kind, 1) or 1)
    while True:
        uid = f'{prefix}{n:03d}' if prefix != 'TAX' else f'TAX{n:03d}'
        n += 1
        if uid not in used:
            cat['next'][kind] = n
            return uid

def _resp_key(kind, title='', team='', type_id=''):
    return f"{kind}|{type_id or ''}|{team or ''}|{title or ''}"

def _closing_module_for_kind(kind):
    return {'monthly':'MonthlyClose', 'quarterly':'QuarterlyClose', 'yearly':'YearlyClose'}.get(deadline_kind_name(kind))

def _merge_resp(cat, item):
    item = dict(item); item['key'] = item.get('key') or _resp_key(item.get('kind'), item.get('title'), item.get('team'), item.get('type_id'))
    cur = next((x for x in cat.get('items', []) if x.get('key') == item['key']), None)
    if cur is None:
        if not item.get('task_uid'): item['task_uid'] = next_responsibility_task_uid(cat, item.get('kind'))
        cat.setdefault('items', []).append(item); return item
    for k, v in item.items():
        cur.setdefault(k, v)
        if cur.get(k) in ('', None) and v not in ('', None): cur[k] = v
    if not cur.get('task_uid'): cur['task_uid'] = next_responsibility_task_uid(cat, cur.get('kind'))
    return cur

def collect_responsibility_catalog(kind, include_tax_for_monthly=False):
    kind = deadline_kind_name(kind); cat = load_responsibility_catalog(); module = _closing_module_for_kind(kind)
    if module:
        period_dir = bin_dir() / 'Closing' / module / 'periods'
        if period_dir.exists():
            for p in sorted(period_dir.glob('*.json')):
                try: data = json.loads(p.read_text(encoding='utf-8'))
                except Exception: continue
                for t in data.get('tasks', []) or []:
                    if t.get('deleted'): continue
                    _merge_resp(cat, {'kind': kind, 'source': 'closing_period', 'period': p.stem, 'type_id': t.get('id',''), 'team': t.get('team',''), 'title': t.get('title',''), 'task_uid': t.get('task_uid',''), 'owner': t.get('owner',''), 'owner_user_key': t.get('owner_user_key',''), 'sync_with_calendar': True})
    if include_tax_for_monthly and kind == 'monthly':
        cfg = load_tax_config()
        for rt in cfg.get('report_types', []) or []:
            tid = rt.get('id') or rt.get('title','')
            _merge_resp(cat, {'kind': 'tax', 'source': 'tax_config', 'type_id': tid, 'team': 'Steuermeldung', 'title': rt.get('title', tid), 'task_uid': rt.get('task_uid',''), 'owner': rt.get('owner',''), 'owner_user_key': rt.get('owner_user_key',''), 'sync_with_calendar': rt.get('sync_with_calendar', True)})
    used = set()
    for it in cat.get('items', []):
        uid = str(it.get('task_uid','')).strip()
        if not uid or uid in used: it['task_uid'] = next_responsibility_task_uid(cat, it.get('kind'))
        used.add(it['task_uid'])
    save_responsibility_catalog_data(cat)
    wanted = {kind} | ({'tax'} if include_tax_for_monthly and kind == 'monthly' else set())
    return sorted([x for x in cat.get('items', []) if x.get('kind') in wanted], key=lambda x:(x.get('kind',''), x.get('team',''), x.get('title','')))

def save_responsibility_rows(rows):
    cat = load_responsibility_catalog(); by_key = {x.get('key'): x for x in cat.get('items', [])}; seen=set(); changed=0
    for row in rows:
        key = row.get('key') or _resp_key(row.get('kind'), row.get('title'), row.get('team'), row.get('type_id'))
        item = by_key.get(key)
        if item is None: item={'key':key}; cat.setdefault('items', []).append(item)
        uid=str(row.get('task_uid','')).strip()
        if not uid or uid in seen: uid=next_responsibility_task_uid(cat, row.get('kind'))
        seen.add(uid); item.update(row); item['key']=key; item['task_uid']=uid
        changed += _sync_responsibility_row(item)
    save_responsibility_catalog_data(cat); return changed

def _sync_responsibility_row(row):
    row = normalize_responsibility_row(row, tax_group_shared_uid_from_cfg(load_tax_config())) if 'normalize_responsibility_row' in globals() else dict(row or {})
    kind=row.get('kind'); changed=0
    if is_tax_group_member(row.get('type_id'), row.get('title')) or row.get('responsibility_title') == TAX_GROUP_SHARED_TITLE:
        return _sync_tax_group_targets(row) if '_sync_tax_group_targets' in globals() else 0
    module = _closing_module_for_kind(kind)
    if not module: return 0
    period_dir = bin_dir() / 'Closing' / module / 'periods'
    for p in period_dir.glob('*.json') if period_dir.exists() else []:
        try: data=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        fch=False
        for t in data.get('tasks', []) or []:
            if t.get('task_uid') == row.get('task_uid') or (t.get('title') == row.get('title') and t.get('team') == row.get('team')) or (t.get('id') and t.get('id') == row.get('type_id')):
                for k,v in [('task_uid',row.get('task_uid','')),('owner',row.get('owner','')),('owner_user_key',row.get('owner_user_key',''))]:
                    if t.get(k) != v: t[k]=v; fch=True
        if fch: p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); changed += 1
    return changed


# ---- v0.435 FINAL: Aufgabenverknüpfung, Mehrfachpräfixe und gemeinsame Zuständigkeit ----
def responsibility_uid_prefix(task_uid):
    m = re.match(r'^([A-Z]+)', str(task_uid or '').strip().upper())
    return m.group(1) if m else ''

def responsibility_uid_number(task_uid):
    m = re.search(r'(\d+)$', str(task_uid or '').strip())
    return int(m.group(1)) if m else None

def responsibility_prefix(kind):
    return {'monthly':'M', 'quarterly':'Q', 'yearly':'J', 'tax':'M', 'all':'A'}.get(str(kind or '').lower(), 'A')

def responsibility_uid_letters(task_uid, fallback_kind=''):
    letters = {c for c in responsibility_uid_prefix(task_uid) if c in {'M','Q','J'}}
    if letters:
        return letters
    return {'monthly': {'M'}, 'quarterly': {'Q'}, 'yearly': {'J'}, 'tax': {'M'}}.get(deadline_kind_name(fallback_kind), set())

def responsibility_row_visible_for_kind(row, target_kind):
    target = deadline_kind_name(target_kind)
    if target == 'all':
        return True
    letters = responsibility_uid_letters(row.get('task_uid',''), row.get('kind', target))
    return responsibility_prefix(target) in letters

def responsibility_combined_uid(prefix_letters, preferred_numbers=None, cat=None):
    prefix = ''.join(c for c in 'MQJ' if c in set(prefix_letters or [])) or 'M'
    nums = [int(n) for n in (preferred_numbers or []) if n]
    return f'{prefix}{(min(nums) if nums else 1):03d}'

def normalize_responsibility_row(row, shared_tax_uid=''):
    row = dict(row or {})
    row['kind'] = deadline_kind_name(row.get('kind'))
    if is_tax_group_member(row.get('type_id',''), row.get('title','')):
        row['task_uid'] = str(shared_tax_uid or row.get('task_uid') or tax_group_shared_uid_from_cfg(load_tax_config())).strip() or TAX_GROUP_SHARED_DEFAULT_UID
        row['responsibility_title'] = TAX_GROUP_SHARED_TITLE
        row['responsibility_team'] = TAX_GROUP_SHARED_TEAM
    return row

def _tax_group_match(value):
    return _tax_alias_key(value) in TAX_GROUP_MEMBER_IDS or _tax_alias_key(value) in TAX_GROUP_MEMBER_TITLES

def _sync_tax_group_targets(row):
    changed = 0
    cfg = load_tax_config(); cfg, _ = normalize_tax_config(cfg)
    shared_uid = str(row.get('task_uid','') or tax_group_shared_uid_from_cfg(cfg)).strip() or TAX_GROUP_SHARED_DEFAULT_UID
    owner_user_key = str(row.get('owner_user_key','') or '').strip()
    reviewer_user_key = str(row.get('reviewer_user_key','') or '').strip()
    sync_with_calendar = bool(row.get('sync_with_calendar', True))
    owner_name = str(row.get('owner','') or '').strip()
    cfg_changed = False
    for rt in cfg.get('report_types',[]) or []:
        if is_tax_group_member(rt.get('id'), rt.get('title')):
            for key, value in [('task_uid', shared_uid), ('owner_user_key', owner_user_key), ('reviewer_user_key', reviewer_user_key), ('sync_with_calendar', sync_with_calendar), ('responsibility_title', TAX_GROUP_SHARED_TITLE), ('responsibility_team', TAX_GROUP_SHARED_TEAM)]:
                if rt.get(key) != value:
                    rt[key] = value; cfg_changed = True
    if cfg_changed:
        save_tax_config(cfg); changed += 1
    period_dir = ensure_dirs() / 'TaxReporting' / 'periods'
    for p in period_dir.glob('*.json') if period_dir.exists() else []:
        try: data = json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        fch = False
        for report in data.get('reports',[]) or []:
            if is_tax_group_member(report.get('type_id'), report.get('title')):
                for key, value in [('task_uid', shared_uid), ('owner_user_key', owner_user_key), ('reviewer_user_key', reviewer_user_key), ('sync_with_calendar', sync_with_calendar)]:
                    if report.get(key) != value:
                        report[key] = value; fch = True
        if fch:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); changed += 1
    for module in ('MonthlyClose','QuarterlyClose','YearlyClose'):
        period_dir = bin_dir() / 'Closing' / module / 'periods'
        for p in period_dir.glob('*.json') if period_dir.exists() else []:
            try: data = json.loads(p.read_text(encoding='utf-8'))
            except Exception: continue
            fch = False
            for task in data.get('tasks',[]) or []:
                if _tax_group_match(task.get('id')) or _tax_group_match(task.get('title')) or str(task.get('task_uid','') or '').strip() == shared_uid:
                    for key, value in [('task_uid', shared_uid), ('owner', owner_name), ('owner_user_key', owner_user_key)]:
                        if task.get(key) != value:
                            task[key] = value; fch = True
            if fch:
                p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); changed += 1
    return changed

def collect_responsibility_catalog(kind, include_tax_for_monthly=False):
    kind = deadline_kind_name(kind)
    cat = load_responsibility_catalog()
    cfg = load_tax_config()
    shared_uid = tax_group_shared_uid_from_cfg(cfg)
    scan_kinds = ['monthly','quarterly','yearly'] if kind == 'all' else [kind]
    for scan_kind in scan_kinds:
        module = _closing_module_for_kind(scan_kind) if '_closing_module_for_kind' in globals() else {'monthly':'MonthlyClose','quarterly':'QuarterlyClose','yearly':'YearlyClose'}.get(scan_kind)
        period_dir = bin_dir() / 'Closing' / module / 'periods' if module else None
        if period_dir and period_dir.exists():
            for p in sorted(period_dir.glob('*.json')):
                try: data=json.loads(p.read_text(encoding='utf-8'))
                except Exception: continue
                for t in data.get('tasks', []) or []:
                    if t.get('deleted'): continue
                    item = normalize_responsibility_row({'kind':scan_kind,'source':'closing_period','period':p.stem,'type_id':t.get('id',''),'team':t.get('team',''),'title':t.get('title',''),'task_uid':t.get('task_uid','') or f"{responsibility_prefix(scan_kind)}001",'owner':t.get('owner',''),'owner_user_key':t.get('owner_user_key',''),'sync_with_calendar':True}, shared_uid)
                    _merge_resp(cat, item)
    if include_tax_for_monthly and kind in ('monthly','all'):
        for rt in cfg.get('report_types', []) or []:
            item = normalize_responsibility_row({'kind':'tax','source':'tax_config','type_id':rt.get('id') or rt.get('title',''),'team':rt.get('responsibility_team') or TAX_GROUP_SHARED_TEAM,'title':rt.get('title', rt.get('id','')),'task_uid':rt.get('task_uid',''),'owner':rt.get('owner',''),'owner_user_key':rt.get('owner_user_key',''),'sync_with_calendar':rt.get('sync_with_calendar', True)}, shared_uid)
            _merge_resp(cat, item)
    used = set(); changed = False; normalized_items = []
    for item in cat.get('items', []):
        norm = normalize_responsibility_row(item, shared_uid)
        uid = str(norm.get('task_uid','') or '').strip()
        if not uid:
            norm['task_uid'] = next_responsibility_task_uid(cat, norm.get('kind'))
        elif uid in used and not is_tax_group_member(norm.get('type_id'), norm.get('title')):
            norm['task_uid'] = next_responsibility_task_uid(cat, norm.get('kind'))
        used.add(norm.get('task_uid'))
        if norm != item:
            changed = True
        normalized_items.append(norm)
    cat['items'] = normalized_items
    if changed:
        save_responsibility_catalog_data(cat)
    rows = [normalize_responsibility_row(x, shared_uid) for x in cat.get('items', []) if not x.get('deleted') and responsibility_row_visible_for_kind(normalize_responsibility_row(x, shared_uid), kind)]
    return sorted(rows, key=lambda x:(responsibility_uid_prefix(x.get('task_uid','')), responsibility_uid_number(x.get('task_uid','')) or 0, x.get('kind',''), x.get('team',''), x.get('title','')))

def save_responsibility_rows(rows):
    cat = load_responsibility_catalog(); cfg = load_tax_config(); shared_uid = tax_group_shared_uid_from_cfg(cfg); by_key={x.get('key'):x for x in cat.get('items', []) if x.get('key')}; changed=0
    for row in rows or []:
        row = normalize_responsibility_row(row, shared_uid)
        key=row.get('key') or f"{row.get('kind')}|{row.get('type_id','')}|{row.get('team','')}|{row.get('title','')}"
        item=by_key.get(key)
        if item is None:
            item={'key':key}; cat.setdefault('items', []).append(item); by_key[key]=item
        item.update(row); item['key']=key; item['task_uid']=str(row.get('task_uid','')).strip() or item.get('task_uid') or (shared_uid if is_tax_group_member(row.get('type_id'), row.get('title')) else f"{responsibility_prefix(row.get('kind'))}001")
        try: changed += _sync_responsibility_row(item)
        except Exception: pass
    save_responsibility_catalog_data(cat); return changed

def delete_responsibility_rows(rows):
    cat=load_responsibility_catalog(); cfg = load_tax_config(); shared_uid = tax_group_shared_uid_from_cfg(cfg); by_key={x.get('key'):x for x in cat.get('items', []) if x.get('key')}; count=0
    for row in rows or []:
        row = normalize_responsibility_row(row, shared_uid)
        key=row.get('key') or f"{row.get('kind')}|{row.get('type_id','')}|{row.get('team','')}|{row.get('title','')}"
        item=by_key.get(key)
        if item is None:
            item=dict(row); item['key']=key; cat.setdefault('items', []).append(item)
        item['deleted']=True; count+=1
    save_responsibility_catalog_data(cat); return count
