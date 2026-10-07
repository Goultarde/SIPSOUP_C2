import argparse
import os
import select
import socket
import sys

from sip import build, parse


def main():
    parser = argparse.ArgumentParser(description="Serveur C2 SIP de laboratoire")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5060)
    args = parser.parse_args()
    secret = os.environ.get("SIP_C2_SECRET")
    if not secret:
        parser.error("SIP_C2_SECRET est requis")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.bind, args.port))
    agents, seen = {}, set()
    print(f"C2 SIP sur {args.bind}:{args.port} — commandes: list, send <agent> <ping|info|time>")
    while True:
        readable, _, _ = select.select((sock, sys.stdin), (), ())
        if sock in readable:
            try:
                data, address = sock.recvfrom(65535)
                method, target, sender, body = parse(data, secret, seen)
                if method == "REGISTER" and target == "c2":
                    agents[sender] = address
                    print(f"[{sender}] enregistre depuis {address[0]}:{address[1]}")
                elif method == "MESSAGE" and target == "c2":
                    print(f"[{sender}] {body}")
            except (UnicodeError, ValueError) as error:
                print(f"message refuse: {error}", file=sys.stderr)
        if sys.stdin in readable:
            parts = input("> ").split()
            if parts == ["list"]:
                print("\n".join(f"{name} {address[0]}:{address[1]}" for name, address in agents.items()) or "aucun agent")
            elif len(parts) == 3 and parts[0] == "send" and parts[2] in {"ping", "info", "time"}:
                if parts[1] not in agents:
                    print("agent inconnu")
                else:
                    sock.sendto(build("MESSAGE", parts[1], "c2", parts[2], secret), agents[parts[1]])
            elif parts:
                print("usage: list | send <agent> <ping|info|time>")


if __name__ == "__main__":
    main()
