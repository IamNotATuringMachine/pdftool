import os
from PyPDF2 import PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox,
    QApplication
)
from PySide6.QtCore import Qt, QUrl
# We might need to adjust parse_dropped_files or handle MIME data directly
# from utils.common_helpers import parse_dropped_files 

class MergeTab(QWidget):
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root # Main window reference, if needed
        self.selected_merge_files = [] # List to store full paths

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Controls Group ---
        controls_group = QGroupBox("Dateien zum Zusammenführen")
        controls_group_layout = QHBoxLayout(controls_group) # Main layout for the group

        # Listbox for files
        self.merge_list_widget = QListWidget()
        # Enable both internal move (for reordering) and external drops (for adding files)
        self.merge_list_widget.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.merge_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.merge_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        # Enable accepting drops from external sources
        self.merge_list_widget.setAcceptDrops(True)
        
        # Connect to model changes to keep internal list synchronized
        self.merge_list_widget.model().rowsMoved.connect(self._on_rows_moved)
        
        # Override drag and drop events for external file drops
        self.merge_list_widget.dragEnterEvent = self._drag_enter_event
        self.merge_list_widget.dragMoveEvent = self._drag_move_event
        self.merge_list_widget.dropEvent = self._drop_event
        
        controls_group_layout.addWidget(self.merge_list_widget, 1) # Add stretch factor

        # Buttons for list management
        list_buttons_layout = QVBoxLayout()
        self.add_button = QPushButton("PDF hinzufügen")
        self.add_button.clicked.connect(self._add_pdf_to_merge_list)
        list_buttons_layout.addWidget(self.add_button)

        self.remove_button = QPushButton("Auswahl entfernen")
        self.remove_button.clicked.connect(self._remove_pdf_from_merge_list)
        list_buttons_layout.addWidget(self.remove_button)

        self.move_up_button = QPushButton("Nach oben")
        self.move_up_button.clicked.connect(self._move_merge_item_up)
        list_buttons_layout.addWidget(self.move_up_button)

        self.move_down_button = QPushButton("Nach unten")
        self.move_down_button.clicked.connect(self._move_merge_item_down)
        list_buttons_layout.addWidget(self.move_down_button)
        list_buttons_layout.addStretch()

        controls_group_layout.addLayout(list_buttons_layout)
        main_layout.addWidget(controls_group)

        # --- Action Area ---
        action_layout = QVBoxLayout()
        self.merge_button = QPushButton("PDFs zusammenführen und speichern")
        self.merge_button.clicked.connect(self._execute_merge_pdfs)
        action_layout.addWidget(self.merge_button)

        self.merge_status_label = QLabel("")
        self.merge_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.merge_status_label)
        
        main_layout.addLayout(action_layout)
        main_layout.addStretch() # Pushes everything to the top if vertical space is available

        self.setLayout(main_layout)

    def _on_rows_moved(self, parent, start, end, destination, row):
        """Called when rows are moved via drag and drop. Updates internal file list."""
        self._update_internal_file_list_from_widget()
        self.merge_status_label.setText("Dateien neu sortiert.")

    def _update_internal_file_list_from_widget(self):
        """Synchronizes self.selected_merge_files based on QListWidget items order and data."""
        self.selected_merge_files.clear()
        for i in range(self.merge_list_widget.count()):
            item = self.merge_list_widget.item(i)
            self.selected_merge_files.append(item.data(Qt.ItemDataRole.UserRole)) # Store full path in UserRole

    def _add_files_to_list_widget(self, file_paths):
        added_count = 0
        for file_path in file_paths:
            if file_path.lower().endswith(".pdf"):
                # Check if the full path is already in our internal list
                if not any(file_path == existing_fp for existing_fp in self.selected_merge_files):
                    item = QListWidgetItem(os.path.basename(file_path))
                    item.setData(Qt.ItemDataRole.UserRole, file_path) # Store full path
                    self.merge_list_widget.addItem(item)
                    self.selected_merge_files.append(file_path) # Keep internal list in sync
                    added_count += 1
        if added_count > 0:
            self.merge_status_label.setText(f"{added_count} PDF-Datei(en) hinzugefügt.")
        else:
            self.merge_status_label.setText("Keine neuen PDF-Dateien hinzugefügt oder bereits vorhanden.")

    def _add_pdf_to_merge_list(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "PDF-Dateien auswählen",
            "",
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )
        if files:
            self._add_files_to_list_widget(files)

    def _remove_pdf_from_merge_list(self):
        current_item = self.merge_list_widget.currentItem()
        if current_item:
            row = self.merge_list_widget.row(current_item)
            self.merge_list_widget.takeItem(row)
            self._update_internal_file_list_from_widget() # Resync internal list
            self.merge_status_label.setText("Datei entfernt.")
        else:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.")

    def _move_merge_item_up(self):
        current_item = self.merge_list_widget.currentItem()
        if current_item:
            row = self.merge_list_widget.row(current_item)
            if row > 0:
                # QListWidget's internal drag and drop handles visual reordering if enabled.
                # For manual control or if InternalMove is not sufficient for all cases:
                item = self.merge_list_widget.takeItem(row)
                self.merge_list_widget.insertItem(row - 1, item)
                self.merge_list_widget.setCurrentItem(item)
                self._update_internal_file_list_from_widget() # Resync
                self.merge_status_label.setText("Datei nach oben verschoben.")
        else:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _move_merge_item_down(self):
        current_item = self.merge_list_widget.currentItem()
        if current_item:
            row = self.merge_list_widget.row(current_item)
            if row < self.merge_list_widget.count() - 1:
                item = self.merge_list_widget.takeItem(row)
                self.merge_list_widget.insertItem(row + 1, item)
                self.merge_list_widget.setCurrentItem(item)
                self._update_internal_file_list_from_widget() # Resync
                self.merge_status_label.setText("Datei nach unten verschoben.")
        else:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _execute_merge_pdfs(self):
        self._update_internal_file_list_from_widget() # Ensure list is up-to-date from widget order
        if not self.selected_merge_files or len(self.selected_merge_files) < 2:
            QMessageBox.warning(self, "Nicht genügend Dateien", "Bitte wählen Sie mindestens zwei PDF-Dateien zum Zusammenführen aus.")
            return

        # Suggest a default filename, e.g., based on the first PDF or a generic name
        default_save_name = "merged_document.pdf"
        if self.selected_merge_files:
             first_file_dir = os.path.dirname(self.selected_merge_files[0])
             output_path_suggestion = os.path.join(first_file_dir, default_save_name)
        else:
            output_path_suggestion = default_save_name

        output_filename, _ = QFileDialog.getSaveFileName(
            self,
            "Zusammengeführte PDF speichern unter",
            output_path_suggestion,
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )

        if not output_filename:
            self.merge_status_label.setText("Zusammenführen abgebrochen.")
            return

        pdf_writer = PdfWriter()
        try:
            self.merge_status_label.setText("Führe PDFs zusammen...")
            QApplication.processEvents() # Allow UI to update status label

            for filename in self.selected_merge_files:
                try:
                    pdf_writer.append(filename)
                except Exception as append_error:
                    # Log the specific file that caused an error and skip it or halt
                    print(f"Error appending file {filename}: {append_error}")
                    QMessageBox.critical(self, "Fehler beim Anhängen", f"Fehler beim Anhängen der Datei: {os.path.basename(filename)}\n{append_error}")
                    # Optionally re-raise or return if one file error should stop the whole process
                    # For now, we'll continue with other files if possible, but the writer might be in a bad state.
                    # A safer approach might be to return here or clear the writer.
                    self.merge_status_label.setText(f"Fehler bei Datei: {os.path.basename(filename)}")
                    return # Stop merging on first error
            
            if not pdf_writer.pages: # Check if any pages were actually added
                QMessageBox.warning(self, "Keine Seiten", "Keine Seiten zum Zusammenführen vorhanden. Überprüfen Sie die Quelldateien.")
                self.merge_status_label.setText("Keine Seiten zum Zusammenführen.")
                return

            with open(output_filename, 'wb') as out:
                pdf_writer.write(out)
            
            # pdf_writer.close() # Not typically needed for PyPDF2.PdfWriter
            QMessageBox.information(self, "Erfolg", f"PDFs erfolgreich zusammengeführt in {os.path.basename(output_filename)}")
            self.merge_status_label.setText("Zusammenführen erfolgreich!")
            
            # Clear the list after successful merge
            self.selected_merge_files.clear()
            self.merge_list_widget.clear()

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Zusammenführen", f"Ein Fehler ist aufgetreten: {e}")
            self.merge_status_label.setText(f"Fehler: {e}")

    # --- Drag and Drop Event Handlers ---
    def _drag_enter_event(self, event):
        # Check if the dropped data contains URLs (file paths) - for external drops
        if event.mimeData().hasUrls():
            event.acceptProposedAction() # Accept the drop action if it contains URLs
        # Also allow internal moves
        elif event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
        else:
            event.ignore() # Ignore otherwise

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
                self._add_files_to_list_widget(dropped_files)
            else:
                self.merge_status_label.setText("Keine lokalen Dateien im Drop-Event gefunden.")
        
        # Handle internal moves (let the default implementation handle it)
        elif event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            # Call the parent's dropEvent to handle internal moves
            QListWidget.dropEvent(self.merge_list_widget, event)
        else:
            event.ignore() 