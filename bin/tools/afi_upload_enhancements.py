"""FiBu Mate AFI-Upload UI/rules extension.

Loaded by supplier_invoice_afi_upload.py. Keeps the stable deterministic parsers and
adds central supplier management, AI prompt review, enhanced previews and CSV export.
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from collections import defaultdict
from pathlib import Path

GREEN = "#E6F4EA"

DEFAULT_SUPPLIERS = {
    "enbw": {
        "label": "EnBW Charging",
        "tax_code_19": "VD",
        "text_template": "EnBW Stromtanken {kennzeichen} {name}",
        "prompt": "Grundgebühr je Gesellschaft zusammenfassen. Grundgebühr je Nutzer Netto in Energiekosten einrechnen. Kennzeichen und Name im Text ausgeben.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Tanken Strom", "account_key": "Tanken Strom"}],
        "use_ai": True,
    },
    "dkv": {
        "label": "DKV",
        "tax_code_19": "VD",
        "text_template": "DKV {kostenart} {kennzeichen} {name}",
        "prompt": "Kostenart bestimmen. Tanken je Kennzeichen kontieren. Versicherungen nach Versicherungsregel kontieren. Kennzeichen und Name im Text ausgeben.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [
            {"name": "Tanken", "terms": ["diesel", "benzin", "kraftstoff"], "account_key": "DKV"},
            {"name": "Versicherung", "terms": ["versicherung", "insurance"], "account_key": "DEAS-Versicherungen"},
        ],
        "use_ai": True,
    },
    "vodafone": {
        "label": "Vodafone Mobilfunk",
        "tax_code_19": "VD",
        "text_template": "Vodafone {rufnummer} {name}",
        "prompt": "Rufnummern über die Telefonzuordnung kontieren und je Kostenstelle/Gesellschaft zusammenfassen.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Mobilfunk", "account_key": "Vodafone"}],
        "use_ai": True,
    },
    "kazenmaier": {
        "label": "Kazenmaier Bike Leasing",
        "tax_code_19": "VD",
        "text_template": "Kazenmaier {auftragsnummer} {name}",
        "prompt": "Je Auftragsgruppe und Person kontieren. Auftragsnummer und Name im Text ausgeben.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Bike Leasing", "account_key": "Bike Leasing"}],
        "use_ai": True,
    },
    "telekom": {
        "label": "Telekom",
        "tax_code_19": "VD",
        "text_template": "Telekom {rufnummer} {name}",
        "prompt": "Rufnummer und Name im Text. Kostenstelle aus Telefon- und Mitarbeiterstamm.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Telekommunikation", "account_key": "Telekom"}],
        "use_ai": True,
    },
    "deas": {
        "label": "DEAS",
        "tax_code_19": "VD",
        "text_template": "DEAS {kostenart} {name}",
        "prompt": "Kostenart Versicherung oder sonstige Leistung erkennen und passendes Sachkonto verwenden.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [
            {"name": "Versicherung", "account_key": "DEAS-Versicherungen"},
            {"name": "Sonstige", "account_key": "DEAS"},
        ],
        "use_ai": True,
    },
    "vw_leasing": {
        "label": "VW Leasing",
        "tax_code_19": "VD",
        "text_template": "VW Leasing {kennzeichen} {name}",
        "prompt": "Leasing je Fahrzeug und Kostenstelle kontieren.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Leasing", "account_key": "VW-Leasing"}],
        "use_ai": True,
    },
    "vw_versicherung": {
        "label": "VW Versicherungen",
        "tax_code_19": "VD",
        "text_template": "VW Versicherung {kennzeichen} {name}",
        "prompt": "Versicherung je Fahrzeug und Kostenstelle kontieren.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Versicherung", "account_key": "VW-Versicherungen"}],
        "use_ai": True,
    },
    "generic": {
        "label": "Weitere Lieferanten",
        "tax_code_19": "VD",
        "text_template": "{lieferant} {kostenart} {kennzeichen} {rufnummer} {name}",
        "prompt": "Lieferant, Kostenart und Kontierungsmerkmale ermitteln. Keine Kontierung erfinden.",
        "regions": {"inland": {"tax_code": "VD"}, "ausland": {"tax_code": "V0"}},
        "cost_types": [{"name": "Sonstige", "account_key": "Sonstige"}],
        "use_ai": True,
    },
}


def _merge(first, second):
    result = dict(first)
    for key, value in (second or {}).items():
        result[key] = _merge(result.get(key, {}), value) if isinstance(value, dict) and isinstance(result.get(key), dict) else value
    return result


def _supplier_key(result, rules):
    supplier = str(result.get("invoice", {}).get("supplier", "")).casefold()
    for key, rule in rules.get("suppliers", {}).items():
        words = [word for word in str(rule.get("label", key)).casefold().split() if len(word) > 3]
        if key.casefold() in supplier or any(word in supplier for word in words):
            return key
    return "generic" if "generic" in rules.get("suppliers", {}) else ""


def _ai_review(globals_dict, result, rules, supplier_key):
    """Run prompt review outside the FiBu Mate process; preserve protected fields."""
    rule = rules.get("suppliers", {}).get(supplier_key, {})
    if not rule.get("use_ai", False):
        return result
    module_path = Path(__file__).resolve()
    with tempfile.TemporaryDirectory(prefix="fibu_afi_ai_") as temp_dir:
        input_path = Path(temp_dir) / "input.json"
        output_path = Path(temp_dir) / "output.json"
        input_path.write_text(json.dumps({
            "general_prompt": rules.get("general_prompt", ""),
            "supplier_prompt": rule.get("prompt", ""),
            "structured_rule": rule,
            "upload_rows": result.get("upload_rows", []),
        }, ensure_ascii=False), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(module_path), "--ai-worker", str(input_path), str(output_path)],
            capture_output=True, text=True, timeout=180,
        )
        if completed.returncode != 0 or not output_path.is_file():
            raise RuntimeError((completed.stderr or completed.stdout or "KI-Prüflauf fehlgeschlagen")[-1000:])
        reviewed = json.loads(output_path.read_text(encoding="utf-8")).get("upload_rows", [])
        original = result.get("upload_rows", [])
        if len(reviewed) != len(original):
            raise RuntimeError("KI änderte die Anzahl der AFI-Zeilen")
        for old, new in zip(original, reviewed):
            for field in ("NET_VALUE", "GL_ACCOUNT", "COSTCENTER", "ORDERID"):
                if str(new.get(field, "")) != str(old.get(field, "")):
                    raise RuntimeError(f"KI änderte geschütztes Feld {field}")
            old["TEXT"] = str(new.get("TEXT", old.get("TEXT", "")))[:120]
            old["TAX_CODE"] = str(new.get("TAX_CODE", old.get("TAX_CODE", "")))[:10]
        result.setdefault("technical", {})["ai_prompts_applied"] = True
    return result


def apply_enhancements(g):
    tk, ttk = g["tk"], g["ttk"]
    messagebox, filedialog, simpledialog = g["messagebox"], g["filedialog"], g["simpledialog"]
    BaseUI = g["AFIUI"]
    original_defaults = g["_default_prompt_rules"]
    original_load = g["_load_prompt_rules"]

    def defaults():
        result = original_defaults()
        result["suppliers"] = _merge(DEFAULT_SUPPLIERS, result.get("suppliers", {}))
        return result

    def load_rules():
        return _merge(defaults(), original_load())

    g["_default_prompt_rules"] = defaults
    g["_load_prompt_rules"] = load_rules

    original_process = g["RuleEngine"].process

    def process_with_prompts(self, invoice_path, progress=lambda _message: None):
        result = original_process(self, invoice_path, progress)
        rules = getattr(self, "rules", load_rules())
        key = _supplier_key(result, rules)
        if key and rules.get("suppliers", {}).get(key, {}).get("use_ai", False):
            try:
                progress("Allgemeiner und lieferantenspezifischer Prompt werden durch die lokale KI geprüft ...")
                result = _ai_review(g, result, rules, key)
            except Exception as exc:
                result.setdefault("technical", {})["ai_prompts_applied"] = False
                result.setdefault("validation", {}).setdefault("warnings", []).append(f"KI-Promptprüfung nicht verfügbar: {exc}")
        return result

    g["RuleEngine"].process = process_with_prompts

    class EnhancedAFIUI(BaseUI):
        def __init__(self, app):
            super().__init__(app)
            self.rules = load_rules()
            self.zoom = 1.0
            self.pan_x = self.pan_y = 0
            self.drag_start = None
            self.supplier_tabs = {}
            self.db_open = False

        def render(self):
            super().render()
            self._bind_preview()
            self._postprocess_work_tab()

        def _walk(self, widget):
            yield widget
            for child in widget.winfo_children():
                yield from self._walk(child)

        def _postprocess_work_tab(self):
            for widget in list(self._walk(self.work_tab)):
                try:
                    if isinstance(widget, tk.Button) and widget.cget("text") == "Prompts & Regeln":
                        widget.destroy()
                except Exception:
                    pass
            boxes = [widget for widget in self.work_tab.winfo_children() if isinstance(widget, tk.LabelFrame)]
            if not boxes:
                return
            box = boxes[0]
            for widget in box.grid_slaves(row=0):
                try:
                    widget.configure(font=("Segoe UI", 10, "bold"))
                except Exception:
                    pass
            self.db_toggle = tk.Button(box, text="Datenbanken anzeigen ▼", command=lambda: self._toggle_databases(box), bg="#D9E2F3")
            self.db_toggle.grid(row=4, column=0, columnspan=4, sticky="w", pady=(4, 0))
            for row in (1, 2, 3):
                for widget in box.grid_slaves(row=row):
                    widget.grid_remove()

        def _toggle_databases(self, box):
            self.db_open = not self.db_open
            for row in (1, 2, 3):
                for widget in box.grid_slaves(row=row):
                    widget.grid() if self.db_open else widget.grid_remove()
            self.db_toggle.configure(text="Datenbanken ausblenden ▲" if self.db_open else "Datenbanken anzeigen ▼")

        def _render_rules_tab(self):
            frame = self.rules_tab
            for child in frame.winfo_children():
                child.destroy()
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)
            header = tk.Frame(frame, bg=self.bg)
            header.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
            tk.Label(header, text="Zentrale Prompt- und Regelpflege", bg=self.bg, font=("Segoe UI", 12, "bold")).pack(side="left")
            tk.Button(header, text="Lieferant hinzufügen", command=self.add_supplier, bg="#D9EAD3").pack(side="right", padx=5)
            tk.Button(header, text="Speichern", command=self.save_prompt_rules, bg="#0F6CBD", fg="white").pack(side="right", padx=5)
            notebook = ttk.Notebook(frame)
            notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
            self.rules_notebook = notebook
            general = tk.Frame(notebook, bg=GREEN)
            notebook.add(general, text="▰ Allgemeiner Prompt")
            general.rowconfigure(1, weight=1)
            general.columnconfigure(0, weight=1)
            tk.Label(general, text="Allgemeiner Prompt", bg=GREEN, font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
            prompt = tk.Text(general, wrap="word", undo=True, font=("Consolas", 10), bg="#F3FBF5")
            prompt.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
            prompt.insert("1.0", self.rules.get("general_prompt", ""))
            self.rule_widgets = {"general_prompt": prompt}
            self.supplier_tabs = {}
            for key, rule in self.rules.get("suppliers", {}).items():
                self._add_supplier_tab(notebook, key, rule)

        def _add_supplier_tab(self, notebook, key, rule):
            tab = tk.Frame(notebook, bg=self.bg)
            notebook.add(tab, text=rule.get("label", key))
            tab.columnconfigure(1, weight=1)
            tab.rowconfigure(7, weight=1)
            self.supplier_tabs[key] = tab
            label = tk.StringVar(value=rule.get("label", key))
            tax = tk.StringVar(value=rule.get("tax_code_19", "VD"))
            template = tk.StringVar(value=rule.get("text_template", ""))
            use_ai = tk.BooleanVar(value=rule.get("use_ai", True))
            for row, (caption, variable) in enumerate((("Bezeichnung", label), ("Steuerkennzeichen 19 %", tax), ("Buchungstext-Vorlage", template))):
                tk.Label(tab, text=caption, bg=self.bg).grid(row=row, column=0, sticky="w", padx=8, pady=4)
                tk.Entry(tab, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            tk.Checkbutton(tab, text="Allgemeinen und lieferantenspezifischen Prompt durch lokale KI berücksichtigen", variable=use_ai, bg=self.bg).grid(row=3, column=0, columnspan=2, sticky="w", padx=8)
            tk.Label(tab, text="Inland-/Ausland-Regeln (JSON)", bg=self.bg).grid(row=4, column=0, sticky="nw", padx=8, pady=4)
            regions = tk.Text(tab, height=5, font=("Consolas", 9))
            regions.grid(row=4, column=1, sticky="ew", padx=8, pady=4)
            regions.insert("1.0", json.dumps(rule.get("regions", {}), ensure_ascii=False, indent=2))
            tk.Label(tab, text="Kostenarten (JSON-Liste)", bg=self.bg).grid(row=5, column=0, sticky="nw", padx=8, pady=4)
            costs = tk.Text(tab, height=7, font=("Consolas", 9))
            costs.grid(row=5, column=1, sticky="ew", padx=8, pady=4)
            costs.insert("1.0", json.dumps(rule.get("cost_types", []), ensure_ascii=False, indent=2))
            tk.Label(tab, text="Lieferantenspezifischer Prompt", bg=self.bg).grid(row=6, column=0, columnspan=2, sticky="w", padx=8)
            supplier_prompt = tk.Text(tab, wrap="word", undo=True, font=("Consolas", 10))
            supplier_prompt.grid(row=7, column=0, columnspan=2, sticky="nsew", padx=8, pady=5)
            supplier_prompt.insert("1.0", rule.get("prompt", ""))
            tk.Button(tab, text="Lieferant entfernen", command=lambda supplier=key: self.remove_supplier(supplier), fg="#B42318").grid(row=8, column=1, sticky="e", padx=8, pady=4)
            self.rule_widgets[key] = {"label": label, "tax": tax, "template": template, "use_ai": use_ai, "regions": regions, "costs": costs, "prompt": supplier_prompt, "extra": {}}

        def add_supplier(self):
            label = simpledialog.askstring("Lieferant hinzufügen", "Bezeichnung des neuen Lieferanten:", parent=self.root)
            if not label:
                return
            key = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_") or "lieferant"
            base, number = key, 2
            while key in self.rules["suppliers"]:
                key = f"{base}_{number}"
                number += 1
            self.rules["suppliers"][key] = _merge(DEFAULT_SUPPLIERS["generic"], {"label": label})
            self._add_supplier_tab(self.rules_notebook, key, self.rules["suppliers"][key])
            self.rules_notebook.select(self.supplier_tabs[key])

        def remove_supplier(self, key):
            if messagebox.askyesno("Lieferant entfernen", f"'{self.rules['suppliers'][key].get('label', key)}' entfernen?"):
                self.rules_notebook.forget(self.supplier_tabs[key])
                self.supplier_tabs.pop(key, None)
                self.rule_widgets.pop(key, None)
                self.rules["suppliers"].pop(key, None)

        def save_prompt_rules(self):
            rules = load_rules()
            rules["general_prompt"] = self.rule_widgets["general_prompt"].get("1.0", "end-1c").strip()
            suppliers = {}
            try:
                for key, widgets in self.rule_widgets.items():
                    if key == "general_prompt":
                        continue
                    suppliers[key] = _merge(self.rules["suppliers"].get(key, {}), {
                        "label": widgets["label"].get().strip() or key,
                        "tax_code_19": widgets["tax"].get().strip(),
                        "text_template": widgets["template"].get().strip(),
                        "use_ai": bool(widgets["use_ai"].get()),
                        "regions": json.loads(widgets["regions"].get("1.0", "end-1c") or "{}"),
                        "cost_types": json.loads(widgets["costs"].get("1.0", "end-1c") or "[]"),
                        "prompt": widgets["prompt"].get("1.0", "end-1c").strip(),
                    })
                rules["suppliers"] = suppliers
                g["_save_prompt_rules"](rules)
                self.rules = rules
                messagebox.showinfo("Prompts & Regeln", "Zentrale Regeln wurden gespeichert.")
            except Exception as exc:
                messagebox.showerror("Prompts & Regeln", f"Ungültiges JSON oder Speicherfehler:\n{exc}")

        def _bind_preview(self):
            canvas = self.preview_canvas
            canvas.bind("<MouseWheel>", self._zoom)
            canvas.bind("<Button-4>", lambda event: self._zoom(event, 1))
            canvas.bind("<Button-5>", lambda event: self._zoom(event, -1))
            canvas.bind("<ButtonPress-1>", self._drag_start)
            canvas.bind("<B1-Motion>", self._drag)
            canvas.bind("<ButtonRelease-1>", lambda event: setattr(self, "drag_start", None))

        def _zoom(self, event, direction=None):
            if not self.preview_images:
                return
            step = direction if direction is not None else (1 if event.delta > 0 else -1)
            self.zoom = max(0.25, min(4.0, self.zoom * (1.15 if step > 0 else 1 / 1.15)))
            self.show_preview()

        def _drag_start(self, event):
            self.drag_start = (event.x, event.y, self.pan_x, self.pan_y)

        def _drag(self, event):
            if not self.drag_start:
                return
            x, y, old_x, old_y = self.drag_start
            self.pan_x = old_x + event.x - x
            self.pan_y = old_y + event.y - y
            self.show_preview()

        def show_preview(self):
            if not self.preview_images or not g.get("PIL_AVAILABLE", False) or not hasattr(self, "preview_canvas"):
                return
            source = self.preview_images[self.preview_index]
            width = max(100, self.preview_canvas.winfo_width())
            height = max(100, self.preview_canvas.winfo_height())
            base = min((width - 20) / source.width, (height - 20) / source.height)
            image_width = max(1, int(source.width * base * self.zoom))
            image_height = max(1, int(source.height * base * self.zoom))
            image = source.resize((image_width, image_height))
            limit_x = max(0, (image_width - width) // 2 + width // 3)
            limit_y = max(0, (image_height - height) // 2 + height // 3)
            self.pan_x = max(-limit_x, min(limit_x, self.pan_x))
            self.pan_y = max(-limit_y, min(limit_y, self.pan_y))
            self.preview_photo = g["ImageTk"].PhotoImage(image)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(width // 2 + self.pan_x, height // 2 + self.pan_y, image=self.preview_photo)
            self.preview_page_var.set(f"Seite {self.preview_index + 1} von {len(self.preview_images)} | Zoom {self.zoom:.0%}")
            self.prev_button.config(state="normal" if self.preview_index > 0 else "disabled")
            self.next_button.config(state="normal" if self.preview_index < len(self.preview_images) - 1 else "disabled")

        def _render_document_images(self, path):
            if path.suffix.lower() in (".xlsx", ".xlsm"):
                import openpyxl
                workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
                images = []
                try:
                    for sheet in workbook.worksheets:
                        rows = []
                        for row in sheet.iter_rows(values_only=True):
                            rows.append([str(value or "")[:35] for value in row[:12]])
                            if len(rows) >= 45:
                                break
                        images.append(self._table_image(sheet.title, rows))
                finally:
                    workbook.close()
                return images
            return super()._render_document_images(path)

        def _table_image(self, title, rows):
            Image, ImageDraw, ImageFont = g["Image"], g["ImageDraw"], g["ImageFont"]
            columns = max([len(row) for row in rows] or [1])
            cell_width, row_height = 180, 34
            width = min(2200, columns * cell_width + 40)
            height = max(300, min(1800, (len(rows) + 2) * row_height + 40))
            image = Image.new("RGB", (width, height), "white")
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype("arial.ttf", 15)
                bold = ImageFont.truetype("arialbd.ttf", 17)
            except Exception:
                font = bold = ImageFont.load_default()
            draw.rectangle((0, 0, width, row_height + 15), fill="#D9EAD3")
            draw.text((15, 10), title, fill="black", font=bold)
            for row_index, row in enumerate(rows):
                y = row_height + 15 + row_index * row_height
                for column_index, value in enumerate(row):
                    x = 20 + column_index * cell_width
                    draw.rectangle((x, y, x + cell_width, y + row_height), outline="#AAB2BD", fill="#EEF4FB" if row_index == 0 else "white")
                    draw.text((x + 5, y + 8), value, fill="black", font=font)
            return image

        def done(self, result):
            super().done(result)
            self.export.config(state="normal")

        def export_csv(self):
            if not self.result:
                return
            if not self.result.get("validation", {}).get("export_allowed", False):
                if not messagebox.askyesno("CSV exportieren", "Es bestehen Prüfhinweise. Sichtbare Vorschau trotzdem exportieren?"):
                    return
            path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="AFI_Upload.csv", filetypes=[("CSV-Datei", "*.csv")])
            if path:
                with open(path, "w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=g["UPLOAD_COLUMNS"], delimiter=";", extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(self.result["upload_rows"])
                messagebox.showinfo("CSV exportieren", f"CSV gespeichert:\n{path}")

    g["AFIUI"] = EnhancedAFIUI


def _ai_worker(input_path, output_path):
    data = json.loads(Path(input_path).read_text(encoding="utf-8"))
    from foundry_local_sdk import Configuration, FoundryLocalManager
    root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "FiBuMate" / "FoundryLocal"
    root.mkdir(parents=True, exist_ok=True)
    try:
        FoundryLocalManager.initialize(Configuration(app_name="FiBuMate-AFI-Prompt", app_data_dir=str(root), model_cache_dir=str(root / "models"), logs_dir=str(root / "logs")))
    except Exception:
        pass
    manager = FoundryLocalManager.instance
    model = manager.catalog.get_model("phi-4-mini")
    if model is None:
        raise RuntimeError("phi-4-mini ist nicht verfügbar")
    if not model.is_cached:
        model.download()
    model.load()
    try:
        client = model.get_chat_client()
        client.settings.temperature = 0
        client.settings.max_tokens = 2048
        client.settings.response_format = {"type": "json_object"}
        instruction = (
            "Prüfe die AFI-Zeilen anhand der Prompts. Gib nur JSON mit upload_rows zurück. "
            "Behalte Anzahl, NET_VALUE, GL_ACCOUNT, COSTCENTER und ORDERID unverändert. "
            "Ändere nur TEXT und TAX_CODE.\n\nALLGEMEINER PROMPT:\n" + data["general_prompt"] +
            "\n\nLIEFERANTENPROMPT:\n" + data["supplier_prompt"] +
            "\n\nSTRUKTURIERTE REGELN:\n" + json.dumps(data["structured_rule"], ensure_ascii=False) +
            "\n\nAFI-ZEILEN:\n" + json.dumps(data["upload_rows"], ensure_ascii=False)
        )
        response = client.complete_chat([
            {"role": "system", "content": "Du bist der lokale AFI-Regelprüfer von FiBu Mate."},
            {"role": "user", "content": instruction},
        ])
        result = json.loads(response.choices[0].message.content)
        Path(output_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    finally:
        try:
            model.unload()
        except Exception:
            pass


if __name__ == "__main__" and len(sys.argv) >= 4 and sys.argv[1] == "--ai-worker":
    try:
        _ai_worker(sys.argv[2], sys.argv[3])
    except Exception:
        traceback.print_exc()
        sys.exit(1)
