import json
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

DOC_TYPES=["Nachweis","Anlage","Dokumentationspfad","Abschlussbericht","Steuermeldungsbericht","Audit-Bericht","Kommentar/Notiz","Sonstiges"]
HEADERS=["Aufgabenzuordnung","Dokument","Dokumenttyp","Modul","Zeitraum","Hinzugefügt durch","Datum","Aktion"]
COLUMN_WIDTHS={"Aufgabenzuordnung":34,"Dokument":31,"Dokumenttyp":13,"Modul":19,"Zeitraum":9,"Hinzugefügt durch":20,"Datum":12,"Aktion":18}
COLUMN_PIXELS={"Aufgabenzuordnung":295,"Dokument":265,"Dokumenttyp":120,"Modul":170,"Zeitraum":85,"Hinzugefügt durch":180,"Datum":105,"Aktion":155}
DOC_ICON_PATH=r"C:\python\bin\Imgs\Icons\fileinterfacesymboloftextpapersheet_79740.ico"
ATTACH_ICON_PATH=r"C:\python\bin\Imgs\Icons\-attach-file_90371.ico"
DELETE_ICON_PATH=r"C:\python\bin\Imgs\Icons\biggarbagebin_121980.ico"

BODY_TEXT_SCALE = 2.00  # v0.433 Korrektur Paket 1g: Modul-/Tabellentext-Referenz 1920x1080; dynamisch nach unten nicht kleiner.

def body_font(size=10, weight=None, underline=False, scale=1.0):
    try:
        screen_scale = 1.0
        try:
            import tkinter as _tk
            root = _tk._default_root
            if root is not None:
                sw = max(1, root.winfo_screenwidth())
                sh = max(1, root.winfo_screenheight())
                screen_scale = max(1.0, min(1.18, min(sw / 1920.0, sh / 1080.0)))
        except Exception:
            screen_scale = 1.0
        scaled = max(8, int(round(float(size) * BODY_TEXT_SCALE * screen_scale * float(scale))))
    except Exception:
        scaled = size
    style = []
    if weight:
        style.append(weight)
    if underline:
        style.append('underline')
    return tuple(['Segoe UI', scaled] + style)


