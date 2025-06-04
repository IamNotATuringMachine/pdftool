"""
Modern Apple-inspired styling for the PDF Tool GUI
"""

# Color palette inspired by Apple's design - Light Theme
LIGHT_COLORS = {
    # Main colors
    'primary': '#007AFF',      # Apple Blue
    'secondary': '#34C759',    # Apple Green
    'accent': '#FF9500',       # Apple Orange
    'danger': '#FF3B30',       # Apple Red
    
    # Neutral colors
    'background': '#F2F2F7',   # Light gray background
    'surface': '#FFFFFF',      # White surface
    'card': '#FFFFFF',         # Card background
    'border': '#E5E5EA',       # Light border
    'separator': '#D1D1D6',    # Separator line
    
    # Text colors
    'text_primary': '#000000',     # Black text
    'text_secondary': '#8E8E93',   # Gray text
    'text_tertiary': '#C7C7CC',    # Light gray text
    'text_on_color': '#FFFFFF',    # White text on colored backgrounds
    
    # Interactive states
    'hover': '#E3F2FD',        # Light blue hover (background for elements like list items)
    'pressed': '#BBDEFB',      # Darker blue pressed
    'disabled': '#F2F2F7',     # Disabled background
    'disabled_text': '#C7C7CC', # Disabled text
    'button_hover': '#0069E0', # Specific for button hover
    'button_pressed': '#0052B3', # Specific for button pressed
    'secondary_button_bg': '#EAEAEB',
    'secondary_button_hover': '#DBDBDC',
    'secondary_button_pressed': '#CFCFCF',
    'success_button_hover': '#2FA84F',
    'success_button_pressed': '#288F43',
    'danger_button_hover': '#CC2B20',
    'danger_button_pressed': '#991F17',
}

# Dark Theme Color Palette
DARK_COLORS = {
    # Main colors (can remain similar or be adjusted for dark mode contrast)
    'primary': '#0A84FF',      # Brighter Apple Blue for dark mode
    'secondary': '#30D158',    # Brighter Apple Green
    'accent': '#FF9F0A',       # Brighter Apple Orange
    'danger': '#FF453A',       # Brighter Apple Red

    # Neutral colors
    'background': '#1C1C1E',   # Dark gray background (almost black)
    'surface': '#2C2C2E',      # Slightly lighter dark gray for surfaces
    'card': '#2C2C2E',         # Card background
    'border': '#38383A',       # Darker border
    'separator': '#38383A',    # Separator line (same as border for consistency)

    # Text colors
    'text_primary': '#FFFFFF',     # White text
    'text_secondary': '#8E8E93',   # Lighter Gray text (can be same as light for secondary)
    'text_tertiary': '#48484A',    # Darker gray text (less prominent)
    'text_on_color': '#FFFFFF',    # White text on colored backgrounds (usually stays white)

    # Interactive states
    'hover': '#3A3A3C',        # Darker hover state
    'pressed': '#4A4A4C',      # Darker pressed state
    'disabled': '#2C2C2E',     # Disabled background (same as surface)
    'disabled_text': '#58585A', # Disabled text
    'button_hover': '#0070E0',      # Dark mode primary button hover
    'button_pressed': '#005CBD',    # Dark mode primary button pressed
    'secondary_button_bg': '#3A3A3C',
    'secondary_button_hover': '#4A4A4C',
    'secondary_button_pressed': '#5A5A5E',
    'success_button_hover': '#29B44C',
    'success_button_pressed': '#249A40',
    'danger_button_hover': '#D6362D',
    'danger_button_pressed': '#B02923',
}

# Typography
FONTS = {
    'system': 'SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif',
    'size_small': '12pt',
    'size_body': '14pt',
    'size_title': '16pt',
    'size_large': '18pt',
    'size_header': '20pt',
    'weight_regular': '400',
    'weight_medium': '500',
    'weight_semibold': '600',
    'weight_bold': '700',
}

# Spacing
SPACING = {
    'xs': '4px',
    'sm': '8px',
    'md': '12px',
    'lg': '16px',
    'xl': '20px',
    'xxl': '24px',
    'xxxl': '32px',
}

# Border radius
RADIUS = {
    'sm': '6px',
    'md': '8px',
    'lg': '12px',
    'xl': '16px',
    'round': '50%',
}

