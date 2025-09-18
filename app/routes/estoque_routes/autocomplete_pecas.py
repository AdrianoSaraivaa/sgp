
from flask import Blueprint, jsonify, request
# Use the SQLAlchemy models instead of dataclasses. Import from the
# auto-generated models_sqla package to ensure that ``.query`` is available.
from app.models_sqla import Peca

autocomplete_bp = Blueprint('autocomplete_bp', __name__)

@autocomplete_bp.route('/api/pecas_autocomplete')
def pecas_autocomplete():
    termo = request.args.get('termo', '').lower()
    resultados = Peca.query.filter(Peca.descricao.ilike(f'%{termo}%')).limit(10).all()
    sugestoes = [{"descricao": p.descricao, "codigo": p.codigo_pneumark} for p in resultados]
    return jsonify(sugestoes)
