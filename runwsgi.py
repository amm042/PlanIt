from gevent.wsgi import WSGIServer
from PlanItWebServices import app

http_server = WSGIServer(('', 4002), app)
http_server.serve_forever()

