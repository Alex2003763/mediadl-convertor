"""
Material Design-inspired Color Palette for the Media Downloader and Converter Application.

This module defines a set of color constants based on Material Design principles
to be used throughout the application's GUI for a consistent look and feel.
The primary color is Indigo, and the accent color is Pink.
"""

# Material Design - Indigo Primary, Pink Accent
COLOR_PRIMARY = "#3F51B5"  # Indigo 500
COLOR_PRIMARY_DARK = "#303F9F"  # Indigo 700
COLOR_PRIMARY_LIGHT = "#C5CAE9"  # Indigo 100
COLOR_ACCENT = "#E91E63"  # Pink 500
COLOR_ACCENT_DARK = "#C2185B" # Pink 700
COLOR_ACCENT_LIGHT = "#F8BBD0" # Pink 100

TEXT_PRIMARY_ON_LIGHT = "#212121"  # Almost Black
TEXT_SECONDARY_ON_LIGHT = "#757575"  # Medium Grey
TEXT_HINT_ON_LIGHT = "#BDBDBD" # Light Grey for hints

TEXT_PRIMARY_ON_DARK = "#FFFFFF" # White for text on dark backgrounds
TEXT_SECONDARY_ON_DARK = "#E0E0E0" # Lighter Grey for text on dark backgrounds

BACKGROUND_WINDOW = "#F5F5F5"  # Light Grey - typical Material background
BACKGROUND_CONTENT = "#FFFFFF"  # White - for "cards" or main content areas
BACKGROUND_INPUT = "#E0E0E0" # Slightly darker grey for input backgrounds or disabled states

DIVIDER_COLOR = "#BDBDBD" # For subtle borders or dividers

# Status/Error Colors
COLOR_ERROR = "#D32F2F" # Red
COLOR_SUCCESS = "#388E3C" # Green
COLOR_WARNING = "#FFA000" # Amber

# Base64 encoded GIF for a simple download icon (16x16)
# Source: A common, simple download icon.
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
