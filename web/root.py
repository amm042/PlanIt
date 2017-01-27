from flask import Blueprint, session, render_template
import logging
from .decorators import *

bp_root = Blueprint('root', __name__,
    static_folder='static',
    template_folder ='templates')

applications = [
    {'name': 'PlanIt - Crowdsourced Network Planner', 'func': 'cslpwan.index'},
    {'name': 'PlanIt - Manual Network Planner', 'func': 'planit.index'},
    {'name': 'PlanIt - Web Service API', 'func': 'planitapi.index'},
    {'name': 'Docs', 'func': 'thedocs.index'},
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

    return render_template('root.html', user=session.get('token'),
        services=services, applications=applications)
