import json, os, subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

BG = "#E8EEF5"; HEADER = "#D3DEE9"; BLUE = "#004B93"; TEXT = "#182431"; TEXT2 = "#445364"; WHITE = "#FFFFFF"
BASE = Path(__file__).resolve().parent.parent / "Closing" if Path(__file__).resolve().parent.name.lower()=="tools" else Path(__file__).resolve().parent / "bin" / "Closing"
MODULES = {"Monatsabschluss": "MonthlyClose", "Quartalsabschluss": "QuarterlyClose", "Jahresabschluss": "YearlyClose"}

def period_label(module, key):
    if module == "MonthlyClose":
        names = ["Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
        y,m = map(int,key.split("-")); return f"{names[m-1]} {y}"
    if module == "QuarterlyClose":
        y,q = key.split("-Q"); return f"{q}. Quartal {y}"
    return f"Geschäftsjahr {key}"

def collect(module):
    rows=[]; periods = BASE / module / "periods"
    for path in sorted(periods.glob("*.json")):
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except Exception: continue
        for t in data.get("tasks", []):
            uid=t.get("task_uid","");
            if uid: rows.append((uid,t,path.stem,module))
    return rows

def latest_by_uid(module):
    out={}
    for uid,t,period,mod in collect(module): out[uid]=(t,period,mod)
    return out

class HistoryUI:
    def __init__(self, app):
        self.app=app; self.root=app.root; self.canvas=app.canvas; self.current="MonthlyClose"; self.frame=tk.Frame(self.root,bg=BG); self.app.widget_items.append(self.frame); self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(400,self.canvas.winfo_height()-172)); self.render()
    def clear(self):
        for w in self.frame.winfo_children(): w.destroy()
    def render(self):
        self.clear(); top=tk.Frame(self.frame,bg=BG); top.pack(fill="x",padx=24,pady=12)
        for label,mod in MODULES.items(): tk.Button(top,text=label,command=lambda m=mod:self.switch(m),bg=BLUE if self.current==mod else WHITE,fg=WHITE if self.current==mod else BLUE,bd=1,padx=12,pady=6).pack(side="left",padx=4)
        outer=tk.Frame(self.frame,bg=WHITE,bd=1,relief="solid"); outer.pack(fill="both",expand=True,padx=24,pady=(0,12))
        canvas=tk.Canvas(outer,bg=WHITE,highlightthickness=0); sb=tk.Scrollbar(outer,orient="vertical",command=canvas.yview); table=tk.Frame(canvas,bg=WHITE); win=canvas.create_window((0,0),window=table,anchor="nw")
        def upd(e=None): canvas.itemconfigure(win,width=max(1,canvas.winfo_width())); canvas.configure(scrollregion=canvas.bbox("all"))
        table.bind("<Configure>",upd); canvas.bind("<Configure>",upd); canvas.configure(yscrollcommand=sb.set); canvas.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        headers=["Aufgaben-ID","Aufgabenname","Zuständigkeit","Fälligkeitslogik","Datum letzte Erledigung","Status","Bericht"]
        for c,h in enumerate(headers): tk.Label(table,text=h,bg=HEADER,fg=TEXT,font=("Segoe UI",10,"bold"),padx=6,pady=6).grid(row=0,column=c,sticky="nsew",padx=1,pady=1)
        for r,(uid,(task,period,mod)) in enumerate(sorted(latest_by_uid(self.current).items()),1):
            vals=[uid,task.get("title",""),task.get("owner",""),task.get("due_mode",""),task.get("done_at","") or "", "Aktive Aufgabe" if not task.get("archived") else "Archivierte Aufgabe"]
            for c,v in enumerate(vals):
                lab=tk.Label(table,text=v,bg=WHITE,fg=TEXT,padx=6,pady=5,anchor="w"); lab.grid(row=r,column=c,sticky="nsew",padx=1,pady=1); lab.bind("<Button-1>",lambda e,u=uid:self.detail(u))
            tk.Button(table,text="PDF",command=lambda u=uid:self.pdf_uid(u),bg=WHITE,fg=BLUE,bd=1).grid(row=r,column=6,sticky="nsew",padx=1,pady=1)
        self.app.active_scroll_canvas=canvas
    def switch(self,mod): self.current=mod; self.render()
    def detail(self,uid):
        win=tk.Toplevel(self.root); win.title(f"Historie {uid}"); win.geometry("900x520"); win.configure(bg=BG)
        txt=tk.Text(win,wrap="word",bg=WHITE,fg=TEXT); txt.pack(fill="both",expand=True,padx=12,pady=12)
        for u,t,p,m in collect(self.current):
            if u==uid:
                txt.insert("end", f"{period_label(m,p)}\nAufgabe: {t.get('title','')}\nZuständig: {t.get('owner','')}\nStatus: {t.get('status','')}\nErledigt: {t.get('done_at','')}\nAnlagen: {len(t.get('attachments',[]))}\nKommentare: {len(t.get('comments',[]))}\n\n")
    def pdf_uid(self,uid):
        if not REPORTLAB_AVAILABLE: messagebox.showerror("PDF", "reportlab ist nicht verfügbar."); return
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile=f"Aufgaben-ID_{uid}.pdf")
        if not path: return
        styles=getSampleStyleSheet(); story=[Paragraph(f"Gesamtbericht Aufgaben-ID {uid}",styles["Title"]),Spacer(1,12)]
        rows=[["Zeitraum","Aufgabe","Zuständig","Status","Erledigt","Anlagen","Kommentare"]]
        for u,t,p,m in collect(self.current):
            if u==uid: rows.append([period_label(m,p),t.get('title',''),t.get('owner',''),t.get('status',''),t.get('done_at',''),str(len(t.get('attachments',[]))),str(len(t.get('comments',[])))])
        tbl=Table(rows,repeatRows=1); tbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D3DEE9"))])); story.append(tbl); SimpleDocTemplate(path,pagesize=A4).build(story)
        if messagebox.askyesno("PDF erstellt","PDF öffnen?"):
            try: os.startfile(path)
            except Exception: subprocess.Popen(["xdg-open",path])

def render(app): HistoryUI(app)
