"""
Estimación de la personalidad con el modelo de los Cinco Grandes (Big Five / OCEAN)
a partir de los datos que guardó el scraper en data/datos_tiktok_<usuario>.json.

Los cinco rasgos (escala 0-100, donde 50 es el promedio):
    - Apertura a la experiencia: curiosidad, creatividad, variedad de intereses.
    - Responsabilidad: orden, constancia, disciplina.
    - Extraversión: sociabilidad, energía, búsqueda de interacción.
    - Amabilidad: calidez, empatía, cooperación.
    - Neuroticismo: tendencia a emociones negativas (ansiedad, enojo, tristeza).

Método (100 % gratuito y sin internet):
    1. preparar_corpus()   -> junta lo que la persona ESCRIBIÓ, DIJO o COMPARTIÓ.
    2. calcular_metricas() -> indicadores numéricos de su actividad (frecuencia, variedad...).
    3. analizar_personalidad():
         a) Cuenta las palabras del diccionario (app/lexico.py) que suben o bajan
            cada rasgo, por cada 100 palabras de texto.
         b) Suma pequeños ajustes según las métricas (por ejemplo, publicar con un
            ritmo regular sube la responsabilidad).
         c) Puntaje = 50 + aporte del texto + aporte de las métricas (limitado a 0-100).

Cada puntaje guarda su cálculo y las palabras que lo produjeron, así se puede
explicar exactamente de dónde salió cada número.
"""
import math
import re
import statistics
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from app.config import MIN_REPOSTS_RESPALDO, MIN_TEXTOS_PROPIOS
from app.lexico import LEXICO, PREFIJOS_GENERICOS

RASGOS = ["apertura", "responsabilidad", "extraversion", "amabilidad", "neuroticismo"]
NOMBRES = {
    "apertura": "Apertura",
    "responsabilidad": "Responsabilidad",
    "extraversion": "Extraversión",
    "amabilidad": "Amabilidad",
    "neuroticismo": "Neuroticismo",
}

METODO = "Diccionario de palabras en español (estilo LIWC) + métricas de actividad"
ADVERTENCIA = (
    "Estimación automática a partir de contenido público de TikTok. No es un diagnóstico "
    "psicológico ni debe usarse para tomar decisiones sobre la persona."
)

# --- Parámetros de la fórmula (se pueden ajustar) ---
PUNTAJE_BASE = 50          # Punto de partida: el promedio de la población
# Puntos por cada palabra neta (a favor - en contra) cada 100 palabras. En textos
# reales cada categoría suele ocupar entre 1 y 5 % de las palabras, así que 3 puntos
# por palabra deja los perfiles típicos entre ~35 y ~65 y reserva los extremos.
FACTOR_TEXTO = 3
MAX_APORTE_TEXTO = 30      # El texto mueve el puntaje como máximo ±30
MAX_APORTE_METRICAS = 15   # Las métricas lo mueven como máximo ±15
PALABRAS_SUAVIZADO = 50    # Con poco texto el aporte se reduce (ver _puntuar_rasgo)
PESO_REPOSTS = 0.5         # Lo que comparte cuenta la mitad que lo que escribe
# Cuánto se amplifican las diferencias al repartir el 100 % (ver _distribucion).
# Más pequeño = reparto más marcado; más grande = reparto más parejo (todos cerca de 20 %).
SUAVIDAD_DISTRIBUCION = 6


# ---------------------------------------------------------------------------
# 1. Preparar el corpus (los textos que hablan de la persona)
# ---------------------------------------------------------------------------

