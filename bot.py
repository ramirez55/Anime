# bot.py
import logging
import asyncio
from datetime import datetime, timedelta
import pytz # Para manejar zonas horarias
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS, NOTIFICATION_CHAT_ID, CHECK_INTERVAL_MINUTES
from db import init_db, add_followed_anime, remove_followed_anime, get_followed_anime, update_next_episode, get_anime_by_id, get_followed_anime_count
from anilist_api import search_anime, get_anime_details

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Comandos para usuarios ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje de bienvenida cuando se inicia el bot."""
    user = update.effective_user
    await update.message.reply_html(
        f"¡Hola {user.mention_html()}!\n\n"
        "Soy tu bot personal de AniList para seguir tus animes favoritos. "
        "Te notificaré cuando se emitan nuevos episodios.\n\n"
        "Para empezar a seguir un anime, usa el comando /addanime seguido del nombre del anime. "
        "Ejemplo: XXXINLINECODEXXX9XXXINLINECODEXXX\n\n"
        "Otros comandos:\n"
        "/listanime - Ver los animes que estás siguiendo.\n"
        "/removeanime - Eliminar un anime de la lista.\n"
        "/help - Muestra esta ayuda nuevamente."
    )
    logger.info(f"Comando /start ejecutado por {user.id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envía un mensaje de ayuda."""
    await update.message.reply_html(
        "Aquí tienes los comandos disponibles:\n\n"
        "<b>Comandos de Usuario:</b>\n"
        "/addanime &lt;nombre del anime&gt; - Busca y agrega un anime para seguir.\n"
        "/listanime - Muestra la lista de todos los animes que estás siguiendo.\n"
        "/removeanime - Te permite eliminar un anime de tu lista de seguimiento.\n"
        "/help - Muestra esta información de ayuda.\n\n"
        "<b>Comandos de Administrador (solo para administradores):</b>\n"
        "/admin_status - Muestra el estado actual del bot y la tarea de comprobación.\n"
        "/admin_reschedule &lt;minutos&gt; - Cambia el intervalo de la tarea de comprobación.\n"
        "/admin_force_check - Fuerza una comprobación inmediata de todos los animes.\n\n"
        "¡Recuerda que solo los administradores pueden usar los comandos /admin_! "
        "Si tienes alguna pregunta o necesitas ayuda, no dudes en preguntar."
    )
    logger.info(f"Comando /help ejecutado por {update.effective_user.id}")

async def add_anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Busca un anime por el título proporcionado y ofrece opciones para seguirlo.
    """
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Por favor, proporciona el nombre del anime que deseas agregar. Ejemplo: XXXINLINECODEXXX10XXXINLINECODEXXX")
        return

    await update.message.reply_text(f"Buscando animes para '{query}'...")
    results = await asyncio.to_thread(search_anime, query)

    if results is None:
        await update.message.reply_text("Hubo un error al conectar con AniList. Por favor, inténtalo de nuevo más tarde.")
        return
    elif not results:
        await update.message.reply_text(f"No se encontraron animes para '{query}'. Intenta con un nombre diferente.")
        return

    keyboard_buttons = []
    message_text = "Se encontraron varios resultados. Por favor, selecciona el anime que deseas seguir:\n\n"

    for i, anime in enumerate(results):
        title = anime['title']
        status = anime['status'].replace('_', ' ').title() if anime['status'] else 'Desconocido'
        episodes = anime['episodes'] if anime['episodes'] else '?'
        year = anime['year'] if anime['year'] else '?'
        
        message_text += f"<b>{i+1}. {title}</b> ({status}, {episodes} eps, {year})\n"
        keyboard_buttons.append([InlineKeyboardButton(f"{i+1}. {title}", callback_data=f"add_{anime['id']}")])

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_html(message_text, reply_markup=reply_markup)
    logger.info(f"Comando /addanime ejecutado por {update.effective_user.id} para '{query}'. Resultados mostrados.")

async def list_anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra la lista de animes que el bot está siguiendo."""
    animes = await asyncio.to_thread(get_followed_anime)

    if not animes:
        await update.message.reply_text("Actualmente no estás siguiendo ningún anime. Usa /addanime para empezar a seguir uno.")
        return

    message_text = "<b>Animes que estás siguiendo:</b>\n\n"
    for anilist_id, title, next_episode in animes:
        if next_episode is not None:
            message_text += f"• <b>{title}</b> (Próx. Ep: {next_episode}, ID: {anilist_id})\n"
        else:
            message_text += f"• <b>{title}</b> (Estado del próximo episodio desconocido, ID: {anilist_id})\n"

    await update.message.reply_html(message_text)
    logger.info(f"Comando /listanime ejecutado por {update.effective_user.id}. {len(animes)} animes listados.")

