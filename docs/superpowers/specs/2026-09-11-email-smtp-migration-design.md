# Email SMTP Migration Design (Perito System → Perito v6)

**Date:** 2026-09-11  
**Status:** Design Approved  
**Scope:** Migrate Gmail SMTP email service from Perito System (Node.js/Nodemailer) to Perito v6 (FastAPI/Python)

---

## 1. Overview

### Current State (Perito System Legacy)
- **Technology:** Node.js + Nodemailer
- **SMTP Provider:** Gmail (smtp.gmail.com:587)
- **Authentication:** App-specific password
- **Email:** ipcms@ipcms.com.br
- **Use Case:** Notify users when intimações (legal notices) are processed
- **Location:** `/root/perito-system/src/notificador.js`

### Target State (Perito v6)
- **Technology:** FastAPI (Python) + smtplib (stdlib)
- **SMTP Provider:** Same Gmail
- **Authentication:** Same app-specific password
- **Email:** Same (ipcms@ipcms.com.br)
- **Use Case:** Same (notify users on intimação processing)
- **Location:** `backend/app/services/email_service.py`

### Success Criteria
- ✅ Emails are sent when intimações are processed
- ✅ Retry logic handles temporary SMTP failures (max 5 attempts with exponential backoff)
- ✅ Error handling is robust (logs critical failures, notifies admin)
- ✅ No external dependencies added (use Python stdlib `smtplib`)
- ✅ All emails arrive within 10 seconds
- ✅ Service is testable locally and on VPS

---

## 2. Architecture

### Component Diagram
```
┌─────────────────────────────────────────────────────────┐
│ Perito v6 Backend (FastAPI)                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Rota: POST /api/v1/intimacoes/processar]            │
│           ↓                                             │
│  [Service: IntimacaoService]                           │
│           ├─ OCR                                        │
│           ├─ Field extraction                           │
│           ├─ Classification (tipo, setor, riscos)      │
│           ├─ Save to DB                                │
│           └─ Call: EmailService.enviar_notificacao()   │
│                     ↓                                   │
│           [Service: EmailService] ← NEW                │
│                     ├─ Mount HTML with v6 data         │
│                     ├─ Retry loop (5x with backoff)    │
│                     └─ Send via SMTP or log error      │
│                     ↓                                   │
│           [SMTP Gmail smtp.gmail.com:587]              │
│                     ↓                                   │
│           [📧 Email sent or critical alert sent]       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Design Principles
- **Isolation:** EmailService is a self-contained class with no external dependencies
- **Robustness:** Exponential backoff retry logic handles transient failures
- **Observability:** Comprehensive logging at each step
- **Fallback:** If email fails, admin is notified; processing continues (non-blocking)
- **Testability:** Can be tested with mocks locally and with real SMTP on VPS

---

## 3. Components

### 3.1 EmailService Class
**File:** `backend/app/services/email_service.py`  
**Responsibilities:**
- Read SMTP configuration from environment
- Mount HTML email with intimação data (tipo_pericia, setor, riscos, campos_extraidos)
- Connect to SMTP server
- Handle SMTP errors and retry with backoff
- Log all operations
- Notify admin on critical failures

**Public Methods:**
```python
async def enviar_notificacao(
    usuario_id: int,
    analise: dict
) -> bool:
    """
    Send email notification for processed intimação.
    
    Args:
        usuario_id: User ID (to fetch email address)
        analise: Dict with intimação analysis (arquivo, confianca, tipo_pericia, etc)
    
    Returns:
        bool: True if sent successfully, False if failed after all retries
    """
```

**Configuration (Environment Variables):**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=ipcms@ipcms.com.br
SMTP_PASS=<app-specific-password>
SMTP_FROM=ipcms@ipcms.com.br
SMTP_TIMEOUT=10
EMAIL_ADMIN=bruno@ipcms.com.br
EMAIL_DEBUG=false  # optional: print email instead of sending
```

### 3.2 Integration Points
**In IntimacaoService (or equivalent):**
```python
from app.services.email_service import EmailService

email_service = EmailService()
await email_service.enviar_notificacao(usuario_id, analise_dict)
```

---

## 4. Data Flow

