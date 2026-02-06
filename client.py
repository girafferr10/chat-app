"""
CHAT CLIENT
-----------
Run this script on any computer to connect to the chat server.

Usage:
  python client.py

It will ask you for:
  1. The server URL  (the Replit URL of whoever is hosting)
  2. Your username
"""

import asyncio
import websockets
import json
import sys
import threading

async def receive_messages(ws):
    try:
        async for raw in ws:
            data = json.loads(raw)

            if data["type"] == "chat":
                print(f"\r  {data['sender']}: {data['text']}")
                print("  You: ", end="", flush=True)

            elif data["type"] == "system":
                print(f"\r  ** {data['text']} **")
                print("  You: ", end="", flush=True)

            elif data["type"] == "users":
                print(f"\r  Online: {', '.join(data['list'])}")
                print("  You: ", end="", flush=True)

            elif data["type"] == "error":
                print(f"\r  [ERROR] {data['text']}")
                print("  You: ", end="", flush=True)

    except websockets.exceptions.ConnectionClosed:
        print("\n  Disconnected from server.")
        sys.exit(0)

async def run():
    print()
    print("=" * 50)
    print("  CHAT CLIENT")
    print("=" * 50)
    print()

    url = input("  Server URL (Replit URL): ").strip()
    if not url:
        print("  No URL provided. Exiting.")
        return

    if url.startswith("http://"):
        url = "ws://" + url[7:]
    elif url.startswith("https://"):
        url = "wss://" + url[8:]
    elif not url.startswith("ws://") and not url.startswith("wss://"):
        url = "wss://" + url

    if url.endswith("/"):
        url = url[:-1]

    name = input("  Your username: ").strip()
    if not name:
        print("  No username provided. Exiting.")
        return

    print()
    print(f"  Connecting to {url} ...")

    try:
        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"type": "join", "username": name}))

            print("  Connected! Type your messages below.")
            print("  Type /quit to leave.")
            print("-" * 50)
            print()

            recv_task = asyncio.create_task(receive_messages(ws))

            loop = asyncio.get_event_loop()
            while True:
                text = await loop.run_in_executor(None, lambda: input("  You: "))
                if text.strip().lower() == "/quit":
                    print("  Leaving chat...")
                    break
                if text.strip():
                    await ws.send(json.dumps({"type": "chat", "text": text.strip()}))

            recv_task.cancel()

    except Exception as e:
        print(f"  Could not connect: {e}")
        print("  Make sure the server URL is correct and the server is running.")

asyncio.run(run())
