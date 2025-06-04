import os
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
        
        # Start with a more Windows Explorer-like default
        self.current_root_path = QDir.rootPath()  # Shows drives on Windows
        self.current_recent_file_paths = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5) # Reduced margins
        self.layout.setSpacing(5) # Reduced spacing

        # --- Recently Used Files Section ---
        self.recent_files_header_layout = QHBoxLayout()
        self.recent_files_toggle_button = QPushButton("▼")
        self.recent_files_toggle_button.setMaximumWidth(25)
        self.recent_files_toggle_button.clicked.connect(self._toggle_recent_files)
        self.recent_files_header_layout.addWidget(self.recent_files_toggle_button)
        
        self.recent_files_label = QLabel("Zuletzt verwendet")
        self.recent_files_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        self.recent_files_header_layout.addWidget(self.recent_files_label)
        self.recent_files_header_layout.addStretch()
        
        self.layout.addLayout(self.recent_files_header_layout)

        # Container for recent files content
        self.recent_files_container = QWidget()
        self.recent_files_container_layout = QVBoxLayout(self.recent_files_container)
        self.recent_files_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.recent_files_list_view = QListView()
        self.recent_files_list_view.setFixedHeight(200) # Increased from 100 to 200 pixels
        self.recent_files_model = QStringListModel(self)
        self.recent_files_list_view.setModel(self.recent_files_model)
        self.recent_files_list_view.doubleClicked.connect(self._recent_file_double_clicked)
        self.recent_files_container_layout.addWidget(self.recent_files_list_view)
        
        self.layout.addWidget(self.recent_files_container)

        # --- Separator ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(separator)
        
        # --- Folder Navigation Section ---
        self.folder_nav_header_layout = QHBoxLayout()
        self.folder_nav_toggle_button = QPushButton("▼")
        self.folder_nav_toggle_button.setMaximumWidth(25)
        self.folder_nav_toggle_button.clicked.connect(self._toggle_folder_navigation)
        self.folder_nav_header_layout.addWidget(self.folder_nav_toggle_button)
        
        self.folder_nav_label = QLabel("Ordnernavigation")
        self.folder_nav_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        self.folder_nav_header_layout.addWidget(self.folder_nav_label)
        self.folder_nav_header_layout.addStretch()
        
        self.layout.addLayout(self.folder_nav_header_layout)

        # Container for folder navigation content
        self.folder_nav_container = QWidget()
        self.folder_nav_container_layout = QVBoxLayout(self.folder_nav_container)
        self.folder_nav_container_layout.setContentsMargins(0, 0, 0, 0)

        # Add quick access buttons for common Windows locations
        self.quick_access_layout = QHBoxLayout()
        
        # Common folders button
        self.documents_button = QPushButton("Dokumente")
        self.documents_button.clicked.connect(lambda: self._navigate_to_standard_location(QStandardPaths.StandardLocation.DocumentsLocation))
        self.quick_access_layout.addWidget(self.documents_button)
        
        self.downloads_button = QPushButton("Downloads")
        self.downloads_button.clicked.connect(lambda: self._navigate_to_standard_location(QStandardPaths.StandardLocation.DownloadLocation))
        self.quick_access_layout.addWidget(self.downloads_button)
        
        self.desktop_button = QPushButton("Desktop")
        self.desktop_button.clicked.connect(lambda: self._navigate_to_standard_location(QStandardPaths.StandardLocation.DesktopLocation))
        self.quick_access_layout.addWidget(self.desktop_button)
        
        self.folder_nav_container_layout.addLayout(self.quick_access_layout)

        # Custom folder selection button (for scans folder, etc.)
        self.select_folder_button = QPushButton("Anderen Ordner wählen...")
        self.select_folder_button.clicked.connect(self._select_root_folder)
        self.folder_nav_container_layout.addWidget(self.select_folder_button)

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

        # Expand to show user's home directory by default
        user_home = QDir.homePath()
        home_index = self.file_system_model.index(user_home)
        self.tree_view.scrollTo(home_index)
        self.tree_view.expand(home_index)

        self.folder_nav_container_layout.addWidget(self.tree_view)
        self.layout.addWidget(self.folder_nav_container)
        
        self.setLayout(self.layout)

    def _toggle_recent_files(self):
        """Toggle the visibility of the recent files section"""
        if self.recent_files_container.isVisible():
            self.recent_files_container.hide()
            self.recent_files_toggle_button.setText("►")
        else:
            self.recent_files_container.show()
            self.recent_files_toggle_button.setText("▼")

    def _toggle_folder_navigation(self):
        """Toggle the visibility of the folder navigation section"""
        if self.folder_nav_container.isVisible():
            self.folder_nav_container.hide()
            self.folder_nav_toggle_button.setText("►")
        else:
            self.folder_nav_container.show()
            self.folder_nav_toggle_button.setText("▼")

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
                print(f"Navigated to standard location: {location_path}")
            else:
                QMessageBox.warning(self, "Ordner nicht gefunden", 
                                    f"Der Standardordner konnte nicht gefunden werden.")
        except Exception as e:
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
            print(f"Navigated to custom folder: {new_path}")

    def _tree_item_double_clicked(self, index):
        file_path = self.file_system_model.filePath(index)
        if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
            print(f"File double-clicked in explorer: {file_path}")
            self.file_selected_for_processing.emit(file_path)
        elif os.path.isdir(file_path):
            # For directories, expand/collapse them
            if self.tree_view.isExpanded(index):
                self.tree_view.collapse(index)
            else:
                self.tree_view.expand(index)

    def set_recent_files(self, file_paths_list: list):
        self.current_recent_file_paths = list(file_paths_list)
        display_names = [os.path.basename(p) for p in self.current_recent_file_paths]
        self.recent_files_model.setStringList(display_names)
        # print(f"Explorer updated with recent files: {display_names}")

    def _recent_file_double_clicked(self, index):
        row = index.row()
        if 0 <= row < len(self.current_recent_file_paths):
            file_path = self.current_recent_file_paths[row]
            if os.path.isfile(file_path):
                print(f"Recent file double-clicked: {file_path}")
                self.file_selected_for_processing.emit(file_path)
            else:
                QMessageBox.warning(self, "Datei nicht gefunden", 
                                    f"Die kürzlich verwendete Datei '{os.path.basename(file_path)}' wurde nicht gefunden.\nPfad: {file_path}")
                # Optionally, ask MainWindow to refresh/remove this missing recent file
        else:
            print(f"Invalid row index {row} from recent files list view.")

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