def preparar_corpus(datos: dict) -> dict:
    """
    Selecciona del JSON del scraper solo lo que sirve para conocer a la persona,
    separado por fuente para poder darle a cada una su peso.
    """
    videos = []
    comentarios_creador = []

    for video in datos.get("videos", []):
        musica = video.get("musica") or {}
        videos.append({
            "fecha": video.get("fecha"),
            "descripcion": video.get("descripcion"),
            "hashtags": video.get("hashtags", []),
            "transcripcion": video.get("transcripcion"),
            "musica": musica.get("titulo"),
            "sonido_original": musica.get("original"),
        })

        # Recorremos los comentarios buscando los que escribió el dueño del perfil,
        # tanto comentarios sueltos como respuestas a sus seguidores.
        for comentario in video.get("comentarios", []):
            if not isinstance(comentario, dict):
                continue  # Los JSON antiguos guardaban comentarios como texto sin autor
            if comentario.get("es_creador"):
                comentarios_creador.append({"en_respuesta_a": None, "texto": comentario.get("texto")})
            for respuesta in comentario.get("respuestas", []):
                if respuesta.get("es_creador"):
                    comentarios_creador.append({
                        "en_respuesta_a": comentario.get("texto"),
                        "texto": respuesta.get("texto"),
                    })

    reposts = [
        {
            "autor_original": r.get("autor"),
            "descripcion": r.get("descripcion"),
            "hashtags": r.get("hashtags", []),
        }
        for r in datos.get("reposts", [])
    ]

    return {
        "bio": datos.get("bio") or "",
        "videos": videos,
        "comentarios_del_creador": comentarios_creador,
        "reposts": reposts,
    }


def contar_textos_propios(corpus: dict) -> int:
    """Cuántos textos escritos o dichos por la persona tenemos (los reposts no cuentan)."""
    total = 1 if corpus["bio"].strip() else 0
    total += sum(1 for v in corpus["videos"] if v.get("descripcion") or v.get("transcripcion"))
    total += len(corpus["comentarios_del_creador"])
    return total


def contar_reposts_utiles(corpus: dict) -> int:
    """
    Cuántos compartidos tienen texto que sirva: al menos 3 palabras reales.
    No cuentan los que solo traen hashtags genéricos como "#fyp #parati #viral".
    """
    return sum(
        1 for r in corpus["reposts"]
        if len([p for p in _palabras(r.get("descripcion") or "") if not p.startswith(PREFIJOS_GENERICOS)]) >= 3
    )


def _textos_del_corpus(corpus: dict):
    """Devuelve dos listas de textos: los propios y los de los videos compartidos."""
    propios = [corpus["bio"]]
    for video in corpus["videos"]:
        propios += [video.get("descripcion") or "", video.get("transcripcion") or ""]
    propios += [c.get("texto") or "" for c in corpus["comentarios_del_creador"]]
    compartidos = [r.get("descripcion") or "" for r in corpus["reposts"]]
    return [t for t in propios if t], [t for t in compartidos if t]


# ---------------------------------------------------------------------------
# 2. Métricas objetivas de actividad
# ---------------------------------------------------------------------------

def calcular_metricas(datos: dict, corpus: dict) -> dict:
    videos = datos.get("videos", [])

    # Días entre publicaciones consecutivas -> ritmo y regularidad (responsabilidad)
    fechas = sorted(datetime.fromisoformat(v["fecha"]) for v in videos if v.get("fecha"))
    intervalos = [(b - a).total_seconds() / 86400 for a, b in zip(fechas, fechas[1:])]
    promedio = statistics.mean(intervalos) if intervalos else None
    desviacion = statistics.pstdev(intervalos) if len(intervalos) > 1 else None

    # Variedad de hashtags -> variedad de temas (apertura)
    hashtags = [h.lower() for v in videos for h in v.get("hashtags", [])]

    # Audio propio vs. canciones o sonidos de moda -> originalidad (apertura)
    con_musica = [v["musica"] for v in videos if isinstance(v.get("musica"), dict) and "original" in v["musica"]]

    # ¿Da like a los comentarios de sus seguidores? -> calidez (amabilidad)
    ajenos = [
        c for v in videos for c in v.get("comentarios", [])
        if isinstance(c, dict) and c.get("autor") and not c.get("es_creador")
    ]

    # Signos de exclamación en sus textos -> energía y expresividad (extraversión)
    propios, _ = _textos_del_corpus(corpus)
    palabras_propias = sum(len(_palabras(t)) for t in propios)
    exclamaciones = sum(t.count("!") + t.count("¡") for t in propios)

    reposts = datos.get("reposts", [])

    return {
        "videos_analizados": len(videos),
        "palabras_propias": palabras_propias,
        # Si el video tiene transcripción, la persona habla en él
        "proporcion_videos_con_voz": _proporcion(sum(1 for v in videos if v.get("transcripcion")), len(videos)),
        "dias_promedio_entre_videos": _redondear(promedio) if promedio is not None else None,
        # Coeficiente de variación = desviación / promedio. Cerca de 0 = publica con
        # un ritmo muy regular; mayor que 1 = publica a rachas.
        "coeficiente_variacion_dias": _redondear(desviacion / promedio) if desviacion is not None and promedio else None,
        "hashtags_distintos": len(set(hashtags)),
        "proporcion_hashtags_distintos": _proporcion(len(set(hashtags)), len(hashtags)),
        "proporcion_sonido_original": _proporcion(sum(1 for m in con_musica if m["original"]), len(con_musica)),
        "comentarios_del_creador": len(corpus["comentarios_del_creador"]),
        "proporcion_comentarios_con_like_del_creador": _proporcion(
            sum(1 for c in ajenos if c.get("like_del_creador")), len(ajenos)
        ),
        "exclamaciones_por_100_palabras": _redondear(exclamaciones / palabras_propias * 100) if palabras_propias else 0,
        "reposts_analizados": len(reposts),
        "autores_distintos_en_reposts": len({r.get("autor") for r in reposts if r.get("autor")}),
        "seguidores": datos.get("seguidores"),
        "seguidos": datos.get("seguidos"),
    }


