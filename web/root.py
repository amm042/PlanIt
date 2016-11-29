from flask import Blueprint, session
import logging
from .decorators import *

bp_root = Blueprint('root', __name__)
applications = [
    {'name': 'PlanIt', 'func': 'planitapi.index'},
    {'name': 'API key manager', 'func': 'keyapi.index'}
]
services = [
        {'name':'Elevation', 'func': "planitapi.elevation"}
        ]

@bp_root.route("/")
@log
def index():
    # logging.info("index, session is: {}".format(session))
    if 'logged_in' in session and session['logged_in'] == True and 'token' not in session:
        session.clear()

    return render_template('index.html', user=session.get('token'),
        services=services, applications=applications)
