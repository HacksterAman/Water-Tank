from machine import Pin, PWM
from utime import sleep
import uasyncio as asyncio

# Permanent Data Storage File
file=open("log.txt", "r+")
log=file.read()

# Output Pin declaration
Relay1=Pin(7, Pin.OUT)
Relay2=Pin(6, Pin.OUT)
Buzzer=Pin(4, Pin.OUT)

# LED Pin declaration 
L_Over=Pin(26, Pin.OUT)
L_Start=Pin(17, Pin.OUT)
L_Stop=Pin(16, Pin.OUT)
L_Filling=Pin(22, Pin.OUT)

# PWM LED Pin declaration
L_100=PWM(Pin(15))
L_75=PWM(Pin(13))
L_50=PWM(Pin(10))
L_25=PWM(Pin(8))
L_0=PWM(Pin(5))
L_Power=PWM(Pin(28))

# Input Pin declaration
In_Power=Pin(12, Pin.IN, Pin.PULL_UP)
In_100=Pin(0, Pin.IN, Pin.PULL_UP)
In_75=Pin(1, Pin.IN, Pin.PULL_UP)
In_50=Pin(3, Pin.IN, Pin.PULL_UP)
In_25=Pin(2, Pin.IN, Pin.PULL_UP)

# Button Pin declaration
B_StaSto=Pin(19, Pin.IN, Pin.PULL_UP)
B_Over=Pin(27, Pin.IN, Pin.PULL_UP)
B_Max=Pin(20, Pin.IN, Pin.PULL_UP)
B_Min=Pin(21, Pin.IN, Pin.PULL_UP)
B_Setting=Pin(9, Pin.IN, Pin.PULL_UP)
B_Bright=Pin(14, Pin.IN, Pin.PULL_UP)

# Global Variables
start=int(log[0])
min=int(log[1])
max=int(log[2])
over=int(log[3])
bright=int(log[4])
level=1
power=False
filling=False
overflowing=False
led_list=[L_0,L_25,L_50,L_75,L_100]
original_bright_list=[10000,37500,65000]
bright_list=[10000,37500,65000]
brightness=original_bright_list[bright]
main_list=[1,2,3,4,5]
indicate=True

# Initial Task
if start:
    L_Start.on()
else:
    L_Stop.on() 

L_Over.value(over)

while bright_list[0]!=brightness:
    bright_list.insert(0,bright_list.pop())

for i in led_list:
    i.freq(1000)

# For checking any Button press
async def button(B):
    if not B.value():
        Buzzer.on()
        while not B.value():
            await asyncio.sleep_ms(10)
        else:
            Buzzer.off()
            await asyncio.sleep_ms(100)            
            return True
    else:
        return False

# For blinking any LED
async def blink(led):
    while True:
        led.toggle()
        await asyncio.sleep_ms(500)

# For cotrolling PWM LEDs
def L(led,mode):
    if mode:
        led.duty_u16(brightness)
    else:
        led.duty_u16(0)

# For controlling Brightness of Display LEDs
def bright_control():
    global brightness,bright_list
    bright_list.insert(0,bright_list.pop())
    brightness=bright_list[0]
    file.seek(4)
    file.write(str(original_bright_list.index(brightness)))
    file.flush()

# For Displaying Tank Level
async def display(level):
    used_list=main_list[:level]
    while True:
        for i in range(level):
            used_list.insert(0,used_list.pop())
            for j in range(level):
                led_list[j].duty_u16(int(brightness/level*used_list[j]))
                await asyncio.sleep_ms((6-level)*100)

