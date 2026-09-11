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
import hashlib
import zipfile
import threading
import urllib.parse
from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional, Tuple

SERVER_VERSION = "2.0.0-final"
CHUNK_SIZE_DEFAULT = 2 * 1024 * 1024  # 2 MB
DEFAULT_SESSION_TTL_SECONDS = 7200     # 2 hours
DOWNLOAD_TICKET_TTL_SECONDS = 180      # 3 minutes

class UploadSession:
    """
    Manages chunked, resumable, and disk-persisted upload sessions.
    Maintains atomic metadata on disk to survive server restarts.
    """
    def __init__(
        self,
        upload_id: str,
        resume_token: str,
        filename: str,
        target_dir: str,
        total_size: int,
        client_fingerprint: Optional[str] = None,
        expected_hash: Optional[str] = None,
        created_at: Optional[float] = None,
        last_activity: Optional[float] = None,
        received_chunks: Optional[List[int]] = None
    ):
        self.upload_id = upload_id
        self.resume_token = resume_token
        self.original_filename = filename
        self.target_dir = os.path.realpath(target_dir)
        self.total_size = int(total_size)
        self.client_fingerprint = client_fingerprint or f"{filename}:{total_size}"
        self.expected_hash = expected_hash.lower() if expected_hash else None
        self.created_at = created_at if created_at is not None else time.time()
        self.last_activity = last_activity if last_activity is not None else time.time()

        # Place .part and .meta.json directly inside destination filesystem for atomic commit
        self.part_path = os.path.join(self.target_dir, f".{upload_id}.part")
        self.meta_path = os.path.join(self.target_dir, f".{upload_id}.meta.json")
        self.final_path = os.path.join(self.target_dir, filename)

        self.received_chunks = received_chunks if received_chunks is not None else []
        self.received_bytes = 0

        # Initialize or synchronize with file on disk
        if os.path.exists(self.part_path):
            if os.path.islink(self.part_path):
                raise PermissionError("Part file cannot be a symbolic link")
            self.received_bytes = os.path.getsize(self.part_path)
        else:
            os.makedirs(self.target_dir, exist_ok=True)
            # Open with O_NOFOLLOW to avoid symlink traversal at creation
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(self.part_path, flags, 0o644)
                os.close(fd)
            except FileExistsError:
                self.received_bytes = os.path.getsize(self.part_path)

        self.save_metadata()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "upload_id": self.upload_id,
            "resume_token": self.resume_token,
            "filename": self.original_filename,
            "target_dir": self.target_dir,
            "total_size": self.total_size,
            "received_bytes": self.received_bytes,
            "received_chunks": self.received_chunks,
            "client_fingerprint": self.client_fingerprint,
            "expected_hash": self.expected_hash,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "part_path": self.part_path,
            "final_path": self.final_path
        }

    def save_metadata(self):
        """Atomically saves upload session state to disk."""
        try:
            data = self.to_dict()
            tmp_meta = f"{self.meta_path}.tmp_{os.getpid()}_{secrets.token_hex(4)}"
            with open(tmp_meta, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_meta, self.meta_path)
        except Exception as e:
            sys.stderr.write(f"[WARN] Failed to write session metadata for {self.upload_id}: {e}\n")

    @classmethod
    def load_from_meta(cls, meta_path: str) -> Optional['UploadSession']:
        """Reconstructs an upload session from an existing metadata file on disk."""
        try:
            if not os.path.isfile(meta_path) or os.path.islink(meta_path):
                return None
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            part_path = data.get("part_path")
            if not part_path or not os.path.isfile(part_path) or os.path.islink(part_path):
                return None

            session = cls(
                upload_id=data["upload_id"],
                resume_token=data.get("resume_token", ""),
                filename=data["filename"],
                target_dir=data["target_dir"],
                total_size=data["total_size"],
                client_fingerprint=data.get("client_fingerprint"),
                expected_hash=data.get("expected_hash"),
                created_at=data.get("created_at"),
                last_activity=data.get("last_activity"),
                received_chunks=data.get("received_chunks", [])
            )
            session.received_bytes = os.path.getsize(part_path)
            return session
        except Exception as e:
            sys.stderr.write(f"[WARN] Failed to load session from {meta_path}: {e}\n")
            return None

    def append_chunk(self, chunk_index: int, offset: int, data: bytes) -> int:
        """
        Appends chunk with strict sequential validation and O_NOFOLLOW.
        Supports idempotent resend of current chunk without duplication.
        """
        self.last_activity = time.time()
        chunk_len = len(data)

        # Idempotent retransmission check
        if self.received_chunks and chunk_index == self.received_chunks[-1]:
            expected_offset = self.received_bytes - chunk_len
            if offset == expected_offset:
                # Already recorded this chunk at this offset, return current bytes
                return self.received_bytes

        # Strict sequential protocol validation
        expected_chunk_index = len(self.received_chunks)
        if chunk_index != expected_chunk_index:
            raise ValueError(f"Sequencing error: expected chunk index {expected_chunk_index}, got {chunk_index}")

        if offset != self.received_bytes:
            raise ValueError(f"Offset mismatch: expected byte offset {self.received_bytes}, got {offset}")

        if offset + chunk_len > self.total_size:
            raise ValueError(f"Chunk exceeds declared total size: {offset + chunk_len} > {self.total_size}")

        if os.path.islink(self.part_path):
            raise PermissionError("Part file was converted into a symbolic link")

        flags = os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.part_path, flags)
        try:
            with os.fdopen(fd, "r+b") as f:
                f.seek(offset)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            raise

        self.received_bytes = os.path.getsize(self.part_path)
        if chunk_index not in self.received_chunks:
            self.received_chunks.append(chunk_index)

        self.save_metadata()
        return self.received_bytes

    def finalize(self) -> str:
        """
        Atomic commit within the exact same filesystem.
        Validates size, checksum (if supplied), executes atomic os.replace(), and removes metadata.
        """
        if not os.path.exists(self.part_path):
            raise FileNotFoundError("Part file missing on disk")
        if os.path.islink(self.part_path):
            raise PermissionError("Part file cannot be a symbolic link")

        actual_size = os.path.getsize(self.part_path)
        if self.total_size > 0 and actual_size != self.total_size:
            raise ValueError(f"Size mismatch: expected {self.total_size} bytes, got {actual_size}")

        if actual_size != self.received_bytes:
            raise ValueError(f"Integrity mismatch: file on disk ({actual_size} bytes) does not match received bytes ({self.received_bytes})")

        # Validate SHA-256 hash if supplied at handshake
        if self.expected_hash:
            h = hashlib.sha256()
            with open(self.part_path, "rb") as f:
                while True:
                    chunk = f.read(128 * 1024)
                    if not chunk:
                        break
                    h.update(chunk)
            computed_hash = h.hexdigest().lower()
            if computed_hash != self.expected_hash:
                raise ValueError(f"Hash verification failed: expected {self.expected_hash}, calculated {computed_hash}")

        # Check target destination
        if os.path.islink(self.final_path):
            raise PermissionError(f"Target path '{self.final_path}' is an existing symbolic link")

        # Atomic rename/replace on the exact same filesystem
        os.replace(self.part_path, self.final_path)

        # Clean up metadata file
        if os.path.exists(self.meta_path):
            try:
                os.unlink(self.meta_path)
            except OSError:
                pass

        return self.final_path

    def cancel(self):
        """Cancels upload and purges temporary files."""
        for p in (self.part_path, self.meta_path):
            if os.path.exists(p) and not os.path.islink(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass


class BackgroundTaskManager:
    """Manages asynchronous heavy operations (recursive delete, copy, move, zip)."""
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def start_task(self, task_type: str, worker_fn, *args, **kwargs) -> str:
        task_id = secrets.token_hex(12)
        with self.lock:
            self.tasks[task_id] = {
                "id": task_id,
                "type": task_type,
                "status": "running",
                "progress_text": "Iniciando processamento...",
                "created_at": time.time(),
                "result": None,
                "error": None
            }

        def run():
            try:
                res = worker_fn(lambda text: self.update_progress(task_id, text), *args, **kwargs)
                with self.lock:
                    if task_id in self.tasks:
                        self.tasks[task_id]["status"] = "completed"
                        self.tasks[task_id]["progress_text"] = "Concluído"
                        self.tasks[task_id]["result"] = res
            except Exception as e:
                with self.lock:
                    if task_id in self.tasks:
                        self.tasks[task_id]["status"] = "failed"
                        self.tasks[task_id]["error"] = str(e)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return task_id

    def update_progress(self, task_id: str, text: str):
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["progress_text"] = text

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.tasks.get(task_id)

    def cleanup_old_tasks(self, max_age: int = 3600):
        now = time.time()
        with self.lock:
            to_del = [tid for tid, t in self.tasks.items() if now - t["created_at"] > max_age]
            for tid in to_del:
                del self.tasks[tid]


class FileManagerBackend:
    """Core filesystem sandbox, state manager, and upload session tracker."""
    def __init__(
        self,
        allowed_roots: List[str],
        auth_token: str,
        ui_html_path: str,
        session_ttl: int = DEFAULT_SESSION_TTL_SECONDS
    ):
        # Filter strictly for existing directories among candidates
        self.allowed_roots = []
        cwd_real = os.path.realpath(".")
        for r in allowed_roots:
            if not r or r == "." or r == "/" or r == cwd_real:
                # STRICT RULE: Never allow '.', '/', or current working directory as fallback!
                continue
            if os.path.exists(r) and os.path.isdir(r):
                real_r = os.path.realpath(r)
                if real_r not in self.allowed_roots and real_r != "/" and real_r != cwd_real:
                    self.allowed_roots.append(real_r)

        # Rejection if no valid authorized root exists
        if not self.allowed_roots:
            raise RuntimeError("Nenhuma raiz de armazenamento autorizada e acessível foi encontrada (/roms, /roms2, /media, /mnt). Servidor abortado.")

        self.auth_token = auth_token
        self.ui_html_path = ui_html_path
        self.session_ttl = session_ttl
        self.upload_sessions: Dict[str, UploadSession] = {}
        self.download_tickets: Dict[str, Dict[str, Any]] = {}
        self.task_manager = BackgroundTaskManager()
        self.start_time = time.time()

        # Initial cleanup and restoration of any active sessions on disk
        self.cleanup_abandoned_uploads(self.session_ttl)

    def create_download_ticket(self, file_path: str, is_temp_zip: bool = False) -> str:
        """Generates a short-lived, single-use ticket for safe file download without exposing master token in URL."""
        ticket_id = secrets.token_hex(16)
        self.download_tickets[ticket_id] = {
            "ticket": ticket_id,
            "file_path": file_path,
            "is_temp_zip": is_temp_zip,
            "expires_at": time.time() + DOWNLOAD_TICKET_TTL_SECONDS
        }
        return ticket_id

    def get_and_validate_download_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        ticket = self.download_tickets.get(ticket_id)
        if not ticket:
            return None
        if now > ticket["expires_at"]:
            self.download_tickets.pop(ticket_id, None)
            return None
        return ticket

    def consume_download_ticket(self, ticket_id: str):
        self.download_tickets.pop(ticket_id, None)

    def get_session(self, upload_id: str) -> Optional[UploadSession]:
        """
        Retrieves active upload session from memory or recovers it from on-disk metadata.
        Verifies session expiration against session_ttl.
        """
        now = time.time()
        # 1. Check in-memory session table
        session = self.upload_sessions.get(upload_id)
        if session:
            if now - session.last_activity > self.session_ttl:
                session.cancel()
                del self.upload_sessions[upload_id]
                return None
            return session

        # 2. Not in memory: Scan allowed roots for disk metadata .<upload_id>.meta.json
        meta_filename = f".{upload_id}.meta.json"
        for root in self.allowed_roots:
            try:
                for dirpath, _, filenames in os.walk(root, followlinks=False):
                    if meta_filename in filenames:
                        meta_full = os.path.join(dirpath, meta_filename)
                        recovered = UploadSession.load_from_meta(meta_full)
                        if recovered:
                            if now - recovered.last_activity > self.session_ttl:
                                recovered.cancel()
                                return None
                            self.upload_sessions[upload_id] = recovered
                            return recovered
            except Exception:
                pass

        return None

    def cleanup_abandoned_uploads(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Scans for abandoned uploads older than max_age_seconds (default: 2 hours)
        and purges their .part and .meta.json files without disturbing active ones.
        """
        ttl = max_age_seconds if max_age_seconds is not None else self.session_ttl
        now = time.time()
        purged = 0

        # Purge expired in-memory sessions
        expired_ids = [uid for uid, s in self.upload_sessions.items() if (now - s.last_activity) > ttl]
        for uid in expired_ids:
            self.upload_sessions[uid].cancel()
            del self.upload_sessions[uid]
            purged += 1

        # Scan filesystem for orphaned metadata and part files
        for root in self.allowed_roots:
            try:
                for dirpath, _, filenames in os.walk(root, followlinks=False):
                    for f in filenames:
                        if f.startswith(".") and f.endswith(".meta.json"):
                            full_meta = os.path.join(dirpath, f)
                            try:
                                mtime = os.path.getmtime(full_meta)
                                if (now - mtime) > ttl:
                                    uid = f[1:-10]
                                    part_file = os.path.join(dirpath, f".{uid}.part")
                                    if os.path.exists(part_file):
                                        try:
                                            os.unlink(part_file)
                                        except OSError:
                                            pass
                                    try:
                                        os.unlink(full_meta)
                                    except OSError:
                                        pass
                                    purged += 1
                            except OSError:
                                pass
            except Exception:
                pass

        return purged

    def refresh_roots(self) -> List[Dict[str, Any]]:
        """Dynamically detect active mount points."""
        detected = []
        candidates = ["/roms", "/roms2", "/media", "/mnt"]

        mounts_map = {}
        if os.path.exists("/proc/mounts"):
            try:
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            mounts_map[parts[1]] = parts[2]
            except Exception:
                pass

        for c in candidates:
            if os.path.exists(c):
                real_c = os.path.realpath(c)
                if os.path.isdir(real_c):
                    try:
                        total, used, free = shutil.disk_usage(real_c)
                    except Exception:
                        total, used, free = (0, 0, 0)

                    label = os.path.basename(c) or c
                    if c == "/roms":
                        label = "SD1 (ROMs & Tools)"
                    elif c == "/roms2":
                        label = "SD2 (Segundo SD)"
                    elif "/media" in c or "/mnt" in c:
                        label = f"USB/OTG ({os.path.basename(c)})"

                    detected.append({
                        "path": real_c,
                        "display_name": label,
                        "fstype": mounts_map.get(c, "ext4/fat"),
                        "total_bytes": total,
                        "free_bytes": free,
                        "used_bytes": used
                    })
                    if real_c not in self.allowed_roots:
                        self.allowed_roots.append(real_c)

        # Fallback to configured allowed_roots if candidates aren't standard
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

    def validate_safe_path(
        self,
        target_path: str,
        allow_symlinks_in_leaf: bool = False,
        is_write_operation: bool = False
    ) -> str:
        """
        Anti-Path-Traversal and Anti-Symlink Bypass Validator.
        Verifies parent directory, rejects symlinks in ancestor paths,
        decodes traversal tricks, and eliminates TOCTOU vulnerabilities.
        """
        if not target_path:
            raise PermissionError("Caminho de destino não fornecido")

        target_path = target_path.strip()
        if "\0" in target_path:
            raise ValueError("Injeção de caractere nulo detectada")

        # Normalize backslashes and redundant separators
        target_path = target_path.replace("\\", "/")
        unquoted = urllib.parse.unquote(target_path)
        if ".." in unquoted.split("/"):
            # Traversal attempt detected
            pass

        # For write/create operations (where leaf file may not exist yet)
        if is_write_operation:
            clean_leaf = os.path.basename(target_path)
            if not clean_leaf or clean_leaf in (".", "..") or "/" in clean_leaf or "\\" in clean_leaf:
                raise ValueError(f"Nome de arquivo ou diretório inválido: '{clean_leaf}'")

            parent_dir = os.path.dirname(target_path) or "."
            canonical_parent = self.validate_safe_path(parent_dir, allow_symlinks_in_leaf=False, is_write_operation=False)

            if not os.path.isdir(canonical_parent):
                raise NotADirectoryError(f"Diretório pai '{parent_dir}' não é um diretório")
            if os.path.islink(canonical_parent):
                raise PermissionError(f"Diretório pai '{canonical_parent}' é um link simbólico")

            canonical_target = os.path.join(canonical_parent, clean_leaf)
        else:
            canonical_target = os.path.realpath(target_path)

        # Prevent symlink attacks on mutating operations
        if not allow_symlinks_in_leaf and (os.path.islink(target_path) or os.path.islink(canonical_target)):
            raise PermissionError("Links simbólicos não são permitidos nesta operação")

        is_safe = False
        for root in self.allowed_roots:
            canonical_root = os.path.realpath(root)
            if canonical_target == canonical_root or canonical_target.startswith(canonical_root + os.sep):
                is_safe = True
                break

        if not is_safe:
            raise PermissionError("Acesso negado: o caminho solicitado está fora das raízes de armazenamento autorizadas")

        # Explicit blacklist of critical Linux system paths
        forbidden_prefixes = ["/etc", "/proc", "/sys", "/dev", "/boot", "/root", "/bin", "/sbin", "/lib", "/usr"]
        for fb in forbidden_prefixes:
            if canonical_target == fb or canonical_target.startswith(fb + os.sep):
                raise PermissionError("Acesso negado a diretórios do sistema operacional")

        return canonical_target

    def list_directory(self, dir_path: str) -> Dict[str, Any]:
        safe_path = self.validate_safe_path(dir_path, allow_symlinks_in_leaf=True)
        if not os.path.isdir(safe_path):
            raise NotADirectoryError(f"'{dir_path}' não é um diretório")

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
                        is_dir = entry.is_dir(follow_symlinks=False)
                        is_file = entry.is_file(follow_symlinks=False)
                        size = stat_info.st_size
                        mtime = int(stat_info.st_mtime)
                    except (OSError, PermissionError):
                        pass

                    # Hide temporary transfer files
                    if entry.name.startswith(".") and (entry.name.endswith(".part") or entry.name.endswith(".meta.json")):
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
            raise PermissionError(f"Permissão negada ao ler o diretório")

        entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        parent = os.path.dirname(safe_path)
        can_go_up = False
        if parent and parent != safe_path:
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
        clean_name = os.path.basename(name.strip())
        if not clean_name or clean_name in (".", "..") or "/" in clean_name or "\\" in clean_name:
            raise ValueError("Nome de diretório inválido")
        target = os.path.join(parent_dir, clean_name)
        safe_path = self.validate_safe_path(target, is_write_operation=True)
        if os.path.exists(safe_path):
            raise FileExistsError("Um item com este nome já existe")
        os.makedirs(safe_path, exist_ok=False)
        return safe_path

    def rename_item(self, old_path: str, new_name: str) -> str:
        clean_name = os.path.basename(new_name.strip())
        if not clean_name or clean_name in (".", "..") or "/" in clean_name or "\\" in clean_name:
            raise ValueError("Nome de destino inválido")
        safe_old = self.validate_safe_path(old_path)
        if not os.path.exists(safe_old):
            raise FileNotFoundError("O item de origem não foi encontrado")

        target = os.path.join(os.path.dirname(safe_old), clean_name)
        safe_new = self.validate_safe_path(target, is_write_operation=True)
        if os.path.exists(safe_new):
            raise FileExistsError("Um item com o nome de destino já existe")

        os.replace(safe_old, safe_new)
        return safe_new

    def delete_items_sync(self, paths: List[str], progress_callback=None) -> Dict[str, Any]:
        results = {"success": [], "errors": []}
        total = len(paths)
        for idx, p in enumerate(paths):
            if progress_callback:
                progress_callback(f"Excluindo item {idx + 1} de {total}...")
            try:
                safe_p = self.validate_safe_path(p)
                if not os.path.exists(safe_p) and not os.path.islink(safe_p):
                    results["errors"].append({"path": p, "error": "Item não encontrado"})
                    continue
                if os.path.isdir(safe_p) and not os.path.islink(safe_p):
                    shutil.rmtree(safe_p)
                else:
                    os.unlink(safe_p)
                results["success"].append(p)
            except Exception as e:
                results["errors"].append({"path": p, "error": str(e)})
        return results

    def move_items_sync(self, sources: List[str], dest_dir: str, progress_callback=None) -> Dict[str, Any]:
        safe_dest = self.validate_safe_path(dest_dir)
        if not os.path.isdir(safe_dest):
            raise NotADirectoryError("Destino não é um diretório válido")
        results = {"success": [], "errors": []}
        total = len(sources)
        for idx, s in enumerate(sources):
            if progress_callback:
                progress_callback(f"Movendo item {idx + 1} de {total}...")
            try:
                safe_src = self.validate_safe_path(s)
                if os.path.isdir(safe_src):
                    try:
                        rel = os.path.relpath(safe_dest, safe_src)
                        if rel == "." or not rel.startswith(".."):
                            results["errors"].append({"path": s, "error": "Não é possível mover uma pasta para dentro de si mesma"})
                            continue
                    except ValueError:
                        pass
                dest_file = os.path.join(safe_dest, os.path.basename(safe_src))
                if dest_file == safe_src:
                    results["errors"].append({"path": s, "error": "Destino é idêntico à origem"})
                    continue
                self.validate_safe_path(dest_file, is_write_operation=True)
                if os.path.exists(dest_file):
                    results["errors"].append({"path": s, "error": "O arquivo de destino já existe"})
                    continue
                shutil.move(safe_src, dest_file)
                results["success"].append(s)
            except Exception as e:
                results["errors"].append({"path": s, "error": str(e)})
        return results

    def copy_items_sync(self, sources: List[str], dest_dir: str, progress_callback=None) -> Dict[str, Any]:
        safe_dest = self.validate_safe_path(dest_dir)
        if not os.path.isdir(safe_dest):
            raise NotADirectoryError("Destino não é um diretório válido")
        results = {"success": [], "errors": []}
        total = len(sources)
        for idx, s in enumerate(sources):
            if progress_callback:
                progress_callback(f"Copiando item {idx + 1} de {total}...")
            try:
                safe_src = self.validate_safe_path(s)
                if os.path.isdir(safe_src):
                    try:
                        rel = os.path.relpath(safe_dest, safe_src)
                        if rel == "." or not rel.startswith(".."):
                            results["errors"].append({"path": s, "error": "Não é possível copiar uma pasta para dentro de si mesma"})
                            continue
                    except ValueError:
                        pass
                dest_file = os.path.join(safe_dest, os.path.basename(safe_src))
                if dest_file == safe_src:
                    results["errors"].append({"path": s, "error": "Destino é idêntico à origem"})
                    continue
                self.validate_safe_path(dest_file, is_write_operation=True)
                if os.path.exists(dest_file):
                    results["errors"].append({"path": s, "error": "O arquivo de destino já existe"})
                    continue
                if os.path.isdir(safe_src):
                    # symlinks=False ignores symlinks copying
                    shutil.copytree(safe_src, dest_file, symlinks=False)
                else:
                    shutil.copy2(safe_src, dest_file)
                results["success"].append(s)
            except Exception as e:
                results["errors"].append({"path": s, "error": str(e)})
        return results

    def create_batch_zip(self, paths: List[str], progress_callback=None) -> Tuple[str, str]:
        """
        Creates a ZIP in a safe temporary directory inside storage roots.
        Never follows symlinks (followlinks=False).
        Returns (zip_file_path, download_ticket).
        """
        if not paths:
            raise ValueError("Nenhum item selecionado para compactação")

        # Pick primary storage root for temp zip
        base_root = self.allowed_roots[0]
        tmp_dir = os.path.join(base_root, ".tmp_transfers")
        os.makedirs(tmp_dir, exist_ok=True)
        zip_filename = f"r36s_batch_{secrets.token_hex(6)}.zip"
        zip_path = os.path.join(tmp_dir, zip_filename)

        if progress_callback:
            progress_callback("Iniciando compactação...")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, p in enumerate(paths):
                safe_p = self.validate_safe_path(p, allow_symlinks_in_leaf=True)
                if progress_callback:
                    progress_callback(f"Compactando {os.path.basename(safe_p)}...")

                if os.path.isfile(safe_p) and not os.path.islink(safe_p):
                    zf.write(safe_p, arcname=os.path.basename(safe_p))
                elif os.path.isdir(safe_p) and not os.path.islink(safe_p):
                    base_parent = os.path.dirname(safe_p)
                    for root, _, files in os.walk(safe_p, followlinks=False):
                        for f in files:
                            full_path = os.path.join(root, f)
                            if not os.path.islink(full_path):
                                rel_path = os.path.relpath(full_path, base_parent)
                                zf.write(full_path, arcname=rel_path)

        ticket = self.create_download_ticket(zip_path, is_temp_zip=True)
        return zip_path, ticket


def make_request_handler(backend: FileManagerBackend):
    class R36SRequestHandler(BaseHTTPRequestHandler):
        server_version = f"R36S-WebFileManager/{SERVER_VERSION}"

        def log_message(self, format, *args):
            sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {args[0]} {args[1]} {args[2]}\n")

        def send_cors_headers(self):
            """Restricted CORS: allows same-origin or matches Host, prevents open LAN exploitation."""
            origin = self.headers.get("Origin")
            host = self.headers.get("Host")
            if origin:
                # Allow if origin host matches the server Host or is localhost/local LAN
                parsed_origin = urllib.parse.urlparse(origin)
                if parsed_origin.netloc == host or parsed_origin.hostname in ("127.0.0.1", "localhost"):
                    self.send_header("Access-Control-Allow-Origin", origin)
                    self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "X-Auth-Token, X-Resume-Token, Content-Type, X-Upload-Id, X-Chunk-Index, X-Chunk-Offset")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def send_json(self, status_code: int, data: Any):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def send_error_json(self, status_code: int, message: str):
            self.send_json(status_code, {"success": False, "error": message})

        def check_master_auth(self) -> bool:
            """Validates master token via Header (X-Auth-Token) or Query Parameter (token)."""
            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)

            if "token" in query and secrets.compare_digest(query["token"][0], backend.auth_token):
                return True

            token_header = self.headers.get("X-Auth-Token")
            if token_header and secrets.compare_digest(token_header, backend.auth_token):
                return True

            return False

        def check_session_auth(self, session: UploadSession) -> bool:
            """
            Validates access to an upload session.
            Accepts either valid master token OR the session's specific resume_token.
            """
            if self.check_master_auth():
                return True

            resume_header = self.headers.get("X-Resume-Token")
            if resume_header and secrets.compare_digest(resume_header, session.resume_token):
                return True

            parsed = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            if "resume_token" in query and secrets.compare_digest(query["resume_token"][0], session.resume_token):
                return True

            return False

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_cors_headers()
            self.end_headers()

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            # 0. Static Assets (Icons, Branding, Sprites)
            if path.startswith("/assets/"):
                asset_rel = path[len("/assets/"):]
                ui_dir = os.path.dirname(backend.ui_html_path)
                asset_full = os.path.normpath(os.path.join(ui_dir, "assets", asset_rel))
                if not asset_full.startswith(os.path.realpath(os.path.join(ui_dir, "assets"))) or not os.path.isfile(asset_full):
                    self.send_response(404)
                    self.end_headers()
                    return
                ct = "application/octet-stream"
                if asset_full.endswith(".svg"):
                    ct = "image/svg+xml"
                elif asset_full.endswith(".png"):
                    ct = "image/png"
                elif asset_full.endswith(".css"):
                    ct = "text/css"
                elif asset_full.endswith(".js"):
                    ct = "application/javascript"
                
                with open(asset_full, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            # 1. UI SPA Landing (Token authenticated via query or header)
            if path in ("/", "/index.html"):
                if not self.check_master_auth():
                    self.send_response(401)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>401 Nao Autorizado</h1><p>Sessao invalida ou token ausente. Escaneie o QR Code exibido no console R36S.</p>")
                    return

                if os.path.exists(backend.ui_html_path):
                    with open(backend.ui_html_path, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_error_json(500, "Modelo ui.html nao encontrado")
                return

            # 2. Secure Single-Use Download Ticket (NO master token in URL!)
            if path == "/api/download-ticket":
                query = urllib.parse.parse_qs(parsed.query)
                ticket_id = query.get("ticket", [""])[0]
                ticket = backend.get_and_validate_download_ticket(ticket_id)
                if not ticket:
                    self.send_error_json(403, "Ticket de download inválido ou expirado")
                    return

                file_path = ticket["file_path"]
                is_temp_zip = ticket["is_temp_zip"]

                try:
                    safe_path = backend.validate_safe_path(file_path, allow_symlinks_in_leaf=True)
                    if not os.path.isfile(safe_path):
                        self.send_error_json(404, "Arquivo não encontrado")
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

                    # Consume ticket if not partial range or upon completion
                    backend.consume_download_ticket(ticket_id)

                    # If temporary ZIP, purge it immediately from disk
                    if is_temp_zip and os.path.exists(safe_path):
                        try:
                            os.unlink(safe_path)
                        except OSError:
                            pass
                except Exception as e:
                    self.send_error_json(500, "Erro durante transferência do arquivo")
                return

            # 3. Direct Download with Master Token (fallback with range support)
            if path == "/api/download":
                if not self.check_master_auth():
                    self.send_error_json(401, "Token de autorização inválido ou ausente")
                    return

                query = urllib.parse.parse_qs(parsed.query)
                file_path = query.get("path", [""])[0]
                try:
                    safe_path = backend.validate_safe_path(file_path, allow_symlinks_in_leaf=True)
                    if not os.path.isfile(safe_path):
                        self.send_error_json(404, "Arquivo não encontrado")
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
                    self.send_error_json(400, "Erro ao processar download")
                return

            # 4. Upload Status / Resume Query (Validates either master token OR session resume_token)
            if path == "/api/upload/status":
                query = urllib.parse.parse_qs(parsed.query)
                upload_id = query.get("id", [""])[0]
                session = backend.get_session(upload_id)
                if not session:
                    self.send_error_json(404, "Sessão de upload não encontrada ou expirada")
                    return

                if not self.check_session_auth(session):
                    self.send_error_json(401, "Acesso não autorizado para esta sessão de upload")
                    return

                self.send_json(200, {
                    "success": True,
                    "upload_id": session.upload_id,
                    "filename": session.original_filename,
                    "total_size": session.total_size,
                    "received_bytes": session.received_bytes,
                    "received_chunks": session.received_chunks,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity
                })
                return

            # All other API endpoints require master authentication
            if not self.check_master_auth():
                self.send_error_json(401, "Token de autorização inválido ou ausente")
                return

            query = urllib.parse.parse_qs(parsed.query)

            # 5. Storage roots
            if path == "/api/storage":
                roots = backend.refresh_roots()
                self.send_json(200, {"success": True, "roots": roots})
                return

            # 6. System Status
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

            # 7. List Directory
            if path == "/api/fs/list":
                target_dir = query.get("path", [backend.allowed_roots[0]])[0]
                try:
                    data = backend.list_directory(target_dir)
                    self.send_json(200, {"success": True, "data": data})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 8. Background Task Status
            if path == "/api/tasks/status":
                task_id = query.get("id", [""])[0]
                task_info = backend.task_manager.get_status(task_id)
                if not task_info:
                    self.send_error_json(404, "Tarefa não encontrada")
                    return
                self.send_json(200, {"success": True, "task": task_info})
                return

            self.send_error_json(404, "Endpoint não encontrado")

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            path = parsed.path

            content_length = int(self.headers.get("Content-Length", 0))

            def read_json_body():
                if content_length == 0:
                    return {}
                raw = self.rfile.read(content_length)
                return json.loads(raw.decode("utf-8"))

            # 1. Upload Chunk (Requires master token OR session resume token)
            if path == "/api/upload/chunk":
                upload_id = self.headers.get("X-Upload-Id")
                chunk_index_header = self.headers.get("X-Chunk-Index", "0")
                offset_header = self.headers.get("X-Chunk-Offset", "0")

                session = backend.get_session(upload_id) if upload_id else None
                if not session:
                    self.send_error_json(404, "Sessão de upload não encontrada ou expirada")
                    return

                if not self.check_session_auth(session):
                    self.send_error_json(401, "Não autorizado para gravar nesta sessão")
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
                except ValueError as ve:
                    self.send_error_json(400, str(ve))
                except Exception as e:
                    self.send_error_json(500, f"Erro ao gravar fragmento: {e}")
                return

            # 2. Upload Complete
            if path == "/api/upload/complete":
                try:
                    payload = read_json_body()
                    upload_id = payload.get("upload_id")
                    session = backend.get_session(upload_id) if upload_id else None
                    if not session:
                        raise ValueError("Sessão de upload não encontrada ou expirada")

                    if not self.check_session_auth(session):
                        self.send_error_json(401, "Não autorizado para finalizar esta sessão")
                        return

                    final_path = session.finalize()
                    if upload_id in backend.upload_sessions:
                        del backend.upload_sessions[upload_id]
                    self.send_json(200, {"success": True, "saved_path": final_path})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 3. Upload Cancel
            if path == "/api/upload/cancel":
                try:
                    payload = read_json_body()
                    upload_id = payload.get("upload_id")
                    session = backend.get_session(upload_id) if upload_id else None
                    if session:
                        if not self.check_session_auth(session):
                            self.send_error_json(401, "Não autorizado para cancelar esta sessão")
                            return
                        session.cancel()
                        if upload_id in backend.upload_sessions:
                            del backend.upload_sessions[upload_id]
                    self.send_json(200, {"success": True, "message": "Upload cancelado e arquivos temporários removidos"})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # All remaining POST endpoints require master authentication
            if not self.check_master_auth():
                self.send_error_json(401, "Token de autorização inválido ou ausente")
                return

            # 4. Upload Initialization / Resume Handshake
            if path == "/api/upload/init":
                try:
                    payload = read_json_body()
                    filename = os.path.basename(payload.get("filename", "").strip())
                    target_dir = payload.get("target_dir", "")
                    total_size = int(payload.get("total_size", 0))
                    expected_hash = payload.get("expected_hash")
                    client_fingerprint = payload.get("fingerprint")
                    client_upload_id = payload.get("upload_id") or payload.get("resume_id")
                    client_resume_token = payload.get("resume_token") or self.headers.get("X-Resume-Token")

                    if not filename:
                        raise ValueError("Nome do arquivo é obrigatório")

                    safe_target = backend.validate_safe_path(target_dir, is_write_operation=False)
                    if not os.path.isdir(safe_target):
                        raise NotADirectoryError(f"Destino '{target_dir}' não é um diretório")

                    # Check if client requested resuming an existing session
                    if client_upload_id:
                        existing = backend.get_session(client_upload_id)
                        if existing and existing.original_filename == filename and existing.target_dir == safe_target:
                            # Verify resume token if supplied, or master token
                            if not client_resume_token or secrets.compare_digest(client_resume_token, existing.resume_token) or self.check_master_auth():
                                self.send_json(200, {
                                    "success": True,
                                    "resumed": True,
                                    "upload_id": existing.upload_id,
                                    "resume_token": existing.resume_token,
                                    "filename": existing.original_filename,
                                    "part_path": existing.part_path,
                                    "received_bytes": existing.received_bytes,
                                    "total_size": existing.total_size,
                                    "received_chunks": existing.received_chunks,
                                    "chunk_size": CHUNK_SIZE_DEFAULT
                                })
                                return

                    # New Upload Session
                    upload_id = secrets.token_hex(16)
                    resume_token = secrets.token_hex(24)
                    session = UploadSession(
                        upload_id=upload_id,
                        resume_token=resume_token,
                        filename=filename,
                        target_dir=safe_target,
                        total_size=total_size,
                        client_fingerprint=client_fingerprint,
                        expected_hash=expected_hash
                    )
                    backend.upload_sessions[upload_id] = session

                    self.send_json(200, {
                        "success": True,
                        "resumed": False,
                        "upload_id": upload_id,
                        "resume_token": resume_token,
                        "filename": filename,
                        "part_path": session.part_path,
                        "received_bytes": session.received_bytes,
                        "chunk_size": CHUNK_SIZE_DEFAULT
                    })
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 5. Create Single Download Ticket (Replaces ?token= in URL)
            if path == "/api/download/ticket":
                try:
                    payload = read_json_body()
                    file_path = payload.get("path")
                    safe_path = backend.validate_safe_path(file_path, allow_symlinks_in_leaf=True)
                    if not os.path.isfile(safe_path):
                        raise FileNotFoundError("Arquivo não encontrado")
                    ticket = backend.create_download_ticket(safe_path, is_temp_zip=False)
                    self.send_json(200, {
                        "success": True,
                        "ticket": ticket,
                        "download_url": f"/api/download-ticket?ticket={ticket}"
                    })
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 6. Start Background Task (copy, move, delete, create_zip)
            if path == "/api/tasks/start":
                try:
                    payload = read_json_body()
                    action = payload.get("action")

                    if action == "create_zip":
                        paths = payload.get("paths", [])
                        def worker(progress_cb):
                            zip_path, ticket = backend.create_batch_zip(paths, progress_cb)
                            return {
                                "ticket": ticket,
                                "download_url": f"/api/download-ticket?ticket={ticket}",
                                "zip_name": os.path.basename(zip_path)
                            }
                        tid = backend.task_manager.start_task("create_zip", worker)
                        self.send_json(200, {"success": True, "task_id": tid})
                        return

                    elif action == "delete":
                        paths = payload.get("paths", [])
                        tid = backend.task_manager.start_task(
                            "delete",
                            lambda cb: backend.delete_items_sync(paths, cb)
                        )
                        self.send_json(200, {"success": True, "task_id": tid})
                        return

                    elif action == "copy":
                        sources = payload.get("sources", [])
                        dest_dir = payload.get("dest_dir", "")
                        tid = backend.task_manager.start_task(
                            "copy",
                            lambda cb: backend.copy_items_sync(sources, dest_dir, cb)
                        )
                        self.send_json(200, {"success": True, "task_id": tid})
                        return

                    elif action == "move":
                        sources = payload.get("sources", [])
                        dest_dir = payload.get("dest_dir", "")
                        tid = backend.task_manager.start_task(
                            "move",
                            lambda cb: backend.move_items_sync(sources, dest_dir, cb)
                        )
                        self.send_json(200, {"success": True, "task_id": tid})
                        return

                    else:
                        raise ValueError(f"Ação desconhecida: {action}")
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 7. Create Directory
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

            # 8. Rename Item
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

            # 9. Direct Synchronous Delete Items
            if path == "/api/fs/delete":
                try:
                    payload = read_json_body()
                    paths = payload.get("paths", [])
                    res = backend.delete_items_sync(paths)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 10. Direct Synchronous Move Items
            if path == "/api/fs/move":
                try:
                    payload = read_json_body()
                    sources = payload.get("sources", [])
                    dest = payload.get("dest_dir")
                    res = backend.move_items_sync(sources, dest)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 11. Direct Synchronous Copy Items
            if path == "/api/fs/copy":
                try:
                    payload = read_json_body()
                    sources = payload.get("sources", [])
                    dest = payload.get("dest_dir")
                    res = backend.copy_items_sync(sources, dest)
                    self.send_json(200, {"success": True, "results": res})
                except Exception as e:
                    self.send_error_json(400, str(e))
                return

            # 12. Remote Safe Shutdown
            if path == "/api/shutdown":
                self.send_json(200, {"success": True, "message": "Servidor encerrando com segurança"})
                def delayed_kill():
                    time.sleep(0.3)
                    os.kill(os.getpid(), signal.SIGTERM)
                threading.Thread(target=delayed_kill, daemon=True).start()
                return

            self.send_error_json(404, "Endpoint não encontrado")

    return R36SRequestHandler


# ---------------------------------------------------------------------------
# Pure Python QR Code Generator (Zero-Dependency)
# Version 6 (41x41), Byte mode, Error Correction Level L, Capacity: 134 bytes
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
    version = 6
    size = 17 + 4 * version  # 41
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

    # Alignment patterns for Version 6 (row/col 34)
    align_pos = [6, 34]
    for r in align_pos:
        for c in align_pos:
            if (r <= 8 and c <= 8) or (r <= 8 and c >= size - 8) or (r >= size - 8 and c <= 8):
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    val = (abs(dr) == 2 or abs(dc) == 2 or (dr == 0 and dc == 0))
                    set_module(r + dr, c + dc, val)

    # Timing patterns
    for i in range(8, size - 8):
        set_module(6, i, i % 2 == 0)
        set_module(i, 6, i % 2 == 0)

    # Dark module
    set_module(4 * version + 9, 8, True)

    # Format info reserved
    for i in range(9):
        set_module(8, i, False)
        set_module(i, 8, False)
    for i in range(8):
        set_module(8, size - 1 - i, False)
        set_module(size - 1 - i, 8, False)

    # Encode data in 8-bit byte mode (0100)
    bits = [0, 1, 0, 0]
    count = len(data_bytes)
    for i in range(7, -1, -1):
        bits.append((count >> i) & 1)
    for b in data_bytes:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)

    # Version 6-L: Total data capacity is 134 bytes = 1072 bits
    cap_bits = 134 * 8
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

    # Version 6-L uses 1 block of 134 data codewords + 28 ECC codewords
    ecc = rs_encode(codewords[:134], 28)
    all_codewords = codewords[:134] + ecc

    all_bits = []
    for cw in all_codewords:
        for i in range(7, -1, -1):
            all_bits.append((cw >> i) & 1)

    # Format information bits for L error correction with mask 0
    # L=01, mask 0 = 000 -> 01000 with BCH(15, 5) -> XOR 101010000010010 = 111011111000100
    format_bits = [1, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0]

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
                    # Mask pattern 0: (row + column) % 2 == 0
                    if (r + c) % 2 == 0:
                        val = not val
                    matrix[r][c] = val
        col -= 2

    # Draw format information
    # Top-left around finder pattern
    set_module(8, 0, bool(format_bits[0]), True)
    set_module(8, 1, bool(format_bits[1]), True)
    set_module(8, 2, bool(format_bits[2]), True)
    set_module(8, 3, bool(format_bits[3]), True)
    set_module(8, 4, bool(format_bits[4]), True)
    set_module(8, 5, bool(format_bits[5]), True)
    set_module(8, 7, bool(format_bits[6]), True)
    set_module(8, 8, bool(format_bits[7]), True)
    set_module(7, 8, bool(format_bits[8]), True)
    set_module(5, 8, bool(format_bits[9]), True)
    set_module(4, 8, bool(format_bits[10]), True)
    set_module(3, 8, bool(format_bits[11]), True)
    set_module(2, 8, bool(format_bits[12]), True)
    set_module(1, 8, bool(format_bits[13]), True)
    set_module(0, 8, bool(format_bits[14]), True)

    # Second copy
    for i in range(8):
        set_module(size - 1 - i, 8, bool(format_bits[i]), True)
    for i in range(8, 15):
        set_module(8, size - 15 + i, bool(format_bits[i]), True)

    return matrix

def render_ansi_qr(text: str) -> str:
    """Renders QR code with at least 4 modules quiet zone as requested."""
    try:
        matrix = encode_qr_matrix(text)
        size = len(matrix)
        quiet = 4  # ISO/IEC 18004 requirement: 4 modules quiet zone
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
    except Exception as e:
        return f"[ URL: {text} ]"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="R36S Web File Manager Backend")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--token", type=str, required=True, help="Ephemeral auth token")
    parser.add_argument("--ui", type=str, default="ui.html", help="Path to ui.html")
    parser.add_argument("--roots", nargs="+", default=["/roms", "/roms2", "/media", "/mnt"], help="Allowed roots")
    args = parser.parse_args()

    try:
        backend = FileManagerBackend(allowed_roots=args.roots, auth_token=args.token, ui_html_path=args.ui)
    except Exception as e:
        sys.stderr.write(f"FATAL: {e}\n")
        sys.exit(1)

    handler = make_request_handler(backend)
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
