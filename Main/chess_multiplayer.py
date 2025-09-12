# chess_multiplayer.py
import os, sys, json, asyncio, random, string, queue
import pygame
import chess
from threading import Thread

from aiohttp import ClientSession, WSMsgType
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer,
)

# ====================== Options ======================
# If True: either player may move their own pieces at any time (useful for testing).
# If False: strict chess rules (only the side to move may move).
SANDBOX = True

# ---------- Board & assets ----------
WIDTH, HEIGHT = 800, 800
FPS = 60
TILE_W, TILE_H = 84, 84
OFFSET_X, OFFSET_Y = 55, 60
PIECE_SCALE = 0.9
TWEAK_X, TWEAK_Y = 0, 5

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
AUDIO_DIR  = os.path.join(os.path.dirname(__file__), "audio")

# ---------- Signaling + ICE config ----------
SIGNAL_HOST = os.getenv("SIGNAL_HOST", "127.0.0.1")
SIGNAL_PORT = int(os.getenv("SIGNAL_PORT", "8080"))

ICE_SERVERS = [
    RTCIceServer(urls="stun:stun.l.google.com:19302"),
    RTCIceServer(urls="stun:stun1.l.google.com:19302"),
]
TURN_URL  = os.getenv("TURN_URL")
TURN_USER = os.getenv("TURN_USER")
TURN_PASS = os.getenv("TURN_PASS")
if TURN_URL and TURN_USER and TURN_PASS:
    ICE_SERVERS.append(RTCIceServer(urls=TURN_URL, username=TURN_USER, credential=TURN_PASS))

RTC_CONFIG = RTCConfiguration(iceServers=ICE_SERVERS)

