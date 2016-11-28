from functools import wraps
from flask import request, session, make_response
from .data import planitdb, jsonify

import logging
import traceback

def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'key' not in request.args:
            return jsonify({"error": "No key specified."}, status_code=401)

        if planitdb.validate_key(request.args['key'], request.remote_addr):
            return f(*args, *kwargs)
        else:
            return jsonify({"error": "Key is invalid or disabled."}, status_code=401)
    return wrapper

def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session and session['logged_in'] == True and 'token' in session:
            return f(*args, *kwargs)
        else:
            return jsonify({"error": "Not logged in."}, status_code=401)
    return wrapper

def log(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        rsp = jsonify({"error": "Server error"}, status_code=500)

        try:
            rsp = f(*args, *kwargs)
        except Exception as x:
            logging.error(traceback.format_exc())
            rsp = jsonify({"error": "Server error",
            "exception": str(x)}, status_code=500)
        finally:
            rsp = make_response(rsp)
            # logging.info(dir(rsp))
            # logging.info("log decorator got rsp: {}".format(rsp))
            if 'token' in session:
                tk = session['token']
            else:
                tk = {'sub':-1}
            planitdb.log_access(
                tk,
                request,
                rsp
            )
        return rsp
    return wrapper
