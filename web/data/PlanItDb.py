from flask_pymongo import PyMongo
import datetime
import logging

from itsdangerous import JSONWebSignatureSerializer

class planItDb():
    def __init__(self, secret):
        self.sig = JSONWebSignatureSerializer(secret)
        self.log = logging.getLogger("planItDb")

    def init_db(self, app):
        self.mongo = PyMongo()
        self.mongo.init_app(app)

    def log_access(self, idinfo, request, response):
        #ensure we have the user in the user db
        curs = self.mongo.db.users.find({'sub':idinfo['sub']}).limit(1)
        if curs.count() == 0:
            self.log.info("Add user to db: {}".format(idinfo))
            # need to make a copy because mongo adds its objectid, whcih
            # cannot be seralized into the session.
            d = idinfo.copy()
            d['created'] = datetime.datetime.utcnow()
            d['remote_addr'] = [request.remote_addr]
            self.mongo.db.users.insert(d)
        else:
            dbuser = curs.next()
            if request.remote_addr not in dbuser['remote_addr']:
                self.mongo.db.users.update(
                    {'_id': dbuser['_id']},
                    {'$push': {'remote_addr': request.remote_addr}}
                )

        self.mongo.db.accesses.insert(
        {
            'sub': idinfo['sub'],
            'headers': dict(request.headers),
            'args': {x:request.args[x] for x in request.args.keys()},
            'time': datetime.datetime.utcnow(),
            'remote': request.remote_addr,
            'url': request.url,
            'status': response.status_code,
            'length': response.content_length
        })
    def validate_key(self, key, remote_addr):
        doc = self.mongo.db.keys.find({'signature': key}).next()
        if doc == None:
            return False

        if 'active' not in doc:
            return False

        op = {
            '$inc': {'use_info.use_count': 1},
            '$set': {'use_info.last_used': datetime.datetime.utcnow()}
            }
        if remote_addr not in doc['use_info']['remotes']:
            op['$push'] = {'use_info.remotes': remote_addr}
        self.mongo.db.keys.update({'_id': doc['_id']}, op)

        return doc['active']

    def enable_key(self, idinfo, signature, remote_addr):
        return self.mongo.db.keys.update(
            {'sub': idinfo['sub'], 'signature': signature},
            {'$set': {'active': True}}
        )
    def disable_key(self, idinfo, signature, remote_addr):
        return self.mongo.db.keys.update(
            {'sub': idinfo['sub'], 'signature': signature},
            {'$set': {'active': False}}
        )
    def delete_key(self, idinfo, signature, remote_addr):
        self.mongo.db.users.update(
                {"sub": idinfo['sub']},
                {'$push': {'deleted_keys':
                    {'when': datetime.datetime.utcnow(),
                    'remote_addr': remote_addr,
                     'signature': signature}}
                    }
            )
        return self.mongo.db.keys.remove(
            {'sub': idinfo['sub'], 'signature': signature})

    def get_or_create_webkey(self, idinfo, remote_addr):
        "look for a webkey, reutrn if found, else create one and return it"
        curs = self.mongo.db.keys.find(
            {'sub': idinfo['sub'], 'web': True, 'active':True},
            {'_id': False})
        if curs.count() > 0:
            return curs.next()
        return self.create_key(idinfo, remote_addr, web=True)

    def create_key(self, idinfo, remote_addr, web=False):
        "create a new key for the user with idinfo (jwt)"
        keydoc = {
            'sub': idinfo['sub'],
            'created': datetime.datetime.utcnow(),
            'create_address': remote_addr,
            'use_info': {'use_count': 0,
                        'remotes': [remote_addr]},
            'active': True,
            'web': web,
            'signature': [0*64] # dummy data
        }
        self.mongo.db.keys.insert(keydoc)
        # do the insert to get the _id, then compute the signature on the id

        # store the doc id,
        docid = keydoc['_id']
        del keydoc['_id']

        keydoc['signature'] = self.sig.dumps(str(docid)).decode('utf-8')
        self.log.info("signature is: {}".format(keydoc['signature']))

        self.mongo.db.keys.update(
            {"_id": docid},
            {'$set': {'signature': keydoc['signature']}}
        )

        self.mongo.db.users.update(
            {"sub": idinfo['sub']},
            {'$push': {'created_keys':
                {'when': datetime.datetime.utcnow(),
                 'remote_addr': remote_addr,
                 'signature': keydoc['signature']}}}

        )

        return keydoc

    def list_keys(self, idinfo):
        keys = list(self.mongo.db.keys.find(
            {'sub': idinfo['sub']},
            {'_id': False}))

        self.log.info("got keys: {}".format(keys))

        return keys
