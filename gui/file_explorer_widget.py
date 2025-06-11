import os
import platform
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTreeView, QListView, 
    QFileSystemModel, QFileDialog, QLabel, QFrame, QMessageBox,
    QHBoxLayout
)
from PySide6.QtCore import Qt, QDir, Signal, QStringListModel, QStandardPaths

class FileExplorerWidget(QWidget):
    file_selected_for_processing = Signal(str) # Signal to emit when a file is selected/double-clicked for processing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileExplorerWidget") # For styling if needed
        self.main_window = parent  # Store reference to main window for logging
        
        # Start with a more Windows Explorer-like default
        self.current_root_path = QDir.rootPath()  # Shows drives on Windows

        self.layout = QVBoxLayout(self)
        # Remove internal margins since the widget is wrapped in a container with margins
        self.layout.setContentsMargins(0, 0, 0, 0) 
        self.layout.setSpacing(5) # Reduced spacing


        
        # --- Folder Navigation Section ---
        self.folder_nav_header_layout = QHBoxLayout()
        # self.folder_nav_toggle_button = QPushButton("▼") # Removed toggle button
        # self.folder_nav_toggle_button.setMaximumWidth(25)
        # self.folder_nav_toggle_button.clicked.connect(self._toggle_folder_navigation)
        # self.folder_nav_header_layout.addWidget(self.folder_nav_toggle_button)
        
        self.folder_nav_label = QLabel("Ordnernavigation")
        self.folder_nav_label.setStyleSheet("font-weight: bold;")
        self.folder_nav_header_layout.addWidget(self.folder_nav_label)
        self.folder_nav_header_layout.addStretch()
        
        self.layout.addLayout(self.folder_nav_header_layout)

        # Container for folder navigation content
        self.folder_nav_container = QWidget()
        self.folder_nav_container_layout = QVBoxLayout(self.folder_nav_container)
        self.folder_nav_container_layout.setContentsMargins(0, 0, 0, 0)

        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True) # Hide column headers like 'Name', 'Size', etc.
        self.file_system_model = QFileSystemModel()
        
        # Configure the model to show a Windows Explorer-like view
        self.file_system_model.setRootPath("")  # Empty string shows all drives on Windows
        
        # Show all files and folders initially (we'll filter in the view)
        self.file_system_model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.AllDirs | QDir.Filter.Files)
        
        # Set name filters for PDF files, but allow navigation through directories
        self.file_system_model.setNameFilterDisables(False)
        self.file_system_model.setNameFilters(["*"])  # Show all files initially
        
        self.tree_view.setModel(self.file_system_model)
        
        # Set root to show drives/computer on Windows, or filesystem root on other systems
        if os.name == 'nt':  # Windows
            # Show "This PC" equivalent (all drives)
            self.tree_view.setRootIndex(self.file_system_model.index(""))
        else:
            # On Linux/Mac, show filesystem root
            self.tree_view.setRootIndex(self.file_system_model.index("/"))

        # Hide all columns except for the name column (index 0)
        for i in range(1, self.file_system_model.columnCount()):
            self.tree_view.setColumnHidden(i, True)

        # Enable drag functionality
        self.tree_view.setDragEnabled(True)
        self.tree_view.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)

        # Connect double click to a handler
        self.tree_view.doubleClicked.connect(self._tree_item_double_clicked)
        self.tree_view.clicked.connect(self._tree_item_clicked)

        # Expand to show user's home directory by default
        user_home = QDir.homePath()
        home_index = self.file_system_model.index(user_home)
        self.tree_view.scrollTo(home_index)
        self.tree_view.expand(home_index)

        self.folder_nav_container_layout.addWidget(self.tree_view)
        self.layout.addWidget(self.folder_nav_container)
        
        self.setLayout(self.layout)



    def _navigate_to_standard_location(self, location_type):
        """Navigate to a standard Windows location like Documents, Downloads, etc."""
        try:
            location_path = QStandardPaths.writableLocation(location_type)
            if location_path and os.path.exists(location_path):
                # Expand and scroll to the location
                location_index = self.file_system_model.index(location_path)
                self.tree_view.scrollTo(location_index)
                self.tree_view.expand(location_index)
                self.tree_view.setCurrentIndex(location_index)
                
                # Log the navigation
                folder_name = os.path.basename(location_path) or location_path
                # if hasattr(self.main_window, 'log_message'):
                #     self.main_window.log_message(f"Navigiert zu: {folder_name}")
            else:
                if hasattr(self.main_window, 'log_message'):
                    self.main_window.log_message("Fehler: Standardordner nicht gefunden")
                QMessageBox.warning(self, "Ordner nicht gefunden", 
                                    f"Der Standardordner konnte nicht gefunden werden.")
        except Exception as e:
            if hasattr(self.main_window, 'log_message'):
                self.main_window.log_message(f"Navigationsfehler: {str(e)}")
            QMessageBox.warning(self, "Navigationsfehler", 
                                f"Fehler beim Navigieren zum Ordner: {e}")

    def _select_root_folder(self):
        """Allow user to select a custom folder (like the scans folder)"""
        new_path = QFileDialog.getExistingDirectory(
            self, 
            "Wähle einen Ordner aus",
            QDir.homePath()
        )
        if new_path:
            # Navigate to the selected folder
            folder_index = self.file_system_model.index(new_path)
            self.tree_view.scrollTo(folder_index)
            self.tree_view.expand(folder_index)
            self.tree_view.setCurrentIndex(folder_index)
            
            # Log the navigation
            folder_name = os.path.basename(new_path) or new_path
            # if hasattr(self.main_window, 'log_message'):
            #     self.main_window.log_message(f"Benutzerdefinierten Ordner ausgewählt: {folder_name}")

    def _tree_item_clicked(self, index):
        """Handle single-click on a tree item."""
        if self.file_system_model.isDir(index):
            # For directories, expand/collapse them on single click
            folder_name = self.file_system_model.fileName(index)
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
                # if hasattr(self.main_window, 'log_message'):
                #     self.main_window.log_message(f"Ordner eingeklappt: {folder_name}")
            else:
                self.tree_view.expand(index)
                # if hasattr(self.main_window, 'log_message'):
                #     self.main_window.log_message(f"Ordner aufgeklappt: {folder_name}")

    def _tree_item_double_clicked(self, index):
        file_path = self.file_system_model.filePath(index)
        if os.path.isfile(file_path):
            try:
                if platform.system() == "Windows":
                    os.startfile(os.path.abspath(file_path))
                elif platform.system() == "Darwin":
                    subprocess.run(["open", os.path.abspath(file_path)])
                else:
                    subprocess.run(["xdg-open", os.path.abspath(file_path)])
                
                filename = os.path.basename(file_path)
                if hasattr(self.main_window, 'log_message'):
                    self.main_window.log_message(f"Datei geöffnet: {filename}")
            except Exception as e:
                filename = os.path.basename(file_path)
                if hasattr(self.main_window, 'log_message'):
                    self.main_window.log_message(f"Fehler beim Öffnen von '{filename}': {e}")
                QMessageBox.warning(self, "Datei öffnen Fehler", f"Die Datei '{file_path}' konnte nicht geöffnet werden.\\nFehler: {e}")
        elif os.path.isdir(file_path):
            # Double-clicking a directory now does nothing, as single-click handles expansion
            pass



    # Further methods for drag/drop will be added here
    # and for populating recent files.

if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    explorer = FileExplorerWidget()
    explorer.setWindowTitle("File Explorer Test")
    explorer.setGeometry(100, 100, 300, 500)
    explorer.show()
    sys.exit(app.exec()) 