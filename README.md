# Conversor Masivo PDF a EPUB con Gestión de Metadatos

Este proyecto es una herramienta de escritorio profesional diseñada para automatizar la conversión de archivos PDF a formato EPUB. A diferencia de conversores simples, esta aplicación se enfoca en la calidad del contenido de salida y en el enriquecimiento de los metadatos mediante búsquedas automatizadas en fuentes externas.

## 🚀 Características Principales

- **Interfaz Moderna:** Construida con `ttkbootstrap` para ofrecer una experiencia de usuario oscura y elegante.
- **Procesamiento Masivo:** Permite cargar carpetas completas y procesar múltiples archivos en paralelo utilizando hilos (`ThreadPoolExecutor`).
- **Gestión Inteligente de Metadatos:**
    - Búsqueda automática en **Google Books API** y **OpenLibrary**.
    - Recuperación de Títulos, Autores, Etiquetas (Sujetos) y Portadas.
    - Edición manual de metadatos antes de la conversión.
- **Tratamiento de Portadas:**
    - Extracción automática de la primera página del PDF.
    - Búsqueda de portadas en alta resolución en línea.
    - Carga manual de imágenes locales.
- **Conversión Estructurada:**
    - Detección de capítulos mediante el TOC (Tabla de contenidos) interno del PDF.
    - Heurística basada en el tamaño de fuente dominante para detectar títulos en PDFs sin marcadores.
    - Generación de archivos EPUB válidos con hojas de estilo básicas.

## 🛠️ Estructura del Proyecto

- `main.py`: Punto de entrada de la aplicación.
- `ui/app_window.py`: Define la interfaz gráfica y la lógica de interacción con el usuario.
- `core/`:
    - `metadata_search.py`: Lógica de consulta a APIs externas con reintentos robustos.
    - `pdf_extractor.py`: Motor de extracción de texto, imágenes y análisis de estructura PDF (usa PyMuPDF).
    - `epub_builder.py`: Constructor del archivo final EPUB (usa ebooklib).
    - `conversion_task.py`: Orquestador que maneja la concurrencia para no bloquear la interfaz.
    - `metadata_manager.py`: (Clase de soporte) Gestiona el estado de los archivos en la lista.

## 📋 Requisitos Previos

Asegúrate de tener Python 3.8 o superior instalado. Las dependencias principales son:

```bash
pip install requests pillow PyMuPDF ebooklib ttkbootstrap
```

*Nota: En algunos sistemas, `ebooklib` requiere `lxml`.*

## 📖 Guía de Uso y Ejecución

### 1. Ejecución
Para iniciar la aplicación, ejecuta el script principal desde la raíz del proyecto:

```bash
python main.py
```

### 2. Flujo de Trabajo Recomendado

1.  **Carga de Archivos:** Haz clic en "Seleccionar Carpeta PDF" para importar tus documentos.
2.  **Configuración de Salida:** Define dónde se guardarán los libros convertidos con "Definir Carpeta Salida".
3.  **Enriquecimiento (Opcional pero recomendado):**
    - Selecciona un libro y usa "Autocompletar Metadatos" para buscar información online.
    - O usa "Auto-Metadatos Masivo" para que la IA intente identificar todos los libros de la lista automáticamente.
4.  **Ajuste de Portada:** Si el PDF no tiene una buena portada, intenta "Buscar Online" o "Extracción Auto" para sacar la primera página del documento.
5.  **Conversión:**
    - Haz clic en "Convertir Todo" para iniciar el proceso por lotes.
    - Observa la barra de progreso y el estado en el panel izquierdo.

## ⚙️ Funcionamiento Interno

### Extracción de Texto
El sistema utiliza una **heurística de fuentes**. Analiza las primeras 10 páginas para determinar el tamaño de fuente "normal" (dominante). Cualquier bloque de texto con un tamaño significativamente mayor (1.2x) se considera un posible título de capítulo, permitiendo que el EPUB final tenga una navegación fluida incluso si el PDF original era plano.

### Robustez en Red
Las peticiones a las APIs de Google y OpenLibrary incluyen un `backoff_factor`. Si hay un micro-corte de internet o el servicio está saturado, la aplicación reintentará la conexión automáticamente antes de marcar el proceso como fallido.

### Concurrencia
La conversión se realiza en un `worker_thread` independiente. Esto permite que puedas seguir editando metadatos de un libro mientras otros se están convirtiendo en segundo plano, mejorando drásticamente la eficiencia en colecciones grandes.

---
*Desarrollado como una solución integral para la gestión de bibliotecas digitales personales.*