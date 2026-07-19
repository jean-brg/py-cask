# Cask CLI Reference

The Cask CLI simplifies the build and development process for Cask apps. All commands are run from your project directory (where `cask.toml` lives).


## Commands
| Command | Description |
|---------|-------------|
| `cask init` | Generate a `cask.toml` for the current project |
| `cask build` | Package the app into an executable |
| `cask run` | Run the app in development mode |


### cask init
Scans the current directory for common Flask project files and generates a `cask.toml` config file.

```bash
cask init [-i | --interactive] [--force]
```

| Flag | Description |
|------|-------------|
| `-i`, `--interactive` | Prompt for each value instead of auto-discovering them |
| `--force` | Overwrite an existing `cask.toml` without prompting |

### Discovery
| Field | What Cask looks for |
|-------|-------------------|
| App name | The `app_name` argument in your `Cask()` call, parsed statically. Falls back to `"MyCaskApp"` with a warning if it can't be resolved. |
| Entry file | Searches in order: `main.py`, `app.py`, `run.py` |
| Icon | Searches in order: `static/caskicon.icns/.ico`, `static/favicon.icns/.ico`, `static/icon.ico`, `static/icon.png` |
| Data folders | Any of `static/`, `templates/`, `assets/` that exist. `instance/` only if it contains files. |

In `--interactive` mode, each discovered value is shown as a default in brackets. Press enter to accept it or type in a value to override. If `cask.toml` already exists and `--force` isn't set, you'll be asked before overwriting — declining shows a preview instead.

### cask.toml
```toml
[app]
name = "My App"       # Required — Window title and executable name
entry = "main.py"     # Required — Path to your main application file
icon = "static/caskicon.icns"  # Optional - Icon used in taskbar

[data]
# "source" = "destination" pairs, relative to cask.toml
"static" = "static"
"templates" = "templates"
# "instance" = "instance"   # uncomment to bundle seed files (e.g. a default database)
```

The `name` property must contain only alphanumeric characters, spaces, or hyphens.

The `instance/` folder is for runtime data in development. When packaged, Cask automatically maps it to the correct OS app data folder (`~/Library/Application Support/<app name>/` on macOS, `%APPDATA%/<app name>/` on Windows, `~/.local/share/<app name>/` on Linux).

## cask build
Reads `cask.toml` and packages your app into an executable using PyInstaller. Requires `pip install pyinstaller`.

```bash
cask build [--onefile] [--keep] [--verbose]
```

| Flag | Description |
|------|-------------|
| `--onefile` | Bundle into a single binary. Not recommended on macOS — slower to launch. |
| `--keep` | Keep `./build/` and `.spec` after building. |
| `--verbose` | Print full PyInstaller output instead of the condensed view. |

Output goes to `./dist/<app name>/`. Build artifacts are cleaned up automatically unless `--keep` is set.

> PyInstaller builds for the current OS only. Run `cask build` on each target OS to distribute cross-platform.


## cask run
Runs your app using the entry file in `cask.toml`.

```bash
cask run [--debug]
```

| Flag | Description |
|------|-------------|
| `--debug` | Run via `flask run` with debug mode and auto-reload. Opens in the browser, not the Cask window. |


## Common Errors

| Error | Fix |
|-------|-----|
| `No cask.toml found` | Run from the directory containing `cask.toml` |
| `missing [app] name` / `missing [app] entry` | Add the missing field to `[app]` in `cask.toml` |
| `entry file '<path>' not found` | Check the `entry` path is correct and relative to `cask.toml` |
| `icon file '<path>' not found` | Fix the `icon` path or remove the field to use default Python icon |
| `data source '<path>' not found` | Check the source path in `[data]` exists before building |
| `app name empty after sanitization` | Use only alphanumeric characters, spaces, or hyphens in `name` |
| `PyInstaller is not installed` | Run `pip install pyinstaller` |
| `cask.toml already exists` | Use `--force` to overwrite, or `-i` to preview first |
