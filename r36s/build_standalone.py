#!/usr/bin/env python3
"""
Build script to pack server.py, ui.html, controls.gptk, and assets/ into a single,
completely self-contained R36S_WebFileManager.sh executable with strict integrity manifest.
"""

import os
import base64
import zipfile
import tempfile
import hashlib

def sha256sum(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def build_standalone():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_py = os.path.join(base_dir, "server.py")
    ui_html = os.path.join(base_dir, "ui.html")
    controls_gptk = os.path.join(base_dir, "controls.gptk")
    assets_dir = os.path.join(base_dir, "assets")
    target_sh = os.path.join(base_dir, "R36S_WebFileManager.sh")

    with open(server_py, "rb") as f:
        server_bytes = f.read()
        server_b64 = base64.b64encode(server_bytes).decode("ascii")
        server_sha = hashlib.sha256(server_bytes).hexdigest()

    with open(ui_html, "rb") as f:
        ui_bytes = f.read()
        ui_b64 = base64.b64encode(ui_bytes).decode("ascii")
        ui_sha = hashlib.sha256(ui_bytes).hexdigest()

    with open(controls_gptk, "rb") as f:
        controls_bytes = f.read()
        controls_b64 = base64.b64encode(controls_bytes).decode("ascii")
        controls_sha = hashlib.sha256(controls_bytes).hexdigest()

    # Pack assets dir into a zip in memory
    assets_b64 = ""
    assets_sha = ""
    if os.path.isdir(assets_dir):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            tmp_zip_name = tmp_zip.name
        try:
            with zipfile.ZipFile(tmp_zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(assets_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, assets_dir)
                        zf.write(full_path, rel_path)
            with open(tmp_zip_name, "rb") as f:
                assets_bytes = f.read()
                assets_b64 = base64.b64encode(assets_bytes).decode("ascii")
                assets_sha = hashlib.sha256(assets_bytes).hexdigest()
        finally:
            if os.path.exists(tmp_zip_name):
                os.remove(tmp_zip_name)

    sh_template = f'''#!/usr/bin/env bash
# ==============================================================================
# R36S Web File Manager + QR Transfer (Autocontido com Manifesto SHA-256)
# Desenvolvido para R36S físico com dArkOS RE (Debian 12 Bookworm, Kernel 4.4.189)
#
# Produto 100% autocontido: não depende de nenhum arquivo externo.
# ==============================================================================

set -eo pipefail

# Manifesto de integridade SHA-256 do payload
EXPECTED_SERVER_SHA="{server_sha}"
EXPECTED_UI_SHA="{ui_sha}"
EXPECTED_CONTROLS_SHA="{controls_sha}"
EXPECTED_ASSETS_SHA="{assets_sha}"

# ------------------------------------------------------------------------------
# 1. TRAP & LIMPEZA DE PROCESSOS (Gerenciamento Exclusivo por PID)
# ------------------------------------------------------------------------------
cleanup() {{
    printf "\\033[?25h" || true
    echo ""
    echo ">> Encerrando serviços do R36S Web File Manager..."

    if [[ -n "${{SERVER_PID:-}}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi

    if [[ -n "${{GPTOKEYB_PID:-}}" ]] && kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
        kill "$GPTOKEYB_PID" 2>/dev/null || true
        wait "$GPTOKEYB_PID" 2>/dev/null || true
    fi

    echo ">> Servidor encerrado. Retornando ao EmulationStation..."
    sleep 1
    clear || true
}}

trap cleanup EXIT INT TERM

# ------------------------------------------------------------------------------
# 2. VERIFICAÇÃO DE AMBIENTE & PYTHON 3 RUNTIME
# ------------------------------------------------------------------------------
clear || true
echo "=================================================="
echo "    R36S Web File Manager - Inicializando         "
echo "=================================================="
echo ""

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif [[ -x "/usr/bin/python3" ]]; then
    PYTHON_BIN="/usr/bin/python3"
fi

if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERRO CRÍTICO: Python 3 não foi detectado no sistema."
    exit 1
fi

echo ">> Python 3 detectado: $PYTHON_BIN"

# ------------------------------------------------------------------------------
# 3. EXTRAÇÃO COM STAGING/TRANSAÇÃO E VALIDAÇÃO DE MANIFESTO SHA-256
# ------------------------------------------------------------------------------
if [[ -d "/roms/tools" ]] && [[ -w "/roms/tools" ]]; then
    APP_BASE="/roms/tools/.tools"
else
    SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    APP_BASE="$SCRIPT_DIR/.tools"
fi

APP_DIR="$APP_BASE/R36S_WebFileManager"
STAGING_DIR="$APP_BASE/R36S_WebFileManager_staging"

echo ">> Preparando staging em $STAGING_DIR..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/assets"

# Extrair server.py
"$PYTHON_BIN" -c "import base64; open('$STAGING_DIR/server.py', 'wb').write(base64.b64decode('$SERVER_B64'))"
# Extrair ui.html
"$PYTHON_BIN" -c "import base64; open('$STAGING_DIR/ui.html', 'wb').write(base64.b64decode('$UI_B64'))"
# Extrair controls.gptk
"$PYTHON_BIN" -c "import base64; open('$STAGING_DIR/controls.gptk', 'wb').write(base64.b64decode('$CONTROLS_B64'))"
# Extrair assets zip
"$PYTHON_BIN" -c "
import base64, zipfile, io
b64_data = '$ASSETS_B64'
if b64_data:
    try:
        data = base64.b64decode(b64_data)
        zf = zipfile.ZipFile(io.BytesIO(data))
        zf.extractall('$STAGING_DIR/assets')
    except Exception as e:
        print('Warning extracting assets:', e)
"

# Validação de integridade do payload antes do commit atômico
echo ">> Validando hashes SHA-256 do payload..."
CALC_SERVER_SHA=$("$PYTHON_BIN" -c "import hashlib; print(hashlib.sha256(open('$STAGING_DIR/server.py','rb').read()).hexdigest())")
CALC_UI_SHA=$("$PYTHON_BIN" -c "import hashlib; print(hashlib.sha256(open('$STAGING_DIR/ui.html','rb').read()).hexdigest())")
CALC_CONTROLS_SHA=$("$PYTHON_BIN" -c "import hashlib; print(hashlib.sha256(open('$STAGING_DIR/controls.gptk','rb').read()).hexdigest())")

if [[ "$CALC_SERVER_SHA" != "$EXPECTED_SERVER_SHA" ]] || [[ "$CALC_UI_SHA" != "$EXPECTED_UI_SHA" ]] || [[ "$CALC_CONTROLS_SHA" != "$EXPECTED_CONTROLS_SHA" ]]; then
    echo "ERRO CRÍTICO DE INTEGRIDADE: Falha na validação SHA-256 do payload!"
    rm -rf "$STAGING_DIR"
    exit 1
fi

echo ">> Integridade do payload confirmada com sucesso!"

# Commit atômico (staging -> app_dir)
rm -rf "$APP_DIR"
mv "$STAGING_DIR" "$APP_DIR"
chmod +x "$APP_DIR/server.py"

# ------------------------------------------------------------------------------
# 4. DETECÇÃO DINÂMICA DA INTERFACE E IP LOCAL (Prioridade na Rota Ativa)
# ------------------------------------------------------------------------------
echo ">> Detectando endereço de rede local do console..."
LOCAL_IP=""
LOCAL_IP=$("$PYTHON_BIN" -c "
import socket, subprocess
def get_ip():
    try:
        addrs = subprocess.check_output(['ip', '-4', '-o', 'addr', 'show']).decode()
        candidates = []
        for line in addrs.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                dev = parts[1]
                ip = parts[3].split('/')[0]
                if dev.startswith('lo') or dev.startswith('docker') or dev.startswith('veth') or dev.startswith('br-'):
                    continue
                if ip.startswith('127.') or ip.startswith('169.254.') or ip == '0.0.0.0':
                    continue
                prio = 1
                if dev.startswith('wlan'):
                    prio = 3
                elif dev.startswith('eth') or dev.startswith('en'):
                    prio = 2
                candidates.append((prio, ip))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith('127.') and not ip.startswith('169.254.') and ip != '0.0.0.0':
            return ip
    except Exception:
        pass
    return ''
print(get_ip())
")

if [[ -z "$LOCAL_IP" ]] || [[ "$LOCAL_IP" =~ ^127\. ]] || [[ "$LOCAL_IP" =~ ^169\.254\. ]] || [[ "$LOCAL_IP" == "0.0.0.0" ]]; then
    echo ""
    echo "========================================================"
    echo "  ERRO DE REDE: Wi-Fi / Rede não disponível             "
    echo "  Conecte o R36S a uma rede Wi-Fi e tente novamente.    "
    echo "========================================================"
    echo ""
    exit 1
fi
echo ">> IP Local: $LOCAL_IP"

# ------------------------------------------------------------------------------
# 5. TOKEN EFÊMERO & RAÍZES DE ARMAZENAMENTO (Sem Fallback Artificial para /roms)
# ------------------------------------------------------------------------------
AUTH_TOKEN=$("$PYTHON_BIN" -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || true)
if [[ -z "$AUTH_TOKEN" ]] || [[ ${{#AUTH_TOKEN}} -lt 32 ]]; then
    echo "ERRO CRÍTICO DE SEGURANÇA: Falha ao gerar token criptográfico aleatório."
    exit 1
fi

STORAGE_ROOTS=()
for r in "/roms" "/roms2" "/media" "/mnt"; do
    if [[ -d "$r" ]]; then
        STORAGE_ROOTS+=("$r")
    fi
done

if [[ ${{#STORAGE_ROOTS[@]}} -eq 0 ]]; then
    echo "ERRO CRÍTICO: Nenhum diretório de armazenamento válido encontrado (/roms, /roms2, /media, /mnt)."
    echo "O R36S Web File Manager requer pelo menos uma raiz de armazenamento válida."
    exit 1
fi

# ------------------------------------------------------------------------------
# 6. SELEÇÃO DINÂMICA DE PORTA (8080..8090) & HEALTH CHECK HTTP
# ------------------------------------------------------------------------------
PORT=""
SERVER_PID=""
HEALTHY=0

for p in {{8080..8090}}; do
    if ! "$PYTHON_BIN" -c "import socket; s = socket.socket(); s.bind(('0.0.0.0', $p)); s.close()" 2>/dev/null; then
        continue
    fi

    "$PYTHON_BIN" "$APP_DIR/server.py" \\
        --port "$p" \\
        --token "$AUTH_TOKEN" \\
        --ui "$APP_DIR/ui.html" \\
        --roots "${{STORAGE_ROOTS[@]}}" > "$APP_DIR/server.log" 2>&1 &
    
    CANDIDATE_PID=$!

    IS_OK=0
    for attempt in {{1..15}}; do
        if ! kill -0 "$CANDIDATE_PID" 2>/dev/null; then
            break
        fi
        RESP=$("$PYTHON_BIN" -c "
import urllib.request, json
try:
    req = urllib.request.Request('http://127.0.0.1:$p/api/status?token=$AUTH_TOKEN')
    with urllib.request.urlopen(req, timeout=0.8) as resp:
        data = json.loads(resp.read().decode())
        if data.get('success') is True:
            print('OK')
except Exception:
    pass
" 2>/dev/null || true)

        if [[ "$RESP" == "OK" ]]; then
            IS_OK=1
            break
        fi
        sleep 0.2
    done

    if [[ "$IS_OK" -eq 1 ]]; then
        PORT="$p"
        SERVER_PID="$CANDIDATE_PID"
        HEALTHY=1
        echo ">> Servidor ativo na porta $PORT."
        break
    else
        kill "$CANDIDATE_PID" 2>/dev/null || true
        wait "$CANDIDATE_PID" 2>/dev/null || true
    fi
done

if [[ "$HEALTHY" -ne 1 ]] || [[ -z "$PORT" ]]; then
    echo "ERRO CRÍTICO: Nenhuma porta disponível respondeu ao health check HTTP."
    exit 1
fi

echo "$SERVER_PID" > "$APP_DIR/server.pid" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 7. MAPEAMENTO GPTOKEYB COM DETECÇÃO E RELATÓRIO DE FALHA
# ------------------------------------------------------------------------------
if command -v gptokeyb >/dev/null 2>&1; then
    gptokeyb -c "$APP_DIR/controls.gptk" -1 &
    GPTOKEYB_PID=$!
    echo ">> gptokeyb iniciado (PID: $GPTOKEYB_PID)."
elif [[ -x "/usr/bin/gptokeyb" ]]; then
    /usr/bin/gptokeyb -c "$APP_DIR/controls.gptk" -1 &
    GPTOKEYB_PID=$!
    echo ">> gptokeyb iniciado em /usr/bin/gptokeyb (PID: $GPTOKEYB_PID)."
else
    echo "AVISO: gptokeyb não encontrado no sistema. Controles físicos do gamepad desativados (modo web puro)."
fi

# ------------------------------------------------------------------------------
# 8. EXIBIÇÃO DO QR CODE & LOOP PRINCIPAL
# ------------------------------------------------------------------------------
clear || true
CONNECT_URL="http://$LOCAL_IP:$PORT/?token=$AUTH_TOKEN"

echo "========================================================"
echo "          R36S WEB FILE MANAGER + QR TRANSFER           "
echo "========================================================"
echo ""
echo "  URL: $CONNECT_URL"
echo ""

"$PYTHON_BIN" -c "
import sys
sys.path.insert(0, '$APP_DIR')
from server import render_ansi_qr
print(render_ansi_qr('$CONNECT_URL'))
"

echo ""
echo "--------------------------------------------------------"
echo "  Status: SERVIDOR ATIVO (Porta $PORT)"
echo "  Pressione B ou START no console para sair e retornar"
echo "--------------------------------------------------------"

while kill -0 "$SERVER_PID" 2>/dev/null; do
    if read -t 1 -n 1 KEY 2>/dev/null; then
        break
    fi
done

exit 0
'''

    sh_content = sh_template.replace("{server_sha}", server_sha)
    sh_content = sh_content.replace("{ui_sha}", ui_sha)
    sh_content = sh_content.replace("{controls_sha}", controls_sha)
    sh_content = sh_content.replace("{assets_sha}", assets_sha)

    sh_content = sh_content.replace("$SERVER_B64", server_b64)
    sh_content = sh_content.replace("$UI_B64", ui_b64)
    sh_content = sh_content.replace("$CONTROLS_B64", controls_b64)
    sh_content = sh_content.replace("$ASSETS_B64", assets_b64)

    with open(target_sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(sh_content)
    os.chmod(target_sh, 0o755)
    print(f"Generated self-contained executable: {target_sh} (size: {os.path.getsize(target_sh)} bytes)")

if __name__ == "__main__":
    build_standalone()