async def remove_anime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Permite al usuario seleccionar un anime de la lista para eliminarlo."""
    animes = await asyncio.to_thread(get_followed_anime)

    if not animes:
        await update.message.reply_text("No hay animes que estés siguiendo para eliminar.")
        return

    keyboard_buttons = []
    message_text = "Selecciona el anime que deseas dejar de seguir:\n\n"

    for i, (anilist_id, title, _) in enumerate(animes):
        message_text += f"<b>{i+1}. {title}</b> (ID: {anilist_id})\n"
        keyboard_buttons.append([InlineKeyboardButton(f"{i+1}. {title}", callback_data=f"remove_{anilist_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard_buttons)
    await update.message.reply_html(message_text, reply_markup=reply_markup)
    logger.info(f"Comando /removeanime ejecutado por {update.effective_user.id}. Opciones de eliminación mostradas.")

# --- Callbacks para botones inline ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja las interacciones con los botones inline."""
    query = update.callback_query
    await query.answer() # Siempre responde a la callback query para que el botón no siga 'cargando'

    data_parts = query.data.split('_')
    action = data_parts[0]
    anilist_id = int(data_parts[1])

    if action == "add":
        # Verificar si el anime ya está siendo seguido
        existing_anime = await asyncio.to_thread(get_anime_by_id, anilist_id)
        if existing_anime:
            await query.edit_message_text(f"Ya estás siguiendo '{existing_anime[1]}'.")
            return

        # Obtener detalles completos para el título exacto y el próximo episodio
        anime_details = await asyncio.to_thread(get_anime_details, anilist_id)

        if anime_details:
            title = anime_details['title']
            next_episode = anime_details['next_episode']
            
            success = await asyncio.to_thread(add_followed_anime, anilist_id, title, next_episode)
            if success:
                status_text = f"El anime <b>{title}</b> (ID: {anilist_id}) ha sido agregado a tu lista de seguimiento."
                if next_episode:
                    status_text += f"\nPróximo episodio esperado: {next_episode}."
                else:
                    status_text += "\nNo se encontró información del próximo episodio por ahora."

                await query.edit_message_text(status_text, parse_mode='HTML')
                logger.info(f"Anime ID {anilist_id} ('{title}') agregado por {query.from_user.id}.")
            else:
                await query.edit_message_text(f"Hubo un error al agregar el anime (ID: {anilist_id}). Por favor, inténtalo de nuevo.")
        else:
            await query.edit_message_text(f"No se pudieron obtener los detalles para el anime con ID {anilist_id}. Inténtalo de nuevo.")

    elif action == "remove":
        anime_info = await asyncio.to_thread(get_anime_by_id, anilist_id)
        if anime_info:
            title = anime_info[1]
            success = await asyncio.to_thread(remove_followed_anime, anilist_id)
            if success:
                await query.edit_message_text(f"El anime <b>{title}</b> (ID: {anilist_id}) ha sido eliminado de tu lista de seguimiento.", parse_mode='HTML')
                logger.info(f"Anime ID {anilist_id} ('{title}') eliminado por {query.from_user.id}.")
            else:
                await query.edit_message_text(f"Hubo un error al eliminar el anime (ID: {anilist_id}). Por favor, inténtalo de nuevo.")
        else:
            await query.edit_message_text(f"El anime con ID {anilist_id} no se encontró en tu lista de seguimiento.")

