import tkinter as tk
from PIL import Image, ImageTk
import os

class StarMapAnimator:
    """Controla las animaciones visuales del mapa estelar y del burro."""

    def __init__(self, canvas, loader, root, scale_func):
        self.canvas = canvas
        self.loader = loader
        self.root = root
        self.scale = scale_func
        self.is_paused = False

        # Cargar imagen del burro usando ruta absoluta relativa a este archivo
        self.burro_image = None
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

    def animate_path(self, path, color="red", move_steps=20, step_delay=40):
        """
        Anima el recorrido del burro paso a paso, mostrando la ventana de info en
        cada estrella, esperando 'Siguiente' y luego moviéndose y dibujando la línea.
        """
        if not path or len(path) < 2:
            return

        # Inicializar burro en la primera estrella (si no existe)
        if self.burro_icon is None:
            first_star = self.loader.find_star_by_id(path[0])
            if first_star:
                x0, y0 = self.scale(first_star["coordenates"]["x"], first_star["coordenates"]["y"])
                if self.burro_image:
                    self.burro_icon = self.canvas.create_image(x0, y0, image=self.burro_image)
                else:
                    # fallback: un óvalo blanco pequeño
                    self.burro_icon = self.canvas.create_oval(x0-6, y0-6, x0+6, y0+6, fill="white", outline="")

        def move_burro(x1, y1, x2, y2, steps=move_steps, i=0, callback=None):
            """Mueve suavemente el burro de (x1,y1) a (x2,y2) sin acumulación incorrecta."""
            if i >= steps:
                if callback:
                    callback()
                return

            # desplazamiento relativo por paso
            dx, dy = (x2 - x1) / steps, (y2 - y1) / steps
            if self.burro_icon:
                self.canvas.move(self.burro_icon, dx, dy)

            # ⚠️ IMPORTANTE: no sumar dx/dy a x1,y1 — Tkinter ya lo hace internamente
            self.root.after(step_delay, lambda: move_burro(x1, y1, x2, y2, steps, i + 1, callback))


        def step(i):
            """
            Lógica por paso:
             1) mostrar popup con info de la estrella actual (path[i])
             2) al presionar 'Siguiente' -> mover burro a next
             3) cuando termine movimiento -> dibujar la línea que conecta actual->next y llamar step(i+1)
            """
            if i >= len(path) - 1:
                # recorrido completado: puedes mostrar un popup o efecto final
                print("✅ Recorrido completado.")
                return

            # estrella actual y siguiente
            cur_star = self.loader.find_star_by_id(path[i])
            next_star = self.loader.find_star_by_id(path[i + 1])
            if not cur_star or not next_star:
                # si falta info, saltar
                step(i + 1)
                return

            # coords (pixel)
            x1, y1 = self.scale(cur_star["coordenates"]["x"], cur_star["coordenates"]["y"])
            x2, y2 = self.scale(next_star["coordenates"]["x"], next_star["coordenates"]["y"])

            # 1) Mostrar la ventana con la info del burro para la estrella actual.
            #    Al pulsar 'Siguiente', ejecutamos el callback que mueve y luego dibuja la línea.
            def on_next():
                # 2) mover el burro suavemente hasta next; cuando termine, dibujar línea y avanzar
                def after_move():
                    # 3) Dibujar la línea entre actual y siguiente en color elegido
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=3)
                    # Avanzar al siguiente paso
                    step(i + 1)

                move_burro(x1, y1, x2, y2, steps=move_steps, i=0, callback=after_move)

            # show_burro_window bloqueante; cuando usuario pulsa, on_next será llamado
            self.show_burro_window(cur_star, on_next)

        # iniciar en 0
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

    def show_burro_window(self, star_data, step_callback):
        """Muestra info del burro y espera a que el usuario presione 'Siguiente'."""
        win = tk.Toplevel(self.root)
        win.title("Burro Explorador 🐴")
        win.geometry("300x250")
        win.configure(bg="black")

        tk.Label(win, text="Burro Explorador", fg="orange", bg="black",
                 font=("Arial", 14, "bold")).pack(pady=(10, 5))

        # si se cargó la imagen, mostrar un pequeño retrato en la ventana
        if self.burro_image:
            lbl = tk.Label(win, image=self.burro_image, bg="black")
            lbl.image = self.burro_image
            lbl.pack()

        tk.Label(win, text=f"Estrella actual: {star_data['label']}", fg="white", bg="black").pack(pady=5)
        tk.Label(win, text=f"ID: {star_data['id']}", fg="white", bg="black").pack(pady=5)
        tk.Label(win, text=f"Posición: ({star_data['coordenates']['x']}, {star_data['coordenates']['y']})",
                 fg="white", bg="black").pack(pady=5)

        tk.Button(
            win,
            text="➡ Siguiente estrella",
            bg="green",
            fg="white",
            relief="flat",
            command=lambda: (win.destroy(), step_callback())
        ).pack(pady=(20, 0))

        win.transient(self.root)
        win.grab_set()
        self.root.wait_window(win)
