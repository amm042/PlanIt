from flask import Blueprint, session, request, g
import logging

from .data import *
from .decorators import *

from elevation import Elevation

import traceback

elev = Elevation(mongo_str= None)
bp_planitapi = Blueprint('planitapi', __name__)


@bp_planitapi.route('/elevation', methods=('get',))
@log
@require_key
def elevation():
    if 'lat' in request.args and 'lon' in request.args:
        logging.info("elevation req: {}".format(request.args))

        try:
            result = float(elev.lookup(
                (float(request.args['lon']),
                float(request.args['lat']))))
            #this returns a numpy type, convert it to float
        except Exception as x:
            logging.info("lookup failed")
            logging.error(traceback.format_exc())
            return jsonify({"error": str(x)}), 500

        return jsonify({"result": result})
    else:
        return jsonify({"error":"specify 'lat' and 'lon' in your query string."})


@bp_planitapi.route('/', methods=('get',))
@log
def index():
    return "todo index"
