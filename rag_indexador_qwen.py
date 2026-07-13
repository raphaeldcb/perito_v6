#!/usr/bin/env python3
"""Indexa PDFs de autos para RAG via Qwen + nomic-embed."""
import sys
import json
import requests
import subprocess
from pathlib import Path
from datetime import datetime
import re

API_BASE = "http://localhost:5000"
OLLAMA_BASE = "http://127.0.0.1:11434"

# Diretório remoto de PDFs
PDF_DIR = "/var/www/perito-v6/backend/data/autos_tjms"


def copiar_pdfs_locais() -> list[Path]:
    """Copia PDFs do VPS para /tmp/autos_rag."""
    local_dir = Path("/tmp/autos_rag")
    local_dir.mkdir(exist_ok=True)

    cmd = [
        "scp",
        "-i", "/Users/ipc_server/.ssh/id_ed25519_perito",
        "-P", "22022",
        f"root@129.121.34.186:{PDF_DIR}/*.pdf",
        str(local_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"✗ Erro ao copiar PDFs: {result.stderr}")
        return []

    pdfs = sorted(local_dir.glob("*.pdf"))
    print(f"✓ {len(pdfs)} PDFs copiados para {local_dir}")
    return pdfs


def extrair_numero_cnj(nome_arquivo: str) -> str | None:
    """Extrai número CNJ do nome do arquivo."""
    match = re.search(r"(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})", nome_arquivo)
    return match.group(1) if match else None


def extrair_texto_pdf_ollama(pdf_path: Path) -> str:
    """Extrai texto de PDF via Ollama vision (llava) — PDF → imagens → LLM."""
    temp_dir = Path("/tmp/pdf_vision")
    temp_dir.mkdir(exist_ok=True)

    try:
        # Converter 1ª página do PDF para imagem (usando ImageMagick/convert)
        result = subprocess.run(
            ["convert", f"{str(pdf_path)}[0:2]", "-density", "150", f"{str(temp_dir)}/page.png"],
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            return ""

        imgs = list(temp_dir.glob("page*.png"))
        if not imgs:
            return ""

        # Usar llava:13b para extrair texto da imagem
        textos = []
        for img_path in imgs[:3]:  # Limita a 3 primeiras páginas
            try:
                # Codificar imagem como base64
                import base64

                with open(img_path, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode()

                r = requests.post(
                    f"{OLLAMA_BASE}/api/generate",
                    json={
                        "model": "llava:13b",
                        "prompt": "Extraia TODO o texto desta página. Responda APENAS com o texto extraído, nada mais.",
                        "images": [b64_img],
                        "stream": False,
                    },
                    timeout=120,
                )

                if r.status_code == 200:
                    texto = r.json().get("response", "")
                    if texto:
                        textos.append(texto)
            except:
                pass

        # Limpar
        for img in imgs:
            img.unlink()

        return "\n".join(textos)[:50000]
    except Exception as e:
        print(f"    Vision extraction falhou: {e}")
        return ""


def gerar_embedding(texto: str) -> list[float] | None:
    """Gera embedding via Ollama nomic-embed-text."""
    try:
        r = requests.post(
            f"{OLLAMA_BASE}/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": texto},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json().get("embedding")
    except:
        pass
    return None


def processar_pdf(pdf_path: Path) -> dict | None:
    """Processa um PDF: extrai texto, gera chunks e embeddings."""
    nome = pdf_path.name
    ref_id = extrair_numero_cnj(nome)
    if not ref_id:
        ref_id = nome.replace(".pdf", "")

    print(f"\n📄 Processando {nome}...")

    # Extrair texto via vision LLM
    texto = extrair_texto_pdf_ollama(pdf_path)
    if not texto:
        print(f"  ✗ Nenhum texto extraído")
        return None

    print(f"  ✓ {len(texto)} chars extraído")

    # Dividir em chunks (500 chars)
    chunk_size = 500
    chunks = []
    for i in range(0, len(texto), chunk_size):
        chunk_texto = texto[i : i + chunk_size]
        if len(chunk_texto.strip()) < 50:
            continue

        # Gerar embedding
        embedding = gerar_embedding(chunk_texto)
        if not embedding:
            print(f"  ⚠️ Falha ao gerar embedding para chunk {len(chunks)}")
            continue

        chunks.append(
            {
                "chunk_idx": len(chunks),
                "texto": chunk_texto,
                "embedding": embedding,
            }
        )

    if not chunks:
        print(f"  ✗ Nenhum chunk com embedding gerado")
        return None

    print(f"  ✓ {len(chunks)} chunks com embeddings")

    return {
        "origem": "processo",
        "ref_id": ref_id,
        "chunks": chunks,
    }


def indexar_rag(payload: dict) -> bool:
    """POST /api/v1/rag/indexar."""
    try:
        r = requests.post(
            f"{API_BASE}/api/v1/rag/indexar",
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 201):
            print(f"  ✅ Indexado: {r.json().get('indexados', 0)} chunks")
            return True
        else:
            print(f"  ✗ Erro {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Erro de conexão: {e}")
        return False


def main():
    print("📚 Indexador RAG — PDFs → Qwen + nomic-embed")
    print("=" * 60)

    # Passo 1: Copiar PDFs
    print("\n[1] Copiando PDFs do VPS...")
    pdfs = copiar_pdfs_locais()
    if not pdfs:
        print("✗ Nenhum PDF copiado")
        return 1

    # Passo 2: Processar cada PDF
    print(f"\n[2] Processando {len(pdfs)} PDFs...")
    indexados = 0
    erros = 0

    for pdf_path in pdfs:
        payload = processar_pdf(pdf_path)
        if payload and indexar_rag(payload):
            indexados += 1
        else:
            erros += 1

    # Resumo
    print(f"\n{'=' * 60}")
    print(f"✓ Indexados: {indexados}")
    print(f"✗ Erros: {erros}")

    resultado = {
        "timestamp": datetime.now().isoformat(),
        "pdfs_processados": len(pdfs),
        "indexados": indexados,
        "erros": erros,
    }

    output_file = Path("/tmp/rag_indexador_resultado.json")
    output_file.write_text(json.dumps(resultado, indent=2))
    print(f"\n📁 Resultado: {output_file}")

    return 0 if erros == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
