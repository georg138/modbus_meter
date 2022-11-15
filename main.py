#!/usr/bin/python3
from pymodbus.version import version
from pymodbus.server.asynchronous import StartTcpServer, StartSerialServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.transaction import ModbusRtuFramer, ModbusAsciiFramer

from twisted.internet.task import LoopingCall

import paho.mqtt.client as mqtt

import logging


logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

mqtt_log = logging.getLogger("mqtt")
mqtt_log.setLevel(logging.INFO)

pymodbus_log = logging.getLogger('pymodbus')
pymodbus_log.setLevel(logging.DEBUG)

config = {
    "topic": "vito_energy",
    "powerRegisters": [37, 42, 47],
    "mqttAddress": "192.168.2.102",
    "mqttPort": 1883
}

def on_connect(client, userdata, flags, rc):
    mqtt_log.info("Connected with result code "+str(rc))
    topic = config["topic"] + "/set/+"
    client.subscribe(topic)
    mqtt_log.debug(f"Subscribed to {topic}")

def on_message(client, userdata, msg):
    mqtt_log.debug("received: " + msg.topic + " " + str(msg.payload))
    pass

def set_power(context: ModbusSlaveContext, power):
    total = int(power/10)
    values = [int(total/3)]*3
    values[2] = int(total - 2 * values[0])
    log.debug("new power value: " + str(total) + " * 10 W")
    client.publish(config["topic"] + "/get/power", str(total * 10))

    index = 0
    for register in config["powerRegisters"]:
        context.setValues(3, register, [values[index]])
        client.publish(config["topic"] + "/get/register" + str(register), str(values[index]))
        index += 1


def on_set_power_message(client, userdata: ModbusSlaveContext, msg: mqtt.MQTTMessage):
    mqtt_log.debug("received: " + msg.topic + " " + str(msg.payload))
    cmd = msg.topic.split("/").pop()
    data = str(msg.payload.decode())
    power = int(float(data))
    mqtt_log.info("received power: " + str(power) + " W")
    
    set_power(userdata, power)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(config["mqttAddress"], config["mqttPort"], 60)

client.message_callback_add("vito_energy/set/power", on_set_power_message)


def run_updating_server():
    # ----------------------------------------------------------------------- #
    # initialize your data store
    # ----------------------------------------------------------------------- #
    tab_registers = [0] * 53
    tab_registers[0] = 10; #Firmware

    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(1, tab_registers))
    context = ModbusServerContext(slaves={ 60: store }, single=False)

    set_power(store, 0)

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
    client.user_data_set(store)

    StartSerialServer(context, identity=identity,
                      port='/dev/rs485', framer=ModbusRtuFramer, baudrate=19200, parity='E')


if __name__ == "__main__":
    client.loop_start()
    run_updating_server()
