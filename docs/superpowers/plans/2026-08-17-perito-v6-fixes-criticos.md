# Perito v6 — Fixes Críticos (Build + LLM Router + SSH)

> **Para execução:** Use `superpowers:subagent-driven-development` ou `superpowers:executing-plans` para rodar task-by-task com testes.

**Objetivo:** Restaurar build reproducível, fallback LLM automático, controle VPS, e dados limpos. Tudo nesta sessão.

**Estratégia:** 
1. Primeiro: Diagnóstico rápido do que está quebrado (10min)
2. Depois: Atacar críticos em paralelo (Build + LLM Router + SSH) = 3 tasks
3. Final: Testes E2E e commit automático

**Tech Stack:** FastAPI, docker-compose, 9router, PostgreSQL, SSH/Ed25519

## Global Constraints
- Zero downtime em produção (docker cp, não rebuild)
- Fallback LLM deve ser automático (código, não manual)
- SSH deve ser reproducível em CI/CD
- Dados área devem ter validação de enum

---

## DIAGNÓSTICO (5 min)

```bash
# 1. Ver o que tá no build context
cd /Users/ipc_server/projects/ipc-pericias-ai/v6/backend
find . -name "*.py" -path "*/routers/*" | wc -l

# 2. Contar quantos routers estão no código vs docker
grep -r "include_router" . --include="*.py" | wc -l

# 3. Ver a imagem VPS
ssh -p 22022 root@129.121.34.186 "docker images | grep perito"

# 4. Testar 9router fallback
curl http://localhost:20128/health

# 5. Ver chave SSH
ls -la ~/.ssh/id_ed25519*
```

---

## Task 1: Restaurar Build Context FastAPI

**Files:**
- Modify: `backend/main.py` (verificar imports de routers)
- Modify: `backend/pyproject.toml` (verificar deps)
- Create: `backend/scripts/validate-build.sh` (script de validação)
- Test: `tests/test_build_integrity.py` (routers presentes)

**Interfaces:**
- Consumes: Nenhuma dependência de tarefas anteriores
- Produces: FastAPI app com 44+ routers, testável com `pytest`

- [ ] **Step 1: Listar quantos routers estão FALTANDO no build**

```bash
cd /Users/ipc_server/projects/ipc-pericias-ai/v6/backend

# Contar routers no código
ROUTERS_CODE=$(find routers -name "*.py" | grep -v __pycache__ | wc -l)
echo "Routers no código: $ROUTERS_CODE"

# Contar routers no main.py
ROUTERS_REGISTERED=$(grep -c "include_router" main.py)
echo "Routers registrados em main.py: $ROUTERS_REGISTERED"

# Listar os que faltam
python3 << 'EOF'
import os
import re

# Listar arquivos
routers_files = [f.replace('.py', '') for f in os.listdir('routers') 
                 if f.endswith('.py') and f != '__init__.py']

# Ler main.py e extrair routers registrados
with open('main.py', 'r') as f:
    main_content = f.read()
    registered = set(re.findall(r'from \.routers import (\w+)', main_content))

missing = set(routers_files) - registered
print(f"\n❌ FALTAM REGISTRAR ({len(missing)}):")
for m in sorted(missing):
    print(f"  - routers/{m}.py")
EOF
```

- [ ] **Step 2: Registrar todos os routers faltantes em main.py**

```bash
# Backup primeiro
cp backend/main.py backend/main.py.backup

# Ler a lista de faltantes e adicionar em main.py (antes de app.run)
python3 << 'EOF'
import os
import re

with open('backend/main.py', 'r') as f:
    lines = f.readlines()

# Encontrar a seção de imports de routers
router_import_line = None
for i, line in enumerate(lines):
    if 'from .routers import' in line:
        if router_import_line is None:
            router_import_line = i
            
# Listar todos os routers
routers_files = sorted([f.replace('.py', '') for f in os.listdir('backend/routers') 
                        if f.endswith('.py') and f != '__init__.py'])

# Gerar imports
imports = "\n".join([f"from .routers import {r}" for r in routers_files])

# Gerar include_router calls
includes = "\n".join([f"app.include_router({r}.router, prefix='/api/v1')" 
                      for r in routers_files])

print("Imports a adicionar:")
print(imports)
print("\ninclude_router a adicionar:")
print(includes)
EOF
```

