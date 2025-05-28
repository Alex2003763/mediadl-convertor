# Media Downloader and Converter

A simple desktop application for downloading media from various sources (primarily using `yt-dlp`) and converting it to different formats (using `ffmpeg`).

## Features

*   Download media from URLs supported by `yt-dlp`.
*   Convert downloaded media to formats like MP4, MP3, AVI, MOV, WebM.
*   User-friendly GUI with progress display and status messages.
*   Handles potential filename conflicts by creating unique filenames (e.g., `video_1.mp4`).

## Project Structure

```
.
├── assets/                # For any static assets (not used in current version)
│   ├── downloads/         # (Created by downloader.py tests)
│   └── converted/         # (Created by converter.py tests)
├── downloads/             # Default output directory for the GUI application
├── src/
│   ├── __init__.py
│   ├── core/              # Core logic for downloading and conversion
│   │   ├── __init__.py
│   │   ├── downloader.py
│   │   └── converter.py
│   ├── gui/               # GUI components
│   │   ├── __init__.py
│   │   └── main_window.py
│   └── main.py            # Main entry point for the application
├── tests/                 # Unit tests
│   ├── __init__.py
│   ├── test_downloader.py
│   └── test_converter.py
├── requirements.txt       # Python dependencies
└── README.md
```

## Prerequisites

*   Python 3.x
*   `pip` (Python package installer)
*   `ffmpeg` (must be installed and available in the system PATH)
    *   On Debian/Ubuntu: `sudo apt update && sudo apt install ffmpeg`
    *   On macOS (using Homebrew): `brew install ffmpeg`
    *   On Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.
* use One-Click FFMPEG installer: iex (irm ffmpeg.tc.ht)
## Setup and Installation

1.  **Clone the repository (if applicable):**
    ```bash
    # git clone <repository_url>
    # cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    ```
    Activate it:
    *   On Windows: `venv\Scripts\activate`
    *   On macOS/Linux: `source venv/bin/activate`

3.  **Install dependencies:**
    Make sure `ffmpeg` is installed and accessible in your system's PATH first (see Prerequisites). Then, install the Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

Once the setup is complete, you can run the application using the main entry point script:

```bash
python src/main.py
```

This should be executed from the project's root directory. The application window will appear, and media will be saved by default into a `downloads` directory created in the project root.

## Running Tests (Optional)

To run the unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```
This command should be run from the project's root directory.

## Development

*   **GUI**: Developed using Tkinter.
*   **Downloader**: Uses `yt-dlp` library.
*   **Converter**: Uses `ffmpeg-python` library (which is a wrapper around `ffmpeg`).

The `src/gui/main_window.py` can also be run directly for testing the GUI in isolation:
```bash
python src/gui/main_window.py
```
Similarly, `src/core/downloader.py` and `src/core/converter.py` have their own `if __name__ == "__main__":` blocks for direct testing of their functionalities.
```
