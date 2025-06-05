import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QToolBar, 
    QLabel, QRadioButton, QMenu, QMenuBar, QSizePolicy, QSplitter, QComboBox, QPushButton, QHBoxLayout, QGraphicsOpacityEffect # Added QComboBox, QPushButton, QHBoxLayout, QGraphicsOpacityEffect
)
from PySide6.QtGui import QIcon, QAction, QActionGroup # Added QAction, QActionGroup
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QTimer, QPropertyAnimation, QEasingCurve # Added QEvent, QTimer, QPropertyAnimation, QEasingCurve
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
        
        # Initialize fade animation for theme transitions
        self.fade_animation = None
        self.is_fading = False
        self.pending_theme = None

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
        self._create_toolbar() # Create toolbar with theme toggle and view mode dropdown
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

    def _create_toolbar(self):
        """Create toolbar with theme toggle and view mode dropdown"""
        self.toolbar = QToolBar("Hauptwerkzeugleiste")
        self.addToolBar(self.toolbar)
        
        # Add spacer to push items to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # View mode toggle button
        self.view_mode_button = QPushButton()
        self.view_mode_button.setMinimumWidth(80)  # Fixed width to prevent resizing
        self._update_view_mode_button_text()
        self.view_mode_button.clicked.connect(self._toggle_view_mode)
        self.toolbar.addWidget(self.view_mode_button)
        
        # Theme toggle button with light bulb icons  
        self.theme_button = QPushButton()
        self.theme_button.setMinimumWidth(60)  # Fixed width to prevent resizing
        self._update_theme_button_text()
        self.theme_button.clicked.connect(self._toggle_theme)
        self.toolbar.addWidget(self.theme_button)

    def _update_theme_button_text(self):
        """Update the theme button text based on current theme"""
        if self.current_theme == "dark":
            self.theme_button.setText("Dark")
        else:
            self.theme_button.setText("Light")

    def _toggle_theme(self):
        """Toggle between dark and light theme with fade effect"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self._set_theme_with_fade(new_theme)

    def _update_view_mode_button_text(self):
        """Update the view mode button text based on current view mode"""
        if self.current_view_mode == "list":
            self.view_mode_button.setText("Liste")
        else:
            self.view_mode_button.setText("Symbole")

    def _toggle_view_mode(self):
        """Toggle between list and icon view mode"""
        new_mode = "icon" if self.current_view_mode == "list" else "list"
        self._set_view_mode(new_mode)

    def _create_menus(self):
        # Werkzeuge-Menü entfernt - Funktionen sind in der rechten Seitenleiste verfügbar
        pass

    def _show_password_dialog(self):
        """Show dialog for setting/removing PDF password"""
        from gui.pdf_password_dialog import PDFPasswordDialog
        dialog = PDFPasswordDialog(self)
        dialog.exec()

    def _show_edit_pdf_dialog(self):
        """Show dialog for editing individual PDF"""
        from gui.pdf_edit_dialog import PDFEditDialog
        dialog = PDFEditDialog(self)
        dialog.exec()

    def _show_delete_pages_dialog(self):
        """Show dialog for deleting PDF pages"""
        from gui.modify_pages_tab import ModifyPagesTab
        from PySide6.QtWidgets import QDialog, QVBoxLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("PDF Seiten löschen/extrahieren")
        dialog.setModal(True)
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        modify_widget = ModifyPagesTab(app_root=self)
        layout.addWidget(modify_widget)
        
        dialog.exec()

    def _set_view_mode(self, mode):
        if self.current_view_mode != mode:
            self.current_view_mode = mode
            # Update button text
            self._update_view_mode_button_text()
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
            
            # Additional button styling for dark mode - same as list color
            dark_button_style = """
            QPushButton {
                background-color: #3F4042;
                border: 1px solid #555559;
                border-radius: 4px;
                padding: 6px 12px;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: #4A4A4D;
                border: 1px solid #666669;
            }
            QPushButton:pressed {
                background-color: #353537;
            }
            """
            current_style = self.styleSheet()
            self.setStyleSheet(current_style + dark_button_style)
            
            self.setWindowTitle("PDF & Datei Werkzeug - Dunkler Modus")
        else: # Light theme
            # Additional QSS for light theme with specific white areas - simplified
            light_theme_qss = main_window_rounded_qss + """
            /* Force white background for important UI elements */
            QListWidget {
                background-color: white !important;
                border: 1px solid #D0D0D0 !important;
            }
            QTreeView {
                background-color: white !important;
                border: 1px solid #D0D0D0 !important;
            }
            QListView {
                background-color: white !important;
                border: 1px solid #D0D0D0 !important;
            }
            """
            
            custom_light_colors = {
                "primary": "#000000",                    # Set primary color (buttons) to black for light mode
                "background": "#FFFEF7",                 # Very light beige, almost white background
                "primary>button.hoverBackground": "#C8C4B4",   # Button hover color
                "primary>button.activeBackground": "#BCB8A8",  # Button pressed color
                "input.background": "#FFFFFF"            # Keep input fields white
            }
            qdarktheme.setup_theme(theme="light",
                                   custom_colors=custom_light_colors,
                                   corner_shape="rounded",
                                   additional_qss=light_theme_qss)
            
            # Additional button styling after theme setup - subtle tone darker
            button_style = """
            QPushButton {
                background-color: #F5F4ED;
                border: 1px solid #EBEAE3;
                border-radius: 4px;
                padding: 6px 12px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #F0EFEA;
                border: 1px solid #E0DFD5;
            }
            QPushButton:pressed {
                background-color: #EBEAE3;
            }
            """
            current_style = self.styleSheet()
            self.setStyleSheet(current_style + button_style)
            
            self.setWindowTitle("PDF & Datei Werkzeug - Heller Modus")
        
        # Apply title bar theme immediately without delay
        self._set_windows_title_bar_theme()
        
        # Update theme button text
        self._update_theme_button_text()
        
        # Update theme in file processing tab if it exists
        if hasattr(self, 'file_processing_tab') and self.file_processing_tab is not None:
            self.file_processing_tab.update_theme(self.current_theme)

    def _set_theme_with_fade(self, theme_name):
        """Set theme with fade transition effect"""
        if self.current_theme == theme_name:
            return
            
        if self.is_fading:
            # If already fading, queue the new theme
            self.pending_theme = theme_name
            return
            
        self.is_fading = True
        self.pending_theme = theme_name
        
        # Create new fade effect and animation for each transition
        self.fade_effect = QGraphicsOpacityEffect()
        self.fade_animation = QPropertyAnimation(self.fade_effect, b"opacity")
        self.fade_animation.setDuration(300)  # 300ms fade duration
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Set up fade effect on central widget
        if self.centralWidget():
            self.centralWidget().setGraphicsEffect(self.fade_effect)
            
        # Connect animation signals
        self.fade_animation.finished.connect(self._on_fade_finished)
        
        # Start fade out
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
    
    def _on_fade_finished(self):
        """Handle fade animation completion"""
        # Disconnect the finished signal to avoid repeated calls
        if self.fade_animation:
            self.fade_animation.finished.disconnect()
        
        if self.fade_animation and self.fade_animation.endValue() == 0.0:
            # Fade out completed, apply new theme
            if self.pending_theme:
                self.current_theme = self.pending_theme
                self._apply_theme()
            
            # Start fade in
            self.fade_animation.setStartValue(0.0)
            self.fade_animation.setEndValue(1.0)
            self.fade_animation.finished.connect(self._on_fade_in_finished)
            self.fade_animation.start()
        
    def _on_fade_in_finished(self):
        """Handle fade in completion"""
        # Disconnect the finished signal
        if self.fade_animation:
            self.fade_animation.finished.disconnect()
        
        # Remove the graphics effect
        if self.centralWidget():
            self.centralWidget().setGraphicsEffect(None)
        
        # Clean up
        self.fade_effect = None
        self.fade_animation = None
        self.is_fading = False
        self.pending_theme = None

    def _set_theme(self, theme_name):
        if self.current_theme != theme_name:
            self.current_theme = theme_name
            self._apply_theme()

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