# For Setting Max and Min Level values            
async def setting():
    global min,max,indicate
    for i in led_list:
        L(i,0)
    max_list=main_list[min:]
    min_list=main_list[:max-1]
    temp_max=max
    temp_min=min
    L(led_list[temp_max-1],1)
    L(led_list[temp_min-1],1)
    change=0

    while True:
        if await asyncio.create_task(button(B_Max)):
            L(led_list[temp_max-1],0)
            if change==-1:
                max_list=main_list[temp_min:]
                while max_list[0]!=temp_max:
                    max_list.insert(0,max_list.pop())
                    
            max_list.insert(0,max_list.pop())
            change=1
            temp_max=max_list[0]
            L(led_list[temp_max-1],1)

        elif await asyncio.create_task(button(B_Setting)):
            for i in led_list:
                L(i,0)
            max=temp_max
            min=temp_min
            file.seek(1)
            file.write(str(min))
            file.seek(2)
            file.write(str(max))
            file.flush()
            indicate=True
            return

        elif await asyncio.create_task(button(B_Min)):            
            L(led_list[temp_min-1],0)
            if change==1:
                min_list=main_list[:temp_max-1]
                while min_list[0]!=temp_min:
                    min_list.insert(0,min_list.pop())
                    
            min_list.insert(0,min_list.pop())                
            change=-1
            temp_min=min_list[0]
            L(led_list[temp_min-1],1)
        await asyncio.sleep_ms(10)

# For controlling motor
async def motor(mode):
    global filling
    filling=mode
    if mode:
        Relay1.on()
        await asyncio.sleep(13)
        Relay2.on()
        await asyncio.sleep(3)
        Relay2.off()
    else:
        L_Filling.off()
        Relay2.off()
        Relay1.off()

# For Start and Stop command
def StaSto(mode):
    global start
    start=mode
    L_Start.value(mode)
    L_Stop.value(int(not mode))
    file.seek(0)
    file.write(str(mode))
    file.flush()

# For overflow command
def write_over(mode):
    global over
    over=mode
    L_Over.value(mode)
    file.seek(3)
    file.write(str(mode))
    file.flush()

# For overflowing tank for 2 minutes
async def overflow():
    global overflowing
    overflowing=True        
    await asyncio.sleep(120)
    write_over(0)
    StaSto(0)
    overflowing=False

# Checking Main Line Power Supply
async def line():
    global power
    L_Power.freq(1000)
    while True:
        await asyncio.sleep(3.25)
        if In_Power.value():
            power=False
            L_Power.duty_u16(0)
        else:
            L_Power.duty_u16(brightness)
            power=True

# For checking Tank Level
def new_level():
    if not In_100.value():
        return 5
    elif not In_75.value():
        return 4
    elif not In_50.value():
        return 3
    elif not In_25.value():
        return 2
    else:
        return 1

# Main Function
async def main():
    asyncio.create_task(line())
    global bright_list,brightness,indicate,level,overflowing
    while True:
        # For checking Changes in Tank Level
        if new_level()!=level:
            await asyncio.sleep(2)
            if new_level()!=level:
                if indicate==False:# Checking for is display On
                    display_task.cancel()
                    for i in led_list:
                        L(i,0)
                    indicate=True
                level=new_level()
            
        # For Opening Settings Menu
        if await asyncio.create_task(button(B_Setting)):
            display_task.cancel()
            await setting()
        elif indicate==True:# Checking for is display Off
            indicate=False
            display_task=asyncio.create_task(display(level))
        
        # For setting Brightness of Level Indicator
        if await asyncio.create_task(button(B_Bright)):
            bright_control()
        
        # For contolling Start/Stop using StaSto Button
        if await asyncio.create_task(button(B_StaSto)):
            if start:
                StaSto(0)
                write_over(0)
            elif level<max:
                StaSto(1)
                
        # For contolling Overflow using Over Button
        if await asyncio.create_task(button(B_Over)):
            if over:
                write_over(0)
            else:
                write_over(1)
                StaSto(1)
            
        # For contolling Start/Stop according to Min and Max Limits
        if level<=min and not start:
            StaSto(1)
        elif level>=max and start:
            # Checking for overflow setting
            if over:
                # Checking conditions for Overflowing
                if filling and over and level==5 and not overflowing:
                    overflow_task=asyncio.create_task(overflow())
            else:
                StaSto(0)

        # For checking conditions to Control Motor
        if start and power:
            if not filling:
                fill_task=asyncio.create_task(blink(L_Filling))
                motor_task=asyncio.create_task(motor(True))                    
        elif filling:
            fill_task.cancel()
            motor_task.cancel()
            await motor(False)
            if overflowing: 
                # Cancelling task if Overflowing
                overflow_task.cancel()
                overflowing=False          
            
asyncio.run(main())