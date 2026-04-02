"""
ui.py — Panels responsivos al tamaño de terminal.

Layout:
┌─────────────────────────────┬──────┬──────┐
│         3D VIEW             │ MAP  │ INV  │
│                             ├──────┤(slim)│
│                             │STATS │      │
├─────────────────────────────┴──────┴──────┤
│ LOG  msg  msg  msg  msg  msg  msg  (tall) │
│ LOG  msg  msg  msg  msg  msg  msg         │
│ LOG  msg  msg  msg  msg  msg  msg         │
├───────────────────────────────────────────┤
│▶ comando aquí…  (/ para activar)          │
└───────────────────────────────────────────┘

El log es multi-línea (LOG_ROWS configurable).
El inventario es delgado para dar más espacio a la vista 3D.
La línea de comando recibe texto libre y lo pasa al engine.
"""


import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, sys, re, time

# ── ANSI ─────────────────────────────────────────────────────────────────────
RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'

def fg(r,g,b): return f'\033[38;2;{r};{g};{b}m'
def bg(r,g,b): return f'\033[48;2;{r};{g};{b}m'
def move_to(row, col): return f'\033[{row};{col}H'
def clear_screen(): return '\033[2J\033[H'

# ── Colores ───────────────────────────────────────────────────────────────────
C_GOLD   = fg(220,180, 40)
C_RED    = fg(220, 60, 60)
C_GREEN  = fg( 50,200, 80)
C_BLUE   = fg( 60,140,220)
C_PURPLE = fg(160, 80,220)
C_GRAY   = fg(150,150,150)
C_WHITE  = fg(220,220,220)
C_CYAN   = fg( 60,200,200)
C_ORANGE = fg(220,140, 40)
C_DIM    = fg( 55, 55, 55)
C_LIME   = fg(120,220, 40)

BORDER_C = fg(200,200,200)

# ── Box-drawing ───────────────────────────────────────────────────────────────
H='─'; V='│'; TL='┌'; TR='┐'; BL='└'; BR='┘'
TT='┬'; BB='┴'; LL='├'; RR='┤'; XX='┼'

# Número de líneas de mensajes en el log (ajusta libremente)
LOG_ROWS = 6


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_ansi(s):
    return re.sub(r'\033\[[^m]*m', '', s)

def vis_len(s):
    plain = strip_ansi(s)
    w = 0
    for ch in plain:
        w += 2 if ord(ch) > 0x2000 else 1
    return w

def pad_to(s, width):
    vl = vis_len(s)
    if vl < width:
        return s + ' '*(width-vl)
    return s

def bar(val, max_val, width, fill_color):
    if width < 2: return ''
    filled = int((val/max_val)*width) if max_val else 0
    filled = max(0, min(filled, width))
    return fill_color+'█'*filled + C_DIM+'░'*(width-filled)+RESET


# ── Layout ────────────────────────────────────────────────────────────────────

