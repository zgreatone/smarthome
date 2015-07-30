from flask import *
from flask.json import JSONEncoder
from device import *
from scene import *
from requests.auth import HTTPDigestAuth
import requests
import random
import simplejson as json
import os
import time
import redis

redis = redis.Redis("localhost")

import vera_config


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, Device):
                device_dict = obj.__dict__
                device_dict['_type'] = obj.__class__.__name__
                return device_dict
            elif isinstance(obj, Scene):
                scene_dict = obj.__dict__
                scene_dict['_type'] = obj.__class__.__name__
                return scene_dict
            iterable = iter(obj)
        except TypeError:
            print(type(obj))
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


def device_decoder(dct):
    if '_type' in dct:
        if dct['_type'] == "Light":
            # Is this the right way to do this? I don't use the Lock or Nest functions so this does not get called in my installation.
            return Light(dct["id"], dct["name"], dct["room"], dct["state"], dct["brightness"])
        elif dct['_type'] == "Lock":
            return Lock(dct["id"], dct["name"], dct["room"], dct["state"])
        elif dct['_type'] == "Nest":
            return Nest(dct["id"], dct["name"], dct["room"], dct["currentTemp"], dct["maxTemp"], dct["minTemp"],
                        dct["controllerId"], dct["state"])
    return dct


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder

global lights
lights = {}

global scenes
scenes = {}

global locks
locks = {}

global nests
nests = {}

global motion_sensors
motion_sensors = {}

global verdeDevices
verdeDevices = {}

global smarthomeState
smarthomeState = "smarthome_state_"


@app.route("/")
def hello():
    return "Hello World!"


@app.route("/motion_senors", methods=['GET'])
def list_motion_sensors():
    retrieve_motion_sensor_data()
    return jsonify(**motion_sensors)


