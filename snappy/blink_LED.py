"""Standard reference script for SnapStick - Sets LED green and pulses on USB rx data"""
from synapse.RF200 import *

# LEDs are active-low for SS200
SS200_GRN_LED = 6

# This GPIO is used for both the Paddle board and the proto-board
# however, the paddle board is active low, where as the proto-board is active high
# we are going to toggle the pin with a 50% duty cycle so the direction shouldn't
# be noticeable
PADDLE_GRN_LED = GPIO_1

@setHook(HOOK_STARTUP)
def init():
    setPinDir(SS200_GRN_LED, True)
    setPinDir(PADDLE_GRN_LED, True)
    
    writePin(SS200_GRN_LED, True)
    writePin(PADDLE_GRN_LED, True)

@setHook(HOOK_1S)
def tick():
    pulsePin(SS200_GRN_LED, 500, False)
    pulsePin(PADDLE_GRN_LED, 500, False)



