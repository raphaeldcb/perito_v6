import json
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import subprocess

class NfsEOllamaAnalyzer:
    def __init__(self, ollama_model: str = "llama3"):
        self.ollama_model = ollama_model

    def analisar_xml_nfse(self, xml_content: str) -> Dict:
        """
        Usa Ollama para analisar o conteúdo XML da NFS-e e extrair campos chave.
        """
        # Preparar o prompt para o Ollama
        prompt = f"""
        Analise o seguinte XML de NFS-e e extraia os seguintes campos:
        - Número da NFS-e
        - Data de Emissão
        - Valor Total
        - Nome do Tomador
        - CPF/CNPJ do Tomador
        - Endereço do Tomador
        - Código de Serviços (ISSQN)
        - Alíquota ISSQN
        - Valor ISSQN
        
        XML:
        {xml_content}
        
        Retorne apenas um JSON válido com os campos extraídos.
        """
        
        # Chamar Ollama via subprocess
        try:
            result = subprocess.run(
                ["ollama", "run", self.ollama_model, prompt],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Tentar parsear o JSON retornado
                try:
                    # Remover possíveis marcações de markdown ```json ... ```
                    if output.startswith("```json"):
                        output = output[7:]
                    if output.endswith("```"):
                        output = output[:-3]
                    output = output.strip()
                    
                    data = json.loads(output)
                    return data
                except json.JSONDecodeError:
                    return {"erro": "Falha ao parsear JSON retornado pelo Ollama", "raw_output": output}
            else:
                return {"erro": "Erro ao chamar Ollama", "stderr": result.stderr}
                
        except subprocess.TimeoutExpired:
            return {"erro": "Timeout ao chamar Ollama"}
        except Exception as e:
            return {"erro": str(e)}

    def processar_arquivo_xml(self, caminho_arquivo: str) -> Dict:
        """Processa um arquivo XML de NFS-e."""
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            return self.analisar_xml_nfse(xml_content)
        except Exception as e:
            return {"erro": f"Erro ao ler arquivo: {str(e)}"}

# Exemplo de uso
if __name__ == "__main__":
    analyzer = NfsEOllamaAnalyzer()
    
    # Exemplo de XML simples
    xml_exemplo = """
    <Nfse>
        <InfNfse Id="1">
            <Numero>001</Numero>
            <DataEmissao>2024-05-01</DataEmissao>
            <ValorTotal>1000.00</ValorTotal>
            <Tomador>
                <RazaoSocial>Empresa A</RazaoSocial>
                <DocumentoIdentificacao>
                    <CNPJ>***REMOVED***000190</CNPJ>
                </DocumentoIdentificacao>
            </Tomador>
        </InfNfse>
    </Nfse>
    """
    
    resultado = analyzer.analisar_xml_nfse(xml_exemplo)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
