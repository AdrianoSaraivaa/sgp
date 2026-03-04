# app/routes/utilidades.py
from flask import Blueprint, jsonify, render_template
from random import choice

# ====================================================================
# [BLOCO] BLOCO_CONFIG
# [NOME] utilidades_bp
# [RESPONSABILIDADE] Registro do Blueprint de rotas utilitárias
# ====================================================================
utilidades_bp = Blueprint("utilidades_bp", __name__)
# ====================================================================
# [FIM BLOCO] utilidades_bp
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] frase_motivacional
# [RESPONSABILIDADE] Retornar uma frase motivacional aleatória em JSON
# ====================================================================
@utilidades_bp.route("/api/frase-motivacional", methods=["GET"])
def frase_motivacional():
    frases = [
        {"texto": "Qualidade é fazer o simples, bem feito.", "autor": "Desconhecido"},
        {
            "texto": "Sem dado, você é só mais uma pessoa com opinião.",
            "autor": "W. Edwards Deming",
        },
        {"texto": "O feito é melhor que o perfeito.", "autor": "Sheryl Sandberg"},
        {
            "texto": "Pequenas melhorias diárias geram grandes resultados.",
            "autor": "Kaizen",
        },
        {"texto": "Disciplina supera motivação.", "autor": "Desconhecido"},
        {"texto": "Quem mede, melhora.", "autor": "Gestão"},
        {"texto": "Foco no processo, resultado vem.", "autor": "Desconhecido"},
        {"texto": "Consistência vence talento.", "autor": "Desconhecido"},
        {"texto": "Resolva o problema, não aponte culpados.", "autor": "Gestão Lean"},
        {"texto": "Simplifique. Sempre.", "autor": "Desconhecido"},
        {"texto": "Sem padrão não há melhoria.", "autor": "Lean"},
        {"texto": "Excelência é hábito.", "autor": "Aristóteles"},
        {"texto": "Comece antes de estar pronto.", "autor": "Desconhecido"},
        {"texto": "Quem executa, cresce.", "autor": "Desconhecido"},
        {"texto": "Planejar é economizar energia.", "autor": "Desconhecido"},
        {"texto": "Progresso, não perfeição.", "autor": "Desconhecido"},
        {"texto": "Feito com propósito é melhor.", "autor": "Desconhecido"},
        {"texto": "Sem ação não há mudança.", "autor": "Desconhecido"},
        {"texto": "Velocidade com direção.", "autor": "Desconhecido"},
        {"texto": "Erre rápido, corrija rápido.", "autor": "Startup"},
        {"texto": "Cada detalhe importa.", "autor": "Desconhecido"},
        {"texto": "Compromisso gera confiança.", "autor": "Desconhecido"},
        {"texto": "Organização é produtividade.", "autor": "Desconhecido"},
        {"texto": "Resultado é consequência.", "autor": "Desconhecido"},
        {"texto": "Melhore 1% ao dia.", "autor": "Kaizen"},
        {"texto": "Entrega gera reputação.", "autor": "Desconhecido"},
        {"texto": "Constância constrói legado.", "autor": "Desconhecido"},
        {"texto": "Dados trazem clareza.", "autor": "Gestão"},
        {"texto": "Menos desculpas, mais execução.", "autor": "Desconhecido"},
        {"texto": "Quem lidera serve.", "autor": "Liderança"},
        {"texto": "Ação vence medo.", "autor": "Desconhecido"},
        {"texto": "A melhoria começa na decisão.", "autor": "Desconhecido"},
        {"texto": "Faça hoje melhor que ontem.", "autor": "Desconhecido"},
        {"texto": "Persistência cria resultado.", "autor": "Desconhecido"},
        {"texto": "Clareza gera foco.", "autor": "Desconhecido"},
        {"texto": "Treine até virar padrão.", "autor": "Desconhecido"},
        {"texto": "Eficiência é respeito ao tempo.", "autor": "Desconhecido"},
        {"texto": "Entrega consistente é diferencial.", "autor": "Desconhecido"},
        {"texto": "Sem padrão não há escala.", "autor": "Gestão"},
        {"texto": "Processo forte, equipe forte.", "autor": "Desconhecido"},
        {"texto": "Crescimento exige desconforto.", "autor": "Desconhecido"},
        {"texto": "Responsabilidade gera poder.", "autor": "Desconhecido"},
        {"texto": "Decisão rápida, ajuste constante.", "autor": "Desconhecido"},
        {"texto": "Faça com excelência ou não faça.", "autor": "Desconhecido"},
        {"texto": "Aprender é evoluir.", "autor": "Desconhecido"},
        {"texto": "Quem planeja, domina o caos.", "autor": "Desconhecido"},
        {"texto": "Organize, execute, melhore.", "autor": "Desconhecido"},
        {"texto": "Produtividade é foco aplicado.", "autor": "Desconhecido"},
        {"texto": "Menos ruído, mais resultado.", "autor": "Desconhecido"},
        {"texto": "Clareza reduz retrabalho.", "autor": "Desconhecido"},
        {"texto": "Liderança é exemplo diário.", "autor": "Desconhecido"},
        {"texto": "Controle gera previsibilidade.", "autor": "Gestão"},
        {"texto": "Padronize para crescer.", "autor": "Lean"},
        {"texto": "Excelência é decisão diária.", "autor": "Desconhecido"},
        {"texto": "Sem execução não há estratégia.", "autor": "Desconhecido"},
    ]
    return jsonify(choice(frases))


# ====================================================================
# [FIM BLOCO] frase_motivacional
# ====================================================================


# ====================================================================
# [BLOCO] FUNÇÃO
# [NOME] demo_base
# [RESPONSABILIDADE] Renderizar página de demonstração que estende o _base.html
# ====================================================================
# Página de demonstração que estende o _base.html
@utilidades_bp.route("/demo/base", methods=["GET"])
def demo_base():
    return render_template("demo_base.html")


# ====================================================================
# [FIM BLOCO] demo_base
# ====================================================================


# ====================================================================
# MAPA DO ARQUIVO
# --------------------------------------------------------------------
# BLOCO_CONFIG: utilidades_bp
# FUNÇÃO: frase_motivacional
# FUNÇÃO: demo_base
# ====================================================================
