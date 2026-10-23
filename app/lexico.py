"""
Diccionario de palabras en español para estimar los rasgos del Big Five.

Idea (la misma que usa LIWC, la herramienta clásica de psicología del lenguaje):
las palabras que una persona usa con frecuencia reflejan su personalidad. Por
ejemplo, quien habla mucho de "amigos", "fiesta" y "bailar" tiende a ser más
extravertido; quien usa "triste", "ansiedad" o "estrés" tiende a puntuar más alto
en neuroticismo. Estas asociaciones se basan en estudios como Yarkoni (2010) y
Schwartz et al. (2013), que relacionaron el lenguaje en redes sociales con el Big Five.

Cómo leer las listas:
    - "sube": palabras que SUBEN el puntaje del rasgo.
    - "baja": palabras que lo BAJAN.
    - Una palabra que termina en "*" es un PREFIJO: "viaj*" coincide con viaje,
      viajar, viajes, viajando... Sin "*" la palabra debe coincidir exacta.
    - Todo va en minúsculas y SIN tildes ni ñ (el texto se normaliza igual antes
      de comparar), así "estrés" y "estres" cuentan como la misma palabra.
    - Los emojis se cuentan aparte porque en TikTok expresan mucha emoción.

Las listas se pueden ampliar libremente: basta con agregar palabras aquí.
"""

# Groserías e insultos: en los estudios se asocian con MENOS amabilidad y
# MENOS responsabilidad, por eso se usan en las dos listas de "baja".
GROSERIAS = [
    "idiot*", "estupid*", "imbecil*", "tont*", "pendej*", "mierda*", "puta*", "puto*",
    "carajo", "verga*", "cabron*", "maldit*", "huevon*", "chucha", "hdp", "ctm",
    "perra", "wtf", "fuck*", "shit",
]

LEXICO = {
    "apertura": {
        # Arte, cultura, viajes, ideas, aprendizaje, creatividad
        "sube": [
            "arte*", "artist*", "music*", "pintur*", "pintar", "dibuj*", "disen*", "foto*",
            "crea*", "idea*", "imagin*", "inspir*", "original*", "unic*", "diferent*",
            "viaj*", "aventur*", "explor*", "descubr*", "cultur*", "idioma*", "playa*",
            "montana*", "naturalez*", "museo*", "cine", "pelicula*", "teatro", "danz*",
            "libro*", "leer", "leyendo", "lectur*", "escrib*", "poesi*", "poema*", "poeta*",
            "aprend*", "curios*", "cienc*", "filosof*", "arquitect*",
        ],
        # Preferencia por lo conocido y lo tradicional
        "baja": ["tradicion*", "costumbre*"],
        "emojis_sube": ["🎨", "✈", "🌍", "📸", "🎭", "📖", "🌄"],
        "emojis_baja": [],
    },
    "responsabilidad": {
        # Trabajo, estudio, metas, disciplina, orden
        "sube": [
            "trabaj*", "meta", "metas", "logr*", "objetivo*", "estudi*", "universidad*",
            "colegio", "clase*", "examen*", "tesis", "discipl*", "rutina*", "gym",
            "gimnasio", "entren*", "organiz*", "planific*", "plan", "proyecto*", "esfuerz*",
            "constan*", "dedicac*", "responsab*", "emprend*", "negocio*", "profesion*",
            "carrera", "cumplir", "productiv*", "enfoc*", "focus", "temprano", "ahorr*",
            "orden", "ordenad*", "limpi*", "horario*", "puntual*",
        ],
        # Pereza, desorden, improvisación (+ groserías)
        "baja": [
            "flojer*", "flojo", "floja", "pereza", "procrastin*", "olvid*", "desorden*",
            "caos", "improvis*", "vago", "vaga",
        ] + GROSERIAS,
        "emojis_sube": ["💪", "📚", "✅"],
        "emojis_baja": [],
    },
    "extraversion": {
        # Vida social, fiesta, humor, hablarle al público
        "sube": [
            "amig*", "fiesta*", "farra*", "rumba*", "parche*", "juntos", "juntas",
            "nosotros", "nosotras", "salir", "salimos", "salida*", "bail*", "party", "gente",
            "celebr*", "concierto*", "divert*", "jaj*", "jsj*", "xd", "risa*", "vamos",
            "hola", "holi*", "ustedes", "chicos", "chicas", "comenten", "comenta",
            "cuentenme", "siganme", "sigueme", "etiquet*", "energia",
        ],
        # Soledad, timidez, retraimiento
        "baja": ["soledad", "introvert*", "timid*", "verguenza", "aislad*", "callad*"],
        "emojis_sube": ["😂", "🤣", "🎉", "🥳", "💃", "🕺", "🍻", "🔥", "🎶", "😎"],
        "emojis_baja": [],
    },
    "amabilidad": {
        # Gratitud, cariño, apoyo, cortesía
        "sube": [
            "graci*", "agradec*", "amor*", "amo", "love", "lind*", "hermos*", "precios*",
            "bonit*", "bendic*", "apoy*", "ayud*", "abraz*", "beso*", "carino*", "familia*",
            "mama", "mami", "herman*", "perdon*", "porfa*", "favor", "respet*", "amable*",
            "gentil*", "felicid*", "felicit*", "orgullos*", "cuidat*", "cuidense",
        ],
        # Hostilidad, desprecio, insultos
        "baja": [
            "odi*", "asco", "asqueros*", "callate", "ridicul*", "envidi*", "basura",
        ] + GROSERIAS,
        "emojis_sube": ["❤", "🥰", "😍", "🙏", "🤗", "💕", "💖", "😘", "💗", "🫶"],
        "emojis_baja": ["🖕", "😒", "🙄", "🤬"],
    },
    "neuroticismo": {
        # Emociones negativas: tristeza, ansiedad, enojo, inseguridad
        "sube": [
            "trist*", "deprim*", "depre", "ansie*", "ansios*", "estres*", "preocup*",
            "miedo*", "temor*", "llor*", "sufr*", "dolor*", "duele", "cansad*", "agotad*",
            "harta", "harto", "enoj*", "rabia*", "ira", "frustr*", "insegur*", "nervios*",
            "angusti*", "panico", "soledad", "vacio*", "roto", "rota", "culpa*", "sad",
            "crisis", "overthink*", "odio",
        ],
        # Calma, estabilidad y emociones positivas
        "baja": [
            "tranquil*", "paz", "calma*", "relaj*", "feliz", "felices", "felicidad",
            "seren*", "positiv*", "disfrut*", "chill", "contenta", "contento", "alegr*",
        ],
        # Ojo: 😭 a veces se usa para reír ("me muero de risa"); es una limitación del método
        "emojis_sube": ["😭", "😢", "😔", "💔", "😞", "😩", "😡", "🤬", "😰", "😥", "😓"],
        "emojis_baja": ["😌", "😊", "☺"],
    },
}

# Inicio de los hashtags genéricos que se ponen solo para salir en "Para ti" y no
# dicen nada de la persona: #fyp, #fypシ゚viral, #paratiiii, #foryoupage, #xyzbca...
PREFIJOS_GENERICOS = (
    "fy", "parati", "foryou", "viral", "xyz", "abc", "explore", "capcut", "trend", "tiktok",
)
