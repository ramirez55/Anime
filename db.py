# db.py
import sqlite3
import logging
from config import DATABASE_NAME

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db():
    """Inicializa la base de datos y crea la tabla si no existe."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS followed_anime (
                anilist_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                next_episode INTEGER,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logging.info("Base de datos inicializada correctamente.")
    except sqlite3.Error as e:
        logging.error(f"Error al inicializar la base de datos: {e}")

def add_followed_anime(anilist_id, title, next_episode=None):
    """Agrega un anime a la lista de seguidos."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO followed_anime (anilist_id, title, next_episode) VALUES (?, ?, ?)",
                       (anilist_id, title, next_episode))
        conn.commit()
        conn.close()
        logging.info(f"Anime '{title}' (ID: {anilist_id}) agregado a la base de datos.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error al agregar anime {title} (ID: {anilist_id}): {e}")
        return False

def remove_followed_anime(anilist_id):
    """Elimina un anime de la lista de seguidos."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM followed_anime WHERE anilist_id = ?", (anilist_id,))
        conn.commit()
        conn.close()
        logging.info(f"Anime con ID {anilist_id} eliminado de la base de datos.")
        return True
    except sqlite3.Error as e:
        logging.error(f"Error al eliminar anime con ID {anilist_id}: {e}")
        return False

def get_followed_anime():
    """Obtiene todos los animes seguidos de la base de datos."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT anilist_id, title, next_episode FROM followed_anime")
        animes = cursor.fetchall()
        conn.close()
        return animes
    except sqlite3.Error as e:
        logging.error(f"Error al obtener animes seguidos: {e}")
        return []

def update_next_episode(anilist_id, next_episode):
    """Actualiza el número del próximo episodio de un anime."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE followed_anime SET next_episode = ?, last_checked = CURRENT_TIMESTAMP WHERE anilist_id = ?",
                       (next_episode, anilist_id))
        conn.commit()
        conn.close()
        logging.info(f"Actualizado próximo episodio para ID {anilist_id} a {next_episode}.")
    except sqlite3.Error as e:
        logging.error(f"Error al actualizar próximo episodio para ID {anilist_id}: {e}")

def get_anime_by_id(anilist_id):
    """Obtiene un anime específico por su ID de AniList."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT anilist_id, title, next_episode FROM followed_anime WHERE anilist_id = ?", (anilist_id,))
        anime = cursor.fetchone()
        conn.close()
        return anime
    except sqlite3.Error as e:
        logging.error(f"Error al obtener anime por ID {anilist_id}: {e}")
        return None

def get_followed_anime_count():
    """Obtiene el número de animes seguidos."""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM followed_anime")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except sqlite3.Error as e:
        logging.error(f"Error al contar animes seguidos: {e}")
        return 0

if __name__ == "__main__":
    init_db()
    # Ejemplo de uso (solo para pruebas directas de db.py)
    # add_followed_anime(12345, "Ejemplo Anime", 1)
    # animes = get_followed_anime()
    # print("Animes seguidos:", animes)
    # update_next_episode(12345, 2)
    # animes = get_followed_anime()
    # print("Animes seguidos después de actualizar:", animes)
    # remove_followed_anime(12345)
    # animes = get_followed_anime()
    # print("Animes seguidos después de eliminar:", animes)
