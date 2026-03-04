# app/services/estoque_service.py

import logging
from datetime import datetime
from sqlalchemy import func
from app.models_sqla import db, Peca

# ====================================================================
# [BLOCO] CONFIG_LOGGER
# [NOME] logger
# [RESPONSABILIDADE] Inicializar logger do módulo para rastreamento do serviço de estoque
# ====================================================================
logger = logging.getLogger(__name__)
# ====================================================================
# [FIM BLOCO] logger
# ====================================================================


# ====================================================================
# [BLOCO] BLOCO_DB
# [NOME] update_stock_after_finish
# [RESPONSABILIDADE] Atualizar estoque de conjunto incrementando estoque_atual da peça correspondente ao model_code
# ====================================================================
def update_stock_after_finish(model_code: str):
    """
    Incrementa o estoque_atual da peça (tipo='conjunto')
    correspondente ao model_code informado.
    """
    if not model_code:
        logger.warning("[Estoque] update_stock chamado sem model_code.")
        return

    try:
        # Busca a peca ignorando maiusculas/minusculas no codigo e garantindo tipo conjunto
        peca = (
            db.session.query(Peca)
            .filter(
                func.lower(Peca.tipo) == "conjunto",
                func.lower(Peca.codigo_pneumark) == model_code.lower(),
            )
            .first()
        )

        if not peca:
            # Apenas loga o erro, nao quebra a aplicacao (para nao travar o scanner)
            logger.error(
                f"[Estoque] Peca tipo 'conjunto' nao encontrada para modelo: {model_code}"
            )
            # Se quiser que o scanner avise erro, descomente a linha abaixo:
            # raise ValueError(f"Peca nao encontrada: {model_code}")
            return

        # Incrementa
        peca.estoque_atual = (peca.estoque_atual or 0) + 1
        peca.updated_at = datetime.utcnow()

        db.session.add(peca)
        db.session.commit()

        logger.info(
            f"[Estoque] Sucesso: Modelo {model_code} incrementado. Novo total: {peca.estoque_atual}"
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"[Estoque] Erro ao atualizar estoque para {model_code}: {str(e)}")
        raise e


# ====================================================================
# [FIM BLOCO] update_stock_after_finish
# ====================================================================

# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# CONFIG_LOGGER: logger
# BLOCO_DB: update_stock_after_finish
# ====================================================================
