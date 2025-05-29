"""
Theme definitions for the Media Downloader and Converter Application.

This module defines base64 encoded icons and font settings.
Color themes are now handled by CustomTkinter's built-in theming system.
"""

# --- Base64 encoded Icons ---
# Base64 encoded GIF for a simple download icon (16x16)e
DOWNLOAD_ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAdElEQVR4nM3QsQ2AIBCF4b/QFiwtnYDGdaydCYewtrB3LoO54kIQL7HhJa8gx3chQD0LP7K1jwMwS12GnZqFEj6AVTpleFKzo4Sj8dmxhjvAZ3gAegtOcAdGwaOcvQWjwKkWYcV6gYZY8Vsaw5f87lfTvSc38KofDmta+gUAAAAASUVORK5CYII="
FETCH_ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAA8AAAAPCAYAAAA71pVKAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAsklEQVR4nK2SMQrCQBBFX6MoloG1WBstvYe2XsFOD6HY29okhYpd0EYvkXPJwGfRoE7AfAjDvHmz2UCghRyBG7BxvJ0881NK4ApEZznKMz/F3pg5B0TNzdt+EmxwB3o13hfPnJsxB1Y1tgZm3xYeQAEsgQ5wqs3P4gt55qcYeE3u9EXryxMgSJ4CI9VcfPxrOegnqIALMFCtxIN37SGwB7rqrVpvvNE3e3nzDwJNH/P/yxPr/SmHP39X3gAAAABJRU5ErkJggg=="

# Placeholder for the application icon
APP_ICON_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAACXBIWXMAAAsTAAALEwEAmpwYAAAEm0lEQVR4nO2dS48MURTHKxJW4jv0PaXv7RYWRsyMBU0iYSHEO8G3MAax8RbBSnwAj51IWCIYCXbEgjHvGFKrspkZNjqu3O6e0V1d09OP23WPqf8/OYup7kydOr8691bdx2nPgyAIgiAIgiAIYqB8Pr+KKHuYSD0gUsNCyDkipZezCSFnzbUSqfu+Lw/19PSs9DhICLVfCDXuOkDkHtAYUW6fSxYriNR114EgdiavmdgkTgMwVCMoVxNvpqJOKLVBD569rJ8PfdST33/pINTL2ia//ypd68Dpi1qq9TFQsnttx933/TVCyHNEakoINZnJqJ2lDjzaZ/T2bdOv3w47D1LgyF6/Gy7FIJIlo7Y6+n8g5I/afktNepWnqZrMSDOMoGJDbz/XZYrvy4PdAFFtXuXRduGAaaZcByNgYgODFyJPXupet0BUAZEj1QdMO+o6EAETe/byQzRgw90CsQBECDVTfWDi20/ngQiY2NjX2WiGzNgCkV3Xq3tO3IltsmoOuA5CwMzqAtZA+Xx+tRBqsBGItblNeuPRG7pwc0bvuB3z/wFEdwykHRDzBiChvQzpBASAhPaaLBsgACS0A6TZzrpwa7YhCAAJ7QDpNCMAJLT7lGULBDIktAukUxAAEtoBYgsEgIR2gDTbWQNImAwQmzDwYhgCyH9vhAzRziEACIPABwDiPtgBgLgPcAAg7oMaAIj7QAYA4j54AYC4D1gAIO6DFABIckF4+PhVaRlnX39BP3oyBCCu78i+/sLCcEX/loJzf1I/dELM1okBCAEI6zsyYOZP6iaoiLk/qZvCJeb+pG6RAzH3J3XLgIi5P6lbKEfM/UndUlJi7k/qFlsTc39Stx2BmPuTug07xNyfrm9p47bpkxgBcbXp8wunbdHECIiTbdGmPlT1gVNnLgFIWAZy8tT5SIbIu60AaQeMZ4p11ZXWeOeutAYxyZBXbz7VldbIZOSBdoC0AsYzBVXKxboixWccQSEGQAyMzb1bI77IkUSKzxiZymnRQJi7w9T6MO3o+PTcsgcyPj2nn754X2qmYsoz/fF9uccGjDgwBoQQaqJUnmlepnJasx2PDVtszpyWADI/556kr0Koy54DrUgaStycOS0BpHrOPQH7I4S84qTE37xM5TRTrCuZO09O159f1Xwn+rkQ6lsyMORIN5qptmQ6L1Osy9SHEkJ9rpRQtQ6DKLurdSDZ3d2AYq6xcq13zdMUmzKxrkVLAIEAJN0iZAgvEYDwEgEILxGA8BIBCC8RgNgOqNxuRo/NgFk79dKpQyCVgdKp8gi23O6lXdVD+ULI30S5I0kBIcodKZ9zYfhj1Eu7yplRMyTREhRqE0g9jNIo7YSXdpkmoz4wzUOhNoDEwzB/2/+Jif9S5YHJ2gARqaLvZ4/bBuL78lDcuTIZeczaBaUZCrUABDASgEJNAgGMhKBQE0AAI0EotAQQwEgYCjUAAhgOoNAiQADDERSKAQIYDqFQBAhgJKTF365VdDVI22/9kJ1M0Q0Mb+CMoBQxHMIHShEw+EApAgYfKEXA4DGfMl1e+5vb59ofCIIgCIIgCIIgb5nrL/s9kYENNlLnAAAAAElFTkSuQmCC"
# --- Fonts ---
# CustomTkinter manages fonts internally based on theme.
# These variables are kept for potential future direct use or compatibility,
# but CustomTkinter widgets generally handle font scaling and appearance automatically.
FONT_FAMILY_PRIMARY = "Arial" # Preferred
FONT_FAMILY_FALLBACKS = ("Helvetica Neue", "Helvetica", "Segoe UI", "sans-serif") # Common fallbacks

# Define standard sizes/weights
FONT_SIZE_NORMAL = 11
FONT_SIZE_SMALL = 10
FONT_SIZE_LARGE = 14 # For potential headers, not used yet

FONT_WEIGHT_NORMAL = "normal"
FONT_WEIGHT_BOLD = "bold"

# Remove theme-related functions and variables as CustomTkinter handles them
_current_theme_name = "Light" # Keep for settings file compatibility, but not used for CTk theming

def set_current_theme(theme_name):
    """Sets the current theme name. CustomTkinter handles the actual theme application."""
    global _current_theme_name
    _current_theme_name = theme_name

def get_current_theme_name():
    """Returns the currently selected theme name."""
    return _current_theme_name

# Initialize with default theme name
set_current_theme("Light")
