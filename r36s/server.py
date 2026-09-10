"""
R36S Web File Manager - Backend Server
Dedicated to R36S physical console running dArkOS RE (Debian 12 Bookworm, Kernel 4.4.189)
Zero external dependencies (Python 3 standard library only).
"""

import os
import sys
import json
import time
import socket
import secrets
import shutil
import urllib.parse
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional, Tuple

SERVER_VERSION = "1.0.0-eng"
CHUNK_SIZE_DEFAULT = 2 * 1024 * 1024  # 2 MB

class UploadSession:
    """Manages chunked and resumable upload sessions."""
    def __init__(self, upload_id: str, filename: str, target_dir: str, total_size: int, token: str):
        self.upload_id = upload_id
        self.filename = filename
        self.target_dir = target_dir
        self.total_size = total_size
        self.token = token
        self.created_at = time.time()
        self.last_activity = time.time()
        # Create .part file directly inside the target directory for atomic os.rename()!
        self.part_path = os.path.join(target_dir, f".{upload_id}.part")
        self.final_path = os.path.join(target_dir, filename)
        self.received_bytes = 0
        self.received_chunks: List[int] = []

        # Initialize or check existing file
        if os.path.exists(self.part_path):
            self.received_bytes = os.path.getsize(self.part_path)
        else:
            # Ensure target directory exists and touch the part file
            os.makedirs(self.target_dir, exist_ok=True)
            with open(self.part_path, "wb"):
                pass

    def append_chunk(self, chunk_index: int, offset: int, data: bytes) -> int:
        self.last_activity = time.time()
        with open(self.part_path, "r+b" if os.path.exists(self.part_path) else "wb") as f:
            f.seek(offset)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        
        self.received_bytes = os.path.getsize(self.part_path)
        if chunk_index not in self.received_chunks:
            self.received_chunks.append(chunk_index)
            self.received_chunks.sort()
        return self.received_bytes

    def finalize(self) -> str:
        """Atomic rename within the exact same filesystem."""
        if not os.path.exists(self.part_path):
            raise FileNotFoundError("Part file missing")
        actual_size = os.path.getsize(self.part_path)
        if self.total_size > 0 and actual_size != self.total_size:
            raise ValueError(f"Size mismatch: expected {self.total_size}, got {actual_size}")
        
        # Atomic rename on the same filesystem
        os.rename(self.part_path, self.final_path)
        return self.final_path

    def cancel(self):
        if os.path.exists(self.part_path):
            try:
                os.unlink(self.part_path)
            except OSError:
                pass


