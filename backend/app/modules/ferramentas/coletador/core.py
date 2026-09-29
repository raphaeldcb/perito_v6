"""CNAB240 generator for Banco Inter payments.

Estrutura reutilizável para pagamentos mensais via PIX.
"""
from datetime import datetime
from typing import List, Tuple, Dict, Any


def gerar_cnab240(
    dados_empresa: Dict[str, Any],
    beneficiarios: List[Dict[str, Any]],
    data_pagamento: str = None,
) -> Tuple[List[str], int]:
    """
    Gera arquivo CNAB240 para Banco Inter (código 077).

    Args:
        dados_empresa: dict com {cnpj, agencia, conta, dv_conta}
        beneficiarios: list de dicts com {nome, cpf, agencia, conta, dv, valor}
        data_pagamento: str DDMMYYYY (default: hoje)

    Returns:
        tuple: (list de linhas (240 chars cada), total_valor em centavos)
    """

    if data_pagamento is None:
        data_pagamento = datetime.now().strftime("%d%m%Y")

    linhas = []
    seq = 0
    total_valor = 0

    # Dados empresa
    cnpj = dados_empresa.get('cnpj', '14424142000190')
    agencia = dados_empresa.get('agencia', '00001').rjust(5, '0')
    conta = dados_empresa.get('conta', '4335168').rjust(12, '0')
    dv = dados_empresa.get('dv_conta', '9')
    nome_empresa = dados_empresa.get('nome', 'IPCMS')
    nome_banco = dados_empresa.get('nome_banco', 'BANCO INTER')

    # ===== HEADER ARQUIVO =====
    seq += 1
    l = ("077" +                                      # 1-3: Banco
         "0000" +                                     # 4-7: Lote
         "0" +                                        # 8: Tipo
         ("0"*9) +                                    # 9-17: Reservado
         "1" +                                        # 18: Tipo Inscrição (CNPJ)
         cnpj.ljust(14) +                             # 19-32: CNPJ (alfabético)
         (" "*20) +                                   # 33-52: Convenio
         agencia +                                    # 53-57: Agência
         "0" +                                        # 58: DV Agência
         conta +                                      # 59-70: Conta
         dv +                                         # 71: DV Conta
         " " +                                        # 72: Reservado
         nome_empresa.ljust(30)[:30] +                # 73-102: Nome empresa
         nome_banco.ljust(30)[:30] +                  # 103-132: Nome banco
         (" "*10) +                                   # 133-142: Reservado
         "1" +                                        # 143: Código remessa
         data_pagamento +                             # 144-151: Data geração
         "000000" +                                   # 152-157: Hora
         "000001" +                                   # 158-163: Seq arquivo
         "045" +                                      # 164-166: Versão layout
         "01600" +                                    # 167-171: Densidade
         (" "*69))[:240]                              # 172-240: Reservado

    linhas.append(l.ljust(240))

    # ===== HEADER LOTE =====
    seq += 1
    l = ("077" +                                      # 1-3: Banco
         "0001" +                                     # 4-7: Lote
         "1" +                                        # 8: Tipo (1=header lote)
         "C" +                                        # 9: Operação (Crédito)
         "20" +                                       # 10-11: Tipo serviço (PIX)
         "01" +                                       # 12-13: Forma lançamento
         "045" +                                      # 14-16: Versão layout
         " " +                                        # 17: Reservado
         "1" +                                        # 18: Tipo inscricao
         cnpj.ljust(14) +                             # 19-32: CNPJ
         (" "*20) +                                   # 33-52: Convenio
         agencia +                                    # 53-57: Agência
         "0" +                                        # 58: DV
         conta +                                      # 59-70: Conta
         dv +                                         # 71: DV
         " " +                                        # 72: Reservado
         nome_empresa.ljust(30)[:30] +                # 73-102: Nome
         (" "*40) +                                   # 103-142: Info
         "00001" +                                    # 143-147: Numero remessa
         (" "*8) +                                    # 148-155: Numero lote retorno
         data_pagamento +                             # 156-163: Data geração
         data_pagamento +                             # 164-171: Data crédito
         (" "*69))[:240]                              # 172-240: Reservado

    linhas.append(l.ljust(240))

    # ===== SEGMENTOS A + B =====
    for i, benef in enumerate(beneficiarios, 1):
        # SEGMENTO A
        seq += 1
        valor = int(benef.get('valor', 0))
        total_valor += valor

        l = ("077" +                                  # 1-3: Banco
             "0001" +                                 # 4-7: Lote
             "3" +                                    # 8: Tipo
             str(seq).rjust(5, '0') +                 # 9-13: Seq
             "A" +                                    # 14: Segmento
             "00" +                                   # 15-16: Movimento
             "1" +                                    # 17: Tipo inscricao (CPF)
             "000" +                                  # 18-20: Câmara
             "000" +                                  # 21-23: Banco benef
             benef.get('agencia', '00001').rjust(5, '0') +  # 24-28: Agência
             benef.get('dv', '0') +                   # 29: DV agência
             benef.get('conta', '0').rjust(12, '0') + # 30-41: Conta
             benef.get('dv', '0') +                   # 42: DV conta
             " " +                                    # 43: DV geral
             benef.get('nome', '').ljust(30)[:30] +   # 44-73: Nome
             str(i).rjust(20, '0') +                  # 74-93: Seu número
             data_pagamento +                         # 94-101: Data pag
             "BRL" +                                  # 102-104: Moeda
             ("0"*15) +                               # 105-119: Qtd moeda
             str(valor).rjust(15, '0') +              # 120-134: Valor
             (" "*20) +                               # 135-154: Nosso número
             "00000000" +                             # 155-162: Data real
             ("0"*15) +                               # 163-177: Valor real
             (" "*40) +                               # 178-217: Informação
             "00" +                                   # 218-219: Cod final doc
             "00000" +                                # 220-224: Cod final ted
             "00" +                                   # 225-226: Cod final compl
             "000" +                                  # 227-229: CNAB
             "0" +                                    # 230: Aviso
             (" "*10))[:240]                          # 231-240: Ocorrências

        linhas.append(l.ljust(240))

        # SEGMENTO B
        seq += 1
        l = ("077" +                                  # 1-3: Banco
             "0001" +                                 # 4-7: Lote
             "3" +                                    # 8: Tipo
             str(seq).rjust(5, '0') +                 # 9-13: Seq
             "B" +                                    # 14: Segmento
             "00" +                                   # 15-16: Movimento
             ("0"*5) +                                # 17-21: IR alíquota
             ("0"*15) +                               # 22-36: IR valor
             (" "*140) +                              # 37-176: Descrição
             "0" +                                    # 177: Aviso
             (" "*12) +                               # 178-189: Instrução 1
             (" "*12) +                               # 190-201: Instrução 2
             (" "*39))[:240]                          # 202-240: Reservado

        linhas.append(l.ljust(240))

    # ===== TRAILER LOTE =====
    seq += 1
    l = ("077" +                                      # 1-3: Banco
         "0001" +                                     # 4-7: Lote
         "5" +                                        # 8: Tipo
         str(seq).rjust(5, '0') +                     # 9-13: Seq
         " " +                                        # 14: Reservado
         str(seq-1).rjust(6, '0') +                   # 15-20: Qtd registros
         str(len(beneficiarios)).rjust(6, '0') +      # 21-26: Qtd créditos
         str(total_valor).rjust(18, '0') +            # 27-44: Valor total
         ("0"*6) +                                    # 45-50: Qtd débitos
         ("0"*18) +                                   # 51-68: Valor débitos
         ("0"*6) +                                    # 69-74: Qtd avisos
         (" "*166))[:240]                             # 75-240: Reservado

    linhas.append(l.ljust(240))

    # ===== TRAILER ARQUIVO =====
    seq += 1
    l = ("077" +                                      # 1-3: Banco
         "9999" +                                     # 4-7: Lote
         "9" +                                        # 8: Tipo
         str(seq).rjust(5, '0') +                     # 9-13: Seq
         " " +                                        # 14: Reservado
         "1" +                                        # 15: Qtd lotes
         "1" +                                        # 16: Qtd lotes arquivo
         str(seq).rjust(6, '0') +                     # 17-22: Qtd registros
         (" "*218))[:240]                             # 23-240: Reservado

    linhas.append(l.ljust(240))

    return linhas, total_valor


def salvar_arquivo(linhas: List[str], nome_arquivo: str = None) -> str:
    """Salva linhas em arquivo .rem com encoding ASCII + CRLF."""
    if nome_arquivo is None:
        agora = datetime.now().strftime("%d%m%Y%H%M%S")
        nome_arquivo = f"CI240_001_{agora}.rem"

    with open(nome_arquivo, 'wb') as f:
        for linha in linhas:
            f.write(linha.encode('ascii') + b'\r\n')

    return nome_arquivo
