"""
Automated Test Suite for R36S Web File Manager Backend
Audits API endpoints, security sandbox, path traversal, chunk upload, and shutdown.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
import subprocess

def run_audit():
    print("=== INICIANDO FASE 5: AUDITORIA AUTOMÁTICA DO CÓDIGO ===")

    test_port = 8999
    test_token = "audit_token_test_12345"
    test_dir = os.path.realpath("r36s_test_sandbox")
    os.makedirs(test_dir, exist_ok=True)

    # 1. Start test server
    server_cmd = [
        sys.executable,
        "r36s/server.py",
        "--port", str(test_port),
        "--token", test_token,
        "--ui", "r36s/ui.html",
        "--roots", test_dir
    ]
    proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(1)

    base_url = f"http://127.0.0.1:{test_port}"
    passed = 0
    failed = 0

    def assert_test(name, condition, details=""):
        nonlocal passed, failed
        if condition:
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: {details}")
            failed += 1

    try:
        # Test 1: Unauthorized access without token
        try:
            req = urllib.request.Request(f"{base_url}/api/status")
            urllib.request.urlopen(req)
            assert_test("Segurança: Rejeição sem token (401)", False, "Deveria falhar com 401")
        except urllib.error.HTTPError as e:
            assert_test("Segurança: Rejeição sem token (401)", e.code == 401, f"Código {e.code}")

        # Test 2: Authorized status query
        req = urllib.request.Request(f"{base_url}/api/status")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert_test("API: Status do sistema autenticado", data.get("success") is True and "version" in data)

        # Test 3: Storage roots detection
        req = urllib.request.Request(f"{base_url}/api/storage")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert_test("API: Detecção dinâmica de raízes de armazenamento", len(data.get("roots", [])) > 0)

        # Test 4: Path Traversal Protection (Attempting to escape to /etc)
        traversal_urls = [
            f"{base_url}/api/fs/list?path=/etc",
            f"{base_url}/api/fs/list?path=../../../../etc",
            f"{base_url}/api/fs/list?path={test_dir}/../../../../etc/passwd"
        ]
        all_blocked = True
        for u in traversal_urls:
            try:
                req = urllib.request.Request(u)
                req.add_header("X-Auth-Token", test_token)
                urllib.request.urlopen(req)
                all_blocked = False
            except urllib.error.HTTPError as e:
                if e.code not in (400, 403):
                    all_blocked = False
        assert_test("Segurança: Bloqueio estrito de Path Traversal (Anti-Escape)", all_blocked)

        # Test 5: Safe Directory Creation inside sandbox
        req = urllib.request.Request(f"{base_url}/api/fs/mkdir", method="POST")
        req.add_header("X-Auth-Token", test_token)
        req.add_header("Content-Type", "application/json")
        body = json.dumps({"parent_path": test_dir, "name": "test_folder"}).encode()
        with urllib.request.urlopen(req, data=body) as resp:
            data = json.loads(resp.read().decode())
            created = data.get("created")
            assert_test("Filesystem: Criação de pasta real no disco", created and os.path.isdir(created))

        # Test 6: Chunked Upload Protocol with Handshake & Atomic Rename
        test_file_content = b"TEST_R36S_ROM_DATA_" * 1000  # 19 KB
        init_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
        init_req.add_header("X-Auth-Token", test_token)
        init_req.add_header("Content-Type", "application/json")
        init_body = json.dumps({
            "filename": "test_game.bin",
            "target_dir": test_dir,
            "total_size": len(test_file_content)
        }).encode()
        with urllib.request.urlopen(init_req, data=init_body) as resp:
            init_res = json.loads(resp.read().decode())
            upload_id = init_res.get("upload_id")
            assert_test("Upload Handshake: Geração de sessão segura pelo servidor", bool(upload_id))

        # Send chunk
        chunk_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        chunk_req.add_header("X-Auth-Token", test_token)
        chunk_req.add_header("X-Upload-Id", upload_id)
        chunk_req.add_header("X-Chunk-Index", "0")
        chunk_req.add_header("X-Chunk-Offset", "0")
        chunk_req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(chunk_req, data=test_file_content) as resp:
            chunk_res = json.loads(resp.read().decode())
            assert_test("Upload Chunk: Gravação de chunk binário em arquivo temporário", chunk_res.get("success") is True)

        # Complete upload
        comp_req = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
        comp_req.add_header("X-Auth-Token", test_token)
        comp_req.add_header("Content-Type", "application/json")
        comp_body = json.dumps({"upload_id": upload_id}).encode()
        with urllib.request.urlopen(comp_req, data=comp_body) as resp:
            comp_res = json.loads(resp.read().decode())
            saved_path = comp_res.get("saved_path")
            assert_test("Upload Finalize: os.rename() atômico no mesmo filesystem", os.path.isfile(saved_path) and os.path.getsize(saved_path) == len(test_file_content))

        # Test 7: Download with HTTP Range support
        down_req = urllib.request.Request(f"{base_url}/api/download?path={saved_path}")
        down_req.add_header("X-Auth-Token", test_token)
        down_req.add_header("Range", "bytes=0-99")
        with urllib.request.urlopen(down_req) as resp:
            assert_test("Download HTTP Range: Suporte a 206 Partial Content (Safari iOS)", resp.status == 206 and len(resp.read()) == 100)

        # Test 8: Remote Safe Shutdown
        shut_req = urllib.request.Request(f"{base_url}/api/shutdown", method="POST")
        shut_req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(shut_req) as resp:
            shut_res = json.loads(resp.read().decode())
            assert_test("Encerramento: API de shutdown remoto seguro", shut_res.get("success") is True)

    finally:
        # Terminate test server process
        proc.terminate()
        proc.wait(timeout=3)
        # Clean up test sandbox
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    print(f"\nResultado da Auditoria: {passed} testes passaram, {failed} falharam.")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