def _proporcion(parte, total):
    return _redondear(parte / total) if total else None


def _redondear(valor):
    return round(valor, 2)


# ---------------------------------------------------------------------------
# 3. Análisis: diccionario + métricas
# ---------------------------------------------------------------------------

def analizar_personalidad(datos: dict) -> dict:
    """Devuelve el análisis Big Five listo para guardar en JSON y mostrar en la web."""
    username = datos["username"]
    corpus = preparar_corpus(datos)
    metricas = calcular_metricas(datos, corpus)
    textos_propios = contar_textos_propios(corpus)
    reposts_utiles = contar_reposts_utiles(corpus)

    # ¿En qué nos basamos?
    #   "propio"      -> hay suficiente texto escrito o dicho por la persona (lo ideal).
    #   "compartidos" -> casi no hay texto propio, pero sí compartidos con texto (plan B).
    #   None          -> no hay datos suficientes de ningún tipo.
    if textos_propios >= MIN_TEXTOS_PROPIOS:
        base_analisis = "propio"
    elif reposts_utiles >= MIN_REPOSTS_RESPALDO:
        base_analisis = "compartidos"
    else:
        base_analisis = None

    resultado = {
        "username": username,
        "fecha_analisis": datetime.now(timezone.utc).isoformat(),
        "metodo": METODO,
        "fuentes_usadas": {
            "textos_propios": textos_propios,
            "reposts_con_texto_util": reposts_utiles,
            "videos": len(corpus["videos"]),
            "comentarios_del_creador": len(corpus["comentarios_del_creador"]),
            "reposts": len(corpus["reposts"]),
            "reposts_disponibles": datos.get("reposts_disponibles"),
        },
        "metricas": metricas,
        "advertencia": ADVERTENCIA,
    }

    # Sin texto propio ni compartidos útiles, cualquier puntaje sería una adivinanza
    if base_analisis is None:
        resultado["datos_suficientes"] = False
        resultado["mensaje"] = (
            f"@{username} tiene solo {textos_propios} textos propios (mínimo {MIN_TEXTOS_PROPIOS}) y "
            f"{reposts_utiles} compartidos con texto útil (mínimo {MIN_REPOSTS_RESPALDO}). "
            "Vuelve a extraer los datos o prueba con un perfil que escriba descripciones, "
            "hable en sus videos o comparta videos con texto."
        )
        return resultado

    # Separamos los textos en palabras normalizadas una sola vez
    propios, compartidos = _textos_del_corpus(corpus)
    total_palabras = metricas["palabras_propias"] + PESO_REPOSTS * sum(len(_palabras(t)) for t in compartidos)
    ajustes = _ajustes_por_metricas(metricas)

    big_five = {
        rasgo: _puntuar_rasgo(rasgo, propios, compartidos, total_palabras, ajustes[rasgo])
        for rasgo in RASGOS
    }

    # Plan B: lo que una persona comparte habla de sus GUSTOS, no necesariamente de
    # cómo ES. Por eso todos los rasgos quedan con confianza "baja" y se avisa.
    if base_analisis == "compartidos":
        for rasgo in RASGOS:
            big_five[rasgo]["confianza"] = "baja"
        resultado["aviso"] = (
            f"@{username} casi no publica texto propio ({textos_propios} textos), así que este análisis "
            f"se basa sobre todo en {reposts_utiles} videos que comparte. Refleja más sus intereses "
            "que su forma de ser: tómalo como una aproximación."
        )

    # Reparto del 100 % entre los cinco rasgos (lo pidió el docente)
    distribucion = _distribucion(big_five)
    for rasgo in RASGOS:
        big_five[rasgo]["porcentaje"] = distribucion[rasgo]
    dominante = max(RASGOS, key=lambda r: distribucion[r])

    intereses = _intereses(datos)

    resultado.update({
        "datos_suficientes": True,
        "base_analisis": base_analisis,
        "big_five": big_five,
        "distribucion": distribucion,
        "rasgo_dominante": dominante,
        "intereses_principales": intereses,
        "resumen": _resumen(username, big_five, dominante, intereses, base_analisis),
    })
    return resultado


