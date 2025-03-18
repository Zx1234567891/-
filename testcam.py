import Jetson.GPIO as GPIO
import time
 
# Pin Definitions
output_pin = 37  #J41_BOARD_PIN37---gpio12/GPIO.B26/SPI2_MOSI
 
# Pin Setup:
# Board pin-numbering scheme
GPIO.setmode(GPIO.BOARD)
# set pin as an output pin with optional initial state of HIGH
GPIO.setup(output_pin, GPIO.OUT, initial=GPIO.HIGH)
 
curr_value = GPIO.LOW
GPIO.output(output_pin, curr_value)
curr_value ^= GPIO.HIGH
 
'''
# 等效写法
while True:
    time.sleep(5)
    # Toggle the output every second
    print("Outputting {} to pin {}".format(curr_value, output_pin))
    GPIO.output(output_pin, curr_value)
    if curr_value == GPIO.HIGH:
        curr_value = GPIO.LOW
    else:
        curr_value = GPIO.HIGH
'''