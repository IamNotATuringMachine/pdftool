import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QToolBar, 
    QLabel, QRadioButton, QMenu, QMenuBar, QSizePolicy # Added QMenu, QMenuBar, QSizePolicy (QToolBar, QLabel, QRadioButton might be removed or repurposed)
)
from PySide6.QtGui import QIcon, QAction, QActionGroup # Added QAction, QActionGroup
from PySide6.QtCore import Qt, Signal, QSize

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
# from gui.merge_tab import MergeTab # Removed
# from gui.convert_tab import ConvertTab # Removed
from gui.modify_pages_tab import ModifyPagesTab 
from gui.file_processing_tab import FileProcessingTab # Added

# Modern dark theme stylesheet (No longer needed, will be removed or commented)
# DARK_STYLE = \"\"\"
# QMainWindow {
# ... (rest of the old DARK_STYLE string) ...
# }
# \"\"\"

class MainWindow(QMainWindow):
    view_mode_changed = Signal(str)  # Signal to indicate view mode change

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF & Datei Werkzeug - Light Mode") # Updated title
        self.setGeometry(100, 100, 1000, 700)

        # Define standard icon sizes
        self.list_view_icon_size = QSize(24, 24)
        self.icon_view_icon_size = QSize(80, 100) # Standard icon view size
        self.current_view_mode = "list" # Default view mode

        # Set Window Icon
        # Make sure 'Graphicloads-Filetype-Pdf.ico' is in the same directory as pdf_tool.py
        # or provide the correct path.
        try:
            self.setWindowIcon(QIcon("Graphicloads-Filetype-Pdf.ico"))
        except Exception as e:
            print(f"Could not load window icon: {e}")

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self._create_menus() # Create menus including the View menu
        self._create_tabs()

    def _create_menus(self):
        menu_bar = self.menuBar() # Get the main window's menu bar
        if not menu_bar:
            menu_bar = QMenuBar(self)
            self.setMenuBar(menu_bar)

        # --- Ansicht Menu ---
        view_menu = menu_bar.addMenu("&Ansicht") # Use & for mnemonic

        self.view_action_group = QActionGroup(self)
        self.view_action_group.setExclusive(True)

        self.list_view_action = QAction("Liste", self)
        self.list_view_action.setCheckable(True)
        self.list_view_action.setChecked(self.current_view_mode == "list")
        self.list_view_action.triggered.connect(lambda: self._set_view_mode("list"))
        view_menu.addAction(self.list_view_action)
        self.view_action_group.addAction(self.list_view_action)

        self.icon_view_action = QAction("Symbole", self)
        self.icon_view_action.setCheckable(True)
        self.icon_view_action.setChecked(self.current_view_mode == "icon")
        self.icon_view_action.triggered.connect(lambda: self._set_view_mode("icon"))
        view_menu.addAction(self.icon_view_action)
        self.view_action_group.addAction(self.icon_view_action)

    def _set_view_mode(self, mode):
        if self.current_view_mode != mode:
            self.current_view_mode = mode
            # Update checked state of actions (though QActionGroup should handle it visually)
            self.list_view_action.setChecked(mode == "list")
            self.icon_view_action.setChecked(mode == "icon")
            self.view_mode_changed.emit(mode)

    def _create_tabs(self):
        # Instantiate and add tabs
        # Pass 'self' (MainWindow instance) as app_root to tabs

        # self.delete_tab_instance = DeleteTab(app_root=self)
        # self.tab_widget.addTab(self.delete_tab_instance, "PDF Seiten löschen")

        self.modify_pages_tab_instance = ModifyPagesTab(app_root=self)
        self.tab_widget.addTab(self.modify_pages_tab_instance, "Seiten Bearbeiten") # Added new combined tab
        
        # try:
        #     self.merge_tab_instance = MergeTab(app_root=self)
        #     self.tab_widget.addTab(self.merge_tab_instance, "PDFs zusammenführen")
        #     self.view_mode_changed.connect(self.merge_tab_instance.update_view_mode) # Connect signal
        # except Exception as e:
        #     print(f"Error loading MergeTab: {e}")

        # try:
        #     self.split_tab_instance = SplitTab(app_root=self)
        #     # If SplitTab needs view modes, connect here as well
        # except Exception as e:
        #     print(f"Error loading SplitTab: {e}")

        # try:
        #     self.convert_tab_instance = ConvertTab(app_root=self)
        #     self.tab_widget.addTab(self.convert_tab_instance, "Dateien zu PDF konvertieren")
        #     self.view_mode_changed.connect(self.convert_tab_instance.update_view_mode) # Connect signal
        # except Exception as e:
        #     print(f"Error loading ConvertTab: {e}")

        try:
            self.file_processing_tab_instance = FileProcessingTab(app_root=self) # New Tab instance
            self.tab_widget.addTab(self.file_processing_tab_instance, "Verarbeiten & Zusammenführen") # New Tab title
            self.view_mode_changed.connect(self.file_processing_tab_instance.update_view_mode) # Connect signal
        except Exception as e:
            print(f"Error loading FileProcessingTab: {e}")


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