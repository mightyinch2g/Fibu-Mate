import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import messagebox

TOOL_ID = "x001_sap_test"
TOOL_NAME = "X001 SAP - Test"

BG = "#EEF2F6"
TEXT = "#1F2933"


def draw_footer_logo(app):
    if hasattr(app, "draw_bottom_logo"):
        app.draw_bottom_logo()
    elif hasattr(app, "draw_intersport_logo_above_footer"):
        app.draw_intersport_logo_above_footer(show_mini_logo=False)


# -----------------------------
# Windows helpers (no pywin32)
# -----------------------------

def is_windows():
    return os.name == "nt"


def tasklist_lower():
    try:
        out = subprocess.check_output(["tasklist"], text=True, errors="ignore")
        return out.lower()
    except Exception:
        return ""


def is_sap_running():
    """Checks whether SAP GUI is already running (saplogon.exe or sapgui.exe)."""
    out = tasklist_lower()
    return ("saplogon.exe" in out) or ("sapgui.exe" in out)


def find_sap_exe():
    """Try to locate saplogon.exe."""
    candidates = [
        r"C:\\Program Files (x86)\\SAP\\FrontEnd\\SAPgui\\saplogon.exe",
        r"C:\\Program Files\\SAP\\FrontEnd\\SAPgui\\saplogon.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def start_saplogon():
    exe = find_sap_exe()
    if not exe:
        return False, "saplogon.exe wurde nicht gefunden (SAP GUI installiert?)."
    try:
        subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "SAP Logon wurde gestartet."
    except Exception as e:
        return False, f"SAP Logon konnte nicht gestartet werden: {e}"


def bring_sap_to_front(timeout_sec: float = 10.0):
    """Bring an existing SAP window (SAP Logon / SAP Easy Access) to foreground.

    Uses pure ctypes; no GUI scripting required.
    """
    if not is_windows():
        return False, "Nur unter Windows verfügbar."

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    EnumWindows = user32.EnumWindows
    EnumWindows.argtypes = [wintypes.WNDENUMPROC, wintypes.LPARAM]
    EnumWindows.restype = wintypes.BOOL

    IsWindowVisible = user32.IsWindowVisible
    IsWindowVisible.argtypes = [wintypes.HWND]
    IsWindowVisible.restype = wintypes.BOOL

    GetWindowTextW = user32.GetWindowTextW
    GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    GetWindowTextW.restype = ctypes.c_int

    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    GetWindowThreadProcessId.restype = wintypes.DWORD

    ShowWindow = user32.ShowWindow
    ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    ShowWindow.restype = wintypes.BOOL

    SetForegroundWindow = user32.SetForegroundWindow
    SetForegroundWindow.argtypes = [wintypes.HWND]
    SetForegroundWindow.restype = wintypes.BOOL

    BringWindowToTop = user32.BringWindowToTop
    BringWindowToTop.argtypes = [wintypes.HWND]
    BringWindowToTop.restype = wintypes.BOOL

    SW_RESTORE = 9

    # Titles commonly seen
    title_needles = [
        "sap logon",
        "saplogon",
        "sap easy access",
        "sap gui",
        "sap",
    ]

    best = {"hwnd": None, "title": ""}

    def find_once():
        best["hwnd"] = None
        best["title"] = ""

        @wintypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_proc(hwnd, lparam):
            if not IsWindowVisible(hwnd):
                return True
            buf = ctypes.create_unicode_buffer(512)
            GetWindowTextW(hwnd, buf, 512)
            title = (buf.value or "").strip()
            if not title:
                return True
            lower = title.casefold()
            if any(n in lower for n in title_needles):
                # Prefer more specific SAP-related titles
                score = 0
                if "sap logon" in lower or "saplogon" in lower:
                    score += 3
                if "easy access" in lower:
                    score += 2
                if "sap" in lower:
                    score += 1
                if best["hwnd"] is None or score > best.get("score", -1):
                    best["hwnd"] = hwnd
                    best["title"] = title
                    best["score"] = score
            return True

        EnumWindows(enum_proc, 0)

    deadline = time.time() + max(1.0, timeout_sec)
    while time.time() < deadline:
        find_once()
        if best["hwnd"]:
            try:
                ShowWindow(best["hwnd"], SW_RESTORE)
                BringWindowToTop(best["hwnd"])
                SetForegroundWindow(best["hwnd"])
                return True, f"SAP-Fenster aktiviert: {best['title']}"
            except Exception as e:
                return False, f"Konnte SAP-Fenster nicht aktivieren: {e}"
        time.sleep(0.25)

    return False, "Kein SAP-Fenster gefunden."


def render(app):
    frame = tk.Frame(app.root, bg=BG)

    tk.Label(frame, text=TOOL_NAME, bg=BG, fg=TEXT, font=("Segoe UI", 16, "bold")).pack(pady=(12, 6))
    tk.Label(
        frame,
        text=(
            "Dieses Modul prüft nur, ob SAP bereits geöffnet ist.\n"
            "• Wenn SAP läuft: SAP-Fenster in den Vordergrund.\n"
            "• Wenn SAP nicht läuft: SAP Logon starten und in den Vordergrund."
        ),
        bg=BG,
        fg=TEXT,
        font=("Segoe UI", 10),
        justify="left",
    ).pack(pady=(0, 12))

    status = tk.Label(frame, text="Bereit.", bg=BG, fg=TEXT, font=("Segoe UI", 10, "bold"))
    status.pack(pady=(0, 10))

    def run_check():
        if not is_windows():
            messagebox.showwarning("FiBu Mate", "Dieses Modul ist aktuell nur für Windows gedacht.")
            return

        if is_sap_running():
            status.config(text="SAP läuft – aktiviere Fenster …")
            ok, msg = bring_sap_to_front(timeout_sec=6.0)
            status.config(text=msg)
            if not ok:
                messagebox.showinfo("FiBu Mate", msg)
            return

        status.config(text="SAP läuft nicht – starte SAP Logon …")
        ok, msg = start_saplogon()
        status.config(text=msg)
        if not ok:
            messagebox.showerror("FiBu Mate", msg)
            return

        ok2, msg2 = bring_sap_to_front(timeout_sec=12.0)
        status.config(text=msg2 if ok2 else (msg + " (Fenster nicht gefunden)"))
        if not ok2:
            messagebox.showinfo("FiBu Mate", msg2)

    tk.Button(
        frame,
        text="SAP prüfen / aktivieren",
        command=run_check,
        bg="#004B93",
        fg="white",
        bd=0,
        padx=16,
        pady=10,
        cursor="hand2",
    ).pack(pady=(0, 8))

    app.widget_items.append(frame)
    app.canvas.create_window(app.canvas.winfo_width() / 2, app.canvas.winfo_height() * 0.45, window=frame, anchor="center")

    draw_footer_logo(app)
