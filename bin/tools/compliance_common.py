
import json, os, subprocess, re, webbrowser
from pathlib import Path
from datetime import datetime, date
from urllib.parse import quote
BG="#E8EEF5"; HEADER="#D3DEE9"; BLUE="#004B93"; RED="#E30613"; ORANGE="#F59E0B"; GREEN="#16A34A"; DARK_GREEN="#047857"; TEXT="#182431"; TEXT2="#445364"; WHITE="#FFFFFF"; GREY="#B9C3CF"
ROLE_E1="E1 - Standard"; ROLE_E2="E2 - Erweitert"; ROLE_E3="E3 - Administrator"; ROLE_E4="E4 - System-Administrator"
ROLE_RANK={ROLE_E1:1,ROLE_E2:2,ROLE_E3:3,ROLE_E4:4,"E1":1,"E2":2,"E3":3,"E4":4,"Administrator":3,"System-Administrator":4,"Wagnerm":4}
EVENT_ORDER=["Aufgabe geändert","Aufgabe gelöscht","Aufgaben-ID geändert","Fälligkeit geändert","Zuständigkeit geändert","Nachweis hinzugefügt/geändert/entfernt","PDF-Bericht erstellt","Excel-Bericht erstellt","Benutzer angelegt","Berechtigung geändert","Auto-Mail ein-/ausgeschaltet","fehlgeschlagener E-Mail-Versand","Benutzer gelöscht","Benutzer geändert"]
CRITICAL_EVENTS={"Zeitraum wieder geöffnet","Änderungen nach Wiederöffnung","fehlgeschlagener Pflicht-E-Mail","Nachweis nach Abschluss geändert"}
def script_dir():
    here=Path(__file__).resolve(); return here.parent.parent if here.parent.name.lower()=="tools" else here.parent
def bin_dir(): return script_dir()/"bin"
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
    import calendar; y,m=map(int,period.split('-')); return f"{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}"
def ensure_tax_period(period):
    cfg=load_tax_config(); d=json_load(tax_period_path(period),{"period":period,"created_at":now_iso(),"reports":[]}); d.setdefault("reports",[]); ex={r.get('type_id'):r for r in d['reports']}; ch=False
    for rt in cfg.get('report_types',[]):
        if not rt.get('active',True): continue
        rid=rt.get('id') or rt.get('title')
        if rid not in ex:
            d['reports'].append({"type_id":rid,"title":rt.get('title',rid),"period":period,"status":"Offen","due_date":default_due(period),"owner_user_key":rt.get('owner_user_key',''),"reviewer_user_key":rt.get('reviewer_user_key',''),"reported_at":"","approved_at":"","comments":[],"attachments":[],"history":[],"evidence_required":rt.get('evidence_required',True),"approval_required":rt.get('approval_required',True),"four_eye":rt.get('four_eye',False),"sync_with_calendar":rt.get('sync_with_calendar',False),"task_uid":rt.get('task_uid','')}); ch=True
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
