import os
import sys
import json
import importlib
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

APP_NAME = "FiBu Mate"
VERSION_PREFIX = "0.2"
DEFAULT_BUILD = 5
VERSION_STATE_FILE = "version_state.json"
VERSION_HISTORY_FILE = "version_history.json"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(SCRIPT_DIR, "bin")
IMG_DIR = os.path.join(BIN_DIR, "Imgs")
USER_DIR = os.path.join(BIN_DIR, "User")
USER_DATA_PATH = os.path.join(USER_DIR, "fibu_mate_users.json")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

BANNER_GROSS_PATH = os.path.join(IMG_DIR, "FMBanner_Gross.png")
BANNER_KLEIN_PATH = os.path.join(IMG_DIR, "FMBanner_Klein.png")
HELP_IMAGE_PATH = os.path.join(IMG_DIR, "FM_Help_Menu.png")
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

COLOR_PALETTE = [("Blau", BLUE), ("Grün", "#059669"), ("Rot", RED), ("Gelb", "#F59E0B"), ("Lila", "#7C3AED"), ("Pink", "#EC4899"), ("Dunkelgrau", "#334155"), ("Orange", "#F97316"), ("Türkis", "#06B6D4")]

ROLE_STANDARD = "Standard"
ROLE_ADMIN = "Administrator"
ROLE_WAGNERM = "Wagnerm"
SUPERUSER_KEY = "wagnerm"
ROLE_ORDER = [ROLE_STANDARD, ROLE_ADMIN, ROLE_WAGNERM]
ROLE_RANK = {ROLE_STANDARD: 1, ROLE_ADMIN: 2, ROLE_WAGNERM: 3}

TOOL_REGISTRY = {
    "nike_pdf_to_excel": {"title": "Nike - PDF zu Excel", "module": "bin.tools.nike_pdf_to_excel", "favorite_label": "Nike PDF"},
    "nike_differenzen_pdf_zmir6": {"title": "Nike - Differenzen: PDF vs ZMIR6 (Excel)", "module": "bin.tools.nike_differenzen_pdf_zmir6", "favorite_label": "Nike Diff XLS"},
    "monthly_close": {"title": "Monatsabschluss", "module": "bin.tools.monthly_close", "favorite_label": "Monatsabschluss"},
    "x001_sap_test": {"title": "X001 SAP - Test", "module": "bin.tools.x001_sap_test", "favorite_label": "X001"},
}

