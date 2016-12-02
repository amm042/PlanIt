from flask import Blueprint, session, request, render_template
import logging


# web data
from .data import *
from .decorators import *

bp_keyapi = Blueprint('keyapi', __name__,
    template_folder ='templates',
    static_folder = 'static')


@bp_keyapi.route('/')
@log
@require_login
def index():
    return render_template('keyapi.html', user=session.get('token'))


@bp_keyapi.route('/list_keys', methods=['GET'])
@log
@require_login
def list_keys():
    return jsonify(planitdb.list_keys(session['token']))


@bp_keyapi.route('/create_key', methods=['POST'])
@log
@require_login
def create_key():
    planitdb.create_key(session['token'], request.remote_addr)
    return jsonify({"result": "success", "keys": planitdb.list_keys(session['token'])})

@bp_keyapi.route('/enable_key', methods=['POST'])
@log
@require_login
def enable_key():
    logging.info(request.json)
    signature = request.json['signature']
    logging.info("enable key with signature {} on user {}.".format(
        signature, session['token']['sub']))
    res = planitdb.enable_key(session['token'], signature, request.remote_addr)
    logging.info("result {}.".format(res))
    return list_keys()
@bp_keyapi.route('/disable_key', methods=['POST'])
@log
@require_login
def disable_key():
    logging.info(request.json)
    signature = request.json['signature']
    logging.info("disable key with signature {} on user {}.".format(
        signature, session['token']['sub']))
    res = planitdb.disable_key(session['token'], signature, request.remote_addr)
    logging.info("result {}.".format(res))
    return list_keys()

@bp_keyapi.route('/remove_key', methods=['POST'])
@log
@require_login
def remove_key():
    logging.info(request.json)
    signature = request.json['signature']
    logging.info("remove key with signature {} on user {}.".format(
        signature, session['token']['sub']))
    res = planitdb.delete_key(session['token'], signature, request.remote_addr)
    logging.info("result {}.".format(res))
    return list_keys()
