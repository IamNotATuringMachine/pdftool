# PDF and Image Utility

A Python tool with a graphical user interface (GUI) for common PDF and image manipulations.

## Features

- Merge multiple PDF files into one.
- Extract specific page ranges or individual pages from a PDF.
- Delete specific pages from a PDF.
- Convert JPG images to PDF (either one PDF per image or all images in a single PDF).
- Convert various other file types to PDF, including:
    - Images (PNG, BMP, GIF, TIFF, HEIC/HEIF)
    - Text files (.txt)
    - Rich Text Format (.rtf)
    - HTML files (.html, .htm)
    - SVG vector graphics (.svg)
    - Common office documents (Microsoft Word, Excel, PowerPoint; LibreOffice/OpenOffice Text, Spreadsheet, Presentation) to PDF.

## Prerequisites

- Python 3.x

## Important Notes on Office Document Conversion

For the best results and full support when converting office documents:

-   **Microsoft Office Formats (.doc, .docx, .xls, .xlsx, .ppt, .pptx):**
    -   It is highly recommended to have **Microsoft Office installed** on your system (primarily for Windows users). The tool will attempt to use installed MS Office applications for high-fidelity conversions.
-   **OpenDocument Formats (.odt, .ods, .odp) and Fallback:**
    -   It is highly recommended to have **LibreOffice installed** and its `soffice` command accessible (e.g., added to your system's PATH). LibreOffice provides robust conversion for OpenDocument Formats and also serves as a fallback for Microsoft Office formats if MS Office is not available or its conversion fails.

If these dependencies are not met, conversion of some office document types may not be possible or may result in lower fidelity.

## Setup and Installation

1.  **Clone the repository or download the source code.**
    ```bash
    # If you have git installed
    # git clone <repository_url>
    # cd <repository_folder>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    Activate the virtual environment:
    - Windows:
      ```bash
      .\venv\Scripts\activate
      ```
    - macOS/Linux:
      ```bash
      source venv/bin/activate
      ```

3.  **Install the required dependencies:**
    Run the `install_dependencies.sh` script (for Linux/macOS with bash) or install directly using pip:
    ```bash
    # For Linux/macOS (ensures the script is executable)
    # chmod +x install_dependencies.sh
    # ./install_dependencies.sh
    
    # Or directly using pip (works on all platforms with the venv activated)
    pip install -r requirements.txt
    ```

## How to Run

Once the setup is complete, you can run the application using:

```bash
python pdf_tool.py
```

## Usage

The application provides a tabbed interface for different operations. The main tab allows you to add various files for processing (conversion to PDF and merging into a single PDF, or conversion to individual PDFs).

-   **File Processing Tab:**
    -   Add PDF, image, text, HTML, SVG, and Office documents to the list.
    -   Choose to output all files into a single combined PDF or convert each to a separate PDF.
    -   Rearrange files in the list for merging order.
-   **Modify PDF Tab** (formerly Extract/Delete pages):
    -   Select a single PDF file.
    -   Extract a range of pages or specific pages to a new PDF.
    -   Delete specific pages from the PDF, saving the result as a new file.

Follow the on-screen instructions and use the file dialogs to select input files and specify output locations.

## Dependencies

The main dependencies include:

-   `PySide6` (for the GUI)
-   `PyPDF2` (for PDF manipulation)
-   `Pillow` (for image processing)
-   `reportlab` (for creating PDFs from text/images)
-   `xhtml2pdf`, `svglib`, `striprtf` (for HTML, SVG, RTF to PDF conversion)
-   `docx2pdf`, `pptxtopdf`, `pywin32` (for MS Office conversions, Windows-specific)

The complete list of Python packages is in `requirements.txt`. External software like **Microsoft Office** and **LibreOffice** may be required for full office document conversion capabilities as noted above. 