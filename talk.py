import asyncio
import websockets
import json

connected = {}

def user_list():
    return list(connected.values())

async def broadcast(message):
    data = json.dumps(message)
    tasks = []
    for ws in list(connected.keys()):
        try:
            tasks.append(ws.send(data))
        except Exception:
            pass
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def handle(ws):
    name = None
    try:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("type") != "join" or not data.get("username", "").strip():
            await ws.send(json.dumps({"type": "error", "text": "Send a join message with a username first."}))
            return

        name = data["username"].strip()

        if name in connected.values():
            await ws.send(json.dumps({"type": "error", "text": f"Username '{name}' is already taken."}))
            return

        connected[ws] = name
        print(f"[+] {name} joined  ({len(connected)} online)")

        await broadcast({"type": "system", "text": f"{name} joined the chat"})
        await broadcast({"type": "users", "list": user_list()})

        async for raw in ws:
            data = json.loads(raw)
            if data.get("type") == "chat" and data.get("text", "").strip():
                msg = {"type": "chat", "sender": name, "text": data["text"].strip()}
                print(f"[{name}] {data['text'].strip()}")
                await broadcast(msg)

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        if ws in connected:
            left = connected.pop(ws)
            print(f"[-] {left} left  ({len(connected)} online)")
            await broadcast({"type": "system", "text": f"{left} left the chat"})
            await broadcast({"type": "users", "list": user_list()})

async def main():
    print("=" * 50)
    print("  CHAT SERVER")
    print("=" * 50)
    print()
    print("  Server is running on port 5000")
    print("  Share your Replit URL with friends so they")
    print("  can connect from any device / network.")
    print()
    print("  Waiting for connections...")
    print("=" * 50)
    print()

    async with websockets.serve(handle, "0.0.0.0", 5000):
        await asyncio.Future()

asyncio.run(main())
