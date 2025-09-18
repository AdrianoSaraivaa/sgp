from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = 'chave-super-secreta'

    from app.routes.home_routes.login import home_routes
    app.register_blueprint(home_routes)

    return app