# --- Tareas programadas ---

async def check_for_new_episodes(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Función programada para revisar nuevos episodios de los animes seguidos.
    """
    logger.info("Iniciando la comprobación de nuevos episodios...")
    animes = await asyncio.to_thread(get_followed_anime)
    
    if not animes:
        logger.info("No hay animes seguidos para comprobar.")
        return

    # Usamos una lista para almacenar los mensajes de notificación
    notifications = []

    for anilist_id, title, stored_next_episode in animes:
        anime_details = await asyncio.to_thread(get_anime_details, anilist_id)
        
        if anime_details is None:
            logger.warning(f"No se pudieron obtener detalles para el anime ID {anilist_id} ('{title}'). Saltando.")
            continue
        
        current_next_episode = anime_details['next_episode']
        airing_at_unix = anime_details['airing_at']
        total_episodes = anime_details['total_episodes']
        cover_image_url = anime_details['cover_image']
        site_url = anime_details['site_url']
        status = anime_details['status']

        # Considerar animes que ya finalizaron y eliminar si es el caso.
        if status in ["FINISHED", "CANCELLED"] and stored_next_episode is None:
             # Si no hay stored_next_episode y ya terminó, significa que no lo rastreamos correctamente o ya no hay episodios
            if total_episodes is not None and stored_next_episode is None: # Si ya tiene total_episodes y no hay next_episode
                # Esto es para manejar casos donde un anime es agregado y ya está terminado, o se detecta que terminó.
                # Si total_episodes existe y next_episode es nulo, significa que ya no hay mas episodios o ya terminó
                logger.info(f"Anime '{title}' (ID: {anilist_id}) detectado como {status}. Eliminando de la lista de seguimiento.")
                await asyncio.to_thread(remove_followed_anime, anilist_id)
                notifications.append(f"El anime <b>{title}</b> (ID: {anilist_id}) ha finalizado o sido cancelado. Ha sido eliminado de tu lista de seguimiento.")
            continue # No hay más episodios que rastrear.
        
        # Convertir airing_at de UNIX timestamp a objeto datetime
        airing_datetime = None
        if airing_at_unix:
            airing_datetime = datetime.fromtimestamp(airing_at_unix, tz=pytz.utc)

        # Si el anime ya no tiene un próximo episodio, y no es un anime finalizado
        if current_next_episode is None and status not in ["FINISHED", "CANCELLED"]:
            if stored_next_episode is not None:
                # El anime tenía un próximo episodio, pero ahora ya no. Esto podría significar que terminó o hay un retraso.
                # Actualizamos a None para esperar el siguiente
                await asyncio.to_thread(update_next_episode, anilist_id, None)
                logger.info(f"El anime '{title}' (ID: {anilist_id}) ya no tiene información del próximo episodio. Actualizando a None.")
            continue
        
        # Si stored_next_episode es None (primera vez que lo comprobamos o se actualizó a None previamente)
        # o si el episodio actual de AniList es mayor que el que teníamos guardado
        if current_next_episode is not None and (stored_next_episode is None or current_next_episode > stored_next_episode):
            # Comprobamos si el episodio ya debería haber sido emitido
            if airing_datetime and datetime.now(pytz.utc) > airing_datetime:
                # Hay un nuevo episodio
                episode_number = current_next_episode
                
                notification_text = (
                    f"🎉 ¡Nuevo episodio de <b>{title}</b>!\n"
                    f"Episodio <b>{episode_number}</b> ya disponible.\n"
                    f"<a href='{site_url}'>Ver en AniList</a>"
                )
                notifications.append((notification_text, cover_image_url))
                
                # Actualizar el próximo episodio en la base de datos
                await asyncio.to_thread(update_next_episode, anilist_id, episode_number)
                logger.info(f"Nuevo episodio {episode_number} de '{title}' (ID: {anilist_id}) detectado y notificado.")
            elif airing_datetime:
                # El episodio aún no se ha emitido, pero AniList ya lo ha listado
                logger.info(f"Próximo episodio {current_next_episode} de '{title}' (ID: {anilist_id}) listado, pero aún no se emite.")
                # Actualizar el próximo episodio en la base de datos aunque aún no se haya emitido
                await asyncio.to_thread(update_next_episode, anilist_id, current_next_episode)
        
        # Manejar el caso de animes que ya terminaron después de ser rastreados
        if status == "FINISHED" and total_episodes is not None and stored_next_episode == total_episodes:
            logger.info(f"Anime '{title}' (ID: {anilist_id}) ha llegado a su último episodio ({total_episodes}). Eliminando de la lista de seguimiento.")
            await asyncio.to_thread(remove_followed_anime, anilist_id)
            notifications.append(f"El anime <b>{title}</b> (ID: {anilist_id}) ha finalizado con el episodio {total_episodes}. Ha sido eliminado de tu lista de seguimiento.")
            
    # Enviar todas las notificaciones acumuladas al chat de notificaciones
    if notifications:
        for notif_content in notifications:
            if isinstance(notif_content, tuple): # Si tiene imagen
                text, image_url = notif_content
                try:
                    await context.bot.send_photo(
                        chat_id=NOTIFICATION_CHAT_ID,
                        photo=image_url,
                        caption=text,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error al enviar notificación con imagen para '{text}': {e}")
                    # Enviar solo texto si la imagen falla
                    await context.bot.send_message(
                        chat_id=NOTIFICATION_CHAT_ID,
                        text=text,
                        parse_mode='HTML'
                    )
                await asyncio.sleep(0.5) # Pequeña pausa para no saturar la API
            else: # Solo texto
                await context.bot.send_message(
                    chat_id=NOTIFICATION_CHAT_ID,
                    text=notif_content,
                    parse_mode='HTML'
                )
                await asyncio.sleep(0.5)

    logger.info("Comprobación de nuevos episodios finalizada.")
    
# --- Comandos de Administrador ---

def is_admin(user_id: int) -> bool:
    """Verifica si un usuario es administrador."""
    return user_id in ADMIN_USER_IDS

async def admin_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el estado del bot (solo para administradores)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("¡No tienes permiso para usar este comando!")
        return

    # Obtener el próximo job de la cola de APScheduler
    next_run_time = "N/A"
    current_interval = "N/A"
    
    scheduler: AsyncIOScheduler = context.job_queue.scheduler # Acceder al scheduler
    jobs = scheduler.get_jobs()
    
    for job in jobs:
        if job.id == 'episode_checker':
            next_run_time = job.next_run_time.astimezone(pytz.timezone('America/Santiago')).strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else "Ya no hay próxima ejecución"
            if isinstance(job.trigger, IntervalTrigger):
                current_interval = f"{job.trigger.interval.total_seconds() / 60:.0f} minutos"
            break

    anime_count = await asyncio.to_thread(get_followed_anime_count)
    
    status_message = (
        f"<b>Estado del Bot:</b>\n"
        f"Animes seguidos: {anime_count}\n"
        f"Intervalo de comprobación: {current_interval}\n"
        f"Próxima comprobación: {next_run_time}\n"
        f"ID del Chat de Notificaciones: <code>{NOTIFICATION_CHAT_ID}</code>"
    )
    await update.message.reply_html(status_message)
    logger.info(f"Comando /admin_status ejecutado por {update.effective_user.id}.")

async def admin_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Cambia el intervalo de la tarea de comprobación de episodios (solo para administradores).
    Uso: /admin_reschedule <minutos>
    """
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("¡No tienes permiso para usar este comando!")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Uso: /admin_reschedule <minutos>. Por favor, proporciona un número de minutos válido.")
        return

    new_interval_minutes = int(context.args[0])
    if new_interval_minutes < 1:
        await update.message.reply_text("El intervalo debe ser al menos 1 minuto.")
        return

    scheduler: AsyncIOScheduler = context.job_queue.scheduler
    
    # Remover el job existente si lo hay
    if scheduler.get_job('episode_checker'):
        scheduler.remove_job('episode_checker')

    # Añadir el nuevo job con el nuevo intervalo
    scheduler.add_job(
        check_for_new_episodes,
        trigger=IntervalTrigger(minutes=new_interval_minutes),
        id='episode_checker',
        name='Comprobación de episodios de AniList',
        next_run_time=datetime.now(pytz.utc) + timedelta(seconds=5), # Ejecutar ~5 segundos después de reagendar
        args=[context]
    )

    await update.message.reply_text(f"El intervalo de comprobación ha sido cambiado a {new_interval_minutes} minutos.")
    logger.info(f"Comando /admin_reschedule ejecutado por {update.effective_user.id}. Nuevo intervalo: {new_interval_minutes} min.")

async def admin_force_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fuerza una comprobación inmediata de nuevos episodios (solo para administradores)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("¡No tienes permiso para usar este comando!")
        return

    await update.message.reply_text("Forzando una comprobación inmediata de nuevos episodios...")
    logger.info(f"Comando /admin_force_check ejecutado por {update.effective_user.id}. Ejecutando check_for_new_episodes.")
    await check_for_new_episodes(context)
    await update.message.reply_text("Comprobación forzada completada.")


# --- Función principal del bot ---

async def main() -> None:
    """Configura y ejecuta el bot."""
    # Inicializar la base de datos
    init_db()

    # Crear la aplicación de Telegram
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Obtener el scheduler de APScheduler desde la aplicación
    scheduler = AsyncIOScheduler()
    application.job_queue.scheduler = scheduler # Asignar el scheduler a la aplicación

    # Registrar manejadores de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addanime", add_anime_command))
    application.add_handler(CommandHandler("listanime", list_anime_command))
    application.add_handler(CommandHandler("removeanime", remove_anime_command))
    
    # Manejador de callbacks para botones inline
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Registrar comandos de administrador
    application.add_handler(CommandHandler("admin_status", admin_status))
    application.add_handler(CommandHandler("admin_reschedule", admin_reschedule))
    application.add_handler(CommandHandler("admin_force_check", admin_force_check))

    # Manejar mensajes no conocidos
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message)) # Para el eco de mensajes

    # Añadir la tarea programada para comprobar nuevos episodios
    scheduler.add_job(
        check_for_new_episodes,
        trigger=IntervalTrigger(minutes=CHECK_INTERVAL_MINUTES),
        id='episode_checker', # ID único para el job
        name='Comprobación de episodios de AniList',
        next_run_time=datetime.now(pytz.utc) + timedelta(seconds=5), # Ejecutar la primera vez ~5 segundos después de iniciar
        args=[application.job_queue.job_contexts[0]] # Pasar el context al job
    )
    scheduler.start()
    logger.info("Scheduler de APScheduler iniciado.")

    # Iniciar el bot
    logger.info("Iniciando polling del bot...")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a comandos que el bot no reconoce."""
    await update.message.reply_text("Lo siento, no reconozco ese comando. Usa /help para ver los comandos disponibles.")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eco de los mensajes que no son comandos."""
    # Desactivado para evitar respuestas spammy, pero puede ser útil para depuración.
    # await update.message.reply_text(f"Dijiste: {update.message.text}")
    pass


if __name__ == "__main__":
    # Asegurarse de que el bot se ejecute de forma asíncrona
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido manualmente.")
    except Exception as e:
        logger.error(f"Error crítico en el bot: {e}")