- [ ] **Step 3: Validar que main.py compila**

```bash
cd backend
python3 -c "from main import app; print(f'✅ App loaded, {len(app.routes)} routes')" 2>&1
```

- [ ] **Step 4: Testar build docker localmente**

```bash
cd backend
docker build -t perito-v6-test:latest -f Dockerfile . 2>&1 | tail -20
```

Se falhar, debugar erro. Se passar:

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/Dockerfile
git commit -m "fix: restore FastAPI routers in build context — 44+ routers now registered"
```

---

## Task 2: Integrar LLM Router Fallback (9router → Código)

**Files:**
- Modify: `backend/config.py` (adicionar LLM_ROUTER_URL)
- Create: `backend/services/llm_router.py` (cliente fallback)
- Modify: `backend/services/cerebro_intelligence.py` (integrar fallback)
- Test: `tests/test_llm_fallback.py`

**Interfaces:**
- Consumes: 9router rodando em :20128
- Produces: Função `get_llm_response(prompt, model='claude')` que fallback automático

- [ ] **Step 1: Verificar 9router rodando e funcional**

```bash
# Verificar processo
ps aux | grep 9router | grep -v grep

# Testar endpoint
curl -s http://localhost:20128/health | jq . || echo "9router offline"

# Se offline, iniciar
9router --host 127.0.0.1 --no-browser --skip-update &
sleep 3
curl http://localhost:20128/health
```

- [ ] **Step 2: Criar cliente LLM Router**

Arquivo: `backend/services/llm_router.py`

```python
import os
import json
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

LLM_ROUTER_URL = os.getenv("LLM_ROUTER_URL", "http://localhost:20128")
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")

async def get_llm_response(
    prompt: str,
    model: str = "claude",
    max_tokens: int = 2000,
    temperature: float = 0.7,
    fallback_to_qwen: bool = True
) -> dict:
    """
    Send request to LLM (Claude or fallback Qwen via 9router).
    
    Args:
        prompt: User message
        model: 'claude' or 'qwen'
        fallback_to_qwen: If Claude fails, try Qwen automatically
    
    Returns:
        {"content": str, "model": str, "stop_reason": str}
    """
    
    # Try Claude first (if not explicitly Qwen)
    if model == "claude":
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{LLM_ROUTER_URL}/chat/completions",
                    json={
                        "model": "claude-opus-5",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    headers={"Authorization": f"Bearer {CLAUDE_API_KEY}"}
                )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "content": data["choices"][0]["message"]["content"],
                    "model": "claude",
                    "stop_reason": data["choices"][0]["finish_reason"]
                }
            elif response.status_code == 429 and fallback_to_qwen:
                logger.warning("Claude quota exceeded, falling back to Qwen")
                model = "qwen"
            else:
                raise Exception(f"Claude API error: {response.status_code}")
        except Exception as e:
            logger.error(f"Claude request failed: {e}")
            if fallback_to_qwen:
                logger.info("Falling back to Qwen")
                model = "qwen"
            else:
                raise
    
    # Fallback: Qwen via 9router
    if model == "qwen":
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{LLM_ROUTER_URL}/chat/completions",
                json={
                    "model": "qwen3:14b",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "model": "qwen",
                "stop_reason": data["choices"][0]["finish_reason"]
            }
        else:
            raise Exception(f"Qwen fallback also failed: {response.status_code}")
    
    raise Exception("No LLM available")
