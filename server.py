from flask import Flask, request, redirect, url_for, send_from_directory, Response
import os
import shutil
import json

app = Flask(__name__)
BASE_FOLDER = "uploads"
os.makedirs(BASE_FOLDER, exist_ok=True)

# Multi-user system with folder access control
USERS = {
    "admin": {"password": "1234", "folder": "uploads"},
    "user2": {"password": "5678", "folder": "uploads2"}
}

ALLOWED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
    '.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'
}

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'}

def check_auth(u, p):
    if u not in USERS:
        return False
    return USERS[u]["password"] == p

def get_user_base_folder(username):
    """Get the base folder for a user"""
    if username not in USERS:
        return BASE_FOLDER
    return USERS[username]["folder"]

def authenticate():
    return Response("Login required", 401,
                    {"WWW-Authenticate": 'Basic realm="Login"'})

def get_safe_path(path, base_folder):
    base_abs = os.path.abspath(base_folder)
    full_path = os.path.normpath(os.path.join(base_abs, path))
    if not full_path.startswith(base_abs):
        return base_abs
    return full_path

def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def is_video_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    user_base_folder = get_user_base_folder(auth.username)
    os.makedirs(user_base_folder, exist_ok=True)
    
    current_path = request.args.get("path", "")
    folder = get_safe_path(current_path, user_base_folder)

    if request.method == "POST":
        uploaded_files = request.files.getlist("files")
        for file in uploaded_files:
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
    image_sources = []
    image_index = 0
    if current_path:
        parent = os.path.dirname(current_path)
        html_items += f'<a class="back" href="/?path={parent}">⬅ Back</a>'

    html_items += '<div class="grid">'

    # Folder cards
    for d in folders:
        sub_path = os.path.join(current_path, d) if current_path else d
        html_items += f"""
        <div class="file-card">
            <a class="folder-link" href="/?path={sub_path}">
                <img src="https://img.icons8.com/ios-filled/150/f1f1f1/folder-invoices.png" alt="{d}">
                <div class="filename">{d}</div>
            </a>
            <div class="actions">
                <a class="btn delete" href="/delete?path={sub_path}" onclick="return confirm('Delete folder and all its contents?')">🗑 Delete</a>
            </div>
        </div>
        """

    # Media file cards
    for f in files:
        file_rel_path = os.path.join(current_path, f) if current_path else f
        file_url_path = file_rel_path.replace("\\", "/")
        if is_video_file(f):
            media_preview = f'<video controls preload="metadata"><source src="/files/{file_url_path}"></video>'
        else:
            image_sources.append(f"/files/{file_url_path}")
            media_preview = f'<img src="/files/{file_url_path}" alt="{f}" onclick="openLightbox({image_index})" style="cursor:pointer">'
            image_index += 1
        html_items += f"""
        <div class="file-card">
            {media_preview}
            <div class="filename">{f}</div>
            <div class="actions">
                <a class="btn" href="/download/{file_url_path}">⬇ Download</a>
                <a class="btn delete" href="/delete?path={file_url_path}" onclick="return confirm('Delete file?')">🗑 Delete</a>
            </div>
        </div>
        """

    html_items += '</div>'

    return f"""
    <html>
    <head>
        <title>Dungeon Dreamgirls ❤️‍🔥</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
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
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
            }}
            input[type="file"], input[type="text"], input[type="submit"] {{
                padding: 8px;
                border-radius: 5px;
                border: none;
                font-size: 1em;
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
                flex: 1 0 120px;
                max-width: 150px;
            }}
            .file-card:hover {{ transform: scale(1.05); }}
            .file-card img {{
                width: 100%;
                height: 120px;
                object-fit: cover;
                border-radius: 5px;
                margin-bottom: 5px;
                border: 1px solid #555;
            }}
            .file-card video {{
                width: 100%;
                height: 120px;
                border-radius: 5px;
                margin-bottom: 5px;
                border: 1px solid #555;
                background: #000;
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
            .folder-link {{ color: #ffffff; text-decoration: none; }}
            .folder-link:hover {{ color: #fca311; }}
            #lightbox {{
                position: fixed;
                display: none;
                top: 0; left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.9);
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }}
            #lightbox img {{
                max-width: 90%;
                max-height: 90%;
                border-radius: 10px;
                box-shadow: 0 0 20px #000;
                object-fit: contain;
            }}
            .lightbox-nav {{
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(0, 0, 0, 0.45);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 999px;
                width: 44px;
                height: 44px;
                font-size: 28px;
                line-height: 38px;
                cursor: pointer;
                user-select: none;
            }}
            .lightbox-nav:hover {{
                background: rgba(255, 255, 255, 0.2);
            }}
            #lightbox-prev {{ left: 20px; }}
            #lightbox-next {{ right: 20px; }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 2em; }}
                .file-card {{ width: 45%; max-width: 150px; }}
                input[type="file"], input[type="text"], input[type="submit"] {{ width: 90%; font-size: 0.9em; }}
                .lightbox-nav {{
                    width: 38px;
                    height: 38px;
                    font-size: 24px;
                    line-height: 32px;
                }}
            }}
            @media (max-width: 400px) {{
                .file-card {{ width: 90%; max-width: 200px; }}
                .grid {{ gap: 10px; }}
            }}
        </style>
    </head>
    <body>
        <h1>Dungeon Dreamgirls <span>❤️‍🔥</span></h1>

        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="files" accept="image/*,video/*" multiple required>
            <input type="submit" value="Upload to '{current_path or '/'}'">
        </form>

        <form action="/mkdir" method="GET">
            <input type="hidden" name="path" value="{current_path}">
            <input type="text" name="name" placeholder="New folder name" required autocomplete="off">
            <input type="submit" value="Create Folder">
        </form>

        {html_items}

        <!-- Lightbox container -->
        <div id="lightbox" onclick="closeLightbox()">
            <button id="lightbox-prev" class="lightbox-nav" onclick="event.stopPropagation(); changeLightbox(-1)">&#10094;</button>
            <img id="lightbox-img" src="" onclick="event.stopPropagation()">
            <button id="lightbox-next" class="lightbox-nav" onclick="event.stopPropagation(); changeLightbox(1)">&#10095;</button>
        </div>

        <script>
        const lightboxImages = {json.dumps(image_sources)};
        let currentLightboxIndex = 0;

        function openLightbox(index) {{
            if (!lightboxImages.length) return;
            currentLightboxIndex = index;
            const lightbox = document.getElementById('lightbox');
            showLightboxImage(currentLightboxIndex);
            updateLightboxArrows();
            lightbox.style.display = 'flex';
        }}

        function showLightboxImage(index) {{
            const img = document.getElementById('lightbox-img');
            img.src = lightboxImages[index];
        }}

        function changeLightbox(step) {{
            if (!lightboxImages.length) return;
            currentLightboxIndex = (currentLightboxIndex + step + lightboxImages.length) % lightboxImages.length;
            showLightboxImage(currentLightboxIndex);
        }}

        function updateLightboxArrows() {{
            const showArrows = lightboxImages.length > 1;
            document.getElementById('lightbox-prev').style.display = showArrows ? 'block' : 'none';
            document.getElementById('lightbox-next').style.display = showArrows ? 'block' : 'none';
        }}

        function closeLightbox() {{
            document.getElementById('lightbox').style.display = 'none';
        }}

        document.addEventListener('keydown', function(e) {{
            const lightbox = document.getElementById('lightbox');
            if (lightbox.style.display !== 'flex') return;
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') changeLightbox(-1);
            if (e.key === 'ArrowRight') changeLightbox(1);
        }});
        </script>
    </body>
    </html>
    """