class FileManagerBackend:
    """Core filesystem sandbox and state manager."""
    def __init__(self, allowed_roots: List[str], auth_token: str, ui_html_path: str):
        self.allowed_roots = [os.path.realpath(r) for r in allowed_roots if os.path.exists(r)]
        if not self.allowed_roots:
            # Fallback if specific mounts are not yet ready
            cwd = os.path.realpath(".")
            self.allowed_roots = [cwd]
        self.auth_token = auth_token
        self.ui_html_path = ui_html_path
        self.upload_sessions: Dict[str, UploadSession] = {}
        self.start_time = time.time()

    def refresh_roots(self) -> List[Dict[str, Any]]:
        """Dynamically detect active mount points."""
        detected = []
        candidates = ["/roms", "/roms2", "/media", "/mnt"]
        
        # Inspect /proc/mounts if available on Linux
        mounts_map = {}
        if os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            mounts_map[parts[1]] = parts[2]  # mountpoint -> fstype
            except Exception:
                pass

        for c in candidates:
            if os.path.exists(c):
                real_c = os.path.realpath(c)
                if os.path.isdir(real_c):
                    # Check free disk space
                    try:
                        total, used, free = shutil.disk_usage(real_c)
                    except Exception:
                        total, used, free = (0, 0, 0)
                    
                    label = os.path.basename(c) or c
                    if c == "/roms":
                        label = "SD1 (ROMs & Tools)"
                    elif c == "/roms2":
                        label = "SD2 (Second SD)"
                    elif "/media" in c or "/mnt" in c:
                        label = f"USB/OTG ({os.path.basename(c)})"

                    detected.append({
                        "path": real_c,
                        "display_name": label,
                        "fstype": mounts_map.get(c, "unknown"),
                        "total_bytes": total,
                        "free_bytes": free,
                        "used_bytes": used
                    })
                    if real_c not in self.allowed_roots:
                        self.allowed_roots.append(real_c)

        # Ensure we always have at least one valid root
        if not detected and self.allowed_roots:
            for r in self.allowed_roots:
                try:
                    total, used, free = shutil.disk_usage(r)
                except Exception:
                    total, used, free = (0, 0, 0)
                detected.append({
                    "path": r,
                    "display_name": os.path.basename(r) or r,
                    "fstype": "ext4/fat",
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_bytes": used
                })
        return detected

    def validate_safe_path(self, target_path: str, allow_symlinks_in_leaf: bool = False) -> str:
        """
        Anti-Path-Traversal and Anti-Symlink Bypass Validator.
        Checks that target resolves strictly inside one of the allowed roots.
        """
        if not target_path:
            raise PermissionError("Empty target path")

        canonical_target = os.path.realpath(target_path)

        # Prevent symlink attacks on destructive operations
        if not allow_symlinks_in_leaf and os.path.islink(target_path):
            raise PermissionError("Symbolic links are forbidden for mutating operations")

        is_safe = False
        for root in self.allowed_roots:
            canonical_root = os.path.realpath(root)
            if canonical_target == canonical_root or canonical_target.startswith(canonical_root + os.sep):
                is_safe = True
                break

        if not is_safe:
            raise PermissionError(f"Access denied: target '{target_path}' is outside sandbox roots")

        # Explicit blacklist of critical Linux directories
        forbidden_prefixes = ["/etc", "/proc", "/sys", "/dev", "/boot", "/root", "/bin", "/sbin", "/lib"]
        for fb in forbidden_prefixes:
            if canonical_target == fb or canonical_target.startswith(fb + os.sep):
                raise PermissionError(f"System directory '{fb}' is protected")

        return canonical_target

    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        safe_path = self.validate_safe_path(dir_path, allow_symlinks_in_leaf=True)
        if not os.path.isdir(safe_path):
            raise NotADirectoryError(f"'{dir_path}' is not a directory")

        entries = []
        try:
            with os.scandir(safe_path) as it:
                for entry in it:
                    is_symlink = entry.is_symlink()
                    is_dir = False
                    is_file = False
                    size = 0
                    mtime = 0
                    try:
                        stat_info = entry.stat()
                        is_dir = entry.is_dir(follow_symlinks=True)
                        is_file = entry.is_file(follow_symlinks=True)
                        size = stat_info.st_size
                        mtime = int(stat_info.st_mtime)
                    except (OSError, PermissionError):
                        pass

                    # Hide temporary files
                    if entry.name.endswith(".part") and entry.name.startswith("."):
                        continue

                    entries.append({
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "is_file": is_file,
                        "is_symlink": is_symlink,
                        "size": size,
                        "mtime": mtime
                    })
        except PermissionError:
            raise PermissionError(f"Permission denied reading '{dir_path}'")

        # Sort: directories first, then alphabetically
        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        # Parent directory
        parent = os.path.dirname(safe_path) if safe_path != "/" else None
        can_go_up = False
        if parent:
            try:
                self.validate_safe_path(parent, allow_symlinks_in_leaf=True)
                can_go_up = True
            except PermissionError:
                can_go_up = False

        return {
            "current_path": safe_path,
            "parent_path": parent if can_go_up else None,
            "entries": entries,
            "total_items": len(entries)
        }

    def make_directory(self, parent_dir: str, name: str) -> str:
        # Sanitize name
        clean_name = os.path.basename(name.strip())
        if not clean_name or clean_name in (".", ".."):
            raise ValueError("Invalid directory name")
        target = os.path.join(parent_dir, clean_name)
        safe_path = self.validate_safe_path(target)
        if os.path.exists(safe_path):
            raise FileExistsError("Directory already exists")
        os.makedirs(safe_path, exist_ok=False)
        return safe_path

    def rename_item(self, old_path: str, new_name: str) -> str:
        clean_name = os.path.basename(new_name.strip())
        if not clean_name or clean_name in (".", ".."):
            raise ValueError("Invalid target name")
        safe_old = self.validate_safe_path(old_path)
        if not os.path.exists(safe_old):
            raise FileNotFoundError("Source item does not exist")

        target = os.path.join(os.path.dirname(safe_old), clean_name)
        safe_new = self.validate_safe_path(target)
        if os.path.exists(safe_new):
            raise FileExistsError("An item with the destination name already exists")

        os.rename(safe_old, safe_new)
        return safe_new

    def delete_items(self, paths: List[str]) -> Dict[str, Any]:
        results = {"success": [], "errors": []}
        for p in paths:
            try:
                safe_p = self.validate_safe_path(p)
                if not os.path.exists(safe_p) and not os.path.islink(safe_p):
                    results["errors"].append({"path": p, "error": "Item not found"})
                    continue
                if os.path.isdir(safe_p) and not os.path.islink(safe_p):
                    shutil.rmtree(safe_p)
                else:
                    os.unlink(safe_p)
                results["success"].append(p)
            except Exception as e:
                results["errors"].append({"path": p, "error": str(e)})
        return results

    def move_items(self, sources: List[str], dest_dir: str) -> Dict[str, Any]:
        safe_dest = self.validate_safe_path(dest_dir)
        if not os.path.isdir(safe_dest):
            raise NotADirectoryError("Destination is not a valid directory")

        results = {"success": [], "errors": []}
        for s in sources:
            try:
                safe_src = self.validate_safe_path(s)
                dest_file = os.path.join(safe_dest, os.path.basename(safe_src))
                self.validate_safe_path(dest_file)
                if os.path.exists(dest_file):
                    results["errors"].append({"path": s, "error": "Destination file already exists"})
                    continue
                shutil.move(safe_src, dest_file)
                results["success"].append(s)
            except Exception as e:
                results["errors"].append({"path": s, "error": str(e)})
        return results

    def copy_items(self, sources: List[str], dest_dir: str) -> Dict[str, Any]:
        safe_dest = self.validate_safe_path(dest_dir)
        if not os.path.isdir(safe_dest):
            raise NotADirectoryError("Destination is not a valid directory")

        results = {"success": [], "errors": []}
        for s in sources:
            try:
                safe_src = self.validate_safe_path(s)
                dest_file = os.path.join(safe_dest, os.path.basename(safe_src))
                self.validate_safe_path(dest_file)
                if os.path.exists(dest_file):
                    results["errors"].append({"path": s, "error": "Destination file already exists"})
                    continue
                if os.path.isdir(safe_src):
                    shutil.copytree(safe_src, dest_file)
                else:
                    shutil.copy2(safe_src, dest_file)
                results["success"].append(s)
            except Exception as e:
                results["errors"].append({"path": s, "error": str(e)})
        return results


