import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc
DOC_TYPES=["Nachweis","Anlage","Dokumentationspfad","Abschlussbericht","Steuermeldungsbericht","Audit-Bericht","Kommentar/Notiz","Sonstiges"]
HEADERS=["Dokumentname","Dokumenttyp","Modul","Zeitraum","Zuordnung","Status","Pfad","Hinzugefügt durch","Datum","Aktion"]
COLUMN_SPECS={"Dokumentname":(22,170),"Dokumenttyp":(18,130),"Modul":(20,150),"Zeitraum":(10,80),"Zuordnung":(28,220),"Status":(14,110),"Pfad":(38,300),"Hinzugefügt durch":(18,140),"Datum":(12,90),"Aktion":(16,120)}
def match_query(row, query):
    q=(query or "").strip().lower()
    if not q: return True
    blob=" ".join(str(v) for k,v in row.items() if not str(k).startswith("__")).lower(); q=q.replace('*','').strip()
    return all(p.strip() in blob for p in q.split(' und ') if p.strip()) if ' und ' in q else q in blob
def period_kind_for_module(module):
    if module in ("Monatsabschluss","Steuermeldungs-Cockpit"): return 'monthly'
    if module=="Quartalsabschluss": return 'quarterly'
    if module=="Jahresabschluss": return 'yearly'
    return ''
def period_allowed(module, period):
    try:
        k=period_kind_for_module(module)
        return cc.period_allowed_v0432(k, period, only_started=True) if k else True
    except Exception:
        return True
def display_period(period,module=""):
    return cc.format_period_display(period, period_kind_for_module(module)) if hasattr(cc,'format_period_display') else str(period or '')
def display_date(value):
    return cc.format_date_de(value) if hasattr(cc,'format_date_de') else str(value or '')
