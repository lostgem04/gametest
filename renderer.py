"""
renderer.py — Raycasting 3D.

Cambios:
 - Los árboles NO forman paredes 3D (tile TREE es no-sólido para el rayo,
   el sprite ASCII se muestra como objeto)
 - Cielo: día=azul puro, tarde=naranja, noche=negro con estrellas '*'
 - Suelo: caracteres ricos según tile (agua=~~~, pasto=;;;, madera=:::, etc.)
 - Sin barras de HP ni etiquetas sobre sprites
"""

import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, random
from world import WATER, GRASS, WOOD_FL, LAVA, EMPTY, PORTAL
from sprites import get_frame, NPC_SPRITES, OBJECT_SPRITES

RESET = '\033[0m'

def _rgb(r, g, b):
    return f'\033[38;2;{int(max(0,min(255,r)))};{int(max(0,min(255,g)))};{int(max(0,min(255,b)))}m'

def _mv(row, col):
    return f'\033[{row};{col}H'

def _lp(a, b, t):
    t = max(0.0, min(1.0, t))
    return (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t, a[2]+(b[2]-a[2])*t)

SHADES = [' ', '.', ':', '░', '▒', '▓', '█']

# floor character sets per tile type
FLOOR_CHARS = {
    WATER:   ['~', '~', '~', '≈', '~', '~', '≋'],
    GRASS:   [';', ';', ',', ';', '\'', ';', ','],
    WOOD_FL: [':', '.', ':', '·', ':', '.', ':'],
    LAVA:    ['≈', '~', '≋', '≈', '~', '≈', '~'],
    PORTAL:  ['*', '·', '*', ':', '·', '*', ':'],
    EMPTY:   [':', '.', '·', ':', ' ', '·', '.'],
}
# default for unknown types
FLOOR_CHARS_DEFAULT = [':', '.', '·', ' ', ':', '·', ' ']

# sky char sets
SKY_CHARS_DAY   = [':', ':', ':', ':', ':', ':', ':', ':', ':', ':', ':']
SKY_CHARS_DUSK  = [':', ':', '.', ':', ':', ':', ':', ':', '.', ':', ':']
SKY_STAR_CHARS  = ['*', '·', '✦', '·', '*', ' ', '·', '*', ' ', '✦', ' ', '·']

# Techo interior (dungeon, sótano, etc.) — gris pétreo
CEILING_CHARS   = ['▓', '░', '▒', '░', '▓', '░', '▒', '▒', '░', '▓', '░', '▒']
CEILING_COLOR   = (70, 65, 60)   # gris oscuro piedra


