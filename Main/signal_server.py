import asyncio
from aiohttp import web

# Rooms => connected websockets
rooms = {}        # dict[str, set[WebSocketResponse]]
# Cache last signaling messages so late joiners can catch up
last_msgs = {}    # dict[str, list[str]]

async def ws_handler(request):
    room = request.query.get("room")
    if not room:
        return web.Response(text="room query param required", status=400)

    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)

    peers = rooms.setdefault(room, set())
    peers.add(ws)
    print(f"[room {room}] client joined ({len(peers)} in room)")

    # Re-send cached messages (offer/answer + candidates) to late joiners
    if room in last_msgs:
        for msg in last_msgs[room]:
            print(f"[room {room}] replaying cached: {msg[:60]}... to new peer")
            await ws.send_str(msg)

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                data = msg.data
                print(
                    f"[room {room}] received: {data[:80]}... "
                    f"(from {id(ws)}) relaying to {len(peers)-1} peers"
                )

                # Cache: keep latest offer/answer, and append all candidates
                buf = last_msgs.setdefault(room, [])
                if '"type": "offer"' in data or '"type": "answer"' in data:
                    buf.clear()
                    buf.append(data)
                elif '"type": "candidate"' in data:
                    buf.append(data)

                # Relay to everyone else in the room
                for peer in list(peers):
                    if peer is not ws:
                        await peer.send_str(data)

            elif msg.type == web.WSMsgType.ERROR:
                print(f"[room {room}] ws closed with error: {ws.exception()}")
    finally:
        peers.discard(ws)
        if not peers:
            rooms.pop(room, None)
            last_msgs.pop(room, None)
        print(f"[room {room}] client left ({len(peers)} in room)")

    return ws

app = web.Application()
app.add_routes([web.get("/ws", ws_handler)])

if __name__ == "__main__":
    print("[signal_server] starting on 0.0.0.0:8080")
    web.run_app(app, host="0.0.0.0", port=8080)
