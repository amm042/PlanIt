from flask import Blueprint, session, request, flash, redirect, \
    url_for
import logging

# google login
from oauth2client import client, crypt

# web data
from .data import *
from .decorators import *

bp_login = Blueprint('login', __name__)

CLIENT_ID = "645762832040-gcp2qd1fkgta26c3218l8c43roqsvrnk.apps.googleusercontent.com"

@bp_login.route('/login', methods=['GET', 'POST'])
@log
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
                idinfo = client.verify_id_token(request.form['id_token'],
                    CLIENT_ID)

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
                return jsonify({"error": "invalid id_token!"})

            # planitdb.log_access(idinfo, request)

            session['logged_in'] = True
            session['token'] = idinfo

            flash('You were logged in')
            rsp = {"redirect": url_for('index')}

            return jsonify(rsp)
        else:
            return jsonify({"error": "no id_token!"})
    return redirect(url_for('index'))

@bp_login.route('/logout')
@log
def logout():
    # session.pop('logged_in', None)
    # session.pop('token', None)
    session.clear()
    flash('You were logged out')
    return redirect(url_for('index'))
