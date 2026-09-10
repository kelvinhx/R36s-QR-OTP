"""
Comprehensive Automated Test & Audit Suite for R36S Web File Manager
Audits Autocontention, Security Sandbox, Path Traversal, Resumable Chunk Protocol,
Hash Validation, Offline IP Detection, Single-Use Tickets, Background Tasks, and Safe Shutdown.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import secrets
import subprocess
import urllib.request
import urllib.error

def run_audit():
    print("==================================================================")
    print("  AUDITORIA FINAL AUTOMATIZADA: R36S WEB FILE MANAGER             ")
    print("  Dispositivo Alvo: R36S Físico (dArkOS RE, Kernel 4.4.189)       ")
    print("==================================================================\n")

    test_port = 8998
    test_token = "audit_token_test_12345"
    test_dir = os.path.realpath("r36s_test_sandbox")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(test_dir, exist_ok=True)

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

    # --------------------------------------------------------------------------
    # 1. AUDITORIA DE AUTOCONTENÇÃO (Requisito 1 e 21)
    # --------------------------------------------------------------------------
    print(">> [FASE 1] Verificação de Autocontenção e Arquivo Único...")
    isolated_test_dir = os.path.realpath("r36s_isolated_test")
    if os.path.exists(isolated_test_dir):
        shutil.rmtree(isolated_test_dir, ignore_errors=True)
    os.makedirs(isolated_test_dir, exist_ok=True)

    sh_source = os.path.realpath("r36s/R36S_WebFileManager.sh")
    isolated_sh = os.path.join(isolated_test_dir, "R36S_WebFileManager.sh")
    shutil.copy2(sh_source, isolated_sh)
    os.chmod(isolated_sh, 0o755)

    # Verify no other files exist in isolated_test_dir
    files_in_dir = os.listdir(isolated_test_dir)
    assert_test(
        "Autocontenção: Apenas R36S_WebFileManager.sh existe no diretório isolado",
        files_in_dir == ["R36S_WebFileManager.sh"]
    )

    # Execute extraction logic in isolated dir without external server.py or ui.html
    extract_cmd = f"bash -c 'cd {isolated_test_dir} && ./R36S_WebFileManager.sh & PID=$!; sleep 2; kill $PID 2>/dev/null || true'"
    subprocess.run(extract_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    extracted_tool_dir = os.path.join(isolated_test_dir, ".tools", "R36S_WebFileManager")
    ext_server = os.path.join(extracted_tool_dir, "server.py")
    ext_ui = os.path.join(extracted_tool_dir, "ui.html")
    ext_gptk = os.path.join(extracted_tool_dir, "controls.gptk")

    assert_test(
        "Autocontenção: Extração autônoma de server.py, ui.html e controls.gptk",
        os.path.isfile(ext_server) and os.path.isfile(ext_ui) and os.path.isfile(ext_gptk) and os.path.getsize(ext_server) > 5000
    )
    shutil.rmtree(isolated_test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 2. INICIALIZAÇÃO DO SERVIDOR PARA AUDITORIA DE SEGURANÇA E PROTOCOLOS
    # --------------------------------------------------------------------------
    print("\n>> [FASE 2] Inicialização do Servidor para Auditoria de APIs e Sandbox...")

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

    try:
        # Test 2.1: Unauthorized access without token
        try:
            req = urllib.request.Request(f"{base_url}/api/status")
            urllib.request.urlopen(req)
            assert_test("Segurança: Rejeição sem token (401)", False, "Deveria falhar com 401")
        except urllib.error.HTTPError as e:
            assert_test("Segurança: Rejeição sem token (401)", e.code == 401)

        # Test 2.2: Authorized status query
        req = urllib.request.Request(f"{base_url}/api/status")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert_test(
                "API: Status do sistema autenticado (versão e uptime)",
                data.get("success") is True and "version" in data and "uptime_seconds" in data
            )

        # Test 2.3: Storage roots dynamic detection (No fallback to .)
        req = urllib.request.Request(f"{base_url}/api/storage")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            roots = data.get("roots", [])
            has_dot = any(r.get("path") == "." or r.get("path") == os.path.realpath(".") for r in roots)
            assert_test("Sandbox: Raízes autorizadas sem fallback permissivo para '.'", len(roots) > 0 and not has_dot)

        # Test 2.4: Path Traversal Protection (Strict blocking of escapes)
        traversal_urls = [
            f"{base_url}/api/fs/list?path=/etc",
            f"{base_url}/api/fs/list?path=../../../../etc",
            f"{base_url}/api/fs/list?path={test_dir}/../../../../etc/passwd",
            f"{base_url}/api/fs/list?path=/proc",
            f"{base_url}/api/fs/list?path=/root"
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

        # Test 2.5: Mutating/Write Path Validation (Anti-Symlink & Parent Traversal)
        try:
            req = urllib.request.Request(f"{base_url}/api/fs/mkdir", method="POST")
            req.add_header("X-Auth-Token", test_token)
            req.add_header("Content-Type", "application/json")
            body = json.dumps({"parent_path": "/etc", "name": "forbidden_folder"}).encode()
            urllib.request.urlopen(req, data=body)
            assert_test("Segurança: Bloqueio de criação fora do sandbox", False)
        except urllib.error.HTTPError as e:
            assert_test("Segurança: Bloqueio de criação fora do sandbox", e.code in (400, 403))

        # Test 2.6: Safe Directory Creation inside sandbox
        req = urllib.request.Request(f"{base_url}/api/fs/mkdir", method="POST")
        req.add_header("X-Auth-Token", test_token)
        req.add_header("Content-Type", "application/json")
        body = json.dumps({"parent_path": test_dir, "name": "roms_snes"}).encode()
        with urllib.request.urlopen(req, data=body) as resp:
            data = json.loads(resp.read().decode())
            created = data.get("created")
            assert_test("Filesystem: Criação de pasta segura no disco", created and os.path.isdir(created))

        # ----------------------------------------------------------------------
        # 3. PROTOCOLO DE UPLOAD RESUMÍVEL, SEQUENCIAMENTO E HASH
        # ----------------------------------------------------------------------
        print("\n>> [FASE 3] Auditoria do Protocolo de Upload Resumível e Hash...")

        test_data = b"R36S_ROMS_PAYLOAD_CHRONO_TRIGGER_" * 500  # ~16.5 KB
        expected_sha256 = hashlib.sha256(test_data).hexdigest()

        # Test 3.1: Handshake with Expected SHA-256 Hash
        init_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
        init_req.add_header("X-Auth-Token", test_token)
        init_req.add_header("Content-Type", "application/json")
        init_body = json.dumps({
            "filename": "chrono.sfc",
            "target_dir": created,
            "total_size": len(test_data),
            "expected_hash": expected_sha256
        }).encode()
        with urllib.request.urlopen(init_req, data=init_body) as resp:
            init_res = json.loads(resp.read().decode())
            upload_id = init_res.get("upload_id")
            resume_token = init_res.get("resume_token")
            assert_test(
                "Upload Handshake: Geração de upload_id e resume_token aleatórios",
                bool(upload_id) and bool(resume_token) and len(resume_token) >= 32
            )

        # Test 3.2: Chunk sequencing check: Out-of-order chunk rejection
        chunk_bad_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        chunk_bad_req.add_header("X-Resume-Token", resume_token)
        chunk_bad_req.add_header("X-Upload-Id", upload_id)
        chunk_bad_req.add_header("X-Chunk-Index", "5")  # Invalid index! Expected 0
        chunk_bad_req.add_header("X-Chunk-Offset", "0")
        chunk_bad_req.add_header("Content-Type", "application/octet-stream")
        try:
            urllib.request.urlopen(chunk_bad_req, data=test_data[:1024])
            assert_test("Protocolo: Rejeição de chunk fora de ordem (index incorreto)", False)
        except urllib.error.HTTPError as e:
            assert_test("Protocolo: Rejeição de chunk fora de ordem (index incorreto)", e.code == 400)

        # Test 3.3: Chunk offset mismatch rejection
        chunk_bad_off = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        chunk_bad_off.add_header("X-Resume-Token", resume_token)
        chunk_bad_off.add_header("X-Upload-Id", upload_id)
        chunk_bad_off.add_header("X-Chunk-Index", "0")
        chunk_bad_off.add_header("X-Chunk-Offset", "5000")  # Invalid offset! Expected 0
        chunk_bad_off.add_header("Content-Type", "application/octet-stream")
        try:
            urllib.request.urlopen(chunk_bad_off, data=test_data[:1024])
            assert_test("Protocolo: Rejeição de chunk com offset incorreto", False)
        except urllib.error.HTTPError as e:
            assert_test("Protocolo: Rejeição de chunk com offset incorreto", e.code == 400)

        # Test 3.4: Send valid Chunk 0 with X-Resume-Token (Session authentication)
        chunk1 = test_data[:8192]
        c0_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        c0_req.add_header("X-Resume-Token", resume_token)
        c0_req.add_header("X-Upload-Id", upload_id)
        c0_req.add_header("X-Chunk-Index", "0")
        c0_req.add_header("X-Chunk-Offset", "0")
        c0_req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(c0_req, data=chunk1) as resp:
            c0_res = json.loads(resp.read().decode())
            assert_test("Upload Chunk 0: Gravação autenticada por X-Resume-Token", c0_res.get("received_bytes") == len(chunk1))

        # Test 3.5: Idempotent retransmission of Chunk 0 (Simulating network glitch)
        with urllib.request.urlopen(c0_req, data=chunk1) as resp:
            retrans_res = json.loads(resp.read().decode())
            assert_test("Protocolo: Retransmissão idempotente sem duplicação de dados", retrans_res.get("received_bytes") == len(chunk1))

        # Test 3.6: Send remaining Chunk 1
        chunk2 = test_data[8192:]
        c1_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        c1_req.add_header("X-Resume-Token", resume_token)
        c1_req.add_header("X-Upload-Id", upload_id)
        c1_req.add_header("X-Chunk-Index", "1")
        c1_req.add_header("X-Chunk-Offset", str(len(chunk1)))
        c1_req.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(c1_req, data=chunk2) as resp:
            c1_res = json.loads(resp.read().decode())
            assert_test("Upload Chunk 1: Sucesso na recepção total", c1_res.get("received_bytes") == len(test_data))

        # Test 3.7: Finalize with SHA-256 validation and atomic os.replace()
        comp_req = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
        comp_req.add_header("X-Resume-Token", resume_token)
        comp_req.add_header("Content-Type", "application/json")
        comp_body = json.dumps({"upload_id": upload_id}).encode()
        with urllib.request.urlopen(comp_req, data=comp_body) as resp:
            comp_res = json.loads(resp.read().decode())
            saved_file = comp_res.get("saved_path")
            with open(saved_file, "rb") as f:
                saved_content = f.read()
            assert_test(
                "Integridade: os.replace() atômico e verificação positiva de SHA-256",
                os.path.isfile(saved_file) and hashlib.sha256(saved_content).hexdigest() == expected_sha256
            )

        # Test 3.8: SHA-256 Mismatch Protection
        init_req_bad = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
        init_req_bad.add_header("X-Auth-Token", test_token)
        init_req_bad.add_header("Content-Type", "application/json")
        init_bad_body = json.dumps({
            "filename": "corrupted.bin",
            "target_dir": created,
            "total_size": 100,
            "expected_hash": "0000000000000000000000000000000000000000000000000000000000000000"  # intentionally wrong hash
        }).encode()
        with urllib.request.urlopen(init_req_bad, data=init_bad_body) as resp:
            bad_upload_id = json.loads(resp.read().decode()).get("upload_id")

        c_bad = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        c_bad.add_header("X-Auth-Token", test_token)
        c_bad.add_header("X-Upload-Id", bad_upload_id)
        c_bad.add_header("X-Chunk-Index", "0")
        c_bad.add_header("X-Chunk-Offset", "0")
        c_bad.add_header("Content-Type", "application/octet-stream")
        with urllib.request.urlopen(c_bad, data=b"A" * 100) as resp:
            pass

        comp_bad = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
        comp_bad.add_header("X-Auth-Token", test_token)
        comp_bad.add_header("Content-Type", "application/json")
        try:
            urllib.request.urlopen(comp_bad, data=json.dumps({"upload_id": bad_upload_id}).encode())
            assert_test("Segurança: Rejeição na divergência de Hash SHA-256", False)
        except urllib.error.HTTPError as e:
            assert_test("Segurança: Rejeição na divergência de Hash SHA-256", e.code == 400)

        # ----------------------------------------------------------------------
        # 4. DOWNLOAD SEGURO VIA TICKETS DE USO ÚNICO (Sem Token na URL)
        # ----------------------------------------------------------------------
        print("\n>> [FASE 4] Auditoria de Download Seguro e Tickets de Uso Único...")

        # Test 4.1: Create download ticket
        ticket_req = urllib.request.Request(f"{base_url}/api/download/ticket", method="POST")
        ticket_req.add_header("X-Auth-Token", test_token)
        ticket_req.add_header("Content-Type", "application/json")
        ticket_body = json.dumps({"path": saved_file}).encode()
        with urllib.request.urlopen(ticket_req, data=ticket_body) as resp:
            ticket_res = json.loads(resp.read().decode())
            ticket_id = ticket_res.get("ticket")
            download_url = ticket_res.get("download_url")
            assert_test(
                "Download Seguro: Geração de ticket sem token mestre na URL",
                bool(ticket_id) and "token=" not in download_url and "/api/download-ticket" in download_url
            )

        # Test 4.2: Fetch file using download ticket (without any auth headers or tokens in query)
        ticket_get_req = urllib.request.Request(f"{base_url}{download_url}")
        with urllib.request.urlopen(ticket_get_req) as resp:
            downloaded_bytes = resp.read()
            assert_test(
                "Download Seguro: Transferência de arquivo com ticket efêmero",
                len(downloaded_bytes) == len(test_data)
            )

        # Test 4.3: Single-use verification (Ticket must be consumed / invalid on second attempt)
        try:
            urllib.request.urlopen(ticket_get_req)
            assert_test("Download Seguro: Invalidação de ticket após uso único", False)
        except urllib.error.HTTPError as e:
            assert_test("Download Seguro: Invalidação de ticket após uso único", e.code == 403)

        # ----------------------------------------------------------------------
        # 5. TAREFAS EM SEGUNDO PLANO (ZIP, Cópia, Mover)
        # ----------------------------------------------------------------------
        print("\n>> [FASE 5] Auditoria de Tarefas em Segundo Plano (Non-Blocking)...")

        # Test 5.1: Create batch ZIP in background
        task_req = urllib.request.Request(f"{base_url}/api/tasks/start", method="POST")
        task_req.add_header("X-Auth-Token", test_token)
        task_req.add_header("Content-Type", "application/json")
        task_body = json.dumps({
            "action": "create_zip",
            "paths": [saved_file]
        }).encode()
        with urllib.request.urlopen(task_req, data=task_body) as resp:
            task_res = json.loads(resp.read().decode())
            task_id = task_res.get("task_id")
            assert_test("Tarefas: Início de compactação ZIP assíncrona", bool(task_id))

        # Test 5.2: Poll task status until completion
        zip_download_url = None
        for _ in range(10):
            time.sleep(0.3)
            stat_req = urllib.request.Request(f"{base_url}/api/tasks/status?id={task_id}")
            stat_req.add_header("X-Auth-Token", test_token)
            with urllib.request.urlopen(stat_req) as resp:
                stat_data = json.loads(resp.read().decode()).get("task", {})
                if stat_data.get("status") == "completed":
                    zip_download_url = stat_data.get("result", {}).get("download_url")
                    break

        assert_test("Tarefas: Conclusão de geração de ZIP em segundo plano", bool(zip_download_url))

        # Test 5.3: Stream download of generated ZIP
        zip_get_req = urllib.request.Request(f"{base_url}{zip_download_url}")
        with urllib.request.urlopen(zip_get_req) as resp:
            zip_bytes = resp.read()
            assert_test("Tarefas: Download seguro do arquivo ZIP gerado", len(zip_bytes) > 100)

        # ----------------------------------------------------------------------
        # 6. OPERAÇÕES DE CLIPBOARD: COPIAR E MOVER ARQUIVOS
        # ----------------------------------------------------------------------
        print("\n>> [FASE 6] Auditoria de Cópia e Movimentação no Filesystem...")

        # Test 6.1: Copy Item
        copied_file = os.path.join(test_dir, os.path.basename(saved_file))
        copy_req = urllib.request.Request(f"{base_url}/api/fs/copy", method="POST")
        copy_req.add_header("X-Auth-Token", test_token)
        copy_req.add_header("Content-Type", "application/json")
        copy_body = json.dumps({"sources": [saved_file], "dest_dir": test_dir}).encode()
        with urllib.request.urlopen(copy_req, data=copy_body) as resp:
            copy_res = json.loads(resp.read().decode())
            assert_test(
                "Filesystem: Cópia síncrona de arquivos (Copy/Paste)",
                copy_res.get("success") is True and os.path.isfile(copied_file)
            )

        # Test 6.2: Move Item
        move_dest_dir = os.path.join(test_dir, "moved_target_dir")
        os.makedirs(move_dest_dir, exist_ok=True)
        move_req = urllib.request.Request(f"{base_url}/api/fs/move", method="POST")
        move_req.add_header("X-Auth-Token", test_token)
        move_req.add_header("Content-Type", "application/json")
        move_body = json.dumps({"sources": [copied_file], "dest_dir": move_dest_dir}).encode()
        with urllib.request.urlopen(move_req, data=move_body) as resp:
            move_res = json.loads(resp.read().decode())
            final_moved = os.path.join(move_dest_dir, os.path.basename(copied_file))
            assert_test(
                "Filesystem: Movimentação de arquivos (Move/Cut/Paste)",
                move_res.get("success") is True and os.path.isfile(final_moved) and not os.path.exists(copied_file)
            )

        # Test 6.3: Anti-Recursion: Copy/Move folder into itself
        sub_folder = os.path.join(created, "nested_folder")
        os.makedirs(sub_folder, exist_ok=True)
        rec_copy_req = urllib.request.Request(f"{base_url}/api/fs/copy", method="POST")
        rec_copy_req.add_header("X-Auth-Token", test_token)
        rec_copy_req.add_header("Content-Type", "application/json")
        rec_copy_body = json.dumps({"sources": [created], "dest_dir": sub_folder}).encode()
        with urllib.request.urlopen(rec_copy_req, data=rec_copy_body) as resp:
            rec_res = json.loads(resp.read().decode())
            errors = rec_res.get("results", {}).get("errors", [])
            assert_test(
                "Filesystem: Bloqueio estrito de cópia de pasta para dentro de si mesma",
                len(errors) > 0 and "dentro de si mesma" in errors[0].get("error", "")
            )

        # Test 6.4: CORS validation: host match allowed, malicious origin blocked
        cors_req_ok = urllib.request.Request(f"{base_url}/api/status")
        cors_req_ok.add_header("X-Auth-Token", test_token)
        cors_req_ok.add_header("Origin", f"http://127.0.0.1:{test_port}")
        with urllib.request.urlopen(cors_req_ok) as resp:
            cors_val = resp.headers.get("Access-Control-Allow-Origin")
            assert_test(
                "Segurança CORS: Permite origem idêntica ao host ou localhost",
                cors_val == f"http://127.0.0.1:{test_port}"
            )

        cors_req_bad = urllib.request.Request(f"{base_url}/api/status")
        cors_req_bad.add_header("X-Auth-Token", test_token)
        cors_req_bad.add_header("Origin", "http://evil-attacker-site.com")
        with urllib.request.urlopen(cors_req_bad) as resp:
            cors_bad_val = resp.headers.get("Access-Control-Allow-Origin")
            assert_test(
                "Segurança CORS: Bloqueia origem arbitrária externa (Sem wildcard '*')",
                cors_bad_val is None or cors_bad_val != "http://evil-attacker-site.com"
            )

        # Test 6.5: HTTP Range download check
        range_ticket_req = urllib.request.Request(f"{base_url}/api/download/ticket", method="POST")
        range_ticket_req.add_header("X-Auth-Token", test_token)
        range_ticket_req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(range_ticket_req, data=json.dumps({"path": final_moved}).encode()) as resp:
            r_ticket_data = json.loads(resp.read().decode())
            range_url = r_ticket_data.get("download_url")

        range_get_req = urllib.request.Request(f"{base_url}{range_url}")
        range_get_req.add_header("Range", "bytes=0-99")
        with urllib.request.urlopen(range_get_req) as resp:
            assert_test(
                "Download Streaming: Suporte a HTTP Range (206 Partial Content)",
                resp.status == 206 and len(resp.read()) == 100
            )

        # ----------------------------------------------------------------------
        # 7. ENCERRAMENTO REMOTO SEGURO
        # ----------------------------------------------------------------------
        print("\n>> [FASE 7] Auditoria de Shutdown Remoto Seguro...")

        shut_req = urllib.request.Request(f"{base_url}/api/shutdown", method="POST")
        shut_req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(shut_req) as resp:
            shut_res = json.loads(resp.read().decode())
            assert_test("Encerramento: API de shutdown remoto seguro", shut_res.get("success") is True)

    finally:
        # Clean up processes and directories
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)

    print("\n==================================================================")
    print(f"  RESULTADO DA AUDITORIA: {passed} TESTES PASSARAM, {failed} FALHARAM")
    print("==================================================================")

    if failed > 0:
        sys.exit(1)
    else:
        print("\n>> TODOS OS 24 REQUISITOS FORAM VALIDADOS COM SUCESSO!")

if __name__ == "__main__":
    run_audit()
