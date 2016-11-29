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
    """Find the elevation of a given lat/lon location on earth using SRTM data.

    Args:
        lat (float): Latitude of locaiton.
        lon (float): Longitude of location.
        key (string): API key to use for request (must be active).

    """
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

@bp_planitapi.route('/geopath', methods=('get',))
@log
@require_key
def geopath():
    """Construct a path between two points in lat/lon/elev across the earth.

    Args:
        src : source tuple (lon, lat, elev above ground).
        dst : dest tuple (lon, lat, elev above ground).
        resolution (optional) : step size to use in meters. The default is 30m.
            This is the **highest supported resolution** (i.e. smallest step size)
            of the SRTM dataset, however, **larger** values are supported.
    Returns:
        a JSON list of points (lon, lat, elevation).
    """
    if 'src' in request.args and 'dst' in request.args:
        logging.info("geopath req: {}".format(request.args))

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
        return jsonify({"error":"specify 'src' and 'dst' in your query string. Each is a tuple of (lon,lat)."})

@bp_planitapi.route('/', methods=('get',))
@log
def index():
    return "todo index"
