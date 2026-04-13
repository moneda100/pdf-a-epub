import os
import threading
from concurrent.futures import ThreadPoolExecutor

from core.pdf_extractor import extract_text_and_chapters
from core.epub_builder import create_epub

def _convert_single_item(pdf_metadata, output_dir, callback_update):
    """Lógica para procesar y convertir un solo archivo."""
    try:
        # Extraer texto del PDF
        callback_update(pdf_metadata.filepath, "Procesando", f"Extrayendo texto de: {pdf_metadata.filename}")
        chapters = extract_text_and_chapters(pdf_metadata.filepath)
        
        if not chapters:
            callback_update(pdf_metadata.filepath, "Error", f"Fallo al extraer texto de: {pdf_metadata.filename}")
            return False
            
        # Generar el EPUB
        callback_update(pdf_metadata.filepath, "Procesando", f"Construyendo EPUB: {pdf_metadata.filename}")
        create_epub(pdf_metadata, chapters, output_dir)
        
        callback_update(pdf_metadata.filepath, "Completado", f"Finalizado: {pdf_metadata.filename}")
        return True
    except Exception as e:
        callback_update(pdf_metadata.filepath, "Error", f"Error en {pdf_metadata.filename}: {e}")
        return False

def run_mass_conversion(file_list, output_dir, ui_callback_update, ui_callback_finish):
    """
    Recibe una lista de objetos PdfMetadata y los procesa usando ThreadPoolExecutor.
    Llama a los callbacks para informar a la UI sobre el progreso.
    """
    total = len(file_list)
    if total == 0:
        ui_callback_finish(0)
        return

    # Usamos un Worker para no trabar el UI hilo llamador, 
    # ya que wait() o futures bloquearían si se hacen en el thread principal.
    def worker_thread():
        completed = 0
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for item in file_list:
                futures.append(
                    executor.submit(_convert_single_item, item, output_dir, ui_callback_update)
                )
            
            for f in futures:
                # Al terminar cada future (bloquea el worker_thread, NO el UI principal)
                f.result()
                completed += 1
                
        ui_callback_finish(completed)
        
    th = threading.Thread(target=worker_thread, daemon=True)
    th.start()
