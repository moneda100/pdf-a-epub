import sys
import os

# Asegurarse que el directorio base esté en el sys.path si es necesario
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app_window import PDFtoEPUBApp

def main():
    app = PDFtoEPUBApp()
    app.mainloop()

if __name__ == "__main__":
    main()
