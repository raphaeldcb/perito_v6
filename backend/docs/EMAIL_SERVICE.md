# EmailService Documentation

## Overview

EmailService provides reliable Gmail SMTP integration for the Perito v6 backend. It sends formatted HTML emails with automatic retry logic, exponential backoff, and comprehensive error handling. Primary use case: notifying users when intimações (legal notices) are processed through the forensic analysis pipeline.

## Configuration

EmailService requires 8 environment variables in `.env`:

```env
SMTP_HOST=smtp.gmail.com              # Gmail SMTP server
SMTP_PORT=587                          # TLS port
SMTP_FROM_EMAIL=ipcms@ipcms.com.br    # Sender address
SMTP_PASSWORD=<app-specific-password>  # 16-char Google app password
SMTP_ENABLE=1                          # 1 to enable, 0 to disable
SMTP_DEBUG=0                           # 1 for verbose logging
SMTP_RETRY_ATTEMPTS=5                  # Max retry count
SMTP_RETRY_BACKOFF_FACTOR=1            # Multiplier for exponential backoff
```

**Getting Gmail App Password:**
1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Windows Computer" (or custom)
3. Generate 16-character password
4. Copy to SMTP_PASSWORD in .env
5. Restart backend container

## Usage

```python
from app.services.email_service import EmailService, EmailServiceError

service = EmailService()

# Send intimação notification
try:
    result = await service.send_email(
        to_email="user@example.com",
        subject="Intimação Processed",
        usuario_id=42,
        analise={
            "campo_1": "value1",
            "campo_2": "value2",
            # ... all 12 analysis fields
        }
    )
    print(f"Email sent: {result['message_id']}")
except EmailServiceError as e:
    logger.warning(f"Email delivery failed (non-blocking): {e}")
```

Email is non-blocking—failures do not halt the intimação processing workflow.

## Error Handling

EmailService silently logs failures with 5 retry attempts:
- Attempt 1: 1s delay
- Attempt 2: 2s delay
- Attempt 3: 4s delay
- Attempt 4: 8s delay
- Attempt 5: 16s delay

On final failure:
- Warning logged to app logs
- Exception raised (caught in forensic_analysis endpoint)
- Request proceeds successfully (email optional)

```python
try:
    await service.send_email(...)
except EmailServiceError as e:
    # Logs: "[SMTP] Email delivery failed after 5 attempts: {error}"
    # Request continues normally
```

## Testing

Run unit tests:
```bash
pytest backend/tests/test_email_service.py -v
```

Run integration tests (E2E + intimação workflow):
```bash
pytest backend/tests/test_email_service.py::test_end_to_end_email_workflow -v
pytest backend/tests/test_intimacao_with_email.py -v
```

All 14 tests passing. No external mocking required—tests use stdlib email/smtplib directly.

## Deployment

1. **VPS Setup:**
   - Update `.env` with app-specific password from Google Account
   - Set `SMTP_ENABLE=1`
   - Restart backend: `docker-compose restart backend`

2. **Verify:**
   - Check logs: `docker logs <backend_container> | grep SMTP`
   - Expected: "[SMTP] Connection established", "[SMTP] Email sent"

3. **Troubleshooting:**
   - Enable debug: Set `SMTP_DEBUG=1`, restart, check logs
   - Invalid password: Regenerate at https://myaccount.google.com/apppasswords
   - Port blocked: Contact VPS provider, verify firewall rule for 587/tcp

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **SMTPAuthenticationError** | Verify 16-char app password (not account password) at https://myaccount.google.com/apppasswords |
| **ConnectionRefusedError** | Check VPS firewall allows outbound 587/tcp to smtp.gmail.com |
| **No emails sent** | Set SMTP_ENABLE=1, verify SMTP_FROM_EMAIL is valid Gmail address |
| **Slow delivery** | Check SMTP_RETRY_BACKOFF_FACTOR and attempt count in logs (debug mode) |
| **HTML formatting broken** | Verify all 12 analise fields present in data dict; template expects specific keys |

For support, check backend logs with: `docker logs <container> --tail 100 | grep -i smtp`