# Shadows
SHADOWS = {
    'sm': '0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24)',
    'md': '0 3px 6px rgba(0, 0, 0, 0.16), 0 3px 6px rgba(0, 0, 0, 0.23)',
    'lg': '0 10px 20px rgba(0, 0, 0, 0.19), 0 6px 6px rgba(0, 0, 0, 0.23)',
}

def get_main_window_style(colors):
    """Main window styling"""
    return f"""
    QMainWindow {{
        background-color: {colors['background']};
        color: {colors['text_primary']};
        font-family: {FONTS['system']};
        font-size: {FONTS['size_body']};
    }}
    
    QMainWindow::separator {{
        background-color: {colors['separator']};
        width: 1px;
        height: 1px;
    }}
    """

def get_tab_widget_style(colors):
    """Tab widget styling with modern Apple-like tabs"""
    return f"""
    QTabWidget::pane {{
        border: 1px solid {colors['separator']}; /* Subtle border, can also be colors['surface'] to blend more */
        background-color: {colors['surface']};
        border-radius: {RADIUS['lg']};
        margin-top: -1px; /* Helps align pane top with tab bottom line */
        padding: {SPACING['md']};
    }}
    
    QTabWidget::tab-bar {{
        alignment: center;
        /* You might want to adjust the bottom or top position if there are alignment issues
           with the pane border or tab underlines. Example: 
           bottom: -1px; or top: 1px; depending on how borders align. */
    }}
    
    QTabBar::tab {{
        background-color: transparent; /* Unselected tabs are transparent */
        color: {colors['text_secondary']};
        padding: {SPACING['md']} {SPACING['xl']}; /* Generous padding for a modern look */
        margin-right: {SPACING['xs']}; /* Spacing between tabs */
        border-top-left-radius: {RADIUS['md']};
        border-top-right-radius: {RADIUS['md']};
        border: 1px solid transparent; /* No visible border for unselected tabs initially */
        border-bottom: 2px solid transparent; /* Placeholder for underline effect */
        font-weight: {FONTS['weight_medium']};
        font-size: {FONTS['size_body']};
        min-width: 120px; /* Ensure tabs have enough space */
    }}
    
    QTabBar::tab:selected {{
        background-color: {colors['surface']}; /* Selected tab matches the pane background */
        color: {colors['text_primary']};
        border-bottom: 2px solid {colors['primary']}; /* Highlight with primary color underline */
        font-weight: {FONTS['weight_semibold']};
    }}
    
    QTabBar::tab:hover:!selected {{
        color: {colors['primary']};
        border-bottom: 2px solid {colors['primary']}33; /* Subtle primary color underline on hover */
    }}

    QTabBar::tab:disabled {{
        background-color: {colors['background']};
        color: {colors['disabled_text']};
        border-bottom: 2px solid {colors['separator']};
    }}
    """

def get_group_box_style(colors):
    """Group box styling, aiming for a less obtrusive, more integrated look."""
    return f"""
    QGroupBox {{
        font-size: {FONTS['size_large']}; /* Slightly larger for section heading feel */
        font-weight: {FONTS['weight_semibold']};
        color: {colors['text_primary']};
        border: none; /* Remove the box border */
        border-bottom: 1px solid {colors['separator']}; /* Subtle separator line */
        margin-top: {SPACING['xl']}; /* Increase top margin for separation */
        padding-top: {SPACING['sm']}; /* Space for the title */
        padding-bottom: {SPACING['md']}; /* Space below the content in the groupbox */
        background-color: transparent; /* Blend with parent background */
    }}
    
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left; 
        left: 0px; /* Align with the content */
        padding: 0 0 {SPACING['sm']} 0; /* Padding below title */
        color: {colors['text_primary']};
        font-size: {FONTS['size_large']};
        font-weight: {FONTS['weight_semibold']};
        background-color: transparent; 
    }}
    """

