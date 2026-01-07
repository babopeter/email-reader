# Gemini Context: Web Email Reader

## Project Overview
This project is a Flask-based web application designed to view `.eml` and `.msg` email files directly in the browser. It parses uploaded files, extracts headers, renders the email body (sanitized HTML or plain text), and lists attachments for download.

**Key Technologies:**
*   **Backend:** Python, Flask
*   **Email Parsing:** `email` (Python standard lib), `extract-msg` (for Outlook .msg files)
*   **Security:** `bleach` (HTML sanitization)
*   **Frontend:** HTML5, Bootstrap 5.3 (via CDN)

## Architecture
*   **Entry Point:** `app.py` contains the Flask application, route definitions, and parsing logic.
*   **Templates:** Located in `templates/`.
    *   `index.html`: File upload form.
    *   `view_email.html`: Displays the email headers, body (in an iframe), and attachments.
*   **Storage:** Uploaded files and extracted attachments are stored temporarily in the `uploads/` directory, organized by unique UUIDs to prevent conflicts.
*   **Security:** Email bodies are sanitized using `bleach` before rendering to prevent XSS attacks. The rendered body is displayed within a sandboxed `<iframe>`.

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

### Running the Application
Start the Flask development server:
```bash
python app.py
```
The application will be accessible at `http://127.0.0.1:5000/`.

## Key Files
*   `app.py`: Core logic. Handles file uploads, determines file type (`.eml` vs `.msg`), parses content, sanitizes HTML, and serves files.
*   `templates/view_email.html`: The main view. Uses an `<iframe>` with `srcdoc` to render the email body safely. Note that `| safe` is deliberately omitted from the `srcdoc` attribute to allow Jinja2 to escape the HTML properly for the attribute context.
*   `requirements.txt`: List of Python dependencies (`Flask`, `bleach`, `extract-msg`).

## Development Notes
*   **Debugging:** The application runs in debug mode (`debug=True`).
*   **Sanitization:** The `clean_html` function in `app.py` defines allowed tags and attributes. It specifically allows `html`, `head`, and `body` tags to preserve email structure.
*   **Iframe Sandbox:** The iframe in `view_email.html` uses the `sandbox` attribute to restrict script execution within the rendered email.
