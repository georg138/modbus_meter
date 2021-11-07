#!/usr/bin/env python
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
log = logging.getLogger()
log.setLevel(logging.DEBUG)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))
    pass

power = 0

def on_set_power_message(client, userdata, msg: mqtt.MQTTMessage):
    cmd = msg.topic.split("/").pop()
    data = str(msg.payload.decode())

    global power
    power = int(data)

    print(msg.topic+" "+str(msg.payload))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("mqtt", 1883, 60)

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
    log.debug("new values: " + str(values))
    context[slave_id].setValues(register, 37, values)
    context[slave_id].setValues(register, 42, values)
    context[slave_id].setValues(register, 47, values)

    client.publish("vito_energy/get/37", values[0])
    client.publish("vito_energy/get/42", values[0])
    client.publish("vito_energy/get/47", values[0])


tab_registers = [0] * 48
tab_registers[0] = 10; #Firmware
tab_registers[21] = 0; #Comm ok
tab_registers[24] = 0; #Metering ok
tab_registers[27] = 0; #Counter 1 Total high (in 10 Wh)
tab_registers[28] = 0; #Counter 1 Total low (in 10 Wh)
tab_registers[29] = 0; #Counter 1 Partial high (in 10 Wh)
tab_registers[30] = 0; #Counter 1 Partial low (in 10 Wh)
tab_registers[31] = 0; #Counter 2 Total high (in 10 Wh)
tab_registers[32] = 0; #Counter 2 Total low (in 10 Wh)
tab_registers[33] = 0; #Counter 2 Partial high (in 10 Wh)
tab_registers[34] = 0; #Counter 2 Partial low (in 10 Wh)
tab_registers[37] = 0; #Power Phase 1 (in 10W)
tab_registers[42] = 0; #Power Phase 2 (in 10W)
tab_registers[47] = 0; #Power Phase 3 (in 10W)

def run_updating_server():
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, tab_registers))
    context = ModbusServerContext(slaves=store, single=True)

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
    time = 5  # 5 seconds delay
    loop = LoopingCall(f=updating_writer, a=(context,))
    loop.start(time, now=False)  # initially delay by time

    #StartTcpServer(context, identity=identity, address=("localhost", 5020))

    StartSerialServer(context, identity=identity,
                      port='/dev/ttyp0', framer=ModbusRtuFramer)


if __name__ == "__main__":
    client.loop_start()
    run_updating_server()
