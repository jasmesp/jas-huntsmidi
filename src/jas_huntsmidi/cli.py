"""Huntsman analog-keyboard -> MIDI 4x4 pad controller prototype.

Windows-oriented. Requires Razer Synapse, AnalogSensePy, mido, python-rtmidi.

    uv sync
    uv run jas-huntsmidi --list-ports
    uv run jas-huntsmidi --port "loopMIDI Port"

AnalogSense callbacks are treated as snapshots of currently active analog keys.
"""
from __future__ import annotations

import argparse
import math
import queue
import threading
import time
from dataclasses import dataclass

import mido

# 4x4 keyboard-as-pad grid, row-major. MIDI starts at C1 (36) using 4x4 drum pads.
# HID keyboard usage codes; see USB HID Usage Tables, page 0x07.
PAD_ROWS = ("1234", "qwer", "asdf", "zxcv")
HID = {
    **{chr(ord('a') + i): 0x04 + i for i in range(26)},
    **{str(i): 0x1E + i - 1 for i in range(1, 10)},
    '0': 0x27,
}
PAD_KEYS = [HID[c] for row in PAD_ROWS for c in row]

# MIDI settings
BASE_NOTE = 36
CHANNEL = 9                   # MIDI channel 10 (zero-indexed), conventional drum channel
GATE_ON = 0.20                # normalized travel 0..1
GATE_OFF = 0.09               # hysteresis prevents retrigger at threshold
AFTERTOUCH = True
AFTERTOUCH_HZ = 50
AFTERTOUCH_DEADBAND = 3        # ignore tiny 7-bit changes

# Velocity from depth reached shortly after crossing trigger threshold.
# This is a pragmatic proxy for strike intensity (not a force sensor).
STRIKE_WINDOW_SEC = 0.022
STRIKE_REFERENCE = 0.55       # travel change in window corresponding to strong strike
VELOCITY_FLOOR = 22
VELOCITY_CURVE = 0.70         # <1 makes soft strikes more playable

# Missing keys in callback snapshot are considered released.
# Do not assume missing keys stay pressed, or stuck notes may result.


def velocity_from_motion(speed: float) -> int:
    # speed is normalized travel per second
    scaled = min(1.0, max(0.0, speed * STRIKE_WINDOW_SEC / STRIKE_REFERENCE))
    return max(1, min(127, round(VELOCITY_FLOOR + (127 - VELOCITY_FLOOR) * scaled ** VELOCITY_CURVE)))


@dataclass
class Pad:
    held: bool = False
    note_on_sent: bool = False
    press_t: float = 0.0
    press_depth: float = 0.0
    max_depth: float = 0.0
    previous_depth: float = 0.0
    previous_t: float = 0.0
    max_speed: float = 0.0
    last_pressure: int = -1
    last_pressure_t: float = 0.0


class PadEngine:
    def __init__(self, output):
        self.output = output
        self.pads = {sc: Pad() for sc in PAD_KEYS}
        self.last_received = 0.0
        self.midi_events = 0

    def emit(self, typ: str, note: int, value: int = 0):
        kwargs = {'channel': CHANNEL, 'note': note}
        if typ == 'note_on':
            kwargs['velocity'] = value
        elif typ == 'note_off':
            kwargs['velocity'] = 0
        elif typ == 'polytouch':
            kwargs['value'] = value
        self.output.send(mido.Message(typ, **kwargs))
        self.midi_events += 1
        if typ in ('note_on', 'note_off'):
            print(f'{typ:8s}  note={note:3d}  vel={value:3d}', flush=True)

    def note_for(self, sc: int) -> int:
        return BASE_NOTE + PAD_KEYS.index(sc)

    def snapshot(self, values: dict[int, float], now: float):
        self.last_received = now
        for sc, pad in self.pads.items():
            x = min(1.0, max(0.0, values.get(sc, 0.0)))
            note = self.note_for(sc)
            if pad.held and x <= GATE_OFF:
                if pad.note_on_sent:
                    self.emit('note_off', note)
                self.pads[sc] = Pad(previous_depth=x, previous_t=now)
                continue
            if not pad.held and x >= GATE_ON:
                pad.held = True
                pad.press_t = now
                pad.press_depth = x
                pad.max_depth = x
                pad.previous_depth = x
                pad.previous_t = now
                pad.max_speed = 0.0
                pad.last_pressure = -1
                pad.last_pressure_t = 0.0

            if pad.held:
                dt = now - pad.previous_t
                if dt > 0:
                    speed = max(0.0, (x - pad.previous_depth) / dt)
                    pad.max_speed = max(pad.max_speed, speed)
                pad.max_depth = max(pad.max_depth, x)
                if not pad.note_on_sent and now - pad.press_t >= STRIKE_WINDOW_SEC:
                    # Combine depth accumulated during the strike window and
                    # max positive speed, favoring the larger estimate.
                    depth_speed = max(0.0, pad.max_depth - pad.press_depth) / STRIKE_WINDOW_SEC
                    velocity = velocity_from_motion(max(depth_speed, pad.max_speed))
                    self.emit('note_on', note, velocity)
                    pad.note_on_sent = True
                if pad.note_on_sent and AFTERTOUCH:
                    pressure = round(127 * x)
                    if (abs(pressure - pad.last_pressure) >= AFTERTOUCH_DEADBAND
                            and now - pad.last_pressure_t >= 1.0 / AFTERTOUCH_HZ):
                        self.emit('polytouch', note, pressure)
                        pad.last_pressure = pressure
                        pad.last_pressure_t = now
            pad.previous_depth = x
            pad.previous_t = now

    def stop_all(self):
        for sc, pad in self.pads.items():
            if pad.note_on_sent:
                self.emit('note_off', self.note_for(sc))
            self.pads[sc] = Pad()


