#!/usr/bin/env python
from flask import *
import requests
import simplejson as json
import random
import time
from requests.auth import HTTPDigestAuth

import vera_config


# super class modal for devices
class Device:
    id = 0
    name = ""
    room = ""
    state = 0

    def __init__(self, id, name, room, state):
        self.id = id
        self.name = name
        self.room = room
        self.state = state

    def __repr__(self):
        return json.dumps({"id": self.id, "name": self.name, "room": self.room, "state": self.state})

    def get_state(self):
        return self.state

    def get_id(self):
        return self.id

    def update_state(self, newState):
        self.state = newState

    def verify_state(self, targetState):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        for i in range(80):
            p = {'DeviceNum': self.id, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p)
            states = json.loads(response.__dict__['_content'])['Device_Num_' + str(self.id)]['states']

            for state in states:
                if state["variable"] == "Status":
                    self.state = state["value"]
            if self.state == str(targetState):
                return True
            else:
                time.sleep(0.3)
        return False

    def set_state(self, targetState, serviceName):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        # set state
        p = {'serviceId': serviceName, 'DeviceNum': self.id, 'newTargetValue': targetState, 'rand': random.random()}
        if auth_user is not None and auth_key is not None:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetTarget",
                params=p,
                auth=HTTPDigestAuth(auth_user, auth_key))
        else:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetTarget",
                params=p)

        # return response
        if "ERROR" not in response.__dict__['_content']:
            if self.verify_state(targetState):
                return True
            else:
                return jsonify(result="Error",
                               message="Switching state of " + str(self.name) + "(" + str(self.id) + ") has timed out")
        else:
            return jsonify(result="Error", message=response.__dict__['_content'])


# class light inherits from device
class Light(Device):
    brightness = None

    def __init__(self, id, name, room, state, brightness):
        self.id = id
        self.name = name
        self.room = room
        self.state = state
        self.brightness = brightness

    def __repr__(self):
        if self.brightness is None:
            return json.dumps({"id": self.id, "name": self.name, "room": self.room, "state": self.state,
                               "brightness": self.brightness})
        else:
            return json.dumps({"id": self.id, "name": self.name, "room": self.room, "state": self.state})

    def get_brightness(self):
        return self.brightness

    def update_brightness(self, newBrightness):
        self.brightness = newBrightness

    def set_brightness(self, targetBrightness, serviceName):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        # set state
        p = {'serviceId': serviceName, 'DeviceNum': self.id, 'newLoadlevelTarget': targetBrightness,
             'rand': random.random()}
        if auth_user is not None and auth_key is not None:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetLoadLevelTarget",
                params=p,
                auth=HTTPDigestAuth(auth_user, auth_key))
        else:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetLoadLevelTarget",
                params=p)

        # return response
        if "ERROR" not in response.__dict__['_content']:
            if self.verify_brightness(targetBrightness):
                return True
            else:
                return jsonify(result="Error", message="Changing brightness of " + str(self.name) + "(" + str(
                    self.id) + ") has timed out")
        else:
            return jsonify(result="Error", message=response.__dict__['_content'])

    def verify_brightness(self, targetBrightness):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        for i in range(80):
            p = {'DeviceNum': self.id, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p)
            states = json.loads(response.__dict__['_content'])['Device_Num_' + str(self.id)]['states']

            for state in states:
                if state["variable"] == "LoadLevelStatus":
                    self.state = state["value"]
            if self.state == str(targetBrightness):
                return True
            else:
                time.sleep(0.3)
        return False


# class lock inherits from device
class Lock(Device):
    pass


