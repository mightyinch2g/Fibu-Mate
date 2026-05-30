import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
from pathlib import Path

try:
    from . import compliance_common as cc
except Exception:
    import compliance_common as cc

STATUS_VALUES = ["Offen", "Zur Prüfung", "Freigegeben", "Gemeldet", "Nicht relevant"]

class TaxReportingUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        self.period = cc.current_month_key()
        self.data = cc.ensure_tax_period(self.period)

        self.frame = tk.Frame(self.root, bg=cc.BG)
        self.app.widget_items.append(self.frame)
        self.canvas.create_window(0, 132, window=self.frame, anchor="nw",
                                  width=self.canvas.winfo_width(),
                                  height=max(420, self.canvas.winfo_height() - 172))
        self.render()

    def clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def reports(self):
        return self.data.setdefault("reports", [])

    def fmt(self, value):
        if not value:
            return ""
        try:
            return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y")
        except Exception:
            try:
                return datetime.strptime(str(value), "%Y-%m-%d").strftime("%d.%m.%Y")
            except Exception:
                return str(value)

    def owner_name(self, key):
        if not key:
            return ""
        u = getattr(self.app, "user_data", {}).get("users", {}).get(key, {})
        return u.get("display_name") or u.get("full_name") or key

    def switch(self, delta):
        self.period = cc.add_month(self.period, delta)
        self.render()

    def render(self):
        self.clear()
        self.data = cc.ensure_tax_period(self.period)

        top = tk.Frame(self.frame, bg=cc.BG)
        top.pack(fill="x", padx=24, pady=(12, 6))
        tk.Button(top, text="◀", command=lambda: self.switch(-1), bg=cc.WHITE, fg=cc.BLUE, bd=1, width=4).pack(side="left")
        tk.Label(top, text=cc.period_label(self.period), bg=cc.BG, fg=cc.TEXT, font=("Segoe UI", 16, "bold"), padx=16).pack(side="left")
        tk.Button(top, text="▶", command=lambda: self.switch(1), bg=cc.WHITE, fg=cc.BLUE, bd=1, width=4).pack(side="left")

        if cc.can_admin(self.app):
            tk.Button(top, text="Meldearten/Stammdaten", command=self.config_popup, bg=cc.BLUE, fg="white", bd=0, padx=12, pady=6).pack(side="right", padx=4)

        tk.Button(top, text="PDF-Bericht", command=self.export_pdf, bg=cc.WHITE, fg=cc.BLUE, bd=1, padx=12, pady=6).pack(side="right", padx=4)

        outer = tk.Frame(self.frame, bg=cc.WHITE, bd=1, relief="solid")
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        canvas = tk.Canvas(outer, bg=cc.WHITE, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        table = tk.Frame(canvas, bg=cc.WHITE)
        win = canvas.create_window((0, 0), window=table, anchor="nw")

        def upd(_=None):
            canvas.itemconfigure(win, width=max(1, canvas.winfo_width()))
            canvas.configure(scrollregion=canvas.bbox("all"))

        table.bind("<Configure>", upd)
        canvas.bind("<Configure>", upd)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        headers = ["Meldung", "Status", "Fällig", "Zuständig", "Freigabepflicht", "Prüfung", "Meldedatum", "Freigabe", "Nachweise", "Kommentar", "Aktion"]
        for c, h in enumerate(headers):
            tk.Label(table, text=h, bg=cc.HEADER, fg=cc.TEXT, font=("Segoe UI", 10, "bold"), padx=6, pady=6).grid(row=0, column=c, sticky="nsew", padx=1, pady=1)

        for i, r in enumerate(self.reports(), start=1):
            approval = bool(r.get("approval_required", True))
            freigabepf = "Ja" if approval else "Nein"
            reviewer = self.owner_name(r.get("reviewer_user_key"))
            pruefung = reviewer or ("4-Augen" if r.get("four_eye") else "")
            freigabe = "nicht benötigt" if not approval else self.fmt(r.get("approved_at"))

            vals = [
                r.get("title"),
                r.get("status"),
                self.fmt(r.get("due_date")),
                self.owner_name(r.get("owner_user_key")),
                freigabepf,
                pruefung,
                self.fmt(r.get("reported_at")),
                freigabe,
                str(len(r.get("attachments", []))),
                str(len(r.get("comments", []))),
            ]
            for c, v in enumerate(vals):
                tk.Label(table, text=v, bg=cc.WHITE, fg=cc.TEXT, padx=6, pady=5, anchor="w", wraplength=180).grid(row=i, column=c, sticky="nsew", padx=1, pady=1)

            tk.Button(table, text="Öffnen", command=lambda rr=r: self.detail(rr), bg=cc.BLUE, fg="white", bd=0).grid(row=i, column=10, sticky="nsew", padx=1, pady=1)

        self.app.active_scroll_canvas = canvas

    def can_edit(self, r):
        return cc.can_admin(self.app) or r.get("owner_user_key") == cc.user_key(self.app)

    def detail(self, r):
        win = tk.Toplevel(self.root)
        win.title(f"{r.get('title')} - {cc.period_label(self.period)}")
        win.geometry("850x680")
        win.configure(bg=cc.BG)
        win.transient(self.root)

        form = tk.Frame(win, bg=cc.BG)
        form.pack(fill="both", expand=True, padx=14, pady=14)

        status = tk.StringVar(value=r.get("status", "Offen"))
        due = tk.StringVar(value=r.get("due_date", ""))
        owner = tk.StringVar(value=r.get("owner_user_key", ""))
        reviewer = tk.StringVar(value=r.get("reviewer_user_key", ""))
        reported = tk.StringVar(value=r.get("reported_at", ""))
        approved = tk.StringVar(value=r.get("approved_at", ""))
        reason = tk.StringVar(value=r.get("not_relevant_reason", ""))
        comment = tk.StringVar()

        rows = [
            ("Status", status, "combo"),
            ("Fälligkeit YYYY-MM-DD", due, "entry"),
            ("Zuständig Benutzer-Key", owner, "entry"),
            ("Prüfer Benutzer-Key", reviewer, "entry"),
            ("Meldedatum YYYY-MM-DD", reported, "entry"),
            ("Freigabedatum YYYY-MM-DD", approved, "entry"),
            ("Nicht-relevant-Begründung", reason, "entry"),
            ("Neuer Kommentar", comment, "entry"),
        ]

        for i, (lab, var, kind) in enumerate(rows):
            tk.Label(form, text=lab, bg=cc.BG, fg=cc.TEXT, font=("Segoe UI", 10, "bold")).grid(row=i, column=0, sticky="w", pady=5)
            if kind == "combo":
                ttk.Combobox(form, textvariable=var, values=STATUS_VALUES, state="readonly", width=28).grid(row=i, column=1, sticky="w", pady=5)
            else:
                tk.Entry(form, textvariable=var, width=55, bg=cc.WHITE).grid(row=i, column=1, sticky="we", pady=5)

        # Nachweise
        tk.Label(form, text="Nachweise", bg=cc.BG, fg=cc.TEXT, font=("Segoe UI", 11, "bold")).grid(row=8, column=0, sticky="w", pady=(16, 4))
        attach_box = tk.Listbox(form, height=5, width=86)
        attach_box.grid(row=9, column=0, columnspan=3, sticky="we")

        def refresh_attach():
            attach_box.delete(0, "end")
            for a in r.get("attachments", []):
                attach_box.insert("end", f"{a.get('name','')} | {a.get('path','')} | {a.get('comment','')}")

        refresh_attach()

        def add_att():
            p = filedialog.askopenfilename(title="Nachweis auswählen")
            if not p:
                return
            comm = simpledialog.askstring("Kommentar", "Kommentar zum Nachweis:", parent=win) or ""
            att = {"name": Path(p).name, "path": p, "comment": comm, "added_at": cc.now_iso(), "added_by": cc.user_name(self.app)}
            r.setdefault("attachments", []).append(att)
            r.setdefault("history", []).append({"timestamp": cc.now_iso(), "action": "Nachweis hinzugefügt", "user": cc.user_name(self.app), "path": p})
            cc.log_audit(self.app, "Nachweis hinzugefügt/geändert/entfernt", "Steuermeldungs-Cockpit", f"Nachweis {r.get('title')}", p, "Mittel", self.period, r.get("type_id"), True)
            refresh_attach()

        btns = tk.Frame(form, bg=cc.BG)
        btns.grid(row=10, column=0, columnspan=3, sticky="w", pady=8)
        tk.Button(btns, text="Nachweis hinzufügen", command=add_att, bg=cc.BLUE, fg="white", bd=0, padx=12, pady=6).pack(side="left", padx=4)

        def save():
            if not self.can_edit(r):
                messagebox.showwarning("Berechtigung", "Keine Berechtigung.")
                return

            new_status = status.get()
            if new_status == "Nicht relevant" and not reason.get().strip():
                messagebox.showwarning("Pflichtfeld", "Bitte Begründung für 'Nicht relevant' eintragen.")
                return

            if new_status == "Gemeldet":
                if not reported.get().strip():
                    messagebox.showwarning("Pflichtfeld", "Bitte Meldedatum eintragen.")
                    return
                if r.get("evidence_required", True) and not r.get("attachments"):
                    messagebox.showwarning("Pflichtnachweis", "Bitte mindestens einen Nachweis anhängen.")
                    return

            old = dict(r)
            r.update({
                "status": new_status,
                "due_date": due.get().strip(),
                "owner_user_key": owner.get().strip(),
                "reviewer_user_key": reviewer.get().strip(),
                "reported_at": reported.get().strip(),
                "approved_at": approved.get().strip(),
                "not_relevant_reason": reason.get().strip(),
            })

            if comment.get().strip():
                r.setdefault("comments", []).append({"timestamp": cc.now_iso(), "user": cc.user_name(self.app), "text": comment.get().strip()})

            r.setdefault("history", []).append({"timestamp": cc.now_iso(), "user": cc.user_name(self.app), "action": "Meldung gespeichert", "old_status": old.get("status"), "new_status": new_status})

            cc.log_audit(self.app, "Aufgabe geändert", "Steuermeldungs-Cockpit", f"Meldung {r.get('title')} gespeichert", f"Status {old.get('status')} → {new_status}", "Info", self.period, r.get("type_id"), True)

            cc.save_tax_period(self.period, self.data)
            win.destroy()
            self.render()

        tk.Button(form, text="Speichern", command=save, bg=cc.DARK_GREEN, fg="white", bd=0, padx=18, pady=8).grid(row=11, column=2, sticky="e", pady=14)

    def config_popup(self):
        cfg = cc.load_tax_config()
        win = tk.Toplevel(self.root)
        win.title("Meldearten/Stammdaten")
        win.geometry("900x520")
        win.configure(bg=cc.BG)

        frame = tk.Frame(win, bg=cc.BG)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        rows = []
        headers = ["ID", "Titel", "Aktiv", "Nachweis Pflicht", "Freigabe Pflicht", "4-Augen", "Owner-Key", "Prüfer-Key", "Kalender-Sync"]
        for c, h in enumerate(headers):
            tk.Label(frame, text=h, bg=cc.HEADER, fg=cc.TEXT, font=("Segoe UI", 9, "bold")).grid(row=0, column=c, padx=1, pady=1, sticky="nsew")

        for i, rt in enumerate(cfg.get("report_types", []), start=1):
            vars_ = [tk.StringVar(value=str(rt.get(k, ""))) for k in ["id", "title", "active", "evidence_required", "approval_required", "four_eye", "owner_user_key", "reviewer_user_key", "sync_with_calendar"]]
            rows.append((rt, vars_))
            for c, var in enumerate(vars_):
                tk.Entry(frame, textvariable=var, width=14, bg=cc.WHITE).grid(row=i, column=c, padx=1, pady=1)

        def save_cfg():
            for rt, vars_ in rows:
                keys = ["id", "title", "active", "evidence_required", "approval_required", "four_eye", "owner_user_key", "reviewer_user_key", "sync_with_calendar"]
                for k, var in zip(keys, vars_):
                    v = var.get().strip()
                    if k in ("active", "evidence_required", "approval_required", "four_eye", "sync_with_calendar"):
                        rt[k] = v.lower() in ("true", "1", "ja", "yes")
                    else:
                        rt[k] = v
            cc.save_tax_config(cfg)
            cc.log_audit(self.app, "Aufgabe geändert", "Steuermeldungs-Cockpit", "Meldearten/Stammdaten geändert", "", "Mittel", public=False)
            win.destroy()
            self.render()

        tk.Button(frame, text="Speichern", command=save_cfg, bg=cc.BLUE, fg="white", bd=0, padx=14, pady=8).grid(row=len(rows)+1, column=0, columnspan=2, pady=12, sticky="w")

    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=f"Steuermeldungen_{self.period}.pdf")
        if not path:
            return
        rows = [["Meldung", "Status", "Fällig", "Meldedatum", "Nachweise"]] + [
            [r.get("title"), r.get("status"), self.fmt(r.get("due_date")), self.fmt(r.get("reported_at")), len(r.get("attachments", []))]
            for r in self.reports()
        ]
        cc.write_simple_pdf(path, f"Steuermeldungsbericht {cc.period_label(self.period)}", rows)
        cc.log_audit(self.app, "PDF-Bericht erstellt", "Steuermeldungs-Cockpit", Path(path).name, path, "Info", self.period, public=True)
        if messagebox.askyesno("PDF erstellt", "PDF öffnen?"):
            cc.open_path(path)


def render(app):
    TaxReportingUI(app)
