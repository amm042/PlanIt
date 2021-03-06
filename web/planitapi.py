from flask import Blueprint, session, request, g, Response, url_for, current_app, copy_current_request_context
import logging

from .data import *
from .decorators import *


import matplotlib
#matplotlib.use('pdf')
matplotlib.use('Agg')

from elevation import Elevation
from geopath import GeoPath

from itwom import ItwomParams, itwomParams_average, loss_along_path

from bson import json_util, ObjectId

import gevent
from multiprocessing import Process, Queue

import traceback

import inspect
import time
import pymongo

from shapely.geometry import mapping, shape, Point, Polygon, MultiPolygon, box

import os

from .utils.pointSampler import PopulationBasedPointSampler
from .utils.processSamplePoints import AnalyzePoints
from .utils.plotPointResults import PlotCoverage, PlotLoss, PlotContours

SRTM_PATH=os.path.join(os.getcwd(),"../SRTM_RAW")
elev = Elevation(srtm_path=SRTM_PATH, mongo_str= None)
bp_planitapi = Blueprint('planitapi', __name__,
    template_folder ='templates',
    static_folder = 'static')


bp_planitapi_app = None

@bp_planitapi.record
def record_app(setup_state):
    global bp_planitapi_app
    bp_planitapi_app = setup_state.app
    logging.info("record flask app called for planitapi.")

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

    for d in [25, 50, 100]:
        sh2 = sh.simplify(sh.length/d, preserve_topology=True)
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

    cities = sorted(
        list(planitdb.mongo.db['GENZ2010_160'].find({
            'properties.STATE':args['state'], 'properties.LSAD': 'city'})),
        key=lambda x: x['properties']['NAME'])

    counties = sorted(
        list(planitdb.mongo.db['GENZ2010_050_20m'].find({
            'properties.STATE':args['state'], 'properties.LSAD': 'County'})),
        key=lambda x: x['properties']['NAME'])

    return jsonify({
        "cities": simplifyShapes(cities),
        "counties": simplifyShapes(counties)
    })

@bp_planitapi.route("/analyzeResult", methods=('POST',))
@log
@require_key
def analyzeResult():
    args = request.json
    logging.info("analyzeResult args: {}".format(args))
    if 'id' in args:
        crs = planitdb.mongo.db['RUNCACHE'].find({'_id': ObjectId(args['id'])})
        if crs.count() > 0:
            cache = crs.next()

            result = {'id': str(cache['_id']),
                'complete': cache['complete'],
                'args': cache['args']}

            if cache['complete']:
                logging.info("analyzeResult, job complete.")
                result['loss'] = url_for('root.static',
                    filename='results/loss/'+os.path.basename(cache['loss']))
                result['coverage'] = url_for('root.static',
                    filename='results/coverage/'+os.path.basename(cache['coverage']))
                result['contour'] = url_for('root.static',
                    filename='results/contour/'+os.path.basename(cache['contour']))
            else:
                logging.info("analyzeResult, job NOT YET complete.")
            return jsonify(result)
        else:
            logging.info("analyzeResult, no results for id {}.".format(args['id']))
            return jsonify({"error": "no results for that id."}), 500
    else:
        logging.info("analyzeResult, no id given.")
        return jsonify({"error": "must specify id to get result for."}), 500

