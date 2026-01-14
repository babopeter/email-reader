# Gemini Context: Web Email Reader

## Project Overview
This project is a Flask-based application designed to view `.eml` and `.msg` email files. It can be run as a standard web application or as a standalone desktop application (using `pywebview`). It parses uploaded files, extracts headers, renders the email body (sanitized HTML or plain text), and lists attachments for download.

**Key Technologies:**
*   **Backend:** Python, Flask
*   **Desktop Wrapper:** `pywebview`
*   **Email Parsing:** `email` (Python standard lib), `extract-msg` (for Outlook .msg files)
*   **Security:** `bleach` (HTML sanitization)
*   **Frontend:** HTML5, Bootstrap 5.3 (via CDN), custom CSS/JS
*   **Packaging:** PyInstaller

## Architecture
*   **Entry Points:**
    *   `app.py`: Standard Flask application entry point.
    *   `run_app.py`: Desktop application entry point. Starts Flask in a background thread and opens a native webview window.
*   **Templates:** Located in `templates/`.
    *   `index.html`: File upload form.
    *   `view_email.html`: Displays the email headers, body (in an iframe), and attachments.
*   **Static Assets:** Located in `static/`.
    *   `style.css`: Custom styling.
    *   `script.js`: Frontend logic.
*   **Storage:** Uploaded files and extracted attachments are stored temporarily in the `uploads/` directory, organized by unique UUIDs to prevent conflicts.
*   **Security:** Email bodies are sanitized using `bleach` before rendering. The rendered body is displayed within a sandboxed `<iframe>`.

## Building and Running

### Prerequisites
*   Python 3.x
*   `pip`

### Setup
1.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source ./.venv/bin/activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application (Web Mode)
Start the Flask development server:
```bash
python app.py
```
The application will be accessible at `http://127.0.0.1:5000/`.

### Running the Application (Desktop Mode)
Start the desktop application:
```bash
python run_app.py
```
This will launch a native window containing the application.

### Building the Executable (macOS)
The project is configured with PyInstaller to build a macOS `.app` bundle.
```bash
pyinstaller "Email Reader.spec"
```
The output `Email Reader.app` will be in the `dist/` directory.

## Key Files
*   `app.py`: Core logic. Handles file uploads, parsing, sanitization, and serving.
*   `run_app.py`: Desktop wrapper. Manages the Flask thread and webview window. Handles port finding and logging.
*   `Email Reader.spec`: PyInstaller configuration file for building the macOS bundle.
*   `templates/view_email.html`: Main view. Uses a sandboxed `<iframe>` for email content.
*   `requirements.txt`: Python dependencies (`Flask`, `bleach`, `extract-msg`, `pywebview`).

## Development Notes
*   **Debugging:** `app.py` runs in debug mode by default. `run_app.py` runs Flask with `debug=False` and `threaded=True`.
*   **Desktop Logging:** `run_app.py` logs errors to `~/Library/Logs/EmailReader.log`.
*   **Sanitization:** `clean_html` in `app.py` defines allowed tags/attributes to prevent XSS while preserving email structure.
*   **Iframe Sandbox:** The iframe in `view_email.html` restricts script execution.