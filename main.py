from network import LoRa
import socket
import time
import binascii
import pycom
import struct

from pysense import Pysense
from LTR329ALS01 import LTR329ALS01
from LIS2HH12 import LIS2HH12
from SI7006A20 import SI7006A20
from MPL3115A2 import MPL3115A2

# stop LED heartbeat
pycom.heartbeat(False)
pycom.rgbled(0x000000)           # turn off LEDs

# Initialize LoRa in LORAWAN mode.
lora = LoRa(mode=LoRa.LORAWAN)

# create an OTAA authentication parameters
app_eui = binascii.unhexlify('0000000000000001'.replace(' ',''))
app_key = binascii.unhexlify('11B0282A189B75B0B4D2D8C7FA38548E'.replace(' ',''))

# Get the DevEUI from the node
print('DevEUI ', binascii.hexlify(lora.mac()))

py = Pysense()

lt = LTR329ALS01(py)
acc = LIS2HH12(py)
ht = SI7006A20(py)
pa = MPL3115A2(py)

# while True:
#    light = lt.light()
#    pitch = acc.pitch()
#    roll = acc.roll()
#    humidity = ht.humidity()
#    temperature = ht.temperature()
#    pressure = pa.pressure()
#    print("Pitch:\t\t{}\nRoll:\t\t{}".format(pitch,roll))
#    print("Humidity:\t{}\nTemperature:\t{}" .format(humidity, temperature))
#    print("Light visible:\t{}".format(light[0]))
#    print("Light ir:\t{}".format(light[1]))
#    print("Pressure:\t{}\n".format(pressure))
#    ba = bytearray(struct.pack("f",pressure))
#    print("{} {} {} {}".format(ba[0], ba[1], ba[2], ba[3]))
    #print( [ "%d" % b for b in ba ])
#    time.sleep_ms(100)


# Quick Join in the US
for i in range(8, 72):
    print("Remove channel from search: ", i)
    lora.remove_channel(i)


# join a network using OTAA (Over the Air Activation)
lora.join(activation=LoRa.OTAA, auth=(app_eui, app_key), timeout=0)

# wait until the module has joined the network
while not lora.has_joined():
    time.sleep(1.0)
    pycom.rgbled(0x7f0000)           # blink RED led during join
    print('Not yet joined...')
    time.sleep(0.25)
    pycom.rgbled(0x000000)           # turn LED off


# create a LoRa socket
s = socket.socket(socket.AF_LORA, socket.SOCK_RAW)

# selecting confirmed type of messages
s.setsockopt(socket.SOL_LORA, socket.SO_CONFIRMED, True)

# set the LoRaWAN data rate
#s.setsockopt(socket.SOL_LORA, socket.SO_DR, 5)




cnt = 0
pycom.rgbled(0x000000)           # turn off
update_rate_seconds=5;

while True:
    # make the socket blocking
    # (waits for the data to be sent and for the 2 receive windows to expire)


    pycom.rgbled(0x007f00)           # turn on the green LED

    # read the sensors
    light = lt.light()
    pitch = acc.pitch()
    roll = acc.roll()
    humidity = ht.humidity()
    temperature = ht.temperature()
    pressure = pa.pressure()

    # print debug info
    print("Pitch:\t\t{}\nRoll:\t\t{}".format(pitch,roll))
    print("Humidity:\t{}\nTemperature:\t{}" .format(humidity, temperature))
    print("Light visible:\t{}".format(light[0]))
    print("Light ir:\t{}".format(light[1]))
    print("Pressure:\t{}".format(pressure))

    # "H" produces an unsigned short which is two bytes
    light_vis_ba = bytearray(struct.pack("H",int(light[0])))
    light_ir_ba = bytearray(struct.pack("H",int(light[1])))
    pitch_ba = bytearray(struct.pack("H",int(pitch)))
    roll_ba = bytearray(struct.pack("H",int(roll)))
    # "H" produces an unsigigned short, but we only need lower bytearray
    humidity_ba = bytearray(struct.pack("H",int(humidity)))
    # "F" produces a 4 byte float
    temp_ba = bytearray(struct.pack("f",temperature))
    pressure_ba = bytearray(struct.pack("f",pressure))

    try:
        s.setblocking(True)
        # send some data
        s.send(bytes([light_vis_ba[0], light_vis_ba[1], light_ir_ba[0], light_ir_ba[1],pitch_ba[0],
        pitch_ba[1],roll_ba[0],roll_ba[1],humidity_ba[0],humidity_ba[1],
        temp_ba[0],temp_ba[1],temp_ba[2],temp_ba[3],
        pressure_ba[0],pressure_ba[1],pressure_ba[2], pressure_ba[3]]))
        print( "Sending sensor payload {}\n".format(cnt) )

    except Exception as e:
        if e.args[0] == 11:
            print('cannot send just yet, waiting...')
            time.sleep(2.0)
        else:
            raise    # raise the exception again

    pycom.rgbled(0x000000)           # turn on the RED LED

    # make the socket non-blocking
    # (because if there's no data received it will block forever...)
    s.setblocking(False)
    # get any data received (if any...)
    data = s.recv(64)
    if data:
        pycom.rgbled(0x00007f)           # turn on the RED LED
        print( 'Got Packet')
        update_rate_seconds=int(data[1]<<8) + int(data[0]);
        print( "Setting Update Rate: {}".format(update_rate_seconds) )
        time.sleep(0.25)
    else:
        print( 'No Data Received' )
    # saturating add so that count matches uint8 value in payload
    cnt+=1%255
    pycom.rgbled(0x000000)           # turn off LED
    print("Sleep {} seconds".format(update_rate_seconds))
    time.sleep(update_rate_seconds)
