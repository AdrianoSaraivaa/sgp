# app/routes/producao_routes/rastreabilidade_nserie_routes/__init__.py

from .rastreabilidade_routes import gp_rastreabilidade_bp

def init_app(app):
    """Registra o blueprint de Rastreabilidade no app."""
    app.register_blueprint(gp_rastreabilidade_bp)

# Deixa explícito o que o pacote expõe
__all__ = ["gp_rastreabilidade_bp", "init_app"]
