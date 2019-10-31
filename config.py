import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'm3p%x1134_j7zyjlf#9#c7fgb4jnt1)b2=)05!h*4+eh06wdw6'
    UPLOAD_FOLDER = '/home/jack/img'