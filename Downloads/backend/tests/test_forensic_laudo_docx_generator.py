"""
Test suite for ForensicLaudoDocxGenerator.
Tests template loading, placeholder replacement in paragraphs and tables.
"""
import pytest
from pathlib import Path
from io import BytesIO
from app.services.forensic_laudo_docx_generator import ForensicLaudoDocxGenerator


def test_generate_laudo_docx_with_full_data():
    """Test generating DOCX with full forensic analysis data."""
    # Use local template path for testing
    template_path = Path(__file__).parent.parent / "app" / "templates" / "TEMPLATE_LAUDO_FORENSE.docx"
    generator = ForensicLaudoDocxGenerator(template_path=template_path)

    analysis_data = {
        'codigo_laudo': 'L202608070001',
        'contratante': 'João Silva',
        'objeto': 'Análise de imagem suspeita de deepfake',
        'arquivo_nome': 'video_questionado.mp4',
        'arquivo_mime': 'video/mp4',
        'arquivo_dimensoes': '1920x1080@30fps',
        'arquivo_tamanho': '104857600',
        'arquivo_hash_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        'arquivo_hash_sha1': 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
        'arquivo_hash_md5': 'd41d8cd98f00b204e9800998ecf8427e',
        'data_calculo_hash': '2026-08-07T14:30:00Z',
        'total_achados': '5',
        'total_criticos': '2',
        'total_alertas': '3',
        'total_informativos': '0',
        'confianca': '85',
        'nivel_risco': 'ALTO'
    }

    # Generate DOCX
    docx_bytes = generator.generate(analysis_data)

    # Verify it's bytes
    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000

    # Verify it's a valid DOCX (ZIP archive with PK signature)
    assert docx_bytes[:2] == b'PK'

    # Verify content was replaced
    from docx import Document
    doc = Document(BytesIO(docx_bytes))
    full_text = '\n'.join([p.text for p in doc.paragraphs])

    # Check for replaced values
    assert 'L202608070001' in full_text
    assert 'João Silva' in full_text
    assert 'deepfake' in full_text
    assert 'ALTO' in full_text
