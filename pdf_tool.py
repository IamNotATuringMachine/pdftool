import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PyPDF2 import PdfWriter, PdfReader # Added PdfReader
from PIL import Image, UnidentifiedImageError # Added UnidentifiedImageError
import os # For path manipulations

class PDFToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF & Image Utility")
        self.root.geometry("800x600")

        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)

        # Create frames for each functionality
        self.merge_frame = ttk.Frame(self.notebook)
        self.split_frame = ttk.Frame(self.notebook)
        self.delete_frame = ttk.Frame(self.notebook)
        self.jpg_to_pdf_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.merge_frame, text='Merge PDFs')
        self.notebook.add(self.split_frame, text='Extract PDF Pages')
        self.notebook.add(self.delete_frame, text='Delete PDF Pages')
        self.notebook.add(self.jpg_to_pdf_frame, text='JPG to PDF')

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
        controls_frame = ttk.LabelFrame(self.merge_frame, text="Files to Merge")
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

        add_button = ttk.Button(buttons_frame, text="Add PDF", command=self._add_pdf_to_merge_list)
        add_button.pack(fill="x", pady=2)

        remove_button = ttk.Button(buttons_frame, text="Remove Selected", command=self._remove_pdf_from_merge_list)
        remove_button.pack(fill="x", pady=2)

        move_up_button = ttk.Button(buttons_frame, text="Move Up", command=self._move_merge_item_up)
        move_up_button.pack(fill="x", pady=2)

        move_down_button = ttk.Button(buttons_frame, text="Move Down", command=self._move_merge_item_down)
        move_down_button.pack(fill="x", pady=2)
        
        # Merge button and status
        action_frame = ttk.Frame(self.merge_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        merge_button = ttk.Button(action_frame, text="Merge PDFs and Save", command=self._execute_merge_pdfs)
        merge_button.pack(pady=5)

        self.merge_status_label = ttk.Label(action_frame, text="")
        self.merge_status_label.pack(pady=5)

    def _add_pdf_to_merge_list(self):
        files = filedialog.askopenfilenames(
            title="Select PDF files",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_merge_files:
                    self.selected_merge_files.append(file_path)
                    self.merge_listbox.insert(tk.END, os.path.basename(file_path))
            self.merge_status_label.config(text=f"{len(files)} file(s) added.")

    def _remove_pdf_from_merge_list(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            del self.selected_merge_files[index]
            self.merge_listbox.delete(index)
            self.merge_status_label.config(text="File removed.")
        else:
            messagebox.showwarning("No Selection", "Please select a file to remove.")

    def _move_merge_item_up(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            if index > 0:
                # Move in list of paths
                self.selected_merge_files[index], self.selected_merge_files[index-1] = self.selected_merge_files[index-1], self.selected_merge_files[index]
                # Move in listbox
                text = self.merge_listbox.get(index)
                self.merge_listbox.delete(index)
                self.merge_listbox.insert(index-1, text)
                self.merge_listbox.selection_set(index-1)
                self.merge_status_label.config(text="File moved up.")
        else:
            messagebox.showwarning("No Selection", "Please select a file to move.")

    def _move_merge_item_down(self):
        selected_index = self.merge_listbox.curselection()
        if selected_index:
            index = selected_index[0]
            if index < self.merge_listbox.size() - 1:
                # Move in list of paths
                self.selected_merge_files[index], self.selected_merge_files[index+1] = self.selected_merge_files[index+1], self.selected_merge_files[index]
                # Move in listbox
                text = self.merge_listbox.get(index)
                self.merge_listbox.delete(index)
                self.merge_listbox.insert(index+1, text)
                self.merge_listbox.selection_set(index+1)
                self.merge_status_label.config(text="File moved down.")
        else:
            messagebox.showwarning("No Selection", "Please select a file to move.")

    def _execute_merge_pdfs(self):
        if not self.selected_merge_files or len(self.selected_merge_files) < 2:
            messagebox.showwarning("Not Enough Files", "Please select at least two PDF files to merge.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
            title="Save Merged PDF As"
        )

        if not output_filename:
            self.merge_status_label.config(text="Merge cancelled.")
            return

        pdf_writer = PdfWriter()
        
        try:
            self.merge_status_label.config(text="Merging...")
            self.root.update_idletasks() # Update GUI

            for filename in self.selected_merge_files:
                pdf_writer.append(filename)
            
            with open(output_filename, 'wb') as out:
                pdf_writer.write(out)
            
            pdf_writer.close() # Close the writer object
            messagebox.showinfo("Success", f"PDFs merged successfully into {os.path.basename(output_filename)}")
            self.merge_status_label.config(text="Merge successful!")
            # Clear list after successful merge
            self.selected_merge_files.clear()
            self.merge_listbox.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error Merging PDFs", f"An error occurred: {e}")
            self.merge_status_label.config(text="Error during merge.")

    def _create_split_widgets(self):
        controls_frame = ttk.LabelFrame(self.split_frame, text="Select PDF and Specify Pages")
        controls_frame.pack(padx=10, pady=10, fill="x")

        # File selection
        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="Select PDF", command=self._select_pdf_for_split)
        select_button.pack(side=tk.LEFT, padx=5)

        self.split_selected_file_label = ttk.Label(file_select_frame, text="No file selected.")
        self.split_selected_file_label.pack(side=tk.LEFT, padx=5)

        # Page range input
        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Pages/Ranges (e.g., 1-3, 5, 7-9):")
        pages_label.pack(side=tk.LEFT, padx=5)

        self.split_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.split_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        # Action button and status
        action_frame = ttk.Frame(self.split_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        extract_button = ttk.Button(action_frame, text="Extract Pages and Save", command=self._execute_split_pdf)
        extract_button.pack(pady=5)

        self.split_status_label = ttk.Label(action_frame, text="")
        self.split_status_label.pack(pady=5)

    def _select_pdf_for_split(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if file_path:
            self.split_input_pdf_path = file_path
            self.split_selected_file_label.config(text=os.path.basename(file_path))
            self.split_status_label.config(text="File selected. Enter page ranges.")
        else:
            self.split_input_pdf_path = None
            self.split_selected_file_label.config(text="No file selected.")
            self.split_status_label.config(text="File selection cancelled.")

    def _parse_page_ranges(self, pages_str, total_pages):
        """Parses a string like '1-3,5,7-9' into a sorted list of unique 0-indexed page numbers."""
        if not pages_str.strip():
            raise ValueError("Page range string is empty.")
        
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
                        raise ValueError(f"Range '{part}' is invalid. Max page: {total_pages}")
                    pages_to_extract.update(range(start - 1, end)) # 0-indexed
                except ValueError as e:
                    if "invalid literal" in str(e):
                         raise ValueError(f"Invalid range format: '{part}'. Must be numbers.")
                    raise # re-raise other ValueErrors (like from the check above)
            else:
                try:
                    page_num = int(part)
                    if not (1 <= page_num <= total_pages):
                        raise ValueError(f"Page number '{part}' is out of bounds. Max page: {total_pages}")
                    pages_to_extract.add(page_num - 1) # 0-indexed
                except ValueError:
                    raise ValueError(f"Invalid page number: '{part}'. Must be a number.")
        
        if not pages_to_extract:
            raise ValueError("No valid pages specified for extraction.")
            
        return sorted(list(pages_to_extract))

    def _execute_split_pdf(self):
        if not self.split_input_pdf_path:
            messagebox.showwarning("No PDF Selected", "Please select a PDF file first.")
            return

        pages_str = self.split_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("No Pages Specified", "Please enter the page numbers or ranges to extract.")
            return

        try:
            input_pdf = PdfReader(self.split_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_extract = self._parse_page_ranges(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Invalid Page Input", str(e))
            self.split_status_label.config(text=f"Error: {e}")
            return
        except Exception as e: # Catch PyPDF2 errors or other file errors
            messagebox.showerror("Error Reading PDF", f"Could not read PDF: {e}")
            self.split_status_label.config(text="Error reading PDF.")
            return

        if not pages_to_extract:
            messagebox.showinfo("No Pages to Extract", "The specified pages do not result in any pages to extract.")
            self.split_status_label.config(text="No pages to extract based on input.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
            title="Save Extracted Pages As",
            initialfile=f"{os.path.splitext(os.path.basename(self.split_input_pdf_path))[0]}_extracted.pdf"
        )

        if not output_filename:
            self.split_status_label.config(text="Extraction cancelled.")
            return

        pdf_writer = PdfWriter()
        try:
            self.split_status_label.config(text="Extracting pages...")
            self.root.update_idletasks()

            for page_num in pages_to_extract:
                pdf_writer.add_page(input_pdf.pages[page_num])
            
            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Success", f"Pages extracted successfully to {os.path.basename(output_filename)}")
            self.split_status_label.config(text="Extraction successful!")
            # Reset fields
            # self.split_input_pdf_path = None
            # self.split_selected_file_label.config(text="No file selected.")
            # self.split_pages_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error Extracting Pages", f"An error occurred: {e}")
            self.split_status_label.config(text="Error during extraction.")

    def _create_delete_widgets(self):
        controls_frame = ttk.LabelFrame(self.delete_frame, text="Select PDF and Specify Pages to Delete")
        controls_frame.pack(padx=10, pady=10, fill="x")

        # File selection
        file_select_frame = ttk.Frame(controls_frame)
        file_select_frame.pack(fill="x", pady=5)

        select_button = ttk.Button(file_select_frame, text="Select PDF", command=self._select_pdf_for_delete)
        select_button.pack(side=tk.LEFT, padx=5)

        self.delete_selected_file_label = ttk.Label(file_select_frame, text="No file selected.")
        self.delete_selected_file_label.pack(side=tk.LEFT, padx=5)

        # Page input for deletion
        page_input_frame = ttk.Frame(controls_frame)
        page_input_frame.pack(fill="x", pady=5)

        pages_label = ttk.Label(page_input_frame, text="Pages to Delete (e.g., 1, 3, 5-7):")
        pages_label.pack(side=tk.LEFT, padx=5)

        self.delete_pages_entry = ttk.Entry(page_input_frame, width=40)
        self.delete_pages_entry.pack(side=tk.LEFT, padx=5, expand=True, fill="x")

        # Action button and status
        action_frame = ttk.Frame(self.delete_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        delete_button = ttk.Button(action_frame, text="Delete Pages and Save", command=self._execute_delete_pages)
        delete_button.pack(pady=5)

        self.delete_status_label = ttk.Label(action_frame, text="")
        self.delete_status_label.pack(pady=5)

    def _select_pdf_for_delete(self):
        file_path = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*"))
        )
        if file_path:
            self.delete_input_pdf_path = file_path
            self.delete_selected_file_label.config(text=os.path.basename(file_path))
            self.delete_status_label.config(text="File selected. Enter pages to delete.")
        else:
            self.delete_input_pdf_path = None
            self.delete_selected_file_label.config(text="No file selected.")
            self.delete_status_label.config(text="File selection cancelled.")

    def _parse_pages_to_delete(self, pages_str, total_pages):
        """Parses a string like '1,3,5-7' into a sorted list of unique 0-indexed page numbers for DELETION."""
        # This can reuse/adapt _parse_page_ranges logic. For deletion, ranges are also valid.
        # The core parsing logic is identical to _parse_page_ranges.
        return self._parse_page_ranges(pages_str, total_pages) # Reusing the same robust parser

    def _execute_delete_pages(self):
        if not self.delete_input_pdf_path:
            messagebox.showwarning("No PDF Selected", "Please select a PDF file first.")
            return

        pages_str = self.delete_pages_entry.get()
        if not pages_str:
            messagebox.showwarning("No Pages Specified", "Please enter the page numbers or ranges to delete.")
            return

        try:
            input_pdf = PdfReader(self.delete_input_pdf_path)
            total_pages = len(input_pdf.pages)
            pages_to_delete_indices = self._parse_pages_to_delete(pages_str, total_pages)
        except ValueError as e:
            messagebox.showerror("Invalid Page Input", str(e))
            self.delete_status_label.config(text=f"Error: {e}")
            return
        except Exception as e: # Catch PyPDF2 errors or other file errors
            messagebox.showerror("Error Reading PDF", f"Could not read PDF: {e}")
            self.delete_status_label.config(text="Error reading PDF.")
            return

        if not pages_to_delete_indices:
            messagebox.showinfo("No Valid Pages", "No valid pages specified for deletion.")
            self.delete_status_label.config(text="No valid pages to delete.")
            return
        
        if all(p_idx in pages_to_delete_indices for p_idx in range(total_pages)):
            messagebox.showwarning("All Pages Selected", "You have selected all pages for deletion. This would result in an empty PDF.")
            self.delete_status_label.config(text="Cannot delete all pages.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
            title="Save Modified PDF As",
            initialfile=f"{os.path.splitext(os.path.basename(self.delete_input_pdf_path))[0]}_modified.pdf"
        )

        if not output_filename:
            self.delete_status_label.config(text="Deletion cancelled.")
            return

        pdf_writer = PdfWriter()
        try:
            self.delete_status_label.config(text="Deleting pages...")
            self.root.update_idletasks()

            for i in range(total_pages):
                if i not in pages_to_delete_indices:
                    pdf_writer.add_page(input_pdf.pages[i])
            
            if len(pdf_writer.pages) == 0:
                 messagebox.showwarning("Empty Result", "All specified pages were deleted, resulting in an empty PDF. File not saved.")
                 self.delete_status_label.config(text="Resulting PDF would be empty. Operation aborted.")
                 pdf_writer.close()
                 return

            with open(output_filename, 'wb') as out_pdf:
                pdf_writer.write(out_pdf)
            
            pdf_writer.close()
            messagebox.showinfo("Success", f"Pages deleted successfully. Saved to {os.path.basename(output_filename)}")
            self.delete_status_label.config(text="Deletion successful!")
            # Reset fields
            # self.delete_input_pdf_path = None
            # self.delete_selected_file_label.config(text="No file selected.")
            # self.delete_pages_entry.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error Deleting Pages", f"An error occurred: {e}")
            self.delete_status_label.config(text="Error during deletion.")

    def _create_jpg_to_pdf_widgets(self):
        controls_frame = ttk.LabelFrame(self.jpg_to_pdf_frame, text="Select JPG Files")
        controls_frame.pack(padx=10, pady=10, fill="x")

        # Listbox for JPG files
        list_frame = ttk.Frame(controls_frame)
        list_frame.pack(fill="both", expand=True, pady=5)

        self.jpg_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10) # Allow multiple selection for removal
        self.jpg_listbox.pack(side=tk.LEFT, fill="both", expand=True, padx=5)

        jpg_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.jpg_listbox.yview)
        jpg_scrollbar.pack(side=tk.LEFT, fill="y")
        self.jpg_listbox.config(yscrollcommand=jpg_scrollbar.set)

        # Buttons for JPG list management
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill="x", pady=5)

        add_jpg_button = ttk.Button(buttons_frame, text="Add JPG(s)", command=self._add_jpg_files_to_list)
        add_jpg_button.pack(side=tk.LEFT, padx=5)

        remove_jpg_button = ttk.Button(buttons_frame, text="Remove Selected JPG(s)", command=self._remove_jpg_from_list)
        remove_jpg_button.pack(side=tk.LEFT, padx=5)

        # Conversion options (Simplified based on re-interpretation)
        # The user request seems to imply that multiple JPGs always go into one PDF.
        # "ob jede JPG-Datei in eine separate Seite einer neuen PDF-Datei umgewandelt wird 
        #  oder ob alle ausgewählten JPGs jeweils auf einer eigenen Seite in derselben PDF-Datei zusammengefasst werden."
        # Both options lead to: selected JPGs -> one PDF with multiple pages.
        # Thus, no radio button for mode needed here unless further clarification suggests multiple output PDFs.
        
        options_frame = ttk.Frame(self.jpg_to_pdf_frame) # Kept for potential future options
        options_frame.pack(padx=10, pady=5, fill="x")
        # Example: If we needed options later for quality or single/multiple PDF outputs
        # self.jpg_conversion_mode = tk.StringVar(value="single_pdf")
        # ttk.Radiobutton(options_frame, text="Combine all JPGs into one PDF", variable=self.jpg_conversion_mode, value="single_pdf").pack(anchor=tk.W)
        # ttk.Radiobutton(options_frame, text="Convert each JPG to a separate PDF", variable=self.jpg_conversion_mode, value="multiple_pdfs").pack(anchor=tk.W)

        # Action button and status
        action_frame = ttk.Frame(self.jpg_to_pdf_frame)
        action_frame.pack(padx=10, pady=10, fill="x")

        convert_button = ttk.Button(action_frame, text="Convert JPG(s) to PDF and Save", command=self._execute_jpg_to_pdf)
        convert_button.pack(pady=5)

        self.jpg_to_pdf_status_label = ttk.Label(action_frame, text="")
        self.jpg_to_pdf_status_label.pack(pady=5)

    def _add_jpg_files_to_list(self):
        files = filedialog.askopenfilenames(
            title="Select JPG files",
            filetypes=(("JPEG files", "*.jpg *.jpeg"), ("All files", "*.*"))
        )
        if files:
            for file_path in files:
                if file_path not in self.selected_jpg_files:
                    self.selected_jpg_files.append(file_path)
                    self.jpg_listbox.insert(tk.END, os.path.basename(file_path))
            self.jpg_to_pdf_status_label.config(text=f"{len(files)} JPG file(s) added.")

    def _remove_jpg_from_list(self):
        selected_indices = self.jpg_listbox.curselection()
        if selected_indices:
            # Iterate in reverse to avoid index shifting issues while deleting
            for index in sorted(selected_indices, reverse=True):
                del self.selected_jpg_files[index]
                self.jpg_listbox.delete(index)
            self.jpg_to_pdf_status_label.config(text="Selected JPG file(s) removed.")
        else:
            messagebox.showwarning("No Selection", "Please select JPG file(s) to remove.")

    def _execute_jpg_to_pdf(self):
        if not self.selected_jpg_files:
            messagebox.showwarning("No JPG Files", "Please select at least one JPG file to convert.")
            return

        output_filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")),
            title="Save PDF As"
        )

        if not output_filename:
            self.jpg_to_pdf_status_label.config(text="Conversion cancelled.")
            return

        try:
            self.jpg_to_pdf_status_label.config(text="Converting JPG(s) to PDF...")
            self.root.update_idletasks()

            images_to_save = []
            first_image = None

            for jpg_path in self.selected_jpg_files:
                img = Image.open(jpg_path)
                # Ensure image is in a mode compatible with PDF saving (e.g., RGB)
                # Some images (like RGBA or P mode with transparency) might cause issues if not converted.
                if img.mode == 'RGBA' or img.mode == 'P':
                    img = img.convert('RGB') # Convert to RGB, discarding alpha or handling palette
                
                if not first_image:
                    first_image = img
                else:
                    images_to_save.append(img)
            
            if first_image:
                first_image.save(
                    output_filename, 
                    save_all=True, 
                    append_images=images_to_save # Appends the rest of the images
                )
                messagebox.showinfo("Success", f"JPG(s) converted successfully to {os.path.basename(output_filename)}")
                self.jpg_to_pdf_status_label.config(text="Conversion successful!")
                # Clear list after successful conversion
                self.selected_jpg_files.clear()
                self.jpg_listbox.delete(0, tk.END)
            else:
                # Should not happen if self.selected_jpg_files is not empty, but as a safeguard
                messagebox.showerror("Error", "No images processed for PDF conversion.")
                self.jpg_to_pdf_status_label.config(text="Error: No images to convert.")

        except FileNotFoundError as e:
            messagebox.showerror("File Not Found", f"Error: {e.filename} not found.")
            self.jpg_to_pdf_status_label.config(text="Error: One or more JPG files not found.")
        except UnidentifiedImageError: # From Pillow, if a file is not a valid image
             messagebox.showerror("Invalid Image", f"One of the selected files is not a valid JPG or is corrupted.")
             self.jpg_to_pdf_status_label.config(text="Error: Invalid image file detected.")
        except Exception as e:
            messagebox.showerror("Error Converting JPG to PDF", f"An error occurred: {e}")
            self.jpg_to_pdf_status_label.config(text="Error during conversion.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFToolApp(root)
    root.mainloop() 