def _distribucion(big_five: dict) -> dict:
    """
    Reparte el 100 % entre los cinco rasgos de forma que se note cuál predomina.

    Problema del reparto simple (puntaje ÷ suma): como los puntajes suelen estar
    cerca de 50, todos quedan cerca de 20 % y no se distingue nada.

    Solución: ponderación exponencial (softmax, la misma que usan los modelos de
    clasificación para convertir puntajes en probabilidades):
        1. peso del rasgo = e ^ ((puntaje - 50) / SUAVIDAD_DISTRIBUCION)
        2. porcentaje     = peso del rasgo / (suma de los 5 pesos) × 100
    Con SUAVIDAD_DISTRIBUCION = 6, cada 6 puntos más multiplican el peso por e (≈2,7).
    Así, un rasgo con 61 tiene unas 6 veces más peso que uno con 50.
    Ejemplo: puntajes 59, 50, 61, 54, 56 -> 27,3 %, 6,1 %, 38,1 %, 11,9 %, 16,6 %.

    Al redondear a un decimal la suma podría dar 99,9 o 100,1. Para evitarlo se usa
    el método del "mayor resto": se trabaja en décimas (el total es 1000), se toma la
    parte entera de cada rasgo y las décimas que faltan se reparten a los rasgos que
    perdieron más al redondear.
    """
    pesos = {r: math.exp((big_five[r]["puntaje"] - 50) / SUAVIDAD_DISTRIBUCION) for r in RASGOS}
    total = sum(pesos.values())

    decimas = {r: pesos[r] / total * 1000 for r in RASGOS}
    enteras = {r: int(decimas[r]) for r in RASGOS}
    faltan = 1000 - sum(enteras.values())
    # Los rasgos con mayor parte decimal perdida reciben una décima extra
    for r in sorted(RASGOS, key=lambda r: decimas[r] - enteras[r], reverse=True)[:faltan]:
        enteras[r] += 1
    return {r: enteras[r] / 10 for r in RASGOS}


def _puntuar_rasgo(rasgo, propios, compartidos, total_palabras, ajustes):
    """
    Calcula el puntaje de un rasgo:
        puntaje = 50 + aporte_texto + aporte_metricas

    aporte_texto: (palabras a favor - palabras en contra) por cada 100 palabras,
    multiplicado por FACTOR_TEXTO. Se multiplica además por un "suavizado"
    total / (total + 50): con 50 palabras el aporte se reduce a la mitad y con 1000
    palabras casi no se reduce. Así un perfil con poco texto no obtiene puntajes extremos
    por dos o tres palabras sueltas.
    """
    lexico = LEXICO[rasgo]
    a_favor = _contar_ponderado(propios, compartidos, lexico["sube"], lexico["emojis_sube"])
    en_contra = _contar_ponderado(propios, compartidos, lexico["baja"], lexico["emojis_baja"])
    n_favor, n_contra = sum(a_favor.values()), sum(en_contra.values())

    densidad = (n_favor - n_contra) / max(total_palabras, 1) * 100
    suavizado = total_palabras / (total_palabras + PALABRAS_SUAVIZADO)
    aporte_texto = _limitar(densidad * FACTOR_TEXTO * suavizado, MAX_APORTE_TEXTO)
    aporte_metricas = _limitar(sum(puntos for puntos, _ in ajustes), MAX_APORTE_METRICAS)
    puntaje = round(max(0, min(100, PUNTAJE_BASE + aporte_texto + aporte_metricas)))

    # Evidencia: las palabras más frecuentes de cada lado y los ajustes aplicados
    evidencia = []
    if a_favor:
        evidencia.append("A favor: " + _listar(a_favor))
    if en_contra:
        evidencia.append("En contra: " + _listar(en_contra))
    evidencia += [f"{texto} ({puntos:+d})" for puntos, texto in ajustes]
    if not evidencia:
        evidencia.append("No se encontraron palabras ni señales de este rasgo.")

    # Confianza: depende de cuánto texto hay y de cuántas palabras del rasgo aparecieron
    coincidencias = n_favor + n_contra
    if total_palabras < 100 or coincidencias < 3:
        confianza = "baja"
    elif total_palabras < 400 or coincidencias < 8:
        confianza = "media"
    else:
        confianza = "alta"

    return {
        "puntaje": puntaje,
        "confianza": confianza,
        "justificacion": (
            f"Base {PUNTAJE_BASE} {aporte_texto:+.0f} por el texto ({n_favor:g} palabras a favor y "
            f"{n_contra:g} en contra en {total_palabras:.0f} palabras) {aporte_metricas:+.0f} por "
            f"las métricas = {puntaje}."
        ),
        "evidencia": evidencia,
        "calculo": {
            "base": PUNTAJE_BASE,
            "aporte_texto": round(aporte_texto, 1),
            "aporte_metricas": round(aporte_metricas, 1),
        },
    }


