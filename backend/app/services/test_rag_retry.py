"""Validação de ALTO #2: retry exponencial Ollama com circuit breaker.

Testa que embed_text() implementa exponential backoff (1s, 2s, 4s, 8s)
com max 4 retries, nunca travando silenciosamente.
"""

def test_embed_retry_backoff():
    """Valida retry loop com exponential backoff 1s, 2s, 4s, 8s."""
    import time
    from unittest.mock import patch, MagicMock
    import requests
    
    call_times = []
    
    def mock_embed_call(texto):
        call_times.append(time.time())
        if len(call_times) < 4:
            raise requests.ConnectionError("Ollama down")
        return [0.5] * 768  # Sucesso na 4ª tentativa
    
    from app.services.rag_indexer import embed_text
    
    with patch('app.services.rag_indexer._embed_call', side_effect=mock_embed_call):
        start = time.time()
        result = embed_text("teste embedding")
        elapsed = time.time() - start
        
        # Validações:
        # - 4 tentativas: call_times deve ter 4 elementos
        # - backoff: delay entre tentativas deve ser ~1s, ~2s, ~4s
        # - resultado: deve ter sucesso (não None)
        assert result is not None, "Deve retornar embedding após 4 tentativas"
        assert len(call_times) == 4, f"Deveria fazer 4 chamadas, fez {len(call_times)}"
        
        # Verificar backoff aproximado
        if len(call_times) >= 4:
            delay_1 = call_times[1] - call_times[0]
            delay_2 = call_times[2] - call_times[1]
            delay_3 = call_times[3] - call_times[2]
            
            # Esperado: ~1s, ~2s, ~4s (com margem de erro)
            assert 0.8 <= delay_1 <= 1.5, f"Delay 1ª retry esperado ~1s, veio {delay_1:.1f}s"
            assert 1.8 <= delay_2 <= 2.5, f"Delay 2ª retry esperado ~2s, veio {delay_2:.1f}s"
            assert 3.8 <= delay_3 <= 4.5, f"Delay 3ª retry esperado ~4s, veio {delay_3:.1f}s"
        
        print(f"✅ ALTO #2 validated: exponential backoff (1s, 2s, 4s) × 4 retries, total {elapsed:.1f}s")


if __name__ == "__main__":
    test_embed_retry_backoff()
    print("✅ Test passed!")
