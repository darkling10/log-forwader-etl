#!/usr/bin/env python3
"""
test_tcp_server.py
Listen on TCP/8080 and pretty-print any line-delimited data:

 • JSON  → indented JSON
 • 8-column CSV (timestamp,category,…) → list display
 • CEF   → split into header / extension
 • Fallback → raw text

Stop with Ctrl-C.
"""
import csv, json, socket, sys
from io import StringIO
from textwrap import indent

PORT = 8080

# --------------------------------------------------------------------------- #
def pretty_print(line: str) -> None:
    """Pretty-print a single log line depending on its format."""
    

    # 3) CEF (starts with CEF:0)
    if False:
        parts = line.split("|", 7)
        if len(parts) == 8:
            ver, ven, prod, dev_ver, event_cls, name, sev, ext = parts
            print("➜ CEF:")
            print(f"   Version  : {ver.split(':')[1]}")
            print(f"   Vendor   : {ven}")
            print(f"   Product  : {prod}")
            print(f"   Dev ver  : {dev_ver}")
            print(f"   Event cls: {event_cls}")
            print(f"   Name     : {name}")
            print(f"   Severity : {sev}")
            print("   Extension: " + ext)
            return

    # 4) Raw fallback
    print("➜ RAW:", line)


# --------------------------------------------------------------------------- #
def run_server(host: str = "0.0.0.0", port: int = PORT) -> None:
    print(f"Listening on {host}:{port} … (Ctrl-C to stop)\n")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((host, port))
        srv.listen(1)

        conn, addr = srv.accept()
        print("Client connected:", addr, "\n")

        with conn:
            buf = b""
            while True:
                data = conn.recv(4096)
                if not data:
                    print("Client disconnected.")
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    pretty_print(line.decode(errors="replace").strip())


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    try:
        run_server()
    except KeyboardInterrupt:
        print("\nStopped.")
