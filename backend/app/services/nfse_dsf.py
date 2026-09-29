"""Integração NFSe — prefeitura de Campo Grande/MS (provedor DSF, WsNFe2/LoteRps).

Layout extraído do Manual oficial (v6/docs/manual_nfse_dsf_campogrande.txt):
- Envio de lote de RPS assinado (cada RPS tem uma Assinatura SHA-1 dos campos).
- Homologação NÃO exige assinatura XML do lote; Produção EXIGE (XMLDSig com A1).
- HÁ ambiente de homologação: dá para testar sem emitir nota real.

Guardas: emissão real (transmissão ao WS) só com NFSE_EMISSAO_ATIVA=1.
Ambiente escolhido por NFSE_AMBIENTE ('homologacao' | 'producao').
"""
import hashlib
import os
import logging
import subprocess
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

# URLs do webservice DSF (do manual)
WS_HOMOLOGACAO = "https://issdigital-h.pmcg.ms.gov.br/WsNFe2/LoteRps.jws"
WS_PRODUCAO = "https://issdigital.pmcg.ms.gov.br/WsNFe2/LoteRps.jws"

COD_CIDADE_CG = "9051"  # SIAFI Campo Grande/MS

AMBIENTE = os.environ.get("NFSE_AMBIENTE", "homologacao")
EMISSAO_ATIVA = os.environ.get("NFSE_EMISSAO_ATIVA", "0") == "1"

# Configuração por empresa (chave = CNPJ só dígitos). Cada uma tem sua
# inscrição municipal e seu próprio certificado A1.
EMITENTES = {
    "00920892000149": {  # IPC MS Perícias — CNAE 7119-7/03
        "razao": "IPC MS PERICIAS LTDA",
        "inscricao": "00041121009",
        "cnae": "711970300",
        "aliquota": 5.0,
        "cert_path": "/data/certs/ipc_pericias_a1.pfx",
        "cert_senha": os.environ.get("NFSE_SENHA_PERICIAS", ""),
    },
    "14424142000190": {  # IPC MS Pesquisa — CNAE 8640-2/02
        "razao": "INSTITUTO DE PESQUISAS CIENTIFICAS LTDA",
        "inscricao": "00164980006",
        "cnae": "864020201",
        "aliquota": 5.0,
        "cert_path": "/data/certs/ipc_pesquisa_a1.pfx",
        "cert_senha": os.environ.get("NFSE_SENHA_PESQUISA", ""),
    },
}
# Empresa emitente padrão (perícias saem pela Perícias)
CNPJ_PADRAO = os.environ.get("NFSE_CNPJ_PADRAO", "00920892000149")


def emitente(cnpj: str = None) -> dict:
    return EMITENTES.get(_so_digitos(cnpj) or CNPJ_PADRAO, EMITENTES[CNPJ_PADRAO])


def ws_url() -> str:
    return WS_PRODUCAO if AMBIENTE == "producao" else WS_HOMOLOGACAO


def certificado_disponivel(cnpj: str = None) -> tuple[bool, str]:
    emt = emitente(cnpj)
    if not os.path.exists(emt["cert_path"]):
        return False, f"Certificado não encontrado em {emt['cert_path']}"
    if not emt["cert_senha"]:
        return False, "Senha do certificado não configurada (NFSE_SENHA_*)"
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        with open(emt["cert_path"], "rb") as f:
            pkcs12.load_key_and_certificates(f.read(), emt["cert_senha"].encode())
        return True, f"Certificado A1 de {emt['razao']} válido"
    except Exception as e:
        return False, f"Falha ao abrir certificado: {e}"


def _so_digitos(v) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _centavos(v) -> str:
    """Valor em centavos, string só de dígitos."""
    return str(int(round(float(v or 0) * 100)))