class Renderer:
    def __init__(self, term_cols, term_rows):
        self._tick = 0
        self._star_seed = 42   # stable star pattern
        self.resize(term_cols, term_rows)

    def resize(self, term_cols, term_rows):
        self.vw        = max(40, int(term_cols * 0.58))
        self.vh        = max(16, term_rows - 3)
        self.fov       = math.pi / 3.0
        self.max_depth = 20.0

    # ── main render ──────────────────────────────────────────────────────────

    def render_frame(self, player, world):
        self._tick += 1
        vw, vh = self.vw, self.vh
        vc     = vh / 2.0
        sky_top, sky_bot, stars = world.sky

        # pre-compute stable star map for this frame (hash-based, no random)
        star_set = self._star_map(vw, int(vc))

        # raycasting — build z-buffer
        z_buf = []
        for col in range(vw):
            angle = (player.angle - self.fov/2) + (col/vw) * self.fov
            dist, tx, ty, side = self._cast_ray(player, world, angle)
            z_buf.append((dist, tx, ty, side))

        # build floor tile lookup by screen column (cast floor ray)
        # we sample the floor tile at player position for simplicity —
        # a full floor-cast would be expensive; player tile gives the right
        # colour for the area the player is standing in.

        # pixel rows
        rows = []
        for row in range(vh):
            parts = []
            for col in range(vw):
                dist, tx, ty, side = z_buf[col]

                # ── wall ──────────────────────────────────────────────────
                if dist < self.max_depth:
                    wh = int(vh / (dist + 1e-5))
                    wt = int(vc - wh/2)
                    wb = int(vc + wh/2)
                    if wt <= row <= wb:
                        ch, color = self._wall_px(dist, tx, ty, world, side)
                        parts.append(_rgb(*color) + ch + RESET)
                        continue

                # ── sky / ceiling ──────────────────────────────────────────
                if row < vc:
                    # ── TECHO interior (dungeon, sótano…) ─────────────────
                    if getattr(world, 'has_ceiling', False):
                        shade = 0.5 + 0.5 * (row / max(vc, 1))   # más oscuro arriba
                        cr = int(CEILING_COLOR[0] * shade)
                        cg = int(CEILING_COLOR[1] * shade)
                        cb = int(CEILING_COLOR[2] * shade)
                        ch = CEILING_CHARS[(row * 5 + col * 3) % len(CEILING_CHARS)]
                        parts.append(_rgb(cr, cg, cb) + ch + RESET)
                    else:
                        t  = row / max(vc, 1)
                        cr, cg, cb = _lp(sky_top, sky_bot, t)

                        if stars:
                            # twinkle: stars shift slightly each tick
                            star_key = (row * 1000 + col + self._tick // 8) % 997
                            if (row, col) in star_set:
                                # star brightness flickers
                                flicker = 180 + (self._tick * 37 + col * 13) % 75
                                ch = SKY_STAR_CHARS[(row * 7 + col * 3) % len(SKY_STAR_CHARS)]
                                if ch == ' ':
                                    ch = '·'
                                parts.append(_rgb(flicker, flicker, flicker) + ch + RESET)
                            else:
                                # dark sky — very subtle texture
                                ch = '.' if (row + col * 3) % 23 == 0 else ' '
                                parts.append(_rgb(int(cr*0.6), int(cg*0.6), int(cb*0.6)) + ch + RESET)
                        else:
                            # day / dusk sky chars
                            if sky_top[2] > 150:   # day (blue dominant)
                                ch = SKY_CHARS_DAY[(row + col * 2) % len(SKY_CHARS_DAY)]
                            else:                   # dusk
                                ch = SKY_CHARS_DUSK[(row + col) % len(SKY_CHARS_DUSK)]
                            parts.append(_rgb(int(cr), int(cg), int(cb)) + ch + RESET)

                # ── floor ──────────────────────────────────────────────────
                else:
                    ft = (row - vc) / (vh - vc + 1e-5)
                    fc = world.floor_color(player.x, player.y)
                    tile_t = world.floor_tile_type(player.x, player.y)

                    # distance darkening
                    shade = 1.0 - ft * 0.70
                    r_ = int(fc[0] * shade)
                    g_ = int(fc[1] * shade)
                    b_ = int(fc[2] * shade)

                    # pick floor char from tile set
                    char_pool = FLOOR_CHARS.get(tile_t, FLOOR_CHARS_DEFAULT)
                    fx = int(player.x * 3) + col
                    fy = int(player.y * 3) + row
                    ch = char_pool[(fx * 3 + fy * 7) % len(char_pool)]

                    parts.append(_rgb(r_, g_, b_) + ch + RESET)

            rows.append(''.join(parts))

        sprite_buf = self._build_sprite_buf(player, world, z_buf)
        return rows, sprite_buf

    # ── star map ──────────────────────────────────────────────────────────────

    def _star_map(self, vw, sky_h):
        """Generate a stable set of (row,col) star positions."""
        stars = set()
        rng   = self._star_seed
        count = max(10, (vw * sky_h) // 30)
        for i in range(count):
            rng = (rng * 1664525 + 1013904223) & 0xFFFFFFFF
            r   = rng % max(1, sky_h - 1)
            rng = (rng * 1664525 + 1013904223) & 0xFFFFFFFF
            c   = rng % vw
            stars.add((r, c))
        return stars

    # ── DDA raycasting ───────────────────────────────────────────────────────

    def _cast_ray(self, player, world, angle):
        from world import TREE   # trees are non-solid for ray (show as sprite)
        cos_a = math.cos(angle) or 1e-10
        sin_a = math.sin(angle) or 1e-10
        mx, my = int(player.x), int(player.y)
        ddx, ddy = abs(1/cos_a), abs(1/sin_a)
        sx = 1 if cos_a > 0 else -1
        sy = 1 if sin_a > 0 else -1
        sdx = (mx + (1 if cos_a > 0 else 0) - player.x) * ddx
        sdy = (my + (1 if sin_a > 0 else 0) - player.y) * ddy
        side = 0
        for _ in range(int(self.max_depth * 4)):
            if sdx < sdy:
                sdx += ddx; mx += sx; side = 0
            else:
                sdy += ddy; my += sy; side = 1
            t = world.tile(mx, my)
            # trees are transparent to rays — skip them
            if world.is_solid(mx, my) and t != TREE:
                break
        else:
            return self.max_depth, 0, 0, 0
        dist = abs((mx - player.x + (1-sx)/2) / cos_a if side == 0
                   else (my - player.y + (1-sy)/2) / sin_a)
        return dist, mx, my, side

    def _wall_px(self, dist, tx, ty, world, side):
        br, bg_, bb = world.wall_color(tx, ty)
        depth = (1.0 - min(dist / self.max_depth, 1.0)) ** 1.2
        vol   = 0.72 if side == 1 else 1.0
        shade = depth * vol
        idx   = min(int(depth * (len(SHADES)-1)), len(SHADES)-1)
        return SHADES[idx], (int(br*shade), int(bg_*shade), int(bb*shade))

    # ── sprite buffer ─────────────────────────────────────────────────────────

    def _build_sprite_buf(self, player, world, z_buf):
        """
        Sprites for enemies, NPCs, static objects, and floor items.
        All sprites rendered in WHITE (brightness scaled by distance).
        Trees render as sprites (not walls).
        """
        from sprites import get_floor_sprite
        vw, vh = self.vw, self.vh
        vc     = vh // 2
        buf    = []

        drawables = []  # (dist, screen_x, sprite_id, color, kind, extra)

        # ── floor items ───────────────────────────────────────────────────────
        for (ix, iy), item_list in world.items.items():
            if not item_list:
                continue
            item = item_list[0]
            dist, scx = self._project(player, ix + 0.5, iy + 0.5)
            if dist is None or dist > 10:
                continue
            drawables.append((dist, scx, '__floor_item__', (255, 255, 200), 'floor_item', item))

        # enemies
        for e in world.enemies:
            if not e['alive']:
                continue
            dist, scx = self._project(player, e['x'], e['y'])
            if dist is None:
                continue
            drawables.append((dist, scx, e['id'], e['color'], 'enemy', e))

        # NPCs
        for n in world.npcs:
            dist, scx = self._project(player, n['x'], n['y'])
            if dist is None:
                continue
            color = n.get('color', (200, 180, 140))
            drawables.append((dist, scx, n['sprite_id'], color, 'npc', n))

        # ── Animals ───────────────────────────────────────────────────────────
        animal_mgr = getattr(world, 'animal_manager', None)
        if animal_mgr:
            for a in animal_mgr.animals:
                if not a.get('alive', True):
                    continue
                dist, scx = self._project(player, a['x'], a['y'])
                if dist is None:
                    continue
                drawables.append((dist, scx, 'npc_villager', a['color'], 'animal', a))

        # ── Ghost players (multiplayer) ────────────────────────────────────────
        for g in getattr(world, '_ghost_players', []):
            if not g.alive:
                continue
            dist, scx = self._project(player, g.x, g.y)
            if dist is None:
                continue
            drawables.append((dist, scx, 'npc_villager', g.color, 'ghost', g))

        # static objects (trees + furniture)
        px, py = player.x, player.y
        static_count = 0
        for (ox, oy), sprite_id in world.objects.items():
            if static_count >= 40:
                break
            if abs(ox-px) > 16 or abs(oy-py) > 16:
                continue
            dist, scx = self._project(player, ox+0.5, oy+0.5)
            if dist is None or dist > 14:
                continue
            static_count += 1

            # color by sprite type
            if 'tree_oak' == sprite_id:
                color = (40, 130, 30)
            elif 'tree_pine' == sprite_id:
                color = (30, 110, 25)
            elif 'tree_dead' == sprite_id:
                color = (90, 70, 40)
            elif 'tree_palm' == sprite_id:
                color = (50, 160, 30)
            elif 'tree_snow' == sprite_id:
                color = (200, 220, 255)
            elif sprite_id in ('chest', 'barrel', 'table', 'bed', 'bookshelf'):
                color = (160, 110, 50)
            elif sprite_id == 'fireplace':
                color = (220, 100, 20)
            elif sprite_id == 'forge':
                color = (210, 80, 20)
            elif sprite_id == 'anvil':
                color = (130, 130, 140)
            elif sprite_id == 'well':
                color = (100, 130, 160)
            elif sprite_id == 'shop_counter':
                color = (180, 150, 60)
            else:
                color = (160, 140, 100)

            drawables.append((dist, scx, sprite_id, color, 'static', None))

        # sort far → near
        drawables.sort(key=lambda d: -d[0])

        for dist, screen_x, sprite_id, color, kind, extra in drawables:
            if kind == 'floor_item':
                frame = get_floor_sprite(extra)
            elif kind == 'static':
                frame = get_frame(sprite_id, dist)
            elif kind == 'enemy':
                frame = get_frame(sprite_id, dist, extra.get('attacking', False), self._tick)
            else:
                frame = get_frame(sprite_id, dist)

            if not frame:
                continue

            n_lines = len(frame)
            art_w   = max(len(line) for line in frame)
            wall_h  = int(vh / (dist + 1e-5))
            top     = vc - wall_h // 2
            v_off   = max(0, (wall_h - n_lines) // 2)
            left    = screen_x - art_w // 2

            # ── ALL sprites in white, brightness fades with distance ──────────
            depth_f  = (1.0 - min(dist / self.max_depth, 1.0)) ** 0.9
            # floor items get a warm-yellow tint; everything else pure white
            if kind == 'floor_item':
                base = (255, 255, 180)
            else:
                base = (255, 255, 255)
            cr = int(base[0] * depth_f)
            cg = int(base[1] * depth_f)
            cb = int(base[2] * depth_f)
            col_code = _rgb(cr, cg, cb)

            # floor items sit at the bottom of the sprite volume
            if kind == 'floor_item':
                top = vc + wall_h // 4

            for li, art_line in enumerate(frame):
                term_row = top + v_off + li + 1
                if not (1 <= term_row <= vh):
                    continue
                for ci, ch in enumerate(art_line):
                    if ch == ' ':
                        continue
                    col_pos = left + ci
                    if not (0 < col_pos <= vw):
                        continue
                    zidx = col_pos - 1
                    if 0 <= zidx < len(z_buf) and z_buf[zidx][0] < dist:
                        continue
                    buf.append(_mv(term_row, col_pos))
                    buf.append(col_code + ch + RESET)

        return buf

    def _project(self, player, sx, sy):
        vw   = self.vw
        dx   = sx - player.x
        dy   = sy - player.y
        dist = math.hypot(dx, dy)
        if dist < 0.3 or dist > self.max_depth:
            return None, None
        angle_to   = math.atan2(dy, dx)
        angle_diff = (angle_to - player.angle + math.pi) % (2*math.pi) - math.pi
        if abs(angle_diff) > self.fov/2 + 0.2:
            return None, None
        screen_x = int((vw/2) * (1 + angle_diff / (self.fov/2)))
        return dist, screen_x
