---
name: feedback_nunca_destruir_sistema
description: "Instrução crítica — ao implementar mudanças, NUNCA destruir ou quebrar sistema funcionando"
metadata: 
  node_type: memory
  type: feedback
  session: 20260714
  critical: true
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# 🚨 FEEDBACK: NUNCA DESTRUIR O QUE FUNCIONA

**Instrução do Bruno**: "faça tudo mas, nunca destrua oq está funcionando no sistema"

## Regra

Ao implementar remediações de segurança, melhorias, ou qualquer mudança:

1. **NÃO apagar código que está rodando** sem antes ter substituição pronta
2. **NÃO fazer reset/rebase** em commits já publicados sem avisar
3. **NÃO remover dependências** que estão em uso (mesmo que "unused")
4. **NÃO limpar databases/backups** até validar que novo sistema está 100% funcional
5. **NÃO parar serviços** sem ter plano de fallback
6. **NÃO editar .env** sem teste de compatibilidade primeiro

## Abordagem Segura

✅ **Sempre fazer**:
- Implementar feature nova em paralelo (não sobrescrever)
- Testar em staging antes de produção
- Manter rollback plan (versão anterior acessível)
- Fazer backup ANTES de qualquer alteração crítica
- Avisar usuários de downtime antecipadamente (se necessário)
- Verificar dependências antes de remover (grep, imports, etc.)

❌ **Nunca fazer**:
- `git reset --hard` sem avisar
- `rm -rf` em diretórios produção sem backup
- Editar código crítico sem teste
- Remover secrets de .env sem ter Vault pronto
- Parar containers sem ter health check passando

## Contexto

Sistema Perito v6 está **LIVE em produção** com dados reais de 828+ processos judiciais. Qualquer downtime ou corrupção de dados = dano direto ao negócio e clientes jurídicos.

## Como Aplicar

Ao planejar implementação:

1. Ler este feedback
2. Fazer plano com rollback explícito
3. Testar em staging (VPS DEV) primeiro
4. Avisar Bruno antes de mudanças que afetam disponibilidade
5. Monitorar logs pós-deploy
6. Ter plano de reversão rápida (< 15min)

---

**Criado**: 14/07/2026  
**Próxima aplicação**: Phase 2 (22/07) — Azure Key Vault migration  
**Status**: ✅ Memorizado para futuras ações

