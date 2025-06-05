import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout,
    QFileIconProvider, QApplication, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize, QFileInfo
from PySide6.QtGui import QIcon, QPixmap

# Import constants for file extensions
from utils.constants import IMAGE_EXTENSIONS

class RecentFilesWidget(QWidget):

    def __init__(self, parent=None, console_output=None):
        super().__init__(parent)
        self.setObjectName("RecentFilesWidget")
        self.main_window = parent
        self.preview_size = QSize(64, 64)
        
        # Use a QVBoxLayout to enforce a fixed split
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # --- Recently Used Files Section ---
        # Container for the recent files section (list and label)
        self.recent_files_container = QWidget()
        recent_files_layout = QVBoxLayout(self.recent_files_container)
        recent_files_layout.setContentsMargins(0, 0, 0, 0)
        
        recent_files_label = QLabel("Zuletzt verwendet")
        recent_files_label.setStyleSheet("font-weight: bold;")
        recent_files_layout.addWidget(recent_files_label)

        self.recent_files_list = QListWidget()
        self.recent_files_list.itemDoubleClicked.connect(self._recent_file_double_clicked)
        self.recent_files_list.setDragEnabled(True)
        self.recent_files_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        recent_files_layout.addWidget(self.recent_files_list)
        
        # Add the container to the main layout
        self.layout.addWidget(self.recent_files_container)

        # --- Console Section ---
        if console_output:
            # Container for the console section (widget and label)
            self.console_container = QWidget()
            console_layout = QVBoxLayout(self.console_container)
            console_layout.setContentsMargins(0, 5, 0, 0)
            
            console_label = QLabel("Aktivitäten")
            console_label.setStyleSheet("font-weight: bold;")
            console_layout.addWidget(console_label)
            
            console_layout.addWidget(console_output)
            
            # Add the container to the main layout
            self.layout.addWidget(self.console_container)

            # Set stretch factors to create a fixed 50/50 split
            self.layout.setStretchFactor(self.recent_files_container, 1)
            self.layout.setStretchFactor(self.console_container, 1)

    def update_recent_files(self, recent_files_list):
        """Update the recent files list widget"""
        self.recent_files_list.clear()
        for file_path in recent_files_list:
            if os.path.exists(file_path):
                file_name = os.path.basename(file_path)
                item = QListWidgetItem(f"{file_name}\n{file_path}")
                item.setToolTip(file_path)
                
                # Set icon for the file
                icon = self._get_q_icon_for_file(file_path)
                item.setIcon(icon)
                
                # Store the full path in user data for easy access
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                self.recent_files_list.addItem(item)
        
        # Log the update
        if hasattr(self.main_window, 'log_message'):
            count = len(recent_files_list)
            self.main_window.log_message(f"Liste der zuletzt verwendeten Dateien aktualisiert: {count} Dateien")

    def _recent_file_double_clicked(self, item):
        """Handle double click on recent file item - opens the file"""
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                try:
                    # Open the file with the default system application
                    os.startfile(file_path)
                    if hasattr(self.main_window, 'log_message'):
                        self.main_window.log_message(f"Datei aus zuletzt verwendet geöffnet: {filename}")
                except Exception as e:
                    if hasattr(self.main_window, 'log_message'):
                        self.main_window.log_message(f"Fehler beim Öffnen von '{filename}': {e}")
                    QMessageBox.warning(self, "Datei öffnen Fehler", 
                                        f"Die Datei '{filename}' konnte nicht geöffnet werden.\nFehler: {e}")
            else:
                # File doesn't exist anymore, remove it from the list
                self.recent_files_list.takeItem(self.recent_files_list.row(item))
                if hasattr(self.main_window, 'log_message'):
                    self.main_window.log_message(f"Nicht existierende Datei aus zuletzt verwendet entfernt: {file_path}")

    def _get_q_icon_for_file(self, file_path):
        """Get an appropriate icon for the file, similar to FileProcessingTab implementation"""
        file_info = QFileInfo(file_path)
        icon_provider = QFileIconProvider()
        icon = icon_provider.icon(file_info)
        if icon.isNull():  # Fallback if system icon is not good
            # Attempt to create a basic pixmap if it's an image, or generic file icon
            ext = file_info.suffix().lower()
            if ext in IMAGE_EXTENSIONS:
                try:
                    pixmap = QPixmap(file_path)
                    if not pixmap.isNull():
                        return QIcon(pixmap.scaled(self.preview_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                except Exception:
                    pass  # Ignore if pixmap creation fails
            return QApplication.style().standardIcon(QApplication.Style.StandardPixmap.SP_FileIcon)
        return icon 