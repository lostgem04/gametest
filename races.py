"""
races.py — Definiciones de razas para Arcane Abyss.

Cada raza modifica los stats base del jugador y aplica
bonificaciones/penalizaciones a skills, cooldowns y capacidades.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Esquema de cada raza:
#   id            str   — clave interna
#   name          str   — nombre mostrado
#   description   str   — texto largo en el menú
#   ascii_art     list  — art ASCII para el menú de selección
#   color         tuple — (r,g,b) color del nombre en menú
#
#   stat_mods     dict  — modificadores sobre stats base del Player:
#                         hp, max_hp, mp, max_mp, attack, defense, speed
#   skill_mult    dict  — multiplicadores de XP de skill {melee/bow/magic: float}
#   cooldown_mult dict  — multiplicadores de cooldown {melee/bow/fireball/lightning: float}
#                         < 1.0 = más rápido, > 1.0 = más lento
#   xp_mult       float — multiplicador global de XP ganado
#   arrow_dmg     float — multiplicador de daño de flechas
#   spell_dmg     float — multiplicador de daño de hechizos
#   melee_range   float — modificador de alcance cuerpo a cuerpo (+/-)
#   block_bonus   float — bonus a porcentaje de bloqueo
#   passives      list  — strings descriptivos de habilidades pasivas
# ─────────────────────────────────────────────────────────────────────────────

RACE_DEFS = {

    'human': {
        'id':          'human',
        'name':        'Humano',
        'description': (
            "Versátil y adaptable, el Humano es la raza más equilibrada.\n"
            "Sin debilidades extremas ni ventajas exageradas, se adapta\n"
            "a cualquier estilo de combate con facilidad.\n\n"
            "  ⚔  Melee     ████████  Normal\n"
            "  🏹 Arco      ████████  Normal\n"
            "  ✨ Magia     ████████  Normal\n"
            "  ❤  Vida      ████████  Normal\n"
            "  💨 Velocidad ████████  Normal"
        ),
        'ascii_art': [
            "  O  ",
            " /|\\ ",
            " / \\ ",
        ],
        'color': (220, 200, 160),
        'stat_mods': {
            'hp': 0, 'max_hp': 0,
            'mp': 0, 'max_mp': 0,
            'attack': 0, 'defense': 0, 'speed': 0.0,
        },
        'skill_mult':    {'melee': 1.0, 'bow': 1.0, 'magic': 1.0},
        'cooldown_mult': {'melee': 1.0, 'bow': 1.0, 'fireball': 1.0, 'lightning': 1.0},
        'xp_mult':       1.0,
        'arrow_dmg':     1.0,
        'spell_dmg':     1.0,
        'melee_range':   0.0,
        'block_bonus':   0.0,
        'passives': [
            "Adaptable: gana XP un 10% extra al subir de nivel",
            "Resistente: la primera muerte en cada sesión restaura 20 HP",
        ],
    },

    'elf': {
        'id':          'elf',
        'name':        'Elfo',
        'description': (
            "Ágil y preciso, el Elfo domina el arco y la ballesta.\n"
            "Sus reflejos sobrehumanos reducen los tiempos de recarga\n"
            "ranged, pero su constitución frágil lo hace vulnerable\n"
            "al combate cuerpo a cuerpo directo.\n\n"
            "  ⚔  Melee     ██████    -20% XP\n"
            "  🏹 Arco      ██████████ +40% XP · +25% DMG\n"
            "  ✨ Magia     █████████  +20% XP\n"
            "  ❤  Vida      ██████    -20 HP\n"
            "  💨 Velocidad ██████████ +20%"
        ),
        'ascii_art': [
            "  Ô  ",
            " /|\\ ",
            "  |  ",
        ],
        'color': (100, 220, 140),
        'stat_mods': {
            'hp': -20, 'max_hp': -20,
            'mp':  10, 'max_mp':  10,
            'attack': -2, 'defense': -1, 'speed': 0.024,  # +20% de 0.12
        },
        'skill_mult':    {'melee': 0.80, 'bow': 1.40, 'magic': 1.20},
        'cooldown_mult': {'melee': 0.90, 'bow': 0.65, 'fireball': 0.85, 'lightning': 0.85},
        'xp_mult':       1.0,
        'arrow_dmg':     1.25,
        'spell_dmg':     1.10,
        'melee_range':   -0.3,
        'block_bonus':   0.0,
        'passives': [
            "Puntería Élfica: +25% daño con arcos y ballestas",
            "Ágil: recarga de arco 35% más rápida",
            "Frágil: -20 HP máximo, -2 ataque base",
        ],
    },

    'wizard': {
        'id':          'wizard',
        'name':        'Hechicero',
        'description': (
            "Maestro de las artes arcanas, el Hechicero canaliza\n"
            "fuerzas devastadoras pero paga el precio con un cuerpo\n"
            "débil y poca resistencia física.\n\n"
            "  ⚔  Melee     ████      -30% XP · -4 ATK\n"
            "  🏹 Arco      █████     -10% XP\n"
            "  ✨ Magia     ██████████ +60% XP · +40% DMG\n"
            "  ❤  Vida      █████     -30 HP\n"
            "  💙 Maná      ██████████ +30 MP"
        ),
        'ascii_art': [
            "  ^  ",
            " (|) ",
            "  |  ",
        ],
        'color': (160, 80, 255),
        'stat_mods': {
            'hp': -30, 'max_hp': -30,
            'mp':  30, 'max_mp':  30,
            'attack': -4, 'defense': -2, 'speed': -0.01,
        },
        'skill_mult':    {'melee': 0.70, 'bow': 0.90, 'magic': 1.60},
        'cooldown_mult': {'melee': 1.20, 'bow': 1.10, 'fireball': 0.60, 'lightning': 0.60},
        'xp_mult':       1.0,
        'arrow_dmg':     0.85,
        'spell_dmg':     1.40,
        'melee_range':   -0.2,
        'block_bonus':   0.0,
        'passives': [
            "Poder Arcano: +40% daño con hechizos",
            "Recarga de hechizos 40% más rápida",
            "Cuerpo Frágil: -30 HP máx, -4 ataque base",
            "Reserva Mágica: +30 MP máximo",
        ],
    },

    'goblin': {
        'id':          'goblin',
        'name':        'Goblin',
        'description': (
            "Pequeño, astuto y brutalmente rápido, el Goblin ataca\n"
            "antes que nadie. Su baja constitución lo obliga a depender\n"
            "de la velocidad para sobrevivir.\n\n"
            "  ⚔  Melee     █████████  +30% XP · cooldown -40%\n"
            "  🏹 Arco      ████████   +10% XP\n"
            "  ✨ Magia     ██████     -10% XP\n"
            "  ❤  Vida      ██████     -30 HP\n"
            "  💨 Velocidad ██████████ +30%"
        ),
        'ascii_art': [
            " .o. ",
            " >|< ",
            "  ^  ",
        ],
        'color': (80, 200, 60),
        'stat_mods': {
            'hp': -30, 'max_hp': -30,
            'mp':  -5, 'max_mp':  -5,
            'attack':  2, 'defense': -2, 'speed': 0.036,  # +30%
        },
        'skill_mult':    {'melee': 1.30, 'bow': 1.10, 'magic': 0.90},
        'cooldown_mult': {'melee': 0.60, 'bow': 0.85, 'fireball': 1.10, 'lightning': 1.10},
        'xp_mult':       1.0,
        'arrow_dmg':     1.05,
        'spell_dmg':     0.85,
        'melee_range':   -0.1,
        'block_bonus':   0.0,
        'passives': [
            "Frenesí: cooldown melee -40%, velocidad +30%",
            "Golpe Bajo: +10% probabilidad de crítico en melee",
            "Poca Vida: -30 HP máximo",
            "Anti-magia: -15% daño con hechizos",
        ],
    },

    'orc': {
        'id':          'orc',
        'name':        'Orco',
        'description': (
            "Mole de músculo y hueso, el Orco es el guerrero definitivo.\n"
            "Su fuerza bruta aplasta enemigos pero su lentitud lo\n"
            "convierte en blanco fácil para arcos y hechizos.\n\n"
            "  ⚔  Melee     ██████████ +40% XP · +6 ATK\n"
            "  🏹 Arco      ██████     -20% XP\n"
            "  ✨ Magia     █████      -30% XP\n"
            "  ❤  Vida      ██████████ +60 HP\n"
            "  💨 Velocidad ██████     -20%"
        ),
        'ascii_art': [
            "  M  ",
            " [|] ",
            " / \\ ",
        ],
        'color': (180, 100, 40),
        'stat_mods': {
            'hp':  60, 'max_hp':  60,
            'mp': -15, 'max_mp': -15,
            'attack':  6, 'defense':  4, 'speed': -0.024,  # -20%
        },
        'skill_mult':    {'melee': 1.40, 'bow': 0.80, 'magic': 0.70},
        'cooldown_mult': {'melee': 1.15, 'bow': 1.30, 'fireball': 1.40, 'lightning': 1.40},
        'xp_mult':       1.0,
        'arrow_dmg':     0.80,
        'spell_dmg':     0.70,
        'melee_range':   0.3,
        'block_bonus':   0.08,
        'passives': [
            "Piel Gruesa: +4 defensa base, +8% bloqueo pasivo",
            "Golpe Devastador: melee tiene alcance +0.3 extra",
            "Lento: -20% velocidad de movimiento",
            "Anti-magia: -30% XP magia, -30% daño arcano",
        ],
    },
}

# Lista ordenada para el menú
RACE_ORDER = ['human', 'elf', 'wizard', 'goblin', 'orc']


def apply_race(player, race_id):
    """
    Aplica los modificadores de raza al player.
    Llamar UNA VEZ tras crear el Player.
    """
    race = RACE_DEFS.get(race_id, RACE_DEFS['human'])
    player.race_id = race_id
    player.race    = race

    mods = race['stat_mods']
    player.hp        = max(1,  player.hp      + mods.get('hp',      0))
    player.max_hp    = max(10, player.max_hp  + mods.get('max_hp',  0))
    player.mp        = max(0,  player.mp      + mods.get('mp',      0))
    player.max_mp    = max(0,  player.max_mp  + mods.get('max_mp',  0))
    player.attack    = max(1,  player.attack  + mods.get('attack',  0))
    player.defense   = max(0,  player.defense + mods.get('defense', 0))
    player.speed     = max(0.04, player.speed + mods.get('speed',   0.0))

    # melee range override
    if race.get('melee_range', 0.0) != 0.0:
        player._race_melee_range_bonus = race['melee_range']
    else:
        player._race_melee_range_bonus = 0.0

    return race


def race_skill_mult(player, skill):
    """Multiplicador de XP de skill según raza."""
    race = getattr(player, 'race', RACE_DEFS['human'])
    return race.get('skill_mult', {}).get(skill, 1.0)


def race_cooldown_mult(player, key):
    """Multiplicador de cooldown según raza."""
    race = getattr(player, 'race', RACE_DEFS['human'])
    return race.get('cooldown_mult', {}).get(key, 1.0)


def race_arrow_dmg_mult(player):
    race = getattr(player, 'race', RACE_DEFS['human'])
    return race.get('arrow_dmg', 1.0)


def race_spell_dmg_mult(player):
    race = getattr(player, 'race', RACE_DEFS['human'])
    return race.get('spell_dmg', 1.0)


def race_block_bonus(player):
    race = getattr(player, 'race', RACE_DEFS['human'])
    return race.get('block_bonus', 0.0)
