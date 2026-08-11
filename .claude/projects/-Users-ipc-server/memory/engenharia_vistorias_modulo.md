---
name: engenharia-vistorias-modulo
description: Módulo Engenharia (vistorias de campo schema-driven) — Fase 1 LIVE; PWA offline/PDF/assinatura/laudo nas próximas fases
metadata:
  type: project
  originSessionId: e5e12bc5-e7a5-4c74-8878-f1788809d4ca
---

# Engenharia — vistorias de campo (Fase 1 LIVE, 10/07/26)

Ferramenta dentro do Perito v6 (`Ferramentas › dropdown Engenharia`) pra os engenheiros
preencherem vistorias em campo. **Motor schema-driven**: cada modelo é um schema JSON e um
único renderizador desenha o formulário (por isso os 4 modelos distintos saem do mesmo motor
e o construtor edita esses schemas).

## Decisões (Bruno, AskUserQuestion)
- PWA offline dentro do Perito v6 (não app à parte).
- Construtor configurável (schema-driven) desde já.
- Vistoria vira dados + PDF anexados ao processo (peça do laudo).
- Os 4 modelos numa tela de escolha; bases comuns reaproveitadas.

## O que já está LIVE (Fase 1)
- Backend: `models/engenharia.py` (ModeloVistoria, Vistoria, VistoriaFoto, VistoriaAssinatura);
  `routes/engenharia.py` (`/api/v1/engenharia/modelos` CRUD, `/vistorias` upsert por `uuid_offline`
  p/ sync offline, `/vistorias/{id}/enviar` vincula processo). Tabelas via create_all.
- Seed: `backend/scripts/seed_modelos_engenharia.py` → 4 modelos: **Avaliação Rural, Benfeitorias,
  Insalubridade, Energisa/Elétrica** (rodar `docker exec perito-v6-backend python3 -m scripts.seed_modelos_engenharia`).
- Front: `pages/EngenhariaPage.jsx` (renderizador dinâmico: text/textarea/number/date/boolean/
  select/multiselect/tabela/gps/foto + condicional `mostrar_se`), dropdown na `FerramentasPage.jsx`,
  rota `/ferramentas/engenharia` no App.jsx.
- Fotos com flag obrigatória/acessória (preview base64 provisório); tabela repetível (equipamentos);
  GPS via navigator.geolocation; validação de obrigatórios no Enviar.

## Feedback Joyce (Eng.) — 6 ajustes FEITOS + verificados ao vivo (10/07)
(1) BUG crítico: digitação perdia foco — `Campo` era componente aninhado → movido p/ TOP-LEVEL.
(2) Editar vistoria (botão na lista) + reusa `uuid_offline` (não duplica). (3) Excluir foto (✕).
(4) Msg "salvo" foi p/ o rodapé. (5) Anexos de documentos (planta baixa/matrícula). (6) Benfeitorias
virou **blocos repetíveis** (novo tipo de campo `blocos`): cada benfeitoria com identificação + área
total + specs + fotos próprias. Bônus: rodapé sticky cobria o botão → virou estático. Rascunho×enviada
explicado. Renderer novo suporta `blocos`. ⚠️ re-seed exige rebuild do BACKEND (seed é baked na imagem).

## Status 10/07: equipe testando a Fase 1
URL/atalho do Bruno: **https://sistema.ipcms.com.br/ferramentas/engenharia**.
Ao retomar, começar pela **Fase 2 (offline PWA)** — salvo feedback dos testes da equipe.

## Próximas fases (A FAZER)
2. **Offline PWA**: service worker + IndexedDB (modelos + vistorias + fotos) + sincronização.
3. **Fotos em storage real** (hoje base64 no JSONB) + **assinatura desenhada** (canvas) + PDF com fotos/assinaturas.
4. **Construtor visual** (admin cria/edita modelos pela tela) + **rascunho de laudo via Qwen** a partir dos campos.

## Aprendizado (bug do deploy)
FK deve ser `ForeignKey("usuario.id")` — a tabela de usuários chama-se **`usuario`**, não `user`
(processo.py tem o mesmo erro latente que nunca disparou porque a tabela dela já existia). Um FK
errado quebra o `create_all` e derruba o backend em crash-loop. Deploy = rsync Mac→VPS
(`/var/www/perito-v5.2/v6`) + `docker-compose build` + seed. Ver [[v6-correcoes-producao]].
