#!/usr/bin/env python

from __future__ import print_function

import evdev
import sys
import time


# From http://stackoverflow.com/a/231216
class flushfile(object):
    '''Wrapper around a file object that flushes after every write.'''

    def __init__(self, f):
        self.f = f

    def __getattr__(self,name):
        return object.__getattribute__(self.f, name)

    def write(self, x):
        self.f.write(x)
        self.f.flush()

# Flush after every write to stdout. Required because otherwise prints
#   without newlines won't appear.
sys.stdout = flushfile(sys.stdout)


# Get the device either from the command line or by using identify_evdev
if len(sys.argv) > 2 or len(sys.argv) == 2 and sys.argv[1] == '--help':
    print("USAGE: %s [event-device]" % sys.argv[0], file=sys.stderr)
    print(file=sys.stderr)
    print("Generates a xboxdrv command for treating event-device as an XBox controller.", file=sys.stderr)
    print("If event-device is omitted, the controller will be identified by asking the", file=sys.stderr)
    print("user to press a button on it.", file=sys.stderr)
    sys.exit()
elif len(sys.argv) == 2:
    evdev_filename = sys.argv[1]
else:
    from identify_evdev import list_active_evdev
    fns = None
    # Keep going until there's input from only one device.
    while fns is None or len(fns) != 1:
        print("Press any button on only the joystick you are setting up.")
        fns = list_active_evdev()
    evdev_filename = fns[0]
    print("Selected event device: %s" % evdev_filename)
    print("Stop pressing any buttons.")
    # Give user time to stop pressing buttons.
    time.sleep(2)

# Open the device
dev = evdev.device.InputDevice(evdev_filename)

def convert_keycode_to_name(code):
    '''Convert a keycode number to a string xboxdrv understands.'''

    if code in evdev.ecodes.keys:
        keys = evdev.ecodes.keys[code]
        if not isinstance(keys, str):
            return keys[0]
        else:
            return keys
    else:
        # Workaround supported since xboxdrv v0.6.0 for unnamed keys
        return 'KEY_#%d' % code


def eat_events(dev):
    '''Consume and ignore events on a device until there are none.'''

    while dev.read_one() is not None:
        pass

def get_next_pressed_button_name(dev):
    '''Wait for the next button press and report its xboxdrv name.'''

    for event in dev.read_loop():
        if event.type == evdev.ecodes.EV_KEY:
            if event.value == evdev.KeyEvent.key_down:
                return convert_keycode_to_name(event.code)

def get_next_maxed_axis(dev, mappings):
    '''Wait for any axis (joystick direction or analog button) to reach
       an extreme value and report which axis did so along with whether
       it hit the "min" or "max" value.'''

    for event in dev.read_loop():
        # Allow the user to cancel by pressing the "start" button.
        if event.type == evdev.ecodes.EV_KEY:
            if event.value == evdev.KeyEvent.key_down:
                if convert_keycode_to_name(event.code) == mappings['start']:
                    return None, None
        # If an axis has been moved...
        elif event.type == evdev.ecodes.EV_ABS:
            # ... look up the min/max values for that axis...
            absinfo = dict(dev.capabilities()[evdev.ecodes.EV_ABS])[event.code]
            axis = evdev.ecodes.ABS[event.code]
            # ... and if the min or max has been reached, return it.
            if event.value <= absinfo.min + 20:
                return 'min', axis
            elif event.value >= absinfo.max - 20:
                return 'max', axis

def ask_user_for_keymap(dev):
    '''Generates a mapping for buttons by listing all of the XBox controller
       buttons and having the user press the corresponding button on their
       controller.'''

    xbox_button_names = [
        ('start', None),
        ('back', 'or select'),
        ('guide', 'large center button'),
        ('a', 'bottom (green)'),
        ('b', 'right (red)'),
        ('x', 'left (blue)'),
        ('y', 'top (yellow)'),
        ('black', None),
        ('white', None),
        ('lb', 'left trigger (front, digital) (L1)'),
        ('rb', 'right trigger (front, digital) (R1)'),
        ('lt', 'left trigger (back, analog) (L2)'),
        ('rt', 'right trigger (back, analog) (R2)'),
        ('tl', 'left analog stick button (L3)'),
        ('tr', 'right analog stick button (R3)'),
        ('du', 'd-pad up'),
        ('dr', 'd-pad right'),
        ('dl', 'd-pad left'),
        ('dd', 'd-pad down'),
        ('green', 'guitar button'),
        ('red', 'guitar button'),
        ('yellow', 'guitar button'),
        ('blue', 'guitar button'),
        ('orange', 'guitar button'),
    ]

    print("Press the corresponding button on your controller. If the button doesn't exist, press the start button again to ignore it.")
    # Dictionary of XBox buttons to xboxdrv key names.
    mappings = {}
    # Values of mappings dictionary to avoid mapping the same button twice.
    assigned_keys = set()
    for button, description in xbox_button_names:
        if description is not None:
            description = ' (%s)' % description
        else:
            description = ''
        print("Press %s%s: " % (button, description), end="")
        key = get_next_pressed_button_name(dev)
        if key in assigned_keys:
            # If the button is already assigned, then a repeat means this
            #   button should not have a mapping.
            print("(none)")
        else:
            mappings[button] = key
            assigned_keys.add(key)
            print(key)

    return mappings

