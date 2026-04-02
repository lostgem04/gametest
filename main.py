#!/usr/bin/env python3
"""
Arcane Abyss — v3.1
main.py: título, selección de cuenta, raza y mundo multijugador.
"""
import sys, os, time, tty, termios, select

# ── Asegurar que el directorio del script esté en sys.path ──────────────────
# Permite ejecutar desde cualquier directorio: python3 /ruta/main.py
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# ── ANSI ──────────────────────────────────────────────────────────────────────
RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
ITALIC = '\033[3m'

def fg(r, g, b):    return f'\033[38;2;{r};{g};{b}m'
def bg(r, g, b):    return f'\033[48;2;{r};{g};{b}m'
def cup(r, c):      return f'\033[{r};{c}H'
def erase_line():   return '\033[2K'
def clear_screen(): return '\033[2J\033[H'

C_GOLD   = fg(220, 180,  40)
C_GRAY   = fg(150, 150, 150)
C_WHITE  = fg(220, 220, 220)
C_DIM    = fg( 55,  55,  55)
C_RED    = fg(200,  60,  60)
C_GREEN  = fg( 80, 200,  80)
C_CYAN   = fg( 60, 200, 200)
C_PURPLE = fg(160,  80, 255)

SUBTITLE  = "Terminal 3D RPG  ·  Multi-World Edition  ·  v3.1"
TAGLINES  = [
    '"Darkness waits beyond the threshold..."',
    '"Steel, sorcery and shadow."',
    '"The dungeon remembers those who fall."',
    '"Glory or oblivion — the abyss decides."',
]

# ── Terminal helpers ───────────────────────────────────────────────────────────

def get_sz():
    try:
        s = os.get_terminal_size()
        return s.columns, s.lines
    except Exception:
        return 120, 40

def set_raw(fd):
    old = termios.tcgetattr(fd)
    tty.setraw(fd)
    return old

def restore_term(fd, old):
    termios.tcsetattr(fd, termios.TCSADRAIN, old)

def read_key(timeout=0.06):
    if select.select([sys.stdin], [], [], timeout)[0]:
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            rest = sys.stdin.read(2) if select.select([sys.stdin], [], [], 0.02)[0] else ''
            return {'[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left'}.get(rest, 'esc')
        return ch
    return ''

