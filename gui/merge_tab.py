import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfWriter
import os
from tkinterdnd2 import DND_FILES
from utils.common_helpers import parse_dropped_files

class MergeTab:
    def __init__(self, parent_notebook, app_root):
        self.app_root = app_root  # For messagebox, update_idletasks
        self.merge_frame = ttk.Frame(parent_notebook)
        
        self.selected_merge_files = []
        self.merge_listbox = None
        self.merge_status_label = None
        
        self._create_merge_widgets()

    def get_frame(self):
        return self.merge_frame

    def _create_merge_widgets(self):
        # Frame for file list and controls
        controls_frame = ttk.LabelFrame(self.merge_frame, text="Dateien zum Zusammenführen")
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

        add_button = ttk.Button(buttons_frame, text="PDF hinzufügen", command=self._add_pdf_to_merge_list)
        add_button.pack(fill="x", pady=2)

        remove_button = ttk.Button(buttons_frame, text="Auswahl entfernen", command=self._remove_pdf_from_merge_list)
        remove_button.pack(fill="x", pady=2)

        move_up_button = ttk.Button(buttons_frame, text="Nach oben", command=self._move_merge_item_up)
        move_up_button.pack(fill="x", pady=2)

        move_down_button = ttk.Button(buttons_frame, text="Nach unten", command=self._move_merge_item_down)
        move_down_button.pack(fill="x", pady=2)
        
        # Register merge_listbox for drag and drop
        self.merge_listbox.drop_target_register(DND_FILES)
        self.merge_listbox.dnd_bind('<<Drop>>', self._handle_merge_drop)
        
        # Merge button and status
        action_frame = ttk.Frame(self.merge_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        merge_button = ttk.Button(action_frame, text="PDFs zusammenführen und speichern", command=self._execute_merge_pdfs)
        merge_button.pack(pady=5)

        self.merge_status_label = ttk.Label(action_frame, text="")
        self.merge_status_label.pack(pady=5)

    def _add_pdf_to_merge_list(self):
        files = filedialog.askopenfilenames(
            title="PDF-Dateien auswählen",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*"))
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_merge_files:
                    self.selected_merge_files.append(file_path)
                    self.merge_listbox.insert(tk.END, os.path.basename(file_path))
            self.merge_status_label.config(text=f"{len(files)} Datei(en) hinzugefügt.")

    def _remove_pdf_from_merge_list(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            del self.selected_merge_files[index]
            self.merge_listbox.delete(index)
            self.merge_status_label.config(text="Datei entfernt.")
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.")

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
                self.merge_status_label.config(text="Datei nach oben verschoben.")
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

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
                self.merge_status_label.config(text="Datei nach unten verschoben.")
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _execute_merge_pdfs(self):
        if not self.selected_merge_files or len(self.selected_merge_files) < 2:
            messagebox.showwarning("Nicht genügend Dateien", "Bitte wählen Sie mindestens zwei PDF-Dateien zum Zusammenführen aus.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF-Dateien", "*.pdf"), ("Alle Dateien", "*.*")),
            title="Zusammengeführte PDF speichern unter"
        )

        if not output_filename:
            self.merge_status_label.config(text="Zusammenführen abgebrochen.")
            return

        pdf_writer = PdfWriter()
        
        try:
            self.merge_status_label.config(text="Führe PDFs zusammen...")
            self.app_root.update_idletasks() 

            for filename in self.selected_merge_files:
                pdf_writer.append(filename)
            
            with open(output_filename, 'wb') as out:
                pdf_writer.write(out)
            
            pdf_writer.close() 
            messagebox.showinfo("Erfolg", f"PDFs erfolgreich zusammengeführt in {os.path.basename(output_filename)}")
            self.merge_status_label.config(text="Zusammenführen erfolgreich!")
            self.selected_merge_files.clear()
            self.merge_listbox.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Fehler beim Zusammenführen", f"Ein Fehler ist aufgetreten: {e}")
            self.merge_status_label.config(text="Fehler beim Zusammenführen.")

    def _handle_merge_drop(self, event):
        dropped_files = parse_dropped_files(event.data)
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