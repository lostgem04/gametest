"""
npc.py — Sistema de NPCs: diálogo, quests, comercio, herrería.

Tipos de NPC:
  - Conversacionales: frases + quests
  - Mercaderes: compran y venden items (role='merchant')
  - Herreros: crean armas y armaduras por materiales+oro (role='blacksmith')

Interacción:
  F         — hablar / ver oferta
  F + número — comprar/encargar
"""


import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import random, copy

# ── Quest templates ────────────────────────────────────────────────────────────

QUESTS = {
    'q_skeletons': {
        'id':           'q_skeletons',
        'title':        'Bones of the Crypt',
        'description':  'Skeletons have been rising from the old crypt.\n'
                        'Slay 3 of them and return.',
        'goal_type':    'kill',
        'goal_target':  'skeleton',
        'goal_count':   3,
        'reward_gold':  40,
        'reward_xp':    60,
        'reward_item':  None,
    },
    'q_slimes': {
        'id':           'q_slimes',
        'title':        'Slime Infestation',
        'description':  'The cellar is overrun with slimes.\n'
                        'Kill 2 slimes and I will pay you well.',
        'goal_type':    'kill',
        'goal_target':  'slime',
        'goal_count':   2,
        'reward_gold':  30,
        'reward_xp':    40,
        'reward_item':  None,
    },
    'q_collect_gold': {
        'id':           'q_collect_gold',
        'title':        'Tax Collection',
        'description':  'Collect the Gold Coins from the dungeon\n'
                        'and bring them back.',
        'goal_type':    'collect',
        'goal_target':  'gold',
        'goal_count':   1,
        'reward_gold':  20,
        'reward_xp':    30,
        'reward_item':  None,
    },
    'q_portal': {
        'id':           'q_portal',
        'title':        'Through the Portal',
        'description':  'A strange portal has appeared to the east.\n'
                        'Step through it and report back.',
        'goal_type':    'reach',
        'goal_target':  'world_forest',
        'goal_count':   1,
        'reward_gold':  50,
        'reward_xp':    80,
        'reward_item':  None,
    },
    'q_wolves': {
        'id':           'q_wolves',
        'title':        'Wolf Trouble',
        'description':  'Wolves have been preying on the villagers.\n'
                        'Hunt down 2 wolves.',
        'goal_type':    'kill',
        'goal_target':  'wolf',
        'goal_count':   2,
        'reward_gold':  35,
        'reward_xp':    50,
        'reward_item':  None,
    },
    'q_golems': {
        'id':           'q_golems',
        'title':        'Stone Giants',
        'description':  'Ancient golems guard the deep dungeon.\n'
                        'Slay 2 of them. Beware their massive health.',
        'goal_type':    'kill',
        'goal_target':  'golem',
        'goal_count':   2,
        'reward_gold':  120,
        'reward_xp':    150,
        'reward_item':  None,
    },
    'q_vampires': {
        'id':           'q_vampires',
        'title':        'Children of the Night',
        'description':  'Vampires stalk the dark corners of the dungeon.\n'
                        'Destroy 3 of them before they drain your life.',
        'goal_type':    'kill',
        'goal_target':  'vampire',
        'goal_count':   3,
        'reward_gold':  90,
        'reward_xp':    120,
        'reward_item':  None,
    },
    'q_necromancer': {
        'id':           'q_necromancer',
        'title':        'Lord of the Undead',
        'description':  'The Necromancer rules the deepest crypt.\n'
                        'Defeat him and end his undead army.',
        'goal_type':    'kill',
        'goal_target':  'necromancer',
        'goal_count':   1,
        'reward_gold':  300,
        'reward_xp':    400,
        'reward_item':  None,
    },
    'q_dragon': {
        'id':           'q_dragon',
        'title':        'Slay the Dragon',
        'description':  "The Dragon lairs in the deepest volcanic chamber.\n"
                        "Only the mightiest hero can face it.",
        'goal_type':    'kill',
        'goal_target':  'dragon',
        'goal_count':   1,
        'reward_gold':  500,
        'reward_xp':    800,
        'reward_item':  None,
    },
    'q_elf_silk': {
        'id':           'q_elf_silk',
        'title':        'The Silk Weaver',
        'description':  'We need spider silk to weave magical tunics.\n'
                        'Bring me 3 spider silks from the dungeon.',
        'goal_type':    'collect_material',
        'goal_target':  'silk',
        'goal_count':   3,
        'reward_gold':  60,
        'reward_xp':    80,
        'reward_item':  None,
    },
    'q_golem_cores': {
        'id':           'q_golem_cores',
        'title':        'Heart of Stone',
        'description':  'Golem cores are needed for elven enchantments.\n'
                        'Defeat 2 golems and bring their cores.',
        'goal_type':    'kill',
        'goal_target':  'golem',
        'goal_count':   2,
        'reward_gold':  150,
        'reward_xp':    200,
        'reward_item':  None,
    },
}

