 
from flask import Blueprint

utilidades_bp = Blueprint("utilidades_bp", __name__, url_prefix="/api")
from .rotas import *  # noqa
