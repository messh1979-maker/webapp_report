from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "برای دسترسی به این صفحه ابتدا وارد شوید."
login_manager.login_message_category = "warning"
