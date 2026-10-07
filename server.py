import argparse
import os
import readline
import shlex
import socket
import threading
import time

from sip import build, parse

ROOT_COMMANDS = ("help", "list", "interact", "send", "clear", "quit")
AGENT_COMMANDS = ("ping", "info", "hostname", "user", "time", "disk")
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[38;5;51m"
PURPLE = "\033[38;5;135m"
GREEN = "\033[38;5;82m"
RED = "\033[38;5;203m"
GOLD = "\033[38;5;220m"


def prompt(agent=None, safe=False):
    name = f"{agent}" if agent else "COMMAND"
    color = CYAN if agent else PURPLE
    if safe:
        color, end = f"\001{color}{BOLD}\002", f"\001{RESET}\002"
    else:
        color, end = color + BOLD, RESET
    return f"{color}╭─[ SIP::{name} ]\n╰─❯{end} "


def banner(bind, port):
    print("\033[2J\033[H", end="")
    print(f"""{PURPLE}{BOLD}
   ███████╗██╗██████╗       ██████╗██████╗
   ██╔════╝██║██╔══██╗     ██╔════╝╚════██╗
   ███████╗██║██████╔╝     ██║      █████╔╝
   ╚════██║██║██╔═══╝      ██║     ██╔═══╝
   ███████║██║██║          ╚██████╗███████╗
   ╚══════╝╚═╝╚═╝           ╚═════╝╚══════╝{RESET}
   {DIM}Secure Interactive Protocol · Command Console{RESET}

   {GREEN}● ONLINE{RESET}   {DIM}UDP{RESET} {bind}:{port}   {DIM}HMAC-SHA256 · anti-replay{RESET}
   {PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
   {DIM}Tapez {RESET}{BOLD}help{RESET}{DIM} pour ouvrir la palette de commandes.{RESET}
""")


def show_help(agent=False):
    rows = [(name, "Diagnostic distant") for name in AGENT_COMMANDS] + [("back", "Fermer la session")] if agent else [
        ("list", "Afficher les agents actifs"),
        ("interact <agent>", "Ouvrir une console interactive"),
        ("send <agent> <cmd>", "Envoyer une commande directe"),
        ("clear", "Redessiner la console"),
        ("quit", "Arrêter le serveur"),
    ]
    print(f"\n  {GOLD}{BOLD}PALETTE DE COMMANDES{RESET}")
    print(f"  {PURPLE}╭{'─' * 52}╮{RESET}")
    for command, description in rows:
        print(f"  {PURPLE}│{RESET}  {CYAN}{command:<24}{RESET} {DIM}{description:<25}{RESET} {PURPLE}│{RESET}")
    print(f"  {PURPLE}╰{'─' * 52}╯{RESET}\n")


def show_agents(agents):
    print(f"\n  {GOLD}{BOLD}AGENTS  {RESET}{DIM}{len(agents)} actif(s){RESET}")
    print(f"  {PURPLE}╭{'─' * 24}┬{'─' * 25}╮{RESET}")
    print(f"  {PURPLE}│{RESET} {BOLD}{'IDENTITÉ':<22}{RESET} {PURPLE}│{RESET} {BOLD}{'ADRESSE SIP':<23}{RESET} {PURPLE}│{RESET}")
    print(f"  {PURPLE}├{'─' * 24}┼{'─' * 25}┤{RESET}")
    if agents:
        for name, address in agents.items():
            print(f"  {PURPLE}│{RESET} {GREEN}●{RESET} {name:<20} {PURPLE}│{RESET} {address[0]}:{address[1]:<16} {PURPLE}│{RESET}")
    else:
        print(f"  {PURPLE}│{RESET} {DIM}{'En attente de connexion…':<22}{RESET} {PURPLE}│{RESET} {'—':<23} {PURPLE}│{RESET}")
    print(f"  {PURPLE}╰{'─' * 24}┴{'─' * 25}╯{RESET}\n")


def setup_readline(agents, state):
    readline.parse_and_bind("set editing-mode emacs")
    readline.parse_and_bind("tab: complete")
    def complete(text, index):
        words = (*AGENT_COMMANDS, "help", "back") if state["agent"] else (*ROOT_COMMANDS, *agents)
        return ([word for word in words if word.startswith(text)] + [None])[index]

    readline.set_completer(complete)


def receive(sock, secret, agents, seen, state):
    while True:
        try:
            data, address = sock.recvfrom(65535)
            method, target, sender, body = parse(data, secret, seen)
            if method == "REGISTER" and target == "c2":
                agents[sender] = address
                message = f"{GREEN}◆ LINK{RESET}  {BOLD}{sender}{RESET}  {DIM}{address[0]}:{address[1]}{RESET}"
            elif method == "MESSAGE" and target == "c2":
                message = f"{CYAN}◀ RECV{RESET}  {BOLD}{sender}{RESET}  {body}"
            else:
                continue
        except (UnicodeError, ValueError) as error:
            message = f"{RED}✖ DROP{RESET}  {error}"
        except OSError:
            return
        line = readline.get_line_buffer()
        stamp = time.strftime("%H:%M:%S")
        print(f"\r\033[2K{DIM}{stamp}{RESET}  {message}\n{prompt(state['agent'])}{line}", end="", flush=True)


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
    agents, seen, state = {}, set(), {"agent": None}
    setup_readline(agents, state)
    banner(args.bind, args.port)
    threading.Thread(target=receive, args=(sock, secret, agents, seen, state), daemon=True).start()
    while True:
        try:
            parts = shlex.split(input(prompt(state["agent"], safe=True)))
        except (EOFError, KeyboardInterrupt):
            print("\nAu revoir.")
            return
        if state["agent"] and parts in (["back"], ["exit"]):
            state["agent"] = None
            print(f"{DIM}Session fermée.{RESET}")
        elif state["agent"] and parts == ["help"]:
            show_help(agent=True)
        elif state["agent"] and len(parts) == 1 and parts[0] in AGENT_COMMANDS:
            agent = state["agent"]
            sock.sendto(build("MESSAGE", agent, "c2", parts[0], secret), agents[agent])
        elif state["agent"] and parts:
            print("Commande refusée. Tapez 'help' ou 'back'.")
        elif parts == ["list"]:
            show_agents(agents)
        elif parts == ["help"]:
            show_help()
        elif len(parts) == 2 and parts[0] == "interact":
            if parts[1] in agents:
                state["agent"] = parts[1]
                print(f"\n{GREEN}  ◆ SESSION OUVERTE{RESET}  {BOLD}{parts[1]}{RESET}\n{DIM}  help affiche les commandes · back ferme la session{RESET}\n")
            else:
                print(f"Agent inconnu: {parts[1]}")
        elif parts == ["clear"]:
            banner(args.bind, args.port)
        elif parts in (["quit"], ["exit"]):
            print("Au revoir.")
            return
        elif len(parts) == 3 and parts[0] == "send" and parts[2] in AGENT_COMMANDS:
            if parts[1] not in agents:
                print(f"Agent inconnu: {parts[1]}")
            else:
                sock.sendto(build("MESSAGE", parts[1], "c2", parts[2], secret), agents[parts[1]])
        elif parts:
            print("Commande inconnue. Tapez 'help'.")


if __name__ == "__main__":
    main()