MODULE_DESCRIPTIONS = {
    "nike_pdf_to_excel": "Mit diesem Modul lassen sich große Mengen an Nike PDF-Rechnungen in Excel ein Excel-Format ausgeben. Die auszugebenden Daten lassen sich filtern und sind individuell anpassbar.",
    "nike_differenzen_pdf_zmir6": "Vergleicht zwei Excel-Dateien (z. B. ZMIR6-Export vs. Nike PDF-Rechnungen Excel) und erzeugt eine Ergebnisdatei mit Differenzen.",
    "monthly_close": "Interaktives Monatsabschluss-Cockpit mit Teamfortschritt, Aufgabenstatus, Fristwarnungen und Anlagen je Aufgabe.",
    "quarterly_close": "Modul für den Quartalsabschluss. Inhalt und Logik werden noch definiert.",
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

    def _draw_module_menu_icon(self, cx, cy):
        color = "white"
        self.create_rectangle(cx - 22, cy - 12, cx - 6, cy + 4, outline=color, width=2)
        self.create_rectangle(cx - 4, cy - 12, cx + 12, cy + 4, outline=color, width=2)
        self.create_rectangle(cx - 13, cy + 7, cx + 3, cy + 23, outline=color, width=2)
        self.create_line(cx - 18, cy - 4, cx - 10, cy - 4, fill=color, width=2)
        self.create_line(cx, cy - 4, cx + 8, cy - 4, fill=color, width=2)
        self.create_line(cx - 9, cy + 15, cx - 1, cy + 15, fill=color, width=2)

    def _draw_gear_icon(self, cx, cy):
        color = "white"
        for dx, dy in [(0, -16), (0, 16), (-16, 0), (16, 0), (-11, -11), (11, -11), (-11, 11), (11, 11)]:
            self.create_rectangle(cx + dx - 3, cy + dy - 3, cx + dx + 3, cy + dy + 3, fill=color, outline=color)
        self.create_oval(cx - 13, cy - 13, cx + 13, cy + 13, outline=color, width=3)
        self.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, outline=color, width=2)

    def _draw_info_icon(self, cx, cy):
        color = "white"
        self.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, outline=color, width=3)
        self.create_text(cx, cy + 1, text="i", fill=color, font=("Segoe UI", 20, "bold"))

    def _draw_lock_icon(self, cx, cy):
        color = BLUE if self.lock_tile else "white"
        self.create_arc(cx - 14, cy - 20, cx + 14, cy + 8, start=0, extent=180, style="arc", outline=color, width=3)
        self.create_rectangle(cx - 17, cy - 2, cx + 17, cy + 22, outline=color, width=3)
        self.create_oval(cx - 3, cy + 7, cx + 3, cy + 13, fill=color, outline=color)
        self.create_line(cx, cy + 12, cx, cy + 18, fill=color, width=2)

    def _draw_main_icon(self, icon_type, cx, cy):
        if icon_type == "modules":
            self._draw_module_menu_icon(cx, cy)
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
        if self.lock_tile:
            self.create_text((x0 + x1) / 2, y0 + 22, text=self.title, anchor="n", fill=TEXT, font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")
            self._draw_main_icon("lock", (x0 + x1) / 2, y0 + self.tile_height * 0.64)
        else:
            if self.center_text:
                self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=self.title, anchor="center", fill="white", font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")
            else:
                self.create_text((x0 + x1) / 2, y0 + 36, text=self.title, anchor="n", fill="white", font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")
            if self.icon_type:
                self._draw_main_icon(self.icon_type, (x0 + x1) / 2, y0 + self.tile_height * 0.64)
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
        default = {"last_username_prefill": "", "users": {}}
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
            u.setdefault("auth", {"password_hash": None, "enabled": False})
            u["favorites"] = [fav for fav in u.get("favorites", []) if fav in TOOL_REGISTRY]
            if key == SUPERUSER_KEY:
                u["permission"] = ROLE_WAGNERM
            else:
                if u.get("permission") == ROLE_WAGNERM:
                    u["permission"] = ROLE_STANDARD
                else:
                    u.setdefault("permission", ROLE_STANDARD)

    def my_role(self):
        if not self.current_user_key:
            return ROLE_STANDARD
        if self.current_user_key == SUPERUSER_KEY:
            return ROLE_WAGNERM
        return self.user_data.get("users", {}).get(self.current_user_key, {}).get("permission", ROLE_STANDARD)

    def role_rank(self, role):
        return ROLE_RANK.get(role, ROLE_RANK[ROLE_STANDARD])

    def can_view_user_management(self):
        return self.my_role() in (ROLE_ADMIN, ROLE_WAGNERM)

    def can_create_users(self):
        return self.my_role() == ROLE_WAGNERM

    def can_manage_permissions(self):
        return self.my_role() in (ROLE_ADMIN, ROLE_WAGNERM)

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
        self.draw_help_control(); self.draw_close_control()

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

    def draw_help_control(self):
        if self.current_page == "launch": return
        frame = tk.Frame(self.root, bg=HEADER, cursor="hand2")
        icon = tk.Canvas(frame, width=24, height=18, bg=HEADER, highlightthickness=0, bd=0, cursor="hand2")
        icon.create_text(12, 9, text="[i]", fill="black", font=("Segoe UI", 10, "bold"))
        txt = tk.Label(frame, text="Hilfe", fg="black", bg=HEADER, font=("Segoe UI", 10, "bold"), cursor="hand2")
        icon.pack(side="left"); txt.pack(side="left", padx=(2, 0))
        def open_help(_event=None): self.show_help_popup()
        frame.bind("<Button-1>", open_help); icon.bind("<Button-1>", open_help); txt.bind("<Button-1>", open_help)
        self.widget_items.append(frame); self.canvas.create_window(self.canvas.winfo_width() - 66, 7, window=frame, anchor="ne")

    def draw_close_control(self):
        label = tk.Label(self.root, text="X", bg=HEADER, fg=RED, font=("Segoe UI", 10, "bold"), cursor="hand2", relief="solid", bd=1, padx=4)
        label.bind("<Button-1>", lambda e: self.confirm_exit()); self.widget_items.append(label)
        self.canvas.create_window(self.canvas.winfo_width() - 22, 7, window=label, anchor="ne")

    def show_help_popup(self):
        popup = tk.Toplevel(self.root); popup.title("FiBu Mate - Hilfe"); popup.configure(bg=BG); popup.transient(self.root); popup.grab_set(); popup.resizable(True, True); popup.geometry("1000x700"); popup.minsize(780, 520)
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
        app_tiles = [
            {"title": "Datenaufbereitung", "cmd": lambda: self.show_page("data_prep", "Datenaufbereitung", True), "fixed": None, "lock": False, "icon": "modules", "fold": False},
            {"title": "Abschlusskalender", "cmd": lambda: self.show_page("closing_calendar", "Abschlusskalender", True), "fixed": None, "lock": False, "icon": "modules", "fold": False},
        ]
        footer_tiles = [
            {"title": "In Entwicklung", "cmd": self.try_open_in_dev, "fixed": GREY_TILE, "lock": True, "icon": None, "fold": False},
            {"title": "Informationen", "cmd": lambda: self.show_page("information", "Informationen", True), "fixed": None, "lock": False, "icon": "info", "fold": True},
            {"title": "Einstellungen", "cmd": lambda: self.show_page("settings", "Einstellungen", True), "fixed": None, "lock": False, "icon": "gear", "fold": True},
        ]
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); tw = max(230, min(310, int(w * 0.155))); th = max(125, min(170, int(h * 0.155))); gap_x = max(34, int(w * 0.035))
        def centered_x_positions(count):
            if count <= 0: return []
            total_width = count * tw + (count - 1) * gap_x; start_x = (w - total_width) / 2 + tw / 2
            return [start_x + i * (tw + gap_x) for i in range(count)]
        def create_tile_group(items, center_y_percent, id_prefix):
            xs = centered_x_positions(len(items)); y = y_pct(h, center_y_percent)
            for i, item in enumerate(items):
                tile = Tile(self.root, self, f"{id_prefix}_{i}", item["title"], item["cmd"], favorite_enabled=False, fixed_color=item["fixed"], lock_tile=item["lock"], icon_type=item["icon"], corner_fold=item["fold"])
                tile.resize_tile(tw, th); self.widget_items.append(tile); self.focusable_tiles.append(tile); self.canvas.create_window(xs[i], y, window=tile, anchor="center")
        create_tile_group(app_tiles, 60, "main_app"); line_y = y_pct(h, 25); self.canvas.create_line(x_pct(w, 9.5), line_y, x_pct(w, 92), line_y, fill=BLUE, width=4); create_tile_group(footer_tiles, 17.5, "main_footer"); self.draw_bottom_logo()

    def try_open_in_dev(self):
        if self.my_role() != ROLE_WAGNERM: return
        self.show_page("in_dev", "In Entwicklung", True)

    def render_data_prep_menu(self):
        modules = [("Nike - PDF zu Excel", "nike_pdf_to_excel"), ("Nike - Differenzen: PDF vs ZMIR6 (Excel)", "nike_differenzen_pdf_zmir6"), ("Nike - Differenzbericht Sales und Lager", "nike_sales_stock_diff")]
        self.render_module_menu(modules, show_descriptions=True); self.draw_bottom_logo()

    def render_closing_calendar_menu(self):
        modules = [("Monatsabschluss", "monthly_close"), ("Quartalsabschluss", "quarterly_close")]
        self.render_module_menu(modules, show_descriptions=True); self.draw_bottom_logo()

    def render_in_dev_menu(self):
        self.render_module_menu([("X001 SAP - Test", "x001_sap_test")], show_descriptions=True); self.draw_bottom_logo()

    def render_settings_menu(self):
        items = [("Farbschema", "tile_colors")]
        if self.can_view_user_management(): items.append(("Benutzerverwaltung", "users"))
        items.append(("Berechtigungen", "permissions")); self.render_center_menu(items, title="Einstellungen"); self.draw_bottom_logo()

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
        def set_color(col):
            if self.current_user_key:
                self.user_data["users"][self.current_user_key]["tile_color"] = col; self.save_user_data()
            self.render_page()
        for idx, (name, color) in enumerate(COLOR_PALETTE):
            r = 1 + idx // 5; c = idx % 5; sw = tk.Canvas(frame, width=140, height=78, bg=BG, highlightthickness=0, bd=0, cursor="hand2")
            sw.create_rectangle(8, 8, 132, 54, fill=color, outline=LINE, width=2); sw.create_text(70, 66, text=name, fill=TEXT, font=("Segoe UI", 9, "bold")); sw.bind("<Button-1>", lambda e, col=color: set_color(col)); sw.grid(row=r, column=c, padx=10, pady=10)
        def reset():
            if self.current_user_key:
                self.user_data["users"][self.current_user_key].pop("tile_color", None); self.save_user_data()
            self.render_page()
        tk.Button(frame, text="Standard wiederherstellen", command=reset, bg=BLUE, fg="white", bd=0, padx=16, pady=10, cursor="hand2").grid(row=r + 1, column=0, columnspan=5, pady=(18, 6))
        self.canvas.create_window(self.canvas.winfo_width() / 2, y_pct(self.canvas.winfo_height(), 48), window=frame, anchor="center")

    def render_users_menu(self):
        if not self.can_view_user_management(): self.render_menu_text("Keine Berechtigung für die Benutzerverwaltung."); return
        frame = tk.Frame(self.root, bg=BG); self.widget_items.append(frame); tk.Label(frame, text="Benutzerverwaltung", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 14))
        users = self.user_data.setdefault("users", {}); headers = ["Benutzer", "Anzeigename", "Rolle", "Passwort"]
        for col, header in enumerate(headers): tk.Label(frame, text=header, bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=1, column=col, sticky="w", padx=(0, 20))
        row = 2
        for key in sorted(users.keys()):
            user = users[key]; values = [key, user.get("display_name", key), user.get("permission", ROLE_STANDARD), "aktiv" if user.get("auth", {}).get("enabled") else "nicht aktiv"]
            for col, value in enumerate(values): tk.Label(frame, text=value, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=col, sticky="w", padx=(0, 20), pady=4)
            row += 1
        if self.can_create_users():
            tk.Frame(frame, bg=LINE, height=1).grid(row=row, column=0, columnspan=4, sticky="ew", pady=(18, 14)); row += 1
            tk.Label(frame, text="Neuen Benutzer anlegen", font=("Segoe UI", 12, "bold"), bg=BG, fg=TEXT).grid(row=row, column=0, columnspan=4, sticky="w", pady=(0, 8)); row += 1
            username_var = tk.StringVar(); tk.Label(frame, text="Benutzername", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w")
            tk.Entry(frame, textvariable=username_var, font=("Segoe UI", 10), width=32, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1).grid(row=row, column=1, sticky="w", padx=(0, 20))
            def create_user():
                raw_name = " ".join(username_var.get().strip().split()); key = normalize_username(raw_name)
                if not key: messagebox.showwarning("FiBu Mate", "Bitte einen Benutzernamen eingeben."); return
                if key in users: messagebox.showwarning("FiBu Mate", "Dieser Benutzer existiert bereits."); return
                users[key] = {"display_name": raw_name, "favorites": [], "auth": {"password_hash": None, "enabled": False}, "permission": ROLE_WAGNERM if key == SUPERUSER_KEY else ROLE_STANDARD}; self.ensure_permissions_defaults(); self.save_user_data(); messagebox.showinfo("FiBu Mate", f"Benutzer wurde angelegt:\n\n{raw_name}"); self.render_page()
            tk.Button(frame, text="Benutzer anlegen", command=create_user, bg=BLUE, fg="white", bd=0, padx=14, pady=8, cursor="hand2").grid(row=row, column=2, sticky="w")
        self.canvas.create_window(self.canvas.winfo_width() / 2, y_pct(self.canvas.winfo_height(), 48), window=frame, anchor="center")

    def render_permissions_menu(self):
        frame = tk.Frame(self.root, bg=BG); self.widget_items.append(frame); tk.Label(frame, text="Berechtigungen", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 10))
        info_text = "Berechtigungen können von berechtigten Rollen maximal bis zur eigenen Rolle vergeben werden.\nDie Rolle Wagnerm ist ausschließlich für den Benutzer Wagnerm reserviert."
        tk.Label(frame, text=info_text, bg=BG, fg=TEXT2, font=("Segoe UI", 10), justify="left").grid(row=1, column=0, columnspan=5, sticky="w", pady=(0, 16))
        users = self.user_data.setdefault("users", {}); can_edit = self.can_manage_permissions(); headers = ["Benutzer", "Anzeigename", "Aktuelle Rolle", "Ändern"]
        for col, header in enumerate(headers): tk.Label(frame, text=header, bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=2, column=col, sticky="w", padx=(0, 24))
        row = 3
        for key in sorted(users.keys()):
            user = users[key]; current_role = user.get("permission", ROLE_STANDARD)
            tk.Label(frame, text=key, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=0, sticky="w", padx=(0, 24), pady=5); tk.Label(frame, text=user.get("display_name", key), bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=1, sticky="w", padx=(0, 24), pady=5); tk.Label(frame, text=current_role, bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=2, sticky="w", padx=(0, 24), pady=5)
            if not can_edit:
                tk.Label(frame, text="nur Ansicht", bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=3, sticky="w", pady=5); row += 1; continue
            if self.my_role() == ROLE_ADMIN and (key == SUPERUSER_KEY or current_role == ROLE_WAGNERM):
                tk.Label(frame, text="gesperrt", bg=BG, fg=TEXT2, font=("Segoe UI", 10)).grid(row=row, column=3, sticky="w", pady=5); row += 1; continue
            available_roles = [role for role in ROLE_ORDER if self.role_rank(role) <= self.max_assignable_role_rank()]
            if key != SUPERUSER_KEY and ROLE_WAGNERM in available_roles: available_roles.remove(ROLE_WAGNERM)
            if key == SUPERUSER_KEY: available_roles = [ROLE_WAGNERM]
            role_var = tk.StringVar(value=current_role if current_role in available_roles else available_roles[0]); dropdown = tk.OptionMenu(frame, role_var, *available_roles); dropdown.config(bg="#E8EEF5", fg=TEXT, bd=1, highlightthickness=0, cursor="hand2"); dropdown.grid(row=row, column=3, sticky="w", pady=5)
            def save_role(user_key=key, var=role_var):
                new_role = var.get()
                if user_key == SUPERUSER_KEY: new_role = ROLE_WAGNERM
                if user_key != SUPERUSER_KEY and new_role == ROLE_WAGNERM: messagebox.showwarning("FiBu Mate", "Die Rolle Wagnerm darf nur der Benutzer Wagnerm tragen."); return
                if self.role_rank(new_role) > self.max_assignable_role_rank(): messagebox.showwarning("FiBu Mate", "Du kannst keine Rolle vergeben, die höher als deine eigene Rolle ist."); return
                users[user_key]["permission"] = new_role; self.ensure_permissions_defaults(); self.save_user_data(); messagebox.showinfo("FiBu Mate", "Berechtigung wurde gespeichert."); self.render_page()
            tk.Button(frame, text="Speichern", command=save_role, bg=BLUE, fg="white", bd=0, padx=10, pady=5, cursor="hand2").grid(row=row, column=4, sticky="w", padx=(8, 0), pady=5); row += 1
        self.canvas.create_window(self.canvas.winfo_width() / 2, y_pct(self.canvas.winfo_height(), 48), window=frame, anchor="center")

    def render_versions_menu(self):
        history = self.load_version_history().get("entries", []); w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); area_top = 132; area_bottom = max(area_top + 260, h - 92); view_h = int(area_bottom - area_top)
        container = tk.Frame(self.root, bg=BG); self.widget_items.append(container); self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)
        scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0); scroll_canvas.place(x=0, y=0, width=w - 10, height=view_h)
        y = 20; left = 24; right = w - 34
        for e in history:
            ver = e.get("version", ""); date = e.get("date", ""); bullets = e.get("bullets", []); scroll_canvas.create_text(left, y, text=f"{ver}.{date}", anchor="nw", fill=TEXT, font=("Segoe UI", 12, "bold")); y += 24
            for b in bullets: scroll_canvas.create_text(left + 16, y, text=f"• {b}", anchor="nw", fill=TEXT2, font=("Segoe UI", 11), width=max(200, right - (left + 16))); y += 18
            y += 12; self.draw_relief_line(scroll_canvas, y, 10, right); y += 22
        scroll_canvas.configure(scrollregion=(0, 0, w, max(view_h, y + 40)))

    def render_menu_text(self, text):
        lab = tk.Label(self.root, text=text, font=("Segoe UI", 16), bg=BG, fg=TEXT); self.widget_items.append(lab); self.canvas.create_window(x_pct(self.canvas.winfo_width(), 50), y_pct(self.canvas.winfo_height(), 60), window=lab, anchor="center"); self.draw_bottom_logo()

    def draw_relief_line(self, canvas, y, x1, x2):
        for i in range(120):
            t = i / 119; fade = 1 - abs(t - 0.5) * 2; sx = x1 + (x2 - x1) * i / 120; ex = x1 + (x2 - x1) * (i + 1) / 120
            canvas.create_line(sx, y, ex, y, fill=blend(BG, "#1F2933", 0.30 * fade), width=2); canvas.create_line(sx, y + 2, ex, y + 2, fill=blend(BG, WHITE, 0.65 * fade), width=1)

    def draw_module_description(self, canvas, module_id, x1, y_top, width):
        txt = MODULE_DESCRIPTIONS.get(module_id, "")
        if txt: canvas.create_text(x1 + DESCRIPTION_X_OFFSET, y_top + DESCRIPTION_Y_OFFSET, text=txt, anchor="nw", fill=DESCRIPTION_COLOR, font=DESCRIPTION_FONT, width=max(120, int(width) - 2 * DESCRIPTION_X_OFFSET), justify="left")

    def render_module_menu(self, modules, show_descriptions=True):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height(); tile_w = max(290, min(390, int(w * 0.22))); tile_h = max(120, min(160, int(h * 0.15))); gap = max(18, int(h * 0.025)); area_top = 132; area_bottom = max(area_top + 260, h - 92); view_h = int(area_bottom - area_top); first_center_x = x_pct(w, 25); first_center_y = y_pct(h, 70); left_x = max(0, first_center_x - tile_w / 2 - 8); top = max(0, first_center_y - tile_h / 2 - area_top - 8)
        container = tk.Frame(self.root, bg=BG); self.widget_items.append(container); self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h); canvas_w = w - left_x - 10; scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0); scroll_canvas.place(x=left_x, y=0, width=canvas_w, height=view_h); content_h = top + len(modules) * (tile_h + gap) + 20; scroll_canvas.configure(scrollregion=(0, 0, canvas_w, content_h)); desc_x1 = tile_w + 90; desc_x2 = canvas_w - 20
        for idx, (title, module_id) in enumerate(modules):
            y = top + idx * (tile_h + gap); cmd = (lambda mid=module_id: self.open_tool(mid)) if module_id in TOOL_REGISTRY else self.show_placeholder
            tile = Tile(scroll_canvas, self, module_id, title, cmd, favorite_enabled=module_id in TOOL_REGISTRY); tile.resize_tile(tile_w, tile_h); self.focusable_tiles.append(tile); scroll_canvas.create_window(0, y, window=tile, anchor="nw")
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
        username = " ".join(str(username).strip().split()); key = normalize_username(username)
        if not key: messagebox.showwarning("FiBu Mate", "Bitte einen Nutzernamen eingeben."); return
        users = self.user_data.setdefault("users", {})
        if key not in users: users[key] = {"display_name": username, "favorites": [], "auth": {"password_hash": None, "enabled": False}, "permission": ROLE_WAGNERM if key == SUPERUSER_KEY else ROLE_STANDARD}
        else:
            users[key].setdefault("display_name", username); users[key].setdefault("favorites", []); users[key].setdefault("auth", {"password_hash": None, "enabled": False})
            if key == SUPERUSER_KEY: users[key]["permission"] = ROLE_WAGNERM
            elif users[key].get("permission") == ROLE_WAGNERM: users[key]["permission"] = ROLE_STANDARD
            else: users[key].setdefault("permission", ROLE_STANDARD)
        self.ensure_permissions_defaults(); self.current_user_key = key; self.current_user_display = users[key].get("display_name", username); self.favorites = set(fav for fav in users[key].get("favorites", []) if fav in TOOL_REGISTRY); users[key]["favorites"] = sorted(self.favorites); self.save_user_data(); self.page_history = []; self.breadcrumb = []; self.show_page("main", "Hauptmenü", add_to_history=False)

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
