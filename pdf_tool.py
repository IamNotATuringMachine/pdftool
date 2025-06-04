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
        self.current_theme = "light" # Default theme
        self._apply_theme() # Apply initial theme
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

        # self.tab_widget = QTabWidget() # Removed QTabWidget
        # self.setCentralWidget(self.tab_widget) # Will set central widget after creating FileProcessingTab

        self._create_menus() # Create menus including the View menu
        self._create_main_content_area() # Renamed from _create_tabs

    def _create_menus(self):
        menu_bar = self.menuBar() # Get the main window's menu bar
        if not menu_bar:
            menu_bar = QMenuBar(self)
            self.setMenuBar(menu_bar)

        # --- Ansicht Menu ---
        view_menu = menu_bar.addMenu("&Ansicht") # Use & for mnemonic

        # -- View Mode Submenu --
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

        view_menu.addSeparator()

        # -- Theme Submenu --
        theme_menu = view_menu.addMenu("Erscheinungsbild")
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)

        light_theme_action = QAction("Heller Modus", self)
        light_theme_action.setCheckable(True)
        light_theme_action.setChecked(self.current_theme == "light")
        light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(light_theme_action)
        self.theme_action_group.addAction(light_theme_action)

        dark_theme_action = QAction("Dunkler Modus", self)
        dark_theme_action.setCheckable(True)
        dark_theme_action.setChecked(self.current_theme == "dark")
        dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        self.theme_action_group.addAction(dark_theme_action)

    def _set_view_mode(self, mode):
        if self.current_view_mode != mode:
            self.current_view_mode = mode
            # Update checked state of actions (though QActionGroup should handle it visually)
            self.list_view_action.setChecked(mode == "list")
            self.icon_view_action.setChecked(mode == "icon")
            self.view_mode_changed.emit(mode)
    
    def _apply_theme(self):
        if self.current_theme == "dark":
            custom_dark_colors = {
                "foreground": "#CCCCCC",      # Overall foreground (text) to light gray
                "background>list": "#3F4042"  # QListWidget background to match QLineEdit's default dark
            }
            qdarktheme.setup_theme(theme="dark", custom_colors=custom_dark_colors)
            self.setWindowTitle("PDF & Datei Werkzeug - Dunkler Modus")
        else: # Light theme
            # No custom colors for light theme for now, use qdarktheme defaults
            qdarktheme.setup_theme(theme="light")
            self.setWindowTitle("PDF & Datei Werkzeug - Heller Modus")

    def _set_theme(self, theme_name):
        if self.current_theme != theme_name:
            self.current_theme = theme_name
            self._apply_theme()
            # Update checked state of actions
            for action in self.theme_action_group.actions():
                if action.text() == "Heller Modus" and theme_name == "light":
                    action.setChecked(True)
                elif action.text() == "Dunkler Modus" and theme_name == "dark":
                    action.setChecked(True)

    def _create_main_content_area(self): # Renamed from _create_tabs
        # Instantiate FileProcessingTab and set it as the central widget
        try:
            self.file_processing_tab_instance = FileProcessingTab(app_root=self) # New Tab instance
            self.setCentralWidget(self.file_processing_tab_instance) # Set as central widget
            self.view_mode_changed.connect(self.file_processing_tab_instance.update_view_mode) # Connect signal
        except Exception as e:
            print(f"Error loading FileProcessingTab: {e}")

        # All other tab instantiation and adding to tab_widget is now removed.
        # self.modify_pages_tab_instance = ModifyPagesTab(app_root=self) # Commented out
        # self.tab_widget.addTab(self.modify_pages_tab_instance, "Seiten Bearbeiten") # Commented out
        
        # try:
        #     self.merge_tab_instance = MergeTab(app_root=self)
        # except Exception as e:
        #     print(f"Error loading MergeTab: {e}")

        # try:
        #     self.split_tab_instance = SplitTab(app_root=self)
        # except Exception as e:
        #     print(f"Error loading SplitTab: {e}")

        # try:
        #     self.convert_tab_instance = ConvertTab(app_root=self)
        # except Exception as e:
        #     print(f"Error loading ConvertTab: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply light theme using qdarktheme - This will be handled by MainWindow's __init__
    # qdarktheme.setup_theme("light") 
    
    # Set application properties for better integration
    app.setApplicationName("PDF & Datei Werkzeug")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("PDF Tools")
    
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec()) 