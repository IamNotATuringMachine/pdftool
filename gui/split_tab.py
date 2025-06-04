import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
import os
from utils.common_helpers import parse_page_ranges # Import the helper function

class SplitTab:
    def __init__(self, parent_notebook, app_root):
        self.app_root = app_root
        self.split_frame = ttk.Frame(parent_notebook)

        self.split_input_pdf_path = None
        self.split_selected_file_label = None
        self.split_pages_entry = None
        self.split_status_label = None

        self._create_split_widgets()

    def get_frame(self):
        return self.split_frame

    def _create_split_widgets(self):
        controls_frame = ttk.LabelFrame(self.split_frame, text="PDF auswählen und Seiten angeben")
        controls_frame.pack(padx=10, pady=10, fill="x")

        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="PDF auswählen", command=self._select_pdf_for_split)
        select_button.pack(side=tk.LEFT, padx=5)

        self.split_selected_file_label = ttk.Label(file_select_frame, text="Keine Datei ausgewählt.")
        self.split_selected_file_label.pack(side=tk.LEFT, padx=5)

        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Seiten/Bereiche (z.B. 1-3, 5, 7-9):")
        pages_label.pack(side=tk.LEFT, padx=5)

        self.split_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.split_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        action_frame = ttk.Frame(self.split_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        extract_button = ttk.Button(action_frame, text="Seiten extrahieren und speichern", command=self._execute_split_pdf)
        extract_button.pack(pady=5)

        self.split_status_label = ttk.Label(action_frame, text="")
        self.split_status_label.pack(pady=5)

    def _select_pdf_for_split(self):
        file_path = filedialog.askopenfilename(
            title="PDF-Datei auswählen",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*"))
        )
        if file_path:
            self.split_input_pdf_path = file_path
            self.split_selected_file_label.config(text=os.path.basename(file_path))
            self.split_status_label.config(text="Datei ausgewählt. Seitenbereiche eingeben.")
        else:
            self.split_input_pdf_path = None
            self.split_selected_file_label.config(text="Keine Datei ausgewählt.")
            self.split_status_label.config(text="Dateiauswahl abgebrochen.")

    def _execute_split_pdf(self):
        if not self.split_input_pdf_path:
            messagebox.showwarning("Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return

        pages_str = self.split_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("Keine Seiten angegeben", "Bitte geben Sie die zu extrahierenden Seitenzahlen oder Bereiche ein.")
            return

        try:
            input_pdf = PdfReader(self.split_input_pdf_path)
            total_pages = len(input_pdf.pages)
            # Use the imported helper function
            pages_to_extract = parse_page_ranges(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Ungültige Seiteneingabe", str(e))
            self.split_status_label.config(text=f"Fehler: {e}")
            return
        except Exception as e: 
            messagebox.showerror("Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.split_status_label.config(text="Fehler beim Lesen der PDF.")
            return

        if not pages_to_extract:
            messagebox.showinfo("Keine Seiten zu extrahieren", "Die angegebenen Seiten ergeben keine zu extrahierenden Seiten.")
            self.split_status_label.config(text="Keine Seiten zum Extrahieren basierend auf der Eingabe.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")) ,
            title="Extrahierte Seiten speichern unter",
            initialfile=f"{os.path.splitext(os.path.basename(self.split_input_pdf_path))[0]}_extrahiert.pdf"
        )

        if not output_filename:
            self.split_status_label.config(text="Extraktion abgebrochen.")
            return

        pdf_writer = PdfWriter()
        try:
            self.split_status_label.config(text="Extrahiere Seiten...")
            self.app_root.update_idletasks()

            for page_num in pages_to_extract:
                pdf_writer.add_page(input_pdf.pages[page_num])
            
            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Erfolg", f"Seiten erfolgreich extrahiert nach {os.path.basename(output_filename)}")
            self.split_status_label.config(text="Extraktion erfolgreich!")

        except Exception as e:
            messagebox.showerror("Fehler beim Extrahieren der Seiten", f"Ein Fehler ist aufgetreten: {e}")
            self.split_status_label.config(text="Fehler während der Extraktion.") 