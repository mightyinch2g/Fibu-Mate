
import os
import sys
import json
import importlib
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from PIL import Image, ImageTk

APP_NAME = "FiBu Mate"

# --- Versioning ---
# v0.2 is static prefix. The digit(s) after v0.2 is an incrementing build number.
# Date appended in format JJ.MM.TT.
VERSION_PREFIX = "0.2"
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
INTERSPORT_LOGO_CANDIDATES = [
    "IS_Banner_lang.png",
    "Intersport_Logo.png",
    "INTERSPORT_Logo.png",
    "intersport_logo.png",
    "INTERSPORT.png",
]

TOOL_REGISTRY = {
    "nike_pdf_to_excel": {
        "title": "Nike - PDF zu Excel",
        "module": "bin.tools.nike_pdf_to_excel",
        "favorite_label": "Nike PDF",
    },
    "nike_zmir6_diff": {
        "title": "Nike - Differenzabgleich: Rechnungen & SAP",
        "module": "bin.tools.nike_zmir6_diff",
        "favorite_label": "Modul Diff",
    },
}

# --- Design colors ---
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
GREY_DISABLED = "#B9C3CF"
WHITE = "#FFFFFF"

FONT_TITLE = ("Segoe UI", 36, "bold")
FONT_MENU = ("Segoe UI", 27, "bold")
FONT_TILE = ("Segoe UI", 18, "bold")
FONT_TILE_SMALL = ("Segoe UI", 15, "bold")
FONT_SMALL = ("Segoe UI", 10)

# --- Kachelfarben (Standardfarben) ---
COLOR_PALETTE = [
    ("Blau", BLUE),
    ("Grün", "#059669"),
    ("Rot", RED),
    ("Gelb", "#FFD700"),
    ("Lila", "#7C3AED"),
    ("Pink", "#EC4899"),
    ("Dunkelgrau", "#334155"),
    ("Hellgrau", "#D6DCE4"),
    ("Weiß", "#FFFFFF"),
    ("Orange", "#F97316"),
    ("Türkis", "#06B6D4"),
]

# --- Modulbeschreibungen (Vorlage Modulmenü) ---
MODULE_DESCRIPTIONS = {
    "nike_pdf_to_excel": (
        "Mit diesem Modul lassen sich große Mengen an Nike PDF-Rechnungen in Excel ein Excel-Format ausgeben. "
        "Die auszugebenden Daten lassen sich filtern und sind individuell anpassbar."
    )
}
DESCRIPTION_FONT = ("Segoe UI", 11)
DESCRIPTION_COLOR = TEXT2
DESCRIPTION_X_OFFSET = 14
DESCRIPTION_Y_OFFSET = 18

# --- Berechtigungen ---
ROLE_STANDARD = "Standard"
ROLE_ADMIN = "Administrator"
ROLE_WAGNERM = "Wagnerm"
ROLE_RANK = {ROLE_STANDARD: 1, ROLE_ADMIN: 2, ROLE_WAGNERM: 3}
SUPERUSER_KEY = "wagnerm"  # normalize_username("Wagnerm")


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


def now_date_str() -> str:
    # JJ.MM.TT
    return datetime.now().strftime("%y.%m.%d")


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


def load_image(path: str):
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
        p = os.path.join(IMG_DIR, name)
        if os.path.exists(p):
            return p
    return None


class ArrowIndicator(tk.Canvas):
    """Blauer (oder ausgegrauter) Scroll-Indikatorpfeil."""

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


class IconButton(tk.Canvas):
    def __init__(self, parent, text, icon, command, width=210, height=50, bg_color=BLUE, font=("Segoe UI", 10, "bold")):
        super().__init__(parent, width=width, height=height, bg=BG, highlightthickness=0, bd=0, cursor="arrow")
        self.text = text
        self.icon = icon
        self.command = command
        self.w = width
        self.h = height
        self.bg_color = bg_color
        self.font = font
        self.hovered = False
        self.pressed = False
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.draw()

    def current_color(self):
        if self.pressed:
            return darken(self.bg_color, 0.28)
        if self.hovered:
            return darken(self.bg_color, 0.16)
        return self.bg_color

    def draw_icon(self, x, y):
        if self.icon == "logout":
            self.create_rectangle(x - 13, y - 10, x + 1, y + 10, outline="white", width=2)
            self.create_polygon(x - 2, y - 4, x + 9, y - 4, x + 9, y - 9, x + 18, y, x + 9, y + 9, x + 9, y + 4, x - 2, y + 4, fill="white", outline="white")
        elif self.icon == "userplus":
            self.create_oval(x - 12, y - 13, x + 2, y + 1, outline="white", width=2)
            self.create_arc(x - 18, y, x + 8, y + 22, start=20, extent=140, outline="white", width=2, style="arc")
            self.create_line(x + 14, y - 7, x + 14, y + 9, fill="white", width=3, capstyle="round")
            self.create_line(x + 7, y + 1, x + 21, y + 1, fill="white", width=3, capstyle="round")
        elif self.icon == "save":
            self.create_rectangle(x - 13, y - 13, x + 13, y + 13, outline="white", width=2)
            self.create_rectangle(x - 7, y - 10, x + 7, y - 3, fill="white", outline="white")
            self.create_rectangle(x - 7, y + 4, x + 7, y + 12, outline="white", width=2)
        elif self.icon == "cancel":
            self.create_line(x - 10, y - 10, x + 10, y + 10, fill="#FFB4B4", width=4, capstyle="round")
            self.create_line(x + 10, y - 10, x - 10, y + 10, fill="#FFB4B4", width=4, capstyle="round")

    def draw(self):
        self.delete("all")
        off = 1 if self.pressed else 0
        c = self.current_color()
        self.create_rectangle(2 + off, 2 + off, self.w - 2 + off, self.h - 2 + off, fill=c, outline=c)
        if self.icon:
            self.draw_icon(30 + off, self.h / 2 + off)
            self.create_text(58 + off, self.h / 2 + off, text=self.text, anchor="w", fill="white", font=self.font, width=self.w - 66)
        else:
            self.create_text(self.w / 2 + off, self.h / 2 + off, text=self.text, fill="white", font=self.font, width=self.w - 18)

    def on_enter(self, *_):
        self.hovered = True
        self.configure(cursor="hand2")
        self.draw()

    def on_leave(self, *_):
        self.hovered = False
        self.pressed = False
        self.configure(cursor="arrow")
        self.draw()

    def on_press(self, *_):
        self.pressed = True
        self.draw()

    def on_release(self, *_):
        was = self.pressed
        self.pressed = False
        self.draw()
        if was and self.command:
            self.after(50, self.command)