def period_in_range(period,start,end): return str(start)<=str(period)<=str(end)
class DocumentationCenterUI:
    def __init__(self, app):
        self.app=app; self.root=app.root; self.canvas=app.canvas
        self.search=tk.StringVar(); self.only_missing=tk.BooleanVar(value=False); self.only_invalid=tk.BooleanVar(value=False)
        self.selected_row=None; self.row_frames=[]
        self.frame=tk.Frame(self.root,bg=cc.BG); self.app.widget_items.append(self.frame)
        self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(420,self.canvas.winfo_height()-172))
        self.render()
    def _row(self, **kwargs):
        base={h: kwargs.get(h, kwargs.get(h.replace(' ','_'), '')) for h in HEADERS}
        if base.get('Zeitraum'): base['Zeitraum']=display_period(base.get('Zeitraum'), base.get('Modul',''))
        if base.get('Datum'): base['Datum']=display_date(base.get('Datum'))
        for k,v in kwargs.items():
            if k.startswith('__'): base[k]=v
        return base
    def collect(self):
        rows=[]
        for period in cc.all_tax_periods():
            if not period_allowed("Steuermeldungs-Cockpit", period): continue
            data=cc.ensure_tax_period(period)
            for rep in data.get('reports',[]):
                title=rep.get('title') or rep.get('type_id') or ''; tid=rep.get('type_id','')
                meta={'__source':'tax','__period':period,'__type_id':tid,'__title':title}
                if rep.get('evidence_required') and not rep.get('attachments'):
                    rows.append(self._row(Dokumentname='Nachweis fehlt',Dokumenttyp='Nachweis',Modul='Steuermeldungs-Cockpit',Zeitraum=period,Zuordnung=title,Status='Fehlt',Aktion='Nachweis anhängen',**meta))
                for a in rep.get('attachments',[]):
                    path=a.get('path','')
                    rows.append(self._row(Dokumentname=a.get('name') or Path(path).name,Dokumenttyp='Nachweis',Modul='Steuermeldungs-Cockpit',Zeitraum=period,Zuordnung=title,Status=cc.path_status(path),Pfad=path,Hinzugefügt_durch=a.get('added_by',''),Datum=a.get('added_at',''),Aktion='Quelle öffnen',**meta))
        closing_base=cc.bin_dir()/"Closing"
        for module_dir,label in [("MonthlyClose","Monatsabschluss"),("QuarterlyClose","Quartalsabschluss"),("YearlyClose","Jahresabschluss")]:
            for p in (closing_base/module_dir/"periods").glob('*.json'):
                period=p.stem
                if not period_allowed(label, period): continue
                try: data=json.loads(p.read_text(encoding='utf-8'))
                except Exception: continue
                for idx,t in enumerate(data.get('tasks',[])):
                    if t.get('deleted'): continue
                    title=t.get('title',''); uid=t.get('task_uid',''); assign=f"{uid} {title}".strip()
                    meta={'__source':'close','__module_dir':module_dir,'__period':period,'__task_index':idx,'__task_uid':uid,'__title':title}
                    doc_path=t.get('documentation_path') or t.get('documentation') or ''
                    if doc_path:
                        rows.append(self._row(Dokumentname=Path(doc_path).name,Dokumenttyp='Dokumentationspfad',Modul=label,Zeitraum=period,Zuordnung=assign,Status=cc.path_status(doc_path),Pfad=doc_path,Aktion='Quelle öffnen',**meta))
                    if not doc_path and not t.get('attachments'):
                        rows.append(self._row(Dokumentname='Nachweis fehlt',Dokumenttyp='Nachweis',Modul=label,Zeitraum=period,Zuordnung=assign,Status='Fehlt',Aktion='Nachweis anhängen',**meta))
                    for a in t.get('attachments',[]):
                        path=a.get('path') if isinstance(a,dict) else str(a)
                        rows.append(self._row(Dokumentname=(a.get('name') if isinstance(a,dict) else '') or Path(path).name,Dokumenttyp='Anlage',Modul=label,Zeitraum=period,Zuordnung=assign,Status=cc.path_status(path),Pfad=path,Hinzugefügt_durch=a.get('added_by','') if isinstance(a,dict) else '',Datum=a.get('added_at','') if isinstance(a,dict) else '',Aktion='Quelle öffnen',**meta))
        for d in cc.docs_load_manual().get('documents',[]):
            if d.get('removed'): continue
            if d.get('period') and not period_allowed(d.get('module',''), d.get('period')): continue
            rows.append(self._row(Dokumentname=d.get('name'),Dokumenttyp=d.get('doc_type'),Modul=d.get('module'),Zeitraum=d.get('period'),Zuordnung=d.get('assignment',''),Status=cc.path_status(d.get('path')),Pfad=d.get('path'),Hinzugefügt_durch=d.get('added_by'),Datum=d.get('added_at'),Aktion='Manuell',__source='manual'))
        return rows
    def filtered(self):
        out=[]
        for r in self.collect():
            if self.only_missing.get() and r.get('Status')!='Fehlt': continue
            if self.only_invalid.get() and r.get('Status')!='Pfad ungültig': continue
            if not match_query(r,self.search.get()): continue
            out.append(r)
        return out
    def select_row(self,row,frame):
        self.selected_row=row
        for fr in self.row_frames:
            try:
                fr.configure(bg=cc.WHITE)
                for child in fr.winfo_children(): child.configure(bg=cc.WHITE)
            except Exception: pass
        frame.configure(bg='#DBEAFE')
        for child in frame.winfo_children():
            try: child.configure(bg='#DBEAFE')
            except Exception: pass
        self.add_btn.configure(state='normal')
    def render(self):
        for w in self.frame.winfo_children(): w.destroy()
        self.selected_row=None; self.row_frames=[]; rows=self.filtered()
        total=len(rows); missing=sum(1 for r in rows if r.get('Status')=='Fehlt'); invalid=sum(1 for r in rows if r.get('Status')=='Pfad ungültig'); present=sum(1 for r in rows if r.get('Status')=='Vorhanden'); reports=sum(1 for r in rows if 'Bericht' in str(r.get('Dokumenttyp')))
        top=tk.Frame(self.frame,bg=cc.BG); top.pack(fill='x',padx=24,pady=12)
        for title,val,col in [('Dokumente gesamt',total,cc.BLUE),('Nachweise vorhanden',present,cc.DARK_GREEN),('fehlende Nachweise',missing,cc.RED),('ungültige Pfade',invalid,cc.ORANGE),('Berichte',reports,cc.GREY)]:
            card=tk.Frame(top,bg=col,width=155,height=58); card.pack(side='left',padx=5); card.pack_propagate(False)
            tk.Label(card,text=str(val),bg=col,fg='white',font=('Segoe UI',16,'bold')).pack(); tk.Label(card,text=title,bg=col,fg='white',font=('Segoe UI',8,'bold')).pack()
        controls=tk.Frame(self.frame,bg=cc.BG); controls.pack(fill='x',padx=24,pady=(0,8))
        tk.Label(controls,text='Suche',bg=cc.BG,fg=cc.TEXT,font=('Segoe UI',10,'bold')).pack(side='left')
        tk.Entry(controls,textvariable=self.search,width=42,bg=cc.WHITE).pack(side='left',padx=6)
        tk.Checkbutton(controls,text='nur fehlende',variable=self.only_missing,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side='left')
        tk.Checkbutton(controls,text='nur ungültige Pfade',variable=self.only_invalid,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side='left')
        tk.Button(controls,text='Suchen',command=self.render,bg=cc.BLUE,fg='white',bd=0,padx=10).pack(side='left',padx=4)
        self.add_btn=tk.Button(controls,text='Dokument hinzufügen',command=self.add_manual,bg=cc.BLUE,fg='white',bd=0,padx=10,state='disabled'); self.add_btn.pack(side='right',padx=4)
        tk.Button(controls,text='Export',command=self.open_export_popup,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=14).pack(side='right',padx=4)
        outer=tk.Frame(self.frame,bg=cc.WHITE,bd=1,relief='solid'); outer.pack(fill='both',expand=True,padx=24,pady=(0,12))
        canvas=tk.Canvas(outer,bg=cc.WHITE,highlightthickness=0); sb=tk.Scrollbar(outer,orient='vertical',command=canvas.yview); table=tk.Frame(canvas,bg=cc.WHITE); win=canvas.create_window((0,0),window=table,anchor='nw')
        def upd(e=None): canvas.itemconfigure(win,width=max(1,canvas.winfo_width())); canvas.configure(scrollregion=canvas.bbox('all'))
        table.bind('<Configure>',upd); canvas.bind('<Configure>',upd); canvas.configure(yscrollcommand=sb.set); canvas.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y')
        for c,h in enumerate(HEADERS):
            width,wrap=COLUMN_SPECS.get(h,(18,160)); tk.Label(table,text=h,bg=cc.HEADER,fg=cc.TEXT,font=('Segoe UI',9,'bold'),padx=5,pady=6,width=width,wraplength=wrap).grid(row=0,column=c,sticky='nsew',padx=1,pady=1)
        for r_idx,row in enumerate(rows,1):
            row_frame=tk.Frame(table,bg=cc.WHITE); row_frame.grid(row=r_idx,column=0,columnspan=len(HEADERS),sticky='nsew'); self.row_frames.append(row_frame)
            for c,h in enumerate(HEADERS):
                width,wrap=COLUMN_SPECS.get(h,(18,160)); lbl=tk.Label(row_frame,text=row.get(h,''),bg=cc.WHITE,fg=cc.TEXT,padx=5,pady=4,anchor='w',width=width,wraplength=wrap,justify='left')
                lbl.grid(row=0,column=c,sticky='nsew',padx=1,pady=1); lbl.bind('<Button-1>',lambda e,rr=row,fr=row_frame:self.select_row(rr,fr))
            row_frame.bind('<Button-1>',lambda e,rr=row,fr=row_frame:self.select_row(rr,fr))
        self.app.active_scroll_canvas=canvas
    def _period_options_for_selection(self,row):
        try: return cc.allowed_periods_for_kind_v0432(period_kind_for_module(row.get('Modul','')), only_started=True)
        except Exception: return [row.get('__period') or row.get('Zeitraum','')]
    def add_manual(self):
        if not self.selected_row: messagebox.showinfo('Dokument hinzufügen','Bitte zuerst eine Position auswählen.'); return
        src=self.selected_row; win=tk.Toplevel(self.root); win.title('Dokument hinzufügen'); win.geometry('760x430'); win.configure(bg=cc.BG)
        name_var=tk.StringVar(); path_var=tk.StringVar(); dtype=tk.StringVar(value='Nachweis'); module_var=tk.StringVar(value=src.get('Modul','')); period_var=tk.StringVar(value=display_period(src.get('__period') or src.get('Zeitraum',''),src.get('Modul',''))); assign_var=tk.StringVar(value=src.get('Zuordnung',''))
        raw_periods=self._period_options_for_selection(src); period_labels={display_period(p,src.get('Modul','')):p for p in raw_periods}
        fields=[('Dokumentname',name_var,'entry'),('Dokumenttyp',dtype,DOC_TYPES),('Modul',module_var,[src.get('Modul','')]),('Zeitraum',period_var,list(period_labels.keys())),('Zuordnung',assign_var,[src.get('Zuordnung','')]),('Pfad',path_var,'path')]
        for i,(lab,var,values) in enumerate(fields):
            tk.Label(win,text=lab,bg=cc.BG,fg=cc.TEXT,font=('Segoe UI',10,'bold')).grid(row=i,column=0,sticky='w',padx=12,pady=8)
            if values=='entry': tk.Entry(win,textvariable=var,width=58,bg=cc.WHITE).grid(row=i,column=1,sticky='we',padx=12,pady=8)
            elif values=='path': tk.Label(win,textvariable=var,bg=cc.WHITE,fg=cc.TEXT,width=58,anchor='w',relief='sunken').grid(row=i,column=1,sticky='we',padx=12,pady=8)
            else: ttk.Combobox(win,textvariable=var,values=values,state='readonly',width=54).grid(row=i,column=1,sticky='we',padx=12,pady=8)
        def browse():
            p=filedialog.askopenfilename()
            if p: path_var.set(p); name_var.set(name_var.get().strip() or Path(p).name)
        tk.Button(win,text='Datei wählen',command=browse,bg=cc.WHITE,fg=cc.BLUE,bd=1).grid(row=5,column=2,padx=4)
        def save():
            if not path_var.get().strip(): messagebox.showwarning('Pflichtfeld','Bitte eine Datei auswählen.'); return
            if self.attach_to_position(src,name_var.get().strip() or Path(path_var.get()).name,path_var.get().strip(),dtype.get()):
                cc.log_audit(self.app,'Nachweis hinzugefügt/geändert/entfernt','Dokumentationszentrale','Dokument an Position angehängt',path_var.get(),'Info',period=src.get('__period') or src.get('Zeitraum',''),public=True); win.destroy(); self.render()
        tk.Button(win,text='Speichern',command=save,bg=cc.BLUE,fg='white',bd=0,padx=14,pady=8).grid(row=7,column=1,sticky='e',padx=12,pady=14)
    def attach_to_position(self,row,name,path,doc_type):
        src=row.get('__source')
        if src=='tax':
            data=cc.ensure_tax_period(row.get('__period'))
            for report in data.get('reports',[]):
                if report.get('type_id')==row.get('__type_id') or report.get('title')==row.get('__title'):
                    report.setdefault('attachments',[]).append({'name':name,'path':path,'added_by':cc.user_name(self.app),'added_at':cc.now_iso(),'doc_type':doc_type}); cc.save_tax_period(row.get('__period'),data); return True
        if src=='close':
            p=cc.bin_dir()/"Closing"/row.get('__module_dir','')/"periods"/f"{row.get('__period')}.json"
            if p.exists():
                data=json.loads(p.read_text(encoding='utf-8')); tasks=data.get('tasks',[]); idx=row.get('__task_index'); task=tasks[idx] if isinstance(idx,int) and idx<len(tasks) else None
                if not task: task=next((t for t in tasks if t.get('task_uid')==row.get('__task_uid') and t.get('title')==row.get('__title')),None)
                if task: task.setdefault('attachments',[]).append({'name':name,'path':path,'added_by':cc.user_name(self.app),'added_at':cc.now_iso(),'doc_type':doc_type}); p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); return True
        data=cc.docs_load_manual(); data.setdefault('documents',[]).append({'name':name,'module':row.get('Modul',''),'period':row.get('__period') or row.get('Zeitraum',''),'assignment':row.get('Zuordnung',''),'path':path,'doc_type':doc_type,'added_by':cc.user_name(self.app),'added_at':cc.now_iso()}); cc.docs_save_manual(data); return True
    def export_rows(self, rows=None):
        src=rows if rows is not None else self.filtered(); return HEADERS, [[r.get(h,'') for h in HEADERS] for r in src]
    def open_export_popup(self):
        rows=self.filtered(); raw_periods=sorted(set(str(r.get('__period') or r.get('Zeitraum','')) for r in rows if (r.get('__period') or r.get('Zeitraum')))); period_labels={display_period(p):p for p in raw_periods}; periods=list(period_labels.keys())
        if not periods: messagebox.showinfo('Export','Es sind keine exportierbaren Positionen vorhanden.'); return
        win=tk.Toplevel(self.root); win.title('Export'); win.geometry('560x310'); win.configure(bg=cc.BG); mode=tk.StringVar(value='all'); fmt=tk.StringVar(value='Excel'); from_var=tk.StringVar(value=periods[0]); to_var=tk.StringVar(value=periods[-1])
        tk.Label(win,text='Exportumfang',bg=cc.BG,fg=cc.TEXT,font=('Segoe UI',11,'bold')).pack(anchor='w',padx=18,pady=(16,6))
        for text,val in [('Alles exportieren','all'),('Bestimmte Zeiträume exportieren (von/bis)','include'),('Bestimmte Zeiträume nicht exportieren (von/bis ausschließen)','exclude')]: tk.Radiobutton(win,text=text,variable=mode,value=val,bg=cc.BG,fg=cc.TEXT).pack(anchor='w',padx=24)
        row=tk.Frame(win,bg=cc.BG); row.pack(fill='x',padx=18,pady=12); tk.Label(row,text='Von',bg=cc.BG,fg=cc.TEXT).pack(side='left'); ttk.Combobox(row,textvariable=from_var,values=periods,state='readonly',width=16).pack(side='left',padx=8); tk.Label(row,text='Bis',bg=cc.BG,fg=cc.TEXT).pack(side='left'); ttk.Combobox(row,textvariable=to_var,values=periods,state='readonly',width=16).pack(side='left',padx=8); tk.Label(row,text='Format',bg=cc.BG,fg=cc.TEXT).pack(side='left',padx=(18,4)); ttk.Combobox(row,textvariable=fmt,values=['PDF','Excel'],state='readonly',width=10).pack(side='left')
        def run_export():
            start=period_labels.get(from_var.get(),from_var.get()); end=period_labels.get(to_var.get(),to_var.get()); selected=rows
            if mode.get()=='include': selected=[r for r in rows if period_in_range(str(r.get('__period') or r.get('Zeitraum','')),start,end)]
            elif mode.get()=='exclude': selected=[r for r in rows if not period_in_range(str(r.get('__period') or r.get('Zeitraum','')),start,end)]
            self.export_excel(selected) if fmt.get()=='Excel' else self.export_pdf(selected); win.destroy()
        tk.Button(win,text='Export starten',command=run_export,bg=cc.BLUE,fg='white',bd=0,padx=14,pady=8).pack(anchor='e',padx=18,pady=18)
    def export_excel(self, rows=None):
        path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='Dokumentationsindex.xlsx')
        if not path: return
        headers,data_rows=self.export_rows(rows); from openpyxl import Workbook; from openpyxl.styles import PatternFill,Font; from openpyxl.utils import get_column_letter
        wb=Workbook(); ws=wb.active; ws.title='Export'; ws.append(headers)
        for r in data_rows: ws.append(list(r))
        fill=PatternFill(fill_type='solid',fgColor='D9D9D9')
        for cell in ws[1]: cell.fill=fill; cell.font=Font(bold=True)
        for col in ws.columns:
            letter=get_column_letter(col[0].column); width=max(len(str(cell.value or '')) for cell in col)+2; ws.column_dimensions[letter].width=min(max(width,10),80)
        wb.save(path); cc.log_audit(self.app,'Excel-Bericht erstellt','Dokumentationszentrale',Path(path).name,path,'Info',public=True)
        if messagebox.askyesno('Excel erstellt','Datei öffnen?'): cc.open_path(path)
    def export_pdf(self, rows=None):
        path=filedialog.asksaveasfilename(defaultextension='.pdf',filetypes=[('PDF','*.pdf')],initialfile='Dokumentationsindex.pdf')
        if not path: return
        headers,data_rows=self.export_rows(rows); cc.write_simple_pdf(path,'Dokumentationsindex',[headers]+data_rows); cc.log_audit(self.app,'PDF-Bericht erstellt','Dokumentationszentrale',Path(path).name,path,'Info',public=True)
        if messagebox.askyesno('PDF erstellt','PDF öffnen?'): cc.open_path(path)
def render(app): DocumentationCenterUI(app)
