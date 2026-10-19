import asyncio
from playwright.async_api import async_playwright

async def guardar_sesion():
    async with async_playwright() as p:
        # headless=False abre el navegador visiblemente
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto("https://www.tiktok.com/login")
        print("Tienes 60 segundos para iniciar sesión manualmente en la ventana que se abrió...")
        
        # Espera 60 segundos mientras pones tu usuario y contraseña
        await page.wait_for_timeout(60000) 
        
        # Guarda las cookies y tokens de sesión
        await context.storage_state(path="state.json")
        print("¡Sesión capturada con éxito! Archivo state.json generado.")
        
        await browser.close()

asyncio.run(guardar_sesion())