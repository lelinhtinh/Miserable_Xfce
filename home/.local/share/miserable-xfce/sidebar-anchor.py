#!/usr/bin/python
"""Refresh Eww's cached monitor geometry after display/workarea changes."""
import logging
import subprocess
from pathlib import Path
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GLib
from Xlib import X, display as xdisplay, error, protocol

EWW = str(Path.home() / '.local/bin/eww')
display = Gdk.Display.get_default()
previous = None
pending = None
panel_height = int(subprocess.check_output([
    "xfconf-query", "-c", "xfce4-panel", "-p", "/panels/panel-2/size"], text=True))

def run(*args):
    return subprocess.run([EWW, *args], text=True, capture_output=True, timeout=5)

def reposition():
    global pending
    pending = None
    try:
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return False
        g, a = monitor.get_geometry(), monitor.get_workarea()
        bottom = max(0, g.y + g.height - (a.y + a.height))
        if bottom == 0:
            bottom = int(subprocess.check_output(
                ['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-2/size'],
                text=True, timeout=5))
        active = run('active-windows')
        if active.returncode == 0:
            opened = {line.split(':', 1)[0].strip() for line in active.stdout.splitlines()}
            for name in ('sidebar', 'sysstat'):
                if name not in opened:
                    continue
                run('close', name).check_returncode()
                run('open', '--screen', '<primary>', '--pos', f'0x-{bottom}', name).check_returncode()
                logging.warning('%s anchored to monitor %sx%s; bottom offset %s', name, g.width, g.height, bottom)
    except Exception:
        logging.exception('Could not refresh Sidebar position')
    return False

def check():
    global previous, pending
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    if monitor is None:
        return True
    g, a = monitor.get_geometry(), monitor.get_workarea()
    current = (g.x, g.y, g.width, g.height, a.x, a.y, a.width, a.height)
    if current != previous:
        previous = current
        if pending is not None:
            GLib.source_remove(pending)
        pending = GLib.timeout_add(350, reposition)
    return True

# Track focus only for the two Eww popup windows.
xconnection = xdisplay.Display()
xroot = xconnection.screen().root
popup_windows = {}
POPUPS = {'Eww - sidebar': 'sidebar', 'Eww - sysstat': 'sysstat'}

def check_popup_focus():
    try:
        while xconnection.pending_events():
            xconnection.next_event()
        visible = {}
        for window in xroot.query_tree().children:
            try:
                name = POPUPS.get(window.get_wm_name())
                if name and window.get_attributes().map_state == X.IsViewable:
                    visible[name] = window
            except error.XError:
                continue
        for name in list(popup_windows):
            if name not in visible:
                del popup_windows[name]
        for name, current in visible.items():
            try:
                if popup_windows.get(name) != current.id:
                    popup_windows[name] = current.id
                    current.change_attributes(event_mask=X.FocusChangeMask)
                    current.set_input_focus(X.RevertToParent, X.CurrentTime)
                    xconnection.flush()
                    continue
                focus = xconnection.get_input_focus().focus
                inside = False
                for _ in range(16):
                    if not hasattr(focus, 'id') or focus.id == xroot.id:
                        break
                    if focus.id == current.id:
                        inside = True
                        break
                    focus = focus.query_tree().parent
                if not inside:
                    run('close', name)
                    popup_windows.pop(name, None)
            except error.XError:
                popup_windows.pop(name, None)
    except Exception:
        logging.exception('Could not update popup focus')
    return True

def check_whisker_position():
    try:
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return True
        geometry, workarea = monitor.get_geometry(), monitor.get_workarea()
        clients = xroot.get_full_property(xconnection.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
        for wid in clients.value if clients else ():
            window = xconnection.create_resource_object('window', int(wid))
            try:
                if window.get_wm_name() != 'Whisker Menu' or window.get_attributes().map_state != X.IsViewable:
                    continue
                if 'wrapper' not in str(window.get_wm_class()).lower():
                    continue
                size = window.get_geometry()
                position = xroot.translate_coords(window, 0, 0)
                left = geometry.x
                bottom = max(0, geometry.y + geometry.height - (workarea.y + workarea.height))
                if bottom == 0:
                    bottom = panel_height
                top = max(geometry.y, geometry.y + geometry.height - bottom - size.height)
                if position.x != left or position.y != top:
                    # Ask XFWM to move the menu client, respecting its frame.
                    xroot.send_event(protocol.event.ClientMessage(
                        window=window.id,
                        client_type=xconnection.intern_atom('_NET_MOVERESIZE_WINDOW'),
                        data=(32, [X.NorthWestGravity | (1 << 8) | (1 << 9) | (2 << 12),
                                   left, top, 0, 0])),
                        event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                    xconnection.flush()
            except error.XError:
                continue
    except Exception:
        logging.exception('Could not anchor Whisker Menu')
    return True

GLib.timeout_add(100, check_whisker_position)
GLib.timeout_add(100, check_popup_focus)
GLib.timeout_add(250, check)
check()
GLib.MainLoop().run()
