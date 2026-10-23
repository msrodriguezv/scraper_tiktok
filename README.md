# Scraper de TikTok - Extracción Asistida con Playwright y FastAPI

Este proyecto académico implementa un scraper en Python para extraer información pública de perfiles de TikTok (biografía y métricas del usuario; descripción, hashtags, fecha, música y métricas de sus videos; comentarios con su autor y las respuestas del creador; transcripción del audio; videos compartidos o *reposts*), consolidando los datos en formato JSON. A partir de esos datos estima la **personalidad del usuario según el modelo Big Five** (Cinco Grandes / OCEAN). Todo se expone mediante una API REST con FastAPI y una interfaz web sencilla.

El diseño cumple con estrictas restricciones técnicas universitarias: la extracción se realiza sin utilizar APIs oficiales, servicios de pago de terceros, ni extensiones externas para la resolución de bloqueos. El análisis de personalidad tampoco usa servicios externos: funciona sin internet con un diccionario de palabras propio y métricas calculadas en Python.

---

## 🗂️ Estructura del Proyecto

```
scraper_tiktok/
├── app/
│   ├── __init__.py
│   ├── main.py             # API FastAPI: define las rutas
│   ├── scraper.py          # Lógica de scraping con Playwright
│   ├── personalidad.py     # Análisis Big Five (fórmula y métricas)
│   ├── lexico.py           # Diccionario de palabras en español por rasgo
│   ├── almacenamiento.py   # Sanitización del usuario y lectura/escritura de JSON
│   ├── config.py           # Rutas y parámetros (nº de videos, comentarios, tiempos, mínimo de textos)
│   └── static/
│       └── index.html      # Interfaz web
├── scripts/
│   └── generar_auth.py     # Inicio de sesión manual para generar state.json
├── data/                   # Resultados de cada extracción (no se versionan)
├── state.json              # Sesión de TikTok (no se versiona)
├── requirements.txt
└── README.md
```

| Módulo | Responsabilidad |
|---|---|
| `app/main.py` | Recibe las peticiones HTTP, coordina el scraping, el análisis y el guardado, y sirve el front. |
| `app/scraper.py` | Abre Chromium, navega el perfil y extrae los datos. No sabe nada de HTTP ni de archivos. |
| `app/personalidad.py` | Prepara los textos de la persona, calcula métricas y obtiene el Big Five. No abre el navegador. |
| `app/lexico.py` | Listas de palabras y emojis que suben o bajan cada rasgo. Se pueden ampliar sin tocar la fórmula. |
| `app/almacenamiento.py` | Normaliza el nombre de usuario y guarda/lee los JSON en `data/` (datos y análisis por separado). |
| `app/config.py` | Centraliza rutas y constantes para no tener valores repetidos en el código. |

---

## ⚙️ Arquitectura y Decisiones de Diseño Técnico

### 1. Evasión Nativa de Chromium
Para reducir la probabilidad de detección algorítmica por parte de las defensas de TikTok sin depender de librerías de terceros inestables, el scraper modifica los parámetros de lanzamiento nativos del motor Chromium. Se inyecta el argumento `--disable-blink-features=AutomationControlled` (definido en `app/config.py`) para borrar las banderas internas que delatan la automatización.

### 2. Manejo de Sesiones (Evasión de Login Wall)
Para evitar los bloqueos que TikTok impone a la navegación anónima, el sistema utiliza un modelo de inyección de estado. Se captura una sesión humana real en el archivo `state.json` y se inyecta en el contexto de Chromium.
> **Nota de Seguridad:** El archivo `state.json` contiene tokens sensibles y está excluido del control de versiones mediante `.gitignore` para proteger la cuenta.

### 3. Detección de Sesión Expirada y Cierre del Modal de Login
TikTok puede invalidar la sesión desde su servidor aunque las cookies de `state.json` no hayan vencido. En ese caso el navegador entra como invitado y TikTok muestra periódicamente el modal *"Inicia sesión en TikTok"*. El scraper:
- **Detecta** la sesión expirada (aparece el botón "Iniciar sesión") y lo registra en el campo `sesion_activa` del JSON, en la consola y en la interfaz web.
- **Cierra el modal automáticamente** mediante `page.add_locator_handler` de Playwright: cada vez que el modal bloquea una acción, se pulsa su botón de cerrar (o `Escape` si la variante del modal no lo tiene) y la extracción continúa.