@bp_planitapi.route("/analyze", methods=('POST',))
@log
@require_key
def analyze():
    """CSLPWAN network analizer

    args:
        pointid: object id of point set to use [required]
        numBase: number of base stations (array) [required if no basestations]
        numRuns: number of simulation runs (int) [required if numBase]
        basestations: the locations of base statiosn [requried if no numBase]
        freq: frequency MHz (float) [required]
        txHeight: transmitter height agl meters [required]
        rxHeight: transmitter reciever agl meters [required]
        model: itwom model 'city' or 'average' [required]
        lossThreshold: radio loss threshold (float) [required]
        bounds: map bounds (LatLngBounds.toJSON) to plot contour [required]
        key: api key [required]

    This is a two-part call due to the possibly long running analysis.
    First call analyze and get a id/jobid. Then pass these to
    analizeResult() to get the results/check progress.
    """

    args = request.json

    @copy_current_request_context
    def async(db, args):
        #global bp_planitapi_app
        #with bp_planitapi_app.app_context():
            logging.info("analyze args: {}".format(args))

            #check if we have results from a previous run
            cache = {'args': args}
            curs = db['RUNCACHE'].find({'args': args})
            if curs.count() > 0:
                logging.info("Cache hit, returning cached results.")
                cache = curs.next()
            else:
                cache['complete'] = False
                db['RUNCACHE'].insert(cache)

            if 'loss' not in cache or   \
                'coverage' not in cache or  \
                'contour' not in cache:
                def worker(mstr, cache):
                    # save result set in database, pass object id of results
                    # and links to plot images back to web service

                    # connect to db in this process.
                    connection = pymongo.MongoClient(mstr)
                    db = connection.get_default_database()
                    rdocs = AnalyzePoints(dbcon=db,
                        connect_str = mstr,
                        srtm_path=SRTM_PATH, **args)

                    ## generate plots of results
                    logging.info("static path is {}".format(
                        os.path.join(os.getcwd(), 'web/static')))

                    cache['coverage'] = PlotCoverage(rdocs, os.path.join(os.getcwd(),
                        os.path.join('web/static/results/coverage')), str(cache['_id']))

                    cache['loss'] = PlotLoss(rdocs, float(args['lossThreshold']),
                        os.path.join(os.getcwd(),
                            os.path.join('web/static/results/loss')), str(cache['_id']))

                    cache['contour'] = PlotContours(rdocs, cache['args']['bounds'],
                        float(args['lossThreshold']), os.path.join(os.getcwd(),
                            os.path.join('web/static/results/contour')), str(cache['_id']))

                    cache['complete'] = True

                    db['RUNCACHE'].update(
                        {'_id': cache['_id']}, cache)

                proc = Process(target=worker,
                    args=("mongodb://{}:{}@{}:{}/{}".format(
                            current_app.config.get('MONGO_USERNAME'),
                            current_app.config.get('MONGO_PASSWORD'),
                            current_app.config.get('MONGO_HOST'),
                            current_app.config.get('MONGO_PORT'),
                            current_app.config.get('MONGO_DBNAME')),
                            cache),
                    name="analysis job")
                proc.start()

                result = {'args': args,
                    'jobid': proc.pid,
                    'id': str(cache['_id'])}

            else:
                result = {'id': str(cache['_id']),
                    'complete': cache['complete'],
                    'args': args,
                    'loss': url_for('root.static',
                        filename='results/loss/'+os.path.basename(cache['loss'])),
                    'coverage': url_for('root.static',
                        filename='results/coverage/'+os.path.basename(cache['coverage'])),
                    'contour': url_for('root.static',
                        filename='results/contour/'+os.path.basename(cache['contour'])),
                        }

            return json_util.dumps(result)

    return Response(async(planitdb.mongo.db, args), mimetype='application/json')

