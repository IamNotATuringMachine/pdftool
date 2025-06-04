# Defines various constants used throughout the application, especially for file handling.

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

# Define actually implemented and supported file types (Example, adjust as features are built)
# This might be more relevant for UI filtering if not all SUPPORTED_FILE_TYPES are fully convertible yet.
ACTUALLY_SUPPORTED_FILE_TYPES = [
    ("Bilder", "JPEG (*.jpg, *.jpeg), PNG (*.png), BMP (*.bmp), GIF (*.gif), TIFF (*.tif, *.tiff), HEIC/HEIF (*.heic, *.heif)"),
    ("Textdateien", "Einfacher Text (*.txt)"),
    ("Rich Text Format", "RTF (*.rtf)"),
    ("HTML-Dateien", "HTML (*.html, *.htm)"),
    ("Vektorgrafiken", "SVG (*.svg)")
]

ALL_SUPPORTED_EXTENSIONS_DESC = "Alle unterstützten Dateien"
ALL_SUPPORTED_EXTENSIONS_PATTERNS = "*.doc *.docx *.xls *.xlsx *.ppt *.pptx *.jpg *.jpeg *.png *.gif *.tif *.tiff *.bmp *.heic *.heif *.svg *.txt *.rtf *.odt *.ods *.odp *.html *.htm *.pub *.vsd *.vsdx *.eml *.msg"

# Create a tuple for filetypes dialog, combining all supported and individual types
FILETYPES_FOR_DIALOG = [(ALL_SUPPORTED_EXTENSIONS_DESC, ALL_SUPPORTED_EXTENSIONS_PATTERNS)] + SUPPORTED_FILE_TYPES

# For drag and drop validation (flat list of lowercased extensions with dot)
ALL_SUPPORTED_EXT_PATTERNS_LIST = [
    item.replace("*","") for sublist in FILETYPES_FOR_DIALOG[:-1] # Exclude "Alle Dateien *.*"
    for item in sublist[1].split()
]

# Specific extension lists for conversion logic
IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".heic", ".heif"]
TEXT_EXTENSIONS = [".txt"]
RTF_EXTENSIONS = [".rtf"]
HTML_EXTENSIONS = [".html", ".htm"]
SVG_EXTENSIONS = [".svg"]

# It might also be useful to have a mapping from extension to a more general type
# e.g., EXT_TO_TYPE_MAP = {ext: "image" for ext in IMAGE_EXTENSIONS} ... etc. 