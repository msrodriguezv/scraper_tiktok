import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from playwright.sync_api import sync_playwright

# Inicializamos la aplicación FastAPI
app = FastAPI(title="TikTok Scraper API", description="API para extracción de datos de TikTok.")

@app.get("/", include_in_schema=False)
def front():
    return FileResponse("index.html")

@app.get("/datos/{username}")
def obtener_datos_guardados(username: str):
    # Devuelve el último JSON extraído sin volver a abrir el navegador
    username_limpio = username.lower().replace(" ", "").replace("@", "")
    nombre_archivo = f"datos_tiktok_{username_limpio}.json"
    if not os.path.exists(nombre_archivo):
        raise HTTPException(status_code=404, detail=f"No hay datos guardados de @{username_limpio}")
    with open(nombre_archivo, encoding="utf-8") as f:
        return json.load(f)

@app.get("/scrapi/{username}")
def extraer_datos_tiktok(username: str):
    # --- SANITIZACIÓN DE ENTRADA (Recomendación de Jordi) ---
    # 1. Convertir todo a minúsculas
    # 2. Eliminar espacios en blanco
    # 3. Quitar el '@' si el usuario lo pone, para evitar duplicados en la URL
    username_limpio = username.lower().replace(" ", "").replace("@", "")
    # --------------------------------------------------------

    with sync_playwright() as p:
        # Evasión nativa inyectada directamente al motor de Chromium
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # --- INTERRUPTOR DE NAVEGACIÓN ---
        context = browser.new_context(storage_state="state.json")
        # context = browser.new_context() # MODO INVITADO
        
        page = context.new_page()
        page.set_default_timeout(90000)
        datos_perfil = {"username": username_limpio, "videos": []}

        print(f"Navegando al perfil de @{username_limpio}...")
        page.goto(f"https://www.tiktok.com/@{username_limpio}", wait_until="domcontentloaded")
        
        try:
            datos_perfil["seguidores"] = page.locator('[data-e2e="followers-count"]').inner_text()
            datos_perfil["seguidos"] = page.locator('[data-e2e="following-count"]').inner_text()
        except Exception:
            print("Aviso: No se extrajeron las métricas del perfil.")

        page.wait_for_selector('[data-e2e="user-post-item"] a', timeout=90000)
        page.wait_for_timeout(2000)
        items_videos = page.locator('[data-e2e="user-post-item"]')

        # TikTok responde HTTP 403 al cargar /video/... directamente con page.goto().
        # Por eso abrimos cada video haciendo clic en la cuadrícula del perfil
        # (navegación interna de la SPA) y lo cerramos para volver al perfil.
        for i in range(min(items_videos.count(), 10)):
            item = items_videos.nth(i)
            url = item.locator("a").first.get_attribute("href")
            if not url or "/video/" not in url:
                continue

            video_data = {"url": url, "comentarios": []}

            # Las vistas solo se muestran en la miniatura del perfil
            try:
                video_data["vistas"] = item.locator('[data-e2e="video-views"]').inner_text(timeout=5000)
            except Exception:
                pass

            try:
                item.locator("a").first.click()
                page.wait_for_selector('[data-e2e="browse-like-count"]', timeout=30000)
            except Exception:
                print(f"Aviso: no se pudo abrir el video {url}")
                continue

            try:
                video_data["likes"] = page.locator('[data-e2e="browse-like-count"]').inner_text()
                video_data["num_comentarios"] = page.locator('[data-e2e="browse-comment-count"]').inner_text()
            except Exception:
                pass

            try:
                page.wait_for_selector('[data-e2e="comment-level-1"]', timeout=5000)
                comentarios_html = page.locator('[data-e2e="comment-level-1"]').all()
                for comentario in comentarios_html[:15]:
                    texto = comentario.inner_text()
                    video_data["comentarios"].append(texto.replace("\n", " - "))
            except Exception:
                video_data["comentarios"].append("Sin comentarios o deshabilitados")

            datos_perfil["videos"].append(video_data)

            # Cerrar el visor y volver a la cuadrícula del perfil
            try:
                page.locator('[data-e2e="browse-close"]').click()
                page.wait_for_selector('[data-e2e="browse-like-count"]', state="detached", timeout=15000)
            except Exception:
                page.goto(f"https://www.tiktok.com/@{username_limpio}", wait_until="domcontentloaded")
                page.wait_for_selector('[data-e2e="user-post-item"] a', timeout=90000)
            page.wait_for_timeout(2500)

        nombre_archivo = f"datos_tiktok_{username_limpio}.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(datos_perfil, f, ensure_ascii=False, indent=4)
            
        browser.close()
        
        return {"estado": "éxito", "mensaje": f"Datos extraídos correctamente en {nombre_archivo}", "usuario": username_limpio, "datos": datos_perfil}