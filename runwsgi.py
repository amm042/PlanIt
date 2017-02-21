# flask /wsgi
from gevent.wsgi import WSGIServer
from gevent import monkey
from flask import Flask, request, redirect
from urllib.parse import urlparse, urlunparse

# logging
import logging

# patch for gevent cooperative tasking
monkey.patch_all()

from PlanItWebServices import makeApp
"""
OLD

logfile = os.path.splitext(sys.argv[0])[0] + ".log"

logging.basicConfig(
    level = logging.DEBUG,
    handlers = (
        logging.StreamHandler(stream=sys.stdout),
              logging.handlers.RotatingFileHandler(
                logfile,
                maxBytes = 256*1024,
                backupCount = 6)),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask('main',static_url_path='/static')
app.config.update({
    'MONGO_HOST': 'eg-mongodb',
    'MONGO_PORT': 27017,
    'MONGO_DBNAME': 'planit',
    'MONGO_USERNAME': 'webservice',
    'MONGO_PASSWORD': 'F7ZGLY86xjby',
})
# key for session
app.config['SECRET_KEY'] = "not a very secret key."
app.config['APPLICATION_ROOT'] = '/planit'
app.config['DEBUG'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
planitdb.init_db(app)

app.register_blueprint(bp_login, url_prefix='/planit/user')
app.register_blueprint(bp_keyapi, url_prefix='/planit/keys')
app.register_blueprint(bp_cslpwan, url_prefix='/planit/cslpwan')
app.register_blueprint(bp_planitapi, url_prefix='/planit/planitapi')
app.register_blueprint(bp_planitv1, url_prefix='/planit/planit')
app.register_blueprint(bp_docs, url_prefix='/planit/docs')
app.register_blueprint(bp_root, url_prefix='/planit')
"""


# @app.errorhandler(404)
# def page_not_found(error):
#     print(error)
#     print(request.url)
#     return "page not found", 404

@app.before_request
def redirect_eg():
    u = urlparse(request.url)

    # don't redirect static content to https
    # possibel security risk by appending static to a non-static url??
    if '/static/' in u.path:
        return None

    # already https
    if u.netloc == 'www.eg.bucknell.edu':# and request.is_secure:
        # logging.info("NO redirect {}".format(request.url))
        return None

    # redirect everything else
    # logging.info(str(u))
    # logging.info(request.headers)
    # force https
    x  = urlunparse(('https', 'www.eg.bucknell.edu') + u[2:])
    logging.info("redirect {} to {}".format(request.url, x))
    return redirect(x, code=301)


app = makeApp(preprefix='/planit')
http_server = WSGIServer(('', 4002), app)
http_server.serve_forever()
