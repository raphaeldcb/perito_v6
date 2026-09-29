"""
Gerador de Laudo Forense em PDF — Estrutura formal p/ perícias judiciais.
Integra resultados do FakeDetectorCombo em documento auditável.
"""
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY


class LaudoForenseGenerator:
    """Gera PDF de laudo forense com análise de fake detector."""

    NOME_EMPRESA = "IPC-MS Perícias"
    CNPJ_EMPRESA = "XX.XXX.XXX/0001-XX"

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._add_custom_styles()

    def _add_custom_styles(self):
        """Define estilos customizados para o laudo."""
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=24,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='Conclusion',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            leftIndent=20,
            rightIndent=20,
            alignment=TA_JUSTIFY,
            fontName='Helvetica-Bold'
        ))

    def gerar_pdf(self, laudo_data: dict) -> bytes:
        """
        Gera PDF do laudo forense.

        Args:
            laudo_data: Dict com:
              - numero_laudo: str
              - cliente: {"nome": str, "cnpj": str, "email": str}
              - arquivo_hash: str
              - arquivo_nome: str
              - arquivo_tamanho_mb: float
              - arquivo_tipo: str
              - veredicto: str (APROVADO/REJEITADO/REVISAR)
              - authenticity_score: float (0-100)
              - consensus: float (0-100)
              - resultados_apis: [{"api": str, "is_fake": bool, "confidence": float}]
              - descricao: str (opcional)
              - created_at: str (ISO format)

        Returns:
            bytes: PDF renderizado
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch,
            title=f"Laudo Forense {laudo_data['numero_laudo']}"
        )

        story = []

        # Cabeçalho
        story.append(Paragraph(
            "LAUDO DE ANÁLISE FORENSE DE MÍDIA",
            self.styles['Title']
        ))
        story.append(Paragraph(
            f"{self.NOME_EMPRESA} | CNPJ: {self.CNPJ_EMPRESA}",
            self.styles['Subtitle']
        ))
        story.append(Spacer(1, 0.2*inch))

        # Informações do Laudo
        info_laudo = [
            ['Número do Laudo:', laudo_data['numero_laudo']],
            ['Data de Emissão:', laudo_data['created_at'][:10]],
            ['Hash do Arquivo:', laudo_data['arquivo_hash'][:32] + '...'],
        ]
        t = Table(info_laudo, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

        # Cliente
        story.append(Paragraph("<b>DADOS DO CLIENTE</b>", self.styles['Heading2']))
        cliente_data = [
            ['Nome:', laudo_data['cliente']['nome']],
            ['CNPJ/CPF:', laudo_data['cliente']['cnpj']],
            ['Email:', laudo_data['cliente']['email']],
        ]
        t = Table(cliente_data, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

        # Arquivo
        story.append(Paragraph("<b>ARQUIVO ANALISADO</b>", self.styles['Heading2']))
        arquivo_data = [
            ['Nome:', laudo_data['arquivo_nome']],
            ['Tipo:', laudo_data['arquivo_tipo']],
            ['Tamanho:', f"{laudo_data['arquivo_tamanho_mb']:.2f} MB"],
            ['Hash MD5:', laudo_data['arquivo_hash']],
        ]
        t = Table(arquivo_data, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

        # Resultados por API
        story.append(Paragraph("<b>ANÁLISE POR FERRAMENTAS</b>", self.styles['Heading2']))
        apis_data = [['Ferramenta', 'Resultado', 'Confiança']]
        for api_result in laudo_data['resultados_apis']:
            resultado = '✓ Legítimo' if not api_result['is_fake'] else '✗ Fake'
            confianca = f"{api_result.get('confidence', 0):.1f}%"
            apis_data.append([
                api_result['api'],
                resultado,
                confianca
            ])

        t = Table(apis_data, colWidths=[2*inch, 2*inch, 2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')])
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2*inch))

        # Resultado Final
        cor_veredicto = {
            'APROVADO': colors.HexColor('#2ecc71'),
            'REJEITADO': colors.HexColor('#e74c3c'),
            'REVISAR': colors.HexColor('#f39c12'),
        }.get(laudo_data['veredicto'], colors.grey)

        veredicto_text = f"""
        <font color="{cor_veredicto.hexval()}" size="14"><b>{laudo_data['veredicto']}</b></font><br/>
        Autenticidade: <b>{laudo_data['authenticity_score']:.1f}%</b><br/>
        Consenso: <b>{laudo_data['consensus']:.1f}%</b>
        """

        story.append(Paragraph("<b>VEREDICTO FINAL</b>", self.styles['Heading2']))
        story.append(Paragraph(veredicto_text, self.styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # Conclusão
        conclusao = "Com base na análise realizada pelas múltiplas ferramentas de detecção de deepfake, " \
                   f"concluímos que a mídia analisada foi classificada como <b>{laudo_data['veredicto']}</b> " \
                   f"com índice de autenticidade de {laudo_data['authenticity_score']:.1f}% e consenso de " \
                   f"{laudo_data['consensus']:.1f}% entre as ferramentas utilizadas."

        story.append(Paragraph(conclusao, self.styles['Conclusion']))
        story.append(Spacer(1, 0.3*inch))

        # Rodapé
        rodape = f"""
        <font size="8">
        Laudo gerado automaticamente pelo sistema IPC-MS Perícias.<br/>
        Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br/>
        Número: {laudo_data['numero_laudo']}<br/>
        <i>Documento com validade legal para fins periciais.</i>
        </font>
        """
        story.append(Paragraph(rodape, self.styles['Normal']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
