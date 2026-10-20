# Scraper de TikTok - Extracción Asistida con Playwright

Este proyecto académico implementa un script de web scraping nativo en Python para extraer información pública de perfiles de TikTok (métricas de usuario, enlaces de videos, interacciones y comentarios), consolidando los datos en formato JSON.

El diseño del script cumple con estrictas restricciones técnicas universitarias, logrando la extracción de datos sin utilizar APIs oficiales, servicios de pago de terceros, ni extensiones externas para la resolución de bloqueos.

---

## ⚙️ Arquitectura y Decisiones de Diseño Técnico

### 1. Evasión de Huellas (Playwright Stealth)
Para reducir la probabilidad de detección algorítmica por parte de las defensas de TikTok, el script implementa la librería `playwright-stealth`. Esta capa de invisibilidad borra los rastros internos de Chromium que delatan la automatización, permitiendo que el bot navegue simulando ser un usuario humano estándar.

### 2. Manejo de Sesiones (Evasión de Login Wall)
Para evitar los bloqueos agresivos que TikTok impone a la navegación anónima, el sistema utiliza un modelo de inyección de estado. Se captura una sesión humana real en el archivo `state.json` y se inyecta en el contexto de Chromium. 
> **Nota de Seguridad:** El archivo `state.json` contiene tokens sensibles y está estrictamente excluido del control de versiones mediante `.gitignore` para proteger la cuenta.

### 3. Modos de Navegación Intercambiables
El código fuente (`scraper_tiktok.py`) cuenta con un "interruptor" lógico basado en comentarios de Python, permitiendo alternar la estrategia de acceso en vivo durante la sustentación:
- **Modo Autenticado (Default):** Flujo continuo evadiendo el muro de registro mediante inyección de cookies.
- **Modo Invitado:** Levanta una instancia de navegador limpia sin inyección de datos. Requiere el descarte manual inmediato del pop-up de inicio de sesión de TikTok.

### 4. Automatización Asistida ante Biometría (CAPTCHAs)
Al tener restringido el uso de APIs de visión artificial o granjas de resolución de terceros, el script aplica un enfoque de "Automatización Asistida".
El programa se ejecuta de forma visual (`headless=False`) y con tiempos de espera extendidos (`timeout=90000` ms). Si TikTok lanza un desafío biométrico (rompecabezas), el operador humano tiene una ventana de tiempo amplia para resolverlo manualmente. Una vez superado el bloqueo, el script detecta la liberación del DOM y retoma la extracción autónoma sin colapsar.

---

## 🚀 Requisitos, Instalación y Despliegue

### Tecnologías Utilizadas
- **Python:** 3.15.0
- **Librerías:** `playwright`, `playwright-stealth`
- **Navegador:** Chromium

### Instrucciones de Despliegue

1. **Clonar el repositorio:**
   ```bash
   git clone [https://github.com/msrodriguezv/scraper_tiktok.git](https://github.com/msrodriguezv/scraper_tiktok.git)
   cd scraper_tiktok