def get_button_style(colors):
    """Modern button styling with different variants"""
    return f"""
    QPushButton {{
        background-color: {colors['primary']};
        color: {colors['text_on_color']};
        border: none;
        border-radius: {RADIUS['md']};
        padding: {SPACING['md']} {SPACING['xl']};
        font-size: {FONTS['size_body']};
        font-weight: {FONTS['weight_medium']};
        min-height: 40px;
        min-width: 100px;
        outline: none;
    }}
    
    QPushButton:hover {{
        background-color: {colors['button_hover']};
    }}
    
    QPushButton:pressed {{
        background-color: {colors['button_pressed']};
    }}
    
    QPushButton:disabled {{
        background-color: {colors['disabled']};
        color: {colors['disabled_text']};
    }}
    
    /* Secondary button style - Light Gray */
    QPushButton[buttonStyle="secondary"] {{
        background-color: {colors['secondary_button_bg']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
    }}
    
    QPushButton[buttonStyle="secondary"]:hover {{
        background-color: {colors['secondary_button_hover']};
    }}
    
    QPushButton[buttonStyle="secondary"]:pressed {{
        background-color: {colors['secondary_button_pressed']};
    }}
    
    /* Success button style */
    QPushButton[buttonStyle="success"] {{
        background-color: {colors['secondary']};
        color: {colors['text_on_color']};
        border: none;
    }}
    
    QPushButton[buttonStyle="success"]:hover {{
        background-color: {colors['success_button_hover']};
    }}
    
    QPushButton[buttonStyle="success"]:pressed {{
        background-color: {colors['success_button_pressed']};
    }}
    
    /* Danger button style */
    QPushButton[buttonStyle="danger"] {{
        background-color: {colors['danger']};
        color: {colors['text_on_color']};
    }}
    
    QPushButton[buttonStyle="danger"]:hover {{
        background-color: {colors['danger_button_hover']};
    }}
    
    QPushButton[buttonStyle="danger"]:pressed {{
        background-color: {colors['danger_button_pressed']};
    }}
    """

def get_input_style(colors):
    """Modern styling for input fields like QLineEdit."""
    return f"""
    QLineEdit {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: {RADIUS['md']};
        padding: {SPACING['sm']} {SPACING['md']};
        font-size: {FONTS['size_body']};
        min-height: 38px; 
        selection-background-color: {colors['primary']};
        selection-color: {colors['text_on_color']};
    }}
    
    QLineEdit:focus {{
        border-color: {colors['primary']};
        /* Optional: box-shadow for dark mode could be different if needed */
        /* box-shadow: 0 0 0 2px {colors['primary']}33;  Example with alpha  */
    }}
    
    QLineEdit::placeholder {{
        color: {colors['text_tertiary']};
    }}
    
    QLineEdit:disabled {{
        background-color: {colors['disabled']};
        color: {colors['disabled_text']};
        border-color: {colors['separator']};
    }}

    /* QTextEdit could also be styled here if needed, similarly to QLineEdit */
    /*
    QTextEdit {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: {RADIUS['md']};
        padding: {SPACING['sm']};
        font-size: {FONTS['size_body']};
        selection-background-color: {colors['primary']};
        selection-color: {colors['text_on_color']};
    }}

    QTextEdit:focus {{
        border-color: {colors['primary']};
    }}

    QTextEdit:disabled {{
        background-color: {colors['disabled']};
        color: {colors['disabled_text']};
        border-color: {colors['separator']};
    }}
    */
    """

def get_list_widget_style(colors):
    """List widget styling with modern appearance"""
    return f"""
    QListWidget {{
        background-color: {colors['surface']};
        color: {colors['text_primary']};
        border: 1px solid {colors['border']};
        border-radius: {RADIUS['md']};
        padding: {SPACING['xs']};
        font-size: {FONTS['size_body']};
        outline: none; /* Remove focus outline if not desired */
    }}
    
    QListWidget::item {{
        padding: {SPACING['sm']} {SPACING['md']};
        border-radius: {RADIUS['sm']}; /* Slightly rounded items */
        margin: 2px 0; /* Add a little vertical space between items */
    }}
    
    QListWidget::item:hover:!selected {{
        background-color: {colors['hover']};
    }}
    
    QListWidget::item:selected {{
        background-color: {colors['primary']};
        color: {colors['text_on_color']};
    }}
    
    QListWidget::item:disabled {{
        color: {colors['disabled_text']};
        background-color: transparent;
    }}
    """