> En modo invitado TikTok oculta algunas publicaciones, por lo que la lista de videos puede diferir de la que ve un usuario con sesión iniciada. Para resultados completos, renueva la sesión (ver [Generación de Sesión](#-generación-de-sesión-paso-obligatorio)).

### 4. Navegación Interna a los Videos (Evasión del HTTP 403)
TikTok responde con **HTTP 403 (Acceso denegado)** cuando se carga directamente la URL de un video (`/@usuario/video/...`) desde el navegador automatizado. Por ello, el scraper **no navega a la URL de cada video**: hace clic sobre la miniatura en la cuadrícula del perfil, lo que abre el visor del video mediante la navegación interna de la SPA (sin recargar la página). Tras extraer los datos, cierra el visor y continúa con el siguiente video. Si el visor no se cierra correctamente, recarga el perfil y sigue. Si un video falla, se omite sin interrumpir el resto de la extracción.

### 5. Modos de Navegación Intercambiables
`app/scraper.py` cuenta con un "interruptor" lógico basado en comentarios de Python que permite alternar la estrategia de acceso:
- **Modo Autenticado (Default):** inyección de cookies desde `state.json`.
- **Modo Invitado:** instancia de navegador limpia sin inyección de datos (`browser.new_context()`).

### 6. Automatización Asistida ante Biometría (CAPTCHAs)
Al tener restringido el uso de APIs de visión artificial o granjas de resolución de terceros, el scraper aplica un enfoque de "Automatización Asistida". Se ejecuta de forma visual (`headless=False`) y con tiempos de espera extendidos (`TIMEOUT_MS = 90000`). Si TikTok lanza un desafío biométrico (rompecabezas), el operador humano tiene una ventana amplia para resolverlo manualmente; una vez superado, el scraper retoma la extracción. Además, aplica una pausa de 2,5 segundos entre videos para mitigar el rastreo por velocidad.

### 7. Sanitización de Entrada
El nombre de usuario recibido por la API se normaliza antes de usarse (`app/almacenamiento.py`): se convierte a minúsculas, se eliminan los espacios y se quita el `@`. Así, `@Tittaa.ec` y `tittaa.ec` apuntan al mismo perfil y al mismo archivo de salida.

---

## 🚀 Requisitos e Instalación

### Tecnologías Utilizadas
- **Lenguaje:** Python 3.10+ (probado con 3.15.0)
- **Scraping:** Playwright (API síncrona) con Chromium
- **API:** FastAPI + Uvicorn
- **Interfaz:** HTML, CSS y JavaScript sin dependencias externas

### Configuración Inicial (Entorno Virtual)

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

**3. Instalar las dependencias:**
Con el entorno virtual activo (debe aparecer `(env)` al inicio de la terminal):
```bash
pip install -r requirements.txt
```

**4. Instalar los binarios del navegador:**
```bash
python -m playwright install chromium
```

---

## 🔐 Generación de Sesión (Paso Obligatorio)

Como `state.json` no se incluye en el repositorio, es indispensable generar una sesión local antes de ejecutar el scraper por primera vez, y **cada vez que el scraper avise que la sesión expiró**.

**1. Ejecutar el script de autenticación** (desde la raíz del proyecto):
```bash
python scripts/generar_auth.py
```

**2. Intervención manual:** Se abrirá una ventana de Chromium. Dispones de **2 minutos** para iniciar sesión manualmente en una cuenta válida de TikTok y resolver cualquier CAPTCHA.

**3. Captura de estado:** Una vez dentro, espera sin cerrar la ventana. Al terminar el tiempo, el script guarda las cookies en `state.json` en la raíz del proyecto y cierra el navegador.

---

## ▶️ Ejecución del Proyecto

Desde la raíz del proyecto, con el entorno virtual activo:

```bash
python -m uvicorn app.main:app
```

Luego abre en el navegador: **http://localhost:8000/**

> - Si el puerto 8000 está ocupado, usa otro: `python -m uvicorn app.main:app --port 8001`.
> - **Si modificas el código, detén el servidor (`Ctrl + C`) y vuelve a iniciarlo.** Un servidor arrancado antes de un cambio sigue ejecutando el código anterior.
> - En Windows no se recomienda `--reload`: al recargar puede dejar procesos antiguos atendiendo el puerto con el código viejo.

### Interfaz Web
- **Extraer datos:** lanza el scraping completo del usuario indicado. Se abrirá una ventana de Chromium; el proceso tarda aproximadamente 1-2 minutos.
- **Ver últimos guardados:** muestra al instante el último JSON extraído de ese usuario, sin abrir el navegador.
- **Analizar personalidad:** calcula el Big Five con los datos ya guardados (requiere haber extraído antes los datos). Es instantáneo.
- **Ver último análisis:** muestra el último análisis guardado.

La página muestra el usuario, nickname, biografía, seguidores, seguidos, *likes* del perfil, el total de vistas y *likes* de los videos, una tabla con cada video (enlace, descripción, hashtags, transcripción, fecha, vistas, *likes*, comentarios, compartidos y los comentarios extraídos, marcando los del creador) y la tabla de compartidos. El análisis muestra una barra de distribución con el porcentaje de cada rasgo (suman 100 %) y el rasgo predominante, un gráfico de barras con el puntaje de cada rasgo (0-100, con el promedio en 50), el resumen, los intereses principales y, por cada rasgo, su cálculo (base + texto + métricas), nivel de confianza y evidencia (las palabras encontradas y las métricas aplicadas). Si la sesión de TikTok expiró, muestra un aviso indicando que hay que renovarla.

### Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Interfaz web. |
| `GET` | `/scrapi/{username}` | Ejecuta el scraping, guarda el JSON en `data/` y devuelve los datos en el campo `datos`. |
| `GET` | `/datos/{username}` | Devuelve el último JSON guardado del usuario (404 si no existe). |
| `GET` | `/analizar/{username}` | Analiza la personalidad con los datos guardados, guarda el resultado en `data/personalidad_<usuario>.json` y lo devuelve. |
| `GET` | `/personalidad/{username}` | Devuelve el último análisis de personalidad guardado (404 si no existe). |
| `GET` | `/docs` | Documentación interactiva generada por FastAPI. |

### Flujo de Ejecución del Scraper
1. Apertura de Chromium e inyección del `state.json`.
2. Navegación al perfil objetivo (`https://www.tiktok.com/@usuario`) y verificación de la sesión.
3. Extracción de los datos del perfil (nickname, biografía, verificación, seguidores, seguidos, *likes* y número de videos) desde el JSON que TikTok incrusta en la página (`__UNIVERSAL_DATA_FOR_REHYDRATION__`), con respaldo en el HTML.
4. Lectura de los primeros **10 videos** de la cuadrícula.
5. Por cada video: clic en la miniatura, extracción de sus datos, de su **transcripción** y de hasta **15 comentarios**, cierre del visor y pausa de 2,5 segundos.
6. Clic en la pestaña **Compartidos** (si es pública) y lectura de hasta **20 reposts**.
7. Guardado del resultado en `data/datos_tiktok_<usuario>.json`.

#### Captura de la API interna
Mientras navega, el scraper escucha las respuestas JSON que la propia web de TikTok pide a su API interna (`/api/post/item_list/` para los videos y `/api/comment/list/` para los comentarios). De ahí obtiene datos que el HTML no muestra completos: descripción, hashtags, fecha de publicación, duración, música, vistas/compartidos/guardados exactos y el **autor de cada comentario**, lo que permite identificar las **respuestas del creador**. Si alguna respuesta no llega, el scraper recurre al HTML y lo indica en el campo `fuente` de cada video (`"api"` o `"html"`).

#### Transcripción del audio
TikTok genera subtítulos automáticos de muchos videos y deja su enlace en los datos de la API (`subtitleInfos`). El scraper descarga ese archivo (formato WebVTT) y se queda solo con el texto. Así se obtiene lo que la persona **dice** en el video sin descargarlo ni usar reconocimiento de voz. Si el video no tiene subtítulos, `transcripcion` queda en `null`. Se puede desactivar con `DESCARGAR_TRANSCRIPCIONES = False`.

#### Compartidos (reposts)
La pestaña "Compartidos" muestra videos de otras cuentas que la persona volvió a publicar. Solo es visible si el usuario la tiene pública; si no, `reposts_disponibles` es `false`. Los reposts se leen de `/api/repost/item_list/` sin abrir cada video.

Los límites (10 videos, 15 comentarios, 20 reposts) y los tiempos de espera se configuran en `app/config.py`.

---

## 🧠 Análisis de Personalidad (Big Five)

El modelo de los **Cinco Grandes** describe la personalidad con cinco rasgos, cada uno en una escala de 0 a 100 (50 = promedio de la población):

| Rasgo | Qué mide | Señales que se buscan en TikTok |
|---|---|---|
| Apertura | Curiosidad, creatividad, variedad de intereses | Variedad de temas y hashtags, contenido original, arte, viajes, ideas nuevas |
| Responsabilidad | Orden, constancia, disciplina | Regularidad al publicar, contenido planificado, metas, estudio o trabajo |
| Extraversión | Sociabilidad, energía | Habla a la cámara, humor, planes con amigos, busca interacción |
| Amabilidad | Calidez, empatía, cooperación | Tono de sus respuestas, agradecimientos, apoyo a otros, *likes* a sus seguidores |
| Neuroticismo | Tendencia a emociones negativas | Expresiones de ansiedad, tristeza, enojo o inseguridad |

### Cómo funciona (`app/personalidad.py` y `app/lexico.py`)
El método es el mismo que usa **LIWC**, la herramienta clásica de psicología del lenguaje: las palabras que una persona usa con frecuencia reflejan su personalidad. Las asociaciones entre palabras y rasgos se basan en estudios que relacionaron el lenguaje en redes sociales con el Big Five (Yarkoni, 2010; Schwartz et al., 2013).

1. **Corpus:** se toma solo lo que la persona escribió, dijo o compartió: biografía, descripciones y transcripciones de sus videos, sus propios comentarios y respuestas, y sus reposts. Los comentarios de otras personas no se usan porque describen a la audiencia, no al dueño del perfil.
2. **Normalización:** el texto se pasa a minúsculas, se quitan tildes (`estrés` → `estres`) y se reducen letras repetidas (`graciasss` → `gracias`).
3. **Diccionario (`app/lexico.py`):** cada rasgo tiene una lista de palabras y emojis que lo **suben** y otra que lo **bajan**. Una palabra con `*` es un prefijo (`viaj*` = viaje, viajar, viajes...), igual que en LIWC. Lo que la persona comparte cuenta la mitad que lo que escribe.
4. **Aporte del texto:** `(palabras a favor − palabras en contra) por cada 100 palabras × 3`, limitado a ±30. Con poco texto el aporte se reduce (suavizado `palabras / (palabras + 50)`), para que dos o tres palabras sueltas no den puntajes extremos.
5. **Aporte de las métricas** (limitado a ±15):

| Rasgo | Regla | Puntos |
|---|---|---|
| Apertura | Hashtags muy variados (≥70 % distintos) / repetitivos (≤40 %) | +5 / −5 |
| Apertura | La mayoría de sus videos usan audio original | +3 |
| Apertura | Comparte videos de 5 o más cuentas distintas | +3 |
| Responsabilidad | Ritmo de publicación regular (coef. de variación ≤0,5) / irregular (≥1,5) | +6 / −6 |
| Responsabilidad | Publica cada 3 días o menos | +3 |
| Extraversión | Habla en la mayoría de sus videos (tienen transcripción) | +5 |
| Extraversión | 3 o más exclamaciones por cada 100 palabras | +4 |
| Extraversión | Al menos un comentario propio por video | +3 |
| Amabilidad | Da *like* a la mayoría de los comentarios de sus seguidores | +5 |
| Amabilidad | Responde 3 o más comentarios | +3 |
| Neuroticismo | (solo se estima por el lenguaje) | — |

6. **Puntaje final:** `50 + aporte del texto + aporte de las métricas`, limitado entre 0 y 100.
7. **Confianza:** *baja* si hay menos de 100 palabras o menos de 3 palabras del rasgo; *media* si hay menos de 400 palabras u 8 coincidencias; *alta* en otro caso.
8. **Umbral mínimo y plan B (compartidos):**
   - Con 5 o más textos propios (`MIN_TEXTOS_PROPIOS`) el análisis se basa en lo que la persona escribe y dice (`base_analisis: "propio"`).
   - Muchas cuentas personales casi no escriben, pero comparten mucho. Si hay menos de 5 textos propios pero 5 o más compartidos con texto útil (`MIN_REPOSTS_RESPALDO`), el análisis se hace igual con base en los compartidos (`base_analisis: "compartidos"`). En ese caso **todos los rasgos quedan con confianza "baja"** y se agrega un `aviso`: lo que alguien comparte refleja más sus **intereses** que su forma de ser.
   - Un compartido tiene "texto útil" si su descripción tiene al menos 3 palabras que no sean hashtags genéricos (`#fyp`, `#parati`, `#viral`, `#explore`...). Esos hashtags genéricos tampoco cuentan en el diccionario ni en los intereses.
   - Si no se cumple ninguna de las dos condiciones, se responde `datos_suficientes: false`.
9. **Intereses y resumen:** los intereses son los hashtags más usados (sin genéricos como `#fyp`) y el resumen se arma con una plantilla a partir de los puntajes.

Todos los parámetros (factor 3, topes ±30 y ±15, peso de los reposts) están al inicio de `app/personalidad.py` y se pueden ajustar.

### Distribución en porcentaje (los 5 rasgos suman 100 %)
Además del puntaje 0-100 de cada rasgo, el análisis reparte el **100 %** entre los cinco rasgos para mostrar cuál predomina en la persona.

Un reparto simple (`puntaje ÷ suma × 100`) no sirve, porque los puntajes suelen estar cerca de 50 y todos quedarían cerca de 20 %. Por eso se usa una **ponderación exponencial** (*softmax*, la misma técnica que usan los modelos de clasificación para convertir puntajes en probabilidades), que **amplifica las diferencias**:

```
1. peso del rasgo = e ^ ((puntaje − 50) ÷ 6)
2. porcentaje     = peso del rasgo ÷ (suma de los 5 pesos) × 100
```

Cada 6 puntos de diferencia multiplican el peso por *e* (≈ 2,7). El 6 es `SUAVIDAD_DISTRIBUCION` en `app/personalidad.py`: un número menor da un reparto más marcado y uno mayor, más parejo.

Ejemplo real (@karolg):

| Rasgo | Puntaje | Peso = e^((puntaje − 50) ÷ 6) | Porcentaje |
|---|---|---|---|
| Apertura | 59 | e^1,50 = 4,48 | 27,3 % |
| Responsabilidad | 50 | e^0,00 = 1,00 | 6,1 % |
| Extraversión | 61 | e^1,83 = 6,25 | **38,1 %** (predominante) |
| Amabilidad | 54 | e^0,67 = 1,95 | 11,9 % |
| Neuroticismo | 56 | e^1,00 = 2,72 | 16,6 % |
| **Total** | | 16,40 | **100 %** |

Para que la suma sea exactamente 100 % después de redondear a un decimal se usa el método del **mayor resto**: la décima que sobra o falta se asigna al rasgo que más perdió al redondear. El rasgo con mayor porcentaje es el **rasgo predominante**.

> Nota: en psicología los cinco rasgos son dimensiones independientes (una persona puede puntuar alto en todos), por eso se conservan también los puntajes 0-100. La distribución muestra el **peso relativo** de cada rasgo dentro del perfil.

### ¿Qué API o herramienta se usa para el análisis?
**Ninguna API externa.** El análisis Big Five es código propio en Python que corre en la misma computadora, sin internet y sin costo:

| Parte | Qué se usa |
|---|---|
| Datos de TikTok | La API **interna** de la web de TikTok (`/api/post/item_list/`, `/api/comment/list/`, `/api/repost/item_list/`), leída con **Playwright** mientras el navegador navega el perfil. No es la API oficial de TikTok. |
| Diccionario de palabras | `app/lexico.py`, creado para este proyecto con la notación de **LIWC** y basado en estudios de lenguaje y personalidad (Yarkoni, 2010; Schwartz et al., 2013). |
| Cálculo de puntajes, métricas y distribución | `app/personalidad.py`, solo con la librería estándar de Python (`re`, `unicodedata`, `collections`, `statistics`). |
| API del proyecto | **FastAPI** (propia): `/analizar/{usuario}` y `/personalidad/{usuario}`. |

### Limitaciones
- Es una **estimación**, no una medición: los estudios que predicen el Big Five desde redes sociales reportan correlaciones moderadas (aprox. 0,3-0,4) con los cuestionarios validados.
- El diccionario y los parámetros de la fórmula son **heurísticos**: no se calibraron con personas que hayan respondido un test de personalidad real.
- Un diccionario no entiende contexto: no detecta ironía ni negaciones ("no estoy triste" cuenta "triste"), y algunos emojis cambian de sentido (😭 también se usa para reír).
- TikTok muestra una imagen pública cuidada, no a la persona completa.
- Inferir la personalidad de una persona identificable es **perfilamiento de datos personales** (en Ecuador lo regula la Ley Orgánica de Protección de Datos Personales). El resultado no debe usarse para tomar decisiones sobre la persona.
- El diccionario evita a propósito palabras sobre salud, orientación sexual, religión, política o etnia.

---

## 📁 Estructura de Salida de Datos

Cada extracción genera un archivo JSON en `data/` (ej. `data/datos_tiktok_tittaa.ec.json`):

```json
{
    "username": "tittaa.ec",
    "sesion_activa": true,
    "nickname": "Titta",
    "bio": "Texto de la biografía",
    "verificado": false,
    "seguidores": 5244,
    "seguidos": 1608,
    "total_likes": 98000,
    "total_videos": 120,
    "videos": [
        {
            "url": "https://www.tiktok.com/@tittaa.ec/video/7692004176087289106",
            "id": "7692004176087289106",
            "vistas": 27100,
            "descripcion": "Texto del video #viaje #ecuador",
            "hashtags": ["viaje", "ecuador"],
            "fecha": "2026-09-30T18:20:00+00:00",
            "duracion_seg": 24,
            "musica": {"titulo": "sonido original", "autor": "Titta", "original": true},
            "likes": 2682,
            "num_comentarios": 2,
            "compartidos": 15,
            "guardados": 40,
            "fuente": "api",
            "comentarios": [
                {
                    "autor": "seguidor123",
                    "texto": "¡Qué lindo lugar!",
                    "likes": 3,
                    "es_creador": false,
                    "like_del_creador": true,
                    "respuestas": [
                        {"autor": "tittaa.ec", "texto": "¡Gracias! 😊", "likes": 1, "es_creador": true, "like_del_creador": false, "respuestas": []}
                    ]
                }
            ]
        }
    ]
}
```

- Los valores numéricos se guardan como enteros (`"27.1K"` → `27100`).
- `sesion_activa` es `false` si la extracción se hizo como invitado porque la sesión de `state.json` expiró.
- `fuente` indica si los datos del video vinieron de la API interna (completos) o del HTML (respaldo: sin fecha, compartidos ni autor de los comentarios).
- `es_creador` marca los comentarios y respuestas escritos por el dueño del perfil; `like_del_creador`, los comentarios a los que el creador dio *like*. Solo se capturan las respuestas que TikTok muestra sin desplegar el hilo.
- Si un video no tiene comentarios visibles, `comentarios` es una lista vacía. TikTok puede indicar un número de comentarios mayor a cero y aun así ocultarlos (por ejemplo, comentarios filtrados).
- `transcripcion` contiene el texto hablado del video (o `null` si no tiene subtítulos).
- `reposts` tiene la misma estructura que un video (sin comentarios ni transcripción) más `autor`, la cuenta original del video compartido.
- Los JSON generados con versiones anteriores (valores como texto y comentarios sin autor) se siguen mostrando en la interfaz, pero no tienen texto suficiente para el análisis de personalidad: hay que volver a extraerlos.

### Análisis de personalidad
Cada análisis se guarda en `data/personalidad_<usuario>.json`:

```json
{
    "username": "tittaa.ec",
    "fecha_analisis": "2026-10-22T15:00:00+00:00",
    "metodo": "Diccionario de palabras en español (estilo LIWC) + métricas de actividad",
    "fuentes_usadas": {"textos_propios": 18, "reposts_con_texto_util": 9, "videos": 10, "comentarios_del_creador": 6, "reposts": 12, "reposts_disponibles": true},
    "metricas": {"dias_promedio_entre_videos": 3.2, "hashtags_distintos": 21, "proporcion_sonido_original": 0.4},
    "advertencia": "Estimación automática a partir de contenido público de TikTok...",
    "datos_suficientes": true,
    "base_analisis": "propio",
    "big_five": {
        "apertura": {
            "puntaje": 66,
            "confianza": "media",
            "justificacion": "Base 50 +8 por el texto (9 palabras a favor y 0 en contra en 310 palabras) +8 por las métricas = 66.",
            "evidencia": [
                "A favor: viaje (4), arte (2), explorando (1), ✈ (1)",
                "Usa hashtags muy variados (21 distintos) (+5)",
                "La mayoría de sus videos usan audio original (+3)"
            ],
            "calculo": {"base": 50, "aporte_texto": 8.2, "aporte_metricas": 8},
            "porcentaje": 27.3
        },
        "responsabilidad": {},
        "extraversion": {},
        "amabilidad": {},
        "neuroticismo": {}
    },
    "distribucion": {"apertura": 27.3, "responsabilidad": 6.1, "extraversion": 38.1, "amabilidad": 11.9, "neuroticismo": 16.6},
    "rasgo_dominante": "extraversion",
    "intereses_principales": ["#viajes", "#ecuador", "#cocina"],
    "resumen": "Según el análisis por diccionario, @tittaa.ec muestra apertura en nivel alto (66), ..."
}
```

(En el ejemplo, `metricas` y los rasgos vacíos están abreviados; en el archivo real cada rasgo tiene los mismos campos que `apertura`.)

Si el análisis se basó en los compartidos, `base_analisis` es `"compartidos"`, todos los rasgos tienen `"confianza": "baja"` y aparece el campo `aviso` explicándolo.

Si no hay datos suficientes, `datos_suficientes` es `false`, no aparecen `big_five`, `resumen` ni `intereses_principales`, y `mensaje` explica el motivo.

---

## ⚠️ Solución de Problemas

**El análisis dice "datos insuficientes":**
El perfil tiene muy poco texto propio (sin descripciones, sin voz y sin respuestas a comentarios) y tampoco tiene compartidos públicos con texto, o el JSON se generó con una versión anterior del scraper. Vuelve a extraer los datos o prueba con otro perfil.

**TikTok pide iniciar sesión a cada rato / aviso "la sesión de state.json ya no es válida":**
TikTok invalidó la sesión guardada. El scraper sigue funcionando como invitado (cerrando el modal automáticamente), pero puede omitir videos. Renueva la sesión con `python scripts/generar_auth.py` y reinicia el servidor.

**Acceso denegado (HTTP 403) al abrir un video:**
Si el navegador muestra *"Se ha denegado el acceso a www.tiktok.com - HTTP ERROR 403"* en una URL `/video/...`, se está ejecutando una versión antigua del scraper que navegaba directamente a cada video. Detén **todos** los servidores (`Ctrl + C`) y vuelve a iniciarlo con `python -m uvicorn app.main:app`.

**Bloqueo del perfil (Rate Limiting):**
Si se realizan muchas ejecuciones seguidas, el firewall de TikTok puede bloquear temporalmente la IP pública (se evidencia con un `TimeoutError` tras 90000 ms o un 403 al cargar el perfil).

1. Detener el proceso en la terminal (`Ctrl + C`).
2. Esperar entre 15 y 30 minutos antes de reintentar, o cambiar de IP:
   1. Desconectar el equipo de la red Wi-Fi.
   2. Conectar el equipo mediante *tethering* (compartir internet) a una red de datos móviles.
   3. Activar y desactivar el **Modo Avión** del móvil durante 10 segundos para forzar la asignación de una IP nueva.
3. Si el bloqueo persiste, regenerar `state.json` con `python scripts/generar_auth.py`.
4. Retomar la ejecución.
