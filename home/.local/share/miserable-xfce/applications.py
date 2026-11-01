#!/usr/bin/python
"""Toggle Rofi without a keyboard grab, keeping global XFCE shortcuts usable."""
import os
import signal
import subprocess
import time
from Xlib import X, display, protocol

TITLE = 'Applications'
d = display.Display()
root = d.screen().root

def windows():
    prop = root.get_full_property(d.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
    if prop:
        for wid in prop.value:
            w = d.create_resource_object('window', wid)
            try:
                if w.get_wm_name() in (TITLE, 'rofi - drun') and 'rofi' in str(w.get_wm_class()).lower():
                    yield w
            except Exception:
                continue

for w in windows():
    pid = w.get_full_property(d.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
    if pid:
        os.kill(int(pid.value[0]), signal.SIGTERM)
    raise SystemExit(0)

p = subprocess.Popen(['rofi', '-show', 'drun', '-normal-window', '-steal-focus'])
try:
    for _ in range(60):
        if p.poll() is not None:
            break
        found = list(windows())
        if found:
            w = found[0]
            w.change_attributes(event_mask=X.FocusChangeMask)
            w.set_wm_name(TITLE)
            w.change_property(d.intern_atom('_NET_WM_NAME'), d.intern_atom('UTF8_STRING'), 8, TITLE.encode())
            for states in [('_NET_WM_STATE_SKIP_TASKBAR', '_NET_WM_STATE_SKIP_PAGER'),
                           ('_NET_WM_STATE_ABOVE',)]:
                atoms = [d.intern_atom(s) for s in states]
                atoms += [0] * (2-len(atoms))
                root.send_event(protocol.event.ClientMessage(
                    window=w.id, client_type=d.intern_atom('_NET_WM_STATE'),
                    data=(32, [1, *atoms, 1, 0])),
                    event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            root.send_event(protocol.event.ClientMessage(
                window=w.id, client_type=d.intern_atom('_NET_ACTIVE_WINDOW'),
                data=(32, [2, X.CurrentTime, 0, 0, 0])),
                event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.flush()
            break
        time.sleep(.025)
    # Allow XFWM and Rofi's initial focus requests to settle first.
    time.sleep(.3)
    while p.poll() is None:
        while d.pending_events():
            d.next_event()
        focus = d.get_input_focus().focus
        inside = False
        for _ in range(16):
            if not hasattr(focus, 'id') or focus.id == root.id:
                break
            if focus.id == w.id:
                inside = True
                break
            try:
                focus = focus.query_tree().parent
            except Exception:
                break
        if not inside:
            p.terminate()
        time.sleep(.05)
    raise SystemExit(p.wait())
finally:
    d.close()