def assinatura_rps(nota, inscricao_municipal: str, codigo_atividade: str,
                   tributacao: str = "T", situacao: str = "N",
                   tipo_recolhimento: str = "A") -> str:
    """Assinatura do RPS: concatenação de 11 campos com larguras fixas → SHA-1.

    Layout (Manual, seção Assinatura):
      01 InscrMunicipal   11  zeros à esquerda
      02 Série RPS         5  espaços à direita
      03 Número RPS       12  zeros à esquerda
      04 DataEmissão       8  yyyyMMdd
      05 Tributação        2  espaço à direita
      06 Situação          1
      07 TipoRecolhimento  1  'A'→'N', senão 'S'
      08 Valor-Dedução    15  centavos, zeros à esquerda
      09 Dedução          15  centavos, zeros à esquerda
      10 Cód. Atividade   10  zeros à esquerda
      11 CPF/CNPJ tomador 14  zeros à esquerda
    """
    valor = float(nota.valor_servico or 0)
    linha = (
        _so_digitos(inscricao_municipal).zfill(11)
        + (nota.serie_rps or "NF").ljust(5)[:5]
        + _so_digitos(nota.numero_rps).zfill(12)
        + (nota.data_emissao or datetime.now()).strftime("%Y%m%d")
        + (tributacao or "T").ljust(2)[:2]
        + (situacao or "N")[:1]
        + ("N" if (tipo_recolhimento or "A") == "A" else "S")
        + _centavos(valor).zfill(15)
        + "0".zfill(15)                                  # dedução = 0
        + _so_digitos(codigo_atividade).zfill(10)
        + _so_digitos(nota.tomador_documento).zfill(14)
    )
    return hashlib.sha1(linha.encode("utf-8")).hexdigest()


