"""

Run with gunicorn with multiple workers (production):
$ gunicorn -w 4 PlanItWebServices:app

Simlpy running this script runs the debug flask server.

"""

import flask
from flask import Flask, request, render_template, Response, redirect, \
    url_for, session, flash

import sys
import os
import os.path
import datetime

# blueprints
from web.login import bp_login
from web.keyapi import bp_keyapi
from web.planit import bp_planitv1
from web.planitapi import bp_planitapi
from web.cslpwan import bp_cslpwan
from web.root import bp_root
from web.thedocs import bp_docs
# from web import *
from web.data import *
from web.decorators import *

# patch for gevent cooperative tasking
from gevent.wsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

import logging
import logging.handlers
#logfile =  os.path.splitext(sys.argv[0])[0] + ".log"
logfile = 'PlanItWebServices.log'

logging.basicConfig(level=logging.DEBUG,
                handlers=(logging.StreamHandler(stream=sys.stdout),
                          logging.handlers.RotatingFileHandler(logfile,
                                                                maxBytes = 256*1024,
                                                                backupCount = 6), ),
                format='%(asctime)s - [%(process)d]- %(name)s - %(levelname)s - %(message)s')

def makeApp(preprefix = '', debug=False):
    app = Flask('main', static_url_path=preprefix+'/web/static')
    app.config.update({
        'MONGO_HOST': 'eg-mongodb',
        'MONGO_PORT': 27017,
        'MONGO_DBNAME': 'planit',
        'MONGO_USERNAME': 'webservice',
        'MONGO_PASSWORD': 'F7ZGLY86xjby',
    })
    # key for session
    app.config['SECRET_KEY'] = "not a very secret key."
    app.config['DEBUG'] = debug
    #app.config['EXPLAIN_TEMPLATE_LOADING'] = True
    #mongo.init_app(app)
    planitdb.init_db(app)

    app.register_blueprint(bp_login, url_prefix=preprefix+'/user')
    app.register_blueprint(bp_keyapi, url_prefix=preprefix+'/keys')
    app.register_blueprint(bp_cslpwan, url_prefix=preprefix+'/cslpwan')
    app.register_blueprint(bp_planitapi, url_prefix=preprefix+'/planitapi')
    app.register_blueprint(bp_planitv1, url_prefix=preprefix+'/planit')
    app.register_blueprint(bp_docs, url_prefix=preprefix+'/docs')
    app.register_blueprint(bp_root, url_prefix=preprefix)
    return app

if __name__=="__main__":
    app = MakeApp(debug=True)
    app.run(host="0.0.0.0", port=8000, debug=True)
    #http_server = WSGIServer(('', 5000), app)
    #http_server.serve_forever()
