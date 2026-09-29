"""Seed initial data to database"""
import os
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models import Role, User, Tool, Permission
from app.models.kanban import Kanban, KanbanColuna
from app.services import hash_password
from app.services.database import SessionLocal


PERITOS_REAIS = [
    ("Marzia Almeida Samha Santos", "marzia@ipcms.com.br"),
    ("Paulo Sérgio Penha da Silva", "paulo.silva@ipcms.com.br"),
    ("Alaíde Rodrigues Fraga", "alaide@ipcms.com.br"),
    ("Walter Pereira Dias", "walter@ipcms.com.br"),
    ("Elenilde Aparecida Neco da Silva", "elenilde@ipcms.com.br"),
    ("Iza Maria Ribeiro Coelho", "iza@ipcms.com.br"),
    ("Luzia Aparecida Miranda", "luzia@ipcms.com.br"),
    ("Tânia Rossana Antunes Quintana", "tania@ipcms.com.br"),
    ("Gervásio Tadeu Teixeira Viana", "gervasio@ipcms.com.br"),
    ("João Silva Pereira", "joao.silva@ipcms.com.br"),
    ("Maria Oliveira Santos", "maria.oliveira@ipcms.com.br"),
    ("Carlos Alberto Dias", "carlos.dias@ipcms.com.br"),
    ("Ana Paula Costa", "ana.costa@ipcms.com.br"),
    ("Roberto Ferreira", "roberto.ferreira@ipcms.com.br"),
    ("Fernanda Rodrigues", "fernanda.rodrigues@ipcms.com.br"),
]

KANBAN_COLUNAS_PADRAO = [
    ("Rascunho", 1, "#95a5a6"),
    ("Em Análise", 2, "#f39c12"),
    ("Revisão", 3, "#3498db"),
    ("Aprovado", 4, "#2ecc71"),
    ("Pronto para Protocolar", 5, "#9b59b6"),
    ("Protocolado", 6, "#27ae60"),
]


def seed_roles(db: Session):
    roles = [
        Role(name="admin", description="Administrator with full access"),
        Role(name="power_user", description="Power user with extended access"),
        Role(name="user", description="Standard user"),
        Role(name="coletador", description="Coletador — acesso apenas ao próprio portal"),
        Role(name="public", description="Public access (unauthenticated)"),
    ]
    for role in roles:
        if not db.query(Role).filter(Role.name == role.name).first():
            db.add(role)
    db.commit()
    print("✅ Roles seeded")


def seed_permissions(db: Session):
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    power_user_role = db.query(Role).filter(Role.name == "power_user").first()
    user_role = db.query(Role).filter(Role.name == "user").first()

    permissions = [
        # Admin permissions
        Permission(role_id=admin_role.id, action="read", resource="users"),
        Permission(role_id=admin_role.id, action="write", resource="users"),
        Permission(role_id=admin_role.id, action="delete", resource="users"),
        Permission(role_id=admin_role.id, action="admin", resource="tools"),
        Permission(role_id=admin_role.id, action="read", resource="audit_logs"),

        # Power user permissions
        Permission(role_id=power_user_role.id, action="read", resource="tools"),
        Permission(role_id=power_user_role.id, action="write", resource="tools"),
        Permission(role_id=power_user_role.id, action="read", resource="audit_logs"),

        # User permissions
        Permission(role_id=user_role.id, action="read", resource="tools"),
    ]

    for perm in permissions:
        if not db.query(Permission).filter(
            Permission.role_id == perm.role_id,
            Permission.action == perm.action,
            Permission.resource == perm.resource
        ).first():
            db.add(perm)
    db.commit()
    print("✅ Permissions seeded")


