from flask import Blueprint, send_from_directory, request
import logging
from .decorators import log

bp_docs = Blueprint('thedocs', 'thedocs')

@bp_docs.route("/")
def index():
    return send_from_directory('./doc/build/html/', 'index.html')


@bp_docs.route("/<path:filename>")
def rootfile(filename):
	logging.info("filename: {}".format(filename))
	return send_from_directory('./doc/build/html/', filename)

@bp_docs.route('/_static/<path:fn>')
def docstatic(fn):
    logging.info("url: {}".format(request.url))
    logging.info("root: {}".format(request.script_root))
    logging.info("doc: {}".format(fn))
    logging.info(fn)
    return send_from_directory('./doc/build/html/_static', fn)