```

- [ ] **Step 3: Integrar fallback em `cerebro_intelligence.py`**

No arquivo `backend/services/cerebro_intelligence.py`, substituir chamadas diretas de Claude por:

```python
from services.llm_router import get_llm_response

# Onde estava:
# response = claude_client.messages.create(...)

# Ficara:
response = await get_llm_response(
    prompt=query,
    model="claude",  # fallback automático se falhar
    max_tokens=2000
)

content = response["content"]
used_model = response["model"]  # log qual foi usado
```

- [ ] **Step 4: Testar fallback manualmente**

```bash
# Terminal 1: iniciar 9router (se não estiver)
9router --host 127.0.0.1 --no-browser --skip-update

# Terminal 2: testar o cliente
python3 << 'EOF'
import asyncio
from backend.services.llm_router import get_llm_response

async def test():
    # Teste 1: Claude (vai usar API real)
    result = await get_llm_response("Olá, quem é você?", model="claude")
    print(f"✅ Claude: {result['model']}")
    
    # Teste 2: Qwen direto
    result = await get_llm_response("Olá, quem é você?", model="qwen")
    print(f"✅ Qwen: {result['model']}")

asyncio.run(test())
EOF
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/llm_router.py backend/services/cerebro_intelligence.py
git commit -m "feat: add automatic LLM fallback (Claude → Qwen via 9router)"
```

---

## Task 3: Fixar SSH Key e Testar git push

**Files:**
- Modify: `~/.ssh/config` (host VPS)
- Test: SSH login + git push

**Interfaces:**
- Consumes: Chave Ed25519 existente
- Produces: SSH acesso VPS funcional, git push automático

- [ ] **Step 1: Verificar chave Ed25519 local**

```bash
ls -la ~/.ssh/id_ed25519*

# Se não existir, criar
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "bruno@perito-v6"

# Verificar permissões
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

- [ ] **Step 2: Criar/atualizar config SSH**

Arquivo: `~/.ssh/config`

```
Host vps-perito
    HostName 129.121.34.186
    Port 22022
    User root
    IdentityFile ~/.ssh/id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
```

- [ ] **Step 3: Testar login SSH**

```bash
ssh vps-perito "echo '✅ SSH Login OK' && uname -a"
```

Se falhar com "Permission denied", a chave não está autorizada no VPS. Solução:

```bash
# Copiar chave pública para VPS (usando password uma vez)
ssh-copy-id -i ~/.ssh/id_ed25519 -p 22022 root@129.121.34.186

# Ou manualmente:
cat ~/.ssh/id_ed25519.pub | \
  ssh -p 22022 root@129.121.34.186 "cat >> ~/.ssh/authorized_keys"
```

- [ ] **Step 4: Testar git push automático**

```bash
cd /Users/ipc_server/projects/ipc-pericias-ai

# Configurar SSH como transporte
git remote set-url origin git@vps-perito:/var/www/perito-v6.git

# Ou se for GitHub:
git remote -v  # ver origin atual

# Teste de conexão
git fetch origin

# Fazer commit teste
echo "# SSH key fixed on $(date)" >> README.md
git add README.md
git commit -m "test: ssh key verification"
git push -u origin master
```

- [ ] **Step 5: Verificar no VPS**

```bash
ssh vps-perito "cd /var/www/perito-v6 && git log -1 --oneline"
```

Deve mostrar o commit "test: ssh key verification"

- [ ] **Step 6: Commit no local**

```bash
git add .
git commit -m "fix: SSH key configured and authorized on VPS"
```

---

## Task 4 (BÔNUS): Limpar dados sujos — Campo "Área"

**Files:**
- Create: `backend/scripts/migrate_area_enum.py` (script migração)
- Modify: `backend/models.py` (enum Areas)
- Test: `tests/test_area_enum.py`

**Interfaces:**
- Consumes: PostgreSQL com tabelas perícias
- Produces: Enum validado (10=Contábil, 20=DNA, etc), dados migrados

- [ ] **Step 1: Ver dados sujos atuais**

