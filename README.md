# Scraper de TikTok - Extracción Asistida con Playwright y FastAPI

Este proyecto académico implementa un scraper en Python para extraer información pública de perfiles de TikTok (métricas del usuario, enlaces de videos, vistas, *likes* y comentarios), consolidando los datos en formato JSON. La extracción se expone mediante una API REST con FastAPI y una interfaz web sencilla para lanzar el scraping y visualizar los resultados.

El diseño cumple con estrictas restricciones técnicas universitarias: la extracción se realiza sin utilizar APIs oficiales, servicios de pago de terceros, ni extensiones externas para la resolución de bloqueos.

---

## ⚙️ Arquitectura y Decisiones de Diseño Técnico

### 1. Evasión Nativa de Chromium
Para reducir la probabilidad de detección algorítmica por parte de las defensas de TikTok sin depender de librerías de terceros inestables, el script modifica los parámetros de lanzamiento nativos del motor Chromium. Se inyecta el argumento `--disable-blink-features=AutomationControlled` para borrar las banderas internas que delatan la automatización.

### 2. Manejo de Sesiones (Evasión de Login Wall)
Para evitar los bloqueos agresivos que TikTok impone a la navegación anónima, el sistema utiliza un modelo de inyección de estado. Se captura una sesión humana real en el archivo `state.json` y se inyecta en el contexto de Chromium.
> **Nota de Seguridad:** El archivo `state.json` contiene tokens sensibles y está excluido del control de versiones mediante `.gitignore` para proteger la cuenta.

### 3. Navegación Interna a los Videos (Evasión del HTTP 403)
TikTok responde con **HTTP 403 (Acceso denegado)** cuando se carga directamente la URL de un video (`/@usuario/video/...`) desde el navegador automatizado. Por ello, el scraper **no navega a la URL de cada video**: hace clic sobre la miniatura en la cuadrícula del perfil, lo que abre el visor del video mediante la navegación interna de la SPA (sin recargar la página). Tras extraer los datos, cierra el visor con el botón de cerrar y continúa con el siguiente video. Si el visor no se cierra correctamente, recarga el perfil y sigue.

### 4. Modos de Navegación Intercambiables
El código fuente (`scraper_tiktok.py`) cuenta con un "interruptor" lógico basado en comentarios de Python que permite alternar la estrategia de acceso:
- **Modo Autenticado (Default):** Flujo continuo evadiendo el muro de registro mediante inyección de cookies (`storage_state="state.json"`).
- **Modo Invitado:** Levanta una instancia de navegador limpia sin inyección de datos. Requiere el descarte manual del pop-up de inicio de sesión de TikTok.

### 5. Automatización Asistida ante Biometría (CAPTCHAs)
Al tener restringido el uso de APIs de visión artificial o granjas de resolución de terceros, el script aplica un enfoque de "Automatización Asistida". El programa se ejecuta de forma visual (`headless=False`) y con tiempos de espera extendidos (`timeout=90000` ms). Si TikTok lanza un desafío biométrico (rompecabezas), el operador humano tiene una ventana de tiempo amplia para resolverlo manualmente. Una vez superado, el script detecta la liberación del DOM y retoma la extracción. Además, aplica una pausa de 2,5 segundos entre videos para mitigar el rastreo por velocidad.

### 6. Sanitización de Entrada
El nombre de usuario recibido por la API se normaliza antes de usarse: se convierte a minúsculas, se eliminan los espacios y se quita el `@` si se incluye. Así, `@Tittaa.ec` y `tittaa.ec` apuntan al mismo perfil y al mismo archivo de salida.

---

## 🗂️ Estructura del Proyecto

| Archivo | Descripción |
|---|---|
| `scraper_tiktok.py` | API FastAPI con la lógica de scraping (Playwright síncrono) y los endpoints. |
| `index.html` | Interfaz web para lanzar el scraping y visualizar los resultados. |
| `generar_auth.py` | Script para iniciar sesión manualmente y generar `state.json`. |
| `state.json` | Sesión de TikTok (cookies y almacenamiento local). **No se versiona.** |
| `datos_tiktok_<usuario>.json` | Archivo de salida generado por cada extracción. |

---

## 🚀 Requisitos, Instalación y Despliegue en Otra Máquina

### Tecnologías Utilizadas
- **Lenguaje:** Python 3.10+ (probado con 3.15.0)
- **Scraping:** Playwright (API síncrona) con Chromium
- **API:** FastAPI + Uvicorn
- **Interfaz:** HTML, CSS y JavaScript sin dependencias externas

### Instrucciones de Configuración Inicial (Entorno Virtual)

**1. Clonar el repositorio:**
```bash
git clone https://github.com/msrodriguezv/scraper_tiktok.git
cd scraper_tiktok
```

**2. Crear y activar el entorno virtual (recomendado):**

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
Con el entorno virtual activo (debe aparecer `(env)` al inicio de la terminal):
```bash
pip install fastapi uvicorn playwright
```

**4. Instalar los binarios del navegador:**
Playwright requiere descargar su propia instancia de Chromium:
```bash
python -m playwright install chromium
```

