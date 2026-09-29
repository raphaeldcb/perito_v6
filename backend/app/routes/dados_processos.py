from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/dados", tags=["dados"])

COMARCAS = [
    {"id": "cg", "nome": "Campo Grande"},
    {"id": "cp", "nome": "Corumbá"},
    {"id": "tr", "nome": "Três Lagoas"},
    {"id": "db", "nome": "Dourados"},
]

VARAS = {
    "cg": [
        {"id": 1, "nome": "1ª Vara Cível"},
        {"id": 2, "nome": "2ª Vara Cível"},
        {"id": 3, "nome": "Vara de Família"},
        {"id": 4, "nome": "Vara Trabalhista"},
        {"id": 5, "nome": "Vara Criminal"},
    ],
    "cp": [
        {"id": 6, "nome": "1ª Vara Cível"},
        {"id": 7, "nome": "Vara Criminal"},
    ],
    "tr": [
        {"id": 8, "nome": "1ª Vara Cível"},
        {"id": 9, "nome": "Vara Trabalhista"},
    ],
    "db": [
        {"id": 10, "nome": "1ª Vara Cível"},
        {"id": 11, "nome": "2ª Vara Cível"},
    ]
}

JUIZES = {
    1: [
        {"id": 1, "nome": "Juiz Carlos Silva"},
        {"id": 2, "nome": "Juiz Maria Santos"},
    ],
    2: [
        {"id": 3, "nome": "Juiz João Oliveira"},
    ],
    3: [
        {"id": 4, "nome": "Juiza Ana Costa"},
    ],
    4: [
        {"id": 5, "nome": "Juiz Roberto Lima"},
    ],
    5: [
        {"id": 6, "nome": "Juiz Pedro Alves"},
    ],
}

TIPOS_DOCUMENTO = [
    {"id": "oficio", "label": "Ofício"},
    {"id": "laudo", "label": "Laudo"},
    {"id": "parecer", "label": "Parecer"},
    {"id": "relatorio", "label": "Relatório"},
    {"id": "carta", "label": "Carta"},
]

TIPOS_PERICIA = [
    {"id": "Judicial", "label": "Judicial"},
    {"id": "Extrajudicial", "label": "Extrajudicial"},
    {"id": "AT", "label": "Assistência Técnica"},
]


@router.get("/comarcas")
async def listar_comarcas():
    return {"comarcas": COMARCAS}


@router.get("/varas/{comarca_id}")
async def listar_varas(comarca_id: str):
    varas = VARAS.get(comarca_id, [])
    return {"varas": varas}


@router.get("/juizes/{vara_id}")
async def listar_juizes(vara_id: int):
    juizes = JUIZES.get(vara_id, [])
    return {"juizes": juizes}


@router.get("/tipos-documento")
async def listar_tipos_documento():
    return {"tipos": TIPOS_DOCUMENTO}


@router.get("/tipos-pericia")
async def listar_tipos_pericia():
    return {"tipos": TIPOS_PERICIA}


@router.get("/empresas")
async def listar_empresas():
    return {
        "empresas": [
            {"id": 1, "nome": "Empresa 1"},
            {"id": 2, "nome": "Empresa 2"},
        ]
    }


@router.post("/populate-dna")
async def populate_dna_from_partes() -> dict:
    """Popula participantes_dna a partir de partes."""
    from app.services.database import get_db
    from app.models.processo import Processo

    db = next(get_db())

    try:
        processos = db.query(Processo).all()
        count = 0

        for p in processos:
            if not p.partes or not isinstance(p.partes, list):
                continue

            if p.participantes_dna and p.participantes_dna != []:
                continue

            dna = []
            for parte in p.partes:
                if isinstance(parte, dict):
                    dna.append({
                        "tipo": parte.get("papel", "desconhecido"),
                        "nome_real": parte.get("nome", ""),
                        "nome_doc": parte.get("nome", "")
                    })

            if dna:
                p.participantes_dna = dna
                count += 1

        db.commit()

        return {
            "status": "sucesso",
            "processos_atualizados": count,
        }
    except Exception as e:
        db.rollback()
        return {"status": "erro", "message": str(e)}
    finally:
        db.close()
