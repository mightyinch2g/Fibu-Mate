## FiBuMate_PATCH_MARKER: 20260529_v0435_AUFGABENMANAGER

import json
import os
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, filedialog

BG = "#E8EEF5"
HEADER = "#D3DEE9"
BLUE = "#004B93"
TEXT = "#182431"
TEXT2 = "#445364"
WHITE = "#FFFFFF"
LINE = "#91A3B5"

BASE = Path(__file__).resolve().parent.parent / "Closing" if Path(__file__).resolve().parent.name.lower() == "tools" else Path(__file__).resolve().parent / "bin" / "Closing"
MODULES = {"Monatsabschluss": "MonthlyClose", "Quartalsabschluss": "QuarterlyClose", "Jahresabschluss": "YearlyClose"}

# v0.435: Aufgabenmanager nutzt bewusst feste, große Schriften und keinen Bereichszoom.
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_TAB = ("Segoe UI", 13, "bold")
FONT_HEAD = ("Segoe UI", 13, "bold")
FONT_CELL = ("Segoe UI", 13)
FONT_CELL_BOLD = ("Segoe UI", 13, "bold")


def period_label(module, key):
    try:
        if module == "MonthlyClose":
            y, m = map(int, str(key).split("-"))
            return f"{m:02d}/{str(y)[-2:]}"
        if module == "QuarterlyClose":
            y, q = str(key).split("-Q")
            return f"Q{q}/{str(y)[-2:]}"
        y1, y2 = str(key).split("-")
        return f"GJ {y1}/{y2}"
    except Exception:
        return str(key or "")


def collect(module):
    rows = []
    periods = BASE / module / "periods"
    for path in sorted(periods.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for t in data.get("tasks", []):
            uid = str(t.get("task_uid", "") or "").strip()
            if uid:
                rows.append((uid, t, path.stem, module))
    return rows


def latest_by_uid(module):
    out = {}
    for uid, task, period, mod in collect(module):
        out[uid] = (task, period, mod)
    return out


def pdf_escape(text):
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def write_pdf(path, title, rows):
    lines = [title, ''] + [" | ".join(str(x) for x in row) for row in rows]
    pages = []
    for start in range(0, len(lines), 42):
        ops = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL"]
        for line in lines[start:start + 42]:
            ops += [f"({pdf_escape(line[:150])}) Tj", "T*"]
        ops.append("ET")
        pages.append("\n".join(ops).encode('latin-1', 'replace'))
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + i * 2} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, c in enumerate(pages):
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {4 + i * 2} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(c)).encode() + b" >>\nstream\n" + c + b"\nendstream")
    pdf = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(pdf)
    pdf += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offs:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    Path(path).write_bytes(bytes(pdf))


