import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfWriter # PdfReader might not be needed here, but PdfWriter is for merging temp PDFs
from PIL import Image, UnidentifiedImageError, ImageSequence
import os
from tkinterdnd2 import DND_FILES
from xhtml2pdf import pisa
from svglib.svglib import svg2rlg
from pillow_heif import register_heif_opener # Keep if HEIC/HEIF is directly handled
from striprtf.striprtf import rtf_to_text
import io # For BytesIO, used with xhtml2pdf
import tempfile

# --- ReportLab Imports ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4 # Using A4 by default
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
# from reportlab.lib.styles import getSampleStyleSheet # For Paragraph, if used later
# from reportlab.platypus import Paragraph # For more advanced text layout, if used later
# --- End ReportLab Imports ---

from utils.common_helpers import parse_dropped_files
# Import constants from the new central location
from utils.constants import (
    FILETYPES_FOR_DIALOG,
    ALL_SUPPORTED_EXT_PATTERNS_LIST,
    IMAGE_EXTENSIONS,
    TEXT_EXTENSIONS,
    RTF_EXTENSIONS,
    HTML_EXTENSIONS,
    SVG_EXTENSIONS
)

# --- pillow-heif registration (if not already done globally, but should be) ---
# register_heif_opener() # Assuming this is called once in the main app

# --- Constants (will be moved to utils/constants.py later) --- 
# SUPPORTED_FILE_TYPES, ALL_SUPPORTED_EXTENSIONS_DESC, etc. removed