# ── Shop catalogues ────────────────────────────────────────────────────────────

SHOP_BROM = {
    'name': "Brom's Goods",
    'buy_items': [
        {'id':'potion',    'name':'Health Potion',   'type':'consumable','hp':30,  'price':25},
        {'id':'potion_big','name':'Mega Potion',      'type':'consumable','hp':60,  'price':50},
        {'id':'elixir',    'name':'Mana Elixir',      'type':'consumable','mp':25,  'price':20},
        {'id':'pot_str',   'name':'Strength Potion',  'type':'consumable','buff':'strength','price':45},
        {'id':'pot_haste', 'name':'Haste Potion',     'type':'consumable','buff':'haste',   'price':40},
        {'id':'arrows',    'name':'Arrow Bundle x15', 'type':'arrows','count':15,  'price':18},
        {'id':'arrows',    'name':'Arrow Bundle x30', 'type':'arrows','count':30,  'price':32},
        {'id':'shortbow',  'name':'Short Bow',        'type':'bow','dmg':8,        'price':80},
        {'id':'spellbook', 'name':'Tome of Flames',   'type':'spellbook',          'price':120},
    ],
    # items the merchant buys from player (sell_price = item value)
    'sell_ratio': 0.4,   # player gets 40% of base price when selling
}

SHOP_FOREST_TRADER = {
    'name': "Forest Trader",
    'buy_items': [
        {'id':'potion',    'name':'Health Potion',   'type':'consumable','hp':30,  'price':30},
        {'id':'elixir',    'name':'Mana Elixir',      'type':'consumable','mp':25,  'price':22},
        {'id':'arrows',    'name':'Arrow Bundle x15', 'type':'arrows','count':15,  'price':20},
        {'id':'mineral_iron','name':'Iron Ore',       'type':'material','mat':'iron','price':15},
        {'id':'mineral_gem', 'name':'Gemstone',       'type':'material','mat':'gem','price':60},
    ],
    'sell_ratio': 0.45,
}

# ── Forge/Blacksmith catalogues ────────────────────────────────────────────────

