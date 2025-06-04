import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

# --- pillow-heif Import and registration ---
# This is still relevant if any part of your PDF processing (e.g. image conversion) uses Pillow
from pillow_heif import register_heif_opener
register_heif_opener()
# --- End pillow-heif ---

# --- qdarktheme Import ---
import qdarktheme
# --- End qdarktheme ---

# --- Custom Module Imports (will be updated as we refactor them) ---
# We will assume these are (or will be) PySide6 QWidget classes
from gui.merge_tab import MergeTab
from gui.split_tab import SplitTab
from gui.delete_tab import DeleteTab # This is already refactored
from gui.convert_tab import ConvertTab

# Modern dark theme stylesheet (No longer needed, will be removed or commented)
# DARK_STYLE = \"\"\"
# QMainWindow {
# ... (rest of the old DARK_STYLE string) ...
# }
# \"\"\"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF & Datei Werkzeug - Light Mode") # Updated title
        self.setGeometry(100, 100, 1000, 700)

        # Set Window Icon
        # Make sure 'Graphicloads-Filetype-Pdf.ico' is in the same directory as pdf_tool.py
        # or provide the correct path.
        try:
            self.setWindowIcon(QIcon("Graphicloads-Filetype-Pdf.ico"))
        except Exception as e:
            print(f"Could not load window icon: {e}")

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self._create_tabs()

    def _create_tabs(self):
        # Instantiate and add tabs
        # The 'app_root' argument might not be needed or will be handled differently in Qt.
        # For now, we pass 'self' if a tab needs a reference to the main window.

        self.delete_tab_instance = DeleteTab(app_root=self) # Already refactored
        self.tab_widget.addTab(self.delete_tab_instance, "PDF Seiten löschen")
        
        # All tabs are now properly refactored to PySide6
        try:
            self.merge_tab_instance = MergeTab(app_root=self)
            self.tab_widget.addTab(self.merge_tab_instance, "PDFs zusammenführen")
        except Exception as e:
            print(f"Error loading MergeTab: {e}")

        try:
            self.split_tab_instance = SplitTab(app_root=self)
            self.tab_widget.addTab(self.split_tab_instance, "PDF Seiten extrahieren")
        except Exception as e:
            print(f"Error loading SplitTab: {e}")

        try:
            self.convert_tab_instance = ConvertTab(app_root=self)
            self.tab_widget.addTab(self.convert_tab_instance, "Dateien zu PDF konvertieren")
        except Exception as e:
            print(f"Error loading ConvertTab: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply light theme using qdarktheme
    qdarktheme.setup_theme("light") 
    
    # Set application properties for better integration
    app.setApplicationName("PDF & Datei Werkzeug")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("PDF Tools")
    
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec()) 