### Happy Path: Email Sent Successfully
```
1. Intimação is processed
2. IntimacaoService calls EmailService.enviar_notificacao(usuario_id=1, analise={...})
3. EmailService fetches user email from DB
4. EmailService mounts HTML with:
   - Arquivo (filename)
   - Confiança (%)
   - Tipo de Perícia (Contábil, DNA, Eng, etc)
   - Setor (10=Contábil, 20=DNA, etc)
   - Riscos (Baixo, Médio, Alto)
   - Campos Extraídos (table with 41 fields)
   - Timestamp
5. EmailService connects to smtp.gmail.com:587 (TLS)
6. Authenticates with SMTP_USER + SMTP_PASS
7. Sends message
8. Returns True
9. Log: ✅ Email enviado para usuário 1 | intimacao_001
```

### Error Path: Retry Logic
```
1. Attempt 1: SMTP connect fails (network error)
   → Wait 1s → Log warning
2. Attempt 2: SMTP succeeds, but send fails (temporary server error)
   → Wait 2s → Log warning
3. Attempt 3: SMTP succeeds, send succeeds
   → Return True
   → Log: ✅ Email enviado na tentativa 3
```

### Critical Failure Path
```
1. Attempts 1-5 all fail (e.g., invalid credentials, server down)
   → Log: ❌ Email falhou após 5 tentativas | usuário 1 | erro: SMTPAuthenticationError
   → Send alert email to EMAIL_ADMIN with details
   → Save notification to DB (for dashboard visibility)
   → Return False
   → IntimacaoService continues (non-blocking)
```

---

## 5. Error Handling

### Retry Strategy
- **Max Attempts:** 5
- **Backoff Sequence:** [1s, 2s, 4s, 8s, 16s]
- **Total Max Wait:** 31 seconds

### Error Categories

| Error Type | Category | Action |
|-----------|----------|--------|
| SMTPAuthenticationError | Critical | Log error, send admin alert, stop retry |
| SMTPException (generic) | Transient | Log warning, retry |
| ConnectionRefusedError | Transient | Log warning, retry |
| socket.timeout | Transient | Log warning, retry |
| Exception (unknown) | Unknown | Log error, stop retry (non-recoverable) |

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Success
logger.info(f"✅ Email enviado para usuário {usuario_id} | {analise_id}")

# Retry
logger.warning(f"⚠️ Email falhou, tentativa {attempt}/{max_retries} | aguardando {backoff}s | erro: {e}")