FORGE_GAUNTHOR = {
    'name': "Gaunthor's Forge",
    'recipes': [
        {
            'id':     'iron_sword',
            'name':   'Iron Sword',
            'type':   'weapon',
            'dmg':    18,
            'gold':   60,
            'mats':   {'iron': 2},
            'desc':   'A solid iron blade. Reliable.',
        },
        {
            'id':     'steel_sword',
            'name':   'Steel Sword',
            'type':   'weapon',
            'dmg':    30,
            'gold':   140,
            'mats':   {'iron': 3, 'gem': 1},
            'desc':   'Forged with a gemstone core. Keen edge.',
        },
        # ── Armaduras de materiales ────────────────────────────────────────────
        {
            'id':     'leather_armor',
            'name':   'Leather Armor',
            'type':   'armor',
            'def':    6,
            'block':  0.10,
            'gold':   40,
            'mats':   {'pelt': 3},
            'desc':   'Light leather from wolf pelts. Good for archers.',
        },
        {
            'id':     'iron_shield',
            'name':   'Iron Shield',
            'type':   'armor',
            'def':    10,
            'block':  0.25,
            'gold':   70,
            'mats':   {'iron': 3},
            'desc':   'Heavy but protective.',
        },
        {
            'id':     'iron_armor',
            'name':   'Iron Plate',
            'type':   'armor',
            'def':    18,
            'gold':   180,
            'mats':   {'iron': 5},
            'desc':   'Full iron plate. Slows you slightly.',
        },
        {
            'id':     'chainmail',
            'name':   'Chainmail',
            'type':   'armor',
            'def':    14,
            'block':  0.20,
            'gold':   120,
            'mats':   {'iron': 4},
            'desc':   'Linked iron rings. Balanced protection.',
        },
        {
            'id':     'silk_tunic',
            'name':   'Silk Tunic',
            'type':   'armor',
            'def':    4,
            'magic_bonus': 8,
            'gold':   90,
            'mats':   {'silk': 3},
            'desc':   'Woven spider silk. Light, boosts spell power.',
        },
        {
            'id':     'gem_bow',
            'name':   'Gem-Tipped Bow',
            'type':   'bow',
            'dmg':    22,
            'gold':   160,
            'mats':   {'iron': 2, 'gem': 2},
            'desc':   'Magical arrows hit harder.',
        },
        {
            'id':     'pickaxe',
            'name':   'Iron Pickaxe',
            'type':   'tool',
            'id_tag': 'pickaxe',
            'gold':   50,
            'mats':   {'iron': 2},
            'desc':   'Mine ore from mineral veins.',
        },
        {
            'id':     'wood_axe',
            'name':   'Woodcutter Axe',
            'type':   'weapon',
            'dmg':    16,
            'id_tag': 'axe',
            'gold':   40,
            'mats':   {'iron': 1, 'wood': 2},
            'desc':   'Chop trees and fight. Dual purpose.',
        },
        {
            'id':     'wood_shield',
            'name':   'Wooden Shield',
            'type':   'armor',
            'def':    5,
            'block':  0.18,
            'gold':   30,
            'mats':   {'wood': 3},
            'desc':   'Light shield made from sturdy wood.',
        },
    ],
}

# ── Elven shop & forge ────────────────────────────────────────────────────────

SHOP_ELVEN_TRADER = {
    'name': "Elyndra's Elven Goods",
    'buy_items': [
        {'id':'potion',       'name':'Health Potion',      'type':'consumable','hp':30,  'price':28},
        {'id':'potion_big',   'name':'Mega Potion',         'type':'consumable','hp':80,  'price':60},
        {'id':'elixir',       'name':'Mana Elixir',         'type':'consumable','mp':40,  'price':30},
        {'id':'pot_str',      'name':'Strength Potion',     'type':'consumable','buff':'strength','price':50},
        {'id':'pot_haste',    'name':'Haste Potion',        'type':'consumable','buff':'haste',   'price':45},
        {'id':'silver_arrows','name':'Silver Arrows x20',   'type':'arrows','count':20,   'price':45, 'silver':True},
        {'id':'elven_bow',    'name':'Elven Longbow',       'type':'bow','dmg':20,'cooldown':0.5, 'price':180},
        {'id':'elven_tome',   'name':'Elven Spellbook',     'type':'spellbook','magic_bonus':10,  'price':200},
        {'id':'blood_vial',   'name':'Blood Vial',          'type':'consumable','hp':20,'mp':15,   'price':35},
    ],
    'sell_ratio': 0.5,
}

