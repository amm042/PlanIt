import flask
from flask import Flask, request, render_template, Response, redirect, \
    url_for, session, flash

from flask_pymongo import PyMongo

from bson import json_util

# need to fixy jsonify to handle mongo object id's
# http://stackoverflow.com/questions/19877903/using-mongo-with-flask-and-python
def jsonify(x):
    return Response(
        json_util.dumps(x),
        mimetype='application/json'
    )

import sys
import os
import os.path
import datetime

from data import *

# from apiclient import discovery
from oauth2client import client, crypt

app = Flask(__name__)
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
mongo = PyMongo(app)
db = planItDb(mongo, secret = b'\xc3\x16g\xae\x1a\x03{')

CLIENT_ID = "645762832040-gcp2qd1fkgta26c3218l8c43roqsvrnk.apps.googleusercontent.com"

services = [
        {'name':'Elevation', 'func': "elevation"}
        ];

@app.route("/")
def index():
    # logging.info("index, session is: {}".format(session))
    if 'logged_in' in session and session['logged_in'] == True and 'token' not in session:
        session.pop('logged_in', None)
    if 'token' in session:
        db.log_access(session['token'], request.remote_addr)
    return render_template('index.html', user=session.get('token'),
        services=services)

@app.route('/list_keys', methods=['GET'])
def list_keys():
    if 'logged_in' in session and session['logged_in'] == True and 'token' in session:

        return jsonify(db.list_keys(session['token']))
    return jsonify({"error": "Not logged in."}), 401
@app.route('/create_key', methods=['POST'])
def create_key():
    if 'logged_in' in session and session['logged_in'] == True and 'token' in session:
        db.create_key(session['token'], request.remote_addr)
        return jsonify({"result": "success", "keys": db.list_keys(session['token'])})
    else:
        logging.info(session)
    return jsonify({"error": "Not logged in."}), 401

@app.route('/remove_key/<int:k_id>', methods=['POST'])
@app.route('/remove_key', methods=['POST'])
def remove_key(k_id=None):
    if 'logged_in' in session and session['logged_in'] == True and 'token' in session:
        if 'keys' in session and k_id < len(session['keys']):
            logging.info("remove {} from {}.".format(k_id, session['keys']))
            kys = session['keys']

            # kys.remove(k_id)
            del kys[k_id]

            # refresh the session variable
            session.pop('keys')
            session['keys'] = kys
            logging.info("result {}.".format(session['keys']))
            return jsonify({"result": "success", "keys": session['keys']})
        else:
            jsonify({"error": "Key not found."}), 400
    return jsonify({"error": "Not logged in."}), 401

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    # logging.info("login valu -- {}".format(request.values))
    # logging.info("login data -- {}".format(request.data))
    logging.info("login form -- {}".format(request.form))
    if request.method == 'POST':
        if 'id_token' in request.form:
            # need to verify the token.
            # see https://developers.google.com/identity/sign-in/web/backend-auth
            try:
                idinfo = client.verify_id_token(request.form['id_token'], CLIENT_ID)

                logging.info("got token: {}".format(idinfo))

                if idinfo['aud'] not in [CLIENT_ID]:
                    raise crypt.AppIdentityError("Unrecognized client.")
                if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                    raise crypt.AppIdentityError("Wrong issuer.")
                # allow accounts from all domains, but could make bucknell.edu here
                # if idinfo['hd'] != APPS_DOMAIN_NAME:
                #     raise crypt.AppIdentityError("Wrong hosted domain.")
            except crypt.AppIdentityError:
                # Invalid token
                return flask.jsonify({"error": "invalid id_token!"})

            log_access(idinfo, request.remote_addr)

            session['logged_in'] = True
            session['token'] = idinfo

            flash('You were logged in')
            rsp = {"redirect": url_for('index')}

            return flask.jsonify(rsp)
        else:
            return flask.jsonify({"error": "no id_token!"})
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('token', None)
    flash('You were logged out')
    return redirect(url_for('index'))

@app.route('/elevation', methods=('get',))
def elevation():
    return 'qs = '+ str(list(request.args))

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
