from flask import Blueprint, session, request, render_template
import logging

# web data
from .data import *
from .decorators import *

bp_cslpwan = Blueprint('cslpwan', __name__,
    template_folder ='templates',
    static_folder = 'static')

@bp_cslpwan.route('/')
@log
@require_login
def index():
    return render_template('cslpwan.html',
        user=session.get('token'),
        key=planitdb.get_or_create_webkey(session.get('token'), request.remote_addr))
