import os
import io
import tempfile
from PyPDF2 import PdfWriter, PdfReader # PdfReader for merging existing PDFs
from PIL import Image, UnidentifiedImageError, ImageSequence
from xhtml2pdf import pisa
from svglib.svglib import svg2rlg
from striprtf.striprtf import rtf_to_text

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader as ReportLabImageReader # Alias to avoid conflict

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QListWidget, QListWidgetItem, QRadioButton,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QCheckBox,
    QApplication, QScrollArea, QFrame, QFileIconProvider # Added QFileIconProvider
)
from PySide6.QtCore import Qt, QUrl, QSize, QFileInfo
from PySide6.QtGui import QIcon, QPixmap, QPainter # For icons

from utils.common_helpers import parse_dropped_files # May need adjustment for Qt mime data
from utils.constants import (
    FILETYPES_FOR_DIALOG,
    ALL_SUPPORTED_EXT_PATTERNS_LIST,
    IMAGE_EXTENSIONS,
    TEXT_EXTENSIONS,
    RTF_EXTENSIONS,
    HTML_EXTENSIONS,
    SVG_EXTENSIONS
)

# It's good practice to ensure pillow_heif is registered if you handle HEIC directly.
# Assuming it's done in main pdf_tool.py is fine.
# from pillow_heif import register_heif_opener
# register_heif_opener()

