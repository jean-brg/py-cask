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
    def __init__(self, import_name: str, app_name: str = "Python-Cask-App", *args, **kwargs):
        super().__init__(import_name, *args, **kwargs)

        if getattr(sys, "frozen", False):
            self.root_path = sys._MEIPASS

        self.template_folder = os.path.join(self.root_path, "templates")
        self.static_folder = os.path.join(self.root_path, "static")
        self.app_name = self._safe_app_name(app_name) if app_name else "Python-Cask-App"
    
    # HELPER METHODS
    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
        
    def _init_instance(self) -> None:
        if not getattr(sys, "frozen", False):
            return

        seed_dir = os.path.join(sys._MEIPASS, "instance")
        if not os.path.exists(seed_dir):
            return

        user_dir = self.get_instance_path()
        for filename in os.listdir(seed_dir):
            dest = os.path.join(user_dir, filename)
            if not os.path.exists(dest):
                import shutil
                shutil.copy2(os.path.join(seed_dir, filename), dest)

    def _safe_app_name(self, raw_name) -> str:
        import re
        return re.sub(r"[^\w\s-]", "", raw_name).strip()

    # EXPORT METHODS
    def run_as_app(self, **kwargs):
        self._init_instance()
        target_port: int = self._get_free_port()
        icon_path: str = kwargs.get("icon") or ("./static/favicon.ico" if os.path.isfile("./static/favicon.ico") else None)

        if getattr(sys, "frozen", False) and kwargs.get("debug"):
            kwargs["debug"] = False

        flask_thread: threading.Thread = threading.Thread(
            target=lambda: self.run(host="127.0.0.1", port=target_port, debug=kwargs.get("debug", False), use_reloader=False),
            daemon=True,
            name=f"PyFlask Sever: {self.app_name}" if self.app_name else None
        )
        flask_thread.start()

        window = webview.create_window(self.app_name, f"http://127.0.0.1:{target_port}")
        window.events.closed += lambda: os._exit(0)
        webview.start(icon=icon_path)

    def get_instance_path(self, filename: str = "") -> str:
        if getattr(sys, 'frozen', False):
            if sys.platform == "darwin":
                base_instance = os.path.join(os.path.expanduser("~"), "Library", "Application Support", self.app_name, "instance")
            elif sys.platform == "win32":
                base_instance = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), self.app_name, "instance")
            else:
                base_instance = os.path.join(os.path.expanduser("~"), ".local", "share", self.app_name, "instance")
        else:
            base_instance = os.path.join(self.root_path, 'instance')

        os.makedirs(base_instance, exist_ok=True)
        return os.path.join(base_instance, filename) if filename else base_instance
    
    def read_instance_file(self, filename: str, default: str = "") -> str:
        path = self.get_instance_path(filename)
        if not os.path.exists(path):
            return default
        with open(path, "r") as f:
            return f.read()
