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
from sml import *
from pprint import pprint


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


if __name__ == '__main__':

    serial_port = '/dev/ttyUSB0'

    if (len(sys.argv) > 1):
        serial_port = sys.argv[1]

    print('Using {:s}'.format(serial_port))

    port = serial.Serial(
        port=serial_port,
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS
    )

    sml = Sml()

    energy_consumption_kWh = 0.0
    energy_supply_kWh = 0.0
    power_W = 0

    while True:
        byte = port.read()
        if sml.parse_byte(byte) == True:
            # print()
            # pprint(sml.sml_file, indent=2, width=120)

            messages = [x for x in sml.sml_file if 'GetListResponse' in x['messageBody']]
            for msg in messages:
                for val in msg['messageBody']['GetListResponse']['valList']:
                    if val['objName'] == b'\x01\x00\x01\x08\x00\xff':       # Wirkarbeit Bezug (+)
                        energy_consumption_kWh = pow10(val['value'], val['scaler']) / 1000
                    elif val['objName'] == b'\x01\x00\x02\x08\x00\xff':     # Wirkarbeit Lieferung (-)
                        energy_supply_kWh = pow10(val['value'], val['scaler']) / 1000
                    elif val['objName'] == b'\x01\x00\x10\x07\x00\xff':     # Leistung (+/-)
                        power_W = pow10(val['value'], val['scaler'])

            print('Bezug = {:.3f} kWh  Lieferung = {:.3f} kWh  Leistung = {:4d} W'.format(
                energy_consumption_kWh, energy_supply_kWh, power_W))
