from pathlib import Path

from playwright.sync_api import sync_playwright

# state.json se guarda en la raíz del proyecto, donde lo lee el scraper
STATE_FILE = Path(__file__).resolve().parent.parent / "state.json"


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
        context.storage_state(path=str(STATE_FILE))
        print(f"¡Sesión guardada exitosamente en {STATE_FILE}!")

        browser.close()


if __name__ == "__main__":
    generar_estado()