def seed_admin_user(db: Session):
    # admin@perito.local não pode ser usado: o EmailStr do login rejeita o TLD
    # reservado ".local", tornando o login desse usuário impossível.
    import os
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@ipcms.com.br")
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")

    admin_role = db.query(Role).filter(Role.name == "admin").first()

    if not db.query(User).filter(User.email == admin_email).first():
        admin = User(
            email=admin_email,
            full_name="Administrator",
            hashed_password=hash_password(admin_password),
            is_active=True,
            role_id=admin_role.id,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin user created ({admin_email})")

    # Bruno — dono, admin (login "bruno")
    if not db.query(User).filter(User.email == "bruno@ipcms.com.br").first():
        db.add(User(email="bruno@ipcms.com.br", full_name="Bruno",
                    hashed_password=hash_password(os.environ.get("BRUNO_PASSWORD", "1234adv")),
                    is_active=True, role_id=admin_role.id))
        db.commit()
        print("✅ Bruno (admin) criado")


def seed_peritos_reais(db: Session):
    """Seed 15+ real peritos from IPC MS"""
    user_role = db.query(Role).filter(Role.name == "user").first()

    peritos_criados = 0
    for nome, email in PERITOS_REAIS:
        if not db.query(User).filter(User.email == email).first():
            perito = User(
                email=email,
                full_name=nome,
                hashed_password=hash_password("senha123"),  # Senha temporária
                is_active=True,
                role_id=user_role.id,
            )
            db.add(perito)
            peritos_criados += 1

    db.commit()
    print(f"✅ {peritos_criados} peritos reais criados")


def seed_kanbans_para_peritos(db: Session):
    """Create kanban boards for each perito"""
    peritos = db.query(User).filter(User.role_id == db.query(Role).filter(Role.name == "user").first().id).all()

    kanbans_criados = 0
    for perito in peritos:
        if not db.query(Kanban).filter(Kanban.perito_id == perito.id).first():
            kanban = Kanban(
                perito_id=perito.id,
                nome="Meu Kanban",
                descricao=f"Quadro de trabalho de {perito.full_name}"
            )
            db.add(kanban)
            db.flush()  # Para obter o ID

            # Criar colunas padrão
            for nome, posicao, cor in KANBAN_COLUNAS_PADRAO:
                coluna = KanbanColuna(
                    kanban_id=kanban.id,
                    nome=nome,
                    posicao=posicao,
                    cor=cor
                )
                db.add(coluna)

            kanbans_criados += 1

    db.commit()
    print(f"✅ Kanbans criados para {kanbans_criados} peritos")


def seed_initial_tools(db: Session):
    tools = [
        Tool(
            name="analise-completa",
            title="Análise Completa",
            description="Consolidação de Qwen 3.6 + Mídia + Processos",
            url="/analise-completa.html",
            icon="🎯",
            component="AnalisaCompletaPage",
            access_level="user",
            version="6.0",
        ),
        Tool(
            name="analise-ia",
            title="Análise IA",
            description="Ollama + Qwen 3.6",
            url="/api/analise/ia",
            icon="🤖",
            component="AnalisaIAPage",
            access_level="user",
            version="6.0",
        ),
        Tool(
            name="captura-intimacoes",
            title="Captura de Intimações",
            description="Automático via Email + ESAJ",
            url="/api/intimacoes/capturar",
            icon="📧",
            component="CapturacaoIntimacoes",
            access_level="user",
            version="6.0",
        ),
    ]

    for tool in tools:
        if not db.query(Tool).filter(Tool.name == tool.name).first():
            db.add(tool)
    db.commit()
    print("✅ Initial tools seeded")


PARAMETROS_PADRAO = [
    # (chave, valor, categoria, descricao, secreto, tipo)
    # --- Credenciais de tribunais (agente Mac consome em tempo real) ---
    ("esaj_tjms_cpf", "00022358110", "credenciais", "CPF de login no ESAJ TJMS", False, "texto"),
    ("esaj_tjms_senha", "", "credenciais", "Senha do ESAJ TJMS", True, "senha"),
    ("eproc_tjms_login", "", "credenciais", "Login do eproc TJMS (migração em andamento)", False, "texto"),
    ("eproc_tjms_senha", "", "credenciais", "Senha do eproc TJMS", True, "senha"),
    ("pje_tjmt_login", "", "credenciais", "Login do PJe TJMT", False, "texto"),
    ("pje_tjmt_senha", "", "credenciais", "Senha do PJe TJMT", True, "senha"),
    # --- URLs dos sistemas ---
    ("url_esaj_tjms", "https://esaj.tjms.jus.br", "urls", "Site do ESAJ TJMS", False, "url"),
    ("url_eproc_tjms", "https://eproc1g.tjms.jus.br", "urls", "Site do eproc TJMS 1º grau", False, "url"),
    ("url_eproc_tjms_2g", "https://eproc2g.tjms.jus.br", "urls", "Site do eproc TJMS 2º grau", False, "url"),
    ("url_pje_tjmt", "https://pje.tjmt.jus.br", "urls", "Site do PJe TJMT", False, "url"),
    ("url_datajud", "https://api-publica.datajud.cnj.jus.br", "urls", "API pública DataJud (CNJ)", False, "url"),
    ("url_nfse", "https://nfse.campogrande.ms.gov.br", "urls", "Emissão de Nota Fiscal de Serviço", False, "url"),
    # --- Caminhos (aceitam formato Windows; ver mapa_unidades_windows) ---
    ("dir_modelos", "I:\\MODELOS\\DNA", "caminhos", "Diretório padrão dos modelos de documentos", False, "caminho"),
    ("dir_destino", "U:\\CPG\\SCPG", "caminhos", "Diretório de destino dos documentos gerados", False, "caminho"),
    ("dir_laudos", "I:\\LAUDOS", "caminhos", "Diretório de integração dos laudos", False, "caminho"),
    ("dir_pagamentos_coletadores", "U:\\CPG\\Pagamentos de Conveniados", "caminhos", "Planilhas de pagamento dos coletadores", False, "caminho"),
    ("dir_intimacoes_baixadas", "/Users/ipc_server/Library/CloudStorage/OneDrive-BibliotecasCompartilhadas-IPCMSPERICIASLTDA/IPCMS - GERENCIA/DIRETORIA/Testes IA/ESAJBrunoFigueiredo/intimacoes_baixadas", "caminhos", "Onde os autos baixados do ESAJ ficam (Mac/OneDrive)", False, "caminho"),
    # --- Valores de honorários (tabela do sistema antigo) ---
    ("valor_judicial", "30.00", "valores", "Valor Judicial (R$)", False, "valor"),
    ("valor_particular", "50.00", "valores", "Valor Particular (R$)", False, "valor"),
    ("valor_mp", "30.00", "valores", "Valor MP (R$)", False, "valor"),
    ("valor_dp", "30.00", "valores", "Valor DP (R$)", False, "valor"),
    ("valor_ct", "30.00", "valores", "Valor CT (R$)", False, "valor"),
    # --- Sistema ---
    ("mapa_unidades_windows", '{"I:": "", "U:": ""}', "sistema",
     'Mapeia unidades Windows para caminhos reais. Ex: {"I:": "/Users/ipc_server/Library/CloudStorage/OneDrive-.../MODELOS"}', False, "texto"),
]


def seed_parametros(db: Session):
    from app.models.parametro import Parametro
    criados = 0
    for chave, valor, categoria, descricao, secreto, tipo in PARAMETROS_PADRAO:
        if not db.query(Parametro).filter(Parametro.chave == chave).first():
            db.add(Parametro(
                chave=chave, valor=valor, categoria=categoria,
                descricao=descricao, secreto=secreto, tipo=tipo,
            ))
            criados += 1
    db.commit()
    if criados:
        print(f"✅ {criados} parâmetros padrão criados")


EMPRESAS_REAIS = [
    ("IPC MS PERICIAS LTDA", "IPC MS Perícias", "00.920.892/0001-49", "Lucro Presumido", ""),
    ("IPC MS PESQUISA LTDA", "IPC MS Pesquisa", "14.424.142/0001-90", "Simples Nacional", "Inter (conta Pesquisa)"),
]

# Áreas/especialidades periciais do IPC MS
ESPECIALIDADES = [
    "Perícia Contábil", "Perícia Grafotécnica", "Genética Forense (DNA)",
    "Perícia de Engenharia", "Perícia Médica", "Perícia Ambiental",
    "Perícia Psicológica", "Perícia Documentoscópica",
]


def seed_empresas(db: Session):
    from app.models import Empresa
    criadas = 0
    for razao, fantasia, cnpj, regime, banco in EMPRESAS_REAIS:
        if not db.query(Empresa).filter(Empresa.cnpj == cnpj).first():
            db.add(Empresa(razao_social=razao, nome_fantasia=fantasia, cnpj=cnpj,
                           regime_tributario=regime, banco=banco))
            criadas += 1
    db.commit()
    if criadas:
        print(f"✅ {criadas} empresas criadas")


def seed_especialidades(db: Session):
    from app.models.parametro import Parametro
    p = db.query(Parametro).filter(Parametro.chave == "especialidades").first()
    if not p:
        import json
        db.add(Parametro(
            chave="especialidades", valor=json.dumps(ESPECIALIDADES, ensure_ascii=False),
            categoria="sistema", descricao="Áreas periciais do IPC MS (JSON)", tipo="texto",
        ))
        db.commit()
        print("✅ Especialidades/áreas criadas")


def seed_coletadores(db: Session):
    """Importa os coletadores do CSV (login_coletadores.csv → data_coletadores.csv).
    Login por CPF, senha padrão 123456, primeiro acesso obrigatório."""
    import csv
    import os
    import re
    from app.models import Coletador, Empresa

    caminho = os.path.join(os.path.dirname(__file__), "data_coletadores.csv")
    if not os.path.exists(caminho):
        print("⚠️  data_coletadores.csv não encontrado — coletadores não importados")
        return

    # Todos os coletadores são da IPC MS Pesquisa
    pesquisa = db.query(Empresa).filter(Empresa.cnpj == "14.424.142/0001-90").first()
    empresa_id = pesquisa.id if pesquisa else None
    senha_padrao = hash_password("123456")

    # Mapa nome→código SCPG real (do Locais_Coleta.xls). Usado para nomear o
    # comprovante como CODIGO.ANO.MES.pdf. Casa por nome normalizado.
    import json as _json
    import unicodedata as _ud
    def _norm(s):
        s = _ud.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9 ]", " ", s.lower()).strip()
    scpg = {}
    scpg_path = os.path.join(os.path.dirname(__file__), "scpg_codigos.json")
    if os.path.exists(scpg_path):
        for _k, _v in _json.load(open(scpg_path, encoding="utf-8")).items():
            scpg[_k] = _v["codigo"]
    criados = 0
    with open(caminho, encoding="utf-8-sig") as f:
        for linha in csv.DictReader(f):
            cpf = re.sub(r"\D", "", linha.get("CPF", ""))
            nome = (linha.get("Nome Completo") or "").strip()
            apelido = (linha.get("Apelido") or "").strip()
            # Código SCPG real (do Locais_Coleta.xls), casado por nome normalizado.
            codigo = scpg.get(_norm(nome))
            if len(cpf) != 11 or not nome:
                continue
            if db.query(Coletador).filter(Coletador.cpf == cpf).first():
                continue
            db.add(Coletador(
                codigo_scpg=codigo, cpf=cpf, nome_completo=nome, apelido=apelido or None,
                hashed_password=senha_padrao, ativo=True, primeiro_acesso=True,
                empresa_id=empresa_id,
            ))
            criados += 1
    db.commit()
    if criados:
        print(f"✅ {criados} coletadores importados")


