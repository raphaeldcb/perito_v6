# Memory Index — ipc_server

## Projetos (Em Progresso)
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
- [Phase 2: Azure Key Vault (22/07)](phase2_azure_keyvault_22_07.md) — migrar secrets .env → Vault seguro, 90min, pronto deploy
- [Feedback: Nunca destruir sistema](feedback_nunca_destruir_sistema.md) — regra crítica — rollback plan, staging test, sem reset/clean destructivos
