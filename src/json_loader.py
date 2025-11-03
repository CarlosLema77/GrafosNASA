import json
from pathlib import Path

class JsonLoadError(Exception):
    """Custom exception for JSON loading errors."""
    pass

class JsonLoader:
    """Handles loading and validating the constellations JSON file."""

    REQUIRED_TOP_KEYS = {"constellations", "burroenergiaInicial", "estadoSalud", "pasto"}

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self._star_index = {}               # {id: star_object}
        self._star_to_constellations = {}   # {id: [constellation names]}

    def load(self):
        """Load and validate the JSON structure."""
        if not self.file_path.exists():
            raise JsonLoadError(f"Archivo no encontrado: {self.file_path}")

        try:
            with self.file_path.open("r", encoding="utf-8") as f:
                self.data = json.load(f)
        except json.JSONDecodeError as e:
            raise JsonLoadError(f"JSON inválido: {e}")

        missing = self.REQUIRED_TOP_KEYS - set(self.data.keys())
        if missing:
            raise JsonLoadError(f"Faltan claves principales: {missing}")

        consts = self.data.get("constellations")
        if not isinstance(consts, list):
            raise JsonLoadError("La clave 'constellations' debe ser una lista")

        self._star_index.clear()
        self._star_to_constellations.clear()

        # ✅ Registrar todas las estrellas reales
        for constellation in consts:
            if "name" not in constellation or "starts" not in constellation:
                raise JsonLoadError("Cada constelación debe tener 'name' y 'starts'")

            cname = constellation["name"]
            for star in constellation["starts"]:
                for key in ("id", "label", "coordenates", "linkedTo"):
                    if key not in star:
                        raise JsonLoadError(f"Estrella en {cname} falta clave '{key}'")

                coords = star["coordenates"]
                if "x" not in coords or "y" not in coords:
                    raise JsonLoadError(f"Estrella {star['id']} en {cname} falta coordenadas x/y")

                sid = int(star["id"])
                self._star_index[sid] = star
                self._star_to_constellations.setdefault(sid, []).append(cname)

        # ✅ Segunda pasada: registrar conexiones solo si la estrella de destino ya existe
        for constellation in consts:
            cname = constellation["name"]
            for star in constellation["starts"]:
                for link in star["linkedTo"]:
                    linked_id = int(link["starId"])
                    if linked_id in self._star_index:
                        # Solo agregar si la estrella enlazada ya pertenece a otra constelación
                        if cname not in self._star_to_constellations[linked_id]:
                            self._star_to_constellations[linked_id].append(cname)

        print("✅ Archivo JSON cargado y validado correctamente.")


    def get_constellations(self):
        """Return all constellations."""
        if self.data is None:
            raise JsonLoadError("JSON no cargado. Ejecuta load() primero.")
        return self.data["constellations"]

    def get_general_info(self):
        """Return general info (energy, health, etc)."""
        if self.data is None:
            raise JsonLoadError("JSON no cargado.")
        keys = ["burroenergiaInicial", "estadoSalud", "pasto", "startAge", "deathAge"]
        return {k: self.data.get(k) for k in keys}

    def find_star_by_id(self, star_id: int):
        """Find a star by ID."""
        return self._star_index.get(int(star_id))

    def find_shared_stars(self):
        """List of stars appearing in multiple constellations."""
        return [sid for sid, consts in self._star_to_constellations.items() if len(consts) > 1]

if __name__ == "__main__":
    loader = JsonLoader("data/Constellations.json")
    loader.load()
    print("Estrellas compartidas:", loader.find_shared_stars())

