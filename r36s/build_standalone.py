#!/usr/bin/env python3
"""
Build script to pack server.py, ui.html, controls.gptk, and assets/ into a single,
completely self-contained R36S_WebFileManager.sh executable.
"""

import os
import base64
import zipfile
import tempfile

def build_standalone():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_py = os.path.join(base_dir, "server.py")
    ui_html = os.path.join(base_dir, "ui.html")
    controls_gptk = os.path.join(base_dir, "controls.gptk")
    assets_dir = os.path.join(base_dir, "assets")
    target_sh = os.path.join(base_dir, "R36S_WebFileManager.sh")

    with open(server_py, "rb") as f:
        server_b64 = base64.b64encode(f.read()).decode("ascii")

    with open(ui_html, "rb") as f:
        ui_b64 = base64.b64encode(f.read()).decode("ascii")

    with open(controls_gptk, "rb") as f:
        controls_b64 = base64.b64encode(f.read()).decode("ascii")

    # Pack assets dir into a zip in memory
    assets_b64 = ""
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
                assets_b64 = base64.b64encode(f.read()).decode("ascii")
        finally:
            if os.path.exists(tmp_zip_name):
                os.remove(tmp_zip_name)

    sh_template = f'''#!/usr/bin/env bash
# ==============================================================================
# R36S Web File Manager + QR Transfer (Autocontido)
# Desenvolvido para R36S físico com dArkOS RE (Debian 12 Bookworm, Kernel 4.4.189)
#
# Produto 100% autocontido: não depende de nenhum arquivo externo.
# Pode ser colocado diretamente em /roms/tools/ e iniciado pelo EmulationStation.
# ==============================================================================

set -eo pipefail

# ------------------------------------------------------------------------------
# 1. TRAP & LIMPEZA DE PROCESSOS (Encerramento Limpo Garantido)
# ------------------------------------------------------------------------------
cleanup() {{
    # Restaurar cursor e limpar terminal
    printf "\\033[?25h" || true
    echo ""
    echo ">> Encerrando serviços do R36S Web File Manager..."

    if [[ -n "${{SERVER_PID:-}}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi

    if [[ -n "${{GPTOKEYB_PID:-}}" ]] && kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
        kill "$GPTOKEYB_PID" 2>/dev/null || true
    fi
    killall -9 gptokeyb 2>/dev/null || true

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
    echo "O dArkOS RE requer o runtime padrão do Python 3."
    echo "Pressione qualquer tecla ou aguarde para sair..."
    read -t 5 -n 1 || true
    exit 1
fi

echo ">> Python 3 detectado: $PYTHON_BIN"

# ------------------------------------------------------------------------------
# 3. EXTRAÇÃO DOS COMPONENTES AUTOCONTIDOS (Zero Dependências Externas)
# ------------------------------------------------------------------------------
# Determina diretório de instalação dos utilitários
if [[ -d "/roms/tools" ]] && [[ -w "/roms/tools" ]]; then
    APP_DIR="/roms/tools/.tools/R36S_WebFileManager"
else
    # Fallback para teste em qualquer outro diretório
    SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    APP_DIR="$SCRIPT_DIR/.tools/R36S_WebFileManager"
fi

mkdir -p "$APP_DIR/assets"
echo ">> Preparando arquivos da aplicação em $APP_DIR..."

# Extrair server.py
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/server.py', 'wb').write(base64.b64decode('$SERVER_B64'))"
# Extrair ui.html
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/ui.html', 'wb').write(base64.b64decode('$UI_B64'))"
# Extrair controls.gptk
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/controls.gptk', 'wb').write(base64.b64decode('$CONTROLS_B64'))"
# Extrair assets zip
"$PYTHON_BIN" -c "
import base64, zipfile, io
b64_data = '$ASSETS_B64'
if b64_data:
    try:
        data = base64.b64decode(b64_data)
        zf = zipfile.ZipFile(io.BytesIO(data))
        zf.extractall('$APP_DIR/assets')
    except Exception as e:
        print('Warning extracting assets:', e)
"

chmod +x "$APP_DIR/server.py"

# ------------------------------------------------------------------------------
# 4. DETECÇÃO DINÂMICA DO IP LOCAL (Offline-first, sem ping externo 1.1.1.1)
# ------------------------------------------------------------------------------
echo ">> Detectando endereço de rede local do console..."
LOCAL_IP=""

# Método 1: Rota padrão da rede local
LOCAL_IP=$("$PYTHON_BIN" -c "
import socket, subprocess
ip = ''
try:
    routes = subprocess.check_output(['ip', 'route', 'show']).decode()
    for line in routes.splitlines():
        if line.startswith('default'):
            parts = line.split()
            if 'dev' in parts:
                dev = parts[parts.index('dev') + 1]
                addrs = subprocess.check_output(['ip', '-4', '-o', 'addr', 'show', dev]).decode()
                for a in addrs.splitlines():
                    ip = a.split()[3].split('/')[0]
                    break
            if ip:
                break
except Exception:
    pass

if not ip:
    try:
        addrs = subprocess.check_output(['ip', '-4', '-o', 'addr', 'show']).decode()
        for a in addrs.splitlines():
            dev = a.split()[1]
            if not dev.startswith('lo') and not dev.startswith('docker') and not dev.startswith('veth'):
                ip = a.split()[3].split('/')[0]
                break
    except Exception:
        pass

print(ip)
")

if [[ -z "$LOCAL_IP" ]]; then
    echo "AVISO: Não foi possível detectar IP de rede local Wi-Fi ativa."
    echo "Verifique se o adaptador Wi-Fi USB do R36S está conectado."
    LOCAL_IP="127.0.0.1"
fi

echo ">> IP Local: $LOCAL_IP"

# ------------------------------------------------------------------------------
# 5. GERAÇÃO DO TOKEN CRIPTOGRÁFICO EFÊMERO (Zero Fallback Previsível)
# ------------------------------------------------------------------------------
AUTH_TOKEN=$("$PYTHON_BIN" -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || true)
if [[ -z "$AUTH_TOKEN" ]] || [[ ${{#AUTH_TOKEN}} -lt 32 ]]; then
    echo "ERRO CRÍTICO DE SEGURANÇA: Falha ao gerar token criptográfico aleatório."
    echo "O dArkOS RE requer gerador seguro (secrets.token_hex). Abortando."
    exit 1
fi

# ------------------------------------------------------------------------------
# 6. SELEÇÃO DINÂMICA DE PORTA (8080..8090) & INICIALIZAÇÃO COM HEALTH CHECK REAL
# ------------------------------------------------------------------------------
echo ">> Alocando porta dinâmica de serviço (8080-8090) e validando HTTP..."

# Identificar raízes válidas no R36S
STORAGE_ROOTS=()
for r in "/roms" "/roms2" "/media" "/mnt"; do
    if [[ -d "$r" ]]; then
        STORAGE_ROOTS+=("$r")
    fi
done

if [[ ${{#STORAGE_ROOTS[@]}} -eq 0 ]]; then
    STORAGE_ROOTS=("/roms")
fi

PORT=""
SERVER_PID=""
HEALTHY=0

for p in {{8080..8090}}; do
    # 1. Checa disponibilidade preliminar de socket
    if ! "$PYTHON_BIN" -c "import socket; s = socket.socket(); s.bind(('0.0.0.0', $p)); s.close()" 2>/dev/null; then
        echo "   [Porta $p em uso, testando próxima...]"
        continue
    fi

    # 2. Inicia servidor na porta candidata
    "$PYTHON_BIN" "$APP_DIR/server.py" \\
        --port "$p" \\
        --token "$AUTH_TOKEN" \\
        --ui "$APP_DIR/ui.html" \\
        --roots "${{STORAGE_ROOTS[@]}}" > "$APP_DIR/server.log" 2>&1 &
    
    CANDIDATE_PID=$!

    # 3. Health check HTTP real via GET /api/status?token=...
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

    # 4. Avaliação do health check
    if [[ "$IS_OK" -eq 1 ]]; then
        PORT="$p"
        SERVER_PID="$CANDIDATE_PID"
        HEALTHY=1
        echo ">> Servidor ativo e verificado com sucesso via HTTP na porta $PORT."
        break
    else
        kill "$CANDIDATE_PID" 2>/dev/null || true
        wait "$CANDIDATE_PID" 2>/dev/null || true
    fi
done

if [[ "$HEALTHY" -ne 1 ]] || [[ -z "$PORT" ]]; then
    echo "ERRO CRÍTICO: Nenhuma porta disponível na faixa 8080-8090 respondeu ao health check HTTP."
    if [[ -f "$APP_DIR/server.log" ]]; then
        echo "Últimas linhas do log do servidor:"
        tail -n 15 "$APP_DIR/server.log"
    fi
    exit 1
fi

echo "$SERVER_PID" > "$APP_DIR/server.pid" 2>/dev/null || true
echo ">> Servidor ONLINE e verificado com sucesso!"

# ------------------------------------------------------------------------------
# 8. MAPEAMENTO DE CONTROLES GPTOKEYB (dArkOS RE)
# ------------------------------------------------------------------------------
if command -v gptokeyb >/dev/null 2>&1; then
    gptokeyb -c "$APP_DIR/controls.gptk" -1 &
    GPTOKEYB_PID=$!
elif [[ -x "/usr/bin/gptokeyb" ]]; then
    /usr/bin/gptokeyb -c "$APP_DIR/controls.gptk" -1 &
    GPTOKEYB_PID=$!
fi

# ------------------------------------------------------------------------------
# 9. EXIBIÇÃO DO QR CODE & INSTRUÇÕES NA TELA DO R36S (640x480)
# ------------------------------------------------------------------------------
clear || true
CONNECT_URL="http://$LOCAL_IP:$PORT/?token=$AUTH_TOKEN"

echo "========================================================"
echo "          R36S WEB FILE MANAGER + QR TRANSFER           "
echo "========================================================"
echo ""
echo "  Escaneie o QR Code abaixo com a câmera do seu celular"
echo "  ou acesse o link no navegador do seu computador/PC:"
echo ""
echo "  URL: $CONNECT_URL"
echo ""

# Renderizar QR Code no console usando o gerador interno de alta precisão
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

# ------------------------------------------------------------------------------
# 10. LOOP PRINCIPAL DE AGUARDO DE TECLA OU ENCERRAMENTO REMOTO
# ------------------------------------------------------------------------------
while kill -0 "$SERVER_PID" 2>/dev/null; do
    # Ler tecla com timeout de 1s para responder a shutdown remoto via web
    if read -t 1 -n 1 KEY 2>/dev/null; then
        # Tecla pressionada (ESC, q, Enter, etc)
        break
    fi
done

exit 0
'''

    # Replace placeholders
    sh_content = sh_template.replace("$SERVER_B64", server_b64)
    sh_content = sh_content.replace("$UI_B64", ui_b64)
    sh_content = sh_content.replace("$CONTROLS_B64", controls_b64)
    sh_content = sh_content.replace("$ASSETS_B64", assets_b64)

    with open(target_sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(sh_content)
    os.chmod(target_sh, 0o755)
    print(f"Generated self-contained executable: {target_sh} (size: {os.path.getsize(target_sh)} bytes)")

if __name__ == "__main__":
    build_standalone()
