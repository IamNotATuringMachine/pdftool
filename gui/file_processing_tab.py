import os
import io
import shutil # For copying PDFs in separate processing
import tempfile
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
    SVG_EXTENSIONS
)

class FileProcessingTab(QWidget): # Renamed class
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.selected_files_for_processing = [] # Renamed variable
        self.preview_size = QSize(64, 64)

        self._init_ui()
        if self.app_root:
            self.update_view_mode(self.app_root.current_view_mode)

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
                    return True # Event handled by filter

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
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie Dateien aus der Liste für die Verarbeitung aus.")
            return

        files_to_actually_process = [item.data(Qt.ItemDataRole.UserRole) for item in selected_qlist_items]

        # self._update_internal_file_list_from_widget() # Ensure order is correct - order is from selection now

        if self.single_pdf_output_check.isChecked():
            if len(files_to_actually_process) == 1 and files_to_actually_process[0].lower().endswith(".pdf"):
                 QMessageBox.information(self, "Einzelne PDF", "Nur eine einzelne PDF-Datei ausgewählt. Es gibt nichts zum Zusammenführen. Sie können die Datei ggf. über 'Speichern unter' kopieren, wenn Sie den Modus für separate Dateien wählen.")
                 return
            self._process_files_to_single_pdf(files_to_actually_process) # Pass selected files
        else:
            self._process_files_to_separate_pdfs(files_to_actually_process) # Pass selected files

    def _process_files_to_single_pdf(self, files_to_process): # Added files_to_process parameter
        output_filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Zusammengeführte PDF speichern unter", 
            "zusammengefuehrt.pdf", 
            "PDF-Dateien (*.pdf)"
        )
        if not output_filename:
            self.processing_status_label.setText("Speichern abgebrochen.")
            return

        merger = PdfWriter()
        skipped_files = []
        processed_count = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, file_path in enumerate(files_to_process): # Use passed files_to_process
                _, ext = os.path.splitext(file_path.lower())
                QApplication.processEvents()
                self.processing_status_label.setText(f"Verarbeite: {os.path.basename(file_path)}...")

                if ext == ".pdf":
                    try:
                        # Validate PDF and handle encryption
                        reader_check = PdfReader(file_path)
                        if reader_check.is_encrypted: # Basic check
                            try:
                                # Attempt to decrypt with an empty password, or just check pages
                                if reader_check.decrypt('') != 1 and len(reader_check.pages) == 0 : # PyPDF2 decrypt: 1=success, 2=owner_pass, 0=failure
                                     raise Exception("Failed to decrypt with empty password or no pages found.")
                            except Exception as e_decrypt:
                                print(f"Skipping encrypted/unreadable PDF {file_path}: {e_decrypt}")
                                QMessageBox.warning(self, "Verschlüsselte PDF", f"PDF {os.path.basename(file_path)} ist verschlüsselt oder unlesbar und wird übersprungen: {e_decrypt}")
                                skipped_files.append(os.path.basename(file_path))
                                continue
                        merger.append(file_path)
                        processed_count += 1
                    except Exception as e:
                        print(f"Error appending PDF {file_path}: {e}")
                        QMessageBox.warning(self, "PDF Fehler", f"PDF {os.path.basename(file_path)} konnte nicht direkt hinzugefügt werden und wird übersprungen: {e}")
                        skipped_files.append(os.path.basename(file_path))
                    continue # Next file

                # --- Existing conversion logic for non-PDFs, outputting to temp_pdf_path ---
                temp_pdf_path = os.path.join(temp_dir, f"temp_conversion_{i}.pdf")
                conversion_success = False
                try:
                    c = canvas.Canvas(temp_pdf_path, pagesize=A4)
                    if ext in IMAGE_EXTENSIONS:
                        self._add_image_to_pdf_canvas(file_path, c)
                        conversion_success = True
                    elif ext in TEXT_EXTENSIONS:
                        self._add_text_file_to_pdf_canvas(file_path, c)
                        conversion_success = True
                    elif ext in RTF_EXTENSIONS:
                        self._add_rtf_to_pdf_canvas(file_path, c)
                        conversion_success = True
                    elif ext in HTML_EXTENSIONS:
                        # xhtml2pdf writes directly to file, doesn't use our canvas easily for multi-page merge
                        # So, we convert HTML to a temp PDF, then merge that temp PDF.
                        self._convert_html_to_pdf_file(file_path, temp_pdf_path) # Modified to take output path
                        conversion_success = True # Assume success if no exception
                    elif ext in SVG_EXTENSIONS:
                        self._add_svg_to_pdf_canvas(file_path, c)
                        conversion_success = True
                    else: # Should not happen if filtered by ALL_SUPPORTED_EXT_PATTERNS_LIST
                        print(f"Skipping unsupported file type during single PDF merge: {file_path}")
                        skipped_files.append(os.path.basename(file_path))
                        continue
                    
                    if conversion_success and not (ext in HTML_EXTENSIONS): # HTML is saved separately
                         c.save()

                    if os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                        merger.append(temp_pdf_path)
                        processed_count += 1
                    elif conversion_success : # File existed but was empty, or html conversion failed silently before.
                         QMessageBox.warning(self, "Konvertierungsfehler", f"Erstellte PDF für {os.path.basename(file_path)} war leer oder fehlerhaft.")
                         skipped_files.append(os.path.basename(file_path))

                except UnidentifiedImageError:
                    QMessageBox.critical(self, "Fehler", f"Bilddatei {os.path.basename(file_path)} nicht erkannt oder beschädigt.")
                    skipped_files.append(os.path.basename(file_path))
                except Exception as e:
                    QMessageBox.critical(self, "Konvertierungsfehler", f"Fehler beim Konvertieren von {os.path.basename(file_path)}: {e}")
                    skipped_files.append(os.path.basename(file_path))
        
        if processed_count > 0 and len(merger.pages) > 0:
            try:
                with open(output_filename, "wb") as output_f:
                    merger.write(output_f)
                QMessageBox.information(self, "Erfolg", f"{processed_count} Datei(en) erfolgreich in {os.path.basename(output_filename)} zusammengeführt.")
                self.processing_status_label.setText(f"Erfolgreich gespeichert: {os.path.basename(output_filename)}")
            except Exception as e:
                QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der PDF: {e}")
                self.processing_status_label.setText("Fehler beim Speichern.")
        else:
            QMessageBox.warning(self, "Kein Ergebnis", "Keine Dateien konnten verarbeitet oder zusammengeführt werden.")
            self.processing_status_label.setText("Keine Dateien verarbeitet.")

        if skipped_files:
            QMessageBox.warning(self, "Einige Dateien übersprungen", f"Folgende Dateien wurden übersprungen: {', '.join(skipped_files)}")

    def _process_files_to_separate_pdfs(self, files_to_process): # Added files_to_process parameter
        if not files_to_process: # Check the passed list
            QMessageBox.warning(self, "Keine Dateien ausgewählt", "Keine Dateien für die separate Verarbeitung ausgewählt.") # More specific message
            return

        output_dir = QFileDialog.getExistingDirectory(self, "Zielordner für separate PDFs auswählen")
        if not output_dir:
            self.processing_status_label.setText("Speichern abgebrochen.")
            return

        processed_count = 0
        skipped_files = []
        
        for i, file_path in enumerate(files_to_process): # Use passed files_to_process
            _, ext = os.path.splitext(file_path.lower())
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            # Suggest unique output name in case of conflicts (e.g. file.jpg and file.txt)
            output_filename_suggestion = os.path.join(output_dir, f"{base_name}_{i}.pdf") 
            
            QApplication.processEvents()
            self.processing_status_label.setText(f"Verarbeite: {os.path.basename(file_path)}...")

            # If file is already PDF, copy it instead of re-processing
            if ext == ".pdf":
                # We still need a save dialog for *each* PDF to allow renaming or skipping
                # Or we decide on a naming convention and save automatically to output_dir
                # For simplicity, let's try to copy with a slightly modified name to avoid overwrite confirmation for each.
                # A better UX might be a dialog for each, or more complex overwrite handling.
                try:
                    # Check for encryption first
                    reader_check = PdfReader(file_path)
                    if reader_check.is_encrypted:
                        try:
                            if reader_check.decrypt('') != 1 and len(reader_check.pages) == 0:
                                raise Exception("Failed to decrypt or no pages.")
                        except Exception as e_decrypt:
                            QMessageBox.warning(self, "Verschlüsselte PDF", f"PDF {os.path.basename(file_path)} ist verschlüsselt/unlesbar, wird übersprungen: {e_decrypt}")
                            skipped_files.append(os.path.basename(file_path))
                            continue
                    
                    # Suggest a name, but let user confirm/change it for each PDF file
                    individual_output_filename, _ = QFileDialog.getSaveFileName(
                        self,
                        f"{os.path.basename(file_path)} speichern unter",
                        os.path.join(output_dir, f"{base_name}.pdf"), # Simpler suggestion
                        "PDF-Dateien (*.pdf)"
                    )
                    if not individual_output_filename:
                        skipped_files.append(f"{os.path.basename(file_path)} (Speichern abgebrochen)")
                        continue

                    shutil.copy2(file_path, individual_output_filename)
                    processed_count += 1
                    self.processing_status_label.setText(f"{os.path.basename(file_path)} kopiert nach {os.path.basename(individual_output_filename)}.")

                except Exception as e:
                    QMessageBox.critical(self, "Fehler beim Kopieren", f"PDF {os.path.basename(file_path)} konnte nicht kopiert werden: {e}")
                    skipped_files.append(os.path.basename(file_path))
                continue # Next file

            # --- Existing conversion logic for non-PDFs, saving each to its own output_filename ---
            # Suggest a name, but let user confirm/change it
            individual_output_filename, _ = QFileDialog.getSaveFileName(
                self,
                f"{os.path.basename(file_path)} als PDF speichern unter",
                os.path.join(output_dir, f"{base_name}.pdf"),
                "PDF-Dateien (*.pdf)"
            )
            if not individual_output_filename:
                skipped_files.append(f"{os.path.basename(file_path)} (Speichern abgebrochen)")
                continue

            try:
                c = canvas.Canvas(individual_output_filename, pagesize=A4)
                conversion_done = False
                if ext in IMAGE_EXTENSIONS:
                    self._add_image_to_pdf_canvas(file_path, c)
                    conversion_done = True
                elif ext in TEXT_EXTENSIONS:
                    self._add_text_file_to_pdf_canvas(file_path, c)
                    conversion_done = True
                elif ext in RTF_EXTENSIONS:
                    self._add_rtf_to_pdf_canvas(file_path, c)
                    conversion_done = True
                elif ext in HTML_EXTENSIONS:
                    self._convert_html_to_pdf_file(file_path, individual_output_filename)
                    conversion_done = True # Assumes success if no exception
                elif ext in SVG_EXTENSIONS:
                    self._add_svg_to_pdf_canvas(file_path, c)
                    conversion_done = True
                else: # Should not be reached if filtered
                    skipped_files.append(os.path.basename(file_path) + " (unbekannter Typ)")
                    continue
                
                if conversion_done and not (ext in HTML_EXTENSIONS): # HTML saved by its own function
                    c.save()
                
                if os.path.exists(individual_output_filename) and os.path.getsize(individual_output_filename) > 0:
                    processed_count += 1
                else: # Conversion might have failed silently or produced empty file
                    QMessageBox.warning(self, "Konvertierungsfehler", f"Erstellte PDF für {os.path.basename(file_path)} war leer oder fehlerhaft.")
                    skipped_files.append(os.path.basename(file_path))


            except UnidentifiedImageError:
                QMessageBox.critical(self, "Fehler", f"Bilddatei {os.path.basename(file_path)} nicht erkannt oder beschädigt.")
                skipped_files.append(os.path.basename(file_path))
            except Exception as e:
                QMessageBox.critical(self, "Fehler", f"Fehler beim Konvertieren von {os.path.basename(file_path)} zu PDF: {e}")
                skipped_files.append(os.path.basename(file_path))

        if processed_count > 0:
            QMessageBox.information(self, "Erfolg", f"{processed_count} Datei(en) erfolgreich als separate PDFs gespeichert im Ordner: {output_dir}")
            self.processing_status_label.setText(f"{processed_count} Dateien separat gespeichert.")
        else:
            QMessageBox.warning(self, "Kein Ergebnis", "Keine Dateien konnten verarbeitet werden.")
            self.processing_status_label.setText("Keine Dateien verarbeitet.")
        
        if skipped_files:
            QMessageBox.warning(self, "Einige Dateien übersprungen", f"Folgende Dateien wurden übersprungen oder nicht gespeichert: {', '.join(skipped_files)}")

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
        except UnidentifiedImageError:
            raise # Re-raise to be caught by caller
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
        except Exception as e:
            raise Exception(f"Fehler beim Lesen/Rendern der Textdatei {os.path.basename(file_path)}: {e}")

    def _add_rtf_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f: # RTF might have weird encodings sometimes
                rtf_content = f.read()
            text_content = rtf_to_text(rtf_content)
            self._render_text_to_pdf_canvas(text_content, pdf_canvas, source_filename=os.path.basename(file_path))
        except Exception as e:
            raise Exception(f"Fehler beim Verarbeiten der RTF-Datei {os.path.basename(file_path)}: {e}")

    def _add_svg_to_pdf_canvas(self, file_path, pdf_canvas):
        # svglib's svg2rlg converts SVG to a ReportLab Drawing object
        try:
            drawing = svg2rlg(file_path)
            if drawing:
                # Scale drawing to fit A4 if too large, maintaining aspect ratio
                a4_width, a4_height = A4
                
                # ReportLab drawing objects might not have a straightforward width/height like images
                # We might need to render it and see, or use its properties if available
                # For simplicity, let's assume it tries to render at its native size first
                # and rely on ReportLab's canvas clipping or try a scale if we can get bounds.
                # This part can be complex depending on SVG content and svglib behavior.
                
                # A simple approach: render at 0,0 and let it take space.
                # For better control, one would inspect drawing.width, drawing.height
                # and apply scaling similar to images.
                # drawing.scale(scale_factor, scale_factor)
                # drawing.translate(x_offset, y_offset)
                
                # Example: attempt to scale if drawing object has width/height attributes
                render_width = drawing.width if hasattr(drawing, 'width') else a4_width
                render_height = drawing.height if hasattr(drawing, 'height') else a4_height

                if render_width == 0 or render_height == 0 : # Cant get size, dont scale
                     scale_x, scale_y = 1.0, 1.0
                else:
                    scale_x = a4_width / render_width
                    scale_y = a4_height / render_height
                
                scale_factor = min(scale_x, scale_y, 1.0) # Don't upscale beyond 1.0 unless small

                original_drawing_width = drawing.width if hasattr(drawing, 'width') else 0
                original_drawing_height = drawing.height if hasattr(drawing, 'height') else 0
                
                scaled_width = original_drawing_width * scale_factor
                scaled_height = original_drawing_height * scale_factor
                
                x_offset = (a4_width - scaled_width) / 2
                y_offset = (a4_height - scaled_height) - inch # Position towards bottom for typical full page
                if y_offset < inch : y_offset = inch


                # Apply transformations for scaling and positioning
                # ReportLab's renderPDF.draw can take a drawing and a canvas.
                # It's often better to add the drawing to a Flowable list for complex docs,
                # but for single page on canvas:
                from reportlab.graphics import renderPDF
                
                # Need to handle the drawing object carefully.
                # Create a temporary canvas frame for the drawing might be safer.
                # For now, let's assume drawing.drawOn(pdf_canvas, x, y) works after scaling
                
                # Store original transform
                original_transform = drawing.transform
                
                drawing.scale(scale_factor, scale_factor)
                # Center the drawing on the page
                # The drawing's own (0,0) will be placed at x_offset, y_offset on the canvas.
                drawing.translate(x_offset / scale_factor, y_offset / scale_factor) # Adjust translation by scale factor

                renderPDF.draw(drawing, pdf_canvas, 0, 0) # Draw at canvas origin after transform

                # Restore original transform if needed elsewhere, though drawing is usually local here
                drawing.transform = original_transform

            else:
                raise Exception("SVG konnte nicht geladen werden.")
        except Exception as e:
            raise Exception(f"Fehler beim Verarbeiten der SVG-Datei {os.path.basename(file_path)}: {e}")

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