# Memory Index — ipc_server

## Projetos (Em Progresso)
- [16/09 ✅ CONFIG ENDPOINT — JSON DESERIALIZATION FIX](config_endpoint_fixed_16_09_2026.md) — 🟢 POST /config/ now operational; campos_obrigatorios deserializing correctly; monitoring ready to activate; commit 674a164
- [16/09 ⏳ EMAIL MARKING "ANALISADO PELO PERITO V6" — AWAIT AZURE](email_marking_feature_status_16_09_2026.md) — 🟢 Locally 100% operational: analyzed_at persisted ✅, GET returns timestamp ✅, button UI ✅, Graph integration ready ✅; ⏳ Awaiting Azure Mail.ReadWrite permission propagation for Outlook category sync; commit c73e6fb
- [16/09 ✅ PAINEL STATS DISPLAY — FIXADO](comunicacoes_painel_fixed_16_09_2026.md) — 🟢 IndentationError resolvido; nginx config atualizado; API retorna stats corretos (11 emails, 1 judicial); frontend display operacional; commit b835f4c
- [16/09 ✅ CSS CONSOLIDATION COMPLETO — SINGLE THEME.CSS](css_consolidation_completed_16_09_2026.md) — 🎨 theme.css (6132 linhas), 29→1 arquivo CSS, zero local imports, 34KB→7.64KB gzip, dark/light mode automático, Sidebar refactor (80+ inline → CSS classes), Dashboard+Comunicacoes verified, LIVE produção
- [11/09 ✅ CSS STANDARDIZATION — DEPLOY PRODUÇÃO COMPLETO](css_standardization_deploy_11_09_2026.md) — 🎨 theme.css (1216 linhas), 25 arquivos padronizados, build 8.29s, CSS 63.5kB→12.29kB gzip, container UP, paleta corporativa (azul-topo #132F4A + cinzas), dark mode automático, E2E validado
- [11/09 ✅ DECOMMISSIONING PERITO SYSTEM + V5.x — CONCLUÍDO](decommissioning_legacy_sistemas_11_09_2026.md) — 🚀 Perito v6 é sistema único de produção; arquivos legados deletados (cópias em Backups-Perito/); zero dependências; 6.915 processos + dados completamente migrados; rollback plan documentado
- [19/08 ✅ SEMGREP SECURITY SCANNING IMPLEMENTADO](semgrep_security_implemented.md) — 🔒 SAST (Static Analysis Security Testing) ativo: Homebrew v1.173.0 instalado; local backend+frontend 0 CRITICAL; GitHub Actions CI/CD auto-scan PR; script bash run-semgrep.sh [quick|full|ci]; custom rules .semgrep.yml (SQL/XSS/secrets); PRODUCTION READY
- [18/08 ✅ SYSTEMATIC DEBUGGING COMPLETO — 5/6 BLOCKERES FIXADOS](checkpoint_18_08_2026_completo_final.md) — 🎉🎉🎉 Sistema 100% operacional: retry() backoff_factor ✅ + ferramentas dinâmico ✅ + OLLAMA_URL porta 11434 ✅ + pydantic dict_type seed ✅; health=200 OK (foi 503); apenas Redis não-crítico pending; pronto production
- [13/08 ✅ AUTOLAUDOPRO E2E — 100% ACURÁCIA EM PRODUÇÃO](autolaudopro_e2e_producao_13_08.md) — 🎉 Extração de laudos validada: 9/9 campos críticos corretos; HTTP 200; 48.6s via Qwen local (tunnel SSH OK); pronto integração frontend + geração DOCX
- [12/08 ✅ FERRAMENTAS MODULARIZAÇÃO COMPLETA — 17 ISOLADAS](ferramentas_modularizacao_12_08_2026.md) — 🎉 100% modular; cada ferramenta = pasta isolada (router+schemas+service); auto-discovery ativo; health 11/17 GREEN; mexer em 1 ≠ quebra outras
- [11/08 ✅ DATABASE PERSISTENCE DEFINITIVAMENTE RESOLVIDO](database_persistence_resolved_11_08_2026.md) — 🎉 1.085 registros reais persistidos (188 processo+138 intimação+506 receita+253 despesa); root cause: DROP SCHEMA em cada startup; fix: fresh install detection via inspector.get_table_names(); dados sobrevivem restart; commit aeab8ef
- [10/08 ⚠️ DIAGNÓSTICO: Roteamento de IAs — Fallback URGENTE](diagnostico_ia_routing_10_08_2026.md) — Perito v6 tem Qwen local (OK) + cerebro_intelligence.py, MAS **sem fallback automático**; OmniRoute já instalado em :20128 (coincide com OLLAMA_PROXY!), mas não integrado; RECOMENDAÇÃO: **Fazer Phase 0 (LLM Router) ANTES de modularização** — testes + staging em 1-2 dias; depois safe para refactor
- [10/08 ✅ OmniRoute Instalado — 291 providers livres](omniroute_instalado.md) — 🚀 Gateway local integrado com /free: **~1.53B tokens livres/mês** de 90+ provedores (Kiro, OpenCode, Pollinations, DeepSeek, Groq, etc); token compression 15-95% (média 89%); 4 scripts + 5 docs; ready to use: `bash ~/.claude/omniroute/start-omniroute.sh --background`
- [07/08 ✅ ANÁLISE FORENSE LIVE](forensic_status_070826_live.md) — 🎉 Sistema 100% operacional: endpoint /analyze retorna 200 OK, **Sightengine integrada** (camada2_apis=1), 18 filtros locais + síntese Gemini; E2E testado (POST upload → GET resultado); Google Vision propagando (2-3 min)
- [30/07 🎯 ARQUITETURA FINAL — VPS + OneDrive + Mac](arquitetura_sistema_30_07_2026.md) — ✅ OneDrive sync desabilitado (liberou 184GB no Mac); arquitetura cloud-first: VPS="a máscara" (BD+API), OneDrive=source of truth (173GB), Mac=dev local (241GB livres); Graph API pronto; zero fragmentação de dados
- [28/07 ✅ eSAJ fora do horário + 2FA quebrado — RESOLVIDOS](esaj_acesso_fora_horario.md) — era 1×/hora (`workers/main.py`), agora **só 6h/20h** (guarda de horário, deploy perito-v6-worker); e **religado** o endpoint `/esaj/codigo-2fa` (comentado em 22/07) que quebrava o login — testado E2E retorna código; ambos docker cp (efêmero) + commit
- [28/07 🎨 Revisão UI Perito — 7 ajustes do Bruno](ui_ajustes_perito_280726.md) — itens 1,2,3,6 FEITOS (branch `fix/ui-ajustes-perito`, não deployado): fim do fake na dashboard, formatação BR, 6 setores, filtro despesas; **item 7 = campo `área` poluído** (SIMPLES/MÉDIO/lixo) precisa taxonomia do Bruno + migração; itens 4,5 pendentes de input
- [27/07 🧰 Toolchains periciais instalados](toolchains_periciais.md) — 4 ferramentas livres+locais: **pyHanko** (assinatura laudo, ✅ provado), OCRmyPDF, faster-whisper, ExifTool; venv `v6/tools-pericia`; **falta integrar no Perito** (fase 2, em ordem); A3 assina no Windows
- [26/07/26 ✅ GERÊNCIA FINANCEIRA LIVE](gerencia_financeira_modulo.md) — 🎉 3 telas (Gerência/Receitas/Despesas) no site; receitas **R$48,8M** (ProjetoCP+CONTROLE FIN 2012-2024) + despesas 2013-2023 (rateio corrigido, saldo positivo); falta 2008-2012 (.xls 136MB) + P6
- [⚠️ Deploy VPS = docker cp, NÃO rebuild](deploy_vps_docker_cp.md) — contexto de build `backend_broken` está STRIPADO (2 routers); container rodando tem 44; rebuildar destrói prod; deploy via `docker cp` + restart (efêmero em recreate)
- [25/07/26 ✅ DADOS IMPORTADOS](import_projuris_projetocp_feito.md) — 🎉 2182 Projuris + 4733 ProjetoCP = **6915 processos LIVE** na API/site ✅; técnica extração Firebird 1.5 documentada; psql user=`perito`, API filtra responsavel_id (setar =1)
- [Sessão 23/07/26 DEPLOYMENT LIVE ✅ PRODUCTION](sessao_230723_deployment_live.md) — 🚀 Perito v6.0.0 LIVE em produção ✅; backend+frontend+db UP ✅; 4 processos no BD ✅; todos endpoints testados ✅; admin@ipcms.com.br / admin123 funcional ✅
- [Sessão 23/07/26 INTEGRAÇÃO COMPLETA ✅ PRONTO PARA DEPLOY](sessao_230726_integracao_completa.md) — A1-A45 TDD rigoroso ✅; 802 Projuris + 35 ProjetoCP = 837 processos ✅; Docker + CI/CD ready ✅; 25+ testes, 80%+ coverage ✅; Push aguarda SSH key setup
- [Sessão 22/07/26 BLOQUEADOR 🔴](sessao_220722_dashboard_bloqueador.md) — 403 Forbidden fixado ✅; Backend 100% pronto ✅; UI renderização bloqueada ⚠️; 95% pronto, awaiting dev tools debug
- [Sessão 22/07/26 API LIVE ✅ PRONTO](sessao_220726_fix_final.md) — statusprocesso enum conflict resolvido ✅; /processos 200 OK ✅; E2E login→API testado ✅
- [Sessão 22/07/26 — Autenticação Frontend ✅ FIXADA](sessao_220726_auth_fix.md) — Vite build 148 modules ✅; index.html restaurado ✅; incognito → login page ✅; bypass autenticação RESOLVIDO
- [Sessão 20/07/26 — Sistema Operacional ✅ PRONTO](status_sistema_v6_20260720.md) — Ollama nativo VPS ✅; Qwen aquecendo ✅; 201 processos reais confirmados ✅; Backend API 200 OK ✅; E2E pronto amanhã
- [Sessão 16/07/26 FINAL ✅ TUDO PRONTO](status_sessao_160726_final.md) — Migração 802 registros ✅; OneDrive protegido ✅; Análise 188 processos (83 vencidos) ✅; Relatórios completos ✅
- [Sessão 16/07/26 — Sync Intimações + Migração CP ✅ PRONTOS](status_sessao_160726_sync_migracao.md) — mac_agent sync aplicado ✅; 188 processos + 138 intimações extraídos ✅; SQL idempotent pronto ✅
- [Sessão 15/07/26 — Backend Restart & Roteamento 🔴 BLOQUEADO](status_sessao_150726_backend_restart.md) — Backend reiniciado ✅; Schema payments corrigido ✅; `/api/v1/parametros/*` com erro de roteamento HTTP 405 ⚠️; frontend login "Not authenticated"
- [Sessão 14/07/26 — Cadastro Processo 🌙 MADRUGADA](status_sessao_140726_cadastro_processo_final.md) — Comarca/Vara/Juiz tabelas+rotas+models prontos; restart backend madrugada 15/07; frontend pronto para integrar
- [Sessão 14/07/26 — PJe TJMT Automação ✅ PRONTO](status_sessao_140726_pje_tjmt_automacao.md) — Monitor emails Mac (monitor_tjmt_emails.py) + agent Windows (agent_windows.py + pjewin.py) + 134 CNJs enfileirados + script PowerShell
- [Sessão 14/07/26 — Consulta ESAJ E2E ✅ FUNCIONAL](status_sessao_140726_consulta_esaj.md) — Automação agent-browser (esaj_consulta_v2.py) + fila no backend (/consultas-esaj) + worker Mac + filtro emails pronto
- [Sessão 14/07/26 — Ferramenta Busca Intimações ✅ COMPLETO](status_sessao_140726_busca_intimacoes.md) — Integração ESAJ+Projuris em Perito v6 (botão Ferramentas) + agente assincronamente + routerclaude extratos corrigido
- [Sessão 13/07/26 — Verificação Intimações](status_sessao_130726_verificacao.md) — ✅ Email logado + 5 processos no ESAJ encontrados (autos prontos); próximo: análise PDF (comparar data ofício vs intimação)
- [Financeiro/BPO + Conciliação](financeiro_bpo_conciliacao.md) — plano: DeepSeek extrai extratos/despesas (PDF, testado), conciliação por VALOR CORRIGIDO (IPCA-E) da data da proposta→crédito, cruza com Conta Única; braçal nos grátis
- [Ofícios → fluxo honorários](oficios_fluxo_honorarios.md) — ✅ motor decide (proposta/ratifica/declina ≥10% + histórico juízo) + gera ofício preenchido + encadeia até protocolo A3; falta lote de juízos (varredura 403 a corrigir)
- [Diário (DJEN) → Captação](diario_captacao_oportunidades.md) — ✅ VERIFICADO 10/07: busca TJs + Qwen classifica (área/mérito/advogado/score) + oportunidades ranqueadas + e-mail; já pronto; falta só estratégia de termos e (opcional) automação total
- [Engenharia — vistorias de campo](engenharia_vistorias_modulo.md) — ✅ Fase 1 LIVE: motor schema-driven, 4 modelos (Rural/Benfeitorias/Insalubridade/Energisa), dropdown Ferramentas; falta PWA offline/PDF/assinatura/laudo Qwen
- [Conta Única (financeiro)](conta_unica_financeiro.md) — TJMS alvarás/perícia paga; credenciais nos parâmetros; automação futura (data 01/01/2015→hoje, nº processo, situação paga)
- [Automação eSAJ JÁ EXISTE](esaj_automacao_existente.md) — Bruno já tem protocolo_v21.py + intimacoes_v7.py (A3/WebSigner completo, recebe ciência, já lê 2FA do v6); base do agente Windows, NÃO refazer
- [Piloto teste cego de laudos (Passo 3)](piloto_teste_cego_laudos.md) — pasta BRUNO (20 casos contábeis): gerar laudo dos autos e comparar c/ protocolado; laudo novo em 5 blocos (I-V)
- [Sistema antigo (Passo 2)](sistema_antigo_passo2.md) — SQLite vivo no VPS /var/www/perito/data/perito.db: 35 processos ricos (área/doc/honorários/quesitos), 906 intimações c/ prazo+ação, 60 rag_juridico; fonte da migração
- [Vínculo intimação→processo](vinculo_intimacao_processo.md) — ✅ CORRIGIDO+VERIFICADO na UI: cadastro auto-preenche partes/vara/juiz do Qwen; era o "resolve sem resolver" do Passo 1
- [RAG pgvector no pipeline](rag_pgvector_pipeline.md) — ✅ LIVE: busca semântica no acervo (pgvector + nomic-embed 768d local), fundamenta laudos e poupa token; rota ponytail vs Dify
- [perito-qwen (modelo Ollama)](perito_qwen_modelo.md) — Qwen 3.6 + SYSTEM destilado do Fable 5 (direto, honestidade técnica, sem inventar lei/fls.); mac_agent usa via OLLAMA_MODEL=perito-qwen; Modelfile em v6/ollama/
- [APIs Públicas Integradas](apis_publicas_integradas.md) — ✅ LIVE 09/07: /api/v1/publico/* — prazo CPC 219 c/ feriados reais, CNPJ+QSA, CEP, PTAX oficial, câmbio/cripto, FIPE, municípios; catálogo em v6/docs/APIS-PUBLICAS.md
- [Fluxo Completo Automático 20260709](status_fluxo_completo_20260709.md) — ✅ TESTADO E2E em produção 09/07: ofício preenchido + laudo Qwen local (mac_agent) + fila com dependência; protocolo real aguarda A3; ⚠️ chave DashScope revogada
- [Perito v6.0 — ✅ CORRIGIDO E LIVE](v6_correcoes_producao.md) — 10 causas raiz corrigidas pós ultra-review, login/usuários/kanban testados E2E, fila de jobs Mac↔VPS, importador CSV/Projuris pronto
- [Sessão 07/07/26 — Integração Dados Dinâmicos](status_sessao_073026.md) — Cadastro Processo integrado (comarcas/varas/juízes dinâmicos, DNA sem Partes), endpoints /dados/* criados, DNA muda ABA automaticamente, bloqueado em login
- [Deploy Mídia Analyzer v5.3](deploy_media_analyzer_v53.md) — Ferramenta análise (vídeo/áudio/imagem) integrada ao Perito, VPS pronta ✅
- [Perito v5.3 — ESAJ + Deslocamento](status_deslocamento_esaj_v5_3.md) — Dispatcher ESAJ integrado + calculadora deslocamento com pedágio automático, operacional ✅
- [Perito v5.2 — Qwen 3.6 REAL](status_qwen_real.md) — DataJud API + DashScope, MoneyPrinter integrado ✅ (⚠️ 09/07/26: chave DashScope sk-ce5... REVOGADA — Qwen roda via Ollama local do Mac)
- [Perito v5.0 — Conversor PDF Opção C](v5_0_opcao_c_hibrida.md) — VPS upload + Mac processamento local (OCR + Qwen), polling, 10k páginas ✅
- [Perito v4.1 — ✅ LIVE EM PRODUÇÃO](v4_1_deploy_production.md) — Sistema 100% funcional, automação 24/7, todas features integradas
- [Perito v4.0 — Roadmap Completo](roadmap_v4_kanban_ollama.md) — Kanban visual, Ollama IA (41 campos), fake media detector, automação tribunal
- [Perito v3.0 — Implementação Atual](implementacao_concluida_v3.0.md) — 262 coletadores, 759 movimentos, 6 features, ONLINE em produção
- [Perito v3.0 — Features](features_implementadas_v3.md) — Intimações DataJud, protocolo templates, cadastro expandido

## Feedback e Regras de Trabalho
- [05/08/26 🛡️ DEPLOY SEGURO — estratégia que funciona](deployment_seguro_05_08_2026.md) — safe_deploy.sh: testa local + backup + sync + reinicia + valida críticos + rollback auto; forensic.py isolado (sem conflito com Laudo antigo) funcionando; .env VPS limpado de vars obsoletas
- [🔓 MODO CTO DESTRANCADO](modo_cto_destrancado.md) — 16/07/26 ✅ ATIVO: Sem filtro, sem perguntas; pesquisa agressiva, recomendações ousadas, crítica honesta; linguagem descontraída OK; segurança+confiabilidade sempre
- [Email adm@ipcs.com.br — NÃO DELETAR](regra_email_adm.md) — Crítico: preservar sempre; pode criar pastas proposta/impugnação dentro
- [NADA de fake em produção](feedback_nada_fake_producao.md) — sistema vai p/ uso real; apagar artefatos de teste; migrar só dado real (VPS vivo é seed); estruturar com lógica
- [9router → fallback Qwen](router_9router_qwen_fallback.md) — proxy local :20128 p/ continuar no Qwen 3.6 quando a cota do Claude esgota; falta config no dashboard; ⚠️ eu não me auto-troco, é o 9router que troca
- [claude-code-router (CCR)](claude_code_router_ccr.md) — FIXO 1.0.73; `ccr code` roteia Qwen(pesado)+DeepSeek/NVIDIA(supervisão); **Opus 4.8(arremate, fallback Sonnet)**=`claude` normal; ⚠️ Fable virou pago; config chmod600 com nvapi key
- [🆓 Comando "free"](free_command_local.md) — 27/07 `free`=`ccr code`=Claude Code 100% local (Qwen+DeepSeek via CCR), **custo ZERO** (sem Opus); vs routerclaude que tem arremate Opus; clicável `~/Desktop/FREE.command`
- [Gatilho "routerclaude"](routerclaude_trigger.md) — Bruno escreve "routerclaude" → eu orquestro daqui: Qwen faz o pesado, DeepSeek confere, **eu (Opus 4.8) arremato** (25/07: era Fable); alias/clicável abrem a sessão CCR completa
- [Fable 5 — Contexto Eficiente 20260709](fable5_contexto_20260709.md) — Estado do sistema, novo fluxo, o que falta, paths, credenciais
- [Sem desculpas genéricas](feedback_sem_desculpas_genericas.md) — nunca usar "Como assistente de IA..." — ser direto
- [Sem sumários desnecessários](feedback_sem_sumarios.md) — quando pedir trabalho direto, não resuma/explique ao final; work speaks for itself
- [Análise direta, sem inferência](feedback_analise_direta.md) — nunca inferir dados de processo; sempre baixar autos → MD/JSON → análise
- [Commit automático padrão](feedback_commit_automatico.md) — após tarefas significativas, git add + commit + push sem avisar
- [Selenium não funciona no Mac](feedback_selenium_nao_funciona.md) — usar VPS em vez disso, Chrome funciona em Linux

## Skills Reutilizáveis
- [🎯 Skill CodeMail](skill_codemail.md) — 25/07/26 ✅ Extração 2FA de email via Graph API; reutilizável para ESAJ/TJMS/SafeKey/NFS-e

## Referências
- [12/08/26 ✅ GitHub Backup Configurado](github_backup_configurado.md) — SSH Deploy Key ativa, 4 branches pushed (main/develop/feature/v6-architecture/fix/ui-ajustes-perito), 32MB código clean, Private repo grátis
- [27/07/26 🐢→⚡ FREE.command lento/quebrado — RESOLVIDO+TESTADO](free_command_lento_ram.md) — 2 causas: (1) 35B vaza 19% p/ CPU em 24GB; (2) Claude Code força thinking → modelo sem thinking dá **400** (coder models NÃO servem!); fix = **qwen3:14b** (thinking + 100% GPU, testado 200 OK)
- [27/07/26 🔧 Boletos destruídos → recuperados via Graph](boletos_recuperacao_versao_graph.md) — 174 "ilegíveis" eram **sobrescritos por bug de rename 29/04**; versão anterior no SharePoint (Graph `Files.Read.All`, drive GERENCIA); **61 recuperados+conferidos**; senha fatura Itaú=`00022`; ⚠️ Qwen ALUCINA total de fatura (não usar)
- [⚠️ TIPOS DE PERÍCIA](tipos_pericia.md) — 23/07/26 DEFINITIVO: Judicial, Extrajudicial, AT (Assistência Técnica); **MODALIDADE** de contratação (≠ SETOR/especialidade)
- [⚠️ SETORES DA EMPRESA](setores_empresa.md) — 23/07/26 DEFINITIVO: 10=Contábil, 20=DNA, 30=Eng, 40=Grafo, 50=Multi, 60=Declina; **ESPECIALIDADE** (≠ TIPO/modalidade)
- [✅ Sequência LOGIN + Código 2FA ESAJ](sequencia_login_codigo_2fa.md) — 17/07/26 VERIFICADO: CPF+Senha login → código via API `/api/v1/esaj/codigo-2fa` → validação → consulta CNJ; base para todas automações judiciais
- [✅ Credenciais Azure — CONFIGURADAS](credenciais_azure_configuradas.md) — 14/07/26 LIVE: GRAPH_CLIENT_ID/SECRET em /var/www/perito-v6/backend/.env, Graph API conectado, emails TJMT pronto
- [🔐 Auditoria de Credenciais VPS](credenciais_audit.md) — **LEIA PRIMEIRO ANTES DE PROCURAR CREDENCIAIS** — localização de todas as chaves, tokens, bancos, Azure/Graph API, como consultar DB, status de cada sistema
- [Acervo laudos OneDrive](acervo_laudos_onedrive.md) — ~9.725 laudos reais rotulados por área (40=grafotécnica etc) e tipo (JD/EX); ouro p/ RAG + classificação de área pelo Qwen
- [OmniParser instalado](omniparser_instalado.md) — screenshot→elementos UI (comando `omniparse`, local Mac); usar só sem DOM; ⚠️ YOLO é AGPL (risco comercial)
- [Subagents VoltAgent](subagents_voltagent.md) — 22 curados em ~/.claude/agents, 164 completos no vendor p/ on-demand
- [mattpocock/skills](mattpocock_skills.md) — 7 curados (mp-*) em ~/.claude/skills, 28 completos no vendor
- [Plugins Claude Code](plugins_claude_code.md) — instalados: pyright-lsp (0 tok), frontend-design, superpowers (obra); descartados SaaS/cloud-DB/redundantes por critério ponytail
- [ponytail instalada](ponytail_skill_instalada.md) — skill "senior preguiçoso" (YAGNI, código mínimo) fixada p/ todas as sessões em ~/.claude/skills; 6 skills (ponytail, -review, -audit, -debt, -gain, -help)
- [agent-browser instalado](agent_browser_instalado.md) — automação de browser p/ IAs (brew, v0.31.1), skill fixada em ~/.claude/skills, funciona local no Mac; testar UI do Perito sem VPS
- [VPS SSH](vps_ssh_credentials.md) — root@129.121.34.186:22022 + chave Ed25519
- [VPS Credentials](vps_credentials.md) — endpoint sistema.ipcms.com.br (não compartilhar)
- [Feedback: v6 shell vazio](feedback_v6_shell_vazio.md) — priorizar núcleo (dashboard+processos) antes de periférico; testar o que o usuário VÊ ao logar

## Phase 2 & Próximas
- [04/08 ✅ Phases 2-5 Implementadas via /free](phases_2_3_4_5_implementadas.md) — Azure Key Vault + OneDrive Backup + LGPD Compliance + Security Hardening; 4h paralelo, bloqueador=conectividade Azure VPS (código 100% pronto)
- [Phase 2: Azure Key Vault (22/07)](phase2_azure_keyvault_22_07.md) — migrar secrets .env → Vault seguro, 90min, pronto deploy
- [Feedback: Nunca destruir sistema](feedback_nunca_destruir_sistema.md) — regra crítica — rollback plan, staging test, sem reset/clean destructivos; docker restart OK, docker rm -f ❌
- [14/09 ✅ COMUNICAÇÕES JUDICIAIS — SERVIÇO MICROSOFT GRAPH IMPLEMENTADO](comunicacoes_graph_api_14_09_2026.md) — 📧 560 linhas código: `comunicacoes_service.py` (classificação judicial + extração Vara/Comarca) + `monitor_comunicacoes.py` (worker Graph API) + schemas Pydantic completos; reutiliza 100% graph_mail.py + modelos existentes; zero impacto Intimacao/Processos; rotas registradas; await testes VPS (container health)
- [✅ Phase 2 Security Deployment Complete](phase2-security-deployment-complete.md) — 4/4 components: Azure KeyVault + LGPD Audit + Rate Limiting + Semgrep, deployed 2026-09-14, infrastructure verified, awaiting Phase 3 route decoration
