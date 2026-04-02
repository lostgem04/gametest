"""
animals.py — Animales NPC para Arcane Abyss.

Los animales son entidades no-hostiles (por defecto) que pueblan
el mundo. Se mueven aleatoriamente, huyen del jugador si se acercan,
y algunos pueden ser cazados para obtener materiales.

Tipos de comportamiento:
  'passive'  — huye del jugador si está cerca
  'neutral'  — ignora al jugador a menos que lo ataquen
  'timid'    — permanece quieto, huye rápidamente al detectar al jugador
"""


import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, random, time

# ── Definiciones de animales ──────────────────────────────────────────────────

ANIMAL_DEFS = {
    'rabbit': {
        'id':        'rabbit',
        'name':      'Conejo',
        'hp':        8,
        'max_hp':    8,
        'dmg':       0,
        'xp':        5,
        'speed':     0.18,
        'behavior':  'timid',
        'flee_dist': 4.0,
        'color':     (230, 220, 200),
        'loot_table': [
            ('rabbit_pelt', 0.80),
            ('rabbit_meat', 0.60),
        ],
        'desc': 'Un pequeño conejo. Inofensivo pero rápido.',
    },
    'deer': {
        'id':        'deer',
        'name':      'Ciervo',
        'hp':        25,
        'max_hp':    25,
        'dmg':       2,
        'xp':        15,
        'speed':     0.16,
        'behavior':  'passive',
        'flee_dist': 5.0,
        'color':     (180, 130, 70),
        'loot_table': [
            ('deer_pelt', 0.75),
            ('venison',   0.70),
            ('antler',    0.30),
        ],
        'desc': 'Un ciervo grácil. Huye al detectar peligro.',
    },
    'fox': {
        'id':        'fox',
        'name':      'Zorro',
        'hp':        20,
        'max_hp':    20,
        'dmg':       4,
        'xp':        12,
        'speed':     0.17,
        'behavior':  'neutral',
        'flee_dist': 3.0,
        'color':     (220, 110, 30),
        'loot_table': [
            ('fox_pelt', 0.70),
        ],
        'desc': 'Un zorro astuto. Puede morder si se siente acorralado.',
    },
    'boar': {
        'id':        'boar',
        'name':      'Jabalí',
        'hp':        45,
        'max_hp':    45,
        'dmg':       8,
        'xp':        25,
        'speed':     0.13,
        'behavior':  'neutral',
        'flee_dist': 1.5,
        'color':     (120, 80, 50),
        'loot_table': [
            ('boar_pelt',  0.80),
            ('boar_tusk',  0.40),
            ('boar_meat',  0.70),
        ],
        'desc': 'Un jabalí robusto. Cargará si se acerca demasiado.',
    },
    'crow': {
        'id':        'crow',
        'name':      'Cuervo',
        'hp':        6,
        'max_hp':    6,
        'dmg':       1,
        'xp':        4,
        'speed':     0.20,
        'behavior':  'timid',
        'flee_dist': 3.5,
        'color':     (60, 60, 70),
        'loot_table': [
            ('feather', 0.90),
        ],
        'desc': 'Un cuervo negro. Presagio de lo que viene.',
    },
    'snake': {
        'id':        'snake',
        'name':      'Serpiente',
        'hp':        15,
        'max_hp':    15,
        'dmg':       6,
        'xp':        18,
        'speed':     0.10,
        'behavior':  'neutral',
        'flee_dist': 1.0,
        'color':     (60, 140, 40),
        'loot_table': [
            ('snake_skin',   0.75),
            ('snake_venom',  0.35),
        ],
        'desc': 'Una serpiente venenosa. No la toques.',
    },
    'horse': {
        'id':        'horse',
        'name':      'Caballo',
        'hp':        60,
        'max_hp':    60,
        'dmg':       5,
        'xp':        20,
        'speed':     0.22,
        'behavior':  'passive',
        'flee_dist': 4.0,
        'color':     (150, 100, 50),
        'loot_table': [
            ('horsehair', 0.60),
        ],
        'desc': 'Un caballo salvaje. Majestuoso e inalcanzable.',
    },
    'cat': {
        'id':        'cat',
        'name':      'Gato',
        'hp':        12,
        'max_hp':    12,
        'dmg':       2,
        'xp':        6,
        'speed':     0.19,
        'behavior':  'timid',
        'flee_dist': 3.0,
        'color':     (210, 190, 150),
        'loot_table': [],
        'desc': 'Un gato doméstico. No te sirve de nada atacarlo.',
    },
    'bear': {
        'id':        'bear',
        'name':      'Oso',
        'hp':        90,
        'max_hp':    90,
        'dmg':       14,
        'xp':        45,
        'speed':     0.11,
        'behavior':  'neutral',
        'flee_dist': 0.5,
        'color':     (100, 70, 30),
        'loot_table': [
            ('bear_pelt', 0.85),
            ('bear_claw', 0.50),
            ('bear_meat', 0.65),
        ],
        'desc': 'Un oso enorme. Extremadamente peligroso si se enfada.',
    },
    'parrot': {
        'id':        'parrot',
        'name':      'Loro',
        'hp':        8,
        'max_hp':    8,
        'dmg':       1,
        'xp':        5,
        'speed':     0.21,
        'behavior':  'timid',
        'flee_dist': 3.0,
        'color':     (40, 200, 80),
        'loot_table': [
            ('feather', 0.95),
        ],
        'desc': 'Un loro colorido. Se puede escuchar a lo lejos.',
    },
}