FORGE_ELVEN = {
    'name': "Theron's Elven Forge",
    'recipes': [
        {
            'id':    'elven_sword',
            'name':  'Elven Blade',
            'type':  'weapon',
            'dmg':   28,
            'gold':  120,
            'mats':  {'iron': 2, 'enchanted': 1},
            'desc':  'Light and razor-sharp. Enhanced with enchanted ore.',
        },
        {
            'id':    'silver_sword',
            'name':  'Silver Sword',
            'type':  'weapon',
            'dmg':   22,
            'silver': True,
            'gold':  100,
            'mats':  {'iron': 2, 'gem': 1},
            'desc':  'Silver is deadly to vampires (+60% dmg).',
        },
        # ── Armaduras y túnicas mágicas ────────────────────────────────────────
        {
            'id':    'mage_robe',
            'name':  'Mage Robe',
            'type':  'armor',
            'def':   5,
            'magic_bonus': 18,
            'gold':  150,
            'mats':  {'silk': 2, 'enchanted': 1},
            'desc':  "Enchanted robes for pure spellcasters. Greatly boosts magic.",
        },
        {
            'id':    'arcane_tunic',
            'name':  'Arcane Tunic',
            'type':  'armor',
            'def':   10,
            'magic_bonus': 25,
            'block': 0.10,
            'gold':  220,
            'mats':  {'silk': 2, 'enchanted': 2},
            'desc':  'Balanced tunic: light armor AND strong spell amplification.',
        },
        {
            'id':    'void_robe',
            'name':  'Void Robe',
            'type':  'armor',
            'def':   8,
            'magic_bonus': 35,
            'gold':  350,
            'mats':  {'soul': 3, 'enchanted': 2},
            'desc':  'Woven from soul shards. Extreme magic power, little defense.',
        },
        {
            'id':    'enchanted_armor',
            'name':  'Enchanted Plate',
            'type':  'armor',
            'def':   22,
            'magic_bonus': 15,
            'block': 0.30,
            'gold':  300,
            'mats':  {'iron': 4, 'enchanted': 2},
            'desc':  'Plates imbued with arcane power. Boosts magic damage.',
        },
        {
            'id':    'elven_leather',
            'name':  'Elven Leather',
            'type':  'armor',
            'def':   12,
            'block': 0.15,
            'magic_bonus': 10,
            'gold':  180,
            'mats':  {'pelt': 2, 'enchanted': 1},
            'desc':  'Enchanted leather. Perfect for archer-mages.',
        },
        {
            'id':    'dragon_armor',
            'name':  'Dragon Scale Armor',
            'type':  'armor',
            'def':   40,
            'block': 0.45,
            'fire_resist': True,
            'gold':  500,
            'mats':  {'dragon': 3, 'iron': 2},
            'desc':  'Forged from dragon scales. Supreme protection.',
        },
        {
            'id':    'dragonfire_staff',
            'name':  'Dragonfire Staff',
            'type':  'weapon',
            'dmg':   20,
            'magic_bonus': 35,
            'gold':  600,
            'mats':  {'dragonfire': 2, 'enchanted': 2},
            'desc':  'Channels dragonfire. Massively boosts spell damage.',
        },
        {
            'id':    'elven_pickaxe',
            'name':  'Elven Pickaxe',
            'type':  'tool',
            'gold':  80,
            'mats':  {'iron': 1, 'enchanted': 1},
            'desc':  'Mines enchanted veins more efficiently.',
        },
    ],
}

# ── NPC definitions ────────────────────────────────────────────────────────────

