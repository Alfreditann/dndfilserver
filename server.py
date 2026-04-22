import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote
from jinja2 import Environment, FileSystemLoader
import os
import shutil
import json
import mimetypes
import base64
from http.cookies import SimpleCookie

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

# Setup Jinja2
os.makedirs("templates", exist_ok=True)
env = Environment(loader=FileSystemLoader("templates"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def check_auth(auth_header):
    """Check basic auth credentials"""
    if not auth_header:
        return None
    try:
        auth_type, credentials = auth_header.split(' ', 1)
        if auth_type.lower() != 'basic':
            return None
        decoded = base64.b64decode(credentials).decode('utf-8')
        username, password = decoded.split(':', 1)
        if username in USERS and USERS[username]["password"] == password:
            return username
    except:
        pass
    return None

def get_user_base_folder(username):
    """Get the base folder for a user"""
    if username not in USERS:
        return BASE_FOLDER
    return USERS[username]["folder"]

def get_safe_path(path, base_folder):
    """Ensure path is within base_folder"""
    base_abs = os.path.abspath(base_folder)
    full_path = os.path.normpath(os.path.join(base_abs, path))
    if not full_path.startswith(base_abs):
        return base_abs
    return full_path

def allowed_file(filename):
    """Check if file extension is allowed"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def is_video_file(filename):
    """Check if file is a video"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in VIDEO_EXTENSIONS

def respond_html(handler, html, code=200):
    """Send HTML response"""
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html")
    handler.end_headers()
    handler.wfile.write(html.encode())
    handler.log_custom(code)

def respond_binary(handler, data, mime_type="application/octet-stream"):
    """Send binary response"""
    handler.send_response(200)
    handler.send_header("Content-Type", mime_type)
    handler.send_header("Content-Length", len(data))
    handler.end_headers()
    handler.wfile.write(data)
    handler.log_custom(200)

class Handler(BaseHTTPRequestHandler):
    """HTTP request handler for file server"""
    
    def log_custom(self, code=200):
        """Log request in aligned format"""
        msg = f"{self.client_address[0]:15} | {self.command:6} | {self.path:20} | {code}"
        if code >= 500:
            logging.error(msg)
        elif code >= 400:
            logging.warning(msg)
        else:
            logging.info(msg)
    
    def do_GET(self):
        """Handle GET requests"""
        auth_header = self.headers.get("Authorization")
        username = check_auth(auth_header)
        
        if not username:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Login"')
            self.end_headers()
            self.log_custom(401)
            return
        
        try:
            user_base_folder = get_user_base_folder(username)
            os.makedirs(user_base_folder, exist_ok=True)
            
            # Parse path from query string
            if '?' in self.path:
                path_part, query_part = self.path.split('?', 1)
                query_params = parse_qs(query_part)
                current_path = query_params.get('path', [''])[0]
            else:
                path_part = self.path
                current_path = ""
            
            # Handle static files
            if path_part.startswith("/static/"):
                file_path = "." + path_part
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream"
                    with open(file_path, "rb") as f:
                        respond_binary(self, f.read(), mime_type)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.log_custom(404)
                return
            
            # Handle /files/* - serve user files
            if path_part.startswith("/files/"):
                file_rel_path = unquote(path_part[7:])
                full_file_path = get_safe_path(file_rel_path, user_base_folder)
                if os.path.exists(full_file_path) and os.path.isfile(full_file_path):
                    mime_type, _ = mimetypes.guess_type(full_file_path)
                    if mime_type is None:
                        mime_type = "application/octet-stream"
                    with open(full_file_path, "rb") as f:
                        respond_binary(self, f.read(), mime_type)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.log_custom(404)
                return
            
            # Handle /download/* - serve files as attachment
            if path_part.startswith("/download/"):
                file_rel_path = unquote(path_part[10:])
                full_file_path = get_safe_path(file_rel_path, user_base_folder)
                if os.path.exists(full_file_path) and os.path.isfile(full_file_path):
                    with open(full_file_path, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(full_file_path)}"')
                    self.send_header("Content-Length", len(data))
                    self.end_headers()
                    self.wfile.write(data)
                    self.log_custom(200)
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.log_custom(404)
                return
            
            # Handle /delete
            if path_part == "/delete":
                path_to_delete = unquote(query_params.get('path', [''])[0])
                full_path = get_safe_path(path_to_delete, user_base_folder)
                
                if os.path.isdir(full_path):
                    try:
                        shutil.rmtree(full_path)
                    except Exception as e:
                        logging.error(f"Error deleting folder: {e}")
                elif os.path.isfile(full_path):
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        logging.error(f"Error deleting file: {e}")
                
                parent = os.path.dirname(path_to_delete)
                self.send_response(302)
                self.send_header("Location", f"/?path={parent}")
                self.end_headers()
                self.log_custom(302)
                return
            
            # Handle /mkdir
            if path_part == "/mkdir":
                folder_name = unquote(query_params.get('name', [''])[0])
                if folder_name:
                    folder_path = get_safe_path(current_path, user_base_folder)
                    os.makedirs(os.path.join(folder_path, folder_name), exist_ok=True)
                
                self.send_response(302)
                self.send_header("Location", f"/?path={current_path}")
                self.end_headers()
                self.log_custom(302)
                return
            
            # Handle main index page
            if path_part == "/" or path_part == "/index":
                folder = get_safe_path(current_path, user_base_folder)
                
                items = os.listdir(folder)
                files = []
                folders = []
                
                for item in items:
                    item_path = os.path.join(folder, item)
                    if os.path.isdir(item_path):
                        folders.append(item)
                    elif os.path.isfile(item_path) and allowed_file(item):
                        files.append(item)
                
                # Prepare image sources for lightbox
                image_sources = []
                for f in files:
                    if not is_video_file(f):
                        file_rel_path = os.path.join(current_path, f) if current_path else f
                        image_sources.append(f"/files/{file_rel_path.replace(chr(92), '/')}")
                
                template = env.get_template("index.html")
                html = template.render(
                    current_path=current_path,
                    folders=folders,
                    files=files,
                    is_video_file=is_video_file,
                    username=username,
                    image_sources=json.dumps(image_sources),
                    parent_path=os.path.dirname(current_path) if current_path else ""
                )
                respond_html(self, html)
                return
            
            # 404
            self.send_response(404)
            self.end_headers()
            self.log_custom(404)
            
        except Exception as e:
            logging.exception("Unhandled exception in do_GET:")
            self.send_response(500)
            self.end_headers()
            self.log_custom(500)
    
    def do_POST(self):
        """Handle POST requests"""
        auth_header = self.headers.get("Authorization")
        username = check_auth(auth_header)
        
        if not username:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Login"')
            self.end_headers()
            self.log_custom(401)
            return
        
        try:
            user_base_folder = get_user_base_folder(username)
            
            if '?' in self.path:
                path_part, query_part = self.path.split('?', 1)
                query_params = parse_qs(query_part)
                current_path = query_params.get('path', [''])[0]
            else:
                path_part = self.path
                current_path = ""
            
            # Handle file upload
            if path_part == "/" or path_part == "/index":
                content_type = self.headers.get('Content-Type', '')
                
                if 'multipart/form-data' in content_type:
                    boundary = content_type.split("boundary=")[1].encode()
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    
                    folder = get_safe_path(current_path, user_base_folder)
                    
                    # Simple multipart parser
                    parts = body.split(b'--' + boundary)
                    for part in parts:
                        if b'filename=' in part:
                            try:
                                # Extract filename
                                filename_start = part.find(b'filename="') + 10
                                filename_end = part.find(b'"', filename_start)
                                filename = part[filename_start:filename_end].decode('utf-8')
                                
                                # Extract file content
                                content_start = part.find(b'\r\n\r\n') + 4
                                content_end = part.rfind(b'\r\n')
                                content = part[content_start:content_end]
                                
                                if allowed_file(filename):
                                    with open(os.path.join(folder, filename), 'wb') as f:
                                        f.write(content)
                            except Exception as e:
                                logging.error(f"Error processing upload: {e}")
                
                self.send_response(302)
                self.send_header("Location", f"/?path={current_path}")
                self.end_headers()
                self.log_custom(302)
                return
            
            # 404
            self.send_response(404)
            self.end_headers()
            self.log_custom(404)
            
        except Exception as e:
            logging.exception("Unhandled exception in do_POST:")
            self.send_response(500)
            self.end_headers()
            self.log_custom(500)


# Run server
if __name__ == "__main__":
    server_address = ("0.0.0.0", 5500)
    httpd = HTTPServer(server_address, Handler)
    logging.info(f"Server running at http://{server_address[0]}:{server_address[1]}")
    httpd.serve_forever()