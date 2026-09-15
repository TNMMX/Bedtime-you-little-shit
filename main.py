#Bedtime you little shit v0.8

# Warning: this version of Byls contains AI code! <-- this will get replaced in the future (hopefully).

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import QTimer, Qt, QFile, QTextStream
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QSystemTrayIcon, QMenu, QMessageBox,
    QStyle
)


# Applying the Breeze theme was basically vibe coded. Please keep that in mind.
try:
    import breeze_pyside6
except ImportError:
    print("Error: Could not find 'breeze_pyside6.py' in the project folder!")
    sys.exit(1)

# Where scheduled time is stored
STATE_FILE = Path.home() / ".cache" / "bedtime.json"

# Read the saved shutdown time from disk, if any.
def load_target() -> datetime | None:
    if not STATE_FILE.exists():
        return None
    try:
        data = json.loads(STATE_FILE.read_text())
        target = datetime.fromisoformat(data["target"])
        if target > datetime.now():
            return target
        STATE_FILE.unlink(missing_ok=True)
    except Exception:
        STATE_FILE.unlink(missing_ok=True)
    return None


def save_target(target: datetime):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"target": target.isoformat()}))

# Remove any saved shutdown time (used on cancel or after shutting down).
def clear_target():
    STATE_FILE.unlink(missing_ok=True)


def do_shutdown():
    try:
        subprocess.run(["systemctl", "poweroff"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(
            ["notify-send", "-u", "critical", "Sleep Early",
             "Shutdown failed: not authorized. See setup notes for the polkit rule."],
            check=False
        )


def remaining_str(target: datetime) -> str:
    delta = target - datetime.now()
    total = int(delta.total_seconds())
    if total <= 0:
        return "0 min"
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"

#First window shown where I ask the user what they want ("What's up?"). User can answer with: ("I need to sleep early tonight.")
class StartWindow(QWidget):
    def __init__(self, app_controller):
        super().__init__()
        self.ctrl = app_controller
        self.setWindowTitle("What's up?")
        self.setFixedSize(320, 140)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn = QPushButton("I need to sleep early tonight.")
        btn.setMinimumHeight(50)
        btn.setFont(QFont("", 12))
        btn.clicked.connect(self.on_click)
        layout.addWidget(btn)

    def on_click(self):
        self.hide()
        self.ctrl.show_time_window()

# Lets the user pick an hour+minute for the shutdown.
class TimeWindow(QWidget):
    def __init__(self, app_controller):
        super().__init__()
        self.ctrl = app_controller
        self.setWindowTitle("When?")
        self.setFixedSize(280, 180)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)


        # Hour+minute spin boxes, pre-filled with 23:00. Might add a feature that saves previous days values and pre-fill the spin boxes with those instead.
        row = QHBoxLayout()
        self.hour = QSpinBox()
        self.hour.setRange(0, 23)
        self.hour.setValue(23)
        self.hour.setSuffix(" h")
        self.minute = QSpinBox()
        self.minute.setRange(0, 59)
        self.minute.setValue(0)
        self.minute.setSuffix(" m")
        row.addWidget(self.hour)
        row.addWidget(self.minute)
        layout.addLayout(row)

        ok = QPushButton("Okay")
        ok.clicked.connect(self.schedule)
        layout.addWidget(ok)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.close)
        layout.addWidget(cancel)

    # Build the target datetime from the chosen hour+minute, confirm, then persist it and start the countdown.
    def schedule(self):
        now = datetime.now()
        target = now.replace(
            hour=self.hour.value(),
            minute=self.minute.value(),
            second=0,
            microsecond=0
        )
        # If the chosen time has already passed today, assume tomorrow.
        if target <= now:
            target += timedelta(days=1)

        reply = QMessageBox.warning(
            self,
            "Confirm",
            f"The computer will shut down at {target.strftime('%H:%M')}.\n\n"
            "It will NOT wait for games, projects or unsaved work.\n"
            "Everything will be closed immediately.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Ok:
            return

        save_target(target)
        self.hide()
        self.ctrl.start_tray(target)

# Shows the current countdown to shutdown and lets the user cancel it.
# Cancel might get replaced with delay since the point is forcing you to sleep but either way no one wants file corrpution because a teenagers program shutdown your computer in the middle of important work.
class StatusWindow(QWidget):
    def __init__(self, app_controller, target: datetime):
        super().__init__()
        self.ctrl = app_controller
        self.target = target
        self.setWindowTitle("Shutdown scheduled")
        self.setFixedSize(300, 160)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFont(QFont("", 11))
        layout.addWidget(self.label)

        cancel = QPushButton("Cancel shutdown")
        cancel.setMinimumHeight(40)
        cancel.clicked.connect(self.cancel)
        layout.addWidget(cancel)

        self.update_label()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_label)
        self.timer.start(1000)

    def update_label(self):
        if not load_target():
            self.close()
            return
        self.label.setText(
            f"Shutdown at {self.target.strftime('%H:%M')}\n"
            f"Time left: {remaining_str(self.target)}"
        )

    def cancel(self):
        clear_target()
        self.ctrl.stop_everything()
        self.close()

