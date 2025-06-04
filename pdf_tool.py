import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QToolBar, 
    QLabel, QRadioButton, QMenu, QMenuBar, QSizePolicy, QSplitter # Added QMenu, QMenuBar, QSizePolicy (QToolBar, QLabel, QRadioButton might be removed or repurposed)
)
from PySide6.QtGui import QIcon, QAction, QActionGroup # Added QAction, QActionGroup
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer # Added QEvent, QTimer
import ctypes
from ctypes import wintypes
import collections # Added for deque
import os # Added for os.path.exists

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
from gui.file_explorer_widget import FileExplorerWidget # Added

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
        self.current_theme = "dark" # Default theme
        self.setGeometry(100, 100, 1200, 800) # Increased default size
        self.recent_files = collections.deque(maxlen=10) # Max 10 recent files

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
        self._create_main_layout() # Renamed from _create_tabs / _create_main_content_area

    def showEvent(self, event):
        super().showEvent(event)
        # Apply the initial theme when the window is first shown
        # This ensures winId() is valid.
        if not hasattr(self, '_initial_theme_applied'): # Ensure it only runs once initially via showEvent
            self._apply_theme()
            # Also apply title bar theme immediately in showEvent for instant effect
            self._set_windows_title_bar_theme()
            self._initial_theme_applied = True

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
    
    def _set_windows_title_bar_theme(self):
        if sys.platform == "win32":
            try:
                hwnd = self.winId()
                if hwnd:
                    is_dark = self.current_theme == "dark"
                    
                    # Try multiple attribute values for better compatibility
                    # Value 20 is for Windows 11 22000+, value 19 for older versions
                    DWMWA_VALUES = [20, 19]  # Try 20 first, then 19 for compatibility
                    
                    success = False
                    for dwm_attr in DWMWA_VALUES:
                        try:
                            value = wintypes.BOOL(is_dark)
                            hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                                wintypes.HWND(hwnd),
                                wintypes.DWORD(dwm_attr),
                                ctypes.byref(value),
                                ctypes.sizeof(value)
                            )
                            
                            if hr == 0:  # S_OK - success
                                success = True
                                break
                                
                        except Exception as e:
                            print(f"Failed to set DWMWA attribute {dwm_attr}: {e}")
                            continue
                    
                    if success:
                        # Force window frame redraw with multiple methods for better reliability
                        try:
                            # Method 1: SetWindowPos with SWP_FRAMECHANGED
                            SWP_FRAMECHANGED = 0x0020
                            SWP_NOMOVE = 0x0002
                            SWP_NOSIZE = 0x0001
                            SWP_NOZORDER = 0x0004
                            SWP_NOACTIVATE = 0x0010
                            
                            ctypes.windll.user32.SetWindowPos(
                                wintypes.HWND(hwnd), None, 0, 0, 0, 0, 
                                SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                            )
                            
                            # Method 2: Small resize trick to force frame update (more reliable)
                            # Get current window rect
                            rect = wintypes.RECT()
                            ctypes.windll.user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
                            
                            width = rect.right - rect.left
                            height = rect.bottom - rect.top
                            
                            # Resize by 1 pixel then back
                            ctypes.windll.user32.MoveWindow(
                                wintypes.HWND(hwnd), rect.left, rect.top, width + 1, height, True
                            )
                            ctypes.windll.user32.MoveWindow(
                                wintypes.HWND(hwnd), rect.left, rect.top, width, height, True
                            )
                            
                        except Exception as e:
                            print(f"Failed to force frame redraw: {e}")
                    else:
                        print("Failed to set any DWMWA_USE_IMMERSIVE_DARK_MODE attribute")

            except Exception as e:
                print(f"Failed to set Windows title bar theme (General Exception): {e}")

    def _apply_theme(self):
        # QSS for rounded corners on the main window and removing underlines from radio buttons
        main_window_rounded_qss = """
        QMainWindow { 
            border-radius: 10px; 
        }
        QRadioButton {
            text-decoration: none !important;
            font-weight: normal !important;
            font-style: normal !important;
        }
        QRadioButton::indicator {
            text-decoration: none !important;
        }
        QRadioButton QWidget {
            text-decoration: none !important;
        }
        """

        if self.current_theme == "dark":
            custom_dark_colors = {
                "foreground": "#CCCCCC",      # Overall foreground (text) to light gray
                "background>list": "#3F4042",  # QListWidget background to match QLineEdit's default dark
                "primary": "#FFFFFF"          # Set primary color (buttons) to white for dark mode
            }
            qdarktheme.setup_theme(theme="dark",
                                   custom_colors=custom_dark_colors,
                                   corner_shape="rounded",
                                   additional_qss=main_window_rounded_qss)
            self.setWindowTitle("PDF & Datei Werkzeug - Dunkler Modus")
        else: # Light theme
            custom_light_colors = {
                "primary": "#000000"          # Set primary color (buttons) to black for light mode
            }
            qdarktheme.setup_theme(theme="light",
                                   custom_colors=custom_light_colors,
                                   corner_shape="rounded",
                                   additional_qss=main_window_rounded_qss)
            self.setWindowTitle("PDF & Datei Werkzeug - Heller Modus")
        
        # Apply title bar theme immediately without delay
        self._set_windows_title_bar_theme()

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

    def _create_main_layout(self): # Renamed and modified
        self.splitter = QSplitter(Qt.Horizontal, self)
        self.setCentralWidget(self.splitter)

        # Instantiate FileExplorerWidget
        self.file_explorer = FileExplorerWidget(self) 
        self.splitter.addWidget(self.file_explorer)
        
        # Remove the placeholder for the left panel
        # left_placeholder = QWidget()
        # left_placeholder.setMinimumWidth(200) # Give it some initial size
        # left_placeholder.setStyleSheet(\"background-color: #282c34;\") # Temporary distinct color
        # self.splitter.addWidget(left_placeholder)

        # Instantiate FileProcessingTab 
        self.file_processing_tab = FileProcessingTab(self) # Pass self if it needs main window reference
        self.view_mode_changed.connect(self.file_processing_tab.update_view_mode)
        
        # Connect the file_selected_for_processing signal from the explorer
        # to a handler in FileProcessingTab (assuming it has a method like add_file_from_path)
        # We'll need to ensure FileProcessingTab has such a method or create a new one.
        # For now, let's assume a method `handle_explorer_selection` exists or will be created in FileProcessingTab.
        # For now, let's assume a method `handle_explorer_selection` exists or will be created in FileProcessingTab.
        self.file_explorer.file_selected_for_processing.connect(self.file_processing_tab.add_single_file_from_path) # Connecting to a new dedicated slot
        self.file_processing_tab.files_processed_for_recent_list.connect(self.add_to_recent_files) # Connect to recent files handler

        self.splitter.addWidget(self.file_processing_tab)
        
        # Set initial sizes for the splitter panes
        # Give more space to the main content area initially
        self.splitter.setSizes([250, 950]) # Adjust as needed, e.g. 25% for explorer, 75% for content

    def add_to_recent_files(self, file_paths: list):
        if not isinstance(file_paths, list):
            print(f"add_to_recent_files expects a list, got {type(file_paths)}")
            return

        for file_path in file_paths:
            if not isinstance(file_path, str) or not os.path.exists(file_path): # Added os.path.exists check
                print(f"Invalid or non-existent file path in recent files list: {file_path}")
                continue
            
            # Normalize path to avoid near-duplicates (e.g. / vs \)
            normalized_path = os.path.normpath(file_path)

            if normalized_path in self.recent_files:
                self.recent_files.remove(normalized_path)
            # Add to the left (most recent)
            self.recent_files.appendleft(normalized_path)
        
        # Update the explorer widget
        if hasattr(self, 'file_explorer') and self.file_explorer is not None:
            self.file_explorer.set_recent_files(list(self.recent_files))
        print(f"Recent files updated: {list(self.recent_files)}")

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            if self.isActiveWindow():
                # Re-apply title bar theme when window becomes active
                self._set_windows_title_bar_theme()
        elif event.type() == QEvent.WindowStateChange:
            # Also re-apply if window state changes (e.g., minimized then restored)
            # as this can sometimes reset the title bar appearance
            self._set_windows_title_bar_theme()


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
    # Initial _apply_theme is now called from MainWindow's showEvent
    sys.exit(app.exec()) 