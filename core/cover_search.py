import os
import requests

def search_cover_online(title, author, output_dir):
    """Busca una portada en la API de Google Books basándose en el título y autor."""
    try:
        query = title
        if author and author != "Desconocido":
            query += f"+inauthor:{author}"
            
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "items" in data and len(data["items"]) > 0:
                volume_info = data["items"][0].get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})
                
                # Intentar obtener la mejor imagen disponible (thumbnail)
                img_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
                
                if img_url:
                    # Algunas URLs vienen como http en lugar de https, forzamos https
                    img_url = img_url.replace("http://", "https://")
                    
                    img_response = requests.get(img_url, timeout=10)
                    if img_response.status_code == 200:
                        safe_title = "".join([c if c.isalnum() else "_" for c in title])
                        cover_path = os.path.join(output_dir, f"{safe_title}_online_cover.jpg")
                        
                        with open(cover_path, "wb") as f:
                            f.write(img_response.content)
                        return cover_path
        return None
    except Exception as e:
        print(f"Error en búsqueda online de portada para '{title}': {e}")
        return None
