from playwright.sync_api import sync_playwright

def generar_estado():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("Navegando a TikTok...")
        page.goto("https://www.tiktok.com/login")
        
        print("Tienes 2 minutos para iniciar sesión manualmente y resolver cualquier CAPTCHA.")
        # Pausa la ejecución por 120 segundos para que te dé tiempo de loguearte
        page.wait_for_timeout(120000) 
        
        # Guarda las cookies y el almacenamiento local
        context.storage_state(path="state.json")
        print("¡Sesión guardada exitosamente en state.json!")
        
        browser.close()

if __name__ == "__main__":
    generar_estado()