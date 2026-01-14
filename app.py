import os
import sys
import uuid
import email
from email import policy
import re
import extract_msg
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import bleach

# Handle PyInstaller bundled app - templates/static are in the bundle
if getattr(sys, 'frozen', False):
    # Running as a bundled app
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    # Running normally
    app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for session/flash

# Configure upload folder - use user-writable location for bundled apps
if getattr(sys, 'frozen', False):
    # Running as bundled app - use Application Support directory
    base_dir = os.path.join(
        os.path.expanduser("~"),
        "Library",
        "Application Support",
        "EmailReader",
    )
    upload_dir = os.path.join(base_dir, "uploads")
    app.config['UPLOAD_FOLDER'] = upload_dir
else:
    # Running normally - use local uploads directory
    app.config['UPLOAD_FOLDER'] = 'uploads'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'eml', 'msg'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def replace_cid_urls(html_content, cid_map):
    """
    Replace cid: URLs in the HTML with real URLs pointing to saved attachments.
    Expects cid_map keys to be the raw CID value without angle brackets, e.g. "image001.png@01D...".
    """
    if not html_content or not cid_map:
        return html_content

    def _repl(match):
        cid = match.group(1)
        replacement = cid_map.get(cid)
        if not replacement:
            # Try again without surrounding whitespace just in case
            cid_stripped = cid.strip()
            replacement = cid_map.get(cid_stripped)
        return f'src="{replacement}"' if replacement else match.group(0)

    # src="cid:something" or src='cid:something'
    return re.sub(r'src=[\'"]cid:(.+?)[\'"]', _repl, html_content, flags=re.IGNORECASE)

def clean_html(html_content):
    # Allow common tags and attributes for email rendering
    allowed_tags = list(bleach.sanitizer.ALLOWED_TAGS) + [
        'html', 'head', 'body', 'title',
        'p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'ul', 'ol', 'li',
        'img', 'a', 'b', 'i', 'strong', 'em', 'font', 'center', 'style', 'hr', 'blockquote',
        'dl', 'dt', 'dd', 'pre', 'code'
    ]
    allowed_attrs = {
        '*': ['style', 'class', 'id', 'width', 'height', 'align', 'valign', 'bgcolor', 'border'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'width', 'height', 'style'],
        'font': ['color', 'face', 'size'],
        'table': ['border', 'cellpadding', 'cellspacing', 'width', 'bgcolor'],
        'td': ['width', 'align', 'valign', 'bgcolor', 'colspan', 'rowspan'],
        'th': ['width', 'align', 'valign', 'bgcolor', 'colspan', 'rowspan'],
        'body': ['bgcolor', 'text', 'link', 'vlink', 'alink']
    }
    # Allow all css styles in style attribute? Bleach sanitizes inside style by default if not configured differently.
    # We aren't passing a css_sanitizer, so it warns.
    # But effectively it might be stripping dangerous CSS.
    
    return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attrs, strip=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Create a unique directory for this upload to isolate attachments
            upload_id = str(uuid.uuid4())
            upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
            os.makedirs(upload_dir, exist_ok=True)

            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)

            return redirect(url_for('view_email', upload_id=upload_id, filename=filename))

    return render_template('index.html')

