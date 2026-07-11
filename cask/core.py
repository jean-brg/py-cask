# IMPORTS
import os
import re
import shutil
import socket
import sys
import threading
import time

import webview
from flask import Flask

# MAIN CLASS
class Cask(Flask):
    """
    A Flask subclass that packages a web app as a desktop application.

    Extends Flask with desktop-specific functionality including native window
    management via pywebview, cross-platform instance file handling, and
    PyInstaller compatibility.

    Args:
        import_name: The name of the application package, passed to Flask (usually `__name__`).
        app_name: The name displayed in the window title and used for the
                  instance folder. Defaults to 'MyCaskApp'.

    Example:
        app = Cask(__name__, app_name="My App")

        @app.route('/')
        def home():
            return render_template('home.html')

        if __name__ == '__main__':
            app.run_as_app()
    """
    def __init__(self, import_name: str, app_name: str = "MyCaskApp", *args, **kwargs) -> None:
        super().__init__(import_name, *args, **kwargs)

        self._menu = None
        self._base_instance: str = ""
        self.is_instance_initiated: bool = False
        self.is_running_as_package: bool = getattr(sys, "frozen", False)
        self.app_name: str = self._safe_app_name(app_name) if app_name else "MyCaskApp"

        if self.is_running_as_package:
            self.root_path = sys._MEIPASS

        self.template_folder: str = os.path.join(self.root_path, "templates")
        self.static_folder: str = os.path.join(self.root_path, "static")
    
    # HELPER METHODS
    def _get_free_port(self) -> int:
        """Finds and returns a free port to host the app on"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return s.getsockname()[1]
        
    def _init_instance(self) -> None:
        """Initializes the instance directory and sets the `_base_instance` path"""
        self._base_instance = self._get_instance_path()

        if not self.is_running_as_package:
            return

        instance_source_dir = os.path.join(self.root_path, "instance")
        if not os.path.exists(instance_source_dir):
            return

        os.makedirs(self._base_instance, exist_ok=True)
        for filename in os.listdir(instance_source_dir):
            dest = os.path.join(self._base_instance, filename)
            if not os.path.exists(dest):
                shutil.copy2(os.path.join(instance_source_dir, filename), dest)

    def _safe_app_name(self, raw_name: str) -> str:
        """Returns a safe name for the app with proper formatting"""
        sanitized = re.sub(r"[^\w\s-]", "", raw_name).strip()
        if not sanitized:
            print(f"Error: app_name '{raw_name}' is empty after sanitization.")
            print("Please use alphanumeric characters, spaces, or hyphens.")
            sys.exit(1)
        return sanitized
    
    def _get_default_icon(self) -> str | None:
        """Returns the file path to the app icon, if found"""
        ext = "icns" if sys.platform == "darwin" else "ico"
        path = os.path.join(self.static_folder, f"caskicon.{ext}")
        return path if os.path.isfile(path) else None
    
    def _get_instance_path(self) -> str:
        """Returns the path to the instance folder, based on the system and app state"""
        if self.is_running_as_package:
            if sys.platform == "darwin":
                return os.path.join(os.path.expanduser("~"), "Library", "Application Support", self.app_name, "instance")
            elif sys.platform == "win32":
                return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), self.app_name, "instance")
            else:
                return os.path.join(os.path.expanduser("~"), ".local", "share", self.app_name, "instance")
        return os.path.join(self.root_path, "instance")
    
    def _wait_for_flask(self, port: int, timeout: float = 10.0) -> bool:
        """Pings the Flask server until it responds or timeout is reached"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return True
            except OSError:
                time.sleep(0.05)
        return False

    def _flask_timeout_error_page(self) -> str:
        """Returns an HTML error page for when Flask fails to start"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: system-ui; display: flex; justify-content: center; 
                    align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }
                .card { background: white; padding: 2rem; border-radius: 8px; 
                        max-width: 500px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
                h2 { color: #c0392b; margin-top: 0; }
                details { margin-top: 1rem; }
                summary { cursor: pointer; color: #666; font-size: 0.9rem; }
                pre { background: #f0f0f0; padding: 1rem; border-radius: 4px; 
                    font-size: 0.8rem; overflow-x: auto; white-space: pre-wrap; }
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Failed to start</h2>
                <p>The application server did not respond within 10 seconds.</p>
            </div>
        </body>
        </html>
        """

    # EXPORT METHODS
    def run_as_app(self, **kwargs) -> None:
        """Main method to run Cask app in app window"""
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

        if self._wait_for_flask(target_port):
            window = webview.create_window(self.app_name, f"http://127.0.0.1:{target_port}", menu=self._menu)
        else:
            window = webview.create_window(self.app_name, html=self._flask_timeout_error_page(), menu=self._menu)

        window.events.closed += lambda: os._exit(0)
        webview.start(icon=icon_path)

    def get_instance_file_path(self, filename: str = "") -> str:
        """Returns the file path for a file in `instance`"""
        if not self.is_instance_initiated:
            self._init_instance()
            self.is_instance_initiated = True

        return os.path.join(self._base_instance, filename) if filename else self._base_instance
    
    def read_from_instance_file(self, filename: str, default: str = "", mode: str = "r") -> str:
        """Reads and returns the content of a file in `instance`"""
        path = self.get_instance_file_path(filename)
        if not os.path.exists(path):
            return default
        with open(path, mode) as f:
            return f.read()
        
    def write_to_instance_file(self, filename: str, content: str, mode: str = "w") -> None:
        """Writes the content of a file in `instance`, creating the file if needed"""
        path = self.get_instance_file_path(filename)
        with open(path, mode) as f:
            f.write(content)

    def set_menu(self, menu: list) -> None:
        """Sets the native application menu (Cannot be changed at run time)"""
        self._menu = menu
