# gamepad-util

Scripts to help setting up gamepads on Linux:
 * [**`identify_evdev.py`**](identify_evdev.py) (blog post: [Identifying joystick devices](https://aweirdimagination.net/2015/04/04/identifying-joystick-devices/)): blocks until any `/dev/input/event*` device has any input and prints that device's path. 
    
    Example:
    ```
    $ gamepad-util/identify_evdev.py
    /dev/input/event22
    ```
 * [**`create_xboxdrv_evdev_map.py`**](create_xboxdrv_evdev_map.py) (blog post: [Emulating Xbox controllers on Linux](https://aweirdimagination.net/2015/04/06/emulating-xbox-controllers-on-linux/)): interactive script to help generate arguments to [`xboxdrv`](https://pingus.seul.org/~grumbel/xboxdrv/) for remapping buttons/axes as desired.
 
     Example:
    ```
    $ gamepad-util/create_xboxdrv_evdev_map.py
    Press any button on only the joystick you are setting up.
    Selected event device: /dev/input/event22
    Stop pressing any buttons.
    Press the corresponding button on your controller. If the button doesn't exist, press the start button again to ignore it.
    Press start: BTN_START
    Press back (or select): BTN_SELECT
    Press guide (large center button): (none)
    # ...
    Press trigger lt (left analog trigger (L or L2 button)) all the way: ABS_Z
    Press trigger rt (right analog trigger (R or R2 button)) all the way: ABS_RZ
    xboxdrv --evdev "/dev/input/event22" --evdev-keymap "BTN_A=a,BTN_B=b,BTN_TL=lb,BTN_THUMBR=tr,BTN_SELECT=back,BTN_START=start,BTN_THUMBL=tl,BTN_TR=rb,BTN_WEST=y,BTN_NORTH=x" --evdev-absmap "ABS_RZ=rt,ABS_RY=y2,ABS_RX=x2,ABS_Z=lt,ABS_Y=y1,ABS_X=x1" --axismap "-y2=y2,-y1=y1" --mimic-xpad --silent
    ```
