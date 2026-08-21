import os

# Configurações do Motor IA (Ollama Local)
# O modelo 'qwen3.6-35b' deve estar disponível localmente via `ollama list`
# Se o nome for diferente (ex: 'qwen3.6:35b'), ajuste aqui.
OLLAMA_MODELS = {
    "primary": "qwen3.6-35b",  # Modelo principal para análise
    "fallback": ["qwen2.5-coder:35b", "llama3"],  # Modelos de fallback
    "embedding": "nomic-embed-text"  # Modelo para embeddings no ChromaDB
}

# Configurações de Conexão com Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # Aumentei o timeout para modelos maiores
