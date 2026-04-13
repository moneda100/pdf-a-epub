import os
import threading
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from core.metadata_manager import MetadataManager
from core.pdf_extractor import extract_cover
from core.metadata_search import search_metadata_online
from core.conversion_task import run_mass_conversion

class PDFtoEPUBApp(ttk.Window):
    def __init__(self):
        super().__init__(themename="darkly", title="Conversor Masivo PDF a EPUB", size=(1000, 700))
        
        self.metadata_mgr = MetadataManager()
        self.output_dir = ""
        self.current_selected_filepath = None
        self.temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_covers")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
        self._build_ui()
        
    def _build_ui(self):
        # 1. Top Navigation
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(side=TOP, fill=X)
        
        ttk.Button(top_frame, text="Seleccionar Carpeta PDF", command=self.load_pdfs, bootstyle=PRIMARY).pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="Auto-Metadatos Masivo", command=self.autocomplete_all_metadata, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="Definir Carpeta Salida", command=self.set_output_dir, bootstyle=INFO).pack(side=LEFT, padx=5)
        ttk.Button(top_frame, text="Limpiar Lista", command=self.clear_list, bootstyle=DANGER).pack(side=LEFT, padx=5)
        
        self.output_lbl = ttk.Label(top_frame, text="Salida: No definida", foreground="gray")
        self.output_lbl.pack(side=LEFT, padx=10, pady=5)
        
        ttk.Button(top_frame, text="Convertir Todo", command=self.start_conversion, bootstyle=SUCCESS).pack(side=RIGHT, padx=5)
        
        # 2. Central Body (Panedwindow)
        paned = ttk.Panedwindow(self, orient=HORIZONTAL)
        paned.pack(expand=True, fill=BOTH, padx=10, pady=5)
        
        # 2A. Left Panel: Treeview
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        columns = ("archivo", "titulo", "estado", "portada")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("archivo", text="Archivo")
        self.tree.heading("titulo", text="Título")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("portada", text="Portada")
        
        self.tree.column("archivo", width=150)
        self.tree.column("titulo", width=200)
        self.tree.column("estado", width=100)
        self.tree.column("portada", width=80)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=LEFT, expand=True, fill=BOTH)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # 2B. Right Panel: Metadata Editor and Cover
        right_frame = ttk.Frame(paned, padding=10)
        paned.add(right_frame, weight=1)
        
        ttk.Label(right_frame, text="Metadatos", font=("Helvetica", 14, "bold")).pack(anchor=W, pady=(0,10))
        
        # Formulario
        form_frame = ttk.Frame(right_frame)
        form_frame.pack(fill=X)
        
        ttk.Label(form_frame, text="Título:").grid(row=0, column=0, sticky=W, pady=5)
        self.title_var = ttk.StringVar()
        self.title_entry = ttk.Entry(form_frame, textvariable=self.title_var, state=DISABLED)
        self.title_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Autor:").grid(row=1, column=0, sticky=W, pady=5)
        self.author_var = ttk.StringVar()
        self.author_entry = ttk.Entry(form_frame, textvariable=self.author_var, state=DISABLED)
        self.author_entry.grid(row=1, column=1, sticky=EW, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Etiquetas:").grid(row=2, column=0, sticky=W, pady=5)
        self.tags_var = ttk.StringVar()
        self.tags_entry = ttk.Entry(form_frame, textvariable=self.tags_var, state=DISABLED)
        self.tags_entry.grid(row=2, column=1, sticky=EW, padx=5, pady=5)
        
        ttk.Button(form_frame, text="Autocompletar Metadatos", command=self.autocomplete_metadata, bootstyle=(INFO, OUTLINE)).grid(row=3, column=1, sticky=W, padx=5, pady=5)
        ttk.Button(form_frame, text="Guardar Cambios", command=self.save_metadata, bootstyle=SECONDARY).grid(row=3, column=1, sticky=E, padx=5, pady=5)
        form_frame.columnconfigure(1, weight=1)
        
        # Portada
        ttk.Label(right_frame, text="Portada", font=("Helvetica", 14, "bold")).pack(anchor=W, pady=(20,10))
        
        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=X, pady=5)
        ttk.Button(buttons_frame, text="Extracción Auto", command=self.auto_cover, bootstyle=(INFO, OUTLINE)).pack(side=LEFT, padx=2)
        ttk.Button(buttons_frame, text="Buscar Online", command=self.search_cover, bootstyle=(INFO, OUTLINE)).pack(side=LEFT, padx=2)
        ttk.Button(buttons_frame, text="Cargar Manual", command=self.manual_cover, bootstyle=(INFO, OUTLINE)).pack(side=LEFT, padx=2)
        
        self.cover_lbl = ttk.Label(right_frame, anchor=CENTER, background="#333", relief=SUNKEN)
        self.cover_lbl.pack(expand=True, fill=BOTH, pady=10)
        
        ttk.Button(right_frame, text="Convertir este PDF", command=self.convert_selected, bootstyle=SUCCESS).pack(fill=X, pady=5)
        
        # 3. Footer
        footer_frame = ttk.Frame(self, padding=10)
        footer_frame.pack(side=BOTTOM, fill=X)
        
        self.status_var = ttk.StringVar(value="Listo.")
        ttk.Label(footer_frame, textvariable=self.status_var).pack(side=LEFT)
        
        self.progress = ttk.Progressbar(footer_frame, mode='determinate', bootstyle=SUCCESS)
        self.progress.pack(side=RIGHT, fill=X, expand=True, padx=(20, 0))

    def load_pdfs(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de PDFs")
        if folder:
            base = folder
            pdfs = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
            if not pdfs:
                messagebox.showinfo("Información", "No se encontraron PDFs en esa carpeta.")
                return
            
            for p in pdfs:
                filepath = os.path.join(base, p)
                self.metadata_mgr.add_file(filepath)
                meta = self.metadata_mgr.get_file(filepath)
                portada = "Sí" if meta.cover_image_path else "No"
                self.tree.insert("", END, iid=filepath, values=(meta.filename, meta.title, meta.status, portada))
            self.status_var.set(f"Se cargaron {len(self.tree.get_children())} archivos en total.")

    def clear_list(self):
        if not self.tree.get_children():
            return
        if messagebox.askyesno("Confirmar", "¿Deseas limpiar toda la lista de archivos?"):
            self.metadata_mgr.clear()
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.current_selected_filepath = None
            self.title_var.set("")
            self.author_var.set("")
            self.tags_var.set("")
            self.cover_lbl.config(image='', text="Sin portada")
            self.status_var.set("Lista despejada.")

    def set_output_dir(self):
        folder = filedialog.askdirectory(title="Seleccionar carpeta de Salida")
        if folder:
            self.output_dir = folder
            self.output_lbl.config(text=f"Salida: {self.output_dir}")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        
        self.current_selected_filepath = selected[0]
        meta = self.metadata_mgr.get_file(self.current_selected_filepath)
        
        # Habilitar campos
        self.title_entry.config(state=NORMAL)
        self.author_entry.config(state=NORMAL)
        self.tags_entry.config(state=NORMAL)
        
        # Llenar datos
        self.title_var.set(meta.title)
        self.author_var.set(meta.author if meta.author != "Desconocido" else "")
        self.tags_var.set(meta.tags)
        
        # Cargar imagen de portada si existe
        self._render_cover(meta.cover_image_path)

    def _render_cover(self, image_path):
        if not image_path or not os.path.exists(image_path):
            self.cover_lbl.config(image='', text="Sin portada")
            self.cover_lbl.image = None
            return
            
        try:
            img = Image.open(image_path)
            img.thumbnail((300, 400)) # Limitar tamaño max
            photo = ImageTk.PhotoImage(img)
            self.cover_lbl.config(image=photo, text="")
            self.cover_lbl.image = photo # Guardar referencia!
        except Exception as e:
            self.cover_lbl.config(image='', text="Error cargando imagen")

    def save_metadata(self):
        if not self.current_selected_filepath: return
        meta = self.metadata_mgr.get_file(self.current_selected_filepath)
        meta.title = self.title_var.get()
        meta.author = self.author_var.get() or "Desconocido"
        meta.tags = self.tags_var.get()
        
        # Actualizar Treeview
        item = self.tree.item(self.current_selected_filepath)
        vals = list(item['values'])
        vals[1] = meta.title  # Actualizar columna Titulo
        self.tree.item(self.current_selected_filepath, values=vals)
        self.status_var.set(f"Metadatos guardados para {meta.filename}")

    def auto_cover(self):
        if not self.current_selected_filepath: return
        self.status_var.set("Extrayendo portada del documento...")
        
        # Lo corremos en thread por si es un PDF pesado
        def task():
            cover_path = extract_cover(self.current_selected_filepath, self.temp_dir)
            
            def on_done():
                if cover_path:
                    meta = self.metadata_mgr.get_file(self.current_selected_filepath)
                    meta.cover_image_path = cover_path
                    self._update_tree_cover_status(self.current_selected_filepath, "Sí")
                    self._render_cover(cover_path)
                    self.status_var.set("Portada extraída.")
                else:
                    self.status_var.set("No se pudo extraer portada.")
            self.after(0, on_done)
            
        threading.Thread(target=task, daemon=True).start()

    def search_cover(self):
        if not self.current_selected_filepath: return
        meta = self.metadata_mgr.get_file(self.current_selected_filepath)
        title = self.title_var.get()
        author = self.author_var.get()
        
        self.status_var.set("Buscando portada en línea...")
        
        def task():
            result = search_metadata_online(title, author, self.temp_dir)
            def on_done():
                if result and result["cover_path"]:
                    meta.cover_image_path = result["cover_path"]
                    self._update_tree_cover_status(self.current_selected_filepath, "Sí")
                    self._render_cover(result["cover_path"])
                    self.status_var.set("Portada encontrada.")
                else:
                    self.status_var.set("No se encontraron resultados.")
            self.after(0, on_done)
            
        threading.Thread(target=task, daemon=True).start()

    def autocomplete_metadata(self):
        if not self.current_selected_filepath: return
        meta = self.metadata_mgr.get_file(self.current_selected_filepath)
        # Usar el titulo actual o el nombre de archivo si esta vacio
        search_title = self.title_var.get() or meta.title
        search_author = self.author_var.get()
        
        self.status_var.set("Buscando metadatos completos...")
        
        def task():
            result = search_metadata_online(search_title, search_author, self.temp_dir)
            def on_done():
                if result:
                    if result["title"]: self.title_var.set(result["title"])
                    if result["author"]: self.author_var.set(result["author"])
                    if result["tags"]: self.tags_var.set(result["tags"])
                    if result["cover_path"]:
                        meta.cover_image_path = result["cover_path"]
                        self._update_tree_cover_status(self.current_selected_filepath, "Sí")
                        self._render_cover(result["cover_path"])
                    
                    # Guardar automáticamente los cambios de texto en el manager
                    self.save_metadata()
                    self.status_var.set("Metadatos actualizados automáticamente.")
                else:
                    self.status_var.set("No se encontró información para autocompletar.")
            self.after(0, on_done)
            
        threading.Thread(target=task, daemon=True).start()

    def manual_cover(self):
        if not self.current_selected_filepath: return
        file_path = filedialog.askopenfilename(
            title="Seleccionar Portada",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png")]
        )
        if file_path:
            meta = self.metadata_mgr.get_file(self.current_selected_filepath)
            meta.cover_image_path = file_path
            self._update_tree_cover_status(self.current_selected_filepath, "Sí")
            self._render_cover(file_path)
            self.status_var.set("Portada manual asignada.")

    def _update_tree_cover_status(self, filepath, status_str):
        item = self.tree.item(filepath)
        vals = list(item['values'])
        vals[3] = status_str
        self.tree.item(filepath, values=vals)

    def start_conversion(self):
        if not self.output_dir:
            messagebox.showwarning("Atención", "Por favor define una carpeta de salida.")
            return
            
        files_to_process = [f for f in self.metadata_mgr.get_all_files() if f.status in ["Pendiente", "Error"]]
        if not files_to_process:
            messagebox.showinfo("Información", "No hay archivos pendientes para convertir.")
            return

        self.progress.configure(maximum=len(files_to_process), value=0)
        self.status_var.set("Iniciando conversión...")
        
        # Deshabilitar botones principales
        # ... por simplicidad, no lo hacemos aquí, pero se recomendaría
        
        # Callback para ir actualizando el tree y la status bar
        def update_cb(filepath, status, log_msg):
            # Debe correrse en hilos, por lo que usamos self.after para encolar al hilo principal
            def safe_update():
                meta = self.metadata_mgr.get_file(filepath)
                meta.status = status
                
                # Update item list
                if self.tree.exists(filepath):
                    item = self.tree.item(filepath)
                    vals = list(item['values'])
                    vals[2] = status
                    self.tree.item(filepath, values=vals)
                    
                self.status_var.set(log_msg)
                
                if status in ["Completado", "Error"]:
                    self.progress['value'] += 1
            self.after(0, safe_update)

        def finish_cb(completed_count):
            def safe_finish():
                self.status_var.set(f"Conversión masiva terminada. {completed_count} completados.")
                messagebox.showinfo("Completado", f"Se procesaron {completed_count} archivos.")
            self.after(0, safe_finish)

        run_mass_conversion(files_to_process, self.output_dir, update_cb, finish_cb)

    def convert_selected(self):
        if not self.current_selected_filepath:
            messagebox.showwarning("Atención", "Selecciona un PDF de la lista primero.")
            return
        if not self.output_dir:
            messagebox.showwarning("Atención", "Por favor define una carpeta de salida.")
            return
            
        meta = self.metadata_mgr.get_file(self.current_selected_filepath)
        self.progress.configure(maximum=1, value=0)
        self.status_var.set(f"Convirtiendo: {meta.filename}...")
        
        def update_cb(filepath, status, log_msg):
            def safe_update():
                meta.status = status
                if self.tree.exists(filepath):
                    item = self.tree.item(filepath)
                    vals = list(item['values'])
                    vals[2] = status
                    self.tree.item(filepath, values=vals)
                self.status_var.set(log_msg)
                if status in ["Completado", "Error"]:
                    self.progress['value'] = 1
            self.after(0, safe_update)

        def finish_cb(completed_count):
            def safe_finish():
                if completed_count > 0:
                    self.status_var.set("Conversión individual finalizada.")
                else:
                    self.status_var.set("Error en la conversión individual.")
            self.after(0, safe_finish)

        run_mass_conversion([meta], self.output_dir, update_cb, finish_cb)

    def autocomplete_all_metadata(self):
        files = self.metadata_mgr.get_all_files()
        if not files:
            messagebox.showinfo("Información", "No hay archivos en la lista para procesar.")
            return

        if not messagebox.askyesno("Confirmar", f"¿Deseas buscar metadatos automáticamente para {len(files)} archivos?\n(Solo se rellenarán los campos faltantes)"):
            return

        self.progress.configure(maximum=len(files), value=0)
        self.status_var.set("Iniciando búsqueda masiva de metadatos...")
        
        def process_item(meta):
            import time
            needs_online_search = (meta.author == "Desconocido" or meta.title == os.path.splitext(meta.filename)[0])
            needs_cover = not meta.cover_image_path
            
            if needs_online_search or needs_cover:
                # 1. Intentar online si los metadatos son genéricos
                if needs_online_search:
                    result = search_metadata_online(meta.title, meta.author, self.temp_dir)
                    if result:
                        if result["title"]: meta.title = result["title"]
                        if result["author"]: meta.author = result["author"]
                        if result["tags"]: meta.tags = result["tags"]
                        if result["cover_path"]: meta.cover_image_path = result["cover_path"]
                        
                # 2. Plan B: Si todavía no hay portada (falló red o no lo encontramos online o no necesitaba busqueda online)
                if not meta.cover_image_path:
                    local_cover = extract_cover(meta.filepath, self.temp_dir)
                    if local_cover:
                        meta.cover_image_path = local_cover
                        
                # Actualizar UI de manera segura
                def update_ui():
                    if self.tree.exists(meta.filepath):
                        item = self.tree.item(meta.filepath)
                        vals = list(item['values'])
                        vals[1] = meta.title
                        vals[3] = "Sí" if meta.cover_image_path else "No"
                        self.tree.item(meta.filepath, values=vals)
                    self.progress['value'] += 1
                    self.status_var.set(f"Procesado: {meta.title}")
                self.after(0, update_ui)
                
                # Pequeña pausa para no arrollar la UI ni la API tan rápido en descargas masivas
                time.sleep(0.5)
            else:
                 self.after(0, lambda: self.progress.step(1))

        def worker():
            with ThreadPoolExecutor(max_workers=3) as executor:
                executor.map(process_item, files)
            self.after(0, lambda: self.status_var.set("Búsqueda masiva de metadatos finalizada."))
            self.after(0, lambda: messagebox.showinfo("Completado", "Se ha finalizado la búsqueda masiva de metadatos."))

        threading.Thread(target=worker, daemon=True).start()

