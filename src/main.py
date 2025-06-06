import sys
import os
import customtkinter as ctk # Import customtkinter

# Adjust sys.path to ensure 'src' is recognized as a package root
# when running this script directly (e.g., python src/main.py)
# This adds the project root directory (parent of 'src') to sys.path
# so that imports like 'from src.gui.main_window import App' work correctly.
# __file__ is src/main.py
# os.path.dirname(__file__) is src
# os.path.dirname(os.path.dirname(__file__)) is the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now that the project root is in sys.path, we can use absolute imports from src
from src.gui.main_window import App

if __name__ == "__main__":
    # Set default appearance mode and color theme for CustomTkinter
    ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
    ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "dark-blue", "green"

    app = App()
    app.mainloop()
