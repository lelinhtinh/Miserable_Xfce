#!/usr/bin/env bash
case ${1:-} in
 --taskmanager) xfce4-terminal --title="Task Manager — btop" -x btop &;;
 --filemanager) exo-open --launch FileManager &;;
 --webbrowser) exo-open --launch WebBrowser &;;
 --terminal) exo-open --launch TerminalEmulator &;;
 --texteditor) exo-open --launch TextEditor &;;
 --calendar) "$HOME/.local/bin/eww" open --toggle calendarevent;;
esac
"$HOME/.local/bin/eww" close sidebar
"$HOME/.local/bin/eww" close sysstat
