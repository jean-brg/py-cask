# IMPORTS
import os
import re
import shutil
import socket
import sys
import threading

import webview
from flask import Flask

# MAIN CLASS
class Cask(Flask):
    def __init__(self, import_name: str, app_name: str = "MyCaskApp", *args, **kwargs):
        super().__init__(import_name, *args, **kwargs)

        self._base_instance = ""
        self.is_instance_initiated = False
        self.is_running_as_package = getattr(sys, "frozen", False)
        self.app_name = self._safe_app_name(app_name) if app_name else "MyCaskApp"

        if self.is_running_as_package:
            self.root_path = sys._MEIPASS

        self.template_folder = os.path.join(self.root_path, "templates")
        self.static_folder = os.path.join(self.root_path, "static")
    
    # HELPER METHODS
    def _get_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
        
    def _init_instance(self) -> None:
        # Set the base instance only if instance is initialized
        self._base_instance = self._get_instance_path()

        # If app is running as Python, use local path
        if not self.is_running_as_package:
            return

        # If no instance was bundled, do not copy files
        instance_source_dir = os.path.join(self.root_path, "instance")
        if not os.path.exists(instance_source_dir):
            return

        # Copy instance file from bundle and set self._base_instance property
        os.makedirs(self._base_instance, exist_ok=True)
        for filename in os.listdir(instance_source_dir):
            dest = os.path.join(self._base_instance, filename)
            if not os.path.exists(dest):
                shutil.copy2(os.path.join(instance_source_dir, filename), dest)

    def _safe_app_name(self, raw_name) -> str:
        return re.sub(r"[^\w\s-]", "", raw_name).strip()
    
    def _get_default_icon(self) -> str | None:
        ext = "icns" if sys.platform == "darwin" else "ico"
        path = os.path.join(self.static_folder, f"caskicon.{ext}")
        return path if os.path.isfile(path) else None
    
    def _get_instance_path(self) -> str:
        if self.is_running_as_package:
            if sys.platform == "darwin":
                return os.path.join(os.path.expanduser("~"), "Library", "Application Support", self.app_name, "instance")
            elif sys.platform == "win32":
                return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), self.app_name, "instance")
            else:
                return os.path.join(os.path.expanduser("~"), ".local", "share", self.app_name, "instance")
        return os.path.join(self.root_path, "instance")

    # EXPORT METHODS
    def run_as_app(self, **kwargs):
        target_port: int = self._get_free_port()
        icon_path = self._get_default_icon()

        if self.is_running_as_package and kwargs.get("debug"):
            kwargs["debug"] = False

        flask_thread: threading.Thread = threading.Thread(
            target=lambda: self.run(host="127.0.0.1", port=target_port, debug=kwargs.get("debug", False), use_reloader=False),
            daemon=True,
            name=f"PyFlask Server: {self.app_name}"
        )
        flask_thread.start()

        window = webview.create_window(self.app_name, f"http://127.0.0.1:{target_port}")
        window.events.closed += lambda: os._exit(0)
        webview.start(icon=icon_path)

    def get_instance_file_path(self, filename: str = "") -> str:
        if not self.is_instance_initiated:
            self._init_instance()
            self.is_instance_initiated = True

        return os.path.join(self._base_instance, filename) if filename else self._base_instance
    
    def read_from_instance_file(self, filename: str, default: str = "", mode: str = "r") -> str:
        path = self.get_instance_file_path(filename)
        if not os.path.exists(path):
            return default
        with open(path, mode) as f:
            return f.read()
        
    def write_to_instance_file(self, filename: str, content: str, mode: str = "w") -> None:
        path = self.get_instance_file_path(filename)
        with open(path, mode) as f:
            f.write(content)