@bp_planitapi.route("/sample", methods=('POST',))
@log
@require_key
def sample():
    """Population based point sampler

    args:
        pointid: object id of previous return set [optional]
        state: numerical state (eg 42 = PA) [required]
        cities: list of city GEO_IDs [optional]
        counties: list of county GEO_IDs [optional]

    returns IoT test point locations within the given geographic bounds
    sampled by population. If no cities or unties are given, the whole
    state is sampled.

    todo: make this async.

    """

    args = request.json
    logging.info("sample args: {}".format(args))

    #@copy_current_request_context
    def async(db, args):
        #global bp_planitapi_app
        #with bp_planitapi_app.app_context():
            if 'pointid' in args:
                cur = db.POINTS.find({'_id': ObjectId(args['pointid'])})
                if cur.count() > 0:
                    logging.info("got points from DB.")
                    result = cur.next()
                    result['pointid'] = str(result['_id'])
                    del result['_id']
                    #del result['args']
                    yield json_util.dumps(result)

                else:
                    yield json_util.dumps({"error":"invalid pointid."}, 406)
                return
            elif 'basestations' in args:
                # basestations takes priorty over bounds
                # these are json points + radius in meters, this defines the
                # sample area
                logging.info("sampling from basesations + radius: {}".format(args['basestations']))
                pbs = PopulationBasedPointSampler(db=db)
                trshapes = []
                names = []
                bbox = None
                for bs in args['basestations']:

                    #area = shape(bs['geometry']).buffer(1000*bs['radius'])
                    area = pbs.get_circle(shape(bs['geometry']), 1000*bs['radius'])
                    #logging.info("constructed area: {}".format(area))
                    if bbox == None:
                        bbox = area
                    else:
                        bbox.union(area)

                    #trshapes += list(pbs.get_shapes(area, 1000*bs['radius']))
                    trshapes += list(pbs.get_tract_shapes_in_area(area))
                    names.append("{},{},{}".format(area.centroid.x, area.centroid.y, bs['radius']))

                name = ", ".join(names)
            elif 'bounds' in args:
                # planit samples from the gmaps bounds
                logging.info("sampling from area: {}".format(args['bounds']))
                b= args['bounds']
                bbox = box(b['west'],  b['south'], b['east'], b['north'])
                pbs = PopulationBasedPointSampler(db=db)
                trshapes = list(pbs.get_tract_shapes_in_area(bbox))
                name = json_util.dumps(b)
            else:
                # cslpwan sampler uses state / cities / counties
                pbs = PopulationBasedPointSampler(db=db)
                trshapes = []
                bbox = None
                name = args['state']
                if (len(args['cities'])> 0):
                    c = db['GENZ2010_160'].find({
                        'properties.STATE':args['state'],
                        'properties.LSAD': 'city',
                        'properties.GEO_ID': {'$in': args['cities']}})
                    for sh in c:
                        name += "-" + sh['properties']['NAME']
                        logging.info("getting tracts for {}".format(sh['properties']))
                        trshapes += pbs.get_tract_shapes_in_area(sh)
                if (len(args['counties']) > 0):
                    c = db['GENZ2010_050'].find({
                        'properties.STATE':args['state'],
                        'properties.LSAD': 'County',
                        'properties.GEO_ID': {'$in': args['counties']}})
                    for sh in c:
                        name += "." + sh['properties']['NAME']
                        logging.info("getting tracts for {}".format(sh['properties']))
                        trshapes += pbs.get_tract_shapes(
                            sh['properties']['STATE'],
                            sh['properties']['COUNTY'])
                if len(trshapes) == 0:
                    # use the whole state
                    trshapes = list(pbs.get_shapes_for_state(args['state']))

            logging.info("got {} tract shapes".format(len(trshapes)))

            for i, sh in enumerate(trshapes):
                logging.info("tract shape {}: {}".format(i, sh['properties']))

            result = {
                'args': args,
                'name': name,
                'population': sum([t['properties']['population']['effective'] for t in trshapes]),
                'area': sum(t['properties']['area']['effective'] for t in trshapes)
            }
            if 'basestations' in args:
                result['basestations'] = args['basestations']
            if 'state' in args:
                result['state'] = args['state']

            logging.info("results, prio to sample: {}".format(result))



            if bbox !=None:
                logging.info("have bbox, using intersect")
                result['points'] = [{
                    'geometry':mapping(p),
                    'title': str(list(p.coords)[0]),
                    'id': 'point_{}'.format(i)} for i,p in
                        enumerate(pbs.sample(
                            args['count'], trshapes, intersect=True))]
            else:
                # using state/county/city there is no bounding box.
                result['points'] = [{
                    'geometry':mapping(p),
                    'title': str(list(p.coords)[0]),
                    'id': 'point_{}'.format(i)} for i,p in
                        enumerate(pbs.sample(args['count'], trshapes))]


            db.POINTS.insert(result)
            result['pointid'] = str(result['_id'])
            del result['_id']
            #del result['args']
            yield json_util.dumps(result)

    return Response(async(planitdb.mongo.db, args), mimetype='application/json')

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