---

## 🔐 Generación de Sesión (Paso Obligatorio)

Como `state.json` no se incluye en el repositorio, es indispensable generar una sesión local antes de ejecutar el scraper por primera vez (y cada vez que la sesión expire).

**1. Ejecutar el script de autenticación:**
```bash
python generar_auth.py
```

**2. Intervención manual:** Se abrirá una ventana de Chromium. Dispones de **2 minutos** para iniciar sesión manualmente en una cuenta válida de TikTok y resolver cualquier CAPTCHA.

**3. Captura de estado:** Una vez dentro, espera sin cerrar la ventana. Al terminar el tiempo, el script guarda las cookies en `state.json` en la raíz del proyecto y cierra el navegador.

---

## ▶️ Ejecución del Proyecto

Desde la carpeta del proyecto, con el entorno virtual activo:

```bash
python -m uvicorn scraper_tiktok:app --reload
```

Luego abre en el navegador: **http://localhost:8000/**

> Si el puerto 8000 está ocupado, usa otro: `python -m uvicorn scraper_tiktok:app --reload --port 8001`.
>
> **Importante:** si modificas el código, reinicia el servidor (o usa `--reload`). Un servidor arrancado antes de un cambio sigue ejecutando el código anterior.

### Interfaz Web
- **Extraer datos:** lanza el scraping completo del usuario indicado. Se abrirá una ventana de Chromium; el proceso tarda aproximadamente 1-2 minutos.
- **Ver últimos guardados:** muestra al instante el último JSON extraído de ese usuario, sin abrir el navegador.

La página muestra el usuario, seguidores, seguidos, el total de vistas y *likes* de los videos, y una tabla con cada video (enlace, vistas, *likes*, número de comentarios y los comentarios extraídos).

### Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Interfaz web. |
| `GET` | `/scrapi/{username}` | Ejecuta el scraping, guarda el JSON y devuelve los datos en el campo `datos`. |
| `GET` | `/datos/{username}` | Devuelve el último JSON guardado del usuario (404 si no existe). |
| `GET` | `/docs` | Documentación interactiva generada por FastAPI. |

### Flujo de Ejecución del Scraper
1. Apertura de Chromium e inyección del `state.json`.
2. Navegación al perfil objetivo (`https://www.tiktok.com/@usuario`).
3. Extracción de las métricas del perfil (seguidores y seguidos).
4. Lectura de los primeros **10 videos** de la cuadrícula; las **vistas** se toman de la miniatura (solo se muestran ahí).
5. Por cada video: clic en la miniatura, extracción de *likes*, número de comentarios y hasta **15 comentarios**, cierre del visor y pausa de 2,5 segundos.
6. Guardado del resultado en `datos_tiktok_<usuario>.json`.

---

## 📁 Estructura de Salida de Datos

Cada extracción genera un archivo JSON (ej. `datos_tiktok_tittaa.ec.json`):

```json
{
    "username": "tittaa.ec",
    "videos": [
        {
            "url": "https://www.tiktok.com/@tittaa.ec/video/7692004176087289106",
            "comentarios": [
                "Sin comentarios o deshabilitados"
            ],
            "vistas": "27K",
            "likes": "2682",
            "num_comentarios": "0"
        }
    ],
    "seguidores": "5244",
    "seguidos": "1608"
}
```

- Los valores numéricos se guardan tal como los muestra TikTok (`"27K"`, `"12.4K"`, `"1379"`).
- Si un video no tiene comentarios visibles, la lista contiene `"Sin comentarios o deshabilitados"`. TikTok puede indicar un número de comentarios mayor a cero y aun así ocultarlos (por ejemplo, comentarios filtrados).

---

## ⚠️ Protocolo ante Bloqueos (HTTP 403 / Timeout)

**Acceso denegado al abrir un video:** si el navegador muestra *"Se ha denegado el acceso a www.tiktok.com - HTTP ERROR 403"* en una URL `/video/...`, se está ejecutando una versión antigua del scraper que navegaba directamente a cada video. Detén el servidor (`Ctrl + C`) y vuelve a iniciarlo con el código actual.

**Bloqueo del perfil (Rate Limiting):** si se realizan muchas ejecuciones seguidas, el firewall de TikTok puede bloquear temporalmente la IP pública (se evidencia con un `TimeoutError` tras 90000 ms o un 403 al cargar el perfil).

**Procedimiento de recuperación:**
1. Detener el proceso en la terminal (`Ctrl + C`).
2. Esperar entre 15 y 30 minutos antes de reintentar, o cambiar de IP:
   1. Desconectar el equipo de la red Wi-Fi.
   2. Conectar el equipo mediante *tethering* (compartir internet) a una red de datos móviles.
   3. Activar y desactivar el **Modo Avión** del móvil durante 10 segundos para forzar la asignación de una IP nueva.
3. Si el bloqueo persiste, la sesión puede haber expirado: regenerar `state.json` con `python generar_auth.py`.
4. Retomar la ejecución.
