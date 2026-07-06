# Banana v1.0 Python3 Lightweight IRC Bot
#
# Features:
# - ADMIN invite-only channel joining
# - VHOST support via PERFORM: /vhost <user> <pass>
# - CTCP support: VERSION and PING with flood protection
#
# Run:
#  nohup python3 banana.py &

import socket
import time
import sys
import threading

# ================= CONFIG =================
SERVER = "irc.server.org"
PORT = 6667

NICK = "banana"
ANICK = "banana_"
IDENT = "banana"
REALNAME = "banana"

CHANNELS = "#banana"

JOIN_CHANNELS_DELAY = 10

ADMIN = "yournick"

VERSION = (
    "banana1.0 "
    f"python{sys.version_info.major}."
    f"{sys.version_info.minor}."
    f"{sys.version_info.micro}"
)

PERFORM = [
    "VHOST user password",
]

# =========================================

PING_INTERVAL = 60
LAST_CLIENT_PING = 0

ctcp_count = 0
ctcp_block_until = 0


def send(sock, msg):
    sock.send((msg + "\r\n").encode("utf-8"))
    print(">>", msg)


def parse(line):
    prefix = ""
    if line.startswith(":"):
        prefix, line = line[1:].split(" ", 1)

    if " :" in line:
        head, trail = line.split(" :", 1)
        args = head.split()
        args.append(trail)
    else:
        args = line.split()

    return prefix, args


def connect():
    s = socket.socket()
    s.connect((SERVER, PORT))

    send(s, f"NICK {NICK}")
    send(s, f"USER {IDENT} 0 * :{REALNAME}")

    return s


def run():
    global LAST_CLIENT_PING, ctcp_count, ctcp_block_until

    sock = connect()
    buffer = ""
    backoff = 1

    def delayed_join():
        time.sleep(JOIN_CHANNELS_DELAY)
        for ch in CHANNELS.split():
            send(sock, f"JOIN {ch}")

    while True:
        try:
            data = sock.recv(4096)
            if not data:
                raise ConnectionError("Disconnected")

            buffer += data.decode(errors="ignore")
            lines = buffer.split("\r\n")
            buffer = lines.pop()

            for line in lines:
                if not line:
                    continue

                print("<<", line)

                prefix, args = parse(line)
                cmd = args[0] if args else ""

                # KEEPALIVE
                if cmd == "PING":
                    send(sock, f"PONG {args[1]}")

                # NICK IN USE
                elif "433" in args:
                    send(sock, f"NICK {ANICK}")

                # CONNECTED
                elif "001" in args:
                    for cmdline in PERFORM:
                        send(sock, cmdline)

                    threading.Thread(target=delayed_join, daemon=True).start()
                    backoff = 1

                # CTCP HANDLING (ONLY VERSION + PING)
                elif cmd == "PRIVMSG" and "\x01" in line:
                    now = time.time()

                    if now < ctcp_block_until:
                        continue

                    nick = prefix.split("!")[0]
                    msg = args[-1]

                    handled = False

                    if msg.startswith("\x01VERSION"):
                        send(sock, f"NOTICE {nick} :\x01VERSION {VERSION}\x01")
                        handled = True

                    elif msg.startswith("\x01PING"):
                        payload = msg[6:-1]
                        send(sock, f"NOTICE {nick} :\x01PING {payload}\x01")
                        handled = True

                    if handled:
                        ctcp_count += 1

                    if ctcp_count >= 2:
                        ctcp_block_until = now + 5
                        ctcp_count = 0

            # CLIENT KEEPALIVE
            now = time.time()
            if now - LAST_CLIENT_PING > PING_INTERVAL:
                send(sock, f"PING {NICK}")
                LAST_CLIENT_PING = now

        except Exception as e:
            print("reconnecting:", e)

            try:
                sock.close()
            except:
                pass

            print(f"retry in {backoff}s")
            time.sleep(backoff)

            backoff = min(backoff * 2, 60)
            sock = connect()


run()
