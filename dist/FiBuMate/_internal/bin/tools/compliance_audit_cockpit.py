import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

def zfont(app, size=12, weight=None):
    """v0.434: Scharfe, direkte Modulschrift mit Bereichszoom."""
    try:
        scale = float(getattr(app, "current_scope_zoom", 1.0) or 1.0)
        final = max(9, int(round(float(size) * 1.22 * scale)))
    except Exception:
        final = int(size)
    return ("Segoe UI", final, weight) if weight else ("Segoe UI", final)



def _parse_audit_date(value):
    from datetime import datetime
    raw = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19] if "T" in raw else raw[:10], fmt).date()
        except Exception:
            pass
    return None

def _fiscal_period_for_date(value):
    d = _parse_audit_date(value)
    if not d:
        return ""
    start = d.year if d.month >= 10 else d.year - 1
    return f"GJ {start}/{start + 1}"

def normalize_audit_period_value(period, timestamp=None):
    """v0.435: Geschäftsjahre einheitlich als GJ JJJJ/JJJJ darstellen und erkannte Fehlzuordnungen korrigieren."""
    import re
    raw = str(period or "").strip()
    ts_period = _fiscal_period_for_date(timestamp)
    m = re.fullmatch(r"(?:GJ\s*)?(\d{4})/(\d{4})", raw)
    if m:
        normalized = f"GJ {m.group(1)}/{m.group(2)}"
        # bekannte Fehlzuordnung: Ereignisse am 30.05.2026 gehören ins GJ 2025/2026, nicht GJ 2026/2027.
        if str(timestamp or "").startswith(("2026-05-30", "30.05.2026")) and normalized == "GJ 2026/2027":
            return "GJ 2025/2026"
        return normalized
    if raw:
        try:
            if hasattr(cc, "format_any_period_display"):
                formatted = cc.format_any_period_display(raw)
                if formatted:
                    return formatted
        except Exception:
            pass
    return ts_period or raw

def save_audit_if_possible(data):
    try:
        if hasattr(cc, "save_audit"):
            cc.save_audit(data)
            return
    except Exception:
        pass
    for attr in ("AUDIT_PATH", "AUDIT_LOG_PATH", "AUDIT_FILE"):
        try:
            path = getattr(cc, attr, None)
            if path:
                import json
                Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return
        except Exception:
            pass

