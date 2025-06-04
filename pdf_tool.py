import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfWriter, PdfReader # Added PdfReader
from PIL import Image, UnidentifiedImageError, ImageSequence # Added ImageSequence for GIFs
import os # For path manipulations
from tkinterdnd2 import DND_FILES, TkinterDnD # Added for Drag and Drop
# Placeholder for new imports - will be added as converters are implemented
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import letter, A4
# from reportlab.lib.utils import ImageReader
# import python_docx
# import openpyxl
# import python_pptx
# import odfpy
from xhtml2pdf import pisa
from svglib.svglib import svg2rlg
# from reportlab.graphics import renderPDF
from pillow_heif import register_heif_opener
from striprtf.striprtf import rtf_to_text # Import for RTF processing
# from email import message_from_string
import io # For BytesIO, used with xhtml2pdf
import tempfile # For temporary files if needed for merging

# --- pillow-heif Import and registration ---
register_heif_opener() # Call once to enable HEIC/HEIF support in Pillow
# --- End pillow-heif --- 

# Define supported file types for the new converter
SUPPORTED_FILE_TYPES = [
    ("Word-Dokumente", "*.doc *.docx"),
    ("Excel-Tabellen", "*.xls *.xlsx"),
    ("PowerPoint-Präsentationen", "*.ppt *.pptx"),
    ("JPEG-Bilder", "*.jpg *.jpeg"),
    ("PNG-Bilder", "*.png"),
    ("GIF-Bilder", "*.gif"),
    ("TIFF-Bilder", "*.tif *.tiff"),
    ("BMP-Bilder", "*.bmp"),
    ("HEIC/HEIF-Bilder", "*.heic *.heif"),
    ("SVG-Vektorgrafiken", "*.svg"),
    ("Textdateien", "*.txt"),
    ("Rich Text Format", "*.rtf"),
    ("OpenDocument Text", "*.odt"),
    ("OpenDocument Spreadsheet", "*.ods"),
    ("OpenDocument Presentation", "*.odp"),
    ("HTML-Dateien", "*.html *.htm"),
    ("Publisher-Dateien", "*.pub"),
    ("Visio-Dateien", "*.vsd *.vsdx"),
    ("E-Mail-Dateien", "*.eml *.msg"),
    ("Alle Dateien", "*.*")
]

# Define actually implemented and supported file types
ACTUALLY_SUPPORTED_FILE_TYPES = [
    ("Bilder", "JPEG (*.jpg, *.jpeg), PNG (*.png), BMP (*.bmp), GIF (*.gif), TIFF (*.tif, *.tiff), HEIC/HEIF (*.heic, *.heif)"),
    ("Textdateien", "Einfacher Text (*.txt)"),
    ("Rich Text Format", "RTF (*.rtf)"),
    ("HTML-Dateien", "HTML (*.html, *.htm)"),
    ("Vektorgrafiken", "SVG (*.svg)")
]

# Combine into a flat list for filedialog
ALL_SUPPORTED_EXTENSIONS_DESC = "Alle unterstützten Dateien"
ALL_SUPPORTED_EXTENSIONS_PATTERNS = "*.doc *.docx *.xls *.xlsx *.ppt *.pptx *.jpg *.jpeg *.png *.gif *.tif *.tiff *.bmp *.heic *.heif *.svg *.txt *.rtf *.odt *.ods *.odp *.html *.htm *.pub *.vsd *.vsdx *.eml *.msg"
# Create a tuple for filetypes dialog
FILETYPES_FOR_DIALOG = [(ALL_SUPPORTED_EXTENSIONS_DESC, ALL_SUPPORTED_EXTENSIONS_PATTERNS)] + SUPPORTED_FILE_TYPES

# --- ReportLab Imports ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4 # Using A4 by default
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet # For Paragraph, if used later
from reportlab.platypus import Paragraph # For more advanced text layout, if used later
# --- End ReportLab Imports ---

# For drag and drop validation (flat list of lowercased extensions with dot)
ALL_SUPPORTED_EXT_PATTERNS_LIST = [
    item.replace("*","") for sublist in FILETYPES_FOR_DIALOG[:-1] # Exclude "Alle Dateien *.*"
    for item in sublist[1].split()
]

# Define supported file types for the new converter
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".heic", ".heif"]
TEXT_EXTENSIONS = [".txt"] # Defined TEXT_EXTENSIONS
RTF_EXTENSIONS = [".rtf"] # Defined RTF_EXTENSIONS
HTML_EXTENSIONS = [".html", ".htm"]
SVG_EXTENSIONS = [".svg"] # Defined SVG_EXTENSIONS
# ... (other extension lists)

# Update FILETYPES_FOR_DIALOG and ALL_SUPPORTED_EXT_PATTERNS_LIST accordingly.
# The global ALL_SUPPORTED_EXTENSIONS_PATTERNS and FILETYPES_FOR_DIALOG near the top of the file
# will need to be regenerated or manually updated if they are static. 
# Assuming they are built from these lists or need manual update.

class PDFToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF & Datei Werkzeug") # Updated title
        self.root.geometry("800x600")

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create frames for each functionality
        self.merge_frame = ttk.Frame(self.notebook)
        self.split_frame = ttk.Frame(self.notebook)
        self.delete_frame = ttk.Frame(self.notebook)
        self.file_to_pdf_frame = ttk.Frame(self.notebook) # Renamed

        self.notebook.add(self.merge_frame, text='PDFs zusammenführen') # Translated
        self.notebook.add(self.split_frame, text='PDF Seiten extrahieren') # Translated
        self.notebook.add(self.delete_frame, text='PDF Seiten löschen') # Translated
        self.notebook.add(self.file_to_pdf_frame, text='Dateien zu PDF konvertieren') # Renamed tab text

        self.selected_merge_files = []
        self.split_input_pdf_path = None # To store path of PDF for splitting
        self.delete_input_pdf_path = None # To store path of PDF for page deletion
        self.selected_files_for_conversion = [] # Renamed

        self._create_merge_widgets()
        self._create_split_widgets()
        self._create_delete_widgets()
        self._create_file_to_pdf_widgets() # Renamed method call

    def _create_merge_widgets(self):
        # Frame for file list and controls
        controls_frame = ttk.LabelFrame(self.merge_frame, text="Dateien zum Zusammenführen") # Translated
        controls_frame.pack(padx=10, pady=10, fill="x")

        # Listbox to display selected files
        self.merge_listbox = tk.Listbox(controls_frame, selectmode=tk.SINGLE, height=10)
        self.merge_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)

        # Scrollbar for the listbox
        scrollbar = ttk.Scrollbar(controls_frame, orient="vertical", command=self.merge_listbox.yview)
        scrollbar.pack(side=tk.LEFT, fill="y", pady=5)
        self.merge_listbox.config(yscrollcommand=scrollbar.set)

        # Frame for buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.LEFT, fill="y", padx=5)

        add_button = ttk.Button(buttons_frame, text="PDF hinzufügen", command=self._add_pdf_to_merge_list) # Translated
        add_button.pack(fill="x", pady=2)

        remove_button = ttk.Button(buttons_frame, text="Auswahl entfernen", command=self._remove_pdf_from_merge_list) # Translated
        remove_button.pack(fill="x", pady=2)

        move_up_button = ttk.Button(buttons_frame, text="Nach oben", command=self._move_merge_item_up) # Translated
        move_up_button.pack(fill="x", pady=2)

        move_down_button = ttk.Button(buttons_frame, text="Nach unten", command=self._move_merge_item_down) # Translated
        move_down_button.pack(fill="x", pady=2)
        
        # Register merge_listbox for drag and drop
        self.merge_listbox.drop_target_register(DND_FILES)
        self.merge_listbox.dnd_bind('<<Drop>>', self._handle_merge_drop)
        
        # Merge button and status
        action_frame = ttk.Frame(self.merge_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        merge_button = ttk.Button(action_frame, text="PDFs zusammenführen und speichern", command=self._execute_merge_pdfs) # Translated
        merge_button.pack(pady=5)

        self.merge_status_label = ttk.Label(action_frame, text="")
        self.merge_status_label.pack(pady=5)

    def _add_pdf_to_merge_list(self):
        files = filedialog.askopenfilenames(
            title="PDF-Dateien auswählen", # Translated
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")) # Translated
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_merge_files:
                    self.selected_merge_files.append(file_path)
                    self.merge_listbox.insert(tk.END, os.path.basename(file_path))
            self.merge_status_label.config(text=f"{len(files)} Datei(en) hinzugefügt.") # Translated

    def _remove_pdf_from_merge_list(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            del self.selected_merge_files[index]
            self.merge_listbox.delete(index)
            self.merge_status_label.config(text="Datei entfernt.") # Translated
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.") # Translated

    def _move_merge_item_up(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            if index > 0:
                self.selected_merge_files[index], self.selected_merge_files[index-1] = self.selected_merge_files[index-1], self.selected_merge_files[index]
                text = self.merge_listbox.get(index)
                self.merge_listbox.delete(index)
                self.merge_listbox.insert(index-1, text)
                self.merge_listbox.selection_set(index-1)
                self.merge_status_label.config(text="Datei nach oben verschoben.") # Translated
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.") # Translated

    def _move_merge_item_down(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            if index < self.merge_listbox.size() - 1:
                self.selected_merge_files[index], self.selected_merge_files[index+1] = self.selected_merge_files[index+1], self.selected_merge_files[index]
                text = self.merge_listbox.get(index)
                self.merge_listbox.delete(index)
                self.merge_listbox.insert(index+1, text)
                self.merge_listbox.selection_set(index+1)
                self.merge_status_label.config(text="Datei nach unten verschoben.") # Translated
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.") # Translated

    def _execute_merge_pdfs(self):
        if not self.selected_merge_files or len(self.selected_merge_files) < 2:
            messagebox.showwarning("Nicht genügend Dateien", "Bitte wählen Sie mindestens zwei PDF-Dateien zum Zusammenführen aus.") # Translated
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")), # Translated
            title="Zusammengeführte PDF speichern unter" # Translated
        )

        if not output_filename:
            self.merge_status_label.config(text="Zusammenführen abgebrochen.") # Translated
            return

        pdf_writer = PdfWriter()
        
        try:
            self.merge_status_label.config(text="Führe PDFs zusammen...") # Translated
            self.root.update_idletasks() 

            for filename in self.selected_merge_files:
                pdf_writer.append(filename)
            
            with open(output_filename, 'wb') as out:
                pdf_writer.write(out)
            
            pdf_writer.close() 
            messagebox.showinfo("Erfolg", f"PDFs erfolgreich zusammengeführt in {os.path.basename(output_filename)}") # Translated
            self.merge_status_label.config(text="Zusammenführen erfolgreich!") # Translated
            self.selected_merge_files.clear()
            self.merge_listbox.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Fehler beim Zusammenführen", f"Ein Fehler ist aufgetreten: {e}") # Translated
            self.merge_status_label.config(text="Fehler beim Zusammenführen.") # Translated

    def _create_split_widgets(self):
        controls_frame = ttk.LabelFrame(self.split_frame, text="PDF auswählen und Seiten angeben") # Translated
        controls_frame.pack(padx=10, pady=10, fill="x")

        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="PDF auswählen", command=self._select_pdf_for_split) # Translated
        select_button.pack(side=tk.LEFT, padx=5)

        self.split_selected_file_label = ttk.Label(file_select_frame, text="Keine Datei ausgewählt.") # Translated
        self.split_selected_file_label.pack(side=tk.LEFT, padx=5)

        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Seiten/Bereiche (z.B. 1-3, 5, 7-9):") # Translated
        pages_label.pack(side=tk.LEFT, padx=5)

        self.split_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.split_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        action_frame = ttk.Frame(self.split_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        extract_button = ttk.Button(action_frame, text="Seiten extrahieren und speichern", command=self._execute_split_pdf) # Translated
        extract_button.pack(pady=5)

        self.split_status_label = ttk.Label(action_frame, text="")
        self.split_status_label.pack(pady=5)

    def _select_pdf_for_split(self):
        file_path = filedialog.askopenfilename(
            title="PDF-Datei auswählen", # Translated
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")) # Translated
        )
        if file_path:
            self.split_input_pdf_path = file_path
            self.split_selected_file_label.config(text=os.path.basename(file_path))
            self.split_status_label.config(text="Datei ausgewählt. Seitenbereiche eingeben.") # Translated
        else:
            self.split_input_pdf_path = None
            self.split_selected_file_label.config(text="Keine Datei ausgewählt.") # Translated
            self.split_status_label.config(text="Dateiauswahl abgebrochen.") # Translated

    def _parse_page_ranges(self, pages_str, total_pages):
        if not pages_str.strip():
            raise ValueError("Seitenbereichsangabe ist leer.") # Translated
        
        pages_to_extract = set()
        parts = pages_str.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                try:
                    start, end = map(int, part.split('-'))
                    if not (1 <= start <= end <= total_pages):
                        raise ValueError(f"Bereich '{part}' ist ungültig. Max. Seite: {total_pages}") # Translated
                    pages_to_extract.update(range(start - 1, end)) 
                except ValueError as e:
                    if "invalid literal" in str(e) or "ungültiges Literal" in str(e).lower(): # Added German variant
                         raise ValueError(f"Ungültiges Bereichsformat: '{part}'. Muss Zahlen enthalten.") # Translated
                    raise 
            else:
                try:
                    page_num = int(part)
                    if not (1 <= page_num <= total_pages):
                        raise ValueError(f"Seitenzahl '{part}' ist außerhalb des Bereichs. Max. Seite: {total_pages}") # Translated
                    pages_to_extract.add(page_num - 1) 
                except ValueError:
                    raise ValueError(f"Ungültige Seitenzahl: '{part}'. Muss eine Zahl sein.") # Translated
        
        if not pages_to_extract:
            raise ValueError("Keine gültigen Seiten für die Extraktion angegeben.") # Translated
            
        return sorted(list(pages_to_extract))

    def _execute_split_pdf(self):
        if not self.split_input_pdf_path:
            messagebox.showwarning("Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.") # Translated
            return

        pages_str = self.split_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("Keine Seiten angegeben", "Bitte geben Sie die zu extrahierenden Seitenzahlen oder Bereiche ein.") # Translated
            return

        try:
            input_pdf = PdfReader(self.split_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_extract = self._parse_page_ranges(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Ungültige Seiteneingabe", str(e)) # Translated
            self.split_status_label.config(text=f"Fehler: {e}") # Translated
            return
        except Exception as e: 
            messagebox.showerror("Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}") # Translated
            self.split_status_label.config(text="Fehler beim Lesen der PDF.") # Translated
            return

        if not pages_to_extract:
            messagebox.showinfo("Keine Seiten zu extrahieren", "Die angegebenen Seiten ergeben keine zu extrahierenden Seiten.") # Translated
            self.split_status_label.config(text="Keine Seiten zum Extrahieren basierend auf der Eingabe.") # Translated
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")), # Translated
            title="Extrahierte Seiten speichern unter", # Translated
            initialfile=f"{os.path.splitext(os.path.basename(self.split_input_pdf_path))[0]}_extrahiert.pdf" # Translated
        )

        if not output_filename:
            self.split_status_label.config(text="Extraktion abgebrochen.") # Translated
            return

        pdf_writer = PdfWriter()
        try:
            self.split_status_label.config(text="Extrahiere Seiten...") # Translated
            self.root.update_idletasks()

            for page_num in pages_to_extract:
                pdf_writer.add_page(input_pdf.pages[page_num])
            
            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Erfolg", f"Seiten erfolgreich extrahiert nach {os.path.basename(output_filename)}") # Translated
            self.split_status_label.config(text="Extraktion erfolgreich!") # Translated

        except Exception as e:
            messagebox.showerror("Fehler beim Extrahieren der Seiten", f"Ein Fehler ist aufgetreten: {e}") # Translated
            self.split_status_label.config(text="Fehler während der Extraktion.") # Translated

    def _create_delete_widgets(self):
        controls_frame = ttk.LabelFrame(self.delete_frame, text="PDF auswählen und zu löschende Seiten angeben") # Translated
        controls_frame.pack(padx=10, pady=10, fill="x")

        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="PDF auswählen", command=self._select_pdf_for_delete) # Translated
        select_button.pack(side=tk.LEFT, padx=5)

        self.delete_selected_file_label = ttk.Label(file_select_frame, text="Keine Datei ausgewählt.") # Translated
        self.delete_selected_file_label.pack(side=tk.LEFT, padx=5)

        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Zu löschende Seiten (z.B. 1, 3, 5-7):") # Translated
        pages_label.pack(side=tk.LEFT, padx=5)

        self.delete_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.delete_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        action_frame = ttk.Frame(self.delete_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        delete_button = ttk.Button(action_frame, text="Seiten löschen und speichern", command=self._execute_delete_pages) # Translated
        delete_button.pack(pady=5)

        self.delete_status_label = ttk.Label(action_frame, text="")
        self.delete_status_label.pack(pady=5)

    def _select_pdf_for_delete(self):
        file_path = filedialog.askopenfilename(
            title="PDF-Datei auswählen", # Translated
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")) # Translated
        )
        if file_path:
            self.delete_input_pdf_path = file_path
            self.delete_selected_file_label.config(text=os.path.basename(file_path))
            self.delete_status_label.config(text="Datei ausgewählt. Zu löschende Seiten eingeben.") # Translated
        else:
            self.delete_input_pdf_path = None
            self.delete_selected_file_label.config(text="Keine Datei ausgewählt.") # Translated
            self.delete_status_label.config(text="Dateiauswahl abgebrochen.") # Translated

    def _parse_pages_to_delete(self, pages_str, total_pages):
        return self._parse_page_ranges(pages_str, total_pages) 

    def _execute_delete_pages(self):
        if not self.delete_input_pdf_path:
            messagebox.showwarning("Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.") # Translated
            return

        pages_str = self.delete_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("Keine Seiten angegeben", "Bitte geben Sie die zu löschenden Seitenzahlen oder Bereiche ein.") # Translated
            return

        try:
            input_pdf = PdfReader(self.delete_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_delete_indices = self._parse_pages_to_delete(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Ungültige Seiteneingabe", str(e)) # Translated
            self.delete_status_label.config(text=f"Fehler: {e}") # Translated
            return
        except Exception as e: 
            messagebox.showerror("Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}") # Translated
            self.delete_status_label.config(text="Fehler beim Lesen der PDF.") # Translated
            return

        if not pages_to_delete_indices:
            messagebox.showinfo("Keine gültigen Seiten", "Keine gültigen Seiten zum Löschen angegeben.") # Translated
            self.delete_status_label.config(text="Keine gültigen Seiten zum Löschen.") # Translated
            return
        
        if all(p_idx in pages_to_delete_indices for p_idx in range(total_pages)):
            messagebox.showwarning("Alle Seiten ausgewählt", "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.") # Translated
            self.delete_status_label.config(text="Kann nicht alle Seiten löschen.") # Translated
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")), # Translated
            title="Geänderte PDF speichern unter", # Translated
            initialfile=f"{os.path.splitext(os.path.basename(self.delete_input_pdf_path))[0]}_geändert.pdf" # Translated
        )

        if not output_filename:
            self.delete_status_label.config(text="Löschen abgebrochen.") # Translated
            return

        pdf_writer = PdfWriter()
        try:
            self.delete_status_label.config(text="Lösche Seiten...") # Translated
            self.root.update_idletasks()

            for i in range(total_pages):
                if i not in pages_to_delete_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0:
                 messagebox.showwarning("Leeres Ergebnis", "Alle angegebenen Seiten wurden gelöscht, was zu einer leeren PDF führt. Datei nicht gespeichert.") # Translated
                 self.delete_status_label.config(text="Die resultierende PDF wäre leer. Vorgang abgebrochen.") # Translated
                 pdf_writer.close()
                 return

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Erfolg", f"Seiten erfolgreich gelöscht. Gespeichert unter {os.path.basename(output_filename)}") # Translated
            self.delete_status_label.config(text="Löschen erfolgreich!") # Translated

        except Exception as e:
            messagebox.showerror("Fehler beim Löschen der Seiten", f"Ein Fehler ist aufgetreten: {e}") # Translated
            self.delete_status_label.config(text="Fehler während des Löschens.") # Translated

    def _create_file_to_pdf_widgets(self): # Renamed method
        # Frame for file list and controls
        controls_frame = ttk.LabelFrame(self.file_to_pdf_frame, text="Dateien für Konvertierung") # Translated
        controls_frame.pack(padx=10, pady=10, fill="x")

        # Listbox to display selected files
        self.file_to_pdf_listbox = tk.Listbox(controls_frame, selectmode=tk.SINGLE, height=10) # Restored original height
        self.file_to_pdf_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)

        # Scrollbar for the listbox
        file_to_pdf_scrollbar = ttk.Scrollbar(controls_frame, orient="vertical", command=self.file_to_pdf_listbox.yview)
        file_to_pdf_scrollbar.pack(side=tk.LEFT, fill="y", pady=5)
        self.file_to_pdf_listbox.config(yscrollcommand=file_to_pdf_scrollbar.set)

        # Frame for buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.LEFT, fill="y", padx=5)

        add_button = ttk.Button(buttons_frame, text="Dateien hinzufügen", command=self._add_files_to_convert_list) # Renamed method & text
        add_button.pack(fill="x", pady=2)

        remove_button = ttk.Button(buttons_frame, text="Auswahl entfernen", command=self._remove_file_from_convert_list) # Renamed method
        remove_button.pack(fill="x", pady=2)

        move_up_button = ttk.Button(buttons_frame, text="Nach oben", command=self._move_convert_item_up) # Renamed method
        move_up_button.pack(fill="x", pady=2)

        move_down_button = ttk.Button(buttons_frame, text="Nach unten", command=self._move_convert_item_down) # Renamed method
        move_down_button.pack(fill="x", pady=2)
        
        # Register listbox for drag and drop
        self.file_to_pdf_listbox.drop_target_register(DND_FILES) # Renamed
        self.file_to_pdf_listbox.dnd_bind('<<Drop>>', self._handle_file_drop) # Renamed method
        
        # Convert button and status
        options_frame = ttk.Frame(self.file_to_pdf_frame) # Added options frame
        options_frame.pack(padx=10, pady=5, fill="x")

        self.single_pdf_output_var = tk.BooleanVar(value=True)
        single_pdf_output_check = ttk.Checkbutton(
            options_frame, 
            text="Alle Dateien in eine einzelne PDF-Datei zusammenfassen", 
            variable=self.single_pdf_output_var
        )
        single_pdf_output_check.pack(side=tk.LEFT, padx=5)

        action_frame = ttk.Frame(self.file_to_pdf_frame) # Renamed
        action_frame.pack(padx=10, pady=10, fill="x")

        convert_button = ttk.Button(action_frame, text="Ausgewählte Dateien zu PDF konvertieren und speichern", command=self._execute_file_to_pdf) # Renamed method & text
        convert_button.pack(pady=5)

        self.file_conversion_status_label = ttk.Label(action_frame, text="") # Renamed
        self.file_conversion_status_label.pack(pady=5)

    def _add_files_to_convert_list(self): # Renamed method
        files = filedialog.askopenfilenames(
            title="Dateien für Konvertierung auswählen", # Updated title
            filetypes=FILETYPES_FOR_DIALOG # Updated filetypes
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_files_for_conversion: # Renamed
                    self.selected_files_for_conversion.append(file_path) # Renamed
                    self.file_to_pdf_listbox.insert(tk.END, os.path.basename(file_path)) # Renamed
            self.file_conversion_status_label.config(text=f"{len(files)} Datei(en) hinzugefügt.") # Renamed

    def _remove_file_from_convert_list(self): # Renamed method
        selected_index = self.file_to_pdf_listbox.curselection() # Renamed
        if selected_index:
            index = selected_index[0]
            del self.selected_files_for_conversion[index] # Renamed
            self.file_to_pdf_listbox.delete(index) # Renamed
            self.file_conversion_status_label.config(text="Datei entfernt.") # Renamed
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.")

    def _move_convert_item_up(self): # Renamed method
        selected_index = self.file_to_pdf_listbox.curselection() # Renamed
        if selected_index:
            index = selected_index[0]
            if index > 0:
                # Swap in the main list
                self.selected_files_for_conversion[index], self.selected_files_for_conversion[index-1] = \
                    self.selected_files_for_conversion[index-1], self.selected_files_for_conversion[index]
                # Update listbox
                text = self.file_to_pdf_listbox.get(index) # Renamed
                self.file_to_pdf_listbox.delete(index) # Renamed
                self.file_to_pdf_listbox.insert(index-1, text) # Renamed
                self.file_to_pdf_listbox.selection_set(index-1) # Renamed
                self.file_conversion_status_label.config(text="Datei nach oben verschoben.") # Renamed
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _move_convert_item_down(self): # Renamed method
        selected_index = self.file_to_pdf_listbox.curselection() # Renamed
        if selected_index:
            index = selected_index[0]
            if index < self.file_to_pdf_listbox.size() - 1: # Renamed
                # Swap in the main list
                self.selected_files_for_conversion[index], self.selected_files_for_conversion[index+1] = \
                    self.selected_files_for_conversion[index+1], self.selected_files_for_conversion[index]
                # Update listbox
                text = self.file_to_pdf_listbox.get(index) # Renamed
                self.file_to_pdf_listbox.delete(index) # Renamed
                self.file_to_pdf_listbox.insert(index+1, text) # Renamed
                self.file_to_pdf_listbox.selection_set(index+1) # Renamed
                self.file_conversion_status_label.config(text="Datei nach unten verschoben.") # Renamed
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _parse_dropped_files(self, event_data):
        # event.data might be like: "{/path/to/file with spaces.pdf} {/another/path/file.jpg}"
        # Or on some systems, just a list of paths separated by spaces if they don't contain spaces themselves.
        # A more robust way is to look for "{" and "}"
        files = []
        if '{' in event_data and '}' in event_data:
            # Paths are enclosed in braces, possibly with spaces
            raw_paths = event_data.strip().split('} {')
            for raw_path in raw_paths:
                clean_path = raw_path.replace('{', '').replace('}', '').strip()
                if clean_path:
                    files.append(clean_path)
        else:
            # Assume space-separated paths (might fail for paths with spaces if not braced)
            # This is a fallback, TkinterDnD usually braces paths with spaces.
            files = [f for f in event_data.split(' ') if f]
        return files

    def _handle_merge_drop(self, event):
        dropped_files = self._parse_dropped_files(event.data)
        added_count = 0
        if dropped_files:
            for file_path in dropped_files:
                if file_path.lower().endswith(".pdf"):
                    if file_path not in self.selected_merge_files:
                        self.selected_merge_files.append(file_path)
                        self.merge_listbox.insert(tk.END, os.path.basename(file_path))
                        added_count += 1
            if added_count > 0:
                self.merge_status_label.config(text=f"{added_count} PDF-Datei(en) per Drag & Drop hinzugefügt.")
            else:
                self.merge_status_label.config(text="Keine neuen PDF-Dateien per Drag & Drop hinzugefügt.")
        else:
            self.merge_status_label.config(text="Keine Dateien im Drop-Event gefunden.")

    def _handle_file_drop(self, event): # Renamed method
        try:
            # Attempt to parse the dropped file paths
            dropped_files = self._parse_dropped_files(event.data)
            
            added_count = 0
            unsupported_files = []
            for file_path in dropped_files:
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_path.lower())
                    if ext in ALL_SUPPORTED_EXT_PATTERNS_LIST:
                        if file_path not in self.selected_files_for_conversion: 
                            self.selected_files_for_conversion.append(file_path) 
                            self.file_to_pdf_listbox.insert(tk.END, os.path.basename(file_path)) 
                            added_count += 1
                    else:
                        unsupported_files.append(os.path.basename(file_path))
                        
            if added_count > 0:
                status_msg = f"{added_count} Datei(en) per Drag & Drop hinzugefügt."
                if unsupported_files:
                    status_msg += f" Nicht unterstützte Dateien: {', '.join(unsupported_files)}"
                self.file_conversion_status_label.config(text=status_msg) 
            elif unsupported_files:
                 self.file_conversion_status_label.config(text=f"Keine unterstützten Dateien per Drag & Drop hinzugefügt. Nicht unterstützt: {', '.join(unsupported_files)}")
            elif not dropped_files: 
                 self.file_conversion_status_label.config(text="Keine gültigen Dateien im Drop gefunden.") 
                 
        except Exception as e:
            self.file_conversion_status_label.config(text="Fehler beim Drag & Drop.") # Renamed
            messagebox.showerror("Drag & Drop Fehler", f"Ein Fehler ist aufgetreten: {e}")

    def _execute_file_to_pdf(self):
        if not self.selected_files_for_conversion:
            messagebox.showwarning("Keine Dateien ausgewählt", "Bitte wählen Sie mindestens eine Datei für die Konvertierung aus.")
            return

        single_output_mode = self.single_pdf_output_var.get()
        output_final_pdf_path = None
        output_directory_for_multiple = None
        
        if single_output_mode:
            output_final_pdf_path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*"))
            )
            if not output_final_pdf_path:
                self.file_conversion_status_label.config(text="Konvertierung abgebrochen.")
                return
        else:
            output_directory_for_multiple = filedialog.askdirectory(title="Ordner für konvertierte PDFs auswählen")
            if not output_directory_for_multiple:
                self.file_conversion_status_label.config(text="Konvertierung abgebrochen.")
                return

        self.file_conversion_status_label.config(text="Konvertiere Dateien...")
        self.root.update_idletasks()

        files_processed_this_run = 0
        errors_occurred = []
        temp_files_to_merge_in_single_mode = []
        
        # Temporary canvas for ReportLab drawn content (images, text etc.) in single mode
        # This will be one of the PDFs to merge if single_output_mode is true and it has content.
        reportlab_canvas_content_temp_path = None
        shared_reportlab_canvas = None
        reportlab_canvas_has_content = False

        if single_output_mode:
            # Create a temporary file path for the canvas content
            fd, reportlab_canvas_content_temp_path = tempfile.mkstemp(suffix=".pdf", prefix="rl_canvas_")
            os.close(fd) # Close the file descriptor, Canvas will open it
            shared_reportlab_canvas = canvas.Canvas(reportlab_canvas_content_temp_path, pagesize=A4)
            shared_reportlab_canvas.setTitle("Canvas Content")

        try:
            for index, file_path in enumerate(self.selected_files_for_conversion):
                base_name = os.path.basename(file_path)
                name_no_ext, ext = os.path.splitext(base_name)
                ext = ext.lower()
                current_file_processed_successfully = False
                
                # Determine the canvas to use or output path
                current_canvas_for_drawing = None # For ReportLab direct drawing types
                individual_output_path_for_direct_pdf = None # For types like HTML generating own PDF

                if single_output_mode:
                    if ext in IMAGE_EXTENSIONS or ext in TEXT_EXTENSIONS or ext in RTF_EXTENSIONS or ext in SVG_EXTENSIONS:
                        current_canvas_for_drawing = shared_reportlab_canvas
                    elif ext in HTML_EXTENSIONS:
                        # HTML in single mode will create a temp PDF to be merged
                        fd, temp_html_pdf_path = tempfile.mkstemp(suffix=".pdf", prefix=f"html_{name_no_ext}_")
                        os.close(fd)
                        individual_output_path_for_direct_pdf = temp_html_pdf_path
                        temp_files_to_merge_in_single_mode.append(temp_html_pdf_path)
                    # Add other direct-to-PDF generating types here
                else: # Multiple output mode
                    if ext in IMAGE_EXTENSIONS or ext in TEXT_EXTENSIONS or ext in RTF_EXTENSIONS or ext in SVG_EXTENSIONS:
                        individual_rl_pdf_path = os.path.join(output_directory_for_multiple, f"{name_no_ext}_drawn.pdf")
                        current_canvas_for_drawing = canvas.Canvas(individual_rl_pdf_path, pagesize=A4)
                        current_canvas_for_drawing.setTitle(base_name)
                    elif ext in HTML_EXTENSIONS:
                        individual_output_path_for_direct_pdf = os.path.join(output_directory_for_multiple, f"{name_no_ext}.pdf")
                    # Add other direct-to-PDF generating types here

                try:
                    self.file_conversion_status_label.config(text=f"Verarbeite: {base_name}...")
                    self.root.update_idletasks()

                    if ext in IMAGE_EXTENSIONS:
                        self._add_image_to_pdf(file_path, current_canvas_for_drawing)
                        current_file_processed_successfully = True
                        if single_output_mode: reportlab_canvas_has_content = True
                    elif ext in TEXT_EXTENSIONS:
                        self._add_text_file_to_pdf(file_path, current_canvas_for_drawing)
                        current_file_processed_successfully = True
                        if single_output_mode: reportlab_canvas_has_content = True
                    elif ext in RTF_EXTENSIONS:
                        self._add_rtf_to_pdf(file_path, current_canvas_for_drawing)
                        current_file_processed_successfully = True
                        if single_output_mode: reportlab_canvas_has_content = True
                    elif ext in HTML_EXTENSIONS:
                        self._convert_html_to_separate_pdf(file_path, individual_output_path_for_direct_pdf)
                        current_file_processed_successfully = True
                    elif ext in SVG_EXTENSIONS:
                        self._add_svg_to_pdf(file_path, current_canvas_for_drawing)
                        current_file_processed_successfully = True
                        if single_output_mode: reportlab_canvas_has_content = True
                    else:
                        error_msg = f"{base_name}: Dateityp '{ext}' nicht unterstützt."
                        errors_occurred.append(error_msg)
                        if current_canvas_for_drawing: # Add note to its PDF if one was created
                            current_canvas_for_drawing.drawString(72, A4[1] - 72, f"Datei: {base_name} (nicht unterstützt)")
                            current_canvas_for_drawing.showPage()
                            if single_output_mode: reportlab_canvas_has_content = True
                        # In single mode, if HTML was supposed to make a temp file, clean it up
                        if single_output_mode and individual_output_path_for_direct_pdf and os.path.exists(individual_output_path_for_direct_pdf):
                            if individual_output_path_for_direct_pdf in temp_files_to_merge_in_single_mode:
                                temp_files_to_merge_in_single_mode.remove(individual_output_path_for_direct_pdf)
                            try: os.remove(individual_output_path_for_direct_pdf) 
                            except OSError: pass

                    if current_file_processed_successfully:
                        files_processed_this_run += 1
                    
                    # Save individual canvas if in multi-mode and it was used for drawing
                    if not single_output_mode and current_canvas_for_drawing and current_file_processed_successfully:
                        current_canvas_for_drawing.save()

                except Exception as file_e:
                    error_msg = f"Fehler bei {base_name}: {str(file_e)}"
                    errors_occurred.append(error_msg)
                    print(f"Error processing {base_name}: {file_e}")
                    # Cleanup temporary files if error occurred during their specific processing
                    if single_output_mode and individual_output_path_for_direct_pdf and os.path.exists(individual_output_path_for_direct_pdf):
                        if individual_output_path_for_direct_pdf in temp_files_to_merge_in_single_mode:
                           temp_files_to_merge_in_single_mode.remove(individual_output_path_for_direct_pdf)
                        try: os.remove(individual_output_path_for_direct_pdf) 
                        except OSError: pass
                    if not single_output_mode and current_canvas_for_drawing: # If canvas created for multi-mode, it might be empty/half-done
                        # We are not saving it if an error occurred.
                        pass 
            # End of loop through files

            # Finalize PDFs
            if single_output_mode:
                if shared_reportlab_canvas: # Save the shared canvas if it was used
                    if reportlab_canvas_has_content:
                        shared_reportlab_canvas.save()
                        temp_files_to_merge_in_single_mode.insert(0, reportlab_canvas_content_temp_path) # Add to merge list
                    else: # No content was drawn, delete the empty temp canvas PDF
                        try: os.remove(reportlab_canvas_content_temp_path)
                        except OSError: pass
                        reportlab_canvas_content_temp_path = None # Nullify path
                
                if files_processed_this_run > 0 and temp_files_to_merge_in_single_mode:
                    merger = PdfWriter()
                    for pdf_path in temp_files_to_merge_in_single_mode:
                        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                            try:
                                merger.append(pdf_path)
                            except Exception as merge_e:
                                errors_occurred.append(f"Fehler beim Mergen von {os.path.basename(pdf_path)}: {merge_e}")
                        elif os.path.exists(pdf_path): # file exists but is empty
                             errors_occurred.append(f"Temporäre Datei {os.path.basename(pdf_path)} war leer und wurde übersprungen.")
                    
                    if len(merger.pages) > 0 : # Check if merger actually has pages before writing
                        with open(output_final_pdf_path, 'wb') as f_out:
                            merger.write(f_out)
                    elif not errors_occurred: # No pages but also no other errors, means files were processed but resulted in no output pages
                        errors_occurred.append("Keine Seiten konnten aus den ausgewählten Dateien generiert werden.")
                    merger.close()
                elif files_processed_this_run == 0 and not errors_occurred: # No files processed, no real errors means all unsupported or empty
                     errors_occurred.append("Keine unterstützten Dateien für die Konvertierung gefunden oder verarbeitet.")
                
                # Clean up all temporary files used for merging
                for temp_file_path in temp_files_to_merge_in_single_mode:
                    if os.path.exists(temp_file_path):
                        try: os.remove(temp_file_path)
                        except OSError as e: print(f"Could not delete temp file {temp_file_path}: {e}")
                if reportlab_canvas_content_temp_path and os.path.exists(reportlab_canvas_content_temp_path):
                     try: os.remove(reportlab_canvas_content_temp_path)
                     except OSError as e: print(f"Could not delete rl_canvas temp file {reportlab_canvas_content_temp_path}: {e}")
            
            # Reporting logic (simplified, needs refinement based on new flow)
            if not errors_occurred and files_processed_this_run > 0:
                messagebox.showinfo("Erfolg", f"{files_processed_this_run} Datei(en) erfolgreich zu PDF konvertiert.")
                self.file_conversion_status_label.config(text="Konvertierung erfolgreich!")
            elif errors_occurred:
                processed_msg = f"{files_processed_this_run} Datei(en) erfolgreich verarbeitet." if files_processed_this_run > 0 else "Keine Dateien erfolgreich verarbeitet."
                final_error_msg = f"{processed_msg}\n{len(errors_occurred)} Fehler aufgetreten:\n\n" + "\n".join(errors_occurred)
                messagebox.showerror("Konvertierung mit Fehlern", final_error_msg)
                self.file_conversion_status_label.config(text=f"Konvertierung mit {len(errors_occurred)} Fehlern abgeschlossen.")
            elif files_processed_this_run == 0: # No files processed, errors_occurred might be empty or have "unsupported" messages
                msg = "Keine Dateien verarbeitet."
                if errors_occurred : msg += "\nDetails:\n" + "\n".join(errors_occurred)
                else: msg += " Keine unterstützten Dateien ausgewählt."
                messagebox.showwarning("Keine Dateien verarbeitet", msg)
                self.file_conversion_status_label.config(text="Keine Dateien verarbeitet.")

            self.selected_files_for_conversion.clear()
            self.file_to_pdf_listbox.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Schwerwiegender Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")
            self.file_conversion_status_label.config(text="Schwerwiegender Konvertierungsfehler.")
            # Clean up any temp files if major crash
            for temp_file_path in temp_files_to_merge_in_single_mode:
                if os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass
            if reportlab_canvas_content_temp_path and os.path.exists(reportlab_canvas_content_temp_path):
                try:
                    os.remove(reportlab_canvas_content_temp_path)
                except OSError:
                    pass
            if single_output_mode and output_final_pdf_path and os.path.exists(output_final_pdf_path) and files_processed_this_run == 0:
                 try:
                     os.remove(output_final_pdf_path) # If final PDF was created but nothing went into it
                 except OSError:
                     pass       

    def _convert_html_to_separate_pdf(self, html_file_path, output_pdf_path):
        """Converts an HTML file to a PDF file using xhtml2pdf."""
        try:
            with open(html_file_path, "r", encoding="utf-8") as source_html_file:
                html_content = source_html_file.read()
        except Exception as e:
            raise RuntimeError(f"Fehler beim Lesen der HTML-Datei {os.path.basename(html_file_path)}: {e}")
        
        try:
            with open(output_pdf_path, "wb") as result_file:
                pisa_status = pisa.CreatePDF(html_content, dest=result_file, encoding='utf-8')
            
            if pisa_status.err:
                # Clean up failed PDF attempt
                if os.path.exists(output_pdf_path):
                    try: os.remove(output_pdf_path)
                    except OSError: pass 
                raise RuntimeError(f"xhtml2pdf Fehler für {os.path.basename(html_file_path)}: {pisa_status.err}")
        except Exception as e:
            # If error occurs during pisa.CreatePDF, try to remove partially created output file
            if os.path.exists(output_pdf_path):
                try: os.remove(output_pdf_path)
                except OSError: pass
            raise RuntimeError(f"Fehler beim Konvertieren von HTML zu PDF ({os.path.basename(html_file_path)}): {e}")

    def _add_image_to_pdf(self, image_path, pdf_canvas):
        """Adds an image to the PDF canvas on a new page, scaled to fit."""
        try:
            img = Image.open(image_path)
            
            if img.format == "GIF":
                try:
                    img.seek(0)
                    if img.mode not in ['L', 'RGB', 'CMYK']:
                        img = img.convert('RGB')
                except EOFError: 
                    if img.mode not in ['L', 'RGB', 'CMYK']:
                         img = img.convert('RGB') 
            elif img.mode == 'RGBA':
                img = img.convert('RGB') 
            elif img.mode == 'P': 
                img = img.convert('RGB')

            img_reader = ImageReader(img) 
        except UnidentifiedImageError:
            raise ValueError(f"Kann Bilddatei nicht identifizieren: {os.path.basename(image_path)}")
        except Exception as e:
            raise RuntimeError(f"Fehler beim Öffnen/Verarbeiten von {os.path.basename(image_path)}: {e}")

        img_width, img_height = img.size
        page_width, page_height = A4 
        margin = 0.5 * inch 

        available_width = page_width - 2 * margin
        available_height = page_height - 2 * margin

        scale_w = available_width / img_width
        scale_h = available_height / img_height
        scale = min(scale_w, scale_h)

        draw_width = img_width * scale
        draw_height = img_height * scale

        pos_x = (page_width - draw_width) / 2
        pos_y = (page_height - draw_height) / 2

        pdf_canvas.setPageSize((page_width, page_height))
        pdf_canvas.drawImage(img_reader, pos_x, pos_y, width=draw_width, height=draw_height, mask='auto')
        pdf_canvas.showPage()

    def _render_text_to_pdf_canvas(self, text_content, pdf_canvas, source_filename="Text"):
        """Renders raw text_content to the PDF canvas."""
        page_width, page_height = A4
        margin = 0.75 * inch
        line_height = 14 # points
        font_name = "Helvetica"
        font_size = 10

        available_width = page_width - 2 * margin
        max_lines_per_page = int((page_height - 2 * margin) / line_height)

        lines = text_content.split('\n')
        
        current_line_on_page = 0
        # first_page_for_file = True # Not strictly needed with current logic

        text_object = pdf_canvas.beginText()
        text_object.setFont(font_name, font_size)
        text_object.setTextOrigin(margin, page_height - margin - line_height)
        text_object.setLeading(line_height)

        if not lines or (len(lines) == 1 and not lines[0]):
            pass 

        for i, line in enumerate(lines):
            chars_per_line_approx = int(available_width / (font_size * 0.55)) 
            if chars_per_line_approx <= 0: chars_per_line_approx = 1 
            
            sub_lines = [line[j:j+chars_per_line_approx] for j in range(0, len(line), chars_per_line_approx)]
            if not sub_lines and line == "": 
                sub_lines = ['']
            elif not sub_lines and line != "":
                sub_lines = [line] 

            for sub_line in sub_lines:
                if current_line_on_page >= max_lines_per_page:
                    pdf_canvas.drawText(text_object)
                    pdf_canvas.showPage()
                    text_object = pdf_canvas.beginText()
                    text_object.setFont(font_name, font_size)
                    text_object.setTextOrigin(margin, page_height - margin - line_height)
                    text_object.setLeading(line_height)
                    current_line_on_page = 0
                    # first_page_for_file = False # Not strictly needed
                
                text_object.textLine(sub_line)
                current_line_on_page += 1
        
        pdf_canvas.drawText(text_object) 
        pdf_canvas.showPage()

    def _add_text_file_to_pdf(self, file_path, pdf_canvas):
        """Reads a plain text file and renders its content to the PDF canvas."""
        base_name = os.path.basename(file_path)
        try:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    text_content = f.read()
        except Exception as e:
            raise RuntimeError(f"Fehler beim Lesen der Textdatei {base_name}: {e}")
        
        self._render_text_to_pdf_canvas(text_content, pdf_canvas, source_filename=base_name)

    def _add_rtf_to_pdf(self, file_path, pdf_canvas):
        """Reads an RTF file, converts to plain text, and renders to PDF canvas."""
        base_name = os.path.basename(file_path)
        try:
            # RTF files can be finicky with encoding; often they are ASCII/latin-1 based
            # but can declare other encodings. striprtf should handle internal encoding.
            with open(file_path, 'r', encoding='latin-1') as f: # More common for RTF
                rtf_content = f.read()
        except UnicodeDecodeError:
             try:
                with open(file_path, 'r', encoding='utf-8') as f: # Fallback
                    rtf_content = f.read()
             except Exception as e:
                 raise RuntimeError(f"Fehler beim Lesen der RTF-Datei {base_name} (nach Fallback): {e}")
        except Exception as e:
            raise RuntimeError(f"Fehler beim Lesen der RTF-Datei {base_name}: {e}")

        try:
            plain_text = rtf_to_text(rtf_content)
        except Exception as e:
            raise RuntimeError(f"Fehler beim Konvertieren von RTF zu Text für {base_name}: {e}")
        
        self._render_text_to_pdf_canvas(plain_text, pdf_canvas, source_filename=base_name)

    def _add_svg_to_pdf(self, file_path, pdf_canvas):
        """Adds an SVG file to the PDF canvas on a new page, scaled to fit."""
        try:
            drawing = svg2rlg(file_path)
            if not drawing:
                raise ValueError("SVG konnte nicht geladen oder geparst werden.")
        except Exception as e:
            raise RuntimeError(f"Fehler beim Laden der SVG-Datei {os.path.basename(file_path)}: {e}")

        svg_width = drawing.width
        svg_height = drawing.height

        if svg_width <= 0 or svg_height <= 0:
            # Add a placeholder page indicating an issue with SVG dimensions or content
            pdf_canvas.drawString(72, A4[1] - 72, f"SVG: {os.path.basename(file_path)}")
            pdf_canvas.drawString(72, A4[1] - 90, "SVG hat keine Dimensionen oder ist leer.")
            pdf_canvas.showPage()
            # Consider raising an error or returning a status if this should halt processing for this file
            # For now, we just add a note and a blank page for this SVG.
            # raise ValueError(f"SVG {os.path.basename(file_path)} hat keine Dimensionen oder ist leer.")
            return # Successfully processed by adding a note, even if SVG content isn't drawn

        page_width, page_height = A4
        margin = 0.5 * inch

        available_width = page_width - 2 * margin
        available_height = page_height - 2 * margin

        scale_w = available_width / svg_width
        scale_h = available_height / svg_height
        scale = min(scale_w, scale_h)

        if scale <= 0: # Should not happen if svg_width/height are positive
            scale = 1 # Default to no scaling if something went wrong with calculation

        # The drawing object's transform property can be used for scaling and translation.
        # It's a list [a, b, c, d, e, f] for the transformation matrix.
        # Scale: [scale_x, 0, 0, scale_y, 0, 0]
        # Translate: [1, 0, 0, 1, dx, dy]
        # We need to scale first, then translate to center.
        
        scaled_width = svg_width * scale
        scaled_height = svg_height * scale

        pos_x = (page_width - scaled_width) / 2
        pos_y = (page_height - scaled_height) / 2

        # Important: svglib drawings are often defined with (0,0) at top-left for SVG coordinate system.
        # ReportLab canvas has (0,0) at bottom-left. Adjustments might be needed for `drawOn`.
        # The `drawing.width` and `drawing.height` are useful, but how `drawOn` interprets coordinates
        # with respect to the drawing's internal origin vs. canvas origin matters.
        # `drawOn` usually draws the bounding box of the drawing at the given (x,y) of the canvas.
        # Let's assume standard drawOn behavior; scaling the drawing object itself is safer.

        drawing.scale(scale, scale) # Scale the drawing object itself
        drawing.width = scaled_width # Update drawing object's reported width/height after scaling
        drawing.height = scaled_height

        # Position to draw the (now scaled) drawing on the canvas
        # The (pos_x, pos_y) calculated should be the bottom-left corner for ReportLab canvas
        
        pdf_canvas.setPageSize((page_width, page_height)) # Ensure page size is set for current page
        drawing.drawOn(pdf_canvas, pos_x, pos_y)
        pdf_canvas.showPage()

# Main application setup - This is the end of the PDFToolApp class.
# The following lines are OUTSIDE the class.
if __name__ == "__main__":
    root = TkinterDnD.Tk() # Use TkinterDnD Tk object for drag & drop
    app = PDFToolApp(root)
    root.mainloop() 