def _ajustes_por_metricas(m: dict) -> dict:
    """
    Reglas sencillas que convierten las métricas en puntos extra para cada rasgo.
    Devuelve {rasgo: [(puntos, explicación), ...]}.
    El neuroticismo no tiene reglas por métricas: solo se estima por el lenguaje.
    """
    ajustes = {rasgo: [] for rasgo in RASGOS}

    # --- Apertura: variedad de temas, audio original, variedad de cuentas que comparte
    if m["proporcion_hashtags_distintos"] is not None and m["hashtags_distintos"] >= 5:
        if m["proporcion_hashtags_distintos"] >= 0.7:
            ajustes["apertura"].append((5, f"Usa hashtags muy variados ({m['hashtags_distintos']} distintos)"))
        elif m["proporcion_hashtags_distintos"] <= 0.4:
            ajustes["apertura"].append((-5, "Repite casi siempre los mismos hashtags"))
    if (m["proporcion_sonido_original"] or 0) >= 0.5:
        ajustes["apertura"].append((3, "La mayoría de sus videos usan audio original"))
    if m["autores_distintos_en_reposts"] >= 5:
        ajustes["apertura"].append((3, f"Comparte videos de {m['autores_distintos_en_reposts']} cuentas distintas"))

    # --- Responsabilidad: constancia al publicar
    cv = m["coeficiente_variacion_dias"]
    if cv is not None:
        if cv <= 0.5:
            ajustes["responsabilidad"].append((6, "Publica con un ritmo muy regular"))
        elif cv >= 1.5:
            ajustes["responsabilidad"].append((-6, "Publica de forma muy irregular"))
    dias = m["dias_promedio_entre_videos"]
    if dias is not None and dias <= 3:
        ajustes["responsabilidad"].append((3, f"Publica con frecuencia (cada {dias:g} días en promedio)"))

    # --- Extraversión: habla en sus videos, expresividad, interacción con su público
    if (m["proporcion_videos_con_voz"] or 0) >= 0.5:
        ajustes["extraversion"].append((5, "Habla en la mayoría de sus videos"))
    if m["exclamaciones_por_100_palabras"] >= 3:
        ajustes["extraversion"].append((4, f"Usa muchas exclamaciones ({m['exclamaciones_por_100_palabras']:g} por cada 100 palabras)"))
    if m["videos_analizados"] and m["comentarios_del_creador"] / m["videos_analizados"] >= 1:
        ajustes["extraversion"].append((3, "Comenta y responde a menudo en sus videos"))

    # --- Amabilidad: atención y reconocimiento a sus seguidores
    if (m["proporcion_comentarios_con_like_del_creador"] or 0) >= 0.5:
        ajustes["amabilidad"].append((5, "Da like a la mayoría de los comentarios de sus seguidores"))
    if m["comentarios_del_creador"] >= 3:
        ajustes["amabilidad"].append((3, f"Responde a sus seguidores ({m['comentarios_del_creador']} respuestas)"))

    return ajustes


