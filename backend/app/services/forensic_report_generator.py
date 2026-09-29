import json
from datetime import datetime
from typing import Dict, Any

class ForensicReportGenerator:
    """Gera PDF + JSON do laudo"""
    
    @staticmethod
    def generate_json(analysis_result: Dict[str, Any]) -> str:
        """Retorna JSON formatado"""
        return json.dumps(analysis_result, indent=2, default=str)
    
    @staticmethod
    def generate_pdf(analysis_result: Dict[str, Any]) -> bytes:
        """Retorna PDF em bytes (usando jsPDF no frontend para simplificar)"""
        # Placeholder: PDF será gerado no frontend
        return b"PDF Placeholder"
