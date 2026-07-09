# IMPORTS
import os
import sys
import subprocess
import tomllib
import argparse
import ast
import shutil
import re

# TOML FUNCTIONS
def find_toml() -> dict:
    """Finds cask.toml config file and return the data"""
    toml_path = os.path.join(os.getcwd(), "cask.toml")
    if not os.path.exists(toml_path):
        print("Error: No cask.toml found in current directory.")
        sys.exit(1)
    with open(toml_path, "rb") as f:
        return tomllib.load(f)

def validate_toml(config: dict) -> None:
    """Validates necessary fields of the cask.toml config file"""
    app = config.get("app", {})
    if not app.get("name"):
        print("Error: cask.toml missing [app] name")
        sys.exit(1)
    
    sanitized = re.sub(r"[^\w\s-]", "", app["name"]).strip()
    if not sanitized:
        print(f"Error: app name '{app['name']}' is empty after sanitization.")
        print("Please use alphanumeric characters, spaces, or hyphens.")
        sys.exit(1)

    if not app.get("entry"):
        print("Error: cask.toml missing [app] entry")
        sys.exit(1)
    if not os.path.exists(app["entry"]):
        print(f"Error: entry file '{app['entry']}' not found")
        sys.exit(1)

# HELPER FUNCTIONS
def _invalid_cask_name_fallback(reason: str) -> str:
    """Prints a warning and returns the default app name"""
    print(f"Warning: Could not find proper name due to: {reason}, using \"MyCaskApp\" as default.")
    print('You can override this in interactive mode or set the name in [app] in cask.toml.')
    return "MyCaskApp"

def find_cask_app_name(entry_file: str) -> str:
    """Uses the entry file's syntax tree to find the app_name of the Cask app"""
    if not entry_file or not os.path.isfile(entry_file):
        return _invalid_cask_name_fallback("No entry file found to find name")
    try:
        with open(entry_file) as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not isinstance(node.value, ast.Call):  # guards against x = 1 style assignments
                continue
            func = node.value.func
            is_cask_call = (
                (isinstance(func, ast.Name) and func.id == "Cask") or
                (isinstance(func, ast.Attribute) and func.attr == "Cask")
            )
            if not is_cask_call:
                continue
            for keyword in node.value.keywords:
                if keyword.arg != "app_name":
                    continue
                if isinstance(keyword.value, ast.Constant):
                    return keyword.value.value
                else:
                    return _invalid_cask_name_fallback("app_name is not a string literal")
        return "MyCaskApp"
    except SyntaxError:
        return _invalid_cask_name_fallback("Could not parse entry file")
    except Exception:
        return _invalid_cask_name_fallback("Unexpected error reading entry file")

# COMMAND: BUILD
def build_pyinstaller_cmd(config: dict, args: argparse.Namespace) -> list[str]:
    """Uses app config and cli args to generate pyinstaller CLI command"""
    app = config.get("app", {})
    data = config.get("data", {})

    cmd = [
        "pyinstaller",
        "--windowed",
        "--noconfirm",
        "--name", app["name"],
        "--paths", ".",
    ]

    if app.get("icon"):
        cmd += ["--icon", app["icon"]]

    if args.onefile:
        cmd.append("--onefile")

    path_separator = ";" if sys.platform == "win32" else ":"
    for source, dest in data.items():
        cmd += ["--add-data", f"{source}{path_separator}{dest}"]

    cmd.append(app["entry"])
    return cmd

def run_pyinstaller_cmd(cmd: list[str], verbose: bool) -> tuple[bool, int]:
    """Runs the pyinstaller cmd and parses the output"""
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    error_count = 0

    for line in process.stdout:
        if verbose:
            print(line.strip())
        else:
            line = ' '.join(line.split(" ")[1:]).rstrip()

            if line.startswith("INFO:"):
                truncated = line[:77] + '...' if len(line) > 80 else line
                print(f"\r  {truncated.strip()}", end="", flush=True)

            elif line.startswith("WARNING:"):
                print(f"\n  {line.strip()}")

            elif line.startswith("ERROR:"):
                error_count += 1
                print(f"\n  {line.strip()}")

    process.wait()
    print()

    return process.returncode == 0, error_count

def cmd_build(args: argparse.Namespace) -> None:
    """Uses CLI args to package Flask app into executable"""
    if shutil.which("pyinstaller") is None:
        print("Error: PyInstaller is not installed or not in PATH.")
        print("Install it with: pip install pyinstaller")
        sys.exit(1)

    config = find_toml()
    validate_toml(config)
    cmd = build_pyinstaller_cmd(config, args)

    app_name = config.get("app", {}).get("name", "")
    cask_webview_app_name = find_cask_app_name(config.get("app", {}).get("entry", ""))
    print(f"Building {app_name} ({cask_webview_app_name}):")

    build_success, error_count = run_pyinstaller_cmd(cmd, args.verbose)

    if build_success:
        print(f"Built ./dist/{app_name} successfully")
    else:
        print(f"Build of ./dist/{app_name} failed with {error_count} error{'s' if error_count else ''}")

    if not args.keep:
        try:
            if os.path.isdir(f"./build/{app_name}"):
                shutil.rmtree(f"./build/{app_name}")
                if os.path.isdir("./build") and not os.listdir("./build"):
                    os.rmdir("./build")
            if os.path.exists(f"./{app_name}.spec"):
                os.remove(f"./{app_name}.spec")
        except FileNotFoundError:
            pass

