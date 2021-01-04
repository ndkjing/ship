import cv2
import numpy as np

# a = {1:2,2:3}
#
# print(len(a))
#
# print(type(list(a.keys())),1 in a.keys())
# print(type(a.values()),a.values())
#
# print(1 if 1 else 2)

import time
import random
import serial
import com_data
start_time = time.time()

port = 'com8'
baud = 9600
serial_obj = com_data.SerialData(
                        port,
                        baud,
                        timeout=1)

if not serial_obj.uart.isOpen():
    serial_obj.uart.open()
print('%s is open'%(port), serial_obj.uart.isOpen())

while True:
    d = serial_obj.readline()
    if d is None:
        pass
    else:
        print('data',d)
    # 114.433961,30.519594
    data_send = 'AA%03d,%f,%f,%f,%f\r\n'%(random.randint(0,20),114.433961+(random.random()-0.5)/100,30.519594+(random.random()-0.5)/100,3.2+(random.random()-0.5)/10,100.0-(time.time()-start_time)/60)
    serial_obj.send_data(data_send)

    time.sleep(1)