# Critical Failure
logger.error(f"❌ Email falhou após {max_retries} tentativas | usuário {usuario_id} | erro: {e}")
```

### Admin Notifications
When all 5 retries fail:
1. Send alert email to EMAIL_ADMIN (bruno@ipcms.com.br)
2. Include: user affected, intimação details, all 5 errors, timestamp
3. Save notification to `notificacoes` table for dashboard visibility

---

## 6. HTML Email Template

The email HTML should include:
```html
<html>
  <head>
    <meta charset="utf-8">
    <style>
      body { font-family: Arial, sans-serif; }
      .container { max-width: 600px; margin: auto; padding: 20px; }
      .header { background: #2196F3; color: white; padding: 20px; }
      .content { border: 1px solid #ddd; padding: 20px; }
      table { width: 100%; border-collapse: collapse; }
      th { background: #f5f5f5; padding: 10px; text-align: left; font-weight: bold; }
      td { padding: 10px; border-bottom: 1px solid #eee; }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="header">
        <h2>✅ Intimação Processada</h2>
      </div>
      <div class="content">
        <p><strong>Arquivo:</strong> {arquivo}</p>
        <p><strong>Confiança:</strong> {confianca}%</p>
        <p><strong>Tipo de Perícia:</strong> {tipo_pericia}</p>
        <p><strong>Setor:</strong> {setor}</p>
        <p><strong>Riscos:</strong> {riscos}</p>
        
        <h3>Campos Extraídos</h3>
        <table>
          <thead>
            <tr><th>Campo</th><th>Valor</th></tr>
          </thead>
          <tbody>
            {campos_table}
          </tbody>
        </table>
        
        <p style="color: #999; font-size: 12px;">
          Processado em: {timestamp}
        </p>
      </div>
    </div>
  </body>
</html>
```

---

## 7. Testing

### Unit Tests (Local - Mock SMTP)
**File:** `backend/tests/test_email_service.py`

```python
def test_send_email_success(mock_smtp):
    """Email sends successfully on first attempt"""
    service = EmailService()
    result = await service.enviar_notificacao(usuario_id=1, analise={...})
    assert result == True
    mock_smtp.send_message.assert_called_once()

def test_retry_after_first_failure():
    """Retry logic works: fails once, succeeds on retry"""
    # Mock SMTP that fails once, succeeds on 2nd call
    result = await service.enviar_notificacao(usuario_id=1, analise={...})
    assert result == True
    assert mock_smtp.send_message.call_count == 2

def test_critical_failure_after_5_retries():
    """After 5 failures, return False and notify admin"""
    # Mock SMTP that always fails
    result = await service.enviar_notificacao(usuario_id=1, analise={...})
    assert result == False
    assert mock_smtp.send_message.call_count == 5
    # Verify admin was notified
```

### Integration Tests (VPS - Real SMTP)
```bash
# 1. SSH to VPS
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186

# 2. Run test
python3 -c "
from app.services.email_service import EmailService
import asyncio

service = EmailService()
result = await service.enviar_notificacao(
    usuario_id=1,
    analise={
        'arquivo': 'test_intimacao.pdf',
        'confianca': 95,
        'tipo_pericia': 'Contábil',
        'setor': 10,
        'riscos': 'Médio',
        'campos_extraidos': {'numero_processo': '0001234-56.2026'}
    }
)
print(f'✅ Test: {result}')
"

# 3. Verify email arrives in bruno@ipcms.com.br within 10s
```

### Validation Checklist
- [ ] Email arrives in bruno@ipcms.com.br with correct subject
- [ ] HTML renders correctly in Gmail, Outlook, mobile clients
- [ ] Retry logic works (simulate failure, verify backoff)
- [ ] Admin receives alert if critical failure
- [ ] No errors in backend logs
- [ ] System continues processing even if email fails (non-blocking)

---

## 8. Deployment

### Prerequisites
- App-specific password generated in Google Account (from /root/perito-system/.env)
- Credentials stored securely (not in git, only in .env)

### Deployment Steps

**Step 1: Local Development (Mac)**
```bash
# Copy env template
cp backend/.env.example backend/.env

# Fill in SMTP credentials (from Perito System legacy .env)
# SMTP_PASS=<app-specific-password>

# Run unit tests
pytest backend/tests/test_email_service.py -v
```

**Step 2: VPS Deployment**
```bash
# SSH to VPS
ssh -i ~/.ssh/id_ed25519_perito -p 22022 root@129.121.34.186

# Update backend/.env with SMTP credentials
echo "SMTP_PASS=<app-specific-password>" >> /var/www/perito-v6/backend/.env

# Rebuild/restart container
cd /var/www/perito-v6
docker restart perito-v6-backend

# Verify service is up
curl http://localhost:8000/health
```

**Step 3: Validation on VPS**
```bash
# Process a test intimação and verify email
# Check backend logs for success
docker logs -f perito-v6-backend | grep -i email

# Verify email arrives within 10s
# Test retry by simulating a failure
```

### Rollback Plan
If critical issues arise:
```bash
# 1. Remove SMTP_* from .env (or comment out)
# 2. Comment out EmailService call in IntimacaoService
# 3. Restart container: docker restart perito-v6-backend
# System continues working without email notifications
```

---

## 9. Migration Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 1 | Design & Approval | - | ✅ Done |
| 2 | Implement EmailService | 2-3 hours | Pending |
| 3 | Unit Tests | 1-2 hours | Pending |
| 4 | VPS Integration & E2E Tests | 1-2 hours | Pending |
| 5 | Validation & Rollback Plan | 30 min | Pending |
| 6 | Decommission Perito System | TBD | After v5 fully working |

---

## 10. Post-Migration

### Monitoring
- Check backend logs daily for email errors
- Monitor EMAIL_ADMIN inbox for alerts
- If failures exceed 5% of emails, investigate SMTP provider

### Decommissioning Perito System
Once v6 is fully validated and all critical services migrated:
1. Stop Perito System service on VPS
2. Archive email service code (for reference)
3. Delete `/root/perito-system` directory
4. Document completion in memory

---

## Appendix A: App-Specific Password Generation

1. Go to https://myaccount.google.com/apppasswords
2. Select app: "Other (custom name)" → "Perito v6"
3. Generate password (16 characters, auto-generated)
4. Copy password → store in SMTP_PASS environment variable
5. Never commit password to git

---

**Design Reviewed & Approved:** 2026-09-11  
**Author:** Claude Code  
**Next Step:** Implementation Plan (writing-plans skill)