# ---------------------------------------------------------------------------
# Procesamiento del texto
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes y la virgulilla de la ñ: 'Estrés' -> 'estres'."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())  # 'é' -> 'e' + tilde suelta
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")  # quita la tilde suelta


def _palabras(texto: str) -> list[str]:
    """
    Separa el texto en palabras normalizadas. También reduce las letras repetidas
    que se usan para dar énfasis: 'graciasss' -> 'gracias', 'holaaa' -> 'hola'.
    Los hashtags también se cuentan: '#viajesecuador' -> 'viajesecuador'.
    """
    palabras = re.findall(r"[a-z]+", _normalizar(texto))
    return [re.sub(r"(.)\1{2,}", r"\1", p) for p in palabras]


def _contar(textos, entradas, emojis) -> Counter:
    """Cuenta cuántas veces aparece cada palabra (o emoji) de la lista en los textos."""
    # Separamos las entradas exactas de los prefijos (las que terminan en "*")
    exactas = {e for e in entradas if not e.endswith("*")}
    prefijos = tuple(e[:-1] for e in entradas if e.endswith("*"))

    conteo = Counter()
    for texto in textos:
        for palabra in _palabras(texto):
            if palabra.startswith(PREFIJOS_GENERICOS):
                continue  # #explore, #viral, #fyp... no dicen nada de la persona
            if palabra in exactas or palabra.startswith(prefijos):
                conteo[palabra] += 1
        for emoji in emojis:
            if emoji in texto:
                conteo[emoji] += texto.count(emoji)
    return conteo


def _contar_ponderado(propios, compartidos, entradas, emojis) -> Counter:
    """Suma lo propio con peso 1 y lo compartido con peso PESO_REPOSTS."""
    total = _contar(propios, entradas, emojis)
    for clave, cantidad in _contar(compartidos, entradas, emojis).items():
        total[clave] += cantidad * PESO_REPOSTS
    return total


def _listar(conteo: Counter, maximo=6) -> str:
    """Counter -> 'viaje (3), arte (2), ...' con las más frecuentes primero."""
    return ", ".join(f"{palabra} ({cantidad:g})" for palabra, cantidad in conteo.most_common(maximo))


def _limitar(valor, maximo):
    return max(-maximo, min(maximo, valor))


# ---------------------------------------------------------------------------
# Intereses y resumen
# ---------------------------------------------------------------------------

def _intereses(datos: dict) -> list[str]:
    """Los hashtags más usados (propios y compartidos), sin los genéricos como #fyp."""
    conteo = Counter()
    for video in datos.get("videos", []) + datos.get("reposts", []):
        for hashtag in video.get("hashtags", []):
            if not _normalizar(hashtag).startswith(PREFIJOS_GENERICOS):
                conteo[hashtag.lower()] += 1
    return ["#" + h for h, _ in conteo.most_common(6)]


def _nivel(puntaje: int) -> str:
    if puntaje >= 60:
        return "alto"
    if puntaje <= 40:
        return "bajo"
    return "medio"


def _resumen(username: str, big_five: dict, dominante: str, intereses: list[str], base_analisis: str) -> str:
    """Arma un párrafo legible a partir de los puntajes (plantilla, sin IA)."""
    partes = [f"{NOMBRES[r].lower()} en nivel {_nivel(big_five[r]['puntaje'])} ({big_five[r]['puntaje']})" for r in RASGOS]
    if base_analisis == "compartidos":
        texto = (
            f"Según lo que @{username} comparte (casi no publica texto propio), su perfil "
            f"sugiere {', '.join(partes[:-1])} y {partes[-1]}."
        )
    else:
        texto = f"Según el análisis por diccionario, @{username} muestra {', '.join(partes[:-1])} y {partes[-1]}."
    texto += (
        f" Su rasgo predominante es {NOMBRES[dominante].lower()}, con el "
        f"{big_five[dominante]['porcentaje']:g} % de la distribución."
    )

    if intereses:
        texto += f" Sus temas más frecuentes son {', '.join(intereses[:3])}."

    # En el plan B todos los rasgos tienen confianza baja; el aviso ya lo explica
    poca_evidencia = [NOMBRES[r].lower() for r in RASGOS if big_five[r]["confianza"] == "baja"]
    if poca_evidencia and base_analisis != "compartidos":
        texto += f" Hay poca evidencia para: {', '.join(poca_evidencia)}."
    return texto
