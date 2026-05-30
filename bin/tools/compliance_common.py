
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
def default_tax_config():
    return {"report_types":[{"id":"ZM","title":"ZM","task_uid":"MQ002","active":True,"evidence_required":True,"approval_required":True,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True},{"id":"Z4","title":"Z4","task_uid":"MQ001","active":True,"evidence_required":True,"approval_required":True,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True},{"id":"Z5a","title":"Z5a","task_uid":"MQ003","active":True,"evidence_required":True,"approval_required":True,"four_eye":False,"owner_user_key":"","reviewer_user_key":"","sync_with_calendar":True}],"warning_days":{"yellow":10,"orange":5},"next_task_uid":1}
def load_tax_config():
    d=json_load(tax_config_path(),default_tax_config()); d.setdefault("report_types",[]); d.setdefault("next_task_uid",1)
    for r in d["report_types"]:
        r.setdefault("task_uid",r.get("id","")); r.setdefault("active",True); r.setdefault("evidence_required",True); r.setdefault("approval_required",True); r.setdefault("four_eye",False); r.setdefault("owner_user_key",""); r.setdefault("reviewer_user_key",""); r.setdefault("sync_with_calendar",False)
    return d
def save_tax_config(d): json_save(tax_config_path(),d)
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
    cfg=load_tax_config(); d=json_load(tax_period_path(period),{"period":period,"created_at":now_iso(),"reports":[]}); d.setdefault("reports",[]); ex={r.get('type_id'):r for r in d['reports']}; ch=False
    for rt in cfg.get('report_types',[]):
        if not rt.get('active',True): continue
        rid=rt.get('id') or rt.get('title')
        if rid not in ex:
            d['reports'].append({"type_id":rid,"title":rt.get('title',rid),"period":period,"status":"Offen","due_date":default_due(period),"owner_user_key":rt.get('owner_user_key',''),"reviewer_user_key":rt.get('reviewer_user_key',''),"reported_at":"","approved_at":"","comments":[],"attachments":[],"history":[],"evidence_required":rt.get('evidence_required',True),"approval_required":rt.get('approval_required',True),"four_eye":rt.get('four_eye',False),"sync_with_calendar":rt.get('sync_with_calendar',False),"task_uid":rt.get('task_uid','')}); ch=True
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
