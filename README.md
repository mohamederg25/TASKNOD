# TaskNudge

A small, friendly Windows task reminder that nudges you at the right moment, then gets out of the way.

![TaskNudge icon](assets/tasknudge.png)

## What it does

- **Gentle random nudges** between a configurable interval, weighted by priority, urgency and how long a task has been waiting.
- **Exact-time reminders** for tasks with a specific due time.
- **Snooze, skip or complete** straight from the popup; recurring tasks move themselves to the next occurrence.
- **Quiet hours** and a **morning summary** so reminders fit your day.
- **Progress view** with today/week completions, a streak and a seven-day chart.
- **Lives in the system tray**, starts minimized at sign-in if you want, and keeps a single instance running.
- **Stays quiet during fullscreen apps** such as games, videos and presentations.

Tasks, settings and logs are stored locally in `%APPDATA%\TaskNudge`.

## Run from source

Requires Windows 10/11 and Python 3.10+.

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

To keep data somewhere else (for example a USB stick), set `TASKNUDGE_DATA_DIR` before starting.

### Command line

```text
python main.py                    # open normally
python main.py --minimized        # start in the tray only
python main.py --install-autostart
python main.py --remove-autostart
python main.py --version
```

Auto-start uses the current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` entry, so no administrator rights are needed.

## Build a standalone EXE

Run `build.bat`. It creates `.venv` if needed, installs dependencies and produces `dist\TaskNudge.exe` with PyInstaller. Move the EXE to a permanent folder before enabling "Start with Windows".

## Tests

The test suite uses only the standard library's `unittest`; no extra packages are required.

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

It covers storage and repeat handling, statistics, configuration recovery, date helpers, and the scheduler's timed/random/quiet/paused/summary decisions.

## Project layout

```text
main.py                     entry point, single-instance socket, logging
tasknudge/
  application.py            wires tray, windows, scheduler and popups
  scheduler.py              reminder timing and task selection
  storage.py                SQLite persistence for tasks and completions
  config.py                 JSON settings with normalization and recovery
  models.py, util.py        data model and shared date helpers
  ui/                       task list, dialogs, stylesheet and popups
  avatar.py, sound.py       generated character face and chime
tests/                      unittest suite for the non-GUI core
TaskNudge.spec, build.bat   PyInstaller packaging
```
