---
name: azure_keyvault_access
description: Azure Key Vault access pattern — MEMORIZAR para nunca perder credenciais
metadata: 
  node_type: memory
  type: reference
  session: 20260714
  critical: true
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# 🔑 Azure Key Vault — Como Acessar (MEMORIZAR)

## Vault Principal
```
Vault Name: ipcms-perito-secrets
URL: https://ipcms-perito-secrets.vault.azure.net/
Region: eastus
Owner: IPC (Bruno)
```

## Secrets Armazenadas (14/07/2026)

| Secret Name | Value Type | Location | Access |
|---|---|---|---|
| GRAPH-CLIENT-SECRET | secret | Azure Portal | Copy to .env |
| AGENT-API-KEY | secret | Azure Portal | Copy to PowerShell |
| JWT-SECRET | secret | Azure Portal | Copy to .env |

## Como Acessar (Python)

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(
    vault_url="https://ipcms-perito-secrets.vault.azure.net/",
    credential=credential
)

# Ler secret
secret = client.get_secret("GRAPH-CLIENT-SECRET")
print(secret.value)  # ← o valor real
```

## Como Acessar (CLI — Azure Portal)

1. Login: `az login`
2. List secrets: `az keyvault secret list --vault-name ipcms-perito-secrets`
3. Get secret: `az keyvault secret show --vault-name ipcms-perito-secrets --name GRAPH-CLIENT-SECRET`

## Backend .env Integration

```bash
# VPS: /var/www/perito-v6/backend/.env
AZURE_KEY_VAULT_URL=https://ipcms-perito-secrets.vault.azure.net/

# Backend code: app/config.py
client = SecretClient(vault_url=settings.AZURE_KEY_VAULT_URL, credential=credential)
GRAPH_CLIENT_SECRET = client.get_secret("GRAPH-CLIENT-SECRET").value
```

## NUNCA fazer

- ❌ Guardar secrets em .env (use Vault)
- ❌ Guardar secrets em logs
- ❌ Guardar secrets em git
- ❌ Imprimir secrets no console

## SEMPRE fazer

- ✅ Usar DefaultAzureCredential (busca do Vault)
- ✅ Rotacionar secrets periodicamente
- ✅ Auditar acesso via Azure Monitor
- ✅ Salvar referência do Vault (esta página) em memória

---

**Criado**: 14/07/2026
**Próxima revisão**: 31/07/2026 (rotação de secrets)
