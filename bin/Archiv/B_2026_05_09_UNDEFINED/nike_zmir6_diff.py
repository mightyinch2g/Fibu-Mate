
import tkinter as tk

TOOL_ID = "nike_zmir6_diff"
TOOL_NAME = "Nike - Differenzabgleich: Rechnungen & SAP"

BG = "#EEF2F6"
TEXT = "#1F2933"


def draw_footer_logo(app):
    if hasattr(app, "draw_bottom_logo"):
        app.draw_bottom_logo()
    elif hasattr(app, "draw_intersport_logo_above_footer"):
        app.draw_intersport_logo_above_footer(show_mini_logo=False)


def render(app):
    label = tk.Label(
        app.root,
        text="Nike - Differenzabgleich: Rechnungen & SAP\n\nDieses Modul wird vorbereitet.",
        font=("Segoe UI", 16, "bold"),
        bg=BG,
        fg=TEXT,
        justify="center",
    )
    app.widget_items.append(label)
    app.canvas.create_window(
        app.canvas.winfo_width() / 2,
        app.canvas.winfo_height() * 0.48,
        window=label,
        anchor="center",
    )
    draw_footer_logo(app)
