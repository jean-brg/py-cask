# IMPORTS
import os
import sys
import subprocess
import tomllib
import argparse

# HELPER FUNCTIONS
def find_toml() -> dict:
    toml_path = os.path.join(os.getcwd(), "cask.toml")
    if not os.path.exists(toml_path):
        print("Error: No cask.toml found in current directory.")
        sys.exit(1)
    with open(toml_path, "rb") as f:
        return tomllib.load(f)

def validate_toml(config: dict) -> None:
    app = config.get("app", {})
    if not app.get("name"):
        print("Error: cask.toml missing [app] name")
        sys.exit(1)
    if not app.get("entry"):
        print("Error: cask.toml missing [app] entry")
        sys.exit(1)
    if not os.path.exists(app["entry"]):
        print(f"Error: entry file '{app['entry']}' not found")
        sys.exit(1)

def build_pyinstaller_cmd(config: dict) -> list[str]:
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

    path_seperator = ";" if sys.platform == "win32" else ":"
    for source, dest in data.items():
        cmd += ["--add-data", f"{source}{path_seperator}{dest}"]

    cmd.append(app["entry"])
    return cmd

def cmd_build(args) -> None:
    config = find_toml()
    validate_toml(config)
    cmd = build_pyinstaller_cmd(config)
    subprocess.run(cmd)

# MAIN FUNCTION
def main() -> None:
    parser = argparse.ArgumentParser(prog="cask", description="Cask - Flask app packager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("build", help="Package the app using cask.toml")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()