# ====================== UI helpers ======================
def center_text(surf, text, y, font, color=(255,255,255)):
    t = font.render(text, True, color)
    r = t.get_rect(center=(WIDTH//2, y))
    surf.blit(t, r)

def random_room_code(n=5):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def ask_host_or_join(screen):
    font_big  = pygame.font.SysFont("arial", 30)
    font_small= pygame.font.SysFont("arial", 22)
    while True:
        screen.fill((15,18,22))
        center_text(screen, "Press  H  to Host   or   J  to Join", HEIGHT//2, font_big)
        center_text(screen, "ESC to cancel", HEIGHT//2 + 60, font_small, (180,180,180))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return None
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return None
                if e.key == pygame.K_h: return "host"
                if e.key == pygame.K_j: return "join"

def ask_room_code(screen):
    font = pygame.font.SysFont("arial", 28)
    helpf= pygame.font.SysFont("arial", 20)
    code = ""
    while True:
        screen.fill((15,18,22))
        center_text(screen, "Enter ROOM CODE:", 220, font)
        box = pygame.Rect(WIDTH//2 - 160, 270, 320, 46)
        pygame.draw.rect(screen, (40,45,52), box, border_radius=10)
        pygame.draw.rect(screen, (100,110,120), box, 2, border_radius=10)
        txt = font.render(code, True, (220,220,220))
        screen.blit(txt, (box.x+10, box.y+8))
        center_text(screen, "Enter = Join   |   ESC = Cancel", 330, helpf, (180,180,180))
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

# ====================== Board / Drawing ======================
def load_piece_images():
    pieces = {}
    fmap = {"P":"Pawn","R":"Rook","N":"Knight","B":"Bishop","Q":"Queen","K":"King"}
    for c in ["w","b"]:
        for s, name in fmap.items():
            key = c+s
            pth = os.path.join(PIECES_DIR, f"{c}_{name}.png")
            if not os.path.exists(pth):
                raise FileNotFoundError(pth)
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
        screen.blit(img, (x, y))

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

# ====================== Async / WebRTC ======================
def _start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def _webrtc_connect(signal_url: str, is_host: bool, inbound_q: "queue.Queue[str]"):
    print("[webrtc] signaling url:", signal_url)
    print("[webrtc] role:", "host" if is_host else "join")
    print("[webrtc] ICE servers:", [s.urls for s in RTC_CONFIG.iceServers])

    pc = RTCPeerConnection(configuration=RTC_CONFIG)

    # Fallback: mark open when PC hits 'connected'
    open_flag = {"open": False}

    @pc.on("iceconnectionstatechange")
    def _on_ice_state():
        print("[webrtc] ICE state:", pc.iceConnectionState)

    @pc.on("connectionstatechange")
    def _on_conn_state():
        print("[webrtc] PC state:", pc.connectionState)
        if pc.connectionState == "connected":
            open_flag["open"] = True

    @pc.on("signalingstatechange")
    def _on_sig_state():
        print("[webrtc] signaling state:", pc.signalingState)

    session = ClientSession()
    ws = await session.ws_connect(signal_url, heartbeat=20)

    channel_box = {"ch": None}

    def _push_inbound(msg):
        try:
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", errors="ignore")
            inbound_q.put_nowait(str(msg))
            print("[dc] inbound -> queue:", msg)
        except Exception as e:
            print("[dc] inbound queue error:", e)

    @pc.on("datachannel")
    def on_datachannel(ch):
        print("[dc] joiner got datachannel:", ch.label)
        channel_box["ch"] = ch

        @ch.on("open")
        def _open():
            print("[dc] joiner datachannel open")
            open_flag["open"] = True
            try:
                ch.send("__hello_from_joiner__")
            except Exception:
                pass

        @ch.on("message")
        def _msg(m):
            _push_inbound(m)

    async def ws_reader():
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            data = json.loads(msg.data)
            typ  = data.get("type")
            if typ == "offer":
                print("[ws] got offer")
                await pc.setRemoteDescription(RTCSessionDescription(data["sdp"], "offer"))
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                print("[ws] sending answer")
                await ws.send_json({"type":"answer", "sdp": pc.localDescription.sdp})
            elif typ == "answer":
                print("[ws] got answer")
                await pc.setRemoteDescription(RTCSessionDescription(data["sdp"], "answer"))
            elif typ == "candidate":
                print("[ws] got candidate")
                c = data["candidate"]
                try:
                    await pc.addIceCandidate(RTCIceCandidate(
                        sdpMid=c.get("sdpMid"),
                        sdpMLineIndex=c.get("sdpMLineIndex"),
                        candidate=c.get("candidate"),
                    ))
                except Exception as e:
                    print("[ws] addIceCandidate error:", e)

    asyncio.create_task(ws_reader())

    @pc.on("icecandidate")
    async def on_icecandidate(event):
        if event.candidate:
            print("[ws] sending candidate")
            await ws.send_json({
                "type": "candidate",
                "candidate": {
                    "sdpMid": event.candidate.sdpMid,
                    "sdpMLineIndex": event.candidate.sdpMLineIndex,
                    "candidate": event.candidate.to_sdp(),
                }
            })
        else:
            print("[webrtc] ICE gathering complete")

    if is_host:
        ch = pc.createDataChannel("chess")
        channel_box["ch"] = ch
        print("[dc] host created datachannel")

        @ch.on("open")
        def _open():
            print("[dc] host datachannel open")
            open_flag["open"] = True
            try:
                ch.send("__hello_from_host__")
            except Exception:
                pass

        @ch.on("message")
        def on_message(msg):
            _push_inbound(msg)

        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        print("[ws] sending offer")
        await ws.send_json({"type":"offer", "sdp": pc.localDescription.sdp})

    async def closer():
        try: await ws.close()
        except: pass
        await session.close()
        await pc.close()

    return pc, channel_box, closer, open_flag

# ====================== Game helpers ======================
def try_push_move(board: chess.Board, mv: chess.Move, my_color: bool):
    if mv is None:
        return False
    mover_piece = board.piece_at(mv.from_square)
    if mover_piece is None:
        return False
    mover_color = mover_piece.color
    if mover_color != my_color:
        return False
    if SANDBOX and mover_color != board.turn:
        board.turn = mover_color
    if mv in board.legal_moves:
        board.push(mv)
        return True
    return False

def apply_inbound_uci(board: chess.Board, uci: str):
    try:
        mv = chess.Move.from_uci(uci)
    except Exception:
        return False
    piece = board.piece_at(mv.from_square)
    if SANDBOX and piece and piece.color != board.turn:
        board.turn = piece.color
    if mv in board.legal_moves:
        board.push(mv)
        return True
    return False

# ====================== Main entry ======================
def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chess Multiplayer (aiortc)")
    clock = pygame.time.Clock()

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

    role = ask_host_or_join(screen)
    if role is None:
        pygame.quit(); return

    if role == "host":
        room = random_room_code()
    else:
        room = ask_room_code(screen)
        if not room: pygame.quit(); return

    signal_url = f"ws://{SIGNAL_HOST}:{SIGNAL_PORT}/ws?room={room}"

    # Thread-safe inbox fed by the asyncio thread
    inbound_q: "queue.Queue[str]" = queue.Queue()

    # Run asyncio loop in background
    loop = asyncio.new_event_loop()
    thread = Thread(target=_start_loop, args=(loop,), daemon=True)
    thread.start()

    fut = asyncio.run_coroutine_threadsafe(
        _webrtc_connect(signal_url, role=="host", inbound_q=inbound_q), loop
    )
    pc = chan_box = closer = open_flag = None

    font = pygame.font.SysFont("arial", 28)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                if closer:
                    try: asyncio.run_coroutine_threadsafe(closer(), loop).result(timeout=3)
                    except: pass
                pygame.quit(); return

        if pc is None and fut.done():
            try:
                pc, chan_box, closer, open_flag = fut.result()
            except Exception as e:
                print("[multiplayer] connect failed:", e)
                pygame.quit(); return

        screen.fill((15,18,22))
        center_text(screen, "Hosting room" if role=="host" else "Joining room", 200, font)
        center_text(screen, f"ROOM CODE: {room}", 260, font, (100,200,255))
        if open_flag and open_flag.get("open"):
            center_text(screen, "Connected. Finalizing channel...", 320, font, (180,220,180))
        else:
            center_text(screen, "Waiting for peer...", 320, font)
        center_text(screen, "ESC to cancel", 360, pygame.font.SysFont("arial", 20), (180,180,180))
        pygame.display.flip()
        clock.tick(30)

        if open_flag and open_flag.get("open") and chan_box and chan_box.get("ch") is not None:
            break

    # Real channel (we send moves with it)
    chan = chan_box["ch"]

    board_img = pygame.image.load(os.path.join(ASSETS_DIR, "board", "chess_board.png"))
    board_img = pygame.transform.smoothscale(board_img, (WIDTH, HEIGHT))
    pieces = load_piece_images()

    board = chess.Board()
    my_color = chess.WHITE if role == "host" else chess.BLACK
    selected_square = None

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False

            allow_click = True if SANDBOX else (board.turn == my_color)

            if e.type == pygame.MOUSEBUTTONDOWN and allow_click:
                x, y = e.pos
                if (OFFSET_X <= x < OFFSET_X + 8*TILE_W) and (OFFSET_Y <= y < OFFSET_Y + 8*TILE_H):
                    col = (x - OFFSET_X) // TILE_W
                    row = 7 - ((y - OFFSET_Y) // TILE_H)
                    sq  = row * 8 + col

                    if selected_square is None:
                        p = board.piece_at(sq)
                        if p and p.color == my_color:
                            selected_square = sq
                    else:
                        p = board.piece_at(selected_square)
                        if p and p.piece_type == chess.PAWN and chess.square_rank(sq) in [0,7]:
                            promo = promotion_menu(screen, p.color, pieces)
                            mv = chess.Move(selected_square, sq, promotion=promo)
                        else:
                            mv = chess.Move(selected_square, sq)

                        if try_push_move(board, mv, my_color):
                            # sfx
                            if cap_snd and board.is_capture(mv): cap_snd.play()
                            elif move_snd: move_snd.play()
                            try:
                                uci = mv.uci()
                                print("[game] scheduling send:", uci)
                                # SCHEDULE SEND ON ASYNCIO LOOP (thread-safe)
                                loop.call_soon_threadsafe(chan.send, uci)
                            except Exception as ex:
                                print("[game] send schedule failed:", ex)
                        selected_square = None

        # Drain inbound queue and apply moves
        while True:
            try:
                uci = inbound_q.get_nowait()
            except queue.Empty:
                break
            if apply_inbound_uci(board, uci):
                try:
                    mv = chess.Move.from_uci(uci)
                    if cap_snd and board.is_capture(mv): cap_snd.play()
                    elif move_snd: move_snd.play()
                except Exception:
                    pass

        draw_board(screen, board_img)
        highlight_moves(screen, board, selected_square)
        draw_pieces(screen, board, pieces)
        pygame.display.flip()
        clock.tick(FPS)

    # Cleanup
    try: asyncio.run_coroutine_threadsafe(closer(), loop).result(timeout=5)
    except: pass
    try: loop.call_soon_threadsafe(loop.stop)
    except: pass
    pygame.quit()


if __name__ == "__main__":
    run()
