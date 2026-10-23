"""
Extracción de datos públicos de un perfil de TikTok con Playwright.

Qué se extrae:
    - Perfil: nickname, biografía, verificación, seguidores, seguidos, likes, nº de videos.
    - Videos propios (los últimos MAX_VIDEOS): descripción, hashtags, fecha, música,
      métricas, transcripción del audio y comentarios (marcando los del creador).
    - Compartidos / reposts: videos de otras cuentas que la persona volvió a publicar.

Cómo se extrae (dos fuentes):
    1. API interna: la web de TikTok pide sus datos en formato JSON a direcciones como
       /api/post/item_list/. Playwright "escucha" esas respuestas mientras navegamos y
       las leemos. Es la fuente más completa y precisa.
    2. HTML: si la API no respondió, se lee lo que se ve en pantalla (respaldo).
"""
import json
import re
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

from app.config import (
    CHROMIUM_ARGS, DESCARGAR_TRANSCRIPCIONES, MAX_COMENTARIOS, MAX_REPOSTS, MAX_VIDEOS,
    PAUSA_ENTRE_VIDEOS_MS, STATE_FILE, TIKTOK_URL, TIMEOUT_MS,
)

# Direcciones de la API interna de TikTok que nos interesan
API_VIDEOS = "/api/post/item_list/"       # Videos publicados por el perfil
API_REPOSTS = "/api/repost/item_list/"    # Videos de la pestaña "Compartidos"
API_COMENTARIOS = "/api/comment/list/"    # Comentarios de un video


