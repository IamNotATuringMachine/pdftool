import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QGroupBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt
from PyPDF2 import PdfReader

class PDFEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einzelne PDF bearbeiten")
        self.setModal(True)
        self.resize(600, 400)
        
        # Remove minimize button and set window flags for rounded corners
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.CustomizeWindowHint)
        
        self.input_pdf_path = None
        self.pdf_reader = None
        
        self._init_ui()
    
    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        
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
        
        # PDF Info
        self.info_group = QGroupBox("PDF-Informationen")
        info_layout = QVBoxLayout(self.info_group)
        
        self.info_label = QLabel("Wählen Sie eine PDF-Datei aus, um Informationen anzuzeigen.")
        info_layout.addWidget(self.info_label)
        
        main_layout.addWidget(self.info_group)
        
        # Pages List
        self.pages_group = QGroupBox("Seiten-Übersicht")
        pages_layout = QVBoxLayout(self.pages_group)
        
        self.pages_list = QListWidget()
        pages_layout.addWidget(self.pages_list)
        
        main_layout.addWidget(self.pages_group)
        
        # Action Buttons
        action_group = QGroupBox("Verfügbare Aktionen")
        action_layout = QVBoxLayout(action_group)
        
        self.extract_pages_button = QPushButton("Ausgewählte Seiten extrahieren")
        self.extract_pages_button.clicked.connect(self._extract_selected_pages)
        self.extract_pages_button.setEnabled(False)
        action_layout.addWidget(self.extract_pages_button)
        
        self.split_pdf_button = QPushButton("PDF in einzelne Seiten aufteilen")
        self.split_pdf_button.clicked.connect(self._split_pdf)
        self.split_pdf_button.setEnabled(False)
        action_layout.addWidget(self.split_pdf_button)
        
        main_layout.addWidget(action_group)
        
        # Close Button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Schließen")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        main_layout.addLayout(button_layout)
        
        # Status Label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
    
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
            self._load_pdf_info()
    
    def _load_pdf_info(self):
        if not self.input_pdf_path:
            return
        
        try:
            self.pdf_reader = PdfReader(self.input_pdf_path)
            
            # Check if PDF is encrypted
            if self.pdf_reader.is_encrypted:
                password, ok = QMessageBox.getText(self, "Passwort erforderlich", 
                                                  "Diese PDF ist passwortgeschützt. Bitte geben Sie das Passwort ein:",
                                                  echo=QMessageBox.EchoMode.Password)
                if ok and password:
                    if not self.pdf_reader.decrypt(password):
                        QMessageBox.warning(self, "Falsches Passwort", "Das eingegebene Passwort ist falsch.")
                        return
                else:
                    return
            
            # Display PDF info
            num_pages = len(self.pdf_reader.pages)
            info_text = f"Anzahl Seiten: {num_pages}\n"
            info_text += f"Dateigröße: {self._get_file_size(self.input_pdf_path)}\n"
            
            # Try to get metadata
            try:
                metadata = self.pdf_reader.metadata
                if metadata:
                    if metadata.title:
                        info_text += f"Titel: {metadata.title}\n"
                    if metadata.author:
                        info_text += f"Autor: {metadata.author}\n"
                    if metadata.subject:
                        info_text += f"Betreff: {metadata.subject}\n"
            except:
                pass
            
            self.info_label.setText(info_text)
            
            # Populate pages list
            self.pages_list.clear()
            for i in range(num_pages):
                item = QListWidgetItem(f"Seite {i + 1}")
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.pages_list.addItem(item)
            
            # Enable action buttons
            self.extract_pages_button.setEnabled(True)
            self.split_pdf_button.setEnabled(True)
            
            self.status_label.setText(f"PDF geladen: {num_pages} Seiten")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden der PDF: {str(e)}")
            self.status_label.setText("Fehler beim Laden der PDF.")
    
    def _get_file_size(self, file_path):
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _extract_selected_pages(self):
        if not self.pdf_reader:
            return
        
        selected_items = self.pages_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Keine Auswahl", "Bitte wählen Sie mindestens eine Seite aus.")
            return
        
        # Ask for output file
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Extrahierte Seiten speichern als",
            os.path.splitext(self.input_pdf_path)[0] + "_extrahiert.pdf",
            "PDF-Dateien (*.pdf)"
        )
        
        if not output_path:
            return
        
        try:
            from PyPDF2 import PdfWriter
            
            pdf_writer = PdfWriter()
            
            # Add selected pages
            for item in selected_items:
                page_index = item.data(Qt.ItemDataRole.UserRole)
                pdf_writer.add_page(self.pdf_reader.pages[page_index])
            
            # Write to file
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", 
                                   f"Ausgewählte Seiten wurden als '{os.path.basename(output_path)}' gespeichert.")
            self.status_label.setText(f"{len(selected_items)} Seite(n) extrahiert.")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Extrahieren der Seiten: {str(e)}")
            self.status_label.setText("Fehler beim Extrahieren.")
    
    def _split_pdf(self):
        if not self.pdf_reader:
            return
        
        # Ask for output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Ausgabeordner für aufgeteilte PDF-Seiten auswählen"
        )
        
        if not output_dir:
            return
        
        try:
            from PyPDF2 import PdfWriter
            
            base_name = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
            
            for i, page in enumerate(self.pdf_reader.pages):
                pdf_writer = PdfWriter()
                pdf_writer.add_page(page)
                
                output_path = os.path.join(output_dir, f"{base_name}_Seite_{i + 1}.pdf")
                
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            QMessageBox.information(self, "Erfolg", 
                                   f"PDF wurde in {len(self.pdf_reader.pages)} einzelne Dateien aufgeteilt.")
            self.status_label.setText(f"PDF in {len(self.pdf_reader.pages)} Dateien aufgeteilt.")
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Aufteilen der PDF: {str(e)}")
            self.status_label.setText("Fehler beim Aufteilen.")
    
    def update_theme(self, theme_name):
        """Update the dialog's theme to match the application theme."""
        if theme_name == "dark":
            bg_color = "#3F4042"
            text_color = "#CCCCCC"
            border_color = "#555559"
            input_bg_color = "#2b2b2b"
            input_text_color = "#CCCCCC"
            placeholder_color = "#888888"
        else:
            bg_color = "#FFFFFF"
            text_color = "#333333"
            border_color = "#D0D0D0"
            input_bg_color = "#FFFFFF"
            input_text_color = "#333333"
            placeholder_color = "#999999"
        
        # Apply styling to this dialog
        self.setStyleSheet(f"""
            QDialog {{
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
            QListWidget {{
                background-color: {input_bg_color};
                color: {input_text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                selection-background-color: #0078D4;
                selection-color: white;
            }}
            QLabel {{
                color: {text_color};
            }}
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: {border_color};
            }}
            QPushButton:pressed {{
                background-color: {placeholder_color};
            }}
            QPushButton:disabled {{
                background-color: {bg_color};
                color: {placeholder_color};
                border: 1px solid {placeholder_color};
            }}
        """) 