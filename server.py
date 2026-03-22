from flask import Flask, request, redirect, url_for, send_from_directory, Response
import os

app = Flask(__name__)
BASE_FOLDER = "uploads"
os.makedirs(BASE_FOLDER, exist_ok=True)

USERNAME = "admin"
PASSWORD = "1234"

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}

def check_auth(u, p):
    return u == USERNAME and p == PASSWORD

def authenticate():
    return Response("Login required", 401,
                    {"WWW-Authenticate": 'Basic realm="Login"'})

def get_safe_path(path):
    base_abs = os.path.abspath(BASE_FOLDER)
    full_path = os.path.normpath(os.path.join(base_abs, path))
    if not full_path.startswith(base_abs):
        return base_abs
    return full_path

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    current_path = request.args.get("path", "")
    folder = get_safe_path(current_path)

    if request.method == "POST":
        file = request.files.get("file")
        if file and allowed_file(file.filename):
            file.save(os.path.join(folder, file.filename))
        return redirect(url_for("index", path=current_path))

    items = os.listdir(folder)
    files = []
    folders = []

    for item in items:
        item_path = os.path.join(folder, item)
        if os.path.isdir(item_path):
            folders.append(item)
        elif os.path.isfile(item_path) and allowed_file(item):
            files.append(item)

    html_items = ""

    if current_path:
        parent = os.path.dirname(current_path)
        html_items += f'<a class="back" href="/?path={parent}">⬅ Back</a>'

    html_items += '<div class="grid">'

    # Folder cards with placeholder icon and white folder name
    for d in folders:
        sub_path = os.path.join(current_path, d) if current_path else d
        html_items += f"""
        <div class="file-card">
            <a class="folder-link" href="/?path={sub_path}">
                <img src="https://img.icons8.com/ios-filled/150/f1f1f1/folder-invoices.png" alt="{d}">
                <div class="filename">{d}</div>
            </a>
            <div class="actions">
                <a class="btn delete" href="/delete?path={sub_path}" onclick="return confirm('Delete empty folder?')">🗑 Delete</a>
            </div>
        </div>
        """

    # Image file cards
    for f in files:
        file_rel_path = os.path.join(current_path, f) if current_path else f
        html_items += f"""
        <div class="file-card">
            <img src="/files/{file_rel_path}" alt="{f}">
            <div class="filename">{f}</div>
            <div class="actions">
                <a class="btn" href="/download/{file_rel_path}">⬇ Download</a>
                <a class="btn delete" href="/delete?path={file_rel_path}" onclick="return confirm('Delete file?')">🗑 Delete</a>
            </div>
        </div>
        """

    html_items += '</div>'

    return f"""
    <html>
    <head>
        <title>Dungeon Dreamgirls ❤️‍🔥</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #1e1e2f;
                color: #f1f1f1;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                text-align: center;
                font-size: 3em;
                color: #e63946;
                text-shadow: 2px 2px 5px #0d0d1a;
            }}
            h1 span {{ color: #fca311; }}
            form {{
                margin: 10px auto;
                text-align: center;
            }}
            input[type="file"], input[type="text"], input[type="submit"] {{
                padding: 8px;
                margin: 5px;
                border-radius: 5px;
                border: none;
            }}
            input[type="submit"] {{
                background-color: #e63946;
                color: white;
                cursor: pointer;
            }}
            input[type="submit"]:hover {{
                background-color: #f77f00;
            }}
            .grid {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                justify-content: center;
                margin-top: 20px;
            }}
            .file-card {{
                background: #2a2a3f;
                padding: 10px;
                border-radius: 10px;
                width: 150px;
                text-align: center;
                transition: transform 0.2s;
            }}
            .file-card:hover {{
                transform: scale(1.05);
            }}
            .file-card img {{
                width: 120px;
                height: 120px;
                object-fit: cover;
                border-radius: 5px;
                margin-bottom: 5px;
                border: 1px solid #555;
            }}
            .filename {{
                margin-bottom: 5px;
                font-size: 0.9em;
                word-wrap: break-word;
            }}
            .actions a {{
                display: inline-block;
                margin: 2px;
                padding: 5px 7px;
                border-radius: 5px;
                text-decoration: none;
                color: white;
                font-size: 0.8em;
            }}
            .btn {{ background-color: #457b9d; }}
            .btn:hover {{ background-color: #1d3557; }}
            .btn.delete {{ background-color: #e63946; }}
            .btn.delete:hover {{ background-color: #f77f00; }}
            .back {{
                display: inline-block;
                margin-bottom: 10px;
                color: #f1f1f1;
                text-decoration: none;
                font-weight: bold;
            }}
            .back:hover {{ color: #fca311; }}
            .folder-link {{
                color: #ffffff;          /* folder name white */
                text-decoration: none;
            }}
            .folder-link:hover {{
                color: #fca311;          /* hover gold */
            }}
        </style>
    </head>
    <body>
        <h1>Dungeon Dreamgirls <span>❤️‍🔥</span></h1>

        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*" required>
            <input type="submit" value="Upload to '{current_path or '/'}'">
        </form>

        <form action="/mkdir" method="GET">
            <input type="hidden" name="path" value="{current_path}">
            <input type="text" name="name" placeholder="New folder name" required autocomplete="off">
            <input type="submit" value="Create Folder">
        </form>

        {html_items}
    </body>
    </html>
    """

@app.route("/mkdir")
def mkdir():
    path = request.args.get("path", "")
    name = request.args.get("name", "")

    if not name:
        return redirect(url_for("index", path=path))

    folder = get_safe_path(path)
    os.makedirs(os.path.join(folder, name), exist_ok=True)

    return redirect(url_for("index", path=path))

@app.route("/files/<path:filename>")
def files(filename):
    return send_from_directory(BASE_FOLDER, filename)

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(BASE_FOLDER, filename, as_attachment=True)

@app.route("/delete")
def delete():
    path = request.args.get("path", "")
    full_path = get_safe_path(path)

    if os.path.isdir(full_path):
        try:
            os.rmdir(full_path)
        except Exception:
            pass
    elif os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except Exception:
            pass

    parent = os.path.dirname(path)
    return redirect(url_for("index", path=parent))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # default 10000 for local testing
    app.run(host="0.0.0.0", port=port)