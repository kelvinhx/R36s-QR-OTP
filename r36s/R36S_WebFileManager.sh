#!/bin/bash
# ==============================================================================
# R36S Web File Manager + QR Transfer
# Dispositivo Alvo: R36S Físico (SoC Rockchip RK3326, dArkOS RE, Linux 4.4.189)
# Autocontido - Zero Dependência Manual Externa
# ==============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL_DIR="/roms/tools/.tools/R36S_WebFileManager"

# Se executado fora de /roms/tools durante testes locais, adapta o caminho
if [ ! -d "/roms/tools" ]; then
    TOOL_DIR="$SCRIPT_DIR/.tools/R36S_WebFileManager"
fi

PID_FILE="$TOOL_DIR/server.pid"
LOG_FILE="$TOOL_DIR/server.log"
GPTOKEYB_PID=""
SERVER_PID=""

# ------------------------------------------------------------------------------
# 1. Rotina de Limpeza e Encerramento Seguro (Respeitando PIDs Específicos)
# ------------------------------------------------------------------------------
cleanup() {
    # Evita reentrância
    trap - EXIT INT TERM

    echo ""
    echo "[R36S Web File Manager] Encerrando processos e liberando recursos..."

    # Encerra estritamente o servidor Python deste projeto
    if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        kill "$SERVER_PID" 2>/dev/null
        wait "$SERVER_PID" 2>/dev/null || true
    elif [ -f "$PID_FILE" ]; then
        PID_FROM_FILE=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$PID_FROM_FILE" ]; then
            kill "$PID_FROM_FILE" 2>/dev/null
        fi
    fi

    # REGRA DE ENGENHARIA #5: Encerra estritamente o PID do gptokeyb iniciado por este script
    if [ -n "$GPTOKEYB_PID" ] && kill -0 "$GPTOKEYB_PID" 2>/dev/null; then
        kill "$GPTOKEYB_PID" 2>/dev/null
    fi

    # Remove arquivos de controle
    rm -f "$PID_FILE" 2>/dev/null

    # Restaura o terminal TTY1 limpo para o EmulationStation
    if [ -w "/dev/tty1" ]; then
        reset >/dev/tty1 2>/dev/null || clear >/dev/tty1 2>/dev/null
    else
        clear 2>/dev/null || true
    fi

    exit 0
}

trap cleanup EXIT INT TERM

# ------------------------------------------------------------------------------
# 2. Verificação de Ambiente e Dependência em Runtime (Zero Instalação Externa)
# ------------------------------------------------------------------------------
# REGRA DE ENGENHARIA #1: Python 3 é detectado em runtime, sem apt ou internet
if ! command -v python3 >/dev/null 2>&1; then
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "R36S Web File Manager" \
               --msgbox "ERRO DE AMBIENTE:\n\nPython 3 não foi encontrado no dArkOS RE instalado.\nO sistema não realizará instalações automáticas pela Internet.\n\nOperação cancelada." 10 50
    else
        echo "========================================================="
        echo "ERRO DE AMBIENTE: Python 3 não encontrado no dArkOS RE."
        echo "Nenhuma instalação automática pela Internet será feita."
        echo "========================================================="
        sleep 5
    fi
    exit 1
fi

# ------------------------------------------------------------------------------
# 3. Preparação e Extração Autocontida dos Componentes Internos
# ------------------------------------------------------------------------------
mkdir -p "$TOOL_DIR" 2>/dev/null

# Extração de controls.gptk se não existir ou se atualizado
cat << 'EOF_GPTK' > "$TOOL_DIR/controls.gptk"
back = esc
start = enter
a = enter
b = esc
x = r
y = space
up = up
down = down
left = left
right = right
left_analog_up = up
left_analog_down = down
left_analog_left = left
left_analog_right = right
EOF_GPTK

# Extrai server.py e ui.html caso não estejam presentes na pasta interna
if [ -f "$SCRIPT_DIR/server.py" ]; then
    cp "$SCRIPT_DIR/server.py" "$TOOL_DIR/server.py"
fi
if [ -f "$SCRIPT_DIR/ui.html" ]; then
    cp "$SCRIPT_DIR/ui.html" "$TOOL_DIR/ui.html"
fi

chmod +x "$TOOL_DIR/server.py" 2>/dev/null || true

