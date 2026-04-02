"""
world.py — Sistema multi-mundo.

Cada World tiene su propio mapa, enemigos, NPCs, items y objetos.
Los portales (tile P) conectan mundos entre sí.
"""

import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import random, math, copy, time
from npc import NPC_DEFS


# ── Tile types ────────────────────────────────────────────────────────────────
EMPTY    = 0
WALL     = 1
DOOR     = 2
WATER    = 3
LAVA     = 4
GRASS    = 5
WOOD_FL  = 6
PORTAL   = 7
TREE     = 8   # sólido, sprite árbol
WOOD_W   = 9
FURN     = 10  # mueble sólido (cofre, barril…)

TILE_WALL_COLORS = {
    WALL:   (130, 130, 130),
    DOOR:   (160, 100,  30),
    WATER:  ( 30,  80, 180),
    LAVA:   (220,  80,  20),
    TREE:   ( 40, 130,  30),
    WOOD_W: (140,  90,  30),
    PORTAL: (100,  30, 220),
    FURN:   (160, 110,  50),
}

TILE_FLOOR_COLORS = {
    EMPTY:   ( 50,  40,  30),
    GRASS:   ( 35,  90,  25),
    WOOD_FL: (100,  65,  25),
    WATER:   ( 10,  40, 100),
}

WALKABLE = {EMPTY, DOOR, WATER, GRASS, WOOD_FL, PORTAL, TREE}

# ── Day/night ─────────────────────────────────────────────────────────────────
DAY_DURATION = 120.0

def sky_color(phase):
    """
    Returns (top_rgb, bot_rgb, stars:bool).
    0.00-0.15  madrugada/noche final  → negro, estrellas
    0.15-0.25  amanecer               → naranja/rosa
    0.25-0.50  día pleno              → azul cielo puro
    0.50-0.62  tarde                  → azul→naranja
    0.62-0.75  puesta de sol          → rojo/violeta
    0.75-1.00  noche                  → negro, estrellas
    """
    def lp(a, b, t):
        return tuple(int(a[i] + (b[i]-a[i]) * max(0.0, min(1.0, t))) for i in range(3))

    stars = False

    if phase < 0.15:                        # noche tardía
        top = (4, 4, 12)
        bot = (8, 6, 18)
        stars = True
    elif phase < 0.25:                      # amanecer
        t   = (phase - 0.15) / 0.10
        top = lp((4, 4, 12),    (240, 120, 20), t)
        bot = lp((8, 6, 18),    (255, 190, 70), t)
    elif phase < 0.50:                      # día — azul puro
        t   = (phase - 0.25) / 0.25
        top = lp((30, 140, 255), (15, 110, 240), t)
        bot = lp((80, 190, 255), (55, 165, 255), t)
    elif phase < 0.62:                      # tarde
        t   = (phase - 0.50) / 0.12
        top = lp((15, 110, 240), (210, 80, 20),  t)
        bot = lp((55, 165, 255), (255, 160, 40), t)
    elif phase < 0.75:                      # puesta de sol
        t   = (phase - 0.62) / 0.13
        top = lp((210, 80, 20),  (50, 15, 50),   t)
        bot = lp((255, 160, 40), (110, 35, 15),  t)
    else:                                   # noche
        t   = min(1.0, (phase - 0.75) / 0.08)
        top = lp((50, 15, 50),  (4, 4, 12),  t)
        bot = lp((110, 35, 15), (8, 6, 18),  t)
        stars = True

    return top, bot, stars

def time_name(p):
    if p < 0.15:  return 'Night'
    if p < 0.25:  return 'Dawn'
    if p < 0.50:  return 'Day'
    if p < 0.62:  return 'Dusk'
    if p < 0.75:  return 'Sunset'
    return 'Night'

# ═══════════════════════════════════════════════════════════════════
#  Map definitions
# ═══════════════════════════════════════════════════════════════════
# Symbol key:
#  # stone wall   . empty floor   D door      ~ water    L lava
#  G grass        W wood floor    P portal    T tree     w wood wall
#  F furniture    N NPC spawn

