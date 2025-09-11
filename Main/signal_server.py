# signal_server.py
import asyncio
from aiohttp import web

rooms = {}  # room -> set of websockets

async def ws_handler(request):
    room = request.query.get("room")
    if not room:
        return web.Response(text="room query param required", status=400)

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    peers = rooms.setdefault(room, set())
    peers.add(ws)
    print(f"[room {room}] client joined ({len(peers)} in room)")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                # relay to everyone else in room
                for peer in list(peers):
                    if peer is not ws:
                        await peer.send_str(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                print(f"ws connection closed with exception {ws.exception()}")
    finally:
        peers.discard(ws)
        if not peers:
            rooms.pop(room, None)
        print(f"[room {room}] client left ({len(peers)} in room)")

    return ws

app = web.Application()
app.add_routes([web.get("/ws", ws_handler)])

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