def get_evdev_keymap_for_mappings(mappings):
    '''Converts a mappings dictionary in the format of XBox button names
       mapped to xboxdrv key names of the key on the controller that should
       be mapped to that XBox button to the format taken by xboxdrv as
       the command line option --evdev-keymap.'''

    return ','.join(["%s=%s" % (mappings[button], button)
                     for button in mappings])

def ask_user_for_axismap(dev, mappings):
    '''Generates a mapping for the axes by for each XBox axis, asking the
       user to max out the axis on their controller to map to that axis.'''

    xbox_axis_names = [
        # y-axes are inverted in xboxdrv's uinput_config.cpp:120-3
        #   for some reason
        ('x1', ('left', 'right'), 'left analog stick (left/right)'),
        ('y1', ('down', 'up'), 'left analog stick (up/down)'),
        ('x2', ('left', 'right'), 'right anlog stick (left/right)'),
        ('y2', ('down', 'up'), 'right anlog stick (up/down)'),
        ('lt', ('trigger',), 'left analog trigger (L or L2 button)'),
        ('rt', ('trigger',), 'right analog trigger (R or R2 button)'),
    ]

    print("Move the corresponding axis on your controller. If the axis doesn't exist, press the start button to ignore it.")
    axis_mapping = {}
    for axis, dirs, description in xbox_axis_names:
        # Is this an axis that can be moved in both directions (a joystick)?
        if len(dirs) == 2:
            # For an axis, we need to both identify which axis it is and
            #   whether the axis needs to be flipped, so we will ask the
            #   user to move the axis in both directions... of course,
            #   they might not move the same axis both times, so we need
            #   to check for that.
            same_axis = False # Were both readings on the same axis?
            while not same_axis:
                evaxis = None # Which axis has been used so far?
                inverse = None # Is the axis
                for d in dirs:
                    # Ignore events for half a second to give axes a chance
                    #   to reset.
                    time.sleep(0.5)
                    eat_events(dev)

                    print('Move %s (%s) %s: ' % (axis, description, d), end="")
                    level, evaxis = get_next_maxed_axis(dev, mappings)
                    if evaxis is None:
                        # get_next_maxed_axis() was cancelled, so the user
                        #   does not want to map this axis.
                        same_axis = True
                        print('(none)')
                    else:
                        print('%s (%s)' % (evaxis, level))
                        # There's only two loop iterations:
                        #   d == dirs[0] and d == dirs[1].
                        # If this is the second iteration and the evaxis
                        #   is different, then we need to try again.
                        if d == dirs[1] and prev_evaxis != evaxis:
                            print("different axes were moved; please try again")
                            same_axis = False
                        else:
                            # Remember the previous iteration's values (if any)
                            prev_evaxis = evaxis
                            prev_inverse = inverse
                            # The first direction is the min direction.
                            if d == dirs[0] and level == 'min' \
                                    or d == dirs[1] and level == 'max':
                                inverse = False
                            else:
                                inverse = True
                            # Was it moved in the same direction both times?
                            if d == dirs[1] and prev_inverse != inverse:
                                print("please move axis in the requested direction")
                                same_axis = False
                            else:
                                # If we get here, then the same axis was moved
                                #   in two different directions, so we believe
                                #   evaxis and inverse are correct.
                                axis_mapping[axis] = (evaxis, inverse)
                                # And we can exit the loop.
                                same_axis = True
        # Otherwise, it's an analog button/trigger.
        else:
            # Ignore events for half a second to give axes a chance to reset.
            time.sleep(0.5)
            eat_events(dev)

            print('Press trigger %s (%s) all the way: ' % (axis, description),
                  end="")
            level, evaxis = get_next_maxed_axis(dev, mappings)
            if evaxis is None:
                # get_next_maxed_axis() was cancelled, so the user does not
                #   want to map this axis.
                print("(none)")
            else:
                # We expect pressing a trigger to max its value, so if the
                #   level is actually its min, then the axis needs to be
                #   inverted.
                axis_mapping[axis] = (evaxis, level == 'min')
                print(evaxis)

    # Return the results in the format for the --evdev-absmap and --axis-map
    #   xboxdrv options.
    return (','.join(["%s=%s" % (axis_mapping[axis][0], axis)
                      for axis in axis_mapping]),
            # Invert axes by listing them in the --axis-map with a minus sign.
            ','.join(['-%s=%s' % (axis, axis)
                      for axis in axis_mapping
                      if axis_mapping[axis][1]]))

# Ask the user for all of the mappings...
mappings = ask_user_for_keymap(dev)
evdev_keymap = get_evdev_keymap_for_mappings(mappings)
evdev_absmap, axismap = ask_user_for_axismap(dev, mappings)

# ... and print out the xboxdrv command for those mappings.
print("xboxdrv --evdev \"%s\" --evdev-keymap \"%s\" --evdev-absmap \"%s\" --axismap \"%s\" --mimic-xpad --silent" \
        % (evdev_filename, evdev_keymap, evdev_absmap, axismap))
