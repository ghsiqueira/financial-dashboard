from flask import Blueprint

notifications = Blueprint('notifications', __name__)

from app.notifications import routes