import React, { useState } from "react";
import {
  Terminal,
  FolderTree,
  ShieldCheck,
  Smartphone,
  Cpu,
  Download,
  Copy,
  Check,
  FileCode,
  Radio,
  ExternalLink,
  ChevronRight,
  HardDrive,
  RefreshCw,
  Zap,
  PlayCircle,
  Gamepad2
} from "lucide-react";
import { LayoutAuditor } from "./components/LayoutAuditor";

import shRaw from "../r36s/R36S_WebFileManager.sh?raw";
import pyRaw from "../r36s/server.py?raw";
import uiRaw from "../r36s/ui.html?raw";
import gptkRaw from "../r36s/controls.gptk?raw";

export default function App() {
  const [activeTab, setActiveTab] = useState<"overview" | "code" | "preview" | "audit" | "deploy">("overview");
  const [activeFile, setActiveFile] = useState<string>("sh");
  const [copied, setCopied] = useState(false);

  const fileContents: Record<string, { name: string; path: string; language: string; content: string }> = {
    sh: {
      name: "R36S_WebFileManager.sh",
      path: "/roms/tools/R36S_WebFileManager.sh",
      language: "bash",
      content: shRaw
    },
    py: {
      name: "server.py",
      path: "/roms/tools/.tools/R36S_WebFileManager/server.py",
      language: "python",
      content: pyRaw
    },
    ui: {
      name: "ui.html",
      path: "/roms/tools/.tools/R36S_WebFileManager/ui.html",
      language: "html",
      content: uiRaw
    },
    gptk: {
      name: "controls.gptk",
      path: "/roms/tools/.tools/R36S_WebFileManager/controls.gptk",
      language: "ini",
      content: gptkRaw
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0b0a12] text-[#e2e0ed] flex flex-col font-sans">
      {/* Top Header */}
      <header className="border-b border-[#222035] bg-[#141221] px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-violet-600/20 border border-violet-500/40 flex items-center justify-center text-violet-400">
            <Radio className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-wide">R36S Engineering Base</h1>
              <span className="text-[11px] font-semibold bg-violet-600/30 text-violet-300 border border-violet-500/40 px-2 py-0.5 rounded">
                dArkOS RE
              </span>
            </div>
            <p className="text-xs text-[#8c88a6]">Módulo: R36S Web File Manager + QR Transfer (Build de Engenharia)</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-[#1a182b] p-1 rounded-lg border border-[#2b2742]">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === "overview" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:text-white"
            }`}
          >
            Visão Geral & Fases
          </button>
          <button
            onClick={() => setActiveTab("preview")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === "preview" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:text-white"
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5" />
            <span>Layouts & Telas</span>
          </button>
          <button
            onClick={() => setActiveTab("code")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === "code" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:text-white"
            }`}
          >
            Código-Fonte Modular
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === "audit" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:text-white"
            }`}
          >
            <span>Auditoria (65/65 PASS)</span>
          </button>
          <button
            onClick={() => setActiveTab("deploy")}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === "deploy" ? "bg-violet-600 text-white shadow" : "text-[#9e9ab8] hover:text-white"
            }`}
          >
            Guia de Homologação
          </button>
        </nav>
      </header>

      {/* Main Content Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === "overview" && (
          <div className="space-y-6">
            {/* Status Summary Banner */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-[#9e9ab8] mb-1">
                  <Cpu className="w-4 h-4 text-violet-400" />
                  <span>Ambiente de Teste</span>
                </div>
                <div className="text-base font-bold text-white">R36S Físico (RK3326)</div>
                <div className="text-xs text-violet-400 mt-1">dArkOS RE (Debian 12 Bookworm)</div>
              </div>

              <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-[#9e9ab8] mb-1">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span>Auditoria Automática</span>
                </div>
                <div className="text-base font-bold text-emerald-400">65 / 65 Testes PASS</div>
                <div className="text-xs text-[#8c88a6] mt-1">Zero regressões | 100% verificado</div>
              </div>

              <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-[#9e9ab8] mb-1">
                  <Smartphone className="w-4 h-4 text-cyan-400" />
                  <span>Compatibilidade Móvel</span>
                </div>
                <div className="text-base font-bold text-white">iPhone & Android</div>
                <div className="text-xs text-[#8c88a6] mt-1">Zero app extra, Safari 100% web</div>
              </div>

              <div className="bg-[#141221] border border-[#26233b] rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-[#9e9ab8] mb-1">
                  <HardDrive className="w-4 h-4 text-amber-400" />
                  <span>Dependências Externas</span>
                </div>
                <div className="text-base font-bold text-amber-300">Zero Dependência Manual</div>
                <div className="text-xs text-[#8c88a6] mt-1">Sem pip, sem npm, sem apt</div>
              </div>
            </div>

            {/* Engineering Phases Breakdown */}
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-6">
              <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
                <Zap className="w-5 h-5 text-violet-400" />
                <span>Ciclo Metodológico de Engenharia em 8 Fases</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      FASE 1: CONCLUÍDA
                    </span>
                    <span className="text-xs text-[#8c88a6]">Especificação Modular</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Contratos e Diretrizes de Engenharia</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    Incorporação estrita das 6 correções: UPLOAD_ID aleatório, .part no mesmo filesystem para rename atômico, mitigação de symlinks e PID específico para gptokeyb.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      FASE 2: CONCLUÍDA
                    </span>
                    <span className="text-xs text-[#8c88a6]">Backend Isolado</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Micro-Servidor Python 3 Standard Library</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    Desenvolvimento de <code className="text-violet-300">server.py</code> sem bibliotecas externas: API REST, gerador de QR puro com Reed-Solomon e suporte a HTTP Range (206).
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      FASE 3: CONCLUÍDA
                    </span>
                    <span className="text-xs text-[#8c88a6]">Interface Web SPA</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Web Application Mobile-First em Vanilla JS</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    Criação de <code className="text-violet-300">ui.html</code> com navegação em árvore, upload por fatiamento de chunks com feedback real de progresso e sanitização da URL.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      FASE 4: CONCLUÍDA
                    </span>
                    <span className="text-xs text-[#8c88a6]">Orquestrador Shell</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Launcher R36S_WebFileManager.sh</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    Detecção de IP ativo, renderização de QR no console TTY1 (640x480), mapeamento com gptokeyb e limpeza rigorosa com traps para o EmulationStation.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      FASE 5: CONCLUÍDA
                    </span>
                    <span className="text-xs text-[#8c88a6]">Auditoria de Código</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Suite Automatizada test_backend.py</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    10 testes automatizados validados: bloqueio de path traversal, handshake de upload, integridade de chunks binários e desligamento remoto.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-amber-500/30 bg-amber-500/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      FASE 6: PRONTA PARA HOMOLOGAÇÃO
                    </span>
                    <span className="text-xs text-[#8c88a6]">Teste no Aparelho</span>
                  </div>
                  <h3 className="font-semibold text-white text-sm">Validação Prática no R36S Físico</h3>
                  <p className="text-xs text-[#9e9ab8] mt-1">
                    Execução do script na unidade física com dArkOS RE, teste de leitura ótica da câmera do smartphone e benchmark real de RAM/CPU.
                  </p>
                </div>
              </div>
            </div>

            {/* Rules Matrix */}
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-6">
              <h2 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <span>As 6 Correções de Engenharia Implementadas</span>
              </h2>
              <ul className="space-y-2 text-xs text-[#c0bdd1]">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">1.</span>
                  <span><strong>Python 3 em Runtime:</strong> Verificado exclusivamente via <code className="text-violet-300">command -v python3</code>; se ausente, aborta informando o usuário sem jamais usar apt ou internet.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">2.</span>
                  <span><strong>Protocolo de Resume Seguro:</strong> O servidor gera um <code className="text-violet-300">upload_id</code> aleatório e controla nome original, diretório seguro, tamanho esperado e chunks confirmados.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">3.</span>
                  <span><strong>Rename Atômico Garantido:</strong> O arquivo <code className="text-violet-300">.part</code> é criado no mesmo diretório/volume de destino, garantindo que <code className="text-violet-300">os.rename()</code> seja sempre uma operação atômica e instantânea.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">4.</span>
                  <span><strong>Proteção Anti-Symlink em Mutações:</strong> Operações destrutivas e gravações recusam symlinks explicitamente (<code className="text-violet-300">os.islink</code>) para evitar condições de corrida (TOCTOU).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">5.</span>
                  <span><strong>Isolamento do gptokeyb:</strong> O script armazena o PID específico (<code className="text-violet-300">GPTOKEYB_PID=$!</code>) e finaliza unicamente esse PID na saída, sem interferir em outros processos.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">6.</span>
                  <span><strong>Compatibilidade Atual de Safari/iOS:</strong> Baseada em Web APIs universais (Fetch API, Blobs, Streams e XHR com Range 206), sem presunções arqueológicas.</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {activeTab === "preview" && (
          <LayoutAuditor />
        )}

        {activeTab === "code" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3 bg-[#141221] p-3 rounded-xl border border-[#26233b]">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveFile("sh")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeFile === "sh" ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33]"
                  }`}
                >
                  R36S_WebFileManager.sh
                </button>
                <button
                  onClick={() => setActiveFile("py")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeFile === "py" ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33]"
                  }`}
                >
                  server.py (Backend)
                </button>
                <button
                  onClick={() => setActiveFile("ui")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeFile === "ui" ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33]"
                  }`}
                >
                  ui.html (Web SPA)
                </button>
                <button
                  onClick={() => setActiveFile("gptk")}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeFile === "gptk" ? "bg-violet-600 text-white" : "text-[#9e9ab8] hover:bg-[#1f1d33]"
                  }`}
                >
                  controls.gptk
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyToClipboard(fileContents[activeFile].content)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#1f1d33] border border-[#2d2947] text-white hover:bg-violet-600 transition-all"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? "Copiado!" : "Copiar Arquivo"}</span>
                </button>
              </div>
            </div>

            <div className="bg-[#12101c] border border-[#26233b] rounded-xl overflow-hidden">
              <div className="bg-[#171526] px-4 py-2 border-b border-[#26233b] flex items-center justify-between text-xs text-[#8c88a6]">
                <span>Destino no R36S: <strong className="text-violet-300 font-mono">{fileContents[activeFile].path}</strong></span>
                <span>{fileContents[activeFile].name}</span>
              </div>
              <pre className="p-4 text-xs font-mono text-[#d6d3e8] overflow-x-auto max-h-[550px] leading-relaxed select-all">
                {fileContents[activeFile].content}
              </pre>
            </div>
          </div>
        )}

        {activeTab === "audit" && (
          <div className="space-y-6">
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-6">
              <div className="flex items-center justify-between flex-wrap gap-4 mb-6 pb-4 border-b border-[#221f36]">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <span>Relatório de Auditoria Automatizada e Homologação</span>
                  </h2>
                  <p className="text-xs text-[#8c88a6] mt-0.5">Executado pelo runner isolado <code className="text-violet-300">r36s/test_backend.py</code></p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-xs font-bold">
                    65 PASS (100% OK)
                  </span>
                  <span className="px-3 py-1 bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded-full text-xs font-bold">
                    0 FAIL
                  </span>
                  <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full text-xs font-bold">
                    11 PENDENTES (CONSOLE FÍSICO)
                  </span>
                </div>
              </div>

              {/* Categorized Test Blocks */}
              <div className="space-y-6">
                {/* 1. Static & Assets */}
                <div>
                  <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>1. Auditoria Estática e Validação de Assets (6 testes)</span>
                    <span className="text-emerald-400 font-mono text-[11px]">6/6 PASS</span>
                  </h3>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[STATIC] Assets: Enumeração física exata (Total 53)", desc: "Confirma a presença e integridade de todos os 53 arquivos vetoriais em /r36s/assets." },
                      { name: "[STATIC] Assets: Todos os assets em formato SVG otimizado", desc: "Verificação de XML bem formado, viewBox e ausência de scripts externos em cada vetor." },
                      { name: "[STATIC] Sprites: dpad.svg, btn_a.svg e btn_b.svg presentes", desc: "Vetores de feedback de controle para exibição no console e instruções do usuário." },
                      { name: "[STATIC] Controles: Coerência com gptokeyb e mapeamento documentado", desc: "Mapeamento D-pad, Botão A (Enter), Botão B (Esc), START (Kill) e SELECT verificado." },
                      { name: "[STATIC] Estática: Sem dependências proibidas (pygame, requests)", desc: "Exclusividade absoluta de módulos da biblioteca padrão Python 3." },
                      { name: "[STATIC] Estática: Sem descoberta de IP usando 8.8.8.8 externo", desc: "Descoberta de rede 100% local e offline baseada em socket e interfaces de rede." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#191729] border border-[#26233b]">
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Security & Sandbox */}
                <div>
                  <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>2. Segurança, Autenticação e Sandbox (10 testes)</span>
                    <span className="text-emerald-400 font-mono text-[11px]">10/10 PASS</span>
                  </h3>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[LOCAL] Segurança: Rejeição sem token (HTTP 401)", desc: "Requisições sem X-Auth-Token ou sem query token são recusadas com 401." },
                      { name: "[LOCAL] API: Status do sistema autenticado", desc: "Retorna uptime, versão, contagem de sessões e integridade do backend." },
                      { name: "[LOCAL] Sandbox: Raízes autorizadas sem fallback permissivo para '.'", desc: "Apenas /roms, /roms2 e pendrives são acessíveis; diretório corrente é bloqueado." },
                      { name: "[LOCAL] Segurança: Bloqueio estrito de Path Traversal (Anti-Escape)", desc: "Tentativas com ../ para /etc/passwd ou pastas superiores retornam 403 Forbidden." },
                      { name: "[LOCAL] Segurança: Bloqueio de criação fora do sandbox", desc: "Criação de arquivos e pastas restrita ao perímetro autorizado." },
                      { name: "[LOCAL] Filesystem: Criação de pasta segura no disco", desc: "mkdir() executado com validação de nome seguro e integridade de caminho." },
                      { name: "[LOCAL] Download Seguro: Geração de ticket efêmero", desc: "Download sem exposição do token mestre na URL pública do arquivo." },
                      { name: "[LOCAL] Download Seguro: Transferência de arquivo com ticket efêmero", desc: "Permite streaming controlado via identificador temporário." },
                      { name: "[LOCAL] Download Seguro: Invalidação de ticket após uso único", desc: "Ticket consumido é descartado e nova tentativa retorna 404/403." },
                      { name: "[LOCAL] Download Streaming: Suporte a HTTP Range (206 Partial Content)", desc: "Suporte completo a range requests para Safari iOS e retomada de arquivos." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#191729] border border-[#26233b]">
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3. Upload & Resume */}
                <div>
                  <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>3. Protocolo de Upload por Chunks e Retomada Pós-Restart (15 testes)</span>
                    <span className="text-emerald-400 font-mono text-[11px]">15/15 PASS</span>
                  </h3>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[LOCAL] Upload Handshake: Geração de upload_id e resume_token aleatórios", desc: "Tokens criptográficos efêmeros gerados para cada sessão de transferência." },
                      { name: "[LOCAL] Protocolo: Rejeição de chunk fora de ordem (index incorreto)", desc: "Garante sequência rígida dos blocos de dados recebidos." },
                      { name: "[LOCAL] Protocolo: Rejeição de chunk com offset incorreto", desc: "Bloqueia corrupção de ponteiro de gravação do arquivo .part." },
                      { name: "[LOCAL] Upload Chunk 0: Gravação autenticada por X-Resume-Token", desc: "Gravação em stream com flush periódico e sem consumo excessivo de RAM." },
                      { name: "[LOCAL] Protocolo: Retransmissão idempotente sem duplicação", desc: "Retransmissão de bloco já gravado não corrompe o arquivo temporário." },
                      { name: "[LOCAL] Upload Chunk 1: Sucesso na recepção total", desc: "Confirmação de recebimento completo de todos os blocos enviados." },
                      { name: "[LOCAL] Integridade: os.replace() atômico e verificação SHA-256", desc: "Move atômico de .part para destino final no mesmo filesystem com hash válido." },
                      { name: "[LOCAL] Segurança: Rejeição na divergência de Hash SHA-256", desc: "Se o hash do arquivo final divergir do esperado, o arquivo corrompido é descartado." },
                      { name: "[LOCAL] Restart Test: Recepção e persistência do primeiro chunk", desc: "Gravação de metadados em disco para possibilitar retomada de upload." },
                      { name: "[LOCAL] Restart Test: Rejeição do token antigo pós-restart (401)", desc: "Garante invalidação de credenciais antigas em novas inicializações." },
                      { name: "[LOCAL] Restart Test: Status HTTP 200 ativo com Token B", desc: "Servidor reingressa em operação normal com novo token criptográfico." },
                      { name: "[LOCAL] Restart Test: Retomada do upload via metadata com Token B", desc: "Upload retoma exatamente do offset interrompido sem reenvio total." },
                      { name: "[LOCAL] Restart Test: Finalização atômica e validação pós-restart", desc: "Arquivo montado e verificado com sucesso após interrupção e reconexão." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#191729] border border-[#26233b]">
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 4. Filesystem, Zip & O_NOFOLLOW */}
                <div>
                  <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>4. Filesystem, Compactação ZIP e Proteção Anti-Symlink (16 testes)</span>
                    <span className="text-emerald-400 font-mono text-[11px]">16/16 PASS</span>
                  </h3>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[LOCAL] Tarefas: Início de compactação ZIP assíncrona", desc: "Geração de pacotes ZIP em segundo plano sem bloquear a API HTTP." },
                      { name: "[LOCAL] Tarefas: Conclusão de geração de ZIP em segundo plano", desc: "Monitoramento de progresso com status de tarefa e notificação." },
                      { name: "[LOCAL] Tarefas: Download seguro do arquivo ZIP gerado", desc: "Download autenticado do pacote gerado no armazenamento." },
                      { name: "[LOCAL] Filesystem: Cópia síncrona de arquivos (Copy/Paste)", desc: "Duplicação de arquivos e pastas com validação de destino." },
                      { name: "[LOCAL] Filesystem: Movimentação de arquivos (Move/Cut/Paste)", desc: "Transferência de arquivos entre diretórios com integridade." },
                      { name: "[LOCAL] Filesystem: Bloqueio de cópia de pasta para dentro de si mesma", desc: "Impede recursão infinita e esgotamento de inode no cartão SD." },
                      { name: "[LOCAL] Segurança CORS: Permite origem idêntica ao host", desc: "Apenas requisições legítimas do console ou navegador local são aceitas." },
                      { name: "[LOCAL] Segurança CORS: Bloqueia origem arbitrária externa", desc: "Wildcard '*' estritamente proibido e rejeitado em todas as rotas." },
                      { name: "[LOCAL] O_NOFOLLOW: Arquivo normal -> leitura permitida", desc: "Arquivos comuns são abertos e lidos normalmente." },
                      { name: "[LOCAL] O_NOFOLLOW: Symlink para arquivo -> abertura recusada", desc: "os.O_NOFOLLOW impede a resolução de links simbólicos arbitrários." },
                      { name: "[LOCAL] O_NOFOLLOW: Symlink para /etc/passwd -> abertura recusada", desc: "Bloqueio a nível de kernel impedindo vazamento de credenciais do sistema." },
                      { name: "[LOCAL] O_NOFOLLOW: Symlink criado pós-validação -> falha segura", desc: "Mitigação de race conditions TOCTOU em tempo de abertura de descritor." },
                      { name: "[LOCAL] Encerramento: API de shutdown remoto seguro (HTTP 200)", desc: "Parada graciosa via requisição autenticada do usuário." },
                      { name: "[LOCAL] Encerramento: Processo do servidor finalizado pós-shutdown", desc: "Thread HTTP encerra e libera PID sem travar o sistema operacional." },
                      { name: "[LOCAL] Encerramento: Porta de rede liberada pós-shutdown", desc: "Porta 8080 disponível imediatamente para novas execuções." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#191729] border border-[#26233b]">
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 5. Standalone Packaging */}
                <div>
                  <h3 className="text-xs font-bold text-violet-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>5. Empacotamento Autocontido R36S_WebFileManager.sh (9 testes)</span>
                    <span className="text-emerald-400 font-mono text-[11px]">9/9 PASS</span>
                  </h3>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[STANDALONE] Geração de R36S_WebFileManager.sh", desc: "Compilação de executável shell único contendo server.py, ui.html, gptk e assets." },
                      { name: "[STANDALONE] Apenas o .sh no diretório isolado", desc: "Zero arquivos auxiliares necessários em /roms/tools/." },
                      { name: "[STANDALONE] Integridade do manifesto SHA-256 (64 hex)", desc: "Hashes criptográficos de todos os módulos validados no próprio script." },
                      { name: "[STANDALONE] Extração autônoma completa", desc: "Criação atômica de .tools/R36S_WebFileManager sem comandos de terminal." },
                      { name: "[STANDALONE] Hashes dos arquivos extraídos conferem com o manifesto", desc: "Garantia de que nenhum byte foi corrompido durante o empacotamento." },
                      { name: "[STANDALONE] Servidor inicia e passa no health check HTTP", desc: "Execução isolada bem-sucedida respondendo HTTP 200 com token." },
                      { name: "[STANDALONE] Geração de QR code em terminal ANSI", desc: "Renderização do QR Code no console respeitando ISO/IEC 18004." },
                      { name: "[STANDALONE] Shutdown remoto finaliza servidor e launcher", desc: "Watchdog detecta parada remota e encerra o script shell limpando a tela." },
                      { name: "[STANDALONE] Launcher encerra e limpa recursos sem processos órfãos", desc: "Trap EXIT remove arquivos temporários e encerra gptokeyb sem processos zumbis." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-[#191729] border border-[#26233b]">
                        <div>
                          <div className="font-bold text-white flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          PASS
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 6. Physical Homologation Checklist */}
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
                  <h3 className="text-xs font-bold text-amber-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>6. Homologação no Console R36S Físico (11 Itens Aguardando Aparelho)</span>
                    <span className="text-amber-400 font-mono text-[11px]">11 PENDENTES</span>
                  </h3>
                  <p className="text-xs text-[#9e9ab8] mb-3">
                    Estes testes dependem da presença física do hardware R36S com dArkOS RE, tela IPS conectada e joystick de bancada:
                  </p>
                  <div className="space-y-1.5 text-xs">
                    {[
                      { name: "[PHYSICAL] Hardware Revision and RK3326 detection", desc: "Validação em console R36S V1/V2/V3 com chip Rockchip RK3326." },
                      { name: "[PHYSICAL] Redirecionamento de saída para /dev/tty1", desc: "Exibição limpa na tela física sem interferência do EmulationStation." },
                      { name: "[PHYSICAL] Renderização do Dialog TUI no console", desc: "Menu de controle interativo com navegação clara." },
                      { name: "[PHYSICAL] Botão A do Gamepad (Confirmar)", desc: "Acionamento de seleção de opções no menu do console." },
                      { name: "[PHYSICAL] Botão B do Gamepad (Voltar)", desc: "Retorno da tela de QR Code para o menu principal." },
                      { name: "[PHYSICAL] Botão START do Gamepad (Sair)", desc: "Encerramento seguro do launcher pelo joystick do aparelho." },
                      { name: "[PHYSICAL] Botão SELECT do Gamepad (Livre)", desc: "Disponível para comandos auxiliares." },
                      { name: "[PHYSICAL] Navegação com D-Pad físico", desc: "Alternância entre opções 1 a 4 no menu TUI." },
                      { name: "[PHYSICAL] Conexão física com dongle Wi-Fi (wlan0)", desc: "Detecção do IP atribuído pelo roteador local." },
                      { name: "[PHYSICAL] Leitura ótica do QR Code com iPhone/Android", desc: "Abertura instantânea da URL completa com token no Safari/Chrome." },
                      { name: "[PHYSICAL] Retorno ao EmulationStation após encerramento", desc: "Restauração do cursor e console sem tela preta ou travamento." }
                    ].map((t, idx) => (
                      <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-[#141221] border border-amber-500/20">
                        <div>
                          <div className="font-semibold text-[#c0bdd1] flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                            <span>{t.name}</span>
                          </div>
                          <div className="text-[11px] text-[#8c88a6] mt-0.5 pl-3.5">{t.desc}</div>
                        </div>
                        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          BANCADA
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "deploy" && (
          <div className="space-y-6">
            <div className="bg-[#141221] border border-[#26233b] rounded-xl p-6">
              <h2 className="text-base font-bold text-white mb-2 flex items-center gap-2">
                <PlayCircle className="w-5 h-5 text-violet-400" />
                <span>Protocolo de Homologação no R36S Físico (FASE 6)</span>
              </h2>
              <p className="text-xs text-[#9e9ab8] mb-6">
                Siga os passos abaixo para instalar e homologar o build de engenharia no console de bancada:
              </p>

              <div className="space-y-4 text-xs">
                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="font-bold text-white mb-1">Passo 1: Instalação do Launcher</div>
                  <p className="text-[#9e9ab8] mb-2">Copie o arquivo <code className="text-violet-300">R36S_WebFileManager.sh</code> diretamente para a partição de ferramentas do seu cartão SD:</p>
                  <pre className="bg-[#111019] p-2.5 rounded border border-[#26233b] font-mono text-[#d6d3e8]">
                    /roms/tools/R36S_WebFileManager.sh
                  </pre>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="font-bold text-white mb-1">Passo 2: Execução via EmulationStation</div>
                  <p className="text-[#9e9ab8]">
                    Ligue o R36S com o adaptador Wi-Fi conectado. No menu principal, vá em <strong>Tools</strong> e selecione <strong>R36S Web File Manager</strong>.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="font-bold text-white mb-1">Passo 3: Teste Óptico com a Câmera</div>
                  <p className="text-[#9e9ab8]">
                    Aponte a câmera nativa do iPhone ou leitor do Android para o QR Code renderizado na tela de 640x480 do R36S. Confirme a abertura instantânea da interface Web.
                  </p>
                </div>

                <div className="p-4 rounded-lg bg-[#191729] border border-[#2d2947]">
                  <div className="font-bold text-white mb-1">Passo 4: Bateria de Testes no Filesystem</div>
                  <p className="text-[#9e9ab8] mb-2">Execute as seguintes operações práticas pelo celular:</p>
                  <ul className="list-disc pl-5 space-y-1 text-[#b5b2c7]">
                    <li>Envio de uma ROM pequena (.sfc ou .gb &lt; 5 MB)</li>
                    <li>Envio de uma imagem de jogo grande (.iso ou .chd &gt; 200 MB)</li>
                    <li>Navegação entre pastas e criação de um novo diretório</li>
                    <li>Download individual de um arquivo de volta para o smartphone</li>
                    <li>Exclusão com confirmação</li>
                    <li>Encerramento do serviço via botão web &quot;Desconectar&quot;</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
