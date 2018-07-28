#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import time
import subprocess
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import RPi.GPIO as GPIO
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306


def cmd(_cmd):
    return subprocess.Popen(_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)


def main():
    # Pin Setup
    L_pin = 27
    R_pin = 23
    C_pin = 4
    U_pin = 17
    D_pin = 22
    A_pin = 5
    B_pin = 6
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(A_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # To switch Node "serving" on/off
    GPIO.setup(B_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # To switch Node "consuming" on/off
    GPIO.setup(L_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(R_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(U_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(D_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(C_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # To shutdown Raspberry Pi off

    # Display Setup
    # Raspberry Pi pin configuration:
    RST = None

    # 128x64 display with hardware I2C:
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)

    # Initialize library.
    disp.begin()

    # Clear display.
    disp.clear()
    disp.display()

    # Display Substratum Logo for 5 seconds
    image = Image.open('/home/alarm/sub_logo_128_64.ppm').convert('1')
    disp.image(image)
    disp.display()
    time.sleep(5)
    disp.clear()
    disp.display()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    width = disp.width
    height = disp.height
    image = Image.new('1', (width, height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Load font
    font = ImageFont.truetype('/home/alarm/pixelmix.ttf', 8)

    IP = subprocess.check_output('hostname -i', shell=True).decode('ascii').strip()
    old_dns = subprocess.check_output('cat /etc/resolv.conf', shell=True).decode('ascii')

    pub_key = ''

    cmd_run_node = '/home/alarm/SubstratumNode --dns_servers 1.1.1.1'
    cmd_start_resolving = 'systemctl start systemd-resolved'
    cmd_stop_resolving = 'systemctl stop systemd-resolved'
    cmd_set_dns_to_localhost = 'cat <<EOF > /etc/resolv.conf\nnameserver 127.0.0.1\nEOF'
    cmd_set_dns_to_normal = 'cat <<EOF > /etc/resolv.conf\n{}\nEOF'.format(old_dns)
    cmd_shutdown = 'shutdown -h now'

    serving = False
    consuming = False
    while True:
        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=0)

        # Write two lines of text.
        draw.text((0, 0), 'SUBSTRATUM NODE 0.3.3', font=font, fill=255)
        draw.line((0, 9, width, 9), fill=255)
        draw.text((0, 11), 'IP Address: {}'.format(IP), font=font, fill=255)
        draw.text((0, 20), 'Serving: {}'.format('ON' if serving else 'OFF'), font=font, fill=255)
        draw.text((0, 29), 'Consuming: {}'.format('ON' if consuming else 'OFF'), font=font, fill=255)
        draw.text((0, 38), 'Public Key:   {}'.format(pub_key[:8]), font=font, fill=255)
        draw.text((0, 47), '  ' + pub_key[8:26], font=font, fill=255)
        draw.text((0, 56), '  ' + pub_key[26:44], font=font, fill=255)

        if not GPIO.input(A_pin):   # Pressed button A
            if not serving:                 # If serving is OFF, turn it on
                cmd(cmd_stop_resolving)
                process_node = cmd(cmd_run_node)
                while True:
                    line = process_node.stdout.readline().decode('ascii').strip()
                    if line != '':
                        if 'public key' in line:
                            _, key = line.split(':')
                            pub_key = key.strip()
                            serving = True
                            break
                    else:
                        break
            else:                           # If serving is ON, turn both the serving & consuming off
                process_node.kill()
                pub_key = ''
                serving = False
                cmd(cmd_start_resolving)
                consuming = False

        if not GPIO.input(B_pin):   # Pressed button B
            if consuming:                   # If consuming is ON, turn it off
                cmd(cmd_set_dns_to_normal)
                consuming = False
            elif serving:                   # If consuming is OFF, turn it on only if serving is ON
                cmd(cmd_set_dns_to_localhost)
                consuming = True

        if not GPIO.input(C_pin):   # Pressed button C
            if consuming:
                cmd(cmd_set_dns_to_normal)
            if serving:
                process_node.kill()
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            disp.image(image)
            disp.display()
            cmd(cmd_shutdown)

        # Display image.
        disp.image(image)
        disp.display()
        time.sleep(0.1)


if __name__ == '__main__':
    main()
