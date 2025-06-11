import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QHBoxLayout,
    QFileIconProvider, QApplication, QMessageBox, QMenu
)
from PySide6.QtCore import Qt, Signal, QSize, QFileInfo
from PySide6.QtGui import QIcon, QPixmap, QActionGroup

# Import constants for file extensions
from utils.constants import IMAGE_EXTENSIONS

class RecentFilesWidget(QWidget):

    def __init__(self, parent=None, console_output=None):
        super().__init__(parent)
        self.setObjectName("RecentFilesWidget")
        self.main_window = parent
        self.preview_size = QSize(64, 64)
        
        # Data and state
        self.all_files_info = []
        self.file_types = set()
        self.current_sort_by = "Änderungsdatum"
        self.current_filter_by = "Alle Typen"
        
        # Use a QVBoxLayout to enforce a fixed split
        self.layout = QVBoxLayout(self)
        # Remove margins since the widget is now wrapped in a container with margins
        self.layout.setContentsMargins(0, 0, 0, 0)
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
        self.recent_files_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.recent_files_list.customContextMenuRequested.connect(self.show_context_menu)
        recent_files_layout.addWidget(self.recent_files_list)
        
        # Add the container to the main layout
        self.layout.addWidget(self.recent_files_container)

        # --- Console Section ---
        if console_output:
            # Container for the console section (widget and label)
            self.console_container = QWidget()
            console_layout = QVBoxLayout(self.console_container)
            console_layout.setContentsMargins(0, 0, 0, 0)
            
            console_label = QLabel("Aktivitäten")
            console_label.setStyleSheet("font-weight: bold;")
            console_layout.addWidget(console_label)
            
            console_layout.addWidget(console_output)
            
            # Add the container to the main layout
            self.layout.addWidget(self.console_container)

            # Set stretch factors to create a fixed 50/50 split
            self.layout.setStretchFactor(self.recent_files_container, 1)
            self.layout.setStretchFactor(self.console_container, 1)

    def show_context_menu(self, position):
        """Create and show the context menu for sorting and filtering."""
        menu = QMenu(self)
        
        # --- Sort Menu ---
        sort_menu = menu.addMenu("Sortieren nach")
        sort_group = QActionGroup(self)
        sort_options = ["Änderungsdatum", "Dateityp", "Name"]
        for option in sort_options:
            action = sort_menu.addAction(option)
            action.setCheckable(True)
            if self.current_sort_by == option:
                action.setChecked(True)
            action.triggered.connect(lambda checked, opt=option: self._set_sort_option(opt))
            sort_group.addAction(action)

        # --- Filter Menu ---
        if self.file_types:
            menu.addSeparator()
            filter_menu = menu.addMenu("Filtern nach")
            filter_group = QActionGroup(self)
            
            filter_options = ["Alle Typen"] + sorted(list(self.file_types))
            for option in filter_options:
                action = filter_menu.addAction(option)
                action.setCheckable(True)
                if self.current_filter_by == option:
                    action.setChecked(True)
                action.triggered.connect(lambda checked, opt=option: self._set_filter_option(opt))
                filter_group.addAction(action)

        menu.exec(self.recent_files_list.mapToGlobal(position))

    def _set_sort_option(self, option):
        """Set the sorting option and update the display."""
        if self.current_sort_by != option:
            self.current_sort_by = option
            self._update_display()

    def _set_filter_option(self, option):
        """Set the filtering option and update the display."""
        if self.current_filter_by != option:
            self.current_filter_by = option
            self._update_display()

    def update_recent_files(self, recent_files_list):
        """Update the internal list of files and then refresh the display."""
        self.all_files_info.clear()
        self.file_types.clear()

        for file_path in recent_files_list:
            if os.path.exists(file_path):
                file_info = {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "type": os.path.splitext(file_path)[1].lower() or "Sonstiges",
                    "mod_time": os.path.getmtime(file_path)
                }
                self.all_files_info.append(file_info)
                if file_info["type"]:
                    self.file_types.add(file_info["type"])
        
        self._update_display()
        
        if hasattr(self.main_window, 'log_message'):
            count = len(recent_files_list)
            self.main_window.log_message(f"Liste der zuletzt verwendeten Dateien aktualisiert: {count} Dateien")

    def _update_display(self):
        """Filter and sort files based on current settings, then update the list widget."""
        # Filter
        if self.current_filter_by == "Alle Typen":
            display_files = self.all_files_info[:]
        else:
            display_files = [f for f in self.all_files_info if f["type"] == self.current_filter_by]

        # Sort
        if self.current_sort_by == "Änderungsdatum":
            display_files.sort(key=lambda f: f["mod_time"], reverse=True)
        elif self.current_sort_by == "Dateityp":
            display_files.sort(key=lambda f: (f["type"], f["name"]))
        elif self.current_sort_by == "Name":
            display_files.sort(key=lambda f: f["name"])

        # Update widget
        self.recent_files_list.clear()
        for file_info in display_files:
            file_path = file_info["path"]
            file_name = file_info["name"]
            
            item = QListWidgetItem(f"{file_name}\n{file_path}")
            item.setToolTip(file_path)
            
            icon = self._get_q_icon_for_file(file_path)
            item.setIcon(icon)
            
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.recent_files_list.addItem(item)

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