def retrieve_motion_sensor_data():
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    p = {'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p)

    response_content = json.loads(response.__dict__['_content'])
    devices = response_content['devices']
    rooms = response_content['rooms']
    available_scenes = response_content['scenes']
    room_names = {}
    for room in rooms:
        if room["id"] not in room_names:
            room_names[room["id"]] = room["name"]
    for scene in available_scenes:
        # add scene to dictionary (except it doesn't seem to really work like a dictionary)
        scenes[str(scene["id"])] = Scene(str(str(scene["id"])), scene["name"])
        # uncomment the below to have your scenes printed to stdout because of the problem with listScenes()
        # print vars(scenes[str(scene["id"])])
    for device in devices:
        if "device_type" in device:
            if "MotionSensor" in device["device_type"]:
                # get room name
                if int(device["room"]) not in room_names:
                    room_name = "Room not found"
                else:
                    room_name = room_names[int(device["room"])]

                # get device state
                configured = None
                capabilities = None
                armed = None
                motion = False
                for state in device["states"]:
                    if state["variable"] == "Armed":
                        device_state = state["value"]
                        armed = state["value"]
                    if state["variable"] == "Capabilities":
                        capabilities = state["value"]
                    if state["variable"] == "Configured":
                        configured = state["value"]
                    if state["variable"] == "SensorMlType":
                        if state["value"] == "1,3,5":
                            motion = True

                # add motion sensor to dictionary
                if motion:
                    motion_sensors[device["id"]] = MotionSensor(device["id"], device["name"], room_name, device_state,
                                                                configured, capabilities, armed)
    return motion_sensors


@app.route("/lights", methods=['GET'])
def list_lights():
    retrieve_light_data()
    return jsonify(**lights)


def retrieve_light_data():
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    p = {'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p)

    responseContent = json.loads(response.__dict__['_content'])
    devices = responseContent['devices']
    rooms = responseContent['rooms']
    availableScenes = responseContent['scenes']
    roomNames = {}
    for room in rooms:
        if room["id"] not in roomNames:
            roomNames[room["id"]] = room["name"]
    for scene in availableScenes:
        # add scene to dictionary (except it doesn't seem to really work like a dictionary)
        scenes[str(scene["id"])] = Scene(str(str(scene["id"])), scene["name"])
        # uncomment the below to have your scenes printed to stdout because of the problem with listScenes()
        # print vars(scenes[str(scene["id"])])
    for device in devices:
        if "device_type" in device:
            if ("Light" in device["device_type"] or "WeMoControllee" in device["device_type"]) and "Sensor" not in \
                    device["device_type"]:
                # get room name
                if int(device["room"]) not in roomNames:
                    roomName = "Room not found"
                else:
                    roomName = roomNames[int(device["room"])]

                # get device state
                brightness = None
                for state in device["states"]:
                    if state["variable"] == "Status":
                        deviceState = state["value"]
                    if state["variable"] == "LoadLevelStatus":
                        brightness = state["value"]

                # add light to dictionary
                lights[device["id"]] = Light(device["id"], device["name"], roomName, deviceState, brightness)
    return lights


def retrieve_scene_data():
    if scenes == {}:
        retrieve_light_data()

    return scenes


def retrieve_room_data():
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    p = {'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p)

    responseContent = json.loads(response.__dict__['_content'])
    rooms = responseContent['rooms']
    return rooms


@app.route("/scenes", methods=['GET'])
def list_scenes():
    retrieve_scene_data()
    # this function does not work because scenes is not JSON serializable. I could not figure out what to do about it
    return jsonify(**scenes)


@app.route("/motion_sensor/<int:id>", methods=['GET'])
def get_motion_sensor(id):
    get_motion_sensor_info(id)

    return jsonify(**motion_sensors[str(id)].__dict__)


def get_motion_sensor_info(id):
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    if motion_sensors == {}:
        list_motion_sensors()
    p = {'DeviceNum': id, 'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p)
    states = json.loads(response.__dict__['_content'])['Device_Num_' + str(id)]['states']
    for state in states:
        if state["variable"] == "Armed":
            motion_sensors[str(id)].update_state(state["value"])

    return motion_sensors[str(id)].__dict__


@app.route("/motion_sensor/<int:id>", methods=['PUT'])
def put_motion_sensor(id):
    if motion_sensors == {}:
        list_motion_sensors()

    # check inputs
    if str(id) not in motion_sensors:
        return jsonify(result="Error", message="not a motion sensor")

    if "state" not in request.get_json():
        return jsonify(result="Error", message="State not specified")

    change = motion_sensors[str(id)].set_state(request.get_json()['state'],
                                               "urn:micasaverde-com:serviceId:SecuritySensor1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK", state=request.get_json()['state'])


@app.route("/motion_sensor/armed/<int:id>", methods=['PUT'])
def put_motion_sensor_armed_state(id):
    if motion_sensors == {}:
        list_motion_sensors()

    # check inputs
    if str(id) not in motion_sensors:
        return jsonify(result="Error", message="not a motion sensor")

    if lights[str(id)].brightness is None:
        return jsonify(result="Error", message="Does not have brightness")

    if "brightness" not in request.get_json():
        return jsonify(result="Error", message="Brightness not specified")

    change = motion_sensors[str(id)].set_brightness(request.get_json()['armed'],
                                                    "urn:micasaverde-com:serviceId:SecuritySensor1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK", state=request.get_json()['brightness'])


@app.route("/lights/<int:id>", methods=['GET'])
def get_light(id):
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']

    if lights == {}:
        list_lights()
    p = {'DeviceNum': id, 'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p)
    states = json.loads(response.__dict__['_content'])['Device_Num_' + str(id)]['states']

    for state in states:
        if state["variable"] == "Status":
            lights[str(id)].update_state(state["value"])

    return jsonify(**lights[str(id)].__dict__)


@app.route("/lights/<int:id>", methods=['PUT'])
def put_light(id):
    if lights == {}:
        list_lights()

    # check inputs
    if str(id) not in lights:
        return jsonify(result="Error", message="Not a light")

    if "state" not in request.get_json():
        return jsonify(result="Error", message="State not specified")

    change = lights[str(id)].set_state(request.get_json()['state'], "urn:upnp-org:serviceId:SwitchPower1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK", state=request.get_json()['state'])


@app.route("/lights/brightness/<int:id>", methods=['PUT'])
def put_light_brightness(id):
    if lights == {}:
        list_lights()

    # check inputs
    if str(id) not in lights:
        return jsonify(result="Error", message="Not a light")

    if lights[str(id)].brightness is None:
        return jsonify(result="Error", message="Does not have brightness")

    if "brightness" not in request.get_json():
        return jsonify(result="Error", message="Brightness not specified")

    change = lights[str(id)].set_brightness(request.get_json()['brightness'], "urn:upnp-org:serviceId:Dimming1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK", state=request.get_json()['brightness'])


@app.route("/scenes/<int:id>", methods=['PUT'])
def put_scene(id):
    if scenes == {}:
        list_lights()

    # check inputs
    if str(id) not in scenes:
        return jsonify(result="Error", message="Not a scene")

    change = scenes[str(id)].activate("urn:micasaverde-com:serviceId:HomeAutomationGateway1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK")


@app.route("/locks", methods=['GET'])
def list_locks():
    retrieve_lock_data()

    return jsonify(**locks)


def retrieve_lock_data():
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    p = {'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p)
    responseContent = json.loads(response.__dict__['_content'])
    devices = responseContent['devices']
    rooms = responseContent['rooms']
    roomNames = {}
    for room in rooms:
        if room["id"] not in roomNames:
            roomNames[room["id"]] = room["name"]
    for device in devices:
        if "device_type" in device:
            if "DoorLock" in device["device_type"]:
                # get room name
                if int(device["room"]) not in roomNames:
                    roomName = "Room not found"
                else:
                    roomName = roomNames[int(device["room"])]

                # get device state
                for state in device["states"]:
                    if state["variable"] == "Status" and "DoorLock" in state["service"]:
                        deviceState = state["value"]

                # add lock to dictionary
                locks[device["id"]] = Lock(device["id"], device["name"], roomName, deviceState)
    return locks


@app.route("/locks/<int:id>", methods=['GET'])
def get_lock(id):
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    if locks == {}:
        list_locks()

    p = {'DeviceNum': id, 'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p)
    states = json.loads(response.__dict__['_content'])['Device_Num_' + str(id)]['states']

    for state in states:
        if state["variable"] == "Status" and "DoorLock" in state["service"]:
            locks[str(id)].update_state(state["value"])

    return jsonify(**locks[str(id)].__dict__)


@app.route("/locks/<int:id>", methods=['PUT'])
def put_lock(id):
    # check inputs
    if str(id) not in locks:
        return jsonify(result="Error", message="Not a lock")

    if "state" not in request.get_json():
        return jsonify(result="Error", message="State not specified")

    if "password" not in request.get_json():
        return jsonify(result="Error", message="Password not specified")

    if request.get_json()['password'] != os.environ['LOCKSECRET']:
        return jsonify(result="Error", message="Wrong password")

    change = locks[str(id)].set_state(request.get_json()['state'], "urn:micasaverde-com:serviceId:DoorLock1")

    if change is not True:
        return change
    else:
        return jsonify(result="OK", state=request.get_json()['state'])


@app.route("/nests", methods=['GET'])
def list_nests():
    retrieve_nest_data()

    return jsonify(**nests)


def retrieve_nest_data():
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    p = {'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=user_data",
                                params=p)
    responseContent = json.loads(response.__dict__['_content'])
    devices = responseContent['devices']
    rooms = responseContent['rooms']
    roomNames = {}
    for room in rooms:
        if room["id"] not in roomNames:
            roomNames[room["id"]] = room["name"]
    for device in devices:
        if "device_type" in device:
            if "HVAC" in device["device_type"] or "NestStructure" in device["device_type"]:
                if "HVAC" in device["device_type"]:
                    deviceId = device["id"]
                    deviceName = device["name"]
                    # get room name
                    if int(device["room"]) not in roomNames:
                        roomName = "Room not found"
                    else:
                        roomName = roomNames[int(device["room"])]

                    # get device state
                    for state in device["states"]:
                        if state["variable"] == "CurrentTemperature":
                            currentTemperature = state["value"]
                        if "TemperatureSetpoint1_Cool" in state["service"] and state["variable"] == "CurrentSetpoint":
                            maxTemp = state["value"]
                        if "TemperatureSetpoint1_Heat" in state["service"] and state["variable"] == "CurrentSetpoint":
                            minTemp = state["value"]

                else:
                    # get home/ away mode and id of controller
                    if "NestStructure" in device["device_type"]:
                        controllerId = device["id"]
                        for state in device["states"]:
                            if state["variable"] == "OccupancyState":
                                if state["value"] == "Occupied":
                                    deviceState = "1"
                                elif state["value"] == "Unoccupied":
                                    deviceState = "0"

    # add nest to dictionary
    if deviceId is not None and controllerId is not None:
        nests[deviceId] = Nest(deviceId, deviceName, roomName, currentTemperature, maxTemp, minTemp, controllerId,
                               deviceState)
    else:
        raise Exception('Problem with Nest API')

    return nests


@app.route("/nests/<int:id>", methods=['GET'])
def get_nest(id):
    connection_config = vera_config.get_vera_config()
    auth_user = connection_config['vera_auth_user']
    auth_key = connection_config['vera_auth_password']
    vera_ip = connection_config['vera_ip']
    if nests == {}:
        list_nests()

    p = {'DeviceNum': id, 'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p)
    states = json.loads(response.__dict__['_content'])['Device_Num_' + str(id)]['states']

    for state in states:
        if state["variable"] == "CurrentTemperature":
            nests[str(id)].update_current_temp(state["value"])
        if "TemperatureSetpoint1_Cool" in state["service"] and state["variable"] == "CurrentSetpoint":
            nests[str(id)].update_max_temp(state["value"])
        if "TemperatureSetpoint1_Heat" in state["service"] and state["variable"] == "CurrentSetpoint":
            nests[str(id)].update_min_temp(state["value"])

    # get state for controller
    controllerId = nests[str(id)].get_controller_id()

    p = {'DeviceNum': controllerId, 'rand': random.random()}
    if auth_user is not None and auth_key is not None:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p,
                                auth=HTTPDigestAuth(auth_user, auth_key))
    else:
        response = requests.get("http://" + vera_ip + "/port_3480/data_request?id=status&output_format=json",
                                params=p)
    controllerStates = json.loads(response.__dict__['_content'])['Device_Num_' + str(controllerId)]['states']
    for state in controllerStates:
        if state["variable"] == "OccupancyState":
            if state["value"] == "Occupied":
                nests[str(id)].update_state("1")
            elif state["value"] == "Unoccupied":
                nests[str(id)].update_state("0")

    return jsonify(**nests[str(id)].__dict__)


@app.route("/nests/<int:id>", methods=['PUT'])
def put_nest(id):
    # check inputs
    if str(id) not in nests:
        return jsonify(result="Error", message="Not a Nest")

    if "maxTemp" not in request.get_json() and "minTemp" not in request.get_json() and "state" not in request.get_json():
        return jsonify(result="Error", message="No change specified")

    if "maxTemp" in request.get_json() and "minTemp" in request.get_json():
        if request.get_json()['maxTemp'] < request.get_json()['minTemp']:
            return jsonify(result="Error", message="Max temp cannot be lower than min temp")

    if "password" not in request.get_json():
        return jsonify(result="Error", message="Password not specified")

    if request.get_json()['password'] != os.environ['LOCKSECRET']:
        return jsonify(result="Error", message="Wrong password")

    # make the changes
    if "minTemp" in request.get_json() and "maxTemp" in request.get_json():
        change = nests[str(id)].set_temp(request.get_json()['minTemp'], request.get_json()['maxTemp'])
        if change is not True:
            return change
    elif "minTemp" in request.get_json() and "maxTemp" not in request.get_json():
        change = nests[str(id)].set_temp(request.get_json()['minTemp'], nests[str(id)].get_max_temp())
        if change is not True:
            return change
    elif "minTemp" not in request.get_json() and "maxTemp" in request.get_json():
        change = nests[str(id)].set_temp(nests[str(id)].get_min_temp(), request.get_json()['maxTemp'])
        if change is not True:
            return change

    if "state" in request.get_json():
        if request.get_json()['state'] == "0":
            change = nests[str(id)].set_state("Unoccupied", "urn:upnp-org:serviceId:HouseStatus1")
        elif request.get_json()['state'] == "1":
            change = nests[str(id)].set_state("Occupied", "urn:upnp-org:serviceId:HouseStatus1")
        if change is not True:
            return change

    return jsonify(result="OK", message="All changes made")


@app.route("/states", methods=['GET'])
def list_states():
    keys = redis.keys(smarthomeState + "*")
    result = []
    for key in keys:
        result.append(key[len(smarthomeState):])
    return json.dumps(result)


@app.route("/states/<string:slot>", methods=['GET'])
def get_state(slot):
    slot = smarthomeState + slot
    return jsonify(json.loads(redis.get(slot), object_hook=device_decoder))


@app.route("/states/<string:slot>", methods=['PUT'])
def save_current_state(slot):
    slot = smarthomeState + slot
    if "password" not in request.get_json():
        return jsonify(result="Error", message="Password not specified")

    if request.get_json()['password'] != os.environ['LOCKSECRET']:
        return jsonify(result="Error", message="Wrong password")

    list_lights()
    list_locks()
    list_nests()

    for light in lights:
        verdeDevices[light] = lights[light]
    for lock in locks:
        verdeDevices[lock] = locks[lock]
    for nest in nests:
        verdeDevices[nest] = nests[nest]

    redis.set(slot, json.dumps(verdeDevices, cls=CustomJSONEncoder))

    return jsonify(result="OK", message=slot + " state saved")


@app.route("/states/load/<string:slot>", methods=['PUT'])
def load_state(slot):
    slot = smarthomeState + slot
    if "password" not in request.get_json():
        return jsonify(result="Error", message="Password not specified")

    if request.get_json()['password'] != os.environ['LOCKSECRET']:
        return jsonify(result="Error", message="Wrong password")

    list_lights()
    list_locks()
    list_nests()

    savedStates = json.loads(redis.get(slot), object_hook=device_decoder)

    for savedState in savedStates:
        if isinstance(savedStates[savedState], Light):
            if savedStates[savedState].get_state() != lights[savedStates[savedState].get_id()].get_state():
                change = lights[savedStates[savedState].get_id()].set_state(savedStates[savedState].get_state(),
                                                                            "urn:upnp-org:serviceId:SwitchPower1")
                if change is not True:
                    return change
        elif isinstance(savedStates[savedState], Lock):
            if savedStates[savedState].get_state() != locks[savedStates[savedState].get_id()].get_state():
                change = locks[savedStates[savedState].get_id()].set_state(savedStates[savedState].get_state(),
                                                                           "urn:micasaverde-com:serviceId:DoorLock1")
                if change is not True:
                    return change
        elif isinstance(savedStates[savedState], Nest):
            if savedStates[savedState].get_min_temp() != nests[savedStates[savedState].get_id()].get_min_temp() or \
                            savedStates[savedState].get_max_temp() != nests[
                        savedStates[savedState].get_id()].get_max_temp():
                change = nests[savedStates[savedState].get_id()].set_temp(savedStates[savedState].get_min_temp(),
                                                                          savedStates[savedState].get_max_temp())
                if change is not True:
                    return change
            if savedStates[savedState].get_state() != nests[savedStates[savedState].get_id()].get_state():
                if savedStates[savedState].get_state() == "0":
                    change = nests[savedStates[savedState].get_id()].set_state("Unoccupied",
                                                                               "urn:upnp-org:serviceId:HouseStatus1")
                    if change is not True:
                        return change
                elif savedStates[savedState].get_state() == "1":
                    change = nests[savedStates[savedState].get_id()].set_state("Occupied",
                                                                               "urn:upnp-org:serviceId:HouseStatus1")
                    if change is not True:
                        return change

    return jsonify(result="OK", message="All states restored")

# gunicorn stuff here
from werkzeug.contrib.fixers import ProxyFix

app.wsgi_app = ProxyFix(app.wsgi_app)
app.config.from_pyfile('config.py')

import logging
from logging.handlers import RotatingFileHandler

file_handler = RotatingFileHandler('flask.log', maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
