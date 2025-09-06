from flask import Blueprint

budgets = Blueprint('budgets', __name__)

from app.budgets import routes