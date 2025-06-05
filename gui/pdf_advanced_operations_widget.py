import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QGroupBox, QRadioButton, QApplication,
    QInputDialog, QFrame # Added for password prompt and separator
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from utils.common_helpers import parse_page_ranges

class PDFAdvancedOperationsWidget(QWidget): # CLASS RENAMED
    def __init__(self, app_root=None):
        super().__init__()
        self.app_root = app_root
        self.input_pdf_path = None
        self.pdf_reader = None # To store the PdfReader instance
        self.current_mode = "delete"  # delete, extract, split, set_pwd, remove_pwd

        self._init_ui()
        self._update_ui_for_mode() # Initial UI setup based on default mode

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Controls Group (for page operations) ---
        self.page_controls_group = QGroupBox("Seiten-Optionen")
        page_controls_layout = QVBoxLayout(self.page_controls_group)

        # File Selection (re-used by all modes)
        file_select_layout = QHBoxLayout()
        self.loaded_pdf_display_label = QLabel("Keine PDF-Datei zum Bearbeiten geladen.")
        self.loaded_pdf_display_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.loaded_pdf_display_label.setWordWrap(True)
        file_select_layout.addWidget(self.loaded_pdf_display_label, 1)
        page_controls_layout.addLayout(file_select_layout)

        # Page Input (only for delete/extract)
        self.page_input_widget = QWidget()
        page_input_layout = QHBoxLayout(self.page_input_widget)
        page_input_layout.setContentsMargins(0,0,0,0)
        self.pages_label = QLabel() 
        page_input_layout.addWidget(self.pages_label)
        self.pages_entry = QLineEdit()
        page_input_layout.addWidget(self.pages_entry, 1)
        page_controls_layout.addWidget(self.page_input_widget)
        
        main_layout.addWidget(self.page_controls_group)

        # --- PDF Password Management Group ---
        self.password_fields_group = QGroupBox("Passwort-Optionen")
        password_fields_layout = QVBoxLayout(self.password_fields_group)
        
        # Current password (for removing)
        self.current_password_layout_widget = QWidget()
        current_password_layout = QHBoxLayout(self.current_password_layout_widget)
        current_password_layout.setContentsMargins(0,0,0,0)
        current_password_layout.addWidget(QLabel("Aktuelles Passwort:"))
        self.current_password_entry = QLineEdit()
        self.current_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        current_password_layout.addWidget(self.current_password_entry)
        password_fields_layout.addWidget(self.current_password_layout_widget)
        
        # New password (for setting)
        self.new_password_layout_widget = QWidget()
        new_password_layout = QHBoxLayout(self.new_password_layout_widget)
        new_password_layout.setContentsMargins(0,0,0,0)
        new_password_layout.addWidget(QLabel("Neues Passwort:"))
        self.new_password_entry = QLineEdit()
        self.new_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        new_password_layout.addWidget(self.new_password_entry)
        password_fields_layout.addWidget(self.new_password_layout_widget)
        
        # Confirm password
        self.confirm_password_layout_widget = QWidget()
        confirm_password_layout = QHBoxLayout(self.confirm_password_layout_widget)
        confirm_password_layout.setContentsMargins(0,0,0,0)
        confirm_password_layout.addWidget(QLabel("Passwort bestätigen:"))
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        confirm_password_layout.addWidget(self.confirm_password_entry)
        password_fields_layout.addWidget(self.confirm_password_layout_widget)
        
        main_layout.addWidget(self.password_fields_group)
        
        self.setLayout(main_layout)

    def set_mode(self, mode):
        """Public method to allow external switching of the mode."""
        self._set_mode(mode)

    def _set_mode(self, mode):
        # This function is now the single point of control for the mode.
        if self.current_mode != mode:
            self.current_mode = mode
            self._update_ui_for_mode()
            if self.app_root:
                self.app_root.log_message(f"PDFAdvancedOps: Mode changed to \'{mode}\'.")

    def _update_ui_for_mode(self):
        # Page operations visibility
        is_page_op = self.current_mode in ["delete", "extract", "split"]
        self.page_controls_group.setVisible(is_page_op)
        
        if is_page_op:
            if self.current_mode == "delete":
                self.page_controls_group.setTitle("Zu löschende Seiten angeben")
                self.pages_label.setText("Seiten (z.B. 1, 3, 5-7):")
                self.pages_entry.setPlaceholderText("z.B. 1,3,5-7")
                self.page_input_widget.setVisible(True)
            elif self.current_mode == "extract":
                self.page_controls_group.setTitle("Zu extrahierende Seiten angeben")
                self.pages_label.setText("Seiten (z.B. 1-3, 5):")
                self.pages_entry.setPlaceholderText("z.B. 1-3, 5, 7-9")
                self.page_input_widget.setVisible(True)
            elif self.current_mode == "split":
                self.page_controls_group.setTitle("PDF in Einzelseiten aufteilen")
                self.page_input_widget.setVisible(False)
        
        # Password operations visibility
        is_password_op = self.current_mode in ["set_pwd", "remove_pwd"]
        self.password_fields_group.setVisible(is_password_op)
        
        if is_password_op:
            if self.current_mode == "set_pwd":
                self.password_fields_group.setTitle("Neues Passwort festlegen")
                self.current_password_layout_widget.setVisible(False)
                self.new_password_layout_widget.setVisible(True)
                self.confirm_password_layout_widget.setVisible(True)
            elif self.current_mode == "remove_pwd":
                self.password_fields_group.setTitle("Aktuelles Passwort zum Entfernen")
                self.current_password_layout_widget.setVisible(True)
                self.new_password_layout_widget.setVisible(False)
                self.confirm_password_layout_widget.setVisible(False)

    def public_perform_action_and_save(self):
        if not self.input_pdf_path:
            QMessageBox.warning(self, "Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Action attempted with no PDF.")
            return False

        # Page operations need a decrypted reader.
        if self.current_mode in ["delete", "extract", "split"]:
            if not self.pdf_reader or self.pdf_reader.is_encrypted:
                QMessageBox.warning(self, "PDF ist verschlüsselt oder nicht geladen", "Seiten-Operationen können nicht auf einer verschlüsselten oder nicht geladenen PDF ausgeführt werden.")
                if self.app_root: self.app_root.log_message("PDFAdvancedOps: Page action attempted on encrypted or unloaded PDF.")
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
            if self.app_root:
                self.app_root.log_message(f"PDF-Passwort gesetzt: {os.path.basename(output_path)}")
                self.app_root.add_to_recent_files([output_path])
            
            self.new_password_entry.clear()
            self.confirm_password_entry.clear()
            return True
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Setzen des Passworts: {str(e)}")
            if self.app_root: self.app_root.log_message(f"Fehler beim Setzen des PDF-Passworts: {str(e)}")
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
            if self.app_root:
                self.app_root.log_message(f"PDF-Passwort entfernt: {os.path.basename(output_path)}")
                self.app_root.add_to_recent_files([output_path])
            self.current_password_entry.clear()
            return True
                
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Entfernen des Passworts: {str(e)}")
            if self.app_root: self.app_root.log_message(f"Fehler beim Entfernen des PDF-Passworts: {str(e)}")
            return False

    def load_pdf(self, pdf_path):
        self.input_pdf_path = pdf_path
        self.pdf_reader = None # Reset
        
        if not pdf_path:
            self.loaded_pdf_display_label.setText("Fehler: Ungültiger PDF-Pfad empfangen.")
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Invalid PDF path.")
            return

        try:
            self.pdf_reader = PdfReader(self.input_pdf_path)
            num_pages = 0

            if self.pdf_reader.is_encrypted:
                password, ok = QInputDialog.getText(self, "Passwort erforderlich",
                                                   "Diese PDF ist passwortgeschützt. Bitte geben Sie das Passwort ein:",
                                                   QLineEdit.EchoMode.Password)
                if ok and password:
                    if not self.pdf_reader.decrypt(password):
                        QMessageBox.warning(self, "Falsches Passwort", "Das eingegebene Passwort ist falsch. PDF kann nicht geladen werden.")
                        if self.app_root: self.app_root.log_message("PDFAdvancedOps: Incorrect password for PDF.")
                        self.clear_loaded_pdf()
                        return
                    # If decrypted, num_pages will be set below
                else: # User cancelled or entered no password
                    if self.app_root: self.app_root.log_message("PDFAdvancedOps: Password entry cancelled for PDF.")
                    self.clear_loaded_pdf()
                    return
            
            num_pages = len(self.pdf_reader.pages)
            self.loaded_pdf_display_label.setText(f"Bearbeite: {os.path.basename(pdf_path)} ({num_pages} Seiten)")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Loaded '{os.path.basename(pdf_path)}' ({num_pages} pages).")

        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Laden der PDF", f"PDF konnte nicht gelesen werden: {e}")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error loading PDF '{os.path.basename(pdf_path)}': {e}")
            self.clear_loaded_pdf()
            return
        
        QApplication.processEvents()

    def set_pdf_file(self, file_path):
        if file_path and os.path.exists(file_path) and file_path.lower().endswith('.pdf'):
            self.load_pdf(file_path)
            # No separate log here, load_pdf does it
        else:
            self.clear_loaded_pdf()
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Invalid or non-PDF file selected.")

    def clear_loaded_pdf(self):
        self.input_pdf_path = None
        self.pdf_reader = None
        self.loaded_pdf_display_label.setText("Keine PDF-Datei zum Bearbeiten geladen.")
        self.pages_entry.setText("")
        # Clear password fields as well when PDF is cleared
        self.current_password_entry.clear()
        self.new_password_entry.clear()
        self.confirm_password_entry.clear()
        if self.app_root: self.app_root.log_message("PDFAdvancedOps: Cleared loaded PDF and password fields.")

    def is_ready_for_action(self):
        if not self.input_pdf_path or not self.pdf_reader: # Check pdf_reader too
            return False
        if self.current_mode in ["delete", "extract"]:
            return bool(self.pages_entry.text().strip())
        elif self.current_mode == "split":
            return True # Split only needs a loaded PDF
        return False

    def _perform_delete_extract_action(self, is_delete):
        action_name = "löschende" if is_delete else "extrahierende"
        action_past_tense = "gelöscht" if is_delete else "extrahiert"
        output_suffix = "_geloescht" if is_delete else "_extrahiert"
        
        pages_str = self.pages_entry.text()
        if not pages_str:
            QMessageBox.warning(self, "Keine Seiten angegeben",
                                f"Bitte geben Sie die zu {action_name}n Seitenzahlen oder Bereiche ein.")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: No pages specified for {self.current_mode}.")
            return False

        try:
            total_pages = len(self.pdf_reader.pages)
            target_indices = parse_page_ranges(pages_str, total_pages) # Uses common helper
        except ValueError as e:
            QMessageBox.critical(self, "Ungültige Seiteneingabe", str(e))
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Invalid page input for {self.current_mode}: {e}")
            return False
        except Exception as e: # Should not happen if pdf_reader is loaded correctly
            QMessageBox.critical(self, "Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error reading PDF for {self.current_mode}: {e}")
            return False

        if not target_indices:
            QMessageBox.information(self, "Keine gültigen Seiten",
                                    f"Keine gültigen Seiten zum {action_past_tense} angegeben.")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: No valid pages for {self.current_mode}.")
            return False

        pdf_writer = PdfWriter()

        if is_delete:
            if all(p_idx in target_indices for p_idx in range(total_pages)):
                QMessageBox.warning(self, "Alle Seiten ausgewählt",
                                    "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
                if self.app_root: self.app_root.log_message("PDFAdvancedOps: Attempted to delete all pages.")
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
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Resulting PDF for {self.current_mode} would be empty.")
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
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Save cancelled for {self.current_mode}.")
            return False

        try:
            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            QMessageBox.information(self, "Erfolg",
                                    f"Seiten erfolgreich {action_past_tense}. Gespeichert unter {os.path.basename(output_filename)}")
            if self.app_root: 
                self.app_root.log_message(f"PDFAdvancedOps: Pages {action_past_tense} successfully. Output: {os.path.basename(output_filename)}")
                self.app_root.add_to_recent_files([output_filename]) # Add to recent files
            return True
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Speichern", f"Fehler beim Speichern der PDF: {e}")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error saving PDF for {self.current_mode}: {e}")
            return False

    def _perform_split_action(self):
        if not self.pdf_reader: # Should be loaded
            QMessageBox.critical(self, "Fehler", "PDF nicht geladen.")
            if self.app_root: self.app_root.log_message("PDFAdvancedOps: Split action attempted with no PDF reader.")
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
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Failed to create split output directory: {e}")
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
            if self.app_root: 
                self.app_root.log_message(f"PDFAdvancedOps: PDF split successfully into {num_pages} pages in \'{os.path.basename(split_output_dir)}\'.")
                if processed_files:
                    self.app_root.add_to_recent_files(processed_files) # Add all split files to recent
            return True
        except Exception as e:
            QMessageBox.critical(self, "Fehler beim Aufteilen", f"Fehler beim Aufteilen der PDF: {str(e)}")
            if self.app_root: self.app_root.log_message(f"PDFAdvancedOps: Error during PDF split: {str(e)}")
            return False

    def update_theme(self, theme_name):
        # This method is no longer needed as the styled buttons have been removed.
        # Keeping it might cause errors if it's called from the main window.
        # For example, if it tries to access self.mode_buttons which no longer exists.
        pass

    def _style_mode_button(self, button):
        # This method is no longer needed as the styled buttons have been removed.
        # Keeping it might cause errors if it's called from the main window.
        # For example, if it tries to access self.mode_buttons which no longer exists.
        pass 