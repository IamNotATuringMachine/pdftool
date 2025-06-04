#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for diagnosing PDF conversion issues.
This script helps identify why file conversions might be failing.
"""

import os
import sys
import tempfile
import subprocess
import platform

# Add the current directory to Python path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_dependencies():
    """Test all dependencies and conversion tools."""
    print("=== DIAGNOSE DER PDF-KONVERTIERUNGS-ABHÄNGIGKEITEN ===\n")
    
    results = {}
    
    # 1. Python-Pakete testen
    print("1. PYTHON-PAKETE:")
    python_packages = [
        ('PySide6', 'PySide6'),
        ('PIL/Pillow', 'PIL'),
        ('PyPDF2', 'PyPDF2'),
        ('reportlab', 'reportlab'),
        ('xhtml2pdf', 'xhtml2pdf'),
        ('svglib', 'svglib'),
        ('striprtf', 'striprtf'),
        ('pillow-heif', 'pillow_heif'),
    ]
    
    for name, module in python_packages:
        try:
            __import__(module)
            print(f"  ✓ {name}: Installiert")
            results[name] = True
        except ImportError as e:
            print(f"  ✗ {name}: FEHLT - {e}")
            results[name] = False
    
    # 2. Windows-spezifische Pakete testen (nur auf Windows)
    if os.name == 'nt':
        print("\n2. WINDOWS-SPEZIFISCHE PAKETE:")
        windows_packages = [
            ('win32com', 'win32com.client'),
            ('pythoncom', 'pythoncom'),
            ('docx2pdf', 'docx2pdf'),
            ('pptxtopdf', 'pptxtopdf'),
        ]
        
        for name, module in windows_packages:
            try:
                __import__(module)
                print(f"  ✓ {name}: Installiert")
                results[name] = True
            except ImportError as e:
                print(f"  ✗ {name}: FEHLT - {e}")
                results[name] = False
    
    # 3. LibreOffice testen
    print("\n3. LIBREOFFICE:")
    soffice_path = find_libreoffice()
    if soffice_path:
        print(f"  ✓ LibreOffice gefunden: {soffice_path}")
        results['LibreOffice'] = True
        
        # Test LibreOffice conversion
        try:
            test_result = test_libreoffice_conversion(soffice_path)
            if test_result:
                print("  ✓ LibreOffice Konvertierung: Funktioniert")
            else:
                print("  ✗ LibreOffice Konvertierung: FEHLER")
        except Exception as e:
            print(f"  ✗ LibreOffice Konvertierung: FEHLER - {e}")
    else:
        print("  ✗ LibreOffice: NICHT GEFUNDEN")
        results['LibreOffice'] = False
    
    # 4. MS Office testen (nur auf Windows)
    if os.name == 'nt':
        print("\n4. MICROSOFT OFFICE:")
        office_apps = [
            ('Word.Application', 'MS Word'),
            ('Excel.Application', 'MS Excel'),
            ('PowerPoint.Application', 'MS PowerPoint')
        ]
        
        for app_name, display_name in office_apps:
            available = test_ms_office_app(app_name)
            if available:
                print(f"  ✓ {display_name}: Verfügbar")
                results[display_name] = True
            else:
                print(f"  ✗ {display_name}: NICHT VERFÜGBAR")
                results[display_name] = False
    
    # 5. System-Info
    print("\n5. SYSTEM-INFORMATIONEN:")
    print(f"  Betriebssystem: {platform.system()} {platform.release()}")
    print(f"  Python-Version: {sys.version}")
    print(f"  Aktuelles Verzeichnis: {os.getcwd()}")
    
    # 6. Empfehlungen basierend auf Ergebnissen
    print("\n=== EMPFEHLUNGEN ===")
    
    missing_critical = []
    if not results.get('PIL/Pillow', False):
        missing_critical.append("pip install Pillow")
    if not results.get('PyPDF2', False):
        missing_critical.append("pip install PyPDF2") 
    if not results.get('reportlab', False):
        missing_critical.append("pip install reportlab")
    if not results.get('xhtml2pdf', False):
        missing_critical.append("pip install xhtml2pdf")
    if not results.get('svglib', False):
        missing_critical.append("pip install svglib")
    if not results.get('striprtf', False):
        missing_critical.append("pip install striprtf")
    
    if missing_critical:
        print("KRITISCHE PAKETE FEHLEN:")
        for cmd in missing_critical:
            print(f"  {cmd}")
    
    if not results.get('LibreOffice', False):
        print("\nLibreOffice wird für Office-Dokumente empfohlen:")
        print("  Download: https://www.libreoffice.org/download/download/")
    
    if os.name == 'nt':
        windows_missing = []
        if not results.get('win32com', False):
            windows_missing.append("pip install pywin32")
        if not results.get('docx2pdf', False):
            windows_missing.append("pip install docx2pdf")
        if not results.get('pptxtopdf', False):
            windows_missing.append("pip install pptxtopdf")
        
        if windows_missing:
            print("\nOptionale Windows-Pakete für bessere Office-Unterstützung:")
            for cmd in windows_missing:
                print(f"  {cmd}")
    
    return results

def find_libreoffice():
    """Find LibreOffice soffice executable."""
    system = platform.system()
    
    if system == "Windows":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        possible_paths = [
            os.path.join(program_files, "LibreOffice", "program", "soffice.exe"),
            os.path.join(program_files_x86, "LibreOffice", "program", "soffice.exe"),
        ]
    elif system == "Linux":
        possible_paths = [
            "/usr/bin/soffice",
            "/usr/local/bin/soffice",
            "/opt/libreoffice/program/soffice",
        ]
    elif system == "Darwin":  # macOS
        possible_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        ]
    else:
        return None

    for path in possible_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    return None

def test_libreoffice_conversion(soffice_path):
    """Test LibreOffice conversion with a simple text file."""
    try:
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as temp_txt:
            temp_txt.write("Test für LibreOffice Konvertierung\nDies ist ein Test.")
            temp_txt_path = temp_txt.name
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                soffice_path,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", temp_dir,
                temp_txt_path
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Check if PDF was created
            base_name = os.path.splitext(os.path.basename(temp_txt_path))[0]
            pdf_path = os.path.join(temp_dir, base_name + ".pdf")
            
            success = os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0
            
            # Clean up
            os.unlink(temp_txt_path)
            
            return success
            
    except Exception as e:
        print(f"LibreOffice Test-Fehler: {e}")
        return False

def test_ms_office_app(app_name):
    """Test if MS Office application is available."""
    if os.name != 'nt':
        return False
    
    try:
        import pythoncom
        import win32com.client
        
        pythoncom.CoInitialize()
        try:
            win32com.client.Dispatch(app_name)
            return True
        except:
            return False
        finally:
            pythoncom.CoUninitialize()
    except:
        return False

def test_file_conversion(file_path):
    """Test conversion of a specific file."""
    if not os.path.exists(file_path):
        print(f"Datei nicht gefunden: {file_path}")
        return
    
    print(f"\n=== TEST KONVERTIERUNG: {os.path.basename(file_path)} ===")
    
    try:
        # Initialize QApplication if needed
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        from gui.file_processing_tab import FileProcessingTab
        
        # Create a test instance
        test_tab = FileProcessingTab()
        
        # Test the file
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        print(f"Dateierweiterung: {ext}")
        
        # Check which conversion method would be used
        from utils.constants import (
            IMAGE_EXTENSIONS, TEXT_EXTENSIONS, RTF_EXTENSIONS, 
            HTML_EXTENSIONS, SVG_EXTENSIONS, MS_WORD_EXTENSIONS,
            MS_EXCEL_EXTENSIONS, MS_POWERPOINT_EXTENSIONS,
            ODF_TEXT_EXTENSIONS, ODF_SPREADSHEET_EXTENSIONS, ODF_PRESENTATION_EXTENSIONS
        )
        
        if ext == ".pdf":
            print("Dateityp: PDF (bereits PDF)")
        elif ext in IMAGE_EXTENSIONS:
            print("Dateityp: Bild")
            # Test image conversion
            try:
                from reportlab.pdfgen import canvas
                import tempfile
                import io
                from PyPDF2 import PdfReader
                
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                    temp_pdf_path = temp_pdf.name
                
                try:
                    img_pdf_bytes = io.BytesIO()
                    pdf_canvas = canvas.Canvas(img_pdf_bytes, pagesize=(595, 842))  # A4
                    success = test_tab._add_image_to_pdf_canvas(file_path, pdf_canvas)
                    if success:
                        pdf_canvas.save()
                        print("✓ Bildkonvertierung erfolgreich!")
                    else:
                        print("✗ Bildkonvertierung fehlgeschlagen")
                finally:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
            except Exception as e:
                print(f"✗ Bildkonvertierung Fehler: {e}")
                
        elif ext in TEXT_EXTENSIONS:
            print("Dateityp: Text")
            # Test text conversion
            try:
                from reportlab.pdfgen import canvas
                import tempfile
                
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                    temp_pdf_path = temp_pdf.name
                
                try:
                    from reportlab.lib.pagesizes import A4
                    pdf_canvas = canvas.Canvas(temp_pdf_path, pagesize=A4)
                    success = test_tab._add_text_file_to_pdf_canvas(file_path, pdf_canvas)
                    pdf_canvas.save()
                    if success and os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                        print(f"✓ Textkonvertierung erfolgreich! PDF-Größe: {os.path.getsize(temp_pdf_path)} Bytes")
                    else:
                        print("✗ Textkonvertierung fehlgeschlagen")
                finally:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
            except Exception as e:
                print(f"✗ Textkonvertierung Fehler: {e}")
                
        elif ext in RTF_EXTENSIONS:
            print("Dateityp: RTF")
        elif ext in HTML_EXTENSIONS:
            print("Dateityp: HTML")
        elif ext in SVG_EXTENSIONS:
            print("Dateityp: SVG")
        elif ext in (MS_WORD_EXTENSIONS + MS_EXCEL_EXTENSIONS + MS_POWERPOINT_EXTENSIONS +
                     ODF_TEXT_EXTENSIONS + ODF_SPREADSHEET_EXTENSIONS + ODF_PRESENTATION_EXTENSIONS):
            print("Dateityp: Office-Dokument")
            
            # Test office conversion
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
                temp_pdf_path = temp_pdf.name
            
            try:
                success = test_tab._convert_office_to_pdf_native(file_path, temp_pdf_path)
                if success and os.path.exists(temp_pdf_path) and os.path.getsize(temp_pdf_path) > 0:
                    print(f"✓ Konvertierung erfolgreich! PDF-Größe: {os.path.getsize(temp_pdf_path)} Bytes")
                else:
                    print("✗ Konvertierung fehlgeschlagen")
            finally:
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
        else:
            print(f"Dateityp: Unbekannt ({ext})")
        
    except Exception as e:
        print(f"Fehler beim Test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific file
        file_path = sys.argv[1]
        test_dependencies()
        test_file_conversion(file_path)
    else:
        # General dependency test
        test_dependencies()
        print("\nUm eine spezifische Datei zu testen, verwenden Sie:")
        print(f"python {sys.argv[0]} <dateipfad>") 