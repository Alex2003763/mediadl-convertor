"""
Material Design-inspired Color Palette for the Media Downloader and Converter Application.

This module defines a set of color constants based on Material Design principles
to be used throughout the application's GUI for a consistent look and feel.
It includes definitions for both a Light and a Dark theme.
"""

# --- Theme Definitions ---

THEMES = {
    "Light": {
        "COLOR_PRIMARY": "#3F51B5",  # Indigo 500
        "COLOR_PRIMARY_DARK": "#303F9F",  # Indigo 700
        "COLOR_PRIMARY_LIGHT": "#C5CAE9",  # Indigo 100
        "COLOR_ACCENT": "#E91E63",  # Pink 500
        "COLOR_ACCENT_DARK": "#C2185B", # Pink 700
        "COLOR_ACCENT_LIGHT": "#F8BBD0", # Pink 100
        "TEXT_PRIMARY": "#000000",  # True Black (on light backgrounds)
        "TEXT_SECONDARY": "#757575",  # Medium Grey (on light backgrounds)
        "TEXT_HINT": "#BDBDBD", # Light Grey for hints (on light backgrounds)
        "BACKGROUND_WINDOW": "#F5F5F5",  # Light Grey - typical Material background
        "BACKGROUND_CONTENT": "#FFFFFF",  # White - for "cards" or main content areas
        "BACKGROUND_INPUT": "#E0E0E0", # Slightly darker grey for input backgrounds or disabled states
        "DIVIDER_COLOR": "#BDBDBD", # For subtle borders or dividers
        "TEXT_ON_PRIMARY_COLOR": "#FFFFFF", # Text that goes on COLOR_PRIMARY background
        "TEXT_ON_ACCENT_COLOR": "#FFFFFF", # Text that goes on COLOR_ACCENT background
    },
    "Dark": {
        "COLOR_PRIMARY": "#7986CB",  # Indigo 200 (Lighter Indigo for Dark Theme)
        "COLOR_PRIMARY_DARK": "#5C6BC0",  # Indigo 300 
        "COLOR_PRIMARY_LIGHT": "#9FA8DA",  # Indigo 100
        "COLOR_ACCENT": "#F06292",  # Pink 200 (Lighter Pink for Dark Theme)
        "COLOR_ACCENT_DARK": "#EC407A", # Pink 300
        "COLOR_ACCENT_LIGHT": "#F48FB1", # Pink 100
        "TEXT_PRIMARY": "#FFFFFF",  # White (on dark backgrounds)
        "TEXT_SECONDARY": "#B0BEC5",  # Bluish Grey (on dark backgrounds)
        "TEXT_HINT": "#78909C", # Darker Bluish Grey for hints (on dark backgrounds)
        "BACKGROUND_WINDOW": "#121212",  # Very Dark Grey (Material Dark Theme window background)
        "BACKGROUND_CONTENT": "#1E1E1E",  # Dark Grey (Material Dark Theme content background)
        "BACKGROUND_INPUT": "#2C2C2C", # Slightly lighter dark grey for inputs
        "DIVIDER_COLOR": "#373737", # Darker divider for dark theme
        "TEXT_ON_PRIMARY_COLOR": "#000000", # Text that goes on COLOR_PRIMARY background (Dark theme often uses dark text on lighter primary)
        "TEXT_ON_ACCENT_COLOR": "#000000", # Text that goes on COLOR_ACCENT background
    }
}

# --- Default Theme Selection ---
# For now, we'll keep the global variables and update them.
# Later, the application will dynamically change these.
_current_theme_name = "Light" # Default theme name

def get_current_theme_colors():
    """Returns the color dictionary for the currently selected theme."""
    return THEMES.get(_current_theme_name, THEMES["Light"]) # Fallback to Light

