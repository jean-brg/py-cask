# Cask Core API Reference

`core.py` provides the `Cask` class, a simple replacement for Flask's `Flask` object that adds desktop window management and instance file handling.

## Class

### `class cask.Cask(import_name, app_name='MyCaskApp')`
A Flask subclass that runs your web app as a native desktop application via pywebview.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `import_name` | `str` | The name of the application package, passed to Flask. Usually `__name__`. | — |
| `app_name` | `str` | The name shown in the window title bar and used for the instance folder path. | `'MyCaskApp'` |

**Note:** `app_name` is sanitized on init — only alphanumeric characters, spaces, and hyphens are allowed. A `ValueError` is raised if the name is empty after sanitization.


## App Methods

### `run_as_app(**kwargs)`
Starts the Flask server in a background thread and opens the app in a native pywebview window. This is a blocking call — code after it will not run until the window is closed.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `icon` | `str` | Path to the app icon. Falls back to `static/caskicon.icns` or `static/caskicon.ico` if not set. | `None` |
| `debug` | `bool` | Runs Flask in debug mode. Automatically disabled when running as a packaged app. | `False` |
| `window_options` | `dict` | Additional options passed directly to `webview.create_window()`, such as `width`, `height`, `resizable`, and `fullscreen`. | `{}` |

**Note:** If Flask does not respond within 10 seconds, a timeout error page is shown in the window instead.

### `set_menu(menu)`
Sets the application menu shown in the menu bar. Must be called before `run_as_app()`. For reference: [pywebview menu docs](https://pywebview.flowrl.com/api/#webview-menu)

| Parameter | Type | Description |
|-----------|------|-------------|
| `menu` | `list` | A list of `Menu` objects. Import `Menu`, `MenuAction`, and `MenuSeparator` from `cask` directly. |

**Note:** The menu is static after the app starts — pywebview does not support runtime menu updates.

### `get_instance_file_path(filename='')`
Returns the correct path to a file in the instance folder, regardless of whether the app is running in development or as a packaged executable.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `filename` | `str` | The filename to resolve inside the instance folder. If omitted, returns the instance folder path itself. | `''` |

**Returns:** `str` — the full path to the file or folder.  
**Note:** The instance folder is created on first call. On macOS it is `~/Library/Application Support/<app name>/instance/`, on Windows `%APPDATA%/<app name>/instance/`, and on Linux `~/.local/share/<app name>/instance/`. In development it resolves to `instance/` relative to your entry file.

### `read_from_instance_file(filename, default='', mode='r')`
Reads and returns the content of a file in the instance folder.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `filename` | `str` | The filename to read from the instance folder. | — |
| `default` | `str` | The value returned if the file does not exist yet. | `''` |
| `mode` | `str` | The file open mode, e.g. `'r'` for text or `'rb'` for binary. | `'r'` |

**Returns:** `str` — the file content, or `default` if the file does not exist.

### `write_to_instance_file(filename, content, mode='w')`
Writes content to a file in the instance folder, creating the file and any parent directories if needed.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `filename` | `str` | The filename to write to in the instance folder. | — |
| `content` | `str` | The content to write. | — |
| `mode` | `str` | The file open mode, e.g. `'w'` to overwrite or `'a'` to append. | `'w'` |

### `open_file(allowed_extensions=('*.*',), allow_multiple=False)`
Opens a native file picker dialog and returns the selected file path(s).

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `allowed_extensions` | `tuple[str]` | File extensions to filter by, e.g. `('*.png', '*.jpg')`. | `('*.*',)` |
| `allow_multiple` | `bool` | Whether the user can select more than one file. | `False` |

**Returns:** `tuple[str]` — the selected file paths, or `None` if cancelled.  
**Raises:** `RuntimeError` — if called before `run_as_app()`.

### `save_file(filename='untitled', directory='/')`
Opens a native save file dialog and returns the chosen destination path.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `filename` | `str` | The default filename shown in the dialog. | `'untitled'` |
| `directory` | `str` | The directory the dialog opens in. | `'/'` |

**Returns:** `str` — the full destination path chosen by the user, or `None` if cancelled.  
**Raises:** `RuntimeError` — if called before `run_as_app()`.  
**Note:** This returns the intended save path — the file is not written automatically. Use the returned path with `open()` or `write_to_instance_file()` to write the file.

### `open_folder()`
Opens a native folder picker dialog and returns the selected folder path.

**Returns:** `str` — the selected folder path, or `None` if cancelled.  
**Raises:** `RuntimeError` — if called before `run_as_app()`.


## Window Methods
These methods require an active window and must be called after `run_as_app()`. Calling them before will raise a `RuntimeError`.

### `prompt(message, default='')`
Shows a browser prompt dialog and returns the user's input.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `message` | `str` | The message shown in the dialog. | — |
| `default` | `str` | The default value pre-filled in the input field. | `''` |

**Returns:** `str` — the text entered by the user, or `None` if cancelled.

### `alert(message)`
Shows a browser alert dialog.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | The message shown in the dialog. |

### `confirm(message)`
Shows a browser confirmation dialog with OK and Cancel buttons.

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | The message shown in the dialog. |

**Returns:** `bool` — `True` if the user clicked OK, `False` if cancelled.

### `evaluate_js(code)`
Executes arbitrary JavaScript in the webview and returns the result.

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | `str` | The JavaScript code to execute. |

**Returns:** the JavaScript return value as a Python object, or `None`.

### `minimize()`
Minimizes the app window.

### `restore()`
Restores a minimized window to its previous size and position.

### `toggle_fullscreen()`
Toggles the window between fullscreen and its previous size.

### `resize(width, height)`
Resizes the window to the given dimensions.

| Parameter | Type | Description |
|-----------|------|-------------|
| `width` | `int` | The new window width in pixels. |
| `height` | `int` | The new window height in pixels. |

### `set_title(title)`
Changes the window title bar text at runtime.

| Parameter | Type | Description |
|-----------|------|-------------|
| `title` | `str` | The new window title. |

### `hide()`
Hides the window without closing the app.

### `show()`
Shows a window that was previously hidden with `hide()`.
