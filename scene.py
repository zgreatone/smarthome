#!/usr/bin/env python
from flask import *
import requests
import simplejson as json
import random
import time
from requests.auth import HTTPDigestAuth

import vera_config


# super class modal for devices
class Scene:
    id = 0
    name = ""

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return json.dumps({"id": self.id, "name": self.name})

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def activate(self, serviceName):
        # set state
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        p = {'serviceId': serviceName, 'SceneNum': self.id, 'rand': random.random()}
        if auth_user is not None and auth_key is not None:
            response = requests.get(
                "http://" + vera_ip + "/port_3480//data_request?id=lu_action&output_format=json&action=RunScene",
                params=p,
                auth=HTTPDigestAuth(auth_user, auth_key))
        else:
            response = requests.get(
                "http://" + vera_ip + "/port_3480//data_request?id=lu_action&output_format=json&action=RunScene",
                params=p)

        # return response
        if "ERROR" not in response.__dict__['_content']:
            return True
        else:
            return jsonify(result="Error from Vera", message=response.__dict__['_content'])