# Funcionários por área — só primeiro nome (sobrenomes eram inventados; Bruno 06/07).
FUNCIONARIOS_AREAS = [
    ("Leticia", "leticia@ipcms.com.br", "Contábil", "especialista"),
    ("Allan", "allan@ipcms.com.br", "Contábil", "coordenador"),
    ("Ana Paula", "ana@ipcms.com.br", "DNA", "especialista"),
    ("Melissa", "melissa@ipcms.com.br", "DNA", "especialista"),
    ("Miriam", "miriam@ipcms.com.br", "DNA", "coordenador"),
    ("Cezar", "cezar@ipcms.com.br", "Engenharia", "especialista"),
    ("Joyce", "joyce@ipcms.com.br", "Engenharia", "coordenador"),
    ("Alberto", "alberto@ipcms.com.br", "Grafotécnica", "coordenador"),
]


def seed_funcionarios_areas(db: Session):
    """Insere/atualiza funcionários com sua área. Coordenador→power_user, especialista→user."""
    pu = db.query(Role).filter(Role.name == "power_user").first()
    us = db.query(Role).filter(Role.name == "user").first()
    senha = hash_password("ipcms123")
    n = 0
    for nome, email, area, nivel in FUNCIONARIOS_AREAS:
        role = pu if nivel == "coordenador" else us
        u = db.query(User).filter(User.email == email).first()
        if u:
            u.area = area; u.nivel = nivel
        else:
            db.add(User(email=email, full_name=nome, hashed_password=senha,
                        is_active=True, role_id=role.id, area=area, nivel=nivel))
            n += 1
    db.commit()
    if n:
        print(f"✅ {n} funcionários (áreas) criados")