class ConvertTab:
    def __init__(self, parent_notebook, app_root):
        self.app_root = app_root
        self.file_to_pdf_frame = ttk.Frame(parent_notebook)

        self.selected_files_for_conversion = []
        self.view_mode_var = tk.StringVar(value="list")
        self.list_view_frame = None
        self.file_to_pdf_listbox = None
        self.icon_view_frame = None
        self.icon_canvas = None
        self.icon_scrollbar = None
        self.icon_scrollable_frame = None
        self.selected_file_index = -1
        self.icon_buttons = []
        self.single_pdf_output_var = tk.BooleanVar(value=True)
        self.file_conversion_status_label = None

        self._create_file_to_pdf_widgets()

    def get_frame(self):
        return self.file_to_pdf_frame

    def _create_file_to_pdf_widgets(self): 
        view_toggle_frame = ttk.Frame(self.file_to_pdf_frame)
        view_toggle_frame.pack(padx=10, pady=5, fill="x")
        
        ttk.Label(view_toggle_frame, text="Ansicht:").pack(side=tk.LEFT, padx=5)
        
        list_view_radio = ttk.Radiobutton(view_toggle_frame, text="Liste", variable=self.view_mode_var, 
                                         value="list", command=self._toggle_view_mode)
        list_view_radio.pack(side=tk.LEFT, padx=5)
        
        icon_view_radio = ttk.Radiobutton(view_toggle_frame, text="Symbole", variable=self.view_mode_var, 
                                         value="icons", command=self._toggle_view_mode)
        icon_view_radio.pack(side=tk.LEFT, padx=5)
        
        controls_frame = ttk.LabelFrame(self.file_to_pdf_frame, text="Dateien für Konvertierung")
        controls_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.views_container = ttk.Frame(controls_frame)
        self.views_container.pack(side=tk.LEFT, fill="both", expand=True, padx=5, pady=5)
        
        self.list_view_frame = ttk.Frame(self.views_container)
        self.list_view_frame.pack(fill="both", expand=True)
        
        self.file_to_pdf_listbox = tk.Listbox(self.list_view_frame, selectmode=tk.SINGLE, height=10)
        self.file_to_pdf_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        self.file_to_pdf_listbox.bind('<<ListboxSelect>>', self._on_listbox_select)

        file_to_pdf_scrollbar = ttk.Scrollbar(self.list_view_frame, orient="vertical", command=self.file_to_pdf_listbox.yview)
        file_to_pdf_scrollbar.pack(side=tk.LEFT, fill="y")
        self.file_to_pdf_listbox.config(yscrollcommand=file_to_pdf_scrollbar.set)
        
        self.icon_view_frame = ttk.Frame(self.views_container)
        
        self.icon_canvas = tk.Canvas(self.icon_view_frame, bg="white")
        self.icon_scrollbar = ttk.Scrollbar(self.icon_view_frame, orient="vertical", command=self.icon_canvas.yview)
        self.icon_scrollable_frame = ttk.Frame(self.icon_canvas)
        
        self.icon_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
        )
        
        self.icon_canvas.create_window((0, 0), window=self.icon_scrollable_frame, anchor="nw")
        self.icon_canvas.configure(yscrollcommand=self.icon_scrollbar.set)
        
        self.icon_canvas.pack(side="left", fill="both", expand=True)
        self.icon_scrollbar.pack(side="right", fill="y")
        
        self.icon_canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        self.icon_buttons = []

        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(side=tk.RIGHT, fill="y", padx=5)

        add_button = ttk.Button(buttons_frame, text="Dateien hinzufügen", command=self._add_files_to_convert_list)
        add_button.pack(fill="x", pady=2)

        remove_button = ttk.Button(buttons_frame, text="Auswahl entfernen", command=self._remove_file_from_convert_list)
        remove_button.pack(fill="x", pady=2)

        move_up_button = ttk.Button(buttons_frame, text="Nach oben", command=self._move_convert_item_up)
        move_up_button.pack(fill="x", pady=2)

        move_down_button = ttk.Button(buttons_frame, text="Nach unten", command=self._move_convert_item_down)
        move_down_button.pack(fill="x", pady=2)
        
        self.file_to_pdf_listbox.drop_target_register(DND_FILES)
        self.file_to_pdf_listbox.dnd_bind('<<Drop>>', self._handle_file_drop)
        
        self.icon_canvas.drop_target_register(DND_FILES)
        self.icon_canvas.dnd_bind('<<Drop>>', self._handle_file_drop)
        
        options_frame = ttk.Frame(self.file_to_pdf_frame)
        options_frame.pack(padx=10, pady=5, fill="x")

        single_pdf_output_check = ttk.Checkbutton(
            options_frame, 
            text="Alle Dateien in eine einzelne PDF-Datei zusammenfassen", 
            variable=self.single_pdf_output_var
        )
        single_pdf_output_check.pack(side=tk.LEFT, padx=5)

        action_frame = ttk.Frame(self.file_to_pdf_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        convert_button = ttk.Button(action_frame, text="Ausgewählte Dateien zu PDF konvertieren und speichern", command=self._execute_file_to_pdf)
        convert_button.pack(pady=5)

        self.file_conversion_status_label = ttk.Label(action_frame, text="")
        self.file_conversion_status_label.pack(pady=5)
        
        self._toggle_view_mode()

    def _toggle_view_mode(self):
        if self.view_mode_var.get() == "list":
            self.icon_view_frame.pack_forget()
            self.list_view_frame.pack(fill="both", expand=True)
        else:
            self.list_view_frame.pack_forget()
            self.icon_view_frame.pack(fill="both", expand=True)
            self._refresh_icon_view()
    
    def _on_mousewheel(self, event):
        self.icon_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _get_file_icon(self, file_path):
        _, ext = os.path.splitext(file_path.lower())
        icon_map = {
            '.pdf': '📄',
            '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.bmp': '🖼️', 
            '.gif': '🖼️', '.tiff': '🖼️', '.tif': '🖼️', '.heic': '🖼️', '.heif': '🖼️',
            '.txt': '📝',
            '.rtf': '📝',
            '.html': '🌐', '.htm': '🌐',
            '.svg': '🎨',
            '.doc': '📄', '.docx': '📄',
            '.xls': '📊', '.xlsx': '📊',
            '.ppt': '📊', '.pptx': '📊',
            '.odt': '📄', '.ods': '📊', '.odp': '📊'
        }
        return icon_map.get(ext, '📁')
    
    def _refresh_icon_view(self):
        for widget in self.icon_scrollable_frame.winfo_children():
            widget.destroy()
        self.icon_buttons.clear()
        
        row, col = 0, 0
        max_cols = 4
        
        for i, file_path in enumerate(self.selected_files_for_conversion):
            icon_frame = ttk.Frame(self.icon_scrollable_frame, relief="raised", borderwidth=1)
            icon_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            icon_text = self._get_file_icon(file_path)
            icon_label = ttk.Label(icon_frame, text=icon_text, font=("Arial", 24))
            icon_label.pack(pady=5)
            
            filename = os.path.basename(file_path)
            if len(filename) > 15:
                display_name = filename[:12] + "..."
            else:
                display_name = filename
            
            name_label = ttk.Label(icon_frame, text=display_name, font=("Arial", 8), wraplength=80)
            name_label.pack(pady=2)
            
            def make_click_handler(index):
                def on_click(event):
                    self._select_icon(index)
                return on_click
            
            click_handler = make_click_handler(i)
            icon_frame.bind("<Button-1>", click_handler)
            icon_label.bind("<Button-1>", click_handler)
            name_label.bind("<Button-1>", click_handler)
            
            self.icon_buttons.append(icon_frame)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        for i in range(max_cols):
            self.icon_scrollable_frame.columnconfigure(i, weight=1)
        
        self.icon_scrollable_frame.update_idletasks()
        self.icon_canvas.configure(scrollregion=self.icon_canvas.bbox("all"))
    
    def _select_icon(self, index):
        for frame in self.icon_buttons:
            frame.configure(relief="raised", borderwidth=1)
        
        if 0 <= index < len(self.icon_buttons):
            self.icon_buttons[index].configure(relief="solid", borderwidth=2)
            self.selected_file_index = index
            
            self.file_to_pdf_listbox.selection_clear(0, tk.END)
            self.file_to_pdf_listbox.selection_set(index)
    
    def _get_current_selection_index(self):
        if self.view_mode_var.get() == "list":
            selection = self.file_to_pdf_listbox.curselection()
            return selection[0] if selection else -1
        else:
            return self.selected_file_index
    
    def _on_listbox_select(self, event):
        selected_indices = self.file_to_pdf_listbox.curselection()
        if selected_indices:
            self.selected_file_index = selected_indices[0]

    def _add_files_to_convert_list(self):
        files = filedialog.askopenfilenames(
            title="Dateien für Konvertierung auswählen",
            filetypes=FILETYPES_FOR_DIALOG
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_files_for_conversion:
                    self.selected_files_for_conversion.append(file_path)
                    self.file_to_pdf_listbox.insert(tk.END, os.path.basename(file_path))
            self.file_conversion_status_label.config(text=f"{len(files)} Datei(en) hinzugefügt.")
            
            if self.view_mode_var.get() == "icons":
                self._refresh_icon_view()

    def _remove_file_from_convert_list(self):
        selected_index = self._get_current_selection_index()
        if selected_index >= 0:
            del self.selected_files_for_conversion[selected_index]
            self.file_to_pdf_listbox.delete(selected_index)
            self.file_conversion_status_label.config(text="Datei entfernt.")
            self.selected_file_index = -1
            if self.view_mode_var.get() == "icons":
                self._refresh_icon_view()
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Entfernen aus.")

    def _move_convert_item_up(self):
        selected_index = self._get_current_selection_index()
        if selected_index >= 0:
            if selected_index > 0:
                self.selected_files_for_conversion[selected_index], self.selected_files_for_conversion[selected_index-1] = \
                    self.selected_files_for_conversion[selected_index-1], self.selected_files_for_conversion[selected_index]
                text = self.file_to_pdf_listbox.get(selected_index)
                self.file_to_pdf_listbox.delete(selected_index)
                self.file_to_pdf_listbox.insert(selected_index-1, text)
                self.file_to_pdf_listbox.selection_set(selected_index-1)
                self.file_conversion_status_label.config(text="Datei nach oben verschoben.")
                self.selected_file_index = selected_index - 1
                if self.view_mode_var.get() == "icons":
                    self._refresh_icon_view()
                    self._select_icon(selected_index - 1)
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _move_convert_item_down(self):
        selected_index = self._get_current_selection_index()
        if selected_index >= 0:
            if selected_index < len(self.selected_files_for_conversion) - 1:
                self.selected_files_for_conversion[selected_index], self.selected_files_for_conversion[selected_index+1] = \
                    self.selected_files_for_conversion[selected_index+1], self.selected_files_for_conversion[selected_index]
                text = self.file_to_pdf_listbox.get(selected_index)
                self.file_to_pdf_listbox.delete(selected_index)
                self.file_to_pdf_listbox.insert(selected_index+1, text)
                self.file_to_pdf_listbox.selection_set(selected_index+1)
                self.file_conversion_status_label.config(text="Datei nach unten verschoben.")
                self.selected_file_index = selected_index + 1
                if self.view_mode_var.get() == "icons":
                    self._refresh_icon_view()
                    self._select_icon(selected_index + 1)
        else:
            messagebox.showwarning("Keine Auswahl", "Bitte wählen Sie eine Datei zum Verschieben aus.")

    def _handle_file_drop(self, event):
        try:
            dropped_files = parse_dropped_files(event.data)
            added_count = 0
            unsupported_files = []
            for file_path in dropped_files:
                if os.path.isfile(file_path):
                    _, ext = os.path.splitext(file_path.lower())
                    # Use ALL_SUPPORTED_EXT_PATTERNS_LIST from this module for now
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
                if self.view_mode_var.get() == "icons":
                    self._refresh_icon_view()
            elif unsupported_files:
                 self.file_conversion_status_label.config(text=f"Keine unterstützten Dateien per Drag & Drop hinzugefügt. Nicht unterstützt: {', '.join(unsupported_files)}")
            elif not dropped_files: 
                 self.file_conversion_status_label.config(text="Keine gültigen Dateien im Drop gefunden.") 
                 
        except Exception as e:
            self.file_conversion_status_label.config(text="Fehler beim Drag & Drop.")
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
        self.app_root.update_idletasks()

        files_processed_this_run = 0
        errors_occurred = []
        temp_files_to_merge_in_single_mode = []
        
        reportlab_canvas_content_temp_path = None
        shared_reportlab_canvas = None
        reportlab_canvas_has_content = False

        if single_output_mode:
            fd, reportlab_canvas_content_temp_path = tempfile.mkstemp(suffix=".pdf", prefix="rl_canvas_")
            os.close(fd)
            shared_reportlab_canvas = canvas.Canvas(reportlab_canvas_content_temp_path, pagesize=A4)
            shared_reportlab_canvas.setTitle("Canvas Content")

        try:
            for index, file_path in enumerate(self.selected_files_for_conversion):
                base_name = os.path.basename(file_path)
                name_no_ext, ext = os.path.splitext(base_name)
                ext = ext.lower()
                current_file_processed_successfully = False
                
                current_canvas_for_drawing = None
                individual_output_path_for_direct_pdf = None

                if single_output_mode:
                    if ext in IMAGE_EXTENSIONS or ext in TEXT_EXTENSIONS or ext in RTF_EXTENSIONS or ext in SVG_EXTENSIONS:
                        current_canvas_for_drawing = shared_reportlab_canvas
                    elif ext in HTML_EXTENSIONS:
                        fd, temp_html_pdf_path = tempfile.mkstemp(suffix=".pdf", prefix=f"html_{name_no_ext}_")
                        os.close(fd)
                        individual_output_path_for_direct_pdf = temp_html_pdf_path
                        temp_files_to_merge_in_single_mode.append(temp_html_pdf_path)
                else:
                    if ext in IMAGE_EXTENSIONS or ext in TEXT_EXTENSIONS or ext in RTF_EXTENSIONS or ext in SVG_EXTENSIONS:
                        individual_rl_pdf_path = os.path.join(output_directory_for_multiple, f"{name_no_ext}_drawn.pdf")
                        current_canvas_for_drawing = canvas.Canvas(individual_rl_pdf_path, pagesize=A4)
                        current_canvas_for_drawing.setTitle(base_name)
                    elif ext in HTML_EXTENSIONS:
                        individual_output_path_for_direct_pdf = os.path.join(output_directory_for_multiple, f"{name_no_ext}.pdf")

                try:
                    self.file_conversion_status_label.config(text=f"Verarbeite: {base_name}...")
                    self.app_root.update_idletasks()

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
                        if current_canvas_for_drawing:
                            current_canvas_for_drawing.drawString(72, A4[1] - 72, f"Datei: {base_name} (nicht unterstützt)")
                            current_canvas_for_drawing.showPage()
                            if single_output_mode: reportlab_canvas_has_content = True
                        if single_output_mode and individual_output_path_for_direct_pdf and os.path.exists(individual_output_path_for_direct_pdf):
                            if individual_output_path_for_direct_pdf in temp_files_to_merge_in_single_mode:
                                temp_files_to_merge_in_single_mode.remove(individual_output_path_for_direct_pdf)
                            try: os.remove(individual_output_path_for_direct_pdf) 
                            except OSError: pass

                    if current_file_processed_successfully:
                        files_processed_this_run += 1
                    
                    if not single_output_mode and current_canvas_for_drawing and current_file_processed_successfully:
                        current_canvas_for_drawing.save()

                except Exception as file_e:
                    error_msg = f"Fehler bei {base_name}: {str(file_e)}"
                    errors_occurred.append(error_msg)
                    print(f"Error processing {base_name}: {file_e}")
                    if single_output_mode and individual_output_path_for_direct_pdf and os.path.exists(individual_output_path_for_direct_pdf):
                        if individual_output_path_for_direct_pdf in temp_files_to_merge_in_single_mode:
                           temp_files_to_merge_in_single_mode.remove(individual_output_path_for_direct_pdf)
                        try: os.remove(individual_output_path_for_direct_pdf) 
                        except OSError: pass
            
            if single_output_mode:
                if shared_reportlab_canvas:
                    if reportlab_canvas_has_content:
                        shared_reportlab_canvas.save()
                        temp_files_to_merge_in_single_mode.insert(0, reportlab_canvas_content_temp_path)
                    else:
                        try: os.remove(reportlab_canvas_content_temp_path)
                        except OSError: pass
                        reportlab_canvas_content_temp_path = None
                
                if files_processed_this_run > 0 and temp_files_to_merge_in_single_mode:
                    merger = PdfWriter()
                    for pdf_path in temp_files_to_merge_in_single_mode:
                        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                            try:
                                merger.append(pdf_path)
                            except Exception as merge_e:
                                errors_occurred.append(f"Fehler beim Mergen von {os.path.basename(pdf_path)}: {merge_e}")
                        elif os.path.exists(pdf_path):
                             errors_occurred.append(f"Temporäre Datei {os.path.basename(pdf_path)} war leer und wurde übersprungen.")
                    
                    if len(merger.pages) > 0 :
                        with open(output_final_pdf_path, 'wb') as f_out:
                            merger.write(f_out)
                    elif not errors_occurred:
                        errors_occurred.append("Keine Seiten konnten aus den ausgewählten Dateien generiert werden.")
                    merger.close()
                elif files_processed_this_run == 0 and not errors_occurred:
                     errors_occurred.append("Keine unterstützten Dateien für die Konvertierung gefunden oder verarbeitet.")
                
                for temp_file_path in temp_files_to_merge_in_single_mode:
                    if os.path.exists(temp_file_path):
                        try: os.remove(temp_file_path)
                        except OSError as e: print(f"Could not delete temp file {temp_file_path}: {e}")
                if reportlab_canvas_content_temp_path and os.path.exists(reportlab_canvas_content_temp_path):
                     try: os.remove(reportlab_canvas_content_temp_path)
                     except OSError as e: print(f"Could not delete rl_canvas temp file {reportlab_canvas_content_temp_path}: {e}")
            
            if not errors_occurred and files_processed_this_run > 0:
                messagebox.showinfo("Erfolg", f"{files_processed_this_run} Datei(en) erfolgreich zu PDF konvertiert.")
                self.file_conversion_status_label.config(text="Konvertierung erfolgreich!")
            elif errors_occurred:
                processed_msg = f"{files_processed_this_run} Datei(en) erfolgreich verarbeitet." if files_processed_this_run > 0 else "Keine Dateien erfolgreich verarbeitet."
                final_error_msg = f"{processed_msg}\n{len(errors_occurred)} Fehler aufgetreten:\n\n" + "\n".join(errors_occurred)
                messagebox.showerror("Konvertierung mit Fehlern", final_error_msg)
                self.file_conversion_status_label.config(text=f"Konvertierung mit {len(errors_occurred)} Fehlern abgeschlossen.")
            elif files_processed_this_run == 0:
                msg = "Keine Dateien verarbeitet."
                if errors_occurred : msg += "\nDetails:\n" + "\n".join(errors_occurred)
                else: msg += " Keine unterstützten Dateien ausgewählt."
                messagebox.showwarning("Keine Dateien verarbeitet", msg)
                self.file_conversion_status_label.config(text="Keine Dateien verarbeitet.")

            self.selected_files_for_conversion.clear()
            self.file_to_pdf_listbox.delete(0, tk.END)
            if self.view_mode_var.get() == "icons":
                self._refresh_icon_view() # Clear icons as well
            
        except Exception as e:
            messagebox.showerror("Schwerwiegender Fehler", f"Ein unerwarteter Fehler ist aufgetreten: {e}")
            self.file_conversion_status_label.config(text="Schwerwiegender Konvertierungsfehler.")
            for temp_file_path in temp_files_to_merge_in_single_mode:
                if os.path.exists(temp_file_path):
                    try: os.remove(temp_file_path)
                    except OSError: pass
            if reportlab_canvas_content_temp_path and os.path.exists(reportlab_canvas_content_temp_path):
                try: os.remove(reportlab_canvas_content_temp_path)
                except OSError: pass
            if single_output_mode and output_final_pdf_path and os.path.exists(output_final_pdf_path) and files_processed_this_run == 0:
                 try: os.remove(output_final_pdf_path)
                 except OSError: pass       

    def _convert_html_to_separate_pdf(self, html_file_path, output_pdf_path):
        try:
            with open(html_file_path, "r", encoding="utf-8") as source_html_file:
                html_content = source_html_file.read()
        except Exception as e:
            raise RuntimeError(f"Fehler beim Lesen der HTML-Datei {os.path.basename(html_file_path)}: {e}")
        
        try:
            with open(output_pdf_path, "wb") as result_file:
                pisa_status = pisa.CreatePDF(html_content, dest=result_file, encoding='utf-8')
            
            if pisa_status.err:
                if os.path.exists(output_pdf_path):
                    try: os.remove(output_pdf_path)
                    except OSError: pass 
                raise RuntimeError(f"xhtml2pdf Fehler für {os.path.basename(html_file_path)}: {pisa_status.err}")
        except Exception as e:
            if os.path.exists(output_pdf_path):
                try: os.remove(output_pdf_path)
                except OSError: pass
            raise RuntimeError(f"Fehler beim Konvertieren von HTML zu PDF ({os.path.basename(html_file_path)}): {e}")

    def _add_image_to_pdf(self, image_path, pdf_canvas):
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
        page_width, page_height = A4
        margin = 0.75 * inch
        line_height = 14
        font_name = "Helvetica"
        font_size = 10

        available_width = page_width - 2 * margin
        max_lines_per_page = int((page_height - 2 * margin) / line_height)

        lines = text_content.split('\n')
        
        current_line_on_page = 0
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
                
                text_object.textLine(sub_line)
                current_line_on_page += 1
        
        pdf_canvas.drawText(text_object) 
        pdf_canvas.showPage()

    def _add_text_file_to_pdf(self, file_path, pdf_canvas):
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
        base_name = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                rtf_content = f.read()
        except UnicodeDecodeError:
             try:
                with open(file_path, 'r', encoding='utf-8') as f:
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
        try:
            drawing = svg2rlg(file_path)
            if not drawing:
                raise ValueError("SVG konnte nicht geladen oder geparst werden.")
        except Exception as e:
            raise RuntimeError(f"Fehler beim Laden der SVG-Datei {os.path.basename(file_path)}: {e}")

        svg_width = drawing.width
        svg_height = drawing.height

        if svg_width <= 0 or svg_height <= 0:
            pdf_canvas.drawString(72, A4[1] - 72, f"SVG: {os.path.basename(file_path)}")
            pdf_canvas.drawString(72, A4[1] - 90, "SVG hat keine Dimensionen oder ist leer.")
            pdf_canvas.showPage()
            return

        page_width, page_height = A4
        margin = 0.5 * inch

        available_width = page_width - 2 * margin
        available_height = page_height - 2 * margin

        scale_w = available_width / svg_width
        scale_h = available_height / svg_height
        scale = min(scale_w, scale_h)

        if scale <= 0: scale = 1
        
        scaled_width = svg_width * scale
        scaled_height = svg_height * scale

        pos_x = (page_width - scaled_width) / 2
        pos_y = (page_height - scaled_height) / 2

        drawing.scale(scale, scale)
        drawing.width = scaled_width
        drawing.height = scaled_height
        
        pdf_canvas.setPageSize((page_width, page_height))
        drawing.drawOn(pdf_canvas, pos_x, pos_y)
        pdf_canvas.showPage() 