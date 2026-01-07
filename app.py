import os
import uuid
import email
from email import policy
import extract_msg
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
import bleach

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for session/flash
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'eml', 'msg'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    file_ext = filename.rsplit('.', 1)[1].lower()

    if file_ext == 'msg':
        try:
            msg = extract_msg.Message(file_path)
            email_data['subject'] = msg.subject if msg.subject else '(No Subject)'
            email_data['from'] = msg.sender if msg.sender else '(Unknown Sender)'
            email_data['to'] = msg.to if msg.to else '(No Recipient)'
            email_data['date'] = msg.date if msg.date else '(Unknown Date)'

            # Extract Body
            body_content = ""
            print(f"MSG htmlBody type: {type(msg.htmlBody)}", flush=True)
            if msg.htmlBody:
                # msg.htmlBody is bytes in some versions, string in others. Ensure decoding.
                try:
                    raw_html = msg.htmlBody.decode('utf-8', errors='ignore') if isinstance(msg.htmlBody, bytes) else msg.htmlBody
                    print(f"MSG HTML Body (len={len(raw_html)})", flush=True)
                    body_content = clean_html(raw_html)
                    print(f"Cleaned MSG Body (len={len(body_content)})", flush=True)
                    print(f"Cleaned MSG Snippet: {body_content[:1000]}", flush=True)
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

            # Extract Attachments
            for attachment in msg.attachments:
                fname = attachment.getFilename()
                if fname:
                    fname = secure_filename(fname)
                    att_path = os.path.join(upload_dir, fname)
                    
                    if not os.path.exists(att_path):
                        with open(att_path, 'wb') as f:
                            f.write(attachment.data)
                    
                    email_data['attachments'].append({
                        'filename': fname,
                        'url': url_for('download_attachment', upload_id=upload_id, filename=fname)
                    })
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

        # Extract Body
        body_content = ""
        # Prefer HTML, fallback to plain text
        body_part = msg.get_body(preferencelist=('html', 'plain'))

        if body_part:
            try:
                content = body_part.get_content()
                if body_part.get_content_type() == 'text/html':
                    print(f"EML HTML Body (len={len(content)})", flush=True)
                    body_content = clean_html(content)
                    print(f"Cleaned EML Body (len={len(body_content)})", flush=True)
                    print(f"Cleaned EML Snippet: {body_content[:1000]}", flush=True)
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

        # Extract Attachments
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

                email_data['attachments'].append({
                    'filename': fname,
                    'url': url_for('download_attachment', upload_id=upload_id, filename=fname)
                })

    return render_template('view_email.html', email=email_data)

@app.route('/uploads/<upload_id>/<filename>')
def download_attachment(upload_id, filename):
    upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_id)
    return send_from_directory(upload_dir, filename)

if __name__ == '__main__':
    app.run(debug=True)