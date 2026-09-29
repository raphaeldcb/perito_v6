"""Geração de PDF para relatórios de vistoria de engenharia.

Produz PDF A4 com logo, dados da vistoria, fotos, assinaturas e campo para
assinatura digital (WebSigner/A3). Usa reportlab para flexibilidade.
"""
import io
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak, KeepTogether
from reportlab.pdfgen import canvas

from app.models import Vistoria, ModeloVistoria


def gerar_pdf_vistoria(vistoria: Vistoria, fotos_paths: list = None) -> bytes:
    """
    Gera PDF completo da vistoria.

    Retorna bytes do PDF pronto para assinatura digital.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=10*mm, bottomMargin=10*mm,
                            leftMargin=15*mm, rightMargin=15*mm)

    story = []
    styles = getSampleStyleSheet()

    # Estilo customizado
    titulo_style = ParagraphStyle(
        'TituloCustom', parent=styles['Heading1'],
        fontSize=16, textColor=colors.HexColor("#1f2937"), spaceAfter=6,
        alignment=1  # center
    )
    secao_style = ParagraphStyle(
        'SecaoCustom', parent=styles['Heading2'],
        fontSize=12, textColor=colors.HexColor("#374151"), spaceAfter=4,
        spaceBefore=8
    )
    normal_style = ParagraphStyle(
        'NormalCustom', parent=styles['Normal'],
        fontSize=10, leading=12
    )

    # ---- CABEÇALHO
    titulo = Paragraph("RELATÓRIO DE VISTORIA DE ENGENHARIA", titulo_style)
    story.append(titulo)

    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    info_header = Paragraph(
        f"<b>Modelo:</b> {vistoria.modelo.nome} | "
        f"<b>Gerado em:</b> {data_hora} | "
        f"<b>ID:</b> {vistoria.id}",
        normal_style
    )
    story.append(info_header)
    story.append(Spacer(1, 0.3*cm))

    # ---- METADADOS
    meta_data = [
        ["Local", vistoria.local or "—"],
        ["Data da vistoria", vistoria.created_at.strftime("%d/%m/%Y") if vistoria.created_at else "—"],
        ["GPS", vistoria.gps or "—"],
        ["Engenheiro", vistoria.modelo.nome if vistoria.modelo else "—"],
    ]

    meta_table = Table(meta_data, colWidths=[3*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e5e7eb")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5*cm))

    # ---- DADOS DO FORMULÁRIO
    story.append(Paragraph("DADOS COLETADOS", secao_style))

    dados = vistoria.dados or {}
    for chave, valor in dados.items():
        if chave.startswith("_") or not valor:
            continue
        # Tentar extrair label do modelo
        label = chave.replace("_", " ").title()
        for secao in (vistoria.modelo.schema.get("secoes") or []):
            for campo in secao.get("campos", []):
                if campo.get("key") == chave:
                    label = campo.get("label", label)
                    break

        # Formatar valor
        if isinstance(valor, (list, dict)):
            valor_str = str(valor)[:100]  # truncar se muito grande
        else:
            valor_str = str(valor)

        linha_html = f"<b>{label}:</b> {valor_str}"
        story.append(Paragraph(linha_html, normal_style))

    story.append(Spacer(1, 0.3*cm))

    # ---- FOTOS (se houver)
    if vistoria.fotos:
        story.append(Paragraph("FOTOS DA VISTORIA", secao_style))
        fotos_data = []

        for idx, foto in enumerate(vistoria.fotos[:6]):  # máx 6 fotos por página
            try:
                # Se foto_path for caminho local, carregar; se for base64, skip (muito grande)
                if foto.arquivo_path and foto.arquivo_path.startswith("/"):
                    if Path(foto.arquivo_path).exists():
                        img = Image(foto.arquivo_path, width=4*cm, height=3*cm)
                        legenda = f"Foto {idx+1}: {foto.legenda or '—'}"
                        fotos_data.append([img, legenda])
            except Exception as e:
                print(f"Erro ao carregar foto {foto.id}: {e}")

        if fotos_data:
            fotos_table = Table(fotos_data, colWidths=[5*cm, 10*cm])
            fotos_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e5e7eb")),
            ]))
            story.append(fotos_table)
            story.append(Spacer(1, 0.5*cm))

    # ---- ASSINATURAS
    story.append(PageBreak())
    story.append(Paragraph("ASSINATURAS E CERTIFICAÇÃO", secao_style))

    # Tabela de assinaturas
    if vistoria.assinaturas:
        assin_data = [["Nome", "CPF/RG", "Papel", "Assinatura"]]
        for assin in vistoria.assinaturas:
            assin_data.append([
                assin.nome,
                assin.documento or "—",
                assin.papel,
                "[espaço para assinatura]" if not assin.imagem_path else "[assinado]"
            ])
        assin_table = Table(assin_data, colWidths=[4*cm, 3*cm, 3*cm, 4*cm])
        assin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#e5e7eb")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(assin_table)
    else:
        story.append(Paragraph("Nenhuma assinatura registrada.", normal_style))

    story.append(Spacer(1, 0.8*cm))

    # Campo de assinatura digital
    story.append(Paragraph(
        "<b>Este documento deve ser assinado digitalmente com certificado A3/WebSigner.</b><br/>"
        "Hash MD5: [a ser preenchido pelo sistema de assinatura]",
        normal_style
    ))

    # ---- BUILD PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def salvar_pdf_vistoria(vistoria: Vistoria, caminho_saida: str) -> str:
    """Gera PDF e salva em arquivo, retorna o caminho."""
    pdf_bytes = gerar_pdf_vistoria(vistoria)
    with open(caminho_saida, "wb") as f:
        f.write(pdf_bytes)
    return caminho_saida