WORLD_MAPS = {

'world_dungeon': {
    'name':       'Dungeon',
    'has_ceiling': True,        # ← interior: mostrar techo en vez de cielo
    'sky_override': None,
    'raw': [
        "################################",
        "#.............................P#",
        "#.###.#####.###.#####.wwwwwww.#",
        "#.#.............#.....wN....w.#",
        "#.#.###.###.###.#.###.w..F..w.#",
        "#.#.#...#.....#.#.#...w..F..wD#",
        "#...#.###.###.#.#.#.###wwwwww.#",
        "###.#.#.......#...#...........#",
        "#...#.#.#####.#####.GGGGGGGGG.#",
        "#.###.#.#...#.......GTGTGTGTG.#",
        "#.....#.#.#.#####.###GGGGGGG..#",
        "#.#####.#.#.....#.....GTGTGT..#",
        "#.......#.#####.#####.GGGGG...#",
        "#.#####.#.......#.....GGGGG..N#",
        "#.#...#.#######.#.###.........#",
        "#.#.#.#.........#.#...........#",
        "#.#.#.###########.#.###########",
        "#.#.#.............#...........#",
        "#.#.#####.#####.###P#.WWWWWWW.#",
        "#.#.......#...#.....#.WN....W.#",
        "#.#######.#.#.#######.W..P..W.#",
        "#.........#.#.........W..F..W.#",
        "#.#########.###########WWWWWWW#",
        "#.............................N#",
        "#..GGGGGGGGG..#####............#",
        "#..GTGTGTGTG..#...#...WWWWW...#",
        "#..GGGGGGGGG..#.P.#...W...W...#",
        "#..GTGTGTGTG..#N..#...W...W...#",
        "#..GGGGGGGGG..#####...WWWWW...#",
        "#......................P........#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (30, 1):  ('world_forest',      (2, 15)),
        (12, 26): ('world_ruins',        (2, 2)),
        (12, 20): ('world_cellar',       (2, 2)),
        (19, 18): ('world_necro_crypt',  (2, 21)),
        (23, 29): ('world_dragon_lair',  (2, 28)),
    },
    'enemy_spawns': [
        (5,5,'skeleton'),(18,5,'goblin'),(5,18,'slime'),
        (18,18,'orc'),(10,10,'skeleton'),(14,14,'wraith'),
        (3,14,'goblin'),(20,10,'troll'),(8,8,'bat'),
        (16,16,'spider'),(12,3,'wolf'),(12,20,'skeleton'),
        (25,25,'golem'),(6,25,'vampire'),(20,25,'vampire'),
    ],
    'npc_spawns': [
        (22, 3, 'elara'),
        (13, 23,'garrison'),
        (27, 13,'brom'),
        (5,  28,'gaunthor'),   # blacksmith in dungeon
    ],
    'furniture': [
        (22, 4, 'barrel'),
        (22, 5, 'barrel'),
        (21, 21,'chest'),
        (22, 21,'table'),
        (10, 5, 'signpost'),
        (4,  28,'forge'),      # forge next to blacksmith
        (6,  28,'anvil'),      # anvil
        (28, 13,'shop_counter'),  # shop counter near Brom
    ],
    'ore_veins': [
        (3,5,'iron'),(3,6,'iron'),(28,10,'gold'),(28,11,'gem'),(15,30,'enchanted'),
    ],
},

'world_forest': {
    'name':       'Forest',
    'sky_override': None,
    'raw': [
        "################################",
        "#..............................#",
        "#.TT...GGG..TT...GGG..TT......#",
        "#.T....GGG..T....GGG..T.....P.#",
        "#.T..T.GGG..T..T.GGG..T..T....#",
        "#......GGG.........G...........#",
        "#.TT...GGG..TT...GGG..TT.T....#",
        "#......GGG...................G.#",
        "#..TT.GGGGGGGGGGGGGGGGGGGGG....#",
        "#.....GGGGGGGGGGGGGGGGGGGGG....#",
        "#.....GGGGGG~~~~~~~~~GGGGGGG...#",
        "#.....GGGGG~~~~~~~~~~~GGGGG.N..#",
        "#.....GGGGG~~~~~~~~~~~GGGGG....#",
        "#..TT.GGGGG~~~~~~~~~GGGGGGGGG..#",
        "#.....GGGGGGGGGGGGGGGGGGGGG....#",
        "#.TT..GGGGGGGGGG.GGG..GGGGG....#",
        "#.TT..T.....TTTTT.T.T.........#",
        "#.....T.N...T.....T.T..TT.....#",
        "#..TTTT.....TTTTTTT.T..T......#",
        "#.T..........GGG....T..T.F....#",
        "#.T..TTTTTTTTTTTTTTTTT..T.....#",
        "#....T.................T.TT....#",
        "#..TTTTTTTTTTTTTTTTTTTTTT......#",
        "#..............................#",
        "#.TT....GGG..TTTTTT............#",
        "#.T.....GGG..T....T............#",
        "#.T.TT..GGG..T....T............#",
        "#.T.TT..GGG..T....T..N.........#",
        "#.T.....GGG..TTTTTT............#",
        "#.TT....GGG....................#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (30, 2): ('world_dungeon', (29, 1)),
        (30, 3): ('world_dungeon', (29, 1)),
    },
    'enemy_spawns': [
        (5,5,'wolf'),(15,5,'bat'),(25,5,'spider'),
        (5,15,'wolf'),(15,15,'bat'),(25,15,'spider'),
        (5,25,'wolf'),(15,25,'wolf'),(20,20,'bat'),
    ],
    'npc_spawns': [
        (12, 11, 'mira'),
        (17, 17, 'zephyr'),
        (27, 27, 'forest_trader'),
        (10, 20, 'sylvara'),    # elf quest NPC
        (22, 14, 'elyndra'),    # elven merchant
        (5,  26, 'theron'),     # elven smith
    ],
    'furniture': [
        (5, 19, 'well'),
        (14, 19,'signpost'),
        (26, 27,'shop_counter'),     # shop counter near trader
    ],
},

'world_ruins': {
    'name':       'Ancient Ruins',
    'sky_override': None,
    'raw': [
        "################################",
        "#..............................#",
        "#.###.....###.....###.....###..#",
        "#.#.........#.....#...........#",
        "#.#.GGGGG...#.GGG.#.GGGGG....#",
        "#...GGGGG.......G...GGGGG....#",
        "#.###GGGGG..###.G...GGGGG..###.#",
        "#....GGGGG..#...G...........#..#",
        "#.GGG~~~~~GGG.GGG.GGG~~~~~GGG.#",
        "#.GGG~~~~~GGG.GGG.GGG~~~~~GGG.#",
        "#.GGG~~~~~GGG.GGG.GGG~~~~~GGG.#",
        "#...GGG...........GGG..........#",
        "#.######..........######.......#",
        "#.#....#..GGGGGGG.#....#.......#",
        "#.#.F..#..GGGGGGG.#.F..#.N....#",
        "#.#....#..GGGGGGG.#....#.......#",
        "#.######..........######.......#",
        "#..............................#",
        "#.GGGGGGGGG.....GGGGGGGGG......#",
        "#.GGGGGGGGG..P..GGGGGGGGG......#",
        "#.GGGGGGGGG.....GGGGGGGGG......#",
        "#..............................#",
        "#.###.....###.N...###.....###..#",
        "#.#.........#.....#...........#",
        "#.#.GGGGG...#.GGG.#.GGGGG....#",
        "#...GGGGG.......G...GGGGG....#",
        "#.###GGGGG..###.G.N.GGGGG..###.#",
        "#....GGGGG..#...G...........#..#",
        "#..................................#",
        "#..............................#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (15, 19): ('world_dungeon', (12, 25)),
    },
    'enemy_spawns': [
        (5,5,'skeleton'),(25,5,'wraith'),(5,25,'skeleton'),
        (25,25,'orc'),(15,15,'wraith'),(10,10,'goblin'),
        (20,20,'troll'),(8,20,'skeleton'),(22,8,'wraith'),
    ],
    'npc_spawns': [
        (15, 14, 'garrison'),
        (15, 22, 'elara'),
        (22, 26, 'wizard'),
    ],
    'furniture': [
        (5,14,'chest'),
        (25,14,'chest'),
        (15,10,'signpost'),
    ],
},

'world_cellar': {
    'name':       'Dark Cellar',
    'has_ceiling': True,        # ← sótano: techo oscuro
    'sky_override': ((5,3,15),(8,5,20)),  # always dark
    'raw': [
        "################################",
        "#..............................#",
        "#.########.......########......#",
        "#.#......#...FFF.#......#......#",
        "#.#..FF..#...FFF.#..FF..#......#",
        "#.#......D...FFF.D......#......#",
        "#.########.......########......#",
        "#..............................#",
        "#.~~~~~.....####.....~~~~~.....#",
        "#.~~~~~.....#..#.....~~~~~.....#",
        "#.~~~~~.....#..#.....~~~~~.....#",
        "#.~~~~~.....####.....~~~~~.....#",
        "#..............................#",
        "#.########.......########......#",
        "#.#......#...FFF.#......#......#",
        "#.#..FF..D...FFF.D..FF..#.N....#",
        "#.#......#...FFF.#......#......#",
        "#.########.......########......#",
        "#..............................#",
        "#.LLLL.....WWWWWWW.....LLLL....#",
        "#.LLLL.....W.....W.....LLLL....#",
        "#.LLLL.....W..P..W.....LLLL....#",
        "#.LLLL.....W.....W.....LLLL....#",
        "#.LLLL.....WWWWWWW.....LLLL....#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (12, 21): ('world_dungeon', (12, 20)),
    },
    'enemy_spawns': [
        (5,5,'spider'),(25,5,'bat'),(5,15,'spider'),
        (25,15,'bat'),(15,10,'slime'),(15,20,'troll'),
        (8,8,'spider'),(22,22,'slime'),
    ],
    'npc_spawns': [
        (15, 15, 'brom'),
    ],
    'furniture': [
        (5,3,'barrel'),(6,3,'barrel'),(7,3,'barrel'),
        (25,3,'barrel'),(26,3,'barrel'),
        (5,14,'chest'),(25,14,'chest'),
        (3,4,'fireplace'),
    ],
},

'world_dragon_lair': {
    'name':       "Dragon's Lair",
    'has_ceiling': True,
    'sky_override': ((30,5,0),(15,2,0)),
    'raw': [
        "################################",
        "#..............................#",
        "#.LLLL.....###.....###...LLLL..#",
        "#.LLLL.....#.#.....#.#...LLLL..#",
        "#.LLLL......#.......#....LLLL..#",
        "#..........###.....###.........#",
        "#..............................#",
        "#.###.################.####....#",
        "#.#...#..............#...#.....#",
        "#.#.#.#.LLLLLLLLLLLL.#.#.#.....#",
        "#.#.#.#.L..........L.#.#.#.....#",
        "#.#.#.#.L...........L#.#.#.....#",
        "#.#.#.#.LLLLLLLLLLLL.#.#.#.....#",
        "#.#.#.#..............#.#.#.....#",
        "#.#.#.################.#.#.....#",
        "#.#.#..................#.#.....#",
        "#.#.#####################.#....#",
        "#.#......................#.#....#",
        "#.#.#####################.#....#",
        "#.#...................N...#.#....#",
        "#.#.#####################.#....#",
        "#.#......................#.#....#",
        "#.###.................###.###...#",
        "#.....LLLLLLLLLLLL.............#",
        "#.....L..N.......L.............#",
        "#.....L..........L.............#",
        "#.....LLLLLLLLLLLL.............#",
        "#..............................#",
        "#.P............................#",
        "#..............................#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (2, 28): ('world_dungeon', (25, 29)),
    },
    'enemy_spawns': [
        (15,19,'dragon'),
        (5,5,'golem'),(25,5,'golem'),
        (10,24,'vampire'),(20,24,'vampire'),
        (8,3,'bat'),(22,3,'bat'),
    ],
    'npc_spawns': [],
    'furniture': [
        (15,19,'fireplace'),
    ],
    'ore_veins': [
        (5,10,'iron'),(25,10,'iron'),(15,5,'enchanted'),
    ],
},

'world_necro_crypt': {
    'name':       'Necromancer Crypt',
    'has_ceiling': True,
    'sky_override': ((2,0,10),(5,2,20)),
    'raw': [
        "################################",
        "#..............................#",
        "#.######.######.######.######..#",
        "#.#....#.#....#.#....#.#....#..#",
        "#.#.FF.D.#.FF.D.#.FF.D.#.FF.#..#",
        "#.#....#.#....#.#....#.#....#..#",
        "#.######.######.######.######..#",
        "#..............................#",
        "#.######.######.######.######..#",
        "#.#....#.#....#.#....#.#....#..#",
        "#.#.FF.D.#.FF.D.#.FF.D.#.FF.#..#",
        "#.#....#.#....#.#....#.#....#..#",
        "#.######.######.######.######..#",
        "#..............................#",
        "#..........#########...........#",
        "#..........#.......#...........#",
        "#..........#...N...#...........#",
        "#..........#.......#...........#",
        "#..........#########...........#",
        "#..............................#",
        "#..............................#",
        "#.P............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "#..............................#",
        "################################",
    ],
    'portals': {
        (2, 21): ('world_dungeon', (18, 18)),
    },
    'enemy_spawns': [
        (15,16,'necromancer'),
        (5,5,'skeleton'),(25,5,'skeleton'),(5,12,'skeleton'),(25,12,'skeleton'),
        (10,5,'wraith'),(20,5,'wraith'),(10,12,'wraith'),(20,12,'wraith'),
        (8,8,'vampire'),(22,8,'vampire'),
    ],
    'npc_spawns': [],
    'furniture': [
        (14,15,'chest'),(16,15,'chest'),
        (15,18,'table'),
    ],
    'ore_veins': [
        (5,7,'iron'),(25,7,'iron'),
    ],
},

}