def get_label_style(colors):
    """Modern label styling with variants for title, subtitle, caption, and status messages."""
    return f"""
    QLabel {{
        color: {colors['text_primary']};
        font-size: {FONTS['size_body']};
        background-color: transparent; /* Ensure labels don't obscure background */
    }}

    /* Title Label */
    QLabel[labelStyle="title"] {{
        color: {colors['text_primary']};
        font-size: {FONTS['size_header']};
        font-weight: {FONTS['weight_semibold']};
    }}

    /* Subtitle Label */
    QLabel[labelStyle="subtitle"] {{
        color: {colors['text_secondary']};
        font-size: {FONTS['size_title']};
        font-weight: {FONTS['weight_regular']};
        line-height: 1.4; /* For better readability of wrapped text */
    }}

    /* Caption Label */
    QLabel[labelStyle="caption"] {{
        color: {colors['text_tertiary']};
        font-size: {FONTS['size_small']};
    }}

    /* Base Status Label Style */
    QLabel[labelStyle="status"] {{
        font-size: {FONTS['size_body']};
        font-weight: {FONTS['weight_medium']};
        padding: {SPACING['sm']};
        border-radius: {RADIUS['sm']};
        margin-top: {SPACING['sm']};
        text-align: center; /* Ensure text is centered if label is wide */
        color: {colors['text_secondary']}; /* Default status color */
        /* Optional default background: background-color: #F0F0F0; */
        /* Optional default border: border: 1px solid #DCDCDC; */
    }}

    /* Status Label - Success */
    QLabel[labelStyle="status"][status="success"] {{
        color: {colors.get('secondary', '#34C759')}; /* Fallback if not in all palettes */
        font-weight: {FONTS['weight_medium']};
    }}

    /* Status Label - Error */
    QLabel[labelStyle="status"][status="error"] {{
        color: {colors.get('danger', '#FF3B30')}; /* Fallback if not in all palettes */
        font-weight: {FONTS['weight_medium']};
    }}

    /* Status Label - Warning */
    QLabel[labelStyle="status"][status="warning"] {{
        color: {colors['accent']};
        /* Optional: background-color: #FFF9E6; */
        /* Optional: border: 1px solid {colors['accent']}; */
    }}
    """

def get_message_box_style(colors):
    """Message box styling"""
    # Basic styling, can be expanded
    return f"""
    QMessageBox {{
        background-color: {colors['surface']};
        border: 1px solid {colors['border']};
        border-radius: {RADIUS['md']};
    }}
    QMessageBox QLabel {{
        color: {colors['text_primary']};
        font-size: {FONTS['size_body']};
        background-color: transparent; /* Ensure QLabel inside MessageBox is transparent */
    }}
    QMessageBox QPushButton {{
        /* Uses global button style, ensure it's appropriate or customize here */
        min-width: 80px; /* Adjust if needed for standard dialog buttons */
        background-color: {colors['primary']};
        color: {colors['text_on_color']};
        border-radius: {RADIUS['sm']};
        padding: {SPACING['sm']} {SPACING['lg']};
    }}
    QMessageBox QPushButton:hover {{
        background-color: {colors['button_hover']};
    }}
    QMessageBox QPushButton:pressed {{
        background-color: {colors['button_pressed']};
    }}
    """

def get_scrollbar_style(colors):
    """Modern scrollbar styling"""
    return f"""
    QScrollBar:vertical {{
        border: none;
        background: {colors['surface']};
        width: {SPACING['md']}; /* 12px */
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {colors['separator']};
        min-height: {SPACING['xl']}; /* 20px */
        border-radius: {RADIUS['sm']}; /* 6px */
    }}
    QScrollBar::handle:vertical:hover {{
        background: {colors['text_secondary']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        border: none;
        background: none;
        height: 0px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }}
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: {colors['surface']};
        height: {SPACING['md']}; /* 12px */
        margin: 0px 0px 0px 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {colors['separator']};
        min-width: {SPACING['xl']}; /* 20px */
        border-radius: {RADIUS['sm']}; /* 6px */
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {colors['text_secondary']};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        border: none;
        background: none;
        width: 0px;
        subcontrol-position: left;
        subcontrol-origin: margin;
    }}
    QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
        background: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: none;
    }}
    """

def get_complete_style(theme="light"):
    """Complete stylesheet combining all components"""
    colors = DARK_COLORS if theme == "dark" else LIGHT_COLORS

    style = ""
    style += get_main_window_style(colors)
    style += get_tab_widget_style(colors)
    style += get_group_box_style(colors)
    style += get_button_style(colors)
    style += get_input_style(colors)
    style += get_list_widget_style(colors)
    style += get_label_style(colors)
    style += get_message_box_style(colors)
    style += get_scrollbar_style(colors)
    
    return style 