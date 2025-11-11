import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pygame
from src.core.burrito_runtime import BurroRuntimeEngine, StarEffect
from src.core.hypergiants import is_hypergiant, collect_hypergiants, list_jump_destinations, apply_hypergiant_effects


class StarMapAnimator:

    def __init__(self, canvas, loader, root, scale_func, burro=None, report_gen=None):
        self.canvas = canvas
        self.loader = loader
        self.root = root
        self.scale = scale_func
        self.burro_icon = None
        self.burro_image = None  # si tienes una imagen cargada
        self.burro = burro
        self.report_gen = report_gen
        self.hypergiants = collect_hypergiants(self.loader)

        try:
            base_dir = os.path.dirname(__file__)           # carpeta animations/
            assets_dir = os.path.normpath(os.path.join(base_dir, "..", "..", "assets"))
            img_path = os.path.join(assets_dir, "burro.png")
            if not os.path.exists(img_path):
                # intenta ruta relativa al working dir por compatibilidad
                img_path = os.path.join("assets", "burro.png")
            self.burro_image = ImageTk.PhotoImage(Image.open(img_path).resize((48, 48)))
        except Exception as e:
            print(f"⚠️ Error cargando imagen del burro ({img_path}): {e}")
            self.burro_image = None

        self.burro_icon = None

        self.engine = BurroRuntimeEngine(self.burro, on_update=self.actualizar_ui)
        self.current_star_id = 1  # se actualiza dinámicamente según el recorrido

    def actualizar_ui(self, estado):
        """Callback que actualiza la interfaz cuando el burro cambia."""
        print("🟢 Estado del burro actualizado:", estado)



    def animate_path(self, path, color="red", move_steps=20, step_delay=40):
        if not path or len(path) < 2:
            return

        # inicializar bandera de control
        self.stop_animation = False

        # Inicializar burro en la primera estrella (si no existe)
        if self.burro_icon is None:
            first_star = self.loader.find_star_by_id(path[0])
            if first_star:
                x0, y0 = self.scale(first_star["coordenates"]["x"], first_star["coordenates"]["y"])
                if self.burro_image:
                    self.burro_icon = self.canvas.create_image(x0, y0, image=self.burro_image)
                else:
                    self.burro_icon = self.canvas.create_oval(x0-6, y0-6, x0+6, y0+6, fill="white", outline="")

        burro = self.burro
        report = self.report_gen

        def move_burro(x1, y1, x2, y2, steps=move_steps, j=0, callback=None):
            if j >= steps or self.stop_animation:
                if callback and not self.stop_animation:
                    callback()
                return
            dx, dy = (x2 - x1) / steps, (y2 - y1) / steps
            if self.burro_icon:
                self.canvas.move(self.burro_icon, dx, dy)
            self.root.after(step_delay, lambda: move_burro(x1, y1, x2, y2, steps, j + 1, callback))

        def step(i):
            if i >= len(path) - 1 or self.stop_animation:
                # Si fue detenido por muerte, el callback encargado ya generará el reporte; si no, finalizar normal.
                if not self.stop_animation and report and burro:
                    path_report = report.finalize(
                        life_left_ly=burro.vida_restante,
                        end_reason="finished" if not burro.esta_muerto else "dead"
                    )
                    messagebox.showinfo("✅ Recorrido completado", f"Reporte guardado en:\n{path_report}")
                return

            cur_star = self.loader.find_star_by_id(path[i])
            next_star = self.loader.find_star_by_id(path[i + 1])
            if not cur_star or not next_star:
                step(i + 1)
                return

            x1, y1 = self.scale(cur_star["coordenates"]["x"], cur_star["coordenates"]["y"])
            x2, y2 = self.scale(next_star["coordenates"]["x"], next_star["coordenates"]["y"])

            cur_galaxy = cur_star.get("galaxy_id")
            next_galaxy = next_star.get("galaxy_id")

            def after_move():
                # dibujar línea
                self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3)

                # actualizar modelo y reportes
                if burro and report:
                    distancia_ly = ((x2 - x1)**2 + (y2 - y1)**2)**0.5 / 3
                    burro.viajar(distancia_ly)
                    energia_inicial = burro.energia
                    energia_consumida = burro.investigar(3.0, 1.5, 1.0)
                    burro.comer_en_estrella(3.0, 1.0)

                    report.log_hop(cur_star["id"], next_star["id"], distancia_ly, energia_consumida)
                    report.log_visit(
                        star_id=next_star["id"],
                        label=next_star["label"],
                        galaxy_id=None,
                        hypergiant=next_star.get("hypergiant", False),
                        grass_kg=burro.pasto_kg,
                        time_x=3.0,
                        energy_in_pct=energia_inicial,
                        energy_out_pct=burro.energia
                    )

                # Chequear hipergigante y aplicar buff
                from src.core.hypergiants import is_hypergiant, apply_hypergiant_effects, list_jump_destinations
                if is_hypergiant(next_star):
                    apply_hypergiant_effects(burro)
                    print(f"💥 Hipergigante! Energía={burro.energia:.1f}%, Pasto={burro.pasto_kg:.1f}kg")

                    # Opcional: listar destinos de salto
                    destinos = list_jump_destinations(
                        loader=self.loader,
                        current_star_id=next_star["id"],
                        current_galaxy_id = next_star.get("galaxy_id")
                    )
                    print("Destinos posibles para hipersalto:", destinos)



                # ---> Comprobar muerte
                if burro and burro.esta_muerto:
                    # detener animación y generar reporte final con motivo 'dead'
                    self.stop_animation = True

                    # Efecto visual: reemplazar burro por "tumba" (opcional)
                    if self.burro_icon:
                        # borramos icono y dibujamos una pequeña cruz en su lugar
                        coords = self.canvas.coords(self.burro_icon)
                        try:
                            self.canvas.delete(self.burro_icon)
                        except Exception:
                            pass
                        if coords:
                            cx, cy = coords[0], coords[1]
                            # cruz simple
                            size = 8
                            self.canvas.create_line(cx - size, cy - size, cx + size, cy + size, fill="white", width=2)
                            self.canvas.create_line(cx - size, cy + size, cx + size, cy - size, fill="white", width=2)
                        self.burro_icon = None

                    # finalizar reporte de forma definitiva
                    path_report = report.finalize(life_left_ly=burro.vida_restante, end_reason="dead")
                    messagebox.showerror("💀 El burro ha muerto", f"El burro murió en la estrella {next_star['label']}.\nReporte: {path_report}")

                    if burro.esta_muerto:
                        death_win = tk.Toplevel(self.root)
                        death_win.title("💀 BURRO MUERTO 💀")
                        death_win.geometry("400x220")
                        death_win.configure(bg="black")

                        label = tk.Label(
                            death_win,
                            text="💀 EL BURRO HA MUERTO 💀",
                            fg="red",
                            bg="black",
                            font=("Arial Black", 18)
                        )
                        label.pack(pady=25)

                        tk.Label(
                            death_win,
                            text=f"Energía final: {burro.energia:.1f}%\nVida restante: {burro.vida_restante:.2f} años luz",
                            fg="white",
                            bg="black",
                            font=("Consolas", 12)
                        ).pack(pady=10)

                        tk.Button(
                            death_win,
                            text="Cerrar",
                            command=death_win.destroy,
                            bg="gray20",
                            fg="white"
                        ).pack(pady=10)

                        # 🔥 Animación: parpadeo rojo
                        def blink():
                            current_color = label.cget("fg")
                            new_color = "darkred" if current_color == "red" else "red"
                            label.config(fg=new_color)
                            death_win.after(400, blink)

                        blink()

                        def play_death_sound():
                            try:
                                base_dir = os.path.dirname(__file__)
                                sound_path = os.path.normpath(os.path.join(base_dir, "..", "..", "assets", "sounds", "burro_muere.mp3"))
                                if not os.path.exists(sound_path):
                                    sound_path = os.path.join("assets", "sounds", "burro_muere.mp3")

                                pygame.mixer.init()
                                pygame.mixer.music.load(sound_path)
                                pygame.mixer.music.play()
                            except Exception as e:
                                print("⚠️ No se pudo reproducir el sonido de muerte:", e)

                        threading.Thread(target=play_death_sound, daemon=True).start()

                        step(i+1)

                    return

                # si no murió, mostrar ventana y continuar al siguiente paso
                self.show_burro_window(next_star, lambda: step(i + 1))

            # Solo mostrar ventana inicial antes del primer salto
            if i == 0:
                self.show_burro_window(cur_star, lambda: move_burro(x1, y1, x2, y2, callback=after_move))
            else:
                move_burro(x1, y1, x2, y2, callback=after_move)

        step(0)


    # (los demás métodos quedan igual; animate_burro / animate_hypergiants / show_burro_window...)
    def animate_burro(self, path, delay=400):
        """Simula al burro moviéndose automáticamente entre estrellas (no bloqueante)."""
        if not path or len(path) < 2:
            return

        burro_icon = None

        def move_step(i=0):
            nonlocal burro_icon
            if i >= len(path):
                return

            star = self.loader.find_star_by_id(path[i])
            if not star:
                return

            x, y = self.scale(star["coordenates"]["x"], star["coordenates"]["y"])

            if burro_icon is None:
                burro_icon = self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill="white", outline="")
            else:
                self.canvas.coords(burro_icon, x - 6, y - 6, x + 6, y + 6)

            # Destello
            self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#ff4c4c", outline="")

            self.root.after(delay, lambda: move_step(i + 1))

        move_step()

    def animate_hypergiants(self, interval=1200):
        """Hace parpadear las estrellas hipergigantes periódicamente."""
        for constellation in self.loader.constellations:
            for star in constellation["starts"]:
                if star.get("hypergiant", False):
                    x, y = self.scale(star["coordenates"]["x"], star["coordenates"]["y"])
                    radius = star["radius"] * 6
                    self.canvas.create_oval(
                        x - radius, y - radius, x + radius, y + radius,
                        fill="red", outline="", width=0
                    )
        self.root.after(interval, lambda: self.animate_hypergiants(interval))

    def show_burro_window(self, star, on_next):
        """Ventana para editar los efectos de la estrella visitada (acorde con StarEffect)."""
        win = tk.Toplevel(self.root)
        win.title("Efectos estelares 🌌")
        win.geometry("360x420")
        win.configure(bg="black")

        # Estado actual del burro (desde el motor)
        state = self.engine.state()

        # --- Título ---
        tk.Label(
            win, text=f"🌟 Estrella visitada: {star['label']}",
            fg="cyan", bg="black", font=("Arial", 14, "bold")
        ).pack(pady=(10, 5))

        # --- Datos no editables ---
        frame_info = tk.Frame(win, bg="black")
        frame_info.pack(pady=10)

        def add_info(label, value):
            tk.Label(frame_info, text=f"{label}: ", fg="white", bg="black", width=16, anchor="w").grid(sticky="w", row=add_info.row, column=0)
            tk.Label(frame_info, text=value, fg="lightgreen", bg="black", anchor="w").grid(sticky="w", row=add_info.row, column=1)
            add_info.row += 1
        add_info.row = 0

        add_info("Vida restante (ly)", f"{state['vida_restante']:.2f}")
        add_info("Energía actual (%)", f"{state['energia']:.2f}")
        add_info("Pasto actual (kg)", f"{state['pasto_kg']:.2f}")

        # --- Campos editables (efectos a aplicar) ---
        frame_edit = tk.LabelFrame(win, text="Cambios (ganados o perdidos)", fg="yellow", bg="black", padx=10, pady=10)
        frame_edit.pack(pady=(10, 10))

        tk.Label(frame_edit, text="Δ Edad (años-luz):", fg="white", bg="black").grid(row=0, column=0, sticky="e", padx=5, pady=3)
        edad_entry = tk.Entry(frame_edit, width=10)
        edad_entry.grid(row=0, column=1, pady=3)

        tk.Label(frame_edit, text="Δ Energía (%):", fg="white", bg="black").grid(row=1, column=0, sticky="e", padx=5, pady=3)
        energia_entry = tk.Entry(frame_edit, width=10)
        energia_entry.grid(row=1, column=1, pady=3)

        tk.Label(frame_edit, text="Δ Pasto (kg):", fg="white", bg="black").grid(row=2, column=0, sticky="e", padx=5, pady=3)
        pasto_entry = tk.Entry(frame_edit, width=10)
        pasto_entry.grid(row=2, column=1, pady=3)

        # Campo opcional para nota o descripción del efecto
        tk.Label(frame_edit, text="Nota:", fg="white", bg="black").grid(row=3, column=0, sticky="e", padx=5, pady=3)
        nota_entry = tk.Entry(frame_edit, width=20)
        nota_entry.grid(row=3, column=1, pady=3)

        # --- Acción Guardar y continuar ---
        def guardar_y_continuar():
            try:
                delta_vida = float(edad_entry.get() or 0)
                delta_energia = float(energia_entry.get() or 0)
                delta_pasto = float(pasto_entry.get() or 0)
                nota = nota_entry.get().strip()

                # Crear un StarEffect con los datos ingresados
                efecto = StarEffect(
                    vida_ly=delta_vida,
                    energia=delta_energia,
                    alimento=delta_pasto,
                    nota=nota
                )

                # Buscar la distancia entre la estrella actual y la siguiente
                distancia_ly = 0
                cur_star = self.loader.find_star_by_id(self.current_star_id)
                next_star = star  # 'star' es la estrella actual de la ventana

                if cur_star and next_star:
                    for link in cur_star.get("linkedTo", []):
                        if link["starId"] == next_star["id"]:
                            distancia_ly = link["distance"]
                            break

                # Aplicar el paso en el motor
                self.engine.apply_step(
                    from_star_id=self.current_star_id,
                    to_star_id=star["id"],
                    to_star_label=star["label"],
                    distancia_ly=distancia_ly,
                    effect=efecto
                )

            except ValueError:
                messagebox.showwarning("Error", "Por favor ingresa solo números válidos.")
                return

            # Cerrar ventana y continuar recorrido
            win.destroy()
            on_next()

        tk.Button(
            win, text="Guardar y continuar →", bg="green", fg="white",
            font=("Arial", 12, "bold"), command=guardar_y_continuar
        ).pack(pady=15)

        tk.Label(win, text="(Usa valores positivos o negativos según corresponda)", fg="gray", bg="black").pack(pady=(0, 10))
