import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QRadioButton, QApplication
)
from PySide6.QtCore import Qt
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
        mode_layout.addWidget(self.delete_radio)

        self.extract_radio = QRadioButton("Seiten extrahieren")
        self.extract_radio.toggled.connect(lambda: self._set_mode("extract"))
        mode_layout.addWidget(self.extract_radio)
        
        main_layout.addWidget(mode_group)

        # --- Controls Group ---
        controls_group = QGroupBox() # Title will be set dynamically
        self.controls_group = controls_group # To access it later for setTitle
        controls_layout = QVBoxLayout(controls_group)

        # File Selection
        file_select_layout = QHBoxLayout()
        self.select_button = QPushButton("PDF auswählen")
        self.select_button.clicked.connect(self._select_pdf)
        file_select_layout.addWidget(self.select_button)

        self.selected_file_label = QLabel("Keine Datei ausgewählt.")
        self.selected_file_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        file_select_layout.addWidget(self.selected_file_label, 1)
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
        self.execute_button.clicked.connect(self._execute_action)
        action_layout.addWidget(self.execute_button)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        action_layout.addWidget(self.status_label)
        
        main_layout.addLayout(action_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

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
            self.execute_button.setText("Seiten löschen und speichern")
        else: # extract mode
            self.controls_group.setTitle("PDF auswählen und Seiten/Bereiche für Extraktion angeben")
            self.pages_label.setText("Zu extrahierende Seiten/Bereiche (z.B. 1-3, 5, 7-9):")
            self.pages_entry.setPlaceholderText("z.B. 1-3, 5, 7-9")
            self.execute_button.setText("Seiten extrahieren und speichern")
        # Clear status on mode change if a file was previously processed
        if self.input_pdf_path:
            self.status_label.setText("Modus geändert. Bereit für neue Aktion.")
        else:
            self.status_label.setText("")


    def _select_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF-Datei auswählen",
            "",
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )
        if file_path:
            self.input_pdf_path = file_path
            self.selected_file_label.setText(os.path.basename(file_path))
            self.status_label.setText(f"Datei ausgewählt. '{self.current_mode.capitalize()}' Modus aktiv.")
        else:
            self.input_pdf_path = None
            self.selected_file_label.setText("Keine Datei ausgewählt.")
            self.status_label.setText("Dateiauswahl abgebrochen.")

    def _execute_action(self):
        if not self.input_pdf_path:
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return

        pages_str = self.pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben", 
                                f"Bitte geben Sie die zu {self.current_mode}enden Seitenzahlen oder Bereiche ein.")
            return

        try:
            input_pdf = PdfReader(self.input_pdf_path)
            total_pages = len(input_pdf.pages)
            # parse_page_ranges returns 0-based indices
            target_indices = parse_page_ranges(pages_str, total_pages) 
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            self.status_label.setText(f"Fehler: {e}")
            return
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.status_label.setText("Fehler beim Lesen der PDF.")
            return

        if not target_indices:
            QMessageBox.information(self, "Keine gültigen Seiten", 
                                    f"Keine gültigen Seiten zum {self.current_mode} angegeben.")
            self.status_label.setText(f"Keine gültigen Seiten zum {self.current_mode}.")
            return

        pdf_writer = PdfWriter()
        action_performed = False

        if self.current_mode == "delete":
            if all(p_idx in target_indices for p_idx in range(total_pages)):
                QMessageBox.warning(self, "Alle Seiten ausgewählt", 
                                    "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
                self.status_label.setText("Kann nicht alle Seiten löschen.")
                return

            for i in range(total_pages):
                if i not in target_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0: # Should be caught by 'all pages selected' but as a safeguard
                 QMessageBox.warning(self, "Leeres Ergebnis", "Alle angegebenen Seiten wurden gelöscht, was zu einer leeren PDF führt. Datei nicht gespeichert.")
                 self.status_label.setText("Die resultierende PDF wäre leer. Vorgang abgebrochen.")
                 return
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
                return
            action_performed = True
            initial_save_name_suffix = "_extrahiert"
            success_message = "Seiten erfolgreich extrahiert."

        if not action_performed or len(pdf_writer.pages) == 0 : # Should not happen if logic above is correct
            self.status_label.setText(f"Keine Aktion durchgeführt oder Ergebnis wäre leer.")
            return

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
            return

        try:
            self.status_label.setText(f"{self.current_mode.capitalize()} Seiten...")
            QApplication.processEvents() 

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            QMessageBox.information(self, "Erfolg", 
                                    f"{success_message} Gespeichert unter {os.path.basename(output_filename)}")
            self.status_label.setText(f"{self.current_mode.capitalize()} erfolgreich!")

        except Exception as e:
            QMessageBox.critical(self, f"Fehler beim {self.current_mode} der Seiten", 
                                 f"Ein Fehler ist aufgetreten: {e}")
            self.status_label.setText(f"Fehler während {self.current_mode}.")

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