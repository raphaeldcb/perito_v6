import logging
import sys
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings
from app.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    } if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria tabelas e roda o seed. Falhas de seed são FATais se deixarem o
    sistema sem admin — subir 'saudável' sem nenhum usuário é pior que não subir."""

    print("🔍 [INIT_DB] Starting database initialization...")
    sys.stdout.flush()

    # EXPERT FIX: Import from __init__.py ensures all models are registered
    # We DO NOT import models here — let __init__.py handle it.
    # Just verify Base.metadata has tables before create_all()
    import app.models  # This triggers app/models/__init__.py which imports everything

    tables_count_before = len(Base.metadata.tables)
    print(f"🔍 [INIT_DB] Base.metadata registered {tables_count_before} tables")
    sys.stdout.flush()
    logger.info(f"📦 Base.metadata registered {tables_count_before} tables BEFORE create_all()")

    # Check if schema already has data (don't destroy it on restart)
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        is_fresh_install = len(existing_tables) == 0

        if is_fresh_install:
            logger.info("🆕 Fresh install detected — creating schema")
            with engine.begin() as conn:
                conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
            logger.info("✅ Schema dropped and recreated")
        else:
            logger.info(f"♻️ Existing database detected ({len(existing_tables)} tables) — skipping DROP SCHEMA")
    except Exception as e:
        logger.warning(f"Warn ao verificar schema: {e}")

    # Postgres pode ainda estar inicializando quando o container do backend
    # sobe (depends_on não espera readiness) — retry com backoff.
    ultimo_erro = None
    for tentativa in range(30):
        try:
            logger.info(f"🔨 create_all() attempt {tentativa + 1}/30, Base has {len(Base.metadata.tables)} tables")
            Base.metadata.create_all(bind=engine)
            logger.info(f"✅ create_all() succeeded")

            # Verify tables actually exist in database
            from sqlalchemy import text, inspect
            inspector = inspect(engine)
            existing = len(inspector.get_table_names())
            logger.info(f"✅ Database now has {existing} tables")
            break
        except Exception as e:
            ultimo_erro = e
            logger.warning(f"Banco indisponível (tentativa {tentativa + 1}/30): {e}")
            time.sleep(2)
    else:
        raise RuntimeError(f"Banco de dados inacessível após 60s: {ultimo_erro}")

    # Adiciona colunas faltantes (mitigação para create_all() incompleto)
    db = SessionLocal()
    try:
        from sqlalchemy import text

        missing_cols = [
            ("usuario", "device_id", "VARCHAR(100) UNIQUE"),
            ("usuario", "salario_mensal", "NUMERIC(10, 2)"),
            ("usuario", "honorario_mensal", "NUMERIC(10, 2)"),
            ("usuario", "area", "VARCHAR(40)"),
            ("usuario", "nivel", "VARCHAR(20)"),
            ("despesa", "ano", "SMALLINT"),
            ("despesa", "mes", "SMALLINT"),
            ("despesa", "pago", "BOOLEAN DEFAULT false"),
            ("despesa", "origem", "VARCHAR(30)"),
            ("despesa", "origem_ref", "VARCHAR(200)"),
            # Task 8 (calculo_v2): Qwen lê o PDF oficial em processo.decisao_oficial_path
            ("processo", "decisao_oficial_path", "VARCHAR(500)"),
            # Task 3/7/8 (calculo_v2): padrão semântico com tokens [MARCO] — já
            # cobertos por backend/migrations/2026_08_03_calculo_v2_tables.sql,
            # repetidos aqui como self-heal (essa migration solta não roda no
            # deploy padrão via Alembic, ver ressalva no relatório da Task 6).
            ("padrao_calculo", "regra_semantica", "TEXT"),
            ("padrao_calculo", "tokens_encontrados", "JSON"),
            ("padrao_calculo", "validacao_oficial", "BOOLEAN DEFAULT false"),
        ]

        for table, col, type_def in missing_cols:
            result = db.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}'"))
            if not result.fetchone():
                try:
                    logger.warning(f"Adicionando coluna {col} em {table}...")
                    db.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {type_def}"))
                    db.commit()
                    logger.info(f"✅ {col} adicionado")
                except Exception as e:
                    logger.warning(f"Coluna {col} pode já existir: {e}")
                    db.rollback()
    except Exception as e:
        logger.warning(f"Erro ao adicionar colunas: {e}")
    finally:
        db.close()

    try:
        from app.seed import seed_database
        logger.info("🌱 Iniciando seed de dados...")
        seed_database()
        logger.info("✅ Seed completado")
    except SystemExit as e:
        logger.info(f"Seed exited with code {e.code}")
    except Exception as e:
        logger.error(f"❌ SEED ERROR: {e}")
        # Não falha — deixa sistema rodar, seed manual depois se needed

    # Invariante mínima: o sistema precisa ter pelo menos um admin ativo.
    from app.models import User, Role
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        tem_admin = admin_role and db.query(User).filter(
            User.role_id == admin_role.id, User.is_active == True
        ).first()
        if not tem_admin:
            logger.warning("⚠️ Nenhum admin ativo — login pode falhar")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível verificar admin: {e}")
    finally:
        db.close()


def graceful_shutdown():
    """Faz graceful shutdown da pool de conexões.
    Aguarda jobs processando e fecha pool de forma limpa."""
    logger.info("🔄 Graceful shutdown: aguardando jobs processando...")
    try:
        from app.models import Job
        db = SessionLocal()
        try:
            # Busca jobs ainda "processando"
            jobs_processando = db.query(Job).filter(
                Job.status == "processando"
            ).all()

            if jobs_processando:
                logger.info(
                    f"⚠️  {len(jobs_processando)} jobs ainda processando — "
                    f"marcando como falhou"
                )
                from datetime import datetime
                for job in jobs_processando:
                    job.status = "falhou"
                    job.erro = "Shutdown forçado: backend encerrado durante processamento"
                    job.concluido_em = datetime.utcnow()
                db.commit()
                logger.info(f"✅ {len(jobs_processando)} jobs marcados como falhou")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Erro ao processar jobs órfãos no shutdown: {e}")

    # Fecha pool
    try:
        engine.dispose()
        logger.info("✅ Pool de conexões fechada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao fechar pool: {e}")