# Materiales de loot de animales
ANIMAL_LOOT_ITEMS = {
    'rabbit_pelt': {'id':'rabbit_pelt',  'name':'Piel de Conejo',    'type':'material','mat':'pelt',   'price':8},
    'rabbit_meat': {'id':'rabbit_meat',  'name':'Carne de Conejo',   'type':'consumable','hp':12,      'price':5},
    'deer_pelt':   {'id':'deer_pelt',    'name':'Piel de Ciervo',    'type':'material','mat':'pelt',   'price':18},
    'venison':     {'id':'venison',      'name':'Venado',            'type':'consumable','hp':20,      'price':10},
    'antler':      {'id':'antler',       'name':'Asta de Ciervo',    'type':'material','mat':'antler', 'price':25},
    'fox_pelt':    {'id':'fox_pelt',     'name':'Piel de Zorro',     'type':'material','mat':'pelt',   'price':22},
    'boar_pelt':   {'id':'boar_pelt',    'name':'Piel de Jabalí',    'type':'material','mat':'pelt',   'price':20},
    'boar_tusk':   {'id':'boar_tusk',    'name':'Colmillo de Jabalí','type':'material','mat':'bone',   'price':30},
    'boar_meat':   {'id':'boar_meat',    'name':'Carne de Jabalí',   'type':'consumable','hp':25,      'price':12},
    'feather':     {'id':'feather',      'name':'Pluma',             'type':'material','mat':'feather','price':5},
    'snake_skin':  {'id':'snake_skin',   'name':'Piel de Serpiente', 'type':'material','mat':'scale',  'price':20},
    'snake_venom': {'id':'snake_venom',  'name':'Veneno de Serpiente','type':'material','mat':'venom', 'price':35},
    'horsehair':   {'id':'horsehair',    'name':'Crin de Caballo',   'type':'material','mat':'hair',   'price':12},
    'bear_pelt':   {'id':'bear_pelt',    'name':'Piel de Oso',       'type':'material','mat':'pelt',   'price':40},
    'bear_claw':   {'id':'bear_claw',    'name':'Garra de Oso',      'type':'material','mat':'bone',   'price':35},
    'bear_meat':   {'id':'bear_meat',    'name':'Carne de Oso',      'type':'consumable','hp':30,      'price':15},
}

# Mundos donde aparecen cada animal (world_id → lista de animal_id)
WORLD_ANIMALS = {
    'world_dungeon': ['crow', 'cat', 'snake'],
    'world_forest':  ['rabbit', 'deer', 'fox', 'boar', 'crow', 'snake', 'bear', 'parrot'],
    'world_ruins':   ['crow', 'snake', 'fox', 'cat'],
    'world_cellar':  ['cat', 'snake', 'crow'],
    'world_volcano': ['snake'],
    'world_dragon_lair': ['crow'],
}

# Número máximo de animales por mundo
MAX_ANIMALS_PER_WORLD = 5


