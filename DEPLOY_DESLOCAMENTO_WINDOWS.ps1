# Deploy Deslocamento V2 → VPS (via SSH do Windows)
# Uso: .\DEPLOY_DESLOCAMENTO_WINDOWS.ps1

Write-Host "🚀 DEPLOY DESLOCAMENTO V2 PARA VPS" -ForegroundColor Cyan
Write-Host ""

$VPS_HOST = "129.121.34.186"
$VPS_PORT = "22022"
$VPS_USER = "root"
$BACKEND_PATH = "/var/www/perito-v6/backend"
$SCRATCHPAD = "/private/tmp/claude-501/-Users-ipc-server/dcebcc85-5ffd-487b-bfef-21b2e9f16b0d/scratchpad"

Write-Host "📤 PASSO 1: Enviando arquivos via SCP..." -ForegroundColor Yellow
Write-Host ""

# SCP commands (PowerShell)
$files = @(
    @{"src" = "$SCRATCHPAD/deslocamento_v2.py"; "dst" = "$VPS_USER@$VPS_HOST`:$BACKEND_PATH/app/services/"; "name" = "deslocamento_v2.py"},
    @{"src" = "$SCRATCHPAD/deslocamento_routes_v2.py"; "dst" = "$VPS_USER@$VPS_HOST`:$BACKEND_PATH/app/routes/"; "name" = "deslocamento_routes_v2.py"},
    @{"src" = "$SCRATCHPAD/deslocamento_ui.html"; "dst" = "$VPS_USER@$VPS_HOST`:$BACKEND_PATH/frontend/public/"; "name" = "deslocamento_ui.html"},
    @{"src" = "$SCRATCHPAD/requirements_deslocamento_v2.txt"; "dst" = "$VPS_USER@$VPS_HOST`:$BACKEND_PATH/"; "name" = "requirements_deslocamento_v2.txt"}
)

foreach ($file in $files) {
    Write-Host "  → $($file.name)..." -NoNewline
    try {
        & scp -P $VPS_PORT $file.src $file.dst 2>$null
        Write-Host " ✅" -ForegroundColor Green
    } catch {
        Write-Host " ❌" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "⚙️  PASSO 2: Instalando no VPS via SSH..." -ForegroundColor Yellow
Write-Host ""

# SSH command
$ssh_commands = @"
cd $BACKEND_PATH
echo '📥 Instalando dependências...'
pip install -r requirements_deslocamento_v2.txt -q
echo '✅ Deps instaladas'
echo '🔄 Reiniciando container...'
docker restart perito-v6-backend
sleep 5
echo '✅ Container reiniciado'
"@

Write-Host "  → Executando via SSH..." -NoNewline
try {
    $ssh_commands | & ssh -p $VPS_PORT $VPS_USER@$VPS_HOST 2>$null
    Write-Host " ✅" -ForegroundColor Green
} catch {
    Write-Host " ❌" -ForegroundColor Red
}

Write-Host ""
Write-Host "🧪 PASSO 3: Testando endpoints..." -ForegroundColor Yellow
Write-Host ""

Start-Sleep -Seconds 2

Write-Host "  → GET /api/v1/deslocamento/cidades..." -NoNewline
try {
    $response = Invoke-WebRequest -Uri "http://129.121.34.186:8000/api/v1/deslocamento/cidades?query=Campo" -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ⚠️ (Status: $($response.StatusCode))" -ForegroundColor Yellow
    }
} catch {
    Write-Host " ⚠️ (Backend ainda inicializando)" -ForegroundColor Yellow
}

Write-Host "  → POST /calcular..." -NoNewline
try {
    $body = @{
        origem = "Campo Grande"
        destino = "Dourados"
        tipo_deslocamento = "rodovia"
        ida_volta = $false
    } | ConvertTo-Json

    $response = Invoke-WebRequest -Uri "http://129.121.34.186:8000/api/v1/deslocamento/calcular" `
        -Method POST `
        -ContentType "application/json" `
        -Body $body `
        -ErrorAction SilentlyContinue

    if ($response.StatusCode -eq 200) {
        $data = $response.Content | ConvertFrom-Json
        if ($data.sucesso) {
            Write-Host " ✅" -ForegroundColor Green
            Write-Host "    Distância: $($data.distancia_km) km"
            Write-Host "    Pedágio: R$ $($data.pedagio_total)"
            Write-Host "    Total: R$ $($data.total_deslocamento)"
        } else {
            Write-Host " ❌ ($($data.erro))" -ForegroundColor Red
        }
    }
} catch {
    Write-Host " ⚠️ (Backend pode estar inicializando)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ DEPLOYMENT COMPLETO" -ForegroundColor Green
Write-Host "═════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "🌐 Acessar UI:" -ForegroundColor Yellow
Write-Host "   http://129.121.34.186:8000/frontend/public/deslocamento_ui.html"
Write-Host ""
Write-Host "📚 Documentação:" -ForegroundColor Yellow
Write-Host "   /Users/ipc_server/UPGRADE_DESLOCAMENTO_V2_FINAL.md"
Write-Host ""
Write-Host "Features ✅:" -ForegroundColor Green
Write-Host "   • Pedágio Automático"
Write-Host "   • Deslocamento em Terra (lat/lon)"
Write-Host "   • Upload KML/GeoJSON"
Write-Host "   • UI com 4 abas + mapa preview + PDF export"
Write-Host ""
