import os
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
# Assume que .env está na raiz do projeto ou no mesmo diretório deste script
load_dotenv()

# Configurações Gerais
# Caminho absoluto para o OneDrive conforme instrução
ONE_DRIVE_DIR = "/Users/ipc_server/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA"

# Determina a raiz do projeto baseada na localização deste arquivo
# Se este arquivo estiver em /Users/ipc_server/.../pipeline/, o pai é a raiz
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

# Configurações Ollama
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Carregamento dinâmico de conveniados
CONVENIDOS_PATH = os.path.join(PROJECT_ROOT, "pipeline", "convenidos.json")
CONVENIDOS = []
if os.path.exists(CONVENIDOS_PATH):
    with open(CONVENIDOS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        CONVENIDOS = data.get("conveniados", [])

# Configurações ChromaDB
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
RAG_N_EXEMPLOS = int(os.getenv("RAG_N_EXEMPLOS", "3"))

# Configurações Email
EMAIL_MONITOR_ENABLED = os.getenv("EMAIL_MONITOR_ENABLED", "true").lower() == "true"
EMAIL_USER = os.getenv("EMAIL_USER", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Configurações VPS
VPS_HOST = os.getenv("VPS_HOST", "sistema.ipcms.com.br")
VPS_USER = os.getenv("VPS_USER", "admin")
VPS_PASSWORD = os.getenv("VPS_PASSWORD", "Admin@2026")
