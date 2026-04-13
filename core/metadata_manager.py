import os

class PdfMetadata:
    def __init__(self, filepath):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.title = os.path.splitext(self.filename)[0]
        self.author = "Desconocido"
        self.tags = ""
        self.cover_image_path = None
        self.status = "Pendiente" # Pendiente, Procesando, Completado, Error
        
    def to_dict(self):
        return {
            "filepath": self.filepath,
            "filename": self.filename,
            "title": self.title,
            "author": self.author,
            "tags": self.tags,
            "cover_image_path": self.cover_image_path,
            "status": self.status
        }

class MetadataManager:
    def __init__(self):
        self.files = {} # filepath -> PdfMetadata
        
    def add_file(self, filepath):
        if filepath not in self.files:
            self.files[filepath] = PdfMetadata(filepath)
            
    def get_file(self, filepath):
        return self.files.get(filepath)
        
    def get_all_files(self):
        return list(self.files.values())
        
    def clear(self):
        self.files.clear()
        
    def update_file_status(self, filepath, status):
        if filepath in self.files:
            self.files[filepath].status = status
