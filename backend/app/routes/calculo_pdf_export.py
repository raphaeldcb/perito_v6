"""PDF export com fPDF2 (A4 margens 5/32/10/10mm)"""
from fpdf import FPDF
from io import BytesIO
from fastapi.responses import StreamingResponse
import unicodedata

def a(s):
    """Converte string pra latin-1 (FPDF compat)"""
    return unicodedata.normalize("NFKD", str(s)).encode("latin-1", "ignore").decode("latin-1")

def exportar_pdf(resultado: dict) -> StreamingResponse:
    """Gera PDF A4 com margens exatas"""
    pdf = FPDF(format="A4", orientation="P")
    pdf.set_margins(left=32, top=5, right=10)
    pdf.set_auto_page_break(auto=True, margin=10)
    
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, a("Memória de Cálculo - Atualização Monetária"), ln=True)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, a(f"Valor Original: {resultado['totais']['valor_original']}"), ln=True)
    pdf.cell(0, 6, a(f"Saldo Final: {resultado['totais']['saldo_final']}"), ln=True)
    pdf.ln(3)
    
    # Tabela
    COLS = ["Mês/Ano", "Valor Nominal", "% Correção", "Saldo Corrigido"]
    pdf.set_font("Helvetica", "B", 8)
    larg = (pdf.w - 42) / len(COLS)
    
    for col in COLS:
        pdf.cell(larg, 6, a(col), border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 7)
    for linha in resultado.get("linhas", [])[:20]:  # Max 20 linhas por página
        for v in linha.values() if isinstance(linha, dict) else linha:
            pdf.cell(larg, 5, a(str(v)), border=1, align="R")
        pdf.ln()
    
    buf = BytesIO(pdf.output())
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="calculo_atualizacao.pdf"'}
    )