def make_request_handler(backend: FileManagerBackend):
    class R36SRequestHandler(BaseHTTPRequestHandler):
        server_version = f"R36S-WebFileManager/{SERVER_VERSION}"

        def log_message(self, format, *args):
            # Clean silent logger or write to file if needed
            sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {args[0]} {args[1]} {args[2]}\n")

        def send_json(self, status_code: int, data: Any):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "X-Auth-Token, Content-Type, X-Upload-Id, X-Chunk-Index, X-Total-Chunks")
            self.end_headers()
            self.wfile.write(body)

        def send_error_json(self, status_code: int, message: str):
            self.send_json(status_code, {"success": False, "error": message})

        def check_auth(self) -> bool:
            """Validates session token from Header or Query Param."""
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            # Check query param
            if "token" in query and query["token"][0] == backend.auth_token:
                return True

            # Check header
            token_header = self.headers.get("X-Auth-Token")
            if token_header and token_header == backend.auth_token:
                return True

            return False

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "X-Auth-Token, Content-Type, X-Upload-Id, X-Chunk-Index, X-Total-Chunks")
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # 1. Root / UI SPA
            if path in ("/", "/index.html"):
                if not self.check_auth():
                    self.send_response(401)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>401 Unauthorized</h1><p>Sessao invalida ou expirada. Escaneie o QR Code novamente no R36S.</p>")
                    return

                # Serve UI HTML
                if os.path.exists(backend.ui_html_path):
                    with open(backend.ui_html_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_error_json(500, "ui.html template missing")
                return

            # All API endpoints require authentication
            if not self.check_auth():
                self.send_error_json(401, "Invalid or missing auth token")
                return

            query = urllib.parse.parse_qs(parsed.query)

            # 2. Storage roots
            if path == "/api/storage":
                roots = backend.refresh_roots()
                self.send_json(200, {"success": True, "roots": roots})
                return

            # 3. System Status
            if path == "/api/status":
                uptime_sec = int(time.time() - backend.start_time)
                self.send_json(200, {
                    "success": True,
                    "version": SERVER_VERSION,
                    "uptime_seconds": uptime_sec,
                    "roots_count": len(backend.allowed_roots),
                    "active_uploads": len(backend.upload_sessions)
                })
                return

            # 4. List Directory
            if path == "/api/fs/list":
                target_dir = query.get("path", ["/roms"])[0]
                try:
                    data = backend.list_directory(target_dir)
                    self.send_json(200, {"success": True, "data": data})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 5. Upload Status / Resume Query
            if path == "/api/upload/status":
                upload_id = query.get("id", [""])[0]
                session = backend.upload_sessions.get(upload_id)
                if not session:
                    self.send_error_json(404, "Upload session not found or expired")
                    return
                self.send_json(200, {
                    "success": True,
                    "upload_id": session.upload_id,
                    "filename": session.filename,
                    "total_size": session.total_size,
                    "received_bytes": session.received_bytes,
                    "received_chunks": session.received_chunks
                })
                return

            # 6. File Download with HTTP Range Support (For Safari iOS & resuming)
            if path == "/api/download":
                file_path = query.get("path", [""])[0]
                try:
                    safe_path = backend.validate_safe_path(file_path, allow_symlinks_in_leaf=True)
                    if not os.path.isfile(safe_path):
                        self.send_error_json(404, "File not found")
                        return

                    file_size = os.path.getsize(safe_path)
                    filename = os.path.basename(safe_path)
                    encoded_filename = urllib.parse.quote(filename)

                    range_header = self.headers.get("Range")
                    start = 0
                    end = file_size - 1
                    status_code = 200

                    if range_header and range_header.startswith("bytes="):
                        ranges = range_header[6:].split("-")
                        try:
                            if ranges[0]:
                                start = int(ranges[0])
                            if len(ranges) > 1 and ranges[1]:
                                end = int(ranges[1])
                            status_code = 206
                        except ValueError:
                            pass

                    if start > end or start >= file_size:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{file_size}")
                        self.end_headers()
                        return

                    content_length = end - start + 1
                    self.send_response(status_code)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{encoded_filename}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", str(content_length))
                    if status_code == 206:
                        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                    self.end_headers()

                    # Stream file chunk by chunk
                    with open(safe_path, "rb") as f:
                        f.seek(start)
                        remaining = content_length
                        chunk_size = 64 * 1024
                        while remaining > 0:
                            read_bytes = min(remaining, chunk_size)
                            chunk = f.read(read_bytes)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            remaining -= len(chunk)
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            self.send_error_json(404, "Endpoint not found")

        def do_POST(self):
            if not self.check_auth():
                self.send_error_json(401, "Unauthorized")
                return

            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            content_length = int(self.headers.get("Content-Length", 0))

            # Helper to read JSON body
            def read_json_body():
                if content_length == 0:
                    return {}
                raw = self.rfile.read(content_length)
                return json.loads(raw.decode("utf-8"))

            # 1. Create Directory
            if path == "/api/fs/mkdir":
                try:
                    payload = read_json_body()
                    parent = payload.get("parent_path")
                    name = payload.get("name")
                    new_dir = backend.make_directory(parent, name)
                    self.send_json(200, {"success": True, "created": new_dir})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 2. Rename Item
            if path == "/api/fs/rename":
                try:
                    payload = read_json_body()
                    old_path = payload.get("old_path")
                    new_name = payload.get("new_name")
                    renamed = backend.rename_item(old_path, new_name)
                    self.send_json(200, {"success": True, "new_path": renamed})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 3. Delete Items
            if path == "/api/fs/delete":
                try:
                    payload = read_json_body()
                    paths = payload.get("paths", [])
                    res = backend.delete_items(paths)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 4. Move Items
            if path == "/api/fs/move":
                try:
                    payload = read_json_body()
                    sources = payload.get("sources", [])
                    dest = payload.get("dest_dir")
                    res = backend.move_items(sources, dest)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 5. Copy Items
            if path == "/api/fs/copy":
                try:
                    payload = read_json_body()
                    sources = payload.get("sources", [])
                    dest = payload.get("dest_dir")
                    res = backend.copy_items(sources, dest)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 6. Upload Initialization (Generates Secure Server-side Upload Session)
            if path == "/api/upload/init":
                try:
                    payload = read_json_body()
                    filename = os.path.basename(payload.get("filename", "").strip())
                    target_dir = payload.get("target_dir", "")
                    total_size = int(payload.get("total_size", 0))

                    if not filename:
                        raise ValueError("Filename is required")

                    safe_target = backend.validate_safe_path(target_dir)
                    if not os.path.isdir(safe_target):
                        raise NotADirectoryError(f"Target '{target_dir}' is not a directory")

                    # Generate cryptographically secure upload session ID
                    upload_id = secrets.token_hex(12)
                    session = UploadSession(
                        upload_id=upload_id,
                        filename=filename,
                        target_dir=safe_target,
                        total_size=total_size,
                        token=backend.auth_token
                    )
                    backend.upload_sessions[upload_id] = session

                    self.send_json(200, {
                        "success": True,
                        "upload_id": upload_id,
                        "filename": filename,
                        "part_path": session.part_path,
                        "received_bytes": session.received_bytes,
                        "chunk_size": CHUNK_SIZE_DEFAULT
                    })
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 7. Upload Chunk
            if path == "/api/upload/chunk":
                upload_id = self.headers.get("X-Upload-Id")
                chunk_index_header = self.headers.get("X-Chunk-Index", "0")
                offset_header = self.headers.get("X-Chunk-Offset", "0")

                session = backend.upload_sessions.get(upload_id)
                if not session:
                    self.send_error_json(404, "Invalid or expired upload session")
                    return

                try:
                    chunk_index = int(chunk_index_header)
                    offset = int(offset_header)
                    chunk_data = self.rfile.read(content_length)

                    new_received = session.append_chunk(chunk_index, offset, chunk_data)
                    self.send_json(200, {
                        "success": True,
                        "upload_id": upload_id,
                        "chunk_index": chunk_index,
                        "received_bytes": new_received
                    })
                except Exception as e:
                    self.send_error_json(500, f"Error writing chunk: {e}")
                return

            # 8. Upload Complete (Atomic Rename on exact same filesystem)
            if path == "/api/upload/complete":
                try:
                    payload = read_json_body()
                    upload_id = payload.get("upload_id")
                    session = backend.upload_sessions.get(upload_id)
                    if not session:
                        raise ValueError("Upload session not found")

                    final_path = session.finalize()
                    del backend.upload_sessions[upload_id]
                    self.send_json(200, {"success": True, "saved_path": final_path})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 9. Download Multiple Files as ZIP (Streamed from Disk)
            if path == "/api/download-zip":
                try:
                    payload = read_json_body()
                    paths = payload.get("paths", [])
                    if not paths:
                        raise ValueError("No paths provided")

                    # Create zip file in destination's local tmp folder
                    tmp_zip = os.path.join(os.path.dirname(backend.ui_html_path), f"batch_{secrets.token_hex(6)}.zip")
                    import zipfile
                    with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                        for p in paths:
                            safe_p = backend.validate_safe_path(p, allow_symlinks_in_leaf=True)
                            if os.path.isfile(safe_p):
                                zf.write(safe_p, arcname=os.path.basename(safe_p))
                            elif os.path.isdir(safe_p):
                                for root, _, files in os.walk(safe_p):
                                    for f in files:
                                        full_path = os.path.join(root, f)
                                        rel_path = os.path.relpath(full_path, os.path.dirname(safe_p))
                                        zf.write(full_path, arcname=rel_path)

                    zip_size = os.path.getsize(tmp_zip)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/zip")
                    self.send_header("Content-Disposition", "attachment; filename=\"R36S_Download.zip\"")
                    self.send_header("Content-Length", str(zip_size))
                    self.end_headers()

                    with open(tmp_zip, "rb") as zf:
                        while True:
                            buf = zf.read(64 * 1024)
                            if not buf:
                                break
                            self.wfile.write(buf)

                    try:
                        os.unlink(tmp_zip)
                    except OSError:
                        pass
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 10. Remote Safe Shutdown
            if path == "/api/shutdown":
                self.send_json(200, {"success": True, "message": "Server shutting down cleanly"})
                # Schedule shutdown in 0.5s so HTTP response finishes
                def delayed_kill():
                    time.sleep(0.5)
                    os._exit(0)
                import threading
                threading.Thread(target=delayed_kill).start()
                return

            self.send_error_json(404, "Endpoint not found")

    return R36SRequestHandler


# ---------------------------------------------------------------------------
# Pure Python QR Code Generator (Zero-Dependency)
# ---------------------------------------------------------------------------
GF_EXP = [0] * 512
GF_LOG = [0] * 256
_x = 1
for _i in range(255):
    GF_EXP[_i] = _x
    GF_EXP[_i + 255] = _x
    GF_LOG[_x] = _i
    _x <<= 1
    if _x & 256:
        _x ^= 0x11d

def gf_mul(x, y):
    if x == 0 or y == 0:
        return 0
    return GF_EXP[GF_LOG[x] + GF_LOG[y]]

def rs_poly_mul(p1, p2):
    res = [0] * (len(p1) + len(p2) - 1)
    for j in range(len(p2)):
        for i in range(len(p1)):
            res[i + j] ^= gf_mul(p1[i], p2[j])
    return res

def rs_generator_poly(nsym):
    g = [1]
    for i in range(nsym):
        g = rs_poly_mul(g, [1, GF_EXP[i]])
    return g

def rs_encode(data, nsym):
    gen = rs_generator_poly(nsym)
    res = [0] * (len(data) + nsym)
    res[:len(data)] = data
    for i in range(len(data)):
        coef = res[i]
        if coef != 0:
            for j in range(len(gen)):
                res[i + j] ^= gf_mul(gen[j], coef)
    return res[len(data):]

def encode_qr_matrix(text: str) -> list:
    data_bytes = text.encode("utf-8")
    version = 4
    size = 17 + 4 * version
    matrix = [[False] * size for _ in range(size)]
    reserved = [[False] * size for _ in range(size)]

    def set_module(r, c, val, is_res=True):
        if 0 <= r < size and 0 <= c < size:
            matrix[r][c] = val
            if is_res:
                reserved[r][c] = True

    def add_finder(r_start, c_start):
        for r in range(7):
            for c in range(7):
                if r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4):
                    set_module(r_start + r, c_start + c, True)
                else:
                    set_module(r_start + r, c_start + c, False)
        for r in range(-1, 8):
            for c in range(-1, 8):
                if r in (-1, 7) or c in (-1, 7):
                    if 0 <= r_start + r < size and 0 <= c_start + c < size:
                        set_module(r_start + r, c_start + c, False)

    add_finder(0, 0)
    add_finder(0, size - 7)
    add_finder(size - 7, 0)

    if version >= 2:
        align_pos = 24
        for r in range(-2, 3):
            for c in range(-2, 3):
                val = (abs(r) == 2 or abs(c) == 2 or (r == 0 and c == 0))
                set_module(align_pos + r, align_pos + c, val)

    for i in range(8, size - 8):
        set_module(6, i, i % 2 == 0)
        set_module(i, 6, i % 2 == 0)

    set_module(4 * version + 9, 8, True)

    bits = [0, 1, 0, 0]
    count = len(data_bytes)
    for i in range(7, -1, -1):
        bits.append((count >> i) & 1)
    for b in data_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    cap_bits = 80 * 8
    bits.extend([0] * min(4, cap_bits - len(bits)))
    while len(bits) % 8 != 0:
        bits.append(0)

    pad_bytes = [0xEC, 0x11]
    pad_idx = 0
    while len(bits) < cap_bits:
        pad_b = pad_bytes[pad_idx % 2]
        pad_idx += 1
        for i in range(7, -1, -1):
            bits.append((pad_b >> i) & 1)

    codewords = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for b in range(8):
            byte_val = (byte_val << 1) | bits[i + b]
        codewords.append(byte_val)

    ecc = rs_encode(codewords[:80], 20)
    all_codewords = codewords[:80] + ecc

    all_bits = []
    for cw in all_codewords:
        for i in range(7, -1, -1):
            all_bits.append((cw >> i) & 1)

    bit_idx = 0
    bit_len = len(all_bits)
    col = size - 1
    while col > 0:
        if col == 6:
            col -= 1
        col_range = (col, col - 1)
        upward = ((col + 1) // 2) % 2 == 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for c in col_range:
                if not reserved[r][c]:
                    val = bool(all_bits[bit_idx]) if bit_idx < bit_len else False
                    bit_idx += 1
                    if (r + c) % 2 == 0:
                        val = not val
                    matrix[r][c] = val
        col -= 2

    return matrix

def render_ansi_qr(text: str) -> str:
    try:
        matrix = encode_qr_matrix(text)
        size = len(matrix)
        quiet = 2
        padded_size = size + quiet * 2
        full_grid = [[False] * padded_size for _ in range(padded_size)]
        for r in range(size):
            for c in range(size):
                full_grid[r + quiet][c + quiet] = matrix[r][c]

        lines = []
        for r in range(0, padded_size, 2):
            row1 = full_grid[r]
            row2 = full_grid[r + 1] if r + 1 < padded_size else [False] * padded_size
            line_chars = []
            for c in range(padded_size):
                top = row1[c]
                bottom = row2[c]
                if top and bottom:
                    line_chars.append("█")
                elif top and not bottom:
                    line_chars.append("▀")
                elif not top and bottom:
                    line_chars.append("▄")
                else:
                    line_chars.append(" ")
            lines.append("".join(line_chars))
        return "\n".join(lines)
    except Exception:
        return f"[ URL: {text} ]"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="R36S Web File Manager Backend")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--token", type=str, required=True, help="Ephemeral auth token")
    parser.add_argument("--ui", type=str, default="ui.html", help="Path to ui.html")
    parser.add_argument("--roots", nargs="+", default=["/roms", "/roms2", "/media", "/mnt", "."], help="Allowed roots")
    args = parser.parse_args()

    backend = FileManagerBackend(allowed_roots=args.roots, auth_token=args.token, ui_html_path=args.ui)
    handler = make_request_handler(backend)

    # Bind on 0.0.0.0 for LAN access
    server_address = ("0.0.0.0", args.port)
    httpd = ThreadingHTTPServer(server_address, handler)
    print(f"R36S Backend started on port {args.port} with token {args.token}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()
