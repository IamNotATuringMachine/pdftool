import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QApplication
)
from PySide6.QtCore import Qt
from utils.common_helpers import parse_page_ranges # Assuming this remains compatible

class SplitTab(QWidget):
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.split_input_pdf_path = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Controls Group ---
        controls_group = QGroupBox("PDF auswählen und Seiten/Bereiche für Extraktion angeben")
        controls_layout = QVBoxLayout(controls_group)

        # File Selection
        file_select_layout = QHBoxLayout()
        self.select_button = QPushButton("PDF auswählen")
        self.select_button.clicked.connect(self._select_pdf_for_split)
        file_select_layout.addWidget(self.select_button)

        self.split_selected_file_label = QLabel("Keine Datei ausgewählt.")
        self.split_selected_file_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        file_select_layout.addWidget(self.split_selected_file_label, 1) # Add stretch
        controls_layout.addLayout(file_select_layout)

        # Page Input
        page_input_layout = QHBoxLayout()
        pages_label = QLabel("Seiten/Bereiche (z.B. 1-3, 5, 7-9):")
        page_input_layout.addWidget(pages_label)

        self.split_pages_entry = QLineEdit()
        self.split_pages_entry.setPlaceholderText("z.B. 1-3, 5, 7-9")
        page_input_layout.addWidget(self.split_pages_entry, 1) # Add stretch
        controls_layout.addLayout(page_input_layout)
        
        main_layout.addWidget(controls_group)

        # --- Action Area ---
        action_layout = QVBoxLayout()
        self.extract_button = QPushButton("Seiten extrahieren und speichern")
        self.extract_button.clicked.connect(self._execute_split_pdf)
        action_layout.addWidget(self.extract_button)

        self.split_status_label = QLabel("")
        self.split_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.split_status_label)
        
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _select_pdf_for_split(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF-Datei auswählen",
            "",  # Start directory
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )
        if file_path:
            self.split_input_pdf_path = file_path
            self.split_selected_file_label.setText(os.path.basename(file_path))
            self.split_status_label.setText("Datei ausgewählt. Seitenbereiche eingeben.")
        else:
            self.split_input_pdf_path = None
            self.split_selected_file_label.setText("Keine Datei ausgewählt.")
            self.split_status_label.setText("Dateiauswahl abgebrochen.")

    def _execute_split_pdf(self):
        if not self.split_input_pdf_path:
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return

        pages_str = self.split_pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben", "Bitte geben Sie die zu extrahierenden Seitenzahlen oder Bereiche ein.")
            return

        try:
            input_pdf = PdfReader(self.split_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_extract_indices = parse_page_ranges(pages_str, total_pages) # Helper function returns 0-based indices
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            self.split_status_label.setText(f"Fehler: {e}")
            return
        except Exception as e: 
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.split_status_label.setText("Fehler beim Lesen der PDF.")
            return

        if not pages_to_extract_indices:
            QMessageBox.information(self, "Keine Seiten zu extrahieren", "Die angegebenen Seiten ergeben keine zu extrahierenden Seiten.")
            self.split_status_label.setText("Keine Seiten zum Extrahieren basierend auf der Eingabe.")
            return

        initial_save_name = f"{os.path.splitext(os.path.basename(self.split_input_pdf_path))[0]}_extrahiert.pdf"
        output_filename, _ = QFileDialog.getSaveFileName(
            self,
            "Extrahierte Seiten speichern unter",
            os.path.join(os.path.dirname(self.split_input_pdf_path), initial_save_name),
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )

        if not output_filename:
            self.split_status_label.setText("Extraktion abgebrochen.")
            return

        pdf_writer = PdfWriter()
        try:
            self.split_status_label.setText("Extrahiere Seiten...")
            QApplication.processEvents() # Allow UI to update status label

            for page_index in pages_to_extract_indices:
                pdf_writer.add_page(input_pdf.pages[page_index])
            
            if len(pdf_writer.pages) == 0:
                QMessageBox.warning(self, "Leeres Ergebnis", "Es wurden keine Seiten extrahiert, die PDF wäre leer. Datei nicht gespeichert.")
                self.split_status_label.setText("Keine Seiten extrahiert. Vorgang abgebrochen.")
                return

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            # pdf_writer.close() # Not needed for PyPDF2.PdfWriter
            QMessageBox.information(self, "Erfolg", f"Seiten erfolgreich extrahiert nach {os.path.basename(output_filename)}")
            self.split_status_label.setText("Extraktion erfolgreich!")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Extrahieren der Seiten", f"Ein Fehler ist aufgetreten: {e}")
            self.split_status_label.setText(f"Fehler während der Extraktion: {e}") 