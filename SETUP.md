# 🚀 Setup Local - Perito v6

**Guia passo-a-passo para rodar o sistema em sua máquina**

---

## ✅ Pré-requisitos

- **Mac/Linux/Windows**
- **Docker Desktop** (https://www.docker.com/products/docker-desktop)
- **Git** (pré-instalado ou https://git-scm.com)
- **Terminal/CLI** (Terminal.app no Mac, WSL no Windows)

---

## 1️⃣ Clone o Repositório

```bash
git clone https://github.com/raphaeldcb/perito_v6.git
cd perito_v6
```

---

## 2️⃣ Prepare o Ambiente

### 2.1 Copie o Template de Variáveis

```bash
cp .env.example .env
```

### 2.2 Edite `.env` (Mínimo para testar)

```bash
# Abra com seu editor favorito
nano .env

# Alterações necessárias:
# DB_PASSWORD=perito_local_dev  # ← Deixe padrão ou mude
# ENVIRONMENT=development        # ← Correto
# DEBUG=true                     # ← Para desenvolvimento

# Salve: Ctrl+O → Enter → Ctrl+X
```

---

## 3️⃣ Inicie os Serviços com Docker

### 3.1 Verifique se Docker está rodando

```bash
docker --version
docker-compose --version
```

Se não achar, instale Docker Desktop.

### 3.2 Inicie tudo

```bash
docker-compose up -d
```

**Primeira vez**: Vai baixar e compilar. Pode levar 5-10 min.

### 3.3 Verifique o Status

```bash
docker-compose ps
```

Você verá algo como:

```
NAME                   STATUS
perito_postgres        Up 2 minutes (healthy)
perito_backend         Up 1 minute (healthy)
perito_frontend        Up 30 seconds
```

### 3.4 Veja os Logs (opcional, para diagnosticar)

```bash
# Logs de tudo
docker-compose logs -f

# Só do backend
docker-compose logs -f backend

# Só do frontend
docker-compose logs -f frontend

# Sair: Ctrl+C
```

---

## 4️⃣ Acesse a Aplicação

Abra seu navegador:

### Frontend (Interface Gráfica)
```
http://localhost:3000
```

### Backend (API + Docs)
```
http://localhost:8000/docs
```

Padrão de login:
- **Email**: admin@ipcms.com.br
- **Senha**: admin123

---

## 5️⃣ Próximos Passos

### 5.1 Mude sua Senha (⚠️ Importante)

1. Faça login
2. Vá em Settings → Change Password
3. Defina uma senha segura

### 5.2 Importe Dados (Opcional)

```bash
# Se tem dados SQL:
docker-compose exec postgres psql -U perito perito_v6 < seus_dados.sql

# Acesse http://localhost:3000 para ver
```

### 5.3 Teste a API

```bash
# Exemplo: Listar processos
curl -X GET http://localhost:8000/api/v1/processos \
  -H "Authorization: Bearer SEU_TOKEN"
```

---

## 🔧 Desenvolvimento (Backend)

### Adicionar Dependência Python

```bash
# 1. Edite backend/requirements.txt
nano backend/requirements.txt

# 2. Instale no container
docker-compose exec backend pip install -r requirements.txt

# 3. Reinicie
docker-compose restart backend
```

### Fazer Mudanças no Código

O código está em:
- `backend/app/` — Python (FastAPI)
- `frontend/src/` — React (TypeScript)

Mudanças são **refletidas em tempo real** (hot reload ativado).

### Rodar Testes

```bash
docker-compose exec backend pytest tests/ -v
```

---

## 🎨 Desenvolvimento (Frontend)

### Adicionar Dependência Node

```bash
# 1. Edite frontend/package.json
nano frontend/package.json

# 2. Instale
docker-compose exec frontend npm install

# 3. Reinicie
docker-compose restart frontend
```

### Mudanças são Automáticas

Vite faz hot reload — edite `frontend/src/` e veja no navegador.

### Build para Produção

```bash
docker-compose exec frontend npm run build
```

---

## 🧪 Testes Completos

```bash
# Backend
docker-compose exec backend pytest tests/ -v --cov=app

# Frontend
docker-compose exec frontend npm test

# Ambos
docker-compose exec backend pytest tests/ && \
docker-compose exec frontend npm test
```

---

## 💾 Banco de Dados

### Acesse o PostgreSQL

```bash
docker-compose exec postgres psql -U perito perito_v6
```

Comandos úteis:

```sql
-- Ver tabelas
\dt

-- Ver processos
SELECT id, numero_processo, data_entrada FROM "Processo" LIMIT 10;

-- Contar registros
SELECT COUNT(*) FROM "Processo";

-- Sair
\q
```

### Faça Backup

```bash
docker-compose exec postgres pg_dump -U perito perito_v6 > backup.sql
```

### Restaure Backup

```bash
docker-compose exec -T postgres psql -U perito perito_v6 < backup.sql
```

---

## 🛑 Parar os Serviços

```bash
# Parar (dados preservados)
docker-compose stop

# Parar e limpar containers (dados preservados)
docker-compose down

# LIMPAR TUDO (⚠️ Deleta dados!)
docker-compose down -v
```

---

## 🆘 Troubleshooting

### "Cannot connect to Docker"

```bash
# Verifique se está rodando
docker ps

# Se não funciona, reinicie Docker Desktop
# Ou: `docker-compose restart`
```

### "Backend returns 500"

```bash
# Veja logs de erro
docker-compose logs backend

# Reinicie
docker-compose restart backend
```

### "Frontend é blank ou erro"

```bash
# Limpe cache
docker-compose exec frontend rm -rf node_modules
docker-compose exec frontend npm install
docker-compose restart frontend
```

### "Porta já está em uso"

```bash
# Veja o que está usando porta 3000 ou 8000
lsof -i :3000
lsof -i :8000

# Se é outro container, force parar:
docker-compose down
docker system prune
```

### "Database connection error"

```bash
# Reinicie PostgreSQL
docker-compose restart postgres

# Espere ~10 segundos antes de acessar
sleep 10
docker-compose exec backend curl http://localhost:5432
```

---

## 🚀 Deploy em Servidor

Quando pronto para produção:

```bash
# No servidor (VPS/AWS/etc):
git clone https://github.com/raphaeldcb/perito_v6.git
cd perito_v6

# Configure .env com credenciais REAIS
cp .env.example .env
nano .env

# Inicie com Nginx (reverse proxy)
docker-compose --profile production up -d
```

---

## 📚 Documentação

- **API Completa**: http://localhost:8000/docs
- **Código Backend**: `backend/app/README.md`
- **Código Frontend**: `frontend/README.md`
- **Desenvolvimento**: `CLAUDE.md`

---

## ✨ Próximas Mudanças?

Depois de editar código:

```bash
# 1. Faça commit
git add .
git commit -m "Sua mudança aqui"

# 2. Push para GitHub
git push

# 3. Pull no servidor VPS para deploy
ssh seu-vps "cd /var/www/perito-v6 && git pull && docker-compose up -d"
```

---

**Pronto!** 🎉 Seu Perito v6 está rodando localmente.

Alguma dúvida? Veja `README.md` ou `CLAUDE.md`.
