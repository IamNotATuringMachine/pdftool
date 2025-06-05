import os
from PyPDF2 import PdfReader, PdfWriter
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QRadioButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class PDFPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Passwort setzen/entfernen")
        self.setModal(True)
        self.resize(500, 300)
        
        self.input_pdf_path = None
        self.action_mode = "set"  # "set" or "remove"
        
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Mode Selection
        mode_group = QGroupBox("Aktion auswählen")
        mode_layout = QHBoxLayout(mode_group)
        
        self.set_password_radio = QRadioButton("Passwort setzen")
        self.set_password_radio.setChecked(True)
        self.set_password_radio.toggled.connect(lambda: self._set_mode("set"))
        mode_layout.addWidget(self.set_password_radio)
        
        self.remove_password_radio = QRadioButton("Passwort entfernen")
        self.remove_password_radio.toggled.connect(lambda: self._set_mode("remove"))
        mode_layout.addWidget(self.remove_password_radio)
        
        main_layout.addWidget(mode_group)
        
        # File Selection
        file_group = QGroupBox("PDF-Datei auswählen")
        file_layout = QVBoxLayout(file_group)
        
        file_select_layout = QHBoxLayout()
        self.file_path_label = QLabel("Keine Datei ausgewählt")
        file_select_layout.addWidget(self.file_path_label, 1)
        
        self.browse_button = QPushButton("Durchsuchen...")
        self.browse_button.clicked.connect(self._browse_file)
        file_select_layout.addWidget(self.browse_button)
        
        file_layout.addLayout(file_select_layout)
        main_layout.addWidget(file_group)
        
        # Password Input
        self.password_group = QGroupBox("Passwort eingeben")
        password_layout = QVBoxLayout(self.password_group)
        
        # Current password (for removing)
        self.current_password_layout = QHBoxLayout()
        self.current_password_layout.addWidget(QLabel("Aktuelles Passwort:"))
        self.current_password_entry = QLineEdit()
        self.current_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_layout.addWidget(self.current_password_entry)
        password_layout.addLayout(self.current_password_layout)
        
        # New password (for setting)
        self.new_password_layout = QHBoxLayout()
        self.new_password_layout.addWidget(QLabel("Neues Passwort:"))
        self.new_password_entry = QLineEdit()
        self.new_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_layout.addWidget(self.new_password_entry)
        password_layout.addLayout(self.new_password_layout)
        
        # Confirm password
        self.confirm_password_layout = QHBoxLayout()
        self.confirm_password_layout.addWidget(QLabel("Passwort bestätigen:"))
        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_layout.addWidget(self.confirm_password_entry)
        password_layout.addLayout(self.confirm_password_layout)
        
        main_layout.addWidget(self.password_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.execute_button = QPushButton()
        self.execute_button.clicked.connect(self._execute_action)
        button_layout.addWidget(self.execute_button)
        
        cancel_button = QPushButton("Abbrechen")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Status Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        self._update_ui_for_mode()
    
    def _set_mode(self, mode):
        self.action_mode = mode
        self._update_ui_for_mode()
    
    def _update_ui_for_mode(self):
        if self.action_mode == "set":
            self.execute_button.setText("Passwort setzen")
            # Hide current password for setting
            for i in range(self.current_password_layout.count()):
                widget = self.current_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(False)
            # Show new password and confirm
            for i in range(self.new_password_layout.count()):
                widget = self.new_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            for i in range(self.confirm_password_layout.count()):
                widget = self.confirm_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
        else:  # remove
            self.execute_button.setText("Passwort entfernen")
            # Show current password for removing
            for i in range(self.current_password_layout.count()):
                widget = self.current_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(True)
            # Hide new password fields
            for i in range(self.new_password_layout.count()):
                widget = self.new_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(False)
            for i in range(self.confirm_password_layout.count()):
                widget = self.confirm_password_layout.itemAt(i).widget()
                if widget:
                    widget.setVisible(False)
    
    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "PDF-Datei auswählen",
            "",
            "PDF-Dateien (*.pdf)"
        )
        if file_path:
            self.input_pdf_path = file_path
            self.file_path_label.setText(os.path.basename(file_path))
            self.status_label.setText("")
    
    def _execute_action(self):
        if not self.input_pdf_path:
            QMessageBox.warning(self, "Keine Datei", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return
        
        if self.action_mode == "set":
            self._set_password()
        else:
            self._remove_password()
    
    def _set_password(self):
        new_password = self.new_password_entry.text()
        confirm_password = self.confirm_password_entry.text()
        
        if not new_password:
            QMessageBox.warning(self, "Kein Passwort", "Bitte geben Sie ein Passwort ein.")
            return
        
        if new_password != confirm_password:
            QMessageBox.warning(self, "Passwörter stimmen nicht überein", 
                               "Die eingegebenen Passwörter stimmen nicht überein.")
            return
        
        try:
            # Read the PDF
            pdf_reader = PdfReader(self.input_pdf_path)
            pdf_writer = PdfWriter()
            
            # Copy all pages
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            # Set password
            pdf_writer.encrypt(new_password)
            
            # Save with _protected suffix
            base_name = os.path.splitext(self.input_pdf_path)[0]
            output_path = f"{base_name}_geschützt.pdf"
            
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", 
                                   f"PDF wurde mit Passwort geschützt und als '{os.path.basename(output_path)}' gespeichert.")
            self.status_label.setText("Passwort erfolgreich gesetzt.")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Setzen des Passworts: {str(e)}")
            self.status_label.setText("Fehler beim Setzen des Passworts.")
    
    def _remove_password(self):
        current_password = self.current_password_entry.text()
        
        if not current_password:
            QMessageBox.warning(self, "Kein Passwort", "Bitte geben Sie das aktuelle Passwort ein.")
            return
        
        try:
            # Read the PDF with password
            pdf_reader = PdfReader(self.input_pdf_path)
            
            if pdf_reader.is_encrypted:
                if not pdf_reader.decrypt(current_password):
                    QMessageBox.warning(self, "Falsches Passwort", "Das eingegebene Passwort ist falsch.")
                    return
            
            pdf_writer = PdfWriter()
            
            # Copy all pages
            for page in pdf_reader.pages:
                pdf_writer.add_page(page)
            
            # Save without password
            base_name = os.path.splitext(self.input_pdf_path)[0]
            output_path = f"{base_name}_ungeschützt.pdf"
            
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", 
                                   f"Passwort wurde entfernt und PDF als '{os.path.basename(output_path)}' gespeichert.")
            self.status_label.setText("Passwort erfolgreich entfernt.")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Entfernen des Passworts: {str(e)}")
            self.status_label.setText("Fehler beim Entfernen des Passworts.") 