class AuditCockpitUI:
    def __init__(self, app):
        self.app=app; self.root=app.root; self.canvas=app.canvas
        self.filter_text=tk.StringVar(); self.risk=tk.StringVar(value="Alle"); self.event=tk.StringVar(value="Alle")
        self.frame=tk.Frame(self.root,bg=cc.BG); self.app.widget_items.append(self.frame)
        self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(420,self.canvas.winfo_height()-172))
        self.render()
    def format_ts(self, value):
        return cc.format_date_de(value) if hasattr(cc,"format_date_de") else str(value or "")
    def format_period(self, value, timestamp=None):
        try:
            return normalize_audit_period_value(value, timestamp)
        except Exception:
            return cc.format_any_period_display(value) if hasattr(cc,"format_any_period_display") else str(value or "")
    def visible_entries(self):
        data=cc.load_audit().get("entries",[]); out=[]
        for e in data:
            if e.get("archived"): continue
            if not cc.can_admin(self.app):
                if e.get("user_key") != cc.user_key(self.app) and not e.get("public", False): continue
                if e.get("event_type") in ("Benutzer angelegt","Benutzer gelöscht","Benutzer geändert","Berechtigung geändert"): continue
            txt=self.filter_text.get().strip().lower(); blob=" ".join(str(e.get(k,"")) for k in e.keys()).lower()
            if txt and txt not in blob: continue
            if self.risk.get()!="Alle" and e.get("risk")!=self.risk.get(): continue
            if self.event.get()!="Alle" and e.get("event_type")!=self.event.get(): continue
            period=str(e.get("period","") or "")
            try:
                kind=cc.detect_period_kind(period) if hasattr(cc,"detect_period_kind") else ""
                if kind and hasattr(cc,"period_allowed_v0432") and not cc.period_allowed_v0432(kind, period, existing_only=False):
                    continue
            except Exception:
                pass
            out.append(e)
        return out
    def render(self):
        for w in self.frame.winfo_children(): w.destroy()
        entries=self.visible_entries(); critical=sum(1 for e in entries if e.get("risk") in ("Hoch","Kritisch") or e.get("event_type") in cc.CRITICAL_EVENTS)
        top=tk.Frame(self.frame,bg=cc.BG); top.pack(fill="x",padx=24,pady=12)
        for title,val,col in [("Ereignisse",len(entries),cc.BLUE),("Kritisch",critical,cc.RED),("Benutzer",len(set(e.get('user_key') for e in entries)),cc.ORANGE),("Module",len(set(e.get('module') for e in entries)),cc.DARK_GREEN)]:
            card=tk.Frame(top,bg=col,width=150,height=60); card.pack(side="left",padx=6); card.pack_propagate(False)
            tk.Label(card,text=str(val),bg=col,fg="white",font=zfont(self.app, 17, "bold")).pack(); tk.Label(card,text=title,bg=col,fg="white",font=zfont(self.app, 11, "bold")).pack()
        btns=tk.Frame(top,bg=cc.BG); btns.pack(side="right")
        if cc.can_admin(self.app):
            tk.Button(btns,text="Archivieren",command=self.archive_visible,bg=cc.BLUE,fg="white",bd=0,padx=12,pady=6).pack(side="left",padx=4)
            tk.Button(btns,text="PDF-Bericht",command=self.export_pdf,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=12,pady=6).pack(side="left",padx=4)
        filt=tk.Frame(self.frame,bg=cc.BG); filt.pack(fill="x",padx=24,pady=(0,8))
        tk.Label(filt,text="Suche",bg=cc.BG,fg=cc.TEXT,font=zfont(self.app, 12, "bold")).pack(side="left")
        tk.Entry(filt,textvariable=self.filter_text,width=32,bg=cc.WHITE,font=zfont(self.app, 12)).pack(side="left",padx=6)
        ttk.Combobox(filt,textvariable=self.risk,values=["Alle","Info","Niedrig","Mittel","Hoch","Kritisch"],state="readonly",width=12).pack(side="left",padx=6)
        ttk.Combobox(filt,textvariable=self.event,values=["Alle"]+cc.EVENT_ORDER,state="readonly",width=28).pack(side="left",padx=6)
        tk.Button(filt,text="Filter anwenden",command=self.render,bg=cc.BLUE,fg="white",bd=0,padx=10).pack(side="left",padx=6)
        outer=tk.Frame(self.frame,bg=cc.WHITE,bd=1,relief="solid"); outer.pack(fill="both",expand=True,padx=24,pady=(0,12))
        canvas=tk.Canvas(outer,bg=cc.WHITE,highlightthickness=0); sb=tk.Scrollbar(outer,orient="vertical",command=canvas.yview); table=tk.Frame(canvas,bg=cc.WHITE); win=canvas.create_window((0,0),window=table,anchor="nw")
        def upd(e=None): canvas.itemconfigure(win,width=max(1,canvas.winfo_width())); canvas.configure(scrollregion=canvas.bbox("all"))
        table.bind("<Configure>",upd); canvas.bind("<Configure>",upd); canvas.configure(yscrollcommand=sb.set); canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        headers=["Zeitpunkt","Ereignis","Modul","Risiko","Zeitraum","Benutzer","Details"]
        for c,h in enumerate(headers): tk.Label(table,text=h,bg=cc.HEADER,fg=cc.TEXT,font=zfont(self.app, 12, "bold"),padx=6,pady=6).grid(row=0,column=c,sticky="nsew",padx=1,pady=1)
        for r,e in enumerate(entries,1):
            vals=[self.format_ts(e.get("timestamp","")),e.get("event_type",""),e.get("module",""),e.get("risk",""),self.format_period(e.get("period",""), e.get("timestamp","")),e.get("user_name","")]
            for c,v in enumerate(vals): tk.Label(table,text=v,bg=cc.WHITE,fg=cc.TEXT,font=zfont(self.app, 12),padx=6,pady=5,anchor="w",wraplength=220).grid(row=r,column=c,sticky="nsew",padx=1,pady=1)
            tk.Button(table,text="öffnen",font=zfont(self.app, 12, "bold"),command=lambda ee=e: self.show_details(ee),bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=6,pady=5).grid(row=r,column=6,sticky="nsew",padx=1,pady=1)
        self.app.active_scroll_canvas=canvas
    def show_details(self, entry):
        win=tk.Toplevel(self.root); win.title("Audit-Details"); win.geometry("760x520"); win.configure(bg=cc.BG); win.transient(self.root)
        txt=tk.Text(win,wrap="word",bg=cc.WHITE,fg=cc.TEXT,font=zfont(self.app, 12),padx=12,pady=12); txt.pack(fill="both",expand=True,padx=14,pady=14)
        txt.insert("1.0", cc.audit_entry_long_text(entry)); txt.configure(state="disabled")
        tk.Button(win,text="Schließen",command=win.destroy,bg=cc.BLUE,fg="white",bd=0,padx=14,pady=7).pack(anchor="e",padx=14,pady=(0,14))
    def archive_visible(self):
        entries=self.visible_entries()
        if not entries: messagebox.showinfo("Archivieren","Keine Einträge zum Archivieren."); return
        note=simpledialog.askstring("Archivieren","Archivierungsnotiz:",parent=self.root) or "Manuelle Archivierung"
        if not messagebox.askyesno("Archivieren", f"{len(entries)} sichtbare Audit-Einträge archivieren?\n\nDie Einträge werden nicht gelöscht."): return
        archive_file=cc.archive_audit_entries(entries,self.app,note); messagebox.showinfo("Archiviert", f"Archiv erstellt:\n{archive_file.name}"); self.render()
    def export_pdf(self):
        entries=self.visible_entries(); path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile="Audit-Bericht.pdf")
        if not path: return
        rows=[["Zeitpunkt","Ereignis","Modul","Risiko","Zeitraum","Benutzer","Details"]]+[[self.format_ts(e.get("timestamp")),e.get("event_type"),e.get("module"),e.get("risk"),self.format_period(e.get("period"), e.get("timestamp")),e.get("user_name"),e.get("details")] for e in entries]
        cc.write_simple_pdf(path,"Audit-Bericht",rows); cc.log_audit(self.app,"PDF-Bericht erstellt","Audit-Cockpit",Path(path).name,path,"Info",public=False)
        if messagebox.askyesno("PDF erstellt","PDF öffnen?"): cc.open_path(path)
def render(app): AuditCockpitUI(app)
