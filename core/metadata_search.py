import os
import requests
import time

def robust_get(url, retries=3, backoff_factor=1.5):
    """Realiza una petición GET de manera segura con reintentos."""
    for attempt in range(retries):
        try:
            # Fakeamos los headers para evitar ser bloqueados por user-agent genérico
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            # Retornar cualquier respuesta que no sea de error grave de conexión temporal
            return response
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt < retries - 1:
                time.sleep(backoff_factor * (attempt + 1))
            else:
                return None
    return None

def download_image(url, output_path):
    """Descarga la imagen con reintentos."""
    response = robust_get(url)
    if response and response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        return True
    return False

def search_metadata_online(title, author, output_dir):
    """
    Busca metadatos y portada en Google Books. 
    Si no encuentra la portada, intenta buscarla en OpenLibrary.
    Retorna diccionario con resultados hallados.
    """
    result = {
        "title": None,
        "author": None,
        "tags": None,
        "cover_path": None
    }
    
    # Limpiamos parte del título que puede dificultar búsqueda. Extensión PDF y otras hierbas.
    # Eliminamos el .pdf para usar de manera más limpia, aunque usualmente ya viene filtrado en meta.title.
    clean_title = str(title).replace(".pdf", "").replace(".PDF", "")

    query = clean_title
    if author and author != "Desconocido":
        query += f"+inauthor:{author}"
        
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
    response = robust_get(url)
    
    # Limitar el nombre del archivo a 50 caracteres para evitar errores de sistema/git
    safe_title = "".join([c if c.isalnum() else "_" for c in clean_title])[:50]
    
    # === Analizar Resultados de Google Books ===
    if response and response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            volume_info = data["items"][0].get("volumeInfo", {})
            
            result["title"] = volume_info.get("title")
            authors = volume_info.get("authors", [])
            if authors:
                result["author"] = ", ".join(authors)
            
            categories = volume_info.get("categories", [])
            if categories:
                result["tags"] = ", ".join(categories)
            
            # Buscar Portada
            image_links = volume_info.get("imageLinks", {})
            img_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
            
            if img_url:
                img_url = img_url.replace("http://", "https://")
                cover_path = os.path.join(output_dir, f"{safe_title}_online_cover.jpg")
                if download_image(img_url, cover_path):
                    result["cover_path"] = cover_path
                    return result # Encontramos todo, salimos de una.

    # === Fallback: Buscar Portada en OpenLibrary ===
    # Si Google falló en darnos la imagen o simplemente los datos enteros fallaron o no hay cover
    if not result["cover_path"]:
        # Podemos intentar una búsqueda por título exacto en OpenLibrary
        ol_url = f"https://openlibrary.org/search.json?q={clean_title}&limit=1"
        ol_response = robust_get(ol_url)
        if ol_response and ol_response.status_code == 200:
            ol_data = ol_response.json()
            if "docs" in ol_data and len(ol_data["docs"]) > 0:
                doc = ol_data["docs"][0]
                
                # Si google falló y no tenemos ni título, adoptamos lo de open library
                if not result["title"] and "title" in doc:
                    result["title"] = doc["title"]
                if not result["author"] and "author_name" in doc:
                    result["author"] = doc["author_name"][0]
                if not result["tags"] and "subject" in doc:
                    result["tags"] = ", ".join(doc["subject"][:3]) # las primeras 3 materias
                    
                # Si encontramos un ID de cover, la bajamos
                if "cover_i" in doc:
                    cover_id = doc["cover_i"]
                    img_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                    cover_path = os.path.join(output_dir, f"{safe_title}_ol_cover.jpg")
                    if download_image(img_url, cover_path):
                        result["cover_path"] = cover_path

    return result if any(v is not None for v in result.values()) else None
