import pygame
import sys
import chess
import os
from typing import Optional

# --- Board settings ---
WIDTH, HEIGHT = 800, 800
FPS = 60
TILE_W, TILE_H = 84, 84
OFFSET_X, OFFSET_Y = 55, 60
PIECE_SCALE = 0.9

# --- Paths ---
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
PIECES_DIR = os.path.join(ASSETS_DIR, "pieces")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")

# --- AI config ---
AI_PLAYS_WHITE = False
AI_DEPTH = 2

# --- Piece values ---
PIECE_VAL = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000,
}

# ---------------------------
# UI: difficulty menu
# ---------------------------
def difficulty_menu(screen, font):
    options = [
        ("Easy", 1),
        ("Medium", 2),
        ("Hard", 3),
        ("Advanced", 4),
    ]
    buttons = []

    while True:
        screen.fill((30, 30, 30))
        title = font.render("Select Difficulty", True, (255, 255, 255))
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 120))

        start_y = 250
        buttons.clear()
        for i, (label, depth) in enumerate(options):
            rect = pygame.Rect(WIDTH//2 - 100, start_y + i*90, 200, 60)
            pygame.draw.rect(screen, (80, 80, 80), rect)
            pygame.draw.rect(screen, (200, 200, 200), rect, 3)
            text = font.render(label, True, (255, 255, 255))
            screen.blit(text, (rect.centerx - text.get_width()//2,
                               rect.centery - text.get_height()//2))
            buttons.append((rect, depth))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                for rect, depth in buttons:
                    if rect.collidepoint(event.pos):
                        return depth

# ---------------------------
# Loaders & drawing
# ---------------------------
def load_piece_images():
    pieces = {}
    mapping = {"P": "Pawn", "R": "Rook", "N": "Knight",
               "B": "Bishop", "Q": "Queen", "K": "King"}
    for color in ["w", "b"]:
        for sym, name in mapping.items():
            key = color + sym
            filename = f"{color}_{name}.png"
            path = os.path.join(PIECES_DIR, filename)
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(
                img, (int(TILE_W*PIECE_SCALE), int(TILE_H*PIECE_SCALE))
            )
            pieces[key] = img
    return pieces

def draw_board(screen, board_img):
    screen.blit(board_img, (0, 0))

def draw_pieces(screen, board, piece_images):
    TWEAK_X, TWEAK_Y = 0, 5
    for square, piece in board.piece_map().items():
        row = 7 - (square // 8)
        col = square % 8
        key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
        img = piece_images[key]
        rect = pygame.Rect(
            OFFSET_X + col*TILE_W,
            OFFSET_Y + row*TILE_H,
            TILE_W, TILE_H
        )
        x = rect.x + (TILE_W - img.get_width())//2 + TWEAK_X
        y = rect.y + (TILE_H - img.get_height())//2 + TWEAK_Y
        screen.blit(img, (x, y))

def highlight_moves(screen, board, selected_square):
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
        pygame.draw.circle(screen, (0, 255, 0), center, 10)

# ---------------------------
# Promotion menu
# ---------------------------
def promotion_menu(screen, color, piece_images):
    choices = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    labels = ["Q", "R", "B", "N"]

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    menu_buttons = []
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

# ---------------------------
# AI core
# ---------------------------
def evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -999999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for sq, piece in board.piece_map().items():
        score += PIECE_VAL[piece.piece_type] * (1 if piece.color else -1)
    return score if board.turn == chess.WHITE else -score

def alphabeta(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate(board)
    best = -1_000_000
    for move in board.legal_moves:
        board.push(move)
        val = -alphabeta(board, depth-1, -beta, -alpha)
        board.pop()
        if val > best: best = val
        if best > alpha: alpha = best
        if alpha >= beta: break
    return best

def find_ai_move(board, depth):
    best_move = None
    best_val = -1_000_000
    for move in board.legal_moves:
        board.push(move)
        val = -alphabeta(board, depth-1, -1_000_000, 1_000_000)
        board.pop()
        if val > best_val:
            best_val, best_move = val, move
    return best_move or next(iter(board.legal_moves))

# ---------------------------
# Audio helpers
# ---------------------------
def load_sounds():
    move_sound = capture_sound = None
    if os.path.exists(os.path.join(AUDIO_DIR, "move.wav")):
        move_sound = pygame.mixer.Sound(os.path.join(AUDIO_DIR, "move.wav"))
    if os.path.exists(os.path.join(AUDIO_DIR, "capture.wav")):
        capture_sound = pygame.mixer.Sound(os.path.join(AUDIO_DIR, "capture.wav"))
    return move_sound, capture_sound

def play_sound_for_move(board_before: chess.Board, move: chess.Move, move_sound, capture_sound):
    if board_before.is_capture(move):
        if capture_sound: capture_sound.play()
    else:
        if move_sound: move_sound.play()

# ---------------------------
# Main loop
# ---------------------------
def run():
    global AI_DEPTH, AI_PLAYS_WHITE

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Offline Chess (vs AI)")
    clock = pygame.time.Clock()

    font_menu = pygame.font.SysFont("consolas", 36)

    # 🎵 Init audio
    pygame.mixer.init()
    music_file = os.path.join(AUDIO_DIR, "game_music_1.mp3")
    if os.path.exists(music_file):
        pygame.mixer.music.load(music_file)
        pygame.mixer.music.play(-1)
    move_sound, capture_sound = load_sounds()

    # Difficulty menu
    AI_DEPTH = difficulty_menu(screen, font_menu)

    # Board and pieces
    board_img_path = os.path.join(ASSETS_DIR, "board", "chess_board.png")
    board_img = pygame.image.load(board_img_path)
    board_img = pygame.transform.smoothscale(board_img, (WIDTH, HEIGHT))
    piece_images = load_piece_images()

    board = chess.Board()
    selected_square: Optional[int] = None

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_r:
                    board = chess.Board()
                if event.key == pygame.K_a:
                    AI_PLAYS_WHITE = not AI_PLAYS_WHITE
                if event.key == pygame.K_1:
                    AI_DEPTH = 1
                if event.key == pygame.K_2:
                    AI_DEPTH = 2
                if event.key == pygame.K_3:
                    AI_DEPTH = 3

            if event.type == pygame.MOUSEBUTTONDOWN:
                human_is_white = not AI_PLAYS_WHITE
                if board.turn == (chess.WHITE if human_is_white else chess.BLACK):
                    x, y = event.pos
                    if (OFFSET_X <= x < OFFSET_X+8*TILE_W) and (OFFSET_Y <= y < OFFSET_Y+8*TILE_H):
                        col = (x - OFFSET_X)//TILE_W
                        row = 7 - ((y - OFFSET_Y)//TILE_H)
                        square = row*8 + col
                        if selected_square is None:
                            if board.piece_at(square) and board.piece_at(square).color == board.turn:
                                selected_square = square
                        else:
                            # Handle promotion
                            if (board.piece_at(selected_square).piece_type == chess.PAWN
                                and chess.square_rank(square) in [0, 7]):
                                promotion_piece = promotion_menu(screen, board.turn, piece_images)
                                move = chess.Move(selected_square, square, promotion=promotion_piece)
                            else:
                                move = chess.Move(selected_square, square)

                            if move in board.legal_moves:
                                before = board.copy()
                                board.push(move)
                                play_sound_for_move(before, move, move_sound, capture_sound)
                            selected_square = None

        # AI move
        if not board.is_game_over():
            ai_turn = (board.turn == chess.WHITE and AI_PLAYS_WHITE) or \
                      (board.turn == chess.BLACK and not AI_PLAYS_WHITE)
            if ai_turn:
                ai_move = find_ai_move(board, AI_DEPTH)
                # auto promote to queen if pawn hits last rank
                if ai_move.promotion is None:
                    if board.piece_at(ai_move.from_square) and \
                       board.piece_at(ai_move.from_square).piece_type == chess.PAWN and \
                       chess.square_rank(ai_move.to_square) in (0, 7):
                        ai_move = chess.Move(ai_move.from_square, ai_move.to_square, promotion=chess.QUEEN)
                before = board.copy()
                board.push(ai_move)
                play_sound_for_move(before, ai_move, move_sound, capture_sound)

        draw_board(screen, board_img)
        highlight_moves(screen, board, selected_square)
        draw_pieces(screen, board, piece_images)
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    run()
