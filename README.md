
# Scraper de TikTok - Extracción Asistida con Playwright

Este proyecto académico implementa un script de web scraping nativo en Python para extraer información pública de perfiles de TikTok (métricas de usuario, enlaces de videos, interacciones y comentarios), consolidando los datos en formato JSON.

El diseño del script cumple con estrictas restricciones técnicas universitarias, logrando la extracción de datos sin utilizar APIs oficiales, servicios de pago de terceros, ni extensiones externas para la resolución de bloqueos.

---

## ⚙️ Arquitectura y Decisiones de Diseño Técnico

### 1. Evasión Nativa de Chromium

Para reducir la probabilidad de detección algorítmica por parte de las defensas de TikTok sin depender de librerías de terceros inestables, el script modifica los parámetros de lanzamiento nativos del motor Chromium. Se inyecta el argumento `--disable-blink-features=AutomationControlled` para borrar las banderas internas que delatan la automatización, permitiendo una navegación más limpia.

### 2. Manejo de Sesiones (Evasión de Login Wall y Archivo .json)

Para evitar los bloqueos agresivos que TikTok impone a la navegación anónima, el sistema utiliza un modelo de inyección de estado. Se captura una sesión humana real en el archivo de configuración `state.json` y se inyecta en el contexto de Chromium.

> **Nota de Seguridad:** El archivo `state.json` contiene tokens sensibles y está estrictamente excluido del control de versiones mediante `.gitignore`. **Para correr el proyecto en otra máquina, es obligatorio generar este archivo .json localmente.**

### 3. Modos de Navegación Intercambiables

El código fuente (`scraper_tiktok.py`) cuenta con un "interruptor" lógico basado en comentarios de Python, permitiendo alternar la estrategia de acceso en vivo durante la sustentación:

* **Modo Autenticado (Default):** Flujo continuo evadiendo el muro de registro mediante inyección de cookies.
* **Modo Invitado:** Levanta una instancia de navegador limpia sin inyección de datos. Requiere el descarte manual inmediato del pop-up de inicio de sesión de TikTok.

### 4. Automatización Asistida ante Biometría (CAPTCHAs)

Al tener restringido el uso de APIs de visión artificial o granjas de resolución de terceros, el script aplica un enfoque de "Automatización Asistida". El programa se ejecuta de forma visual (`headless=False`) y con tiempos de espera extendidos (`timeout=90000` ms). Si TikTok lanza un desafío biométrico (rompecabezas), el operador humano tiene una ventana de tiempo amplia para resolverlo manualmente. Una vez superado el bloqueo, el script detecta la liberación del DOM y retoma la extracción autónoma sin colapsar. Adicionalmente, cuenta con retardos asíncronos dinámicos para simular comportamiento humano natural en la navegación.

---

## 🚀 Requisitos, Instalación y Despliegue en Otra Máquina

### Tecnologías Utilizadas

* **Lenguaje:** Python 3.10+ (Testeado en entorno de producción con 3.15.0)
* **Librería Principal:** Playwright (Asíncrono)
* **Navegador:** Chromium

### Instrucciones de Configuración Inicial (Entorno Virtual)

Para correr el proyecto en una máquina nueva sin generar conflictos de librerías, sigue estos pasos desde la terminal:

**1. Clonar el repositorio:**

```bash
git clone https://github.com/msrodriguezv/scraper_tiktok.git
cd scraper_tiktok

```

**2. Crear y activar el entorno virtual (Recomendado):**
En Windows:

```bash
python -m venv env
.\env\Scripts\activate

```

En macOS/Linux:

```bash
python3 -m venv env
source env/bin/activate

```

**3. Instalar las dependencias del proyecto:**
Asegúrate de que el entorno virtual esté activo (debe salir `(env)` al inicio de tu terminal).

```bash
pip install playwright asyncio

```

**4. Instalar los binarios del navegador:**
Playwright requiere descargar su propia instancia independiente de Chromium.

```bash
playwright install chromium

```

---

## 🔐 Configuración del `.json` para Pruebas (Generación de Sesión)

Dado que el archivo de configuración `state.json` está bloqueado en el repositorio por protocolos de seguridad, **es indispensable generar este .json en la nueva máquina** antes de mandar a correr el scraper por primera vez para no ser clasificado como tráfico anónimo malicioso.

**1. Ejecutar el script de autenticación:**

```bash
python generar_auth.py

```

**2. Intervención Manual:** Se desplegará una ventana de Chromium. Dispones de 2 minutos exactos para iniciar sesión de forma manual en una cuenta de TikTok válida y resolver cualquier control CAPTCHA.
**3. Captura de Estado:** Una vez dentro del feed principal, espera sin cerrar la ventana. El script capturará las cookies y creará el archivo `state.json` en la raíz del proyecto de manera automática, dejándolo configurado para realizar pruebas.

---

## ▶️ Ejecución del Scraper

Con las dependencias instaladas en el entorno virtual y el archivo `.json` de estado ya configurado, inicializa el módulo principal para correr la extracción:

```bash
python scraper_tiktok.py

```

**Flujo de ejecución del script:**

1. Apertura de Chromium e inyección silenciosa del `state.json`.
2. Navegación directa al perfil objetivo.
3. Extracción estructural de las métricas principales (seguidores y seguidos).
4. Barrido del DOM para recopilar los enlaces ancla (`href`) de los videos recientes.
5. Acceso secuencial a cada enlace recopilado, aplicando retardos biomiméticos (pausas aleatorias) para extraer *likes*, vistas y comentarios.

---

## 📁 Estructura de Salida de Datos

Al concluir el ciclo de extracción exitosamente, el sistema genera de forma automática un archivo JSON con los datos finales (ej. `datos_tiktok_tittaa.ec.json`):

```json
{
    "username": "tittaa.ec",
    "seguidores": "5243",
    "seguidos": "1608",
    "videos": [
        {
            "url": "https://www.tiktok.com/@tittaa.ec/video/7696...",
            "likes": "121.6K",
            "vistas": "1.2M",
            "comentarios": [
                "Comentario de ejemplo extraído del DOM 1",
                "Comentario de ejemplo extraído del DOM 2"
            ]
        }
    ]
}

```

---

## ⚠️ Protocolo ante Bloqueos de Red (HTTP 403 / Timeout)

Si el firewall perimetral de TikTok aplica un bloqueo de IP por realizar múltiples pruebas sucesivas (evidenciado por un `TimeoutError` en consola tras 90000ms):

1. Detener el proceso en la terminal de inmediato (`Ctrl + C`).
2. Conectar el equipo mediante *tethering* (compartir internet) a una red de datos móviles.
3. Aplicar un reinicio de red activando y desactivando el **Modo Avión** en el dispositivo móvil durante 10 segundos para forzar al ISP a asignar una IP dinámica completamente limpia.
4. Retomar la ejecución del script.