SYMBOL_TO_TILE = {
    '#': WALL,  '.': EMPTY, 'D': DOOR,
    '~': WATER, 'L': LAVA,  'G': GRASS,
    'W': WOOD_FL,'P': PORTAL,'T': TREE,
    'w': WOOD_W, 'F': FURN,  'N': EMPTY,  # N = NPC spawn point (walkable)
}

# ── Object sprite map per tile char ──────────────────────────────────────────
# maps tile coords → sprite_id (for static 3D objects)
FURN_SPRITE_CYCLE = ['chest','barrel','table','bed','bookshelf','fireplace']

# ── World class ───────────────────────────────────────────────────────────────

class World:
    def __init__(self, world_id='world_dungeon', start_time=None):
        self.world_id   = world_id
        self._start_time = start_time or time.time()
        self.tick_count  = 0

        defn = WORLD_MAPS[world_id]
        self.name = defn['name']
        self._sky_override = defn.get('sky_override')
        self.has_ceiling   = defn.get('has_ceiling', False)

        raw = defn['raw']
        self.width  = len(raw[0])
        self.height = len(raw)
        self.grid   = []
        for row in raw:
            self.grid.append([SYMBOL_TO_TILE.get(c, EMPTY) for c in row])

        self.items    = {}
        self.enemies  = []
        self.npcs     = []       # list of npc dicts with x,y
        self.objects  = {}       # (x,y) → sprite_id  (trees, furniture)
        self.ore_veins = {}      # (x,y) → {ore, charges}
        self.trees     = {}      # (x,y) → {charges} for logging

        self._portal_map = defn.get('portals', {})   # (x,y)→(world_id, (sx,sy))

        self._place_trees_and_furn(raw, defn)
        self._place_items()
        self._place_enemies(defn.get('enemy_spawns', []))
        self._place_npcs(defn.get('npc_spawns', []))
        self._place_ore_veins(defn.get('ore_veins', []))
        self._place_tree_objects(raw)

        self.revealed = [[False]*self.width for _ in range(self.height)]

        # ── Animal manager ────────────────────────────────────────────────────
        try:
            from animals import AnimalManager
            self.animal_manager = AnimalManager(world_id, self.grid, self.walkable)
        except Exception:
            self.animal_manager = None

        # ghost players injected by engine each frame
        self._ghost_players = []

    # ── time ─────────────────────────────────────────────────────────────────

    @property
    def day_phase(self):
        return ((time.time()-self._start_time) % DAY_DURATION) / DAY_DURATION

    @property
    def sky(self):
        if self._sky_override:
            # override may be old 2-tuple format — pad with no-stars
            ov = self._sky_override
            if len(ov) == 2:
                return ov[0], ov[1], False
            return ov
        return sky_color(self.day_phase)

    def time_name(self):
        return time_name(self.day_phase)

    # ── tile queries ─────────────────────────────────────────────────────────

    def tile(self, x, y):
        gx,gy = int(x),int(y)
        if 0<=gx<self.width and 0<=gy<self.height:
            return self.grid[gy][gx]
        return WALL

    def is_solid(self, x, y):
        return self.tile(x,y) not in WALKABLE

    def walkable(self, x, y):
        return self.tile(x,y) in WALKABLE

    def wall_color(self, x, y):
        t = self.tile(int(x),int(y))
        return TILE_WALL_COLORS.get(t,(130,130,130))

    def floor_color(self, x, y):
        t = self.tile(int(x),int(y))
        return TILE_FLOOR_COLORS.get(t,(50,40,30))

    def floor_tile_type(self, x, y):
        """Return tile type int so renderer can pick floor characters."""
        return self.tile(int(x), int(y))

    def portal_at(self, x, y):
        """Return (world_id, (sx,sy)) or None."""
        return self._portal_map.get((int(x),int(y)))

    # ── minimap char ─────────────────────────────────────────────────────────

    def minimap_char(self, mx, my):
        from ui import (C_GRAY, C_BLUE, C_GREEN, C_ORANGE,
                        C_RED, C_PURPLE, C_DIM, C_WHITE, RESET, fg)
        if not (0 <= my < self.height and 0 <= mx < self.width):
            return ' '
        t = self.grid[my][mx]
        if t == WALL:    return fg(160,160,160)+'█'+RESET
        if t == WOOD_W:  return C_ORANGE+'▓'+RESET
        if t == DOOR:    return C_ORANGE+'D'+RESET
        if t == WATER:   return C_BLUE+'~'+RESET
        if t == LAVA:    return C_RED+'≈'+RESET
        if t == GRASS:   return C_GREEN+','+RESET
        if t == WOOD_FL: return C_ORANGE+'.'+RESET
        if t == PORTAL:  return C_PURPLE+'P'+RESET
        if t == TREE:    return C_GREEN+'T'+RESET
        if t == FURN:    return fg(160,110,50)+'F'+RESET
        return C_DIM+'·'+RESET

    # ── placement helpers ─────────────────────────────────────────────────────

    def _place_trees_and_furn(self, raw, defn):
        """Register tree tiles and explicit furniture as sprite objects."""
        fi = 0
        for y, row in enumerate(raw):
            for x, ch in enumerate(row):
                if ch == 'T':
                    # alternate oak/pine
                    TREE_CYCLE = ['tree_oak','tree_pine','tree_dead','tree_palm','tree_snow']
                    self.objects[(x,y)] = TREE_CYCLE[(x*3 + y*7) % 5]
                elif ch == 'F':
                    sprite = FURN_SPRITE_CYCLE[fi % len(FURN_SPRITE_CYCLE)]
                    self.objects[(x,y)] = sprite
                    fi += 1
        # explicit furniture from defn
        for fx, fy, sprite_id in defn.get('furniture', []):
            self.objects[(fx,fy)] = sprite_id

    def _place_items(self):
        """
        Solo objetos muy básicos en el suelo — el equipo bueno se obtiene
        matando monstruos o forjándolo. Los minerales SOLO se obtienen minando.
        """
        base = [
            # equipo super básico (nivel 1 equivalente)
            {'id':'sword',      'name':'Rusty Sword',    'type':'weapon',     'dmg':6},
            {'id':'dagger',     'name':'Crude Dagger',   'type':'weapon',     'dmg':4,  'cooldown':0.15, 'range':1.8},
            {'id':'shortbow',   'name':'Old Short Bow',  'type':'bow',        'dmg':5},
            {'id':'spellbook',  'name':'Torn Spellbook', 'type':'spellbook',  'spells':['fireball']},
            # consumibles (estos sí se pueden encontrar)
            {'id':'potion',     'name':'Health Potion',  'type':'consumable', 'hp':30},
            {'id':'potion',     'name':'Health Potion',  'type':'consumable', 'hp':30},
            {'id':'potion',     'name':'Health Potion',  'type':'consumable', 'hp':30},
            {'id':'elixir',     'name':'Mana Elixir',    'type':'consumable', 'mp':25},
            {'id':'elixir',     'name':'Mana Elixir',    'type':'consumable', 'mp':25},
            # flechas básicas
            {'id':'arrows',     'name':'Arrow Bundle',   'type':'arrows',     'count':10},
            {'id':'arrows',     'name':'Arrow Bundle',   'type':'arrows',     'count':10},
            # oro
            {'id':'gold',       'name':'Gold Coins',     'type':'gold',       'val':20},
            {'id':'gold',       'name':'Gold Coins',     'type':'gold',       'val':15},
            {'id':'gold',       'name':'Gold Coins',     'type':'gold',       'val':30},
            # llave (para puertas / cofres)
            {'id':'key',        'name':'Iron Key',       'type':'key'},
            # pickaxe básico en el suelo para que el jugador pueda empezar a minar
            {'id':'pickaxe',    'name':'Crude Pickaxe',  'type':'tool',       'price':30},
        ]
        placed = 0
        rng = random.Random(hash(self.world_id))
        for item in base:
            for _ in range(50):
                x = rng.randint(1, self.width-2)
                y = rng.randint(1, self.height-2)
                if self.walkable(x,y) and (x,y) not in self.items:
                    self.items[(x,y)] = [item]
                    placed += 1
                    break

    def _place_enemies(self, spawns):
        templates = {
            'skeleton':    {'name':'Skeleton',    'hp':30,  'max_hp':30,  'dmg':5,  'xp':15, 'color':(200,200,180),
                            'loot_table':[('gold_coins',0.6),('health_potion',0.25),('bone_armor',0.08)]},
            'slime':       {'name':'Slime',       'hp':80,  'max_hp':80,  'dmg':5,  'xp':20, 'color':( 60,200, 60),
                            'loot_table':[('health_potion',0.5),('mana_elixir',0.3),('gold_coins',0.4)]},
            'goblin':      {'name':'Goblin',      'hp':40,  'max_hp':40,  'dmg':15, 'xp':25, 'color':(150,220, 80),
                            'loot_table':[('gold_coins',0.7),('arrows',0.4),('goblin_bow',0.10),('health_potion',0.2)]},
            'orc':         {'name':'Orc',         'hp':120, 'max_hp':120, 'dmg':25, 'xp':60, 'color':(180, 80, 40),
                            'loot_table':[('gold_coins',0.8),('orc_axe',0.15),('rusty_weapon',0.25),('health_potion',0.3)]},
            'wraith':      {'name':'Wraith',      'hp':50,  'max_hp':50,  'dmg':20, 'xp':40, 'color':(160,160,240),
                            'loot_table':[('mana_elixir',0.6),('soul_shard',0.30),('wraith_robe',0.12),('gold_coins',0.5)]},
            'troll':       {'name':'Cave Troll',  'hp':200, 'max_hp':200, 'dmg':35, 'xp':80, 'color':(100,140, 70),
                            'loot_table':[('gold_coins',0.9),('troll_club',0.15),('mega_potion',0.35),('arrows',0.5)]},
            'bat':         {'name':'Bat',         'hp':20,  'max_hp':20,  'dmg':4,  'xp':10, 'color':(120, 80,160),
                            'loot_table':[('gold_coins',0.3),('health_potion',0.15)]},
            'spider':      {'name':'Spider',      'hp':35,  'max_hp':35,  'dmg':8,  'xp':18, 'color':(160, 60, 60),
                            'loot_table':[('gold_coins',0.4),('spider_silk',0.5),('spider_silk',0.3),('spider_fang_dagger',0.08)]},
            'wolf':        {'name':'Wolf',        'hp':55,  'max_hp':55,  'dmg':12, 'xp':22, 'color':(180,160,120),
                            'loot_table':[('gold_coins',0.5),('wolf_pelt',0.6),('wolf_pelt',0.3)]},
            # ── NEW MONSTERS ──────────────────────────────────────────────────
            'golem':       {'name':'Stone Golem', 'hp':450, 'max_hp':450, 'dmg':40, 'xp':120,'color':(160,140,100),
                            'speed':0.06,   # very slow
                            'loot_table':[('gold_coins',1.0),('golem_core',0.5),('iron_ore_loot',0.7),('strength_potion',0.4)]},
            'vampire':     {'name':'Vampire',     'hp':90,  'max_hp':90,  'dmg':18, 'xp':70, 'color':(200, 40,100),
                            'drain':True,   # life steal
                            'loot_table':[('gold_coins',0.8),('blood_vial',0.7),('blood_vial',0.4),('shadow_cloak',0.20),('mana_elixir',0.5)]},
            'necromancer': {'name':'Necromancer', 'hp':350, 'max_hp':350, 'dmg':30, 'xp':300,'color':( 80, 60,180),
                            'boss':True, 'summons':True,
                            'loot_table':[('gold_coins',1.0),('staff_of_death',0.6),('tome_of_shadows',0.5),('soul_shard',1.0),('soul_shard',0.8),('mega_potion',1.0)]},
            'dragon':      {'name':'Dragon',      'hp':800, 'max_hp':800, 'dmg':60, 'xp':500,'color':(220, 80, 20),
                            'boss':True, 'aoe':True,
                            'loot_table':[('gold_coins',1.0),('gold_coins',1.0),('dragon_scale',1.0),('dragon_scale',0.8),('dragonfire_gem',0.8),('dragon_heart',0.6)]},
        }
        for i,(sx,sy,eid) in enumerate(spawns):
            if self.walkable(sx,sy) and eid in templates:
                e = copy.deepcopy(templates[eid])
                e['id']        = eid
                e['x']         = sx+0.5
                e['y']         = sy+0.5
                e['alive']     = True
                e['tick']      = i % 5
                e['attacking'] = False
                self.enemies.append(e)

    def drop_loot(self, enemy):
        """
        Generate loot items from a dead enemy's loot_table.
        Equipment (armor, weapons) ONLY drops from monsters — never on the floor.
        Minerals NEVER drop from monsters — only from mining.
        Returns list of items.
        """
        LOOT_ITEMS = {
            # ── Oro ──────────────────────────────────────────────────────────
            'gold_coins':      {'id':'gold',           'name':'Gold Coins',        'type':'gold',       'val':random.randint(10,60)},
            # ── Consumibles ──────────────────────────────────────────────────
            'arrows':          {'id':'arrows',          'name':'Arrow Bundle',      'type':'arrows',     'count':12},
            'health_potion':   {'id':'potion',          'name':'Health Potion',     'type':'consumable', 'hp':30},
            'mega_potion':     {'id':'potion_big',      'name':'Mega Potion',       'type':'consumable', 'hp':60},
            'mana_elixir':     {'id':'elixir',          'name':'Mana Elixir',       'type':'consumable', 'mp':25},
            'strength_potion': {'id':'pot_str',         'name':'Strength Potion',   'type':'consumable', 'buff':'strength'},
            'haste_potion':    {'id':'pot_haste',       'name':'Haste Potion',      'type':'consumable', 'buff':'haste'},
            'blood_vial':      {'id':'blood_vial',      'name':'Blood Vial',        'type':'consumable', 'hp':20, 'mp':15},
            'dragon_heart':    {'id':'dragon_heart',    'name':'Dragon Heart',      'type':'consumable', 'hp':200,'buff':'strength'},
            # ── Materiales (drop de monstruos, NO minerales) ─────────────────
            'wolf_pelt':       {'id':'wolf_pelt',       'name':'Wolf Pelt',         'type':'material',   'mat':'pelt',       'price':20},
            'spider_silk':     {'id':'spider_silk',     'name':'Spider Silk',       'type':'material',   'mat':'silk',       'price':18},
            'soul_shard':      {'id':'soul_shard',      'name':'Soul Shard',        'type':'material',   'mat':'soul',       'price':50},
            'golem_core':      {'id':'golem_core',      'name':'Golem Core',        'type':'material',   'mat':'golem',      'price':120},
            'dragon_scale':    {'id':'dragon_scale',    'name':'Dragon Scale',      'type':'material',   'mat':'dragon',     'price':200},
            'dragonfire_gem':  {'id':'dragonfire_gem',  'name':'Dragonfire Gem',    'type':'material',   'mat':'dragonfire', 'price':300},
            # Excepción: loot de golem puede dar hierro (como si sus partes fueran hierro)
            'iron_ore_loot':   {'id':'mineral_iron',    'name':'Iron Fragments',    'type':'material',   'mat':'iron',       'price':12},
            # ── Equipo (SOLO de monstruos) ────────────────────────────────────
            'rusty_weapon':    {'id':'sword',           'name':'Rusty Sword',       'type':'weapon',     'dmg':8,            'price':15},
            'orc_axe':         {'id':'axe',             'name':'Orc Battle Axe',    'type':'weapon',     'dmg':22,           'price':80},
            'troll_club':      {'id':'mace',            'name':'Troll Club',        'type':'weapon',     'dmg':28, 'cooldown':0.6, 'price':90},
            'shadow_cloak':    {'id':'shadow_cloak',    'name':'Shadow Cloak',      'type':'armor',      'def':12, 'block':0.20, 'magic_bonus':8,  'price':180},
            'wraith_robe':     {'id':'wraith_robe',     'name':'Wraith Robe',       'type':'armor',      'def':7,  'magic_bonus':12,                 'price':140},
            'bone_armor':      {'id':'bone_armor',      'name':'Bone Armor',        'type':'armor',      'def':9,  'block':0.15,                     'price':80},
            'goblin_bow':      {'id':'shortbow',        'name':'Goblin Shortbow',   'type':'bow',        'dmg':10,           'price':55},
            'staff_of_death':  {'id':'staff_of_death',  'name':'Staff of Death',    'type':'weapon',     'dmg':35, 'magic_bonus':20, 'price':250},
            'tome_of_shadows': {'id':'tome_of_shadows', 'name':'Tome of Shadows',   'type':'spellbook',  'magic_bonus':15,   'price':200},
            'spider_fang_dagger':{'id':'dagger',        'name':'Spider Fang Dagger','type':'weapon',     'dmg':11, 'cooldown':0.11, 'range':2.0, 'price':70},
        }
        drops = []
        loot_table = enemy.get('loot_table', [])
        for item_id, chance in loot_table:
            if random.random() < chance and item_id in LOOT_ITEMS:
                item = copy.deepcopy(LOOT_ITEMS[item_id])
                # re-roll gold value each time so it varies
                if item['type'] == 'gold':
                    item['val'] = random.randint(10, 60)
                drops.append(item)
        return drops

    def _place_npcs(self, spawns):
        for sx, sy, npc_id in spawns:
            if npc_id in NPC_DEFS:
                n = copy.deepcopy(NPC_DEFS[npc_id])
                n['x'] = sx+0.5
                n['y'] = sy+0.5
                self.npcs.append(n)

    def _place_ore_veins(self, vein_list):
        """Place explicit ore veins from world definition, plus random ones."""
        for vx, vy, ore_type in vein_list:
            self.ore_veins[(vx,vy)] = {'ore': ore_type, 'charges': random.randint(2,5)}
        # also scatter random ore veins in wall-adjacent cells
        rng = random.Random(hash(self.world_id) ^ 0xABCD)
        ore_types = ['iron','iron','iron','iron','gold','gold','gem','enchanted']
        for _ in range(8):
            for attempt in range(30):
                x = rng.randint(1, self.width-2)
                y = rng.randint(1, self.height-2)
                if not self.walkable(x,y): continue
                # must have at least one wall neighbor
                has_wall = any(not self.walkable(x+dx,y+dy) for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)])
                if has_wall and (x,y) not in self.ore_veins:
                    ore = rng.choice(ore_types)
                    self.ore_veins[(x,y)] = {'ore': ore, 'charges': rng.randint(2,4)}
                    break

    def _place_tree_objects(self, raw):
        """Register trees for logging."""
        for y, row in enumerate(raw):
            for x, ch in enumerate(row):
                if ch == 'T':
                    self.trees[(x,y)] = {'charges': random.randint(2,4), 'sprite': 'tree_oak'}

    def chop_tree(self, px, py, player):
        """Chop adjacent tree. Returns (item, msg)."""
        has_axe = any('axe' in it.get('name','').lower() or it.get('id','') == 'axe'
                      for it in player.inventory) or \
                  ('axe' in (player.equipped.get('weapon') or {}).get('name','').lower())
        if not has_axe:
            return None, "Necesitas un hacha para talar. Busca una en el mundo."
        for dy in range(-1,2):
            for dx in range(-1,2):
                tx,ty = int(px)+dx, int(py)+dy
                tree  = self.trees.get((tx,ty))
                if tree and tree['charges'] > 0:
                    tree['charges'] -= 1
                    wood_item = {'id':'wood','name':'Wood Log','type':'material','mat':'wood','price':8}
                    exhausted = tree['charges'] <= 0
                    if exhausted:
                        # remove tree tile so it becomes walkable
                        if 0<=tx<self.width and 0<=ty<self.height:
                            self.grid[ty][tx] = EMPTY
                        del self.trees[(tx,ty)]
                        if (tx,ty) in self.objects:
                            del self.objects[(tx,ty)]
                    return wood_item, f"🪓 Talado: Wood Log" + (" (árbol derribado)" if exhausted else f" ({tree['charges']} restantes)")
        return None, "No hay árboles adyacentes para talar."

    def reveal_around(self, px, py, radius=6):
        cx,cy = int(px),int(py)
        for dy in range(-radius,radius+1):
            for dx in range(-radius,radius+1):
                nx,ny = cx+dx,cy+dy
                if 0<=nx<self.width and 0<=ny<self.height:
                    if math.hypot(dx,dy)<=radius:
                        self.revealed[ny][nx]=True

    # ── enemy AI  (SLOWER: tick every 5 instead of 4, interval longer) ────────

    def tick_enemies(self, player):
        self.tick_count += 1
        for e in self.enemies:
            if not e['alive']:
                continue
            e['tick'] = (e['tick']+1) % 6
            if e['tick'] != 0:
                continue
            dx   = player.x-e['x']
            dy   = player.y-e['y']
            dist = math.hypot(dx,dy)
            e['attacking'] = dist < 1.1
            if dist < 8 and dist > 0.8:
                # bosses and golems move slower
                spd = e.get('speed', 0.12)
                nx  = e['x']+(dx/dist)*spd
                ny  = e['y']+(dy/dist)*spd
                if self.walkable(nx,e['y']): e['x']=nx
                if self.walkable(e['x'],ny): e['y']=ny
            # vampire life drain on contact
            if e.get('drain') and dist < 1.0 and player.alive:
                drain_hp = max(1, e['dmg'] // 4)
                player.hp = max(0, player.hp - drain_hp)
                e['hp']   = min(e['max_hp'], e['hp'] + drain_hp)
                if player.hp <= 0:
                    player.alive = False

    # ── ore vein mining ──────────────────────────────────────────────────────

    def mine_vein(self, px, py, player):
        """
        Try to mine an ore vein adjacent to the player.
        Returns list of (item, msg) tuples for mined ore.
        Requires a pickaxe in inventory or equipped.
        """
        has_pick = any(it.get('id') == 'pickaxe' for it in player.inventory)
        if not has_pick:
            return None, "No tienes un pico. Fabrica uno con el herrero."

        # find adjacent vein
        for dy in range(-1,2):
            for dx in range(-1,2):
                vx,vy = int(px)+dx, int(py)+dy
                vein  = self.ore_veins.get((vx,vy))
                if vein and vein['charges'] > 0:
                    vein['charges'] -= 1
                    ore_type = vein['ore']
                    # build ore item
                    ORE_ITEMS = {
                        'iron':      {'id':'mineral_iron',     'name':'Iron Ore',       'type':'material','mat':'iron',     'price':15},
                        'gold':      {'id':'mineral_gold',     'name':'Gold Ore',        'type':'material','mat':'gold',    'price':35},
                        'gem':       {'id':'mineral_gem',      'name':'Gemstone',        'type':'material','mat':'gem',     'price':60},
                        'enchanted': {'id':'mineral_enchanted','name':'Enchanted Ore',   'type':'material','mat':'enchanted','price':80},
                        'dragon':    {'id':'mineral_dragon',   'name':'Dragonite Ore',   'type':'material','mat':'dragonfire','price':200},
                    }
                    item = dict(ORE_ITEMS.get(ore_type, ORE_ITEMS['iron']))
                    exhausted = vein['charges'] <= 0
                    return item, f"⛏ Extraído: {item['name']}" + (" (vena agotada)" if exhausted else f" ({vein['charges']} restantes)")
        return None, "No hay venas de mineral adyacentes."

    def enemy_at(self, x, y, radius=0.8):
        for e in self.enemies:
            if e['alive'] and math.hypot(e['x']-x,e['y']-y)<radius:
                return e
        return None

    def npc_nearby(self, x, y, radius=1.5):
        for n in self.npcs:
            if math.hypot(n['x']-x,n['y']-y)<radius:
                return n
        return None

    def item_at(self, x, y):
        key = (int(x),int(y))
        items = self.items.get(key,[])
        return items[0] if items else None

    def remove_item(self, x, y, item):
        key = (int(x),int(y))
        if key in self.items and item in self.items[key]:
            self.items[key].remove(item)
            if not self.items[key]:
                del self.items[key]


# ── WorldManager: holds all loaded worlds ────────────────────────────────────

class WorldManager:
    def __init__(self):
        self._worlds    = {}
        self._start_time = time.time()
        self.current_id  = 'world_dungeon'
        self._load('world_dungeon')

    def _load(self, world_id):
        if world_id not in self._worlds:
            self._worlds[world_id] = World(world_id, self._start_time)
        return self._worlds[world_id]

    @property
    def current(self):
        return self._worlds[self.current_id]

    def travel(self, world_id, spawn_pos):
        """Switch active world, load if needed."""
        self._load(world_id)
        self.current_id = world_id
        return self._worlds[world_id], spawn_pos
