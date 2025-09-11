import pygame
import sys
import chess
import os

# --- Board settings ---
WIDTH, HEIGHT = 800, 800
FPS = 60
TILE_W, TILE_H = 84, 84  # measured tile sizes
OFFSET_X, OFFSET_Y = 55, 60  # board frame offsets
PIECE_SCALE = 0.9  # shrink slightly inside each tile

# --- Paths ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")


def load_piece_images():
    """Load and scale all piece sprites using underscore filenames (w_Pawn.png, b_King.png, etc.)"""
    pieces = {}
    PIECE_FILE_MAP = {
        "P": "Pawn",
        "R": "Rook",
        "N": "Knight",
        "B": "Bishop",
        "Q": "Queen",
        "K": "King",
    }
    for color in ["w", "b"]:
        for symbol, name in PIECE_FILE_MAP.items():
            key = color + symbol          # ex: "wP"
            filename = f"{color}_{name}.png"  # ex: "w_Pawn.png"
            path = os.path.join(PIECES_DIR, filename)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing piece image: {path}")
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(
                img, (int(TILE_W * PIECE_SCALE), int(TILE_H * PIECE_SCALE))
            )
            pieces[key] = img
    return pieces


def draw_board(screen, board_img):
    screen.blit(board_img, (0, 0))


def draw_pieces(screen, board, piece_images):
    """Draw all pieces, centered in their tiles with fine-tuned alignment."""
    TWEAK_X, TWEAK_Y = 0, 5   # shift all pieces down slightly

    for square, piece in board.piece_map().items():
        row = 7 - (square // 8)
        col = square % 8
        piece_key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
        img = piece_images[piece_key]

        rect = pygame.Rect(
            OFFSET_X + col * TILE_W,
            OFFSET_Y + row * TILE_H,
            TILE_W,
            TILE_H
        )

        x = rect.x + (TILE_W - img.get_width()) // 2 + TWEAK_X
        y = rect.y + (TILE_H - img.get_height()) // 2 + TWEAK_Y

        screen.blit(img, (x, y))


def highlight_moves(screen, board, selected_square):
    """Draw green dots for valid moves of a selected piece."""
    if selected_square is None:
        return
    moves = [m for m in board.legal_moves if m.from_square == selected_square]
    for move in moves:
        row = 7 - (move.to_square // 8)
        col = move.to_square % 8
        center = (
            OFFSET_X + col * TILE_W + TILE_W // 2,
            OFFSET_Y + row * TILE_H + TILE_H // 2,
        )
        pygame.draw.circle(screen, (0, 255, 0), center, 12)


def promotion_menu(screen, color, piece_images):
    """Draw promotion selection menu and return chosen piece type."""
    choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    labels = ["Q", "R", "B", "N"]

    # Dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    menu_buttons = []  # list of (rect, choice)
    start_x = WIDTH // 2 - (len(choices) * TILE_W) // 2
    y = HEIGHT // 2 - TILE_H // 2

    for i, choice in enumerate(choices):
        rect = pygame.Rect(start_x + i * (TILE_W + 10), y, TILE_W, TILE_H)
        piece_key = ("w" if color == chess.WHITE else "b") + labels[i]
        img = piece_images[piece_key]
        x = rect.x + (TILE_W - img.get_width()) // 2
        y_img = rect.y + (TILE_H - img.get_height()) // 2
        screen.blit(img, (x, y_img))
        menu_buttons.append((rect, choice))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for rect, choice in menu_buttons:
                    if rect.collidepoint(event.pos):
                        return choice


def run():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Offline Chess")
    clock = pygame.time.Clock()

    # 🎨 Load board background
    board_img_path = os.path.join(ASSETS_DIR, "board", "chess_board.png")
    if not os.path.exists(board_img_path):
        raise FileNotFoundError(f"Missing board image: {board_img_path}")
    board_img = pygame.image.load(board_img_path)
    board_img = pygame.transform.smoothscale(board_img, (WIDTH, HEIGHT))

    # ♟ Load pieces
    piece_images = load_piece_images()

    # 🎵 Music + sounds
    pygame.mixer.init()
    game_music = os.path.join(AUDIO_DIR, "game_music_1.mp3")
    if os.path.exists(game_music):
        pygame.mixer.music.load(game_music)
        pygame.mixer.music.play(-1)

    move_sound = pygame.mixer.Sound(os.path.join(AUDIO_DIR, "move.wav"))
    capture_sound = pygame.mixer.Sound(os.path.join(AUDIO_DIR, "capture.wav"))

    # ♟ Game state
    board = chess.Board()
    selected_square = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if (OFFSET_X <= x < OFFSET_X + 8 * TILE_W) and (OFFSET_Y <= y < OFFSET_Y + 8 * TILE_H):
                    col = (x - OFFSET_X) // TILE_W
                    row = 7 - ((y - OFFSET_Y) // TILE_H)
                    square = row * 8 + col

                    if selected_square is None:
                        if board.piece_at(square) and board.piece_at(square).color == board.turn:
                            selected_square = square
                    else:
                        # --- Promotion logic FIRST ---
                        if (board.piece_at(selected_square).piece_type == chess.PAWN
                            and chess.square_rank(square) in [0, 7]):
                            promotion_piece = promotion_menu(screen, board.turn, piece_images)
                            move = chess.Move(selected_square, square, promotion=promotion_piece)
                        else:
                            move = chess.Move(selected_square, square)

                        # --- Now validate and play sounds ---
                        if move in board.legal_moves:
                            if board.is_capture(move):
                                capture_sound.play()
                            else:
                                move_sound.play()
                            board.push(move)

                        selected_square = None

        # 🔄 Draw everything
        draw_board(screen, board_img)
        highlight_moves(screen, board, selected_square)
        draw_pieces(screen, board, piece_images)

        pygame.display.flip()
        clock.tick(FPS)

# 🚨 No auto-run. Only runs when called from main_menu.py
