import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QToolBar, 
    QLabel, QRadioButton, QMenu, QMenuBar, QSizePolicy, QSplitter, QComboBox, QPushButton, QHBoxLayout, QGraphicsOpacityEffect, QTextEdit, QVBoxLayout # Added QComboBox, QPushButton, QHBoxLayout, QGraphicsOpacityEffect, QTextEdit, QVBoxLayout
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
from gui.file_processing_tab import FileProcessingTab # Added
from gui.file_explorer_widget import FileExplorerWidget # Added
from gui.pdf_advanced_operations_widget import PDFAdvancedOperationsWidget 

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

        # Initialize console output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        
        # Track currently active PDF function button
        self.active_pdf_function = None

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
        """Create toolbar with PDF function buttons on the left and theme controls on the right"""
        self.toolbar = QToolBar("Hauptwerkzeugleiste")
        self.addToolBar(self.toolbar)
        
        # PDF function buttons on the left
        # self.password_button = QPushButton("PDF Passwort") # Removed
        # self.password_button.setMinimumWidth(100) # Removed
        # self.password_button.clicked.connect(self._show_password_dialog) # Removed
        # self.toolbar.addWidget(self.password_button) # Removed
        
        # "PDF bearbeiten" button removed
        # self.edit_pdf_button = QPushButton("PDF bearbeiten")
        # self.edit_pdf_button.setMinimumWidth(100)
        # self.edit_pdf_button.clicked.connect(self._show_edit_pdf_dialog)
        # self.toolbar.addWidget(self.edit_pdf_button)
        
        # Repurposed "Seiten löschen" button for advanced operations
        # self.advanced_ops_button = QPushButton("PDF Anpassen") # New text
        # self.advanced_ops_button.setMinimumWidth(100)
        # self.advanced_ops_button.clicked.connect(self._show_advanced_ops_widget) # Connect to new/renamed slot
        # self.toolbar.addWidget(self.advanced_ops_button)
        
        self.delete_pages_button = QPushButton("Seiten löschen")
        self.delete_pages_button.setToolTip("Bestimmte Seiten aus einem PDF-Dokument entfernen")
        self.delete_pages_button.clicked.connect(lambda: self._show_advanced_ops_with_mode("delete"))
        self.toolbar.addWidget(self.delete_pages_button)

        self.extract_pages_button = QPushButton("Seiten extrahieren")
        self.extract_pages_button.setToolTip("Bestimmte Seiten aus einem PDF-Dokument extrahieren und als neues PDF speichern")
        self.extract_pages_button.clicked.connect(lambda: self._show_advanced_ops_with_mode("extract"))
        self.toolbar.addWidget(self.extract_pages_button)

        self.split_pdf_button = QPushButton("PDF teilen")
        self.split_pdf_button.setToolTip("Ein PDF-Dokument in mehrere separate Dateien aufteilen")
        self.split_pdf_button.clicked.connect(lambda: self._show_advanced_ops_with_mode("split"))
        self.toolbar.addWidget(self.split_pdf_button)

        self.set_password_button = QPushButton("Passwort setzen")
        self.set_password_button.setToolTip("Ein Passwort für ein PDF-Dokument festlegen zum Schutz vor unbefugtem Zugriff")
        self.set_password_button.clicked.connect(lambda: self._show_advanced_ops_with_mode("set_pwd"))
        self.toolbar.addWidget(self.set_password_button)

        self.remove_password_button = QPushButton("Passwort entfernen")
        self.remove_password_button.setToolTip("Das Passwort von einem geschützten PDF-Dokument entfernen")
        self.remove_password_button.clicked.connect(lambda: self._show_advanced_ops_with_mode("remove_pwd"))
        self.toolbar.addWidget(self.remove_password_button)
        
        # Store PDF function buttons for highlighting
        self.pdf_function_buttons = {
            "delete": self.delete_pages_button,
            "extract": self.extract_pages_button,
            "split": self.split_pdf_button,
            "set_pwd": self.set_password_button,
            "remove_pwd": self.remove_password_button
        }

        # Add spacer to push theme controls to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # View mode toggle button
        self.view_mode_button = QPushButton()
        self.view_mode_button.setMinimumWidth(80)  # Fixed width to prevent resizing
        self.view_mode_button.setToolTip("Zwischen Listen- und Symbolansicht wechseln")
        self._update_view_mode_button_text()
        self.view_mode_button.clicked.connect(self._toggle_view_mode)
        self.toolbar.addWidget(self.view_mode_button)
        
        # Theme toggle button with light bulb icons  
        self.theme_button = QPushButton()
        self.theme_button.setMinimumWidth(60)  # Fixed width to prevent resizing
        self.theme_button.setToolTip("Zwischen hellem und dunklem Design wechseln")
        self._update_theme_button_text()
        self.theme_button.clicked.connect(self._toggle_theme)
        self.toolbar.addWidget(self.theme_button)
        
        # Set tooltip delay and styling
        self._setup_tooltip_delay()
        self._setup_tooltip_styling()

    def _update_theme_button_text(self):
        """Update the theme button text based on current theme"""
        if self.current_theme == "dark":
            self.theme_button.setText("Dark")
        else:
            self.theme_button.setText("Light")

    def _toggle_theme(self):
        """Toggle between dark and light theme with fade effect"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.log_message(f"Theme gewechselt zu: {new_theme.upper()}")
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
        self.log_message(f"Ansichtsmodus gewechselt zu: {new_mode.upper()}")
        self._set_view_mode(new_mode)

    def _create_menus(self):
        # Werkzeuge-Menü entfernt - Funktionen sind in der rechten Seitenleiste verfügbar
        pass

    # def _show_password_dialog(self): # Removed
    #     \"\"\"Show PDF password widget in function container\"\"\" # Removed
    #     self.log_message("PDF Passwort-Widget geöffnet") # Removed
    #     self._show_function_widget("password") # Removed

    # _show_edit_pdf_dialog method removed
    # def _show_edit_pdf_dialog(self):

    # Renamed method to show the new advanced operations widget
    def _show_advanced_ops_widget(self): 
        self.log_message("PDF Anpassen/Aufteilen-Widget geöffnet")
        self._show_function_widget("advanced_ops") # Use new key for widget_map

    def _show_advanced_ops_with_mode(self, mode):
        # Clear previous highlighting
        self._clear_button_highlighting()
        
        # Set the new active function and highlight the button
        self.active_pdf_function = mode
        self._highlight_active_button(mode)
        
        # Check if this is a mode change for animation
        is_mode_change = (self.function_container.isVisible() and 
                         hasattr(self, 'current_advanced_mode') and 
                         self.current_advanced_mode != mode)
        
        # Show the widget with mode change information
        self._show_function_widget("advanced_ops", force_animation=is_mode_change)
        
        # Track the current mode
        self.current_advanced_mode = mode
        self.advanced_ops_widget.set_mode(mode)

    def _highlight_active_button(self, mode):
        """Highlight the active PDF function button"""
        if mode in self.pdf_function_buttons:
            button = self.pdf_function_buttons[mode]
            # Apply highlighting style that matches the theme with consistent text formatting
            if self.current_theme == "dark":
                # Use warmer gray tones that match the dark theme
                highlight_style = """
                QPushButton {
                    background-color: #5A5A5D; 
                    border: 2px solid #8A8A8D; 
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: normal;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #6A6A6D;
                    border: 2px solid #9A9A9D;
                    color: #FFFFFF;
                }
                """
            else:
                # Use warm beige tones that match the light theme
                highlight_style = """
                QPushButton {
                    background-color: #E8E7DA; 
                    border: 2px solid #D0CFC2; 
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: normal;
                    color: #333333;
                }
                QPushButton:hover {
                    background-color: #EEEEE1;
                    border: 2px solid #DAD9CC;
                }
                """
            button.setStyleSheet(highlight_style)

    def _clear_button_highlighting(self):
        """Clear highlighting from all PDF function buttons"""
        for button in self.pdf_function_buttons.values():
            button.setStyleSheet("")  # Reset to default style
        self.active_pdf_function = None

    def _update_button_highlighting_theme(self):
        """Update button highlighting colors when theme changes"""
        if self.active_pdf_function:
            self._highlight_active_button(self.active_pdf_function)

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
            spacing: 8px;
            margin: 4px 0px;
        }
        QRadioButton:hover {
            text-decoration: none !important;
        }
        QRadioButton::indicator {
            text-decoration: none !important;
            width: 0px;
            height: 0px;
            margin-right: 0px;
        }
        QRadioButton QWidget {
            text-decoration: none !important;
        }
        QGroupBox {
            border: none;
            padding-top: 15px;
            margin-top: 5px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 0 0 5px;
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
            
            # Additional button styling for dark mode - same as list color with white text
            dark_button_style = """
            QPushButton {
                background-color: #3F4042;
                border: 1px solid #555559;
                border-radius: 4px;
                padding: 6px 12px;
                color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #4A4A4D;
                border: 1px solid #666669;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #353537;
            }
            """
            current_style = self.styleSheet()
            self.setStyleSheet(current_style + dark_button_style)
            
            self.setWindowTitle("PDF Tool - Dunkler Modus")
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
            
            self.setWindowTitle("PDF Tool - Heller Modus")
        
        # Apply title bar theme immediately without delay
        self._set_windows_title_bar_theme()
        
        # Update theme button text
        self._update_theme_button_text()
        
        # Update button highlighting with new theme colors
        self._update_button_highlighting_theme()
        
        # Reapply tooltip styling to ensure black text in all themes
        self._apply_tooltip_styling()
        
        # Update theme in file processing tab if it exists
        if hasattr(self, 'file_processing_tab') and self.file_processing_tab is not None:
            self.file_processing_tab.update_theme(self.current_theme)
        
        # Update theme in function widgets if they exist
        if hasattr(self, 'function_container') and self.function_container is not None:
            self._update_function_widgets_theme()
        
        # Also update console theme if it exists
        if hasattr(self, 'console_output'):
            # Use the same colors as the drag-and-drop areas (QListWidget)
            if self.current_theme == "dark":
                console_bg_color = "#3F4042"  # Same as QListWidget in dark mode
                console_text_color = "#CCCCCC"  # Same as foreground color
                console_border_color = "#555559"  # Same as button border
            else:
                console_bg_color = "#FFFFFF"  # White for light mode
                console_text_color = "#333333"  # Dark text for light mode  
                console_border_color = "#D0D0D0"  # Light border
            
            self.console_output.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {console_bg_color};
                    color: {console_text_color};
                    border: 2px solid {console_border_color};
                    border-radius: 4px;
                    padding: 5px;
                    margin-bottom: 5px;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 9pt;
                }}
            """)

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

        # Instantiate FileExplorerWidget (left side)
        self.file_explorer = FileExplorerWidget(self) 
        self.splitter.addWidget(self.file_explorer)
        
        # Create a container for the middle (file processing tab, function widgets, and console)
        middle_container = QWidget()
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0,0,0,0) # Remove margins for a tighter fit
        middle_layout.setSpacing(5) # Spacing between widgets

        # Instantiate FileProcessingTab 
        self.file_processing_tab = FileProcessingTab(self) # Pass self if it needs main window reference
        self.view_mode_changed.connect(self.file_processing_tab.update_view_mode)
        
        self.file_explorer.file_selected_for_processing.connect(self.file_processing_tab.add_single_file_from_path)
        self.file_explorer.file_selected_for_processing.connect(self._on_file_selected_for_function_widgets)
        self.file_processing_tab.file_selected_for_function_widgets.connect(self._on_file_selected_for_function_widgets)
        self.file_processing_tab.files_processed_for_recent_list.connect(self.add_to_recent_files)

        middle_layout.addWidget(self.file_processing_tab)
        
        # Create container for PDF function widgets
        self.function_container = QWidget()
        self.function_container.setVisible(False)  # Initially hidden
        self.function_layout = QVBoxLayout(self.function_container)
        self.function_layout.setContentsMargins(5, 5, 5, 5)
        
        # Create widgets for PDF functions
        self._create_function_widgets()
        
        middle_layout.addWidget(self.function_container)
        
        middle_layout.addStretch(1)

        self.splitter.addWidget(middle_container) # Add the middle container to the splitter
        
        # Import and instantiate RecentFilesWidget (right side) with console
        from gui.recent_files_widget import RecentFilesWidget
        self.recent_files_widget = RecentFilesWidget(self, self.console_output)
        self.splitter.addWidget(self.recent_files_widget)
        
        # Set initial sizes for the splitter panes: left explorer, middle content, right activities panel
        self.splitter.setSizes([300, 600, 300]) # Explorer, Middle Container, Activities Panel (Recent Files + Console)
        
        # Log initial message
        self.log_message("Anwendung gestartet.")

    def _create_function_widgets(self):
        """Create all PDF function widgets"""
        # from gui.pdf_password_widget import PDFPasswordWidget # Removed
        # PDFEditWidget import removed
        # from gui.pdf_edit_widget import PDFEditWidget
        # Import for PDFAdvancedOperationsWidget should already be at the top
        
        # Create header with close button
        header_layout = QHBoxLayout()
        self.function_title = QLabel("")
        self.function_title.setStyleSheet("font-weight: bold; font-size: 14px; margin: 5px;")
        header_layout.addWidget(self.function_title)
        
        header_layout.addStretch()
        
        close_button = QPushButton("✕")
        close_button.setFixedSize(25, 25)
        close_button.setStyleSheet("QPushButton { border: none; font-weight: bold; } QPushButton:hover { background-color: #ff6b6b; color: white; }")
        close_button.clicked.connect(self._hide_function_widget)
        header_layout.addWidget(close_button)
        
        self.function_layout.addLayout(header_layout)
        
        # Create stacked widget to hold different function widgets
        from PySide6.QtWidgets import QStackedWidget
        self.function_stack = QStackedWidget()
        self.function_layout.addWidget(self.function_stack)
        
        # Create individual function widgets
        # self.password_widget = PDFPasswordWidget(self) # Removed
        # self.edit_widget instantiation removed
        self.advanced_ops_widget = PDFAdvancedOperationsWidget(app_root=self) # New combined widget
        
        # Add widgets to stack
        # self.function_stack.addWidget(self.password_widget) # Removed
        self.function_stack.addWidget(self.advanced_ops_widget) # Add new widget to stack
        
        # Updated widget_map and widget_titles
        self.widget_map = {
            # "password": 0, # Removed
            "advanced_ops": 0 # advanced_ops_widget is now the first widget
        }
        self.widget_titles = {
            # "password": "PDF Passwort setzen/entfernen", # Removed
            "advanced_ops": "PDF Anpassen & Passwort" # Updated title
        }
        # Ensure no other comments or definitions exist here until the method ends.

    def _show_function_widget(self, widget_name, force_animation=False):
        """Show specific function widget with fade-in animation"""
        if widget_name in self.widget_map: # Corrected: Check in self.widget_map
            # Track if this is a mode change (different widget) or first opening
            is_first_opening = not self.function_container.isVisible()
            is_widget_change = (self.function_container.isVisible() and 
                              hasattr(self, 'current_widget_name') and 
                              self.current_widget_name != widget_name)
            
            self.function_stack.setCurrentIndex(self.widget_map[widget_name]) # Corrected: Use self.widget_map to get index
            self.function_title.setText(self.widget_titles[widget_name])
            self.current_widget_name = widget_name  # Track current widget
            
            # Create fade-in animation for the function container
            should_animate = is_first_opening or is_widget_change or force_animation
            if should_animate:
                self.function_container.setVisible(True)
                
                # Create opacity effect for fade-in animation
                self.menu_fade_effect = QGraphicsOpacityEffect()
                self.function_container.setGraphicsEffect(self.menu_fade_effect)
                
                # Create fade-in animation
                self.menu_fade_animation = QPropertyAnimation(self.menu_fade_effect, b"opacity")
                self.menu_fade_animation.setDuration(300)  # 300ms for smoother, more visible transitions
                self.menu_fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.menu_fade_animation.setStartValue(0.0)
                self.menu_fade_animation.setEndValue(1.0)
                self.menu_fade_animation.start()
            elif not self.function_container.isVisible():
                # Just show without animation if no animation needed
                self.function_container.setVisible(True)
            
            # Set the current selected file if any
            if hasattr(self, 'current_selected_file') and self.current_selected_file:
                self._set_file_for_current_widget(self.current_selected_file)
        
    def _hide_function_widget(self):
        """Hide function widget container"""
        self.function_container.setVisible(False)
        # Clear button highlighting when closing function widget
        self._clear_button_highlighting()
        # Reset current widget tracking
        if hasattr(self, 'current_widget_name'):
            self.current_widget_name = None
        # Reset current advanced mode tracking
        if hasattr(self, 'current_advanced_mode'):
            self.current_advanced_mode = None
        self.log_message("Funktions-Widget geschlossen")

    def _update_function_widgets_theme(self):
        """Update theme for function widgets"""
        if self.current_theme == "dark":
            bg_color = "#3F4042"
            text_color = "#CCCCCC"
            border_color = "#555559"
        else:
            bg_color = "#FFFFFF"
            text_color = "#333333"
            border_color = "#D0D0D0"
        
        self.function_container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
            }}
            QGroupBox {{
                border: none;
                padding-top: 15px;
                margin-top: 5px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 0 0 5px;
            }}
            QRadioButton {{
                text-decoration: none !important;
                font-weight: normal !important;
                font-style: normal !important;
                spacing: 8px;
                margin: 4px 0px;
            }}
            QRadioButton::indicator {{
                width: 13px;
                height: 13px;
                margin-right: 5px;
            }}
        """)
        
        # Also call update_theme on individual widgets if they have this method
        if hasattr(self, 'function_stack') and self.function_stack:
            current_widget = self.function_stack.currentWidget()
            if hasattr(current_widget, 'update_theme'):
                current_widget.update_theme(self.current_theme)

    def _on_file_selected_for_function_widgets(self, file_path):
        """Handle file selection for function widgets"""
        self.current_selected_file = file_path
        # Update the currently visible widget if any
        if self.function_container.isVisible():
            self._set_file_for_current_widget(file_path)

    def _set_file_for_current_widget(self, file_path):
        """Set the file for the currently active function widget"""
        current_widget = self.function_stack.currentWidget()
        if hasattr(current_widget, 'set_pdf_file'):
            current_widget.set_pdf_file(file_path)

    def log_message(self, message: str):
        """Appends a message to the console output widget with timestamp, filtering for document-related actions only."""
        # Define keywords for document-related actions
        document_keywords = [
            "dokument", "document", "datei", "file", "pdf", "seite", "page",
            "hinzugefügt", "added", "gelöscht", "deleted", "bearbeitet", "edited",
            "zusammengeführt", "merged", "aufgeteilt", "split", "konvertiert", "converted",
            "gespeichert", "saved", "geöffnet", "opened", "verschlüsselt", "encrypted",
            "entschlüsselt", "decrypted", "erstellt", "created", "verarbeitet", "processed",
            "extrahiert", "extracted", "passwort", "password"
        ]
        
        # Define phrases to exclude (system messages)
        exclude_phrases = [
            "zuletzt verwendete dateien aktualisiert",
            "liste der zuletzt verwendeten dateien aktualisiert",
            "theme gewechselt",
            "ansichtsmodus gewechselt",
            "anwendung gestartet",
            "navigiert zu:",
            "ordner aufgeklappt",
            "ordner eingeklappt",
            "benutzerdefinierten ordner ausgewählt",
            "funktions-widget geschlossen",
            "widget geöffnet"
        ]
        
        # Check if message contains any excluded phrases
        message_lower = message.lower()
        is_excluded = any(phrase in message_lower for phrase in exclude_phrases)
        
        # Check if message contains any document-related keywords
        is_document_related = any(keyword in message_lower for keyword in document_keywords)
        
        # Only log document-related messages that are not excluded
        if is_document_related and not is_excluded:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.console_output.append(formatted_message)
            # Auto-scroll to bottom
            self.console_output.verticalScrollBar().setValue(
                self.console_output.verticalScrollBar().maximum()
            )
    
    def log_document_action(self, action_type: str, details: str = ""):
        """Log specific document actions with standardized formatting."""
        action_messages = {
            "document_added": f"Dokument hinzugefügt{f': {details}' if details else ''}",
            "document_removed": f"Dokument entfernt{f': {details}' if details else ''}",
            "page_deleted": f"Seite {details} gelöscht" if details else "Seite gelöscht",
            "page_extracted": f"Seite {details} extrahiert" if details else "Seite extrahiert",
            "pages_merged": f"Dokumente zusammengeführt{f': {details}' if details else ''}",
            "pdf_split": f"PDF aufgeteilt{f': {details}' if details else ''}",
            "password_set": f"PDF-Passwort gesetzt{f': {details}' if details else ''}",
            "password_removed": f"PDF-Passwort entfernt{f': {details}' if details else ''}",
            "file_converted": f"Datei konvertiert{f': {details}' if details else ''}",
            "file_saved": f"Datei gespeichert{f': {details}' if details else ''}"
        }
        
        message = action_messages.get(action_type, f"{action_type}: {details}")
        self.log_message(message)

    def add_to_recent_files(self, file_paths: list):
        if not isinstance(file_paths, list):
            self.log_message(f"Fehler: add_to_recent_files erwartet eine Liste, bekam aber {type(file_paths)}")
            return

        for file_path in file_paths:
            if not isinstance(file_path, str) or not os.path.exists(file_path):
                self.log_message(f"Ungültiger oder nicht existierender Dateipfad in der Liste der zuletzt verwendeten Dateien: {file_path}")
                continue
            
            normalized_path = os.path.normpath(file_path)

            if normalized_path in self.recent_files:
                self.recent_files.remove(normalized_path)
            self.recent_files.appendleft(normalized_path)
        
        if hasattr(self, 'recent_files_widget') and self.recent_files_widget is not None:
            self.recent_files_widget.update_recent_files(list(self.recent_files))
        self.log_message(f"Liste der zuletzt verwendeten Dateien aktualisiert: {list(self.recent_files)}")

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

    def _setup_tooltip_delay(self):
        """Set up 2-second tooltip delay for all toolbar buttons"""
        # Install custom tooltip behavior on all toolbar buttons
        for button in self.pdf_function_buttons.values():
            button.installEventFilter(self)
        
        self.view_mode_button.installEventFilter(self)
        self.theme_button.installEventFilter(self)
        
        # Timer for tooltip delay
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._show_delayed_tooltip)
        self.tooltip_timer.setInterval(1000)  # 1 second
        
        # Track tooltip state
        self.tooltip_widget = None
        self.tooltip_text = ""

    def eventFilter(self, obj, event):
        """Custom event filter for tooltip delay"""
        # Check if this is one of our toolbar buttons and get its original tooltip
        original_tooltip = None
        if obj in self.pdf_function_buttons.values():
            # Get original tooltip from our stored tooltips
            for mode, button in self.pdf_function_buttons.items():
                if button == obj:
                    if mode == "delete":
                        original_tooltip = "Bestimmte Seiten aus einem PDF-Dokument entfernen"
                    elif mode == "extract":
                        original_tooltip = "Bestimmte Seiten aus einem PDF-Dokument extrahieren und als neues PDF speichern"
                    elif mode == "split":
                        original_tooltip = "Ein PDF-Dokument in mehrere separate Dateien aufteilen"
                    elif mode == "set_pwd":
                        original_tooltip = "Ein Passwort für ein PDF-Dokument festlegen zum Schutz vor unbefugtem Zugriff"
                    elif mode == "remove_pwd":
                        original_tooltip = "Das Passwort von einem geschützten PDF-Dokument entfernen"
                    break
        elif obj == self.view_mode_button:
            original_tooltip = "Zwischen Listen- und Symbolansicht wechseln"
        elif obj == self.theme_button:
            original_tooltip = "Zwischen hellem und dunklem Design wechseln"
        
        if original_tooltip:
            if event.type() == QEvent.Type.Enter:
                # Mouse entered widget - start timer
                self.tooltip_widget = obj
                self.tooltip_text = original_tooltip
                self.tooltip_timer.start()
                return False
            elif event.type() == QEvent.Type.Leave:
                # Mouse left widget - stop timer and hide tooltip
                self.tooltip_timer.stop()
                if self.tooltip_widget == obj:
                    self.tooltip_widget = None
                return False
        
        return super().eventFilter(obj, event)

    def _setup_tooltip_styling(self):
        """Set up tooltip styling with black text"""
        self._apply_tooltip_styling()
        
    def _apply_tooltip_styling(self):
        """Apply tooltip styling with high priority to override theme"""
        app = QApplication.instance()
        current_style = app.styleSheet()
        
        # Remove any existing QToolTip styling
        import re
        current_style = re.sub(r'QToolTip\s*\{[^}]*\}', '', current_style)
        
        # Add tooltip styling with !important to override theme
        tooltip_style = """
            QToolTip {
                color: black !important;
                background-color: white !important;
                border: 1px solid #CCCCCC !important;
                padding: 4px !important;
                border-radius: 3px !important;
                font-size: 11px !important;
                font-weight: normal !important;
            }
        """
        app.setStyleSheet(current_style + tooltip_style)

    def _show_delayed_tooltip(self):
        """Show tooltip after delay"""
        if self.tooltip_widget and self.tooltip_text:
            # Force tooltip to show at current mouse position
            import PySide6.QtWidgets as QtWidgets
            QtWidgets.QToolTip.showText(
                self.tooltip_widget.mapToGlobal(self.tooltip_widget.rect().center()),
                self.tooltip_text,
                self.tooltip_widget
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply light theme using qdarktheme - This will be handled by MainWindow's __init__
    # qdarktheme.setup_theme("light") 
    
    # Set application properties for better integration
    app.setApplicationName("PDF Tool")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("PDF Tools")
    
    main_win = MainWindow()
    main_win.show()
    # Initial _apply_theme is now called from MainWindow's showEvent
    sys.exit(app.exec()) 