"""Analog key travel -> desktop mouse or browser navigation (Windows POC).
Usage: py -m pip install -r requirements-experiments.txt
       py playground.py --mode monitor
       py playground.py --mode mouse
       py playground.py --mode browser
       Ctrl+C to quit. No firmware writes.
"""
import argparse
import math
import threading
import time

from analogsense import AnalogSense

HID = {**{chr(97+i):4+i for i in range(26)},
       **{str(i):0x1d+i for i in range(1,10)}}
DEADZONE = 0.12
SPEED = 1000
SCROLL_SPEED = 12

def amount(depth):
    x=max(0, min(1, (depth-DEADZONE)/(1-DEADZONE)))
    return x*x

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=("monitor","mouse","browser"),default="monitor")
    parser.add_argument("--device",type=int,default=0)
    parser.add_argument("--list-devices",action="store_true")
    args=parser.parse_args()
    analog=AnalogSense()
    devices=analog.get_devices()
    for i,device in enumerate(devices):
        print(f"[{i}] {device.product_name}")
    if args.list_devices:
        return
    if not devices:
        raise SystemExit("AnalogSense found no keyboard. Try usb_probe.py; new HE models may need a new backend.")
    if args.device >= len(devices):
        raise SystemExit("Bad device index")
    from pynput.mouse import Controller as Mouse, Button
    from pynput.keyboard import Controller as Keyboard, Key
    mouse, keyboard = Mouse(), Keyboard()
    state={}
    lock=threading.Lock()
    def on_keys(keys):
        with lock:
            state.clear()
            state.update({int(k["scancode"]):float(k["value"]) for k in keys})
    def shortcut(*keys):
        for k in keys: keyboard.press(k)
        for k in reversed(keys): keyboard.release(k)
    device=devices[args.device]
    device.start_listening(on_keys)
    print(f"Mode={args.mode}. Ctrl+C to stop.")
    left=right=False
    latch={}
    fraction_x=fraction_y=fraction_scroll=0.
    previous=time.perf_counter()
    last_print=0.
    try:
        while True:
            now=time.perf_counter()
            dt=min(.05,now-previous)
            previous=now
            with lock:
                snapshot=state.copy()
            def a(key):
                return amount(snapshot.get(HID[key],0))
            if args.mode=="monitor":
                if now-last_print>.1:
                    print("\r"+" ".join(f"{k.upper()}:{snapshot.get(HID[k],0):.2f}"
                                        for k in "wasdqerfzx")+"   ",end="",flush=True)
                    last_print=now
            elif args.mode=="mouse":
                x=a("d")-a("a")
                y=a("s")-a("w")
                factor=max(1,math.hypot(x,y))
                fraction_x+=x/factor*SPEED*dt
                fraction_y+=y/factor*SPEED*dt
                dx,dy=int(fraction_x),int(fraction_y)
                fraction_x-=dx
                fraction_y-=dy
                if dx or dy: mouse.move(dx,dy)
                fraction_scroll+=(a("e")-a("q"))*SCROLL_SPEED*dt
                scroll=int(fraction_scroll)
                fraction_scroll-=scroll
                if scroll: mouse.scroll(0,scroll)
                for key,button,old in (("f",Button.left,left),("r",Button.right,right)):
                    pressed=a(key)>.2
                    if pressed!=old:
                        (mouse.press if pressed else mouse.release)(button)
                    if key=="f": left=pressed
                    else: right=pressed
            else:
                fraction_scroll+=(a("w")-a("s"))*SCROLL_SPEED*dt
                scroll=int(fraction_scroll)
                fraction_scroll-=scroll
                if scroll: mouse.scroll(0,scroll)
                fraction_x+=(a("d")-a("a"))*SCROLL_SPEED*dt
                horiz=int(fraction_x)
                fraction_x-=horiz
                if horiz: mouse.scroll(horiz,0)
                shortcuts={
                    "q":(Key.ctrl,Key.shift,Key.tab),
                    "e":(Key.ctrl,Key.tab),
                    "z":(Key.alt,Key.left),
                    "x":(Key.alt,Key.right),
                }
                for key,combo in shortcuts.items():
                    pressed=a(key)>.2
                    if pressed and not latch.get(key,False):
                        shortcut(*combo)
                    latch[key]=pressed
            time.sleep(1/90)
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        if left: mouse.release(Button.left)
        if right: mouse.release(Button.right)
        device.stop_listening()

if __name__=="__main__":
    main()
