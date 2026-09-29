"""
Module loader — Auto-discover and load routers from ferramentas modules.
"""

import importlib
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# ===== CONFIG — 18 ferramentas carregadas
MULTIHANDLER_MODULES = {
    "ferramentas": [
        "auto_laudo_pro_router",
        "banco_router",
        "calculator_router",
        "cerebro_router",
        "cnj_router",
        "coletador_router",
        "conciliacao_router",
        "dashboard_alertas_router",
        "deslocamento_router",
        "diario_router",
        "dna_router",
        "engenharia_router",
        "fake_detector_router",
        "fluxo_honorarios_router",
        "forensic_router",
        "intimacoes_router",
        "padroes_router",
        "rag_router"
    ]
}

def load_module_routers(app) -> Dict[str, Any]:
    """
    Auto-discover and load module routers from config.
    """
    result = {
        "success": True,
        "loaded": [],
        "failed": [],
        "total": 0
    }
    
    ferramentas = MULTIHANDLER_MODULES.get("ferramentas", [])
    
    for router_name in ferramentas:
        tool_name = router_name.replace("_router", "")
        try:
            # Dynamic import: app.modules.ferramentas.{tool_name}
            module = importlib.import_module(f"app.modules.ferramentas.{tool_name}")
            
            if hasattr(module, "router"):
                router = getattr(module, "router")
                app.include_router(router)
                result["loaded"].append(tool_name)
                logger.info(f"✅ [{tool_name}] router carregado")
            else:
                result["failed"].append((tool_name, "sem atributo router"))
                logger.warning(f"⚠️  [{tool_name}] sem atributo router")
                
        except Exception as e:
            result["failed"].append((tool_name, str(e)))
            logger.error(f"❌ [{tool_name}] erro: {e}")
    
    result["total"] = len(ferramentas)
    result["success"] = len(result["failed"]) == 0
    
    logger.info(f"🎉 Módulos carregados: {len(result['loaded'])}/{result['total']}")
    
    return result
