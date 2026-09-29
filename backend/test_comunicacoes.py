#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/perito-v6/backend')

try:
    from app.routes.comunicacoes import router
    print(f"✅ Router importado")
    print(f"   Prefix: {router.prefix}")
    print(f"   Rotas: {len(router.routes)}")
    for r in router.routes[:3]:
        print(f"   - {r.path}: {r.methods}")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
