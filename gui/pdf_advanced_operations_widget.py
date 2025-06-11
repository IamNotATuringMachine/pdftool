import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QRadioButton, QApplication,
    QInputDialog, QFrame, QListWidget, QListWidgetItem, QCheckBox, QFormLayout # Added for multi-export functionality
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from utils.common_helpers import parse_page_ranges
from PIL import Image

class PDFAdvancedOperationsWidget(QWidget): # CLASS RENAMED
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.input_pdf_path = None
        self.pdf_reader = None # To store the PdfReader instance
        self.current_mode = "delete"  # delete, extract, split, set_pwd, remove_pwd, convert_to_pdf
        self.convert_files = []  # List to store files for conversion

        self._init_ui()
        self._update_ui_for_mode() # Initial UI setup based on default mode

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        # Remove margins since middle container now handles them
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(15)

        # --- Controls Group (for page operations) ---
        self.page_controls_group = QWidget()
        page_group_container_layout = QVBoxLayout(self.page_controls_group)
        page_group_container_layout.setContentsMargins(0,0,0,0)
        page_group_container_layout.setSpacing(5)
        self.page_group_title = QLabel("Seiten-Optionen")
        font = self.page_group_title.font(); font.setBold(True); self.page_group_title.setFont(font)
        page_group_container_layout.addWidget(self.page_group_title)
        page_content_frame = QFrame()
        page_content_frame.setFrameShape(QFrame.StyledPanel)
        page_content_frame.setObjectName("groupContentFrame")

        # Using QFormLayout for aligned labels and fields
        page_controls_layout = QFormLayout(page_content_frame)
        page_controls_layout.setContentsMargins(10, 10, 10, 10)
        page_controls_layout.setSpacing(10)
        page_controls_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        page_group_container_layout.addWidget(page_content_frame)

        # File Selection (re-used by all modes)
        self.loaded_pdf_display_label = QLabel("Keine PDF-Datei zum Bearbeiten geladen.")
        self.loaded_pdf_display_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loaded_pdf_display_label.setWordWrap(True)
        # Add as a full row that spans both columns
        page_controls_layout.addRow(self.loaded_pdf_display_label)

        # Page Input (only for delete/extract)
        self.pages_label = QLabel() 
        self.pages_entry = QLineEdit()
        page_controls_layout.addRow(self.pages_label, self.pages_entry)
        
        main_layout.addWidget(self.page_controls_group)

        # --- File to PDF Conversion Group ---
        self.file_conversion_group = QWidget()
        file_conv_container_layout = QVBoxLayout(self.file_conversion_group)
        file_conv_container_layout.setContentsMargins(0,0,0,0)
        file_conv_container_layout.setSpacing(5)
        self.file_conversion_group_title = QLabel("Datei(en) zu PDF konvertieren")
        font = self.file_conversion_group_title.font(); font.setBold(True); self.file_conversion_group_title.setFont(font)
        file_conv_container_layout.addWidget(self.file_conversion_group_title)
        file_conv_content_frame = QFrame()
        file_conv_content_frame.setFrameShape(QFrame.StyledPanel)
        file_conv_content_frame.setObjectName("groupContentFrame")
        file_conversion_layout = QVBoxLayout(file_conv_content_frame)
        file_conversion_layout.setContentsMargins(5, 5, 5, 5)
        file_conv_container_layout.addWidget(file_conv_content_frame)

        self.file_conversion_label = QLabel("Die Dateien aus der Hauptliste werden für die Konvertierung verwendet.")
        self.file_conversion_label.setWordWrap(True)
        file_conversion_layout.addWidget(self.file_conversion_label)
        
        # Conversion options
        self.single_pdf_convert_checkbox = QCheckBox("Alle Dateien in eine einzige PDF zusammenfassen")
        self.single_pdf_convert_checkbox.setChecked(True)
        file_conversion_layout.addWidget(self.single_pdf_convert_checkbox)
        
        main_layout.addWidget(self.file_conversion_group)

        # --- PDF Password Management Group ---
        self.password_fields_group = QWidget()
        password_fields_container_layout = QVBoxLayout(self.password_fields_group)
        password_fields_container_layout.setContentsMargins(0,0,0,0)
        password_fields_container_layout.setSpacing(5)
        self.password_fields_group_title = QLabel("Passwort-Optionen")
        font = self.password_fields_group_title.font(); font.setBold(True); self.password_fields_group_title.setFont(font)
        password_fields_container_layout.addWidget(self.password_fields_group_title)
        password_fields_content_frame = QFrame()
        password_fields_content_frame.setFrameShape(QFrame.StyledPanel)
        password_fields_content_frame.setObjectName("groupContentFrame")
        
        # Using QFormLayout for aligned labels and fields
        password_fields_layout = QFormLayout(password_fields_content_frame)
        password_fields_layout.setContentsMargins(10, 10, 10, 10) # Add some padding
        password_fields_layout.setSpacing(10) # Add some spacing between rows
        password_fields_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight) # Align labels to the right

        password_fields_container_layout.addWidget(password_fields_content_frame)

        # Current password (for removing)
        self.current_password_label = QLabel("Aktuelles Passwort:")
        self.current_password_entry = QLineEdit()
        self.current_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        password_fields_layout.addRow(self.current_password_label, self.current_password_entry)
        
        # New password (for setting)
        self.new_password_label = QLabel("Neues Passwort:")
        self.new_password_entry = QLineEdit()
        self.new_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        password_fields_layout.addRow(self.new_password_label, self.new_password_entry)
        
        # Confirm password
        self.confirm_password_label = QLabel("Passwort bestätigen:")
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        password_fields_layout.addRow(self.confirm_password_label, self.confirm_password_entry)
        
        main_layout.addWidget(self.password_fields_group)
        
        self.setLayout(main_layout)

    def set_files_for_conversion(self, file_paths):
        """Public method to set the list of files for conversion."""
        self.convert_files = list(file_paths)
        if self.app_root:
            self.app_root.log_message(f"PDFAdvancedOps: {len(self.convert_files)} Datei(en) für Konvertierung bereit.")

    def set_mode(self, mode):
        """Public method to allow external switching of the mode."""
        self._set_mode(mode)

    def _set_mode(self, mode):
        # This function is now the single point of control for the mode.
        if self.current_mode != mode:
            self.current_mode = mode
            self._update_ui_for_mode()
            # if self.app_root:
            #     self.app_root.log_message(f"PDFAdvancedOps: Mode changed to \'{mode}\'.")

    def _update_ui_for_mode(self):
        # Page operations visibility
        is_page_op = self.current_mode in ["delete", "extract", "split"]
        self.page_controls_group.setVisible(is_page_op)
        
        if is_page_op:
            if self.current_mode == "delete":
                self.page_group_title.setText("Zu löschende Seiten angeben")
                self.pages_label.setText("Seiten (z.B. 1, 3, 5-7):")
                self.pages_entry.setPlaceholderText("z.B. 1,3,5-7")
                self.pages_label.setVisible(True)
                self.pages_entry.setVisible(True)
            elif self.current_mode == "extract":
                self.page_group_title.setText("Zu extrahierende Seiten angeben")
                self.pages_label.setText("Seiten (z.B. 1-3, 5):")
                self.pages_entry.setPlaceholderText("z.B. 1-3, 5, 7-9")
                self.pages_label.setVisible(True)
                self.pages_entry.setVisible(True)
            elif self.current_mode == "split":
                self.page_group_title.setText("PDF in Einzelseiten aufteilen")
                self.pages_label.setVisible(False)
                self.pages_entry.setVisible(False)
        
        # File conversion visibility
        is_conversion_op = self.current_mode == "convert_to_pdf"
        self.file_conversion_group.setVisible(is_conversion_op)
        
        # Password operations visibility
        is_password_op = self.current_mode in ["set_pwd", "remove_pwd"]
        self.password_fields_group.setVisible(is_password_op)
        
        if is_password_op:
            if self.current_mode == "set_pwd":
                self.password_fields_group_title.setText("Neues Passwort festlegen")
                self.current_password_label.setVisible(False)
                self.current_password_entry.setVisible(False)
                self.new_password_label.setVisible(True)
                self.new_password_entry.setVisible(True)
                self.confirm_password_label.setVisible(True)
                self.confirm_password_entry.setVisible(True)
            elif self.current_mode == "remove_pwd":
                self.password_fields_group_title.setText("Aktuelles Passwort zum Entfernen")
                self.current_password_label.setVisible(True)
                self.current_password_entry.setVisible(True)
                self.new_password_label.setVisible(False)
                self.new_password_entry.setVisible(False)
                self.confirm_password_label.setVisible(False)
                self.confirm_password_entry.setVisible(False)
        


    def execute_action(self):
        if not self.input_pdf_path and self.current_mode != "convert_to_pdf":
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Action attempted with no PDF.")
            return False
        
        if self.current_mode == "convert_to_pdf" and not self.convert_files:
            QMessageBox.warning(self, "Keine Dateien ausgewählt", "Bitte fügen Sie zuerst Dateien zum Konvertieren hinzu.")
            return False

        # Page operations need a decrypted reader.
        if self.current_mode in ["delete", "extract", "split"]:
            if not self.pdf_reader or self.pdf_reader.is_encrypted:
                QMessageBox.warning(self, "PDF ist verschlüsselt oder nicht geladen", "Seiten-Operationen können nicht auf einer verschlüsselten oder nicht geladenen PDF ausgeführt werden.")
                # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Page action attempted on encrypted or unloaded PDF.")
                return False
        
        success = False
        if self.current_mode == "delete":
            success = self._perform_delete_extract_action(is_delete=True)
        elif self.current_mode == "extract":
            success = self._perform_delete_extract_action(is_delete=False)
        elif self.current_mode == "split":
            success = self._perform_split_action()
        elif self.current_mode == "set_pwd":
            success = self._set_pdf_password()
        elif self.current_mode == "remove_pwd":
            success = self._remove_pdf_password()
        elif self.current_mode == "convert_to_pdf":
            success = self._perform_conversion()
        
        if success:
            # Optionally clear loaded PDF for page ops, but maybe not for password ops
            # For now, let's not clear it, to allow multiple operations.
            # self.clear_loaded_pdf() 
            pass
        return success

    def _set_pdf_password(self):
        new_password = self.new_password_entry.text()
        confirm_password = self.confirm_password_entry.text()
        
        if not new_password or not confirm_password:
            QMessageBox.warning(self, "Fehlende Eingabe", "Bitte geben Sie das neue Passwort ein und bestätigen Sie es.")
            return False
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "Passwörter stimmen nicht überein", "Die eingegebenen Passwörter stimmen nicht überein.")
            return False
        
        try:
            # We must re-open the file to handle currently encrypted files correctly
            pdf_reader_local = PdfReader(self.input_pdf_path)
            if pdf_reader_local.is_encrypted:
                current_pwd_prompt, ok = QInputDialog.getText(self, "Passwort erforderlich",
                                                   "Die PDF ist bereits verschlüsselt. Bitte geben Sie das aktuelle Passwort ein, um es zu ändern:",
                                                   QLineEdit.EchoMode.Password)
                if not (ok and current_pwd_prompt and pdf_reader_local.decrypt(current_pwd_prompt)):
                    QMessageBox.warning(self, "Falsches Passwort", "Das eingegebene aktuelle Passwort ist falsch. Passwort kann nicht geändert werden.")
                    return False

            pdf_writer = PdfWriter()
            pdf_writer.clone_document_from_reader(pdf_reader_local)
            pdf_writer.encrypt(new_password)
            
            base_name = os.path.splitext(self.input_pdf_path)[0]
            output_path = f"{base_name}_geschützt.pdf"
            
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", f"PDF wurde mit Passwort geschützt und als '{os.path.basename(output_path)}' gespeichert.")
            # if self.app_root:
            #     self.app_root.log_message(f"PDF-Passwort gesetzt: {os.path.basename(output_path)}")
            #     self.app_root.add_to_recent_files([output_path])
            
            self.new_password_entry.clear()
            self.confirm_password_entry.clear()
            return True
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Setzen des Passworts: {str(e)}")
            # if self.app_root: self.app_root.log_message(f"Fehler beim Setzen des PDF-Passworts: {str(e)}")
            return False

    def _remove_pdf_password(self):
        current_password = self.current_password_entry.text()
        if not current_password:
            QMessageBox.warning(self, "Kein Passwort", "Bitte geben Sie das aktuelle Passwort ein.")
            return False
        
        try:
            pdf_reader_local = PdfReader(self.input_pdf_path)
            if not pdf_reader_local.is_encrypted:
                QMessageBox.information(self, "Kein Passwort", "Diese PDF-Datei ist nicht passwortgeschützt.")
                return False

            if not pdf_reader_local.decrypt(current_password):
                QMessageBox.warning(self, "Falsches Passwort", "Das eingegebene Passwort ist falsch.")
                return False
            
            pdf_writer = PdfWriter()
            pdf_writer.clone_document_from_reader(pdf_reader_local)
            # By not calling encrypt, the new PDF will be unprotected
            
            base_name = os.path.splitext(self.input_pdf_path)[0]
            output_path = f"{base_name}_ungeschützt.pdf"
            
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", f"Passwort wurde entfernt und PDF als '{os.path.basename(output_path)}' gespeichert.")
            # if self.app_root:
            #     self.app_root.log_message(f"PDF-Passwort entfernt: {os.path.basename(output_path)}")
            #     self.app_root.add_to_recent_files([output_path])
            self.current_password_entry.clear()
            return True
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Entfernen des Passworts: {str(e)}")
            # if self.app_root: self.app_root.log_message(f"Fehler beim Entfernen des PDF-Passworts: {str(e)}")
            return False



    def load_pdf(self, file_path):
        self.clear_loaded_pdf() # Clear previous state first

        if not file_path:
            self.loaded_pdf_display_label.setText("Fehler: Ungültiger Dateipfad empfangen.")
            # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Invalid file path received.")
            return

        self.input_pdf_path = file_path
        
        if self.current_mode == "convert_to_pdf":
            # For conversion mode, add the file to the conversion list instead
            if file_path not in self.convert_files:
                self.convert_files.append(file_path)
                # self._refresh_convert_list()
                if self.app_root:
                    self.app_root.log_message(f"Datei zur Konvertierungsliste hinzugefügt: {os.path.basename(file_path)}")
            return # Exit early

        # For all other modes, assume it's a PDF and try to read it.
        try:
            self.pdf_reader = PdfReader(self.input_pdf_path)
            num_pages = 0

            if self.pdf_reader.is_encrypted:
                self.loaded_pdf_display_label.setText(f"Verschlüsselte PDF geladen: {os.path.basename(self.input_pdf_path)}")
                # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Encrypted PDF loaded: {self.input_pdf_path}")
                # Don't decrypt here, let the specific action handle it if needed.
            else:
                num_pages = len(self.pdf_reader.pages)
                self.loaded_pdf_display_label.setText(f"PDF geladen: {os.path.basename(self.input_pdf_path)} ({num_pages} Seiten)")
                # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: PDF loaded: {self.input_pdf_path}")
        
            # Reset UI elements that depend on the PDF
            self.pages_entry.clear()

            # No longer need to manage a separate list of conversion files here
            # self._refresh_convert_list()

        except Exception as e:
            self.clear_loaded_pdf()
            self.loaded_pdf_display_label.setText(f"Fehler beim Laden der PDF: {os.path.basename(file_path)}")
            QMessageBox.warning(self, "Fehler beim Laden", f"Konnte die Datei nicht als PDF laden: {str(e)}")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Failed to load PDF {file_path}. Error: {e}")

    def _decrypt_pdf(self, file_path):
        """Tries to decrypt the PDF, returns reader instance or None."""
        try:
            pdf_reader = PdfReader(file_path)
            if pdf_reader.is_encrypted:
                password, ok = QInputDialog.getText(self, "Passwort erforderlich",
                                                   "Die PDF ist verschlüsselt. Bitte geben Sie das Passwort ein:",
                                                   QLineEdit.EchoMode.Password)
                if ok and password and pdf_reader.decrypt(password):
                    return pdf_reader
                else:
                    return None
            else:
                return pdf_reader
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Lesen der PDF: {str(e)}")
            return None

    def set_pdf_file(self, file_path):
        # This is the public entry point for setting a file from the main window.
        self.load_pdf(file_path)

    def clear_loaded_pdf(self):
        self.input_pdf_path = None
        self.pdf_reader = None
        self.loaded_pdf_display_label.setText("Keine PDF-Datei zum Bearbeiten geladen.")
        self.pages_entry.setText("")
        # Clear password fields as well when PDF is cleared
        self.current_password_entry.clear()
        self.new_password_entry.clear()
        self.confirm_password_entry.clear()
        # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Cleared loaded PDF and password fields.")

    def is_ready(self):
        """Checks if the widget is ready to perform the selected action."""
        if self.current_mode == "convert_to_pdf":
            # Ready if there are files selected for conversion.
            return bool(self.convert_files)

        # For all other modes, a PDF must be loaded.
        if not self.input_pdf_path or not self.pdf_reader:
            return False
        
        if self.pdf_reader.is_encrypted:
            # For encrypted PDFs, only password operations can be initiated.
            # The action itself will prompt for the password again if needed.
            return self.current_mode in ["set_pwd", "remove_pwd"]

        # From here on, the PDF is loaded and decrypted.
        if self.current_mode in ["delete", "extract"]:
            # Ready if page numbers are provided.
            return bool(self.pages_entry.text().strip())
        elif self.current_mode in ["split", "set_pwd"]:
            # Split and set_pwd only need a loaded (and decrypted) PDF.
            return True
        
        return False

    def _perform_delete_extract_action(self, is_delete):
        action_name = "löschende" if is_delete else "extrahierende"
        action_past_tense = "gelöscht" if is_delete else "extrahiert"
        output_suffix = "_geloescht" if is_delete else "_extrahiert"
        
        pages_str = self.pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben",
                                f"Bitte geben Sie die zu {action_name}n Seitenzahlen oder Bereiche ein.")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: No pages specified for {self.current_mode}.")
            return False

        try:
            total_pages = len(self.pdf_reader.pages)
            target_indices = parse_page_ranges(pages_str, total_pages) # Uses common helper
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Invalid page input for {self.current_mode}: {e}")
            return False
        except Exception as e: # Should not happen if pdf_reader is loaded correctly
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error reading PDF for {self.current_mode}: {e}")
            return False

        if not target_indices:
            QMessageBox.information(self, "Keine gültigen Seiten",
                                    f"Keine gültigen Seiten zum {action_past_tense} angegeben.")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: No valid pages for {self.current_mode}.")
            return False

        pdf_writer = PdfWriter()

        if is_delete:
            if all(p_idx in target_indices for p_idx in range(total_pages)):
                QMessageBox.warning(self, "Alle Seiten ausgewählt",
                                    "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
                # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Attempted to delete all pages.")
                return False
            for i in range(total_pages):
                if i not in target_indices:
                    pdf_writer.add_page(self.pdf_reader.pages[i])
        else: # Extract
            for page_index in target_indices:
                if 0 <= page_index < total_pages: # Should be guaranteed by parse_page_ranges
                    pdf_writer.add_page(self.pdf_reader.pages[page_index])
        
        if len(pdf_writer.pages) == 0:
            QMessageBox.warning(self, "Leeres Ergebnis", f"Keine Seiten {action_past_tense} oder Ergebnis wäre leer. Datei nicht gespeichert.")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Resulting PDF for {self.current_mode} would be empty.")
            return False

        base_name = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
        initial_name = f"{base_name}{output_suffix}.pdf"
        
        output_filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Modifizierte PDF speichern unter ({self.current_mode})",
            os.path.join(os.path.dirname(self.input_pdf_path), initial_name),
            "PDF-Dateien (*.pdf);;Alle Dateien (*.*)"
        )

        if not output_filename:
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Save cancelled for {self.current_mode}.")
            return False

        try:
            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            QMessageBox.information(self, "Erfolg",
                                    f"Seiten erfolgreich {action_past_tense}. Gespeichert unter {os.path.basename(output_filename)}")
            # if self.app_root: 
            #     self.app_root.log_message(f"PDFAdvancedOps: Pages {action_past_tense} successfully. Output: {os.path.basename(output_filename)}")
            #     self.app_root.add_to_recent_files([output_filename]) # Add to recent files
            return True
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", f"Fehler beim Speichern der PDF: {e}")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error saving PDF for {self.current_mode}: {e}")
            return False

    def _perform_split_action(self):
        if not self.pdf_reader: # Should be loaded
            QMessageBox.critical(self, "Fehler", "PDF nicht geladen.")
            # if self.app_root: self.app_root.log_message("PDFAdvancedOps: Split action attempted with no PDF reader.")
            return False

        output_dir = os.path.dirname(self.input_pdf_path)
        base_name = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
        num_pages = len(self.pdf_reader.pages)
        
        # Create a sub-directory for split files
        split_output_dir = os.path.join(output_dir, f"{base_name}_aufgeteilt")
        try:
            if not os.path.exists(split_output_dir):
                os.makedirs(split_output_dir)
        except OSError as e:
            QMessageBox.critical(self, "Fehler beim Erstellen des Ordners", f"Konnte den Ausgabeordner nicht erstellen: {split_output_dir}\\n{e}")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Failed to create split output directory: {e}")
            return False

        processed_files = []
        try:
            for i in range(num_pages):
                pdf_writer = PdfWriter()
                pdf_writer.add_page(self.pdf_reader.pages[i])
                
                output_path = os.path.join(split_output_dir, f"{base_name}_seite_{i + 1}.pdf")
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                processed_files.append(output_path)

            QMessageBox.information(self, "Erfolg", f"{num_pages} Seiten wurden erfolgreich in den Ordner \'{os.path.basename(split_output_dir)}\' aufgeteilt.")
            # if self.app_root: 
            #     self.app_root.log_message(f"PDFAdvancedOps: PDF split successfully into {num_pages} pages in \'{os.path.basename(split_output_dir)}\'.")
            #     if processed_files:
            #         self.app_root.add_to_recent_files(processed_files) # Add all split files to recent
            return True
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Aufteilen", f"Fehler beim Aufteilen der PDF: {str(e)}")
            # if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error during PDF split: {str(e)}")
            return False

    def update_theme(self, theme_name):
        """Update the widget's theme to match the application theme."""
        if theme_name == "dark":
            bg_color = "#3F4042"
            text_color = "#CCCCCC"
            border_color = "#555559"
            input_bg_color = "#2b2b2b"  # Use darker background color for input fields
            input_text_color = "#CCCCCC"
            placeholder_color = "#888888"
        else:
            bg_color = "#FFFFFF"
            text_color = "#333333"
            border_color = "#D0D0D0"
            input_bg_color = "#FFFFFF"
            input_text_color = "#333333"
            placeholder_color = "#999999"
        
        # Apply styling to this widget
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 10px;
            }}
            QGroupBox {{
                border: none;
                padding-top: 15px;
                margin-top: 5px;
                font-weight: bold;
                color: {text_color};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 0 0 5px;
            }}
            QLineEdit {{
                background-color: {input_bg_color} !important;
                color: {input_text_color} !important;
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 8px;
                selection-background-color: #0078D4;
                selection-color: white;
            }}
            QLineEdit:focus {{
                border: 2px solid #0078D4;
            }}
            QLineEdit:disabled {{
                background-color: {bg_color};
                color: {placeholder_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)

        if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Theme updated to {theme_name}")

    def _style_mode_button(self, button):
        # This method is no longer needed as the styled buttons have been removed.
        # Keeping it might cause errors if it's called from the main window.
        # For example, if it tries to access self.mode_buttons which no longer exists.
        pass

    def _perform_conversion(self):
        if not self.convert_files:
            QMessageBox.warning(self, "Keine Dateien", "Es wurden keine Dateien für die Konvertierung bereitgestellt.")
            if self.app_root:
                self.app_root.log_message("PDFAdvancedOps: Conversion attempted with no files.")
            return False
            
        if self.single_pdf_convert_checkbox.isChecked():
            return self._export_to_single_pdf()
        else:
            return self._export_to_separate_pdfs()

    def _export_to_single_pdf(self):
        # Existing implementation...
        # ...
        # This method now relies on `self.convert_files` being set externally.
        
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zusammengefasste PDF speichern unter...",
            "",
            "PDF-Dateien (*.pdf)"
        )
        if not output_path:
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Save cancelled for single PDF.")
            return False

        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        # This method now directly uses self.convert_files
        pdf_writer = PdfWriter()
        temp_files = [] # To clean up intermediate PDFs

        try:
            total_files = len(self.convert_files)
            for i, file_path in enumerate(self.convert_files):
                if self.app_root:
                    self.app_root.log_message(f"Verarbeite Datei {i+1}/{total_files}: {os.path.basename(file_path)}")

                temp_pdf_path = None
                if file_path.lower().endswith('.pdf'):
                    # Directly append pages from existing PDFs
                    try:
                        pdf_reader = PdfReader(file_path)
                        if pdf_reader.is_encrypted:
                            # For now, we skip encrypted PDFs in merge mode.
                            # A more advanced implementation could prompt for a password.
                            if self.app_root:
                                self.app_root.log_message(f"Warnung: Verschlüsselte PDF übersprungen: {os.path.basename(file_path)}")
                            continue
                        for page in pdf_reader.pages:
                            pdf_writer.add_page(page)
                    except Exception as e:
                        if self.app_root:
                            self.app_root.log_message(f"Fehler beim Lesen von PDF {os.path.basename(file_path)}: {e}")
                        continue
                else:
                    # Convert other file types to a temporary PDF
                    temp_pdf_path = self._convert_file_to_temp_pdf(file_path)
                    if temp_pdf_path:
                        temp_files.append(temp_pdf_path)
                        try:
                            pdf_reader = PdfReader(temp_pdf_path)
                            for page in pdf_reader.pages:
                                pdf_writer.add_page(page)
                        except Exception as e:
                            if self.app_root:
                                self.app_root.log_message(f"Fehler beim Verarbeiten der temporären PDF für {os.path.basename(file_path)}: {e}")

            if len(pdf_writer.pages) > 0:
                with open(output_path, 'wb') as f:
                    pdf_writer.write(f)
                if self.app_root:
                    self.app_root.log_document_action("PDF erstellt", f"Alle Dateien wurden in '{os.path.basename(output_path)}' zusammengefasst.")
                return True
            else:
                QMessageBox.warning(self, "Keine Inhalte", "Es konnten keine Inhalte für die PDF-Erstellung gefunden oder konvertiert werden.")
                if self.app_root:
                    self.app_root.log_message("PDFAdvancedOps: No content could be converted to create single PDF.")
                return False

        except Exception as e:
            QMessageBox.critical(self, "Fehler bei der Konvertierung", f"Ein Fehler ist aufgetreten: {e}")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error during single PDF export: {e}")
            return False
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except OSError as e:
                    if self.app_root:
                        self.app_root.log_message(f"PDFAdvancedOps: Could not remove temp file {temp_file}: {e}")

    def _export_to_separate_pdfs(self):
        # This method also relies on `self.convert_files` being set externally.
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Ausgabeordner für PDFs auswählen"
        )
        if not output_dir:
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Save cancelled for separate PDFs.")
            return False

        success_count = 0
        total_files = len(self.convert_files)
        for i, file_path in enumerate(self.convert_files):
            if self.app_root:
                self.app_root.log_message(f"Exportiere Datei {i+1}/{total_files}: {os.path.basename(file_path)}")

            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

            if self._convert_file_to_pdf(file_path, output_pdf_path):
                success_count += 1
                if self.app_root:
                    self.app_root.log_document_action("PDF erstellt", f"'{os.path.basename(file_path)}' wurde nach '{os.path.basename(output_pdf_path)}' konvertiert.")
            else:
                if self.app_root:
                    self.app_root.log_message(f"Fehler beim Konvertieren von '{os.path.basename(file_path)}'.")

        if success_count > 0:
            QMessageBox.information(self, "Konvertierung abgeschlossen", f"{success_count} von {total_files} Datei(en) erfolgreich als separate PDFs exportiert.")
            return True
        else:
            QMessageBox.warning(self, "Konvertierung fehlgeschlagen", "Keine der ausgewählten Dateien konnte konvertiert werden.")
            return False

    def _convert_file_to_temp_pdf(self, file_path):
        """Convert a file to a temporary PDF and return the path"""
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            temp_pdf_path = os.path.join(temp_dir, f"{base_name}_temp.pdf")
            
            if self._convert_file_to_pdf(file_path, temp_pdf_path):
                return temp_pdf_path
            return None
        except Exception:
            return None

    def _convert_file_to_pdf(self, input_path, output_path):
        """Convert various file formats to PDF"""
        try:
            file_ext = os.path.splitext(input_path)[1].lower()
            
            # Handle images
            if file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
                return self._convert_image_to_pdf(input_path, output_path)
            
            # Handle text files
            elif file_ext == '.txt':
                return self._convert_text_to_pdf(input_path, output_path)
            
            # Handle HTML files
            elif file_ext in ['.html', '.htm']:
                return self._convert_html_to_pdf(input_path, output_path)
            
            # Handle RTF files
            elif file_ext == '.rtf':
                return self._convert_rtf_to_pdf(input_path, output_path)
            
            # Handle SVG files
            elif file_ext == '.svg':
                return self._convert_svg_to_pdf(input_path, output_path)
            
            # Handle Office files (basic attempt)
            elif file_ext in ['.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp']:
                return self._convert_office_to_pdf(input_path, output_path)
            
            return False
            
        except Exception as e:
            if self.app_root:
                self.app_root.log_message(f"Konvertierungsfehler für {os.path.basename(input_path)}: {str(e)}")
            return False

    def _convert_image_to_pdf(self, image_path, output_path):
        """Convert image to PDF"""
        try:
            from PIL import Image
            image = Image.open(image_path)
            if image.mode in ['RGBA', 'P']:
                image = image.convert('RGB')
            image.save(output_path, "PDF", resolution=100.0)
            return True
        except Exception:
            return False

    def _convert_text_to_pdf(self, text_path, output_path):
        """Convert text file to PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            with open(text_path, 'r', encoding='utf-8', errors='ignore') as f:
                text_content = f.read()
            
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            lines = text_content.split('\n')
            y_position = height - 50
            
            for line in lines:
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                
                c.drawString(50, y_position, line[:100])  # Limit line length
                y_position -= 20
            
            c.save()
            return True
        except Exception:
            return False

    def _convert_html_to_pdf(self, html_path, output_path):
        """Convert HTML file to PDF"""
        try:
            from xhtml2pdf import pisa
            
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
            
            with open(output_path, 'wb') as result_file:
                pisa_status = pisa.CreatePDF(html_content, dest=result_file)
            
            return not pisa_status.err
        except Exception:
            return False

    def _convert_rtf_to_pdf(self, rtf_path, output_path):
        """Convert RTF file to PDF"""
        try:
            from striprtf.striprtf import rtf_to_text
            
            with open(rtf_path, 'r', encoding='utf-8', errors='ignore') as f:
                rtf_content = f.read()
            
            text_content = rtf_to_text(rtf_content)
            return self._convert_text_to_pdf_content(text_content, output_path)
        except Exception:
            return False

    def _convert_svg_to_pdf(self, svg_path, output_path):
        """Convert SVG file to PDF"""
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPDF
            
            drawing = svg2rlg(svg_path)
            renderPDF.drawToFile(drawing, output_path)
            return True
        except Exception:
            return False

    def _convert_office_to_pdf(self, office_path, output_path):
        """Basic attempt to convert Office files to PDF"""
        try:
            # This is a simplified version - in practice, you'd need LibreOffice or similar
            # For now, we'll just create a placeholder PDF with the filename
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            c.drawString(50, height - 50, f"Office-Datei: {os.path.basename(office_path)}")
            c.drawString(50, height - 80, "Vollständige Konvertierung erfordert LibreOffice oder MS Office.")
            c.save()
            return True
        except Exception:
            return False

    def _convert_text_to_pdf_content(self, text_content, output_path):
        """Convert text content to PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            
            c = canvas.Canvas(output_path, pagesize=A4)
            width, height = A4
            
            lines = text_content.split('\n')
            y_position = height - 50
            
            for line in lines:
                if y_position < 50:
                    c.showPage()
                    y_position = height - 50
                
                c.drawString(50, y_position, line[:100])
                y_position -= 20
            
            c.save()
            return True
        except Exception:
            return False 