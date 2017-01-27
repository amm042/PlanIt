from flask import Blueprint, session, request, g, Response, url_for
import logging

from .data import *
from .decorators import *

from elevation import Elevation
from geopath import GeoPath

from itwom import ItwomParams, itwomParams_average, loss_along_path

from bson import json_util

import gevent
from multiprocessing import Process, Queue

import traceback

import inspect
import time


from shapely.geometry import mapping, shape, Point, Polygon, MultiPolygon

SRTM_PATH="../SRTM_RAW"
elev = Elevation(srtm_path=SRTM_PATH, mongo_str= None)
bp_planitapi = Blueprint('planitapi', __name__,
    template_folder ='templates',
    static_folder = 'static')

#http://code.activestate.com/recipes/52308-the-simple-but-handy-collector-of-a-bunch-of-named/?in=user-97991
# class Bunch:
#     def __init__(self, **kwds):
#         self.__dict__.update(kwds)
@bp_planitapi.route('/elevation', methods=['GET'])
@log
def elevation_help():
    return  inspect.getdoc(elevation)

@bp_planitapi.route('/elevation', methods=['POST'])
@log
@require_key
def elevation():
    """Find the elevation of a given lat/lon location on earth using SRTM data.

    Args:
        lat (float): Latitude of locaiton.
        lon (float): Longitude of location.
        key (string): API key to use for request (must be active).

    """
    args = request.json

    if 'lat' in args and 'lon' in args:
        logging.info("elevation req: {}".format(args))

        try:
            result = elev.lookup(
                (float(args['lon']),
                float(args['lat'])))

        except Exception as x:
            logging.info("lookup failed")
            logging.error(traceback.format_exc())
            return jsonify({"error": str(x)}), 500

        return jsonify({"result": result})
    else:
        return jsonify({"error":"specify 'lat' and 'lon' in your request."})

@bp_planitapi.route('/geopath', methods=('POST',))
@log
@require_key
def geopath():
    """Construct a path between two points in lat/lon/elev across the earth.

    Args:
        src : source tuple (lon, lat).
        dst : dest tuple (lon, lat).
        resolution (optional) : step size to use in meters. The default is 30m.
            This is the **highest supported resolution** (i.e. smallest step size)
            of the SRTM dataset, however, **larger** values are supported.
    Returns:
        a JSON list of points with elevations: (lon, lat, elevation).
    """
    args = request.json
    logging.info("geopath: ({})".format(args))
    if 'src' in args and 'dst' in args:
        logging.info("geopath req: {}".format(args))

        try:
            #src = [float(x) for x in args['src']]
            #dst = [float(x) for x in args['dst']]
            src = args['src']
            dst = args['dst']

            resolution = 30
            if 'resolution' in args:
                resolution = float(args['resolution'])

            gp = GeoPath(src, dst, resolution=resolution, elev=elev, async=True)

            def json_wrap():
                # note: http://sergray.me/asynchony-in-the-flask.html
                yield ''
                for x in gp.async():
                    yield json_util.dumps(x)
            logging.info("geopath api -- start response.")
            return Response(gp.async(), mimetype='application/json')

        except Exception as x:
            logging.info("lookup failed")
            logging.error(traceback.format_exc())
            return jsonify({"error": str(x)}), 500

        return jsonify({"result": result})
    else:
        return jsonify({"result":"error", "error":"specify 'src' and 'dst' in your query string. Each is a tuple of (lon,lat)."})

@bp_planitapi.route('/', methods=('get',))
@log
def index():
    return "This is the root of the PlanIt Web Service API. See the <a href={}>docs for more information</a>".format(
        url_for('thedocs.index')
    )

@bp_planitapi.route('/itwomparams', methods=('POST',))
@log
@require_key
def getitwomparams():
    """Returns an ItowmParams object.

    Returns:
        ItwomParams object that can be modified and passed to the pathloss function


    """
    return jsonify({"result": vars(itwomParams_average())})

def simplifyPoly(name, p):
    "p must be a geojson Polygon"
    sh = shape(p)

    for d in [10.0, 20.0, 40]:
        sh2 = sh.simplify(sh.length/20.0, preserve_topology=True)
        if sh2.is_empty:
            logging.info("{} FAILED with src of {} pts".format(
                name,
                len(sh.exterior.coords)
            ))
            sh2 = sh
        else:
            break

    logging.info("{} has {} points --> {} points.".format(
        name,
        len(sh.exterior.coords),
        len(sh2.exterior.coords)))


    return mapping(sh2)