# Owns app-wide state: the current target time, the tray icon, and the ticking timer that checks whether it's time to shut down. Also decides which window to show on startup depending on whether a schedule already exists on disk.
class Controller:
    def __init__(self, app: QApplication):
        self.app = app
        self.tray: QSystemTrayIcon | None = None
        self.target: datetime | None = None
        self.tick_timer = QTimer()
        self.tick_timer.timeout.connect(self.tick)
        self.warned = set()
        self.status_win = None
        self.start_win = None
        self.time_win = None

        # Resume an existing schedule, or create a new one.

        target = load_target()
        if target:
            self.start_tray(target, show_status=True)
        else:
            self.start_win = StartWindow(self)
            self.start_win.show()

    def show_time_window(self):
        self.time_win = TimeWindow(self)
        self.time_win.show()

    #Set the active target time, (re)build the tray icon if needed, and start the per-second countdown timer.
    def start_tray(self, target: datetime, show_status: bool = False):
        self.target = target
        self.warned.clear()

        if not self.tray:
            icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
            self.tray = QSystemTrayIcon(icon, self.app)
            self.tray.setToolTip("Byls – shutdown scheduled")

            menu = QMenu()
            show_action = QAction("Show status", self.app)
            show_action.triggered.connect(self.show_status)
            menu.addAction(show_action)

            cancel_action = QAction("Cancel shutdown", self.app)
            cancel_action.triggered.connect(self.cancel_from_tray)
            menu.addAction(cancel_action)

            menu.addSeparator()
            quit_action = QAction("Quit App (Cancels timer)", self.app)
            quit_action.triggered.connect(self.cancel_from_tray)
            menu.addAction(quit_action)

            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self.on_tray_click)
            self.tray.show()

        self.tick_timer.start(1000)

        if show_status:
            self.show_status()

    def show_status(self):
        if self.target:
            self.status_win = StatusWindow(self, self.target)
            self.status_win.show()

    # Left-click on the tray icon opens the status window.
    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_status()

    # Runs every second: fires warning notifications at 10/5/1 minutes remaining, and triggers the actual shutdown once time is up.
    def tick(self):
        if not self.target:
            self.stop_everything()
            return

        remaining = (self.target - datetime.now()).total_seconds()

        if remaining <= 0:
            self.tick_timer.stop()
            clear_target()
            do_shutdown()
            return

        for mins in (10, 5, 1):
            if mins not in self.warned and remaining <= mins * 60:
                self.warned.add(mins)
                self.notify(f"Shutdown in {mins} minute{'s' if mins > 1 else ''}!")

        if self.tray:
            self.tray.setToolTip(f"Shutdown in {remaining_str(self.target)}")

    # Show a tray balloon/notification with the given message.
    def notify(self, text: str):
        if self.tray:
            self.tray.showMessage("It's bedtime!", text, QSystemTrayIcon.MessageIcon.Warning, 8000)

    def cancel_from_tray(self):
        clear_target()
        self.stop_everything()

    # Tear down the timer and tray icon, clear any saved schedule, and quit the application entirely.
    def stop_everything(self):
        self.tick_timer.stop()
        if self.tray:
            self.tray.hide()
            self.tray = None
        clear_target()
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    # Keep the app running in the background (tray) even when no window is open.
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Byls")

    file = QFile(":/dark/stylesheet.qss") # You can switch between dark and light by editing this line to ":/light/stylesheet.qss" or ":/dark/stylesheet.qss"
    if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())
        file.close()

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Error", "System tray is not available.")
        return 1

    # Controller handles all app logic and decides which window(s) to show.
    _controller = Controller(app)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
