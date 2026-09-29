# Perito v6 — Sistema de Gestão de Perícias Judiciais

Sistema completo de automação para gestão de processos judiciais, perícias e laudos, com IA local (Qwen) e integração com APIs públicas de tribunal.

## 🚀 Quick Start

### Pré-requisitos

- **Docker** & **Docker Compose** (instalados)
- **Git** (clone este repositório)
- **Ollama** (opcional, para usar Qwen local)

### 1. Clone e Configure

```bash
git clone https://github.com/raphaeldcb/perito_v6.git
cd perito_v6

# Copie o template de ambiente
cp .env.example .env

# Edite .env com suas credenciais (veja seção Configuration abaixo)
nano .env
```

### 2. Inicie os Serviços

```bash
# Inicie todos os containers (PostgreSQL, Backend, Frontend)
docker-compose up -d

# Verifique o status
docker-compose ps

# Veja logs em tempo real
docker-compose logs -f backend
```

### 3. Acesse a Aplicação

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs (Swagger)
- **Database**: postgres://perito@localhost:5432/perito_v6

### 4. Primeiro Login

Padrão inicial:
- **Usuário**: admin@ipcms.com.br
- **Senha**: admin123

> ⚠️ **Mude a senha após o primeiro login em produção**

---

## 📋 Estrutura do Repositório

```
perito_v6/
├── backend/                 # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py         # Entry point
│   │   ├── models/         # ORM models (Processo, Intimação, etc)
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Lógica de negócio
│   │   ├── schemas/        # Pydantic schemas
│   │   └── database.py     # Conexão PostgreSQL
│   ├── tests/              # Testes unitários
│   ├── requirements.txt    # Dependências Python
│   └── Dockerfile          # Container image
│
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/         # Page routes
│   │   ├── services/      # API client
│   │   ├── styles/        # CSS/theme
│   │   └── App.tsx        # Root component
│   ├── public/            # Static assets
│   ├── package.json       # Node dependencies
│   └── Dockerfile         # Container image
│
├── docker-compose.yml      # Orquestração de containers
├── .env.example           # Template de variáveis de ambiente
├── README.md              # Este arquivo
└── CLAUDE.md              # Instruções de desenvolvimento

```

---

## 🔧 Configuração (`.env`)

### Essencial (Mínimo pra testar)

```bash
# Banco de dados local
DB_PASSWORD=sua_senha
ENVIRONMENT=development
DEBUG=true
```

### Microsoft Graph API (Opcional - para Email/OneDrive)

Se quiser integração com Outlook/OneDrive:

1. Vá para [Azure Portal](https://portal.azure.com)
2. App registrations → New registration
3. Copie: `Client ID`, `Client Secret`, `Tenant ID`
4. Adicione ao `.env`:

```bash
GRAPH_CLIENT_ID=xxxxx
GRAPH_CLIENT_SECRET=xxxxx
GRAPH_TENANT_ID=xxxxx
GRAPH_MAILBOX=seu@email.com
```

### Ollama (Recomendado - IA local)

Para usar Qwen 7B local:

```bash
# Em outro terminal, instale e inicie Ollama
brew install ollama
ollama serve

# Em outro terminal
ollama pull qwen:7b

# Configure no .env
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen:7b
```

---

## 📦 Comandos Úteis

### Docker

```bash
# Inicie os serviços
docker-compose up -d

# Pare os serviços
docker-compose down

# Veja logs
docker-compose logs backend
docker-compose logs -f frontend

# Execute migrations do DB
docker-compose exec backend python -m alembic upgrade head

# Limpe tudo (⚠️ deleta dados)
docker-compose down -v
```

### Backend (Python)

```bash
# Entre no container
docker-compose exec backend bash

# Instale dependências novas
pip install -r requirements.txt

# Execute testes
pytest tests/

# Linter/type check
black app/
mypy app/
```

### Frontend (Node)

```bash
# Entre no container
docker-compose exec frontend bash

# Instale dependências
npm install

# Build para produção
npm run build

# Testes
npm run test
```

---

## 🧪 Testes

```bash
# Backend
docker-compose exec backend pytest tests/ -v

# Frontend
docker-compose exec frontend npm run test

# Coverage
docker-compose exec backend pytest --cov=app tests/
```

---

## 📊 Banco de Dados

### Acesse o PostgreSQL

```bash
# Via psql dentro do container
docker-compose exec postgres psql -U perito -d perito_v6

# Consultas úteis
SELECT * FROM "Processo" LIMIT 5;
SELECT * FROM "Intimacao" LIMIT 5;
SELECT COUNT(*) FROM "Processo";
```

### Backup

```bash
# Faça backup
docker-compose exec postgres pg_dump -U perito perito_v6 > backup.sql

# Restaure
docker-compose exec -T postgres psql -U perito perito_v6 < backup.sql
```

---

## 🚀 Deploy em Produção

### VPS / Servidor

1. **Clone o repositório**
   ```bash
   git clone https://github.com/raphaeldcb/perito_v6.git
   cd perito_v6
   ```

2. **Configure variáveis de produção**
   ```bash
   cp .env.example .env
   # Edite com credenciais reais de produção
   nano .env
   ```

3. **Inicie com Nginx (reverse proxy)**
   ```bash
   docker-compose --profile production up -d
   ```

4. **Configure HTTPS (certbot + Let's Encrypt)**
   ```bash
   docker-compose exec nginx certbot certonly \
     --webroot -w /var/www/certbot \
     -d seu-dominio.com
   ```

---

## 🐛 Troubleshooting

### "Cannot connect to database"

```bash
# Verifique se o PostgreSQL está rodando
docker-compose ps postgres

# Veja logs
docker-compose logs postgres

# Reinicie
docker-compose restart postgres
```

### "Backend returns 500 error"

```bash
# Veja logs detalhados
docker-compose logs -f backend

# Entre no container e teste a DB
docker-compose exec backend python -c "
from app.database import get_db
db = next(get_db())
print('✅ Database connected')
"
```

### "Frontend não carrega"

```bash
# Limpe node_modules
docker-compose exec frontend rm -rf node_modules package-lock.json
docker-compose exec frontend npm install
docker-compose restart frontend
```

---

## 📚 Documentação

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Frontend Components**: `frontend/src/README.md`
- **Database Schema**: `backend/docs/schema.md`
- **Development Guide**: `CLAUDE.md`

---

## 🤝 Contribuindo

1. Crie uma branch: `git checkout -b feature/sua-feature`
2. Faça commit: `git commit -m "Add feature X"`
3. Push: `git push origin feature/sua-feature`
4. Abra PR no GitHub

---

## 📄 Licença

Proprietary — Desenvolvido para IPC MS Perícias LTDA

---

## 📞 Suporte

- 📧 Email: admin@ipcms.com.br
- 🐛 Issues: GitHub Issues
- 📖 Docs: Veja `docs/` e `CLAUDE.md`

---

**Última atualização**: 29/09/2026  
**Versão**: v6.1.0  
**Status**: ✅ Production Ready
