# PDF and Image Utility

A Python tool with a graphical user interface (GUI) for common PDF and image manipulations.

## Features

- Merge multiple PDF files into one.
- Extract specific page ranges or individual pages from a PDF.
- Delete specific pages from a PDF.
- Convert JPG images to PDF (either one PDF per image or all images in a single PDF).

## Prerequisites

- Python 3.x

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
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

Once the setup is complete, you can run the application using:

```bash
python pdf_tool.py
```

## Usage

The application provides a tabbed interface for different operations:

-   **Merge PDFs**: Select multiple PDF files, arrange them in the desired order, and merge them into a single PDF.
-   **Extract PDF Pages**: Select a PDF file and specify a page range (e.g., "1-5") or individual pages (e.g., "1,3,8") to extract into a new PDF.
-   **Delete PDF Pages**: Select a PDF file and specify page numbers to remove. The modified PDF will be saved as a new file.
-   **JPG to PDF**: Select one or more JPG files. Choose whether to create a separate PDF for each JPG or a single PDF containing all JPGs on different pages.

Follow the on-screen instructions and use the file dialogs to select input files and specify output locations.

## Dependencies

-   `Tkinter` (usually comes with Python standard library)
-   `PyPDF2` (for PDF manipulation)
-   `Pillow` (for image processing)

These are listed in `requirements.txt`. 