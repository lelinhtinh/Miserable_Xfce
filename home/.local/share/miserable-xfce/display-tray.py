#!/usr/bin/env python3
"""Display switcher for XFCE's notification area (GTK 3 / XEmbed)."""
from concurrent.futures import ThreadPoolExecutor
import logging
from pathlib import Path
import signal
import subprocess

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk

from display_status import notify, read_status

ASSETS = Path(__file__).resolve().parent / 'assets'


class DisplayTray:
    def __init__(self):
        self.worker = ThreadPoolExecutor(max_workers=1)
        self.refreshing = False
        self.announce_pending = False
        self.switching = False
        self.status = None
        self.icon = Gtk.StatusIcon(visible=False)
        self.icon.set_name('miserable-display')
        self.icon.set_from_icon_name('video-display')
        self.icon.set_title('Màn hình thật / ảo')
        self.icon.set_tooltip_text('Đang đọc trạng thái màn hình…')
        self.menu = Gtk.Menu()
        self.current = Gtk.MenuItem(label='Đang đọc trạng thái màn hình…')
        self.current.set_sensitive(False)
        self.menu.append(self.current)
        self.menu.append(Gtk.SeparatorMenuItem())
        self.toggle = Gtk.MenuItem(label='Chuyển màn hình thật / ảo')
        self.toggle.set_sensitive(False)
        self.toggle.connect('activate', self.switch)
        self.menu.append(self.toggle)
        self.show_status = Gtk.MenuItem(label='Thông báo trạng thái hiện tại')
        self.show_status.connect('activate', lambda *_: self.refresh(announce=True))
        self.menu.append(self.show_status)
        self.menu.show_all()
        self.icon.connect('activate', lambda *_: self.popup(0, Gtk.get_current_event_time()))
        self.icon.connect('popup-menu', lambda _, button, time: self.popup(button, time))
        self.icon.set_visible(True)
        GLib.timeout_add_seconds(3, self.refresh)
        self.refresh()

    def popup(self, button, time):
        self.refresh()
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, self.icon, button, time)

    def refresh(self, announce=False):
        self.announce_pending |= announce
        if not self.refreshing and not self.switching:
            self.refreshing = True
            # Never block GTK on XRandR, configuration reads or notification clients.
            self.worker.submit(self.query)
        return True

    def query(self):
        try:
            status, error = read_status(), None
        except Exception as exc:
            status, error = None, f'Không đọc được trạng thái màn hình: {exc}'
            logging.exception('Could not read display status')
        GLib.idle_add(self.update, status, error)

    def update(self, status, error):
        self.refreshing = False
        self.status = status
        label = error or status['label']
        if self.announce_pending:
            self.announce_pending = False
            self.worker.submit(notify, label, error=bool(error))
        self.current.set_label(label)
        self.icon.set_tooltip_text(label)
        if error:
            self.icon.set_from_icon_name('dialog-warning')
        elif status['mode'] in ('physical', 'virtual'):
            self.icon.set_from_file(str(ASSETS / f'display-{status["mode"]}.svg'))
        else:
            self.icon.set_from_icon_name('video-display')
        target = 'ảo' if status and status['target'] == 'virtual' else 'thật'
        self.toggle.set_label(f'Chuyển sang màn hình {target}' if status else 'Chuyển màn hình thật / ảo')
        self.toggle.set_sensitive(bool(status and status['can_switch']) and not self.switching)
        if status and not status['can_switch']:
            self.toggle.set_tooltip_text(f'Cổng {status["target_output"]} chưa kết nối')
        else:
            self.toggle.set_tooltip_text(None)
        return False

    def switch(self, *_):
        if self.switching or not self.status:
            return
        self.switching = True
        self.toggle.set_sensitive(False)
        self.show_status.set_sensitive(False)
        self.current.set_label('Đang chuyển màn hình…')
        self.worker.submit(self.run_switch)

    def run_switch(self):
        try:
            # Let the existing helper choose from fresh state and serialize with hotkeys.
            subprocess.run([str(Path.home() / '.local/bin/toggle-rustdesk-display')], check=True)
        except (OSError, subprocess.SubprocessError):
            logging.exception('Could not switch display')
        finally:
            GLib.idle_add(self.switched)

    def switched(self):
        self.switching = False
        self.show_status.set_sensitive(True)
        self.refresh()
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    tray = DisplayTray()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: Gtk.main_quit() or False)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: Gtk.main_quit() or False)
    Gtk.main()
    tray.worker.shutdown(wait=False)
