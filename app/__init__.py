from flask import Flask, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from configurator import Config
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from datetime import datetime



app = Flask(__name__)  # instantiates a raw Flask object
app.config.from_object(Config)  # configures it according to preferences in configurator.py
db = SQLAlchemy(app)  # creates a database instance from the SQLAlchemy library
migrate = Migrate(app, db)  # creates migration instance so that you can alter between versions of db
login = LoginManager(app)  # creates status var for state of login
login.login_view = 'login'  # page for login page (similar to url_for())
mail = Mail(app)
bootstrap = Bootstrap(app)

general_url = 'http://127.0.0.1:5000/'

from app import routes, models, errors
import logging
from logging.handlers import SMTPHandler
from logging.handlers import RotatingFileHandler
import os

if not app.debug:
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr='no-reply@' + app.config['MAIL_SERVER'],
            toaddrs=app.config['ADMINS'], subject='Schoology Linked Program Failure',
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/schoologylinked.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    """
    To make the logging more useful, I'm also lowering the logging level to the INFO category, both in the 
    application logger and the file logger handler. In case you are not familiar with the logging categories, they are 
    DEBUG, INFO, WARNING, ERROR and CRITICAL in increasing order of severity.
    """
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('SchoologyLinked startup')

def url_for_self(**args):
    url = url_for(request.endpoint, **dict(request.view_args, **args)).split('/')
    if url[-1] == 'post' or url[-1] == 'commit':
        url_new = ''
        for x in url[:-1]:
            url_new +=  x + '/'
        return general_url + url_new.strip('/')
    else:
        url_new = ''
        for x in url[1:]:
            url_new += x + '/'
        return general_url + url_new.strip('/')

def time(inputed):
    if inputed.date() == datetime.today().date():
        return 'Today at ' + str(inputed.strftime("%H:%M:%S"))
    else:
        return str(inputed.strftime("%d/%m/%Y at %H:%M"))

def convert_time(minutes):
    hours = minutes // 60
    minutes = minutes % 60
    return str(hours) + ':' + str(minutes)

def colorify(commit):
    commits = models.Assignment.query.filter_by(id=commit.assignment_id).first().commits
    times = [x.time_spent for x in commits]
    avg = sum(times) / len(times)
    leeway = avg * 0.01
    if commit.time_spent + leeway == avg or commit.time_spent - leeway == avg or commit.time_spent == avg:
        return '#F9DF4A'
    elif commit.time_spent + leeway > avg or commit.time_spent - leeway > avg:
        return '#32FF2D'
    elif commit.time_spent + leeway < avg or commit.time_spent - leeway < avg:
        return '#F90E2D'


app.jinja_env.globals['url_for_self'] = url_for_self
app.jinja_env.globals['time'] = time
app.jinja_env.globals['convert_time'] = convert_time
app.static_folder = 'static'
app.jinja_env.globals['now'] = datetime.utcnow
app.jinja_env.globals['colorify'] = colorify
app.config['UPLOADS'] = '/Users/giladspitzer1/Desktop/SENIOR/FLASK/CAPSTONE/app/static/uploads'
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
