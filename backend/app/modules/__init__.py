"""
Modular architecture for PERITO v6.

8 domain modules (auth, processos, esaj, laudos, financeiro, ferramentas, ia, infra)
each with isolated models, schemas, repositories, services, and routes.

Modules communicate via app.shared DTOs and exceptions only.
Cross-module imports are blocked by audit_imports.py in CI/CD.
"""
