#!/usr/bin/env python3

# MIT License
#
# Copyright (c) 2021 Oliver Tscherwitschke
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import sys
import serial

import io
import re
import time
from datetime import timedelta
import threading

from sml import *
import paho.mqtt.client as mqtt
import json


def pow10(a, e):
    """ Calculate a to the power of e. e must be an integer. """
    e = int(e)
    if (e < 0):
        for i in range(-e):
            a /= 10
    else:
        for i in range(e):
            a *= 10

    return a


######################################################################
class SmartMeterThread:
    def __init__(self):
        self.running = True
        self.energy_consumption_Wh = 0.0
        self.energy_supply_Wh = 0.0
        self.power_W = 0

    def run(self):
        print('Init start')
        sml = Sml()

        tty = serial.Serial(
            port=serial_port,
            baudrate=9600,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS
        )
        print('\nInit done')

        while self.running:
            byte = tty.read()
            if sml.parse_byte(byte) == True:
                # print()
                # pprint(sml.sml_file, indent=2, width=120)
                messages = [
                    x for x in sml.sml_file if 'GetListResponse' in x['messageBody']]
                for msg in messages:
                    for val in msg['messageBody']['GetListResponse']['valList']:
                        # Wirkarbeit Bezug (+)
                        if val['objName'] == b'\x01\x00\x01\x08\x00\xff':
                            self.energy_consumption_Wh = pow10(
                                val['value'], val['scaler'])

                        # Wirkarbeit Lieferung (-)
                        elif val['objName'] == b'\x01\x00\x02\x08\x00\xff':
                            self.energy_supply_Wh = pow10(
                                val['value'], val['scaler'])

                        # momentane Wirkleistung (+/-)
                        elif val['objName'] == b'\x01\x00\x10\x07\x00\xff':
                            self.power_W = pow10(val['value'], val['scaler'])

                data = {'import': self.energy_consumption_Wh,
                        'export': self.energy_supply_Wh, 'power': self.power_W}
                mqtt_client.publish("devices/smartmeter/import", json.dumps(self.energy_consumption_Wh))
                mqtt_client.publish("devices/smartmeter/export", json.dumps(self.energy_supply_Wh))
                mqtt_client.publish("devices/smartmeter/power", json.dumps(self.power_W))
                # print('Bezug = {:.1f} Wh  Lieferung = {:.1f} Wh  Leistung = {:4d} W'.format(energy_consumption_Wh, energy_supply_Wh, power_W))

    def stop(self):
        self.running = False


if __name__ == '__main__':

    serial_port = '/dev/ttyUSB0'

    if (len(sys.argv) > 1):
        serial_port = sys.argv[1]

    print('Using {:s}'.format(serial_port))

    while True:
        try:
            import paho.mqtt.client as mqtt      # import the client1
            broker_address = "mqtt.fritz.box"
            mqtt_client = mqtt.Client("P1")      # create new instance
            mqtt_client.username_pw_set("mosquitto", "mosquitto")
            mqtt_client.connect(broker_address)  # connect to broker

            smartmeter_thread = SmartMeterThread()
            smartmeter_thread.run()
        except:
            pass