class AnimalManager:
    """
    Gestiona los animales en un mundo. Se instancia por World.
    Los animales se mueven independientemente, huyen del jugador
    y pueden ser cazados.
    """

    def __init__(self, world_id, world_grid, walkable_fn):
        self.world_id   = world_id
        self.walkable   = walkable_fn
        self.animals    = []
        self._rng       = random.Random(hash(world_id) ^ 0xBEEF)
        self._tick      = 0
        self._spawn_cooldown = 0

        animal_ids = WORLD_ANIMALS.get(world_id, [])
        if not animal_ids:
            return

        # Spawn inicial: intentar colocar animales en posiciones libres
        width  = len(world_grid[0]) if world_grid else 32
        height = len(world_grid)
        for _ in range(MAX_ANIMALS_PER_WORLD):
            aid = self._rng.choice(animal_ids)
            for attempt in range(40):
                x = self._rng.randint(2, width - 3) + 0.5
                y = self._rng.randint(2, height - 3) + 0.5
                if self.walkable(x, y):
                    self._spawn_animal(aid, x, y)
                    break

    def _spawn_animal(self, animal_id, x, y):
        defn = ANIMAL_DEFS.get(animal_id)
        if not defn:
            return
        import copy
        a = copy.deepcopy(defn)
        a['x']         = x
        a['y']         = y
        a['alive']      = True
        a['tick']       = self._rng.randint(0, 5)
        a['dir_x']      = self._rng.uniform(-1, 1)
        a['dir_y']      = self._rng.uniform(-1, 1)
        a['wander_t']   = 0.0
        a['fleeing']    = False
        a['sprite_id']  = animal_id   # para el renderer (comparte con enemy sprites)
        a['attacking']  = False
        self.animals.append(a)

    def tick(self, player):
        """Actualizar comportamiento de todos los animales. Llamar cada frame lento."""
        self._tick += 1
        now = time.time()

        for a in self.animals:
            if not a['alive']:
                continue

            a['tick'] = (a['tick'] + 1) % 4
            if a['tick'] != 0:
                continue

            px, py = player.x, player.y
            dist   = math.hypot(a['x'] - px, a['y'] - py)
            flee   = dist < a['flee_dist']
            a['fleeing'] = flee

            if flee and a['behavior'] in ('passive', 'timid'):
                # huir en dirección contraria al jugador
                dx = a['x'] - px
                dy = a['y'] - py
                length = math.hypot(dx, dy) or 1.0
                dx, dy = dx / length, dy / length
            elif a['behavior'] == 'neutral' and dist < 1.2 and a.get('dmg', 0) > 0:
                # atacar si muy cerca
                dx = px - a['x']
                dy = py - a['y']
                length = math.hypot(dx, dy) or 1.0
                dx, dy = dx / length, dy / length
                a['attacking'] = True
            else:
                # deambular aleatoriamente
                a['wander_t'] = a.get('wander_t', 0) - 1
                if a['wander_t'] <= 0:
                    angle = self._rng.uniform(0, math.pi * 2)
                    a['dir_x'] = math.cos(angle)
                    a['dir_y'] = math.sin(angle)
                    a['wander_t'] = self._rng.randint(8, 20)
                dx, dy = a.get('dir_x', 1.0), a.get('dir_y', 0.0)
                a['attacking'] = False

            spd  = a['speed']
            nx   = a['x'] + dx * spd
            ny   = a['y'] + dy * spd
            if self.walkable(nx, a['y']):
                a['x'] = nx
            else:
                a['dir_x'] = -a.get('dir_x', 1.0)
                a['wander_t'] = 0
            if self.walkable(a['x'], ny):
                a['y'] = ny
            else:
                a['dir_y'] = -a.get('dir_y', 0.0)
                a['wander_t'] = 0

    def attack_player(self, player):
        """
        Animales neutrales que están muy cerca pueden atacar.
        Retorna lista de mensajes.
        """
        msgs = []
        for a in self.animals:
            if not a['alive']:
                continue
            if not a.get('attacking'):
                continue
            dist = math.hypot(a['x'] - player.x, a['y'] - player.y)
            if dist < 1.0 and a.get('dmg', 0) > 0:
                dmg    = max(1, a['dmg'] + self._rng.randint(-1, 1))
                actual = player.take_damage(dmg)
                msgs.append(f"{a['name']} ataca! -{actual}HP")
        return msgs

    def get_loot(self, animal):
        """Genera loot al matar un animal."""
        import copy
        drops = []
        for item_id, chance in animal.get('loot_table', []):
            if self._rng.random() < chance and item_id in ANIMAL_LOOT_ITEMS:
                drops.append(copy.deepcopy(ANIMAL_LOOT_ITEMS[item_id]))
        return drops

    def animal_at(self, x, y, radius=0.8):
        for a in self.animals:
            if a['alive'] and math.hypot(a['x'] - x, a['y'] - y) < radius:
                return a
        return None
