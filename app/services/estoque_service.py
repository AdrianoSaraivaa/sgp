# app/services/estoque_service.py

from app.models_sqla import db, Peca
from sqlalchemy import func
from datetime import datetime


def update_stock_after_finish(model_code: str):
    if not model_code:
        return

    peca = (
        db.session.query(Peca)
        .filter(func.lower(Peca.tipo) == "conjunto", Peca.codigo_pneumark == model_code)
        .first()
    )

    if not peca:
        raise ValueError(
            f"Peca tipo 'conjunto' não encontrada para modelo: {model_code}"
        )

    peca.estoque_atual += 1
    peca.updated_at = datetime.utcnow()
