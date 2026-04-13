import os
import fitz  # PyMuPDF
from PIL import Image
from collections import Counter

def extract_cover(pdf_path, output_dir):
    """Extrae la primera página del PDF como imagen para la portada."""
    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None
            
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        filename = os.path.basename(pdf_path)
        name, _ = os.path.splitext(filename)
        # Limitar a 50 caracteres para evitar errores de nombres largos en Git/Windows
        name = "".join([c if c.isalnum() else "_" for c in name])[:50]
        cover_path = os.path.join(output_dir, f"{name}_cover.jpg")
        
        img.save(cover_path, "JPEG", quality=90)
        doc.close()
        return cover_path
    except Exception as e:
        print(f"Error extrayendo portada de {pdf_path}: {e}")
        return None

def _get_dominant_font_size(doc):
    """Calcula el tamaño de fuente más común en las primeras páginas."""
    sizes = []
    # Analizamos máximo 10 páginas para no tardar mucho
    for page_num in range(min(10, len(doc))):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        sizes.append(round(s["size"]))
    if not sizes:
        return 12
    return Counter(sizes).most_common(1)[0][0]

def extract_text_and_chapters(pdf_path):
    """
    Extrae texto intentando detectar capítulos mediante TOC o heurística de fuentes.
    """
    chapters = []
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc() # [[lvl, title, page], ...]
        
        if toc:
            # Caso 1: El PDF tiene marcadores internos
            for i in range(len(toc)):
                lvl, title, start_page = toc[i]
                end_page = toc[i+1][2] if i+1 < len(toc) else len(doc) + 1
                
                content = ""
                # Extraer texto del rango de páginas (0-indexed en PyMuPDF)
                for p in range(start_page - 1, min(end_page - 1, len(doc))):
                    page = doc.load_page(p)
                    content += page.get_text("text") + "\n"
                
                if content.strip():
                    chapters.append({
                        "title": title,
                        "content": content.strip()
                    })
        else:
            # Caso 2: Heurística basada en tamaño de fuente
            base_size = _get_dominant_font_size(doc)
            header_threshold = base_size * 1.2
            
            current_chapter_title = "Inicio"
            current_content = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                blocks = page.get_text("dict")["blocks"]
                
                for b in blocks:
                    if "lines" in b:
                        block_text = ""
                        is_header = False
                        
                        # Analizar si el bloque parece un título
                        for l in b["lines"]:
                            for s in l["spans"]:
                                if s["size"] >= header_threshold:
                                    is_header = True
                                block_text += s["text"] + " "
                        
                        block_text = block_text.strip()
                        if not block_text: continue
                        
                        if is_header and len(block_text) < 100: # Filtro para evitar bloques de texto grandes detectados como headers
                            # Guardar capítulo anterior si tiene contenido
                            if current_content.strip():
                                chapters.append({
                                    "title": current_chapter_title,
                                    "content": current_content.strip()
                                })
                            current_chapter_title = block_text
                            current_content = ""
                        else:
                            current_content += block_text + "\n"
                
            # Añadir el último capítulo
            if current_content.strip():
                chapters.append({
                    "title": current_chapter_title,
                    "content": current_content.strip()
                })

        doc.close()
        
        # Si no se detectó nada, fallback a una sola sección
        if not chapters:
            return [{"title": "Contenido", "content": "Sin texto extraible"}]
            
        return chapters
    except Exception as e:
        print(f"Error extrayendo texto de {pdf_path}: {e}")
        return []