NPC_DEFS = {
    'elara': {
        'id':        'elara',
        'name':      'Elara',
        'sprite_id': 'villager',
        'color':     (220, 190, 130),
        'role':      'quest',
        'lines': [
            "Strange times... the dungeons grow restless.",
            "I haven't slept well since the skeletons appeared.",
            "They say the portal to the east leads somewhere dark.",
            "Be careful out there, adventurer.",
            "My family has lived here for generations. This town will survive.",
        ],
        'quest': QUESTS['q_skeletons'],
        'quest_done_lines': [
            "You did it! The skeletons are at rest again. Thank you!",
            "The crypt is quiet now. I can sleep again.",
        ],
    },
    'brom': {
        'id':        'brom',
        'name':      'Brom the Merchant',
        'sprite_id': 'merchant',
        'color':     (200, 160, 50),
        'role':      'merchant',
        'shop':      SHOP_BROM,
        'lines': [
            "Welcome! Press F again to open the shop.",
            "Best prices in the dungeon, guaranteed.",
            "I once sold a sword to a skeleton. True story.",
            "Gold is the universal language, friend.",
        ],
        'quest': QUESTS['q_slimes'],
        'quest_done_lines': [
            "Slimes gone? Excellent! Here's your payment.",
            "My storage room is safe again. You have my thanks.",
        ],
    },
    'zephyr': {
        'id':        'zephyr',
        'name':      'Zephyr the Mage',
        'sprite_id': 'wizard',
        'color':     (140, 100, 220),
        'role':      'quest',
        'lines': [
            "The arcane energies here are... unusual.",
            "I have been studying this portal for weeks.",
            "Magic is simply science we do not yet understand.",
            "Step through the portal and tell me what you find!",
        ],
        'quest': QUESTS['q_portal'],
        'quest_done_lines': [
            "You returned from the other side! Incredible.",
            "The portal leads to the forest world. Fascinating!",
        ],
    },
    'mira': {
        'id':        'mira',
        'name':      'Mira',
        'sprite_id': 'villager',
        'color':     (190, 220, 160),
        'role':      'quest',
        'lines': [
            "The wolves have been getting closer to town every night.",
            "I heard howling again last night. It's getting worse.",
            "Please, someone must deal with those wolves!",
            "My children are afraid to go outside.",
        ],
        'quest': QUESTS['q_wolves'],
        'quest_done_lines': [
            "The wolves are gone! My children can play outside again!",
            "Thank you, adventurer. You are a hero to this village.",
        ],
    },
    'garrison': {
        'id':        'garrison',
        'name':      'Garrison',
        'sprite_id': 'guard',
        'color':     (160, 160, 200),
        'role':      'quest',
        'lines': [
            "Halt! ...Oh, you're an adventurer. Carry on.",
            "Keep the peace and we'll have no trouble.",
            "I've been guarding this post for fifteen years.",
            "Watch yourself. Something has been lurking in the shadows.",
        ],
        'quest': QUESTS['q_collect_gold'],
        'quest_done_lines': [
            "You found the tax gold! The king will be pleased.",
            "Excellent work. Here is your reward.",
        ],
    },
    'gaunthor': {
        'id':        'gaunthor',
        'name':      'Gaunthor the Smith',
        'sprite_id': 'blacksmith',
        'color':     (180, 120, 60),
        'role':      'blacksmith',
        'forge':     FORGE_GAUNTHOR,
        'lines': [
            "Step up! Best steel this side of the dungeon.",
            "Bring me iron ore and I'll forge you something worthy.",
            "A good blade needs good materials. Get mining!",
            "I can forge weapons, armor, and tools. Just bring the ore.",
        ],
        'quest': None,
    },
    'forest_trader': {
        'id':        'forest_trader',
        'name':      'Forest Trader',
        'sprite_id': 'merchant',
        'color':     (120, 200, 100),
        'role':      'merchant',
        'shop':      SHOP_FOREST_TRADER,
        'lines': [
            "Wares from the deep forest. Take a look!",
            "I buy minerals — bring me what you mine.",
            "Arrows and potions — all freshly stocked.",
        ],
        'quest': None,
    },
    'villager': {
        'id':        'villager',
        'name':      'Villager',
        'sprite_id': 'villager',
        'color':     (210, 185, 140),
        'role':      'quest',
        'lines': [
            "Adventurer! These are dangerous times.",
            "I hope you know how to use that weapon.",
            "There's a blacksmith further in — he'll arm you well.",
            "I've heard about treasures deep in the dungeon.",
        ],
        'quest': None,
    },
    'wizard': {
        'id':        'wizard',
        'name':      'Wandering Wizard',
        'sprite_id': 'wizard',
        'color':     (140, 100, 220),
        'role':      'quest',
        'lines': [
            "The old magic still lingers here.",
            "I sense powerful items nearby — keep searching.",
            "That tome you carry — treat it well.",
            "The ruins to the east hold ancient secrets.",
            "A Dragon's Lair lurks beyond the deepest dungeon portal.",
            "The Necromancer Crypt — only the bravest dare enter.",
        ],
        'quest': None,
    },
    # ── ELF NPCs ──────────────────────────────────────────────────────────────
    'sylvara': {
        'id':        'sylvara',
        'name':      'Sylvara the Elf',
        'sprite_id': 'elf',
        'race':      'elf',
        'color':     (100, 220, 130),
        'role':      'quest',
        'lines': [
            "Mae govannen, traveler. The forest has eyes.",
            "We elves have watched these lands for centuries.",
            "Golems have enormous HP but are very slow. Use ranged attacks.",
            "Vampires drain your life on contact — keep distance and use arrows.",
            "The Necromancer summons skeletons endlessly. Kill the boss first.",
            "Dragon scales can be forged into legendary armor at elven forges.",
            "Enchanted ore glows faintly — you'll find it in the deepest veins.",
            "Only miners find our rarest ores — no merchant can give you what the earth holds.",
        ],
        'quest': QUESTS['q_elf_silk'],
        'quest_done_lines': [
            "Excellent! With this silk we can weave Silk Tunics. Mae govannen!",
            "The forest is grateful. Our weavers will use this silk well.",
        ],
    },
    'elyndra': {
        'id':        'elyndra',
        'name':      'Elyndra the Elven Merchant',
        'sprite_id': 'elf',
        'race':      'elf',
        'color':     (120, 240, 160),
        'role':      'merchant',
        'shop':      SHOP_ELVEN_TRADER,
        'lines': [
            "Only the finest elven crafts, friend.",
            "Silver arrows pierce vampires cleanly. Worth the price.",
            "I trade in rare materials. Bring me enchanted ore!",
            "Elven goods are light and powerful — not found anywhere else.",
        ],
        'quest': None,
        'quest_done_lines': [],
    },
    'theron': {
        'id':        'theron',
        'name':      'Theron Elven Smith',
        'sprite_id': 'elf_smith',
        'race':      'elf',
        'color':     (80, 200, 110),
        'role':      'blacksmith',
        'forge':     FORGE_ELVEN,
        'lines': [
            "Elven steel is lighter and sharper than iron.",
            "Bring me enchanted ore and I'll craft armor that boosts your magic.",
            "Dragon scales and dragonfire gems make the finest equipment.",
            "My crafts are rare — you won't find these in any common shop.",
            "Minerals must be mined — I cannot conjure ore from nothing.",
        ],
        'quest': None,
    },
}

