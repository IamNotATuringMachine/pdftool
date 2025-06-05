import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QRadioButton, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from utils.common_helpers import parse_page_ranges

class ModifyPagesTab(QWidget):
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.input_pdf_path = None
        self.current_mode = "delete"  # or "extract"

        self._init_ui()
        self._update_ui_for_mode() # Initial UI setup based on default mode

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Mode Selection Group ---
        mode_group = QGroupBox("Aktion auswählen")
        mode_layout = QHBoxLayout(mode_group)
        
        self.delete_radio = QRadioButton("Seiten löschen")
        self.delete_radio.setChecked(True) # Default mode
        self.delete_radio.toggled.connect(lambda: self._set_mode("delete"))
        self.delete_radio.setStyleSheet("QRadioButton { text-decoration: none; font-weight: normal; }")
        # Create explicit font without underline
        font = QFont()
        font.setUnderline(False)
        font.setBold(False)
        self.delete_radio.setFont(font)
        mode_layout.addWidget(self.delete_radio)

        self.extract_radio = QRadioButton("Seiten extrahieren")
        self.extract_radio.toggled.connect(lambda: self._set_mode("extract"))
        self.extract_radio.setStyleSheet("QRadioButton { text-decoration: none; font-weight: normal; }")
        # Create explicit font without underline
        font2 = QFont()
        font2.setUnderline(False)
        font2.setBold(False)
        self.extract_radio.setFont(font2)
        mode_layout.addWidget(self.extract_radio)
        
        main_layout.addWidget(mode_group)

        # --- Controls Group ---
        controls_group = QGroupBox() # Title will be set dynamically
        self.controls_group = controls_group # To access it later for setTitle
        controls_layout = QVBoxLayout(controls_group)

        # File Selection
        file_select_layout = QHBoxLayout()
        self.loaded_pdf_display_label = QLabel("Keine PDF-Datei zum Bearbeiten geladen.")
        self.loaded_pdf_display_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loaded_pdf_display_label.setWordWrap(True) # In case of long names
        file_select_layout.addWidget(self.loaded_pdf_display_label, 1)
        
        self.browse_button = QPushButton("PDF auswählen...")
        self.browse_button.clicked.connect(self._browse_pdf_file)
        file_select_layout.addWidget(self.browse_button)
        
        controls_layout.addLayout(file_select_layout)

        # Page Input
        page_input_layout = QHBoxLayout()
        self.pages_label = QLabel() # Text will be set dynamically
        page_input_layout.addWidget(self.pages_label)

        self.pages_entry = QLineEdit()
        # Placeholder will be set dynamically
        page_input_layout.addWidget(self.pages_entry, 1)
        controls_layout.addLayout(page_input_layout)
        
        main_layout.addWidget(controls_group)

        # --- Action Area ---
        action_layout = QVBoxLayout()
        self.execute_button = QPushButton() # Text will be set dynamically
        self.execute_button.clicked.connect(self.public_perform_action_and_save)
        action_layout.addWidget(self.execute_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.status_label)
        
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

    def load_pdf(self, pdf_path):
        """Loads a PDF path for modification."""
        self.input_pdf_path = pdf_path
        if pdf_path:
            self.loaded_pdf_display_label.setText(f"Bearbeite: {os.path.basename(pdf_path)}")
        else: # Should ideally not be called with None here, clear_loaded_pdf is for that
            self.loaded_pdf_display_label.setText("Fehler: Ungültiger PDF-Pfad empfangen.")
        
        QApplication.processEvents() # Force UI update for the label
        
        self.status_label.setText("") # Clear previous status

    def clear_loaded_pdf(self):
        """Clears the currently loaded PDF and related fields."""
        self.input_pdf_path = None
        self.loaded_pdf_display_label.setText("Keine PDF-Datei zum Bearbeiten geladen.")
        self.pages_entry.setText("")
        self.status_label.setText("Bereit für PDF-Auswahl aus oberer Liste und Seiteneingabe.")

    def has_pages_to_modify(self):
        """Checks if page numbers have been entered for modification."""
        return bool(self.pages_entry.text().strip())

    def _set_mode(self, mode):
        if self.delete_radio.isChecked() and mode == "delete":
            self.current_mode = "delete"
        elif self.extract_radio.isChecked() and mode == "extract":
            self.current_mode = "extract"
        self._update_ui_for_mode()

    def _update_ui_for_mode(self):
        if self.current_mode == "delete":
            self.controls_group.setTitle("PDF auswählen und zu löschende Seiten angeben")
            self.pages_label.setText("Zu löschende Seiten (z.B. 1, 3, 5-7):")
            self.pages_entry.setPlaceholderText("z.B. 1,3,5-7")
            self.execute_button.setText("Seiten löschen")
        else: # extract mode
            self.controls_group.setTitle("PDF auswählen und Seiten/Bereiche für Extraktion angeben")
            self.pages_label.setText("Zu extrahierende Seiten/Bereiche (z.B. 1-3, 5, 7-9):")
            self.pages_entry.setPlaceholderText("z.B. 1-3, 5, 7-9")
            self.execute_button.setText("Seiten extrahieren")
        # Clear status on mode change if a file was previously processed
        if self.input_pdf_path: # A file might be loaded
            self.status_label.setText(f"Modus auf '{self.current_mode}' geändert. PDF '{os.path.basename(self.input_pdf_path)}' geladen.")
        elif self.has_pages_to_modify(): # Pages entered but no PDF yet
            self.status_label.setText(f"Modus auf '{self.current_mode}' geändert. Seiten eingegeben, PDF oben auswählen.")
        else: # Clean state
            self.status_label.setText(f"Modus auf '{self.current_mode}' geändert. Bereit.")
        # self.pages_entry.setText("") # Don't clear pages on mode change

    def public_perform_action_and_save(self):
        if not self.input_pdf_path:
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return False

        pages_str = self.pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben",
                                f"Bitte geben Sie die zu {self.current_mode}enden Seitenzahlen oder Bereiche ein.")
            return False

        try:
            input_pdf = PdfReader(self.input_pdf_path)
            total_pages = len(input_pdf.pages)
            # parse_page_ranges returns 0-based indices
            target_indices = parse_page_ranges(pages_str, total_pages)
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            self.status_label.setText(f"Fehler: {e}")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.status_label.setText("Fehler beim Lesen der PDF.")
            return False

        if not target_indices:
            QMessageBox.information(self, "Keine gültigen Seiten",
                                    f"Keine gültigen Seiten zum {self.current_mode} angegeben.")
            self.status_label.setText(f"Keine gültigen Seiten zum {self.current_mode}.")
            return False

        pdf_writer = PdfWriter()
        action_performed = False

        if self.current_mode == "delete":
            if all(p_idx in target_indices for p_idx in range(total_pages)):
                QMessageBox.warning(self, "Alle Seiten ausgewählt",
                                    "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
                self.status_label.setText("Kann nicht alle Seiten löschen.")
                return False

            for i in range(total_pages):
                if i not in target_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0: # Should be caught by 'all pages selected' but as a safeguard
                 QMessageBox.warning(self, "Leeres Ergebnis", "Alle angegebenen Seiten wurden gelöscht, was zu einer leeren PDF führt. Datei nicht gespeichert.")
                 self.status_label.setText("Die resultierende PDF wäre leer. Vorgang abgebrochen.")
                 return False
            action_performed = True
            initial_save_name_suffix = "_gelöscht"
            success_message = "Seiten erfolgreich gelöscht."

        else: # extract mode
            for page_index in target_indices:
                # Ensure page_index is valid (parse_page_ranges should handle this, but double check)
                if 0 <= page_index < total_pages:
                    pdf_writer.add_page(input_pdf.pages[page_index])
            
            if len(pdf_writer.pages) == 0:
                QMessageBox.warning(self, "Leeres Ergebnis",
                                    "Es wurden keine Seiten extrahiert, die PDF wäre leer. Datei nicht gespeichert.")
                self.status_label.setText("Keine Seiten extrahiert. Vorgang abgebrochen.")
                return False
            action_performed = True
            initial_save_name_suffix = "_extrahiert"
            success_message = "Seiten erfolgreich extrahiert."

        if not action_performed or len(pdf_writer.pages) == 0 : # Should not happen if logic above is correct
            self.status_label.setText(f"Keine Aktion durchgeführt oder Ergebnis wäre leer.")
            return False

        base_name = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
        initial_name = f"{base_name}{initial_save_name_suffix}.pdf"
        
        output_filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Modifizierte PDF speichern unter ({self.current_mode})",
            os.path.join(os.path.dirname(self.input_pdf_path), initial_name),
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )

        if not output_filename:
            self.status_label.setText(f"{self.current_mode.capitalize()} abgebrochen.")
            return False

        try:
            self.status_label.setText(f"{self.current_mode.capitalize()} Seiten...")
            QApplication.processEvents()

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            QMessageBox.information(self, "Erfolg",
                                    f"{success_message} Gespeichert unter {os.path.basename(output_filename)}")
            self.status_label.setText(f"{self.current_mode.capitalize()} erfolgreich!")
            self.clear_loaded_pdf() # Reset after successful action
            return True # Indicate success

        except Exception as e:
            QMessageBox.critical(self, f"Fehler beim {self.current_mode} der Seiten",
                                 f"Ein Fehler ist aufgetreten: {e}")
            self.status_label.setText(f"Fehler während {self.current_mode}.")
            return False

    def is_ready_for_action(self):
        """Checks if a PDF is loaded and page numbers are entered."""
        return bool(self.input_pdf_path and self.pages_entry.text().strip())

    def _browse_pdf_file(self):
        """Opens a file dialog to select a PDF file."""
        pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF-Datei auswählen",
            "",
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )
        if pdf_path:
            self.load_pdf(pdf_path)

# Basic test structure if run directly (optional)
if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    
    # Example: Apply a theme if you have one (like qdarktheme)
    # import qdarktheme
    # qdarktheme.setup_theme("light")

    main_win = QWidget() # Or a QMainWindow if you want to test it more integratedly
    main_win.setWindowTitle("Modify Pages Tab Test")
    layout = QVBoxLayout(main_win)
    tab = ModifyPagesTab()
    layout.addWidget(tab)
    main_win.resize(600, 400)
    main_win.show()
    
    sys.exit(app.exec()) 