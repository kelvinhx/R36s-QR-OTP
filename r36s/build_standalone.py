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

# Garante permissão de execução
chmod +x "$0" 2>/dev/null || true

# Redirecionamento de TTY para inicialização via EmulationStation
if [[ -e "/dev/tty1" ]] && [[ ! -t 0 ]]; then
    exec < /dev/tty1 > /dev/tty1 2>&1
fi
export TERM=linux
printf "\\033[?25l" 2>/dev/null || true

# Manifesto de integridade SHA-256 do payload
EXPECTED_SERVER_SHA="{server_sha}"
EXPECTED_UI_SHA="{ui_sha}"
EXPECTED_CONTROLS_SHA="{controls_sha}"
EXPECTED_ASSETS_SHA="{assets_sha}"

# ------------------------------------------------------------------------------
# 1. TRAP & LIMPEZA DE PROCESSOS (Gerenciamento Exclusivo por PID - Idempotente)
# ------------------------------------------------------------------------------
CLEANUP_DONE=0
cleanup() {{
    if [[ "$CLEANUP_DONE" -eq 1 ]]; then
        return 0
    fi
    CLEANUP_DONE=1
    printf "\\033[?25h" 2>/dev/null || true
    echo ""
    echo ">> Encerrando serviços do R36S Web File Manager..."

    # 1. Finalizar watchdog remoto
    if [[ -n "${{WATCHDOG_PID:-}}" ]] && kill -0 "$WATCHDOG_PID" 2>/dev/null; then
        kill "$WATCHDOG_PID" 2>/dev/null || true
    fi

    # 2. Encerrar servidor Python do próprio aplicativo (por PID exclusivo)
    if [[ -n "${{SERVER_PID:-}}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill -TERM "$SERVER_PID" 2>/dev/null || true
        for _ in {{1..15}}; do
            if ! kill -0 "$SERVER_PID" 2>/dev/null; then
                break
            fi
            sleep 0.1
        done
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            kill -9 "$SERVER_PID" 2>/dev/null || true
        fi
    fi

    # 3. Encerrar gptokeyb associado ao aplicativo (por PID exclusivo)
    if [[ -n "${{GPTOKEYB_PID:-}}" ]] && kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
        kill -TERM "$GPTOKEYB_PID" 2>/dev/null || true
        for _ in {{1..10}}; do
            if ! kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
                break
            fi
            sleep 0.1
        done
        if kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
            kill -9 "$GPTOKEYB_PID" 2>/dev/null || true
        fi
    fi

    rm -f "${{APP_DIR:-}}/server.pid" 2>/dev/null || true

    echo ">> Servidor encerrado. Retornando ao EmulationStation..."
    sleep 0.5
    clear 2>/dev/null || true
}}

trap cleanup EXIT INT TERM HUP

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
echo "$ASSETS_B64" | "$PYTHON_BIN" -c "
import sys, base64, zipfile, io
b64_data = sys.stdin.read().strip()
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
CALC_ASSETS_SHA=""
if [[ -n "$EXPECTED_ASSETS_SHA" ]] && [[ -n "$ASSETS_B64" ]]; then
    CALC_ASSETS_SHA=$(echo "$ASSETS_B64" | "$PYTHON_BIN" -c "
import sys, base64, hashlib
b64 = sys.stdin.read().strip()
print(hashlib.sha256(base64.b64decode(b64)).hexdigest() if b64 else '')
")
fi

if [[ "$CALC_SERVER_SHA" != "$EXPECTED_SERVER_SHA" ]] || [[ "$CALC_UI_SHA" != "$EXPECTED_UI_SHA" ]] || [[ "$CALC_CONTROLS_SHA" != "$EXPECTED_CONTROLS_SHA" ]] || ([[ -n "$EXPECTED_ASSETS_SHA" ]] && [[ "$CALC_ASSETS_SHA" != "$EXPECTED_ASSETS_SHA" ]]); then
    echo "ERRO CRÍTICO DE INTEGRIDADE: Falha na validação SHA-256 do payload!"
    rm -rf "$STAGING_DIR"
    exit 1
fi

echo ">> Integridade do payload confirmada com sucesso!"

# Commit atômico (staging -> app_dir)
rm -rf "$APP_DIR"
mv "$STAGING_DIR" "$APP_DIR"
chmod +x "$APP_DIR/server.py"

## ------------------------------------------------------------------------------
# 4. DETECÇÃO DINÂMICA DA INTERFACE E IP LOCAL (Sem tráfego externo para 8.8.8.8)
# ------------------------------------------------------------------------------
echo ">> Detectando endereço de rede local do console..."
LOCAL_IP=""
if [[ -n "${{TEST_OVERRIDE_IP:-}}" ]]; then
    LOCAL_IP="$TEST_OVERRIDE_IP"
else
    LOCAL_IP=$("$PYTHON_BIN" -c "
import sys
sys.path.insert(0, '$APP_DIR')
from server import get_ip
print(get_ip())
" 2>/dev/null || true)
fi

if [[ -z "${{TEST_OVERRIDE_IP:-}}" ]] && ([[ -z "$LOCAL_IP" ]] || [[ "$LOCAL_IP" =~ ^127\. ]] || [[ "$LOCAL_IP" =~ ^169\.254\. ]] || [[ "$LOCAL_IP" == "0.0.0.0" ]]); then
    echo ""
    echo "========================================================"
    echo "  AVISO: Wi-Fi / Rede não disponível                    "
    echo "========================================================"
    echo "  O console R36S não possui um endereço IP local ativo. "
    echo "  Conecte o R36S ao Wi-Fi nas configurações do sistema  "
    echo "  e execute o aplicativo novamente.                     "
    echo "========================================================"
    echo ""
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "Wi-Fi Nao Conectado" \
               --msgbox "O R36S nao possui um IP local ativo.\n\nConecte o console ao Wi-Fi nas opcoes de rede do EmulationStation e execute o aplicativo novamente." 10 60
    else
        read -t 4 -p "Pressione qualquer tecla para voltar ao EmulationStation..." || true
    fi
    exit 0
fi
echo ">> IP Local: $LOCAL_IP"

# ------------------------------------------------------------------------------
# 5. TOKEN EFÊMERO & RAÍZES DE ARMAZENAMENTO DINÂMICAS
# ------------------------------------------------------------------------------
AUTH_TOKEN=$("$PYTHON_BIN" -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || true)
if [[ -z "$AUTH_TOKEN" ]] || [[ ${{#AUTH_TOKEN}} -lt 32 ]]; then
    echo "ERRO CRÍTICO DE SEGURANÇA: Falha ao gerar token criptográfico aleatório."
    exit 1
fi

STORAGE_ROOTS=()
if [[ -n "${{TEST_OVERRIDE_ROOTS:-}}" ]]; then
    for r in $TEST_OVERRIDE_ROOTS; do
        if [[ -d "$r" ]]; then
            STORAGE_ROOTS+=("$r")
        fi
    done
else
    for r in "/roms" "/roms2" "/media" "/mnt"; do
        if [[ -d "$r" ]]; then
            STORAGE_ROOTS+=("$r")
        fi
    done
fi

if [[ ${{#STORAGE_ROOTS[@]}} -eq 0 ]]; then
    echo "AVISO: Nenhum diretório de armazenamento válido encontrado (/roms, /roms2, /media, /mnt)."
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "Armazenamento Indisponivel" \
               --msgbox "Nenhum diretorio de armazenamento padrao (/roms, /roms2, /media, /mnt) foi encontrado no console." 8 60
    else
        read -t 4 -p "Pressione qualquer tecla para retornar ao EmulationStation..." || true
    fi
    exit 0
fi

# ------------------------------------------------------------------------------
# 6. SELEÇÃO DINÂMICA DE PORTA (8080..8090) & HEALTH CHECK HTTP REAL
# ------------------------------------------------------------------------------
PORT=""
SERVER_PID=""
HEALTHY=0

for p in {{8080..8090}}; do
    if ! "$PYTHON_BIN" -c "import socket; s = socket.socket(); s.bind(('0.0.0.0', $p)); s.close()" 2>/dev/null; then
        continue
    fi

    "$PYTHON_BIN" "$APP_DIR/server.py" \
        --port "$p" \
        --token "$AUTH_TOKEN" \
        --ui "$APP_DIR/ui.html" \
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
echo "$PORT" > "$APP_DIR/server.port" 2>/dev/null || true
echo "$AUTH_TOKEN" > "$APP_DIR/server.token" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 7. MAPEAMENTO GPTOKEYB & WATCHDOG DE SHUTDOWN REMOTO
# ------------------------------------------------------------------------------
find_gptokeyb() {{
    if command -v gptokeyb >/dev/null 2>&1; then
        command -v gptokeyb
        return 0
    fi
    for path in "/opt/inttools/gptokeyb" "/usr/bin/gptokeyb" "/opt/gptokeyb/gptokeyb" "/usr/local/bin/gptokeyb"; do
        if [[ -x "$path" ]]; then
            echo "$path"
            return 0
        fi
    done
    return 1
}}

GPTOKEYB_BIN="$(find_gptokeyb || true)"
GPTOKEYB_PID=""

# Watchdog em segundo plano: se o servidor terminar remotamente via /api/shutdown,
# o script principal é notificado para executar o cleanup e retornar ao EmulationStation.
(
    while kill -0 "$SERVER_PID" 2>/dev/null; do
        sleep 1
    done
    kill -INT "$$" 2>/dev/null || true
) 2>/dev/null &
WATCHDOG_PID=$!

if command -v dialog >/dev/null 2>&1; then
    if [[ -n "$GPTOKEYB_BIN" ]]; then
        "$GPTOKEYB_BIN" "dialog" -c "$APP_DIR/controls.gptk" &
        GPTOKEYB_PID=$!
        echo ">> gptokeyb iniciado para dialog ($GPTOKEYB_BIN, PID: $GPTOKEYB_PID)."
    else
        echo "AVISO: gptokeyb nao encontrado nos caminhos padroes (/opt/inttools, /usr/bin). Gamepad desativado."
    fi

    CONNECT_URL="http://$LOCAL_IP:$PORT/?token=$AUTH_TOKEN"

    while kill -0 "$SERVER_PID" 2>/dev/null; do
        CHOICE=$(dialog --backtitle "R36S Web File Manager (dArkOS RE)" \
            --title "PAINEL DE CONTROLE" \
            --cancel-label "Sair" \
            --menu "Servidor ativo em:\n$CONNECT_URL\n\nEscolha uma opcao:" 15 65 4 \
            1 "Mostrar QR Code (Conectar)" \
            2 "Status de Rede e Armazenamento" \
            3 "Visualizar Logs do Servidor" \
            4 "Desligar e Retornar ao EmulationStation" \
            3>&1 1>&2 2>&3 || echo "EXIT")

        if [[ "$CHOICE" == "EXIT" ]] || [[ "$CHOICE" == "4" ]]; then
            if dialog --title "Sair" --yesno "Deseja realmente parar o servidor web e retornar ao EmulationStation?" 8 50; then
                break
            fi
        elif [[ "$CHOICE" == "1" ]]; then
            clear
            echo "=== R36S WEB FILE MANAGER: ESCANEE PARA CONECTAR ==="
            echo "  URL: $CONNECT_URL"
            "$PYTHON_BIN" -c "
import sys
sys.path.insert(0, '$APP_DIR')
from server import render_ansi_qr
print(render_ansi_qr('$CONNECT_URL'))
"
            echo "  [ Pressione qualquer tecla ou Botao B para voltar ]"
            read -n 1 -s -r
        elif [[ "$CHOICE" == "2" ]]; then
            ROOTS_STR=""
            for r in "${{STORAGE_ROOTS[@]}}"; do
                ROOTS_STR="$ROOTS_STR  - $r\n"
            done
            dialog --title "Rede e Armazenamento" \
                --msgbox "IP Local: $LOCAL_IP\nPorta: $PORT\nToken: $AUTH_TOKEN\n\nDiretorios de Armazenamento:\n$ROOTS_STR" 15 60
        elif [[ "$CHOICE" == "3" ]]; then
            dialog --title "Logs do Servidor (server.log)" \
                --textbox "$APP_DIR/server.log" 20 70
        fi
    done
else
    # Fallback caso dialog não esteja instalado
    echo "AVISO: dialog nao encontrado. Iniciando em modo CLI de compatibilidade."
    if [[ -n "$GPTOKEYB_BIN" ]]; then
        "$GPTOKEYB_BIN" -c "$APP_DIR/controls.gptk" -1 &
        GPTOKEYB_PID=$!
        echo ">> gptokeyb iniciado em modo console ($GPTOKEYB_BIN, PID: $GPTOKEYB_PID)."
    fi

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
fi

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
