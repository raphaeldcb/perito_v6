import pytest
from app.services.forensic_docx_mapper import ForensicDocxMapper

def test_extract_placeholders_from_template():
    mapper = ForensicDocxMapper()
    placeholders = mapper.extract_placeholders()

    assert '{{CODIGO_LAUDO}}' in placeholders
    assert '{{CONTRATANTE}}' in placeholders
    assert '{{ARQUIVO_NOME}}' in placeholders
    assert '{{ARQUIVO_HASH_SHA256}}' in placeholders
    assert len(placeholders) >= 50

def test_map_forensic_data_to_docx():
    mapper = ForensicDocxMapper()
    data = {
        'codigo_laudo': 'L202608070001',
        'contratante': 'João Silva',
        'objeto': 'Análise de imagem suspeita',
        'arquivo_nome': 'foto.jpg',
        'arquivo_mime': 'image/jpeg',
        'arquivo_dimensoes': '1920x1080',
        'arquivo_tamanho': '2048000',
        'arquivo_hash_sha256': 'abc123...',
        'arquivo_hash_sha1': 'def456...',
        'arquivo_hash_md5': 'ghi789...',
        'data_calculo_hash': '2026-08-07T14:30:00Z',
        'total_achados': '3',
        'total_criticos': '1',
        'total_alertas': '2',
        'total_informativos': '0',
        'confianca': '92',
        'nivel_risco': 'ALTO'
    }

    mapped = mapper.map_data(data)
    assert mapped['{{CODIGO_LAUDO}}'] == 'L202608070001'
    assert mapped['{{CONTRATANTE}}'] == 'João Silva'
    assert mapped['{{ARQUIVO_HASH_SHA256}}'] == 'abc123...'
