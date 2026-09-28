from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler

db = SQLAlchemy()
mail = Mail()
scheduler = BackgroundScheduler(daemon=True)
