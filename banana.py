import socket
import time
import sys
import threading

# ============== CONFIG ==============
SERVER = "localhost"
PORT = 6667
NICK = "banana"
ANICK = "banan"
IDENT = "banana"
REALNAME = "banana"
ADMINS = [
    "Admin1",
    "Administrator2",
]
PERFORM = [
    "VHOST <user> <pass>",
    "OPER <user> <pass>",
]
CHANNELS = "#banana"
JOIN_CHANNELS_DELAY = 3
# ===================================

VERSION = "1.0"

PING_INTERVAL = 60
LAST_CLIENT_PING = 0

# CTCP FLOOD PROTECTION
ctcp_count = 0
ctcp_block_until = 0

CTCP_LIMIT = 3
CTCP_BLOCK_TIME = 5


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


def is_admin(nick):
    return nick in ADMINS


def send_ctcp(sock, nick, command, payload=""):

    if payload:
        msg = f"\x01{command} {payload}\x01"
    else:
        msg = f"\x01{command}\x01"

    send(sock, f"PRIVMSG {nick} :{msg}")


def run():

    global LAST_CLIENT_PING
    global ctcp_count
    global ctcp_block_until

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

                nick = prefix.split("!")[0]


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


                    threading.Thread(
                        target=delayed_join,
                        daemon=True
                    ).start()


                    backoff = 1



                # ADMIN INVITE AUTO JOIN

                elif cmd == "INVITE":

                    if is_admin(nick):

                        channel = args[-1]

                        send(sock, f"JOIN {channel}")



                # CTCP RECEIVE

                elif cmd == "PRIVMSG" and "\x01" in line:

                    now = time.time()


                    if now < ctcp_block_until:
                        continue


                    msg = args[-1]

                    handled = False



                    # CTCP VERSION

                    if msg.startswith("\x01VERSION"):

                        reply = (
                            f"banana{VERSION} "
                            f"python{sys.version_info.major}."
                            f"{sys.version_info.minor}."
                            f"{sys.version_info.micro}"
                        )


                        send(
                            sock,
                            f"NOTICE {nick} :\x01VERSION {reply}\x01"
                        )


                        handled = True



                    # CTCP PING

                    elif msg.startswith("\x01PING"):

                        payload = msg[6:-1]


                        send(
                            sock,
                            f"NOTICE {nick} :\x01PING {payload}\x01"
                        )


                        handled = True



                    if handled:

                        ctcp_count += 1


                        if ctcp_count >= CTCP_LIMIT:

                            ctcp_block_until = now + CTCP_BLOCK_TIME
                            ctcp_count = 0



                # NORMAL PRIVMSG / ADMIN COMMANDS

                elif cmd == "PRIVMSG":

                    if len(args) < 2:
                        continue


                    message = args[-1]


                    if is_admin(nick):


                        if message == "!version":

                            send(
                                sock,
                                f"NOTICE {nick} :banana{VERSION} "
                                f"python{sys.version_info.major}."
                                f"{sys.version_info.minor}."
                                f"{sys.version_info.micro}"
                            )



                        elif message.startswith("!ctcpversion"):

                            parts = message.split()

                            if len(parts) >= 2:

                                send_ctcp(
                                    sock,
                                    parts[1],
                                    "VERSION"
                                )



                        elif message.startswith("!ctcpping"):

                            parts = message.split()

                            if len(parts) >= 2:

                                send_ctcp(
                                    sock,
                                    parts[1],
                                    "PING",
                                    str(int(time.time()))
                                )



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
