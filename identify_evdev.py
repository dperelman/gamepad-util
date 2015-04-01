#!/usr/bin/env python

from __future__ import print_function

# Based on http://python-evdev.readthedocs.org/en/latest/index.html
import evdev
import glob
import select
import sys

def list_active_evdev():
    '''Lists the next /dev/input/event* devices to generate input events.
       Will usually only be a single device.'''

    devices = []
    for dev in glob.glob('/dev/input/event*'):
        try:
            devices.append(evdev.device.InputDevice(dev))
        except (IOError, OSError):
            # Don't have permissions for that device, ignore it.
            pass
    devices = {dev.fd : dev for dev in devices}

    output = []
    anyInput = False
    while not anyInput:
        # use select to wait for input
        r,w,x = select.select(devices, [], [])
        for fd in r:
            for event in list(devices[fd].read())[:1]:
                output.append(devices[fd].fn)
                anyInput = True

    return output

if __name__ == "__main__":
    # Print the next /dev/input/event* device to generate an input event.
    output = list_active_evdev()

    if len(output) == 1:
        print(output[0])
    else:
        print("Detected events from multiple devices. Please try again.",
              file=sys.stderr)
        exit(1)