def ellipsize(value, max_chars):
    text=" ".join(str(value or "").split())
    return text if len(text)<=max_chars else text[:max(1,max_chars-3)] + "..."


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
        self.selected_row=None; self.row_widgets=[]; self._tooltip=None
        self.frame=tk.Frame(self.root,bg=cc.BG); self.app.widget_items.append(self.frame)
        self.canvas.create_window(0,132,window=self.frame,anchor="nw",width=self.canvas.winfo_width(),height=max(420,self.canvas.winfo_height()-172))
        self.doc_icon=self.load_icon(DOC_ICON_PATH,18)
        self.attach_icon=self.load_icon(ATTACH_ICON_PATH,18)
        self.delete_icon=self.load_icon(DELETE_ICON_PATH,18)
        self.render()

    def load_icon(self,path,size=18):
        if not PIL_AVAILABLE: return None
        try:
            if os.path.exists(path):
                img=Image.open(path).resize((size,size))
                return ImageTk.PhotoImage(img)
        except Exception:
            return None
        return None

    def _row(self, **kwargs):
        raw_period=kwargs.get('__period') or kwargs.get('Zeitraum','')
        module=kwargs.get('Modul','')
        base={
            'Aufgabenzuordnung': kwargs.get('Aufgabenzuordnung', kwargs.get('Zuordnung','')),
            'Dokument': kwargs.get('Dokument', kwargs.get('Dokumentname','')),
            'Dokumenttyp': kwargs.get('Dokumenttyp',''),
            'Modul': module,
            'Zeitraum': display_period(raw_period,module) if raw_period else '',
            'Hinzugefügt durch': kwargs.get('Hinzugefügt durch', kwargs.get('Hinzugefügt_durch','')),
            'Datum': display_date(kwargs.get('Datum','')) if kwargs.get('Datum','') else '',
            'Aktion': kwargs.get('Aktion',''),
            '__raw_period': raw_period,
            '__path': kwargs.get('Pfad', kwargs.get('__path','')) or '',
            '__status': kwargs.get('Status',''),
        }
        for k,v in kwargs.items():
            if str(k).startswith('__'): base[k]=v
        return base

    def collect(self):
        rows=[]
        for period in cc.all_tax_periods():
            if not period_allowed("Steuermeldungs-Cockpit", period): continue
            data=cc.ensure_tax_period(period)
            for rep in data.get('reports',[]) or []:
                title=rep.get('title') or rep.get('type_id') or ''; tid=rep.get('type_id','')
                meta={'__source':'tax','__period':period,'__type_id':tid,'__title':title}
                if rep.get('evidence_required') and not rep.get('attachments'):
                    rows.append(self._row(Dokumentname='Nachweis fehlt',Dokumenttyp='Nachweis',Modul='Steuermeldungs-Cockpit',Zeitraum=period,Zuordnung=title,Status='Fehlt',Aktion='Nachweis anhängen',**meta))
                for ai,a in enumerate(rep.get('attachments',[]) or []):
                    path=a.get('path','')
                    rows.append(self._row(Dokumentname=a.get('name') or Path(path).name,Dokumenttyp=a.get('doc_type','Nachweis'),Modul='Steuermeldungs-Cockpit',Zeitraum=period,Zuordnung=title,Status=cc.path_status(path),Pfad=path,Hinzugefügt_durch=a.get('added_by',''),Datum=a.get('added_at',''),Aktion='Quelle öffnen',__attachment_index=ai,**meta))
        closing_base=cc.bin_dir()/"Closing"
        for module_dir,label in [("MonthlyClose","Monatsabschluss"),("QuarterlyClose","Quartalsabschluss"),("YearlyClose","Jahresabschluss")]:
            for p in (closing_base/module_dir/"periods").glob('*.json'):
                period=p.stem
                if not period_allowed(label, period): continue
                try: data=json.loads(p.read_text(encoding='utf-8'))
                except Exception: continue
                for idx,t in enumerate(data.get('tasks',[]) or []):
                    if t.get('deleted'): continue
                    title=t.get('title',''); uid=t.get('task_uid',''); assign=f"{uid} {title}".strip()
                    meta={'__source':'close','__module_dir':module_dir,'__period':period,'__task_index':idx,'__task_uid':uid,'__title':title}
                    doc_path=t.get('documentation_path') or t.get('documentation') or ''
                    if doc_path:
                        rows.append(self._row(Dokumentname=Path(doc_path).name,Dokumenttyp='Dokumentationspfad',Modul=label,Zeitraum=period,Zuordnung=assign,Status=cc.path_status(doc_path),Pfad=doc_path,Aktion='Quelle öffnen',__doc_slot='documentation_path',**meta))
                    if not doc_path and not t.get('attachments'):
                        rows.append(self._row(Dokumentname='Nachweis fehlt',Dokumenttyp='Nachweis',Modul=label,Zeitraum=period,Zuordnung=assign,Status='Fehlt',Aktion='Nachweis anhängen',**meta))
                    for ai,a in enumerate(t.get('attachments',[]) or []):
                        path=a.get('path') if isinstance(a,dict) else str(a)
                        rows.append(self._row(Dokumentname=(a.get('name') if isinstance(a,dict) else '') or Path(path).name,Dokumenttyp=(a.get('doc_type','Anlage') if isinstance(a,dict) else 'Anlage'),Modul=label,Zeitraum=period,Zuordnung=assign,Status=cc.path_status(path),Pfad=path,Hinzugefügt_durch=a.get('added_by','') if isinstance(a,dict) else '',Datum=a.get('added_at','') if isinstance(a,dict) else '',Aktion='Quelle öffnen',__attachment_index=ai,**meta))
        for di,d in enumerate(cc.docs_load_manual().get('documents',[]) or []):
            if d.get('removed'): continue
            if d.get('period') and not period_allowed(d.get('module',''), d.get('period')): continue
            rows.append(self._row(Dokumentname=d.get('name'),Dokumenttyp=d.get('doc_type'),Modul=d.get('module'),Zeitraum=d.get('period'),Zuordnung=d.get('assignment',''),Status=cc.path_status(d.get('path')),Pfad=d.get('path'),Hinzugefügt_durch=d.get('added_by'),Datum=d.get('added_at'),Aktion='Manuell',__source='manual',__manual_index=di))
        return rows

    def filtered(self):
        out=[]
        for r in self.collect():
            if self.only_missing.get() and r.get('__status')!='Fehlt': continue
            if self.only_invalid.get() and r.get('__status')!='Pfad ungültig': continue
            if not match_query(r,self.search.get()): continue
            out.append(r)
        return out

    def open_document(self,row):
        path=row.get('__path','')
        if path: cc.open_path(path)

    def select_row(self,row,widgets):
        self.selected_row=row
        for wl in self.row_widgets:
            for w in wl:
                try: w.configure(bg=cc.WHITE)
                except Exception: pass
        for w in widgets:
            try: w.configure(bg='#DBEAFE')
            except Exception: pass
        self.add_btn.configure(state='normal')

    def show_tooltip(self, widget, text):
        self.hide_tooltip()
        try:
            self._tooltip=tk.Toplevel(widget); self._tooltip.wm_overrideredirect(True)
            self._tooltip.geometry(f"+{widget.winfo_rootx()+20}+{widget.winfo_rooty()+24}")
            tk.Label(self._tooltip,text=text,bg='#FFF8DC',fg=cc.TEXT,relief='solid',bd=1,padx=6,pady=3,wraplength=520,justify='left').pack()
        except Exception: pass
    def hide_tooltip(self):
        try:
            if self._tooltip: self._tooltip.destroy(); self._tooltip=None
        except Exception: pass

    def _bind_cell(self, widget, row, widgets, full_text=''):
        widget.bind('<Button-1>',lambda e,rr=row,ww=widgets:self.select_row(rr,ww))
        shown = widget.cget('text') if hasattr(widget,'cget') else ''
        if full_text and str(full_text)!=shown:
            widget.bind('<Enter>', lambda e, t=str(full_text), w=widget: self.show_tooltip(w,t))
            widget.bind('<Leave>', lambda e: self.hide_tooltip())

    def render(self):
        for w in self.frame.winfo_children(): w.destroy()
        self.selected_row=None; self.row_widgets=[]; rows=self.filtered()
        total=len(rows); missing=sum(1 for r in rows if r.get('__status')=='Fehlt'); invalid=sum(1 for r in rows if r.get('__status')=='Pfad ungültig'); present=sum(1 for r in rows if r.get('__status')=='Vorhanden'); reports=sum(1 for r in rows if 'Bericht' in str(r.get('Dokumenttyp')))
        top=tk.Frame(self.frame,bg=cc.BG); top.pack(fill='x',padx=24,pady=12)
        for title,val,col in [('Dokumente gesamt',total,cc.BLUE),('Nachweise vorhanden',present,cc.DARK_GREEN),('fehlende Nachweise',missing,cc.RED),('ungültige Pfade',invalid,cc.ORANGE),('Berichte',reports,cc.GREY)]:
            card=tk.Frame(top,bg=col,width=155,height=58); card.pack(side='left',padx=5); card.pack_propagate(False)
            tk.Label(card,text=str(val),bg=col,fg='white',font=body_font(16,'bold')).pack(); tk.Label(card,text=title,bg=col,fg='white',font=body_font(8,'bold')).pack()
        controls=tk.Frame(self.frame,bg=cc.BG); controls.pack(fill='x',padx=24,pady=(0,8))
        tk.Label(controls,text='Suche',bg=cc.BG,fg=cc.TEXT,font=body_font(10,'bold')).pack(side='left')
        tk.Entry(controls,textvariable=self.search,width=42,bg=cc.WHITE,font=body_font(10)).pack(side='left',padx=6)
        tk.Checkbutton(controls,text='nur fehlende',font=body_font(10),variable=self.only_missing,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side='left')
        tk.Checkbutton(controls,text='nur ungültige Pfade',font=body_font(10),variable=self.only_invalid,bg=cc.BG,fg=cc.TEXT,command=self.render).pack(side='left')
        tk.Button(controls,text='Suchen',font=body_font(10,'bold'),command=self.render,bg=cc.BLUE,fg='white',bd=0,padx=10).pack(side='left',padx=4)
        self.add_btn=tk.Button(controls,text='Dokument hinzufügen/ändern',font=body_font(10,'bold'),image=self.attach_icon,compound='left',command=self.manage_selected_document,bg=cc.WHITE,fg=cc.BLUE,bd=1,relief='solid',highlightbackground=cc.BLUE,highlightcolor=cc.BLUE,padx=10,state='disabled')
        self.add_btn.pack(side='right',padx=4)
        tk.Button(controls,text='Export',font=body_font(10,'bold'),command=self.open_export_popup,bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=14).pack(side='right',padx=4)
        outer=tk.Frame(self.frame,bg=cc.WHITE,bd=1,relief='solid'); outer.pack(fill='both',expand=True,padx=18,pady=(0,12))
        canvas=tk.Canvas(outer,bg=cc.WHITE,highlightthickness=0); ysb=tk.Scrollbar(outer,orient='vertical',command=canvas.yview); xsb=tk.Scrollbar(outer,orient='horizontal',command=canvas.xview)
        table=tk.Frame(canvas,bg=cc.WHITE); canvas.create_window((0,0),window=table,anchor='nw')
        table.bind('<Configure>',lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.configure(yscrollcommand=ysb.set,xscrollcommand=xsb.set)
        canvas.grid(row=0,column=0,sticky='nsew'); ysb.grid(row=0,column=1,sticky='ns'); xsb.grid(row=1,column=0,sticky='ew')
        outer.grid_rowconfigure(0,weight=1); outer.grid_columnconfigure(0,weight=1)
        for c,h in enumerate(HEADERS):
            table.grid_columnconfigure(c,minsize=COLUMN_PIXELS.get(h,120))
            tk.Label(table,text=h,bg=cc.HEADER,fg=cc.TEXT,font=body_font(9,'bold'),padx=8,pady=8,anchor='w',width=COLUMN_WIDTHS.get(h,18)).grid(row=0,column=c,sticky='nsew',padx=1,pady=1)
        for r_idx,row in enumerate(rows,1):
            widgets=[]
            for c,h in enumerate(HEADERS):
                full=row.get(h,''); text=ellipsize(full,COLUMN_WIDTHS.get(h,18))
                if h=='Dokument':
                    cell=tk.Frame(table,bg=cc.WHITE,width=COLUMN_PIXELS[h],height=max(34, int(30 * min(1.18, BODY_TEXT_SCALE / 2.0))))
                    cell.grid(row=r_idx,column=c,sticky='nsew',padx=1,pady=1); cell.grid_propagate(False)
                    btn=tk.Button(cell,text=text,font=body_font(10),image=self.doc_icon if row.get('__path') else None,compound='right',bg=cc.WHITE,fg=cc.BLUE if row.get('__path') else cc.TEXT,bd=0,anchor='w',justify='left',command=lambda rr=row:self.open_document(rr),cursor='hand2' if row.get('__path') else 'arrow')
                    btn.pack(fill='both',expand=True,padx=3,pady=1); self._bind_cell(btn,row,widgets,full); widgets.extend([cell,btn])
                else:
                    lbl=tk.Label(table,text=text,font=body_font(10),bg=cc.WHITE,fg=cc.TEXT,padx=6,pady=5,anchor='w',width=COLUMN_WIDTHS.get(h,18),justify='left')
                    lbl.grid(row=r_idx,column=c,sticky='nsew',padx=1,pady=1); self._bind_cell(lbl,row,widgets,full); widgets.append(lbl)
            self.row_widgets.append(widgets)
        self.app.active_scroll_canvas=canvas

    def manage_selected_document(self):
        if not self.selected_row:
            messagebox.showinfo('Dokument hinzufügen/ändern','Bitte zuerst eine Position auswählen.'); return
        if self.selected_row.get('__path'):
            self.open_manage_popup(self.selected_row)
        else:
            self.add_document_for_row(self.selected_row)

    def open_manage_popup(self,row):
        win=tk.Toplevel(self.root); win.title('Dokument hinzufügen/ändern'); win.geometry('900x380'); win.configure(bg=cc.BG); win.transient(self.root)
        tk.Label(win,text='Dokumentverwaltung',bg=cc.BG,fg=cc.TEXT,font=body_font(14,'bold')).pack(anchor='w',padx=16,pady=(14,8))
        current=tk.Frame(win,bg=cc.WHITE,bd=1,relief='solid'); current.pack(fill='x',padx=16,pady=8)
        tk.Label(current,text=ellipsize(row.get('Dokument',''),60),bg=cc.WHITE,fg=cc.TEXT,anchor='w').pack(side='left',fill='x',expand=True,padx=8,pady=8)
        tk.Button(current,text='Öffnen',font=body_font(10,'bold'),command=lambda:self.open_document(row),bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=10).pack(side='left',padx=4)
        tk.Button(current,text='Ändern',font=body_font(10,'bold'),image=self.attach_icon,compound='left',command=lambda:(win.destroy(),self.replace_document_interactive(row)),bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=10).pack(side='left',padx=4)
        tk.Button(current,text='Löschen',font=body_font(10,'bold'),image=self.delete_icon,compound='left',command=lambda:(win.destroy(),self.delete_document(row)),bg=cc.WHITE,fg=cc.RED,bd=1,padx=10).pack(side='left',padx=4)
        tk.Button(win,text='Weiteres Dokument hinzufügen',font=body_font(10,'bold'),image=self.attach_icon,compound='left',command=lambda:(win.destroy(),self.add_document_for_row(row)),bg=cc.WHITE,fg=cc.BLUE,bd=1,padx=12,pady=7).pack(anchor='e',padx=16,pady=12)

    def add_document_for_row(self,row):
        p=filedialog.askopenfilename()
        if not p: return
        self.attach_to_position(row,Path(p).name,p,row.get('Dokumenttyp') or 'Nachweis')
        cc.log_audit(self.app,'Nachweis hinzugefügt/geändert/entfernt','Dokumentationszentrale','Dokument an Position angehängt',p,'Info',period=row.get('__raw_period') or row.get('__period',''),public=True)
        self.render()

    def replace_document_interactive(self,row):
        p=filedialog.askopenfilename()
        if not p: return
        if self.delete_document(row,confirm=False,rerender=False): self.attach_to_position(row,Path(p).name,p,row.get('Dokumenttyp') or 'Nachweis')
        self.render()

    def delete_document(self,row,confirm=True,rerender=True):
        if confirm and not messagebox.askyesno('Dokument löschen','Ausgewähltes Dokument wirklich aus der Position entfernen?'):
            return False
        src=row.get('__source'); changed=False
        if src=='tax':
            data=cc.ensure_tax_period(row.get('__period'))
            for report in data.get('reports',[]):
                if report.get('type_id')==row.get('__type_id') or report.get('title')==row.get('__title'):
                    atts=report.get('attachments',[]); idx=row.get('__attachment_index')
                    if isinstance(idx,int) and idx<len(atts): atts.pop(idx)
                    else: report['attachments']=[a for a in atts if a.get('path')!=row.get('__path')]
                    cc.save_tax_period(row.get('__period'),data); changed=True; break
        elif src=='manual':
            data=cc.docs_load_manual(); docs=data.get('documents',[]); idx=row.get('__manual_index')
            if isinstance(idx,int) and idx<len(docs): docs[idx]['removed']=True; cc.docs_save_manual(data); changed=True
        elif src=='close':
            p=cc.bin_dir()/"Closing"/row.get('__module_dir','')/"periods"/f"{row.get('__period')}.json"
            if p.exists():
                data=json.loads(p.read_text(encoding='utf-8')); tasks=data.get('tasks',[]); idx=row.get('__task_index'); task=tasks[idx] if isinstance(idx,int) and idx<len(tasks) else None
                if task:
                    if row.get('__doc_slot'): task.pop('documentation_path',None); task.pop('documentation',None)
                    else:
                        atts=task.get('attachments',[]); ai=row.get('__attachment_index')
                        if isinstance(ai,int) and ai<len(atts): atts.pop(ai)
                    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); changed=True
        if changed: cc.log_audit(self.app,'Nachweis hinzugefügt/geändert/entfernt','Dokumentationszentrale','Dokument entfernt',row.get('__path',''),'Info',period=row.get('__raw_period') or row.get('__period',''),public=True)
        if rerender: self.render()
        return changed

    def add_manual(self):
        if not self.selected_row: messagebox.showinfo('Dokument hinzufügen/ändern','Bitte zuerst eine Position auswählen.'); return
        self.add_document_for_row(self.selected_row)

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
        data=cc.docs_load_manual(); data.setdefault('documents',[]).append({'name':name,'module':row.get('Modul',''),'period':row.get('__raw_period') or row.get('__period') or row.get('Zeitraum',''),'assignment':row.get('Aufgabenzuordnung',''),'path':path,'doc_type':doc_type,'added_by':cc.user_name(self.app),'added_at':cc.now_iso()}); cc.docs_save_manual(data); return True

    def export_rows(self, rows=None):
        src=rows if rows is not None else self.filtered(); return HEADERS, [[r.get(h,'') for h in HEADERS] for r in src]
    def open_export_popup(self):
        rows=self.filtered(); raw_periods=sorted(set(str(r.get('__raw_period') or r.get('__period') or r.get('Zeitraum','')) for r in rows if (r.get('__raw_period') or r.get('__period') or r.get('Zeitraum')))); period_labels={display_period(p):p for p in raw_periods}; periods=list(period_labels.keys())
        if not periods: messagebox.showinfo('Export','Es sind keine exportierbaren Positionen vorhanden.'); return
        win=tk.Toplevel(self.root); win.title('Export'); win.geometry('680x360'); win.configure(bg=cc.BG); mode=tk.StringVar(value='all'); fmt=tk.StringVar(value='Excel'); from_var=tk.StringVar(value=periods[0]); to_var=tk.StringVar(value=periods[-1])
        tk.Label(win,text='Exportumfang',bg=cc.BG,fg=cc.TEXT,font=body_font(11,'bold')).pack(anchor='w',padx=18,pady=(16,6))
        for text,val in [('Alles exportieren','all'),('Bestimmte Zeiträume exportieren (von/bis)','include'),('Bestimmte Zeiträume nicht exportieren (von/bis ausschließen)','exclude')]: tk.Radiobutton(win,text=text,font=body_font(10),variable=mode,value=val,bg=cc.BG,fg=cc.TEXT).pack(anchor='w',padx=24)
        row=tk.Frame(win,bg=cc.BG); row.pack(fill='x',padx=18,pady=12); tk.Label(row,text='Von',font=body_font(10),bg=cc.BG,fg=cc.TEXT).pack(side='left'); ttk.Combobox(row,textvariable=from_var,values=periods,state='readonly',width=16).pack(side='left',padx=8); tk.Label(row,text='Bis',font=body_font(10),bg=cc.BG,fg=cc.TEXT).pack(side='left'); ttk.Combobox(row,textvariable=to_var,values=periods,state='readonly',width=16).pack(side='left',padx=8); tk.Label(row,text='Format',font=body_font(10),bg=cc.BG,fg=cc.TEXT).pack(side='left',padx=(18,4)); ttk.Combobox(row,textvariable=fmt,values=['PDF','Excel'],state='readonly',width=10).pack(side='left')
        def run_export():
            start=period_labels.get(from_var.get(),from_var.get()); end=period_labels.get(to_var.get(),to_var.get()); selected=rows
            if mode.get()=='include': selected=[r for r in rows if period_in_range(str(r.get('__raw_period') or r.get('__period') or r.get('Zeitraum','')),start,end)]
            elif mode.get()=='exclude': selected=[r for r in rows if not period_in_range(str(r.get('__raw_period') or r.get('__period') or r.get('Zeitraum','')),start,end)]
            self.export_excel(selected) if fmt.get()=='Excel' else self.export_pdf(selected); win.destroy()
        tk.Button(win,text='Export starten',font=body_font(10,'bold'),command=run_export,bg=cc.BLUE,fg='white',bd=0,padx=14,pady=8).pack(anchor='e',padx=18,pady=18)
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
