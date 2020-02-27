import os
basedir = os.path.abspath(os.path.dirname(__file__))

#  configuration settings for database (used in init)
class Config(object):
    POSTS_PER_PAGE = 10
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    # SQLALCHEMY_DATABASE_URI = '***REMOVED***'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    os.environ['MAIL_SERVER'] = 'smtp.googlemail.com'
    os.environ['MAIL_PORT'] = '587'
    os.environ['MAIL_USE_TLS'] = '1'
    os.environ['MAIL_USERNAME'] = 'devgilad@gmail.com'
    os.environ['MAIL_PASSWORD'] = current_app.config.get('MAIL_PASSWORD')
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['giladspitzer@gmail.com']


