import os
import sys
import json
import importlib
import webbrowser
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from urllib.parse import quote

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

APP_NAME = "FiBu Mate"
VERSION_PREFIX = "0.4"
DEFAULT_BUILD = 0
VERSION_STATE_FILE = "version_state.json"
VERSION_HISTORY_FILE = "version_history.json"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
IMG_DIR = os.path.join(BIN_DIR, "Imgs")
ICON_DIR = os.path.join(IMG_DIR, "Icons")
USER_DIR = os.path.join(BIN_DIR, "User")
USER_DATA_PATH = os.path.join(USER_DIR, "fibu_mate_users.json")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

BANNER_GROSS_PATH = os.path.join(IMG_DIR, "FMBanner_Gross.png")
BANNER_KLEIN_PATH = os.path.join(IMG_DIR, "FMBanner_Klein.png")
HELP_IMAGE_PATH = os.path.join(IMG_DIR, "FM_Help_Menu.png")
ICON_FILES = {
    "help": "metrostatus_question_support_6987.ico",
    "idea": "2799205-creative-idea-light_99776.ico",
    "doc_add": "addfileinterfacesymbolofpapersheetwithtextlinesandplussign_79821.ico",
    "doc_file": "fileinterfacesymboloftextpapersheet_79740.ico",
    "attach": "-attach-file_90371.ico",
    "calendar": "calendar-icon_34471.ico",
    "gear": "1486504840-cog-cogwheel-gear-repr-options-setting_81360.ico",
    "info": "1486504328-bullet-list-menu-lines-points-items-options_81334.ico",
    "lock": "lock_lock_15063.ico",
    "unlock": "lock_unlock_15064.ico",
    "xls": "ext_xls_filetype_icon_176238.ico",
    "pdf": "ext_pdf_filetype_icon_176234.ico",
    "compliance": "1486503790-bank-building-government-house-real-estate-panteon_81294.ico",
    "tax_reporting": "1486504352-checklist-clipboard-inventory-list-report-tasks-todo_81326.ico",
    "audit": "1486506277-like-thumbs-up-hands-gesture-finger-vote_81482.ico",
    "documentation": "1486485527-account-albums-screens-tabs_81163.ico",
    "search": "1486503763-bigger-enlarge-search-magnifier-magnify-zoom_81256.ico",
    "filter": "1486504837-descending-filter-filtering-tool-funnel-sort_81363.ico",
    "edit": "1486504369-change-edit-options-pencil-settings-tools-write_81307.ico",
}
INTERSPORT_LOGO_CANDIDATES = ["IS_Banner_lang.png", "Intersport_Logo.png", "INTERSPORT_Logo.png", "intersport_logo.png", "INTERSPORT.png"]

BLUE = "#004B93"
RED = "#E30613"
GOLD = "#FFD700"
STAR_GREY = "#7A7F87"
BG = "#E8EEF5"
HEADER = "#D3DEE9"
LINE = "#91A3B5"
TEXT = "#182431"
TEXT2 = "#445364"
SHADOW = "#A8B5C3"
WHITE = "#FFFFFF"
GREY_DISABLED = "#B9C3CF"
GREY_TILE = "#D6DCE4"

FONT_TITLE = ("Segoe UI", 36, "bold")
FONT_MENU = ("Segoe UI", 27, "bold")
FONT_TILE = ("Segoe UI", 18, "bold")
FONT_TILE_SMALL = ("Segoe UI", 15, "bold")
FONT_SMALL = ("Segoe UI", 10)
MINI_WIDGET_W = 174
MINI_WIDGET_H = 30
MINI_WIDGET_GAP = 8

COLOR_PALETTE = [("Blau", BLUE), ("Grün", "#059669"), ("Rot", RED), ("Gelb", "#F59E0B"), ("Lila", "#7C3AED"), ("Pink", "#EC4899"), ("Dunkelgrau", "#334155"), ("Orange", "#F97316"), ("Türkis", "#06B6D4")]

ROLE_E1 = "E1 - Standard"
ROLE_E2 = "E2 - Erweitert"
ROLE_E3 = "E3 - Administrator"
ROLE_E4 = "E4 - System-Administrator"
ROLE_STANDARD = ROLE_E1
ROLE_ADMIN = ROLE_E3
OLD_ROLE_E4 = "Wagnerm"
ROLE_WAGNERM = ROLE_E4
SUPERUSER_KEY = "wagnerm"
ROLE_ORDER = [ROLE_E1, ROLE_E2, ROLE_E3, ROLE_E4]
ROLE_RANK = {
    ROLE_E1: 1, ROLE_E2: 2, ROLE_E3: 3, ROLE_E4: 4,
    "Standard": 1, "Ebene 1": 1, "E1": 1,
    "Ebene 2": 2, "E2": 2,
    "Administrator": 3, "Ebene 3": 3, "E3": 3,
    "System-Administrator": 4, OLD_ROLE_E4: 4, "Ebene 4": 4, "E4": 4,
}
ROLE_MIGRATION = {"Standard": ROLE_E1, "Administrator": ROLE_E3, "System-Administrator": ROLE_E4, OLD_ROLE_E4: ROLE_E4, "Ebene 1": ROLE_E1, "Ebene 2": ROLE_E2, "Ebene 3": ROLE_E3, "Ebene 4": ROLE_E4, "E1": ROLE_E1, "E2": ROLE_E2, "E3": ROLE_E3, "E4": ROLE_E4}

TOOL_REGISTRY = {
    "nike_pdf_to_excel": {"title": "Nike - PDF zu Excel", "module": "bin.tools.nike_pdf_to_excel", "favorite_label": "Nike PDF"},
    "nike_op_liste_pdf_check": {"title": "Nike - OP-Liste: Vollständigkeit PDF-Rechnungen prüfen", "module": "bin.tools.nike_op_liste_pdf_check", "favorite_label": "Nike OP PDF"},
    "monthly_close": {"title": "Monatsabschluss", "module": "bin.tools.monthly_close", "favorite_label": "Monatsabschluss"},
    "quarterly_close": {"title": "Quartalsabschluss", "module": "bin.tools.quarterly_close", "favorite_label": "Quartalsabschluss"},
    "yearly_close": {"title": "Jahresabschluss", "module": "bin.tools.yearly_close", "favorite_label": "Jahresabschluss"},
    "task_history": {"title": "Aufgaben-Historie nach ID", "module": "bin.tools.task_history", "favorite_label": "Historie"},
    "x001_sap_test": {"title": "X001 SAP - Test", "module": "bin.tools.x001_sap_test", "favorite_label": "X001"},
    "tax_reporting": {"title": "Steuermeldungs-Cockpit", "module": "bin.tools.compliance_tax_reporting", "favorite_label": "Steuermeldungen"},
    "audit_cockpit": {"title": "Audit-Cockpit", "module": "bin.tools.compliance_audit_cockpit", "favorite_label": "Audit"},
    "documentation_center": {"title": "Dokumentationszentrale", "module": "bin.tools.compliance_documentation_center", "favorite_label": "Dokumente"},
}

MODULE_DESCRIPTIONS = {
    "nike_pdf_to_excel": "Mit diesem Modul lassen sich große Mengen an Nike PDF-Rechnungen in Excel ein Excel-Format ausgeben. Die auszugebenden Daten lassen sich filtern und sind individuell anpassbar.",
    "nike_op_liste_pdf_check": "Prüft die Vollständigkeit von Nike PDF-Rechnungen gegen eine OP-Liste: Rechnungsnummern aus PDF-Dateinamen werden mit Spalte B der Excel-Datei abgeglichen.",
    "monthly_close": "Interaktives Monatsabschluss-Cockpit mit Teamfortschritt, Aufgabenstatus, Fristwarnungen und Anlagen je Aufgabe.",
    "quarterly_close": "Interaktives Quartalsabschluss-Cockpit auf Basis der Monatsabschluss-Struktur mit Quartalsperioden.",
    "tax_reporting": "Überwacht steuerliche Meldungen und Meldefristen je Zeitraum inklusive Status, Zuständigkeit, Nachweisen, Historie und Abschlussbericht-Integration.",
    "audit_cockpit": "Zentrale Übersicht über kritische Systemereignisse wie Wiederöffnungen, Berechtigungsänderungen, Benutzeränderungen und nachträgliche Änderungen nach Abschluss.",
    "documentation_center": "Zentrale Suche und Prüfung aller Nachweise, Anlagen, Dokumentationspfade und Berichte aus FiBu Mate inklusive fehlender oder ungültiger Dokumentationen.",
    "yearly_close": "Interaktives Jahresabschluss-Cockpit für Geschäftsjahre vom 01.10. bis 30.09.",
    "task_history": "Zentrale Aufgaben-Historie nach Aufgaben-ID mit Zeitraumverlauf und PDF-Berichten.",
    "x001_sap_test": "SAP-Scripting-Test; Scripting in SAP deaktiviert.",
}
DESCRIPTION_FONT = ("Segoe UI", 11)
DESCRIPTION_COLOR = TEXT2
DESCRIPTION_X_OFFSET = 14
DESCRIPTION_Y_OFFSET = 18


def maximize_window(window: tk.Tk):
    try:
        window.state("zoomed")
    except Exception:
        try:
            window.attributes("-zoomed", True)
        except Exception:
            pass


def x_pct(width: int, percent: float) -> float:
    return width * percent / 100


def y_pct(height: int, percent: float) -> float:
    return height * (1 - percent / 100)


def normalize_username(username: str) -> str:
    return " ".join(str(username).strip().split()).casefold()


def _rgb(hex_color: str):
    v = hex_color.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def blend(a: str, b: str, t: float) -> str:
    ar, ag, ab = _rgb(a)
    br, bg, bb = _rgb(b)
    return _hex((int(ar + (br - ar) * t), int(ag + (bg - ag) * t), int(ab + (bb - ab) * t)))


def darken(color: str, amount: float = 0.18) -> str:
    return blend(color, "#000000", amount)


def now_date_str() -> str:
    return datetime.now().strftime("%y%m%d")


def load_image(path: str):
    if not PIL_AVAILABLE:
        return None
    try:
        if path and os.path.exists(path):
            return Image.open(path)
    except Exception:
        return None
    return None


def resize_keep_ratio(image, max_w, max_h):
    ow, oh = image.size
    scale = min(1, max_w / ow, max_h / oh)
    return image.resize((max(1, int(ow * scale)), max(1, int(oh * scale))))


def find_intersport_logo():
    for name in INTERSPORT_LOGO_CANDIDATES:
        path = os.path.join(IMG_DIR, name)
        if os.path.exists(path):
            return path
    return None


class ArrowIndicator(tk.Canvas):
    def __init__(self, parent, direction, command, size=46):
        super().__init__(parent, width=size, height=size, bg=BG, highlightthickness=0, bd=0)
        self.direction = direction
        self.command = command
        self.size = size
        self.enabled = True
        self.hover = False
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)
        self._draw()

    def tip_offset_from_center(self) -> float:
        s = self.size
        tip_y = (s - 11) if self.direction == "down" else 11
        return tip_y - (s / 2)

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        self.configure(cursor="hand2" if self.enabled else "arrow")
        self._draw()

    def _enter(self, *_):
        self.hover = True
        self._draw()

    def _leave(self, *_):
        self.hover = False
        self._draw()

    def _click(self, *_):
        if self.enabled and self.command:
            self.command()

    def _draw(self):
        self.delete("all")
        s = self.size
        if self.hover and self.enabled:
            self.create_oval(4, 4, s - 4, s - 4, fill=blend(BG, WHITE, 0.55), outline="")
        c = BLUE if self.enabled else GREY_DISABLED
        if self.direction == "up":
            pts = (s / 2, 11, 13, s - 14, s - 13, s - 14)
            self.create_polygon(*pts, fill=c, outline=c)
            self.create_rectangle(s / 2 - 4, s - 16, s / 2 + 4, s - 11, fill=c, outline=c)
        else:
            pts = (13, 14, s - 13, 14, s / 2, s - 11)
            self.create_polygon(*pts, fill=c, outline=c)
            self.create_rectangle(s / 2 - 4, 11, s / 2 + 4, 16, fill=c, outline=c)