# ── QuestLog ──────────────────────────────────────────────────────────────────

class QuestLog:
    """Tracks player quest progress."""

    def __init__(self):
        self.active    = {}   # quest_id → {quest, progress}
        self.completed = set()

    def accept(self, quest):
        qid = quest['id']
        if qid not in self.active and qid not in self.completed:
            self.active[qid] = {'quest': quest, 'progress': 0}
            return True
        return False

    def update_kill(self, enemy_id):
        msgs = []
        for qid, entry in list(self.active.items()):
            q = entry['quest']
            if q['goal_type'] == 'kill' and q['goal_target'] == enemy_id:
                entry['progress'] += 1
                need = q['goal_count']
                have = entry['progress']
                msgs.append(f"Quest '{q['title']}': {have}/{need}")
                if have >= need:
                    self.completed.add(qid)
                    del self.active[qid]
                    msgs.append(f"Quest COMPLETE: {q['title']}!")
        return msgs

    def update_collect(self, item_id):
        msgs = []
        for qid, entry in list(self.active.items()):
            q = entry['quest']
            if q['goal_type'] == 'collect' and q['goal_target'] == item_id:
                entry['progress'] = 1
                self.completed.add(qid)
                del self.active[qid]
                msgs.append(f"Quest COMPLETE: {q['title']}!")
        return msgs

    def update_reach(self, world_name):
        msgs = []
        for qid, entry in list(self.active.items()):
            q = entry['quest']
            if q['goal_type'] == 'reach' and q['goal_target'] == world_name:
                self.completed.add(qid)
                del self.active[qid]
                msgs.append(f"Quest COMPLETE: {q['title']}!")
        return msgs

    def is_complete(self, quest_id):
        return quest_id in self.completed

    def is_active(self, quest_id):
        return quest_id in self.active

    def summary(self):
        lines = []
        for qid, entry in self.active.items():
            q = entry['quest']
            lines.append(f"  [!] {q['title']}: {entry['progress']}/{q['goal_count']}")
        for qid in self.completed:
            q_name = QUESTS.get(qid, {}).get('title', qid)
            lines.append(f"  [✓] {q_name}")
        return lines or ["  No active quests."]


