"""Read-only HID inventory and optional incoming report monitor. No output reports.
Usage:
  py -m pip install hidapi
  py usb_probe.py
  py usb_probe.py --listen --interface 2
If another app owns an interface, opening it may fail. This is expected.
"""
import argparse
import time

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--listen",action="store_true")
    p.add_argument("--interface",type=int,help="Exact interface_number to monitor")
    p.add_argument("--product",type=lambda s:int(s,0),help="Product ID, e.g. 0x1234")
    args=p.parse_args()
    try:
        import hid
    except ImportError:
        raise SystemExit("pip install hidapi")
    devices=[d for d in hid.enumerate(0x1532,0)
             if args.product is None or d["product_id"]==args.product]
    for idx,d in enumerate(devices):
        print(f"[{idx}] VID={d['vendor_id']:04x} PID={d['product_id']:04x} "
              f"interface={d.get('interface_number')} usage={d.get('usage_page')}:{d.get('usage')} "
              f"product={d.get('product_string')!r} path={d.get('path')!r}")
    if not args.listen:
        return
    matches=[d for d in devices if args.interface is None or d.get("interface_number")==args.interface]
    if not matches:
        raise SystemExit("No matching HID interfaces")
    if len(matches)!=1:
        raise SystemExit("Choose exactly one interface with --interface and/or --product.")
    dev=hid.device()
    dev.open_path(matches[0]["path"])
    dev.set_nonblocking(True)
    print("Listening for input reports only. Ctrl+C to quit")
    try:
        while True:
            data=dev.read(512)
            if data:
                print(f"{time.time():.3f} {bytes(data).hex(' ')}")
            else:
                time.sleep(.005)
    except KeyboardInterrupt:
        pass
    finally:
        dev.close()

if __name__=="__main__":
    main()
