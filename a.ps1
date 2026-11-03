@'
import re
import time
import hid

VID, PID = 0x1532, 0x02EA

def short_label(info: dict) -> str:
    path = info["path"].decode("ascii", errors="ignore")
    m = re.search(r"(MI_\d+(?:&Col\d+)*)", path, re.IGNORECASE)
    col = m.group(1) if m else path
    return f"{col} (up=0x{info['usage_page']:04X}, u=0x{info['usage']:02X})"

opened = []
for info in hid.enumerate(VID, PID):
    label = short_label(info)
    try:
        dev = hid.device()
        dev.open_path(info["path"])
        dev.set_nonblocking(True)
        # Try a test read immediately; keyboard/mouse boot collections raised read error on Windows
        dev.read(1024)
        opened.append((label, dev))
        print(f"[+] Listening on {label}", flush=True)
    except Exception as e:
        try:
            dev.close()
        except Exception:
            pass
        print(f"[-] Skipped    {label}: {e}", flush=True)

if not opened:
    raise SystemExit("No readable HID interfaces could be opened.")

print("\nSlowly press and release W, then A. Press Ctrl+C to stop.\n", flush=True)
try:
    while True:
        any_data = False
        for label, dev in opened:
            try:
                report = dev.read(1024)
            except OSError:
                continue
            if report:
                any_data = True
                raw = bytes(report)
                # Trim trailing zeros for readability while keeping full length info
                trimmed = raw.rstrip(b"\x00") or b"\x00"
                print(f"[{label:28s}] (len={len(raw):2d}) {trimmed.hex(' ')}", flush=True)
        if not any_data:
            time.sleep(0.002)
except KeyboardInterrupt:
    print("\nStopped.", flush=True)
finally:
    for _, dev in opened:
        try:
            dev.close()
        except Exception:
            pass
'@ | uv run python -