# COMMAND: INIT
def discover_defaults() -> dict:
    """Scans the current directory to find default values for cask.toml"""
    
    entry = next((f for f in ["main.py", "app.py", "run.py"] if os.path.isfile(f)), "")
    app_name = find_cask_app_name(entry)

    icon = next((f for f in [
        f"static/caskicon.{'icns' if sys.platform == 'darwin' else 'ico'}", 
        f"static/favicon.{'icns' if sys.platform == 'darwin' else 'ico'}", 
        "static/icon.ico", 
        "static/icon.png"
    ] if os.path.isfile(f)), "")

    data = []
    for folder in ["static", "templates", "assets"]:
        if os.path.isdir(folder):
            data.append(folder)
    
    if os.path.isdir("instance") and os.listdir("instance"):
        data.append("instance")

    return {"app_name": app_name, "entry": entry, "icon": icon, "data": data}

def generate_toml(app_name: str, entry: str, icon: str, data: list[str]) -> str:
    """Generate cask.toml content given the app properties and data files"""
    lines = [
        "# Generated by cask init",
        "[app]",
        f'name = "{app_name}"',
        f'entry = "{entry}"',
    ]
    if icon:
        lines.append(f'icon = "{icon}"')
    lines.append("")

    if data:
        lines.append("[data]")
        for folder in data:
            lines.append(f'"{folder}" = "{folder}"')
        lines.append("")

    return "\n".join(lines)

def cmd_init(args: argparse.Namespace) -> None:
    """Creates the cask.toml file given the CLI args and discovered values"""
    defaults = discover_defaults()
    toml_exists = os.path.isfile("cask.toml")
    content = ""

    if not args.interactive:
        if toml_exists and not args.force:
            print("Error: cask.toml already exists. Use --force to overwrite.")
            sys.exit(1)

        print("Discovered:")
        print(f"  app name:  {defaults['app_name']}")
        print(f"  entry:     {defaults['entry'] or '(none found)'}")
        print(f"  icon:      {defaults['icon'] or '(none found)'}")
        print(f"  data:      {', '.join(f'{d}/' for d in defaults['data']) or '(none found)'}")
        print()

        content = generate_toml(
            defaults["app_name"], defaults["entry"],
            defaults["icon"], defaults["data"]
        )

    else:
        print("Interactive Mode:")
        print("Press enter to use the [Suggested value], or enter your own value")
        app_name = input(f"App name [{defaults['app_name']}]: ").strip() or defaults["app_name"]
        entry    = input(f"Entry file [{defaults['entry'] or 'main.py'}]: ").strip() or defaults["entry"] or "main.py"
        icon     = input(f"Icon [{defaults['icon'] or 'none'}]: ").strip() or defaults["icon"]
        
        default_data_str = ", ".join(f"{d}/" for d in defaults["data"]) or "none"
        data_input = input(f"Data folders [{default_data_str}]: ").strip()
        if data_input:
            data = [d.strip().rstrip("/") for d in data_input.split(",") if d.strip()]
        else:
            data = defaults["data"]

        content = generate_toml(app_name, entry, icon, data)

        if toml_exists and not args.force:
            answer = input("\ncask.toml already exists. Overwrite? [y/N]: ").strip().lower()
            if answer != "y":
                print("\nPreview of generated cask.toml:")
                print("--------------------------------")
                print(content)
                return

    with open("cask.toml", "w") as f:
        f.write(content)
    print("Generated cask.toml!")

# MAIN FUNCTION
def main() -> None:
    """Main Cask CLI function"""
    # Parser
    parser = argparse.ArgumentParser(prog="cask", description="Cask - Flask app packager")
    subparsers = parser.add_subparsers(dest="command")

    # Command: build
    build_parser = subparsers.add_parser("build", help="Package the app using cask.toml")
    build_parser.add_argument("--onefile", action="store_true", help="Packages app as a single binary")
    build_parser.add_argument("--keep", action="store_true", help="Keeps ./build/<app_name>/* and ./<app_name>.spec after building app")
    build_parser.add_argument("--verbose", action="store_true", help="Prints all of the output lines from the pyinstaller command")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Generate a cask.toml for this project")
    init_parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode for guidance")
    init_parser.add_argument("--force", action="store_true", help="Force creates cask.toml file, overwrites existing cask.toml")

    # Args
    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "init":
        cmd_init(args)
    else:
        parser.print_help()

# MAIN RUNNER
if __name__ == "__main__":
    main()