def extraer_perfil(username: str) -> dict:
    """Abre el perfil de TikTok y devuelve un diccionario con todos sus datos."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=CHROMIUM_ARGS)

        # --- INTERRUPTOR DE NAVEGACIÓN ---
        context = browser.new_context(storage_state=str(STATE_FILE))
        # context = browser.new_context() # MODO INVITADO

        page = context.new_page()
        page.set_default_timeout(TIMEOUT_MS)

        # Sin sesión válida TikTok muestra el modal "Inicia sesión en TikTok" cada
        # cierto tiempo. Playwright lo cierra automáticamente cuando bloquea una acción.
        page.add_locator_handler(
            page.locator('[data-e2e="login-modal"]'),
            lambda modal: _cerrar_modal_login(page),
            no_wait_after=True,
        )

        # --- ESCUCHA DE LA API INTERNA ---
        # Cada vez que el navegador recibe una respuesta, si es de la API que nos
        # interesa la guardamos en "pendientes". No la leemos dentro del evento porque
        # eso puede bloquear Playwright; se lee después con _procesar_respuestas().
        pendientes = []
        page.on("response", lambda r: pendientes.append(r) if _es_api_util(r.url) else None)

        # Aquí se ordena lo leído de la API:
        #   videos      -> {id_del_video: datos}
        #   comentarios -> {id_del_video: [comentarios]}
        #   reposts     -> [datos de cada video compartido]
        api = {"videos": {}, "comentarios": {}, "reposts": []}

        url_perfil = f"{TIKTOK_URL}/@{username}"
        datos_perfil = {"username": username}

        print(f"Navegando al perfil de @{username}...")
        page.goto(url_perfil, wait_until="domcontentloaded")
        page.wait_for_selector('[data-e2e="user-post-item"] a')

        # Si aparece el botón "Iniciar sesión", TikTok invalidó la sesión de state.json
        datos_perfil["sesion_activa"] = page.locator('[data-e2e="top-login-button"]').count() == 0
        if not datos_perfil["sesion_activa"]:
            print("Aviso: la sesión de state.json ya no es válida. Ejecuta: python scripts/generar_auth.py")

        # --- 1. DATOS DEL PERFIL ---
        datos_perfil.update(_extraer_info_perfil(page))

        # --- 2. VIDEOS PROPIOS ---
        datos_perfil["videos"] = []
        page.wait_for_timeout(2000)
        _procesar_respuestas(pendientes, api)
        items_videos = page.locator('[data-e2e="user-post-item"]')

        # TikTok responde HTTP 403 al cargar /video/... directamente con page.goto().
        # Por eso abrimos cada video haciendo clic en la cuadrícula del perfil
        # (navegación interna de la SPA) y lo cerramos para volver al perfil.
        for i in range(min(items_videos.count(), MAX_VIDEOS)):
            try:
                video_data = _extraer_video(page, items_videos.nth(i), username, pendientes, api)
            except Exception as e:
                print(f"Aviso: error al procesar el video {i + 1}: {e}")
                video_data = None
            if video_data is None:
                continue
            datos_perfil["videos"].append(video_data)

            # Cerrar el visor y volver a la cuadrícula del perfil
            try:
                page.locator('[data-e2e="browse-close"]').click()
                page.wait_for_selector('[data-e2e="browse-like-count"]', state="detached", timeout=15000)
            except Exception:
                page.goto(url_perfil, wait_until="domcontentloaded")
                page.wait_for_selector('[data-e2e="user-post-item"] a')
            page.wait_for_timeout(PAUSA_ENTRE_VIDEOS_MS)

        desde_api = sum(v["fuente"] == "api" for v in datos_perfil["videos"])
        print(f"Videos extraídos: {len(datos_perfil['videos'])} ({desde_api} desde la API interna)")

        # --- 3. COMPARTIDOS (REPOSTS) ---
        disponibles, reposts = _extraer_reposts(page, pendientes, api)
        datos_perfil["reposts_disponibles"] = disponibles
        datos_perfil["reposts"] = reposts
        print(f"Reposts extraídos: {len(reposts)}")

        browser.close()
        return datos_perfil


def _cerrar_modal_login(page):
    # Algunas variantes del modal no tienen botón de cerrar; en ese caso se usa Escape
    try:
        page.locator('[data-e2e="modal-close-inner-button"]').first.click(timeout=5000)
    except Exception:
        page.keyboard.press("Escape")
    page.wait_for_timeout(1000)


# ---------------------------------------------------------------------------
# Lectura de la API interna
# ---------------------------------------------------------------------------

def _es_api_util(url):
    return API_VIDEOS in url or API_REPOSTS in url or API_COMENTARIOS in url


def _procesar_respuestas(pendientes, api):
    """Lee el JSON de cada respuesta acumulada y lo guarda ordenado en `api`."""
    while pendientes:
        respuesta = pendientes.pop(0)
        try:
            datos = respuesta.json()
        except Exception:
            continue  # Respuesta vacía o que no es JSON: se ignora

        if API_VIDEOS in respuesta.url:
            # "itemList" es la lista de videos que TikTok envía a la cuadrícula
            for item in datos.get("itemList") or []:
                api["videos"][str(item.get("id"))] = item
        elif API_REPOSTS in respuesta.url:
            api["reposts"].extend(datos.get("itemList") or [])
        else:
            # La URL de comentarios lleva el id del video: ...?aweme_id=7692004176087289106
            # (las respuestas a un comentario, /api/comment/list/reply/, no lo llevan y se omiten)
            aweme_id = parse_qs(urlparse(respuesta.url).query).get("aweme_id", [None])[0]
            if aweme_id:
                api["comentarios"].setdefault(aweme_id, []).extend(datos.get("comments") or [])


# ---------------------------------------------------------------------------
# Perfil
# ---------------------------------------------------------------------------

def _extraer_info_perfil(page):
    """Datos del perfil desde el JSON que TikTok incrusta en la página; si falla, desde el HTML."""
    try:
        # TikTok inserta en el HTML una etiqueta <script> con los datos del perfil en JSON
        bruto = page.locator("#__UNIVERSAL_DATA_FOR_REHYDRATION__").text_content(timeout=5000)
        info = json.loads(bruto)["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        usuario, stats = info["user"], info.get("stats", {})
        return {
            "nickname": usuario.get("nickname"),
            "bio": usuario.get("signature", ""),  # TikTok llama "signature" a la biografía
            "verificado": usuario.get("verified", False),
            "seguidores": stats.get("followerCount"),
            "seguidos": stats.get("followingCount"),
            "total_likes": stats.get("heartCount"),
            "total_videos": stats.get("videoCount"),
        }
    except Exception:
        print("Aviso: no se leyó el JSON del perfil; se usa el HTML.")

    # Respaldo: leer los textos visibles en la cabecera del perfil
    info = {}
    campos = [
        ("nickname", '[data-e2e="user-subtitle"]'),
        ("bio", '[data-e2e="user-bio"]'),
        ("seguidores", '[data-e2e="followers-count"]'),
        ("seguidos", '[data-e2e="following-count"]'),
        ("total_likes", '[data-e2e="likes-count"]'),
    ]
    for campo, selector in campos:
        try:
            texto = page.locator(selector).first.inner_text(timeout=5000)
            info[campo] = texto if campo in ("nickname", "bio") else _a_numero(texto)
        except Exception:
            pass
    return info


# ---------------------------------------------------------------------------
# Videos propios
# ---------------------------------------------------------------------------

def _extraer_video(page, item, username, pendientes, api):
    url = item.locator("a").first.get_attribute("href", timeout=15000)
    if not url or "/video/" not in url:
        return None  # Se omiten los carruseles de fotos (/photo/)

    # El id es el número final de la URL: .../video/7692004176087289106
    video_id = url.split("/video/")[1].split("?")[0]
    video_data = {"url": url, "id": video_id}

    # Las vistas se muestran en la miniatura (se reemplazan por el dato exacto de la API si existe)
    try:
        video_data["vistas"] = _a_numero(item.locator('[data-e2e="video-views"]').inner_text(timeout=5000))
    except Exception:
        pass

    try:
        item.locator("a").first.click()
        page.wait_for_selector('[data-e2e="browse-like-count"]', timeout=30000)
    except Exception:
        print(f"Aviso: no se pudo abrir el video {url}")
        return None

    # Al abrir el visor TikTok pide los comentarios a su API; esperamos a que aparezcan
    try:
        page.wait_for_selector('[data-e2e="comment-level-1"]', timeout=5000)
    except Exception:
        pass
    _procesar_respuestas(pendientes, api)

    # Datos del video: primero la API, si no hay, el HTML
    item_api = api["videos"].get(video_id)
    if item_api:
        video_data.update(_datos_desde_api(item_api))
        video_data["fuente"] = "api"
        if DESCARGAR_TRANSCRIPCIONES:
            video_data["transcripcion"] = _descargar_transcripcion(page, item_api)
    else:
        video_data.update(_datos_desde_html(page))
        video_data["fuente"] = "html"

    # Comentarios: igual, primero la API (trae el autor) y si no, el HTML (solo texto)
    comentarios_api = api["comentarios"].get(video_id)
    if comentarios_api:
        video_data["comentarios"] = [_comentario(c, username) for c in comentarios_api[:MAX_COMENTARIOS]]
    else:
        video_data["comentarios"] = _comentarios_desde_html(page)

    return video_data


def _datos_desde_api(item):
    """Convierte un video del JSON de TikTok (nombres en inglés) a nuestro formato."""
    stats = item.get("stats") or {}
    musica = item.get("music") or {}
    return {
        "descripcion": item.get("desc", ""),
        # "textExtra" marca los elementos especiales del texto; los que tienen
        # "hashtagName" son los hashtags
        "hashtags": [t["hashtagName"] for t in item.get("textExtra") or [] if t.get("hashtagName")],
        "fecha": _fecha_iso(item.get("createTime")),
        "duracion_seg": (item.get("video") or {}).get("duration"),
        "musica": {
            "titulo": musica.get("title"),
            "autor": musica.get("authorName"),
            "original": musica.get("original", False),  # True = audio grabado por el creador
        },
        "vistas": stats.get("playCount"),
        "likes": stats.get("diggCount"),
        "num_comentarios": stats.get("commentCount"),
        "compartidos": stats.get("shareCount"),
        "guardados": stats.get("collectCount"),
    }


def _datos_desde_html(page):
    """Respaldo: lee lo que se ve en el visor del video (sin fecha ni compartidos)."""
    datos = {}
    try:
        datos["likes"] = _a_numero(page.locator('[data-e2e="browse-like-count"]').inner_text())
        datos["num_comentarios"] = _a_numero(page.locator('[data-e2e="browse-comment-count"]').inner_text())
    except Exception:
        pass
    try:
        datos["descripcion"] = page.locator('[data-e2e="browse-video-desc"]').first.inner_text(timeout=5000)
        datos["hashtags"] = re.findall(r"#(\w+)", datos["descripcion"])
    except Exception:
        pass
    try:
        datos["musica"] = {"titulo": page.locator('[data-e2e="browse-music"]').first.inner_text(timeout=5000)}
    except Exception:
        pass
    return datos


# ---------------------------------------------------------------------------
# Transcripción (lo que se dice en el video)
# ---------------------------------------------------------------------------

def _descargar_transcripcion(page, item):
    """
    TikTok genera subtítulos automáticos de muchos videos y deja el enlace en
    item["video"]["subtitleInfos"]. Descargarlos nos da el texto hablado sin tener
    que bajar el video ni usar un programa de reconocimiento de voz.
    Devuelve None si el video no tiene subtítulos.
    """
    subtitulos = (item.get("video") or {}).get("subtitleInfos") or []
    # Preferimos "ASR" (reconocimiento del audio original) antes que "MT" (traducción automática)
    subtitulos = sorted(subtitulos, key=lambda s: s.get("Source") != "ASR")
    for sub in subtitulos:
        if not sub.get("Url"):
            continue
        try:
            # page.request descarga usando las mismas cookies que el navegador
            respuesta = page.request.get(sub["Url"], timeout=15000)
            if respuesta.ok:
                texto = _texto_de_vtt(respuesta.text())
                if texto:
                    return texto
        except Exception:
            continue
    return None


def _texto_de_vtt(vtt):
    """
    Los subtítulos vienen en formato WebVTT:
        WEBVTT
        00:00:00.120 --> 00:00:02.000
        hola a todos
    Nos quedamos solo con las líneas de texto, sin tiempos ni cabeceras.
    """
    lineas = []
    for linea in vtt.splitlines():
        linea = re.sub(r"<[^>]+>", "", linea).strip()  # Quita etiquetas de formato como <c>
        if not linea or linea.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if "-->" in linea or linea.isdigit():  # Línea de tiempos o número de bloque
            continue
        if not lineas or lineas[-1] != linea:  # Los subtítulos automáticos repiten líneas
            lineas.append(linea)
    return " ".join(lineas)


# ---------------------------------------------------------------------------
# Comentarios
# ---------------------------------------------------------------------------

def _comentario(c, username):
    """Convierte un comentario del JSON de TikTok a nuestro formato."""
    autor = (c.get("user") or {}).get("unique_id", "")
    return {
        "autor": autor,
        "texto": c.get("text", ""),
        "likes": c.get("digg_count", 0),
        # Si el autor es el dueño del perfil, este comentario lo escribió la persona analizada
        "es_creador": autor.lower() == username,
        "like_del_creador": c.get("is_author_digged", False),
        # TikTok adelanta algunas respuestas (a menudo la del creador) junto al comentario
        "respuestas": [_comentario(r, username) for r in c.get("reply_comment") or []],
    }


def _comentarios_desde_html(page):
    # Respaldo sin API: solo se obtiene el texto, no el autor
    comentarios = []
    for nodo in page.locator('[data-e2e="comment-level-1"]').all()[:MAX_COMENTARIOS]:
        try:
            texto = nodo.inner_text(timeout=5000).replace("\n", " - ")
        except Exception:
            continue
        comentarios.append({"autor": None, "texto": texto, "es_creador": False, "respuestas": []})
    return comentarios


# ---------------------------------------------------------------------------
# Compartidos (reposts)
# ---------------------------------------------------------------------------

def _extraer_reposts(page, pendientes, api):
    """
    Abre la pestaña "Compartidos" del perfil y devuelve (disponible, lista_de_reposts).
    Solo existe si la persona la tiene pública; si no, devuelve (False, []).
    No hace falta abrir cada video: la API trae todo en una sola respuesta.
    """
    pestana = page.locator('[data-e2e="repost-tab"]')
    if pestana.count() == 0:
        print("Aviso: la pestaña de Compartidos no es pública en este perfil.")
        return False, []

    try:
        # expect_response espera a que llegue la respuesta de la API tras el clic
        with page.expect_response(lambda r: API_REPOSTS in r.url, timeout=15000):
            pestana.first.click()
    except Exception:
        pass  # A veces la respuesta llega antes de empezar a esperar; se revisa abajo
    page.wait_for_timeout(1500)
    _procesar_respuestas(pendientes, api)
    if not api["reposts"]:
        print("Aviso: no se recibieron compartidos (puede que la lista esté vacía).")

    reposts = []
    for item in api["reposts"][:MAX_REPOSTS]:
        # En un repost el autor es OTRA cuenta; la guardamos para saber a quién comparte
        autor = (item.get("author") or {}).get("uniqueId", "")
        repost = {"url": f"{TIKTOK_URL}/@{autor}/video/{item.get('id')}", "id": str(item.get("id")), "autor": autor}
        repost.update(_datos_desde_api(item))
        reposts.append(repost)
    return True, reposts


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _fecha_iso(timestamp):
    """TikTok da la fecha en segundos desde 1970; la pasamos a texto ISO (2026-10-01T18:20:00+00:00)."""
    if not timestamp:
        return None
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()


def _a_numero(texto):
    """Convierte '27.1K', '1,2 M' o '1409' en entero; None si no se reconoce."""
    m = re.fullmatch(r"([\d.,]+)\s*([KMB])?", (texto or "").strip().upper())
    if not m:
        return None
    numero, sufijo = m.groups()
    if sufijo:
        return int(float(numero.replace(",", ".")) * {"K": 1e3, "M": 1e6, "B": 1e9}[sufijo])
    return int(re.sub(r"[.,]", "", numero))  # Sin sufijo, el punto o la coma son separadores de miles
