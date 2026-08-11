---
name: sequencia_login_codigo_2fa
description: Sequência completa de LOGIN + código 2FA via API para ESAJ TJMS
metadata: 
  node_type: memory
  type: reference
  session: 20260717
  status: VERIFICADO — funciona até passo 5
  originSessionId: dcebcc85-5ffd-487b-bfef-21b2e9f16b0d
---

# ✅ SEQUÊNCIA CORRETA: Login + Código 2FA ESAJ

## O que funciona (VERIFIED)

1. **Abrir ESAJ**: `https://esaj.tjms.jus.br/sajcas/login#aba-cpf`
2. **Login (CPF/Senha)**:
   - Campo CPF: `//input[@placeholder='Digite seu CPF/CNPJ.']` → `00022358110`
   - Campo Senha: `//input[@placeholder='Digite sua senha']` → `Bruno@841124`
   - Botão: `//button[@type='submit'] or //input[@name='pbEntrar']`
3. **Aguardar 8s** → redireciona automaticamente pra página de validação
4. **Pegar código via API** (NO PONTO DE VALIDAÇÃO):
   ```python
   import requests
   from pathlib import Path
   
   key_file = Path.home() / ".perito_agent_key"
   agent_key = key_file.read_text().strip()
   
   r = requests.get("https://sistema.ipcms.com.br/api/v1/esaj/codigo-2fa",
                    headers={"X-Agent-Key": agent_key}, timeout=15)
   codigo = r.json().get("codigo")  # Retorna string ex: "331660"
   ```
5. **Preencher código** na página de validação:
   - Campo: `//input[@id='tokenInformado']` (NOT name="codigo")
   - Enviar: `//button[contains(text(), 'Enviar')]`

## O que FALTA (BLOQUEADO)

- ❌ Passo 6: Após enviar código, não redireciona pra página de busca CNJ (timeout mesmo com 60s)
  - Possível causa: código inválido, sessão expirada, ou erro na validação
  - **Precisa testar manualmente** ou verificar resposta HTTP

## IMPORTANTE

- **NÃO FECHAR CHROME**: após login bem-sucedido, MANTER SESSÃO ABERTA
- **REUSAR EM OUTRAS AUTOMAÇÕES**: esse padrão é base pra intimações, downloads, etc.
- **CREDENCIAIS**:
  - Usuário: `00022358110`
  - Senha: `Bruno@841124`
  - Agent key: `~/.perito_agent_key`

## Código Completo (Prototipado)

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from pathlib import Path
import requests
import time

options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)

# 1. Login
driver.get("https://esaj.tjms.jus.br/sajcas/login#aba-cpf")
time.sleep(3)

driver.find_element(By.XPATH, "//input[@placeholder='Digite seu CPF/CNPJ.']").send_keys("00022358110")
driver.find_element(By.XPATH, "//input[@placeholder='Digite sua senha']").send_keys("Bruno@841124")
driver.find_element(By.NAME, "pbEntrar").click()

time.sleep(8)  # Redireciona pra validação

# 2. Código
key_file = Path.home() / ".perito_agent_key"
agent_key = key_file.read_text().strip()
r = requests.get("https://sistema.ipcms.com.br/api/v1/esaj/codigo-2fa",
                 headers={"X-Agent-Key": agent_key})
codigo = r.json().get("codigo")

# 3. Validar
token_field = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "tokenInformado"))
)
token_field.send_keys(str(codigo))
driver.find_element(By.XPATH, "//button[contains(text(), 'Enviar')]").click()

# 4. Aguardar redirecionamento (BLOQUEADO AQUI)
WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.ID, "numeroDigitoAnoUnificado"))
)

# ✅ Sessão logada — MANTER ABERTA
# ... continuar com busca de CNJ, download, etc ...
# NÃO fazer driver.quit()
```

## Next Steps

- [ ] Debug por que código não valida (capturar HTML da página após "Enviar")
- [ ] Verificar se código retornado é válido
- [ ] Testar manualmente se código funciona