def seed_database():
    """Seed idempotente: verifica se admin já existe antes de executar."""
    db = SessionLocal()
    try:
        # Verificar se seed já foi executado (admin já existe)
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@ipcms.com.br")
        admin_existe = db.query(User).filter(User.email == admin_email).first()

        if admin_existe:
            print(f"✅ Seed skipped: {admin_email} já existe")
            return

        # Validar conexão com BD antes de começar
        try:
            db.execute(text("SELECT 1"))
        except Exception as e:
            print(f"❌ ERRO: Seed failed - BD connection error: {e}")
            sys.exit(1)

        # Executar seed completo
        print("🔄 Iniciando seed...")
        seed_roles(db)
        seed_permissions(db)
        seed_admin_user(db)
        # seed_peritos_reais(db)  # DESATIVADO: eram nomes fake (Bruno confirmou 06/07)
        seed_funcionarios_areas(db)
        seed_kanbans_para_peritos(db)
        seed_initial_tools(db)
        seed_parametros(db)
        seed_empresas(db)
        seed_especialidades(db)
        seed_coletadores(db)

        # Validar que dados críticos foram criados
        roles = db.query(Role).count()
        users = db.query(User).count()
        if roles == 0 or users == 0:
            print("❌ ERRO: Seed failed - dados críticos não criados")
            import sys
            sys.exit(1)

        print(f"✅ Database seeded successfully ({roles} roles, {users} users)")
    except Exception as e:
        print(f"❌ ERRO: Seed failed - {e}")
        import sys
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