# ------------------------------------------------------------------------------
# 4. Detecção Dinâmica de Rede e IP Local
# ------------------------------------------------------------------------------
get_local_ip() {
    # Prioridade 1: hostname -I
    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
        echo "$IP"
        return 0
    fi

    # Prioridade 2: ip route
    IP=$(ip route get 1.1.1.1 2>/dev/null | awk -F"src " 'NR==1{split($2,a," ");print a[1]}')
    if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
        echo "$IP"
        return 0
    fi

    # Prioridade 3: ifconfig wlan0
    IP=$(ifconfig wlan0 2>/dev/null | grep -i "inet " | awk '{print $2}' | sed 's/addr://')
    if [ -n "$IP" ] && [ "$IP" != "127.0.0.1" ]; then
        echo "$IP"
        return 0
    fi

    echo ""
}

LOCAL_IP=$(get_local_ip)

if [ -z "$LOCAL_IP" ]; then
    if command -v dialog >/dev/null 2>&1; then
        dialog --title "R36S Web File Manager" \
               --msgbox "AVISO DE CONECTIVIDADE:\n\nNenhuma interface Wi-Fi ativa ou IP local detectado.\n\nVerifique o adaptador USB Wi-Fi ou a conexão de rede nas opções do dArkOS RE e tente novamente." 11 52
    else
        echo "========================================================="
        echo "AVISO: Wi-Fi não conectado ou sem IP atribuído."
        echo "Conecte o adaptador Wi-Fi e reconecte na rede local."
        echo "========================================================="
        sleep 5
    fi
    exit 1
fi

PORT=8080

# ------------------------------------------------------------------------------
# 5. Geração de Token Criptográfico Efêmero
# ------------------------------------------------------------------------------
TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
    TOKEN="r36s_$(date +%s)"
fi

SERVER_URL="http://${LOCAL_IP}:${PORT}/?token=${TOKEN}"

# ------------------------------------------------------------------------------
# 6. Inicialização do gptokeyb (Salvando PID Específico)
# ------------------------------------------------------------------------------
if command -v gptokeyb >/dev/null 2>&1; then
    gptokeyb -1 "R36S_WebFileManager" -c "$TOOL_DIR/controls.gptk" >/dev/null 2>&1 &
    GPTOKEYB_PID=$!
fi

# ------------------------------------------------------------------------------
# 7. Inicialização do Servidor HTTP Python em Background
# ------------------------------------------------------------------------------
cd "$TOOL_DIR" || exit 1
python3 "$TOOL_DIR/server.py" --port "$PORT" --token "$TOKEN" --ui "$TOOL_DIR/ui.html" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

# Aguarda 0.5s para confirmar que o socket abriu
sleep 0.5
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Falha ao iniciar servidor HTTP. Verifique $LOG_FILE"
    exit 1
fi

# ------------------------------------------------------------------------------
# 8. Loop de Interface do Console no Display 640x480 (/dev/tty1)
# ------------------------------------------------------------------------------
# Gera o QR Code via terminal
QR_RENDERED=$(python3 -c "import server; print(server.render_ansi_qr('${SERVER_URL}'))" 2>/dev/null)

render_console() {
    clear
    echo "================================================================================"
    echo "                          R36S WEB FILE MANAGER + QR                            "
    echo "================================================================================"
    echo " IP LOCAL : http://${LOCAL_IP}:${PORT}"
    echo " STATUS   : ONLINE (Serviço ativo na rede local)"
    echo " SESSÃO   : Autenticada via Token Efêmero"
    echo "--------------------------------------------------------------------------------"
    echo ""
    echo "$QR_RENDERED"
    echo ""
    echo "--------------------------------------------------------------------------------"
    echo " Conecte o celular na mesma rede Wi-Fi e escaneie o QR Code acima."
    echo " [A] Recarregar Status/IP    |    [B] Encerrar Servidor e Sair"
    echo "================================================================================"
}

# Redireciona a renderização para /dev/tty1 se disponível (comportamento nativo do dArkOS)
if [ -w "/dev/tty1" ]; then
    render_console >/dev/tty1
else
    render_console
fi

# Monitora teclas e estado do servidor
while kill -0 "$SERVER_PID" 2>/dev/null; do
    # Leitura não-bloqueante de 1 tecla com timeout de 2 segundos
    if read -t 2 -n 1 KEY 2>/dev/null; then
        case "$KEY" in
            q|Q|$'\e')
                # Botão [B] ou ESC/Q: Sair
                break
                ;;
            r|R|$'\n')
                # Botão [A] ou ENTER: Recarregar tela
                render_console >/dev/tty1 2>/dev/null || render_console
                ;;
        esac
    fi
done

# Ao sair do loop (ou se o servidor foi morto remotamente pela web), executa cleanup
cleanup
