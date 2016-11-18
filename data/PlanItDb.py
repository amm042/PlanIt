import datetime
import logging

from itsdangerous import JSONWebSignatureSerializer

class planItDb():
    def __init__(self, mongo, secret):
        self.mongo = mongo
        self.sig = JSONWebSignatureSerializer(secret)
        self.log = logging.getLogger("planItDb")

    def log_access(self, idinfo, remote_addr):
        curs = self.mongo.db.users.find({'sub':idinfo['sub']}).limit(1)
        if curs.count() == 0:
            self.log.info("Add user to db: {}".format(idinfo))
            # need to make a copy because mongo adds its objectid, whcih
            # cannot be seralized into the session.
            d = idinfo.copy()
            d['created'] = datetime.datetime.utcnow()
            d['access_times'] = [datetime.datetime.utcnow()]
            d['addresses'] = [remote_addr]

            self.mongo.db.users.insert(d)
        else:
            dbuser = curs.next()
            self.log.info("User in db: {}".format(dbuser))
            self.mongo.db.users.update(
                {'_id': dbuser['_id']},
                {'$push':
                    {'access_times': datetime.datetime.utcnow(),
                     'addresses': remote_addr}
                })
    def create_key(self, idinfo, remote_addr):
        "create a new key for the user with idinfo (jwt)"
        keydoc = {
            'sub': idinfo['sub'],
            'created': datetime.datetime.utcnow(),
            'create_address': remote_addr,
            'use_info': [],
            'active': True,
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

        return keydoc

    def list_keys(self, idinfo):
        keys = list(self.mongo.db.keys.find(
            {'sub': idinfo['sub']},
            {'_id': False}))

        self.log.info("got keys: {}".format(keys))

        return keys