# ── talk() — main interaction entry point ────────────────────────────────────

def talk(npc_def, quest_log, player):
    """
    Returns a list of dialogue lines to display.
    Role-aware: quest / merchant / blacksmith.
    """
    role = npc_def.get('role', 'quest')
    lines = [f"── {npc_def['name']} ──"]

    if role == 'merchant':
        shop = npc_def.get('shop', {})
        lines.append(f"[{shop.get('name','Shop')}]")
        lines.append("Press F again to browse. Buy: press B<n>  Sell: press S<n>")
        lines.append(random.choice(npc_def['lines']))
        # offer quest too if any
        _maybe_offer_quest(npc_def, quest_log, lines)
        npc_def['_shop_open'] = True
        return lines

    if role == 'blacksmith':
        forge = npc_def.get('forge', {})
        lines.append(f"[{forge.get('name','Forge')}]")
        lines.append("Press F again to see forge menu. Order: press O<n>")
        lines.append(random.choice(npc_def['lines']))
        npc_def['_forge_open'] = True
        return lines

    # default: quest NPC
    quest = npc_def.get('quest')
    if quest:
        qid = quest['id']
        if quest_log.is_complete(qid):
            say = random.choice(npc_def.get('quest_done_lines', ["Thank you!"]))
            lines.append(say)
        elif quest_log.is_active(qid):
            entry = quest_log.active[qid]
            prog  = entry['progress']
            need  = quest['goal_count']
            lines.append(f"[Quest in progress: {prog}/{need}]")
            lines.append(random.choice(npc_def['lines']))
        else:
            lines.append(f"[QUEST: {quest['title']}]")
            lines.append(quest['description'])
            lines.append(f"Reward: {quest['reward_gold']}g  +{quest['reward_xp']} XP")
            lines.append("Press F again to accept.")
            npc_def['_pending_accept'] = True
            return lines
    else:
        lines.append(random.choice(npc_def['lines']))

    return lines


def _maybe_offer_quest(npc_def, quest_log, lines):
    quest = npc_def.get('quest')
    if not quest:
        return
    qid = quest['id']
    if not quest_log.is_complete(qid) and not quest_log.is_active(qid):
        lines.append(f"  Also: [QUEST] {quest['title']} — ask me!")


def accept_quest_if_pending(npc_def, quest_log, player):
    if not npc_def.get('_pending_accept'):
        return None
    npc_def['_pending_accept'] = False
    quest = npc_def.get('quest')
    if not quest:
        return None
    qid = quest['id']
    if quest_log.is_complete(qid) or quest_log.is_active(qid):
        return None
    if quest_log.accept(quest):
        return f"Quest accepted: {quest['title']}"
    return None


def try_complete_quest(npc_def, quest_log, player):
    quest = npc_def.get('quest')
    if not quest:
        return None
    qid = quest['id']
    if quest_log.is_complete(qid):
        key = f'_rewarded_{qid}'
        if npc_def.get(key):
            return None
        npc_def[key] = True
        player.gold  += quest['reward_gold']
        player.gain_xp(quest['reward_xp'])
        return (f"Quest reward: +{quest['reward_gold']}g  +{quest['reward_xp']} XP")
    return None


# ── SHOP functions ────────────────────────────────────────────────────────────

def shop_menu(npc_def):
    """Returns lines listing the shop inventory with prices."""
    shop  = npc_def.get('shop', {})
    items = shop.get('buy_items', [])
    lines = [f"═══ {shop.get('name','Shop')} ═══",
             "  #  Item                   Price"]
    for i, it in enumerate(items):
        lines.append(f"  {i}  {it['name']:<22} {it['price']}g")
    sell_r = int(shop.get('sell_ratio', 0.4)*100)
    lines.append(f"─── Sell items from inventory at {sell_r}% value ───")
    lines.append("B<n>: buy item n  |  S<n>: sell inv slot n")
    return lines