@app.route("/mkdir")
def mkdir():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    user_base_folder = get_user_base_folder(auth.username)
    path = request.args.get("path", "")
    name = request.args.get("name", "")
    if not name:
        return redirect(url_for("index", path=path))
    folder = get_safe_path(path, user_base_folder)
    os.makedirs(os.path.join(folder, name), exist_ok=True)
    return redirect(url_for("index", path=path))

@app.route("/files/<path:filename>")
def files(filename):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    user_base_folder = get_user_base_folder(auth.username)
    return send_from_directory(user_base_folder, filename)

@app.route("/download/<path:filename>")
def download(filename):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    user_base_folder = get_user_base_folder(auth.username)
    return send_from_directory(user_base_folder, filename, as_attachment=True)

@app.route("/delete")
def delete():
    import urllib.parse
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    user_base_folder = get_user_base_folder(auth.username)
    path = request.args.get("path", "")
    path = urllib.parse.unquote(path)  # decode URL
    full_path = get_safe_path(path, user_base_folder)

    if os.path.isdir(full_path):
        try:
            shutil.rmtree(full_path)
        except Exception as e:
            print("Error deleting folder:", e)
    elif os.path.isfile(full_path):
        try:
            os.remove(full_path)
        except Exception as e:
            print("Error deleting file:", e)

    parent = os.path.dirname(path)
    return redirect(url_for("index", path=parent))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)