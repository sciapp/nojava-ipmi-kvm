import os
import signal

try:
    from typing import Text, Tuple  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    pass

import sys
try:
    from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
    qt_installed = True
except ImportError:
    qt_installed = False

if qt_installed:
    class VncBrowserWidget(QtWebEngineWidgets.QWebEngineView):
        def __init__(self, url):
            # type: (Text) -> None
            super().__init__()
            self._url = url
            self._init_ui()

        def _init_ui(self):
            # type: () -> None
            self.load(QtCore.QUrl(self._url))


    def run_vnc_browser(url, hostname, window_size):
        # type: (Text, Text, Tuple[int, int]) -> bool
        app = QtWidgets.QApplication(sys.argv)
        # Ensure that the rest of the application can terminate (-> Docker container)
        app.aboutToQuit.connect(lambda: os.kill(os.getpid(), signal.SIGTERM))
        vnc_browser_window = VncBrowserWidget(url)
        vnc_browser_window.setWindowTitle("nojava-ipmi-kvm [{}]".format(hostname))
        vnc_browser_window.setFixedSize(*window_size)
        vnc_browser_window.show()
        # Let the Python interpreter run every 500 ms to handle signals like SIGTERM
        timer = QtCore.QTimer()
        timer.start(500)
        timer.timeout.connect(lambda: None)
        return bool(app.exec_() == 0)