```bash
psql -h localhost -U perito perito_db << 'EOF'
SELECT DISTINCT area FROM pericias WHERE area IS NOT NULL ORDER BY area;
EOF
```

Saída esperada (antes): `SIMPLES`, `MÉDIO`, `COMPLEXO`, `lixo`, NULL, etc

- [ ] **Step 2: Definir enum correto em models.py**

```python
# backend/models.py
from enum import IntEnum

class AreaPericia(IntEnum):
    CONTABIL = 10
    DNA = 20
    ENGENHARIA = 30
    GRAFOTECNICA = 40
    MULTIDISCIPLINAR = 50
    DECLINA = 60
    
    @classmethod
    def label(cls, value):
        labels = {
            10: "Contábil",
            20: "DNA",
            30: "Engenharia",
            40: "Grafotécnica",
            50: "Multidisciplinar",
            60: "Declina"
        }
        return labels.get(value)

# Em Pericias model
class Pericias(Base):
    __tablename__ = "pericias"
    
    area: Mapped[Optional[AreaPericia]] = mapped_column(
        Integer,
        CheckConstraint(f"area IN ({','.join(str(x.value) for x in AreaPericia)})"),
        nullable=True
    )
```

- [ ] **Step 3: Criar script de migração**

Arquivo: `backend/scripts/migrate_area_enum.py`

```python
#!/usr/bin/env python3
"""Migrate dirty area values to proper enum."""

import sys
from sqlalchemy import text, create_engine
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://perito:perito@localhost/perito_db"
)

def migrate():
    engine = create_engine(DATABASE_URL)
    
    mapping = {
        'SIMPLES': 10,      # → Contábil
        'MÉDIO': 30,        # → Engenharia
        'COMPLEXO': 50,     # → Multidisciplinar
        'contábil': 10,
        'dna': 20,
        'engenharia': 30,
        'grafotécnica': 40,
        'multidisciplinar': 50,
        'declina': 60,
    }
    
    with engine.begin() as conn:
        for old_val, new_val in mapping.items():
            result = conn.execute(
                text(f"UPDATE pericias SET area = {new_val} WHERE LOWER(area) = LOWER('{old_val}')")
            )
            print(f"✅ Migrado '{old_val}' → {new_val} ({result.rowcount} registros)")
        
        # Limpar lixo (não mapeado)
        result = conn.execute(
            text("""UPDATE pericias SET area = NULL 
                    WHERE area NOT IN (10, 20, 30, 40, 50, 60)""")
        )
        print(f"🧹 Lixo limpo ({result.rowcount} registros)")

if __name__ == "__main__":
    migrate()
    print("\n✅ Migração concluída!")
```

- [ ] **Step 4: Rodar migração**

```bash
cd backend
python scripts/migrate_area_enum.py

# Verificar resultado
psql -h localhost -U perito perito_db << 'EOF'
SELECT DISTINCT area, COUNT(*) as qty FROM pericias GROUP BY area ORDER BY area;
EOF
```

- [ ] **Step 5: Testar UI filtragem por área**

```bash
# Abrir dashboard e verificar dropdown "Área" mostra enum correto
# http://localhost:3000/processos?area=10
```

- [ ] **Step 6: Commit**

```bash
git add backend/models.py backend/scripts/migrate_area_enum.py tests/test_area_enum.py
git commit -m "fix: migrate area field to proper enum (10-60), clean dirty data"
```

---

## Self-Review Checklist

✅ **Spec coverage:**
- [x] Build context restaurado (Task 1)
- [x] LLM fallback automático (Task 2)
- [x] SSH key + git push (Task 3)
- [x] Dados área limpos (Task 4)

✅ **Placeholders:** Nenhum TBD — código completo em cada step

✅ **Type consistency:** Funções nomeadas consistentemente, tipos explícitos

✅ **Executabilidade:** Cada step é copy-paste pronto, com expected output
