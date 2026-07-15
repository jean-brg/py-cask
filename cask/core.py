# IMPORTS
import os
import re
import shutil
import socket
import sys
import threading
import time
import json
from html import escape

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
        self._events = {}
        self.window = None
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
        """
        Finds and returns a free port to host the app on.
        Note: May very rarely lead to a race condition if other apps are being launched in parallel
        """
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
            src = os.path.join(instance_source_dir, filename)
            dest = os.path.join(self._base_instance, filename)
            if os.path.exists(dest):
                continue
            if os.path.isdir(src):
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)

    def _safe_app_name(self, raw_name: str) -> str:
        """Returns a safe name for the app with proper formatting"""
        sanitized = re.sub(r"[^\w\s-]", "", raw_name).strip()
        if not sanitized:
            raise ValueError(
                f"app_name '{raw_name}' is empty after sanitization. "
                "Please use alphanumeric characters, spaces, or hyphens."
            )
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

    def _flask_timeout_error_page(self, error_detail: str = "", show_details: bool = False) -> str:
        """Returns an HTML error page for when Flask fails to start"""
        details_html = ""
        if show_details and error_detail:
            details_html = f"""
                    <details>
                        <summary>Show details</summary>
                        <pre>{escape(error_detail)}</pre>
                    </details>"""

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: system-ui; display: flex; justify-content: center; 
                    align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }}
                .card {{ background: white; padding: 2rem; border-radius: 8px; 
                        max-width: 500px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
                h2 {{ color: #c0392b; margin-top: 0; }}
                details {{ margin-top: 1rem; }}
                summary {{ cursor: pointer; color: #666; font-size: 0.9rem; }}
                pre {{ background: #f0f0f0; padding: 1rem; border-radius: 4px; 
                    font-size: 0.8rem; overflow-x: auto; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Failed to start</h2>
                <p>The application server did not respond within 10 seconds.</p>
                {details_html}
            </div>
        </body>
        </html>
        """
    
    def _require_window(self) -> None:
        """Checks if the window exists before using it"""
        if not hasattr(self, 'window') or self.window is None:
            raise RuntimeError("Window is not available yet. Call run_as_app() first.")

    # WINDOW METHODS
    def prompt(self, message: str, default: str = "") -> str | None:
        """Shows a native web prompt dialog and returns the user's input"""
        self._require_window()
        return self.window.evaluate_js(f"prompt({json.dumps(message)}, {json.dumps(default)})")

    def alert(self, message: str) -> None:
        """Shows a native web alert dialog"""
        self._require_window()
        self.window.evaluate_js(f"alert({json.dumps(message)})")

    def confirm(self, message: str) -> bool | None:
        """Shows a native confirmation dialog"""
        self._require_window()
        return self.window.evaluate_js(f"confirm({json.dumps(message)})")

    def evaluate_js(self, code: str) -> any:
        """Runs arbitrary JavaScript in the webview and returns the result"""
        self._require_window()
        return self.window.evaluate_js(code)
    
    def minimize(self) -> None:
        """Minimizes the app window"""
        self._require_window()
        self.window.minimize()

    def restore(self) -> None:
        """Restores a minimized or maximized window"""
        self._require_window()
        self.window.restore()

    def toggle_fullscreen(self) -> None:
        """Toggles fullscreen mode"""
        self._require_window()
        self.window.toggle_fullscreen()

    def resize(self, width: int, height: int) -> None:
        """Resizes the window to the given dimensions in pixels"""
        self._require_window()
        self.window.resize(width, height)

    def set_title(self, title: str) -> None:
        """Changes the window title at runtime"""
        self._require_window()
        self.window.title = title

    def hide(self) -> None:
        """Hides the window without closing it"""
        self._require_window()
        self.window.hide()

    def show(self) -> None:
        """Shows a hidden window"""
        self._require_window()
        self.window.show()

    def set_events(self, **kwargs) -> None:
        """Sets one or more window event handlers."""
        if on_close := kwargs.get("on_close"):
            self._events["closed"] = on_close
        if on_closing := kwargs.get("on_closing"):
            self._events["closing"] = on_closing
        if on_shown := kwargs.get("on_shown"):
            self._events["shown"] = on_shown
        if on_minimize := kwargs.get("on_minimize"):
            self._events["minimized"] = on_minimize
        if on_restore := kwargs.get("on_restore"):
            self._events["restored"] = on_restore
        if on_resize := kwargs.get("on_resize"):
            self._events["resized"] = on_resize

    # APP METHODS
    def run_as_app(self, **kwargs) -> None:
        """Main method to run Cask app in app window"""
        target_port: int = self._get_free_port()
        icon_path = kwargs.get("icon", "") or self._get_default_icon()
        window_options = kwargs.get("window_options", {})
        debug = kwargs.get("debug", False)

        if self.is_running_as_package and debug:
            debug = False

        show_error_details = kwargs.get("show_error_details", debug)

        flask_error: list[Exception] = []

        def _run_flask():
            try:
                self.run(host="127.0.0.1", port=target_port, debug=debug, use_reloader=False)
            except Exception as e:
                flask_error.append(e)

        flask_thread: threading.Thread = threading.Thread(
            target=_run_flask,
            daemon=True,
            name=f"PyFlask Server: {self.app_name}"
        )
        flask_thread.start()

        if self._wait_for_flask(target_port):
            self.window = webview.create_window(self.app_name, f"http://127.0.0.1:{target_port}", menu=self._menu, **window_options)
        else:
            error_detail = str(flask_error[0]) if flask_error else "No response within 10 seconds."
            self.window = webview.create_window(
                self.app_name, 
                html=self._flask_timeout_error_page(error_detail, show_error_details),
                menu=self._menu, 
                **window_options
            )

        def _handle_closed(self) -> None:
            if handler := self._events.get("closed"):
                handler()
            sys.exit(0)

        for event, handler in self._events.items():
            getattr(self.window.events, event) += handler

        self.window.events.closed += _handle_closed
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
        """Writes the content of a file in `instance`, creating the file (and any parent dirs) if needed"""
        path = self.get_instance_file_path(filename)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, mode) as f:
            f.write(content)

    def set_menu(self, menu: list) -> None:
        """Sets the native application menu (Cannot be changed at run time)"""
        self._menu = menu

    def open_file(self, allowed_extensions: tuple[str] = ("*.*",), allow_multiple: bool = False) -> tuple[str] | None:
        """Opens a native file picker and returns the selected file path(s)"""
        self._require_window()
        return self.window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=allow_multiple,
            file_types=(f"Accepted file ({';'.join(list(allowed_extensions))})",)
        )

    def save_file(self, filename: str = "untitled", directory: str = "/") -> str | None:
        """Opens a native save file dialog and returns the chosen path"""
        self._require_window()
        return self.window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=directory,
            save_filename=filename
        )

    def open_folder(self) -> str | None:
        """Opens a native folder picker and returns the selected folder path"""
        self._require_window()
        result = self.window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None
