from flask import Blueprint, send_from_directory, request
import logging
from .decorators import log

bp_doc = Blueprint('thedoc', 'thedoc')

@bp_doc.route("/")
def index():    
    return send_from_directory('/nfs/unixspace/linux/accounts/projects/planit/PlanIt/doc/build/html/', 'index.html')


@bp_doc.route("/<path:filename>")
def rootfile(filename):    
	logging.info("filename: {}".format(filename))
	return send_from_directory('/nfs/unixspace/linux/accounts/projects/planit/PlanIt/doc/build/html/', filename)

@bp_doc.route('/_static/<path:fn>')
def docstatic(fn):
    logging.info("url: {}".format(request.url))
    logging.info("root: {}".format(request.script_root))
    logging.info("doc: {}".format(fn))
    logging.info(fn)
    return send_from_directory('/nfs/unixspace/linux/accounts/projects/planit/PlanIt/doc/build/html/_static', fn)