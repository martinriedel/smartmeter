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

class SmlException(Exception):
    """ SML Communication problem. """


# ---------------------------------------------------------------------
class Sml:
    """ Class for Smart Message Language (SML) parsing. """

    key_names = {
        'messageId': {257: 'OpenResponse', 513: 'CloseResponse', 1793: 'GetListResponse'},
        'timeId': {1: 'secIndex', 2: 'timestamp', 3: 'localTimestamp'}
    }

    sml_struct = {
        'smlFile':         {'type': 'list',   'name': 'smlMessage'},
        'smlMessage':      {'type': 'struct', 'name': ['transactionId', 'groupNo', 'abortOnError', 'messageBody', 'crc16', 'endOfSmlMsg']},
        'messageBody':     {'type': 'struct', 'name': ['messageId', '[messageId]']},
        'message':         {'type': 'list',   'name': 'message'},

        'OpenResponse':    {'type': 'struct', 'name': ['codepage', 'clientId', 'reqFileId', 'serverId', 'refTime', 'smlVersion']},
        'refTime':         {'type': 'struct', 'name': ['timeId', '[timeId]']},

        'CloseResponse':   {'type': 'struct', 'name': ['globalSignature']},

        'GetListResponse': {'type': 'struct', 'name': ['clientId', 'serverId', 'listName', 'actSensorTime', 'valList', 'listSignature', 'actGatewayTime']},
        'actSensorTime':   {'type': 'struct', 'name': ['timeId', '[timeId]']},
        'actGatewayTime':  {'type': 'struct', 'name': ['timeId', '[timeId]']},
        'valList':         {'type': 'list',   'name': 'val'},
        'val':             {'type': 'struct', 'name': ['objName', 'status', 'valTime', 'unit', 'scaler', 'value', 'valueSignature']},
        'valTime':         {'type': 'struct', 'name': ['timeId', '[timeId]']},

        'secIndex':        {'type': 'struct', 'name': ['secIndex']},
        'timestamp':       {'type': 'struct', 'name': ['timestamp']},
        'localTimestamp':  {'type': 'struct', 'name': ['timestamp', 'localOffset', 'seasonTimeOffset']},
    }

    def __init__(self):
        self.sml_file = []
        self.data = bytearray()

        self.esc_sequence = False
        self.esc_count = 0
        self.message_started = False

        self.crc_table = []
        self.crc_init()

    def crc_slow(self, data):
        """ Calculate CCITT-CRC16 checksum bit by bit (this is the reference). """
        polynom = 0x8408     # CCITT Polynom reflected
        crcsum = 0xFFFF

        for byte in data:
            crcsum ^= byte
            for bit in range(8):  # for all 8 bits
                if crcsum & 0x01:
                    crcsum = (crcsum >> 1) ^ polynom
                else:
                    crcsum >>= 1

        return crcsum ^ 0xFFFF

    def crc_init(self):
        """ Init the crc look-up table for byte-wise crc calculation. """
        polynom = 0x8408     # CCITT Polynom reflected
        self.crc_table = []

        for byte in range(256):
            crcsum = byte
            for bit in range(8):  # for all 8 bits
                if crcsum & 0x01:
                    crcsum = (crcsum >> 1) ^ polynom
                else:
                    crcsum >>= 1
            self.crc_table.append(crcsum)

    def crc(self, data):
        """ Calculate CCITT-CRC16 checksum byte by byte. """
        crcsum = 0xFFFF

        for byte in data:
            idx = byte ^ (crcsum & 0xFF)
            crcsum = self.crc_table[idx] ^ (crcsum >> 8)

        return crcsum ^ 0xFFFF

    def parse_byte(self, byte):
        """ 
        Receive and store one byte until a complete message is in 'self.data' and then parse it.
        Return True if message is complete. Store the parsed message in self.sml_file.
        """
        self.data.extend(byte)

        if not self.esc_sequence:
            if byte == b'\x1b':
                self.esc_count += 1
                if self.esc_count == 4:
                    self.esc_sequence = True
            else:
                self.esc_count = 0
        else:
            self.esc_count -= 1
            if self.esc_count == 0:
                self.esc_sequence = False
                esc = self.data[-4:]
                if esc == b'\x1b\x1b\x1b\x1b':      # Escape sequence itself is escaped
                    pass

                elif esc == b'\x01\x01\x01\x01':    # Starts version 1 'Begin of message'
                    if self.message_started:
                        print('WARN: nested START detected')
                    self.message_started = True
                    # Remove everything in front of START
                    del self.data[:-8]

                elif esc[0:1] == b'\x02':           # Starts version 2 with block transfer
                    print('INFO: Start of block transfer')
                elif esc[0:1] == b'\x03':           # Timeout for version 2
                    pass
                elif esc[0:1] == b'\x04':           # Block size for version 2
                    pass

                elif esc[0:1] == b'\x1a':           # End of message
                    message_started_prev = self.message_started
                    self.message_started = False
                    if message_started_prev:
                        padding_bytes = esc[1]
                        crc_msg = int(esc[:-3:-1].hex(), 16)
                        crc = self.crc(self.data[:-2])
                        if crc == crc_msg:
                            # remove start
                            del self.data[:8]
                            # remove end and padding bytes
                            del self.data[-(8 + padding_bytes):]
                            # print(self.data.hex())
                            try:
                                self.sml_file = self.parse()   # Parse w/o start, padding and end identifier
                            except SmlException as e:
                                print(e)

                            return True
                        else:
                            self.data = bytearray()
                            print('WARN: bad CRC')

        return False

    def pop_data(self, len):
        """ Return and remove the first 'len' bytes from self.data. """
        data = self.data[:len]
        del self.data[:len]
        return data

    def parse(self, struct='smlFile', elements=-1):
        """ Parse SML data. """

        sml_list = []
        sml_dict = {}

        while len(self.data) and elements != 0:
            #print('struct:', struct, 'elements:', elements)
            if self.sml_struct[struct]['type'] == 'list':
                etyp = 'list'
                elem = self.sml_struct[struct]['name']
            elif self.sml_struct[struct]['type'] == 'struct':
                etyp = 'struct'
                l = len(self.sml_struct[struct]['name'])
                elem = self.sml_struct[struct]['name'][l - elements]
                ob = elem.find('[')
                cb = elem.find(']')
                if ob != -1:
                    key = elem[ob+1:cb]
                    try:
                        key_str = self.key_names[key][sml_dict[key]]
                    except:
                        elem = key[:-2]
                    else:
                        #print('key: ', key)
                        #print('= ', sml_dict[key])
                        elem_new = elem[:ob] + key_str

                        #print('elem_new: ', elem_new)
                        if elem_new in self.sml_struct:
                            elem = elem_new
                        else:
                            #elem = elem[:ob]
                            elem = key[:-2]

            else:
                raise SmlException('Unknown element type')

            #print('elem:', elem)

            # Read Type-Length-Field
            tl = self.pop_data(1)[0]
            tl_typ = tl & 0x70
            tl_len = tl & 0x0F
            tl_bytes = 1                    # length of the Type-Length-Field itself

            while tl & 0x80:                # another tl-byte follows
                tl = self.pop_data(1)[0]
                tl_bytes += 1
                if (tl & 0x70) == 0:        # another 4 bits for length
                    tl_len = (tl_len << 4) + (tl & 0x0F)

            #print('tl:{:02X}  typ:{:02X}  len:{:02X}'.format(tl, tl_typ, tl_len))
            data_len = tl_len - tl_bytes

            if tl_typ == 0x00:              # octet string
                if data_len == 0:
                    val = None              # optional and not present value
                elif tl == 0:
                    val = b'\x00'           # endOfMessage
                else:
                    val = self.pop_data(data_len)

                if etyp == 'list':
                    sml_list.append(val)
                elif etyp == 'struct':
                    sml_dict[elem] = val
                elements -= 1

            elif tl_typ == 0x40:            # boolean
                val = bool.from_bytes(self.pop_data(data_len), byteorder='big')
                if etyp == 'list':
                    sml_list.append(val)
                elif etyp == 'struct':
                    sml_dict[elem] = val
                elements -= 1

            elif tl_typ == 0x50:            # integer
                val = int.from_bytes(self.pop_data(
                    data_len), byteorder='big', signed=True)
                if etyp == 'list':
                    sml_list.append(val)
                elif etyp == 'struct':
                    sml_dict[elem] = val
                elements -= 1

            elif tl_typ == 0x60:            # unsigned
                val = int.from_bytes(self.pop_data(
                    data_len), byteorder='big', signed=False)
                if etyp == 'list':
                    sml_list.append(val)
                elif etyp == 'struct':
                    sml_dict[elem] = val
                elements -= 1

            elif tl_typ == 0x70:            # list of ...
                if etyp == 'list':
                    sml_list.append(self.parse(elem, tl_len))
                elif etyp == 'struct':
                    sml_dict[elem] = self.parse(elem, tl_len)
                elements -= 1

            else:                           # unknown or reserved value, just consume the data bytes
                self.data = self.data[data_len:]
                print(
                    'WARN: unknown or reserved Type-Length-Field: 0x{:02X}'.format(tl))

        if etyp == 'list':
            return sml_list
        elif etyp == 'struct':
            return sml_dict
