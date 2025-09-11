# chess_multiplayer.py
import os, sys, json, asyncio, chess, pygame, random, string
from threading import Thread
from aiohttp import ClientSession, WSMsgType
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate

# ---------- Board & assets (match offline) ----------
WIDTH, HEIGHT = 800, 800
FPS = 60
TILE_W, TILE_H = 84, 84
OFFSET_X, OFFSET_Y = 55, 60
PIECE_SCALE = 0.9
TWEAK_X, TWEAK_Y = 0, 5

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "audio")

SIGNAL_HOST = "127.0.0.1"
SIGNAL_PORT = 8080

# ---------- Small UI helpers ----------
def center_text(surf, text, y, font, color=(255,255,255)):
    t = font.render(text, True, color); r = t.get_rect(center=(WIDTH//2,y)); surf.blit(t, r)

def random_room_code(n=5):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def ask_host_or_join(screen):
    font = pygame.font.SysFont("arial", 30)
    while True:
        screen.fill((15,18,22))
        center_text(screen, "Press  H  to Host   or   J  to Join", HEIGHT//2, font)
        center_text(screen, "ESC to cancel", HEIGHT//2 + 60, pygame.font.SysFont("arial", 22), (180,180,180))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_h: return "host"
                if e.key == pygame.K_j: return "join"

def ask_room_code(screen):
    font = pygame.font.SysFont("arial", 28)
    code = ""
    while True:
        screen.fill((15,18,22))
        center_text(screen, "Enter ROOM CODE:", 220, font)
        box = pygame.Rect(WIDTH//2 - 160, 270, 320, 46)
        pygame.draw.rect(screen, (40,45,52), box, border_radius=10)
        pygame.draw.rect(screen, (100,110,120), box, 2, border_radius=10)
        txt = font.render(code, True, (220,220,220))
        screen.blit(txt, (box.x+10, box.y+8))
        center_text(screen, "Enter = Join   |   ESC = Cancel", 330, pygame.font.SysFont("arial", 20), (180,180,180))
        pygame.display.flip()

        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_RETURN and code.strip():
                    return code.strip().upper()
                if e.key == pygame.K_BACKSPACE:
                    code = code[:-1]
                else:
                    if e.unicode and e.unicode.isalnum():
                        code += e.unicode.upper()

# ---------- Drawing / assets ----------
def load_piece_images():
    pieces = {}
    fmap = {"P":"Pawn","R":"Rook","N":"Knight","B":"Bishop","Q":"Queen","K":"King"}
    for c in ["w","b"]:
        for s,name in fmap.items():
            key = c+s
            pth = os.path.join(PIECES_DIR, f"{c}_{name}.png")
            if not os.path.exists(pth): raise FileNotFoundError(pth)
            img = pygame.image.load(pth).convert_alpha()
            img = pygame.transform.smoothscale(img, (int(TILE_W*PIECE_SCALE), int(TILE_H*PIECE_SCALE)))
            pieces[key] = img
    return pieces

def draw_board(screen, board_img):
    screen.blit(board_img, (0,0))

def draw_pieces(screen, board, piece_images):
    for sq, piece in board.piece_map().items():
        row = 7 - (sq // 8); col = sq % 8
        key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
        img = piece_images[key]
        rect = pygame.Rect(OFFSET_X + col*TILE_W, OFFSET_Y + row*TILE_H, TILE_W, TILE_H)
        x = rect.x + (TILE_W - img.get_width()) // 2 + TWEAK_X
        y = rect.y + (TILE_H - img.get_height()) // 2 + TWEAK_Y
        screen.blit(img, (x,y))

def highlight_moves(screen, board, selected_square):
    if selected_square is None: return
    for mv in [m for m in board.legal_moves if m.from_square == selected_square]:
        row = 7 - (mv.to_square // 8); col = mv.to_square % 8
        center = (OFFSET_X + col*TILE_W + TILE_W//2, OFFSET_Y + row*TILE_H + TILE_H//2)
        pygame.draw.circle(screen, (0,255,0), center, 12)

def promotion_menu(screen, color, piece_images):
    choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    labels  = ["Q","R","B","N"]
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,180)); screen.blit(overlay, (0,0))
    menu = []
    sx = WIDTH//2 - (len(choices)*TILE_W)//2
    y  = HEIGHT//2 - TILE_H//2
    for i,ch in enumerate(choices):
        r = pygame.Rect(sx + i*(TILE_W+10), y, TILE_W, TILE_H)
        key = ("w" if color==chess.WHITE else "b")+labels[i]
        img = piece_images[key]
        xx = r.x + (TILE_W - img.get_width())//2
        yy = r.y + (TILE_H - img.get_height())//2
        screen.blit(img,(xx,yy))
        menu.append((r,ch))
    pygame.display.flip()
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                for r,ch in menu:
                    if r.collidepoint(e.pos): return ch

# ---------- Async / WebRTC ----------
def start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def _webrtc_connect(signal_url: str, is_host: bool):
    """
    Build RTCPeerConnection and WebSocket signaling.
    Returns (pc, data_channel (maybe not open yet), closer, open_flag_dict)
    open_flag_dict["open"] flips True when the data channel opens.
    """
    # Use STUN so ICE can complete (esp. on different machines)
    pc = RTCPeerConnection(configuration={
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}
        ]
    })
    session = ClientSession()
    ws = await session.ws_connect(signal_url, heartbeat=20)

    channel = None
    open_flag = {"open": False}

    @pc.on("datachannel")
    def on_datachannel(ch):
        nonlocal channel
        channel = ch
        @ch.on("open")
        def _open():
            open_flag["open"] = True

    async def ws_reader():
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            typ  = data.get("type")
            if typ == "offer":
                await pc.setRemoteDescription(RTCSessionDescription(data["sdp"], "offer"))
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await ws.send_json({"type":"answer","sdp":pc.localDescription.sdp})
            elif typ == "answer":
                await pc.setRemoteDescription(RTCSessionDescription(data["sdp"], "answer"))
            elif typ == "candidate":
                c = data["candidate"]
                try:
                    await pc.addIceCandidate(RTCIceCandidate(
                        sdpMid=c.get("sdpMid"),
                        sdpMLineIndex=c.get("sdpMLineIndex"),
                        candidate=c.get("candidate"),
                    ))
                except Exception:
                    pass
    asyncio.create_task(ws_reader())

    @pc.on("icecandidate")
    async def on_icecandidate(event):
        if event.candidate:
            await ws.send_json({
                "type": "candidate",
                "candidate": {
                    "sdpMid": event.candidate.sdpMid,
                    "sdpMLineIndex": event.candidate.sdpMLineIndex,
                    "candidate": event.candidate.to_sdp()
                }
            })

    if is_host:
        channel = pc.createDataChannel("chess")
        @channel.on("open")
        def _open():
            open_flag["open"] = True
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        await ws.send_json({"type":"offer","sdp":pc.localDescription.sdp})

    async def closer():
        try: await ws.close()
        except: pass
        await session.close()
        await pc.close()

    # We DO NOT block here; we return immediately and let the UI
    # show "waiting for peer" until open_flag flips True.
    return pc, channel, closer, open_flag

# ---------- Main entry ----------
def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chess Multiplayer (aiortc)")
    clock = pygame.time.Clock()

    # Music / SFX
    move_snd = cap_snd = None
    try:
        pygame.mixer.init()
        gm = os.path.join(AUDIO_DIR, "game_music_1.mp3")
        if os.path.exists(gm):
            pygame.mixer.music.load(gm)
            pygame.mixer.music.play(-1)
        mv = os.path.join(AUDIO_DIR, "move.wav")
        cp = os.path.join(AUDIO_DIR, "capture.wav")
        if os.path.exists(mv): move_snd = pygame.mixer.Sound(mv)
        if os.path.exists(cp): cap_snd  = pygame.mixer.Sound(cp)
    except Exception:
        pass

    # Ask host/join
    role = ask_host_or_join(screen)
    if role is None:
        pygame.quit(); return

    if role == "host":
        room = random_room_code()
    else:
        room = ask_room_code(screen)
        if not room:
            pygame.quit(); return

    signal_url = f"ws://{SIGNAL_HOST}:{SIGNAL_PORT}/ws?room={room}"

    # Spin an asyncio loop in a background thread
    loop = asyncio.new_event_loop()
    t = Thread(target=start_loop, args=(loop,), daemon=True)
    t.start()

    # Start connection (non-blocking)
    fut = asyncio.run_coroutine_threadsafe(_webrtc_connect(signal_url, role=="host"), loop)

    pc = chan = closer = open_flag = None

    # Waiting screen until the channel opens
    font = pygame.font.SysFont("arial", 28)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                if closer:
                    try: asyncio.run_coroutine_threadsafe(closer(), loop).result(timeout=3)
                    except: pass
                pygame.quit(); return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                if closer:
                    try: asyncio.run_coroutine_threadsafe(closer(), loop).result(timeout=3)
                    except: pass
                pygame.quit(); return

        if pc is None and fut.done():
            try:
                pc, chan, closer, open_flag = fut.result()
            except Exception as e:
                print("[multiplayer] connect failed:", e)
                pygame.quit(); return

        screen.fill((15,18,22))
        mode = "Hosting room" if role=="host" else "Joining room"
        center_text(screen, mode, 200, font)
        center_text(screen, f"ROOM CODE: {room}", 260, font, (100,200,255))
        center_text(screen, "Waiting for peer...", 320, font)
        center_text(screen, "ESC to cancel", 360, pygame.font.SysFont("arial", 20), (180,180,180))
        pygame.display.flip()
        clock.tick(30)

        if open_flag and open_flag.get("open"):
            break  # data channel open → start the game

    # ----- Connected! Build game state -----
    board_img = pygame.image.load(os.path.join(ASSETS_DIR, "board", "chess_board.png"))
    board_img = pygame.transform.smoothscale(board_img, (WIDTH, HEIGHT))
    pieces = load_piece_images()

    board = chess.Board()
    my_color = chess.WHITE if role == "host" else chess.BLACK
    selected_square = None
    inbound_moves = []

    @chan.on("message")
    def on_message(data):
        try:
            inbound_moves.append(data)
        except Exception:
            pass

    # ----- Main game loop -----
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                running = False

            if e.type == pygame.MOUSEBUTTONDOWN and board.turn == my_color:
                x,y = e.pos
                if (OFFSET_X <= x < OFFSET_X + 8*TILE_W) and (OFFSET_Y <= y < OFFSET_Y + 8*TILE_H):
                    col = (x - OFFSET_X) // TILE_W
                    row = 7 - ((y - OFFSET_Y) // TILE_H)
                    sq  = row * 8 + col

                    if selected_square is None:
                        p = board.piece_at(sq)
                        if p and p.color == board.turn:
                            selected_square = sq
                    else:
                        p = board.piece_at(selected_square)
                        if p and p.piece_type == chess.PAWN and chess.square_rank(sq) in [0,7]:
                            promo = promotion_menu(screen, board.turn, pieces)
                            mv = chess.Move(selected_square, sq, promotion=promo)
                        else:
                            mv = chess.Move(selected_square, sq)

                        if mv in board.legal_moves:
                            if cap_snd and board.is_capture(mv): cap_snd.play()
                            elif move_snd: move_snd.play()
                            board.push(mv)
                            try:
                                chan.send(mv.uci())
                            except Exception:
                                pass
                        selected_square = None

        # Apply remote moves
        while inbound_moves:
            uci = inbound_moves.pop(0)
            try:
                mv = chess.Move.from_uci(uci)
                if mv in board.legal_moves:
                    if cap_snd and board.is_capture(mv): cap_snd.play()
                    elif move_snd: move_snd.play()
                    board.push(mv)
            except Exception:
                pass

        # Draw
        draw_board(screen, board_img)
        if board.turn == my_color:
            highlight_moves(screen, board, selected_square)
        draw_pieces(screen, board, pieces)
        pygame.display.flip()
        clock.tick(FPS)

    # Cleanup connection
    try:
        asyncio.run_coroutine_threadsafe(closer(), loop).result(timeout=5)
    except Exception:
        pass
    try:
        loop.call_soon_threadsafe(loop.stop)
    except Exception:
        pass
    pygame.quit()
