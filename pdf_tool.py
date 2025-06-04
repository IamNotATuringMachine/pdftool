import tkinter as tk
from tkinter import ttk # Keep ttk for Notebook
# from tkinter import filedialog, messagebox # No longer directly used in PDFToolApp
# from PyPDF2 import PdfReader # No longer directly used in PDFToolApp
# from PIL import Image, UnidentifiedImageError, ImageSequence # No longer directly used
# import os # No longer directly used in PDFToolApp
from tkinterdnd2 import TkinterDnD # TkinterDnD.Tk() is used at the end

# --- Library Imports for specific conversions (Most are now in ConvertTab or other tabs) ---
from pillow_heif import register_heif_opener # Call once at app start

# --- Custom Module Imports ---
from gui.merge_tab import MergeTab
from gui.split_tab import SplitTab
from gui.delete_tab import DeleteTab
from gui.convert_tab import ConvertTab # Import ConvertTab
# No utils needed directly in PDFToolApp anymore
# --- End Custom Module Imports ---

# --- pillow-heif Import and registration ---
register_heif_opener() # Call once to enable HEIC/HEIF support in Pillow
# --- End pillow-heif ---

# --- Constants formerly in PDFToolApp are now moved to gui.convert_tab or utils.constants ---
# All constants like SUPPORTED_FILE_TYPES, IMAGE_EXTENSIONS, etc., are removed from here.

class PDFToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF & Datei Werkzeug")
        self.root.geometry("800x600")

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Instantiate and add tabs
        self.merge_tab_instance = MergeTab(self.notebook, self.root)
        self.notebook.add(self.merge_tab_instance.get_frame(), text='PDFs zusammenführen')

        self.split_tab_instance = SplitTab(self.notebook, self.root)
        self.notebook.add(self.split_tab_instance.get_frame(), text='PDF Seiten extrahieren')

        self.delete_tab_instance = DeleteTab(self.notebook, self.root)
        self.notebook.add(self.delete_tab_instance.get_frame(), text='PDF Seiten löschen')

        self.convert_tab_instance = ConvertTab(self.notebook, self.root) # Instantiate ConvertTab
        self.notebook.add(self.convert_tab_instance.get_frame(), text='Dateien zu PDF konvertieren') # Add ConvertTab's frame

        # All attributes related to specific tabs (e.g., self.selected_files_for_conversion, 
        # self.split_input_pdf_path, etc.) have been moved to their respective tab classes.

    # All methods related to merge, split, delete, and convert functionalities
    # (e.g., _create_merge_widgets, _execute_split_pdf, _add_image_to_pdf, etc.)
    # have been moved to their respective tab classes (MergeTab, SplitTab, DeleteTab, ConvertTab)
    # or to helper modules (e.g., utils.common_helpers).
    # PDFToolApp is now primarily responsible for creating the main window,
    # the notebook, and instantiating the tab handler classes.

# Main application setup - This is the end of the PDFToolApp class.
# The following lines are OUTSIDE the class.
if __name__ == "__main__":
    root = TkinterDnD.Tk() # Use TkinterDnD Tk object for drag & drop
    app = PDFToolApp(root)
    root.mainloop() 