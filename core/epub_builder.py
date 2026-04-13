import os
from ebooklib import epub

def create_epub(pdf_metadata, chapters, output_dir):
    """Crea un archivo EPUB usando ebooklib a partir de los metadatos y texto extraído."""
    book = epub.EpubBook()
    
    # Metadatos básicos
    book.set_identifier(f"id_{pdf_metadata.filename}")
    book.set_title(pdf_metadata.title)
    book.set_language('es') # Se asume español, se podría hacer dinámico
    
    if pdf_metadata.author:
        book.add_author(pdf_metadata.author)
        
    # Añadir tags/etiquetas si existen
    if pdf_metadata.tags:
        tags = [tag.strip() for tag in pdf_metadata.tags.split(",")]
        for tag in tags:
            if tag:
                # Ebooklib no tiene un soporte estándar tan directo para tags, pero se puede añadir en el metadata dublin core
                book.add_metadata('DC', 'subject', tag)

    # Añadir portada si existe
    if pdf_metadata.cover_image_path and os.path.exists(pdf_metadata.cover_image_path):
        try:
            with open(pdf_metadata.cover_image_path, 'rb') as f:
                cover_content = f.read()
            book.set_cover("cover.jpg", cover_content)
        except Exception as e:
            print(f"Error procesando imagen de portada {pdf_metadata.cover_image_path}: {e}")

    # Crear los capítulos
    epub_chapters = []
    for idx, chap_info in enumerate(chapters):
        # Crear capítulo
        chap = epub.EpubHtml(title=chap_info['title'],
                             file_name=f'chap_{idx+1}.xhtml',
                             lang='es')
        
        # Procesar texto, reemplazando saltos extraños por etiquetas <p>
        paragraphs = chap_info['content'].split('\n')
        html_content = "".join([f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()])
        
        chap.content = f"<h1>{chap_info['title']}</h1>{html_content}"
        
        book.add_item(chap)
        epub_chapters.append(chap)

    # Crear tabla de contenidos
    # Agrupar los capítulos en el TOC
    book.toc = tuple(epub_chapters)

    # Añadir navegación (NCX) e índice de navegación
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Estilos CSS básicos
    style = 'BODY {color: white;}'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    # Spinal cord: define el orden de lectura. 'nav' corresponde a la tabla de contenidos generada
    spine_items = ['nav'] + epub_chapters
    book.spine = spine_items

    # Guardar EPUB
    safe_title = "".join([c if c.isalnum() else "_" for c in pdf_metadata.title])
    output_filepath = os.path.join(output_dir, f"{safe_title}.epub")
    
    epub.write_epub(output_filepath, book, {})
    return output_filepath