def montar_lote_xml(notas: list, emt: dict) -> str:
    """Monta o XML ReciboLote (Cabecalho + lista de RPS) no layout DSF, para a
    empresa emitente `emt` (dict com razao/inscricao/cnpj)."""
    from xml.sax.saxutils import escape

    inscricao_municipal = emt["inscricao"]
    razao = emt["razao"]
    cnpj = emt.get("cnpj", "")

    total_serv = sum(float(n.valor_servico or 0) for n in notas)
    datas = [(n.data_emissao or datetime.now()) for n in notas]
    dt_ini = min(datas).strftime("%Y-%m-%d")
    dt_fim = max(datas).strftime("%Y-%m-%d")

    rps_xml = []
    for n in notas:
        cod_ativ = n.codigo_servico or emt.get("cnae", "")
        aliq = float(n.aliquota_iss if n.aliquota_iss is not None else emt.get("aliquota", 0))
        assin = assinatura_rps(n, inscricao_municipal, cod_ativ)
        # documento do tomador: CPF (11) ou CNPJ (14) → sempre 14 com zeros à esq.
        doc_tom = _so_digitos(n.tomador_documento).zfill(14)
        rps_xml.append(f"""
    <RPS>
      <Assinatura>{assin}</Assinatura>
      <InscricaoMunicipalPrestador>{_so_digitos(inscricao_municipal).zfill(11)}</InscricaoMunicipalPrestador>
      <RazaoSocialPrestador>{escape(razao)}</RazaoSocialPrestador>
      <TipoRPS>RPS</TipoRPS>
      <SerieRPS>{n.serie_rps or 'NF'}</SerieRPS>
      <NumeroRPS>{_so_digitos(n.numero_rps)}</NumeroRPS>
      <DataEmissaoRPS>{(n.data_emissao or datetime.now()).strftime('%Y-%m-%dT%H:%M:%S')}</DataEmissaoRPS>
      <SituacaoRPS>N</SituacaoRPS>
      <SeriePrestacao>99</SeriePrestacao>
      <InscricaoMunicipalTomador>0000000</InscricaoMunicipalTomador>
      <CPFCNPJTomador>{doc_tom}</CPFCNPJTomador>
      <RazaoSocialTomador>{escape(n.tomador_nome or '')}</RazaoSocialTomador>
      <TipoLogradouroTomador>Rua</TipoLogradouroTomador>
      <LogradouroTomador>{escape(n.tomador_logradouro or '')}</LogradouroTomador>
      <NumeroEnderecoTomador>{escape(n.tomador_numero or 'S/N')}</NumeroEnderecoTomador>
      <ComplementoEnderecoTomador></ComplementoEnderecoTomador>
      <TipoBairroTomador>Bairro</TipoBairroTomador>
      <BairroTomador>{escape(n.tomador_bairro or '')}</BairroTomador>
      <CidadeTomador>{COD_CIDADE_CG}</CidadeTomador>
      <CidadeTomadorDescricao>{escape(n.tomador_cidade or 'CAMPO GRANDE')}</CidadeTomadorDescricao>
      <CEPTomador>{_so_digitos(n.tomador_cep).zfill(8)}</CEPTomador>
      <EmailTomador>{escape(n.tomador_email or '-')}</EmailTomador>
      <CodigoAtividade>{cod_ativ}</CodigoAtividade>
      <AliquotaAtividade>{aliq:.4f}</AliquotaAtividade>
      <TipoRecolhimento>A</TipoRecolhimento>
      <MunicipioPrestacao>{COD_CIDADE_CG}</MunicipioPrestacao>
      <MunicipioPrestacaoDescricao>CAMPO GRANDE</MunicipioPrestacaoDescricao>
      <Operacao>A</Operacao>
      <Tributacao>T</Tributacao>
      <ValorServico>{float(n.valor_servico or 0):.2f}</ValorServico>
      <ValorDeducao>0.00</ValorDeducao>
      <DiscriminacaoServico>{escape((n.discriminacao or '')[:1000])}</DiscriminacaoServico>
    </RPS>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ReciboLote xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Cabecalho Versao="1">
    <CodCidade>{COD_CIDADE_CG}</CodCidade>
    <CPFCNPJRemetente>{_so_digitos(cnpj).zfill(14)}</CPFCNPJRemetente>
    <RazaoSocialRemetente>{escape(razao)}</RazaoSocialRemetente>
    <Transacao>true</Transacao>
    <DtInicio>{dt_ini}</DtInicio>
    <DtFim>{dt_fim}</DtFim>
    <QtdRPS>{len(notas)}</QtdRPS>
    <ValorTotalServicos>{total_serv:.2f}</ValorTotalServicos>
    <ValorTotalDeducoes>0.00</ValorTotalDeducoes>
    <Versao>1</Versao>
    <MetodoEnvio>WS</MetodoEnvio>
  </Cabecalho>
  <Lote>{''.join(rps_xml)}
  </Lote>
</ReciboLote>"""


def _assinar_xml_a1(xml_str: str, cert_id: str = None) -> tuple[bool, str]:
    """Assina XML ReciboLote com certificado A1 via xmlsec3 (bash).

    Retorna: (sucesso, xml_assinado_ou_erro)
    """
    from app.services.a1_manager import A1Manager

    try:
        a1 = A1Manager()
        cert_info = a1.get_cert_info(cert_id)
        cert_path = cert_info["path"]
        cert_password = cert_info["password"].decode() if isinstance(cert_info["password"], bytes) else cert_info["password"]

        # Verificar xmlsec3 disponível
        try:
            subprocess.run(["which", "xmlsec1"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("xmlsec1 not found, skipping A1 signing (test mode)")
            return True, xml_str  # Em dev/homolog, continua sem assinatura

        # Escrever XML temp + certificado temp
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_str)
            xml_tmp = f.name

        with tempfile.NamedTemporaryFile(suffix='.pfx', delete=False) as f:
            # Copiar .pfx pro temp
            with open(cert_path, 'rb') as src:
                f.write(src.read())
            pfx_tmp = f.name

        try:
            # Assinar com xmlsec1
            # xmlsec1 sign --pkcs12 <cert> --pwd <senha> <arquivo.xml>
            cmd = [
                "xmlsec1", "sign",
                "--pkcs12", pfx_tmp,
                "--pwd", cert_password,
                "--output", xml_tmp,
                xml_tmp
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return False, f"xmlsec1 error: {result.stderr}"

            # Ler XML assinado
            with open(xml_tmp, 'r') as f:
                xml_assinado = f.read()

            return True, xml_assinado

        finally:
            # Cleanup
            os.unlink(xml_tmp) if os.path.exists(xml_tmp) else None
            os.unlink(pfx_tmp) if os.path.exists(pfx_tmp) else None

    except Exception as e:
        logger.error(f"A1 signing failed: {str(e)}")
        return False, str(e)


def emitir(nota, cnpj_emitente: str = None) -> dict:
    """Emite UMA nota (lote de 1 RPS) pela empresa `cnpj_emitente`.
    Sem NFSE_EMISSAO_ATIVA, monta o lote mas NÃO transmite.
    Em produção: assina com A1 antes de enviar.
    """
    emt = dict(emitente(cnpj_emitente))
    emt["cnpj"] = _so_digitos(cnpj_emitente) or CNPJ_PADRAO
    if not emt.get("inscricao"):
        return {"status": "erro", "erro": "Inscrição Municipal do emitente não configurada"}

    xml = montar_lote_xml([nota], emt)

    if not EMISSAO_ATIVA:
        return {
            "status": "rascunho",
            "mensagem": f"Emissão real DESLIGADA (NFSE_EMISSAO_ATIVA=0). Lote montado "
                        f"por {emt['razao']} para {AMBIENTE}, nada transmitido.",
            "xml": xml,
        }

    # Em produção: assinar com A1 antes de enviar
    if AMBIENTE == "producao":
        ok, msg = certificado_disponivel(emt["cnpj"])
        if not ok:
            return {"status": "erro", "erro": msg}

        # Assinar XML com A1 (cert_id vem de nota.cert_id_usado se disponível)
        cert_id = getattr(nota, 'cert_id_usado', None)
        assinado, xml_ou_erro = _assinar_xml_a1(xml, cert_id)
        if not assinado:
            return {"status": "erro", "erro": f"Falha ao assinar com A1: {xml_ou_erro}"}
        xml = xml_ou_erro

    return _enviar_soap(xml)


def _enviar_soap(xml_lote: str) -> dict:
    """Chama o método EnviarLoteRPS do WsNFe2 (SOAP) e interpreta o retorno."""
    import re
    import requests
    from xml.sax.saxutils import escape

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:web="http://www.webservice.dsf.com.br">
  <soapenv:Body>
    <web:enviar>
      <web:VersaoSchema>1</web:VersaoSchema>
      <web:MensagemXML>{escape(xml_lote)}</web:MensagemXML>
    </web:enviar>
  </soapenv:Body>
</soapenv:Envelope>"""

    try:
        resp = requests.post(
            ws_url(),
            data=envelope.encode("utf-8"),
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "enviar"},
            timeout=60,
        )
    except Exception as e:
        return {"status": "erro", "erro": f"Falha na conexão com o WS ({AMBIENTE}): {e}"}

    corpo = resp.text
    if "<Sucesso>true</Sucesso>" in corpo or "&lt;Sucesso&gt;true" in corpo:
        num = re.search(r"(?:&lt;|<)NumeroNota(?:&gt;|>)(\d+)", corpo)
        cod = re.search(r"(?:&lt;|<)CodigoVerificacao(?:&gt;|>)([^<&]+)", corpo)
        return {"status": "emitida",
                "numero_nfse": num.group(1) if num else None,
                "codigo_verificacao": cod.group(1) if cod else None,
                "retorno": corpo[:2000]}
    return {"status": "erro", "erro": f"WS não retornou sucesso: {corpo[:1500]}"}
