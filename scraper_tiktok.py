import asyncio
import json
from playwright.async_api import async_playwright

async def extraer_datos_tiktok(username):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(storage_state="state.json")
        page = await context.new_page()
        
        page.set_default_timeout(90000)
        datos_perfil = {"username": username, "videos": []}

        print(f"Navegando al perfil de @{username}...")
        await page.goto(f"https://www.tiktok.com/@{username}", wait_until="domcontentloaded")
        
        try:
            datos_perfil["seguidores"] = await page.locator('[data-e2e="followers-count"]').inner_text()
            datos_perfil["seguidos"] = await page.locator('[data-e2e="following-count"]').inner_text()
            print(f"Métricas -> Seguidores: {datos_perfil['seguidores']} | Seguidos: {datos_perfil['seguidos']}")
        except Exception:
            print("Aviso: No se extrajeron las métricas del perfil.")

        await page.wait_for_selector('[data-e2e="user-post-item"]', timeout=10000)
        elementos_videos = await page.locator('[data-e2e="user-post-item"] a').all()
        
        urls_videos = []
        for el in elementos_videos:
            url = await el.get_attribute("href")
            if url and "/video/" in url and url not in urls_videos:
                urls_videos.append(url)
            if len(urls_videos) == 10:
                break
                
        print(f"Se encontraron {len(urls_videos)} videos. Entrando a extraer métricas y comentarios...")

        for url in urls_videos:
            print(f"Intentando entrar a: {url}")
            try:
                # El bloque try envuelve el intento de entrar al video. 
                # Si TikTok lanza el error HTTP, saltará automáticamente al except.
                await page.goto(url, wait_until="domcontentloaded")
            except Exception as e:
                print("TikTok bloqueó temporalmente el acceso a este video. Saltando al siguiente...")
                continue # Le dice al bot que ignore el error y siga con el siguiente video de la lista

            video_data = {"url": url, "comentarios": []}
            
            try:
                video_data["likes"] = await page.locator('[data-e2e="like-count"]').inner_text()
                video_data["vistas"] = await page.locator('[data-e2e="video-views"]').inner_text() 
            except Exception:
                pass
                
            try:
                await page.wait_for_selector('[data-e2e="comment-level-1"]', timeout=5000)
                comentarios_html = await page.locator('[data-e2e="comment-level-1"]').all()
                for comentario in comentarios_html[:15]: 
                    texto = await comentario.inner_text()
                    video_data["comentarios"].append(texto.replace("\n", " - "))
            except Exception:
                video_data["comentarios"].append("Sin comentarios o deshabilitados")
                
            datos_perfil["videos"].append(video_data)
            print("Video procesado con éxito.")
            await page.wait_for_timeout(2500) 

        nombre_archivo = f"datos_tiktok_{username}.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            json.dump(datos_perfil, f, ensure_ascii=False, indent=4)
            
        print(f"\n¡Extracción completada! Revisa el archivo {nombre_archivo}")
        await browser.close()

asyncio.run(extraer_datos_tiktok("tittaa.ec"))