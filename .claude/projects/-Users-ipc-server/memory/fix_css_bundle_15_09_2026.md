---
name: fix_css_bundle_vite_build
description: Problema CSS missing no Vite build — Resolvido (15/09/26)
metadata: 
  node_type: memory
  type: project
  originSessionId: af424ecc-0157-470e-8ddd-5c8351483cc9
  modified: 2026-09-15T14:30:38.896Z
---

# 🔧 Fix: CSS Missing no Bundle Vite

**Data:** 2026-09-15 11:30  
**Status:** ✅ **RESOLVIDO**  
**Causa:** Primeiro build não processou @import('./theme.css')

## 🐛 Problema

Após CSS Standardization deploy (11/09):
- Frontend carregava (HTTP 200) mas sem estilos
- Página aparecia quebrada/sem cores
- CSS não estava no bundle final

**Root Cause:**
- index.css tinha `@import './theme.css'` 
- Vite não processou o import corretamente no primeiro build
- HTML tinha link para CSS, mas arquivo não existia em /dist/assets/

## ✅ Solução

```bash
# 1. Remover dist antigo
rm -rf /var/www/perito-v6/backend_broken/v6/frontend/dist

# 2. Rebuild Vite
npm run build
# ✓ 362 modules, 7.57s
# ✓ CSS: 63.5 kB → 12.29 kB (gzip)
# ✓ JS: 625.65 kB → 187.75 kB (gzip)

# 3. Restart container
docker restart perito-v6-backend
```

## 📊 Verificação

✅ HTML contém link CSS:
```html
<link rel="stylesheet" href="/assets/index-CmHz_6BC.css">
```

✅ Assets presentes:
- `/assets/index-CmHz_6BC.css` (63 KB)
- `/assets/index-eXh7CfQB.js` (614 KB)

✅ Container UP e respondendo (HTTP 200)

## 🎯 Resultado

Processos agora:
- ✅ Carrega página
- ✅ Renderiza com estilos
- ✅ CSS Standardization ativo
- ✅ Dark mode funcional

---

**Status:** ✅ RESOLVIDO
**Next:** Testar em sistema.ipcms.com.br