def write(s):
    sys.stdout.buffer.write(s.encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

def center_col(text, cols):
    return max(1, (cols - len(text)) // 2)


# ── Draw helpers ──────────────────────────────────────────────────────────────

def draw_box(buf, row, col, w, h, color=''):
    tl, tr, bl, br = '╔', '╗', '╚', '╝'
    hz, vt         = '═', '║'
    buf.append(cup(row, col) + color + tl + hz * (w-2) + tr + RESET)
    for r in range(row+1, row+h-1):
        buf.append(cup(r, col) + color + vt + ' '*(w-2) + vt + RESET)
    buf.append(cup(row+h-1, col) + color + bl + hz * (w-2) + br + RESET)

def write_centered(buf, row, text, cols, color=''):
    c = center_col(text, cols)
    buf.append(cup(row, c) + color + text + RESET)


# ── Main title screen ─────────────────────────────────────────────────────────

MAIN_MENU_ITEMS = [
    ("JUGAR",          'play'),
    ("MULTIJUGADOR",   'multi'),
    ("AYUDA / TECLAS", 'help'),
    ("SALIR",          'quit'),
]

def draw_main_title(cols, rows, selected, frame):
    buf = ['\033[?25l']
    for r in range(1, rows + 1):
        buf.append(cup(r, 1) + '\033[2K')

    mid = rows // 2 - 4

    # Title
    title_lines = [
        " █████╗ ██████╗  ██████╗ █████╗ ███╗  ██╗███████╗",
        "██╔══██╗██╔══██╗██╔════╝██╔══██╗████╗ ██║██╔════╝",
        "███████║██████╔╝██║     ███████║██╔██╗██║█████╗  ",
        "██╔══██║██╔══██╗██║     ██╔══██║██║╚████║██╔══╝  ",
        "██║  ██║██║  ██║╚██████╗██║  ██║██║ ╚███║███████╗",
        "╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚══╝╚══════╝",
        "",
        "  █████╗ ██████╗ ██╗   ██╗███████╗███████╗       ",
        "  ██╔══██╗██╔══██╗╚██╗ ██╔╝██╔════╝██╔════╝      ",
        "  ███████║██████╔╝ ╚████╔╝ ███████╗███████╗      ",
        "  ██╔══██║██╔══██╗  ╚██╔╝  ╚════██║╚════██║      ",
        "  ██║  ██║██████╔╝   ██║   ███████║███████║      ",
        "  ╚═╝  ╚═╝╚═════╝    ╚═╝   ╚══════╝╚══════╝      ",
    ]

    art_w = max(len(l) for l in title_lines)
    art_c = max(1, (cols - art_w) // 2)
    for i, line in enumerate(title_lines):
        pulse = 180 + int(20 * abs(math.sin(frame * 0.04 + i * 0.15)))
        buf.append(cup(mid + i, art_c) + fg(pulse, int(pulse*0.75), 30) + line + RESET)

    row = mid + len(title_lines) + 1

    # Subtitle
    write_centered(buf, row, SUBTITLE, cols, C_GRAY + DIM)
    row += 1

    div = '─' * min(50, cols - 4)
    write_centered(buf, row, div, cols, C_DIM)
    row += 2

    # Menu
    max_label = max(len(lbl) for lbl, _ in MAIN_MENU_ITEMS)
    for idx, (label, _) in enumerate(MAIN_MENU_ITEMS):
        if idx == selected:
            entry = BOLD + C_GOLD + f'▶  {label:<{max_label}}  ◀' + RESET
        else:
            entry = C_GRAY + f'   {label:<{max_label}}   ' + RESET
        write_centered(buf, row, f'   {label:<{max_label}}   ', cols)
        # override with colored version
        ctext = f'▶  {label:<{max_label}}  ◀' if idx == selected else f'   {label:<{max_label}}   '
        color = C_GOLD + BOLD if idx == selected else C_GRAY
        c = center_col(ctext, cols)
        buf.append(cup(row, c) + color + ctext + RESET)
        row += 2

    # Tagline
    row += 1
    tl = TAGLINES[int(time.time() / 6) % len(TAGLINES)]
    write_centered(buf, row, tl, cols, C_DIM + DIM)
    row += 2

    hint = 'W/S · flechas  →  mover     Enter  →  confirmar     Q  →  salir'
    write_centered(buf, row, hint, cols, C_DIM)

    write(''.join(buf))

import math


def show_main_menu():
    selected = 0
    frame    = 0

    write(clear_screen() + '\033[?25l')

    while True:
        cols, rows = get_sz()
        draw_main_title(cols, rows, selected, frame)
        frame += 1

        key = read_key(timeout=0.05)
        n = len(MAIN_MENU_ITEMS)
        if key in ('w', 'up'):
            selected = (selected - 1) % n
        elif key in ('s', 'down'):
            selected = (selected + 1) % n
        elif key in ('\r', '\n', ' '):
            return MAIN_MENU_ITEMS[selected][1]
        elif key in ('q', 'esc', '\x03'):
            return 'quit'
        elif key == '1': return 'play'
        elif key == '2': return 'multi'
        elif key == '3': return 'help'
        elif key == '4': return 'quit'


# ── Account name input ────────────────────────────────────────────────────────

def read_text_input(prompt, cols, rows, max_len=20, allowed=None):
    """Lee texto del usuario en modo raw. Retorna el string o '' si canceló."""
    buf   = []
    frame = 0

    while True:
        frame += 1
        out = ['\033[?25l']
        for r in range(1, rows + 1):
            out.append(cup(r, 1) + '\033[2K')

        # decoración
        title = "─── ARCANE ABYSS ───"
        write_centered(out, rows // 2 - 3, title, cols, C_GOLD + BOLD)
        write_centered(out, rows // 2 - 1, prompt, cols, C_WHITE)

        text     = ''.join(buf)
        cursor   = '█' if frame % 20 < 10 else ' '
        display  = f'  {text}{cursor}  '
        write_centered(out, rows // 2 + 1, display, cols, C_CYAN + BOLD)

        hint = 'Enter para confirmar  ·  ESC para cancelar'
        write_centered(out, rows // 2 + 3, hint, cols, C_DIM)

        write(''.join(out))

        key = read_key(timeout=0.07)
        if not key:
            continue
        if key in ('\r', '\n') and buf:
            return ''.join(buf)
        elif key in ('esc', '\x1b', '\x03'):
            return ''
        elif key == '\x7f' or key == '\x08':   # backspace
            if buf:
                buf.pop()
        elif len(key) == 1 and len(buf) < max_len:
            if allowed is None or key in allowed:
                buf.append(key)


# ── Race selection ─────────────────────────────────────────────────────────────

def draw_race_menu(cols, rows, selected_idx, frame):
    from races import RACE_DEFS, RACE_ORDER

    buf = ['\033[?25l']
    for r in range(1, rows + 1):
        buf.append(cup(r, 1) + '\033[2K')

    write_centered(buf, 2, '═══  ELIGE TU RAZA  ═══', cols, C_GOLD + BOLD)

    race_names = RACE_ORDER
    n          = len(race_names)
    panel_w    = min(38, (cols - 4) // 2)

    # Left panel: race list
    list_col = 3
    list_row = 4
    draw_box(buf, list_row, list_col, panel_w - 2, n * 2 + 4, C_DIM)

    for i, rid in enumerate(race_names):
        race  = RACE_DEFS[rid]
        rrow  = list_row + 2 + i * 2
        color = fg(*race['color'])
        if i == selected_idx:
            marker = BOLD + '▶ '
            col_c  = color
        else:
            marker = '  '
            col_c  = C_GRAY
        text = f"{marker}{race['name']}"
        buf.append(cup(rrow, list_col + 2) + col_c + text + RESET)

    # Right panel: details of selected race
    sel_rid  = race_names[selected_idx]
    sel_race = RACE_DEFS[sel_rid]
    det_col  = list_col + panel_w
    det_row  = 4
    det_h    = n * 2 + 4
    draw_box(buf, det_row, det_col, cols - det_col - 2, det_h, fg(*sel_race['color']))

    r = det_row + 1
    buf.append(cup(r, det_col + 2) + fg(*sel_race['color']) + BOLD + sel_race['name'] + RESET)
    r += 1
    buf.append(cup(r, det_col + 2) + C_DIM + '─' * (cols - det_col - 5) + RESET)
    r += 1

    for line in sel_race['description'].split('\n'):
        buf.append(cup(r, det_col + 2) + C_WHITE + line + RESET)
        r += 1
        if r >= det_row + det_h - 1:
            break

    r = det_row + det_h + 1
    buf.append(cup(r, det_col + 2) + C_GRAY + 'Pasivos:' + RESET)
    r += 1
    for p_line in sel_race.get('passives', []):
        buf.append(cup(r, det_col + 2) + C_CYAN + '  · ' + p_line + RESET)
        r += 1

    # ASCII art in left-bottom area
    art_row = list_row + n * 2 + 2
    for li, aline in enumerate(sel_race.get('ascii_art', [])):
        buf.append(cup(art_row + li, list_col + 4) + fg(*sel_race['color']) + BOLD + aline + RESET)

    bottom = rows - 2
    write_centered(buf, bottom, 'W/S o flechas  →  cambiar raza     Enter  →  confirmar', cols, C_DIM)

    write(''.join(buf))


def show_race_menu(existing_race=None):
    """
    Muestra el menú de selección de raza.
    Si existing_race != None, la raza ya fue elegida — devuelve directamente.
    """
    from races import RACE_ORDER, RACE_DEFS

    if existing_race and existing_race in RACE_DEFS:
        return existing_race

    selected = 0
    frame    = 0
    write(clear_screen() + '\033[?25l')

    while True:
        cols, rows = get_sz()
        draw_race_menu(cols, rows, selected, frame)
        frame += 1

        key = read_key(timeout=0.06)
        n   = len(RACE_ORDER)
        if key in ('w', 'up'):
            selected = (selected - 1) % n
        elif key in ('s', 'down'):
            selected = (selected + 1) % n
        elif key in ('\r', '\n', ' '):
            return RACE_ORDER[selected]
        elif key in ('q', 'esc', '\x03'):
            return RACE_ORDER[selected]   # confirmar con raza actual


# ── Multiplayer menu (host / join) ───────────────────────────────────────────

def draw_mp_menu(cols, rows, selected, frame, error_msg=''):
    """Menú de inicio: Crear Servidor / Unirse por IP."""
    buf = ['\033[?25l']
    for r in range(1, rows + 1):
        buf.append(cup(r, 1) + '\033[2K')

    write_centered(buf, 2, '═══  MULTIJUGADOR  ═══', cols, C_GOLD + BOLD)
    write_centered(buf, 3, 'Juega con amigos en la misma red o por internet', cols, C_GRAY + DIM)

    options = [
        ('🖥  CREAR SERVIDOR',  'Tú eres el host. Comparte tu IP y puerto.'),
        ('🔌  UNIRSE A SERVER', 'Conéctate a la IP:puerto de otro jugador.'),
        ('◀   VOLVER',          ''),
    ]

    box_w = min(54, cols - 6)
    box_c = (cols - box_w) // 2
    box_r = rows // 2 - 4
    draw_box(buf, box_r, box_c, box_w, len(options) * 3 + 3, C_DIM)

    r = box_r + 2
    for i, (label, desc) in enumerate(options):
        if i == selected:
            color  = C_GOLD + BOLD
            marker = '▶ '
        else:
            color  = C_WHITE
            marker = '  '
        buf.append(cup(r, box_c + 3) + color + marker + label + RESET)
        if desc:
            buf.append(cup(r+1, box_c + 5) + C_GRAY + DIM + desc + RESET)
        r += 3

    if error_msg:
        write_centered(buf, box_r + len(options)*3 + 4, error_msg, cols, C_RED)

    write_centered(buf, rows-2, 'W/S → mover   Enter → confirmar   ESC → volver', cols, C_DIM)
    write(''.join(buf))


def show_mp_mode_menu():
    """Retorna 'host', 'join' o 'back'."""
    selected = 0
    actions  = ['host','join','back']
    write(clear_screen() + '\033[?25l')
    frame = 0
    while True:
        cols, rows = get_sz()
        draw_mp_menu(cols, rows, selected, frame)
        frame += 1
        key = read_key(timeout=0.06)
        if key in ('w','up'):
            selected = (selected-1) % 3
        elif key in ('s','down'):
            selected = (selected+1) % 3
        elif key in ('\r','\n',' '):
            return actions[selected]
        elif key in ('esc','q','\x03'):
            return 'back'


def draw_host_screen(cols, rows, world_name, ip, port, logs, player_count):
    """Pantalla del host mientras el servidor corre."""
    buf = ['\033[?25l']
    for r in range(1, rows+1):
        buf.append(cup(r,1)+'\033[2K')

    title = f'🖥  SERVIDOR ACTIVO  ·  mundo: {world_name}'
    write_centered(buf, 1, title, cols, C_GOLD + BOLD)

    info = f'Tu IP: {C_CYAN}{BOLD}{ip}{RESET}{C_WHITE}   Puerto: {C_CYAN}{BOLD}{port}{RESET}{C_WHITE}   Jugadores: {player_count}'
    write_centered(buf, 2, f'Tu IP: {ip}   Puerto: {port}   Jugadores: {player_count}', cols, C_WHITE)
    write_centered(buf, 3, f'Comparte esta IP y puerto con tus amigos', cols, C_GRAY+DIM)

    # Log box
    box_h  = min(rows - 8, len(logs) + 2)
    box_w  = min(cols - 4, 90)
    box_r  = 5
    box_c  = (cols - box_w) // 2
    draw_box(buf, box_r, box_c, box_w, box_h, C_DIM)
    for i, line in enumerate(logs[-(box_h-2):]):
        buf.append(cup(box_r+1+i, box_c+2) + C_WHITE + line[:box_w-4] + RESET)

    write_centered(buf, rows-2,
        'Enter → entrar al juego como host   ESC/Q → detener servidor',
        cols, C_DIM)
    write(''.join(buf))


# ── In-game key reader ────────────────────────────────────────────────────────
# ── In-game key reader ────────────────────────────────────────────────────────

def game_read_key(timeout=0.05):
    if select.select([sys.stdin], [], [], timeout)[0]:
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            rest = sys.stdin.read(2) if select.select([sys.stdin], [], [], 0.02)[0] else ''
            return {'[A': 'w', '[B': 's', '[C': 'e', '[D': 'q'}.get(rest, ch)
        return ch
    return ''


# ── Single-player launch ──────────────────────────────────────────────────────

def launch_singleplayer(fd):
    """Inicia partida single-player clásica (save en ~/.arcane_abyss_save.json)."""
    # Nombre de cuenta (opcional para SP)
    cols, rows = get_sz()
    pname = read_text_input('Tu nombre de héroe:', cols, rows, max_len=16)
    if not pname:
        pname = 'Héroe'

    # Selección de raza
    race_id = show_race_menu()

    write(clear_screen() + '\033[?25l')

    from world    import WorldManager
    from player   import Player
    from renderer import Renderer
    from combat   import Combat
    from ui       import UI
    from engine   import Engine
    from races    import apply_race

    cols, rows = get_sz()
    wm         = WorldManager()
    player     = Player(wm.current)
    player.name = pname
    apply_race(player, race_id)

    renderer = Renderer(cols, rows)
    ui_obj   = UI(cols, rows, player, wm)
    combat   = Combat(player)
    engine   = Engine(player, wm, combat, ui_obj)

    # Check for existing save
    save_path = os.path.expanduser('~/.arcane_abyss_save.json')
    if os.path.exists(save_path):
        msg = engine._load_game()
        ui_obj.log(msg, C_GOLD)
    else:
        ui_obj.log(f"¡Bienvenido {pname}! Raza: {race_id.capitalize()}", C_GOLD)

    engine.run(renderer, ui_obj, game_read_key)


# ── Multiplayer launch ────────────────────────────────────────────────────────

def _mp_get_identity(cols, rows, fd):
    """Pide nombre + raza. Retorna (pname, race_id) o (None, None)."""
    pname = read_text_input(
        'Tu nombre de jugador (sin espacios):',
        cols, rows, max_len=20,
        allowed='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
    )
    if not pname:
        return None, None
    race_id = show_race_menu()
    return pname, race_id


def _mp_launch_game(player_obj, wm, race_id, pname, session, world_id):
    """Arranca el motor de juego con sesión multijugador adjunta."""
    from renderer import Renderer
    from combat   import Combat
    from ui       import UI
    from engine   import Engine

    cols, rows = get_sz()
    renderer = Renderer(cols, rows)
    ui_obj   = UI(cols, rows, player_obj, wm)
    combat   = Combat(player_obj)
    engine   = Engine(player_obj, wm, combat, ui_obj)

    engine._mp_session  = session
    engine._player_name = pname

    ui_obj.log(f"✦ Héroe: {pname}  |  Raza: {race_id.capitalize()}", C_GOLD)
    ui_obj.log("WASD mover  QE girar  K melee  R flecha  Z hechizo  F hablar", C_GRAY)

    engine.run(renderer, ui_obj, game_read_key)
    session.disconnect()


def launch_multiplayer(fd):
    """Menú multijugador TCP: host o cliente."""
    cols, rows = get_sz()

    # 1) Elegir modo
    mode = show_mp_mode_menu()
    if mode == 'back':
        return

    cols, rows = get_sz()

    # ── HOST ──────────────────────────────────────────────────────────────────
    if mode == 'host':
        from multiplayer import (GameServer, GameClient, MultiplayerSession,
                                 list_saved_worlds, DEFAULT_PORT)
        from world  import WorldManager
        from player import Player
        from races  import apply_race

        # Nombre del mundo
        write(clear_screen() + '\033[?25l')
        worlds = list_saved_worlds()
        world_name = read_text_input(
            f'Nombre del mundo (existentes: {", ".join(worlds) or "ninguno"}):',
            cols, rows, max_len=24,
            allowed='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
        )
        if not world_name:
            return

        # Puerto
        write(clear_screen() + '\033[?25l')
        port_str = read_text_input(
            f'Puerto (Enter = {DEFAULT_PORT}):',
            cols, rows, max_len=5,
            allowed='0123456789'
        )
        port = int(port_str) if port_str.isdigit() else DEFAULT_PORT

        # Identidad del host
        write(clear_screen() + '\033[?25l')
        pname, race_id = _mp_get_identity(cols, rows, fd)
        if not pname:
            return

        write(clear_screen() + '\033[?25l')

        # Arrancar servidor en hilo
        server = GameServer(world_name, host='0.0.0.0', port=port)
        srv_thread = __import__('threading').Thread(target=server.start, daemon=True)
        srv_thread.start()

        # Esperar hasta que el servidor esté escuchando (máx 5s)
        import time as _t, socket as _sk
        cols, rows = get_sz()
        _draw_waiting(cols, rows, port)
        ready = False
        for _i in range(50):          # 50 × 0.1s = 5 segundos máximo
            _t.sleep(0.1)
            try:
                _ts = _sk.socket(_sk.AF_INET, _sk.SOCK_STREAM)
                _ts.settimeout(0.2)
                _ts.connect(('127.0.0.1', port))
                _ts.close()
                ready = True
                break
            except Exception:
                pass
        if not ready:
            _draw_error(cols, rows,
                f"El servidor no pudo iniciar en el puerto {port}.\n"
                "¿Está ocupado ese puerto? Prueba con otro.")
            read_key(timeout=4.0)
            server.stop()
            return

        # Host también se conecta como cliente
        client = GameClient('127.0.0.1', port, pname, race_id, 'world_dungeon')
        ok, saved_data = client.connect()
        if not ok:
            _draw_error(cols, rows, f"Error interno al conectar: {saved_data}")
            read_key(timeout=4.0)
            server.stop()
            return

        # Mostrar pantalla de servidor mientras se espera o se entra
        ip   = server.get_ip()
        logs = []
        write(clear_screen() + '\033[?25l')
        import time as _t
        deadline = _t.time() + 999
        while True:
            cols, rows = get_sz()
            logs = server.get_logs(rows - 10)
            draw_host_screen(cols, rows, world_name, ip, port, logs, server.player_count())
            key = read_key(timeout=0.15)
            if key in ('\r','\n',' ') or (key and key not in ('esc','q','\x03',' ','')):
                break
            if key in ('esc','q','\x03'):
                server.stop()
                return

        # Entrar al juego
        wm     = WorldManager()
        player = Player(wm.current)
        player.name = pname
        apply_race(player, race_id)

        # Cargar datos guardados si existen
        if saved_data:
            from multiplayer import dict_to_player
            wid = dict_to_player(saved_data, player)
            apply_race(player, race_id)  # re-aplicar raza sobre datos cargados
            if wid != 'world_dungeon':
                try:
                    new_w, _ = wm.travel(wid, [int(player.x), int(player.y)])
                    player.world = new_w
                    new_w.reveal_around(player.x, player.y, radius=5)
                except Exception:
                    pass

        client.set_player(player)
        session = MultiplayerSession(client)
        session.set_world_id(wm.current_id)

        write(clear_screen() + '\033[?25l')
        _mp_launch_game(player, wm, race_id, pname, session, wm.current_id)
        server.stop()

    # ── CLIENTE ───────────────────────────────────────────────────────────────
    elif mode == 'join':
        from multiplayer import (GameClient, MultiplayerSession, DEFAULT_PORT)
        from world  import WorldManager
        from player import Player
        from races  import apply_race

        # IP
        write(clear_screen() + '\033[?25l')
        ip = read_text_input(
            'IP del servidor (ej: 192.168.1.10):',
            cols, rows, max_len=45,
            allowed='0123456789abcdefABCDEF:.'
        )
        if not ip:
            return

        # Puerto
        write(clear_screen() + '\033[?25l')
        port_str = read_text_input(
            f'Puerto (Enter = {DEFAULT_PORT}):',
            cols, rows, max_len=5,
            allowed='0123456789'
        )
        port = int(port_str) if port_str.isdigit() else DEFAULT_PORT

        # Identidad
        write(clear_screen() + '\033[?25l')
        pname, race_id = _mp_get_identity(cols, rows, fd)
        if not pname:
            return

        # Conectar
        write(clear_screen() + '\033[?25l')
        cols, rows = get_sz()
        _draw_connecting(cols, rows, ip, port)

        client = GameClient(ip, port, pname, race_id, 'world_dungeon')
        ok, result = client.connect()

        if not ok:
            _draw_error(cols, rows, f"No se pudo conectar: {result}")
            read_key(timeout=3.0)
            return

        # Construir jugador con datos del servidor
        wm     = WorldManager()
        player = Player(wm.current)
        player.name = pname
        apply_race(player, race_id)

        saved_data = result
        if saved_data:
            from multiplayer import dict_to_player
            wid = dict_to_player(saved_data, player)
            apply_race(player, race_id)
            if wid != 'world_dungeon':
                try:
                    new_w, _ = wm.travel(wid, [int(player.x), int(player.y)])
                    player.world = new_w
                    new_w.reveal_around(player.x, player.y, radius=5)
                except Exception:
                    pass

        client.set_player(player)
        session = MultiplayerSession(client)
        session.set_world_id(wm.current_id)

        write(clear_screen() + '\033[?25l')
        _mp_launch_game(player, wm, race_id, pname, session, wm.current_id)


def _draw_waiting(cols, rows, port):
    buf = ['\033[?25l']
    for r in range(1, rows+1):
        buf.append(cup(r,1)+'\033[2K')
    write_centered(buf, rows//2-1, f'Iniciando servidor en puerto {port}…', cols, C_CYAN+BOLD)
    write_centered(buf, rows//2+1, 'Espera un momento…', cols, C_GRAY+DIM)
    write(''.join(buf))

def _draw_connecting(cols, rows, ip, port):
    buf = ['\033[?25l']
    for r in range(1, rows+1):
        buf.append(cup(r,1)+'\033[2K')
    write_centered(buf, rows//2-1, f'Conectando a {ip}:{port}…', cols, C_CYAN+BOLD)
    write_centered(buf, rows//2+1, 'Por favor espera…', cols, C_GRAY+DIM)
    write(''.join(buf))

def _draw_error(cols, rows, msg):
    buf = ['\033[?25l']
    for r in range(1, rows+1):
        buf.append(cup(r,1)+'\033[2K')
    write_centered(buf, rows//2-1, '✗  Error de conexión', cols, C_RED+BOLD)
    write_centered(buf, rows//2+1, msg, cols, C_WHITE)
    write_centered(buf, rows//2+3, 'Presiona cualquier tecla…', cols, C_GRAY+DIM)
    write(''.join(buf))


# ── Main ────────────────────────────────────────────────────────────────────
# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    cols, rows = get_sz()
    if cols < 80 or rows < 20:
        print(f"\033[33mWarning: terminal {cols}x{rows}. Mínimo recomendado 120x40.\033[0m")
        print("Continuar? [Y/n] ", end='', flush=True)
        if input().strip().lower() == 'n':
            return

    fd  = sys.stdin.fileno()
    old = None

    sys.stdout.write('\033[?1049h\033[?25l')
    sys.stdout.flush()

    try:
        old    = set_raw(fd)
        choice = show_main_menu()

        if choice == 'quit':
            return

        write(clear_screen() + '\033[?25l')

        if choice == 'play':
            launch_singleplayer(fd)

        elif choice == 'multi':
            launch_multiplayer(fd)

        elif choice == 'help':
            _show_help(fd)

    except Exception as ex:
        if old:
            restore_term(fd, old)
        sys.stdout.write('\033[?1049l\033[?25h')
        sys.stdout.flush()
        print(f"\n\033[31mError: {ex}\033[0m")
        import traceback
        traceback.print_exc()
        return

    finally:
        if old:
            try:
                restore_term(fd, old)
            except Exception:
                pass
        sys.stdout.write('\033[?1049l\033[?25h\n')
        sys.stdout.flush()

    print("\n\033[32mGracias por jugar Arcane Abyss!\033[0m\n")


def _show_help(fd):
    cols, rows = get_sz()
    buf = ['\033[?25l']
    for r in range(1, rows + 1):
        buf.append(cup(r, 1) + '\033[2K')

    lines = [
        ("═══  AYUDA — CONTROLES  ═══", C_GOLD + BOLD),
        ("", ""),
        ("MOVIMIENTO",   C_CYAN + BOLD),
        ("  W / ↑   — Avanzar",          C_WHITE),
        ("  S / ↓   — Retroceder",        C_WHITE),
        ("  A        — Strafe izquierda", C_WHITE),
        ("  D        — Strafe derecha",   C_WHITE),
        ("  Q / ←   — Girar izquierda",  C_WHITE),
        ("  E / →   — Girar derecha",    C_WHITE),
        ("", ""),
        ("COMBATE",     C_CYAN + BOLD),
        ("  K   — Atacar cuerpo a cuerpo", C_WHITE),
        ("  R   — Disparar flecha (bow equipado)", C_WHITE),
        ("  Z   — Lanzar hechizo activo",  C_WHITE),
        ("  X   — Cambiar hechizo activo", C_WHITE),
        ("  B   — Bloquear (escudo necesario)", C_WHITE),
        ("  [ESPACIO] — Entrar en portal", C_WHITE),
        ("", ""),
        ("INTERACCIÓN", C_CYAN + BOLD),
        ("  T   — Recoger item del suelo", C_WHITE),
        ("  F   — Hablar con NPC cercano", C_WHITE),
        ("  /   — Abrir consola de texto", C_WHITE),
        ("", ""),
        ("COMANDOS DE TEXTO (/ primero)", C_CYAN + BOLD),
        ("  inv  — Ver inventario", C_WHITE),
        ("  use <n>  — Usar item", C_WHITE),
        ("  shop / buy / sell", C_WHITE),
        ("  forge / order", C_WHITE),
        ("  mine / chop", C_WHITE),
        ("  save / load", C_WHITE),
        ("  skills / map / quests", C_WHITE),
        ("", ""),
        ("Presiona cualquier tecla para volver...", C_DIM),
    ]

    start_row = max(1, (rows - len(lines)) // 2)
    for i, (text, color) in enumerate(lines):
        c = center_col(text, cols) if not text.startswith("  ") else max(1, (cols - 50) // 2)
        buf.append(cup(start_row + i, c) + color + text + RESET)

    write(''.join(buf))

    while not select.select([sys.stdin], [], [], 0.05)[0]:
        pass
    try:
        sys.stdin.read(1)
    except Exception:
        pass


if __name__ == '__main__':
    main()
