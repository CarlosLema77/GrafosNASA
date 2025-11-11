# /ui/report_viewer.py
import json
import os
import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def open_report_window(root, reports_dir: str):
    """Abre una ventana moderna con los datos del reporte más reciente."""

    # Buscar último reporte
    candidates = sorted(
        glob.glob(os.path.join(reports_dir, "report_*.json")),
        key=os.path.getmtime,
        reverse=True
    )
    if not candidates:
        path = filedialog.askopenfilename(
            title="Selecciona un reporte JSON",
            filetypes=[("JSON files", "*.json")]
        )
        if not path:
            messagebox.showinfo("Info", "No se seleccionó ningún reporte.")
            return
    else:
        path = candidates[0]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo leer el reporte:\n{e}")
        return

    # --- Ventana principal ---
    win = tk.Toplevel(root)
    win.title(f"📊 Reporte — {os.path.basename(path)}")
    win.geometry("900x600")
    win.configure(bg="#0c0c0f")

    # --- Estilo moderno ---
    style = ttk.Style(win)
    style.theme_use("clam")

    style.configure("Treeview",
                    background="#1a1a1f",
                    foreground="white",
                    rowheight=25,
                    fieldbackground="#1a1a1f",
                    borderwidth=0)
    style.map("Treeview", background=[("selected", "#2a9df4")])

    style.configure("Treeview.Heading",
                    background="#2a2a35",
                    foreground="white",
                    font=("Segoe UI", 10, "bold"))

    # --- Encabezado principal ---
    header = tk.Frame(win, bg="#141419")
    header.pack(fill="x", pady=(8, 10))
    tk.Label(
        header,
        text="🌌 Reporte del Viaje del Burro",
        font=("Segoe UI", 16, "bold"),
        fg="#00ffcc",
        bg="#141419"
    ).pack()

    tk.Label(
        header,
        text=f"Archivo: {os.path.basename(path)}",
        fg="gray",
        bg="#141419",
        font=("Segoe UI", 9)
    ).pack()

    # --- Información general ---
    totals = data.get("totals", {})
    info_frame = tk.Frame(win, bg="#0c0c0f")
    info_frame.pack(fill="x", padx=15, pady=(0, 10))

    def make_info(label, value, col):
        tk.Label(info_frame, text=label, fg="#00b3ff", bg="#0c0c0f",
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=col, sticky="w", padx=10)
        tk.Label(info_frame, text=value, fg="white", bg="#0c0c0f",
                 font=("Segoe UI", 10)).grid(row=1, column=col, sticky="w", padx=10)

    make_info("Inicio", data.get("start_time", "—"), 0)
    make_info("Motivo fin", data.get("end_reason", "—"), 1)
    make_info("Vida restante (ly)", data.get("life_left_ly", "—"), 2)
    make_info("Distancia total (ly)", totals.get("total_distance_ly", 0), 3)
    make_info("Energía usada (%)", totals.get("total_energy_used_%", 0), 4)
    make_info("Pasto total (kg)", totals.get("total_grass_kg", 0), 5)

    # --- Sección: Visitas ---
    section_title(win, "⭐ Visitas a Estrellas")
    cols_v = ("star_id", "label", "galaxy_id", "hypergiant", "grass_eaten_kg", "invest_time_x", "energy_in_%", "energy_out_%")
    tree_v = make_table(win, cols_v)
    for v in data.get("visited_stars", []):
        tree_v.insert("", "end", values=tuple(v.get(k, "") for k in cols_v))

    # --- Sección: Hops ---
    section_title(win, "🪐 Saltos (Hops)")
    cols_h = ("from", "to", "distance_ly", "energy_used_%")
    tree_h = make_table(win, cols_h)
    for h in data.get("hops", []):
        tree_h.insert("", "end", values=tuple(h.get(k, "") for k in cols_h))

    # --- Botones inferiores ---
    footer = tk.Frame(win, bg="#0c0c0f")
    footer.pack(fill="x", pady=(10, 5))

    def open_other():
        p = filedialog.askopenfilename(
            title="Selecciona otro reporte JSON",
            filetypes=[("JSON files", "*.json")]
        )
        if not p:
            return
        win.destroy()
        open_report_window(root, os.path.dirname(p))

    modern_button(footer, "📂 Abrir otro reporte", open_other).pack(side="right", padx=10)
    modern_button(footer, "❌ Cerrar", win.destroy).pack(side="right", padx=10)


# --- Funciones auxiliares de diseño ---

def section_title(parent, text):
    tk.Label(
        parent,
        text=text,
        fg="#00ffcc",
        bg="#0c0c0f",
        font=("Segoe UI", 13, "bold")
    ).pack(anchor="w", padx=15, pady=(10, 5))


def make_table(parent, columns):
    frame = tk.Frame(parent, bg="#0c0c0f")
    frame.pack(fill="both", padx=10, pady=(0, 10))
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=8)
    for c in columns:
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=110, anchor="center")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(fill="x")
    return tree


def modern_button(parent, text, command):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg="#2a9df4",
        fg="white",
        activebackground="#007acc",
        activeforeground="white",
        relief="flat",
        padx=10,
        pady=4,
        font=("Segoe UI", 10, "bold")
    )

    # efecto hover
    def on_enter(e): btn.config(bg="#007acc")
    def on_leave(e): btn.config(bg="#2a9df4")
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn
