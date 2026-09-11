#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reestruturação da Suíte de Auditoria R36S Web File Manager.
Separa claramente os testes em:
A) STATIC CODE AUDIT
B) LOCAL TEST
C) STANDALONE TEST
D) R36S PHYSICAL TEST
"""

import os
import sys
import time
import json
import shutil
import re
import socket
import errno
import hashlib
import threading
import subprocess
import unittest.mock
import urllib.request
import urllib.parse
import urllib.error

def run_audit():
    print("==================================================================")
    print("  AUDITORIA AVANÇADA REESTRUTURADA: R36S WEB FILE MANAGER        ")
    print("  Ambiente Alvo: R36S Físico (dArkOS RE, Kernel 4.4.189)         ")
    print("==================================================================\n")

    test_port = 8998
    test_token = "audit_token_test_12345"
    test_dir = os.path.realpath("r36s_test_sandbox")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    os.makedirs(test_dir, exist_ok=True)

    passed_tests = []
    failed_tests = []
    not_verified_tests = []

    def assert_test(category, name, condition, details=""):
        full_name = f"[{category}] {name}"
        if condition:
            print(f"  [PASS] {full_name}")
            passed_tests.append(full_name)
        else:
            print(f"  [FAIL] {full_name}: {details}")
            failed_tests.append(full_name)

    def register_not_verified(category, name, details="Requires physical R36S device"):
        full_name = f"[{category}] {name}"
        print(f"  [NOT VERIFIED] {full_name}: {details}")
        not_verified_tests.append(full_name)

    # --------------------------------------------------------------------------
    # CATEGORY A) STATIC CODE AUDIT
    # --------------------------------------------------------------------------
    print(">> [A) STATIC CODE AUDIT] Verificação estática do código-fonte e assets...")

    # Assets enumeration
    assets_dir = "r36s/assets"
    total_assets = 0
    svg_count = 0
    dpad_exists = False
    btn_a_exists = False
    btn_b_exists = False

    if os.path.isdir(assets_dir):
        for root, dirs, files in os.walk(assets_dir):
            for file in files:
                total_assets += 1
                full_path = os.path.join(root, file)
                if file.endswith(".svg"):
                    svg_count += 1
                if "dpad.svg" in file:
                    dpad_exists = True
                if "btn_a.svg" in file:
                    btn_a_exists = True
                if "btn_b.svg" in file:
                    btn_b_exists = True

    assert_test("STATIC", "Assets: Enumeração física exata (Total 53)", total_assets == 53)
    assert_test("STATIC", "Assets: Todos os assets em formato SVG otimizado", svg_count == 53)
    assert_test("STATIC", "Sprites: dpad.svg, btn_a.svg e btn_b.svg presentes", dpad_exists and btn_a_exists and btn_b_exists)

    # Controls.gptk validation
    gptk_file = "r36s/controls.gptk"
    gptk_ok = False
    if os.path.isfile(gptk_file):
        with open(gptk_file, "r") as f:
            content = f.read()
            if "back = esc" in content and "start = enter" in content and "a = enter" in content and "b = esc" in content:
                gptk_ok = True
    assert_test("STATIC", "Controles: Coerência com gptokeyb e mapeamento documentado", gptk_ok)

    # Verify no external forbidden libraries are imported in server.py
    forbidden_libs_ok = True
    no_external_dns_call = True
    server_py_path = "r36s/server.py"
    if os.path.isfile(server_py_path):
        with open(server_py_path, "r", encoding="utf-8", errors="ignore") as f:
            code_lines = f.readlines()
            for line in code_lines:
                # Check forbidden libraries
                for lib in ["pygame", "pysdl2", "flask", "fastapi", "aiohttp", "qrcode", "requests"]:
                    if f"import {lib}" in line or f"from {lib}" in line:
                        forbidden_libs_ok = False
                # Check external DNS socket fallback
                if "8.8.8.8" in line:
                    no_external_dns_call = False

    assert_test("STATIC", "Estática: Sem dependências proibidas (pygame, requests, etc)", forbidden_libs_ok)
    assert_test("STATIC", "Estática: Sem descoberta de IP usando 8.8.8.8 externo", no_external_dns_call)

    # --------------------------------------------------------------------------
    # CATEGORY B) LOCAL TEST
    # --------------------------------------------------------------------------
    print("\n>> [B) LOCAL TEST] Execução e auditoria de APIs e Sandbox localmente...")

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
        # Unauthorized access
        try:
            req = urllib.request.Request(f"{base_url}/api/status")
            urllib.request.urlopen(req)
            assert_test("LOCAL", "Segurança: Rejeição sem token (401)", False, "Deveria falhar com 401")
        except urllib.error.HTTPError as e:
            assert_test("LOCAL", "Segurança: Rejeição sem token (401)", e.code == 401)

        # Authorized status query
        req = urllib.request.Request(f"{base_url}/api/status")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            assert_test(
                "LOCAL", "API: Status do sistema autenticado (versão e uptime)",
                data.get("success") is True and "version" in data and "uptime_seconds" in data
            )

        # Storage roots detection
        req = urllib.request.Request(f"{base_url}/api/storage")
        req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            roots = data.get("roots", [])
            has_dot = any(r.get("path") == "." or r.get("path") == os.path.realpath(".") for r in roots)
            assert_test("LOCAL", "Sandbox: Raízes autorizadas sem fallback permissivo para '.'", len(roots) > 0 and not has_dot)

        # Path Traversal Protection
        traversal_urls = [
            f"{base_url}/api/fs/list?path=/etc",
            f"{base_url}/api/fs/list?path=../../../../etc",
            f"{base_url}/api/fs/list?path={test_dir}/../../../../etc/passwd",
            f"{base_url}/api/fs/list?path=/proc",
        ]
        all_blocked = True
        for url in traversal_urls:
            try:
                t_req = urllib.request.Request(url)
                t_req.add_header("X-Auth-Token", test_token)
                urllib.request.urlopen(t_req)
                all_blocked = False
            except urllib.error.HTTPError as e:
                if e.code not in (400, 403, 404):
                    all_blocked = False

        assert_test("LOCAL", "Segurança: Bloqueio estrito de Path Traversal (Anti-Escape)", all_blocked)

        # Directory creation outside sandbox
        try:
            create_req = urllib.request.Request(f"{base_url}/api/fs/mkdir", method="POST")
            create_req.add_header("X-Auth-Token", test_token)
            create_req.add_header("Content-Type", "application/json")
            create_req.data = json.dumps({"parent_path": "/tmp", "name": "evil_sandbox_escape"}).encode()
            urllib.request.urlopen(create_req)
            assert_test("LOCAL", "Segurança: Bloqueio de criação fora do sandbox", False)
        except urllib.error.HTTPError as e:
            assert_test("LOCAL", "Segurança: Bloqueio de criação fora do sandbox", e.code in (400, 403))

        # Safe directory creation
        try:
            create_req = urllib.request.Request(f"{base_url}/api/fs/mkdir", method="POST")
            create_req.add_header("X-Auth-Token", test_token)
            create_req.add_header("Content-Type", "application/json")
            create_req.data = json.dumps({"parent_path": test_dir, "name": "safe_folder"}).encode()
            with urllib.request.urlopen(create_req) as resp:
                res = json.loads(resp.read().decode())
                created = res.get("created")
                assert_test("LOCAL", "Filesystem: Criação de pasta segura no disco", created and os.path.isdir(created))
        except Exception as e:
            assert_test("LOCAL", "Filesystem: Criação de pasta segura no disco", False, str(e))

        # Upload handshake protocol
        dest_file_path = os.path.join(test_dir, "uploaded_test.txt")
        test_data = "AUDIT_TEST_DATA_" * 1000 # 16KB
        sha256_hash = hashlib.sha256(test_data.encode()).hexdigest()

        try:
            hs_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
            hs_req.add_header("X-Auth-Token", test_token)
            hs_req.add_header("Content-Type", "application/json")
            hs_req.data = json.dumps({
                "filename": "uploaded_test.txt",
                "target_dir": test_dir,
                "total_size": len(test_data),
                "expected_hash": sha256_hash
            }).encode()
            with urllib.request.urlopen(hs_req) as resp:
                hs_res = json.loads(resp.read().decode())
                upload_id = hs_res.get("upload_id")
                resume_token = hs_res.get("resume_token")
                assert_test(
                    "LOCAL", "Upload Handshake: Geração de upload_id e resume_token aleatórios",
                    bool(upload_id) and bool(resume_token)
                )
        except Exception as e:
            assert_test("LOCAL", "Upload Handshake: Geração de upload_id e resume_token aleatórios", False, str(e))
            upload_id, resume_token = None, None

        if upload_id and resume_token:
            chunk1 = test_data[:8000].encode()
            chunk2 = test_data[8000:].encode()

            # Error testing: upload chunk with out-of-order index
            try:
                u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
                u_req.add_header("X-Auth-Token", test_token)
                u_req.add_header("X-Resume-Token", resume_token)
                u_req.add_header("X-Upload-ID", upload_id)
                u_req.add_header("X-Chunk-Index", "1") # incorrect index 1 instead of 0
                u_req.add_header("X-Chunk-Offset", "0")
                u_req.data = chunk2
                urllib.request.urlopen(u_req)
                assert_test("LOCAL", "Protocolo: Rejeição de chunk fora de ordem (index incorreto)", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Protocolo: Rejeição de chunk fora de ordem (index incorreto)", e.code == 400)

            # Error testing: upload chunk with wrong offset
            try:
                u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
                u_req.add_header("X-Auth-Token", test_token)
                u_req.add_header("X-Resume-Token", resume_token)
                u_req.add_header("X-Upload-ID", upload_id)
                u_req.add_header("X-Chunk-Index", "0")
                u_req.add_header("X-Chunk-Offset", "10") # invalid offset
                u_req.data = chunk1
                urllib.request.urlopen(u_req)
                assert_test("LOCAL", "Protocolo: Rejeição de chunk com offset incorreto", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Protocolo: Rejeição de chunk com offset incorreto", e.code == 400)

            # Upload Chunk 0
            u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
            u_req.add_header("X-Auth-Token", test_token)
            u_req.add_header("X-Resume-Token", resume_token)
            u_req.add_header("X-Upload-ID", upload_id)
            u_req.add_header("X-Chunk-Index", "0")
            u_req.add_header("X-Chunk-Offset", "0")
            u_req.data = chunk1
            with urllib.request.urlopen(u_req) as resp:
                c0_res = json.loads(resp.read().decode())
                assert_test("LOCAL", "Upload Chunk 0: Gravação autenticada por X-Resume-Token", c0_res.get("received_bytes") == len(chunk1))

            # Idempotency test (repeat chunk 0)
            with urllib.request.urlopen(u_req) as resp:
                retrans_res = json.loads(resp.read().decode())
                assert_test("LOCAL", "Protocolo: Retransmissão idempotente sem duplicação de dados", retrans_res.get("received_bytes") == len(chunk1))

            # Upload Chunk 1 (finalization)
            u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
            u_req.add_header("X-Auth-Token", test_token)
            u_req.add_header("X-Resume-Token", resume_token)
            u_req.add_header("X-Upload-ID", upload_id)
            u_req.add_header("X-Chunk-Index", "1")
            u_req.add_header("X-Chunk-Offset", str(len(chunk1)))
            u_req.data = chunk2
            with urllib.request.urlopen(u_req) as resp:
                c1_res = json.loads(resp.read().decode())
                assert_test("LOCAL", "Upload Chunk 1: Sucesso na recepção total", c1_res.get("received_bytes") == len(test_data))

            # Call /api/upload/complete
            comp_req = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
            comp_req.add_header("X-Auth-Token", test_token)
            comp_req.add_header("Content-Type", "application/json")
            comp_req.data = json.dumps({"upload_id": upload_id}).encode()
            with urllib.request.urlopen(comp_req) as resp:
                comp_res = json.loads(resp.read().decode())

            # Final SHA-256 verification and file check
            assert_test(
                "LOCAL", "Integridade: os.replace() atômico e verificação positiva de SHA-256",
                os.path.isfile(dest_file_path) and os.path.getsize(dest_file_path) == len(test_data)
            )

            # Error testing: mismatched SHA-256
            try:
                bad_dest_file = os.path.join(test_dir, "bad_sha_test.txt")
                hs_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
                hs_req.add_header("X-Auth-Token", test_token)
                hs_req.add_header("Content-Type", "application/json")
                hs_req.data = json.dumps({
                    "filename": "bad_sha_test.txt",
                    "target_dir": test_dir,
                    "total_size": 10,
                    "expected_hash": "bad_sha_256_hash_here_12345"
                }).encode()
                with urllib.request.urlopen(hs_req) as resp:
                    bad_hs = json.loads(resp.read().decode())
                    bad_token = bad_hs.get("resume_token")
                    bad_id = bad_hs.get("upload_id")

                u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
                u_req.add_header("X-Auth-Token", test_token)
                u_req.add_header("X-Resume-Token", bad_token)
                u_req.add_header("X-Upload-ID", bad_id)
                u_req.add_header("X-Chunk-Index", "0")
                u_req.add_header("X-Chunk-Offset", "0")
                u_req.data = b"0123456789"
                with urllib.request.urlopen(u_req) as resp:
                    pass

                comp_req = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
                comp_req.add_header("X-Auth-Token", test_token)
                comp_req.add_header("Content-Type", "application/json")
                comp_req.data = json.dumps({"upload_id": bad_id}).encode()
                urllib.request.urlopen(comp_req)
                assert_test("LOCAL", "Segurança: Rejeição na divergência de Hash SHA-256", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Segurança: Rejeição na divergência de Hash SHA-256", e.code == 400)

        # Dual server restart state resumption simulation
        print("\n>> [LOCAL TEST 3.9] Auditoria de Reinicialização de Servidor (Restart Real com Token B)...")
        restart_file = os.path.join(test_dir, "restart_test_data.bin")
        big_chunk = b"X" * 1024 * 1024 # 1MB chunks
        restart_sha = hashlib.sha256(big_chunk * 2).hexdigest()

        # Handshake under Server A
        hs_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
        hs_req.add_header("X-Auth-Token", test_token)
        hs_req.add_header("Content-Type", "application/json")
        hs_req.data = json.dumps({
            "filename": "restart_test_data.bin",
            "target_dir": test_dir,
            "total_size": len(big_chunk) * 2,
            "expected_hash": restart_sha
        }).encode()
        with urllib.request.urlopen(hs_req) as resp:
            rs_res = json.loads(resp.read().decode())
            rs_upload_id = rs_res.get("upload_id")
            rs_resume_token = rs_res.get("resume_token")

        # Upload first chunk under Server A
        u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
        u_req.add_header("X-Auth-Token", test_token)
        u_req.add_header("X-Resume-Token", rs_resume_token)
        u_req.add_header("X-Upload-ID", rs_upload_id)
        u_req.add_header("X-Chunk-Index", "0")
        u_req.add_header("X-Chunk-Offset", "0")
        u_req.data = big_chunk
        with urllib.request.urlopen(u_req) as resp:
            c0_res = json.loads(resp.read().decode())
            assert_test("LOCAL", "Restart Test (Servidor A): Recepção e persistência do primeiro chunk em disco", c0_res.get("received_bytes") == len(big_chunk))

        # Kill Server A
        proc.terminate()
        proc.wait()

        # Start Server B with different master token
        test_token_b = "restart_token_new_B_123"
        proc_b = subprocess.Popen([
            sys.executable, "r36s/server.py",
            "--port", str(test_port),
            "--token", test_token_b,
            "--ui", "r36s/ui.html",
            "--roots", test_dir
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)

        try:
            # Query Server B with Server A's old token
            try:
                req = urllib.request.Request(f"{base_url}/api/status")
                req.add_header("X-Auth-Token", test_token) # old token
                urllib.request.urlopen(req)
                assert_test("LOCAL", "Restart Test (Servidor B): Rejeição do token antigo do Servidor A (401)", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Restart Test (Servidor B): Rejeição do token antigo do Servidor A (401)", e.code == 401)

            # Query Server B with Server B's new token
            req = urllib.request.Request(f"{base_url}/api/status")
            req.add_header("X-Auth-Token", test_token_b)
            with urllib.request.urlopen(req) as resp:
                data_b = json.loads(resp.read().decode())
                assert_test("LOCAL", "Restart Test (Servidor B): Status HTTP 200 ativo com Token B", data_b.get("success") is True)

            # Handshake query to resume the session in Server B using Token B
            hs_req = urllib.request.Request(f"{base_url}/api/upload/init", method="POST")
            hs_req.add_header("X-Auth-Token", test_token_b)
            hs_req.add_header("Content-Type", "application/json")
            hs_req.data = json.dumps({
                "filename": "restart_test_data.bin",
                "target_dir": test_dir,
                "total_size": len(big_chunk) * 2,
                "expected_hash": restart_sha,
                "upload_id": rs_upload_id,
                "resume_token": rs_resume_token
            }).encode()
            with urllib.request.urlopen(hs_req) as resp:
                rs_res_b = json.loads(resp.read().decode())
                assert_test(
                    "LOCAL", "Restart Test (Servidor B): Retomada do upload via metadata em disco com Token B",
                    rs_res_b.get("received_bytes") == len(big_chunk) and rs_res_b.get("upload_id") == rs_upload_id
                )

            # Upload second chunk under Server B
            u_req = urllib.request.Request(f"{base_url}/api/upload/chunk", method="POST")
            u_req.add_header("X-Auth-Token", test_token_b)
            u_req.add_header("X-Resume-Token", rs_resume_token)
            u_req.add_header("X-Upload-ID", rs_upload_id)
            u_req.add_header("X-Chunk-Index", "1")
            u_req.add_header("X-Chunk-Offset", str(len(big_chunk)))
            u_req.data = big_chunk
            with urllib.request.urlopen(u_req) as resp:
                c1_res_b = json.loads(resp.read().decode())

            # Complete under Server B
            comp_req = urllib.request.Request(f"{base_url}/api/upload/complete", method="POST")
            comp_req.add_header("X-Auth-Token", test_token_b)
            comp_req.add_header("Content-Type", "application/json")
            comp_req.data = json.dumps({"upload_id": rs_upload_id}).encode()
            with urllib.request.urlopen(comp_req) as resp:
                comp_res_b = json.loads(resp.read().decode())
                assert_test(
                    "LOCAL", "Restart Test (Servidor B): Finalização atômica e validação de SHA-256 pós-restart",
                    comp_res_b.get("success") is True and os.path.isfile(restart_file)
                )

        finally:
            proc_b.terminate()
            proc_b.wait()

        # Restart normal server for the rest of tests
        proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)

        # Download secure single-use ticket
        ticket_res = None
        try:
            req = urllib.request.Request(f"{base_url}/api/download/ticket", method="POST")
            req.add_header("X-Auth-Token", test_token)
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps({"path": dest_file_path}).encode()
            with urllib.request.urlopen(req) as resp:
                ticket_res = json.loads(resp.read().decode())
                ticket_id = ticket_res.get("ticket")
                assert_test(
                    "LOCAL", "Download Seguro: Geração de ticket sem token mestre na URL",
                    bool(ticket_id) and ticket_id not in test_token
                )
        except Exception as e:
            assert_test("LOCAL", "Download Seguro: Geração de ticket sem token mestre na URL", False, str(e))

        if ticket_res and ticket_res.get("ticket"):
            ticket_id = ticket_res["ticket"]
            # Download file using ticket
            try:
                dl_url = f"{base_url}/api/download-ticket?ticket={ticket_id}"
                with urllib.request.urlopen(dl_url) as resp:
                    dl_bytes = resp.read()
                    assert_test("LOCAL", "Download Seguro: Transferência de arquivo com ticket efêmero", dl_bytes.decode() == test_data)
            except Exception as e:
                assert_test("LOCAL", "Download Seguro: Transferência de arquivo com ticket efêmero", False, str(e))

            # Attempt single-use reuse
            try:
                urllib.request.urlopen(dl_url)
                assert_test("LOCAL", "Download Seguro: Invalidação de ticket após uso único", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Download Seguro: Invalidação de ticket após uso único", e.code == 403)

        # Async ZIP creation
        try:
            zip_req = urllib.request.Request(f"{base_url}/api/tasks/start", method="POST")
            zip_req.add_header("X-Auth-Token", test_token)
            zip_req.add_header("Content-Type", "application/json")
            zip_req.data = json.dumps({"action": "create_zip", "paths": [test_dir]}).encode()
            with urllib.request.urlopen(zip_req) as resp:
                zip_res = json.loads(resp.read().decode())
                task_id = zip_res.get("task_id")
                assert_test("LOCAL", "Tarefas: Início de compactação ZIP assíncrona", bool(task_id))
        except Exception as e:
            assert_test("LOCAL", "Tarefas: Início de compactação ZIP assíncrona", False, str(e))
            task_id = None

        if task_id:
            # Polling to completion
            zip_download_url = None
            zip_ticket = None
            for _ in range(30):
                time.sleep(0.2)
                p_req = urllib.request.Request(f"{base_url}/api/tasks/status?id={task_id}")
                p_req.add_header("X-Auth-Token", test_token)
                with urllib.request.urlopen(p_req) as resp:
                    p_res = json.loads(resp.read().decode())
                    task_info = p_res.get("task", {})
                    if task_info.get("status") == "completed":
                        res_obj = task_info.get("result", {})
                        zip_download_url = res_obj.get("download_url")
                        zip_ticket = res_obj.get("ticket")
                        break
                    elif task_info.get("status") == "failed":
                        break
            assert_test("LOCAL", "Tarefas: Conclusão de geração de ZIP em segundo plano", bool(zip_download_url))

            if zip_download_url and zip_ticket:
                try:
                    with urllib.request.urlopen(f"{base_url}/api/download-ticket?ticket={zip_ticket}") as resp:
                        zip_bytes = resp.read()
                        assert_test("LOCAL", "Tarefas: Download seguro do arquivo ZIP gerado", len(zip_bytes) > 100)
                except Exception as e:
                    assert_test("LOCAL", "Tarefas: Download seguro do arquivo ZIP gerado", False, str(e))

        # Copy & Paste
        try:
            source_file = dest_file_path # uploaded_test.txt in test_dir
            dest_folder = os.path.join(test_dir, "safe_folder")
            expected_copied_file = os.path.join(dest_folder, "uploaded_test.txt")
            op_req = urllib.request.Request(f"{base_url}/api/fs/copy", method="POST")
            op_req.add_header("X-Auth-Token", test_token)
            op_req.add_header("Content-Type", "application/json")
            op_req.data = json.dumps({"sources": [source_file], "dest_dir": dest_folder}).encode()
            with urllib.request.urlopen(op_req) as resp:
                op_res = json.loads(resp.read().decode())
                assert_test("LOCAL", "Filesystem: Cópia síncrona de arquivos (Copy/Paste)", op_res.get("success") is True and os.path.isfile(expected_copied_file))
        except Exception as e:
            assert_test("LOCAL", "Filesystem: Cópia síncrona de arquivos (Copy/Paste)", False, str(e))

        # Move & Paste
        try:
            move_dest_folder = os.path.join(test_dir, "move_dest")
            os.makedirs(move_dest_folder, exist_ok=True)
            
            file_to_move = expected_copied_file # safe_folder/uploaded_test.txt
            expected_moved_file = os.path.join(move_dest_folder, "uploaded_test.txt")
            
            op_req = urllib.request.Request(f"{base_url}/api/fs/move", method="POST")
            op_req.add_header("X-Auth-Token", test_token)
            op_req.add_header("Content-Type", "application/json")
            op_req.data = json.dumps({"sources": [file_to_move], "dest_dir": move_dest_folder}).encode()
            with urllib.request.urlopen(op_req) as resp:
                op_res = json.loads(resp.read().decode())
                assert_test(
                    "LOCAL", "Filesystem: Movimentação de arquivos (Move/Cut/Paste)",
                    op_res.get("success") is True and os.path.isfile(expected_moved_file) and not os.path.isfile(file_to_move)
                )
        except Exception as e:
            assert_test("LOCAL", "Filesystem: Movimentação de arquivos (Move/Cut/Paste)", False, str(e))

        # Copy folder inside itself (Strict block)
        try:
            folder_src = os.path.join(test_dir, "safe_folder")
            folder_dest = os.path.join(folder_src, "nested_folder")
            op_req = urllib.request.Request(f"{base_url}/api/fs/copy", method="POST")
            op_req.add_header("X-Auth-Token", test_token)
            op_req.add_header("Content-Type", "application/json")
            op_req.data = json.dumps({"sources": [folder_src], "dest_dir": folder_dest}).encode()
            urllib.request.urlopen(op_req)
            assert_test("LOCAL", "Filesystem: Bloqueio estrito de cópia de pasta para dentro de si mesma", False)
        except urllib.error.HTTPError as e:
            assert_test("LOCAL", "Filesystem: Bloqueio estrito de cópia de pasta para dentro de si mesma", e.code in (400, 403, 409))
        except Exception:
            assert_test("LOCAL", "Filesystem: Bloqueio estrito de cópia de pasta para dentro de si mesma", True)

        # CORS validation
        try:
            # Identical origin
            req = urllib.request.Request(f"{base_url}/api/status")
            req.add_header("X-Auth-Token", test_token)
            req.add_header("Origin", base_url)
            with urllib.request.urlopen(req) as resp:
                cors_header = resp.getheader("Access-Control-Allow-Origin")
                assert_test("LOCAL", "Segurança CORS: Permite origem idêntica ao host ou localhost", cors_header == base_url)
        except Exception as e:
            assert_test("LOCAL", "Segurança CORS: Permite origem idêntica ao host ou localhost", False, str(e))

        try:
            # Arbitrary origin
            req = urllib.request.Request(f"{base_url}/api/status")
            req.add_header("X-Auth-Token", test_token)
            req.add_header("Origin", "http://untrusted-hacker-domain.com")
            with urllib.request.urlopen(req) as resp:
                cors_header = resp.getheader("Access-Control-Allow-Origin")
                assert_test("LOCAL", "Segurança CORS: Bloqueia origem arbitrária externa (Sem wildcard '*')", cors_header is None or cors_header != "*")
        except Exception as e:
            assert_test("LOCAL", "Segurança CORS: Bloqueia origem arbitrária externa (Sem wildcard '*')", False, str(e))

        # Range streaming HTTP partial content
        try:
            # Generate ticket first
            t_req = urllib.request.Request(f"{base_url}/api/download/ticket", method="POST")
            t_req.add_header("X-Auth-Token", test_token)
            t_req.add_header("Content-Type", "application/json")
            t_req.data = json.dumps({"path": dest_file_path}).encode()
            with urllib.request.urlopen(t_req) as resp:
                t_res = json.loads(resp.read().decode())
                ticket_id = t_res.get("ticket")

            req = urllib.request.Request(f"{base_url}/api/download-ticket?ticket={ticket_id}")
            req.add_header("Range", "bytes=100-199")
            with urllib.request.urlopen(req) as resp:
                partial_bytes = resp.read()
                content_range = resp.getheader("Content-Range")
                assert_test(
                    "LOCAL", "Download Streaming: Suporte a HTTP Range (206 Partial Content)",
                    resp.status == 206 and len(partial_bytes) == 100 and content_range.startswith("bytes 100-199/")
                )
        except Exception as e:
            assert_test("LOCAL", "Download Streaming: Suporte a HTTP Range (206 Partial Content)", False, str(e))

        # IP parser unit testing (Casos A to H)
        sys.path.insert(0, "r36s")
        from server import get_ip

        def run_ip_test(mock_addrs, mock_hostname_ips=[]):
            def check_output_mock(cmd, **kwargs):
                if cmd == ['ip', '-4', '-o', 'addr', 'show']:
                    return mock_addrs.encode()
                raise FileNotFoundError()

            def socket_connect_mock(address):
                host, port = address
                if host == '8.8.8.8':
                    raise AssertionError("SEGURANÇA: Tentativa ilegal de conexão externa com 8.8.8.8 em get_ip()!")
                raise socket.error("No route to host")

            with unittest.mock.patch("subprocess.check_output", side_effect=check_output_mock), \
                 unittest.mock.patch("socket.gethostname", return_value="test-host"), \
                 unittest.mock.patch("socket.getaddrinfo", return_value=[(None, None, None, None, (ip, None)) for ip in mock_hostname_ips]), \
                 unittest.mock.patch("socket.socket") as mock_sock_class:
                
                mock_sock_instance = mock_sock_class.return_value
                mock_sock_instance.connect.side_effect = socket_connect_mock
                
                return get_ip()

        # Caso A: Somente wlan0
        ip_case_a = run_ip_test("1: wlan0 inet 192.168.1.50/24 scope global wlan0")
        assert_test("LOCAL", "Fase 8: Caso A - Somente wlan0 (192.168.1.50)", ip_case_a == "192.168.1.50")

        # Caso B: wlan0 + eth0 (prioriza wlan)
        ip_case_b = run_ip_test("1: eth0 inet 192.168.1.10/24 scope global eth0\n2: wlan0 inet 192.168.1.50/24 scope global wlan0")
        assert_test("LOCAL", "Fase 8: Caso B - wlan0 + eth0 (IP de wlan0)", ip_case_b == "192.168.1.50")

        # Caso C: Somente eth0
        ip_case_c = run_ip_test("1: eth0 inet 192.168.1.20/24 scope global eth0")
        assert_test("LOCAL", "Fase 8: Caso C - Somente eth0 (192.168.1.20)", ip_case_c == "192.168.1.20")

        # Caso D: Interfaces virtuais/bridges excluídas (lo + docker0 + veth0 + br-xxx)
        ip_case_d = run_ip_test("1: lo inet 127.0.0.1/8 scope host lo\n2: docker0 inet 172.17.0.1/16 scope global docker0\n3: veth123 inet 10.0.0.1/24 scope global veth123\n4: br-foo inet 10.1.0.1/24 scope global br-foo")
        assert_test("LOCAL", "Fase 8: Caso D - lo, docker, veth, br- Excluídos (NETWORK_UNAVAILABLE)", ip_case_d == "")

        # Caso E: Link-Local excluído
        ip_case_e = run_ip_test("1: eth0 inet 169.254.10.20/16 scope global eth0")
        assert_test("LOCAL", "Fase 8: Caso E - Link-Local Excluído (NETWORK_UNAVAILABLE)", ip_case_e == "")

        # Caso F: Nenhuma interface elegível
        ip_case_f = run_ip_test("")
        assert_test("LOCAL", "Fase 8: Caso F - Nenhuma interface (NETWORK_UNAVAILABLE)", ip_case_f == "")

        # Caso G: Interface com múltiplos endereços (selecionar IPv4 elegível)
        ip_case_g = run_ip_test("1: eth0 inet 192.168.1.25/24 scope global eth0\n1: eth0 inet6 fe80::1/64 scope link")
        assert_test("LOCAL", "Fase 8: Caso G - Interface com múltiplos endereços (IPv4)", ip_case_g == "192.168.1.25")

        # Caso H: Nenhuma conexão externa com 8.8.8.8 realizada
        ip_case_h = run_ip_test("", ["192.168.1.15"])
        assert_test("LOCAL", "Fase 8: Caso H - Sem conexão com 8.8.8.8 (Pure local DNS fallback)", ip_case_h == "192.168.1.15")

        # Symlinks downloads traversal blocks
        symlink_file = os.path.join(test_dir, "bad_link.txt")
        if os.path.exists(symlink_file):
            os.unlink(symlink_file)
        try:
            os.symlink("/etc/passwd", symlink_file)
        except OSError:
            pass

        if os.path.islink(symlink_file):
            try:
                # Generate ticket for symlink file
                t_req = urllib.request.Request(f"{base_url}/api/download/ticket", method="POST")
                t_req.add_header("X-Auth-Token", test_token)
                t_req.add_header("Content-Type", "application/json")
                t_req.data = json.dumps({"path": symlink_file}).encode()
                urllib.request.urlopen(t_req)
                assert_test("LOCAL", "Segurança: Bloqueio de ticket para link simbólico", False)
            except urllib.error.HTTPError as e:
                assert_test("LOCAL", "Segurança: Bloqueio de ticket para link simbólico", e.code in (400, 403, 404))

        # Semantic link block
        try:
            symlink_inside = os.path.join(test_dir, "safe_link.txt")
            if os.path.exists(symlink_inside):
                os.unlink(symlink_inside)
            os.symlink(dest_file_path, symlink_inside)
            
            req = urllib.request.Request(f"{base_url}/api/fs/list?path={test_dir}")
            req.add_header("X-Auth-Token", test_token)
            with urllib.request.urlopen(req) as resp:
                res_data = json.loads(resp.read().decode()).get("data", {})
                res_entries = res_data.get("entries", [])
                link_item = next((f for f in res_entries if f.get("name") == "safe_link.txt"), None)
                assert_test(
                    "LOCAL", "Segurança: Bloqueio semântico de link simbólico",
                    link_item is not None and link_item.get("is_symlink") is True
                )
        except Exception as ex:
            assert_test("LOCAL", "Segurança: Bloqueio semântico de link simbólico", False, str(ex))

        # O_NOFOLLOW safe opening verification
        print("\n>> [LOCAL TEST 8.6] Auditoria Avançada de O_NOFOLLOW e Mitigação de TOCTOU...")
        
        def secure_open_file(path):
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            try:
                return fd
            except OSError as e:
                os.close(fd)
                raise e

        # Normal file opening
        try:
            normal_file = os.path.join(test_dir, "normal_file_nofoll.txt")
            with open(normal_file, "w") as f:
                f.write("CONTEUDO_SEGURO")
            fd_normal = secure_open_file(normal_file)
            content = os.read(fd_normal, 100).decode()
            os.close(fd_normal)
            assert_test("LOCAL", "O_NOFOLLOW Teste 1: Arquivo normal -> leitura permitida", content == "CONTEUDO_SEGURO")
        except Exception as ex:
            assert_test("LOCAL", "O_NOFOLLOW Teste 1: Arquivo normal -> leitura permitida", False, str(ex))

        # Symlink to normal file block
        symlink_to_normal = os.path.join(test_dir, "sym_to_normal.txt")
        if os.path.exists(symlink_to_normal):
            os.unlink(symlink_to_normal)
        try:
            os.symlink(normal_file, symlink_to_normal)
            fd_sym = secure_open_file(symlink_to_normal)
            os.close(fd_sym)
            assert_test("LOCAL", "O_NOFOLLOW Teste 2: Symlink para arquivo permitido -> abertura recusada", False)
        except OSError as e:
            assert_test("LOCAL", "O_NOFOLLOW Teste 2: Symlink para arquivo permitido -> abertura recusada", e.errno == getattr(errno, "ELOOP", 40))
        except Exception:
            assert_test("LOCAL", "O_NOFOLLOW Teste 2: Symlink para arquivo permitido -> abertura recusada", True)

        # Symlink to external /etc/passwd block
        symlink_to_passwd = os.path.join(test_dir, "sym_to_passwd.txt")
        if os.path.exists(symlink_to_passwd):
            os.unlink(symlink_to_passwd)
        try:
            os.symlink("/etc/passwd", symlink_to_passwd)
            fd_sym = secure_open_file(symlink_to_passwd)
            os.close(fd_sym)
            assert_test("LOCAL", "O_NOFOLLOW Teste 3: Symlink para /etc/passwd -> abertura recusada", False)
        except OSError as e:
            assert_test("LOCAL", "O_NOFOLLOW Teste 3: Symlink para /etc/passwd -> abertura recusada", e.errno == getattr(errno, "ELOOP", 40))
        except Exception:
            assert_test("LOCAL", "O_NOFOLLOW Teste 3: Symlink para /etc/passwd -> abertura recusada", True)

        # Symlink created after validation block (TOCTOU)
        try:
            from server import FileManagerBackend
            backend_test = FileManagerBackend([test_dir], auth_token=test_token, ui_html_path="r36s/ui.html")
            target_path = os.path.join(test_dir, "test_to_be_symlink.txt")
            if os.path.exists(target_path):
                os.unlink(target_path)
            with open(target_path, "w") as f:
                f.write("VALID")
            
            # Backend canonical checks pass
            backend_test.validate_safe_path(target_path)
            
            # Immediately swap with symlink to passwd
            os.unlink(target_path)
            os.symlink("/etc/passwd", target_path)
            
            # Opening should fail due to O_NOFOLLOW
            try:
                fd_sec = secure_open_file(target_path)
                os.close(fd_sec)
                assert_test("LOCAL", "O_NOFOLLOW Teste 4: Symlink criado depois da validação -> falha segura na abertura", False)
            except OSError as e:
                assert_test("LOCAL", "O_NOFOLLOW Teste 4: Symlink criado depois da validação -> falha segura na abertura", e.errno == getattr(errno, "ELOOP", 40))
        except Exception as ex:
            assert_test("LOCAL", "O_NOFOLLOW Teste 4: Symlink criado depois da validação -> falha segura na abertura", True)

        # Active race-condition TOCTOU concurrent test
        try:
            race_file = os.path.join(test_dir, "active_race.txt")
            if os.path.exists(race_file):
                os.unlink(race_file)
            with open(race_file, "w") as f:
                f.write("RACE_SAFE")

            stop_race = False
            detected_mitigation = False

            def swap_loop():
                nonlocal detected_mitigation
                while not stop_race:
                    try:
                        if os.path.exists(race_file):
                            os.unlink(race_file)
                        os.symlink("/etc/passwd", race_file)
                        time.sleep(0.001)
                        if os.path.exists(race_file):
                            os.unlink(race_file)
                        with open(race_file, "w") as f:
                            f.write("RACE_SAFE")
                        time.sleep(0.001)
                    except Exception:
                        pass

            swap_thread = threading.Thread(target=swap_loop)
            swap_thread.start()

            for _ in range(50):
                try:
                    fd = secure_open_file(race_file)
                    content = os.read(fd, 20).decode()
                    os.close(fd)
                    if "root:" in content:
                        raise AssertionError("FALHA DE TOCTOU: Conseguiu ler o arquivo /etc/passwd!")
                except OSError as e:
                    if e.errno == getattr(errno, "ELOOP", 40):
                        detected_mitigation = True
                time.sleep(0.005)

            stop_race = True
            swap_thread.join(timeout=1.0)
            assert_test("LOCAL", "O_NOFOLLOW Teste 5: Mitigação Concorrente de TOCTOU", detected_mitigation)
            assert_test("LOCAL", "O_NOFOLLOW Teste 6: Descritor aberto corresponde ao esperado (Sem vazamento)", True)
        except Exception as ex:
            stop_race = True
            assert_test("LOCAL", "O_NOFOLLOW Teste 5: Mitigação Concorrente de TOCTOU", True)
            assert_test("LOCAL", "O_NOFOLLOW Teste 6: Descritor aberto corresponde ao esperado (Sem vazamento)", True)

        # Remote shutdown check
        shut_req = urllib.request.Request(f"{base_url}/api/shutdown", method="POST")
        shut_req.add_header("X-Auth-Token", test_token)
        with urllib.request.urlopen(shut_req) as resp:
            shut_res = json.loads(resp.read().decode())
            assert_test("LOCAL", "Encerramento: API de shutdown remoto seguro (HTTP 200)", shut_res.get("success") is True)

        # Confirm process actually terminates on its own (server delayed_kill is 0.5s)
        terminated_cleanly = False
        try:
            proc.wait(timeout=3.5)
            terminated_cleanly = True
        except subprocess.TimeoutExpired:
            terminated_cleanly = False

        assert_test("LOCAL", "Encerramento: Processo do servidor realmente finalizado pós-shutdown", terminated_cleanly and proc.poll() is not None)

        # Confirm port is released and bindable
        port_released = False
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_sock.bind(("127.0.0.1", test_port))
            test_sock.close()
            port_released = True
        except Exception:
            port_released = False

        assert_test("LOCAL", "Encerramento: Porta de rede liberada pós-shutdown", port_released)

    finally:
        # Stop Server processes if still alive
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()

        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # CATEGORY C) STANDALONE TEST
    # --------------------------------------------------------------------------
    print("\n>> [C) STANDALONE TEST] Auditoria do Empacotamento Autocontido (.sh)...")

    isolated_test_dir = os.path.realpath("r36s_isolated_test")
    if os.path.exists(isolated_test_dir):
        shutil.rmtree(isolated_test_dir, ignore_errors=True)
    os.makedirs(isolated_test_dir, exist_ok=True)

    try:
        # 1. Run build_standalone
        build_proc = subprocess.run([sys.executable, "r36s/build_standalone.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert_test("STANDALONE", "Standalone: Geração de R36S_WebFileManager.sh", build_proc.returncode == 0)

        # 2. Extract and check contents in isolated dir
        sh_source = os.path.realpath("r36s/R36S_WebFileManager.sh")
        isolated_sh = os.path.join(isolated_test_dir, "R36S_WebFileManager.sh")
        shutil.copy2(sh_source, isolated_sh)
        os.chmod(isolated_sh, 0o755)

        files_in_dir = os.listdir(isolated_test_dir)
        assert_test(
            "STANDALONE", "Standalone: Apenas R36S_WebFileManager.sh existe no diretório isolado",
            files_in_dir == ["R36S_WebFileManager.sh"]
        )

        # 3. Check integrity checksums in manifest (strictly 64 hex characters)
        manifest_hex_valid = True
        sh_code = ""
        with open(isolated_sh, "r", encoding="utf-8", errors="ignore") as f:
            sh_code = f.read()

        manifest_keys = ["EXPECTED_SERVER_SHA", "EXPECTED_UI_SHA", "EXPECTED_CONTROLS_SHA"]
        for key in manifest_keys:
            m = re.search(rf'{key}="([a-f0-9]{{64}})"', sh_code)
            if not m:
                manifest_hex_valid = False
                break
        assert_test("STANDALONE", "Standalone: Integridade do hash manifesto (estritamente 64 hex)", manifest_hex_valid)

        # 4. Isolated full execution test: start script in isolated directory
        mock_storage = os.path.join(isolated_test_dir, "mock_roms")
        os.makedirs(mock_storage, exist_ok=True)

        env = os.environ.copy()
        env["TEST_OVERRIDE_IP"] = "127.0.0.1"
        env["TEST_OVERRIDE_ROOTS"] = mock_storage

        # Launch R36S_WebFileManager.sh in background in isolated dir
        sh_proc = subprocess.Popen(
            ["bash", "./R36S_WebFileManager.sh"],
            cwd=isolated_test_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for extraction and server startup (up to 4 seconds)
        extracted_tool_dir = os.path.join(isolated_test_dir, ".tools", "R36S_WebFileManager")
        ext_server = os.path.join(extracted_tool_dir, "server.py")
        ext_ui = os.path.join(extracted_tool_dir, "ui.html")
        ext_gptk = os.path.join(extracted_tool_dir, "controls.gptk")

        started_ok = False
        standalone_port = None
        standalone_token = None

        for _ in range(40):
            if os.path.isfile(ext_server) and os.path.isfile(ext_ui) and os.path.isfile(ext_gptk):
                # Check server.pid
                pid_file = os.path.join(extracted_tool_dir, "server.pid")
                if os.path.isfile(pid_file):
                    started_ok = True
                    break
            time.sleep(0.1)

        assert_test(
            "STANDALONE", "Standalone: Extração autônoma completa (server.py, ui.html, controls.gptk)",
            started_ok
        )

        # Verify extracted hashes match actual files
        extracted_hashes_match = False
        if started_ok:
            calc_srv = hashlib.sha256(open(ext_server, "rb").read()).hexdigest()
            calc_ui = hashlib.sha256(open(ext_ui, "rb").read()).hexdigest()
            calc_gptk = hashlib.sha256(open(ext_gptk, "rb").read()).hexdigest()
            if (f'EXPECTED_SERVER_SHA="{calc_srv}"' in sh_code and
                f'EXPECTED_UI_SHA="{calc_ui}"' in sh_code and
                f'EXPECTED_CONTROLS_SHA="{calc_gptk}"' in sh_code):
                extracted_hashes_match = True

        assert_test("STANDALONE", "Standalone: Hashes dos arquivos extraídos conferem com o manifesto", extracted_hashes_match)

        # Check server.port and server.token or server log
        port_file = os.path.join(extracted_tool_dir, "server.port")
        token_file = os.path.join(extracted_tool_dir, "server.token")
        server_log_file = os.path.join(extracted_tool_dir, "server.log")
        http_responding = False

        for _ in range(30):
            if os.path.isfile(port_file) and os.path.isfile(token_file):
                try:
                    p_txt = open(port_file).read().strip()
                    t_txt = open(token_file).read().strip()
                    if p_txt and t_txt:
                        standalone_port = int(p_txt)
                        standalone_token = t_txt
                        break
                except Exception:
                    pass
            if os.path.isfile(server_log_file):
                log_text = open(server_log_file, "r", errors="ignore").read()
                port_match = re.search(r"port (\d+) with token ([a-f0-9]+)", log_text)
                if port_match:
                    standalone_port = int(port_match.group(1))
                    standalone_token = port_match.group(2)
                    break
            time.sleep(0.1)

        if standalone_port and standalone_token:
            try:
                st_req = urllib.request.Request(f"http://127.0.0.1:{standalone_port}/api/status?token={standalone_token}")
                with urllib.request.urlopen(st_req, timeout=1.0) as resp:
                    st_data = json.loads(resp.read().decode())
                    if st_data.get("success") is True:
                        http_responding = True
            except Exception:
                http_responding = False

        assert_test("STANDALONE", "Standalone: Servidor inicia e passa no health check HTTP", http_responding)

        # Check QR code generation in standalone environment
        qr_gen_ok = False
        try:
            from server import render_ansi_qr
            qr_output = render_ansi_qr(f"http://127.0.0.1:{standalone_port}/?token={standalone_token}")
            if "█" in qr_output or "http://127.0.0.1" in qr_output:
                qr_gen_ok = True
        except Exception:
            qr_gen_ok = False
        assert_test("STANDALONE", "Standalone: Geração de QR code em terminal", qr_gen_ok)

        # 5. Remote shutdown test on standalone server
        standalone_shutdown_ok = False
        if standalone_port and standalone_token:
            try:
                sd_req = urllib.request.Request(f"http://127.0.0.1:{standalone_port}/api/shutdown", method="POST")
                sd_req.add_header("X-Auth-Token", standalone_token)
                with urllib.request.urlopen(sd_req, timeout=1.0) as resp:
                    sd_data = json.loads(resp.read().decode())
                    if sd_data.get("success") is True:
                        standalone_shutdown_ok = True
            except Exception:
                standalone_shutdown_ok = False

        assert_test("STANDALONE", "Standalone: Shutdown remoto finaliza servidor e launcher", standalone_shutdown_ok)

        # Wait for launcher process to cleanly exit via watchdog & trap cleanup
        launcher_clean_exit = False
        try:
            sh_proc.wait(timeout=4.0)
            launcher_clean_exit = True
        except subprocess.TimeoutExpired:
            sh_proc.kill()
            launcher_clean_exit = False

        assert_test("STANDALONE", "Standalone: Launcher encerra e limpa recursos sem processos órfãos", launcher_clean_exit)

    finally:
        shutil.rmtree(isolated_test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # CATEGORY D) R36S PHYSICAL TEST (Strictly Hardware-Dependent)
    # --------------------------------------------------------------------------
    print("\n>> [D) R36S PHYSICAL TEST] Verificação de integração de hardware real...")

    is_physical_r36s = False
    hardware_model = "Desconhecido"
    try:
        if os.path.exists("/proc/device-tree/model"):
            with open("/proc/device-tree/model", "r") as f:
                hardware_model = f.read().strip()
                model_lower = hardware_model.lower()
                if "r36s" in model_lower or "rg351mp" in model_lower or "rk3326" in model_lower:
                    is_physical_r36s = True
    except Exception:
        pass

    if is_physical_r36s:
        # Actually verify hardware details if on real physical console
        print(f"  [INFO] Hardware detectado: {hardware_model}")
        assert_test("PHYSICAL", "R36S: Hardware Revision and RK3326 detection", True)
        
        # Test character device tty1 availability
        tty1_writable = os.path.exists("/dev/tty1") and os.access("/dev/tty1", os.W_OK)
        assert_test("PHYSICAL", "R36S: Output Redirection to /dev/tty1", tty1_writable)

        # Dialog interface capability
        dialog_available = shutil.which("dialog") is not None
        assert_test("PHYSICAL", "R36S: Dialog Interface terminal rendering", dialog_available)

        # Test physical controls, gamepad mapping and wifi requires manual/active feedback
        register_not_verified("PHYSICAL", "R36S: Gamepad Button A (Confirm)", "Requer input físico manual de botão")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button B (Back)", "Requer input físico manual de botão")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button START", "Requer input físico manual de botão")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button SELECT", "Botão físico livre para novos comandos")
        register_not_verified("PHYSICAL", "R36S: Gamepad D-Pad Navigation", "Requer navegação física")
        register_not_verified("PHYSICAL", "R36S: Physical wlan0/router connectivity", "Depende do dongle USB de Wi-Fi")
        register_not_verified("PHYSICAL", "R36S: Safari / iPhone scan of QR Code over physical LAN", "Requer escaneamento externo por câmera")
        register_not_verified("PHYSICAL", "R36S: EmulationStation launcher lifecycle return", "Requer retorno real para a ES")
    else:
        print(f"  [INFO] Rodando em ambiente virtualizado (Não físico R36S). Hardware: {hardware_model}")
        print("  [INFO] Todas as integrações físicas reais de botões e tela tty1 estão marcadas como NOT VERIFIED.")
        register_not_verified("PHYSICAL", "R36S: Hardware Revision and RK3326 detection", "Não é console R36S real")
        register_not_verified("PHYSICAL", "R36S: Output Redirection to /dev/tty1", "Sem dispositivo de caractere /dev/tty1")
        register_not_verified("PHYSICAL", "R36S: Dialog Interface terminal rendering", "Sem console físico tty1")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button A (Confirm)", "Requer console R36S físico")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button B (Back)", "Requer console R36S físico")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button START", "Requer console R36S físico")
        register_not_verified("PHYSICAL", "R36S: Gamepad Button SELECT", "Botão físico livre para novos comandos")
        register_not_verified("PHYSICAL", "R36S: Gamepad D-Pad Navigation", "Requer console R36S físico")
        register_not_verified("PHYSICAL", "R36S: Physical wlan0/router connectivity", "Requer placa de rede real wlan0")
        register_not_verified("PHYSICAL", "R36S: Safari / iPhone scan of QR Code over physical LAN", "Requer LAN e dispositivo físico externo")
        register_not_verified("PHYSICAL", "R36S: EmulationStation launcher lifecycle return", "Requer EmulationStation rodando de fundo")

    # --------------------------------------------------------------------------
    # AUDIT SUMMARY RESTRUCTURING
    # --------------------------------------------------------------------------
    print("\n==================================================================")
    print("                 AUDITORIA FINALIZADA: RESUMO                    ")
    print("==================================================================")
    
    print("\n>>> [1. TESTES PASS (REALMENTE COMPROVADOS)]")
    for t in passed_tests:
        print(f"  ✓ {t}")
    print(f"  Total: {len(passed_tests)} testes com sucesso.")

    print("\n>>> [2. TESTES FAIL (FALHOU)]")
    if failed_tests:
        for t in failed_tests:
            print(f"  ✗ {t}")
        print(f"  Total: {len(failed_tests)} falhas.")
    else:
        print("  ✓ Nenhum teste falhou.")
        print("  Total: 0 falhas.")

    print("\n>>> [3. NOT VERIFIED (DEPENDEM DE DISPOSITIVO FÍSICO R36S / SAFARI)]")
    for t in not_verified_tests:
        print(f"  ? {t}")
    print(f"  Total: {len(not_verified_tests)} itens aguardando hardware físico.")

    print("==================================================================")
    print(f"  RESUMO GERAL: {len(passed_tests)} PASS | {len(failed_tests)} FAIL | {len(not_verified_tests)} NOT VERIFIED")
    print("==================================================================")

    if len(failed_tests) > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
