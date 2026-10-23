import json

from app.config import DATA_DIR


def limpiar_username(username: str) -> str:
    # --- SANITIZACIÓN DE ENTRADA ---
    # 1. Convertir todo a minúsculas
    # 2. Eliminar espacios en blanco
    # 3. Quitar el '@' si el usuario lo pone, para evitar duplicados en la URL
    return username.lower().replace(" ", "").replace("@", "")


# --- Rutas de los archivos en data/ ---
# Cada usuario tiene dos archivos: los datos extraídos y su análisis de personalidad.
# Se guardan por separado para poder repetir el análisis sin volver a scrapear.

def ruta_datos(username: str):
    return DATA_DIR / f"datos_tiktok_{username}.json"


def ruta_personalidad(username: str):
    return DATA_DIR / f"personalidad_{username}.json"


# --- Lectura y escritura genéricas de JSON ---

def _guardar_json(ruta, contenido: dict):
    DATA_DIR.mkdir(exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        # ensure_ascii=False conserva tildes y emojis legibles en el archivo
        json.dump(contenido, f, ensure_ascii=False, indent=4)
    return ruta


def _cargar_json(ruta):
    # Devuelve None si el archivo todavía no existe
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# --- Funciones que usa la API ---

def guardar_datos(datos_perfil: dict):
    return _guardar_json(ruta_datos(datos_perfil["username"]), datos_perfil)


def cargar_datos(username: str):
    return _cargar_json(ruta_datos(username))


def guardar_personalidad(analisis: dict):
    return _guardar_json(ruta_personalidad(analisis["username"]), analisis)


def cargar_personalidad(username: str):
    return _cargar_json(ruta_personalidad(username))
