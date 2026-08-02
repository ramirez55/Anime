# config.py

# --- Configuración de Telegram ---
# Obtén tu token de BotFather en Telegram (envía /newbot a @BotFather)
TELEGRAM_BOT_TOKEN = "8715145205:AAEyoe5MNsYDNixfCLDJabHrMrfdDkYMVak"

# Tu ID de usuario de Telegram. Esto es necesario para los comandos de administrador.
# Puedes obtener tu ID enviando /id a @userinfobot o @getidsbot en Telegram.
ADMIN_USER_IDS = [TU_ID_DE_USUARIO_ADMIN_AQUI] # Ejemplo: [123456789]

# El ID del chat o grupo donde el bot enviará las notificaciones de nuevos episodios.
# Si es un grupo, agrega el bot al grupo, haz que envíe un mensaje,
# y luego reenvía un mensaje del bot a @getidsbot para obtener el Chat ID.
# Los IDs de grupo suelen empezar con -100.
NOTIFICATION_CHAT_ID = TU_ID_DE_CHAT_DE_NOTIFICACIONES_AQUI # Ejemplo: -1001234567890

# --- Intervalo de comprobación ---
# Frecuencia con la que el bot revisará nuevos episodios (en minutos).
# No se recomienda un valor muy bajo para evitar sobrecargar la API de AniList o de Telegram.
CHECK_INTERVAL_MINUTES = 60 # Cada 60 minutos (1 hora)

# --- Configuración de la Base de Datos ---
DATABASE_NAME = "anilist_notifier.db"

# --- Configuración de AniList (no necesita cambios) ---
ANILIST_API_URL = "https://graphql.anilist.co"
