from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.almacenamiento import (
    cargar_datos, cargar_personalidad, guardar_datos, guardar_personalidad, limpiar_username,
)
from app.config import STATIC_DIR
from app.personalidad import analizar_personalidad
from app.scraper import extraer_perfil

# Inicializamos la aplicación FastAPI
app = FastAPI(title="TikTok Scraper API", description="API para extracción de datos de TikTok y análisis Big Five.")


@app.get("/", include_in_schema=False)
def front():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/datos/{username}")
def obtener_datos_guardados(username: str):
    # Devuelve el último JSON extraído sin volver a abrir el navegador
    username_limpio = limpiar_username(username)
    datos = cargar_datos(username_limpio)
    if datos is None:
        raise HTTPException(status_code=404, detail=f"No hay datos guardados de @{username_limpio}")
    return datos


@app.get("/scrapi/{username}")
def extraer_datos_tiktok(username: str):
    username_limpio = limpiar_username(username)
    datos_perfil = extraer_perfil(username_limpio)
    ruta = guardar_datos(datos_perfil)
    return {
        "estado": "éxito",
        "mensaje": f"Datos extraídos correctamente en data/{ruta.name}",
        "usuario": username_limpio,
        "datos": datos_perfil,
    }


@app.get("/analizar/{username}")
def analizar_personalidad_usuario(username: str):
    # Analiza los datos YA GUARDADOS (no abre el navegador). Así se puede repetir
    # el análisis sin volver a scrapear, lo que es más rápido y evita bloqueos de TikTok.
    username_limpio = limpiar_username(username)
    datos = cargar_datos(username_limpio)
    if datos is None:
        raise HTTPException(
            status_code=404,
            detail=f"Primero extrae los datos de @{username_limpio} con /scrapi/{username_limpio}",
        )

    analisis = analizar_personalidad(datos)
    guardar_personalidad(analisis)
    return analisis


@app.get("/personalidad/{username}")
def obtener_personalidad_guardada(username: str):
    # Devuelve el último análisis guardado sin volver a calcularlo
    username_limpio = limpiar_username(username)
    analisis = cargar_personalidad(username_limpio)
    if analisis is None:
        raise HTTPException(status_code=404, detail=f"No hay análisis de personalidad guardado de @{username_limpio}")
    return analisis
