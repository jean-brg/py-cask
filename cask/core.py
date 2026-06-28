# IMPORTS
import os
import sys
import webview
import socket
from flask import Flask
import threading

# MAIN CLASS
class Cask(Flask):
    # NEW
    def __init__(self, import_name: str, app_name: str = "Python Cask App", *args, **kwargs):
        super().__init__(import_name, *args, **kwargs)
        self.template_folder=self._get_template_folder_path()
        self.static_folder=self._get_static_folder_path()
        self.app_name = app_name if app_name else "Python Cask App"
    
    # HELPER METHODS
    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]

    def _get_base_directory(self) -> str:
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))
    
    # MAIN METHODS
    def _get_static_folder_path(self) -> str:
        return os.path.join(self._get_base_directory(), 'static')

    def _get_template_folder_path(self) -> str:
        return os.path.join(self._get_base_directory(), 'templates')

    # EXPORT METHODS
    def run_as_app(self, **kwargs):
        target_port: int = self._get_free_port()
        icon_path: str = kwargs.get("icon") or ("./static/favicon.ico" if os.path.isfile("./static/favicon.ico") else None)

        flask_thread: threading.Thread = threading.Thread(
            target=lambda: self.run(host="127.0.0.1", port=target_port, debug=kwargs.get("debug", False), use_reloader=False),
            daemon=True,
            name=f"PyFlask Sever: {self.app_name}" if self.app_name else None
        )
        flask_thread.start()

        window = webview.create_window(self.app_name, f"http://127.0.0.1:{target_port}")
        window.events.closed += lambda: os._exit(0)
        webview.start(icon=icon_path)