def simplifyShapes(geoobjs):
    "simplifies geojson objects"
    # simplify city geometry
    for obj in geoobjs:
        if obj['geometry']['type'] == 'MultiPolygon':
            cord = []
            logging.info("MULTIPOLY+++")
            for c in obj['geometry']['coordinates']:
                mp = simplifyPoly(
                    obj['properties']['NAME'],
                    {'type':'Polygon', 'coordinates': c})
                cord.append(mp['coordinates'])
            logging.info("MULTIPOLOY---")
            obj['geometry']['coordinates'] = cord

        if obj['geometry']['type'] == 'Polygon':
            mp = simplifyPoly(
                obj['properties']['NAME'], obj['geometry']
            )
            obj['geometry'] = mp
    return geoobjs

@bp_planitapi.route('/geonames', methods=('POST',))
@log
@require_key
def geonames():
    """Returns geographic names that match the given query.

    Args:
        state: state to limit search

    Returns:
        a list of cities and continues in that state
    """
    args = request.json
    logging.info("geonames: ({})".format(args))

    cities = list(planitdb.mongo.db['GENZ2010_160'].find({
        'properties.STATE':args['state'], 'properties.LSAD': 'city'}))
    counties = list(planitdb.mongo.db['GENZ2010_050_20m'].find({
        'properties.STATE':args['state'], 'properties.LSAD': 'County'}))

    return jsonify({
        "cities": simplifyShapes(cities),
        "counties": simplifyShapes(counties)
    })


@bp_planitapi.route('/pathloss', methods=('POST',))
@log
@require_key
def pathloss():
    """Compute the path loss using ITWOM between src and dst.

    Use src/dst OR path as input.

    Args:
        src : source tuple (lon, lat).
        dst : destination tuple (lon, lat).
        tx_height (default: 0): height of transmitter above ground (meters).
        rx_height (default: 0): height of receiver above ground (meters)
        path: a geopath (list of (lon,lat,elevation) containing the source (path[0])
            and destination (path[-1]).
        resolution (default:30): if using src/dst this is the distance in meters between
            the generated points along the path.
        itwomparams (default:itwomparams_average): parameters for ITWOM model (see getitwomparams).
        point_to_point (default:True): if true return the point to point path
            loss between src/dst. Else, returns a list of (lon, lat, path_loss)
            along the entire path.

    Returns:
        Either a single float or a list of tuples (lon, lat, path_loss)

    """
    args = request.json

    logging.info("pathloss: ({})".format(args))

    tx_height = 0
    rx_height = 0
    resolution = 30
    p2p = True
    itwomparams = itwomParams_average()

    try:
        if 'tx_height' in args:
            tx_height = args['tx_height']
        if 'rx_height' in args:
            rx_height = args['rx_height']
        if 'resolution' in args:
            resolution = args['resolution']
        if 'point_to_point' in args:
            p2p = args['point_to_point']
        if 'itwomparams' in args:
            itwomparams = ItwomParams(**args['itwomparams'])
    except Exception as x:
        logging.info("read parmas failed")
        logging.error(traceback.format_exc())
        return jsonify({"error": str(x)}), 406

    # workers will be called as separate processes.
    def loss_worker(q, path, tx_height, rx_height, p2p, itwomparams):
        if p2p:
            result = loss_along_path(tx_height, rx_height, path, params=itwomparams, evaluate_path = False)
            q.put(result)
        else:
            for result in loss_along_path(tx_height, rx_height, path, params=itwomparams, evaluate_path = True):
                q.put(result)
        # put sentinal value
        q.put(None)

    def path_and_loss_worker(q, src, dst, tx_height, rx_height, resolution, p2p, itwomparams):
        gp = GeoPath(src, dst, resolution=resolution, elev=elev)
        loss_worker(q, gp, tx_height, rx_height, p2p, itwomparams)

    q = Queue()
    if 'src' in args and 'dst' in args:
        logging.info("pathloss using src/dst: {}".format(args))

        try:
            # src = [float(x) for x in args['src']]
            # dst = [float(x) for x in args['dst']]
            src = args['src']
            dst = args['dst']

            proc = Process(target = path_and_loss_worker, args=(q, src, dst, tx_height, rx_height, resolution, p2p, itwomparams))
            proc.start()

        except Exception as x:
            logging.info("pathloss calc failed")
            logging.error(traceback.format_exc())
            return jsonify({"error": str(x)}), 500

    elif 'path' in args:
        logging.info("pathloss using path: {}".format(args))
        gp = args['path']

        proc = Process(target = loss_worker, args=(q, GeoPath(path=gp, elev=elev), tx_height, rx_height, p2p, itwomparams))
        proc.start()
    else:
        return jsonify({"result": "error", "error":"Specify src/dst or path in your request."})

    def async(q):
        yield ''
        while q.empty():
            gevent.sleep(1)
            yield ' '

        logging.info("pathloss compelte.")

        while True:
            y = q.get()
            # logging.info("pathloss got result: {}".format(y))
            if y == None:
                logging.info("pathloss got final result, resoponse complete.")
                break
            yield ( json_util.dumps(y) )

    return Response(async(q), mimetype='application/json')
