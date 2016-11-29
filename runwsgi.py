# flask /wsgi
from gevent.wsgi import WSGIServer
from flask import Flask

# logging
import logging
import logging.handlers
import os
import sys

# blueprints
from web.login import bp_login
from web.keyapi import bp_keyapi
from web.planitapi import bp_planitapi
from web.root import bp_root

# data layer
from web.data import planitdb

logfile = os.path.splitext(sys.argv[0])[0] + ".log"

logging.basicConfig(
    level = logging.DEBUG,
    handlers = (
        logging.StreamHandler(stream=sys.stdout),
              logging.handlers.RotatingFileHandler(
                logfile,
                maxBytes = 256*1024,
                backupCount = 6)),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask('main')
app.config.update({
    'MONGO_HOST': 'eg-mongodb',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'planit',
    'MONGO_USERNAME': 'webservice',
    'MONGO_PASSWORD': 'F7ZGLY86xjby',
})
# key for session
app.config['SECRET_KEY'] = "not a very secret key."

planitdb.init_db(app)

app.register_blueprint(bp_login, url_prefix='/planit/user')
app.register_blueprint(bp_keyapi, url_prefix='/planit/keys')
app.register_blueprint(bp_planitapi, url_prefix='/planit')
app.register_blueprint(bp_root, url_prefix='/planit')

http_server = WSGIServer(('', 4002), app)
http_server.serve_forever()
