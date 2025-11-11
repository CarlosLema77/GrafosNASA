import tkinter as tk
from tkinter import ttk, messagebox
import random

# Importar componentes del núcleo
from src.core.json_loader import JsonLoader
from src.core.graph_utils import build_graph_from_loader, get_path_edges
from src.algorythmes.bellman_ford.bellman_algor import BellmanFord, NegativeCycleError


class StarMapApp:
    """Interfaz gráfica principal del Mapa de Constelaciones (NASA Burro Edition)."""

    def __init__(self, json_path: str):
        # --- Configuración base ---
        self.root = tk.Tk()
        self.root.title("Mapa de Constelaciones (NASA Burro Edition)")
        self.root.geometry("920x800")
        self.root.configure(bg="black")

        # --- Datos y estructuras ---
        self.loader = JsonLoader(json_path)
        self.loader.load()
        self.constellations = self.loader.get_constellations()
        self.shared_stars = self.loader.find_shared_stars()
        self.blocked_paths = set()

        self.colors = ["cyan", "yellow", "orange", "violet", "lime", "white"]
        random.shuffle(self.colors)
        self.line_items = {}
        self.line_colors = {}

        # Colores y estructuras
        self.colors = ["cyan", "yellow", "orange", "violet", "lime", "white", "magenta", "gold", "deepskyblue"]
        random.shuffle(self.colors)
        self.line_items = {}
        self.line_colors = {}
        self.blocked_paths = set()

        # 🔹 Asignar un color fijo a cada constelación
        self.constellation_colors = {}
        for i, c in enumerate(self.constellations):
            self.constellation_colors[c["name"]] = self.colors[i % len(self.colors)]

        # --- UI superior ---
        tk.Label(self.root, text="Selecciona constelación:", bg="black", fg="white").place(x=150, y=20)

        self.selector = ttk.Combobox(self.root, state="readonly", width=30)
        self.selector.place(x=290, y=18)

        names = [c["name"] for c in self.constellations]
        self.selector["values"] = ["Todas"] + names
        self.selector.set("Todas")
        self.selected_constellation = "Todas"
        self.selector.bind("<<ComboboxSelected>>", self.on_select_constellation)

        # --- Canvas principal ---
        self.canvas = tk.Canvas(self.root, width=700, height=720, bg="black")
        self.canvas.place(x=6, y=50)
        self.canvas.bind("<Button-1>", self.on_canvas_click)


        # --- Panel lateral ---
        self.show_info_panel()

        # --- Dibujar mapa inicial ---
        self.draw_constellations()

        self.root.mainloop()

    # -------------------------------------------------------------------------
    # 🔹 Panel lateral
    # -------------------------------------------------------------------------
    def show_info_panel(self):
        info = self.loader.get_general_info()

        panel = tk.LabelFrame(
            self.root,
            text="Información general",
            fg="white",
            bg="black",
            padx=10,
            pady=10
        )
        panel.place(x=715, y=20, width=200, height=752)

        for k, v in info.items():
            tk.Label(panel, text=f"{k}: {v}", bg="black", fg="white", anchor="w").pack(anchor="w")

        self.blocked_label = tk.Label(panel, text="Caminos bloqueados: 0", bg="black", fg="orange", anchor="w")
        self.blocked_label.pack(anchor="w", pady=(5, 0))

        tk.Button(
            panel,
            text="Configurar Estrellas",
            bg="green",
            fg="white",
            command=self.open_star_config_window
        ).pack(anchor="w", pady=(10, 0), fill="x")

        tk.Button(
            panel,
            text="Ejecutar Recorrido",
            bg="green",
            fg="white",
            command=self.open_path_window
        ).pack(anchor="w", pady=(5, 0), fill="x")
    def scale(self, x, y):
        """Escala coordenadas 0–200 → 0–600 px."""
        return x * 3, y * 3

    def draw_constellations(self, selected=None):
        """Dibuja todas las constelaciones o una específica."""
        self.canvas.delete("all")
        self.line_items.clear()
        self.line_colors.clear()

        # ✅ Dibuja el plano cartesiano antes de las constelaciones
        self.draw_grid()

        # Filtrar constelaciones a dibujar
        consts_to_draw = (
            self.constellations if selected in (None, "Todas")
            else [c for c in self.constellations if c["name"] == selected]
        )

        # Mapa global de colores por estrella (usando el color fijo)
        color_by_star = {}
        for c in self.constellations:
            color = self.constellation_colors.get(c["name"], "white")
            for s in c["starts"]:
                color_by_star[s["id"]] = color

        # --- Fase de dibujo de aristas ---
        for constellation in consts_to_draw:
            const_color = self.constellation_colors.get(constellation["name"], "white")
            for star in constellation["starts"]:
                x1, y1 = self.scale(star["coordenates"]["x"], star["coordenates"]["y"])
                for link in star["linkedTo"]:
                    target = self.loader.find_star_by_id(link["starId"])
                    if target:
                        x2, y2 = self.scale(target["coordenates"]["x"], target["coordenates"]["y"])
                        pair = tuple(sorted((star["id"], link["starId"])))

                        # 🔹 Si el camino está bloqueado, aplicar estilo visual distinto
                        if pair in self.blocked_paths:
                            line = self.canvas.create_line(
                                x1, y1, x2, y2,
                                fill="gray", dash=(5, 3), width=3
                            )
                        else:
                            line = self.canvas.create_line(
                                x1, y1, x2, y2,
                                fill=const_color, width=2
                            )

                        self.line_items[line] = pair
                        self.line_colors[line] = const_color

        # --- Dibujar estrellas ---
        all_stars = {}
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                all_stars[star["id"]] = {
                    "data": star,
                    "color": color_by_star.get(star["id"], "white")
                }

        # Asegurar que todas las estrellas referenciadas también estén en all_stars
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                for link in star["linkedTo"]:
                    target = self.loader.find_star_by_id(link["starId"])
                    if target and target["id"] not in all_stars:
                        tid = target["id"]
                        all_stars[tid] = {
                            "data": target,
                            "color": color_by_star.get(tid, "white")
                        }

        # --- Dibujar nodos (estrellas) ---
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


    def draw_grid(self, step=20, size=235):
        """Dibuja un plano cartesiano 200x200 con ejes y cuadrícula."""
        scale_factor = 3
        canvas_size = size * scale_factor
        half = canvas_size // 2

        # Limpiar cuadrícula anterior
        # (solo si quieres borrar líneas viejas del grid)
        # self.canvas.delete("grid")

        # Fondo gris suave (opcional)
        self.canvas.create_rectangle(0, 0, canvas_size, canvas_size, fill="black", outline="", tags="grid")

        # Líneas de cuadrícula
        for i in range(0, size + 1, step):
            x = i * scale_factor
            y = i * scale_factor
            # Líneas horizontales y verticales (simétricas en ambos lados del eje)
            self.canvas.create_line(0, y, canvas_size, y, fill="#333333", dash=(2, 2), tags="grid")
            self.canvas.create_line(x, 0, x, canvas_size, fill="#333333", dash=(2, 2), tags="grid")

        # Ejes centrales
        self.canvas.create_line(0, half, canvas_size, half, fill="red", width=2, tags="grid")  # Eje X
        self.canvas.create_line(half, 0, half, canvas_size, fill="red", width=2, tags="grid")  # Eje Y

        # Etiquetas de ejes
        self.canvas.create_text(canvas_size - 15, half - 10, text="X", fill="red", font=("Arial", 10, "bold"), tags="grid")
        self.canvas.create_text(half + 10, 10, text="Y", fill="red", font=("Arial", 10, "bold"), tags="grid")

        # Etiqueta del origen
        self.canvas.create_text(half + 15, half + 15, text="(0,0)", fill="white", font=("Arial", 8), tags="grid")


    # Interacciones
    def on_canvas_click(self, event):
        """Alterna el bloqueo de una arista al hacer clic."""
        item = self.canvas.find_closest(event.x, event.y)[0]
        if item not in self.line_items:
            return

        pair = self.line_items[item]
        if pair in self.blocked_paths:
            self.blocked_paths.remove(pair)
        else:
            self.blocked_paths.add(pair)

        self.blocked_label.config(text=f"Caminos bloqueados: {len(self.blocked_paths)}")

        # Redibujar constelaciones (respetando bloqueos)
        self.draw_constellations(self.selected_constellation)

    def on_select_constellation(self, _event):
        selected = self.selector.get()
        self.selected_constellation = selected
        self.draw_constellations(selected)

    # 🔹 Bellman-Ford
    def open_path_window(self):
        win = tk.Toplevel(self.root)
        win.title("Recorrido del Burro (Bellman-Ford)")
        win.geometry("350x220")
        win.configure(bg="black")

        origin_combo, target_combo = self._create_path_selector_ui(win)

        if origin_combo["values"]:
            origin_combo.set(origin_combo["values"][0])
            target_combo.set(target_combo["values"][-1])

        tk.Button(
            win, text="Ejecutar Recorrido", bg="green", fg="white",
            command=lambda: self._run_bellman(win, origin_combo, target_combo)
        ).pack(pady=20)

    def _create_path_selector_ui(self, win):
        stars = self.get_filtered_stars()
        tk.Label(win, text="Selecciona estrella origen:", fg="white", bg="black").pack(pady=(15, 5))
        origin = ttk.Combobox(win, width=25, state="readonly")
        origin["values"] = [f"{sid} - {label}" for sid, label in stars]
        origin.pack()

        tk.Label(win, text="Selecciona estrella destino:", fg="white", bg="black").pack(pady=(10, 5))
        target = ttk.Combobox(win, width=25, state="readonly")
        target["values"] = [f"{sid} - {label}" for sid, label in stars]
        target.pack()

        return origin, target

    def _run_bellman(self, _win, origin_combo, target_combo):
        if not origin_combo.get() or not target_combo.get():
            messagebox.showwarning("Advertencia", "Selecciona origen y destino.")
            return

        try:
            source = int(origin_combo.get().split(" - ")[0])
            target = int(target_combo.get().split(" - ")[0])
            nodes, edges = build_graph_from_loader(self.loader, self.blocked_paths)
            bf = BellmanFord(nodes, edges)
            dist, prev = bf.run(source)
            path = bf.rebuild_path(prev, target)
            messagebox.showinfo("Recorrido exitoso", f"Camino: {path}\nDistancia total: {dist[target]:.2f}")
            self.highlight_path(path)
        except NegativeCycleError:
            messagebox.showerror("Error", "Se detectó un ciclo negativo.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def highlight_path(self, path):
        for pair in get_path_edges(path):
            for line, edge in self.line_items.items():
                if edge == pair:
                    self.canvas.itemconfig(line, fill="red", width=4)

    # Configuración de estrellas

    def open_star_config_window(self):
        """Ventana para editar timeToEat y amountOfEnergy."""
        config = tk.Toplevel(self.root)
        config.title("Configuración de Estrellas")
        config.geometry("450x600")
        config.configure(bg="black")

        columns = ("id", "label", "timeToEat", "amountOfEnergy")
        tree = ttk.Treeview(config, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col.capitalize())
            tree.column(col, width=100 if col != "label" else 140, anchor="center")
        tree.pack(padx=10, pady=10, fill="both", expand=True)

        for sid, label in self.get_filtered_stars():
            star = self.loader.find_star_by_id(sid)
            if star:
                tree.insert("", "end", values=(
                    sid, label,
                    star.get("timeToEat", 0),
                    star.get("amountOfEnergy", 0)
                ))

        # --- Campos de edición ---
        frame = tk.Frame(config, bg="black")
        frame.pack(pady=5)
        tk.Label(frame, text="Tiempo:", fg="white", bg="black").grid(row=0, column=0, padx=5)
        t_entry = tk.Entry(frame, width=8)
        t_entry.grid(row=0, column=1)
        tk.Label(frame, text="Energía:", fg="white", bg="black").grid(row=0, column=2, padx=5)
        e_entry = tk.Entry(frame, width=8)
        e_entry.grid(row=0, column=3)

        def on_select(_):
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0], "values")
                t_entry.delete(0, tk.END)
                e_entry.delete(0, tk.END)
                t_entry.insert(0, vals[2])
                e_entry.insert(0, vals[3])

        tree.bind("<<TreeviewSelect>>", on_select)

        def save_changes():
            sel = tree.selection()
            if not sel:
                return
            sid, label, *_ = tree.item(sel[0], "values")
            tree.item(sel[0], values=(sid, label, t_entry.get(), e_entry.get()))

        tk.Button(config, text="Guardar Cambios", bg="gray20", fg="white", command=save_changes).pack(pady=5)

        def export_to_json():
            try:
                updated = {
                    int(tree.item(item, "values")[0]): {
                        "timeToEat": float(tree.item(item, "values")[2]),
                        "amountOfEnergy": float(tree.item(item, "values")[3]),
                    }
                    for item in tree.get_children()
                }
                self.loader.update_star_values(updated)
                self.loader.save()
                messagebox.showinfo("✅ Éxito", "Los valores fueron guardados en el JSON.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron guardar los cambios:\n{e}")

        tk.Button(config, text="💾 Guardar en JSON", bg="green", fg="white", command=export_to_json).pack(pady=10)

    # Utilidades
    def get_filtered_stars(self):
        """Devuelve las estrellas visibles según la constelación seleccionada."""
        selected_name = getattr(self, "selected_constellation", "Todas")

        if selected_name in ("Todas", None):
            stars = {}
            for c in self.constellations:
                for s in c["starts"]:
                    stars[int(s["id"])] = s["label"]
            return sorted(stars.items(), key=lambda x: x[1])

        selected = next((c for c in self.constellations if c["name"] == selected_name), None)
        if not selected:
            return []

        stars_in_selected = {int(s["id"]): s["label"] for s in selected["starts"]}

        for sid in list(stars_in_selected.keys()):
            star_obj = self.loader.find_star_by_id(sid)
            if not star_obj:
                continue
            for link in star_obj.get("linkedTo", []):
                linked_id = int(link["starId"])
                if linked_id in self.shared_stars:
                    shared_star = self.loader.find_star_by_id(linked_id)
                    if shared_star:
                        stars_in_selected[linked_id] = shared_star["label"]

        return sorted(stars_in_selected.items(), key=lambda x: x[1])


if __name__ == "__main__":
    StarMapApp("data/Constellations.json")
