import tkinter as tk
from tkinter import ttk
from json_loader import JsonLoader
import random

class StarMapApp:
    """Draws constellations from a JSON file on a canvas, with interactive edge blocking and constellation selector."""

    def __init__(self, json_path):
        self.root = tk.Tk()
        self.root.title("🌌 Mapa de Constelaciones (NASA Burro Edition)")
        self.root.geometry("750x750")
        self.root.configure(bg="black")

        # Frame superior con selector
        top_frame = tk.Frame(self.root, bg="black")
        top_frame.pack(pady=10)

        tk.Label(top_frame, text="Selecciona constelación:", bg="black", fg="white").pack(side="left", padx=5)

        self.selector = ttk.Combobox(top_frame, state="readonly", width=30)
        self.selector.pack(side="left")

        # Canvas principal
        self.canvas = tk.Canvas(self.root, width=600, height=600, bg="black")
        self.canvas.pack(padx=20, pady=10)

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

    def scale(self, x, y):
        """Escala coordenadas 0–200 → 0–600 px."""
        scale_factor = 3
        return x * scale_factor, y * scale_factor

    def draw_constellations(self, selected=None):
        """Dibuja todas las constelaciones o una sola, asegurando que las compartidas se dibujen y pinten correctamente."""
        self.canvas.delete("all")
        self.line_items.clear()
        self.line_colors.clear()

        # 1️⃣ Obtener constelaciones a mostrar
        consts_to_draw = (
            self.constellations if selected in (None, "Todas")
            else [c for c in self.constellations if c["name"] == selected]
        )

        # 🎨 Mapa global de colores por estrella (para evitar búsquedas repetidas)
        color_by_star = {}
        for i, c in enumerate(self.constellations):
            col = self.colors[i % len(self.colors)]
            for s in c["starts"]:
                color_by_star[s["id"]] = col

        # 2️⃣ Fase de dibujo de aristas
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

        # 3️⃣ Construir mapa global de estrellas a dibujar
        all_stars = {}
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                all_stars[star["id"]] = {"data": star, "color": color_by_star.get(star["id"], "white")}

        # 🔄 Asegurar que todas las estrellas referenciadas también estén en all_stars
        for constellation in consts_to_draw:
            for star in constellation["starts"]:
                for link in star["linkedTo"]:
                    target = self.loader.find_star_by_id(link["starId"])
                    if target and target["id"] not in all_stars:
                        tid = target["id"]
                        all_stars[tid] = {"data": target, "color": color_by_star.get(tid, "white")}

        # 4️⃣ Dibujar todas las estrellas
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
        panel.place(x=10, y=10, width=250, height=140)

        for i, (k, v) in enumerate(info.items()):
            tk.Label(panel, text=f"{k}: {v}", bg="black", fg="white", anchor="w").pack(anchor="w")

        self.blocked_label = tk.Label(panel, text="Caminos bloqueados: 0", bg="black", fg="orange", anchor="w")
        self.blocked_label.pack(anchor="w", pady=(5, 0))

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


if __name__ == "__main__":
    StarMapApp("data/Constellations.json")