class Tile(tk.Canvas):
    def __init__(self, parent, app, tile_id, title, command=None, favorite_enabled=False, fixed_color=None, lock_tile=False, center_text=False, icon_type=None, corner_fold=False):
        super().__init__(parent, highlightthickness=0, bd=0, bg=BG, cursor="arrow", takefocus=True)
        self.app = app
        self.tile_id = tile_id
        self.title = title
        self.command = command
        self.favorite_enabled = favorite_enabled
        self.fixed_color = fixed_color
        self.lock_tile = lock_tile
        self.center_text = center_text
        self.icon_type = icon_type
        self.corner_fold = corner_fold
        self.tile_width = 300
        self.tile_height = 150
        self.hovered = False
        self.pressed = False
        self.star_bounds = None
        self.star_click_started = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<FocusIn>", lambda e: self.app.set_focused_tile(self))
        self.bind("<Key-Return>", self.on_keyboard_activate)
        self.bind("<space>", self.on_keyboard_activate)
        self.draw()

    def base_color(self):
        return self.fixed_color or (self.app.current_tile_color() or BLUE)

    def current_color(self):
        c = self.base_color()
        if self.pressed:
            return darken(c, 0.28)
        if self.hovered:
            return darken(c, 0.16)
        return c

    def resize_tile(self, width, height):
        self.tile_width = int(width)
        self.tile_height = int(height)
        self.configure(width=self.tile_width + 16, height=self.tile_height + 16)
        self.draw()

    def title_font(self):
        return FONT_TILE_SMALL if len(self.title) > 28 else FONT_TILE

    def _draw_corner_fold(self, x1, y0):
        size = min(30, max(18, int(self.tile_height * 0.20)))
        self.create_polygon(x1 - size, y0, x1, y0, x1, y0 + size, fill="#D6DCE4", outline="#C2CAD5")
        self.create_line(x1 - size, y0, x1, y0 + size, fill="#EEF2F6", width=1)

    def _draw_worksheet_icon(self, cx, cy):
        color = BLUE if self.lock_tile else "white"
        lw = 2
        # Nur das vordere Blatt: A4-Verhältnis, ohne hinteres Rahmen-/Blatt-Element
        page_w = 34
        page_h = 48
        x0 = cx - page_w / 2
        y0 = cy - page_h / 2
        x1 = cx + page_w / 2
        y1 = cy + page_h / 2
        fold = 10
        self.create_line(x0, y0, x1 - fold, y0, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x1 - fold, y0, x1, y0 + fold, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x1, y0 + fold, x1, y1, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x1, y1, x0, y1, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x0, y1, x0, y0, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x1 - fold, y0, x1 - fold, y0 + fold, fill=color, width=lw)
        self.create_line(x1 - fold, y0 + fold, x1, y0 + fold, fill=color, width=lw)
        # kurze Textlinien oben wie in der Vorlage
        self.create_line(x0 + 6, y0 + 9, x0 + 18, y0 + 9, fill=color, width=lw + 1, capstyle="round")
        self.create_line(x0 + 6, y0 + 15, x0 + 24, y0 + 15, fill=color, width=lw + 1, capstyle="round")
        # Tabellenbereich im unteren Blattbereich
        tx0, ty0, tx1, ty1 = x0 + 5, y0 + 23, x1 - 5, y1 - 5
        self.create_rectangle(tx0, ty0, tx1, ty1, outline=color, width=lw)
        for x in (tx0 + (tx1 - tx0) / 4, tx0 + (tx1 - tx0) / 2, tx0 + 3 * (tx1 - tx0) / 4):
            self.create_line(x, ty0, x, ty1, fill=color, width=lw)
        for y in (ty0 + (ty1 - ty0) / 4, ty0 + (ty1 - ty0) / 2, ty0 + 3 * (ty1 - ty0) / 4):
            self.create_line(tx0, y, tx1, y, fill=color, width=lw)

    def _draw_calendar_icon(self, cx, cy):
        color = "white"
        lw = 3
        # rounded outline built with arcs + lines
        self.create_arc(cx - 25, cy - 19, cx - 7, cy - 1, start=90, extent=90, outline=color, width=lw, style="arc")
        self.create_arc(cx + 7, cy - 19, cx + 25, cy - 1, start=0, extent=90, outline=color, width=lw, style="arc")
        self.create_arc(cx - 25, cy + 8, cx - 7, cy + 26, start=180, extent=90, outline=color, width=lw, style="arc")
        self.create_arc(cx + 7, cy + 8, cx + 25, cy + 26, start=270, extent=90, outline=color, width=lw, style="arc")
        self.create_line(cx - 16, cy - 19, cx + 16, cy - 19, fill=color, width=lw)
        self.create_line(cx - 25, cy - 10, cx - 25, cy + 17, fill=color, width=lw)
        self.create_line(cx + 25, cy - 10, cx + 25, cy + 17, fill=color, width=lw)
        self.create_line(cx - 16, cy + 26, cx + 16, cy + 26, fill=color, width=lw)
        self.create_line(cx - 25, cy - 5, cx + 25, cy - 5, fill=color, width=lw)
        # rings
        self.create_line(cx - 13, cy - 25, cx - 13, cy - 13, fill=color, width=5, capstyle="round")
        self.create_line(cx + 13, cy - 25, cx + 13, cy - 13, fill=color, width=5, capstyle="round")
        # day boxes
        for x, y in [(cx - 12, cy + 4), (cx, cy + 4), (cx + 12, cy + 4), (cx - 12, cy + 16), (cx, cy + 16)]:
            self.create_rectangle(x - 4, y - 4, x + 4, y + 4, outline=color, width=2)
        # check mark
        self.create_line(cx + 10, cy + 16, cx + 15, cy + 21, fill=color, width=lw, capstyle="round")
        self.create_line(cx + 15, cy + 21, cx + 24, cy + 10, fill=color, width=lw, capstyle="round")

    def _draw_module_menu_icon(self, cx, cy):
        self._draw_worksheet_icon(cx, cy)

    def _draw_gear_icon(self, cx, cy):
        color = "white"
        for dx, dy in [(0, -16), (0, 16), (-16, 0), (16, 0), (-11, -11), (11, -11), (-11, 11), (11, 11)]:
            self.create_rectangle(cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3, fill=color, outline=color)
        self.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, outline=color, width=3)
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline=color, width=2)

    def _draw_info_icon(self, cx, cy):
        color = "white"
        self.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, outline=color, width=4)
        self.create_oval(cx - 3, cy - 12, cx + 3, cy - 6, fill=color, outline=color)
        self.create_rectangle(cx - 4, cy - 1, cx + 4, cy + 13, fill=color, outline=color)
        self.create_rectangle(cx - 8, cy + 9, cx + 8, cy + 15, fill=color, outline=color)

    def _draw_lock_icon(self, cx, cy):
        color = BLUE if self.lock_tile else "white"
        lw = 4
        self.create_arc(cx - 19, cy - 27, cx + 19, cy + 11, start=0, extent=180, style="arc", outline=color, width=lw)
        self.create_line(cx - 19, cy - 8, cx - 19, cy - 1, fill=color, width=lw)
        self.create_line(cx + 19, cy - 8, cx + 19, cy - 1, fill=color, width=lw)
        self.create_rectangle(cx - 23, cy - 4, cx + 23, cy + 26, outline=color, width=lw)
        self.create_oval(cx - 5, cy + 6, cx + 5, cy + 16, outline=color, width=lw)
        self.create_line(cx, cy + 15, cx, cy + 23, fill=color, width=lw)

    def _draw_main_icon(self, icon_type, cx, cy):
        if hasattr(self.app, "draw_tile_icon_image") and self.app.draw_tile_icon_image(self, icon_type, cx, cy):
            return
        if icon_type == "modules":
            self._draw_module_menu_icon(cx, cy)
        elif icon_type == "worksheet":
            self._draw_worksheet_icon(cx, cy)
        elif icon_type == "calendar":
            self._draw_calendar_icon(cx, cy)
        elif icon_type == "gear":
            self._draw_gear_icon(cx, cy)
        elif icon_type == "info":
            self._draw_info_icon(cx, cy)
        elif icon_type == "lock":
            self._draw_lock_icon(cx, cy)

    def draw(self):
        self.delete("all")
        pad = 8
        off = 1 if self.pressed else 0
        x0, y0 = pad + off, pad + off
        x1, y1 = x0 + self.tile_width - off * 2, y0 + self.tile_height - off * 2
        if not self.pressed:
            self.create_rectangle(pad + 5, pad + 6, pad + 5 + self.tile_width, pad + 6 + self.tile_height, fill=SHADOW, outline=SHADOW)
        self.create_rectangle(x0, y0, x1, y1, fill=self.current_color(), outline=self.current_color())
        if self.corner_fold:
            self._draw_corner_fold(x1, y0)
        title_y = y0 + 22
        icon_y = y1 - 42
        title_font = FONT_TILE_SMALL if len(self.title) > 28 else self.title_font()
        title_color = BLUE if self.lock_tile else "white"
        icon_to_draw = "lock" if self.lock_tile else self.icon_type
        if self.center_text and not icon_to_draw:
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=self.title, anchor="center", fill=title_color, font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")
        else:
            self.create_text((x0 + x1) / 2, title_y, text=self.title, anchor="n", fill=title_color, font=title_font, width=max(120, self.tile_width - 44), justify="center")
            if icon_to_draw:
                close_period = self.app.current_close_period_label(self.tile_id) if hasattr(self.app, "current_close_period_label") else ""
                if close_period and self.tile_id in ("monthly_close", "quarterly_close", "yearly_close"):
                    icon_x = x0 + 98
                    self._draw_main_icon(icon_to_draw, icon_x, icon_y)
                    self.create_text(icon_x + 48, icon_y, text=close_period, anchor="w", fill=title_color, font=("Segoe UI", 13, "italic"), width=max(120, x1 - icon_x - 58), justify="left")
                else:
                    self._draw_main_icon(icon_to_draw, (x0 + x1) / 2, icon_y)
        self.star_bounds = None
        if self.favorite_enabled and self.tile_id in TOOL_REGISTRY and (self.hovered or self.tile_id in self.app.favorites):
            sx, sy = x1 - 24, y0 + 24
            self.star_bounds = (sx - 18, sy - 18, sx + 18, sy + 18)
            self.create_text(sx, sy, text="★", fill=GOLD if self.tile_id in self.app.favorites else STAR_GREY, font=("Segoe UI", 24, "bold"))

    def point_in_star(self, x, y):
        return bool(self.star_bounds and self.star_bounds[0] <= x <= self.star_bounds[2] and self.star_bounds[1] <= y <= self.star_bounds[3])

    def on_enter(self, *_):
        self.hovered = True
        self.configure(cursor="hand2")
        self.draw()

    def on_leave(self, *_):
        self.hovered = False
        self.pressed = False
        self.star_click_started = False
        self.configure(cursor="arrow")
        self.draw()

    def on_press(self, event=None):
        self.focus_set()
        self.app.set_focused_tile(self)
        self.star_click_started = bool(event and self.point_in_star(event.x, event.y))
        self.pressed = not self.star_click_started
        self.draw()

    def on_release(self, event=None):
        if self.star_click_started:
            self.star_click_started = False
            if event and self.point_in_star(event.x, event.y):
                self.app.toggle_favorite(self.tile_id)
            return
        was = self.pressed
        self.pressed = False
        self.draw()
        if was and self.command:
            self.after(80, self.command)

    def on_keyboard_activate(self, *_):
        if self.command:
            self.command()


class FiBuMateApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_exit)
        maximize_window(self.root)
        self.page_history = []
        self.breadcrumb = []
        self.current_page = "launch"
        self.current_title = ""
        self.widget_items = []
        self.focusable_tiles = []
        self.focus_index = -1
        self._suppress_next_global_return = False
        self.favorites = set()
        self.current_user_key = None
        self.current_user_display = ""
        self.user_data = self.load_user_data()
        self.ensure_permissions_defaults()
        self.version_state = self.load_version_state()
        self.bump_version_once(
            "2026-05-11_close_cutoff_subtasks_team_members_due_rules",
            [
                "Abschlusskalender angepasst: Kreditoren heißt nun Zentralregulierung, Controlling heißt nun Treasury.",
                "Monats- und Quartalsabschluss erweitert: Team-Mitglieder können im Bearbeitungsmodus je Übersichtskachel gepflegt und unter der nächsten Frist angezeigt werden.",
                "Monats- und Quartalsabschluss erweitert: Aufgaben können Unteraufgaben erhalten; Unteraufgaben sind separat abhakbar und steuern den Erledigt-Status der Hauptaufgabe.",
                "Fälligkeitsarten im Monats- und Quartalsabschluss auf Abschluss-Stichtag, x. Werktag des Folgemonats, x. Tag des Kalendermonats und Konkretes Datum umgestellt.",
                "Abschluss-Stichtag kann in der Abschlussübersicht gepflegt werden und wird automatisch auf Aufgaben mit Fälligkeitsart Abschluss-Stichtag übertragen.",
            ],
        )
        self.bump_version_once(
            "2026-05-11_nike_opliste_export_thread_performance_fix",
            [
                "Nike OP-Liste Modul stabilisiert: Export läuft im Hintergrund, damit FiBu Mate während großer .xlsx-Auswertungen nicht einfriert.",
                "Nike OP-Liste Modul optimiert: OP-Liste wird performanter über Zeilen-Iteratoren eingelesen.",
                "Nike OP-Liste Modul verbessert: Export-Button wird während der Verarbeitung gesperrt und Fortschritt/Fehler werden sauber zurückgemeldet.",
            ],
        )
        self.bump_version_once(
            "2026-05-11_nike_obsolete_removed_opliste_pdf_check_added",
            [
                "Nike-Module bereinigt: „Nike - Differenzen: PDF vs ZMIR6“ wurde entfernt, da das Modul obsolet ist.",
                "Nike-Module bereinigt: „Nike - Differenzbericht Sales und Lager“ wurde entfernt, da das Modul obsolet ist.",
                "Neues Modul ergänzt: „Nike - OP-Liste: Vollständigkeit PDF-Rechnungen prüfen“.",
                "Neues Nike-Modul vergleicht Rechnungsnummern aus OP-Liste Excel Spalte B mit Rechnungsnummern aus PDF-Dateinamen und exportiert zwei Auswertungsblätter.",
            ],
        )
        self.bump_version_once(
            "2026-05-12_monthly_close_recurring_workday_catalog_due_visibility",
            [
                "Monatsabschluss erweitert: Aufgaben können im Bearbeitungsmodus als wiederkehrend markiert werden.",
                "Monatsabschluss erweitert: zentraler Aufgabenkatalog für wiederkehrende Aufgaben eingeführt.",
                "Monatsabschluss erweitert: wiederkehrende Aufgaben werden automatisch in Folgemonate ab dem aktuellen Monat übernommen.",
                "Monatsabschluss erweitert: Fälligkeit kann als konkretes Datum, x. Werktag des Monats oder x. Werktag des Folgemonats gepflegt werden.",
                "Monatsabschluss erweitert: Werktagsberechnung berücksichtigt Montag bis Freitag sowie Feiertage Baden-Württemberg und verschiebt auf den nächsten Werktag.",
                "Monatsabschluss verbessert: berechnetes Fälligkeitsdatum wird im Aufgaben-Dialog direkt als Vorschau angezeigt.",
                "Monatsabschluss verbessert: bei Werktags-Fälligkeit wird das Eingabefeld für ein konkretes Fälligkeitsdatum ausgeblendet.",
                "Monatsabschluss verbessert: Tabelle zeigt bei regelbasierter Fälligkeit zusätzlich den Regelhinweis an.",
                "Monatsabschluss angepasst: ZM/Z4/Z5a bleiben vorerst manuell über Aufgabe, Fristart, Priorität und Fälligkeitsregel pflegbar.",
            ],
        )

        self.bump_version_once(
            "2026-05-13_user_permissions_close_sync_transfer_deadline_defaults",
            [
                "Benutzerverwaltung erweitert: Standardbenutzer sehen nur eigene Benutzerdaten, dürfen die eigene E-Mail-Adresse pflegen und die Benutzerliste ist scrollbar mit sichtbarer Neuanlage für System-Administrator.",
                "Berechtigungen angepasst: Rolle Wagnerm heißt nun System-Administrator, Standardbenutzer können das Berechtigungsmenü nicht mehr öffnen und das Berechtigungsmenü ist scrollbar.",
                "Monats- und Quartalsabschluss erweitert: Aufgaben können inklusive Unteraufgaben in den jeweils anderen Abschluss übernommen werden.",
                "Monats- und Quartalsabschluss angepasst: Standardbenutzer dürfen Aufgaben nur als erledigt markieren, wenn sie selbst als zuständig eingetragen sind.",
                "Teammitglieder werden auf folgende Perioden übertragen und zwischen Monats- und Quartalsabschluss synchronisiert.",
                "Fristart keine entfernt; Standard-Fristart ist intern.",
            ],
        )
        self.bump_version_once(
            "2026-05-13_close_team_detail_scroll_collapsible_subtasks_recurring_transfer_fix",
            [
                "Monats- und Quartalsabschluss erweitert: Unteraufgaben sind in der Team-Detailsansicht standardmäßig zugeklappt und können je Aufgabe über „Unteraufgaben ausklappen >“ ein- und ausgeblendet werden.",
                "Monats- und Quartalsabschluss korrigiert: Beim Übernehmen einer Aufgabe in den jeweils anderen Abschluss wird der Status Wiederkehrend mit übernommen.",
                "Monats- und Quartalsabschluss erweitert: Aufgabenübersichten in den Team-Detailsichten sind scrollbar.",
            ],
        )

        self.bump_version_once(
            "2026-05-15_ui_adjustments_icon_background_refinement",
            [
                "Anpassung der Benutzeroberfläche",
            ],
        )

        self.bump_version_once(
            "2026-05-15_ui_adjustments_mini_widgets_help_line_worksheet",
            [
                "Anpassung der Benutzeroberfläche",
            ],
        )

        self.bump_version_once(
            "2026-05-15_close_calendar_documentation_attachments_detail_table",
            [
                "Abschlusskalender erweitert: In den Aufgaben-Detailansichten von Monats- und Quartalsabschluss wurde eine neue Spalte Dokumentation ergänzt; je Aufgabe und Unteraufgabe kann ein Dokumentationspfad als Leitfaden bzw. Aufgabenbeschreibung hinterlegt, geöffnet und geändert werden.",
                "Abschlusskalender erweitert: Das Anlagen-Popup unterstützt mehrere Anlagenpfade je Aufgabe und Unteraufgabe, manuelle Pfadeingabe, Auswahl per Dateidialog und Bemerkungen/Informationen zur Bearbeitung für alle Rollen.",
                "Abschlusskalender angepasst: Spaltenbreiten, Ausrichtungen und Fälligkeitsdarstellung in den Detailtabellen wurden optimiert; Fällig wird nun als Datum plus Fälligkeitsart angezeigt.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_ui_adjustments_ico_icon_replacements",
            [
                "Anpassung der Benutzeroberfläche",
            ],
        )
        self.bump_version_once(
            "2026-05-15_ui_adjustments_menu_tile_alignment_doc_attach_buttons",
            [
                "Anpassung der Benutzeroberfläche",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_documentation_remove_option",
            [
                "Monats- und Quartalsabschluss erweitert: Im Dokumentations-Popup kann ein hinterlegter Dokumentationspfad über ein Papierkorb-Icon entfernt werden.",
                "Monats- und Quartalsabschluss erweitert: Das Entfernen einer Dokumentation ist durch die Sicherheitsabfrage „Dokumentation entfernen?“ mit Ja/Nein geschützt.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_ui_adjustments_task_table_column_separators",
            [
                "Anpassung der Benutzeroberfläche",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_edit_icon_delegate_owner",
            [
                "Monats- und Quartalsabschluss angepasst: Der Bearbeitungsmodus-Button verwendet nun das Stift-Icon als direkte Schaltfläche ohne blaue Kachel.",
                "Monats- und Quartalsabschluss erweitert: Administratoren und System-Administratoren können die Zuständigkeit einer Aufgabe im geöffneten Zeitraum per Delegieren-Button ändern.",
                "Monats- und Quartalsabschluss erweitert: Wird eine Aufgabe mit Unteraufgaben delegiert, werden alle Unteraufgaben im betreffenden Zeitraum mitdelegiert.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_delete_scope_cleanup_sort_fix",
            [
                "Monats- und Quartalsabschluss korrigiert: Beim Löschen wird die ausgewählte Aufgabe eindeutig über die konkrete Aufgabeninstanz bzw. eine stabile Aufgabenkennung identifiziert, damit keine falschen Aufgaben gelöscht werden.",
                "Monats- und Quartalsabschluss erweitert: Beim Löschen kann gewählt werden, ob die Aufgabe nur im aktuellen Zeitraum oder auch in allen folgenden Zeiträumen gelöscht wird.",
                "Monats- und Quartalsabschluss erweitert: Im Bearbeitungsmodus gibt es den Button „Alle Folgezeiträume bereinigen“, der folgende Perioden an den aktuellen Aufgabenbestand anpasst.",
                "Monats- und Quartalsabschluss angepasst: Aufgaben und Unteraufgaben werden alphabetisch nach Titel sortiert angezeigt.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_complete_ids_linking_pdf_no_reportlab",
            [
                "Abschlusskalender erweitert: Jahresabschluss und Aufgaben-Historie nach ID wurden eingebunden.",
                "Monats-, Quartals- und Jahresabschluss erweitert: Aufgaben-IDs sind im Bearbeitungsdialog sichtbar und für Administrator/System-Administrator editierbar; bestehende fachliche Aufgaben erhalten initial QM001 bis QM016.",
                "Monats-, Quartals- und Jahresabschluss erweitert: Aufgaben werden über identische Aufgaben-ID verknüpft; bei ID-Änderung wird die alte ID mit Deaktivierungsdatum archiviert.",
                "Monats-, Quartals- und Jahresabschluss erweitert: Delegierungen können einmalig oder permanent auf Folgezeiträume übertragen werden.",
                "PDF-Berichte korrigiert: Export funktioniert ohne externe reportlab-Abhängigkeit über einen integrierten einfachen PDF-Generator.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_task_linking_mail_delegation",
            [
                "Aufgaben-Historie nach ID erweitert: Dezenter Reiter „Aufgaben verknüpfen“ ergänzt, inklusive Vorschlägen für gleichnamige Aufgaben in Monats-, Quartals- und Jahresabschluss.",
                "Abschlusskalender erweitert: Aufgaben-Verknüpfung setzt gemeinsame IDs automatisch nach Priorität M > Q > J und archiviert alte Aufgaben-IDs mit Deaktivierungsdatum.",
                "Monats-, Quartals- und Jahresabschluss erweitert: Bei Delegierung wird eine E-Mail an die neu zuständige Person vorbereitet; bei permanenter Delegierung mit Hinweis „bis auf Weiteres“.",
            ],
        )
        self.bump_version_once(
            "2026-05-15_close_period_lock_e_roles_reporting",
            [
                "Berechtigungen auf E1 bis E4 migriert: E1 Standard, E2 Erweitert, E3 Administrator, E4 System-Administrator; unbekannte Logins legen keine Benutzer mehr automatisch an.",
                "Benutzerverwaltung erweitert: Vorname und vollständiger Name werden für Ansprache und E-Mail-Kommunikation vorbereitet.",
                "Abschlusskalender erweitert: Zeiträume können ab E3 nach Ablauf des Abschluss-Stichtags geschlossen und wieder geöffnet werden; Wiederöffnung erfordert Begründung und automatische E-Mail-Benachrichtigung an E3/E4.",
                "Abschlussberichte erweitert: Berichtsdialog mit Signatur-/Freigabeoption, ausführlichere Inhalte, Änderungsprotokoll und ReportLab-Unterstützung mit einfachem Fallback.",
            ],
        )
        self.bump_version_once(
            "2026-05-27_ui_login_usermgmt_closetiles_automail_fix",
            [
                "Benutzeranmeldung korrigiert: Unbekannte Benutzernamen werden endgültig nicht mehr automatisch angelegt.",
                "Benutzerverwaltung angepasst: Speichern- und Löschen-Buttons sind getrennt, gleich groß und ohne Aktionsspalten-Überschrift dargestellt.",
                "Mini-Widgets angepasst: Änderung-vorschlagen-Icon wurde auf die neue Icon-Datei umgestellt.",
                "Abschlusskalender angepasst: Monats-, Quartals- und Jahresabschluss-Kacheln zeigen den aktuellen Zeitraum direkt neben dem Kalendericon.",
                "Abschlusskalender erweitert: E4 kann Auto-Mail kompakt ein- und ausschalten; Abschluss- und Wiederöffnungs-Mails beachten diese Einstellung.",
            ],
        )
        self.bump_version_once(
            "2026-05-27_v04_compliance_audit_tax_doc_modules",
            [
                "Major-Version auf v0.4 angehoben.",
                "Neues Hauptmenü Compliance & Audit ergänzt und Hauptmenü-Anordnung angepasst.",
                "Neues Modul Steuermeldungs-Cockpit mit Meldearten, Status, Nachweisen, Freigabe, Historie, PDF-Bericht und Audit-Anbindung ergänzt.",
                "Neues Modul Audit-Cockpit mit zentralem Audit-Log, Risikostufen, Filterung, PDF-Bericht und manuellem Archivierungsbutton für E3/E4 ergänzt.",
                "Neue Dokumentationszentrale mit Suche, Pfadprüfung, manuellen Dokumenten, PDF-/Excel-Export und Fehlende-Dokumentation-Bericht ergänzt.",
            ],
        )
        self.banner_big = load_image(BANNER_GROSS_PATH)
        self.banner_small = load_image(BANNER_KLEIN_PATH)
        self.help_image = load_image(HELP_IMAGE_PATH)
        logo_path = find_intersport_logo()
        self.intersport_logo = load_image(logo_path) if logo_path else None
        self.image_refs = []
        self.create_footer()
        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg=BG, cursor="arrow")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)
        self.active_scroll_canvas = None
        self.root.bind_all("<MouseWheel>", self.on_global_mousewheel)
        for key, handler in [("<Escape>", self.handle_escape), ("<Return>", self.handle_enter), ("<Tab>", self.handle_tab), ("<Shift-Tab>", self.handle_shift_tab), ("<ISO_Left_Tab>", self.handle_shift_tab)]:
            self.root.bind_all(key, handler)
        self.show_page("launch", add_to_history=False)

    def get_icon_photo(self, icon_key, max_w=32, max_h=32):
        if not PIL_AVAILABLE:
            return None
        if not hasattr(self, "icon_cache"):
            self.icon_cache = {}
        cache_key = (icon_key, int(max_w), int(max_h))
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
        file_name = ICON_FILES.get(icon_key, icon_key)
        path = os.path.join(ICON_DIR, file_name)
        img = load_image(path)
        if not img:
            return None
        try:
            img = img.convert("RGBA")
            img = resize_keep_ratio(img, max_w, max_h)
            photo = ImageTk.PhotoImage(img)
            self.icon_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    def draw_canvas_icon(self, canvas, icon_key, x, y, max_w=22, max_h=22):
        photo = self.get_icon_photo(icon_key, max_w, max_h)
        if not photo:
            return False
        canvas.create_image(x, y, image=photo)
        return True

    def draw_tile_icon_image(self, tile, icon_type, cx, cy):
        mapping = {"calendar": "calendar", "gear": "gear", "info": "info", "lock": "lock", "worksheet": "xls", "modules": "xls", "compliance": "compliance", "tax_reporting": "tax_reporting", "audit": "audit", "documentation": "documentation"}
        if icon_type == "pdf_xls":
            p1 = self.get_icon_photo("pdf", 50, 50)
            p2 = self.get_icon_photo("xls", 50, 50)
            if p1 and p2:
                tile.create_image(cx - 31, cy, image=p1)
                tile.create_image(cx + 31, cy, image=p2)
                return True
            return False
        icon_key = mapping.get(icon_type)
        if not icon_key:
            return False
        photo = self.get_icon_photo(icon_key, 48, 48)
        if not photo:
            return False
        tile.create_image(cx, cy, image=photo)
        return True

    def version_label_text(self) -> str:
        build = int(self.version_state.get("build", DEFAULT_BUILD))
        return f"v{VERSION_PREFIX}{build}.{now_date_str()}"

    def load_version_state(self):
        os.makedirs(USER_DIR, exist_ok=True)
        path = os.path.join(USER_DIR, VERSION_STATE_FILE)
        default = {"build": DEFAULT_BUILD}
        try:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(default, f, ensure_ascii=False, indent=2)
                return default
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("build", default["build"])
            return data
        except Exception:
            return default

    def save_version_state(self):
        try:
            with open(os.path.join(USER_DIR, VERSION_STATE_FILE), "w", encoding="utf-8") as f:
                json.dump(self.version_state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load_version_history(self):
        os.makedirs(USER_DIR, exist_ok=True)
        path = os.path.join(USER_DIR, VERSION_HISTORY_FILE)
        try:
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"entries": []}, f, ensure_ascii=False, indent=2)
                return {"entries": []}
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"entries": []}

    def save_version_history(self, history):
        try:
            with open(os.path.join(USER_DIR, VERSION_HISTORY_FILE), "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def bump_version(self, bullets):
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        self.version_state["build"] = int(self.version_state.get("build", DEFAULT_BUILD)) + 1
        self.save_version_state()
        history = self.load_version_history()
        history.setdefault("entries", [])
        history["entries"].insert(0, {"version": f"v{VERSION_PREFIX}{self.version_state['build']}", "date": now_date_str(), "bullets": bullets})
        self.save_version_history(history)
        try:
            self.version_label.config(text=self.version_label_text())
        except Exception:
            pass

    def bump_version_once(self, update_id, bullets):
        """
        Schreibt einen Versionsverlauf-Eintrag nur einmal.
        Damit wird die Version nicht bei jedem Programmstart erneut erhöht.
        """
        try:
            applied = self.version_state.setdefault("applied_updates", [])
            if update_id in applied:
                return
            self.bump_version(bullets)
            applied.append(update_id)
            self.version_state["applied_updates"] = applied
            self.save_version_state()
        except Exception:
            pass

    def load_user_data(self):
        default = {"last_username_prefill": "", "users": {}, "settings": {"auto_close_mail_enabled": True}}
        try:
            os.makedirs(USER_DIR, exist_ok=True)
            if not os.path.exists(USER_DATA_PATH):
                with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(default, f, ensure_ascii=False, indent=2)
                return default
            with open(USER_DATA_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("last_username_prefill", "")
            data.setdefault("users", {})
            data.setdefault("settings", {})
            data["settings"].setdefault("auto_close_mail_enabled", True)
            return data
        except Exception:
            return default

    def save_user_data(self):
        try:
            os.makedirs(USER_DIR, exist_ok=True)
            with open(USER_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("FiBu Mate", f"Benutzerdaten konnten nicht gespeichert werden:\n\n{e}")

    def ensure_permissions_defaults(self):
        users = self.user_data.setdefault("users", {})
        for key, u in users.items():
            u.setdefault("display_name", key)
            u.setdefault("favorites", [])
            u.setdefault("email", "")
            u.setdefault("auth", {"password_hash": None, "enabled": False})
            u["favorites"] = [fav for fav in u.get("favorites", []) if fav in TOOL_REGISTRY]
            u.setdefault("first_name", "")
            u.setdefault("full_name", " ".join(x for x in [u.get("first_name", "").strip(), u.get("display_name", key).strip()] if x).strip() or u.get("display_name", key))
            current_permission = ROLE_MIGRATION.get(u.get("permission"), u.get("permission", ROLE_E1))
            if key == SUPERUSER_KEY:
                u["permission"] = ROLE_E4
            else:
                if current_permission == ROLE_E4:
                    u["permission"] = ROLE_E1
                else:
                    u["permission"] = current_permission if current_permission in ROLE_ORDER else ROLE_E1

    def my_role(self):
        if not self.current_user_key:
            return ROLE_E1
        if self.current_user_key == SUPERUSER_KEY:
            return ROLE_E4
        return ROLE_MIGRATION.get(self.user_data.get("users", {}).get(self.current_user_key, {}).get("permission", ROLE_E1), ROLE_E1)

    def role_rank(self, role):
        return ROLE_RANK.get(ROLE_MIGRATION.get(role, role), ROLE_RANK[ROLE_E1])

    def can_view_user_management(self):
        return True

    def can_create_users(self):
        return self.my_role() in (ROLE_E3, ROLE_E4)

    def can_manage_permissions(self):
        return self.my_role() in (ROLE_E3, ROLE_E4)

    def auto_close_mail_enabled(self):
        return bool(self.user_data.setdefault("settings", {}).setdefault("auto_close_mail_enabled", True))

    def toggle_auto_close_mail(self):
        settings = self.user_data.setdefault("settings", {})
        settings["auto_close_mail_enabled"] = not bool(settings.get("auto_close_mail_enabled", True))
        self.save_user_data()
        self.render_page()

    def log_audit_event(self, event_type="Info", module="FiBu Mate", title="", details="", risk="Info", period="", related_id="", public=True):
        try:
            try:
                from bin.tools import compliance_common as cc
            except Exception:
                import compliance_common as cc
            return cc.log_audit(self, event_type, module, title, details, risk, period, related_id, public)
        except Exception:
            return None

    def current_close_period_label(self, module_id):
        now = datetime.now()
        if module_id == "monthly_close":
            names = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
            return f"{names[now.month - 1]} {now.year}"
        if module_id == "quarterly_close":
            q = (now.month - 1) // 3 + 1
            return f"Q{q} {now.year}"
        if module_id == "yearly_close":
            start_year = now.year if now.month >= 10 else now.year - 1
            return f"GJ {start_year}/{start_year + 1}"
        return ""

    def max_assignable_role_rank(self):
        return self.role_rank(self.my_role())

    def current_tile_color(self):
        if self.current_user_key:
            return self.user_data.get("users", {}).get(self.current_user_key, {}).get("tile_color")
        return None

    def create_footer(self):
        self.footer = tk.Frame(self.root, bg="black", height=40)
        self.footer.pack(side="bottom", fill="x")
        self.footer.pack_propagate(False)
        self.user_label = tk.Label(self.footer, bg="black", fg="white", font=FONT_SMALL)
        self.user_label.place(relx=0, rely=0.5, anchor="w", x=12)
        self.version_label = tk.Label(self.footer, text=self.version_label_text(), bg="black", fg="white", font=FONT_SMALL)
        self.version_label.place(relx=0.5, rely=0.5, anchor="center")
        self.clock_label = tk.Label(self.footer, bg="black", fg="white", font=FONT_SMALL)
        self.clock_label.place(relx=1, rely=0.5, anchor="e", x=-12)
        self.update_clock()

    def update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
        self.user_label.config(text=f"Benutzer {self.current_user_display}" if self.current_user_display else "")
        self.root.after(1000, self.update_clock)

    def show_page(self, page_name, title="", add_to_history=True):
        if add_to_history and self.current_page:
            self.page_history.append((self.current_page, self.current_title))
        self.current_page = page_name
        self.current_title = title
        self.update_breadcrumb(page_name, title)
        self.render_page()

    def update_breadcrumb(self, page_name, title):
        if page_name == "launch":
            self.breadcrumb = []
        elif page_name == "main":
            self.breadcrumb = [("main", "Hauptmenü")]
        else:
            if not self.breadcrumb:
                self.breadcrumb = [("main", "Hauptmenü")]
            existing = next((i for i, (p, _) in enumerate(self.breadcrumb) if p == page_name), None)
            self.breadcrumb = self.breadcrumb[: existing + 1] if existing is not None else self.breadcrumb + [(page_name, title)]

    def jump_to_breadcrumb(self, index):
        if 0 <= index < len(self.breadcrumb):
            self.current_page, self.current_title = self.breadcrumb[index]
            self.breadcrumb = self.breadcrumb[: index + 1]
            self.page_history = self.breadcrumb[:-1].copy()
            self.render_page()

    def go_back(self):
        if self.page_history:
            page, title = self.page_history.pop()
            self.current_page, self.current_title = page, title
            self.update_breadcrumb(page, title)
            self.render_page()

    def on_global_mousewheel(self, event):
        if self.active_scroll_canvas is None:
            return
        self.active_scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
        if hasattr(self, "_update_scroll_indicators"):
            self._update_scroll_indicators()

    def clear_content(self):
        self.active_scroll_canvas = None
        if hasattr(self, "module_escape_handler"):
            delattr(self, "module_escape_handler")
        if hasattr(self, "_update_scroll_indicators"):
            delattr(self, "_update_scroll_indicators")
        self.canvas.delete("all")
        for w in self.widget_items:
            try:
                w.destroy()
            except Exception:
                pass
        self.widget_items.clear()
        self.focusable_tiles.clear()
        self.focus_index = -1
        self.image_refs.clear()

    def render_page(self):
        self.clear_content()
        self.draw_background()
        if self.current_page == "launch":
            self.render_launch()
            return
        self.draw_header(self.current_title)
        self.draw_controls()
        self.draw_path_bar()
        self.draw_favorites_bar()
        if self.current_page == "main": self.render_main_menu()
        elif self.current_page == "data_prep": self.render_data_prep_menu()
        elif self.current_page == "closing_calendar": self.render_closing_calendar_menu()
        elif self.current_page == "compliance_audit": self.render_compliance_audit_menu()
        elif self.current_page == "in_dev": self.render_in_dev_menu()
        elif self.current_page == "settings": self.render_settings_menu()
        elif self.current_page == "tile_colors": self.render_tile_colors_menu()
        elif self.current_page == "users": self.render_users_menu()
        elif self.current_page == "permissions": self.render_permissions_menu()
        elif self.current_page == "information": self.render_information_menu()
        elif self.current_page == "versions": self.render_versions_menu()
        elif self.current_page.startswith("tool:"): self.render_external_tool(self.current_page.replace("tool:", "", 1))
        else: self.render_menu_text("Menü in Arbeit.")
        if self.focusable_tiles:
            self.focus_index = 0
            self.focusable_tiles[0].focus_set()

    def on_resize(self, *_):
        self.root.after(30, self.render_page)

    def draw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_rectangle(0, 0, w, h, fill=BG, outline="")
        # Dezentes dynamisches Hintergrunddesign: weiche Linien und Flächen in FiBu-Mate-/INTERSPORT-Farben
        for i in range(10):
            y = 145 + i * max(52, h * 0.060)
            color = blend(BG, BLUE if i % 2 == 0 else RED, 0.040 + (i % 4) * 0.008)
            self.canvas.create_line(-80, y, w + 90, y + h * 0.075, fill=color, width=1)
        self.canvas.create_oval(w * 0.68, h * 0.18, w * 1.05, h * 0.78, outline=blend(BG, BLUE, 0.11), width=2)
        self.canvas.create_oval(w * 0.73, h * 0.24, w * 1.01, h * 0.70, outline=blend(BG, WHITE, 0.46), width=1)
        self.canvas.create_oval(-w * 0.14, h * 0.42, w * 0.25, h * 1.02, outline=blend(BG, RED, 0.075), width=2)
        self.canvas.create_polygon(w * 0.02, h * 0.90, w * 0.32, h * 0.72, w * 0.60, h * 1.04, fill=blend(BG, WHITE, 0.20), outline="")
        self.canvas.create_polygon(w * 0.62, h * 0.20, w * 0.96, h * 0.36, w * 1.06, h * 0.12, fill=blend(BG, BLUE, 0.040), outline="")
        self.canvas.create_polygon(w * 0.08, h * 0.18, w * 0.22, h * 0.26, w * 0.04, h * 0.34, fill=blend(BG, WHITE, 0.15), outline="")
        self.canvas.create_rectangle(0, 0, w, 128, fill=HEADER, outline="")
        self.canvas.create_rectangle(0, 128, w, 131, fill=LINE, outline="")

    def draw_header(self, title):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.banner_small and PIL_AVAILABLE:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.banner_small, 520, 86))
            self.image_refs.append(ph)
            self.canvas.create_image(w / 2, h * 0.073, image=ph)
        else:
            self.canvas.create_text(w / 2, h * 0.083, text="FiBu Mate", font=FONT_TITLE, fill=TEXT)
        self.canvas.create_text(w / 2, h * 0.155, text=title, font=FONT_MENU, fill=TEXT2)

    def draw_gradient_line(self, x1, x2, y):
        width = max(1, int(x2 - x1)); steps = max(20, min(180, width // 5))
        for i in range(steps):
            t = i / max(1, steps - 1)
            color = blend(HEADER, RED, t / 0.14) if t < 0.14 else blend(BLUE, HEADER, (t - 0.86) / 0.14) if t > 0.86 else blend(RED, BLUE, (t - 0.14) / 0.72)
            self.canvas.create_line(x1 + width * i / steps, y, x1 + width * (i + 1) / steps, y, fill=color, width=2)

    def draw_path_bar(self):
        w = self.canvas.winfo_width(); x1, x2 = 6, min(650, w * 0.38)
        self.draw_gradient_line(x1, x2, 42); self.draw_gradient_line(x1, x2, 68)
        x = x1 + 112
        for idx, (page, title) in enumerate(self.breadcrumb):
            current = idx == len(self.breadcrumb) - 1
            tid = self.canvas.create_text(x, 55, text=title, font=("Segoe UI", 10, "bold") if current else ("Segoe UI", 10), fill=TEXT if current else BLUE, anchor="w")
            bbox = self.canvas.bbox(tid); tw = bbox[2] - bbox[0] if bbox else 70
            if not current:
                self.canvas.tag_bind(tid, "<Button-1>", lambda e, i=idx: self.jump_to_breadcrumb(i))
                self.canvas.tag_bind(tid, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
                self.canvas.tag_bind(tid, "<Leave>", lambda e: self.canvas.config(cursor="arrow"))
            x += tw + 18
            if idx < len(self.breadcrumb) - 1:
                self.canvas.create_polygon(x, 48, x, 62, x + 7, 55, fill=RED, outline=RED); x += 24

    def draw_favorites_bar(self):
        w = self.canvas.winfo_width(); x1, x2 = max(w * 0.68, w - 620), w - 8
        self.draw_gradient_line(x1, x2, 42); self.draw_gradient_line(x1, x2, 68)
        self.canvas.create_text(x1 + 18, 55, text="★", font=("Segoe UI", 16, "bold"), fill=GOLD, anchor="w")
        self.canvas.create_text(x1 + 48, 55, text="Favoriten", font=("Segoe UI", 10, "bold"), fill=TEXT, anchor="w")
        x = x1 + 135; chip_color = self.current_tile_color() or BLUE
        for fav in sorted(f for f in self.favorites if f in TOOL_REGISTRY):
            label = TOOL_REGISTRY.get(fav, {}).get("favorite_label", fav)
            chip = tk.Label(self.root, text=label, bg=chip_color, fg="white", font=("Segoe UI", 9), padx=8, pady=2, cursor="hand2")
            chip.bind("<Button-1>", lambda e, fid=fav: self.execute_favorite(fid))
            self.widget_items.append(chip); self.canvas.create_window(x, 55, window=chip, anchor="w"); x += 120

    def draw_controls(self):
        self.draw_logout_control() if self.current_page == "main" else self.draw_back_control()
        self.draw_suggestion_control()
        self.draw_help_control()
        self.draw_close_control()

    def draw_back_control(self):
        frame = tk.Frame(self.root, bg=HEADER, cursor="hand2")
        arrow = tk.Label(frame, text="←", fg=RED, bg=HEADER, font=("Segoe UI", 14, "bold"), cursor="hand2")
        txt = tk.Label(frame, text="zurück", fg=BLUE, bg=HEADER, font=("Segoe UI", 10, "underline"), cursor="hand2")
        arrow.pack(side="left"); txt.pack(side="left", padx=5)
        arrow.bind("<Button-1>", lambda e: self.go_back()); txt.bind("<Button-1>", lambda e: self.go_back())
        self.widget_items.append(frame); self.canvas.create_window(14, 7, window=frame, anchor="nw")

    def draw_logout_control(self):
        btn = tk.Button(self.root, text="Abmelden", command=self.logout, bg=self.current_tile_color() or BLUE, fg="white", bd=0, cursor="hand2")
        self.widget_items.append(btn); self.canvas.create_window(14, 7, window=btn, anchor="nw")

    def draw_mini_bulb_icon(self, canvas, x, y):
        if self.draw_canvas_icon(canvas, "idea", x, y, 18, 18):
            return
        canvas.create_oval(x - 6, y - 8, x + 6, y + 4, fill="#FFE45C", outline="#FACC15", width=1)
        canvas.create_rectangle(x - 4, y + 4, x + 4, y + 9, outline=BLUE, width=1)

    def draw_mini_help_icon(self, canvas, x, y):
        if self.draw_canvas_icon(canvas, "help", x, y, 19, 19):
            return
        canvas.create_rectangle(x - 17, y - 8, x + 17, y + 8, outline=BLUE, width=1)
        canvas.create_text(x, y, text="HELP", fill=BLUE, font=("Segoe UI", 7, "bold"))

    def draw_suggestion_control(self):
        if self.current_page == "launch":
            return
        btn = tk.Canvas(self.root, width=MINI_WIDGET_W, height=MINI_WIDGET_H, bg=HEADER, highlightthickness=0, bd=0, cursor="hand2")
        btn.create_rectangle(1, 1, MINI_WIDGET_W - 1, MINI_WIDGET_H - 1, fill=HEADER, outline=BLUE, width=1)
        self.draw_mini_bulb_icon(btn, 18, 14)
        btn.create_text((MINI_WIDGET_W / 2) + 10, MINI_WIDGET_H / 2, text="Änderung vorschlagen", fill=TEXT, font=("Segoe UI", 8, "bold"), anchor="center")
        btn.bind("<Button-1>", lambda _e: self.open_suggestion_mail())
        btn.bind("<Enter>", lambda _e: self.show_small_tooltip(btn, "Änderung vorschlagen"))
        btn.bind("<Leave>", lambda _e: self.hide_small_tooltip())
        self.widget_items.append(btn)
        x = self.canvas.winfo_width() - 52 - MINI_WIDGET_W - MINI_WIDGET_GAP
        self.canvas.create_window(x, 7, window=btn, anchor="ne")

    def show_small_tooltip(self, widget, text):
        self.hide_small_tooltip()
        try:
            self._small_tooltip = tk.Toplevel(widget)
            self._small_tooltip.wm_overrideredirect(True)
            self._small_tooltip.geometry(f"+{widget.winfo_rootx() - 90}+{widget.winfo_rooty() + 34}")
            tk.Label(self._small_tooltip, text=text, bg="#111827", fg="white", font=("Segoe UI", 9), padx=7, pady=4).pack()
        except Exception:
            self._small_tooltip = None

    def hide_small_tooltip(self):
        tip = getattr(self, "_small_tooltip", None)
        if tip:
            try:
                tip.destroy()
            except Exception:
                pass
        self._small_tooltip = None

    def open_suggestion_mail(self):
        messagebox.showinfo(
            "Änderung vorschlagen",
            "Vielen Dank für deinen Input! Bitte beschreibe in der folgenden Vorlage deinen Vorschlag so ausführlich wie möglich - Füge gerne Screenshots mit an",
        )
        user_name = self.current_user_display or self.current_user_key or ""
        subject = "Änderungsvorschlag Fibu Mate"
        body = (
            f"Änderungsvorschlag von {user_name},\n\n"
            "Folgenden Änderungsvorschlag würde ich gerne mitteilen / Folgende Anpassung wünsche ich mir:\n\n"
            "[Text des Vorschlagenden]"
        )
        mailto = (
            "mailto:matthias.wagner@intersport.de"
            "?cc=" + quote("matze.wagner1@yahoo.de")
            + "&subject=" + quote(subject)
            + "&body=" + quote(body)
        )
        try:
            webbrowser.open(mailto)
        except Exception as exc:
            messagebox.showerror("Änderung vorschlagen", f"Outlook konnte nicht geöffnet werden:\n\n{exc}")

    def draw_help_control(self):
        if self.current_page == "launch":
            return
        btn = tk.Canvas(self.root, width=MINI_WIDGET_W, height=MINI_WIDGET_H, bg=HEADER, highlightthickness=0, bd=0, cursor="hand2")
        btn.create_rectangle(1, 1, MINI_WIDGET_W - 1, MINI_WIDGET_H - 1, fill=HEADER, outline=BLUE, width=1)
        self.draw_mini_help_icon(btn, 25, MINI_WIDGET_H / 2)
        btn.create_text(MINI_WIDGET_W / 2, MINI_WIDGET_H / 2, text="Hilfe", fill=TEXT, font=("Segoe UI", 8, "bold"), anchor="center")
        def open_help(_event=None):
            self.show_help_popup()
        btn.bind("<Button-1>", open_help)
        btn.bind("<Enter>", lambda _e: self.show_small_tooltip(btn, "Hilfe"))
        btn.bind("<Leave>", lambda _e: self.hide_small_tooltip())
        self.widget_items.append(btn)
        self.canvas.create_window(self.canvas.winfo_width() - 52, 7, window=btn, anchor="ne")

    def draw_close_control(self):
        label = tk.Label(self.root, text="X", bg=HEADER, fg=RED, font=("Segoe UI", 10, "bold"), cursor="hand2", relief="solid", bd=1, padx=4)
        label.bind("<Button-1>", lambda e: self.confirm_exit()); self.widget_items.append(label)
        self.canvas.create_window(self.canvas.winfo_width() - 22, 7, window=label, anchor="ne")

    def show_help_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("FiBu Mate - Hilfe")
        popup.configure(bg=BG)
        popup.transient(self.root)
        popup.resizable(True, True)
        popup.minsize(780, 520)
        popup_w, popup_h = 1000, 700
        try:
            self.root.update_idletasks()
            screen_w = self.root.winfo_screenwidth()
            screen_h = self.root.winfo_screenheight()
            x = max(0, int((screen_w - popup_w) / 2))
            y = max(0, int((screen_h - popup_h) / 2))
            popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")
        except Exception:
            popup.geometry(f"{popup_w}x{popup_h}")
        popup.grab_set()
        header = tk.Frame(popup, bg=HEADER, height=64); header.pack(side="top", fill="x"); header.pack_propagate(False)
        tk.Label(header, text="Hilfe", bg=HEADER, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(side="left", padx=18)
        content = tk.Frame(popup, bg=BG); content.pack(side="top", fill="both", expand=True, padx=16, pady=16)
        if self.help_image and PIL_AVAILABLE:
            try:
                popup.update_idletasks(); img = resize_keep_ratio(self.help_image, max(600, popup.winfo_width() - 70), max(400, popup.winfo_height() - 150)); ph = ImageTk.PhotoImage(img)
                label = tk.Label(content, image=ph, bg=BG); label.image = ph; label.pack(expand=True)
            except Exception as error:
                tk.Label(content, text=f"Das Hilfe-Bild konnte nicht geladen werden:\n\n{error}", bg=BG, fg=TEXT, font=("Segoe UI", 11), justify="left").pack(anchor="nw")
        else:
            tk.Label(content, text=("Das Hilfe-Menü ist vorbereitet, aber das Hilfe-Bild konnte nicht geladen werden.\n\n" f"Erwarteter Pfad:\n{HELP_IMAGE_PATH}"), bg=BG, fg=TEXT, font=("Segoe UI", 11), justify="left").pack(anchor="nw")
        footer = tk.Frame(popup, bg=BG); footer.pack(side="bottom", fill="x", padx=16, pady=(0, 16))
        tk.Button(footer, text="Schließen", command=popup.destroy, bg=BLUE, fg="white", bd=0, padx=18, pady=8, cursor="hand2").pack(side="right")

    def draw_bottom_logo(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.intersport_logo and PIL_AVAILABLE:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.intersport_logo, 420, 55)); self.image_refs.append(ph); self.canvas.create_image(w / 2, h - 24, image=ph)
        else:
            self.canvas.create_text(w / 2, h - 24, text="INTERSPORT", font=("Segoe UI", 22, "bold"), fill=BLUE)

    def draw_intersport_logo_above_footer(self, show_mini_logo=True): return self.draw_bottom_logo()

    def toggle_favorite(self, tool_id):
        if tool_id not in TOOL_REGISTRY: return
        self.favorites.remove(tool_id) if tool_id in self.favorites else self.favorites.add(tool_id)
        if self.current_user_key:
            self.user_data["users"][self.current_user_key]["favorites"] = sorted(self.favorites); self.save_user_data()
        self.render_page()

    def execute_favorite(self, tool_id):
        if tool_id in TOOL_REGISTRY: self.open_tool(tool_id)

    def render_launch(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.banner_big and PIL_AVAILABLE:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.banner_big, 900, 230)); self.image_refs.append(ph); self.canvas.create_image(w / 2, h * 0.235, image=ph)
        else:
            self.canvas.create_text(w / 2, h * 0.235, text="FiBu Mate", font=("Segoe UI", 46, "bold"), fill=TEXT)
        panel = tk.Frame(self.root, bg=BG); username_var = tk.StringVar(value="")
        tk.Label(panel, text="Benutzername", bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(panel, bg=BG); row.pack(fill="x", pady=(0, 18))
        entry = tk.Entry(row, textvariable=username_var, font=("Segoe UI", 13), width=37, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1); entry.pack(side="left", ipady=4)
        btn = tk.Button(row, text="Anmelden", command=lambda: self.login_user(username_var.get()), bg=BLUE, fg="white", bd=0, cursor="hand2"); btn.pack(side="left", padx=(12, 0), ipady=6)
        self.widget_items.append(panel); self.canvas.create_window(x_pct(w, 50), y_pct(h, 39), window=panel, anchor="center")
        entry.focus_set(); entry.bind("<Return>", lambda e: self.login_user_from_entry(username_var.get()))
        self.draw_bottom_logo(); self.draw_close_control()

    def render_main_menu(self):
        top_tiles = [
            {"title": "Abschlusskalender", "cmd": lambda: self.show_page("closing_calendar", "Abschlusskalender", True), "fixed": None, "lock": False, "icon": "calendar", "fold": False},
            {"title": "Compliance & Audit", "cmd": lambda: self.show_page("compliance_audit", "Compliance & Audit", True), "fixed": None, "lock": False, "icon": "compliance", "fold": False},
        ]
        middle_tiles = [
            {"title": "Datenaufbereitung", "cmd": lambda: self.show_page("data_prep", "Datenaufbereitung", True), "fixed": None, "lock": False, "icon": "pdf_xls", "fold": False},
        ]
        footer_tiles = [
            {"title": "In Entwicklung", "cmd": self.try_open_in_dev, "fixed": GREY_TILE, "lock": True, "icon": "lock", "fold": False},
            {"title": "Informationen", "cmd": lambda: self.show_page("information", "Informationen", True), "fixed": None, "lock": False, "icon": "info", "fold": True},
            {"title": "Einstellungen", "cmd": lambda: self.show_page("settings", "Einstellungen", True), "fixed": None, "lock": False, "icon": "gear", "fold": True},
        ]
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        tw = max(240, min(330, int(w * 0.165)))
        th = max(125, min(170, int(h * 0.155)))
        gap_x = max(38, int(w * 0.04))
        def centered_x_positions(count, tile_w=tw, gap=gap_x):
            if count <= 0:
                return []
            total_width = count * tile_w + (count - 1) * gap
            start_x = (w - total_width) / 2 + tile_w / 2
            return [start_x + i * (tile_w + gap) for i in range(count)]
        def create_tile_group(items, y, id_prefix, tile_w=tw, tile_h=th):
            xs = centered_x_positions(len(items), tile_w)
            for i, item in enumerate(items):
                tile = Tile(self.root, self, f"{id_prefix}_{i}", item["title"], item["cmd"], favorite_enabled=False, fixed_color=item["fixed"], lock_tile=item["lock"], icon_type=item["icon"], corner_fold=item["fold"])
                tile.resize_tile(tile_w, tile_h)
                self.widget_items.append(tile)
                self.focusable_tiles.append(tile)
                self.canvas.create_window(xs[i], y, window=tile, anchor="center")
        create_tile_group(top_tiles, y_pct(h, 63), "main_top")
        create_tile_group(middle_tiles, y_pct(h, 43), "main_middle")
        footer_tw = int(tw * 0.85)
        footer_th = int(th * 0.85)
        footer_center_y = y_pct(h, 17.5) + th / 2 - footer_th / 2
        footer_top = footer_center_y - footer_th / 2
        create_tile_group(footer_tiles, footer_center_y, "main_footer", tile_w=footer_tw, tile_h=footer_th)
        self.draw_continuous_relief_line(self.canvas, footer_top - 13, x_pct(w, 9.5), x_pct(w, 92))
        self.draw_bottom_logo()

    def try_open_in_dev(self):
        if self.my_role() != ROLE_E4: return
        self.show_page("in_dev", "In Entwicklung", True)

    def render_data_prep_menu(self):
        modules = [("Nike - PDF zu Excel", "nike_pdf_to_excel"), ("Nike - OP-Liste: Vollständigkeit PDF-Rechnungen prüfen", "nike_op_liste_pdf_check")]
        self.render_module_menu(modules, show_descriptions=True); self.draw_bottom_logo()

    def render_closing_calendar_menu(self):
        modules = [("Monatsabschluss", "monthly_close"), ("Quartalsabschluss", "quarterly_close"), ("Jahresabschluss", "yearly_close"), ("Aufgaben-Historie nach ID", "task_history")]
        self.render_module_menu(modules, show_descriptions=True)
        if self.my_role() == ROLE_E4:
            text = "Auto-Mail: Ein" if self.auto_close_mail_enabled() else "Auto-Mail: Aus"
            btn = tk.Button(self.root, text=text, command=self.toggle_auto_close_mail, bg=BLUE if self.auto_close_mail_enabled() else GREY_DISABLED, fg="white", bd=0, padx=10, pady=3, cursor="hand2", font=("Segoe UI", 9, "bold"))
            self.widget_items.append(btn)
            self.canvas.create_window(self.canvas.winfo_width() / 2, 136, window=btn, anchor="n")
        self.draw_bottom_logo()

    def render_compliance_audit_menu(self):
        modules = [
            ("Steuermeldungs-Cockpit", "tax_reporting"),
            ("Audit-Cockpit", "audit_cockpit"),
            ("Dokumentationszentrale", "documentation_center"),
        ]
        self.render_module_menu(modules, show_descriptions=True)
        self.draw_bottom_logo()

    def render_in_dev_menu(self):
        self.render_module_menu([("X001 SAP - Test", "x001_sap_test")], show_descriptions=True); self.draw_bottom_logo()


    def render_settings_menu(self):
        items = [("Farbschema", "tile_colors")]
        if self.can_view_user_management():
            items.append(("Benutzerverwaltung", "users"))
        if self.can_manage_permissions():
            items.append(("Berechtigungen", "permissions"))
        self.render_center_menu(items, title="Einstellungen"); self.draw_bottom_logo()

    def render_information_menu(self):
        self.render_center_menu([("Versionsverlauf", "versions")], title="Informationen"); self.draw_bottom_logo()

    def render_center_menu(self, items, title=""):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); tile_w = int(max(260, min(360, w * 0.2))); tile_h = int(max(110, min(160, h * 0.14))); gap = int(max(18, h * 0.03)); start_y = y_pct(h, 55); start_x = x_pct(w, 50)
        for i, (label, page) in enumerate(items):
            y = start_y + i * (tile_h + gap); cmd = (lambda p=page, l=label: self.show_page(p, l, True))
            tile = Tile(self.root, self, f"center_{page}", label, cmd, favorite_enabled=False, center_text=True); tile.resize_tile(tile_w, tile_h); self.widget_items.append(tile); self.focusable_tiles.append(tile); self.canvas.create_window(start_x, y, window=tile, anchor="center")

    def render_tile_colors_menu(self):
        frame = tk.Frame(self.root, bg=BG); self.widget_items.append(frame)
        tk.Label(frame, text="Standardfarben", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=5, pady=(0, 14), sticky="w")
        selected_color = self.current_tile_color() or BLUE
        def set_color(col):
            if self.current_user_key:
                self.user_data["users"][self.current_user_key]["tile_color"] = col; self.save_user_data()
            self.render_page()
        for idx, (name, color) in enumerate(COLOR_PALETTE):
            r = 1 + idx // 5; c = idx % 5; sw = tk.Canvas(frame, width=140, height=78, bg=BG, highlightthickness=0, bd=0, cursor="hand2")
            if color == selected_color:
                sw.create_rectangle(4, 4, 136, 58, outline=WHITE, width=4)
            sw.create_rectangle(8, 8, 132, 54, fill=color, outline=LINE, width=2); sw.create_text(70, 66, text=name, fill=TEXT, font=("Segoe UI", 9, "bold")); sw.bind("<Button-1>", lambda e, col=color: set_color(col)); sw.grid(row=r, column=c, padx=10, pady=10)
        def reset():
            if self.current_user_key:
                self.user_data["users"][self.current_user_key].pop("tile_color", None); self.save_user_data()
            self.render_page()
        tk.Button(frame, text="Standard wiederherstellen", command=reset, bg=selected_color, fg="white", bd=0, padx=16, pady=10, cursor="hand2").grid(row=r + 1, column=0, columnspan=5, pady=(18, 6))
        self.canvas.create_window(self.canvas.winfo_width() / 2, y_pct(self.canvas.winfo_height(), 48), window=frame, anchor="center")


    def render_users_menu(self):
        if not self.can_view_user_management():
            self.render_menu_text("Keine Berechtigung für die Benutzerverwaltung."); return
        users = self.user_data.setdefault("users", {})
        visible_keys = [self.current_user_key] if self.my_role() == ROLE_E1 and self.current_user_key in users else sorted(users.keys())
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); area_top = 132; area_bottom = max(area_top + 260, h - 92); view_h = int(area_bottom - area_top)
        container = tk.Frame(self.root, bg=BG); self.widget_items.append(container); self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)
        arrow_col = tk.Frame(container, bg=BG, width=54); arrow_col.pack(side="left", fill="y", padx=(18, 0)); arrow_col.pack_propagate(False)
        body = tk.Frame(container, bg=BG); body.pack(side="left", fill="both", expand=True)
        footer = tk.Frame(body, bg=BG); footer.pack(side="bottom", fill="x", pady=(8, 0))
        scroll_canvas = tk.Canvas(body, bg=BG, highlightthickness=0, bd=0); scrollbar = tk.Scrollbar(body, orient="vertical", command=scroll_canvas.yview)
        content = tk.Frame(scroll_canvas, bg=BG); content_window = scroll_canvas.create_window((0, 0), window=content, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set); scroll_canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y"); self.active_scroll_canvas = scroll_canvas
        def update_arrows():
            try:
                first, last = scroll_canvas.yview(); up_arrow.set_enabled(first > 0.001); down_arrow.set_enabled(last < 0.999)
            except Exception: pass
        def scroll_units(n): scroll_canvas.yview_scroll(n, "units"); update_arrows()
        up_arrow = ArrowIndicator(arrow_col, "up", lambda: scroll_units(-5), size=42); down_arrow = ArrowIndicator(arrow_col, "down", lambda: scroll_units(5), size=42)
        up_arrow.pack(side="top", pady=(78, 10)); down_arrow.pack(side="top", pady=(0, 10))
        def update_scrollregion(_event=None):
            scroll_canvas.itemconfigure(content_window, width=max(1, scroll_canvas.winfo_width())); scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")); update_arrows()
        self._update_scroll_indicators = update_arrows; content.bind("<Configure>", update_scrollregion); scroll_canvas.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<MouseWheel>", lambda e: (scroll_units(int(-e.delta / 120)), "break")[-1])
        frame = content
        tk.Label(frame, text="Benutzerverwaltung", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=8, sticky="w", pady=(0, 14))
        for col, header in enumerate(["Benutzer", "Anzeigename/Nachname", "Vorname", "E-Mail", "Rolle", "Passwort"]):
            tk.Label(frame, text=header, bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=col, sticky="w", padx=(0, 14))
        def can_edit_user(target_key):
            if target_key == self.current_user_key: return True
            if target_key == SUPERUSER_KEY: return False
            target_role = users.get(target_key, {}).get("permission", ROLE_E1)
            return self.my_role() in (ROLE_E3, ROLE_E4) or self.role_rank(target_role) < self.role_rank(self.my_role())
        def save_user_row(old_key, name_var, email_var, first_name_var=None):
            if old_key not in users: return
            data = users[old_key]; data["email"] = email_var.get().strip(); data["first_name"] = first_name_var.get().strip() if first_name_var else data.get("first_name", ""); data["full_name"] = " ".join(x for x in [data.get("first_name", "").strip(), data.get("display_name", old_key).strip()] if x).strip() or data.get("display_name", old_key)
            may_rename = self.my_role() in (ROLE_E3, ROLE_E4) and old_key not in (self.current_user_key, SUPERUSER_KEY) and can_edit_user(old_key)
            if may_rename:
                new_name = " ".join(name_var.get().strip().split()); new_key = normalize_username(new_name)
                if not new_key: messagebox.showwarning("FiBu Mate", "Bitte einen Benutzernamen eingeben."); return
                if new_key == SUPERUSER_KEY: messagebox.showwarning("FiBu Mate", "Der Benutzer Wagnerm kann nicht umbenannt werden."); return
                if new_key != old_key and new_key in users: messagebox.showwarning("FiBu Mate", "Dieser Benutzername existiert bereits."); return
                data = users.pop(old_key); data["display_name"] = new_name; data["full_name"] = " ".join(x for x in [data.get("first_name", "").strip(), new_name] if x).strip() or new_name; users[new_key] = data
            self.save_user_data(); messagebox.showinfo("FiBu Mate", "Benutzerdaten wurden gespeichert."); self.render_page()
        def delete_user(user_key):
            if user_key in (SUPERUSER_KEY, self.current_user_key): messagebox.showwarning("FiBu Mate", "Dieser Benutzer kann nicht gelöscht werden."); return
            if not can_edit_user(user_key): messagebox.showwarning("FiBu Mate", "Keine Berechtigung für diesen Benutzer."); return
            if not messagebox.askyesno("Benutzer löschen", f"Benutzer wirklich löschen?\n\n{users.get(user_key, {}).get('display_name', user_key)}"): return
            users.pop(user_key, None); self.save_user_data(); messagebox.showinfo("FiBu Mate", "Benutzer wurde gelöscht."); self.render_page()
        row = 2
        for key in visible_keys:
            user = users[key]; user.setdefault("email", "")
            tk.Label(frame, text=key, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=4)
            name_var = tk.StringVar(value=user.get("display_name", key)); first_name_var = tk.StringVar(value=user.get("first_name", "")); email_var = tk.StringVar(value=user.get("email", ""))
            name_state = "normal" if self.my_role() in (ROLE_E3, ROLE_E4) and key not in (self.current_user_key, SUPERUSER_KEY) else "disabled"
            tk.Entry(frame, textvariable=name_var, font=("Segoe UI", 10), width=22, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1, state=name_state).grid(row=row, column=1, sticky="w", padx=(0, 14), pady=4)
            tk.Entry(frame, textvariable=first_name_var, font=("Segoe UI", 10), width=18, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=row, column=2, sticky="w", padx=(0, 14), pady=4)
            tk.Entry(frame, textvariable=email_var, font=("Segoe UI", 10), width=32, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=row, column=3, sticky="w", padx=(0, 14), pady=4)
            tk.Label(frame, text=user.get("permission", ROLE_E1), bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=4, sticky="w", padx=(0, 14), pady=4)
            tk.Label(frame, text="aktiv" if user.get("auth", {}).get("enabled") else "nicht aktiv", bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=5, sticky="w", padx=(0, 14), pady=4)
            editable = can_edit_user(key)
            tk.Button(frame, text="Speichern", command=lambda k=key, n=name_var, e=email_var, f=first_name_var: save_user_row(k, n, e, f), bg=BLUE if editable else GREY_DISABLED, fg="white", bd=0, width=9, padx=10, pady=5, cursor="hand2" if editable else "arrow", state="normal" if editable else "disabled").grid(row=row, column=6, sticky="w", padx=(18, 10), pady=4)
            del_ok = editable and key not in (self.current_user_key, SUPERUSER_KEY) and self.my_role() in (ROLE_E3, ROLE_E4)
            tk.Button(frame, text="Löschen", command=lambda k=key: delete_user(k), bg=RED if del_ok else GREY_DISABLED, fg="white", bd=0, width=9, padx=10, pady=5, cursor="hand2" if del_ok else "arrow", state="normal" if del_ok else "disabled").grid(row=row, column=7, sticky="w", padx=(0, 8), pady=4)
            row += 1
        if self.can_create_users():
            tk.Label(footer, text="Neuen Benutzer anlegen", font=("Segoe UI", 12, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 8))
            username_var = tk.StringVar(); first_name_new_var = tk.StringVar(); email_new_var = tk.StringVar()
            tk.Label(footer, text="Benutzername", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", padx=(0, 8))
            tk.Entry(footer, textvariable=username_var, font=("Segoe UI", 10), width=28, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=1, column=1, sticky="w", padx=(0, 14))
            tk.Label(footer, text="Vorname", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=2, sticky="e", padx=(0, 4))
            tk.Entry(footer, textvariable=first_name_new_var, font=("Segoe UI", 10), width=18, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=1, column=3, sticky="w", padx=(0, 14))
            tk.Label(footer, text="E-Mail", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=4, sticky="e", padx=(0, 4))
            tk.Entry(footer, textvariable=email_new_var, font=("Segoe UI", 10), width=32, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=1, column=5, sticky="w", padx=(0, 14))
            def create_user():
                raw_name = " ".join(username_var.get().strip().split()); key = normalize_username(raw_name)
                if not key: messagebox.showwarning("FiBu Mate", "Bitte einen Benutzernamen eingeben."); return
                if key in users: messagebox.showwarning("FiBu Mate", "Dieser Benutzer existiert bereits."); return
                users[key] = {"display_name": raw_name, "first_name": first_name_new_var.get().strip(), "full_name": " ".join(x for x in [first_name_new_var.get().strip(), raw_name] if x).strip() or raw_name, "email": email_new_var.get().strip(), "favorites": [], "auth": {"password_hash": None, "enabled": False}, "permission": ROLE_E4 if key == SUPERUSER_KEY else ROLE_E1}
                self.ensure_permissions_defaults(); self.save_user_data(); messagebox.showinfo("FiBu Mate", f"Benutzer wurde angelegt:\n\n{raw_name}"); self.render_page()
            tk.Button(footer, text="Benutzer anlegen", command=create_user, bg=BLUE, fg="white", bd=0, padx=14, pady=8, cursor="hand2").grid(row=1, column=6, sticky="w")
        update_scrollregion()


    def render_permissions_menu(self):
        if not self.can_manage_permissions():
            self.render_menu_text("Keine Berechtigung für das Menü Berechtigungen."); return
        users = self.user_data.setdefault("users", {})
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); area_top = 132; area_bottom = max(area_top + 260, h - 92); view_h = int(area_bottom - area_top)
        container = tk.Frame(self.root, bg=BG); self.widget_items.append(container); self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)
        arrow_col = tk.Frame(container, bg=BG, width=54); arrow_col.pack(side="left", fill="y", padx=(18, 0)); arrow_col.pack_propagate(False)
        body = tk.Frame(container, bg=BG); body.pack(side="left", fill="both", expand=True)
        scroll_canvas = tk.Canvas(body, bg=BG, highlightthickness=0, bd=0); scrollbar = tk.Scrollbar(body, orient="vertical", command=scroll_canvas.yview)
        content = tk.Frame(scroll_canvas, bg=BG); content_window = scroll_canvas.create_window((0,0), window=content, anchor="nw")
        scroll_canvas.configure(yscrollcommand=scrollbar.set); scroll_canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y"); self.active_scroll_canvas = scroll_canvas
        def update_arrows():
            try:
                first, last = scroll_canvas.yview(); up_arrow.set_enabled(first > 0.001); down_arrow.set_enabled(last < 0.999)
            except Exception: pass
        def scroll_units(n): scroll_canvas.yview_scroll(n, "units"); update_arrows()
        up_arrow = ArrowIndicator(arrow_col, "up", lambda: scroll_units(-5), size=42); down_arrow = ArrowIndicator(arrow_col, "down", lambda: scroll_units(5), size=42)
        up_arrow.pack(side="top", pady=(78, 10)); down_arrow.pack(side="top", pady=(0, 10))
        def update_scrollregion(_event=None):
            scroll_canvas.itemconfigure(content_window, width=max(1, scroll_canvas.winfo_width())); scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")); update_arrows()
        self._update_scroll_indicators = update_arrows; content.bind("<Configure>", update_scrollregion); scroll_canvas.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<MouseWheel>", lambda e: (scroll_units(int(-e.delta / 120)), "break")[-1])
        frame = content
        tk.Label(frame, text="Berechtigungen", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))
        def show_role_info():
            popup = tk.Toplevel(self.root); popup.title("Berechtigungen der Rollen anzeigen"); popup.configure(bg=BG); popup.geometry("820x620"); popup.transient(self.root)
            text = tk.Text(popup, bg="white", fg=TEXT, wrap="word", font=("Segoe UI", 10)); text.pack(fill="both", expand=True, padx=14, pady=14)
            content = "E1 - Standard\n- eigene Benutzerdaten ansehen/pflegen\n- Abschlusskalender lesen\n- eigene zuständige Aufgaben erledigen\n- Berichte, Historie und Änderungsprotokolle ansehen\n\nE2 - Erweitert\n- aktuell gleiche Berechtigungen wie E1\n- Platzhalter für spätere Erweiterungen\n\nE3 - Administrator\n- Benutzer anlegen, bearbeiten und löschen\n- Berechtigungen maximal bis E3 vergeben\n- Aufgaben administrieren und Aufgaben-IDs bearbeiten/verknüpfen\n- Zeiträume nach Stichtag schließen/öffnen\n- Berichte und Änderungsprotokolle ansehen\n\nE4 - System-Administrator\n- Berechtigungen analog E3\n- System-Administrator"
            text.insert("1.0", content); text.config(state="disabled")
        tk.Button(frame, text="Berechtigungen der Rollen anzeigen", command=show_role_info, bg=HEADER, fg=TEXT, bd=1, padx=10, pady=5, cursor="hand2").grid(row=0, column=5, sticky="e", pady=(0,10))
        tk.Label(frame, text="Berechtigungen können von berechtigten Rollen maximal bis zur eigenen Rolle vergeben werden.", bg=BG, fg=TEXT2, font=("Segoe UI", 10), justify="left").grid(row=1, column=0, columnspan=5, sticky="w", pady=(0, 16))
        for col, header in enumerate(["Benutzer", "Anzeigename", "Aktuelle Rolle", "Ändern"]): tk.Label(frame, text=header, bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=col, sticky="w", padx=(0, 24))
        row = 3
        for key in sorted(users.keys()):
            user = users[key]; current_role = user.get("permission", ROLE_E1)
            tk.Label(frame, text=key, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=(0, 24), pady=5)
            tk.Label(frame, text=user.get("display_name", key), bg=BG, fg=TEXT2, font=("Segoe UI", 10), wraplength=260, justify="left").grid(row=row, column=1, sticky="w", padx=(0, 24), pady=5)
            tk.Label(frame, text=current_role, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=2, sticky="w", padx=(0, 24), pady=5)
            if self.my_role() == ROLE_E3 and (key == SUPERUSER_KEY or current_role == ROLE_E4):
                tk.Label(frame, text="gesperrt", bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=3, sticky="w", pady=5); row += 1; continue
            available_roles = [role for role in ROLE_ORDER if self.role_rank(role) <= self.max_assignable_role_rank()]
            if key != SUPERUSER_KEY and ROLE_E4 in available_roles: available_roles.remove(ROLE_E4)
            if key == SUPERUSER_KEY: available_roles = [ROLE_E4]
            role_var = tk.StringVar(value=current_role if current_role in available_roles else available_roles[0])
            dropdown = tk.OptionMenu(frame, role_var, *available_roles); dropdown.config(bg="#E8EEF5", fg=TEXT, bd=1, highlightthickness=0, cursor="hand2"); dropdown.grid(row=row, column=3, sticky="w", pady=5)
            def save_role(user_key=key, var=role_var):
                new_role = var.get()
                if user_key == SUPERUSER_KEY: new_role = ROLE_E4
                if user_key != SUPERUSER_KEY and new_role == ROLE_E4: messagebox.showwarning("FiBu Mate", "Die Rolle System-Administrator darf nur der Benutzer Wagnerm tragen."); return
                if self.role_rank(new_role) > self.max_assignable_role_rank(): messagebox.showwarning("FiBu Mate", "Du kannst keine Rolle vergeben, die höher als deine eigene Rolle ist."); return
                users[user_key]["permission"] = new_role; self.ensure_permissions_defaults(); self.save_user_data(); messagebox.showinfo("FiBu Mate", "Berechtigung wurde gespeichert."); self.render_page()
            tk.Button(frame, text="Speichern", command=save_role, bg=BLUE, fg="white", bd=0, padx=10, pady=5, cursor="hand2").grid(row=row, column=4, sticky="w", padx=(8, 0), pady=5)
            row += 1
        update_scrollregion()

    def render_versions_menu(self):
        history = self.load_version_history().get("entries", [])
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        area_top = 132
        area_bottom = max(area_top + 260, h - 92)
        view_h = int(area_bottom - area_top)

        container = tk.Frame(self.root, bg=BG)
        self.widget_items.append(container)
        self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)

        scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=scroll_canvas.yview)
        content = tk.Frame(scroll_canvas, bg=BG)
        content_window = scroll_canvas.create_window((0, 0), window=content, anchor="nw")

        def update_scrollregion(_event=None):
            scroll_canvas.itemconfigure(content_window, width=max(1, scroll_canvas.winfo_width()))
            scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all"))

        content.bind("<Configure>", update_scrollregion)
        scroll_canvas.bind("<Configure>", update_scrollregion)
        scroll_canvas.configure(yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.active_scroll_canvas = scroll_canvas

        def _on_versions_mousewheel(event):
            scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        scroll_canvas.bind("<MouseWheel>", _on_versions_mousewheel)
        content.bind("<MouseWheel>", _on_versions_mousewheel)

        if not history:
            tk.Label(content, text="Noch kein Versionsverlauf vorhanden.", bg=BG, fg=TEXT2, font=("Segoe UI", 12)).pack(anchor="w", padx=24, pady=24)
            update_scrollregion()
            return

        for entry in history:
            entry_frame = tk.Frame(content, bg=BG)
            entry_frame.pack(fill="x", padx=24, pady=(16, 0), anchor="n")
            ver = entry.get("version", "")
            date = entry.get("date", "")
            bullets = entry.get("bullets", [])
            tk.Label(entry_frame, text=f"{ver}.{date}", bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", anchor="w")
            for bullet in bullets:
                tk.Label(entry_frame, text=f"• {bullet}", bg=BG, fg=TEXT2, font=("Segoe UI", 11), justify="left", anchor="w", wraplength=max(300, w - 110)).pack(fill="x", anchor="w", padx=(16, 0), pady=(2, 0))
            separator = tk.Canvas(content, bg=BG, height=18, highlightthickness=0, bd=0)
            separator.pack(fill="x", padx=10, pady=(8, 0))
            try:
                self.draw_relief_line(separator, 8, 0, max(100, w - 70))
            except Exception:
                separator.create_line(0, 8, max(100, w - 70), 8, fill=LINE, width=1)
        update_scrollregion()

    def render_menu_text(self, text):
        lab = tk.Label(self.root, text=text, font=("Segoe UI", 16), bg=BG, fg=TEXT); self.widget_items.append(lab); self.canvas.create_window(x_pct(self.canvas.winfo_width(), 50), y_pct(self.canvas.winfo_height(), 60), window=lab, anchor="center"); self.draw_bottom_logo()

    def draw_continuous_relief_line(self, canvas, y, x1, x2):
        canvas.create_line(x1, y, x2, y, fill=blend(BG, "#1F2933", 0.30), width=2)
        canvas.create_line(x1, y + 2, x2, y + 2, fill=blend(BG, WHITE, 0.65), width=1)

    def draw_relief_line(self, canvas, y, x1, x2):
        for i in range(120):
            t = i / 119; fade = 1 - abs(t - 0.5) * 2; sx = x1 + (x2 - x1) * i / 120; ex = x1 + (x2 - x1) * (i + 1) / 120
            canvas.create_line(sx, y, ex, y, fill=blend(BG, "#1F2933", 0.30 * fade), width=2); canvas.create_line(sx, y + 2, ex, y + 2, fill=blend(BG, WHITE, 0.65 * fade), width=1)

    def draw_module_description(self, canvas, module_id, x1, y_top, width):
        txt = MODULE_DESCRIPTIONS.get(module_id, "")
        if txt: canvas.create_text(x1 + DESCRIPTION_X_OFFSET, y_top + DESCRIPTION_Y_OFFSET, text=txt, anchor="nw", fill=DESCRIPTION_COLOR, font=DESCRIPTION_FONT, width=max(120, int(width) - 2 * DESCRIPTION_X_OFFSET), justify="left")

    def module_icon_type(self, module_id):
        if module_id == "tax_reporting":
            return "tax_reporting"
        if module_id == "audit_cockpit":
            return "audit"
        if module_id == "documentation_center":
            return "documentation"
        if self.current_page == "data_prep":
            return "pdf_xls"
        if self.current_page == "compliance_audit":
            return "compliance"
        if self.current_page == "closing_calendar":
            return "calendar"
        if module_id in ("monthly_close", "quarterly_close", "yearly_close", "task_history"):
            return "calendar"
        if module_id.startswith("nike_"):
            return "worksheet"
        return "modules"

    def render_module_menu(self, modules, show_descriptions=True):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); tile_w = max(290, min(390, int(w * 0.22))); tile_h = max(120, min(160, int(h * 0.15))); gap = max(18, int(h * 0.025)); area_top = 132; area_bottom = max(area_top + 260, h - 92); view_h = int(area_bottom - area_top); first_center_x = x_pct(w, 25); first_center_y = y_pct(h, 70); left_x = max(0, first_center_x - tile_w / 2 - 8); top = max(0, first_center_y - tile_h / 2 - area_top - 8)
        container = tk.Frame(self.root, bg=BG); self.widget_items.append(container); self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h); canvas_w = w - left_x - 10; scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0); scroll_canvas.place(x=left_x, y=0, width=canvas_w, height=view_h); content_h = top + len(modules) * (tile_h + gap) + 20; scroll_canvas.configure(scrollregion=(0, 0, canvas_w, content_h)); desc_x1 = tile_w + 90; desc_x2 = canvas_w - 20
        for idx, (title, module_id) in enumerate(modules):
            y = top + idx * (tile_h + gap); cmd = (lambda mid=module_id: self.open_tool(mid)) if module_id in TOOL_REGISTRY else self.show_placeholder
            tile = Tile(scroll_canvas, self, module_id, title, cmd, favorite_enabled=module_id in TOOL_REGISTRY, icon_type=self.module_icon_type(module_id)); tile.resize_tile(tile_w, tile_h); self.focusable_tiles.append(tile); scroll_canvas.create_window(0, y, window=tile, anchor="nw")
            if show_descriptions: self.draw_module_description(scroll_canvas, module_id, desc_x1, y, desc_x2 - desc_x1)
            if idx < len(modules) - 1: self.draw_relief_line(scroll_canvas, y + tile_h + gap / 2, desc_x1, desc_x2)

    def render_external_tool(self, tool_id):
        try:
            module = importlib.import_module(TOOL_REGISTRY[tool_id]["module"]); importlib.reload(module)
            if not hasattr(module, "render"): raise RuntimeError("Modul hat keine render(app)-Funktion")
            module.render(self)
        except Exception as e:
            messagebox.showerror("FiBu Mate", f"Fehler beim Laden des Moduls:\n\n{TOOL_REGISTRY.get(tool_id, {}).get('title', tool_id)}\n\n{e}"); self.draw_bottom_logo()

    def open_tool(self, tool_id):
        if tool_id in TOOL_REGISTRY: self.show_page(f"tool:{tool_id}", TOOL_REGISTRY[tool_id]["title"], True)

    def show_placeholder(self): messagebox.showinfo("FiBu Mate", "Hinter diesem Widget entsteht gerade ein Modul.")

    def login_user_from_entry(self, username):
        self._suppress_next_global_return = True
        self.login_user(username)
        return "break"

    def login_user(self, username):
        username = " ".join(str(username).strip().split())
        key = normalize_username(username)
        if not key:
            messagebox.showwarning("FiBu Mate", "Bitte einen Nutzernamen eingeben.")
            return
        users = self.user_data.setdefault("users", {})
        if key not in users:
            messagebox.showwarning("FiBu Mate", "Benutzer nicht gefunden.\nBitte wende dich an eine Administratorin / einen Administrator.")
            return
        users[key].setdefault("display_name", username)
        users[key].setdefault("first_name", "")
        users[key].setdefault("full_name", " ".join(x for x in [users[key].get("first_name", "").strip(), users[key].get("display_name", username).strip()] if x).strip() or username)
        users[key].setdefault("favorites", [])
        users[key].setdefault("email", "")
        users[key].setdefault("auth", {"password_hash": None, "enabled": False})
        users[key]["permission"] = ROLE_MIGRATION.get(users[key].get("permission", ROLE_E1), ROLE_E1)
        if key == SUPERUSER_KEY:
            users[key]["permission"] = ROLE_E4
        self.ensure_permissions_defaults()
        self.current_user_key = key
        self.current_user_display = users[key].get("display_name", username)
        self.favorites = set(fav for fav in users[key].get("favorites", []) if fav in TOOL_REGISTRY)
        users[key]["favorites"] = sorted(self.favorites)
        self.save_user_data()
        self.page_history = []
        self.breadcrumb = []
        self.show_page("main", "Hauptmenü", add_to_history=False)

    def logout(self):
        self.current_user_key = None; self.current_user_display = ""; self.favorites = set(); self.page_history = []; self.show_page("launch", add_to_history=False)

    def set_focused_tile(self, tile):
        if tile in self.focusable_tiles: self.focus_index = self.focusable_tiles.index(tile)

    def handle_escape(self, *_):
        handler = getattr(self, "module_escape_handler", None)
        if handler:
            try:
                if handler():
                    return "break"
            except Exception:
                pass
        if self.current_page != "launch":
            self.go_back()
        return "break"

    def handle_enter(self, *_):
        if getattr(self, "_suppress_next_global_return", False):
            self._suppress_next_global_return = False
            return "break"
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, tk.Entry):
            return "break"
        if 0 <= self.focus_index < len(self.focusable_tiles):
            try:
                self.focusable_tiles[self.focus_index].on_keyboard_activate()
            except Exception:
                pass
        return "break"

    def handle_tab(self, *_):
        if self.focusable_tiles: self.focus_index = (self.focus_index + 1) % len(self.focusable_tiles); self.focusable_tiles[self.focus_index].focus_set()
        return "break"

    def handle_shift_tab(self, *_):
        if self.focusable_tiles: self.focus_index = (self.focus_index - 1) % len(self.focusable_tiles); self.focusable_tiles[self.focus_index].focus_set()
        return "break"

    def confirm_exit(self):
        if messagebox.askyesno("FiBu Mate beenden", "Möchtest du FiBu Mate wirklich schließen?"): self.root.destroy()

    def run(self): self.root.mainloop()


if __name__ == "__main__":
    FiBuMateApp().run()
