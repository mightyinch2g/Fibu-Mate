
import json, os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

DOC_TYPES=["Nachweis","Anlage","Dokumentationspfad","Abschlussbericht","Steuermeldungsbericht","Audit-Bericht","Kommentar/Notiz","Sonstiges"]

def match_query(row, query):
    q=(query or "").strip().lower()
    if not q: return True
    blob=" ".join(str(v) for v in row.values()).lower()
    # *Text und Text* => beide Bestandteile müssen vorkommen, vor-/nachgelagerter Text egal
    q=q.replace('*','').strip()
    if ' und ' in q:
        return all(part.strip() in blob for part in q.split(' und ') if part.strip())
    return q in blob

class DocumentationCenterUI:
    def __init__(self, app):
        self.app=app; self.root=app.root; self.canvas=app.canvas
        self.search=tk.StringVar(); self.only_missing=tk.BooleanVar(value=False); self.only_invalid=tk.BooleanVar(value=False)
        self.frame=tk.Frame(self.root,bg=cc.BG); self.app.widget_items.append(self.frame)
        self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(420,self.canvas.winfo_height()-172))
        self.render()
    def collect(self):
        rows=[]
        # Steuer-Nachweise
        for period in cc.all_tax_periods():
            data=cc.ensure_tax_period(period)
            for r in data.get("reports",[]):
                if r.get("evidence_required") and not r.get("attachments"):
                    rows.append({"Dokumentname":"Nachweis fehlt","Dokumenttyp":"Nachweis","Modul":"Steuermeldungs-Cockpit","Zeitraum":period,"Zuordnung":r.get("title"),"Status":"Fehlt","Pfad":"","Hinzugefügt durch":"","Datum":"","Aktion":""})
                for a in r.get("attachments",[]):
                    rows.append({"Dokumentname":a.get("name"),"Dokumenttyp":"Nachweis","Modul":"Steuermeldungs-Cockpit","Zeitraum":period,"Zuordnung":r.get("title"),"Status":cc.path_status(a.get("path")),"Pfad":a.get("path",""),"Hinzugefügt durch":a.get("added_by",""),"Datum":a.get("added_at",""),"Aktion":"Quelle öffnen"})
        # Abschluss-Anlagen/Dokumentationspfade
        closing_base=cc.bin_dir()/"Closing"
        for module, label in [("MonthlyClose","Monatsabschluss"),("QuarterlyClose","Quartalsabschluss"),("YearlyClose","Jahresabschluss")]:
            for p in (closing_base/module/"periods").glob("*.json"):
                try: data=json.loads(p.read_text(encoding="utf-8"))
                except Exception: continue
                for t in data.get("tasks",[]):
                    title=t.get("title",""); uid=t.get("task_uid",""); period=p.stem
                    doc=t.get("documentation_path") or t.get("documentation") or ""
                    if doc:
                        rows.append({"Dokumentname":Path(doc).name,"Dokumenttyp":"Dokumentationspfad","Modul":label,"Zeitraum":period,"Zuordnung":f"{uid} {title}","Status":cc.path_status(doc),"Pfad":doc,"Hinzugefügt durch":"","Datum":"","Aktion":"Quelle öffnen"})
                    for a in t.get("attachments",[]):
                        path=a.get("path") if isinstance(a,dict) else str(a)
                        rows.append({"Dokumentname":Path(path).name,"Dokumenttyp":"Anlage","Modul":label,"Zeitraum":period,"Zuordnung":f"{uid} {title}","Status":cc.path_status(path),"Pfad":path,"Hinzugefügt durch":a.get("added_by","") if isinstance(a,dict) else "","Datum":a.get("added_at","") if isinstance(a,dict) else "","Aktion":"Quelle öffnen"})
        # Manuelle Dokumente
        for d in cc.docs_load_manual().get("documents",[]):
            if d.get("removed"): continue
            rows.append({"Dokumentname":d.get("name"),"Dokumenttyp":d.get("doc_type"),"Modul":d.get("module"),"Zeitraum":d.get("period"),"Zuordnung":d.get("assignment",""),"Status":cc.path_status(d.get("path")),"Pfad":d.get("path"),"Hinzugefügt durch":d.get("added_by"),"Datum":d.get("added_at"),"Aktion":"Manuell"})
        return rows
    def filtered(self):
        rows=[]
        for r in self.collect():
            if self.only_missing.get() and r.get("Status")!="Fehlt": continue
            if self.only_invalid.get() and r.get("Status")!="Pfad ungültig": continue
            if not match_query(r, self.search.get()): continue
            rows.append(r)
        return rows
    def render(self):
        for w in self.frame.winfo_children(): w.destroy()
        rows=self.filtered(); total=len(rows); missing=sum(1 for r in rows if r.get("Status")=="Fehlt"); invalid=sum(1 for r in rows if r.get("Status")=="Pfad ungültig"); present=sum(1 for r in rows if r.get("Status")=="Vorhanden"); reports=sum(1 for r in rows if "Bericht" in str(r.get("Dokumenttyp")))
        top=tk.Frame(self.frame,bg=cc.BG); top.pack(fill="x",padx=24,pady=12)
        for title,val,col in [("Dokumente gesamt",total,cc.BLUE),("Nachweise vorhanden",present,cc.DARK_GREEN),("fehlende Nachweise",missing,cc.RED),("ungültige Pfade",invalid,cc.ORANGE),("Berichte",reports,cc.GREY)]:
            card=tk.Frame(top,bg=col,width=155,height=58); card.pack(side="left",padx=5); card.pack_propagate(False)
            tk.Label(card,text=str(val),bg=col,fg="white",font=("Segoe UI",16,"bold")).pack(); tk.Label(card,text=title,bg=col,fg="white",font=("Segoe UI",8,"bold")).pack()
        controls=tk.Frame(self.frame,bg=cc.BG); controls.pack(fill="x",padx=24,pady=(0,8))
        tk.Label(controls,text="Suche",bg=cc.BG,fg=cc.TEXT,font=("Segoe UI",10,"bold")).pack(side="left")
        tk.Entry(controls,textvariable=self.search,width=42,bg=cc.WHITE).pack(side="left",padx=6)
        tk.Checkbutton(controls,text="nur fehlende",variable=self.only_missing,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side="left")
        tk.Checkbutton(controls,text="nur ungültige Pfade",variable=self.only_invalid,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side="left")
        tk.Button(controls,text="Suchen",command=self.render,bg=cc.BLUE,fg="white",bd=0,padx=10).pack(side="left",padx=4)
        tk.Button(controls,text="Dokument hinzufügen",command=self.add_manual,bg=cc.BLUE,fg="white",bd=0,padx=10).pack(side="right",padx=4)
        tk.Button(controls,text="Excel",command=self.export_excel,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=10).pack(side="right",padx=4)
        tk.Button(controls,text="PDF",command=self.export_pdf,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=10).pack(side="right",padx=4)
        tk.Button(controls,text="Fehlende-Dokumentation",command=self.missing_report,bg=cc.WHITE,fg=cc.RED,bd=1,padx=10).pack(side="right",padx=4)
        outer=tk.Frame(self.frame,bg=cc.WHITE,bd=1,relief="solid"); outer.pack(fill="both",expand=True,padx=24,pady=(0,12))
        canvas=tk.Canvas(outer,bg=cc.WHITE,highlightthickness=0); sb=tk.Scrollbar(outer,orient="vertical",command=canvas.yview); table=tk.Frame(canvas,bg=cc.WHITE); win=canvas.create_window((0,0),window=table,anchor="nw")
        def upd(e=None): canvas.itemconfigure(win,width=max(1,canvas.winfo_width())); canvas.configure(scrollregion=canvas.bbox("all"))
        table.bind("<Configure>",upd); canvas.bind("<Configure>",upd); canvas.configure(yscrollcommand=sb.set); canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        headers=["Dokumentname","Dokumenttyp","Modul","Zeitraum","Zuordnung","Status","Pfad","Hinzugefügt durch","Datum","Aktion"]
        for c,h in enumerate(headers): tk.Label(table,text=h,bg=cc.HEADER,fg=cc.TEXT,font=("Segoe UI",9,"bold"),padx=5,pady=6).grid(row=0,column=c,sticky="nsew",padx=1,pady=1)
        for r,row in enumerate(rows,1):
            for c,h in enumerate(headers): tk.Label(table,text=row.get(h,""),bg=cc.WHITE,fg=cc.TEXT,padx=5,pady=4,anchor="w",wraplength=240).grid(row=r,column=c,sticky="nsew",padx=1,pady=1)
        self.app.active_scroll_canvas=canvas
    def add_manual(self):
        win=tk.Toplevel(self.root); win.title("Manuelles Dokument hinzufügen"); win.geometry("720x420"); win.configure(bg=cc.BG)
        vars={k:tk.StringVar() for k in ["name","module","period","assignment","path"]}; dtype=tk.StringVar(value="Sonstiges")
        fields=[("Dokumentname",vars["name"]),("Modul",vars["module"]),("Zeitraum",vars["period"]),("Zuordnung",vars["assignment"]),("Pfad",vars["path"])]
        for i,(lab,var) in enumerate(fields):
            tk.Label(win,text=lab,bg=cc.BG,fg=cc.TEXT,font=("Segoe UI",10,"bold")).grid(row=i,column=0,sticky="w",padx=12,pady=8)
            tk.Entry(win,textvariable=var,width=70,bg=cc.WHITE).grid(row=i,column=1,sticky="we",padx=12,pady=8)
        ttk.Combobox(win,textvariable=dtype,values=DOC_TYPES,state="readonly",width=30).grid(row=len(fields),column=1,sticky="w",padx=12,pady=8)
        tk.Label(win,text="Dokumenttyp",bg=cc.BG,fg=cc.TEXT,font=("Segoe UI",10,"bold")).grid(row=len(fields),column=0,sticky="w",padx=12,pady=8)
        def browse():
            p=filedialog.askopenfilename();
            if p: vars["path"].set(p); vars["name"].set(vars["name"].get() or Path(p).name)
        tk.Button(win,text="Datei wählen",command=browse,bg=cc.WHITE,fg=cc.BLUE,bd=1).grid(row=4,column=2,padx=4)
        def save():
            if not vars["module"].get().strip() or not vars["period"].get().strip() or not dtype.get().strip() or not vars["path"].get().strip():
                messagebox.showwarning("Pflichtfelder","Modul, Zeitraum, Dokumenttyp und Pfad sind Pflichtfelder."); return
            data=cc.docs_load_manual(); data["documents"].append({"name":vars["name"].get().strip() or Path(vars["path"].get()).name,"module":vars["module"].get().strip(),"period":vars["period"].get().strip(),"assignment":vars["assignment"].get().strip(),"path":vars["path"].get().strip(),"doc_type":dtype.get(),"added_by":cc.user_name(self.app),"added_at":cc.now_iso(),"history":[{"timestamp":cc.now_iso(),"action":"hinzugefügt","user":cc.user_name(self.app)}]})
            cc.docs_save_manual(data); cc.log_audit(self.app,"Nachweis hinzugefügt/geändert/entfernt","Dokumentationszentrale","Manuelles Dokument hinzugefügt",vars["path"].get(),"Info",vars["period"].get(),public=True); win.destroy(); self.render()
        tk.Button(win,text="Speichern",command=save,bg=cc.BLUE,fg="white",bd=0,padx=14,pady=8).grid(row=7,column=1,sticky="e",padx=12,pady=14)
    def export_rows(self):
        headers=["Dokumentname","Dokumenttyp","Modul","Zeitraum","Zuordnung","Status","Pfad","Hinzugefügt durch","Datum","Aktion"]
        rows=[[r.get(h,"") for h in headers] for r in self.filtered()]
        return headers, rows
    def export_excel(self):
        path=filedialog.asksaveasfilename(defaultextension=".xlsx",filetypes=[("Excel","*.xlsx")],initialfile="Dokumentationsindex.xlsx")
        if not path: return
        h,r=self.export_rows(); cc.export_excel(path,h,r); cc.log_audit(self.app,"PDF-Bericht erstellt","Dokumentationszentrale",Path(path).name,path,"Info",public=True)
        if messagebox.askyesno("Excel erstellt","Datei öffnen?"): cc.open_path(path)
    def export_pdf(self):
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile="Dokumentationsindex.pdf")
        if not path: return
        h,r=self.export_rows(); cc.write_simple_pdf(path,"Dokumentationsindex",[h]+r); cc.log_audit(self.app,"PDF-Bericht erstellt","Dokumentationszentrale",Path(path).name,path,"Info",public=True)
        if messagebox.askyesno("PDF erstellt","PDF öffnen?"): cc.open_path(path)
    def missing_report(self):
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile="Fehlende_Dokumentation.pdf")
        if not path: return
        rows=[r for r in self.collect() if r.get("Status") in ("Fehlt","Pfad ungültig")]
        headers=["Dokumentname","Dokumenttyp","Modul","Zeitraum","Zuordnung","Status","Pfad"]
        cc.write_simple_pdf(path,"Fehlende Dokumentation und ungültige Pfade",[headers]+[[r.get(h,"") for h in headers] for r in rows]); cc.log_audit(self.app,"PDF-Bericht erstellt","Dokumentationszentrale",Path(path).name,path,"Mittel",public=True)
        if messagebox.askyesno("Bericht erstellt","PDF öffnen?"): cc.open_path(path)

def render(app): DocumentationCenterUI(app)