class HistoryUI:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.canvas = app.canvas
        self.current = "MonthlyClose"
        self.frame = tk.Frame(self.root, bg=BG)
        self.app.widget_items.append(self.frame)
        self.canvas.create_window(0, 132, window=self.frame, anchor="nw", width=self.canvas.winfo_width(), height=max(400, self.canvas.winfo_height() - 172))
        # v0.435: Strg+Mausrad im Aufgabenmanager blockieren, damit keine Modul-Zoomfunktion wirkt.
        self.frame.bind_all("<Control-MouseWheel>", self.block_ctrl_wheel)
        self.frame.bind_all("<Control-Button-4>", self.block_ctrl_wheel)
        self.frame.bind_all("<Control-Button-5>", self.block_ctrl_wheel)
        self.render()

    def block_ctrl_wheel(self, _event=None):
        return "break"

    def clear(self):
        for w in self.frame.winfo_children():
            w.destroy()

    def render(self):
        self.clear()
        top = tk.Frame(self.frame, bg=BG)
        top.pack(fill="x", padx=24, pady=12)
        tk.Label(top, text="Aufgabenmanager", bg=BG, fg=TEXT, font=FONT_TITLE).pack(side="left", padx=(0, 18))
        for label, mod in MODULES.items():
            active = self.current == mod
            tk.Button(top, text=label, command=lambda m=mod: self.switch(m), bg=BLUE if active else WHITE, fg=WHITE if active else BLUE, bd=1, padx=14, pady=8, font=FONT_TAB).pack(side="left", padx=4)

        outer = tk.Frame(self.frame, bg=WHITE, bd=1, relief="solid")
        outer.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        canvas = tk.Canvas(outer, bg=WHITE, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        xsb = tk.Scrollbar(outer, orient="horizontal", command=canvas.xview)
        table = tk.Frame(canvas, bg=WHITE)
        win = canvas.create_window((0, 0), window=table, anchor="nw")

        def upd(_event=None):
            table.update_idletasks()
            target_width = max(canvas.winfo_width(), table.winfo_reqwidth())
            canvas.itemconfigure(win, width=max(1, target_width))
            canvas.configure(scrollregion=canvas.bbox("all"))

        table.bind("<Configure>", upd)
        canvas.bind("<Configure>", upd)
        canvas.configure(yscrollcommand=sb.set, xscrollcommand=xsb.set)
        xsb.pack(side="bottom", fill="x")
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        headers = ["Aufgaben-ID", "Aufgabenname", "Zeitraum", "Zuständigkeit", "Fälligkeitslogik", "Datum letzte Erledigung", "Status", "Bericht"]
        widths = [120, 360, 130, 220, 220, 230, 190, 90]
        for c, (h, width) in enumerate(zip(headers, widths)):
            tk.Label(table, text=h, bg=HEADER, fg=TEXT, font=FONT_HEAD, padx=8, pady=9, anchor="w").grid(row=0, column=c, sticky="nsew", padx=1, pady=1)
            table.grid_columnconfigure(c, minsize=width)

        for r, (uid, (task, period, mod)) in enumerate(sorted(latest_by_uid(self.current).items()), 1):
            vals = [
                uid,
                task.get("title", ""),
                period_label(mod, period),
                task.get("owner", ""),
                task.get("due_mode", ""),
                task.get("done_at", "") or "",
                "Aktive Aufgabe" if not task.get("archived") else "Archivierte Aufgabe",
            ]
            for c, v in enumerate(vals):
                font = FONT_CELL_BOLD if c == 0 else FONT_CELL
                lab = tk.Label(table, text=v, bg=WHITE, fg=TEXT if c != 0 else BLUE, font=font, padx=8, pady=8, anchor="w", justify="left", wraplength=max(100, widths[c] - 18))
                lab.grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
                lab.bind("<Double-Button-1>", lambda _e, u=uid: self.detail(u))
            tk.Button(table, text="PDF", command=lambda u=uid: self.pdf_uid(u), bg=WHITE, fg=BLUE, bd=1, font=FONT_CELL_BOLD).grid(row=r, column=7, sticky="nsew", padx=1, pady=1)
        self.app.active_scroll_canvas = canvas
        upd()

    def switch(self, mod):
        self.current = mod
        self.render()

    def detail(self, uid):
        win = tk.Toplevel(self.root)
        win.title(f"Aufgabenmanager {uid}")
        win.geometry("1000x620")
        win.configure(bg=BG)
        txt = tk.Text(win, wrap="word", bg=WHITE, fg=TEXT, font=FONT_CELL, padx=12, pady=12)
        txt.pack(fill="both", expand=True, padx=12, pady=12)
        for u, t, p, m in collect(self.current):
            if u == uid:
                txt.insert("end", f"{period_label(m, p)}\nAufgabe: {t.get('title', '')}\nZuständig: {t.get('owner', '')}\nStatus: {t.get('status', '')}\nErledigt: {t.get('done_at', '')}\nAnlagen: {len(t.get('attachments', []))}\nKommentare: {len(t.get('comments', []))}\n\n")
        txt.configure(state="disabled")

    def pdf_uid(self, uid):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=f"Aufgabenmanager_{uid}.pdf")
        if not path:
            return
        rows = [["Zeitraum", "Aufgabe", "Zuständig", "Status", "Erledigt", "Anlagen", "Kommentare"]]
        for u, t, p, m in collect(self.current):
            if u == uid:
                rows.append([period_label(m, p), t.get('title', ''), t.get('owner', ''), t.get('status', ''), t.get('done_at', ''), str(len(t.get('attachments', []))), str(len(t.get('comments', [])))])
        write_pdf(path, f"Gesamtbericht Aufgaben-ID {uid}", rows)
        if messagebox.askyesno("PDF erstellt", "PDF öffnen?"):
            try:
                os.startfile(path)
            except Exception:
                try:
                    subprocess.Popen(["xdg-open", path])
                except Exception:
                    pass


def render(app):
    HistoryUI(app)
