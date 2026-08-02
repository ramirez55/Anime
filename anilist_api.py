# anilist_api.py
import requests
import logging
from config import ANILIST_API_URL

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def search_anime(title):
    """
    Busca un anime por título en AniList.
    Devuelve una lista de diccionarios con id y title, o None si hay error.
    """
    query = """
    query ($search: String) {
        Page (perPage: 10) {
            media (search: $search, type: ANIME, sort: SEARCH_MATCH) {
                id
                title {
                    romaji
                    english
                    native
                }
                status
                episodes
                startDate {
                    year
                }
            }
        }
    }
    """
    variables = {
        'search': title
    }
    try:
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx
        data = response.json()

        results = []
        if data and 'data' in data and 'Page' in data['data'] and data['data']['Page']['media']:
            for media_item in data['data']['Page']['media']:
                title_obj = media_item.get('title', {})
                # Preferir romaji, luego english, luego native
                display_title = title_obj.get('romaji') or title_obj.get('english') or title_obj.get('native')
                if display_title:
                    results.append({
                        'id': media_item['id'],
                        'title': display_title,
                        'status': media_item.get('status'),
                        'episodes': media_item.get('episodes'),
                        'year': media_item.get('startDate', {}).get('year')
                    })
        return results
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red o HTTP al buscar anime '{title}': {e}")
        return None
    except KeyError as e:
        logging.error(f"Faltan datos esperados en la respuesta de AniList al buscar '{title}': {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al buscar anime '{title}': {e}")
        return None

def get_anime_details(anilist_id):
    """
    Obtiene los detalles de un anime por su ID de AniList, incluyendo el próximo episodio.
    Devuelve un diccionario con los detalles, o None si hay error o no se encuentra.
    """
    query = """
    query ($id: Int) {
        Media (id: $id, type: ANIME) {
            id
            title {
                romaji
                english
                native
            }
            status
            episodes
            coverImage {
                large
            }
            siteUrl
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
        }
    }
    """
    variables = {
        'id': anilist_id
    }
    try:
        response = requests.post(ANILIST_API_URL, json={'query': query, 'variables': variables})
        response.raise_for_status()
        data = response.json()

        if data and 'data' in data and 'Media' in data['data'] and data['data']['Media']:
            media = data['data']['Media']
            title_obj = media.get('title', {})
            display_title = title_obj.get('romaji') or title_obj.get('english') or title_obj.get('native')
            
            next_episode_info = media.get('nextAiringEpisode')
            
            details = {
                'id': media['id'],
                'title': display_title,
                'status': media.get('status'),
                'total_episodes': media.get('episodes'),
                'cover_image': media.get('coverImage', {}).get('large'),
                'site_url': media.get('siteUrl'),
                'next_episode': None,
                'airing_at': None,
                'time_until_airing': None
            }

            if next_episode_info:
                details['next_episode'] = next_episode_info.get('episode')
                details['airing_at'] = next_episode_info.get('airingAt')
                details['time_until_airing'] = next_episode_info.get('timeUntilAiring')
            
            return details
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de red o HTTP al obtener detalles del anime ID {anilist_id}: {e}")
        return None
    except KeyError as e:
        logging.error(f"Faltan datos esperados en la respuesta de AniList para ID {anilist_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error inesperado al obtener detalles del anime ID {anilist_id}: {e}")
        return None

if __name__ == "__main__":
    # Ejemplo de uso (solo para pruebas directas de anilist_api.py)
    # results = search_anime("attack on titan")
    # if results:
    #     print("Resultados de la búsqueda:")
    #     for anime in results:
    #         print(f"ID: {anime['id']}, Título: {anime['title']}, Estado: {anime['status']}, Episodios: {anime['episodes']}, Año: {anime['year']}")
    #
    #     if results:
    #         first_anime_id = results[0]['id']
    #         details = get_anime_details(first_anime_id)
    #         if details:
    #             print("\nDetalles del primer anime:")
    #             print(f"ID: {details['id']}")
    #             print(f"Título: {details['title']}")
    #             print(f"Estado: {details['status']}")
    #             print(f"Total Episodios: {details['total_episodes']}")
    #             print(f"Próximo Episodio: {details['next_episode']}")
    #             print(f"Fecha de Emisión (UNIX): {details['airing_at']}")
    #             print(f"Tiempo hasta Emisión (segundos): {details['time_until_airing']}")
    #             print(f"URL: {details['site_url']}")
    #             print(f"Imagen: {details['cover_image']}")
    #         else:
    #             print("No se pudieron obtener los detalles.")
    # else:
    #     print("No se encontraron resultados para la búsqueda.")
    pass