@app.route('/view/<upload_id>/<filename>')
def view_email(upload_id, filename):
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
    file_path = os.path.join(upload_dir, filename)

    if not os.path.exists(file_path):
        flash('File not found')
        return redirect(url_for('index'))

    email_data = {
        'subject': '(No Subject)',
        'from': '(Unknown Sender)',
        'to': '(No Recipient)',
        'date': '(Unknown Date)',
        'body': '',
        'attachments': []
    }

    # Map of Content-ID (without angle brackets) -> public URL for that attachment
    cid_map = {}

    file_ext = filename.rsplit('.', 1)[1].lower()

    if file_ext == 'msg':
        try:
            msg = extract_msg.Message(file_path)
            email_data['subject'] = msg.subject if msg.subject else '(No Subject)'
            email_data['from'] = msg.sender if msg.sender else '(Unknown Sender)'
            email_data['to'] = msg.to if msg.to else '(No Recipient)'
            email_data['date'] = msg.date if msg.date else '(Unknown Date)'

            # Extract Attachments (and build CID map for inline images, if available)
            for attachment in msg.attachments:
                fname = attachment.getFilename()
                if fname:
                    fname = secure_filename(fname)
                    att_path = os.path.join(upload_dir, fname)
                    
                    if not os.path.exists(att_path):
                        with open(att_path, 'wb') as f:
                            f.write(attachment.data)

                    url = url_for('download_attachment', upload_id=upload_id, filename=fname)

                    # Some extract_msg versions expose Content-ID via .cid or .contentId
                    cid = getattr(attachment, 'cid', None) or getattr(attachment, 'contentId', None)
                    if cid:
                        cid = cid.strip('<>')
                        cid_map[cid] = url
                    
                    email_data['attachments'].append({
                        'filename': fname,
                        'url': url
                    })

            # Extract Body
            body_content = ""
            print(f"MSG htmlBody type: {type(msg.htmlBody)}", flush=True)
            if msg.htmlBody:
                # msg.htmlBody is bytes in some versions, string in others. Ensure decoding.
                try:
                    raw_html = msg.htmlBody.decode('utf-8', errors='ignore') if isinstance(msg.htmlBody, bytes) else msg.htmlBody
                    print(f"MSG HTML Body (len={len(raw_html)})", flush=True)

                    # Replace cid: URLs so inline images load from our server.
                    # We intentionally do NOT sanitize the HTML further here because the
                    # original CSS/positioning is needed to keep annotations (e.g. circles)
                    # aligned with images. Security is still provided by the sandboxed iframe.
                    body_content = replace_cid_urls(raw_html, cid_map)
                    print(f"Rendered MSG Body (len={len(body_content)})", flush=True)
                    print(f"Rendered MSG Snippet: {body_content[:1000]}", flush=True)
                except Exception as e:
                    print(f"Error processing MSG HTML: {e}", flush=True)
                    body_content = f"<p>Error decoding HTML body: {e}</p>"
            elif msg.body:
                print("MSG has no HTML body, falling back to text.", flush=True)
                cleaned_text = bleach.clean(msg.body)
                body_content = f'<div style="white-space: pre-wrap;">{cleaned_text}</div>'
            else:
                print("MSG has NO body at all.", flush=True)
                body_content = "<p>(No readable body found)</p>"
            
            email_data['body'] = body_content
            msg.close()

        except Exception as e:
            print(f"MSG parsing error: {e}")
            flash(f'Error parsing MSG file: {str(e)}')
            return redirect(url_for('index'))

    else: # Default to EML
        # Parse the email
        with open(file_path, 'rb') as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        email_data['subject'] = msg.get('subject', '(No Subject)')
        email_data['from'] = msg.get('from', '(Unknown Sender)')
        email_data['to'] = msg.get('to', '(No Recipient)')
        email_data['date'] = msg.get('date', '(Unknown Date)')

        # Extract Attachments (and build CID map for inline images)
        for part in msg.iter_attachments():
            fname = part.get_filename()
            if fname:
                fname = secure_filename(fname)
                att_path = os.path.join(upload_dir, fname)
                
                # Save attachment if it doesn't exist yet
                if not os.path.exists(att_path):
                    payload = part.get_content()
                    # If payload is bytes, write wb, else w
                    if isinstance(payload, bytes):
                        with open(att_path, 'wb') as f:
                            f.write(payload)
                    else:
                        with open(att_path, 'w') as f:
                            f.write(payload)

                url = url_for('download_attachment', upload_id=upload_id, filename=fname)

                # Attachments that correspond to inline images should have a Content-ID header
                cid_header = part.get('Content-ID')
                if cid_header:
                    cid_value = cid_header.strip('<>')
                    cid_map[cid_value] = url

                email_data['attachments'].append({
                    'filename': fname,
                    'url': url
                })

        # Extract Body
        body_content = ""
        # Prefer HTML, fallback to plain text
        body_part = msg.get_body(preferencelist=('html', 'plain'))

        if body_part:
            try:
                content = body_part.get_content()
                if body_part.get_content_type() == 'text/html':
                    print(f"EML HTML Body (len={len(content)})", flush=True)

                    # Replace cid: URLs with real attachment URLs.
                    # We keep the original HTML/CSS so any relative positioning used
                    # for annotations (e.g. circles over screenshots) is preserved.
                    body_content = replace_cid_urls(content, cid_map)
                    print(f"Rendered EML Body (len={len(body_content)})", flush=True)
                    print(f"Rendered EML Snippet: {body_content[:1000]}", flush=True)
                else:
                    print("EML body is TEXT/PLAIN", flush=True)
                    # Convert newlines to <br> for plain text
                    cleaned_text = bleach.clean(content)
                    body_content = f'<div style="white-space: pre-wrap;">{cleaned_text}</div>'
            except Exception as e:
                print(f"EML Body Error: {e}", flush=True)
                body_content = f"<p>Error decoding body: {e}</p>"
        else:
            print("EML has NO body part found via get_body()", flush=True)
            body_content = "<p>(No readable body found)</p>"

        email_data['body'] = body_content

    return render_template('view_email.html', email=email_data)

@app.route('/uploads/<upload_id>/<filename>')
def download_attachment(upload_id, filename):
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
    return send_from_directory(upload_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)