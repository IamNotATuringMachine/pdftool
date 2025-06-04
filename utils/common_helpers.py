def parse_page_ranges(pages_str, total_pages):
    if not pages_str.strip():
        raise ValueError("Seitenbereichsangabe ist leer.")
    
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
                    raise ValueError(f"Bereich '{part}' ist ungültig. Max. Seite: {total_pages}")
                pages_to_extract.update(range(start - 1, end)) 
            except ValueError as e:
                if "invalid literal" in str(e) or "ungültiges Literal" in str(e).lower():
                     raise ValueError(f"Ungültiges Bereichsformat: '{part}'. Muss Zahlen enthalten.")
                raise 
        else:
            try:
                page_num = int(part)
                if not (1 <= page_num <= total_pages):
                    raise ValueError(f"Seitenzahl '{part}' ist außerhalb des Bereichs. Max. Seite: {total_pages}")
                pages_to_extract.add(page_num - 1) 
            except ValueError:
                raise ValueError(f"Ungültige Seitenzahl: '{part}'. Muss eine Zahl sein.")
    
    if not pages_to_extract:
        raise ValueError("Keine gültigen Seiten für die Extraktion angegeben.")
        
    return sorted(list(pages_to_extract))

def parse_dropped_files(event_data):
    # event.data might be like: "{/path/to/file with spaces.pdf} {/another/path/file.jpg}"
    # Or on some systems, just a list of paths separated by spaces if they don't contain spaces themselves.
    # A more robust way is to look for "{" and "}"
    files = []
    if '{' in event_data and '}' in event_data:
        # Paths are enclosed in braces, possibly with spaces
        raw_paths = event_data.strip().split('} {')
        for raw_path in raw_paths:
            clean_path = raw_path.replace('{', '').replace('}', '').strip()
            if clean_path:
                files.append(clean_path)
    else:
        # Assume space-separated paths (might fail for paths with spaces if not braced)
        # This is a fallback, TkinterDnD usually braces paths with spaces.
        files = [f for f in event_data.split(' ') if f]
    return files 