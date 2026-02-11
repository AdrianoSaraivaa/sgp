
# app/routes/estoque_routes/listar_pecas.py
from flask import Blueprint, render_template, request
from sqlalchemy import or_, case, func
# Import from the SQLAlchemy models package.  The ``Peca`` class
# defined in ``app.models_sqla`` exposes the ``.query`` API that
# SQLAlchemy constructs rely on.
from app.models_sqla import Peca

listar_pecas_bp = Blueprint('listar_pecas_bp', __name__)

@listar_pecas_bp.route('/listar_pecas')
def listar_pecas():
    busca = (request.args.get('busca') or '').strip().lower()

    q = Peca.query
    if busca:
        like = f"%{busca}%"
        q = q.filter(
            or_(
                func.lower(Peca.codigo_pneumark).like(like),
                func.lower(Peca.descricao).like(like),
            )
        )

    # conjuntos no topo, depois descrição A→Z
    ordem_conjunto = case((Peca.tipo == 'conjunto', 0), else_=1)
    pecas = q.order_by(ordem_conjunto.asc(), Peca.descricao.asc()).all()

    return render_template('estoque_templates/listar_peca.html',
                           pecas=pecas,
                           busca=request.args.get('busca', ''))
