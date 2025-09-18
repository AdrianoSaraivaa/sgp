from flask import Blueprint, jsonify
from app import db
from .rop_service import list_rop_needs


gp_needs_api_bp = Blueprint(
    "gp_needs_api_bp",
    __name__,
    url_prefix="/producao/gp"
)

@gp_needs_api_bp.route("/needs", methods=["GET"])
def api_needs():
    """
    Retorna necessidades de montagem quando CONJUNTOS (máquinas) estão em ROP.
    Formato:
      [
        {
          "modelo": "7-000",
          "codigo": "7-000",
          "necessaria": 5,
          "estoque_atual": 10,
          "ponto_pedido": 10,
          "estoque_maximo": 15,
          "capacidade_zero": false
        }, ...
      ]
    """
    needs = list_rop_needs(db.session)
    return jsonify(needs)
