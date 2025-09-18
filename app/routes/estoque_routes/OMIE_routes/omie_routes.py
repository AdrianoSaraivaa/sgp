# app/routes/estoque_routes/OMIE_routes/omie_routes.py
from __future__ import annotations

import logging
from flask import Blueprint, render_template

# Logger simples para este módulo
logger = logging.getLogger(__name__)

# Blueprint do OMIE no módulo de estoque
estoque_omie_bp = Blueprint(
    "estoque_omie_bp",
    __name__,
    url_prefix="/estoque/omie",
)

@estoque_omie_bp.route("/", methods=["GET"])
def home_omie():
    """
    Página inicial da área de integração OMIE no módulo de estoque.
    Renderiza: app/templates/estoque_templates/OMIE_templates/home_omie.html
    """
    logger.info("[OMIE] Renderizando home_omie")
    return render_template("estoque_templates/OMIE_templates/home_omie.html")
