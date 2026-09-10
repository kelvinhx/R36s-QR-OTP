#!/usr/bin/env python3
"""
Build script to pack server.py, ui.html, and controls.gptk into a single,
completely self-contained R36S_WebFileManager.sh executable.
"""

import os
import base64

def build_standalone():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    server_py = os.path.join(base_dir, "server.py")
    ui_html = os.path.join(base_dir, "ui.html")
    controls_gptk = os.path.join(base_dir, "controls.gptk")
    target_sh = os.path.join(base_dir, "R36S_WebFileManager.sh")

    with open(server_py, "rb") as f:
        server_b64 = base64.b64encode(f.read()).decode("ascii")

    with open(ui_html, "rb") as f:
        ui_b64 = base64.b64encode(f.read()).decode("ascii")

    with open(controls_gptk, "rb") as f:
        controls_b64 = base64.b64encode(f.read()).decode("ascii")

    sh_template = f'''#!/usr/bin/env bash
# ==============================================================================
# R36S Web File Manager + QR Transfer (Autocontido)
# Desenvolvido para R36S fisico com dArkOS RE (Debian 12 Bookworm, Kernel 4.4.189)
#
# Produto 100% autocontido: nao depende de nenhum arquivo externo.
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
    echo ">> Encerrando servicos do R36S Web File Manager..."

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
# 2. VERIFICACAO DE AMBIENTE & PYTHON 3 RUNTIME
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
    echo "ERRO CRITICO: Python 3 nao foi detectado no sistema."
    echo "O dArkOS RE requer o runtime padrao do Python 3."
    echo "Pressione qualquer tecla ou aguarde para sair..."
    read -t 5 -n 1 || true
    exit 1
fi

echo ">> Python 3 detectado: $PYTHON_BIN"

# ------------------------------------------------------------------------------
# 3. EXTRAÇÃO DOS COMPONENTES AUTOCONTIDOS (Zero Dependências Externas)
# ------------------------------------------------------------------------------
# Determina diretorio de instalacao dos utilitarios
if [[ -d "/roms/tools" ]] && [[ -w "/roms/tools" ]]; then
    APP_DIR="/roms/tools/.tools/R36S_WebFileManager"
else
    # Fallback para teste em qualquer outro diretorio
    SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
    APP_DIR="$SCRIPT_DIR/.tools/R36S_WebFileManager"
fi

mkdir -p "$APP_DIR"

echo ">> Preparando arquivos da aplicacao em $APP_DIR..."

# Extrair server.py
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/server.py', 'wb').write(base64.b64decode('$SERVER_B64'))"
# Extrair ui.html
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/ui.html', 'wb').write(base64.b64decode('$UI_B64'))"
# Extrair controls.gptk
"$PYTHON_BIN" -c "import base64; open('$APP_DIR/controls.gptk', 'wb').write(base64.b64decode('$CONTROLS_B64'))"

chmod +x "$APP_DIR/server.py"

# ------------------------------------------------------------------------------
# 4. DETECCAO DINAMICA DO IP LOCAL (Offline-first, sem ping externo 1.1.1.1)
# ------------------------------------------------------------------------------
echo ">> Detectando endereco de rede local do console..."

LOCAL_IP=""
# Metodo 1: Rota padrao da rede local
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
    echo "AVISO: Nao foi possivel detectar IP de rede local Wi-Fi ativa."
    echo "Verifique se o adaptador Wi-Fi USB do R36S esta conectado."
    LOCAL_IP="127.0.0.1"
fi

echo ">> IP Local: $LOCAL_IP"

# ------------------------------------------------------------------------------
# 5. SELECAO DINAMICA DE PORTA LIVRE (8080..8090)
# ------------------------------------------------------------------------------
PORT=""
for p in {{8080..8090}}; do
    if ! "$PYTHON_BIN" -c "import socket; s = socket.socket(); s.bind(('0.0.0.0', $p)); s.close()" 2>/dev/null; then
        continue
    fi
    PORT="$p"
    break
done

if [[ -z "$PORT" ]]; then
    echo "ERRO: Nenhuma porta disponivel na faixa 8080-8090."
    exit 1
fi

echo ">> Porta de servico selecionada: $PORT"

# ------------------------------------------------------------------------------
# 6. GERACAO DO TOKEN EFEMERO DE AUTENTICACAO
# ------------------------------------------------------------------------------
AUTH_TOKEN=$("$PYTHON_BIN" -c "import secrets; print(secrets.token_hex(16))")

# ------------------------------------------------------------------------------
# 7. INICIALIZACAO DO BACKEND & HEALTH CHECK HTTP REAL
# ------------------------------------------------------------------------------
echo ">> Iniciando servidor web..."

# Identificar raizes validas no R36S
STORAGE_ROOTS=()
for r in "/roms" "/roms2" "/media" "/mnt"; do
    if [[ -d "$r" ]]; then
        STORAGE_ROOTS+=("$r")
    fi
done

if [[ ${{#STORAGE_ROOTS[@]}} -eq 0 ]]; then
    STORAGE_ROOTS=("/roms")
fi

"$PYTHON_BIN" "$APP_DIR/server.py" \\
    --port "$PORT" \\
    --token "$AUTH_TOKEN" \\
    --ui "$APP_DIR/ui.html" \\
    --roots "${{STORAGE_ROOTS[@]}}" > "$APP_DIR/server.log" 2>&1 &
SERVER_PID=$!

echo ">> Aguardando inicializacao e confirmacao HTTP..."

# Health check real via HTTP GET /api/status com o token
HEALTHY=0
for i in {{1..15}}; do
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        RESP=$("$PYTHON_BIN" -c "
import urllib.request, json
try:
    req = urllib.request.Request('http://127.0.0.1:$PORT/api/status?token=$AUTH_TOKEN')
    with urllib.request.urlopen(req, timeout=1) as resp:
        data = json.loads(resp.read().decode())
        if data.get('success') is True:
            print('OK')
except Exception:
    pass
" 2>/dev/null || true)

        if [[ "$RESP" == "OK" ]]; then
            HEALTHY=1
            break
        fi
    else
        break
    fi
    sleep 0.3
done

if [[ "$HEALTHY" -ne 1 ]]; then
    echo "ERRO: Falha ao iniciar servidor HTTP na porta $PORT."
    if [[ -f "$APP_DIR/server.log" ]]; then
        echo "Log do servidor:"
        tail -n 10 "$APP_DIR/server.log"
    fi
    exit 1
fi

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
# 9. EXIBICAO DO QR CODE & INSTRUCOES NA TELA DO R36S (640x480)
# ------------------------------------------------------------------------------
clear || true
CONNECT_URL="http://$LOCAL_IP:$PORT/?token=$AUTH_TOKEN"

echo "========================================================"
echo "          R36S WEB FILE MANAGER + QR TRANSFER           "
echo "========================================================"
echo ""
echo "  Escaneie o QR Code abaixo com a camera do seu celular"
echo "  ou acesse o link no navegador do seu computador/PC:"
echo ""
echo "  URL: $CONNECT_URL"
echo ""

# Renderizar QR Code no console usando o gerador interno de alta precisao
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

    with open(target_sh, "w", encoding="utf-8", newline="\n") as f:
        f.write(sh_content)

    os.chmod(target_sh, 0o755)
    print(f"Generated self-contained executable: {target_sh} (size: {os.path.getsize(target_sh)} bytes)")

if __name__ == "__main__":
    build_standalone()
