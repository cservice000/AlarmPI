#!/usr/bin/env python

import json
import os
from OpenSSL import SSL

from flask import Flask, send_from_directory, request, Response
from flask_socketio import SocketIO
from functools import wraps
from distutils.util import strtobool

from DoorSensor import DoorSensor

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class myDoorSensor(DoorSensor):
    def updateUI(self, event, data):
        ''' Send changes to the UI '''
        socketio.emit(event, data)


app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)
wd = os.path.dirname(os.path.realpath(__file__))
webDirectory = os.path.join(wd, 'web')
jsonfile = os.path.join(wd, "settings.json")
logfile = os.path.join(wd, "alert.log")
sipcallfile = os.path.join(os.path.join(wd, "voip"), "sipcall")
alarmSensors = myDoorSensor(jsonfile, logfile, sipcallfile)


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not alarmSensors.check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# Start/Stop Application
def shutdownServer():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


def startServer():
    if alarmSensors.getUISettings()['https'] is True:
        context = SSL.Context(SSL.SSLv23_METHOD)
        context.use_privatekey_file('my.cert.key')
        context.use_certificate_file('my.cert.crt')
    else:
        context = None
    socketio.run(app, host="", port=alarmSensors.getPortUI(), ssl_context=context)
    alarmSensors.RefreshAlarmData(None)


@app.route('/restart')
@requires_auth
def restart():
    shutdownServer()
    startServer()
    # python = sys.executable
    # os.execl(python, python, *sys.argv)
    # import subprocess
    # subprocess.Popen(['bash startalarmpi.sh'], shell=True)


# Get the required files for the UI

@app.route('/')
@requires_auth
def index():
    return send_from_directory(webDirectory, 'index.html')


@app.route('/main.css')
def main():
    return send_from_directory(webDirectory, 'main.css')


@app.route('/icon.png')
def icon():
    return send_from_directory(webDirectory, 'icon.png')


@app.route('/mycss.css')
def mycss():
    return send_from_directory(webDirectory, 'mycss.css')


@app.route('/mycssMobile.css')
def mycssMobile():
    return send_from_directory(webDirectory, 'mycssMobile.css')


@app.route('/myjs.js')
def myjs():
    return send_from_directory(webDirectory, 'myjs.js')


@app.route('/jquery.js')
def jqueryfile():
    return send_from_directory(webDirectory, 'jquery.js')


@app.route('/socket.io.js')
def socketiofile():
    return send_from_directory(webDirectory, 'socket.io.js')


# Get the required data from the AlarmPI

@app.route('/alertpins.json')
def alertpinsJson():
    return json.dumps(alarmSensors.getSensorsArmed())


@app.route('/alarmStatus.json')
@requires_auth
def alarmStatus():
    return json.dumps(alarmSensors.getAlarmStatus())


@app.route('/sensorsLog.json', methods=['Get', 'POST'])
@requires_auth
def sensorsLog():
    limit = 10
    if request.args.get('limit').isdigit():
        limit = int(request.args.get('limit'))
    return json.dumps(alarmSensors.getSensorsLog(limit))


@app.route('/serenePin.json')
@requires_auth
def serenePin():
    return json.dumps(alarmSensors.getSerenePin())


@app.route('/getSereneSettings.json')
@requires_auth
def getSereneSettings():
    return json.dumps(alarmSensors.getSereneSettings())


@app.route('/getMailSettings.json')
@requires_auth
def getMailSettings():
    return json.dumps(alarmSensors.getMailSettings())


@app.route('/getVoipSettings.json')
@requires_auth
def getVoipSettings():
    return json.dumps(alarmSensors.getVoipSettings())


@app.route('/getUISettings.json')
@requires_auth
def getUISettings():
    return json.dumps(alarmSensors.getUISettings())


# Change settings to the AlarmPI

@app.route('/activateAlarmOnline')
@requires_auth
def activateAlarmOnline():
    alarmSensors.activateAlarm()
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@app.route('/deactivateAlarmOnline')
@requires_auth
def deactivateAlarmOnline():
    alarmSensors.deactivateAlarm()
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@app.route('/setSensorStateOnline', methods=['GET', 'POST'])
@requires_auth
def setSensorStateOnline():
    message = request.args.get('hello')
    message = {
        "pin": int(request.args.get('pin')),
        "active": strtobool(request.args.get('active').lower())
    }
    message['active'] = True if message['active'] else False
    print message
    alarmSensors.setSensorState(message['pin'], message['active'])
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setSerenePin')
@requires_auth
def setSerenePin(message):
    alarmSensors.setSerenePin(int(message['pin']))
    socketio.emit('pinsChanged')


@socketio.on('setSensorState')
@requires_auth
def setSensorState(message):
    alarmSensors.setSensorState(message['pin'], message['active'])
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setSensorName')
@requires_auth
def setSensorName(message):
    alarmSensors.setSensorName(message['pin'], message['name'])
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setSensorPin')
@requires_auth
def setSensorPin(message):
    alarmSensors.setSensorPin(int(message['pin']), int(message['newpin']))
    socketio.emit('pinsChanged')


@socketio.on('activateAlarm')
@requires_auth
def activateAlarm():
    alarmSensors.activateAlarm()
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('deactivateAlarm')
@requires_auth
def deactivateAlarm():
    alarmSensors.deactivateAlarm()
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('addSensor')
@requires_auth
def addSensor(message):
    alarmSensors.addSensor(int(message['pin']), message['name'], message['active'])
    socketio.emit('pinsChanged')


@socketio.on('delSensor')
@requires_auth
def delSensor(message):
    alarmSensors.delSensor(int(message['pin']))
    socketio.emit('pinsChanged')


@socketio.on('setSereneSettings')
@requires_auth
def setSereneSettings(message):
    alarmSensors.setSereneSettings(message)
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setMailSettings')
@requires_auth
def setMailSettings(message):
    alarmSensors.setMailSettings(message)
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setVoipSettings')
@requires_auth
def setVoipSettings(message):
    alarmSensors.setVoipSettings(message)
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


@socketio.on('setUISettings')
@requires_auth
def setUISettings(message):
    alarmSensors.setUISettings(message)
    socketio.emit('settingsChanged', alarmSensors.getSensorsArmed())


# Run
if __name__ == '__main__':
    startServer()