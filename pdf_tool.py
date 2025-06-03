import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfWriter, PdfReader # Added PdfReader
from PIL import Image, UnidentifiedImageError # Added UnidentifiedImageError
import os # For path manipulations

class PDFToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF & Bild Werkzeug") # Translated
        self.root.geometry("800x600")

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create frames for each functionality
        self.merge_frame = ttk.Frame(self.notebook)
        self.split_frame = ttk.Frame(self.notebook)
        self.delete_frame = ttk.Frame(self.notebook)
        self.jpg_to_pdf_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.merge_frame, text='PDFs zusammenführen') # Translated
        self.notebook.add(self.split_frame, text='PDF Seiten extrahieren') # Translated
        self.notebook.add(self.delete_frame, text='PDF Seiten löschen') # Translated
        self.notebook.add(self.jpg_to_pdf_frame, text='JPG zu PDF') # Translated

        self.selected_merge_files = []
        self.split_input_pdf_path = None # To store path of PDF for splitting
        self.delete_input_pdf_path = None # To store path of PDF for page deletion
        self.selected_jpg_files = [] # To store paths of JPGs for conversion

        self._create_merge_widgets()
        self._create_split_widgets()
        self._create_delete_widgets()
        self._create_jpg_to_pdf_widgets()

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

    def _create_jpg_to_pdf_widgets(self):
        controls_frame = ttk.LabelFrame(self.jpg_to_pdf_frame, text="JPG-Dateien auswählen") # Translated
        controls_frame.pack(padx=10, pady=10, fill="x")

        list_frame = ttk.Frame(controls_frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        self.jpg_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10) 
        self.jpg_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5)

        jpg_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.jpg_listbox.yview)
        jpg_scrollbar.pack(side=tk.LEFT, fill="y")
        self.jpg_listbox.config(yscrollcommand=jpg_scrollbar.set)

        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill="x", pady=5)

        add_jpg_button = ttk.Button(buttons_frame, text="JPG(s) hinzufügen", command=self._add_jpg_files_to_list) # Translated
        add_jpg_button.pack(side=tk.LEFT, padx=5)

        remove_jpg_button = ttk.Button(buttons_frame, text="Ausgewählte JPG(s) entfernen", command=self._remove_jpg_from_list) # Translated
        remove_jpg_button.pack(side=tk.LEFT, padx=5)
        
        options_frame = ttk.Frame(self.jpg_to_pdf_frame) 
        options_frame.pack(padx=10, pady=5, fill="x")

        action_frame = ttk.Frame(self.jpg_to_pdf_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        convert_button = ttk.Button(action_frame, text="JPG(s) zu PDF konvertieren und speichern", command=self._execute_jpg_to_pdf) # Translated
        convert_button.pack(pady=5)

        self.jpg_to_pdf_status_label = ttk.Label(action_frame, text="")
        self.jpg_to_pdf_status_label.pack(pady=5)

    def _add_jpg_files_to_list(self):
        files = filedialog.askopenfilenames(
            title="JPG-Dateien auswählen", # Translated
            filetypes=(("JPEG-Dateien", "*.jpg *.jpeg"), ("Alle Dateien", "*.*")) # Translated
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_jpg_files:
                    self.selected_jpg_files.append(file_path)
                    self.jpg_listbox.insert(tk.END, os.path.basename(file_path))
            self.jpg_to_pdf_status_label.config(text=f"{len(files)} JPG-Datei(en) hinzugefügt.") # Translated

    def _remove_jpg_from_list(self):
        selected_indices = self.jpg_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True):
                del self.selected_jpg_files[index]
                self.jpg_listbox.delete(index)
            self.jpg_to_pdf_status_label.config(text="Ausgewählte JPG-Datei(en) entfernt.") # Translated
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie JPG-Datei(en) zum Entfernen aus.") # Translated

    def _execute_jpg_to_pdf(self):
        if not self.selected_jpg_files:
            messagebox.showwarning("Keine JPG-Dateien", "Bitte wählen Sie mindestens eine JPG-Datei zur Konvertierung aus.") # Translated
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")), # Translated
            title="PDF speichern unter" # Translated
        )

        if not output_filename:
            self.jpg_to_pdf_status_label.config(text="Konvertierung abgebrochen.") # Translated
            return

        try:
            self.jpg_to_pdf_status_label.config(text="Konvertiere JPG(s) zu PDF...") # Translated
            self.root.update_idletasks()

            images_to_save = []
            first_image = None

            for jpg_path in self.selected_jpg_files:
                img = Image.open(jpg_path)
                if img.mode == 'RGBA' or img.mode == 'P':
                    img = img.convert('RGB') 
                
                if not first_image:
                    first_image = img
                else:
                    images_to_save.append(img)
            
            if first_image:
                first_image.save(
                    output_filename, 
                    save_all=True, 
                    append_images=images_to_save 
                )
                messagebox.showinfo("Erfolg", f"JPG(s) erfolgreich zu {os.path.basename(output_filename)} konvertiert") # Translated
                self.jpg_to_pdf_status_label.config(text="Konvertierung erfolgreich!") # Translated
                self.selected_jpg_files.clear()
                self.jpg_listbox.delete(0, tk.END)
            else:
                messagebox.showerror("Fehler", "Keine Bilder für die PDF-Konvertierung verarbeitet.") # Translated
                self.jpg_to_pdf_status_label.config(text="Fehler: Keine Bilder zum Konvertieren.") # Translated

        except FileNotFoundError as e:
            messagebox.showerror("Datei nicht gefunden", f"Fehler: {e.filename} nicht gefunden.") # Translated
            self.jpg_to_pdf_status_label.config(text="Fehler: Eine oder mehrere JPG-Dateien nicht gefunden.") # Translated
        except UnidentifiedImageError: 
             messagebox.showerror("Ungültiges Bild", "Eine der ausgewählten Dateien ist keine gültige JPG-Datei oder ist beschädigt.") # Translated
             self.jpg_to_pdf_status_label.config(text="Fehler: Ungültige Bilddatei erkannt.") # Translated
        except Exception as e:
            messagebox.showerror("Fehler beim Konvertieren von JPG zu PDF", f"Ein Fehler ist aufgetreten: {e}") # Translated
            self.jpg_to_pdf_status_label.config(text="Fehler während der Konvertierung.") # Translated


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFToolApp(root)
    root.mainloop() 