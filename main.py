#!/usr/bin/python3
"""
Pymodbus Server With Updating Thread
--------------------------------------------------------------------------

This is an example of having a background thread updating the
context while the server is operating. This can also be done with
a python thread::

    from threading import Thread

    thread = Thread(target=updating_writer, args=(context,))
    thread.start()
"""
# --------------------------------------------------------------------------- #
# import the modbus libraries we need
# --------------------------------------------------------------------------- #
from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer, StartSerialServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

# --------------------------------------------------------------------------- #
# import the twisted libraries we need
# --------------------------------------------------------------------------- #
from twisted.internet.task import LoopingCall

# --------------------------------------------------------------------------- #
# configure the service logging
# --------------------------------------------------------------------------- #
import logging


import paho.mqtt.client as mqtt

logging.basicConfig()
log = logging.getLogger("modbus")
log.setLevel(logging.DEBUG)

mqtt_log = logging.getLogger("mqtt")
mqtt_log.setLevel(logging.INFO)

pymodbus_log = logging.getLogger('pymodbus')
pymodbus_log.setLevel(logging.DEBUG)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    mqtt_log.info("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    mqtt_log.debug("received: " + msg.topic + " " + str(msg.payload))
    pass

power = 100

def on_set_power_message(client, userdata, msg: mqtt.MQTTMessage):
    mqtt_log.debug("received: " + msg.topic + " " + str(msg.payload))
    cmd = msg.topic.split("/").pop()
    data = str(msg.payload.decode())

    global power
    power = int(data)
    mqtt_log.info("received power: " + str(power) + " W")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("192.168.2.102", 1883, 60)

client.subscribe("vito_energy/set/+")
client.message_callback_add("vito_energy/set/power", on_set_power_message)


# --------------------------------------------------------------------------- #
# define your callback process
# --------------------------------------------------------------------------- #


def updating_writer(a):
    """ A worker process that runs every so often and
    updates live values of the context. It should be noted
    that there is a race condition for the update.

    :param arguments: The input arguments to the call
    """

    log.debug("updating the context")
    context = a[0]
    register = 3
    slave_id = 0x00
    values = [int(power/10/3)]
    log.debug("new power value: " + str(values[0]) + " * 3 * 10 W")
    context[slave_id].setValues(register, 37, values)
    context[slave_id].setValues(register, 42, values)
    context[slave_id].setValues(register, 47, values)

    client.publish("vito_energy/get/37", values[0])
    client.publish("vito_energy/get/42", values[0])
    client.publish("vito_energy/get/47", values[0])


tab_registers = [0] * 53
tab_registers[0] = 10; #Firmware
tab_registers[37] = 100; #Power Phase 1 (in 10W)
tab_registers[42] = 100; #Power Phase 2 (in 10W)
tab_registers[47] = 100; #Power Phase 3 (in 10W)

def run_updating_server():
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(1, tab_registers))
    context = ModbusServerContext(slaves={ 60: store }, single=False)

    # ----------------------------------------------------------------------- #
    # initialize the server information
    # ----------------------------------------------------------------------- #
    identity = ModbusDeviceIdentification()
    identity.VendorName = 'pymodbus'
    identity.ProductCode = 'PM'
    identity.VendorUrl = 'http://github.com/riptideio/pymodbus/'
    identity.ProductName = 'pymodbus Server'
    identity.ModelName = 'pymodbus Server'
    identity.MajorMinorRevision = version.short()

    # ----------------------------------------------------------------------- #
    # run the server you want
    # ----------------------------------------------------------------------- #
    time = 1  # 5 seconds delay
    #loop = LoopingCall(f=updating_writer, a=(context,))
    #loop.start(time, now=False)  # initially delay by time

    #StartTcpServer(context, identity=identity, address=("localhost", 5020))

    StartSerialServer(context, identity=identity,
                      port='/dev/rs485', framer=ModbusRtuFramer, baudrate=19200, parity='E')


if __name__ == "__main__":
    client.loop_start()
    run_updating_server()
