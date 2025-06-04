import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
import os
from utils.common_helpers import parse_page_ranges # Import the helper function

class DeleteTab:
    def __init__(self, parent_notebook, app_root):
        self.app_root = app_root
        self.delete_frame = ttk.Frame(parent_notebook)

        self.delete_input_pdf_path = None
        self.delete_selected_file_label = None
        self.delete_pages_entry = None
        self.delete_status_label = None

        self._create_delete_widgets()

    def get_frame(self):
        return self.delete_frame

    def _create_delete_widgets(self):
        controls_frame = ttk.LabelFrame(self.delete_frame, text="PDF auswählen und zu löschende Seiten angeben")
        controls_frame.pack(padx=10, pady=10, fill="x")

        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="PDF auswählen", command=self._select_pdf_for_delete)
        select_button.pack(side=tk.LEFT, padx=5)

        self.delete_selected_file_label = ttk.Label(file_select_frame, text="Keine Datei ausgewählt.")
        self.delete_selected_file_label.pack(side=tk.LEFT, padx=5)

        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Zu löschende Seiten (z.B. 1, 3, 5-7):")
        pages_label.pack(side=tk.LEFT, padx=5)

        self.delete_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.delete_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        action_frame = ttk.Frame(self.delete_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        delete_button = ttk.Button(action_frame, text="Seiten löschen und speichern", command=self._execute_delete_pages)
        delete_button.pack(pady=5)

        self.delete_status_label = ttk.Label(action_frame, text="")
        self.delete_status_label.pack(pady=5)

    def _select_pdf_for_delete(self):
        file_path = filedialog.askopenfilename(
            title="PDF-Datei auswählen",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*"))
        )
        if file_path:
            self.delete_input_pdf_path = file_path
            self.delete_selected_file_label.config(text=os.path.basename(file_path))
            self.delete_status_label.config(text="Datei ausgewählt. Zu löschende Seiten eingeben.")
        else:
            self.delete_input_pdf_path = None
            self.delete_selected_file_label.config(text="Keine Datei ausgewählt.")
            self.delete_status_label.config(text="Dateiauswahl abgebrochen.")

    def _parse_pages_to_delete(self, pages_str, total_pages):
        # This method now directly uses the imported helper function
        return parse_page_ranges(pages_str, total_pages)

    def _execute_delete_pages(self):
        if not self.delete_input_pdf_path:
            messagebox.showwarning("Keine PDF ausgewählt", "Bitte wählen Sie zuerst eine PDF-Datei aus.")
            return

        pages_str = self.delete_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("Keine Seiten angegeben", "Bitte geben Sie die zu löschenden Seitenzahlen oder Bereiche ein.")
            return

        try:
            input_pdf = PdfReader(self.delete_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_delete_indices = self._parse_pages_to_delete(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Ungültige Seiteneingabe", str(e))
            self.delete_status_label.config(text=f"Fehler: {e}")
            return
        except Exception as e: 
            messagebox.showerror("Fehler beim Lesen der PDF", f"PDF konnte nicht gelesen werden: {e}")
            self.delete_status_label.config(text="Fehler beim Lesen der PDF.")
            return

        if not pages_to_delete_indices:
            messagebox.showinfo("Keine gültigen Seiten", "Keine gültigen Seiten zum Löschen angegeben.")
            self.delete_status_label.config(text="Keine gültigen Seiten zum Löschen.")
            return
        
        if all(p_idx in pages_to_delete_indices for p_idx in range(total_pages)):
            messagebox.showwarning("Alle Seiten ausgewählt", "Sie haben alle Seiten zum Löschen ausgewählt. Dies würde zu einer leeren PDF führen.")
            self.delete_status_label.config(text="Kann nicht alle Seiten löschen.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")) ,
            title="Geänderte PDF speichern unter",
            initialfile=f"{os.path.splitext(os.path.basename(self.delete_input_pdf_path))[0]}_geändert.pdf"
        )

        if not output_filename:
            self.delete_status_label.config(text="Löschen abgebrochen.")
            return

        pdf_writer = PdfWriter()
        try:
            self.delete_status_label.config(text="Lösche Seiten...")
            self.app_root.update_idletasks()

            for i in range(total_pages):
                if i not in pages_to_delete_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0:
                 messagebox.showwarning("Leeres Ergebnis", "Alle angegebenen Seiten wurden gelöscht, was zu einer leeren PDF führt. Datei nicht gespeichert.")
                 self.delete_status_label.config(text="Die resultierende PDF wäre leer. Vorgang abgebrochen.")
                 pdf_writer.close()
                 return

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Erfolg", f"Seiten erfolgreich gelöscht. Gespeichert unter {os.path.basename(output_filename)}")
            self.delete_status_label.config(text="Löschen erfolgreich!")

        except Exception as e:
            messagebox.showerror("Fehler beim Löschen der Seiten", f"Ein Fehler ist aufgetreten: {e}")
            self.delete_status_label.config(text="Fehler während des Löschens.") 