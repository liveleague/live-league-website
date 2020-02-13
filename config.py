import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'i#2yjd!7wbu000jsx-(2%$qvxkgbwa9g-woygexfady!vrxs&i'
    UPLOAD_FOLDER = '/home/jack/img'