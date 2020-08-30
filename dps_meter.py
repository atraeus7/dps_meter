import os
import sys
import re
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import threading
import time
import datetime
import dateutil.parser
import numpy as np
import pathlib

hit_tag = re.compile('.*Your.*hit.*')
damage_tag = re.compile(
    '([0-9]+-[0-9]+-[0-9A-Z]+:[0-9]+:[0-9]+\.[0-9A-Z]+)(.* )([0-9]+ )(.*\w+)')

window_size = 5
time_window = 60

damage_data = []
time_data = []
previous_bin_time = 0
previous_time = 0
total_damage = 0
bin_time = 1
max_damage = 0


def get_datadir() -> pathlib.Path:
    """
    Returns a parent directory path
    where persistent application data can be stored.

    # linux: ~/.local/share
    # macOS: ~/Library/Application Support
    # windows: C:/Users/<USER>/AppData/Roaming
    """

    home = pathlib.Path.home()

    if sys.platform == "win32":
        return home / "AppData/LocalLow"
    elif sys.platform == "linux":
        return home / ".local/share"
    elif sys.platform == "darwin":
        return home / "Library/Application Support"


def find_log() -> str:
    # Find the most recent version of the log and return it
    path = os.path.join(get_datadir(), r'Art+Craft\Crowfall\CombatLogs')
    for root, separator, files in os.walk(path):
        joined_paths = [os.path.join(root, f) for f in files]
        highest_timestamp = 0
        for f in joined_paths:
            timestamp = os.path.getmtime(f)
            if highest_timestamp < timestamp:
                most_recent_file = f
                highest_timestamp = timestamp

    file_label.setText(datetime.datetime.fromtimestamp(
        highest_timestamp).ctime())
    return f


def mouseMoved(evt):
    mousePoint = p.vb.mapSceneToView(evt[0])
    label.setText("<span style='color: white'> DPS = %0.2f</span>" %
                  (mousePoint.y()))


def moving_average(data):
    i = 0
    moving_averages = []
    while i < len(data) - window_size + 1:
        this_window = data[i: i + window_size]
        window_average = sum(this_window) / window_size
        moving_averages.append(window_average)
        i += 1

    return moving_averages


def update():
    global curve, curve2, p, damage_data, time_data, previous_bin_time, previous_time, total_damage, bin_time, max_damage

    current_pos = f.tell()
    a = f.readline()
    if (a == '' or a[-1] != '\n'):
        f.seek(current_pos, 0)

    else:
        match = hit_tag.search(a)
        if match:
            damage_text = match.group(0)
            damage = damage_tag.search(damage_text)
            damage_time = damage.group(1)
            damage_number = int(damage.group(3))
            damage_type = damage.group(4)

            t = dateutil.parser.parse(damage_time)
            t = t.timestamp()

            if previous_time != 0:
                if t-previous_time > bin_time:
                    if total_damage > max_damage:
                        max_damage = total_damage
                    damage_data.append(total_damage)
                    previous_bin_time = previous_bin_time + bin_time
                    time_data.append(previous_bin_time)
                    total_damage = 0

                    # Find moving average
                    ma = moving_average(damage_data)

                    curve.setData(time_data, damage_data)
                    curve2.setData(
                        time_data[window_size-1:], ma, pen=pg.mkPen('g', width=1))
                    p.setXRange(previous_bin_time -
                                time_window, previous_bin_time)
                    p.setYRange(0, max_damage)

                    previous_time = t
            else:
                previous_time = t

            total_damage = total_damage + damage_number

    app.processEvents()


app = QtGui.QApplication([])
w = QtGui.QMainWindow()
cw = pg.GraphicsLayoutWidget()
file_label = pg.LabelItem(justify="right")
label = pg.LabelItem(justify="left")
cw.addItem(label, row=0, col=0)
cw.addItem(file_label, row=0, col=1)
w.show()

w.resize(800, 600)
w.setCentralWidget(cw)
w.setWindowTitle('adCrowfall DPS Meter')

p = cw.addPlot(title="DPS", row=1, col=0, colspan=2)
curve = p.plot()
curve2 = p.plot()

proxy = pg.SignalProxy(p.scene().sigMouseMoved, rateLimit=30, slot=mouseMoved)

recent_file = find_log()
f = open(recent_file)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(20)


# Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        sys.exit(app.exec_())
