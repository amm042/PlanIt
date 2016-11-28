from flask import Response
from .PlanItDb import planItDb

planitdb = planItDb(secret = b'\xc3\x16g\xae\x1a\x03{')

from bson import json_util
# need to fixy jsonify to handle mongo object id's
# http://stackoverflow.com/questions/19877903/using-mongo-with-flask-and-python
def jsonify(x, status_code=None):
    if status_code == None:
        return Response(
            json_util.dumps(x),
            mimetype='application/json'
        )
    else:
        return Response(
            json_util.dumps(x),
            mimetype='application/json',
        ), status_code
