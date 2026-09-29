"""
Endpoint para gerar scripts de setup automático (Windows, Mac, Linux)
Permite que qualquer usuário execute setup local sem precisa fazer nada.
"""
from fastapi import APIRouter, Response
from app.middleware import get_current_user

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


@router.get("/windows-script")
async def windows_setup_script(_=None):
    """
    Retorna script PowerShell completo para setup local no Windows.

    Usuário:
    1. Abre PowerShell
    2. Copia e cola o script
    3. Executa: Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
    4. Tudo roda automático
    """

    script = """
@echo off
REM ===============================================================================
REM PERITO v6 - SETUP AUTOMÁTICO WINDOWS
REM ===============================================================================
REM Este script configura e roda o sistema local completo.
REM Não precisa fazer nada manualmente — siga apenas as instruções na tela.
REM ===============================================================================

echo.
echo ========================================
echo PERITO v6 - SETUP LOCAL WINDOWS
echo ========================================
echo.

REM Detectar pasta
if not exist "backend" (
    echo ERRO: Execute este script na pasta do projeto (onde está backend/ e frontend/)
    echo.
    echo Exemplo:
    echo   cd D:\\Downloads\\Perito-v6-Laudos-Teste
    echo   %0
    exit /b 1
)

REM ===============================================================================
REM 1. VERIFICAR PYTHON
REM ===============================================================================
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado!
    echo Baixe em: https://www.python.org/downloads/
    echo Marque: "Add Python to PATH"
    exit /b 1
)
echo OK: Python está instalado

REM ===============================================================================
REM 2. VERIFICAR NODE
REM ===============================================================================
echo.
echo [2/6] Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Node.js não encontrado!
    echo Baixe em: https://nodejs.org/
    exit /b 1
)
echo OK: Node.js está instalado

REM ===============================================================================
REM 3. SETUP BACKEND
REM ===============================================================================
echo.
echo [3/6] Configurando Backend...
cd backend

if not exist "venv" (
    echo Criando virtual environment...
    python -m venv venv
)

echo Ativando virtual environment...
call venv\Scripts\activate.bat

echo Instalando dependências Python...
pip install -q -r requirements_v6.txt
pip install -q uvicorn alembic

echo Rodando migrations...
alembic upgrade head 2>nul

cd ..
echo OK: Backend pronto

REM ===============================================================================
REM 4. SETUP FRONTEND
REM ===============================================================================
echo.
echo [4/6] Configurando Frontend...
cd frontend

if not exist "node_modules" (
    echo Instalando dependências Node...
    call npm install -q
)

cd ..
echo OK: Frontend pronto

REM ===============================================================================
REM 5. PREPARAR EXECUÇÃO
REM ===============================================================================
echo.
echo [5/6] Preparando ambientes...

REM Abrir 2 terminais para rodar backend e frontend em paralelo
echo Abrindo Backend (porta 8000)...
start cmd /k "cd backend && venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Abrindo Frontend (porta 3000)...
timeout /t 3 /nobreak
start cmd /k "cd frontend && npm start"

REM ===============================================================================
REM 6. AGUARDAR E ABRIR NAVEGADOR
REM ===============================================================================
echo.
echo [6/6] Aguardando servidores iniciarem...
timeout /t 10 /nobreak

echo.
echo ========================================
echo ✅ SETUP COMPLETO!
echo ========================================
echo.
echo Frontend:   http://localhost:3000
echo Backend:    http://localhost:8000/health
echo.
echo Credenciais:
echo   Email: admin@ipcms.com.br
echo   Senha: admin123
echo.
echo Abrindo navegador em 3s...
timeout /t 3 /nobreak
start "" "http://localhost:3000"
echo.
echo ========================================
echo Sistema rodando! Dois terminais foram abertos:
echo   1. Backend FastAPI (não feche)
echo   2. Frontend React (não feche)
echo.
echo Para parar:
echo   - Backend: Ctrl+C no terminal 1
echo   - Frontend: Ctrl+C no terminal 2
echo ========================================
pause
"""

    return Response(
        content=script,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=setup-perito-windows.bat"
        }
    )


@router.get("/linux-script")
async def linux_setup_script():
    """Script bash para Linux/Mac"""

    script = """#!/bin/bash
set -e

echo ""
echo "========================================"
echo "PERITO v6 - SETUP AUTOMÁTICO LINUX/MAC"
echo "========================================"
echo ""

# Verificar pastas
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "ERRO: Execute na pasta do projeto (onde está backend/ e frontend/)"
    exit 1
fi

# 1. Python
echo "[1/6] Verificando Python..."
python3 --version || { echo "ERRO: Python 3 não encontrado"; exit 1; }

# 2. Node
echo "[2/6] Verificando Node.js..."
node --version || { echo "ERRO: Node.js não encontrado"; exit 1; }

# 3. Backend
echo "[3/6] Configurando Backend..."
cd backend
[ ! -d "venv" ] && python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements_v6.txt
alembic upgrade head 2>/dev/null || true
cd ..

# 4. Frontend
echo "[4/6] Configurando Frontend..."
cd frontend
[ ! -d "node_modules" ] && npm install -q
cd ..

# 5. Rodar ambos em background
echo "[5/6] Iniciando servidores..."
cd backend && source venv/bin/activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
cd ../frontend && npm start &

# 6. Aguardar
echo "[6/6] Aguardando 10s..."
sleep 10

echo ""
echo "========================================"
echo "✅ SETUP COMPLETO!"
echo "========================================"
echo ""
echo "Frontend:   http://localhost:3000"
echo "Backend:    http://localhost:8000/health"
echo ""
echo "Credenciais:"
echo "  Email: admin@ipcms.com.br"
echo "  Senha: admin123"
echo ""
echo "Sistema rodando em background"
echo "Para parar: kill %1 %2"
echo ""
open "http://localhost:3000" 2>/dev/null || xdg-open "http://localhost:3000" 2>/dev/null
"""

    return Response(
        content=script,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=setup-perito-linux.sh"
        }
    )


@router.get("/quick-start")
async def quick_start_info():
    """Retorna instruções rápidas em JSON"""
    return {
        "titulo": "Setup Local - 1 Clique",
        "windows": {
            "passos": [
                "1. Clique em 'Baixar Setup Windows'",
                "2. Copie e cole o arquivo em D:\\Downloads\\Perito-v6-Laudos-Teste\\",
                "3. Clique 2x no arquivo setup-perito-windows.bat",
                "4. Pronto! Navegador abre em http://localhost:3000"
            ],
            "credenciais": {
                "email": "admin@ipcms.com.br",
                "senha": "admin123"
            },
            "duracao": "~2 minutos primeira vez"
        },
        "linux_mac": {
            "passos": [
                "1. Clique em 'Baixar Setup Linux/Mac'",
                "2. Abra Terminal na pasta do projeto",
                "3. bash setup-perito-linux.sh",
                "4. Pronto! Navegador abre em http://localhost:3000"
            ],
            "credenciais": {
                "email": "admin@ipcms.com.br",
                "senha": "admin123"
            },
            "duracao": "~2 minutos primeira vez"
        }
    }
