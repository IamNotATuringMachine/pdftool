import os
import io
import shutil # For copying PDFs in separate processing
import tempfile
import subprocess # Added
import platform # Added
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
    QApplication, QFrame, QFileIconProvider
)
from PySide6.QtCore import Qt, QUrl, QSize, QFileInfo, QEvent
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

from gui.modify_pages_tab import ModifyPagesTab # Added import

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
    def __init__(self, app_root=None):
        super().__init__()
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

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        controls_group = QGroupBox("Dateien zur Verarbeitung (Konvertieren & Zusammenführen)") # Updated title
        controls_group_layout = QHBoxLayout(controls_group)

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

        controls_group_layout.addWidget(self.file_list_widget, 1)

        buttons_layout = QVBoxLayout()
        self.add_button = QPushButton("Dateien hinzufügen")
        self.add_button.clicked.connect(self._add_files_to_process_list) 
        buttons_layout.addWidget(self.add_button)
        self.remove_button = QPushButton("Auswahl entfernen")
        self.remove_button.clicked.connect(self._remove_file_from_process_list)
        buttons_layout.addWidget(self.remove_button)
        self.move_up_button = QPushButton("Nach oben")
        self.move_up_button.clicked.connect(self._move_process_item_up) 
        buttons_layout.addWidget(self.move_up_button)
        self.move_down_button = QPushButton("Nach unten")
        self.move_down_button.clicked.connect(self._move_process_item_down)
        buttons_layout.addWidget(self.move_down_button)
        buttons_layout.addStretch()
        controls_group_layout.addLayout(buttons_layout)
        main_layout.addWidget(controls_group)

        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setContentsMargins(0,0,0,0)
        self.single_pdf_output_check = QCheckBox("Alle Dateien in eine einzelne PDF-Datei zusammenfassen/ausgeben") 
        self.single_pdf_output_check.setChecked(True)
        options_layout.addWidget(self.single_pdf_output_check)
        options_layout.addStretch()
        main_layout.addWidget(options_frame)

        action_layout = QVBoxLayout()
        self.process_button = QPushButton("Dateien verarbeiten & speichern") 
        self.process_button.clicked.connect(self._execute_processing) 
        action_layout.addWidget(self.process_button)
        self.processing_status_label = QLabel("") 
        self.processing_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.processing_status_label)
        main_layout.addLayout(action_layout)

        # --- Add ModifyPagesTab section ---
        modify_pages_group = QGroupBox("Einzelnes PDF bearbeiten (Seiten löschen/extrahieren)")
        modify_pages_layout = QVBoxLayout(modify_pages_group)
        self.modify_pages_widget = ModifyPagesTab(app_root=self.app_root) # Instantiate ModifyPagesTab
        modify_pages_layout.addWidget(self.modify_pages_widget)
        main_layout.addWidget(modify_pages_group)
        # --- End ModifyPagesTab section ---

    def _prompt_and_remove_selected_files_on_key_press(self):
        if not self.file_list_widget.selectedItems():
            return

        num_selected = len(self.file_list_widget.selectedItems())
        file_s = "Datei" if num_selected == 1 else "Dateien"
        message = f"Möchten Sie die ausgewählte(n) {num_selected} {file_s} wirklich aus der Liste entfernen?"
        
        reply = QMessageBox.warning(self, "Auswahl entfernen", message,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self._remove_file_from_process_list()

    def _on_file_item_double_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)
                self.processing_status_label.setText(f"'{os.path.basename(file_path)}' geöffnet.")
            except Exception as e:
                self.processing_status_label.setText(f"Fehler beim Öffnen von '{os.path.basename(file_path)}': {e}")
                QMessageBox.warning(self, "Datei öffnen Fehler", f"Die Datei '{file_path}' konnte nicht geöffnet werden.\\nFehler: {e}")
        else:
            self.processing_status_label.setText(f"Datei nicht gefunden: {file_path}")
            QMessageBox.warning(self, "Datei öffnen Fehler", f"Die Datei '{file_path}' wurde nicht gefunden oder ist nicht mehr verfügbar.")

    def eventFilter(self, watched, event):
        if watched == self.file_list_widget:
            if event.type() == QEvent.Type.KeyPress: # Use QEvent.Type.KeyPress
                key_event = QKeyEvent(event) # Cast to QKeyEvent
                if key_event.key() == Qt.Key.Key_Delete:
                    if self.file_list_widget.hasFocus() and self.file_list_widget.selectedItems():
                        self._prompt_and_remove_selected_files_on_key_press()
                        return True # Event handled
            
            if event.type() == QEvent.DragEnter:
                if event.mimeData().hasUrls(): # External file drag
                    is_supported_external = False
                    for url in event.mimeData().urls():
                        file_path = url.toLocalFile()
                        _, ext = os.path.splitext(file_path.lower())
                        if ext in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                            is_supported_external = True
                            break
                    if is_supported_external:
                        event.acceptProposedAction()
                    else:
                        event.ignore()
                    return True # Event handled by filter

                elif event.source() == self.file_list_widget and \
                     self.file_list_widget.dragDropMode() == QListWidget.DragDropMode.InternalMove:
                    event.acceptProposedAction() # Accept internal drag
                    return True # Event handled by filter
                else:
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
                if event.mimeData().hasUrls(): # External file drop
                    file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
                    supported_files = [fp for fp in file_paths if os.path.splitext(fp.lower())[1] in ALL_SUPPORTED_EXT_PATTERNS_LIST]
                    
                    if supported_files:
                        self._add_files_to_gui_list(supported_files)
                        event.acceptProposedAction()
                    else:
                        QMessageBox.information(self, "Keine unterstützten Dateien", "Keine der abgelegten Dateien hat einen unterstützten Dateityp.")
                        event.ignore()
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

    def _on_rows_moved(self, parent, start, end, destination, row):
        self._update_internal_file_list_from_widget()
        self.processing_status_label.setText("Dateireihenfolge geändert.")

    def _update_internal_file_list_from_widget(self):
        self.selected_files_for_processing.clear()
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            self.selected_files_for_processing.append(item.data(Qt.ItemDataRole.UserRole))

    def _refresh_list_widget_items(self):
        # Store the paths of currently selected items
        selected_paths = set()
        for item in self.file_list_widget.selectedItems():
            selected_paths.add(item.data(Qt.ItemDataRole.UserRole))

        self.file_list_widget.clear()
        for file_path in self.selected_files_for_processing:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setIcon(self._get_q_icon_for_file(file_path))
            self.file_list_widget.addItem(item)
            # Restore selection if this item was previously selected
            if file_path in selected_paths:
                item.setSelected(True)
    
    def _get_q_icon_for_file(self, file_path):
        provider = QFileIconProvider()
        file_info = QFileInfo(file_path)
        q_icon = provider.icon(file_info)
        if not q_icon or q_icon.isNull():
            _, ext = os.path.splitext(file_path.lower())
            pixmap = QPixmap(self.preview_size)
            pixmap.fill(Qt.GlobalColor.lightGray)
            painter = QPainter(pixmap)
            text = ext.replace(".","").upper() if ext else "FILE"
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.end()
            q_icon = QIcon(pixmap)
        return q_icon

    def _add_files_to_gui_list(self, file_paths): # Renamed from _add_files_to_list to avoid conflict if any
        added_count = 0
        skipped_unsupported = 0
        for file_path in file_paths:
            if not any(file_path == existing_fp for existing_fp in self.selected_files_for_processing):
                _, ext = os.path.splitext(file_path.lower())
                # ALL_SUPPORTED_EXT_PATTERNS_LIST now includes .pdf
                if ext in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                    self.selected_files_for_processing.append(file_path)
                    added_count += 1
                else:
                    skipped_unsupported +=1
                    print(f"Skipping unsupported file type: {file_path}")
        
        if added_count > 0:
            self._refresh_list_widget_items()
            self.processing_status_label.setText(f"{added_count} Datei(en) zur Liste hinzugefügt.")
        if skipped_unsupported > 0:
             QMessageBox.information(self, "Nicht unterstützte Dateien", f"{skipped_unsupported} Datei(en) wurden nicht hinzugefügt, da ihr Typ nicht unterstützt wird.")
        elif added_count == 0 and skipped_unsupported == 0 : # No new files added at all
             self.processing_status_label.setText("Keine neuen Dateien hinzugefügt (ggf. bereits vorhanden oder nicht unterstützt).")


    def _add_files_to_process_list(self): # Renamed method
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
            self.processing_status_label.setText("Keine Dateien zum Entfernen ausgewählt.")
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
            self.processing_status_label.setText(f"{removed_count} {file_s} aus der Liste entfernt.")
        else:
            self.processing_status_label.setText("Keine Dateien entfernt (möglicherweise bereits entfernt oder Fehler).")

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
            self.processing_status_label.setText(f"Datei {direction_text} verschoben.")

    def _move_process_item_up(self): # Renamed method
        self._move_item_in_list(-1)

    def _move_process_item_down(self): # Renamed method
        self._move_item_in_list(1)

    def _execute_processing(self): # Renamed method
        selected_qlist_items = self.file_list_widget.selectedItems()
        if not selected_qlist_items:
            # Show detailed message about what formats are supported
            detailed_info = self._get_conversion_capability_info()
            self._show_detailed_error(
                "Keine Auswahl", 
                "Bitte wählen Sie Dateien aus der Liste für die Verarbeitung aus.",
                detailed_info
            )
            return

        files_to_actually_process = [item.data(Qt.ItemDataRole.UserRole) for item in selected_qlist_items]

        # Check if all selected files exist
        missing_files = [f for f in files_to_actually_process if not os.path.exists(f)]
        if missing_files:
            missing_list = "\n".join([f"• {os.path.basename(f)}" for f in missing_files])
            self._show_detailed_error(
                "Fehlende Dateien",
                f"{len(missing_files)} Datei(en) wurden nicht gefunden:",
                f"Fehlende Dateien:\n{missing_list}"
            )
            return

        # self._update_internal_file_list_from_widget() # Ensure order is correct - order is from selection now

        if self.single_pdf_output_check.isChecked():
            if len(files_to_actually_process) == 1 and files_to_actually_process[0].lower().endswith(".pdf"):
                 QMessageBox.information(self, "Einzelne PDF", "Nur eine einzelne PDF-Datei ausgewählt. Es gibt nichts zum Zusammenführen. Sie können die Datei ggf. über 'Speichern unter' kopieren, wenn Sie den Modus für separate Dateien wählen.")
                 return
            self._process_files_to_single_pdf(files_to_actually_process) # Pass selected files
        else:
            self._process_files_to_separate_pdfs(files_to_actually_process) # Pass selected files

    def _process_files_to_single_pdf(self, files_to_process):
        if not files_to_process:
            self.processing_status_label.setText("Keine Dateien zum Verarbeiten ausgewählt.")
            return

        output_pdf_path, _ = QFileDialog.getSaveFileName(self, "Einzelne PDF speichern unter...",
                                                         os.path.join(os.getcwd(), "kombinierte_datei.pdf"),
                                                         "PDF-Dateien (*.pdf)")
        if not output_pdf_path:
            self.processing_status_label.setText("Speichervorgang abgebrochen.")
            return

        self.processing_status_label.setText("Verarbeite Dateien zu einer einzelnen PDF...")
        QApplication.processEvents()

        output_pdf_writer = PdfWriter()
        num_successful = 0
        num_errors = 0
        first_error_detail = None # Added to capture first error detail

        for i, file_path in enumerate(files_to_process):
            current_file_basename = os.path.basename(file_path)
            self.processing_status_label.setText(f"Verarbeite Datei {i+1}/{len(files_to_process)}: {current_file_basename}")
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
                    self.processing_status_label.setText(f"PDF '{current_file_basename}' hinzugefügt.")
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
                    self.processing_status_label.setText(f"Konvertiere {current_file_basename} zu PDF...")
                    QApplication.processEvents()
                    if self._convert_office_to_pdf_native(file_path, temp_office_pdf_path):
                        if os.path.exists(temp_office_pdf_path) and os.path.getsize(temp_office_pdf_path) > 0:
                            try:
                                office_pdf_reader = PdfReader(temp_office_pdf_path)
                                for page in office_pdf_reader.pages:
                                    output_pdf_writer.add_page(page)
                                self.processing_status_label.setText(f"{current_file_basename} zu PDF hinzugefügt.")
                                file_processed_successfully = True
                            except Exception as e:
                                error_msg = f"Fehler beim Lesen der konvertierten PDF für {current_file_basename}: {e}"
                                self.processing_status_label.setText(error_msg)
                                print(f"Error reading converted PDF {temp_office_pdf_path}: {e}")
                        else:
                             self.processing_status_label.setText(f"Konvertierte PDF für {current_file_basename} ist leer oder nicht vorhanden.")
                    # If _convert_office_to_pdf_native returned False, status label is already set by it.
                else:
                    self.processing_status_label.setText(f"Dateityp {ext} von '{current_file_basename}' wird nicht unterstützt.")

                if file_processed_successfully:
                    num_successful += 1
                else:
                    num_errors += 1
                    error_on_label = self.processing_status_label.text() # Get status after failed attempt
                    if not first_error_detail:
                        first_error_detail = f"Datei '{current_file_basename}': {error_on_label}"

            except Exception as e:
                error_msg = f"Fehler bei Datei '{current_file_basename}': {e}"
                self.processing_status_label.setText(error_msg)
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
        
        self.processing_status_label.setText("Bereit.")

    def _process_files_to_separate_pdfs(self, files_to_process):
        if not files_to_process:
            self.processing_status_label.setText("Keine Dateien zum Verarbeiten ausgewählt.")
            return

        output_folder = QFileDialog.getExistingDirectory(self, "Zielordner für separate PDFs auswählen", os.getcwd())
        if not output_folder:
            self.processing_status_label.setText("Speichervorgang abgebrochen.")
            return

        self.processing_status_label.setText("Verarbeite Dateien zu separaten PDFs...")
        QApplication.processEvents()

        num_successful = 0
        num_errors = 0
        processed_file_paths = []
        first_error_detail = None # Added to capture first error detail

        for i, file_path in enumerate(files_to_process):
            current_file_basename = os.path.basename(file_path)
            self.processing_status_label.setText(f"Verarbeite Datei {i+1}/{len(files_to_process)}: {current_file_basename}")
            QApplication.processEvents()
            
            base, ext = os.path.splitext(current_file_basename)
            ext = ext.lower()
            output_pdf_name = f"{base}.pdf"
            final_output_pdf_path = os.path.join(output_folder, output_pdf_name)
            
            conversion_successful_flag = False

            try:
                if ext == ".pdf":
                    shutil.copy2(file_path, final_output_pdf_path)
                    self.processing_status_label.setText(f"PDF '{current_file_basename}' kopiert.")
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
                    self.processing_status_label.setText(f"Konvertiere {current_file_basename} zu PDF...")
                    QApplication.processEvents()
                    if self._convert_office_to_pdf_native(file_path, final_output_pdf_path):
                        if os.path.exists(final_output_pdf_path) and os.path.getsize(final_output_pdf_path) > 0:
                             self.processing_status_label.setText(f"{current_file_basename} erfolgreich als PDF gespeichert.")
                             conversion_successful_flag = True
                        else:
                            self.processing_status_label.setText(f"Konvertierte PDF für {current_file_basename} ist leer oder nicht vorhanden (separat).")
                    # If _convert_office_to_pdf_native returned False, status label is already set by it.
                else:
                    self.processing_status_label.setText(f"Dateityp {ext} von '{current_file_basename}' wird nicht unterstützt.")

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
                self.processing_status_label.setText(error_msg)
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
        
        reply = QMessageBox.information(self, "Verarbeitung abgeschlossen", 
                                        final_message + "\\n\\nMöchten Sie den Ausgabeordner öffnen?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                        QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes and os.path.exists(output_folder):
            try:
                # Use os.startfile on Windows, and 'open' on macOS, 'xdg-open' on Linux
                if platform.system() == "Windows":
                    os.startfile(output_folder)
                elif platform.system() == "Darwin": # macOS
                    subprocess.run(["open", output_folder])
                else: # Linux and other Unix-like
                    subprocess.run(["xdg-open", output_folder])
            except Exception as e:
                QMessageBox.warning(self, "Ordner öffnen Fehler", f"Der Ordner '{output_folder}' konnte nicht geöffnet werden.\\nFehler: {e}")

        self.processing_status_label.setText("Bereit.")

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
                self.processing_status_label.setText(f"SVG '{os.path.basename(file_path)}' zu PDF hinzugefügt.")
                return True # Indicate success
            else:
                self.processing_status_label.setText(f"Fehler beim Parsen von SVG '{os.path.basename(file_path)}'.")
        except Exception as e:
            self.processing_status_label.setText(f"Fehler beim Konvertieren von SVG '{os.path.basename(file_path)}': {e}")
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
                    self.processing_status_label.setText(f"COM Initialization failed for {input_basename}: {e2}")
                    # Proceed without COM, relying on LibreOffice or if converters don't need explicit init
        
        try:
            # 1. MS Word (.doc, .docx)
            if ext in MS_WORD_EXTENSIONS:
                if self.msword_available and convert_docx_to_pdf and win32com: # win32com check for safety
                    self.processing_status_label.setText(f"Versuche {input_basename} mit MS Word zu konvertieren...")
                    QApplication.processEvents()
                    try:
                        print(f"Attempting MS Word conversion: {input_path} -> {output_pdf_path}")
                        convert_docx_to_pdf(os.path.abspath(input_path), os.path.abspath(output_pdf_path))
                        if os.path.exists(output_pdf_path) and os.path.getsize(output_pdf_path) > 0:
                            self.processing_status_label.setText(f"{input_basename} erfolgreich mit MS Word konvertiert.")
                            print(f"MS Word conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS Word Konvertierung von {input_basename} fehlgeschlagen (Datei nicht erstellt oder leer)."
                            self.processing_status_label.setText(error_msg)
                            print(f"MS Word conversion failed: {error_msg}")
                    except Exception as e:
                        error_msg = f"MS Word Konvertierungsfehler für {input_basename}: {e}"
                        self.processing_status_label.setText(error_msg)
                        print(f"MS Word conversion error for {input_path}: {e}")
                    # Fall through to LibreOffice if MS Word conversion fails
                else:
                    print(f"MS Word not available for {input_basename}. MSWord available: {self.msword_available}, convert_docx_to_pdf: {convert_docx_to_pdf is not None}, win32com: {win32com is not None}")

            # 2. MS PowerPoint (.ppt, .pptx)
            elif ext in MS_POWERPOINT_EXTENSIONS:
                if self.mspowerpoint_available and pptxtopdf_convert_bulk and win32com:
                    self.processing_status_label.setText(f"Versuche {input_basename} mit MS PowerPoint zu konvertieren...")
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
                            self.processing_status_label.setText(f"{input_basename} erfolgreich mit MS PowerPoint konvertiert.")
                            print(f"MS PowerPoint conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS PowerPoint Konvertierung fehlgeschlagen für {input_basename} (Datei nicht erstellt oder leer)."
                            self.processing_status_label.setText(error_msg)
                            print(f"MS PowerPoint conversion failed: {error_msg}")
                    except Exception as e:
                        error_msg = f"MS PowerPoint Konvertierungsfehler für {input_basename}: {e}"
                        self.processing_status_label.setText(error_msg)
                        print(f"MS PowerPoint conversion error for {input_path}: {e}")
                    finally:
                        temp_dir_powerpoint.cleanup()
                    # Fall through to LibreOffice
                else:
                    print(f"MS PowerPoint not available for {input_basename}. MSPowerPoint available: {self.mspowerpoint_available}, pptxtopdf_convert_bulk: {pptxtopdf_convert_bulk is not None}, win32com: {win32com is not None}")

            # 3. MS Excel (.xls, .xlsx)
            elif ext in MS_EXCEL_EXTENSIONS:
                if self.msexcel_available and win32com:
                    self.processing_status_label.setText(f"Versuche {input_basename} mit MS Excel zu konvertieren...")
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
                            self.processing_status_label.setText(f"{input_basename} erfolgreich mit MS Excel konvertiert.")
                            print(f"MS Excel conversion successful for {input_basename}")
                            return True
                        else:
                            error_msg = f"MS Excel Konvertierung fehlgeschlagen für {input_basename} (Datei nicht erstellt oder leer)."
                            self.processing_status_label.setText(error_msg)
                            print(f"MS Excel conversion failed: {error_msg}") 
                    except Exception as e:
                        error_msg = f"MS Excel Konvertierungsfehler für {input_basename}: {e}"
                        self.processing_status_label.setText(error_msg)
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
                self.processing_status_label.setText(f"Versuche {input_basename} mit LibreOffice zu konvertieren...")
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
                        self.processing_status_label.setText(f"{input_basename} erfolgreich mit LibreOffice konvertiert.")
                        print(f"LibreOffice conversion successful for {input_basename}")
                        return True
                    else:
                        err_msg = process.stderr if process.stderr else "Unbekannter Fehler (Zieldatei nicht gefunden oder leer)."
                        error_detail = f"LibreOffice Konvertierung von {input_basename} fehlgeschlagen: {err_msg}"
                        self.processing_status_label.setText(error_detail)
                        print(f"LibreOffice conversion failed for {input_path}. stderr: {process.stderr}, stdout: {process.stdout}")
                        print(f"Files in temp directory: {os.listdir(temp_dir_libreoffice.name) if os.path.exists(temp_dir_libreoffice.name) else 'Directory not found'}")
                        
                except subprocess.CalledProcessError as e:
                    error_detail = f"LibreOffice Prozessfehler bei {input_basename}: {e.stderr if e.stderr else 'Unbekannter Fehler'}"
                    self.processing_status_label.setText(error_detail)
                    print(f"LibreOffice CalledProcessError for {input_path}: stderr: {e.stderr}, stdout: {e.stdout}, returncode: {e.returncode}")
                except subprocess.TimeoutExpired:
                    error_detail = f"LibreOffice Konvertierung von {input_basename} Zeitüberschreitung (>120s)."
                    self.processing_status_label.setText(error_detail)
                    print(f"LibreOffice TimeoutExpired for {input_path}")
                except Exception as e:
                    error_detail = f"Allgemeiner LibreOffice Fehler bei {input_basename}: {e}"
                    self.processing_status_label.setText(error_detail)
                    print(f"LibreOffice general error for {input_path}: {e}")
                finally:
                    temp_dir_libreoffice.cleanup()
            else: # No soffice_path
                if ext in MS_WORD_EXTENSIONS or ext in MS_EXCEL_EXTENSIONS or ext in MS_POWERPOINT_EXTENSIONS:
                    # This message is shown if MS Office conversion was not available or failed, and LibreOffice is also not found.
                    error_detail = f"Kein MS Office oder LibreOffice für {input_basename} gefunden. Installieren Sie LibreOffice oder MS Office."
                    self.processing_status_label.setText(error_detail)
                    print(f"No converters available for MS Office file: {input_basename}")
                elif ext in ODF_TEXT_EXTENSIONS or ext in ODF_SPREADSHEET_EXTENSIONS or ext in ODF_PRESENTATION_EXTENSIONS:
                    error_detail = f"LibreOffice nicht gefunden für ODF-Datei {input_basename}. Installieren Sie LibreOffice."
                    self.processing_status_label.setText(error_detail)
                    print(f"LibreOffice not found for ODF file: {input_basename}")
                # If it's not an office file type this function shouldn't have been called.
                # However, if it was, this is a generic message.
                else:
                    error_detail = f"Kein geeigneter Konverter für {input_basename} gefunden."
                    self.processing_status_label.setText(error_detail)
                    print(f"No suitable converter found for file: {input_basename}")

            # If we reach here, all conversion attempts failed
            final_error = f"Konvertierung von {input_basename} fehlgeschlagen. Überprüfen Sie die Installation von MS Office/LibreOffice."
            self.processing_status_label.setText(final_error)
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