def set_current_theme(theme_name):
    """Sets the current theme and updates global color variables."""
    global _current_theme_name
    if theme_name not in THEMES:
        print(f"Warning: Theme '{theme_name}' not found. Defaulting to 'Light'.")
        _current_theme_name = "Light"
    else:
        _current_theme_name = theme_name
    
    # Update global color variables based on the new theme
    current_colors = get_current_theme_colors()
    globals().update(current_colors)
    
    # Update the specific on_dark/on_light variables for compatibility if they are directly used.
    # New code should prefer TEXT_PRIMARY, TEXT_SECONDARY from the theme dict.
    # These are a bit of a legacy now but helps with transition.
    if _current_theme_name == "Dark":
        global TEXT_PRIMARY_ON_LIGHT, TEXT_SECONDARY_ON_LIGHT, TEXT_HINT_ON_LIGHT
        global TEXT_PRIMARY_ON_DARK, TEXT_SECONDARY_ON_DARK
        TEXT_PRIMARY_ON_LIGHT = current_colors["TEXT_PRIMARY"] # This is now text on dark effectively
        TEXT_SECONDARY_ON_LIGHT = current_colors["TEXT_SECONDARY"]
        TEXT_HINT_ON_LIGHT = current_colors["TEXT_HINT"]
        TEXT_PRIMARY_ON_DARK = current_colors["TEXT_PRIMARY"] # Re-affirm for clarity
        TEXT_SECONDARY_ON_DARK = current_colors["TEXT_SECONDARY"]
    else: # Light theme
        global TEXT_PRIMARY_ON_LIGHT, TEXT_SECONDARY_ON_LIGHT, TEXT_HINT_ON_LIGHT
        global TEXT_PRIMARY_ON_DARK, TEXT_SECONDARY_ON_DARK # These were already for dark backgrounds
        TEXT_PRIMARY_ON_LIGHT = current_colors["TEXT_PRIMARY"]
        TEXT_SECONDARY_ON_LIGHT = current_colors["TEXT_SECONDARY"]
        TEXT_HINT_ON_LIGHT = current_colors["TEXT_HINT"]
        # TEXT_PRIMARY_ON_DARK and TEXT_SECONDARY_ON_DARK are typically white/light grey,
        # which is fine for the default light theme's dark primary/accent buttons.
        # If a theme has dark text on dark primary, this would need adjustment.
        # For now, assume TEXT_PRIMARY_ON_DARK is generally white or very light.
        TEXT_PRIMARY_ON_DARK = THEMES["Light"]["TEXT_ON_PRIMARY_COLOR"] # Default for light theme buttons
        TEXT_SECONDARY_ON_DARK = THEMES["Light"]["TEXT_ON_PRIMARY_COLOR"] # Lighter Grey for text on dark backgrounds (e.g. on primary color button)


# Initialize global colors with the default theme (Light)
set_current_theme(_current_theme_name)


# Status/Error Colors (These are generally theme-agnostic but could be themed too)
COLOR_ERROR = "#D32F2F" # Red
COLOR_SUCCESS = "#388E3C" # Green
COLOR_WARNING = "#FFA000" # Amber

# Base64 encoded GIF for a simple download icon (16x16)
# Source: A common, simple download icon.
# This icon might need versions for light/dark themes if it doesn't look good on one.
DOWNLOAD_ICON_BASE64 = "R0lGODlhEAAQAMQAAORHHOVSKudfOulrSOp3WOyDZu6QdvCchPGolfO0o/XBs/fNwfjZ0frl3/zy7////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAkAABAALAAAAAAQABAAAAVVICSOZGlCQAosJ6mu7fiyZeKqNKToQGDsMBOAKUTYEYlLPTBByAgBYHhIRAHA4W0LAEGJRIYYBiMQCAYSOSTDPTRENf8gBक्रियர் அனைத்தும் ஒருவரே. TTBkAAA7"

# --- Fonts ---
FONT_FAMILY_PRIMARY = "Roboto" # Preferred
FONT_FAMILY_FALLBACKS = ("Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "sans-serif") # Common fallbacks

# Define standard sizes/weights
FONT_SIZE_NORMAL = 10
FONT_SIZE_SMALL = 9
FONT_SIZE_LARGE = 12 # For potential headers, not used yet

FONT_WEIGHT_NORMAL = "normal"
FONT_WEIGHT_BOLD = "bold"