class Tile(tk.Canvas):
    def __init__(self, parent, app, tile_id, title, command=None, favorite_enabled=False, corner=False, center_text=False):
        super().__init__(parent, highlightthickness=0, bd=0, bg=BG, cursor="arrow", takefocus=True)
        self.app = app
        self.tile_id = tile_id
        self.title = title
        self.command = command
        self.favorite_enabled = favorite_enabled
        self.corner = corner
        self.center_text = center_text
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
        return self.app.current_tile_color() or BLUE

    def current_color(self):
        if self.pressed:
            return darken(self.base_color(), 0.28)
        if self.hovered:
            return darken(self.base_color(), 0.16)
        return self.base_color()

    def resize_tile(self, w, h):
        self.tile_width = int(w)
        self.tile_height = int(h)
        self.configure(width=self.tile_width + 16, height=self.tile_height + 16)
        self.draw()

    def title_font(self):
        return FONT_TILE_SMALL if len(self.title) > 28 else FONT_TILE

    def draw(self):
        self.delete("all")
        pad = 8
        off = 1 if self.pressed else 0
        x0, y0 = pad + off, pad + off
        x1, y1 = x0 + self.tile_width - off * 2, y0 + self.tile_height - off * 2
        if not self.pressed:
            self.create_rectangle(pad + 5, pad + 6, pad + 5 + self.tile_width, pad + 6 + self.tile_height, fill=SHADOW, outline=SHADOW)
        self.create_rectangle(x0, y0, x1, y1, fill=self.current_color(), outline=self.current_color())

        if self.corner:
            tri = min(56, int(self.tile_width * 0.22))
            self.create_polygon(x1 - tri, y0, x1, y0, x1, y0 + tri, fill=RED, outline=RED)

        if self.center_text:
            self.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=self.title, anchor="center", fill="white", font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")
        else:
            self.create_text((x0 + x1) / 2, y0 + 36, text=self.title, anchor="n", fill="white", font=self.title_font(), width=max(120, self.tile_width - 44), justify="center")

        self.star_bounds = None
        if self.favorite_enabled and (self.hovered or self.tile_id in self.app.favorites):
            sx, sy = x1 - 24, y0 + 24
            self.star_bounds = (sx - 18, sy - 18, sx + 18, sy + 18)
            self.create_text(sx, sy, text="★", fill=GOLD if self.tile_id in self.app.favorites else STAR_GREY, font=("Segoe UI", 24, "bold"))

    def point_in_star(self, x, y):
        return self.star_bounds and self.star_bounds[0] <= x <= self.star_bounds[2] and self.star_bounds[1] <= y <= self.star_bounds[3]

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
        self.pressed = True
        self.draw()
        self.after(90, self.release_keyboard)

    def release_keyboard(self):
        self.pressed = False
        self.draw()
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
        self.last_page_change_ms = 0

        self.widget_items = []
        self.focusable_tiles = []
        self.focus_index = -1

        self.favorites = set()
        self.current_user_key = None
        self.current_user_display = ""

        self.user_data = self.load_user_data()
        self.ensure_permissions_defaults()

        self.version_state = self.load_version_state()

        self.image_refs = []
        self.resize_after_id = None
        self.toast_after_id = None

        self.banner_big = load_image(BANNER_GROSS_PATH)
        self.banner_small = load_image(BANNER_KLEIN_PATH)
        self.help_image = load_image(HELP_IMAGE_PATH)
        logo_path = find_intersport_logo()
        self.intersport_logo = load_image(logo_path) if logo_path else None

        self.create_footer()

        self.canvas = tk.Canvas(self.root, highlightthickness=0, bg=BG, cursor="arrow")
        self.canvas.pack(side="top", fill="both", expand=True)
        self.canvas.bind("<Configure>", self.on_resize)

        # global scroll (works even when hovering tiles)
        self.active_scroll_canvas = None
        self.root.bind_all("<MouseWheel>", self.on_global_mousewheel)

        for key, handler in [
            ("<Escape>", self.handle_escape),
            ("<F1>", self.handle_f1),
            ("<Return>", self.handle_enter),
            ("<Tab>", self.handle_tab),
            ("<Shift-Tab>", self.handle_shift_tab),
            ("<ISO_Left_Tab>", self.handle_shift_tab),
            ("<Left>", self.handle_left),
            ("<Right>", self.handle_right),
            ("<Up>", self.handle_up),
            ("<Down>", self.handle_down),
        ]:
            self.root.bind_all(key, handler)

        self.show_page("launch", add_to_history=False)

    # ---------- version ----------
    def version_label_text(self) -> str:
        build = int(self.version_state.get("build", 5))
        return f"v{VERSION_PREFIX}{build}.{now_date_str()}"

    def load_version_state(self):
        os.makedirs(USER_DIR, exist_ok=True)
        path = os.path.join(USER_DIR, VERSION_STATE_FILE)
        default = {"build": 5}
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
            path = os.path.join(USER_DIR, VERSION_STATE_FILE)
            with open(path, "w", encoding="utf-8") as f:
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
            path = os.path.join(USER_DIR, VERSION_HISTORY_FILE)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def bump_version(self, bullets):
        self.version_state["build"] = int(self.version_state.get("build", 5)) + 1
        self.save_version_state()

        history = self.load_version_history()
        history.setdefault("entries", [])
        history["entries"].insert(
            0,
            {
                "version": f"v{VERSION_PREFIX}{self.version_state['build']}",
                "date": now_date_str(),
                "bullets": bullets if isinstance(bullets, list) else [str(bullets)],
            },
        )
        self.save_version_history(history)

        try:
            self.version_label.config(text=self.version_label_text())
        except Exception:
            pass

    # ---------- permissions ----------
    def ensure_permissions_defaults(self):
        users = self.user_data.setdefault("users", {})
        for k, u in users.items():
            if k == SUPERUSER_KEY:
                u["permission"] = ROLE_WAGNERM
            else:
                u.setdefault("permission", ROLE_STANDARD)

    def my_role(self):
        if not self.current_user_key:
            return ROLE_STANDARD
        if self.current_user_key == SUPERUSER_KEY:
            return ROLE_WAGNERM
        return self.user_data.get("users", {}).get(self.current_user_key, {}).get("permission", ROLE_STANDARD)

    def can_assign_role(self, role):
        return ROLE_RANK.get(role, 1) <= ROLE_RANK.get(self.my_role(), 1)

    # ---------- user data ----------
    def current_tile_color(self):
        if self.current_user_key:
            return self.user_data.get("users", {}).get(self.current_user_key, {}).get("tile_color")
        return None

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

    # ---------- footer ----------
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

    # ---------- nav ----------
    def show_page(self, page_name, title="", add_to_history=True):
        if add_to_history and self.current_page:
            self.page_history.append((self.current_page, self.current_title))
        self.current_page = page_name
        self.current_title = title
        self.last_page_change_ms = int(datetime.now().timestamp() * 1000)
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
            self.breadcrumb = self.breadcrumb[:existing + 1] if existing is not None else self.breadcrumb + [(page_name, title)]

    def go_back(self):
        if self.current_page == "permissions_manage" and getattr(self, "permissions_dirty", False):
            self.ask_save_permissions_dialog()
            return
        if self.page_history:
            page, title = self.page_history.pop()
            self.current_page, self.current_title = page, title
            self.update_breadcrumb(page, title)
            self.render_page()

    # ---------- global scroll ----------
    def on_global_mousewheel(self, event):
        if self.active_scroll_canvas is None:
            return
        if self.current_page in ("data_prep", "settings", "information", "versions", "permissions_manage"):
            self.active_scroll_canvas.yview_scroll(int(-event.delta / 120), "units")
            if hasattr(self, "_update_scroll_indicators"):
                self._update_scroll_indicators()

    # ---------- rendering framework ----------
    def clear_content(self):
        self.active_scroll_canvas = None
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
        else:
            self.draw_header(self.current_title)
            self.draw_controls()
            self.draw_path_bar()
            self.draw_favorites_bar()

            if self.current_page == "main":
                self.render_main_menu()
            elif self.current_page == "data_prep":
                self.render_data_prep_menu()
            elif self.current_page == "settings":
                self.render_settings_menu()
            elif self.current_page == "tile_colors":
                self.render_tile_colors_menu()
            elif self.current_page == "permissions_manage":
                self.render_permissions_manage_menu()
            elif self.current_page == "information":
                self.render_information_menu()
            elif self.current_page == "versions":
                self.render_versions_menu()
            elif self.current_page.startswith("tool:"):
                self.render_external_tool(self.current_page.replace("tool:", "", 1))
            else:
                self.render_menu_text("Platzhaltermenü - keine Anwendungen verfügbar.")

        if self.focusable_tiles:
            self.focus_index = 0
            self.focusable_tiles[0].focus_set()

    def on_resize(self, *_):
        if self.resize_after_id:
            self.root.after_cancel(self.resize_after_id)
        self.resize_after_id = self.root.after(35, self.render_page)

    # ---------- background + header ----------
    def draw_background(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_rectangle(0, 0, w, h, fill=BG, outline="")
        self.canvas.create_rectangle(0, 0, w, 128, fill=HEADER, outline="")
        self.canvas.create_rectangle(0, 128, w, 131, fill=LINE, outline="")
        self.canvas.create_polygon(w * 0.64, 128, w, 128, w, h, w * 0.81, h, fill="#DCE5EF", outline="")
        self.canvas.create_polygon(0, h * 0.69, w * 0.30, h, 0, h, fill="#D7E2ED", outline="")
        self.canvas.create_polygon(w * 0.76, h * 0.20, w, h * 0.30, w, h * 0.54, w * 0.70, h * 0.42, fill="#EAF0F6", outline="")
        self.canvas.create_oval(w * 0.07, h * 0.16, w * 0.34, h * 0.58, fill="#F5F8FB", outline="")
        self.canvas.create_oval(w * 0.78, h * 0.63, w * 1.06, h * 1.04, fill="#E1EAF3", outline="")

    def draw_header(self, title):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.banner_small:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.banner_small, 520, 86))
            self.image_refs.append(ph)
            self.canvas.create_image(w / 2, h * 0.073, image=ph)
        else:
            self.canvas.create_text(w / 2, h * 0.083, text="FiBu Mate", font=FONT_TITLE, fill=TEXT)
        self.canvas.create_text(w / 2, h * 0.155, text=title, font=FONT_MENU, fill=TEXT2)

    # ---------- bars ----------
    def draw_gradient_line(self, x1, x2, y):
        width = max(1, int(x2 - x1))
        steps = max(20, min(180, width // 5))
        for i in range(steps):
            t = i / max(1, steps - 1)
            color = blend(HEADER, RED, t / 0.14) if t < 0.14 else (blend(BLUE, HEADER, (t - 0.86) / 0.14) if t > 0.86 else blend(RED, BLUE, (t - 0.14) / 0.72))
            self.canvas.create_line(x1 + width * i / steps, y, x1 + width * (i + 1) / steps, y, fill=color, width=2)

    def draw_path_bar(self):
        w = self.canvas.winfo_width()
        x1, x2 = 6, min(650, w * 0.38)
        self.draw_gradient_line(x1, x2, 42)
        self.draw_gradient_line(x1, x2, 68)
        x = x1 + 112
        for idx, (_, title) in enumerate(self.breadcrumb):
            current = idx == len(self.breadcrumb) - 1
            tid = self.canvas.create_text(x, 55, text=title, font=("Segoe UI", 10, "bold") if current else ("Segoe UI", 10), fill=TEXT if current else BLUE, anchor="w")
            bbox = self.canvas.bbox(tid)
            tw = bbox[2] - bbox[0] if bbox else 70
            x += tw + 18
            if idx < len(self.breadcrumb) - 1:
                self.canvas.create_polygon(x, 48, x, 62, x + 7, 55, fill=RED, outline=RED)
                x += 24

    def draw_favorites_bar(self):
        w = self.canvas.winfo_width()
        x1, x2 = max(w * 0.68, w - 620), w - 8
        self.draw_gradient_line(x1, x2, 42)
        self.draw_gradient_line(x1, x2, 68)
        self.canvas.create_text(x1 + 18, 55, text="★", font=("Segoe UI", 16, "bold"), fill=GOLD, anchor="w")
        self.canvas.create_text(x1 + 48, 55, text="Favoriten", font=("Segoe UI", 10, "bold"), fill=TEXT, anchor="w")

    # ---------- controls ----------
    def draw_controls(self):
        if self.current_page == "main":
            self.draw_logout_control()
        else:
            self.draw_back_control()
        self.draw_close_control()

    def draw_back_control(self):
        frame = tk.Frame(self.root, bg=HEADER, cursor="hand2")
        arrow = tk.Label(frame, text="←", fg=RED, bg=HEADER, font=("Segoe UI", 14, "bold"), cursor="hand2")
        arrow.pack(side="left")
        text = tk.Label(frame, text="zurück", fg=BLUE, bg=HEADER, font=("Segoe UI", 10, "underline"), cursor="hand2")
        text.pack(side="left", padx=5)
        arrow.bind("<Button-1>", lambda e: self.go_back())
        text.bind("<Button-1>", lambda e: self.go_back())
        self.widget_items.append(frame)
        self.canvas.create_window(14, 7, window=frame, anchor="nw")

    def draw_logout_control(self):
        btn = IconButton(self.root, "Abmelden", "logout", self.logout, width=142, height=30, bg_color=self.current_tile_color() or BLUE, font=("Segoe UI", 9, "bold"))
        self.widget_items.append(btn)
        self.canvas.create_window(14, 7, window=btn, anchor="nw")

    def draw_close_control(self):
        label = tk.Label(self.root, text="X", bg=HEADER, fg=RED, font=("Segoe UI", 10, "bold"), cursor="hand2", relief="solid", bd=1, padx=4)
        label.bind("<Button-1>", lambda e: self.confirm_exit())
        self.widget_items.append(label)
        self.canvas.create_window(self.canvas.winfo_width() - 22, 7, window=label, anchor="ne")

    # ---------- logo ----------
    def draw_bottom_logo(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.intersport_logo:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.intersport_logo, 420, 55))
            self.image_refs.append(ph)
            self.canvas.create_image(w / 2, h - 24, image=ph)
        else:
            self.canvas.create_text(w / 2, h - 24, text="INTERSPORT", font=("Segoe UI", 22, "bold"), fill=BLUE)

    def draw_intersport_logo_above_footer(self, show_mini_logo=True):
        # Kompatibilität für Module
        return self.draw_bottom_logo()

    # ---------- helper: relief + descriptions ----------
    def draw_relief_line(self, canvas, y, x1, x2):
        for i in range(120):
            t = i / 119
            fade = 1 - abs(t - 0.5) * 2
            sx = x1 + (x2 - x1) * i / 120
            ex = x1 + (x2 - x1) * (i + 1) / 120
            canvas.create_line(sx, y, ex, y, fill=blend(BG, "#1F2933", 0.30 * fade), width=2)
            canvas.create_line(sx, y + 2, ex, y + 2, fill=blend(BG, WHITE, 0.65 * fade), width=1)

    def draw_module_description(self, canvas, module_id, x1, y_top, width):
        txt = MODULE_DESCRIPTIONS.get(module_id, "")
        if not txt:
            return
        canvas.create_text(
            x1 + DESCRIPTION_X_OFFSET,
            y_top + DESCRIPTION_Y_OFFSET,
            text=txt,
            anchor="nw",
            fill=DESCRIPTION_COLOR,
            font=DESCRIPTION_FONT,
            width=max(120, int(width) - 2 * DESCRIPTION_X_OFFSET),
            justify="left",
        )

    # ---------- Vorlage Modulmenü ----------
    def render_module_menu(self, modules, show_descriptions=True, full_width_reliefs=False, center_tiles=False, tile_scale=1.0):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()

        tile_w = int(max(290, min(390, int(w * 0.22))) * tile_scale)
        tile_h = int(max(120, min(160, int(h * 0.15))) * tile_scale)
        gap = max(18, int(h * 0.025))

        area_top = 132
        area_bottom = max(area_top + 260, h - 92)
        view_h = int(area_bottom - area_top)

        first_center_x = x_pct(w, 25)
        first_center_y = y_pct(h, 70)
        left_x = max(0, first_center_x - tile_w / 2 - 8)
        top = max(0, first_center_y - tile_h / 2 - area_top - 8)

        container = tk.Frame(self.root, bg=BG)
        self.widget_items.append(container)
        self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)

        scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0)
        scroll_canvas.place(x=left_x if not center_tiles else 0, y=0, width=w - (left_x if not center_tiles else 0) - 10, height=view_h)

        scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=scroll_canvas.yview,
            width=10,
            troughcolor=blend(BG, WHITE, 0.35),
            bg=BLUE,
            activebackground=darken(BLUE, 0.12),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scrollbar.place(x=w - 10, y=0, width=10, height=view_h)

        def yscroll_set(first, last):
            scrollbar.set(first, last)
            update_indicators()

        scroll_canvas.configure(yscrollcommand=yscroll_set)
        self.active_scroll_canvas = scroll_canvas

        content_h = top + len(modules) * (tile_h + gap) + 20
        scroll_canvas.configure(scrollregion=(0, 0, w, content_h))

        desc_x1 = 10 if full_width_reliefs else (tile_w + 90)
        desc_x2 = w - 34

        for idx, (title, module_id, cmd) in enumerate(modules):
            y = top + idx * (tile_h + gap)
            x_tile = (x_pct(w, 50) - tile_w / 2) if center_tiles else 0
            tile = Tile(scroll_canvas, self, module_id, title, cmd, favorite_enabled=not center_tiles, center_text=center_tiles)
            tile.resize_tile(tile_w, tile_h)
            self.focusable_tiles.append(tile)
            scroll_canvas.create_window(x_tile, y, window=tile, anchor="nw")

            if show_descriptions and not center_tiles:
                self.draw_module_description(scroll_canvas, module_id, desc_x1, y, desc_x2 - desc_x1)

            if idx < len(modules) - 1:
                self.draw_relief_line(scroll_canvas, y + tile_h + gap / 2, desc_x1, desc_x2)

        # Scroll indicators (positioned lower per screenshot)
        visible_idx = max(0, int((view_h - top + gap) / (tile_h + gap)) - 1)
        bottom_edge = area_top + top + (visible_idx + 1) * (tile_h + gap) - gap

        def can_scroll_up():
            first, _ = scroll_canvas.yview()
            return first > 0.001

        def can_scroll_down():
            _, last = scroll_canvas.yview()
            return last < 0.999

        def scroll_step(direction):
            step_units = max(1, int((tile_h + gap) / 20))
            scroll_canvas.yview_scroll(-step_units if direction == "up" else step_units, "units")
            update_indicators()

        up_arrow = ArrowIndicator(self.root, "up", lambda: scroll_step("up"), size=46)
        down_arrow = ArrowIndicator(self.root, "down", lambda: scroll_step("down"), size=46)
        self.widget_items.extend([up_arrow, down_arrow])

        tip_off = down_arrow.tip_offset_from_center()
        down_center_y = bottom_edge - tip_off
        up_center_y = down_center_y - 60

        ind_x = (left_x + tile_w + 52) if not center_tiles else x_pct(w, 50) + tile_w / 2 + 40
        self.canvas.create_window(ind_x, up_center_y, window=up_arrow, anchor="center")
        self.canvas.create_window(ind_x, down_center_y, window=down_arrow, anchor="center")

        def update_indicators():
            up_arrow.set_enabled(can_scroll_up())
            down_arrow.set_enabled(can_scroll_down())

        self._update_scroll_indicators = update_indicators
        update_indicators()

    # ---------- pages ----------
    def render_launch(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if self.banner_big:
            ph = ImageTk.PhotoImage(resize_keep_ratio(self.banner_big, 900, 230))
            self.image_refs.append(ph)
            self.canvas.create_image(w / 2, h * 0.235, image=ph)
        else:
            self.canvas.create_text(w / 2, h * 0.235, text="FiBu Mate", font=("Segoe UI", 46, "bold"), fill=TEXT)

        panel = tk.Frame(self.root, bg=BG)
        username_var = tk.StringVar(value=self.user_data.get("last_username_prefill", ""))
        tk.Label(panel, text="Benutzername", bg=BG, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(panel, bg=BG)
        row.pack(fill="x", pady=(0, 20))
        entry = tk.Entry(row, textvariable=username_var, font=("Segoe UI", 13), width=37, bg="#E8EEF5", fg=TEXT, relief="solid", bd=1)
        entry.pack(side="left", ipady=4)

        btn = IconButton(row, "Anmelden", None, lambda: self.login_user(username_var.get()), width=120, height=42, bg_color=BLUE, font=("Segoe UI", 9, "bold"))
        btn.pack(side="left", padx=(12, 0))

        IconButton(panel, "Benutzer anlegen", "userplus", self.create_user_popup, width=275, height=46, bg_color="#3D78AE").pack(anchor="center")
        self.widget_items.append(panel)
        self.canvas.create_window(x_pct(w, 50), y_pct(h, 39), window=panel, anchor="center")
        entry.focus_set()
        entry.bind("<Return>", lambda e: self.login_user(username_var.get()))

        self.draw_bottom_logo()
        self.draw_close_control()

    def create_user_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Benutzer anlegen")
        popup.configure(bg=BG)
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(False, False)

        frame = tk.Frame(popup, bg=BG)
        frame.pack(padx=28, pady=24)

        tk.Label(frame, text="Neuen Benutzer anlegen", bg=BG, fg=TEXT, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 14))
        username_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=username_var, font=("Segoe UI", 13), width=32, bg="#E8EEF5", relief="solid", bd=1)
        entry.pack(fill="x", pady=(0, 16))

        def save():
            if self.create_user(username_var.get()):
                popup.destroy()

        IconButton(frame, "Nutzernamen festlegen", "save", save, width=300, height=56, bg_color=self.current_tile_color() or BLUE).pack(anchor="w")
        entry.focus_set()

    def render_main_menu(self):
        tiles = [
            ("Datenaufbereitung", lambda: self.show_page("data_prep", "Datenaufbereitung"), False),
            ("Platzhalter 1", lambda: self.show_page("placeholder", "Platzhalter"), False),
            ("Platzhalter 2", lambda: self.show_page("placeholder", "Platzhalter"), False),
            ("Platzhalter 3", lambda: self.show_page("placeholder", "Platzhalter"), False),
            ("Platzhalter 4", lambda: self.show_page("placeholder", "Platzhalter"), False),
            ("Platzhalter 5", lambda: self.show_page("placeholder", "Platzhalter"), False),
            ("Informationen", lambda: self.show_page("information", "Informationen"), True),
            ("Einstellungen", lambda: self.show_page("settings", "Einstellungen"), True),
        ]
        xs, ys = [18, 39.333, 60.666, 82], [60, 38]
        i = 0
        for r in range(2):
            for c in range(4):
                title, cmd, corner = tiles[i]
                tile = Tile(self.root, self, f"main_{i}", title, cmd, favorite_enabled=False, corner=corner)
                tile_w = max(230, min(310, int(self.canvas.winfo_width() * 0.155)))
                tile_h = max(125, min(170, int(self.canvas.winfo_height() * 0.155)))
                tile.resize_tile(tile_w, tile_h)
                self.widget_items.append(tile)
                self.focusable_tiles.append(tile)
                self.canvas.create_window(x_pct(self.canvas.winfo_width(), xs[c]), y_pct(self.canvas.winfo_height(), ys[r]), window=tile, anchor="center")
                i += 1
        self.draw_bottom_logo()

    def render_data_prep_menu(self):
        modules = [
            ("Nike - PDF zu Excel", "nike_pdf_to_excel", lambda: self.open_tool("nike_pdf_to_excel")),
            ("Nike - Differenzabgleich: Rechnungen & SAP", "nike_zmir6_diff", lambda: self.open_tool("nike_zmir6_diff")),
            ("Nike - Differenzbericht Sales und Lager", "nike_sales_stock_diff", self.show_placeholder),
            ("Platzhaltemodul1", "placeholder_module_1", self.show_placeholder),
            ("Platzhaltemodul2", "placeholder_module_2", self.show_placeholder),
            ("Platzhaltemodul3", "placeholder_module_3", self.show_placeholder),
            ("Platzhaltemodul4", "placeholder_module_4", self.show_placeholder),
            ("Platzhaltemodul5", "placeholder_module_5", self.show_placeholder),
        ]
        self.render_module_menu(modules, show_descriptions=True)
        self.draw_bottom_logo()

    def render_settings_menu(self):
        items = [("Kachelfarben", "settings_tile_colors", lambda: self.show_page("tile_colors", "Kachelfarben", True))]

        if self.my_role() in (ROLE_ADMIN, ROLE_WAGNERM):
            items.append(("Berechtigungen verwalten", "settings_permissions", lambda: self.show_page("permissions_manage", "Berechtigungen verwalten", True)))

        # smaller centered tiles
        self.render_module_menu(items, show_descriptions=False, center_tiles=True, tile_scale=0.84)
        self.draw_bottom_logo()

    def render_tile_colors_menu(self):
        # not empty anymore
        frame = tk.Frame(self.root, bg=BG)
        self.widget_items.append(frame)

        tk.Label(frame, text="Standardfarben", font=("Segoe UI", 15, "bold"), bg=BG, fg=TEXT).grid(row=0, column=0, columnspan=6, pady=(0, 14), sticky="w")

        def make_swatch(name, color, r, c):
            sw = tk.Canvas(frame, width=120, height=74, bg=BG, highlightthickness=0, bd=0, cursor="hand2")
            sw.create_rectangle(6, 6, 114, 52, fill=color, outline=LINE, width=2)
            sw.create_text(60, 63, text=name, fill=TEXT, font=("Segoe UI", 9, "bold"))
            sw.bind("<Button-1>", lambda e, col=color: self.set_tile_color_and_bump(col))
            sw.grid(row=r, column=c, padx=8, pady=8)

        for idx, (name, color) in enumerate(COLOR_PALETTE):
            r = 1 + idx // 6
            c = idx % 6
            make_swatch(name, color, r, c)

        IconButton(frame, "Standard wiederherstellen", "cancel", self.reset_tile_color_and_bump, width=290, height=46, bg_color=BLUE).grid(row=4, column=0, columnspan=6, pady=(18, 6))
        IconButton(frame, "zurück", "logout", self.go_back, width=160, height=40, bg_color=BLUE).grid(row=5, column=0, columnspan=6, pady=(6, 0))

        self.canvas.create_window(self.canvas.winfo_width() / 2, y_pct(self.canvas.winfo_height(), 48), window=frame, anchor="center")
        self.draw_bottom_logo()

    def render_information_menu(self):
        items = [("Versionsverlauf", "info_versions", lambda: self.show_page("versions", "Versionsverlauf", True))]
        self.render_module_menu(items, show_descriptions=False)
        self.draw_bottom_logo()

    def render_versions_menu(self):
        # Layout like Vorlage Modulmenü but no tiles; full width relief lines
        history = self.load_version_history().get("entries", [])
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        area_top = 132
        area_bottom = max(area_top + 260, h - 92)
        view_h = int(area_bottom - area_top)

        container = tk.Frame(self.root, bg=BG)
        self.widget_items.append(container)
        self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)

        scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0)
        scroll_canvas.place(x=0, y=0, width=w - 10, height=view_h)

        scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=scroll_canvas.yview,
            width=10,
            troughcolor=blend(BG, WHITE, 0.35),
            bg=BLUE,
            activebackground=darken(BLUE, 0.12),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scrollbar.place(x=w - 10, y=0, width=10, height=view_h)

        def yscroll_set(first, last):
            scrollbar.set(first, last)

        scroll_canvas.configure(yscrollcommand=yscroll_set)
        self.active_scroll_canvas = scroll_canvas

        y = 20
        left = 24
        right = w - 34

        for e in history:
            ver = e.get("version", "")
            date = e.get("date", "")
            bullets = e.get("bullets", [])

            scroll_canvas.create_text(left, y, text=f"{ver}.{date}", anchor="nw", fill=TEXT, font=("Segoe UI", 12, "bold"))
            y += 22
            for b in bullets:
                scroll_canvas.create_text(left + 16, y, text=f"• {b}", anchor="nw", fill=TEXT2, font=("Segoe UI", 11), width=right - (left + 16))
                y += 18
            y += 12
            self.draw_relief_line(scroll_canvas, y, 10, right)
            y += 20

        scroll_canvas.configure(scrollregion=(0, 0, w, max(view_h, y + 40)))
        self.draw_bottom_logo()

    def render_permissions_manage_menu(self):
        if self.my_role() not in (ROLE_ADMIN, ROLE_WAGNERM):
            self.render_menu_text("Keine Berechtigung.")
            return

        self.permissions_dirty = False
        pending = {}

        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        area_top = 132
        area_bottom = max(area_top + 260, h - 92)
        view_h = int(area_bottom - area_top)

        container = tk.Frame(self.root, bg=BG)
        self.widget_items.append(container)
        self.canvas.create_window(0, area_top, window=container, anchor="nw", width=w, height=view_h)

        scroll_canvas = tk.Canvas(container, bg=BG, highlightthickness=0, bd=0)
        scroll_canvas.place(x=0, y=0, width=w - 10, height=view_h)

        scrollbar = tk.Scrollbar(
            container,
            orient="vertical",
            command=scroll_canvas.yview,
            width=10,
            troughcolor=blend(BG, WHITE, 0.35),
            bg=BLUE,
            activebackground=darken(BLUE, 0.12),
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        scrollbar.place(x=w - 10, y=0, width=10, height=view_h)

        def yscroll_set(first, last):
            scrollbar.set(first, last)

        scroll_canvas.configure(yscrollcommand=yscroll_set)
        self.active_scroll_canvas = scroll_canvas

        users = self.user_data.get("users", {})
        keys = sorted(users.keys())

        y = 20
        scroll_canvas.create_text(24, y, text="Benutzer", anchor="nw", fill=TEXT, font=("Segoe UI", 12, "bold"))
        scroll_canvas.create_text(w - 320, y, text="Berechtigung zuweisen", anchor="nw", fill=TEXT, font=("Segoe UI", 12, "bold"))
        y += 30
        self.draw_relief_line(scroll_canvas, y, 10, w - 34)
        y += 14

        def on_change(user_key, var, current_role):
            new_role = var.get()
            if user_key == SUPERUSER_KEY:
                return
            if new_role != current_role:
                pending[user_key] = new_role
            else:
                pending.pop(user_key, None)
            self.permissions_dirty = bool(pending)

        for k in keys:
            display = users[k].get("display_name", k)
            current_role = users[k].get("permission", ROLE_STANDARD)
            scroll_canvas.create_text(24, y, text=display, anchor="nw", fill=TEXT, font=("Segoe UI", 11))

            var = tk.StringVar(value=current_role)

            avail = [ROLE_STANDARD, ROLE_ADMIN, ROLE_WAGNERM]
            avail = [r for r in avail if self.can_assign_role(r)]
            if self.my_role() != ROLE_WAGNERM and ROLE_WAGNERM in avail:
                avail.remove(ROLE_WAGNERM)
            if k == SUPERUSER_KEY:
                avail = [ROLE_WAGNERM]
                var.set(ROLE_WAGNERM)

            opt = tk.OptionMenu(container, var, *avail)
            opt.config(bg=BG, fg=TEXT, highlightthickness=1, bd=0, relief="solid")
            opt["menu"].config(bg=BG, fg=TEXT)
            self.widget_items.append(opt)
            scroll_canvas.create_window(w - 290, y - 4, window=opt, anchor="nw")
            var.trace_add("write", lambda *_ , kk=k, v=var, cr=current_role: on_change(kk, v, cr))

            y += 48
            self.draw_relief_line(scroll_canvas, y, 10, w - 34)
            y += 10

        scroll_canvas.configure(scrollregion=(0, 0, w, max(view_h, y + 40)))

        def save_changes():
            for kk, rr in pending.items():
                users[kk]["permission"] = rr
            self.user_data["users"] = users
            self.save_user_data()
            self.permissions_dirty = False
            self.bump_version(["Änderung: Berechtigungen angepasst und gespeichert"]) 

        def discard_changes():
            self.permissions_dirty = False

        self._permissions_save = save_changes
        self._permissions_discard = discard_changes

        self.draw_bottom_logo()

    def ask_save_permissions_dialog(self):
        pop = tk.Toplevel(self.root)
        pop.title("Berechtigungen")
        pop.configure(bg=BG)
        pop.transient(self.root)
        pop.grab_set()
        pop.resizable(False, False)

        tk.Label(pop, text="Änderungen speichern?", bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(padx=18, pady=(16, 8))
        frame = tk.Frame(pop, bg=BG)
        frame.pack(padx=18, pady=(0, 16))

        def save():
            try:
                if hasattr(self, "_permissions_save"):
                    self._permissions_save()
            finally:
                pop.destroy()
                self.go_back()

        def discard():
            try:
                if hasattr(self, "_permissions_discard"):
                    self._permissions_discard()
            finally:
                pop.destroy()
                self.go_back()

        tk.Button(frame, text="✔ Speichern", command=save, bg="#16a34a", fg="white", bd=0, padx=14, pady=8, cursor="hand2").pack(side="left", padx=8)
        tk.Button(frame, text="✖ Verwerfen", command=discard, bg="#dc2626", fg="white", bd=0, padx=14, pady=8, cursor="hand2").pack(side="left", padx=8)

    def render_menu_text(self, text):
        lab = tk.Label(self.root, text=text, font=("Segoe UI", 16), bg=BG, fg=TEXT)
        self.widget_items.append(lab)
        self.canvas.create_window(x_pct(self.canvas.winfo_width(), 50), y_pct(self.canvas.winfo_height(), 60), window=lab, anchor="center")
        self.draw_bottom_logo()

    # ---------- tools ----------
    def render_external_tool(self, tool_id):
        try:
            module = importlib.import_module(TOOL_REGISTRY[tool_id]["module"])
            module = importlib.reload(module)
            module.render(self)
        except Exception as e:
            messagebox.showerror("FiBu Mate", f"Fehler beim Laden des Moduls:\n\n{TOOL_REGISTRY.get(tool_id, {}).get('title', tool_id)}\n\n{e}")
            self.draw_bottom_logo()

    def open_tool(self, tool_id):
        # transaction
        self.bump_version([f"Transaktion: Modul geöffnet ({TOOL_REGISTRY.get(tool_id, {}).get('title', tool_id)})"]) 
        self.show_page(f"tool:{tool_id}", TOOL_REGISTRY[tool_id]["title"], True)

    def show_placeholder(self):
        messagebox.showinfo("FiBu Mate", "Hinter diesem Widget entsteht gerade ein Modul.")

    # ---------- auth ----------
    def login_user(self, username):
        username = " ".join(str(username).strip().split())
        key = normalize_username(username)
        if not key or key not in self.user_data.get("users", {}):
            messagebox.showwarning("FiBu Mate", "Benutzer falsch - bitte Eingabe prüfen")
            return
        self.current_user_key = key
        self.current_user_display = self.user_data["users"][key].get("display_name", username)
        self.favorites = set(self.user_data["users"][key].get("favorites", []))
        self.user_data["last_username_prefill"] = self.current_user_display
        self.save_user_data()

        # always main menu
        self.page_history = []
        self.show_page("main", "Hauptmenü", add_to_history=False)

    def create_user(self, username):
        username = " ".join(str(username).strip().split())
        key = normalize_username(username)
        if not key:
            messagebox.showwarning("FiBu Mate", "Bitte einen Nutzernamen eingeben.")
            return False
        if key in self.user_data.get("users", {}):
            messagebox.showwarning("FiBu Mate", "Nutzername bereits vergeben")
            return False
        self.user_data.setdefault("users", {})[key] = {
            "display_name": username,
            "favorites": [],
            "auth": {"password_hash": None, "enabled": False},
            "permission": ROLE_WAGNERM if key == SUPERUSER_KEY else ROLE_STANDARD,
        }
        self.user_data["last_username_prefill"] = username
        self.save_user_data()
        self.login_user(username)
        return True

    def logout(self):
        self.current_user_key = None
        self.current_user_display = ""
        self.favorites = set()
        self.page_history = []
        self.show_page("launch", add_to_history=False)

    # ---------- tile color helpers ----------
    def set_tile_color_and_bump(self, color):
        if self.current_user_key:
            self.user_data["users"][self.current_user_key]["tile_color"] = color
            self.save_user_data()
        self.bump_version(["Transaktion: Kachelfarbe geändert"]) 
        self.render_page()

    def reset_tile_color_and_bump(self):
        if self.current_user_key:
            self.user_data["users"][self.current_user_key].pop("tile_color", None)
            self.save_user_data()
        self.bump_version(["Transaktion: Kachelfarbe zurückgesetzt"]) 
        self.render_page()

    # ---------- favorites ----------
    def toggle_favorite(self, tile_id):
        if tile_id in self.favorites:
            self.favorites.remove(tile_id)
        else:
            self.favorites.add(tile_id)
        if self.current_user_key:
            self.user_data["users"][self.current_user_key]["favorites"] = sorted(self.favorites)
            self.save_user_data()
        self.render_page()

    # ---------- focus/keys ----------
    def set_focused_tile(self, tile):
        if tile in self.focusable_tiles:
            self.focus_index = self.focusable_tiles.index(tile)

    def handle_escape(self, *_):
        if self.current_page != "launch":
            self.go_back()
        return "break"

    def handle_f1(self, *_):
        return "break"

    def handle_enter(self, *_):
        now_ms = int(datetime.now().timestamp() * 1000)
        if now_ms - self.last_page_change_ms < 250:
            return "break"
        if 0 <= self.focus_index < len(self.focusable_tiles):
            self.focusable_tiles[self.focus_index].on_keyboard_activate()
        return "break"

    def focus_next(self):
        if self.focusable_tiles:
            self.focus_index = (self.focus_index + 1) % len(self.focusable_tiles)
            self.focusable_tiles[self.focus_index].focus_set()

    def focus_previous(self):
        if self.focusable_tiles:
            self.focus_index = (self.focus_index - 1) % len(self.focusable_tiles)
            self.focusable_tiles[self.focus_index].focus_set()

    def handle_tab(self, *_):
        self.focus_next();
        return "break"

    def handle_shift_tab(self, *_):
        self.focus_previous();
        return "break"

    def handle_left(self, *_):
        self.focus_previous();
        return "break"

    def handle_right(self, *_):
        self.focus_next();
        return "break"

    def handle_up(self, *_):
        self.focus_previous();
        return "break"

    def handle_down(self, *_):
        self.focus_next();
        return "break"

    def confirm_exit(self):
        if messagebox.askyesno("FiBu Mate beenden", "Möchtest du FiBu Mate wirklich schließen?"):
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FiBuMateApp().run()
