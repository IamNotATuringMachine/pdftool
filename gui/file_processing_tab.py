import os
import io
import shutil # For copying PDFs in separate processing
import tempfile
import subprocess # Added
import platform # Added
import traceback # Added for detailed error reporting
from PyPDF2 import PdfWriter, PdfReader 
from PIL import Image, UnidentifiedImageError, ImageSequence
from xhtml2pdf import pisa
from svglib.svglib import svg2rlg
from striprtf.striprtf import rtf_to_text

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader as ReportLabImageReader

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QCheckBox,
    QApplication, QFrame, QFileIconProvider, QStyle
)
from PySide6.QtCore import Qt, QUrl, QSize, QFileInfo, QEvent, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QKeyEvent

from utils.common_helpers import parse_dropped_files 
from utils.constants import (
    FILETYPES_FOR_DIALOG, # This now includes PDF thanks to previous change
    ALL_SUPPORTED_EXT_PATTERNS_LIST, # This now includes .pdf
    IMAGE_EXTENSIONS,
    TEXT_EXTENSIONS,
    RTF_EXTENSIONS,
    HTML_EXTENSIONS,
    SVG_EXTENSIONS,
    MS_WORD_EXTENSIONS, # Added
    MS_EXCEL_EXTENSIONS, # Added
    MS_POWERPOINT_EXTENSIONS, # Added
    ODF_TEXT_EXTENSIONS, # Added
    ODF_SPREADSHEET_EXTENSIONS, # Added
    ODF_PRESENTATION_EXTENSIONS # Added
)

# Import function widgets for type checking in _handle_unified_action
# from gui.pdf_password_widget import PDFPasswordWidget # Removed
from gui.pdf_advanced_operations_widget import PDFAdvancedOperationsWidget # New import
# PDFEditWidget could be imported if it had a similar action method

# ModifyPagesTab wird nicht mehr hier importiert, da sie ins Werkzeuge-Menü verlegt wurde

# Conditional imports for Windows-specific COM libraries and converters
if os.name == 'nt':
    try:
        import win32com.client
    except ImportError:
        win32com = None
    try:
        import pythoncom
    except ImportError:
        pythoncom = None
    try:
        from docx2pdf import convert as convert_docx_to_pdf
    except ImportError:
        convert_docx_to_pdf = None
    try:
        # pptxtopdf expects input_dir and output_dir
        # We'll need to wrap its usage carefully
        from pptxtopdf import convert as pptxtopdf_convert_bulk 
    except ImportError:
        pptxtopdf_convert_bulk = None
else:
    win32com = None
    pythoncom = None
    convert_docx_to_pdf = None
    pptxtopdf_convert_bulk = None

