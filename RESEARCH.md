# Beyond MIDI: Razer HE protocol exploration (2026-11-03)

This branch is a scratchpad, not a validated hardware driver.

## Findings

- Razer's official Synapse Web compatibility list includes **Huntsman V3 HE Magnetic Mini 65% 8KHz (RZ03-0593x)** and **HE Magnetic Tenkeyless 8KHz (RZ03-0592x)**. It is browser-based and uses WebHID, not WebMIDI. Source: https://mysupport.razer.com/app/answers/detail/a_id/20604/
- Synapse Web: https://synapse.razer.com/ ; configuring onboard profiles implies device command traffic, but does **not** establish that raw per-key analog travel is exposed.
- Razer Chroma SDK exists, primarily for programmable lighting; it is **not** a general open-source per-key sensor driver. https://developer.razer.com/works-with-chroma/setting-up/
- I found no official open-source Synapse profile format or published public Razer analog-input SDK. This is a negative search finding, not proof nothing exists.
- Open-source third-party [AnalogSensePy](https://github.com/girlglock/AnalogSense-Python-SDK) provides per-key travel for listed Razer *optical analog* models via running Synapse, but does **not explicitly list** the new HE Mini. We should try it, not assume it works.

## Practical experiments

1. `py playground.py --list-devices` then `py playground.py --mode monitor`. Do the keys report changing 0..1 values?
2. `py usb_probe.py` lists Razer USB HID interfaces, VID 1532. Optional `--listen --interface N --product 0xXXXX` reads **only incoming** HID reports. No firmware, feature reports, or output reports.
3. On https://synapse.razer.com/ open Chromium DevTools, inspect loaded client JavaScript for `navigator.hid`, `sendReport`, `sendFeatureReport`, `receiveFeatureReport`, `inputreport`, VID/PID. Compare read-only device traffic before and after config changes. Don't replay writes until understood.
4. If standard analog reporting isn't available, investigate controller-emulation mode using `pygame` or `inputs` as an alternative source of analog axes. That is a distinct path from reading raw HE sensors.
5. When travel works, try mouse mode (WASD cursor, Q/E scroll, F/R buttons) and browser mode (WASD scroll, Q/E tab switch, Z/X back/forward).

No automatic firmware or profile writes are implemented. Desktop input actions target the foreground application.
