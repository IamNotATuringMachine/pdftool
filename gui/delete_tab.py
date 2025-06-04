import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QFileDialog,
    QMessageBox,
    QGroupBox
)
from PySide6.QtCore import Qt
from utils.common_helpers import parse_page_ranges # Assuming this remains compatible

class DeleteTab(QWidget):
    def __init__(self, app_root=None): # app_root might be needed for global app functions
        super().__init__()
        self.app_root = app_root # Store if needed, or remove if not used by Qt version
        self.delete_input_pdf_path = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Controls Group ---
        controls_group = QGroupBox("PDF auswählen und zu löschende Seiten angeben")
        controls_layout = QVBoxLayout(controls_group)

        # File Selection
        file_select_layout = QHBoxLayout()
        self.select_button = QPushButton("PDF auswählen")
        self.select_button.clicked.connect(self._select_pdf_for_delete)
        file_select_layout.addWidget(self.select_button)

        self.delete_selected_file_label = QLabel("Keine Datei ausgewählt.")
        self.delete_selected_file_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        file_select_layout.addWidget(self.delete_selected_file_label, 1) # Add stretch
        controls_layout.addLayout(file_select_layout)

        # Page Input
        page_input_layout = QHBoxLayout()
        pages_label = QLabel("Zu löschende Seiten (z.B. 1, 3, 5-7):")
        page_input_layout.addWidget(pages_label)

        self.delete_pages_entry = QLineEdit()
        self.delete_pages_entry.setPlaceholderText("z.B. 1,3,5-7")
        page_input_layout.addWidget(self.delete_pages_entry, 1) # Add stretch
        controls_layout.addLayout(page_input_layout)
        
        main_layout.addWidget(controls_group)

        # --- Action Area ---
        action_layout = QVBoxLayout() # Using QVBoxLayout for vertical arrangement of button and status

        self.delete_button = QPushButton("Seiten löschen und speichern")
        self.delete_button.clicked.connect(self._execute_delete_pages)
        action_layout.addWidget(self.delete_button)

        self.delete_status_label = QLabel("")
        self.delete_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.delete_status_label)
        
        main_layout.addLayout(action_layout)
        main_layout.addStretch() # Pushes everything to the top

        self.setLayout(main_layout)

    def _select_pdf_for_delete(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF-Datei auswählen",
            "",  # Start directory
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )
        if file_path:
            self.delete_input_pdf_path = file_path
            self.delete_selected_file_label.setText(os.path.basename(file_path))
            self.delete_status_label.setText("Datei ausgewählt. Zu löschende Seiten eingeben.")
        else:
            self.delete_input_pdf_path = None
            self.delete_selected_file_label.setText("Keine Datei ausgewählt.")
            self.delete_status_label.setText("Dateiauswahl abgebrochen.")

    def _parse_pages_to_delete(self, pages_str, total_pages):
        # This method directly uses the imported helper function
        return parse_page_ranges(pages_str, total_pages)

    def _execute_delete_pages(self):
        if not self.delete_input_pdf_path:
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return

        pages_str = self.delete_pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben", "Bitte geben Sie die zu löschenden Seitenzahlen oder Bereiche ein.")
            return

        try:
            input_pdf = PdfReader(self.delete_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_delete_indices = self._parse_pages_to_delete(pages_str, total_pages)
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            self.delete_status_label.setText(f"Fehler: {e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.delete_status_label.setText("Fehler beim Lesen der PDF.")
            return

        if not pages_to_delete_indices:
            QMessageBox.information(self, "Keine gültigen Seiten", "Keine gültigen Seiten zum Löschen angegeben.")
            self.delete_status_label.setText("Keine gültigen Seiten zum Löschen.")
            return
        
        if all(p_idx in pages_to_delete_indices for p_idx in range(total_pages)):
            QMessageBox.warning(self, "Alle Seiten ausgewählt", "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
            self.delete_status_label.setText("Kann nicht alle Seiten löschen.")
            return

        initial_name = f"{os.path.splitext(os.path.basename(self.delete_input_pdf_path))[0]}_geändert.pdf"
        output_filename, _ = QFileDialog.getSaveFileName(
            self,
            "Geänderte PDF speichern unter",
            os.path.join(os.path.dirname(self.delete_input_pdf_path), initial_name), # Suggest in same dir with new name
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )

        if not output_filename:
            self.delete_status_label.setText("Speichern abgebrochen.") # Changed from Löschen to Speichern for clarity
            return

        pdf_writer = PdfWriter()
        try:
            self.delete_status_label.setText("Lösche Seiten...")
            # self.app_root.update_idletasks() # Not directly applicable/needed in Qt in the same way
            # Qt processes events in its event loop. For UI updates during long tasks,
            # consider QProgressDialog or threading if it becomes an issue.

            for i in range(total_pages):
                if i not in pages_to_delete_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0:
                 QMessageBox.warning(self, "Leeres Ergebnis", "Alle angegebenen Seiten wurden gelöscht, was zu einer leeren PDF führt. Datei nicht gespeichert.")
                 self.delete_status_label.setText("Die resultierende PDF wäre leer. Vorgang abgebrochen.")
                 # pdf_writer.close() # PdfWriter doesn't have a close() method in PyPDF2 3.0.0+
                 return

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            # pdf_writer.close() # Not needed for PdfWriter
            QMessageBox.information(self, "Erfolg", f"Seiten erfolgreich gelöscht. Gespeichert unter {os.path.basename(output_filename)}")
            self.delete_status_label.setText("Löschen erfolgreich!")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Löschen der Seiten", f"Ein Fehler ist aufgetreten: {e}")
            self.delete_status_label.setText("Fehler während des Löschens.") 