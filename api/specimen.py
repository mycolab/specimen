import os
import etcd
import hashlib
import json

ETCD_HOST = os.environ.get('ETCD_HOST', '127.0.0.1')
ETCD_PORT = os.environ.get('ETCD_PORT', 2379)


def etc_client() -> etcd.Client:
    client = etcd.Client(host=ETCD_HOST, port=ETCD_PORT)
    return client


def get_id(body: dict) -> str:
    body_str = json.dumps(body)
    return hashlib.md5(body_str.encode('utf-8')).hexdigest()


def post(body: dict = None, **kwargs):
    client = etc_client()
    id = get_id(body)
    resp = {
        'id': id
    }
    return resp, 200


def put(id: str = None, body: dict = None, **kwargs):
    pass


def get(id: str = None, **kwargs):
    pass


def delete(id: str = None, **kwargs):
    pass
