from pathlib import Path

# Rutas del proyecto (independientes de la carpeta desde donde se ejecute)
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "state.json"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# Parámetros del scraping
TIKTOK_URL = "https://www.tiktok.com"
MAX_VIDEOS = 10
MAX_COMENTARIOS = 15
MAX_REPOSTS = 20                # Videos de la pestaña "Compartidos" que se guardan
DESCARGAR_TRANSCRIPCIONES = True  # Subtítulos automáticos (lo que se dice en el video)
TIMEOUT_MS = 90000          # Margen amplio para resolver CAPTCHAs manualmente
PAUSA_ENTRE_VIDEOS_MS = 2500

# Evasión nativa inyectada directamente al motor de Chromium
CHROMIUM_ARGS = ["--disable-blink-features=AutomationControlled"]

# Parámetros del análisis de personalidad (Big Five)
# (las palabras están en app/lexico.py y la fórmula en app/personalidad.py)
# Mínimo de textos escritos por la persona (bio, descripciones, transcripciones,
# sus comentarios) para intentar el análisis. Con menos, el resultado sería adivinar.
MIN_TEXTOS_PROPIOS = 5
# Plan B: si no hay suficientes textos propios pero sí este número de compartidos
# con texto útil (3 o más palabras que no sean #fyp, #parati...), el análisis se hace
# con base en los compartidos, con confianza "baja" en todos los rasgos.
MIN_REPOSTS_RESPALDO = 5