def choose_port(requested: str | None, virtual: bool):
    if virtual:
        return mido.open_output('Huntsman Pads', virtual=True)
    ports = mido.get_output_names()
    if requested:
        matches = [p for p in ports if requested.lower() in p.lower()]
        if not matches:
            raise RuntimeError(f'No MIDI output matches {requested!r}. Available: {ports}')
        if len(matches) > 1:
            raise RuntimeError(f'Ambiguous port {requested!r}: {matches}')
        return mido.open_output(matches[0])
    if len(ports) == 1:
        return mido.open_output(ports[0])
    raise RuntimeError('Select an output using --port. Available ports: ' + repr(ports))


def demo(engine: PadEngine):
    """Synthetic two-pad test, useful for checking MIDI routing without hardware."""
    dt = 0.005
    start = time.perf_counter()
    while (now := time.perf_counter()) - start < 1.6:
        elapsed = now - start
        v1 = min(0.92, max(0.0, (elapsed - 0.15) / 0.065)) if elapsed < 0.68 else 0.0
        v2 = min(0.72, max(0.0, (elapsed - 0.40) / 0.10)) if elapsed < 1.06 else 0.0
        engine.snapshot({PAD_KEYS[0]: v1, PAD_KEYS[5]: v2}, now)
        time.sleep(dt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-ports', action='store_true')
    parser.add_argument('--list-devices', action='store_true')
    parser.add_argument('--port', help='MIDI output port name (or unique substring)')
    parser.add_argument('--virtual', action='store_true', help='Create virtual MIDI output (supported by some OS/backends)')
    parser.add_argument('--device', type=int, default=0, help='AnalogSense device index')
    parser.add_argument('--demo', action='store_true', help='Send a synthetic two-pad performance')
    parser.add_argument('--monitor', action='store_true', help='Log analog key travel from callback')
    args = parser.parse_args()

    if args.list_ports:
        for p in mido.get_output_names():
            print(p)
        return

    analog = device = None
    if args.list_devices or not args.demo:
        from analogsense import AnalogSense
        analog = AnalogSense()
        devices = analog.get_devices()
        if args.list_devices:
            for i, d in enumerate(devices):
                print(f'[{i}] {d.product_name}')
            if not devices:
                print('No supported analog keyboard found. Is Razer Synapse running?')
            return
        if not devices:
            raise RuntimeError('No supported analog keyboard found; check Synapse and USB connection')
        if not 0 <= args.device < len(devices):
            raise RuntimeError(f'Device index out of range: {args.device}; found {len(devices)}')
        device = devices[args.device]
        print('Analog keyboard:', device.product_name)

    with choose_port(args.port, args.virtual) as output:
        engine = PadEngine(output)
        print('MIDI out:', output.name)
        print('4x4 pads:', PAD_ROWS, '-> notes', BASE_NOTE, 'through', BASE_NOTE + 15)
        if args.demo:
            try:
                demo(engine)
            finally:
                engine.stop_all()
            return

        # Callback is on the SDK's reader thread. Keep it lightweight:
        # newest snapshot wins, and MIDI is emitted on the main thread.
        inbox: queue.Queue[tuple[float, dict[int, float]]] = queue.Queue(maxsize=64)
        def on_keys(active_keys):
            now = time.perf_counter()
            snapshot = {int(k['scancode']): float(k['value']) for k in active_keys}
            try:
                inbox.put_nowait((now, snapshot))
            except queue.Full:
                try:
                    inbox.get_nowait()
                except queue.Empty:
                    pass
                try:
                    inbox.put_nowait((now, snapshot))
                except queue.Full:
                    pass

        print('Listening. Ctrl+C to quit.')
        device.start_listening(on_keys)
        try:
            while True:
                try:
                    t, snapshot = inbox.get(timeout=0.005)
                except queue.Empty:
                    continue
                # Drain queued frames to avoid significant backlog without
                # discarding intermediate key motions on a normally loaded system.
                if args.monitor:
                    text = ', '.join(f'{analog.scancode_to_string(k)}:{v:.2f}'
                                     for k, v in sorted(snapshot.items()) if v > 0.02)
                    if text:
                        print(text)
                engine.snapshot(snapshot, t)
        except KeyboardInterrupt:
            pass
        finally:
            device.stop_listening()
            engine.stop_all()


if __name__ == '__main__':
    run()