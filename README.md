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

Python 3.15.2 (pinned in `.python-version`), uv, a supported analog keyboard, and access to per-key analog travel through AnalogSensePy. Hardware compatibility with specific Hall-effect Huntsman models has **been verified**. The current prototype uses AnalogSensePy and may need a different transport/SDK for some models. Razer Synapse may be required by the SDK for supported models.

```sh
uv sync
uv run jas-huntsmidi --help
uv run jas-huntsmidi --list-devices
uv run jas-huntsmidi --list-ports
uv run jas-huntsmidi --port "loopMIDI Port" --monitor
```

uv creates `.venv` and installs the locked dependencies from `uv.lock`. It downloads
the pinned Python automatically if a matching interpreter is not installed. No
manual environment activation or pip install is needed. Commit `uv.lock` to keep
installs reproducible.

The keyboard integration is Windows-oriented; MIDI listing and demo mode can also
be used on macOS. On Windows, create a loopMIDI port for routing to your DAW.

Use `--demo` to test MIDI output without a keyboard:

```sh
uv run jas-huntsmidi --port "loopMIDI Port" --demo
```

## Status

Proof of concept. Device integration and strike dynamics need validation on actual hardware. The code has not been tested on the user's specific Hall-effect keyboard.

On macOS, create a virtual MIDI output for the demo:

```sh
uv run jas-huntsmidi --virtual --demo
```

The RtMidi source build disables JACK to avoid its macOS `sem_timedwait` build
error; CoreMIDI, Windows MIDI, and ALSA remain available on their respective systems.

## Project layout

- `src/jas_huntsmidi/cli.py`: CLI, pad engine, and keyboard integration.
- `src/jas_huntsmidi/__main__.py`: supports `uv run python -m jas_huntsmidi`.
- `pyproject.toml`: package metadata, dependencies, and `jas-huntsmidi` command.
- `.python-version`: Python version selected by uv.
- `uv.lock`: resolved dependency versions.
