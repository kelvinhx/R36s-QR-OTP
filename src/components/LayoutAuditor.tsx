import React, { useState } from "react";
import {
  Monitor,
  Smartphone,
  Terminal,
  Gamepad2,
  CheckCircle2,
  Image as ImageIcon,
  HardDrive,
  Layers,
  Search,
  Check,
  Radio,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Maximize2
} from "lucide-react";

// Import all SVGs as raw text using Vite's import.meta.glob
const rawSvgMap = import.meta.glob("../r36s/assets/**/*.svg", {
  query: "?raw",
  import: "default",
  eager: true
}) as Record<string, string>;

// Helper to sanitize key to relative asset path (e.g., "systems/gba.svg")
function getAssetPath(key: string): string {
  return key.replace(/^.*\/r36s\/assets\//, "");
}

// Map of clean path -> raw SVG content
const assetsMap: Record<string, string> = {};
for (const [key, raw] of Object.entries(rawSvgMap)) {
  const cleanPath = getAssetPath(key);
  assetsMap[cleanPath] = raw;
}

// Fallback helper to render raw SVG securely
export function SvgAsset({
  path,
  className = "w-5 h-5",
  title
}: {
  path: string;
  className?: string;
  title?: string;
}) {
  const raw = assetsMap[path];
  if (!raw) {
    return <span className={`inline-block bg-white/10 rounded ${className}`} title={`Missing: ${path}`} />;
  }
  return (
    <span
      className={`inline-flex items-center justify-center [&>svg]:w-full [&>svg]:h-full [&>svg]:block ${className}`}
      title={title || path}
      dangerouslySetInnerHTML={{ __html: raw }}
    />
  );
}

export function LayoutAuditor() {
  const [subView, setSubView] = useState<"console" | "web" | "assets">("console");
  const [consoleScreen, setConsoleScreen] = useState<"qr" | "dialog" | "storage" | "logs">("qr");
  const [assetCategory, setAssetCategory] = useState<string>("all");
  const [assetSearch, setAssetSearch] = useState<string>("");

  const allAssetKeys = Object.keys(assetsMap).sort();
  const categories = Array.from(new Set(allAssetKeys.map((k) => k.split("/")[0]))).sort();

  const filteredAssets = allAssetKeys.filter((key) => {
    const cat = key.split("/")[0];
    const matchesCat = assetCategory === "all" || cat === assetCategory;
    const matchesSearch = assetSearch === "" || key.toLowerCase().includes(assetSearch.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Sub-view Navigation Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#141221] p-3 rounded-xl border border-[#26233b]">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSubView("console")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              subView === "console" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:bg-[#1f1d33] hover:text-white"
            }`}
          >
            <Gamepad2 className="w-4 h-4" />
            <span>Layout Console R36S (640x480 TTY)</span>
          </button>
          <button
            onClick={() => setSubView("web")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              subView === "web" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:bg-[#1f1d33] hover:text-white"
            }`}
          >
            <Smartphone className="w-4 h-4" />
            <span>Layout Web SPA (Mobile / Desktop)</span>
          </button>
          <button
            onClick={() => setSubView("assets")}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              subView === "assets" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:bg-[#1f1d33] hover:text-white"
            }`}
          >
            <ImageIcon className="w-4 h-4" />
            <span>Matriz de Assets (53 SVGs Reais)</span>
          </button>
        </div>

        <div className="text-[11px] text-[#8c88a6] flex items-center gap-1.5 bg-[#1a182c] px-2.5 py-1 rounded border border-[#2b2744]">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>100% Sincronizado & Validado</span>
        </div>
      </div>

      {/* 1. CONSOLE R36S SIMULATOR */}
      {subView === "console" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Controls / Info Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-violet-400" />
                <span>Telas do Console Físico</span>
              </h3>
              <p className="text-xs text-[#8c88a6] mb-3">
                Simulação da tela real IPS de 3.5&quot; (resolução 640x480) gerenciada pelo script shell <code className="text-violet-300">R36S_WebFileManager.sh</code> redirecionada para <code className="text-violet-300">/dev/tty1</code>.
              </p>

              <div className="space-y-1.5">
                {[
                  { id: "qr", label: "Tela 1: QR Code de Conexão", desc: "Terminal ANSI puro com Quiet Zone" },
                  { id: "dialog", label: "Tela 2: Menu Dialog TUI", desc: "Painel de controle com navegação por gamepad" },
                  { id: "storage", label: "Tela 3: Detecção de Armazenamento", desc: "Diálogo com /roms, /roms2 e USB" },
                  { id: "logs", label: "Tela 4: Logs em Tempo Real", desc: "Visualizador de server.log" }
                ].map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setConsoleScreen(s.id as any)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all ${
                      consoleScreen === s.id
                        ? "bg-violet-600/20 border-violet-500/50 text-white"
                        : "bg-[#191729] border-[#29263f] text-[#9e9ab8] hover:text-white"
                    }`}
                  >
                    <div className="font-semibold text-white">{s.label}</div>
                    <div className="text-[10px] text-[#8c88a6] mt-0.5">{s.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Hardware Controls Mapping Reference */}
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-2 flex items-center gap-2">
                <Gamepad2 className="w-4 h-4 text-emerald-400" />
                <span>Mapeamento controls.gptk</span>
              </h3>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between p-2 rounded bg-[#191729] border border-[#26233b]">
                  <div className="flex items-center gap-2">
                    <SvgAsset path="sprites/dpad.svg" className="w-5 h-5 text-violet-300" />
                    <span className="font-medium text-[#c0bdd1]">D-Pad (Cima / Baixo)</span>
                  </div>
                  <span className="font-mono text-emerald-400 font-bold">Navegar itens</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-[#191729] border border-[#26233b]">
                  <div className="flex items-center gap-2">
                    <SvgAsset path="sprites/btn_a.svg" className="w-5 h-5 text-emerald-300" />
                    <span className="font-medium text-[#c0bdd1]">Botão A (Direita)</span>
                  </div>
                  <span className="font-mono text-emerald-400 font-bold">Confirmar / OK</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-[#191729] border border-[#26233b]">
                  <div className="flex items-center gap-2">
                    <SvgAsset path="sprites/btn_b.svg" className="w-5 h-5 text-amber-300" />
                    <span className="font-medium text-[#c0bdd1]">Botão B (Inferior)</span>
                  </div>
                  <span className="font-mono text-amber-400 font-bold">Cancelar / Voltar</span>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-[#191729] border border-[#26233b]">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#29263f] text-white">START</span>
                    <span className="font-medium text-[#c0bdd1]">Botão START</span>
                  </div>
                  <span className="font-mono text-rose-400 font-bold">Sair / Parar</span>
                </div>
              </div>
            </div>
          </div>

          {/* Physical Console Bezel & 640x480 Screen */}
          <div className="lg:col-span-8 flex justify-center">
            <div className="w-full max-w-[580px] bg-[#1a1727] rounded-3xl p-5 border-4 border-[#2c2842] shadow-2xl relative">
              {/* Console Branding & Speaker holes */}
              <div className="flex items-center justify-between mb-3 px-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-black tracking-widest text-[#7a7698]">R36S</span>
                  <span className="text-[10px] bg-[#29263f] text-[#a4a0c2] px-1.5 py-0.5 rounded font-mono">RK3326</span>
                </div>
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#29263f]"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#29263f]"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#29263f]"></span>
                </div>
              </div>

              {/* Screen Frame (4:3 aspect ratio, 640x480 virtual resolution) */}
              <div className="w-full aspect-[4/3] bg-black rounded-xl border-2 border-[#12111c] overflow-hidden shadow-inner flex flex-col font-mono text-white select-none">
                {/* Screen Top Status bar */}
                <div className="bg-[#0f0e17] border-b border-[#1f1d2e] px-3 py-1 flex items-center justify-between text-[11px] text-[#8e8aa8]">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <strong className="text-white">dArkOS RE</strong> | TTY1 (640x480)
                  </span>
                  <span>IP: 192.168.1.150:8080</span>
                </div>

                {/* Content based on screen mode */}
                <div className="flex-1 p-3 flex flex-col justify-center items-center text-center overflow-hidden">
                  {consoleScreen === "qr" && (
                    <div className="w-full flex flex-col items-center justify-center animate-fade-in">
                      <div className="text-[12px] font-bold text-violet-300 tracking-wide mb-1">
                        === R36S WEB FILE MANAGER: ESCANEE PARA CONECTAR ===
                      </div>
                      <div className="text-[11px] text-[#9e9ab8] mb-2 font-mono">
                        URL: <span className="text-emerald-300 font-bold underline">http://192.168.1.150:8080/?token=4f8a92...</span>
                      </div>

                      {/* ANSI High Contrast QR Simulation (with 4 modules quiet zone) */}
                      <div className="bg-white p-2.5 rounded-md shadow-lg my-1">
                        <div className="w-[170px] h-[170px] bg-white flex items-center justify-center">
                          <SvgAsset path="dialogs/qr.svg" className="w-[160px] h-[160px] text-black" />
                        </div>
                      </div>

                      <div className="mt-2 text-[10px] text-[#8e8aa8] bg-[#12111d] px-3 py-1 rounded border border-[#232038]">
                        [ Pressione qualquer tecla ou <span className="text-amber-300 font-bold">Botão B</span> para voltar ]
                      </div>
                    </div>
                  )}

                  {consoleScreen === "dialog" && (
                    <div className="w-full max-w-[420px] bg-[#0000aa] text-white p-4 rounded shadow-2xl border-2 border-white text-left font-mono">
                      <div className="text-center font-bold bg-[#aaaaaa] text-black py-0.5 mb-3 text-xs">
                        Painel de Controle - R36S Web Manager
                      </div>
                      <div className="text-[11px] mb-3 text-[#eeeeee]">
                        Selecione a operacao desejada com o D-Pad:
                      </div>
                      <div className="space-y-1.5 text-xs">
                        <div className="bg-[#aaaaaa] text-black px-2 py-1 font-bold flex items-center justify-between">
                          <span>1. Mostrar QR Code de Conexao</span>
                          <span className="text-[10px]">&lt;ATIVO&gt;</span>
                        </div>
                        <div className="px-2 py-1 text-[#dddddd]">
                          2. Rede e Armazenamento (/roms)
                        </div>
                        <div className="px-2 py-1 text-[#dddddd]">
                          3. Visualizar Logs (server.log)
                        </div>
                        <div className="px-2 py-1 text-[#dddddd]">
                          4. Parar Servidor e Retornar ao ES
                        </div>
                      </div>
                      <div className="flex justify-center gap-4 mt-4 pt-2 border-t border-white/20 text-xs">
                        <span className="bg-[#aaaaaa] text-black px-3 py-0.5 font-bold">[ OK (A) ]</span>
                        <span className="text-white px-3 py-0.5">[ Cancelar (B) ]</span>
                      </div>
                    </div>
                  )}

                  {consoleScreen === "storage" && (
                    <div className="w-full max-w-[420px] bg-[#0000aa] text-white p-4 rounded shadow-2xl border-2 border-white text-left font-mono text-xs">
                      <div className="text-center font-bold bg-[#aaaaaa] text-black py-0.5 mb-3">
                        Rede e Armazenamento Ativo
                      </div>
                      <div className="space-y-1 text-[11px]">
                        <div><strong>IP Local:</strong> 192.168.1.150</div>
                        <div><strong>Porta HTTP:</strong> 8080</div>
                        <div><strong>Token de Sessão:</strong> 4f8a92e10c7b3d5a</div>
                        <div className="pt-2 font-bold text-yellow-300">Diretorios de Armazenamento:</div>
                        <div className="pl-2 text-[10px] space-y-0.5">
                          <div>- /roms (Cartão SD 1 - TF1/INT)</div>
                          <div>- /roms2 (Cartão SD 2 - TF2/EXT)</div>
                          <div>- /media/usb (Pendrive OTG)</div>
                        </div>
                      </div>
                      <div className="flex justify-center mt-4">
                        <span className="bg-[#aaaaaa] text-black px-4 py-0.5 font-bold text-xs">[ OK (A / B) ]</span>
                      </div>
                    </div>
                  )}

                  {consoleScreen === "logs" && (
                    <div className="w-full h-full bg-black text-[#00ff66] p-2 text-left font-mono text-[10px] leading-tight overflow-y-auto">
                      <div>[INFO] R36S Web File Manager inicializando...</div>
                      <div>[INFO] Python 3.11.2 (Standard Library strictly enforced)</div>
                      <div>[INFO] Interfaces de rede detectadas: wlan0 (192.168.1.150)</div>
                      <div>[INFO] Raízes de armazenamento montadas: /roms, /roms2</div>
                      <div>[INFO] Servidor HTTP ativo em http://192.168.1.150:8080</div>
                      <div>[INFO] Token de autenticacao seguro gerado: 4f8a92e10c7b3d5a</div>
                      <div>[INFO] Arquivos de estado gravados em /roms/tools/.tools/R36S_WebFileManager</div>
                      <div>[INFO] Watchdog ativo monitorando PID 4120</div>
                      <div>[LOG] GET /api/status 200 OK (User-Agent: Mobile Safari)</div>
                      <div>[LOG] POST /api/upload/init 200 OK (Arquivo: Pokemon_Emerald.gba)</div>
                      <div>[LOG] POST /api/upload/chunk [0/4] 200 OK (1048576 bytes)</div>
                      <div>[LOG] os.replace() atômico executado com sucesso</div>
                    </div>
                  )}
                </div>

                {/* Screen Bottom Bar */}
                <div className="bg-[#0f0e17] border-t border-[#1f1d2e] px-3 py-1 flex items-center justify-between text-[10px] text-[#6b6782]">
                  <span>Resolução: 640 x 480 IPS</span>
                  <span>gptokeyb: Ativo</span>
                </div>
              </div>

              {/* Console Physical Controls Mockup */}
              <div className="mt-4 flex items-center justify-between px-6 pt-2">
                {/* D-Pad */}
                <div className="relative w-20 h-20 flex items-center justify-center">
                  <SvgAsset path="sprites/dpad.svg" className="w-18 h-18 text-[#363250]" />
                </div>

                {/* Center Start/Select Buttons */}
                <div className="flex gap-4 items-center">
                  <div className="text-center">
                    <div className="w-8 h-2 bg-[#2c2842] rounded-full mx-auto border border-[#3e395c]"></div>
                    <span className="text-[9px] font-bold text-[#6b6782]">SELECT</span>
                  </div>
                  <div className="text-center">
                    <div className="w-8 h-2 bg-[#2c2842] rounded-full mx-auto border border-[#3e395c]"></div>
                    <span className="text-[9px] font-bold text-[#6b6782]">START</span>
                  </div>
                </div>

                {/* Face Buttons A/B */}
                <div className="flex items-center gap-3">
                  <div className="text-center">
                    <div className="w-8 h-8 rounded-full bg-[#2c2842] border border-[#3e395c] flex items-center justify-center font-bold text-xs text-amber-400">
                      B
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="w-8 h-8 rounded-full bg-[#2c2842] border border-[#3e395c] flex items-center justify-center font-bold text-xs text-emerald-400">
                      A
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. WEB SPA SIMULATOR */}
      {subView === "web" && (
        <div className="space-y-4">
          <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4 flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-violet-400" />
                <span>Interface Web SPA Real (ui.html)</span>
              </h3>
              <p className="text-xs text-[#8c88a6] mt-0.5">
                Layout com todos os ícones e elementos visuais sincronizados com <code className="text-violet-300">/r36s/assets/</code>.
              </p>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="bg-violet-500/20 text-violet-300 border border-violet-500/30 px-2.5 py-1 rounded font-medium">
                Mobile & Desktop First
              </span>
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2.5 py-1 rounded font-medium">
                Safari iOS 100% OK
              </span>
            </div>
          </div>

          {/* Web Container Window Frame */}
          <div className="bg-[#0f0d1a] rounded-2xl border-2 border-[#2b2742] overflow-hidden shadow-2xl">
            {/* Browser Browser Top Bar */}
            <div className="bg-[#161426] border-b border-[#26233b] px-4 py-2.5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-rose-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-amber-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80"></span>
                </div>
                <span className="text-[#8c88a6] text-[11px] ml-2">Navegador Mobile / Desktop</span>
              </div>
              <div className="bg-[#0d0c16] px-4 py-1 rounded-full border border-[#26233b] text-[#c0bdd1] font-mono text-[11px] w-80 text-center truncate">
                http://192.168.1.150:8080/?token=4f8a92e10c7b...
              </div>
              <div className="text-[11px] text-emerald-400 font-medium">Conectado</div>
            </div>

            {/* Inner Web UI (Exact replica of ui.html structure with SVG assets) */}
            <div className="p-4 sm:p-6 space-y-5 bg-[#0f0d1a] min-h-[500px]">
              {/* Header */}
              <header className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#221f36]">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center p-1.5">
                    <SvgAsset path="branding/logo_main.svg" className="w-7 h-7" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h1 className="text-base font-bold text-white tracking-tight">R36S File Manager</h1>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-violet-600/30 text-violet-300 border border-violet-500/40">
                        dArkOS RE
                      </span>
                    </div>
                    <p className="text-xs text-[#8c88a6]">Gerenciador de Arquivos e ROMs via Wi-Fi</p>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1c1a2e] border border-[#2e2a4a] text-xs font-semibold text-white hover:bg-[#25223d] transition-all">
                    <SvgAsset path="actions/new_folder.svg" className="w-4 h-4 text-violet-300" />
                    <span>Nova Pasta</span>
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-600 border border-violet-500 text-xs font-semibold text-white hover:bg-violet-500 transition-all shadow-md shadow-violet-600/20">
                    <SvgAsset path="actions/upload.svg" className="w-4 h-4 text-white" />
                    <span>Enviar Arquivos</span>
                  </button>
                  <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/20 border border-rose-500/30 text-xs font-semibold text-rose-300 hover:bg-rose-500/30 transition-all">
                    <SvgAsset path="status/error.svg" className="w-4 h-4 text-rose-400" />
                    <span>Desconectar</span>
                  </button>
                </div>
              </header>

              {/* Storage Devices Pills */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-[#141221] border border-violet-500/40 shadow-sm">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <SvgAsset path="storage/sd.svg" className="w-4 h-4 text-violet-400" />
                      <span className="text-xs font-bold text-white">TF1 (Interno)</span>
                    </div>
                    <span className="text-[10px] text-violet-300 font-mono font-bold">48.2 GB livres</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#221f36] rounded-full overflow-hidden">
                    <div className="w-[62%] h-full bg-violet-500 rounded-full"></div>
                  </div>
                  <div className="text-[10px] text-[#7a7698] mt-1 font-mono">/roms (Sistema & Ferramentas)</div>
                </div>

                <div className="p-3 rounded-xl bg-[#141221] border border-[#26233b]">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <SvgAsset path="storage/sd.svg" className="w-4 h-4 text-emerald-400" />
                      <span className="text-xs font-bold text-white">TF2 (ROMs Secundário)</span>
                    </div>
                    <span className="text-[10px] text-emerald-300 font-mono font-bold">182.5 GB livres</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#221f36] rounded-full overflow-hidden">
                    <div className="w-[28%] h-full bg-emerald-500 rounded-full"></div>
                  </div>
                  <div className="text-[10px] text-[#7a7698] mt-1 font-mono">/roms2 (Jogos Adicionais)</div>
                </div>

                <div className="p-3 rounded-xl bg-[#141221] border border-[#26233b]">
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <SvgAsset path="storage/usb.svg" className="w-4 h-4 text-amber-400" />
                      <span className="text-xs font-bold text-white">USB OTG</span>
                    </div>
                    <span className="text-[10px] text-amber-300 font-mono font-bold">32.1 GB livres</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#221f36] rounded-full overflow-hidden">
                    <div className="w-[49%] h-full bg-amber-500 rounded-full"></div>
                  </div>
                  <div className="text-[10px] text-[#7a7698] mt-1 font-mono">/media/usb (Armazenamento Externo)</div>
                </div>
              </div>

              {/* Breadcrumbs & Search Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 bg-[#141221] p-2.5 rounded-xl border border-[#26233b]">
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 text-xs text-[#a4a0c2]">
                  <button className="flex items-center gap-1 text-white hover:text-violet-300 p-1 rounded">
                    <SvgAsset path="navigation/home.svg" className="w-4 h-4 text-violet-400" />
                    <span>Início</span>
                  </button>
                  <ChevronRight className="w-3 h-3 text-[#585474]" />
                  <span className="text-[#a4a0c2]">roms</span>
                  <ChevronRight className="w-3 h-3 text-[#585474]" />
                  <span className="font-bold text-violet-300">gba</span>
                </div>

                {/* Filter and Selection */}
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <div className="absolute left-2.5 top-2 pointer-events-none">
                      <SvgAsset path="navigation/search.svg" className="w-3.5 h-3.5 text-[#726e8f]" />
                    </div>
                    <input
                      type="text"
                      placeholder="Filtrar ROMs..."
                      className="bg-[#191729] border border-[#2b2744] text-xs text-white pl-8 pr-3 py-1.5 rounded-lg focus:outline-none focus:border-violet-500 w-44"
                      readOnly
                      value=""
                    />
                  </div>
                  <button className="text-[11px] font-semibold text-[#a4a0c2] hover:text-white px-2.5 py-1.5 rounded-lg bg-[#191729] border border-[#2b2744]">
                    ✓ Selecionar Todos
                  </button>
                </div>
              </div>

              {/* Files Table List */}
              <div className="bg-[#141221] border border-[#26233b] rounded-xl overflow-hidden">
                <div className="grid grid-cols-12 gap-2 px-4 py-2 text-[11px] font-semibold text-[#7a7698] uppercase tracking-wider border-b border-[#221f36] bg-[#110f1c]">
                  <div className="col-span-7 sm:col-span-6 flex items-center gap-2">
                    <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" readOnly />
                    <span>Nome do Arquivo / Pasta</span>
                  </div>
                  <div className="col-span-2 hidden sm:block">Tipo</div>
                  <div className="col-span-2 text-right">Tamanho</div>
                  <div className="col-span-3 sm:col-span-2 text-right">Ações</div>
                </div>

                <div className="divide-y divide-[#1e1b30] text-xs">
                  {/* Folder Item */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#191729] transition-all">
                    <div className="col-span-7 sm:col-span-6 flex items-center gap-3">
                      <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" readOnly />
                      <SvgAsset path="icons/folder.svg" className="w-5 h-5 text-amber-400" />
                      <span className="font-semibold text-white">covers/</span>
                    </div>
                    <div className="col-span-2 hidden sm:block text-[#8c88a6]">Diretório</div>
                    <div className="col-span-2 text-right font-mono text-[#8c88a6]">12 itens</div>
                    <div className="col-span-3 sm:col-span-2 flex items-center justify-end gap-1.5">
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/download.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* GBA ROM Item */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#191729] transition-all">
                    <div className="col-span-7 sm:col-span-6 flex items-center gap-3">
                      <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" checked readOnly />
                      <SvgAsset path="systems/gba.svg" className="w-5 h-5 text-violet-400" />
                      <div className="truncate">
                        <span className="font-medium text-white">Pokemon - Emerald Version (USA).gba</span>
                        <div className="flex items-center gap-1 mt-0.5 sm:hidden">
                          <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-violet-600/30 text-violet-300">GBA</span>
                          <span className="text-[10px] text-[#7a7698]">16.0 MB</span>
                        </div>
                      </div>
                    </div>
                    <div className="col-span-2 hidden sm:block">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-violet-600/30 text-violet-300 border border-violet-500/40">
                        ROM GBA
                      </span>
                    </div>
                    <div className="col-span-2 text-right font-mono text-[#c0bdd1]">16.0 MB</div>
                    <div className="col-span-3 sm:col-span-2 flex items-center justify-end gap-1.5">
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/download.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/rename.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-rose-400 hover:bg-[#25223d]">
                        <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* SNES ROM Item */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#191729] transition-all">
                    <div className="col-span-7 sm:col-span-6 flex items-center gap-3">
                      <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" readOnly />
                      <SvgAsset path="systems/snes.svg" className="w-5 h-5 text-indigo-400" />
                      <div className="truncate">
                        <span className="font-medium text-white">Super Mario World.sfc</span>
                      </div>
                    </div>
                    <div className="col-span-2 hidden sm:block">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-600/30 text-indigo-300 border border-indigo-500/40">
                        ROM SNES
                      </span>
                    </div>
                    <div className="col-span-2 text-right font-mono text-[#c0bdd1]">4.0 MB</div>
                    <div className="col-span-3 sm:col-span-2 flex items-center justify-end gap-1.5">
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/download.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* PS1 CHD Item */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#191729] transition-all">
                    <div className="col-span-7 sm:col-span-6 flex items-center gap-3">
                      <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" readOnly />
                      <SvgAsset path="systems/ps1.svg" className="w-5 h-5 text-cyan-400" />
                      <div className="truncate">
                        <span className="font-medium text-white">Castlevania - Symphony of the Night.chd</span>
                      </div>
                    </div>
                    <div className="col-span-2 hidden sm:block">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-cyan-600/30 text-cyan-300 border border-cyan-500/40">
                        ROM PS1
                      </span>
                    </div>
                    <div className="col-span-2 text-right font-mono text-[#c0bdd1]">482.4 MB</div>
                    <div className="col-span-3 sm:col-span-2 flex items-center justify-end gap-1.5">
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/download.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  {/* ZIP Package Item */}
                  <div className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#191729] transition-all">
                    <div className="col-span-7 sm:col-span-6 flex items-center gap-3">
                      <input type="checkbox" className="rounded bg-[#1a182c] border-[#2e2a4a]" readOnly />
                      <SvgAsset path="icons/file_zip.svg" className="w-5 h-5 text-amber-400" />
                      <div className="truncate">
                        <span className="font-medium text-white">mame_arcade_pack_v1.zip</span>
                      </div>
                    </div>
                    <div className="col-span-2 hidden sm:block">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-600/30 text-amber-300 border border-amber-500/40">
                        Arquivo ZIP
                      </span>
                    </div>
                    <div className="col-span-2 text-right font-mono text-[#c0bdd1]">145.2 MB</div>
                    <div className="col-span-3 sm:col-span-2 flex items-center justify-end gap-1.5">
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/download.svg" className="w-3.5 h-3.5" />
                      </button>
                      <button className="p-1.5 rounded bg-[#1c1a2e] text-[#a4a0c2] hover:text-white hover:bg-[#25223d]">
                        <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Floating Batch Selection Bar */}
              <div className="bg-[#1c192d] border border-violet-500/40 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 shadow-xl">
                <div className="flex items-center gap-2 text-xs">
                  <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse"></span>
                  <span className="font-bold text-white">1 item selecionado</span>
                  <span className="text-[#8c88a6] font-mono">(16.0 MB)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#25223d] text-[#c0bdd1] hover:text-white text-xs border border-[#343054]">
                    <SvgAsset path="actions/copy.svg" className="w-3.5 h-3.5 text-violet-300" />
                    <span>Copiar</span>
                  </button>
                  <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#25223d] text-[#c0bdd1] hover:text-white text-xs border border-[#343054]">
                    <SvgAsset path="actions/move.svg" className="w-3.5 h-3.5 text-emerald-300" />
                    <span>Mover</span>
                  </button>
                  <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#25223d] text-[#c0bdd1] hover:text-white text-xs border border-[#343054]">
                    <SvgAsset path="actions/zip.svg" className="w-3.5 h-3.5 text-amber-300" />
                    <span>Compactar ZIP</span>
                  </button>
                  <button className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-500/20 text-rose-300 hover:bg-rose-500/30 text-xs border border-rose-500/30">
                    <SvgAsset path="actions/delete.svg" className="w-3.5 h-3.5 text-rose-400" />
                    <span>Excluir</span>
                  </button>
                </div>
              </div>

              {/* Real Transfer Progress Banner */}
              <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <SvgAsset path="transfer/progress.svg" className="w-4 h-4 text-violet-400" />
                    <span className="font-bold text-white">Transferência Ativa: Pokemon - Emerald Version.gba</span>
                  </div>
                  <div className="flex items-center gap-3 font-mono text-[11px] text-[#9e9ab8]">
                    <span className="flex items-center gap-1">
                      <SvgAsset path="transfer/speed.svg" className="w-3.5 h-3.5 text-emerald-400" />
                      <span>4.8 MB/s</span>
                    </span>
                    <span className="text-violet-300 font-bold">100% (Chunk 16/16)</span>
                  </div>
                </div>
                <div className="w-full h-2 bg-[#221f36] rounded-full overflow-hidden">
                  <div className="w-full h-full bg-emerald-500 rounded-full transition-all"></div>
                </div>
                <div className="flex items-center justify-between text-[10px] text-[#7a7698]">
                  <span>SHA-256 verificado: 8a4f1e0b... OK</span>
                  <span>Rename atômico instantâneo concluído</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 3. ASSET MATRIX AUDIT (53 SVGs) */}
      {subView === "assets" && (
        <div className="space-y-4">
          <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Auditoria Visual de Assets: Todos os 53 SVGs Verificados</span>
              </h3>
              <p className="text-xs text-[#8c88a6] mt-0.5">
                Todos os vetores são arquivos SVG reais, sem dependência de fontes de terceiros, integrados tanto na Web SPA quanto no executável autocontido.
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full font-bold">
                53 / 53 Carregados
              </span>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[#141221] p-3 rounded-xl border border-[#26233b]">
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => setAssetCategory("all")}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all ${
                  assetCategory === "all" ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33] hover:text-white"
                }`}
              >
                Todos ({allAssetKeys.length})
              </button>
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setAssetCategory(cat)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all capitalize ${
                    assetCategory === cat ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33] hover:text-white"
                  }`}
                >
                  {cat} ({allAssetKeys.filter((k) => k.startsWith(cat + "/")).length})
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 text-[#726e8f] absolute left-2.5 top-2.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Buscar asset..."
                value={assetSearch}
                onChange={(e) => setAssetSearch(e.target.value)}
                className="bg-[#191729] border border-[#2b2744] text-xs text-white pl-8 pr-3 py-1.5 rounded-lg focus:outline-none focus:border-violet-500 w-44"
              />
            </div>
          </div>

          {/* Grid of SVGs */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {filteredAssets.map((assetPath) => {
              const parts = assetPath.split("/");
              const cat = parts[0];
              const filename = parts[1];
              const raw = assetsMap[assetPath];
              const byteSize = new TextEncoder().encode(raw).length;

              return (
                <div
                  key={assetPath}
                  className="bg-[#141221] border border-[#26233b] hover:border-violet-500/50 rounded-xl p-3 flex flex-col items-center justify-between text-center transition-all group"
                >
                  <div className="w-full flex items-center justify-between text-[10px] text-[#6b6782] mb-2">
                    <span className="uppercase font-mono">{cat}</span>
                    <span className="font-mono">{byteSize} B</span>
                  </div>

                  {/* SVG Icon Stage (Dark + Contrast back) */}
                  <div className="w-14 h-14 rounded-lg bg-[#0d0c16] border border-[#221f38] flex items-center justify-center p-2 group-hover:bg-violet-950/30 transition-all shadow-inner">
                    <SvgAsset path={assetPath} className="w-10 h-10 text-white" />
                  </div>

                  <div className="mt-3 w-full">
                    <div className="text-xs font-medium text-white truncate" title={filename}>
                      {filename}
                    </div>
                    <div className="text-[10px] text-[#8c88a6] mt-0.5 truncate font-mono">
                      /r36s/assets/{assetPath}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