class Layout:
    def __init__(self, cols, rows):
        self.update(cols, rows)

    def update(self, cols, rows):
        self.cols    = cols
        self.rows    = rows
        self.compact = cols < 90

        # log panel height: LOG_ROWS msg lines + 1 cmd line + 3 borders
        log_panel_h  = LOG_ROWS + 1 + 3

        # 3D view gets the rest
        self.view_h = max(10, rows - log_panel_h)

        # first row of log panel border (right after 3D bottom border)
        self.log_top = self.view_h + 2

        if self.compact:
            right_w     = max(16, min(22, cols // 5))
            self.view_w = cols - right_w - 1
            self.map_w  = right_w
            self.inv_w  = 0
            self.map_h  = self.view_h // 2
            self.stat_h = self.view_h - self.map_h
        else:
            # slim inventory: ~1/7 of screen width
            self.inv_w  = max(14, min(18, cols // 7))
            map_plus    = max(22, cols // 5)
            self.map_w  = map_plus
            right_total = map_plus + self.inv_w
            self.view_w = cols - right_total - 2
            self.map_h  = int(self.view_h * 0.55)
            self.stat_h = self.view_h - self.map_h

        self.map_col = self.view_w + 2
        self.inv_col = self.view_w + self.map_w + 3 if not self.compact else 0
        self.view_w  = max(20, self.view_w)
        self.map_w   = max(10, self.map_w)


# ── UI ────────────────────────────────────────────────────────────────────────

class UI:
    def __init__(self, cols, rows, player, wm):
        self.player   = player
        self._wm      = wm
        self.logs     = []
        self.max_logs = 600
        self.L        = Layout(cols, rows)

        # command input
        self.cmd_buf  = ''
        self.cmd_mode = False
        self._cmd_cb  = None   # callable(str)

    def resize(self, cols, rows):
        self.L.update(cols, rows)

    def set_cmd_callback(self, fn):
        self._cmd_cb = fn

    @property
    def world(self):
        return self._wm.current if hasattr(self._wm, 'current') else self._wm

    @property
    def view_w(self): return self.L.view_w
    @property
    def view_h(self): return self.L.view_h

    # ── render all ───────────────────────────────────────────────────────────

    def render_all(self, frame_rows, hud_parts=None, sprite_buf=None):
        # Detect terminal resize before rendering
        try:
            import os as _os
            sz = _os.get_terminal_size()
            if sz.columns != self.L.cols or sz.lines != self.L.rows:
                self.resize(sz.columns, sz.lines)
        except Exception:
            pass

        buf = ['\033[?25l\033[H']   # hide cursor + home position
        self._draw_3d(buf, frame_rows)
        self._draw_map(buf)
        self._draw_stats(buf)
        if not self.L.compact:
            self._draw_inventory(buf)
        self._draw_log(buf)
        self._draw_borders(buf)
        if sprite_buf:
            buf.extend(sprite_buf)
        if hud_parts:
            buf.extend(hud_parts)
        # Single atomic write to avoid partial-frame flicker
        out = ''.join(buf)
        sys.stdout.buffer.write(out.encode('utf-8', errors='replace'))
        sys.stdout.buffer.flush()

    # ── 3D view ──────────────────────────────────────────────────────────────

    def _draw_3d(self, buf, frame_rows):
        vw, vh = self.L.view_w, self.L.view_h
        for ri, row_str in enumerate(frame_rows[:vh]):
            vl = vis_len(row_str)
            pad = max(0, vw - vl)
            buf.append(move_to(ri+1, 1))
            buf.append(row_str)
            if pad:
                buf.append('\033[K' if pad > 4 else ' ' * pad)
        for ri in range(len(frame_rows), vh):
            buf.append(move_to(ri+1, 1))
            buf.append('\033[K')

    # ── minimap ───────────────────────────────────────────────────────────────

    def _draw_map(self, buf):
        L    = self.L
        p    = self.player
        w    = self.world
        cx   = int(p.x)
        cy   = int(p.y)
        col0 = L.map_col
        hx   = (L.map_w - 3) // 2
        hy   = (L.map_h - 3) // 2

        for rel_y in range(-hy, hy+1):
            my     = cy + rel_y
            draw_r = rel_y + hy + 2
            buf.append(move_to(draw_r, col0))
            line = []
            for rel_x in range(-hx, hx+1):
                mx = cx + rel_x
                if rel_x == 0 and rel_y == 0:
                    arrows = '→↗↑↖←↙↓↘'
                    sec = int(p.angle/(2*math.pi)*8+0.5) % 8
                    line.append(C_CYAN+BOLD+arrows[sec]+RESET)
                    continue
                if not (0 <= mx < w.width and 0 <= my < w.height):
                    line.append(' ')
                    continue
                if not (0 <= my < len(w.revealed) and 0 <= mx < len(w.revealed[my])):
                    line.append(' ')
                    continue
                if not w.revealed[my][mx]:
                    line.append(' ')
                    continue
                has_e = any(int(e['x'])==mx and int(e['y'])==my and e['alive']
                            for e in w.enemies)
                has_boss = any(int(e['x'])==mx and int(e['y'])==my and e['alive'] and e.get('boss')
                               for e in w.enemies)
                has_i = (mx, my) in w.items
                has_v = (mx, my) in getattr(w, 'ore_veins', {}) and w.ore_veins[(mx,my)]['charges'] > 0
                if has_boss:
                    line.append(fg(255,50,50)+BOLD+'B'+RESET)
                elif has_e:
                    line.append(C_RED+'!'+RESET)
                elif has_i:
                    line.append(C_GOLD+'•'+RESET)
                elif has_v:
                    line.append(fg(80,200,255)+'*'+RESET)
                else:
                    try:
                        line.append(w.minimap_char(mx, my))
                    except (IndexError, KeyError):
                        line.append(' ')
            buf.append(''.join(line))

    # ── stats ─────────────────────────────────────────────────────────────────

    def _draw_stats(self, buf):
        L     = self.L
        p     = self.player
        w     = self.world
        x_off = L.map_col
        row0  = L.map_h + 2
        bw    = max(4, L.map_w - 8)

        def put(r, s):
            buf.append(move_to(row0+r, x_off))
            buf.append(s)

        put(0, f'{C_GOLD}{BOLD} ♦ Lv.{p.level}  {w.time_name()}{RESET}')
        put(1, f' {C_RED}HP{RESET} {bar(p.hp,p.max_hp,bw,C_RED)} {C_WHITE}{p.hp}/{p.max_hp}{RESET}')
        put(2, f' {C_BLUE}MP{RESET} {bar(p.mp,p.max_mp,bw,C_BLUE)} {C_WHITE}{p.mp}/{p.max_mp}{RESET}')
        put(3, f' {C_PURPLE}XP{RESET} {bar(p.xp,p.level*100,bw,C_PURPLE)} {p.xp}/{p.level*100}{RESET}')
        put(4, f' {C_ORANGE}ATK{RESET}{C_WHITE}{p.total_attack():3d}{RESET} {C_CYAN}DEF{RESET}{C_WHITE}{p.total_defense():3d}{RESET}')
        # mostrar % bloqueo de escudo si está equipado
        armor = p.equipped.get('armor')
        if armor and hasattr(p, 'shield_block_pct'):
            bp = int(p.shield_block_pct() * 100)
            if bp > 0:
                shield_label = '🛡' if bp >= 20 else '⛨'
                put(4, f' {C_ORANGE}ATK{RESET}{C_WHITE}{p.total_attack():3d}{RESET} {C_CYAN}DEF{RESET}{C_WHITE}{p.total_defense():2d}{RESET} {C_BLUE}{shield_label}{bp}%{RESET}')
        compass = '→↗↑↖←↙↓↘'
        sec = int(p.angle/(2*math.pi)*8+0.5) % 8
        put(5, f' {C_GRAY}{compass[sec]} ({p.x:.1f},{p.y:.1f}){RESET}')
        alive_e = sum(1 for e in w.enemies if e['alive'])
        put(6, f' {C_DIM}⚔{alive_e} 👣{p.steps}{RESET}  {C_GOLD}💰{p.gold}{RESET}')
        arr_col = C_ORANGE if p.arrows > 5 else C_RED
        put(7, f' {arr_col}->({p.arrows}){RESET} {C_PURPLE}[Z]{p.active_spell[:8]}{RESET}')
        # magic bonus from gear
        book_e = p.equipped.get('spellbook') or {}
        weap_e = p.equipped.get('weapon') or {}
        arm_e  = p.equipped.get('armor') or {}
        mgb    = book_e.get('magic_bonus',0) + weap_e.get('magic_bonus',0) + arm_e.get('magic_bonus',0)
        if mgb > 0:
            put(7, f' {arr_col}->({p.arrows}){RESET} {C_PURPLE}[Z]{p.active_spell[:6]} +{mgb}✨{RESET}')
        bline = ''
        for b in p.buffs[:3]:
            rem = max(0.0, b['expires']-time.time())
            cr, cg, cb = b['color']
            bline += fg(cr,cg,cb)+f'{b["label"]}:{rem:.0f}s'+RESET+' '
        if bline:
            put(8, ' '+bline)

        # ── skill XP bars ──────────────────────────────────────────────────────
        sbw = max(3, bw - 4)
        skrow = 9
        for sk, label, col in (('melee', 'MEL', C_RED), ('bow', 'BOW', C_ORANGE), ('magic', 'MAG', C_PURPLE)):
            lv  = p.skill_level.get(sk, 1)
            pct = p.skill_xp_pct(sk)
            put(skrow, f' {col}{label}{RESET}{C_DIM}Lv{lv}{RESET} {bar(int(pct*sbw),sbw,sbw,col)}{RESET}')
            skrow += 1

    # ── inventory (slim) ──────────────────────────────────────────────────────

    def _draw_inventory(self, buf):
        L     = self.L
        p     = self.player
        x_off = L.inv_col
        iw    = max(4, L.inv_w - 2)
        max_show = max(4, L.view_h - 7)

        weap   = p.equipped.get('weapon')
        armo   = p.equipped.get('armor')
        bow_e  = p.equipped.get('bow')
        book_e = p.equipped.get('spellbook')

        buf.append(move_to(2, x_off)); buf.append(C_PURPLE+'EQ'+RESET)
        buf.append(move_to(3, x_off))
        buf.append(f'{C_WHITE}{(weap["name"][:iw] if weap else "—")}{RESET}')
        buf.append(move_to(4, x_off))
        buf.append(f'{C_CYAN}{(armo["name"][:iw] if armo else "—")}{RESET}')
        buf.append(move_to(5, x_off))
        buf.append(f'{C_ORANGE}{(bow_e["name"][:iw] if bow_e else "—")}{RESET}')
        buf.append(move_to(6, x_off))
        buf.append(f'{C_PURPLE}{(book_e["name"][:iw] if book_e else "—")}{RESET}')
        buf.append(move_to(7, x_off)); buf.append(C_DIM+'──'+RESET)

        for i in range(max_show):
            buf.append(move_to(8+i, x_off))
            if i < len(p.inventory):
                item = p.inventory[i]
                t    = item.get('type', '')
                name = item.get('name', '?')[:iw-2]
                col  = (C_RED    if t == 'weapon'     else
                        C_BLUE   if t == 'armor'      else
                        C_GREEN  if t == 'consumable' else
                        C_ORANGE if t == 'material'   else
                        C_GOLD   if t == 'gold'       else C_WHITE)
                buf.append(f'{C_DIM}{i}{RESET}{col}{name}{RESET}')
            else:
                buf.append(f'{C_DIM}·{RESET}')

    # ── log (multi-line tall) ─────────────────────────────────────────────────

    def log(self, msg, color=None):
        c = color or C_WHITE
        self.logs.append(c + msg + RESET)
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

    def _draw_log(self, buf):
        L       = self.L
        avail_w = L.cols - 4   # inner width

        # Word-wrap all recent messages into avail_w-wide lines
        wrapped = []
        for msg in self.logs:
            plain = strip_ansi(msg)
            if vis_len(plain) <= avail_w:
                wrapped.append(msg)
            else:
                # chunk into avail_w visible chars (crude but works)
                chunk = msg
                while vis_len(strip_ansi(chunk)) > avail_w:
                    wrapped.append(chunk[:avail_w])
                    chunk = C_GRAY + '  ' + chunk[avail_w:] + RESET
                wrapped.append(chunk)

        # pick last LOG_ROWS lines
        visible = wrapped[-LOG_ROWS:] if len(wrapped) >= LOG_ROWS else wrapped
        while len(visible) < LOG_ROWS:
            visible.insert(0, '')

        inner_r0 = L.log_top + 1
        for i, line in enumerate(visible):
            buf.append(move_to(inner_r0 + i, 3))
            pl = vis_len(line)
            buf.append(line + ' ' * max(0, avail_w - pl))

        # command input line
        cmd_row = inner_r0 + LOG_ROWS + 1   # after msg divider
        buf.append(move_to(cmd_row, 3))
        if self.cmd_mode:
            prompt = (C_LIME + BOLD + '▶ ' + RESET +
                      C_WHITE + self.cmd_buf + RESET +
                      C_LIME + '█' + RESET)
        else:
            prompt = (C_DIM + '▶ ' + RESET +
                      C_DIM + 'pulsa / para escribir un comando' + RESET)
        buf.append(prompt + ' ' * max(0, avail_w - vis_len(strip_ansi(prompt))))

    # ── borders ───────────────────────────────────────────────────────────────

    def _draw_borders(self, buf):
        L        = self.L
        vw, mw, iw = L.view_w, L.map_w, L.inv_w
        vh, mh   = L.view_h, L.map_h
        bc       = BORDER_C
        total_w  = L.cols - 1
        log_top  = L.log_top
        # log panel: top border + LOG_ROWS msgs + divider + 1 cmd + bottom border
        log_bot  = log_top + LOG_ROWS + 3

        def hl(row, col, n, lc, rc, fill=H):
            buf.append(move_to(row, col))
            buf.append(bc+lc+fill*max(0,n)+rc+RESET)

        def vl(col, r1, r2):
            for r in range(r1, r2+1):
                buf.append(move_to(r, col))
                buf.append(bc+V+RESET)

        if L.compact:
            hl(1,    1, vw, TL, H)
            hl(1, vw+1, mw, TT, TR)
            vl(vw+1, 1, vh+1)
            hl(mh+2, vw+1, mw, LL, RR)
            hl(vh+1, 1, vw,    BL, H)
            hl(vh+1, vw+1, mw, BB, TR)
        else:
            mc = L.map_col
            ic = L.inv_col - 1
            hl(1, 1,   vw, TL, H)
            hl(1, mc,  mw, TT, TT)
            hl(1, ic,  iw, H,  TR)
            vl(mc, 1, vh+1)
            vl(ic, 1, vh+1)
            hl(mh+2, mc, mw, LL, RR)
            hl(vh+1, 1,  vw, BL, H)
            hl(vh+1, mc, mw, BB, BB)
            hl(vh+1, ic, iw, H,  BR)

        # log panel (full width)
        hl(log_top,          1, total_w-1, TL, TR)
        vl(1,           log_top+1, log_bot-1)
        vl(total_w,     log_top+1, log_bot-1)
        cmd_div = log_top + LOG_ROWS + 1
        hl(cmd_div,          1, total_w-1, LL, RR)
        hl(log_bot,          1, total_w-1, BL, BR)

        # labels
        def lbl(row, col, color, text):
            buf.append(move_to(row, col))
            buf.append(bc+'['+RESET+color+BOLD+text+RESET+bc+']'+RESET)

        lbl(1,       3,            C_GOLD,   'ARCANE ABYSS')
        lbl(1,       L.map_col+2,  C_CYAN,   'MAP')
        lbl(mh+2,    L.map_col+2,  C_ORANGE, 'STATS')
        if not L.compact:
            lbl(1,   L.inv_col+1,  C_PURPLE, 'INV')
        lbl(log_top, 3,            C_WHITE,  'LOG')
        lbl(cmd_div, 3,            C_LIME,   'CMD  /=escribir  Enter=enviar  Esc=cancelar')

    # ── HUD ───────────────────────────────────────────────────────────────────

    def hud_crosshair(self, buf):
        r = self.L.view_h // 2
        c = self.L.view_w // 2
        buf.append(move_to(r, c))
        buf.append(C_WHITE+'╋'+RESET)

    def hud_interact(self, buf, msg):
        buf.append(move_to(self.L.view_h-1, 3))
        buf.append(C_CYAN+BOLD+'['+msg+']'+RESET)

    def hud_buffs(self, buf, player):
        if not player.buffs:
            return
        col = 2
        for b in player.buffs:
            rem = max(0.0, b['expires'] - time.time())
            cr, cg, cb = b['color']
            tag = fg(cr,cg,cb)+BOLD+f"[{b['label']} {rem:.0f}s]"+RESET+' '
            buf.append(move_to(2, col))
            buf.append(tag)
            col += len(b['label']) + 8

    def hud_death(self, buf):
        msg = '  ☠  YOU HAVE DIED — PRESS X  ☠  '
        col = max(1, (self.L.view_w-len(msg))//2)
        buf.append(move_to(self.L.view_h//2, col))
        buf.append(C_RED+BOLD+msg+RESET)

    def hud_equipped_hand(self, buf, player, anim_state='idle', anim_tick=0):
        """
        Dibuja el sprite del ítem equipado en la esquina inferior derecha.
        Los espacios se omiten (transparente) para no tapar el mundo 3D.
        """
        vw = self.L.view_w
        vh = self.L.view_h

        weap  = player.equipped.get('weapon')
        bow   = player.equipped.get('bow')
        book  = player.equipped.get('spellbook')
        armor = player.equipped.get('armor')
        has_shield = bool(armor and (
            armor.get('block', 0) > 0 or
            'shield' in armor.get('name', '').lower()
        ))

        # ── sprites idle (perspectiva primera persona, esquina inferior derecha)
        # Cada línea: los espacios son TRANSPARENTES (no se dibujan).
        # El sprite se ancla por la esquina inferior derecha del view.
        HAND_SPRITES = {
            'sword': [
                r"      /",
                r"     / ",
                r"    /  ",
                r"   */  ",
                r"   |/  ",
                r"  _|   ",
                r" (/    ",
                r"/`     ",
            ],
            'longsword': [
                r"     /",
                r"    / ",
                r"   /  ",
                r"  /   ",
                r" */   ",
                r" |/   ",
                r" |    ",
                r"/|    ",
                r"`'    ",
            ],
            'shortsword': [
                r"    /",
                r"   */",
                r"   |/",
                r"  _| ",
                r" (`  ",
                r"/`   ",
            ],
            'dagger': [
                r"   ^ ",
                r"   | ",
                r"  /| ",
                r" / | ",
                r"(  ' ",
                r"`    ",
            ],
            'blade': [
                r"    / ",
                r"   *  ",
                r"  /|  ",
                r" / |  ",
                r"(  '  ",
                r"`     ",
            ],
            'spear': [
                r"    /\  ",
                r"    ||  ",
                r"    ||  ",
                r"   /|   ",
                r"  / |   ",
                r" /      ",
                r"/       ",
            ],
            'axe': [
                r"   /\   ",
                r"  /##\  ",
                r"  \##/  ",
                r"   \/   ",
                r"   |    ",
                r"  /|    ",
                r" / |    ",
                r"/       ",
            ],
            'battleaxe': [
                r"  /\/\  ",
                r" /####\ ",
                r" \####/ ",
                r"  \/\/  ",
                r"   ||   ",
                r"  /||   ",
                r" / ||   ",
                r"/       ",
            ],
            'mace': [
                r"  [###] ",
                r"  |###| ",
                r"  [###] ",
                r"    |   ",
                r"   /|   ",
                r"  / |   ",
                r" /      ",
            ],
            'hammer': [
                r" [=====]",
                r" |     |",
                r" [=====]",
                r"    |   ",
                r"   /|   ",
                r"  / |   ",
                r" /      ",
            ],
            'club': [
                r"  ,###. ",
                r" (####) ",
                r"  `###' ",
                r"    |   ",
                r"   /|   ",
                r"  /     ",
            ],
            'bow': [
                r"  )     ",
                r" )|     ",
                r")|=-----",
                r" )|     ",
                r"  )     ",
                r"   \    ",
                r"    \   ",
            ],
            'shortbow': [
                r" )    ",
                r")|----",
                r" )    ",
                r"  \   ",
                r"   \  ",
            ],
            'longbow': [
                r"   )     ",
                r"  )|     ",
                r" )|------",
                r"  )|     ",
                r"   )     ",
                r"    \    ",
                r"     \   ",
                r"      \  ",
            ],
            'crossbow': [
                r"  ,---. ",
                r" (=====)",
                r"==|===|=",
                r"  |   | ",
                r"  |  /  ",
                r"  | /   ",
                r"  |/    ",
            ],
            'staff': [
                r"  o~o  ",
                r"  \|/  ",
                r"   |   ",
                r"   |   ",
                r"   |   ",
                r"  /    ",
                r" /     ",
                r"/      ",
            ],
            'wand': [
                r"  *  ",
                r"  |  ",
                r"  |  ",
                r" /   ",
                r"/    ",
            ],
            'spellbook': [
                r" ,-----.",
                r" |* * *|",
                r" | ~~~ |",
                r" |* * *|",
                r" | ~~~ |",
                r" `-----'",
                r"    \   ",
                r"     \  ",
            ],
            'tome': [
                r" ,-----.",
                r" |ooooo|",
                r" |-----|",
                r" |ooooo|",
                r" `-----'",
                r"    \   ",
                r"     \  ",
            ],
            'fist': [
                r"  ,---, ",
                r" (##### ",
                r" (#####|",
                r" (#####|",
                r" (####' ",
                r"  `---' ",
                r"    |   ",
                r"   /    ",
            ],
        }

        # ── sprites de ataque (más adelantados, rotados) ───────────────────────
        ATTACK_OVERLAY = {
            'sword': [
                r"  *    ",
                r"  |\   ",
                r"  | \  ",
                r"  |  \ ",
                r"  |    ",
                r" /|    ",
                r"`      ",
            ],
            'dagger': [
                r" ^   ",
                r" |\  ",
                r" | \ ",
                r"(`   ",
                r"`    ",
            ],
            'axe': [
                r"  /\  ",
                r" /##\ ",
                r" \##/ ",
                r"  \/  ",
                r"  |   ",
                r" /    ",
                r"`     ",
            ],
            'mace': [
                r" [###]",
                r" |###|",
                r" [###]",
                r"   \  ",
                r"    \ ",
                r"     \ ",
                r"      ",
            ],
            'bow': [
                r"  )      ",
                r")|=---->>",
                r"  )      ",
                r"   \     ",
                r"    \    ",
            ],
            'spellbook': [
                r" *~~~* ",
                r"*~~~~~*",
                r"|*   *|",
                r"|     |",
                r"`-----'",
                r"   \   ",
                r"    \  ",
            ],
            'fist': [
                r" ,---, ",
                r"(#####|",
                r"(#####|",
                r"(####' ",
                r" `---' ",
                r"   /   ",
                r"  /    ",
            ],
            'staff': [
                r" *~*~* ",
                r"  \|/  ",
                r"   |   ",
                r"  /    ",
                r" /     ",
                r"/      ",
            ],
        }

        # ── escudo alzado ──────────────────────────────────────────────────────
        BLOCK_FRAME = [
            r"  ,----,  ",
            r" / _  _ \ ",
            r"| ( \/ ) |",
            r"| |    | |",
            r"| |    | |",
            r" \_\__/_/ ",
            r"   |  |   ",
            r"   `--'   ",
        ]

        # ── seleccionar sprite base ────────────────────────────────────────────
        name = ''
        if weap:   name = weap.get('name', '').lower()
        elif bow:  name = bow.get('name', '').lower()
        elif book: name = book.get('name', '').lower()
        else:      name = 'fist'

        art = None
        for key in sorted(HAND_SPRITES.keys(), key=len, reverse=True):
            if key in name:
                art = HAND_SPRITES[key]
                break
        if art is None:
            if weap:   art = HAND_SPRITES['sword']
            elif bow:  art = HAND_SPRITES['bow']
            elif book: art = HAND_SPRITES['spellbook']
            else:      art = HAND_SPRITES['fist']

        # ── color base según equipamiento ──────────────────────────────────────
        if weap:
            base_color = fg(200, 210, 220)   # acero plateado
        elif bow:
            base_color = fg(180, 140,  70)   # madera
        elif book:
            base_color = fg(140, 100, 220)   # magia
        else:
            base_color = fg(220, 180, 140)   # piel

        anim_color = base_color
        offset_row = 0

        # ── animaciones ────────────────────────────────────────────────────────
        if anim_state == 'block' and has_shield:
            art        = BLOCK_FRAME
            anim_color = fg(160, 200, 240)
            offset_row = -2

        elif anim_state == 'attack':
            attack_art = None
            for key in sorted(ATTACK_OVERLAY.keys(), key=len, reverse=True):
                if key in name:
                    attack_art = ATTACK_OVERLAY[key]
                    break
            if attack_art is None:
                if not weap and not bow and not book:
                    attack_art = ATTACK_OVERLAY['fist']
                else:
                    attack_art = ATTACK_OVERLAY['sword']
            if attack_art:
                art = attack_art
            # color más brillante al atacar
            if weap:   anim_color = fg(240, 240, 120)
            elif bow:  anim_color = fg(220, 190,  80)
            elif book: anim_color = fg(200, 120, 255)
            else:      anim_color = fg(255, 200, 140)
            offset_row = -1

        # ── render: caracter a caracter, espacios = transparente ──────────────
        art_w     = max(len(l) for l in art)
        art_h     = len(art)
        col_start = vw - art_w      # pegado a la derecha del view
        row_start = vh - art_h + offset_row

        for i, line in enumerate(art):
            r = row_start + i
            if r < 1 or r > vh:
                continue
            for j, ch in enumerate(line):
                if ch == ' ':
                    continue        # transparente — no sobreescribir el mundo
                c = col_start + j
                if c < 1 or c > vw:
                    continue
                buf.append(move_to(r, c))
                buf.append(anim_color + BOLD + ch + RESET)

    # ── command input ─────────────────────────────────────────────────────────

    def handle_cmd_key(self, ch):
        """
        Feed a raw character into the command buffer.
        Returns True if a complete command was dispatched.
        """
        if not self.cmd_mode:
            if ch == '/':
                self.cmd_mode = True
                self.cmd_buf  = ''
            return False

        if ch in ('\r', '\n'):
            cmd = self.cmd_buf.strip()
            self.cmd_mode = False
            self.cmd_buf  = ''
            if cmd and self._cmd_cb:
                self._cmd_cb(cmd)
            return True

        if ch in ('\x7f', '\x08'):
            self.cmd_buf = self.cmd_buf[:-1]
            return False

        if ch == '\x1b':
            self.cmd_mode = False
            self.cmd_buf  = ''
            return False

        if ch.isprintable():
            self.cmd_buf += ch

        return False

    # ── help screen ──────────────────────────────────────────────────────────

    def draw_help(self):
        """
        Renders the help screen using absolute CUP positioning only.
        Never uses \\n so it works correctly in raw-mode terminals.
        """
        import os as _os
        try:
            sz   = _os.get_terminal_size()
            cols = sz.columns
            rows = sz.lines
        except Exception:
            cols = self.L.cols
            rows = self.L.rows

        w    = self.world
        wide = cols >= 100   # two-column layout when wide enough

        # ── content lines (plain strings with ANSI colour) ────────────────
        header = [
            f'{C_GOLD}{BOLD}╔══════════════════════════════════════════════╗{RESET}',
            f'{C_GOLD}{BOLD}║        ARCANE ABYSS  —  AYUDA                ║{RESET}',
            f'{C_GOLD}{BOLD}╚══════════════════════════════════════════════╝{RESET}',
            '',
        ]

        col_left = [
            f'{C_LIME}CONTROLES{RESET}',
            f'{C_CYAN}WASD{RESET} Mover/strafe  {C_CYAN}QE{RESET} Girar',
            f'{C_RED}K{RESET} Melee  {C_ORANGE}R{RESET} Flecha  {C_PURPLE}Z{RESET} Hechizo  {C_PURPLE}C{RESET} Cambiar',
            f'{C_BLUE}B{RESET} Escudo  {C_GREEN}T{RESET} Recoger  {C_CYAN}F{RESET} Hablar/Tienda',
            f'{C_BLUE}U<n>{RESET} Usar  {C_GREEN}M{RESET} Minar  {C_GREEN}N{RESET} Talar',
            f'{C_GOLD}ESPACIO{RESET} Portal  {C_GOLD}J{RESET} Quests  {C_RED}X/Esc{RESET} Salir',
            f'{C_LIME}/{RESET} Escribir comando de texto',
            '',
            f'{C_LIME}MONSTRUOS{RESET}',
            f'{fg(160,140,100)}Golem{RESET}       450HP lento, drops ore',
            f'{fg(200,40,100)}Vampiro{RESET}     drena vida, debil a plata',
            f'{fg(80,60,180)}Necromancer{RESET} BOSS 350HP, invoca esq.',
            f'{fg(220,80,20)}Dragon{RESET}      BOSS 800HP, drops scale',
            '',
            f'{C_LIME}ARMAS{RESET}',
            f'{C_WHITE}Espada/Hacha{RESET}  {C_WHITE}Daga{RESET} (rapida)',
            f'{C_WHITE}Lanza{RESET} (mas alcance)  {C_WHITE}Arco corto{RESET}',
            f'{C_WHITE}Ballesta{RESET} (lenta, gran dano ranged)',
        ]

        col_right = [
            f'{C_LIME}COMANDOS  {C_DIM}(pulsa /){RESET}',
            f'{C_WHITE}look   cast <hechizo>   get   drop <n>{RESET}',
            f'{C_WHITE}equip <n>   use <n>   inv   stats{RESET}',
            f'{C_WHITE}shop   buy <n>   sell <n>{RESET}',
            f'{C_WHITE}forge   order <n>{RESET}',
            f'{C_WHITE}mine   chop   skills   map{RESET}',
            f'{C_WHITE}heal   mana   talk   quest{RESET}',
            f'{C_WHITE}save   load   help   quit{RESET}',
            '',
            f'{C_LIME}RECURSOS{RESET}',
            f'{fg(80,200,255)}*{RESET} Vena mineral  usa M (necesitas pico)',
            f'{C_GREEN}Arbol{RESET}  usa N (necesitas hacha)',
            '',
            f'{C_LIME}MINIMAPA{RESET}',
            f'{C_RED}!{RESET}=enemigo  {fg(255,50,50)}B{RESET}=BOSS',
            f'{C_GOLD}*{RESET}=item  {fg(80,200,255)}o{RESET}=vena mineral',
            '',
            f'{C_LIME}MUNDOS{RESET}',
            f'Dungeon -> Forest/Ruins/Cellar',
            f'-> Dragon Lair / Necro Crypt',
            f'{C_WHITE}Actual: {w.name}  ({w.time_name()}){RESET}',
        ]

        footer = [
            '',
            f'{C_DIM}Presiona cualquier tecla para continuar...{RESET}',
        ]

        # ── assemble line list ────────────────────────────────────────────
        if wide:
            half  = cols // 2 - 4
            lines = list(header)
            for i in range(max(len(col_left), len(col_right))):
                l = col_left[i]  if i < len(col_left)  else ''
                r = col_right[i] if i < len(col_right) else ''
                pl = vis_len(strip_ansi(l))
                pad = max(0, half - pl)
                lines.append('  ' + l + ' ' * pad + '  ' + r)
            lines += footer
        else:
            lines = header + col_left + [''] + col_right + footer

        # trim to screen height
        max_h = rows - 2
        if len(lines) > max_h:
            lines = lines[:max_h - len(footer)] + footer

        top_row = max(1, (rows - len(lines)) // 2)

        # ── render with absolute cup() — NO \n ───────────────────────────
        buf = ['\033[2J\033[?25l']   # clear + hide cursor
        for i, line in enumerate(lines):
            r  = top_row + i
            if r > rows:
                break
            # left-pad 2 spaces, clip to terminal width
            plain_w = vis_len(strip_ansi(line))
            if plain_w > cols - 3:
                # crude clip: truncate raw string (may cut mid-escape, safe fallback)
                line = strip_ansi(line)[:cols - 4] + RESET
            buf.append(move_to(r, 3))     # col 3 = 2-space left margin
            buf.append('\033[2K')         # erase line
            buf.append(line)

        sys.stdout.buffer.write(''.join(buf).encode('utf-8', errors='replace'))
        sys.stdout.buffer.flush()
