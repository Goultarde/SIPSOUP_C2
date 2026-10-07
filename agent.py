import argparse
import os
import platform
import socket
import time

from sip import build, parse


def main():
    parser = argparse.ArgumentParser(description="Agent C2 SIP de laboratoire")
    parser.add_argument("--id", required=True)
    parser.add_argument("--server", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5060)
    args = parser.parse_args()
    secret = os.environ.get("SIP_C2_SECRET")
    if not secret:
        parser.error("SIP_C2_SECRET est requis")

    server = (args.server, args.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    sock.sendto(build("REGISTER", "c2", args.id, "online", secret), server)
    seen = set()
    commands = {
        "ping": lambda: "pong",
        "info": lambda: f"{platform.system()} {platform.release()} {platform.machine()}",
        "time": lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    while True:
        data, address = sock.recvfrom(65535)
        if address != server:
            continue
        try:
            method, target, sender, body = parse(data, secret, seen)
            if method == "MESSAGE" and target == args.id and sender == "c2" and body in commands:
                sock.sendto(build("MESSAGE", "c2", args.id, commands[body](), secret), server)
        except (UnicodeError, ValueError):
            continue


if __name__ == "__main__":
    main()
