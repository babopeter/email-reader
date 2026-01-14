# Web Email Reader

A Flask-based web application to view `.eml` and `.msg` email files in a browser.

## Features

- Upload `.eml` and `.msg` files.
- Displays 'From', 'To', 'Subject', and 'Date' headers.
- Renders HTML or plain text email bodies.
- Sanitizes HTML content using `bleach` to prevent XSS.
- Extracts and provides download links for attachments.

## Installation and Setup

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source ./.venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    ./.venv/bin/pip install -r requirements.txt
    ```

## Usage

1.  **Run the application:**
    ```bash
    nohup ./.venv/bin/python app.py > app.log 2>&1 &
    ```
2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000/`.

## Acknowledgements
This project was developed with the assistance of the Google Gemini CLI.

## TODO

- [x] Implement rendering images inline with the text (e.g., handling `cid:` references for embedded images).
- [ ] Dockerize the application