# class nest inherits from device and contains additional variables
class Nest(Device):
    currentTemp = 0
    maxTemp = 78
    minTemp = 70
    controllerId = 0

    def __init__(self, id, name, room, currentTemp, maxTemp, minTemp, controllerId, state):
        self.id = id
        self.name = name
        self.room = room
        self.state = state
        self.currentTemp = currentTemp
        self.maxTemp = maxTemp
        self.minTemp = minTemp
        self.controllerId = controllerId

    def __repr__(self):
        return json.dumps({"id": self.id, "name": self.name, "room": self.room, "currentTemp": self.currentTemp,
                           "maxTemp": self.maxTemp, "minTemp": self.minTemp, "controllerId": self.controllerId,
                           "state": self.state})

    def update_current_temp(self, newCurrentTemp):
        self.currentTemp = newCurrentTemp

    def update_max_temp(self, newMaxTemp):
        self.maxTemp = newMaxTemp

    def update_min_temp(self, newMinTemp):
        self.minTemp = newMinTemp

    def get_controller_id(self):
        return self.controllerId

    def get_min_temp(self):
        return self.minTemp

    def get_max_temp(self):
        return self.maxTemp

    def verify_temp(self, targetMinTemp, targetMaxTemp):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        for i in range(45):
            p = {'DeviceNum': self.id, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p)
            states = json.loads(response.__dict__['_content'])['Device_Num_' + str(self.id)]['states']

            for state in states:
                if state["variable"] == "CurrentTemperature":
                    self.currentTemp = state["value"]
                if "TemperatureSetpoint1_Heat" in state["service"] and state["variable"] == "CurrentSetpoint":
                    self.minTemp = state["value"]
                if "TemperatureSetpoint1_Cool" in state["service"] and state["variable"] == "CurrentSetpoint":
                    self.maxTemp = state["value"]

            if str(self.minTemp) == str(targetMinTemp) and str(self.maxTemp) == str(targetMaxTemp):
                return True
            else:
                time.sleep(0.3)

        return False

    def set_temp(self, targetMinTemp, targetMaxTemp):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        if targetMinTemp != self.minTemp:
            # set temp
            p = {'DeviceNum': self.id, 'NewCurrentSetpoint': targetMinTemp, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetCurrentSetpoint&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Heat",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetCurrentSetpoint&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Heat",
                    params=p)
            if "ERROR" in response.__dict__['_content']:
                return jsonify(result="Error", message=response.__dict__['_content'])

        if targetMaxTemp != self.maxTemp:
            # set temp
            p = {'DeviceNum': self.id, 'NewCurrentSetpoint': targetMaxTemp, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetCurrentSetpoint&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Cool",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetCurrentSetpoint&serviceId=urn:upnp-org:serviceId:TemperatureSetpoint1_Cool",
                    params=p)
            if "ERROR" in response.__dict__['_content']:
                return jsonify(result="Error", message=response.__dict__['_content'])

        if self.verify_temp(targetMinTemp, targetMaxTemp):
            return True
        else:
            return jsonify(result="Error", message="Switching temp of " + str(self.id) + " has timed out")

    def verify_state(self, targetState):
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        for i in range(500):
            p = {'DeviceNum': self.controllerId, 'rand': random.random()}
            if auth_user is not None and auth_key is not None:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p,
                    auth=HTTPDigestAuth(auth_user, auth_key))
            else:
                response = requests.get(
                    "http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                    params=p)
            states = json.loads(response.__dict__['_content'])['Device_Num_' + str(self.controllerId)]['states']

            for state in states:
                if state["variable"] == "OccupancyState":
                    if state["value"] == "Occupied":
                        self.state = "1"
                    elif state["value"] == "Unoccupied":
                        self.state = "0"

            if targetState == "Occupied":
                if self.state == "1":
                    return True
                else:
                    time.sleep(0.3)
            elif targetState == "Unoccupied":
                if self.state == "0":
                    return True
                else:
                    time.sleep(0.3)

        return False

    def set_state(self, targetState, serviceName):
        # set state
        connection_config = vera_config.get_vera_config()
        auth_user = connection_config['vera_auth_user']
        auth_key = connection_config['vera_auth_password']
        vera_ip = connection_config['vera_ip']
        p = {'serviceId': serviceName, 'DeviceNum': self.controllerId, 'NewOccupancyState': targetState,
             'rand': random.random()}
        if auth_user is not None and auth_key is not None:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetOccupancyState",
                params=p,
                auth=HTTPDigestAuth(auth_user, auth_key))
        else:
            response = requests.get(
                "http://" + vera_ip + "/port_3480/data_request?id=lu_action&output_format=json&action=SetOccupancyState",
                params=p)
        # return response
        if "ERROR" not in response.__dict__['_content']:
            if self.verify_state(targetState):
                return True
            else:
                return jsonify(result="Error", message="Switching state of " + str(self.id) + " has timed out")
        else:
            return jsonify(result="Error", message=response.__dict__['_content'])
