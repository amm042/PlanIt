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
from web.planitapi import bp_planitapi
# from web import *
from web.data import *
from web.decorators import *


app = Flask('main')
app.config.update({
    'MONGO_HOST': 'eg-mongodb',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'planit',
    #'MONGO_USERNAME': 'owner',
    #'MONGO_PASSWORD': '1M$t5iOqXzWMw&aM'
    'MONGO_USERNAME': 'webservice',
    'MONGO_PASSWORD': 'F7ZGLY86xjby',
})
# key for session
app.config['SECRET_KEY'] = "not a very secret key."
# app.config['EXPLAIN_TEMPLATE_LOADING'] = True
#mongo.init_app(app)
planitdb.init_db(app)

app.register_blueprint(bp_login, url_prefix='/user')
app.register_blueprint(bp_keyapi, url_prefix='/keys')
app.register_blueprint(bp_planitapi, url_prefix='/planit')

applications = [
    {'name': 'PlanIt', 'func': 'planitapi.index'},
    {'name': 'API key manager', 'func': 'keyapi.index'}
]
services = [
        {'name':'Elevation', 'func': "planitapi.elevation"}
        ]

@app.route("/")
@log
def index():
    # logging.info("index, session is: {}".format(session))
    if 'logged_in' in session and session['logged_in'] == True and 'token' not in session:
        session.clear()

    return render_template('index.html', user=session.get('token'),
        services=services, applications=applications)

if __name__=="__main__":

    import logging
    import logging.handlers
    logfile =  os.path.splitext(sys.argv[0])[0] + ".log"

    logging.basicConfig(level=logging.DEBUG,
                    handlers=(logging.StreamHandler(stream=sys.stdout),
                              logging.handlers.RotatingFileHandler(logfile,
                                                                    maxBytes = 256*1024,
                                                                    backupCount = 6), ),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    app.run(host="0.0.0.0", port=5000, debug=True)