class ConvertTab(QWidget):
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.selected_files_for_conversion = [] # Stores full paths
        self.icon_size = QSize(80, 100) # Size for icons in icon view
        self.preview_size = QSize(64, 64) # Size for generating pixmap previews

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- View Toggle ---
        view_toggle_frame = QFrame() # Using QFrame for simple grouping
        view_toggle_layout = QHBoxLayout(view_toggle_frame)
        view_toggle_layout.setContentsMargins(0,0,0,0)
        view_toggle_layout.addWidget(QLabel("Ansicht:"))
        self.list_view_radio = QRadioButton("Liste")
        self.list_view_radio.setChecked(True)
        self.list_view_radio.toggled.connect(self._toggle_view_mode)
        view_toggle_layout.addWidget(self.list_view_radio)
        self.icon_view_radio = QRadioButton("Symbole")
        self.icon_view_radio.toggled.connect(self._toggle_view_mode)
        view_toggle_layout.addWidget(self.icon_view_radio)
        view_toggle_layout.addStretch()
        main_layout.addWidget(view_toggle_frame)

        # --- Controls Group (List/Icon View and Buttons) ---
        controls_group = QGroupBox("Dateien für Konvertierung")
        controls_group_layout = QHBoxLayout(controls_group)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Enable both internal move (for reordering) and external drops (for adding files)
        self.file_list_widget.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.file_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        
        self.file_list_widget.setAcceptDrops(True)
        
        # Connect to model changes to keep internal list synchronized
        self.file_list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        # Override drag and drop events for external file drops
        self.file_list_widget.dragEnterEvent = self._drag_enter_event
        self.file_list_widget.dragMoveEvent = self._drag_move_event
        self.file_list_widget.dropEvent = self._drop_event
        
        self.file_list_widget.setViewMode(QListWidget.ViewMode.ListMode)
        self.file_list_widget.setIconSize(self.icon_size) # Set icon size for icon mode
        self.file_list_widget.setWordWrap(True)
        self.file_list_widget.itemSelectionChanged.connect(self._on_list_selection_changed)

        controls_group_layout.addWidget(self.file_list_widget, 1)

        # Buttons
        buttons_layout = QVBoxLayout()
        self.add_button = QPushButton("Dateien hinzufügen")
        self.add_button.clicked.connect(self._add_files_to_convert_list)
        buttons_layout.addWidget(self.add_button)
        self.remove_button = QPushButton("Auswahl entfernen")
        self.remove_button.clicked.connect(self._remove_file_from_convert_list)
        buttons_layout.addWidget(self.remove_button)
        self.move_up_button = QPushButton("Nach oben")
        self.move_up_button.clicked.connect(self._move_convert_item_up)
        buttons_layout.addWidget(self.move_up_button)
        self.move_down_button = QPushButton("Nach unten")
        self.move_down_button.clicked.connect(self._move_convert_item_down)
        buttons_layout.addWidget(self.move_down_button)
        buttons_layout.addStretch()
        controls_group_layout.addLayout(buttons_layout)
        main_layout.addWidget(controls_group)

        # --- Options ---
        options_frame = QFrame()
        options_layout = QHBoxLayout(options_frame)
        options_layout.setContentsMargins(0,0,0,0)
        self.single_pdf_output_check = QCheckBox("Alle Dateien in eine einzelne PDF-Datei zusammenfassen")
        self.single_pdf_output_check.setChecked(True)
        options_layout.addWidget(self.single_pdf_output_check)
        options_layout.addStretch()
        main_layout.addWidget(options_frame)

        # --- Action Area ---
        action_layout = QVBoxLayout()
        self.convert_button = QPushButton("Ausgewählte Dateien zu PDF konvertieren und speichern")
        self.convert_button.clicked.connect(self._execute_file_to_pdf)
        action_layout.addWidget(self.convert_button)
        self.file_conversion_status_label = QLabel("")
        self.file_conversion_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.file_conversion_status_label)
        main_layout.addLayout(action_layout)

        self.setLayout(main_layout)
        self._toggle_view_mode() # Initial setup

    def _toggle_view_mode(self):
        if self.list_view_radio.isChecked():
            self.file_list_widget.setViewMode(QListWidget.ViewMode.ListMode)
        else:
            self.file_list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            self.file_list_widget.setFlow(QListWidget.Flow.LeftToRight) # Typical for icon views
            self.file_list_widget.setWrapping(True)
            self.file_list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._refresh_list_widget_items() # Refresh items as view mode might affect display

    def _on_list_selection_changed(self):
        # This might be useful if we need to act on selection for other UI elements
        # For now, QListWidget handles selection visually.
        pass 

    def _on_rows_moved(self, parent, start, end, destination, row):
        """Called when rows are moved via drag and drop. Updates internal file list."""
        self._update_internal_file_list_from_widget()
        self.file_conversion_status_label.setText("Dateien neu sortiert.")

    def _update_internal_file_list_from_widget(self):
        """Synchronizes self.selected_files_for_conversion based on QListWidget items order and data."""
        self.selected_files_for_conversion.clear()
        for i in range(self.file_list_widget.count()):
            item = self.file_list_widget.item(i)
            self.selected_files_for_conversion.append(item.data(Qt.ItemDataRole.UserRole))

    def _refresh_list_widget_items(self):
        current_selection_path = None
        selected_items = self.file_list_widget.selectedItems()
        if selected_items:
            current_selection_path = selected_items[0].data(Qt.ItemDataRole.UserRole)

        self.file_list_widget.clear()
        for file_path in self.selected_files_for_conversion:
            item = QListWidgetItem(os.path.basename(file_path))
            item.setData(Qt.ItemDataRole.UserRole, file_path) # Store full path
            item.setIcon(self._get_q_icon_for_file(file_path)) # Set QIcon
            self.file_list_widget.addItem(item)
            if file_path == current_selection_path:
                item.setSelected(True)
    
    def _get_q_icon_for_file(self, file_path):
        # Basic file type icon provider
        provider = QFileIconProvider()
        # Use QFileInfo for getting the icon in PySide6
        file_info = QFileInfo(file_path)
        q_icon = provider.icon(file_info) # Use QFileInfo instead of string path
        if not q_icon or q_icon.isNull():
            # Fallback to generating a generic pixmap based on extension if native fails or is generic
            _, ext = os.path.splitext(file_path.lower())
            pixmap = QPixmap(self.preview_size)
            pixmap.fill(Qt.GlobalColor.lightGray)
            painter = QPainter(pixmap)
            text = ext.replace(".","").upper() if ext else "FILE"
            painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
            painter.end()
            q_icon = QIcon(pixmap)
        return q_icon

    def _add_files_to_list(self, file_paths):
        added_count = 0
        for file_path in file_paths:
            # Check if full path already exists to prevent duplicates
            if not any(file_path == existing_fp for existing_fp in self.selected_files_for_conversion):
                _, ext = os.path.splitext(file_path.lower())
                if ext in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                    self.selected_files_for_conversion.append(file_path)
                    added_count += 1
                else:
                    print(f"Skipping unsupported file: {file_path}") # Or show a message box
        
        if added_count > 0:
            self._refresh_list_widget_items()
            self.file_conversion_status_label.setText(f"{added_count} Datei(en) zur Konvertierungsliste hinzugefügt.")
        else:
            self.file_conversion_status_label.setText("Keine neuen unterstützten Dateien hinzugefügt.")

    def _add_files_to_convert_list(self):
        # FILETYPES_FOR_DIALOG should be a string like "Images (*.png *.jpg);;Text files (*.txt)"
        dialog_filter = " ;; ".join([f"{ftype_desc} ({' '.join(['*'+ext for ext in exts])})" for ftype_desc, exts in FILETYPES_FOR_DIALOG.items()])
        dialog_filter += " ;; Alle unterstützten Dateien ({}) ;; Alle Dateien (*.*)".format(' '.join([f"*{ext}" for ext in ALL_SUPPORTED_EXT_PATTERNS_LIST]))
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Dateien für Konvertierung auswählen",
            "",
            dialog_filter
        )
        if files:
            self._add_files_to_list(files)

    def _remove_file_from_convert_list(self):
        selected_items = self.file_list_widget.selectedItems()
        if selected_items:
            item_to_remove = selected_items[0]
            file_path_to_remove = item_to_remove.data(Qt.ItemDataRole.UserRole)
            self.selected_files_for_conversion.remove(file_path_to_remove)
            self._refresh_list_widget_items()
            self.file_conversion_status_label.setText("Datei entfernt.")
        else:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.")

    def _move_item(self, direction):
        selected_items = self.file_list_widget.selectedItems()
        if not selected_items: return
        current_item = selected_items[0]
        current_path = current_item.data(Qt.ItemDataRole.UserRole)
        current_idx = self.selected_files_for_conversion.index(current_path)

        new_idx = current_idx + direction
        if 0 <= new_idx < len(self.selected_files_for_conversion):
            self.selected_files_for_conversion.pop(current_idx)
            self.selected_files_for_conversion.insert(new_idx, current_path)
            self._refresh_list_widget_items()
            # Re-select the moved item
            for i in range(self.file_list_widget.count()):
                if self.file_list_widget.item(i).data(Qt.ItemDataRole.UserRole) == current_path:
                    self.file_list_widget.item(i).setSelected(True)
                    self.file_list_widget.scrollToItem(self.file_list_widget.item(i))
                    break
            self.file_conversion_status_label.setText("Datei verschoben.")

    def _move_convert_item_up(self):
        self._move_item(-1)

    def _move_convert_item_down(self):
        self._move_item(1)

    # --- Drag and Drop --- 
    def _drag_enter_event(self, event):
        # Check if the dropped data contains URLs (file paths) - for external drops
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        # Also allow internal moves
        elif event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _drag_move_event(self, event):
        # This event is similar to dragEnterEvent; often, the same logic applies
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def _drop_event(self, event):
        # Handle external file drops
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            urls = event.mimeData().urls()
            dropped_files = []
            for url in urls:
                if url.isLocalFile():
                    dropped_files.append(url.toLocalFile())
            
            if dropped_files:
                self._add_files_to_list(dropped_files)
            else:
                self.file_conversion_status_label.setText("Keine lokalen Dateien im Drop-Event gefunden.")
        
        # Handle internal moves (let the default implementation handle it)
        elif event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            # Call the parent's dropEvent to handle internal moves
            QListWidget.dropEvent(self.file_list_widget, event)
        else:
            event.ignore()

    # --- PDF Conversion Logic ---
    def _execute_file_to_pdf(self):
        if not self.selected_files_for_conversion:
            QMessageBox.warning(self, "Keine Dateien", "Bitte wählen Sie Dateien für die Konvertierung aus.")
            return

        if self.single_pdf_output_check.isChecked():
            self._convert_to_single_pdf()
        else:
            self._convert_to_separate_pdfs()

    def _convert_to_single_pdf(self):
        output_filename, _ = QFileDialog.getSaveFileName(
            self, "Zusammengeführte PDF speichern unter", "", "PDF-Dateien (*.pdf)"
        )
        if not output_filename: return

        merged_pdf_writer = PdfWriter()
        temp_pdf_files = []
        conversion_successful = True

        self.file_conversion_status_label.setText("Konvertiere und führe zusammen...")
        QApplication.processEvents()

        for i, file_path in enumerate(self.selected_files_for_conversion):
            self.file_conversion_status_label.setText(f"Verarbeite Datei {i+1}/{len(self.selected_files_for_conversion)}: {os.path.basename(file_path)}")
            QApplication.processEvents()
            _, ext = os.path.splitext(file_path.lower())
            temp_pdf_path = None

            try:
                if ext == ".pdf":
                    # For existing PDFs, just add them directly (no temp file needed for merging)
                    pdf_reader = PdfReader(file_path)
                    for page in pdf_reader.pages:
                        merged_pdf_writer.add_page(page)
                    continue # Skip temp file creation/cleanup for this one
                
                # For other types, convert to a temporary PDF
                fd, temp_pdf_path = tempfile.mkstemp(suffix=".pdf")
                os.close(fd)
                temp_pdf_files.append(temp_pdf_path)

                c = canvas.Canvas(temp_pdf_path, pagesize=A4)
                if ext in IMAGE_EXTENSIONS:
                    self._add_image_to_pdf_canvas(file_path, c)
                elif ext in TEXT_EXTENSIONS:
                    self._add_text_file_to_pdf_canvas(file_path, c)
                elif ext in RTF_EXTENSIONS:
                    self._add_rtf_to_pdf_canvas(file_path, c)
                elif ext in HTML_EXTENSIONS:
                    c.save() # Close canvas before xhtml2pdf writes to the same file
                    self._convert_html_to_existing_pdf(file_path, temp_pdf_path) # Use helper to write to existing path
                elif ext in SVG_EXTENSIONS:
                    self._add_svg_to_pdf_canvas(file_path, c)
                else:
                    # Should not happen if list is filtered by supported types
                    print(f"Unsupported file type for temp conversion: {file_path}")
                    conversion_successful = False
                    break # Exit the for loop immediately
                
                if not (ext in HTML_EXTENSIONS): # HTML conversion saves its own canvas
                    c.save()

                # Add the pages from the temporary PDF to the merger
                temp_reader = PdfReader(temp_pdf_path)
                for page in temp_reader.pages:
                    merged_pdf_writer.add_page(page)
            
            except Exception as e:
                QMessageBox.critical(self, "Konvertierungsfehler", "Fehler beim Verarbeiten einer Datei.") # Simplified message
                conversion_successful = False
                break # Exit the for loop immediately
            finally:
                # Canvas saving is done above. Here we only handle cleanup if an error didn't occur for HTML.
                pass
        
        if conversion_successful and len(merged_pdf_writer.pages) > 0:
            try:
                with open(output_filename, 'wb') as f_out:
                    merged_pdf_writer.write(f_out)
                QMessageBox.information(self, "Erfolg", f"Dateien erfolgreich in {os.path.basename(output_filename)} zusammengeführt.")
                self.file_conversion_status_label.setText("Konvertierung erfolgreich!")
            except Exception as e:
                 QMessageBox.critical(self, "Speicherfehler", f"Fehler beim Speichern der PDF: {e}")
                 self.file_conversion_status_label.setText("Fehler beim Speichern.")
        elif conversion_successful and len(merged_pdf_writer.pages) == 0:
            QMessageBox.warning(self, "Leere PDF", "Keine Inhalte konnten konvertiert werden. Die resultierende PDF wäre leer.")
            self.file_conversion_status_label.setText("Keine Inhalte konvertiert.")
        else: # conversion_successful is False
             self.file_conversion_status_label.setText("Konvertierung fehlgeschlagen.")

        # Cleanup temporary PDF files
        for temp_file in temp_pdf_files:
            try: os.remove(temp_file) 
            except OSError: pass

    def _convert_to_separate_pdfs(self):
        output_dir = QFileDialog.getExistingDirectory(self, "Ausgabeverzeichnis auswählen")
        if not output_dir: return

        converted_count = 0
        errors = []

        self.file_conversion_status_label.setText("Konvertiere Dateien...")
        QApplication.processEvents()

        for i, file_path in enumerate(self.selected_files_for_conversion):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
            _, ext = os.path.splitext(file_path.lower())

            self.file_conversion_status_label.setText(f"Konvertiere {i+1}/{len(self.selected_files_for_conversion)}: {os.path.basename(file_path)}")
            QApplication.processEvents()
            
            try:
                if ext == ".pdf": # Just copy if it's already a PDF
                    import shutil
                    shutil.copy2(file_path, output_pdf_path)
                else:
                    c = canvas.Canvas(output_pdf_path, pagesize=A4)
                    if ext in IMAGE_EXTENSIONS:
                        self._add_image_to_pdf_canvas(file_path, c)
                    elif ext in TEXT_EXTENSIONS:
                        self._add_text_file_to_pdf_canvas(file_path, c)
                    elif ext in RTF_EXTENSIONS:
                        self._add_rtf_to_pdf_canvas(file_path, c)
                    elif ext in HTML_EXTENSIONS:
                        c.save() # Save canvas to close it before xhtml2pdf writes to output_pdf_path
                        self._convert_html_to_existing_pdf(file_path, output_pdf_path)
                    elif ext in SVG_EXTENSIONS:
                        self._add_svg_to_pdf_canvas(file_path, c)
                    else:
                        errors.append(f"Nicht unterstützter Dateityp: {os.path.basename(file_path)}")
                        continue # Skip to next file
                    
                    if not (ext in HTML_EXTENSIONS):
                         c.save()
                converted_count += 1
            except Exception as e:
                errors.append(f"Fehler bei {os.path.basename(file_path)}: {e}")

        if errors:
            QMessageBox.warning(self, "Konvertierungsfehler", f"Einige Dateien konnten nicht konvertiert werden:\n\n" + "\n".join(errors))
        if converted_count > 0:
            QMessageBox.information(self, "Erfolg", f"{converted_count} Datei(en) erfolgreich nach PDF konvertiert im Verzeichnis: {output_dir}")
            self.file_conversion_status_label.setText(f"{converted_count} Datei(en) konvertiert.")
        elif not errors: # No errors but nothing converted (e.g. empty selection after filtering)
             QMessageBox.information(self, "Nichts zu tun", "Keine Dateien wurden konvertiert.")
             self.file_conversion_status_label.setText("Keine Dateien konvertiert.")

    # --- Helper methods for adding content to PDF canvas or file ---
    def _add_image_to_pdf_canvas(self, image_path, pdf_canvas):
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size

            # Convert non-RGB/RGBA images (like P mode with palette, or LA)
            if img.mode not in ('RGB', 'RGBA', 'L'):
                if 'A' in img.mode or 'P' in img.mode : # Check for alpha or palette
                     img = img.convert('RGBA')
                else:
                     img = img.convert('RGB')

            # Handle multi-frame GIFs (convert first frame)
            if hasattr(img, 'n_frames') and img.n_frames > 1:
                 img.seek(0) # Ensure we are on the first frame
                 if img.mode not in ('RGB', 'RGBA', 'L'): # Re-check mode after seek
                     img = img.convert('RGBA') if 'A' in img.mode or 'P' in img.mode else img.convert('RGB')

            page_width, page_height = A4
            max_width = page_width - 2 * inch
            max_height = page_height - 2 * inch

            scale_w = max_width / img_width
            scale_h = max_height / img_height
            scale = min(scale_w, scale_h)

            draw_width = img_width * scale
            draw_height = img_height * scale
            x_pos = (page_width - draw_width) / 2
            y_pos = (page_height - draw_height) / 2

            # Use ReportLabImageReader for Pillow images
            pdf_canvas.drawImage(ReportLabImageReader(img), x_pos, y_pos, width=draw_width, height=draw_height, preserveAspectRatio=True)
            pdf_canvas.showPage()
        except UnidentifiedImageError:
            raise ValueError(f"Kann Bildformat nicht identifizieren: {os.path.basename(image_path)}")
        except Exception as e:
            raise ValueError(f"Fehler beim Verarbeiten des Bildes {os.path.basename(image_path)}: {e}")

    def _render_text_to_pdf_canvas(self, text_content, pdf_canvas, source_filename="Text"):
        # Simple text rendering. For advanced, use Paragraph from reportlab.platypus
        text_object = pdf_canvas.beginText()
        text_object.setFont("Helvetica", 10) # Basic font
        text_object.setTextOrigin(inch, A4[1] - inch) # Top-leftish
        text_object.setLeading(14) # Line spacing

        page_width, page_height = A4
        margin = inch
        max_width = page_width - 2 * margin
        current_y = page_height - margin

        lines = text_content.splitlines()
        for line in lines:
            # Basic line wrapping (can be improved)
            while pdf_canvas.stringWidth(line, "Helvetica", 10) > max_width:
                # Find a good place to break the line
                split_at = -1
                for i in range(len(line) -1, 0, -1):
                    if line[i].isspace():
                        if pdf_canvas.stringWidth(line[:i], "Helvetica", 10) <= max_width:
                            split_at = i
                            break
                if split_at == -1: # Cannot break on space, force break
                    # Estimate based on average char width (very rough)
                    avg_char_width = max_width / (len(line) * 0.6 if len(line) > 0 else 1)
                    split_at = int(max_width / (pdf_canvas.stringWidth(" ", "Helvetica", 10) + 0.001) if avg_char_width > 0 else len(line))
                    split_at = min(split_at, len(line) -1)
                    if split_at <=0: split_at = len(line) # prevent infinite loop if line is too long with no spaces

                text_object.textLine(line[:split_at])
                line = line[split_at:].lstrip()
                current_y -= 14 # leading
                if current_y < margin:
                    pdf_canvas.drawText(text_object)
                    pdf_canvas.showPage()
                    text_object = pdf_canvas.beginText()
                    text_object.setFont("Helvetica", 10)
                    text_object.setTextOrigin(inch, A4[1] - inch)
                    text_object.setLeading(14)
                    current_y = page_height - margin
            
            text_object.textLine(line)
            current_y -= 14
            if current_y < margin and line != lines[-1]: #Don't make new page for last line if it fits
                pdf_canvas.drawText(text_object)
                pdf_canvas.showPage()
                text_object = pdf_canvas.beginText()
                text_object.setFont("Helvetica", 10)
                text_object.setTextOrigin(inch, A4[1] - inch)
                text_object.setLeading(14)
                current_y = page_height - margin

        pdf_canvas.drawText(text_object)
        pdf_canvas.showPage()

    def _add_text_file_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self._render_text_to_pdf_canvas(content, pdf_canvas, os.path.basename(file_path))
        except Exception as e:
            raise ValueError(f"Fehler beim Lesen der Textdatei {os.path.basename(file_path)}: {e}")

    def _add_rtf_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            with open(file_path, 'r') as f:
                rtf_content = f.read()
            text_content = rtf_to_text(rtf_content)
            self._render_text_to_pdf_canvas(text_content, pdf_canvas, os.path.basename(file_path))
        except Exception as e:
            raise ValueError(f"Fehler beim Verarbeiten der RTF-Datei {os.path.basename(file_path)}: {e}")

    def _convert_html_to_existing_pdf(self, html_file_path, output_pdf_path):
        # Helper for xhtml2pdf to write to an existing (possibly temporary) PDF file path
        try:
            with open(html_file_path, "r", encoding='utf-8') as html_file:
                html_content = html_file.read()
            with open(output_pdf_path, "wb") as pdf_file:
                pisa_status = pisa.CreatePDF(html_content, dest=pdf_file, encoding='utf-8')
            if pisa_status.err:
                raise ValueError(f"xhtml2pdf Fehler: {pisa_status.err}")
        except Exception as e:
            raise ValueError(f"Fehler beim Konvertieren von HTML {os.path.basename(html_file_path)}: {e}")

    def _add_svg_to_pdf_canvas(self, file_path, pdf_canvas):
        try:
            drawing = svg2rlg(file_path)
            if not drawing:
                raise ValueError("SVG konnte nicht geladen oder geparst werden.")

            page_width, page_height = A4
            drawing_width, drawing_height = drawing.width, drawing.height
            
            if drawing_width <= 0 or drawing_height <= 0:
                 raise ValueError("SVG hat ungültige Dimensionen.")

            margin = inch
            max_render_width = page_width - 2 * margin
            max_render_height = page_height - 2 * margin

            scale_w = max_render_width / drawing_width
            scale_h = max_render_height / drawing_height
            scale = min(scale_w, scale_h)
            if scale <= 0: scale = 1 # Prevent negative or zero scaling

            render_width = drawing_width * scale
            render_height = drawing_height * scale

            drawing.width, drawing.height = render_width, render_height
            drawing.scale(scale, scale)
            
            x_pos = (page_width - render_width) / 2
            y_pos = page_height - render_height - margin # Align top-ish
            
            from reportlab.graphics import renderPDF
            renderPDF.draw(drawing, pdf_canvas, x_pos, y_pos)
            pdf_canvas.showPage()
        except Exception as e:
            raise ValueError(f"Fehler beim Verarbeiten der SVG-Datei {os.path.basename(file_path)}: {e}") 