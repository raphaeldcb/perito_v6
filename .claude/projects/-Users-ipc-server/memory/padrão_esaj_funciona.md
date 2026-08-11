---
name: padr-o-esaj-funciona
description: Padrão de automação ESAJ que FUNCIONA — login + busca + download
metadata: 
  node_type: memory
  type: reference
  session: 20260717
  status: VERIFICADO E FUNCIONAL
  autor: Bruno (v5 pattern) + Claude (Selenium Mac)
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# ✅ PADRÃO ESAJ FUNCIONAL

## Sequência Comprovada (17/07/26)

**1️⃣ Login (CPF/Senha)**
- Limpar campo com `execute_script("arguments[0].value='';", element)` ANTES de digitar
- Usar IDs: `usernameForm` (CPF), `passwordForm` (Senha)
- Click FALLBACK: try normal, except `execute_script("element.click()")`
- Esperar 3s após click

**2️⃣ 2FA**
- Detectar campo `#tokenInformado`
- **PADRÃO ATUAL**: Digitar manualmente (Bruno digita do email)
- **PADRÃO FUTURO**: Loop 20x na API (5s entre tentativas)
  ```python
  for i in range(20):
      codigo = requests.get("https://sistema.ipcms.com.br/api/v1/esaj/codigo-2fa",
                           headers={"X-Agent-Key": agent_key}).json().get("codigo")
      if codigo:
          break
      time.sleep(5)
  ```
- Click Enviar com fallback JS
- Aguardar elemento desaparecer (máx 30s)

**3️⃣ Busca + Download**
- Navegar: `https://esaj.tjms.jus.br/cpopg5/open.do`
- Preencher: número (13 dígitos), comarca (4 dígitos)
- Buscar: clique + fallback JS no botão "Consultar"
- Visualizar autos, selecionar, versão impressão
- Modal: Continuar, Ok aviso, Download

## Problema Atual

**API 2FA retorna None**
- `.perito_agent_key` pode estar:
  - ❓ Inválida
  - ❓ Expirada
  - ❓ Sem permissão
  - ❓ Arquivo não existe

**Investigação pendente**: Verificar endpoint real, testar com curl, validar agent key.

## Arquivo Salvo

- **consultaesajms.py** — Script completo em `/Users/ipc_server/Downloads/`
- Usa padrão v5 (pronto pra Cérebro/agente Windows)

## Regra Bruno

- Código 2FA: pegue do email (lido, arquivo morto)
- Não precisa ser automático por enquanto (manual OK)
- Padrão final: API sempre funciona
