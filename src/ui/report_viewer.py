# /ui/report_viewer.py
import json
import os
import glob
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def open_report_window(root, reports_dir: str):
    """Abre una ventana que muestra el último reporte o permite elegir uno."""
    # Buscar el último report_*.json en reports_dir
    candidates = sorted(
        glob.glob(os.path.join(reports_dir, "report_*.json")),
        key=os.path.getmtime,
        reverse=True
    )
    if not candidates:
        # Si no hay, pedir al usuario seleccionar un JSON
        path = filedialog.askopenfilename(
            title="Selecciona un reporte JSON",
            filetypes=[("JSON files","*.json")]
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

    win = tk.Toplevel(root)
    win.title(f"Reporte — {os.path.basename(path)}")
    win.geometry("800x520")
    win.configure(bg="black")

    # Totales arriba
    totals = data.get("totals", {})
    frame_top = tk.Frame(win, bg="black")
    frame_top.pack(fill="x", padx=10, pady=(10, 5))

    tk.Label(frame_top, text=f"Inicio: {data.get('start_time','')}", fg="white", bg="black").grid(row=0, column=0, sticky="w", padx=4)
    tk.Label(frame_top, text=f"Motivo fin: {data.get('end_reason','')}", fg="white", bg="black").grid(row=0, column=1, sticky="w", padx=12)
    tk.Label(frame_top, text=f"Vida restante (ly): {data.get('life_left_ly','')}", fg="white", bg="black").grid(row=0, column=2, sticky="w", padx=12)

    tk.Label(frame_top, text=f"Distancia total (ly): {totals.get('total_distance_ly',0)}", fg="white", bg="black").grid(row=1, column=0, sticky="w", padx=4)
    tk.Label(frame_top, text=f"Energía usada (%): {totals.get('total_energy_used_%',0)}", fg="white", bg="black").grid(row=1, column=1, sticky="w", padx=12)
    tk.Label(frame_top, text=f"Pasto total (kg): {totals.get('total_grass_kg',0)}", fg="white", bg="black").grid(row=1, column=2, sticky="w", padx=12)
    tk.Label(frame_top, text=f"Tiempo inv. total (X): {totals.get('total_time_x',0)}", fg="white", bg="black").grid(row=1, column=3, sticky="w", padx=12)

    # Tabla de visitas
    tk.Label(win, text="Visitas a estrellas", fg="white", bg="black").pack(anchor="w", padx=10)
    cols_visits = ("star_id", "label", "galaxy_id", "hypergiant", "grass_eaten_kg", "invest_time_x", "energy_in_%", "energy_out_%")
    tree_v = ttk.Treeview(win, columns=cols_visits, show="headings", height=10)
    for c in cols_visits:
        tree_v.heading(c, text=c)
        tree_v.column(c, width=110, anchor="center")
    tree_v.pack(fill="x", padx=10, pady=(4,10))
    for v in data.get("visited_stars", []):
        tree_v.insert("", "end", values=tuple(v.get(k,"") for k in cols_visits))

    # Tabla de hops
    tk.Label(win, text="Saltos (hops)", fg="white", bg="black").pack(anchor="w", padx=10)
    cols_hops = ("from", "to", "distance_ly", "energy_used_%")
    tree_h = ttk.Treeview(win, columns=cols_hops, show="headings", height=6)
    for c in cols_hops:
        tree_h.heading(c, text=c)
        tree_h.column(c, width=140, anchor="center")
    tree_h.pack(fill="x", padx=10, pady=(4,10))
    for h in data.get("hops", []):
        tree_h.insert("", "end", values=tuple(h.get(k,"") for k in cols_hops))

    # Botón abrir otro reporte
    def open_other():
        p = filedialog.askopenfilename(
            title="Selecciona otro reporte JSON",
            filetypes=[("JSON files","*.json")]
        )
        if not p:
            return
        win.destroy()
        open_report_window(root, os.path.dirname(p))

    tk.Button(win, text="Abrir otro reporte…", command=open_other, bg="gray20", fg="white").pack(pady=6)
