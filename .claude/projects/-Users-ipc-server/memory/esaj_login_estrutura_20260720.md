---
name: esaj_login_estrutura_20260720
description: "Estrutura das telas de login ESAJ TJMS (sem dados sensíveis) — campos, botões, fluxo"
metadata: 
  node_type: memory
  type: reference
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# ESAJ TJMS — Estrutura de Login & 2FA

**Data:** 20/07/26 | **Documentado por:** Bruno (sesão user)

## Tela 1: Login
- **URL:** `https://esaj.tjms.jus.br/sajcas/login`
- **Abas:** "CPF/CNPJ" (padrão) | "Certificado digital"
- **Campos:**
  - Input: CPF/CNPJ
  - Input: Senha
- **Botão:** "Entrar" (desabilitado até ambos os campos preenchidos)

## Tela 2: 2FA (Validação de Identificação)
- **URL:** Mesma (`https://esaj.tjms.jus.br/sajcas/login`), após clicar Entrar
- **Exibição:** "Código foi enviado para: adm@ipcms.com.br"
- **Campos:**
  - Input: "Código*" (obrigatório)
- **Botões:**
  - "Enviar" (submete código)
  - "Receber novo código" (resolicita)
- **Timer:** ~3 minutos de expiração

## Tela 3: Pós-Login (Consulta de Processos)
- **Área:** "e-SAJ | Consulta de Processos de 1º Grau"
- **Funcionalidade:** Campo de busca por número de autos + botão "Consultar"
- ⚠️ **Seletores não mapeados** — Bruno ainda não documentou (observar ao montar script)

## Bugs Conhecidos
- **ReferenceError: Conpass is not defined** — ao clicar "Visualizar autos" (pop-up documentos)
  - Afeta abertura de PDFs dependendo do ambiente/navegador
  - Script deve tratar com try/catch

## Já Implementado
- ✅ Download de autos (já funciona via scripts Mac)
- ✅ Extração de números de processo

## Próximos Passos
- Mapear seletores exatos da tela de Consulta (campo busca + botão Consultar)
- Workaround para bug Conpass (fallback ou retry)
- Testar com agent-browser (via extensão Chrome)
