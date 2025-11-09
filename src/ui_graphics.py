import tkinter as tk
from tkinter import ttk
from json_loader import JsonLoader
import random

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "algorythmes", "bellman_ford"))

from bellman_algor import BellmanFord, build_graph_from_loader, NegativeCycleError


class StarMapApp:
    """Draws constellations from a JSON file on a canvas, with interactive edge blocking and constellation selector."""

    def __init__(self, json_path):
        self.root = tk.Tk()
        self.root.title("Mapa de Constelaciones (NASA Burro Edition)")
        self.root.geometry("920x800")
        self.root.configure(bg="black")

        # Frame superior con selector
        tk.Label(self.root, text="Selecciona constelación:", bg="black", fg="white").place(x=150, y=20)

        self.selector = ttk.Combobox(self.root, state="readonly", width=30)
        self.selector.place(x=290, y=18)

        # Canvas principal
        self.canvas = tk.Canvas(self.root, width=700, height=720, bg="black")
        self.canvas.place(x=6, y=50)

        # Cargar datos
        self.loader = JsonLoader(json_path)
        self.loader.load()
        self.constellations = self.loader.get_constellations()
        self.shared_stars = self.loader.find_shared_stars()

        # Colores y estructuras
        self.colors = ["cyan", "yellow", "orange", "violet", "lime", "white"]
        random.shuffle(self.colors)
        self.line_items = {}
        self.line_colors = {}
        self.blocked_paths = set()

        # Rellenar selector
        names = [c["name"] for c in self.constellations]
        self.selector["values"] = ["Todas"] + names
        self.selector.set("Todas")

        # Evento de selección
        self.selector.bind("<<ComboboxSelected>>", self.on_select_constellation)

        # Dibujar mapa inicial
        self.draw_constellations()

        # Mostrar info general
        self.show_info_panel()

        # Clic en líneas
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        self.root.mainloop()

    def open_path_window(self):
            """Abre una ventana para seleccionar origen y destino, y ejecutar Bellman-Ford."""
            import tkinter.messagebox as msg

            win = tk.Toplevel(self.root)
            win.title("Recorrido del Burro (Bellman-Ford)")
            win.geometry("350x220")
            win.configure(bg="black")

            tk.Label(win, text="Selecciona estrella origen:", fg="white", bg="black").pack(pady=(15, 5))
            origin_combo = ttk.Combobox(win, width=25, state="readonly")

            tk.Label(win, text="Selecciona estrella destino:", fg="white", bg="black").pack(pady=(10, 5))
            target_combo = ttk.Combobox(win, width=25, state="readonly")

            all_stars = []
            for c in self.constellations:
                for s in c["starts"]:
                    all_stars.append((s["id"], s["label"]))

            origin_combo["values"] = [f"{sid} - {label}" for sid, label in all_stars]
            target_combo["values"] = [f"{sid} - {label}" for sid, label in all_stars]

            origin_combo.pack()
            target_combo.pack()

            def run_bellman():
                if not origin_combo.get() or not target_combo.get():
                    msg.showwarning("Advertencia", "Selecciona origen y destino.")
                    return

                try:
                    source_id = int(origin_combo.get().split(" - ")[0])
                    target_id = int(target_combo.get().split(" - ")[0])

                    # Construir el grafo respetando bloqueos
                    nodes, edges = build_graph_from_loader(self.loader, self.blocked_paths)

                    # Ejecutar Bellman-Ford
                    bf = BellmanFord(nodes, edges)
                    dist, prev = bf.run(source_id)
                    path = bf.rebuild_path(prev, target_id)

                    # Mostrar resultado
                    msg.showinfo("Recorrido exitoso", f"Camino: {path}\nDistancia total: {dist[target_id]:.2f}")

                    # 🔥 Dibujar el camino en rojo
                    self.highlight_path(path)

                except NegativeCycleError:
                    msg.showerror("Error", "Se detectó un ciclo negativo.")
                except Exception as e:
                    msg.showerror("Error", f"Ocurrió un problema:\n{e}")

            tk.Button(win, text="Ejecutar Recorrido", bg="green", fg="white", command=run_bellman).pack(pady=20)

    def highlight_path(self, path):
        """Resalta el recorrido en el canvas."""
        for i in range(len(path) - 1):
            pair = tuple(sorted((path[i], path[i + 1])))
            for line, p in self.line_items.items():
                if p == pair:
                    self.canvas.itemconfig(line, fill="red", width=4)

    def scale(self, x, y):
        """Escala coordenadas 0–200 → 0–600 px."""
        scale_factor = 3
        return x * scale_factor, y * scale_factor

    def draw_constellations(self, selected=None):
        """Dibuja todas las constelaciones o una sola, asegurando que las compartidas se dibujen y pinten correctamente."""
        self.canvas.delete("all")
        self.line_items.clear()
        self.line_colors.clear()

        # Obtener constelaciones a mostrar
        consts_to_draw = (
            self.constellations if selected in (None, "Todas")
            else [c for c in self.constellations if c["name"] == selected]
        )

        # Mapa global de colores por estrella (para evitar búsquedas repetidas)
        color_by_star = {}
        for i, c in enumerate(self.constellations):
            col = self.colors[i % len(self.colors)]
            for s in c["starts"]:
                color_by_star[s["id"]] = col

        # Fase de dibujo de aristas
        for i, constellation in enumerate(consts_to_draw):
            color = self.colors[i % len(self.colors)]
            for star in constellation["starts"]:
                x1, y1 = self.scale(star["coordenates"]["x"], star["coordenates"]["y"])
                for link in star["linkedTo"]:
                    target = self.loader.find_star_by_id(link["starId"])
                    if target:
                        x2, y2 = self.scale(target["coordenates"]["x"], target["coordenates"]["y"])
                        line = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2)
                        pair = tuple(sorted((star["id"], link["starId"])))
                        self.line_items[line] = pair
                        self.line_colors[line] = color

        # Construir mapa global de estrellas a dibujar
        all_stars = {}
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                all_stars[star["id"]] = {"data": star, "color": color_by_star.get(star["id"], "white")}

        # Asegurar que todas las estrellas referenciadas también estén en all_stars
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                for link in star["linkedTo"]:
                    target = self.loader.find_star_by_id(link["starId"])
                    if target and target["id"] not in all_stars:
                        tid = target["id"]
                        all_stars[tid] = {"data": target, "color": color_by_star.get(tid, "white")}

        #Dibujar todas las estrellas
        for sid, info in all_stars.items():
            star = info["data"]
            x, y = self.scale(star["coordenates"]["x"], star["coordenates"]["y"])
            radius = star["radius"] * 5

            fill_color = "red" if sid in self.shared_stars else info["color"]

            self.canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=fill_color, outline=""
            )
            self.canvas.create_text(x + 10, y, text=star["label"], fill="white", anchor="w")



    def show_info_panel(self):
        """Panel lateral con información general."""
        info = self.loader.get_general_info()
        panel = tk.LabelFrame(self.root, text="Información general", fg="white", bg="black", padx=10, pady=10)
        panel.place(x=715, y=20, width=200, height=752)

        for i, (k, v) in enumerate(info.items()):
            tk.Label(panel, text=f"{k}: {v}", bg="black", fg="white", anchor="w").pack(anchor="w")

        self.blocked_label = tk.Label(panel, text="Caminos bloqueados: 0", bg="black", fg="orange", anchor="w")
        self.blocked_label.pack(anchor="w", pady=(5, 0))
        
        """Botón para configuracion de estrellas"""
        config_btn = tk.Button(
            panel,
            text = "Configurar Estrellas",
            bg = "white",
            fg = "gray",
            command = self.open_star_config_window
        )
        config_btn.pack(anchor = "w", pady = (10,0), fill = "x")

        config_btn.pack(anchor = "w", pady = (10,0), fill = "x")
        path_btn = tk.Button(
            panel,
            text="Ejecutar Recorrido",
            bg="green",
            fg="white",
            command=self.open_path_window
        )
        path_btn.pack(anchor="w", pady=(5, 0), fill="x")

    def on_canvas_click(self, event):
        """Detecta clic sobre una línea y alterna su estado."""
        item = self.canvas.find_closest(event.x, event.y)[0]

        if item in self.line_items:
            pair = self.line_items[item]
            if pair in self.blocked_paths:
                self.blocked_paths.remove(pair)
                original_color = self.line_colors.get(item, "white")
                self.canvas.itemconfig(item, fill=original_color, dash=(), width=2)
            else:
                self.blocked_paths.add(pair)
                self.canvas.itemconfig(item, fill="gray", dash=(5, 3), width=3)

            self.blocked_label.config(text=f"Caminos bloqueados: {len(self.blocked_paths)}")

    def on_select_constellation(self, event):
        """Redibuja el mapa según la constelación seleccionada."""
        selected = self.selector.get()
        self.draw_constellations(selected)


    def export_blocked_paths(self):
        """Devuelve los caminos bloqueados."""
        return list(self.blocked_paths)
    
    def open_star_config_window(self):
        """Abre una ventana para configurar valores de cada estrella (energía y tiempo)."""
        import os, json

        config_win = tk.Toplevel(self.root)
        config_win.title("Configuración de Estrellas")
        config_win.geometry("450x600")
        config_win.configure(bg="black")

        # Si existe un JSON previo, lo cargamos para mantener los datos actualizados
        star_values_path = os.path.join(os.getcwd(), "data", "star_values.json")
        saved_values = {}
        if os.path.exists(star_values_path):
            try:
                with open(star_values_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_values = {int(star["id"]): star for star in data}
            except Exception as e:
                print("⚠️ No se pudo cargar star_values.json:", e)

        # Tabla principal
        columns = ("id", "label", "energia", "tiempo")
        tree = ttk.Treeview(config_win, columns=columns, show="headings", height=15)

        for col in columns:
            tree.heading(col, text=col.capitalize())
            tree.column(col, width=100 if col != "label" else 140, anchor="center")

        tree.pack(padx=10, pady=10, fill="both", expand=True)

        # Cargar estrellas (usando valores guardados si existen)
        for constellation in self.constellations:
            for star in constellation["starts"]:
                sid = int(star["id"])
                existing = saved_values.get(sid, {})
                tree.insert("", "end", values=(
                    sid,
                    star["label"],
                    existing.get("energia", star.get("energia", 0)),
                    existing.get("tiempo", star.get("tiempo", 10))
                ))

        # Campos de edición
        edit_frame = tk.Frame(config_win, bg="black")
        edit_frame.pack(pady=5)

        tk.Label(edit_frame, text="Energía:", fg="white", bg="black").grid(row=0, column=0, padx=5)
        energia_entry = tk.Entry(edit_frame, width=8)
        energia_entry.grid(row=0, column=1)

        tk.Label(edit_frame, text="Tiempo:", fg="white", bg="black").grid(row=0, column=2, padx=5)
        tiempo_entry = tk.Entry(edit_frame, width=8)
        tiempo_entry.grid(row=0, column=3)

        # Al seleccionar una fila, mostrar los valores
        def on_select(event):
            selected = tree.selection()
            if selected:
                values = tree.item(selected[0], "values")
                energia_entry.delete(0, tk.END)
                tiempo_entry.delete(0, tk.END)
                energia_entry.insert(0, values[2])
                tiempo_entry.insert(0, values[3])

        tree.bind("<<TreeviewSelect>>", on_select)

        # Guardar cambios en la tabla (sin exportar aún)
        def save_changes():
            selected = tree.selection()
            if not selected:
                return
            new_energia = energia_entry.get()
            new_tiempo = tiempo_entry.get()

            tree.item(selected[0], values=(
                tree.item(selected[0], "values")[0],  # id
                tree.item(selected[0], "values")[1],  # label
                new_energia,
                new_tiempo
            ))

        save_btn = tk.Button(config_win, text="Guardar Cambios", command=save_changes, bg="gray20", fg="white")
        save_btn.pack(pady=5)

        # Exportar todos los valores a JSON
        def export_values():
            try:
                data_to_save = []
                for item in tree.get_children():
                    vals = tree.item(item, "values")
                    sid = int(vals[0])
                    label = str(vals[1])
                    energia = float(vals[2])
                    tiempo = float(vals[3])
                    data_to_save.append({
                        "id": sid,
                        "label": label,
                        "energia": energia,
                        "tiempo": tiempo
                    })

                os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
                out_path = os.path.join(os.getcwd(), "data", "star_values.json")

                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data_to_save, f, indent=4, ensure_ascii=False)

                from tkinter import messagebox
                messagebox.showinfo("Exportado", f"✅ Valores guardados en:\n{out_path}")
                print("✅ Valores de estrellas guardados en", out_path)

            except Exception as e:
                from tkinter import messagebox
                messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}")
                print("Error guardando star_values.json:", e)

        export_btn = tk.Button(
            config_win,
            text="💾 Exportar a JSON",
            command=export_values,
            bg="green",
            fg="white"
        )
        export_btn.pack(pady=5)






if __name__ == "__main__":
    StarMapApp("data/Constellations.json")
