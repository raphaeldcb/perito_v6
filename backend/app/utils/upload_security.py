"""Upload validation seguro — MIME, tamanho, malware, espaço em disco."""
import os
import uuid
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException


# Limites de tamanho por tipo de arquivo
TAMANHOS_MAX = {
    "pdf": 50 * 1024 * 1024,        # 50 MB
    "image": 10 * 1024 * 1024,      # 10 MB
    "video": 500 * 1024 * 1024,     # 500 MB
}

# Magic bytes (MIME type validation segura)
MAGIC_BYTES = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"GIF87a": "image/gif",
    b"GIF89a": "image/gif",
    b"\x00\x00\x01\x00": "image/vnd.microsoft.icon",  # ICO
    b"\x00\x00\x02\x00": "image/vnd.microsoft.icon",  # CUR
    b"BM": "image/bmp",
    b"\x49\x49\x2a\x00": "image/tiff",  # TIFF LE
    b"\x4d\x4d\x00\x2a": "image/tiff",  # TIFF BE
    b"\x00\x00\x00\x18ftypmp42": "video/mp4",  # MP4
    b"\x00\x00\x00\x20ftypmp42": "video/mp4",
    b"\x00\x00\x00\x1cftypmp42": "video/mp4",
    b"ftypisom": "video/mp4",
    b"ftypiso2": "video/mp4",
    b"ftyp": "video/mp4",  # MP4 genérico
    b"\x00\x00\x00\x14ftypisom": "video/mp4",
    b"\x00\x00\x00\x20ftypisom": "video/mp4",
    b"\xff\xfb\x00": "audio/mpeg",  # MP3
    b"ID3": "audio/mpeg",  # MP3
    b"RIFF": "audio/wav",  # WAV
    b"\x1a\x45\xdf\xa3": "video/webm",  # WebM
    b"\x1a\x45\xdf\xa3": "video/x-matroska",  # MKV
    b"\x4d\x4f\x56": "video/quicktime",  # MOV (simplified)
    b"\x00\x00\x00\x14ftyp": "video/quicktime",  # MOV
    b"RIFF": "video/avi",  # AVI
}

# Extensões aceitas com mapeamento para tipo
EXTENSOES_ACEITAS = {
    "pdf": "pdf",
    "png": "image",
    "jpg": "image",
    "jpeg": "image",
    "gif": "image",
    "bmp": "image",
    "tiff": "image",
    "webp": "image",
    "mp4": "video",
    "mov": "video",
    "avi": "video",
    "mkv": "video",
    "webm": "video",
    "flv": "video",
    "wmv": "video",
    "3gp": "video",
    "m4v": "video",
}

# Extensões PERIGOSAS que devem ser bloqueadas
EXTENSOES_BLOQUEADAS = {
    # Executáveis
    "exe", "bat", "cmd", "com", "scr", "vbs", "vbe", "js", "jse",
    "sh", "bash", "zsh", "ksh", "csh", "tcsh", "ps1", "psc1", "msh",
    "msh1", "msh2", "mshxml", "msh1xml", "msh2xml", "psc2", "msi",
    "app", "bin", "elf",
    # Arquivos comprimidos (risco de bomba ZIP)
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "dmg",
    "pkg", "deb", "rpm",
    # Scripts/código
    "py", "rb", "pl", "java", "cpp", "c", "go", "rs", "ts", "tsx",
    "jsx", "php", "asp", "aspx", "jsp", "cfm", "cfc", "lua", "r",
    "groovy", "gradle", "maven", "pom", "yaml", "yml", "json", "xml",
    "ini", "conf", "cfg", "config", "env", "properties",
    # Documentos office com macros
    "docm", "xlsm", "pptm", "potm", "ppam", "ppsm", "sldm", "odt",
    "ods", "odp",
    # Banco de dados
    "db", "sqlite", "sqlite3", "mdb", "accdb", "dbf", "sql",
    # Disco virtual
    "img", "vmdk", "vdi", "vhd", "qcow", "qcow2",
    # Executáveis/bibliotecas
    "dll", "so", "dylib", "sys", "drv", "ocx", "cpl", "wsc",
    # Arquivos de sistema
    "lnk", "url", "desktop", "shortcut",
}


def detectar_mime_type(dados: bytes) -> Optional[str]:
    """Detecta MIME type por magic bytes (seguro)."""
    for magic, mime in MAGIC_BYTES.items():
        if dados.startswith(magic):
            return mime
    return None