def shop_buy(npc_def, player, index):
    """Player buys item[index] from shop. Returns result message."""
    shop  = npc_def.get('shop', {})
    items = shop.get('buy_items', [])
    if index < 0 or index >= len(items):
        return "Invalid item number."
    item  = items[index]
    price = item['price']
    if player.gold < price:
        return f"Not enough gold! (need {price}g, have {player.gold}g)"
    item_copy = {k: v for k, v in item.items() if k != 'price'}
    if not player.pick_up(item_copy):
        return "Inventory full!"
    player.gold -= price
    return f"Bought {item['name']} for {price}g. ({player.gold}g left)"


def shop_sell(npc_def, player, slot):
    """Player sells inventory slot to merchant. Returns result message."""
    shop = npc_def.get('shop', {})
    ratio = shop.get('sell_ratio', 0.4)
    if slot < 0 or slot >= len(player.inventory):
        return "Invalid inventory slot."
    item = player.inventory[slot]
    # estimate price
    base_price = item.get('price', 20)
    earned = max(1, int(base_price * ratio))
    player.inventory.pop(slot)
    player.gold += earned
    return f"Sold {item['name']} for {earned}g. ({player.gold}g total)"


# ── FORGE functions ───────────────────────────────────────────────────────────

def forge_menu(npc_def, player):
    """Returns lines listing forge recipes, marking affordable ones."""
    forge   = npc_def.get('forge', {})
    recipes = forge.get('recipes', [])
    lines   = [f"═══ {forge.get('name','Forge')} ═══",
               "  #  Item              Gold  Materials"]
    for i, r in enumerate(recipes):
        mats_str = ', '.join(f"{v}x {k}" for k,v in r.get('mats',{}).items())
        can = _can_forge(player, r)
        mark = '✓' if can else ' '
        lines.append(f" {mark}{i}  {r['name']:<18} {r['gold']}g  {mats_str}")
    lines.append("O<n>: order item n  |  Need iron ore & gold")
    return lines


def forge_order(npc_def, player, index):
    """Player orders a forged item. Returns result message."""
    forge   = npc_def.get('forge', {})
    recipes = forge.get('recipes', [])
    if index < 0 or index >= len(recipes):
        return "Invalid recipe number."
    recipe = recipes[index]
    if player.gold < recipe['gold']:
        return f"Not enough gold! Need {recipe['gold']}g."
    # check materials in inventory
    mats_needed = dict(recipe.get('mats', {}))
    inv_mats = {}
    for it in player.inventory:
        if it.get('type') == 'material':
            mat = it.get('mat','')
            inv_mats[mat] = inv_mats.get(mat, 0) + 1
    for mat, count in mats_needed.items():
        if inv_mats.get(mat, 0) < count:
            return f"Missing materials: need {count}x {mat} ore."
    # deduct materials
    for mat, count in mats_needed.items():
        removed = 0
        new_inv = []
        for it in player.inventory:
            if it.get('type') == 'material' and it.get('mat') == mat and removed < count:
                removed += 1
            else:
                new_inv.append(it)
        player.inventory = new_inv
    # deduct gold
    player.gold -= recipe['gold']
    # create forged item
    forged = {k: v for k, v in recipe.items()
              if k not in ('gold', 'mats', 'desc', 'recipes', 'id_tag')}
    # preserve id_tag as the item's id for tool detection
    if 'id_tag' in recipe:
        forged['id'] = recipe['id_tag']
    if not player.pick_up(forged):
        # refund if no space
        player.gold += recipe['gold']
        return "Inventory full! Forging cancelled."
    return f"Forged: {recipe['name']}! ({player.gold}g left)"


def _can_forge(player, recipe):
    """Check if player has gold + all materials for a recipe."""
    if player.gold < recipe['gold']:
        return False
    mats_needed = dict(recipe.get('mats', {}))
    inv_mats = {}
    for it in player.inventory:
        if it.get('type') == 'material':
            mat = it.get('mat', '')
            inv_mats[mat] = inv_mats.get(mat, 0) + 1
    for mat, count in mats_needed.items():
        if inv_mats.get(mat, 0) < count:
            return False
    return True