class FileProcessingTab(QWidget): # Renamed class
    files_processed_for_recent_list = Signal(list) # Signal to emit for recently used files
    file_selected_for_function_widgets = Signal(str) # Signal to emit when a file is selected for function widgets

    def __init__(self, app_root=None):
        super().__init__()
        self.setObjectName("FileProcessingTab") # For CSS styling
        self.app_root = app_root
        self.selected_files_for_processing = [] # Renamed variable
        self.preview_size = QSize(64, 64)

        self._init_ui()
        if self.app_root:
            self.update_view_mode(self.app_root.current_view_mode)

        # --- Dependency Status ---
        self.soffice_path = self._find_libreoffice_soffice()
        self.msword_available = self._is_msoffice_app_available("Word.Application")
        self.msexcel_available = self._is_msoffice_app_available("Excel.Application")
        self.mspowerpoint_available = self._is_msoffice_app_available("PowerPoint.Application")

        # Optionally, display status or log it
        self._log_dependency_status()
        # --- End Dependency Status ---

    def _log_to_console(self, message):
        """Helper function to log messages to console instead of status label"""
        if hasattr(self.app_root, 'log_message'):
            self.app_root.log_message(message)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        self.setLayout(main_layout)

        # Use a QWidget instead of a QGroupBox to avoid extra padding/margins
        controls_container = QWidget()
        controls_container_layout = QHBoxLayout(controls_container)
        controls_container_layout.setContentsMargins(0, 0, 0, 0) # Remove layout margins

        # Erstelle eine vertikale Layout für die Dateiliste mit Hinweistext
        file_area_layout = QVBoxLayout()
        file_area_layout.setContentsMargins(0, 0, 0, 0) # Remove layout margins
        
        # Hinweistext mit anklickbarem "Datei hinzufügen"
        hint_layout = QHBoxLayout()
        hint_layout.setSpacing(2)  # Reduzierter Abstand zwischen den Widgets
        hint_label = QLabel("Sie können")
        hint_layout.addWidget(hint_label)
        
        # Anklickbarer Link für "Datei hinzufügen" - als QPushButton gestylt wie ein Link
        self.add_file_link = QPushButton("Dateien hinzufügen")
        self.add_file_link.clicked.connect(self._add_files_to_process_list)
        self.add_file_link.setFlat(True)  # Removes button appearance
        self.add_file_link.setCursor(Qt.CursorShape.PointingHandCursor)  # Hand cursor like a link
        # Style it to look like a link without underline
        self.add_file_link.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: gray;
                text-decoration: none;
                font: inherit;
                padding: 0px;
                margin: 0px;
            }
            QPushButton:hover {
                color: gray;
                text-decoration: none;
            }
            QPushButton:pressed {
                color: darkgray;
            }
        """)
        hint_layout.addWidget(self.add_file_link)
        
        hint_label2 = QLabel("oder per Drag & Drop Dateien zur Verarbeitung hinzufügen.")
        hint_layout.addWidget(hint_label2)
        hint_layout.addStretch()
        
        file_area_layout.addLayout(hint_layout)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.file_list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove) # Keep InternalMove for explicitness
        self.file_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.file_list_widget.setAcceptDrops(True) # Important for receiving any drops
        
        self.file_list_widget.model().rowsMoved.connect(self._on_rows_moved) # Still needed for data sync

        # Install event filter to handle drag/drop correctly
        self.file_list_widget.installEventFilter(self)

        self.file_list_widget.setWordWrap(True)
        # self.file_list_widget.itemSelectionChanged.connect(self._on_list_selection_changed) # If needed later
        self.file_list_widget.itemDoubleClicked.connect(self._on_file_item_double_clicked) # Open file on double click
        self.file_list_widget.itemSelectionChanged.connect(self._on_file_selection_changed) # Notify function widgets

        file_area_layout.addWidget(self.file_list_widget, 1)
        controls_container_layout.addLayout(file_area_layout, 1)

        main_layout.addWidget(controls_container)

        # Adjust vertical stretch factors to make file_list_widget area taller
        # and action buttons area shorter, while removing the bottom spacer.
        main_layout.setStretch(0, 5) # Main content area gets more space
        
        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setContentsMargins(0,0,0,0)
        self.single_pdf_output_check = QCheckBox("Alle Dateien in eine einzelne PDF-Datei zusammenfassen/ausgeben") 
        self.single_pdf_output_check.setChecked(True)
        options_layout.addWidget(self.single_pdf_output_check)
        options_layout.addStretch()
        main_layout.addWidget(options_frame)
        main_layout.setStretch(1, 0) # Options frame takes minimal space

        action_layout = QVBoxLayout()
        self.unified_action_button = QPushButton("Speichern / Aktion ausführen") # Renamed and text changed
        self.unified_action_button.clicked.connect(self._handle_unified_action) # Connect to new handler
        action_layout.addWidget(self.unified_action_button)
        self.processing_status_label = QLabel("") 
        self.processing_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processing_status_label.hide()  # Hide the status label completely
        # action_layout.addWidget(self.processing_status_label)  # Don't add to layout
        main_layout.addLayout(action_layout)
        main_layout.setStretch(2, 0) # Action layout takes minimal space

        # Adjust vertical stretch factors to make file_list_widget area shorter
        # controls_container (index 0) gets 2 parts of the flexible space
        # main_layout.setStretch(0, 2)
        # options_frame (index 1) takes its preferred height (non-stretchy)
        # main_layout.setStretch(1, 0)
        # action_layout (added as item at index 2) takes its preferred height (default stretch 0)
        # Add a bottom spacer that takes 1 part of the flexible space
        # bottom_spacer = QWidget()
        # main_layout.addWidget(bottom_spacer)
        # main_layout.setStretch(main_layout.count() - 1, 1) # Spacer gets 1 part

        # ModifyPagesTab ist jetzt im Werkzeuge-Menü verfügbar, nicht mehr hier

    def _prompt_and_remove_selected_files_on_key_press(self):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            return

        num_selected = len(selected_items)
        file_s = "Datei" if num_selected == 1 else "Dateien"
        message = f"Möchten Sie die ausgewählte(n) {num_selected} {file_s} wirklich aus der Liste entfernen?"
        
        reply = QMessageBox.warning(self, "Auswahl entfernen", message,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            # Sammle die file_paths der ausgewählten Items
            files_to_remove = []
            for item in selected_items:
                widget = self.file_list_widget.itemWidget(item)
                if widget and hasattr(widget, 'file_path'):
                    files_to_remove.append(widget.file_path)
            
            # Entferne die Dateien aus der Liste
            for file_path in files_to_remove:
                try:
                    self.selected_files_for_processing.remove(file_path)
                except ValueError:
                    pass
            
            self._refresh_list_widget_items()
            if hasattr(self.app_root, 'log_message'):
                self.app_root.log_message(f"{len(files_to_remove)} Datei(en) entfernt.")

    def _on_file_item_double_clicked(self, item):
        widget = self.file_list_widget.itemWidget(item)
        if widget and hasattr(widget, 'file_path'):
            file_path = widget.file_path
            if file_path and os.path.exists(file_path):
                try:
                    os.startfile(file_path)
                    self._log_to_console(f"'{os.path.basename(file_path)}' geöffnet.")
                except Exception as e:
                    self._log_to_console(f"Fehler beim Öffnen von '{os.path.basename(file_path)}': {e}")
                    QMessageBox.warning(self, "Datei öffnen Fehler", f"Die Datei '{file_path}' konnte nicht geöffnet werden.\\nFehler: {e}")
            else:
                self._log_to_console(f"Datei nicht gefunden: {file_path}")
                QMessageBox.warning(self, "Datei öffnen Fehler", f"Die Datei '{file_path}' wurde nicht gefunden oder ist nicht mehr verfügbar.")

    def _on_file_selection_changed(self):
        """Handle file selection change and emit signal for function widgets"""
        selected_items = self.file_list_widget.selectedItems()
        if selected_items:
            # Get the first selected item
            item = selected_items[0]
            widget = self.file_list_widget.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                file_path = widget.file_path
                if file_path and os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
                    # Only emit for PDF files
                    self.file_selected_for_function_widgets.emit(file_path)

    def eventFilter(self, watched, event):
        if watched == self.file_list_widget:
            if event.type() == QEvent.Type.KeyPress: # Use QEvent.Type.KeyPress
                key_event = QKeyEvent(event) # Cast to QKeyEvent
                if key_event.key() == Qt.Key.Key_Delete:
                    if self.file_list_widget.hasFocus() and self.file_list_widget.selectedItems():
                        self._prompt_and_remove_selected_files_on_key_press()
                        return True # Event handled
            
            if event.type() == QEvent.DragEnter:
                print(f"DEBUG: DragEnter event detected")
                # Debug messages removed from console
                if event.mimeData().hasUrls(): # External file drag
                    print(f"DEBUG: Has URLs: {[url.toLocalFile() for url in event.mimeData().urls()]}")
                    is_supported_external = False
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        _, ext = os.path.splitext(file_path.lower())
                        if ext in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                            is_supported_external = True
                            break
                    if is_supported_external:
                        print("DEBUG: Accepting drag")
                        event.acceptProposedAction()
                    else:
                        print("DEBUG: Ignoring drag - no supported files")
                        event.ignore()
                    return True # Event handled by filter

                elif event.source() == self.file_list_widget and \
                     self.file_list_widget.dragDropMode() == QListWidget.DragDropMode.InternalMove:
                    print("DEBUG: Internal drag accepted")
                    event.acceptProposedAction() # Accept internal drag
                    return True # Event handled by filter
                else:
                    print("DEBUG: Drag ignored - other source")
                    event.ignore()
                    return True

            elif event.type() == QEvent.DragMove:
                # Similar logic to DragEnter, could be simplified if DragEnter already set the stage
                if event.mimeData().hasUrls():
                    # Basic acceptance, could add more checks if needed
                    event.acceptProposedAction() 
                    return True
                elif event.source() == self.file_list_widget and \
                     self.file_list_widget.dragDropMode() == QListWidget.DragDropMode.InternalMove:
                    event.acceptProposedAction()
                    return True
                else:
                    event.ignore()
                    return True
            
            elif event.type() == QEvent.Drop:
                print(f"DEBUG: Drop event detected")
                if event.mimeData().hasUrls(): # External file drop
                    file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
                    supported_files = [fp for fp in file_paths if os.path.splitext(fp.lower())[1] in ALL_SUPPORTED_EXT_PATTERNS_LIST]
                    print(f"DEBUG: Dropped files: {file_paths}")
                    print(f"DEBUG: Supported files: {supported_files}")
                    
                    if supported_files:
                        self._add_files_to_gui_list(supported_files)
                        event.acceptProposedAction()
                        print("DEBUG: Drop accepted and files added")
                    else:
                        QMessageBox.information(self, "Keine unterstützten Dateien", "Keine der abgelegten Dateien hat einen unterstützten Dateityp.")
                        event.ignore()
                        print("DEBUG: Drop ignored - no supported files")
                    return True # External drop handled by filter

                # For internal moves (or other drops QListWidget should handle itself):
                # Return False to let QListWidget's own dropEvent process it.
                # This is crucial for InternalMove to work correctly.
                # This ensures QListWidget updates its model and emits rowsMoved.
                return False # Pass event to QListWidget for its default handling
        
        return super().eventFilter(watched, event) # Default event processing

    def update_view_mode(self, mode):
        if not self.app_root: return
        icon_size = self.app_root.list_view_icon_size if mode == "list" else self.app_root.icon_view_icon_size
        view_mode_qt = QListWidget.ViewMode.ListMode if mode == "list" else QListWidget.ViewMode.IconMode
        
        self.file_list_widget.setViewMode(view_mode_qt)
        self.file_list_widget.setIconSize(icon_size)
        self.file_list_widget.setFlow(QListWidget.Flow.TopToBottom if mode == "list" else QListWidget.Flow.LeftToRight)
        self.file_list_widget.setWrapping(mode != "list")
        self.file_list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.file_list_widget.setWordWrap(mode != "list")
        self._refresh_list_widget_items()

    def update_theme(self, theme):
        """Update the link color based on the current theme"""
        if theme == "dark":
            link_color = "white"  # White for dark mode
        else:
            link_color = "gray"   # Gray for light mode
        
        # Update QPushButton styling to match theme
        self.add_file_link.setStyleSheet(f"""
            QPushButton {{
                border: none;
                background: transparent;
                color: {link_color};
                text-decoration: none;
                font: inherit;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                color: {link_color};
                text-decoration: none;
            }}
            QPushButton:pressed {{
                color: {"lightgray" if theme == "dark" else "darkgray"};
            }}
        """)

    def _on_rows_moved(self, parent, start, end, destination, row):
        self._update_internal_file_list_from_widget()
        if hasattr(self.app_root, 'log_message'):
            self.app_root.log_message("Dateireihenfolge geändert.")

    def _update_internal_file_list_from_widget(self):
        self.selected_files_for_processing.clear()
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            widget = self.file_list_widget.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                self.selected_files_for_processing.append(widget.file_path)

    def _refresh_list_widget_items(self):
        # Store the paths of currently selected items
        selected_paths = set()
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            widget = self.file_list_widget.itemWidget(item)
            if widget and hasattr(widget, 'file_path') and item.isSelected():
                selected_paths.add(widget.file_path)

        self.file_list_widget.clear()
        for index, file_path in enumerate(self.selected_files_for_processing):
            item = QListWidgetItem()
            
            # Erstelle Custom Widget für dieses Listenelement
            item_widget = self._create_file_item_widget(file_path, index)
            
            # Setze die Größe des Items basierend auf dem Widget
            item.setSizeHint(item_widget.sizeHint())
            
            self.file_list_widget.addItem(item)
            self.file_list_widget.setItemWidget(item, item_widget)
            
            # Restore selection if this item was previously selected
            if file_path in selected_paths:
                item.setSelected(True)
    
    def _create_file_item_widget(self, file_path, index):
        """Erstellt ein Custom Widget für ein Datei-Listenelement mit Delete-Button und Pfeilsymbolen"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Datei-Icon
        icon_label = QLabel()
        icon = self._get_q_icon_for_file(file_path)
        pixmap = icon.pixmap(24, 24)
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)
        
        # Dateiname
        filename_label = QLabel(os.path.basename(file_path))
        filename_label.setWordWrap(True)
        layout.addWidget(filename_label, 1)
        
        # Use QIcon for buttons for better visibility
        style = self.style()
        up_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp)
        down_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        delete_icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)

        up_button = QPushButton()
        up_button.setIcon(up_icon)
        up_button.setMaximumSize(30, 25)
        up_button.setEnabled(index > 0)
        up_button.setToolTip("Nach oben verschieben")
        up_button.clicked.connect(lambda: self._move_file_up(file_path))
        layout.addWidget(up_button)

        down_button = QPushButton()
        down_button.setIcon(down_icon)
        down_button.setMaximumSize(30, 25)
        down_button.setEnabled(index < len(self.selected_files_for_processing) - 1)
        down_button.setToolTip("Nach unten verschieben")
        down_button.clicked.connect(lambda: self._move_file_down(file_path))
        layout.addWidget(down_button)

        delete_button = QPushButton()
        delete_button.setIcon(delete_icon)
        delete_button.setMaximumSize(30, 25)
        delete_button.setToolTip("Datei entfernen")
        delete_button.clicked.connect(lambda: self._remove_single_file(file_path))
        layout.addWidget(delete_button)

        # Speichere file_path als Attribut für spätere Referenz
        widget.file_path = file_path
        
        return widget
    
    def _move_file_up(self, file_path):
        """Verschiebt eine Datei nach oben in der Liste"""
        try:
            current_idx = self.selected_files_for_processing.index(file_path)
            if current_idx > 0:
                # Tausche mit dem Element darüber
                self.selected_files_for_processing[current_idx], self.selected_files_for_processing[current_idx - 1] = \
                    self.selected_files_for_processing[current_idx - 1], self.selected_files_for_processing[current_idx]
                self._refresh_list_widget_items()
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"'{os.path.basename(file_path)}' nach oben verschoben.")
        except ValueError:
            pass
    
    def _move_file_down(self, file_path):
        """Verschiebt eine Datei nach unten in der Liste"""
        try:
            current_idx = self.selected_files_for_processing.index(file_path)
            if current_idx < len(self.selected_files_for_processing) - 1:
                # Tausche mit dem Element darunter
                self.selected_files_for_processing[current_idx], self.selected_files_for_processing[current_idx + 1] = \
                    self.selected_files_for_processing[current_idx + 1], self.selected_files_for_processing[current_idx]
                self._refresh_list_widget_items()
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"'{os.path.basename(file_path)}' nach unten verschoben.")
        except ValueError:
            pass
    
    def _remove_single_file(self, file_path):
        """Entfernt eine einzelne Datei aus der Liste"""
        try:
            self.selected_files_for_processing.remove(file_path)
            self._refresh_list_widget_items()
            filename = os.path.basename(file_path)
            # Log the action
            if hasattr(self.app_root, 'log_message'):
                self.app_root.log_message(f"Datei aus Liste entfernt: {filename}")
        except ValueError:
            pass

    def _get_q_icon_for_file(self, file_path):
        # Ensure this method correctly handles file_path to provide an icon
        # This is used by _refresh_list_widget_items
        file_info = QFileInfo(file_path)
        icon_provider = QFileIconProvider()
        icon = icon_provider.icon(file_info)
        if icon.isNull(): # Fallback if system icon is not good
            # Attempt to create a basic pixmap if it's an image, or generic file icon
            ext = file_info.suffix().lower()
            if ext in IMAGE_EXTENSIONS:
                try:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        return QIcon(pixmap.scaled(self.preview_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                except Exception:
                    pass # Ignore if pixmap creation fails
            return QApplication.style().standardIcon(QApplication.Style.StandardPixmap.SP_FileIcon)
        return icon

    def _add_files_to_gui_list(self, file_paths):
        added_to_processing_list_paths = [] # Paths newly added to self.selected_files_for_processing
        processed_any_paths = False # Flag to check if any path was processed (even if duplicate)

        for file_path in file_paths:
            processed_any_paths = True
            if not os.path.exists(file_path):
                filename = os.path.basename(file_path)
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"Fehler: Datei nicht gefunden: {filename}")
                continue
            
            _, ext = os.path.splitext(file_path.lower())
            if ext not in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                filename = os.path.basename(file_path)
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"Datei übersprungen (nicht unterstützter Typ): {filename}")
                continue # Skip unsupported files

            if file_path not in self.selected_files_for_processing:
                self.selected_files_for_processing.append(file_path)
                added_to_processing_list_paths.append(file_path)
            else:
                filename = os.path.basename(file_path)
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"Datei bereits in Liste: {filename}")
        
        if added_to_processing_list_paths: # If any new unique files were added to the data model
            self._refresh_list_widget_items() # Rebuilds QListWidget from self.selected_files_for_processing
            self.files_processed_for_recent_list.emit(added_to_processing_list_paths) 
            # Log the successful addition
            if hasattr(self.app_root, 'log_message'):
                file_count = len(added_to_processing_list_paths)
                self.app_root.log_message(f"{file_count} Datei(en) hinzugefügt.")
                self.app_root.log_message(f"{file_count} neue Datei(en) zur Verarbeitung hinzugefügt")
        elif processed_any_paths: # Files were provided, but none were new to selected_files_for_processing
            self._log_to_console("Ausgewählte Datei(en) bereits in der Liste oder nicht unterstützt.")

    def _add_files_to_process_list(self): # Renamed method
        if hasattr(self.app_root, 'log_message'):
            self.app_root.log_message("Datei-Dialog geöffnet")
        
        # FILETYPES_FOR_DIALOG is now correctly configured due to constants.py change
        dialog_filter = " ;; ".join([f"{ftype_desc} ({' '.join(['*'+ext for ext in exts.split()])})" for ftype_desc, exts in FILETYPES_FOR_DIALOG if exts]) # Ensure exts is not empty
        # Ensure "Alle unterstützten Dateien" entry is correctly formatted
        all_supported_entry = f"Alle unterstützten Dateien ({' '.join(['*'+pat for pat in ALL_SUPPORTED_EXT_PATTERNS_LIST])})"
        dialog_filter = f"{all_supported_entry} ;; {dialog_filter} ;; Alle Dateien (*.*)"

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien für Verarbeitung auswählen", # Updated title
            "",
            dialog_filter
        )
        if files:
            self._add_files_to_gui_list(files)

    def _remove_file_from_process_list(self): # Renamed method
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items:
            self._log_to_console("Keine Dateien zum Entfernen ausgewählt.")
            return

        removed_count = 0
        # Create a list of file paths to remove from the model,
        # as removing items from the widget will change indices.
        paths_to_remove_from_model = []
        for item in selected_items:
            paths_to_remove_from_model.append(item.data(Qt.ItemDataRole.UserRole))
            # No need to remove item from widget here, _refresh_list_widget_items will do it
            # based on self.selected_files_for_processing
            removed_count += 1
        
        # Update the internal data model
        self.selected_files_for_processing = [
            fp for fp in self.selected_files_for_processing if fp not in paths_to_remove_from_model
        ]
        
        # Refresh the QListWidget from the updated data model
        # This will also clear previous selections by default.
        self._refresh_list_widget_items() 
        
        # Optional: Attempt to re-select an item if appropriate,
        # for example, the item that was after the last removed one,
        # or the new last item if the original last was removed.
        # This can be complex; for now, clearing selection is acceptable.

        if removed_count > 0:
            file_s = "Datei" if removed_count == 1 else "Dateien"
            if hasattr(self.app_root, 'log_message'):
                self.app_root.log_message(f"{removed_count} {file_s} aus der Liste entfernt.")
        else:
            self._log_to_console("Keine Dateien entfernt (möglicherweise bereits entfernt oder Fehler).")

    def _move_item_in_list(self, direction): # Renamed from _move_item
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items: return
        current_item = selected_items[0]
        current_path = current_item.data(Qt.ItemDataRole.UserRole)
        
        try:
            current_idx = self.selected_files_for_processing.index(current_path)
        except ValueError: # Should not happen if lists are synced
            self._refresh_list_widget_items() # Resync
            return

        new_idx = current_idx + direction
        if 0 <= new_idx < len(self.selected_files_for_processing):
            self.selected_files_for_processing.pop(current_idx)
            self.selected_files_for_processing.insert(new_idx, current_path)
            self._refresh_list_widget_items()
            for i in range(self.file_list_widget.count()):
                if self.file_list_widget.item(i).data(Qt.ItemDataRole.UserRole) == current_path:
                    self.file_list_widget.item(i).setSelected(True)
                    self.file_list_widget.scrollToItem(self.file_list_widget.item(i))
                    break
            direction_text = "nach oben" if direction == -1 else "nach unten"
            if hasattr(self.app_root, 'log_message'):
                self.app_root.log_message(f"Datei {direction_text} verschoben.")

    def _move_process_item_up(self): # Renamed method
        self._move_item_in_list(-1)

    def _move_process_item_down(self): # Renamed method
        self._move_item_in_list(1)

    def _handle_unified_action(self):
        """Handles the action from the main button, routing to either processing or a function widget action"""
        action_handled_by_function_widget = False
        if hasattr(self.app_root, 'function_container') and self.app_root.function_container.isVisible():
            current_widget = self.app_root.function_stack.currentWidget()
            
            if isinstance(current_widget, PDFAdvancedOperationsWidget):
                self.app_root.log_message("Aktion wird durch PDF Anpassen & Passwort-Widget ausgeführt...")
                if hasattr(current_widget, 'public_perform_action_and_save'):
                    current_widget.public_perform_action_and_save()
                elif hasattr(current_widget, 'is_ready_for_action') and current_widget.is_ready_for_action():
                    # Fallback for older structure, if public_perform_action_and_save isn't there
                    current_widget.public_perform_action_and_save()
                else:
                    self.app_root.log_message("PDF Anpassen & Passwort-Widget ist nicht bereit (fehlende Datei oder Seitenangabe).")
                action_handled_by_function_widget = True
        
        if not action_handled_by_function_widget:
            self.app_root.log_message("Aktion wird durch allgemeine Dateiverarbeitung ausgeführt...")
            self._execute_processing()

    def _execute_processing(self): # Renamed method
        if not self.selected_files_for_processing:
            QMessageBox.information(self, "Keine Dateien", "Bitte fügen Sie zuerst Dateien zur Liste hinzu.")
            self._log_to_console("Keine Dateien für Verarbeitung.")
            return

        files_to_process = []
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            widget = self.file_list_widget.itemWidget(item)
            if widget and hasattr(widget, 'file_path'):
                files_to_process.append(widget.file_path)

        if not files_to_process:
            QMessageBox.information(self, "Keine gültigen Dateien", 
                                    "Die Liste enthält keine Elemente mit gültigen Dateipfaden.")
            self._log_to_console("Keine gültigen Dateien für Verarbeitung.")
            return

        # Log the start of processing
        if hasattr(self.app_root, 'log_message'):
            file_count = len(files_to_process)
            output_type = "zu einer PDF zusammengeführt" if self.single_pdf_output_check.isChecked() else "zu separaten PDFs konvertiert"
            self.app_root.log_message(f"Verarbeitung gestartet: {file_count} Datei(en) werden {output_type}")

        # Use a copy for processing to avoid issues if the list is modified elsewhere during processing
        # This was how it was done with self.selected_files_for_processing[:]
        # files_to_process is already a new list here.

        self._log_to_console("Verarbeite Dateien...")
        QApplication.processEvents() # Update UI

        output_directory = ""
        # Determine output directory for individual file saving if not merging
        if not self.single_pdf_output_check.isChecked() and files_to_process:
            # Always ask for an output directory if not merging to a single file
            output_directory = QFileDialog.getExistingDirectory(
                self, "Ausgabeverzeichnis für separate PDF(s) auswählen", # Clarified title
                os.path.dirname(files_to_process[0]) if files_to_process else ""
            )
            if not output_directory:
                self._log_to_console("Verarbeitung abgebrochen. Kein Ausgabeverzeichnis gewählt.")
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message("Verarbeitung abgebrochen: Kein Ausgabeverzeichnis gewählt")
                return

        try:
            if self.single_pdf_output_check.isChecked():
                if len(files_to_process) == 1 and files_to_process[0].lower().endswith(".pdf"):
                    # If it's a single PDF and we want a single output, it's essentially a copy/rename operation.
                    # Or, it could imply that no processing is needed, but we should still offer to save it.
                    # For now, let's treat it like any other single file to be "processed" into a single PDF.
                    pass # The existing logic in _process_files_to_single_pdf will handle this.

                self._process_files_to_single_pdf(files_to_process)
            else:
                self._process_files_to_separate_pdfs(files_to_process, output_directory)
            
            # Status messages are set within the _process_files... methods
            # self._log_to_console("Dateiverarbeitung abgeschlossen.") 
            # QMessageBox.information(self, "Erfolg", "Dateiverarbeitung erfolgreich abgeschlossen.")

        except Exception as e:
            detailed_error = traceback.format_exc()
            self._show_detailed_error("Verarbeitungsfehler", 
                                      f"Ein Fehler ist während der Dateiverarbeitung aufgetreten: {e}",
                                      detailed_info=detailed_error)
            self._log_to_console(f"Fehler bei Dateiverarbeitung: {e}")

    def _process_files_to_single_pdf(self, files_to_process):
        if not files_to_process:
            self._log_to_console("Keine Dateien zum Verarbeiten ausgewählt.")
            return

        output_pdf_path, _ = QFileDialog.getSaveFileName(self, "Einzelne PDF speichern unter...",
                                                         os.path.join(os.getcwd(), "kombinierte_datei.pdf"),
                                                         "PDF-Dateien (*.pdf)")
        if not output_pdf_path:
            self._log_to_console("Speichervorgang abgebrochen.")
            return

        self._log_to_console("Verarbeite Dateien zu einer einzelnen PDF...")
        QApplication.processEvents()

        output_pdf_writer = PdfWriter()
        num_successful = 0
        num_errors = 0
        first_error_detail = None # Added to capture first error detail

        for i, file_path in enumerate(files_to_process):
            current_file_basename = os.path.basename(file_path)
            self._log_to_console(f"Verarbeite Datei {i+1}/{len(files_to_process)}: {current_file_basename}")
            QApplication.processEvents()
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            temp_pdf_for_conversion = None
            file_processed_successfully = False

            try:
                if ext == ".pdf":
                    pdf_reader = PdfReader(file_path)
                    for page in pdf_reader.pages:
                        output_pdf_writer.add_page(page)
                    self._log_to_console(f"PDF '{current_file_basename}' hinzugefügt.")
                    file_processed_successfully = True
                elif ext in IMAGE_EXTENSIONS:
                    img_pdf_bytes = io.BytesIO()
                    pdf_canvas = canvas.Canvas(img_pdf_bytes, pagesize=A4)
                    if self._add_image_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        img_pdf_bytes.seek(0)
                        img_pdf_reader = PdfReader(img_pdf_bytes)
                        for page in img_pdf_reader.pages:
                            output_pdf_writer.add_page(page)
                        file_processed_successfully = True
                    img_pdf_bytes.close()
                elif ext in TEXT_EXTENSIONS:
                    txt_pdf_bytes = io.BytesIO()
                    pdf_canvas = canvas.Canvas(txt_pdf_bytes, pagesize=A4)
                    if self._add_text_file_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        txt_pdf_bytes.seek(0)
                        txt_pdf_reader = PdfReader(txt_pdf_bytes)
                        for page in txt_pdf_reader.pages:
                            output_pdf_writer.add_page(page)
                        file_processed_successfully = True
                    txt_pdf_bytes.close()
                elif ext in RTF_EXTENSIONS:
                    rtf_pdf_bytes = io.BytesIO()
                    pdf_canvas = canvas.Canvas(rtf_pdf_bytes, pagesize=A4)
                    if self._add_rtf_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        rtf_pdf_bytes.seek(0)
                        rtf_pdf_reader = PdfReader(rtf_pdf_bytes)
                        for page in rtf_pdf_reader.pages:
                            output_pdf_writer.add_page(page)
                        file_processed_successfully = True
                    rtf_pdf_bytes.close()
                elif ext in HTML_EXTENSIONS:
                    temp_html_pdf_fd, temp_html_pdf_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(temp_html_pdf_fd)
                    temp_pdf_for_conversion = temp_html_pdf_path
                    if self._convert_html_to_pdf_file(file_path, temp_html_pdf_path):
                        html_pdf_reader = PdfReader(temp_html_pdf_path)
                        for page in html_pdf_reader.pages:
                            output_pdf_writer.add_page(page)
                        file_processed_successfully = True
                elif ext in SVG_EXTENSIONS:
                    svg_pdf_bytes = io.BytesIO()
                    pdf_canvas = canvas.Canvas(svg_pdf_bytes, pagesize=A4)
                    if self._add_svg_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        svg_pdf_bytes.seek(0)
                        svg_pdf_reader = PdfReader(svg_pdf_bytes)
                        for page in svg_pdf_reader.pages:
                             output_pdf_writer.add_page(page)
                        file_processed_successfully = True
                    svg_pdf_bytes.close()
                elif ext in (MS_WORD_EXTENSIONS + MS_EXCEL_EXTENSIONS + MS_POWERPOINT_EXTENSIONS +
                             ODF_TEXT_EXTENSIONS + ODF_SPREADSHEET_EXTENSIONS + ODF_PRESENTATION_EXTENSIONS):
                    temp_office_pdf_fd, temp_office_pdf_path = tempfile.mkstemp(suffix=".pdf")
                    os.close(temp_office_pdf_fd)
                    temp_pdf_for_conversion = temp_office_pdf_path
                    self._log_to_console(f"Konvertiere {current_file_basename} zu PDF...")
                    QApplication.processEvents()
                    if self._convert_office_to_pdf_native(file_path, temp_office_pdf_path):
                        if os.path.exists(temp_office_pdf_path) and os.path.getsize(temp_office_pdf_path) > 0:
                            try:
                                office_pdf_reader = PdfReader(temp_office_pdf_path)
                                for page in office_pdf_reader.pages:
                                    output_pdf_writer.add_page(page)
                                self._log_to_console(f"{current_file_basename} zu PDF hinzugefügt.")
                                file_processed_successfully = True
                            except Exception as e:
                                error_msg = f"Fehler beim Lesen der konvertierten PDF für {current_file_basename}: {e}"
                                self._log_to_console(error_msg)
                                print(f"Error reading converted PDF {temp_office_pdf_path}: {e}")
                        else:
                             self._log_to_console(f"Konvertierte PDF für {current_file_basename} ist leer oder nicht vorhanden.")
                    # If _convert_office_to_pdf_native returned False, status label is already set by it.
                else:
                    self._log_to_console(f"Dateityp {ext} von '{current_file_basename}' wird nicht unterstützt.")

                if file_processed_successfully:
                    num_successful += 1
                else:
                    num_errors += 1
                    error_on_label = self.processing_status_label.text() # Get status after failed attempt
                    if not first_error_detail:
                        first_error_detail = f"Datei '{current_file_basename}': {error_on_label}"

            except Exception as e:
                error_msg = f"Fehler bei Datei '{current_file_basename}': {e}"
                self._log_to_console(error_msg)
                print(f"Error processing file {file_path}: {e}")
                num_errors += 1
                if not first_error_detail:
                    first_error_detail = error_msg # Use the exception message directly
            finally:
                if temp_pdf_for_conversion and os.path.exists(temp_pdf_for_conversion):
                    try:
                        os.remove(temp_pdf_for_conversion)
                    except Exception as e_del:
                        print(f"Could not delete temp file {temp_pdf_for_conversion}: {e_del}")

        if len(output_pdf_writer.pages) > 0:
            try:
                with open(output_pdf_path, "wb") as f_out:
                    output_pdf_writer.write(f_out)
                final_message = f"Erfolgreich {num_successful} Datei(en) in '{os.path.basename(output_pdf_path)}' gespeichert."
                if num_errors > 0:
                    final_message += f" {num_errors} Datei(en) konnten nicht verarbeitet werden."
                if first_error_detail:
                    final_message += f"\n\nDetails zum ersten Fehler:\n{first_error_detail}"
                
                # Log the completion
                if hasattr(self.app_root, 'log_message'):
                    if num_errors == 0:
                        self.app_root.log_message(f"Verarbeitung erfolgreich abgeschlossen: {num_successful} Datei(en) zu einer PDF zusammengeführt")
                    else:
                        self.app_root.log_message(f"Verarbeitung abgeschlossen mit Fehlern: {num_successful} erfolgreich, {num_errors} Fehler")
                
                if num_errors > 0:
                    # Show detailed error information
                    detailed_info = f"Erfolgreich verarbeitet: {num_successful}\nFehler: {num_errors}\n\n"
                    detailed_info += f"Erster Fehler:\n{first_error_detail}\n\n"
                    detailed_info += self._get_conversion_capability_info()
                    
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.Information)
                    msg_box.setWindowTitle("Verarbeitung teilweise erfolgreich")
                    msg_box.setText(final_message)
                    msg_box.setDetailedText(detailed_info)
                    msg_box.exec()
                else:
                    QMessageBox.information(self, "Verarbeitung abgeschlossen", final_message)
            except Exception as e:
                error_detail = f"Fehler beim Speichern der PDF: {e}\n\n"
                error_detail += f"Ausgabepfad: {output_pdf_path}\n"
                error_detail += f"Dateigröße der nicht gespeicherten PDF: {len(output_pdf_writer.pages)} Seiten"
                # Log the error
                if hasattr(self.app_root, 'log_message'):
                    self.app_root.log_message(f"FEHLER beim Speichern der PDF: {str(e)}")
                self._show_detailed_error("Speicherfehler", f"Fehler beim Speichern der PDF: {e}", error_detail)
        elif num_errors > 0 and num_successful == 0:
            final_message = f"Keine Dateien konnten verarbeitet werden. {num_errors} Fehler aufgetreten."
            if first_error_detail:
                final_message += f"\n\nDetails zum ersten Fehler:\n{first_error_detail}"
            
            detailed_info = f"Alle {num_errors} Dateien konnten nicht verarbeitet werden.\n\n"
            detailed_info += f"Erster Fehler:\n{first_error_detail}\n\n"
            detailed_info += self._get_conversion_capability_info()
            
            self._show_detailed_error("Verarbeitung fehlgeschlagen", final_message, detailed_info)
        else:
            QMessageBox.information(self, "Nichts zu speichern", "Keine Inhalte zum Speichern in der PDF vorhanden.")
        
        self._log_to_console("Bereit.")

    def _process_files_to_separate_pdfs(self, files_to_process, output_directory):
        if not files_to_process:
            self._log_to_console("Keine Dateien zum Verarbeiten ausgewählt.")
            return

        self._log_to_console("Verarbeite Dateien zu separaten PDFs...")
        QApplication.processEvents()

        num_successful = 0
        num_errors = 0
        processed_file_paths = []
        first_error_detail = None # Added to capture first error detail

        for i, file_path in enumerate(files_to_process):
            current_file_basename = os.path.basename(file_path)
            self._log_to_console(f"Verarbeite Datei {i+1}/{len(files_to_process)}: {current_file_basename}")
            QApplication.processEvents()
            
            base, ext = os.path.splitext(current_file_basename)
            ext = ext.lower()
            output_pdf_name = f"{base}.pdf"
            final_output_pdf_path = os.path.join(output_directory, output_pdf_name)
            
            conversion_successful_flag = False

            try:
                if ext == ".pdf":
                    shutil.copy2(file_path, final_output_pdf_path)
                    self._log_to_console(f"PDF '{current_file_basename}' kopiert.")
                    conversion_successful_flag = True
                elif ext in IMAGE_EXTENSIONS:
                    pdf_canvas = canvas.Canvas(final_output_pdf_path, pagesize=A4)
                    if self._add_image_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        conversion_successful_flag = True
                elif ext in TEXT_EXTENSIONS:
                    pdf_canvas = canvas.Canvas(final_output_pdf_path, pagesize=A4)
                    if self._add_text_file_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        conversion_successful_flag = True
                elif ext in RTF_EXTENSIONS:
                    pdf_canvas = canvas.Canvas(final_output_pdf_path, pagesize=A4)
                    if self._add_rtf_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        conversion_successful_flag = True
                elif ext in HTML_EXTENSIONS:
                    if self._convert_html_to_pdf_file(file_path, final_output_pdf_path):
                        conversion_successful_flag = True
                elif ext in SVG_EXTENSIONS:
                    pdf_canvas = canvas.Canvas(final_output_pdf_path, pagesize=A4)
                    if self._add_svg_to_pdf_canvas(file_path, pdf_canvas):
                        pdf_canvas.save()
                        conversion_successful_flag = True
                elif ext in (MS_WORD_EXTENSIONS + MS_EXCEL_EXTENSIONS + MS_POWERPOINT_EXTENSIONS +
                             ODF_TEXT_EXTENSIONS + ODF_SPREADSHEET_EXTENSIONS + ODF_PRESENTATION_EXTENSIONS):
                    self._log_to_console(f"Konvertiere {current_file_basename} zu PDF...")
                    QApplication.processEvents()
                    if self._convert_office_to_pdf_native(file_path, final_output_pdf_path):
                        if os.path.exists(final_output_pdf_path) and os.path.getsize(final_output_pdf_path) > 0:
                             self._log_to_console(f"{current_file_basename} erfolgreich als PDF gespeichert.")
                             conversion_successful_flag = True
                        else:
                            self._log_to_console(f"Konvertierte PDF für {current_file_basename} ist leer oder nicht vorhanden (separat).")
                    # If _convert_office_to_pdf_native returned False, status label is already set by it.
                else:
                    self._log_to_console(f"Dateityp {ext} von '{current_file_basename}' wird nicht unterstützt.")

                if conversion_successful_flag:
                    num_successful += 1
                    processed_file_paths.append(final_output_pdf_path)
                else:
                    num_errors += 1
                    error_on_label = self.processing_status_label.text() # Get status after failed attempt
                    if not first_error_detail:
                         # Avoid capturing generic "Processing file X/Y..." if a more specific error wasn't set by a sub-function
                        if not error_on_label.startswith("Verarbeite Datei") and "erfolgreich" not in error_on_label.lower():
                            first_error_detail = f"Datei '{current_file_basename}': {error_on_label}"
                        elif error_on_label.startswith("Verarbeite Datei") : # Fallback if no other specific error was set on label
                             first_error_detail = f"Datei '{current_file_basename}': Konnte nicht verarbeitet werden (keine spezifische Fehlermeldung)."

            except Exception as e:
                error_msg = f"Fehler bei Datei '{current_file_basename}': {e}"
                self._log_to_console(error_msg)
                print(f"Error processing file {file_path} for separate PDF: {e}")
                num_errors += 1
                if not first_error_detail:
                    first_error_detail = error_msg # Use the exception message directly
                if os.path.exists(final_output_pdf_path) and not conversion_successful_flag:
                    try:
                        os.remove(final_output_pdf_path)
                    except Exception as e_del:
                        print(f"Could not delete partial PDF {final_output_pdf_path}: {e_del}")
        
        final_message = f"Verarbeitung abgeschlossen. {num_successful} Datei(en) erfolgreich als separate PDFs gespeichert."
        if num_errors > 0:
            final_message += f" {num_errors} Datei(en) konnten nicht verarbeitet werden."
        if first_error_detail:
             final_message += f"\n\nDetails zum ersten Fehler:\n{first_error_detail}"
        
        # Log the completion
        if hasattr(self.app_root, 'log_message'):
            if num_errors == 0:
                self.app_root.log_message(f"Verarbeitung erfolgreich abgeschlossen: {num_successful} separate PDF(s) erstellt")
            else:
                self.app_root.log_message(f"Verarbeitung abgeschlossen mit Fehlern: {num_successful} erfolgreich, {num_errors} Fehler")
        
        reply = QMessageBox.information(self, "Verarbeitung abgeschlossen", 
                                        final_message + "\\n\\nMöchten Sie den Ausgabeordner öffnen?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                        QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes and os.path.exists(output_directory):
            try:
                # Use os.startfile on Windows, and 'open' on macOS, 'xdg-open' on Linux
                if platform.system() == "Windows":
                    os.startfile(output_directory)
                elif platform.system() == "Darwin": # macOS
                    subprocess.run(["open", output_directory])
                else: # Linux and other Unix-like
                    subprocess.run(["xdg-open", output_directory])
            except Exception as e:
                QMessageBox.warning(self, "Ordner öffnen Fehler", f"Der Ordner '{output_directory}' konnte nicht geöffnet werden.\\nFehler: {e}")

        self._log_to_console("Bereit.")

    # --- Conversion Helper Methods (largely unchanged from ConvertTab, ensure they use 'canvas' (c) correctly) ---
    # Make sure _convert_html_to_pdf_file is defined or adapt usage

    def _convert_html_to_pdf_file(self, html_file_path, output_pdf_path):
        """Converts an HTML file to a PDF file at output_pdf_path."""
        try:
            with open(html_file_path, "r", encoding="utf-8") as html_file:
                source_html = html_file.read()
            with open(output_pdf_path, "w+b") as result_file:
                pisa_status = pisa.CreatePDF(source_html, dest=result_file)
            if pisa_status.err:
                raise Exception(f"pisa error: {pisa_status.err}")
            
            # Check if the output file was actually created and has content
            if not os.path.exists(output_pdf_path) or os.path.getsize(output_pdf_path) == 0:
                raise Exception("PDF-Datei wurde nicht erstellt oder ist leer")
                
            return True  # Indicate successful HTML conversion
        except Exception as e:
            print(f"Error converting HTML {html_file_path} to PDF: {e}")
            # Propagate error to be caught by caller
            raise Exception(f"Fehler beim Konvertieren von HTML {os.path.basename(html_file_path)}: {e}")


    def _add_image_to_pdf_canvas(self, image_path, pdf_canvas):
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            # Handle multi-frame GIFs (convert each frame to PDF page)
            if img.format == "GIF" and hasattr(img, 'n_frames') and img.n_frames > 1:
                for i, frame in enumerate(ImageSequence.Iterator(img)):
                    if i > 0: # Add new page for subsequent frames
                        pdf_canvas.showPage()
                    
                    frame_img = frame.convert("RGBA") # Ensure consistent format
                    frame_width, frame_height = frame_img.size
                    
                    # Scale to fit A4 page while maintaining aspect ratio
                    a4_width, a4_height = A4
                    ratio = min(a4_width/frame_width, a4_height/frame_height)
                    new_width, new_height = frame_width*ratio, frame_height*ratio
                    x_offset = (a4_width - new_width) / 2
                    y_offset = (a4_height - new_height) / 2

                    # Use a temporary file for ReportLab ImageReader with PIL images
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_frame_file:
                        frame_img.save(tmp_frame_file.name, format='PNG')
                        rl_image = ReportLabImageReader(tmp_frame_file.name)
                        pdf_canvas.drawImage(rl_image, x_offset, y_offset, width=new_width, height=new_height, preserveAspectRatio=True, anchor='c')
                    os.remove(tmp_frame_file.name) # Clean up temp file
            else: # Single frame image (JPG, PNG, non-animated GIF, etc.)
                # Scale to fit A4 page while maintaining aspect ratio
                a4_width, a4_height = A4
                ratio = min(a4_width/img_width, a4_height/img_height)
                new_width, new_height = img_width*ratio, img_height*ratio
                x_offset = (a4_width - new_width) / 2
                y_offset = (a4_height - new_height) / 2
                
                # For PIL images, especially those not directly supported by ReportLab, save to a temp file
                # Ensure image is in a format ReportLab can handle well (e.g. PNG, or JPG directly if path is used)
                # If img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info): # Check for alpha
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file: # Save as PNG to preserve transparency
                    img.save(tmp_file.name, format='PNG') # Convert to PNG for RL
                    rl_image = ReportLabImageReader(tmp_file.name)
                    pdf_canvas.drawImage(rl_image, x_offset, y_offset, width=new_width, height=new_height, preserveAspectRatio=True, anchor='c')
                os.remove(tmp_file.name) # Clean up temp file

            # pdf_canvas.showPage() # showPage is called by the loop for GIFs, or once after all content for single PDF.
            # For separate PDFs, c.save() is called after this. For single PDF, this adds to current page of temp_pdf.
            return True  # Indicate successful image processing
        except UnidentifiedImageError as e:
            print(f"Error processing image {image_path}: Unidentified image format - {e}")
            raise Exception(f"Unbekanntes Bildformat für {os.path.basename(image_path)}: {e}")
        except Exception as e:
            print(f"Error processing image {image_path}: {e}")
            raise Exception(f"Fehler bei Bildverarbeitung {os.path.basename(image_path)}: {e}")

    def _render_text_to_pdf_canvas(self, text_content, pdf_canvas, source_filename="Text"):
        # Based on original, simpler text rendering
        text_object = pdf_canvas.beginText()
        text_object.setFont("Helvetica", 10)
        text_object.setTextOrigin(inch, A4[1] - inch) # Start near top-left
        
        max_line_width = A4[0] - 2 * inch # Max width for text lines
        line_height = 12 # Points

        y_position = A4[1] - inch
        first_page = True

        lines = text_content.split('\n')
        for line in lines:
            # Simple line splitting if too long (better: use Paragraph from reportlab.platypus)
            while pdf_canvas.stringWidth(line, "Helvetica", 10) > max_line_width:
                # Find a split point (e.g., at a space)
                split_at = -1
                for i in range(len(line) -1, 0, -1):
                    if line[i] == ' ':
                        if pdf_canvas.stringWidth(line[:i], "Helvetica", 10) <= max_line_width:
                            split_at = i
                            break
                if split_at == -1: # Cannot split nicely, just truncate (or force split)
                    # This is a very basic split, might cut words.
                    # A more robust solution would use ReportLab's Paragraph.
                    temp_line_part = line
                    while pdf_canvas.stringWidth(temp_line_part, "Helvetica", 10) > max_line_width:
                        temp_line_part = temp_line_part[:-1]
                    
                    split_at = len(temp_line_part)
                    if split_at == 0 and len(line) > 0: # single very long char string
                         split_at = int(max_line_width / pdf_canvas.stringWidth("X", "Helvetica", 10)) # rough char count


                current_line_part = line[:split_at]
                line = line[split_at:].lstrip() # Remainder for next iteration/line

                if y_position < inch: # Check for new page
                    pdf_canvas.drawText(text_object)
                    pdf_canvas.showPage()
                    text_object = pdf_canvas.beginText()
                    text_object.setFont("Helvetica", 10)
                    text_object.setTextOrigin(inch, A4[1] - inch)
                    y_position = A4[1] - inch
                    first_page = False

                text_object.setTextOrigin(inch, y_position)
                text_object.textLine(current_line_part)
                y_position -= line_height
            
            # Process (remaining part of) the line
            if y_position < inch: # Check for new page
                pdf_canvas.drawText(text_object)
                pdf_canvas.showPage()
                text_object = pdf_canvas.beginText()
                text_object.setFont("Helvetica", 10)
                text_object.setTextOrigin(inch, A4[1] - inch)
                y_position = A4[1] - inch
                first_page = False
            
            text_object.setTextOrigin(inch, y_position)
            text_object.textLine(line)
            y_position -= line_height

        pdf_canvas.drawText(text_object)
        # pdf_canvas.showPage() # Called by save or outer loop if needed

    def _add_text_file_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            self._render_text_to_pdf_canvas(content, pdf_canvas, source_filename=os.path.basename(file_path))
            return True  # Indicate successful text processing
        except Exception as e:
            print(f"Error processing text file {file_path}: {e}")
            raise Exception(f"Fehler beim Lesen/Rendern der Textdatei {os.path.basename(file_path)}: {e}")

    def _add_rtf_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f: # RTF might have weird encodings sometimes
                rtf_content = f.read()
            text_content = rtf_to_text(rtf_content)
            self._render_text_to_pdf_canvas(text_content, pdf_canvas, source_filename=os.path.basename(file_path))
            return True  # Indicate successful RTF processing
        except Exception as e:
            print(f"Error processing RTF file {file_path}: {e}")
            raise Exception(f"Fehler beim Verarbeiten der RTF-Datei {os.path.basename(file_path)}: {e}")

    def _add_svg_to_pdf_canvas(self, file_path, pdf_canvas):
        # svglib's svg2rlg converts SVG to a ReportLab Drawing object
        try:
            drawing = svg2rlg(file_path)
            if drawing:
                # Scale drawing to fit the page if it's too large, maintaining aspect ratio
                page_width, page_height = pdf_canvas._pagesize
                available_width = page_width - 2 * inch # Assuming 1 inch margins
                available_height = page_height - 2 * inch

                if drawing.width > available_width or drawing.height > available_height:
                    scale_w = available_width / drawing.width if drawing.width else 1
                    scale_h = available_height / drawing.height if drawing.height else 1
                    scale = min(scale_w, scale_h)
                    drawing.width *= scale
                    drawing.height *= scale
                    drawing.scale(scale, scale)
                
                # Center the drawing on the page
                x_offset = (page_width - drawing.width) / 2
                y_offset = (page_height - drawing.height) / 2
                
                drawing.drawOn(pdf_canvas, x_offset, y_offset)
                pdf_canvas.showPage()
                self._log_to_console(f"SVG '{os.path.basename(file_path)}' zu PDF hinzugefügt.")
                return True # Indicate success
            else:
                self._log_to_console(f"Fehler beim Parsen von SVG '{os.path.basename(file_path)}'.")
        except Exception as e:
            self._log_to_console(f"Fehler beim Konvertieren von SVG '{os.path.basename(file_path)}': {e}")
        return False # Indicate failure

    def _is_msoffice_app_available(self, app_name):
        if os.name != 'nt' or not win32com or not pythoncom:
            print(f"MSOffice check for {app_name}: Early exit (not Windows or win32com/pythoncom not imported).")
            return False
        
        com_initialized_here = False
        try:
            # Try to initialize COM for this check. If it's already initialized on this thread,
            # CoInitialize will return S_FALSE, which is not an error.
            # If it returns S_OK, then we must call CoUninitialize.
            # If it raises an error, we can't proceed.
            hr = pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED) # Or COINIT_MULTITHREADED
            # S_OK = 0, S_FALSE = 1. Both mean success in terms of usability.
            if hr == 0 or hr == 1:
                 com_initialized_here = True

            win32com.client.Dispatch(app_name)
            # print(f"MSOffice check for {app_name}: Dispatch successful.") # Optional: for verbose success logging
            return True
        except pythoncom.com_error as e:
            print(f"MSOffice check for {app_name}: COM Error during Dispatch: {e}")
            # This often means the application isn't installed, not registered for COM, or a permissions issue.
            return False
        except Exception as e:
            # Catches other potential errors, e.g., if pythoncom itself is None or Dispatch fails for non-COM reasons.
            print(f"MSOffice check for {app_name}: General error during Dispatch: {e}")
            return False
        finally:
            if com_initialized_here and pythoncom:
                try:
                    pythoncom.CoUninitialize()
                except pythoncom.com_error as e_uninit:
                    # This can happen if CoInitialize wasn't actually the first call on the thread, 
                    # or if an error occurred that left COM in an unstable state.
                    print(f"MSOffice check for {app_name}: COM Error during CoUninitialize: {e_uninit}")
                except Exception as e_uninit_general:
                    print(f"MSOffice check for {app_name}: General error during CoUninitialize: {e_uninit_general}")

    def _find_libreoffice_soffice(self):
        if shutil.which("soffice"): # Check PATH first
            return shutil.which("soffice")

        system = platform.system()
        possible_paths = []
        if system == "Windows":
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
            possible_paths = [
                os.path.join(program_files, "LibreOffice", "program", "soffice.exe"),
                os.path.join(program_files_x86, "LibreOffice", "program", "soffice.exe"),
            ]
        elif system == "Linux":
            possible_paths = [
                "/usr/bin/soffice",
                "/usr/local/bin/soffice",
                "/opt/libreoffice/program/soffice", # Common for manual installs
                # Snap path could be /snap/bin/libreoffice.soffice but might be harder to detect reliably
            ]
        elif system == "Darwin": # macOS
            possible_paths = [
                "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            ]

        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        return None

    def _convert_office_to_pdf_native(self, input_path, output_pdf_path):
        """
        Converts an office document to PDF.
        Tries MS Office first if available (Windows only), then falls back to LibreOffice.
        output_pdf_path is the full desired path for the output PDF.
        Returns True on success, False on failure.
        """
        _, ext = os.path.splitext(input_path)
        ext = ext.lower()
        input_basename = os.path.basename(input_path)
        
        # Log the conversion attempt
        print(f"Starting conversion of {input_basename} ({ext}) to PDF")
        
        # COM Initialization for MS Office operations
        com_initialized = False
        if os.name == 'nt' and pythoncom:
            try:
                pythoncom.CoInitialize()
                com_initialized = True
                print(f"COM initialized successfully for {input_basename}")
            except Exception as e:
                print(f"Failed to CoInitialize: {e}. Trying CoInitializeEx.")
                try:
                    pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)
                    com_initialized = True
                    print(f"COM initialized with CoInitializeEx for {input_basename}")
                except Exception as e2:
                    print(f"Failed to CoInitializeEx: {e2}")
                    self._log_to_console(f"COM Initialization failed for {input_basename}: {e2}")
                    # Proceed without COM, relying on LibreOffice or if converters don't need explicit init
        
        try:
            # 1. MS Word (.doc, .docx)
            if ext in MS_WORD_EXTENSIONS:
                if self.msword_available and convert_docx_to_pdf and win32com: # win32com check for safety
                    self._log_to_console(f"Versuche {input_basename} mit MS Word zu konvertieren...")
                    QApplication.processEvents()
                    try:
                        print(f"Attempting MS Word conversion: {input_path} -> {output_pdf_path}")
                        convert_docx_to_pdf(os.path.abspath(input_path), os.path.abspath(output_pdf_path))
                        if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
                            self._log_to_console(f"{input_basename} erfolgreich mit MS Word konvertiert.")
                            print(f"MS Word conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS Word Konvertierung von {input_basename} fehlgeschlagen (Datei nicht erstellt oder leer)."
                            self._log_to_console(error_msg)
                            print(f"MS Word conversion failed: {error_msg}")
                    except Exception as e:
                        error_msg = f"MS Word Konvertierungsfehler für {input_basename}: {e}"
                        self._log_to_console(error_msg)
                        print(f"MS Word conversion error for {input_path}: {e}")
                    # Fall through to LibreOffice if MS Word conversion fails
                else:
                    print(f"MS Word not available for {input_basename}. MSWord available: {self.msword_available}, convert_docx_to_pdf: {convert_docx_to_pdf is not None}, win32com: {win32com is not None}")

            # 2. MS PowerPoint (.ppt, .pptx)
            elif ext in MS_POWERPOINT_EXTENSIONS:
                if self.mspowerpoint_available and pptxtopdf_convert_bulk and win32com:
                    self._log_to_console(f"Versuche {input_basename} mit MS PowerPoint zu konvertieren...")
                    QApplication.processEvents()
                    temp_dir_powerpoint = tempfile.TemporaryDirectory()
                    try:
                        print(f"Attempting MS PowerPoint conversion: {input_path} -> temp dir: {temp_dir_powerpoint.name}")
                        # pptxtopdf_convert_bulk saves to output_dir with original name + .pdf
                        pptxtopdf_convert_bulk(os.path.abspath(input_path), temp_dir_powerpoint.name)
                        
                        original_basename_no_ext = os.path.splitext(input_basename)[0]
                        converted_pdf_in_temp = os.path.join(temp_dir_powerpoint.name, original_basename_no_ext + ".pdf")

                        if os.path.exists(converted_pdf_in_temp) and os.path.getsize(converted_pdf_in_temp) > 0:
                            shutil.move(converted_pdf_in_temp, os.path.abspath(output_pdf_path))
                            self._log_to_console(f"{input_basename} erfolgreich mit MS PowerPoint konvertiert.")
                            print(f"MS PowerPoint conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS PowerPoint Konvertierung fehlgeschlagen für {input_basename} (Datei nicht erstellt oder leer)."
                            self._log_to_console(error_msg)
                            print(f"MS PowerPoint conversion failed: {error_msg}")
                    except Exception as e:
                        error_msg = f"MS PowerPoint Konvertierungsfehler für {input_basename}: {e}"
                        self._log_to_console(error_msg)
                        print(f"MS PowerPoint conversion error for {input_path}: {e}")
                    finally:
                        temp_dir_powerpoint.cleanup()
                    # Fall through to LibreOffice
                else:
                    print(f"MS PowerPoint not available for {input_basename}. MSPowerPoint available: {self.mspowerpoint_available}, pptxtopdf_convert_bulk: {pptxtopdf_convert_bulk is not None}, win32com: {win32com is not None}")

            # 3. MS Excel (.xls, .xlsx)
            elif ext in MS_EXCEL_EXTENSIONS:
                if self.msexcel_available and win32com:
                    self._log_to_console(f"Versuche {input_basename} mit MS Excel zu konvertieren...")
                    QApplication.processEvents()
                    excel_app = None
                    try:
                        print(f"Attempting MS Excel conversion: {input_path} -> {output_pdf_path}")
                        excel_app = win32com.client.Dispatch("Excel.Application")
                        excel_app.Visible = False # Run in background
                        workbook = excel_app.Workbooks.Open(os.path.abspath(input_path))
                        # Type 0 is for PDF format
                        workbook.ExportAsFixedFormat(0, os.path.abspath(output_pdf_path))
                        workbook.Close(SaveChanges=False)
                        
                        if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
                            self._log_to_console(f"{input_basename} erfolgreich mit MS Excel konvertiert.")
                            print(f"MS Excel conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS Excel Konvertierung fehlgeschlagen für {input_basename} (Datei nicht erstellt oder leer)."
                            self._log_to_console(error_msg)
                            print(f"MS Excel conversion failed: {error_msg}") 
                    except Exception as e:
                        error_msg = f"MS Excel Konvertierungsfehler für {input_basename}: {e}"
                        self._log_to_console(error_msg)
                        print(f"MS Excel conversion error for {input_path}: {e}")
                    finally:
                        if excel_app:
                            try:
                                excel_app.Quit()
                            except:
                                pass
                        # Ensure excel process is not lingering, though Quit should handle it.
                        # Further process killing could be added here if necessary.
                    # Fall through to LibreOffice
                else:
                    print(f"MS Excel not available for {input_basename}. MSExcel available: {self.msexcel_available}, win32com: {win32com is not None}")

            # 4. LibreOffice (ODF formats and fallback for MS Office)
            if self.soffice_path:
                self._log_to_console(f"Versuche {input_basename} mit LibreOffice zu konvertieren...")
                QApplication.processEvents()
                print(f"Attempting LibreOffice conversion using: {self.soffice_path}")
                # LibreOffice --convert-to pdf saves the file in --outdir with the original name + .pdf
                # So we use a temporary output directory and then move the file.
                temp_dir_libreoffice = tempfile.TemporaryDirectory()
                try:
                    cmd = [
                        self.soffice_path,
                        "--headless",       # Run in background
                        "--convert-to", "pdf",
                        "--outdir", temp_dir_libreoffice.name,
                        os.path.abspath(input_path)
                    ]
                    print(f"LibreOffice command: {' '.join(cmd)}")
                    # Increased timeout for potentially large files
                    process = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120) 
                    
                    original_basename_no_ext = os.path.splitext(input_basename)[0]
                    converted_pdf_in_temp = os.path.join(temp_dir_libreoffice.name, original_basename_no_ext + ".pdf")
                    print(f"Looking for converted file at: {converted_pdf_in_temp}")

                    if os.path.exists(converted_pdf_in_temp) and os.path.getsize(converted_pdf_in_temp) > 0:
                        shutil.move(converted_pdf_in_temp, os.path.abspath(output_pdf_path))
                        self._log_to_console(f"{input_basename} erfolgreich mit LibreOffice konvertiert.")
                        print(f"LibreOffice conversion successful for {input_basename}")
                        return True
                    else:
                        err_msg = process.stderr if process.stderr else "Unbekannter Fehler (Zieldatei nicht gefunden oder leer)."
                        error_detail = f"LibreOffice Konvertierung von {input_basename} fehlgeschlagen: {err_msg}"
                        self._log_to_console(error_detail)
                        print(f"LibreOffice conversion failed for {input_path}. stderr: {process.stderr}, stdout: {process.stdout}")
                        print(f"Files in temp directory: {os.listdir(temp_dir_libreoffice.name) if os.path.exists(temp_dir_libreoffice.name) else 'Directory not found'}")
                        
                except subprocess.CalledProcessError as e:
                    error_detail = f"LibreOffice Prozessfehler bei {input_basename}: {e.stderr if e.stderr else 'Unbekannter Fehler'}"
                    self._log_to_console(error_detail)
                    print(f"LibreOffice CalledProcessError for {input_path}: stderr: {e.stderr}, stdout: {e.stdout}, returncode: {e.returncode}")
                except subprocess.TimeoutExpired:
                    error_detail = f"LibreOffice Konvertierung von {input_basename} Zeitüberschreitung (>120s)."
                    self._log_to_console(error_detail)
                    print(f"LibreOffice TimeoutExpired for {input_path}")
                except Exception as e:
                    error_detail = f"Allgemeiner LibreOffice Fehler bei {input_basename}: {e}"
                    self._log_to_console(error_detail)
                    print(f"LibreOffice general error for {input_path}: {e}")
                finally:
                    temp_dir_libreoffice.cleanup()
            else: # No soffice_path
                if ext in MS_WORD_EXTENSIONS or ext in MS_EXCEL_EXTENSIONS or ext in MS_POWERPOINT_EXTENSIONS:
                    # This message is shown if MS Office conversion was not available or failed, and LibreOffice is also not found.
                    error_detail = f"Kein MS Office oder LibreOffice für {input_basename} gefunden. Installieren Sie LibreOffice oder MS Office."
                    self._log_to_console(error_detail)
                    print(f"No converters available for MS Office file: {input_basename}")
                elif ext in ODF_TEXT_EXTENSIONS or ext in ODF_SPREADSHEET_EXTENSIONS or ext in ODF_PRESENTATION_EXTENSIONS:
                    error_detail = f"LibreOffice nicht gefunden für ODF-Datei {input_basename}. Installieren Sie LibreOffice."
                    self._log_to_console(error_detail)
                    print(f"LibreOffice not found for ODF file: {input_basename}")
                # If it's not an office file type this function shouldn't have been called.
                # However, if it was, this is a generic message.
                else:
                    error_detail = f"Kein geeigneter Konverter für {input_basename} gefunden."
                    self._log_to_console(error_detail)
                    print(f"No suitable converter found for file: {input_basename}")

            # If we reach here, all conversion attempts failed
            final_error = f"Konvertierung von {input_basename} fehlgeschlagen. Überprüfen Sie die Installation von MS Office/LibreOffice."
            self._log_to_console(final_error)
            print(f"All conversion attempts failed for: {input_basename}")
            return False

        finally:
            if com_initialized and pythoncom:
                try:
                    pythoncom.CoUninitialize()
                    print(f"COM uninitialized for {input_basename}")
                except Exception as e:
                    print(f"Error during CoUninitialize: {e}") # Log if CoUninitialize fails
                    pass

    def _log_dependency_status(self):
        """Log the status of all conversion dependencies."""
        print("=== PDF Tool Dependency Status ===")
        print(f"LibreOffice soffice path: {self.soffice_path if self.soffice_path else 'NICHT GEFUNDEN'}")
        print(f"MS Word available: {'✓' if self.msword_available else '✗'}")
        print(f"MS Excel available: {'✓' if self.msexcel_available else '✗'}")
        print(f"MS PowerPoint available: {'✓' if self.mspowerpoint_available else '✗'}")
        
        # Count total available converters
        available_count = sum([
            bool(self.soffice_path),
            self.msword_available,
            self.msexcel_available, 
            self.mspowerpoint_available
        ])
        
        if available_count == 0:
            print("⚠️  WARNUNG: Keine Office-Konverter verfügbar!")
            print("   Installieren Sie LibreOffice oder MS Office für Office-Dokumentkonvertierung.")
        else:
            print(f"✓ {available_count} Konverter verfügbar")
        print("=" * 35)

    def _show_detailed_error(self, title, message, detailed_info=None):
        """Show a detailed error message with expandable details."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if detailed_info:
            msg_box.setDetailedText(detailed_info)
        
        msg_box.exec()

    def _get_conversion_capability_info(self):
        """Get detailed information about conversion capabilities."""
        info = []
        info.append("VERFÜGBARE KONVERTER:")
        
        if self.soffice_path:
            info.append(f"✓ LibreOffice: {self.soffice_path}")
            info.append("  Unterstützt: .doc, .docx, .xls, .xlsx, .ppt, .pptx, .odt, .ods, .odp")
        else:
            info.append("✗ LibreOffice: Nicht installiert")
        
        if self.msword_available:
            info.append("✓ MS Word: Verfügbar")
            info.append("  Unterstützt: .doc, .docx")
        else:
            info.append("✗ MS Word: Nicht verfügbar")
        
        if self.msexcel_available:
            info.append("✓ MS Excel: Verfügbar") 
            info.append("  Unterstützt: .xls, .xlsx")
        else:
            info.append("✗ MS Excel: Nicht verfügbar")
        
        if self.mspowerpoint_available:
            info.append("✓ MS PowerPoint: Verfügbar")
            info.append("  Unterstützt: .ppt, .pptx")
        else:
            info.append("✗ MS PowerPoint: Nicht verfügbar")
        
        info.append("\nIMMER UNTERSTÜTZTE FORMATE:")
        info.append("• Bilder: .jpg, .jpeg, .png, .bmp, .gif, .tiff, .heic, .heif")
        info.append("• Text: .txt, .rtf")
        info.append("• Web: .html, .htm")
        info.append("• Vektor: .svg")
        info.append("• PDF: .pdf (direktes Zusammenführen)")
        
        return "\n".join(info)

    # New public slot for adding a single file (e.g., from file explorer double-click)
    def add_single_file_from_path(self, file_path: str):
        if not file_path or not os.path.isfile(file_path):
            print(f"Ungültiger Dateipfad von Explorer erhalten: {file_path}")
            self._log_to_console(f"Ungültiger Pfad: {os.path.basename(file_path if file_path else "N/A")}")
            return

        _, ext = os.path.splitext(file_path.lower())
        # Ensure ALL_SUPPORTED_EXT_PATTERNS_LIST is comprehensive enough for files from explorer
        # Typically, explorer will show PDFs, so this check should pass for intended files.
        if ext not in ALL_SUPPORTED_EXT_PATTERNS_LIST:
            QMessageBox.warning(self, "Nicht unterstützter Dateityp", 
                                f"Die Datei '{os.path.basename(file_path)}' vom Explorer hat einen nicht unterstützten Dateityp ({ext}).")
            self._log_to_console(f"Explorer: Typ nicht unterstützt: {os.path.basename(file_path)}")
            return

        # Use the existing logic to add to GUI list and internal tracking
        self._add_files_to_gui_list([file_path]) # Pass as a list

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
        modify_widget = ModifyPagesTab(app_root=self.app_root)
        layout.addWidget(modify_widget)
        
        dialog.exec()



# For basic testing if run directly (optional)
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    # import qdarktheme
    # qdarktheme.setup_theme("light") # or "dark"
    
    main_win = QWidget() # Using QWidget for simple test window
    main_win.setWindowTitle("File Processing Tab Test")
    layout = QVBoxLayout(main_win)
    tab = FileProcessingTab() # Test the new tab
    layout.addWidget(tab)
    main_win.resize(800, 600)
    main_win.show()
    
    sys.exit(app.exec()) 