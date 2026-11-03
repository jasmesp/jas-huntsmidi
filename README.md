# huntsmidi

Experimental Python proof of concept mapping analog keyboard travel to MIDI pads.

## Features

- 4x4 grid: `1234` / `QWER` / `ASDF` / `ZXCV`
- MIDI notes 36–51 on channel 10
- Note on/off with hysteresis
- Strike velocity estimated from key-travel movement
- Polyphonic key pressure from analog travel
- Demo mode for MIDI routing checks

## Requirements

Windows, Python 3.10+, a supported analog keyboard, and access to per-key analog travel through AnalogSensePy. Hardware compatibility with specific Hall-effect Huntsman models has **not been verified**. The current prototype uses AnalogSensePy and may need a different transport/SDK for some models. Razer Synapse may be required by the SDK for supported models.

```powershell
py -m pip install -r requirements.txt
py huntsman_midi.py --list-devices
py huntsman_midi.py --list-ports
py huntsman_midi.py --port "loopMIDI Port" --monitor
```

Use `--demo` to test MIDI output without a keyboard:

```powershell
py huntsman_midi.py --port "loopMIDI Port" --demo
```

## Status

Proof of concept. Device integration and strike dynamics need validation on actual hardware. The code has not been tested on the user's specific Hall-effect keyboard.