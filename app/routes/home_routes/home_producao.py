# app/routes/home_routes/home_producao.py
from flask import Blueprint, render_template, url_for, redirect

home_producao_bp = Blueprint(
    "home_producao_bp",
    __name__,
    url_prefix="/producao"
)

@home_producao_bp.route("/", methods=["GET"])
def home_producao():
    cards = [
        {
            "title": "Montar Máquina",
            "desc": "Baixar estrutura completa do modelo.",
            "icon": "fa-cogs",
            "endpoint": url_for("maquinas_bp.pagina_montagem"),
            "badge": "Ativo",
        },
        {
            "title": "Gerenciar Produção",
            "desc": "Configurar bancadas, tempos e checklists por modelo.",
            "icon": "fa-clipboard-check",
            "endpoint": "/producao/gp/setup",
        },
        {
            "title": "Painel Visual",
            "desc": "Status em tempo real da produção.",
            "icon": "fa-chart-line",
            "endpoint": "/producao/gp/painel/",  # vai direto pro painel
        },
        {
            "title": "Indicadores",
            "desc": "KPIs e metas do setor.",
            "icon": "fa-gauge-high",
            "endpoint": url_for("home_producao_bp.placeholder", slug="indicadores"),
        },
        {
            "title": "Rastreabilidade das Máquinas",
            "desc": "Consultar histórico completo de produção.",
            "icon": "fa-history",
            "endpoint": url_for("gp_rastreabilidade_bp.rastreabilidade_senha"),
        },
        {
            "title": "Relatórios",
            "desc": "Consolidados por período e modelo.",
            "icon": "fa-file-alt",
            "endpoint": url_for("home_producao_bp.placeholder", slug="relatorios"),
        },
    ]

    try:
        breadcrumb_url = url_for("modulos_bp.tela_modulos")
    except Exception:
        breadcrumb_url = "/"

    return render_template(
        "home_templates/home_producao.html",
        cards=cards,
        breadcrumb_url=breadcrumb_url
    )

@home_producao_bp.route("/placeholder/<slug>", methods=["GET"])
def placeholder(slug):
    mapping = {
        "montar-maquina": ("maquinas_bp.pagina_montagem", {}),
        "painel-visual": (None, {"redirect": "/producao/gp/painel/"}),  # segurança extra
    }

    if slug in mapping:
        endpoint, params = mapping[slug]
        if endpoint:
            return redirect(url_for(endpoint, **params), code=302)
        if "redirect" in params:
            return redirect(params["redirect"], code=302)

    return render_template(
        "home_templates/home_producao.html",
        cards=[],
        placeholder=f'Recurso "{slug}" ainda não disponível.'
    )
