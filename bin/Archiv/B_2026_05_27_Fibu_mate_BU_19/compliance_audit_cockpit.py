
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

class AuditCockpitUI:
    def __init__(self, app):
        self.app=app; self.root=app.root; self.canvas=app.canvas
        self.filter_text=tk.StringVar(); self.risk=tk.StringVar(value="Alle"); self.event=tk.StringVar(value="Alle")
        self.frame=tk.Frame(self.root,bg=cc.BG); self.app.widget_items.append(self.frame)
        self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(420,self.canvas.winfo_height()-172))
        self.render()
    def visible_entries(self):
        data=cc.load_audit().get("entries",[])
        out=[]
        for e in data:
            if e.get("archived"): continue
            if not cc.can_admin(self.app):
                if e.get("user_key") != cc.user_key(self.app) and not e.get("public", False): continue
                if e.get("event_type") in ("Benutzer angelegt","Benutzer gelöscht","Benutzer geändert","Berechtigung geändert"): continue
            txt=self.filter_text.get().strip().lower()
            blob=" ".join(str(e.get(k,"")) for k in e.keys()).lower()
            if txt and txt not in blob: continue
            if self.risk.get()!="Alle" and e.get("risk")!=self.risk.get(): continue
            if self.event.get()!="Alle" and e.get("event_type")!=self.event.get(): continue
            out.append(e)
        return out
    def render(self):
        for w in self.frame.winfo_children(): w.destroy()
        entries=self.visible_entries(); critical=sum(1 for e in entries if e.get("risk") in ("Hoch","Kritisch") or e.get("event_type") in cc.CRITICAL_EVENTS)
        top=tk.Frame(self.frame,bg=cc.BG); top.pack(fill="x",padx=24,pady=12)
        for title,val,col in [("Ereignisse",len(entries),cc.BLUE),("Kritisch",critical,cc.RED),("Benutzer",len(set(e.get('user_key') for e in entries)),cc.ORANGE),("Module",len(set(e.get('module') for e in entries)),cc.DARK_GREEN)]:
            card=tk.Frame(top,bg=col,width=150,height=60); card.pack(side="left",padx=6); card.pack_propagate(False)
            tk.Label(card,text=str(val),bg=col,fg="white",font=("Segoe UI",17,"bold")).pack(); tk.Label(card,text=title,bg=col,fg="white",font=("Segoe UI",9,"bold")).pack()
        btns=tk.Frame(top,bg=cc.BG); btns.pack(side="right")
        if cc.can_admin(self.app):
            tk.Button(btns,text="Archivieren",command=self.archive_visible,bg=cc.BLUE,fg="white",bd=0,padx=12,pady=6).pack(side="left",padx=4)
            tk.Button(btns,text="PDF-Bericht",command=self.export_pdf,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=12,pady=6).pack(side="left",padx=4)
        filt=tk.Frame(self.frame,bg=cc.BG); filt.pack(fill="x",padx=24,pady=(0,8))
        tk.Label(filt,text="Suche",bg=cc.BG,fg=cc.TEXT,font=("Segoe UI",10,"bold")).pack(side="left")
        tk.Entry(filt,textvariable=self.filter_text,width=32,bg=cc.WHITE).pack(side="left",padx=6)
        ttk.Combobox(filt,textvariable=self.risk,values=["Alle","Info","Niedrig","Mittel","Hoch","Kritisch"],state="readonly",width=12).pack(side="left",padx=6)
        ttk.Combobox(filt,textvariable=self.event,values=["Alle"]+cc.EVENT_ORDER,state="readonly",width=28).pack(side="left",padx=6)
        tk.Button(filt,text="Filter anwenden",command=self.render,bg=cc.BLUE,fg="white",bd=0,padx=10).pack(side="left",padx=6)
        outer=tk.Frame(self.frame,bg=cc.WHITE,bd=1,relief="solid"); outer.pack(fill="both",expand=True,padx=24,pady=(0,12))
        canvas=tk.Canvas(outer,bg=cc.WHITE,highlightthickness=0); sb=tk.Scrollbar(outer,orient="vertical",command=canvas.yview); table=tk.Frame(canvas,bg=cc.WHITE); win=canvas.create_window((0,0),window=table,anchor="nw")
        def upd(e=None):
            canvas.itemconfigure(win,width=max(1,canvas.winfo_width()))
            canvas.configure(scrollregion=canvas.bbox("all"))
            try:
                bbox=canvas.bbox("all"); overflow=bool(bbox and (bbox[3]-bbox[1]) > canvas.winfo_height()+2)
                if overflow:
                    if not sb.winfo_ismapped(): sb.pack(side="right",fill="y")
                    self.app.active_scroll_canvas=canvas
                else:
                    if sb.winfo_ismapped(): sb.pack_forget()
            except Exception: pass
        table.bind("<Configure>",upd); canvas.bind("<Configure>",upd); canvas.configure(yscrollcommand=sb.set); canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        headers=["Zeitpunkt","Ereignis","Modul","Risiko","Zeitraum","Benutzer","Details"]
        for c,h in enumerate(headers): tk.Label(table,text=h,bg=cc.HEADER,fg=cc.TEXT,font=("Segoe UI",10,"bold"),padx=6,pady=6).grid(row=0,column=c,sticky="nsew",padx=1,pady=1)
        for r,e in enumerate(entries,1):
            vals=[e.get("timestamp",""),e.get("event_type",""),e.get("module",""),e.get("risk",""),e.get("period",""),e.get("user_name",""),e.get("details","")]
            for c,v in enumerate(vals): tk.Label(table,text=v,bg=cc.WHITE,fg=cc.TEXT,padx=6,pady=5,anchor="w",wraplength=260).grid(row=r,column=c,sticky="nsew",padx=1,pady=1)
        self.app.active_scroll_canvas=canvas
    def archive_visible(self):
        entries=self.visible_entries()
        if not entries: messagebox.showinfo("Archivieren","Keine Einträge zum Archivieren."); return
        note=simpledialog.askstring("Archivieren","Archivierungsnotiz:",parent=self.root) or "Manuelle Archivierung"
        if not messagebox.askyesno("Archivieren", f"{len(entries)} sichtbare Audit-Einträge archivieren?\n\nDie Einträge werden nicht gelöscht."): return
        archive_file=cc.archive_audit_entries(entries,self.app,note); messagebox.showinfo("Archiviert", f"Archiv erstellt:\n{archive_file.name}"); self.render()
    def export_pdf(self):
        entries=self.visible_entries(); path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile="Audit-Bericht.pdf")
        if not path: return
        rows=[["Zeitpunkt","Ereignis","Modul","Risiko","Benutzer","Details"]]+[[e.get("timestamp"),e.get("event_type"),e.get("module"),e.get("risk"),e.get("user_name"),e.get("details")] for e in entries]
        cc.write_simple_pdf(path,"Audit-Bericht",rows); cc.log_audit(self.app,"PDF-Bericht erstellt","Audit-Cockpit",Path(path).name,path,"Info",public=False)
        if messagebox.askyesno("PDF erstellt","PDF öffnen?"): cc.open_path(path)

def render(app): AuditCockpitUI(app)
