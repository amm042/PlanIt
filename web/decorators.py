from functools import wraps
from flask import request, session, make_response
from .data import planitdb, jsonify

import logging
import traceback

#http://flask.pocoo.org/snippets/93/
def ssl_required(fn):
    @wraps(fn)
    def decorated_view(*args, **kwargs):    
        if request.is_secure:
            return fn(*args, **kwargs)
        else:
            return redirect(request.url.replace("http://", "https://"))            
    return decorated_view

def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        # logging.info("headers: {}".format(request.headers))
        # logging.info("form: {}".format(request.form))
        # logging.info("json: {}".format(request.json))
        # logging.info("data: {}".format(request.data))
        # logging.info("args: {}".format(request.args))
        # logging.info("values: {}".format(request.values))
        # logging.info("stream: {}".format(request.stream.read()))
    
        if 'key' in request.args:
            key = request.args['key']
        elif 'key' in request.json:
            key = request.json['key']
        else:
            return jsonify({"error": "No key specified."}, status_code=401)

        if planitdb.validate_key(key, request.remote_addr):
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
