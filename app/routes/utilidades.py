# app/routes/utilidades.py
from flask import Blueprint, jsonify, render_template
from random import choice

utilidades_bp = Blueprint("utilidades_bp", __name__)

@utilidades_bp.route("/api/frase-motivacional", methods=["GET"])
def frase_motivacional():
    frases = [
        {"texto": "Qualidade é fazer o simples, bem feito.", "autor": "Desconhecido"},
        {"texto": "Sem dado, você é só mais uma pessoa com opinião.", "autor": "W. Edwards Deming"},
        {"texto": "O feito é melhor que o perfeito.", "autor": "Sheryl Sandberg"},
        {"texto": "Pequenas melhorias diárias geram grandes resultados.", "autor": "Kaizen"},
    ]
    return jsonify(choice(frases))

# Página de demonstração que estende o _base.html
@utilidades_bp.route("/demo/base", methods=["GET"])
def demo_base():
    return render_template("demo_base.html")