def validar_arquivo(arquivo: UploadFile, dados: bytes) -> Tuple[str, str]:
    """
    Valida um arquivo de upload.

    Retorna: (file_id, tipo_arquivo)

    Levanta HTTPException se:
    - Extensão bloqueada
    - MIME type não detectado ou suspeito
    - Tamanho acima do limite
    - Espaço em disco < 1GB
    """
    filename = arquivo.filename or "unnamed"

    # 1. Validar extensão
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    if not ext:
        raise HTTPException(status_code=400, detail="Arquivo sem extensão")

    if ext in EXTENSOES_BLOQUEADAS:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo .{ext} não permitido")

    if ext not in EXTENSOES_ACEITAS:
        raise HTTPException(status_code=400, detail=f"Extensão .{ext} não suportada. Aceitos: PDF, PNG, JPG, MP4, MOV")

    # 2. Validar MIME type por magic bytes
    mime_detectado = detectar_mime_type(dados)
    tipo_esperado = EXTENSOES_ACEITAS.get(ext)

    if not mime_detectado:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não reconhecido (magic bytes não encontrados)")

    # Validação simples: se detectou PDF, espera PDF
    if tipo_esperado == "pdf" and not mime_detectado.startswith("pdf"):
        raise HTTPException(status_code=400, detail="Arquivo não é PDF válido")

    # Se é imagem, validar que detectou imagem
    if tipo_esperado == "image" and not mime_detectado.startswith("image"):
        raise HTTPException(status_code=400, detail="Arquivo não é imagem válida")

    # Se é vídeo, validar que detectou vídeo
    if tipo_esperado == "video" and not mime_detectado.startswith("video"):
        raise HTTPException(status_code=400, detail="Arquivo não é vídeo válido")

    # 3. Validar tamanho
    tamanho_max = TAMANHOS_MAX.get(tipo_esperado, 50 * 1024 * 1024)
    if len(dados) > tamanho_max:
        tamanho_mb = tamanho_max / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo acima de {tamanho_mb:.0f}MB"
        )

    # 4. Validar espaço em disco
    stat = shutil.disk_usage("/app")
    espaco_livre_gb = stat.free / (1024 * 1024 * 1024)
    if espaco_livre_gb < 1:
        raise HTTPException(
            status_code=507,
            detail=f"Espaço em disco insuficiente ({espaco_livre_gb:.2f}GB livres)"
        )

    return tipo_esperado, mime_detectado


def salvar_arquivo_validado(
    arquivo: UploadFile,
    dados: bytes,
    upload_dir: str = "/app/uploads"
) -> Tuple[str, dict]:
    """
    Salva arquivo após validação completa.

    Retorna: (file_id, metadata)
    """
    # Validar
    tipo_arquivo, mime = validar_arquivo(arquivo, dados)

    # Scannear malware (clamscan se disponível)
    _escanear_malware(dados)

    # Salvar com UUID + nome original em metadados
    os.makedirs(upload_dir, exist_ok=True)
    file_id = uuid.uuid4().hex
    ext = os.path.splitext(arquivo.filename)[1]
    caminho_final = os.path.join(upload_dir, f"{file_id}{ext}")

    with open(caminho_final, "wb") as f:
        f.write(dados)

    metadata = {
        "file_id": file_id,
        "filename_original": arquivo.filename,
        "tipo": tipo_arquivo,
        "mime": mime,
        "tamanho_bytes": len(dados),
        "caminho": caminho_final,
    }

    return file_id, metadata


def _escanear_malware(dados: bytes) -> None:
    """Escaneia malware com clamscan se disponível. Else, log warning."""
    try:
        # Tentar usar clamscan (ClamAV)
        resultado = subprocess.run(
            ["clamscan", "-"],
            input=dados,
            capture_output=True,
            timeout=30,
        )

        if resultado.returncode == 1:  # Vírus detectado
            raise HTTPException(status_code=400, detail="Arquivo contém malware detectado")
        elif resultado.returncode not in [0, -1]:  # Erro ou outras condições
            raise HTTPException(status_code=500, detail="Erro ao escanear malware")
    except FileNotFoundError:
        # clamscan não instalado — usar VirusTotal API se chave disponível
        virustotal_key = os.environ.get("VIRUSTOTAL_API_KEY")
        if virustotal_key:
            _escanear_virustotal(dados, virustotal_key)
        else:
            # Log warning; não bloquear
            import logging
            logging.warning("clamscan não encontrado e VirusTotal não configurado. Pulando scan de malware.")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Timeout ao escanear malware")


def _escanear_virustotal(dados: bytes, api_key: str) -> None:
    """Escaneia com VirusTotal API (apenas se disponível)."""
    import hashlib
    import httpx

    hash_arquivo = hashlib.sha256(dados).hexdigest()

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"https://www.virustotal.com/api/v3/files/{hash_arquivo}",
                headers={"x-apikey": api_key}
            )

            if resp.status_code == 200:
                resultado = resp.json()
                stats = resultado.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})

                # Se algum engine detectou malware
                if stats.get("malicious", 0) > 0:
                    raise HTTPException(status_code=400, detail="Arquivo marcado como malware no VirusTotal")
            elif resp.status_code != 404:  # 404 = arquivo não conhecido (ok)
                import logging
                logging.warning(f"VirusTotal retornou {resp.status_code}")
    except httpx.RequestError as e:
        # Falha de conexão; log warning, não bloquear
        import logging
        logging.warning(f"Erro ao conectar VirusTotal: {e}")
    except Exception as e:
        # Outro erro; log, não bloquear
        import logging
        logging.error(f"Erro ao escanear VirusTotal: {e}")


def gerar_url_download(file_id: str) -> str:
    """Gera URL de download segura para o arquivo."""
    return f"/api/v1/arquivos/{file_id}/download"
