"""player.py — Player state, movement, stats, buffs, spells, bow, race integration."""

import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, time

# ── Buff templates ─────────────────────────────────────────────────────────────
# buff_id → {duration_sec, effect_key, effect_val, display, color_code}
BUFF_DEFS = {
    'strength': {
        'duration': 30.0,
        'stat':     'bonus_attack',
        'val':      20,
        'label':    'STR+20',
        'color':    (220, 80,  40),
    },
    'haste': {
        'duration': 20.0,
        'stat':     'bonus_attack_speed',
        'val':      0.5,          # multiplier reduction on cooldown
        'label':    'HASTE',
        'color':    (80,  220, 220),
    },
}

# ── Spell definitions ──────────────────────────────────────────────────────────
SPELL_DEFS = {
    'fireball': {
        'name':      'Fireball',
        'mp_cost':   15,
        'dmg':       40,
        'range':     12.0,
        'splash':    1.5,          # radius that catches nearby enemies too
        'cooldown':  1.5,
        'color':     (220, 100, 20),
        'char':      'o',
    },
    'lightning': {
        'name':      'Lightning',
        'mp_cost':   20,
        'dmg':       55,
        'range':     18.0,
        'splash':    0.0,
        'cooldown':  2.0,
        'color':     (200, 200, 60),
        'char':      '|',
    },
}

# ── Arrow definition ───────────────────────────────────────────────────────────
ARROW_DEF = {
    'name':     'Arrow',
    'dmg':      18,
    'range':    16.0,
    'cooldown': 0.6,
    'color':    (200, 170, 80),
    'char':     '-',
}

class Player:
    def __init__(self, world):
        self.world     = world
        self.x, self.y = 1.5, 1.5
        self.angle     = 0.0

        # base stats
        self.hp        = 100
        self.max_hp    = 100
        self.mp        = 50
        self.max_mp    = 50
        self.xp        = 0
        self.level     = 1
        self.gold      = 0
        self.defense   = 2
        self.speed     = 0.12
        self.attack    = 8

        self.inventory = []
        self.equipped  = {'weapon': None, 'armor': None,
                          'bow': None, 'spellbook': None}
        self.alive     = True
        self.steps     = 0
        self.blocking  = False   # True mientras B está presionado (bloqueo activo)

        # ── identity ──────────────────────────────────────────────────────────
        self.name    = 'Héroe'
        self.race_id = 'human'
        self.race    = None      # set by races.apply_race()

        # ── buffs: list of {id, stat, val, expires_at, label, color} ──────────
        self.buffs     = []

        # ── cooldown tracking ─────────────────────────────────────────────────
        self._cooldowns = {}   # key → timestamp of last use

        # ── active spell selection ────────────────────────────────────────────
        self.active_spell = 'fireball'   # toggle between fireball / lightning
        # arrows counter (finite ammo)
        self.arrows = 20

        # ── skill XP ──────────────────────────────────────────────────────────
        # Each skill levels up independently; bonuses scale with level.
        # skill_xp[key] = current xp toward next level
        # skill_level[key] = current level (starts at 1)
        self.skill_xp    = {'melee': 0, 'bow': 0, 'magic': 0}
        self.skill_level = {'melee': 1, 'bow': 1, 'magic': 1}

    # ── movement ──────────────────────────────────────────────────────────────

    def move(self, forward, strafe=0.0):
        dx = math.cos(self.angle)*forward - math.sin(self.angle)*strafe
        dy = math.sin(self.angle)*forward + math.cos(self.angle)*strafe
        spd = self.effective_speed()
        nx  = self.x + dx*spd
        ny  = self.y + dy*spd
        moved = False
        pad = 0.25
        if self.world.walkable(nx + math.copysign(pad, dx), self.y):
            self.x = nx; moved = True
        if self.world.walkable(self.x, ny + math.copysign(pad, dy)):
            self.y = ny; moved = True
        if moved:
            self.steps += 1
            self.world.reveal_around(self.x, self.y)
        return moved

    def rotate(self, delta):
        self.angle = (self.angle + delta) % (2*math.pi)

    # ── buff system ───────────────────────────────────────────────────────────

    def apply_buff(self, buff_id):
        """Apply a buff, refreshing duration if already active."""
        defn = BUFF_DEFS.get(buff_id)
        if not defn:
            return f"Unknown buff: {buff_id}"
        # remove existing instance of same buff
        self.buffs = [b for b in self.buffs if b['id'] != buff_id]
        expires = time.time() + defn['duration']
        self.buffs.append({
            'id':       buff_id,
            'stat':     defn['stat'],
            'val':      defn['val'],
            'expires':  expires,
            'label':    defn['label'],
            'color':    defn['color'],
            'duration': defn['duration'],
        })
        return f"{defn['label']} active for {int(defn['duration'])}s!"

    def tick_buffs(self):
        """Remove expired buffs. Call once per frame."""
        now = time.time()
        expired = [b for b in self.buffs if now >= b['expires']]
        self.buffs = [b for b in self.buffs if now < b['expires']]
        return [f"{b['label']} wore off." for b in expired]

    def buff_val(self, stat):
        """Sum of all active buff values for a given stat key."""
        return sum(b['val'] for b in self.buffs if b['stat'] == stat)

    def buff_remaining(self, buff_id):
        """Seconds remaining on a buff, or 0."""
        for b in self.buffs:
            if b['id'] == buff_id:
                return max(0.0, b['expires'] - time.time())
        return 0.0

    # ── cooldown helpers ──────────────────────────────────────────────────────

    def on_cooldown(self, key):
        last = self._cooldowns.get(key, 0)
        cd   = self._get_cooldown(key)
        return (time.time() - last) < cd

    def _get_cooldown(self, key):
        # Race cooldown multiplier
        try:
            from races import race_cooldown_mult
            race_mult = race_cooldown_mult(self, key)
        except Exception:
            race_mult = 1.0

        if key == 'bow':
            # bow item may override cooldown (crossbow is slower)
            bow = self.equipped.get('bow')
            base = bow.get('cooldown', ARROW_DEF['cooldown']) if bow else ARROW_DEF['cooldown']
            return base * (1.0 - self.buff_val('bonus_attack_speed') * 0.5) * race_mult
        elif key in SPELL_DEFS:
            base = SPELL_DEFS[key]['cooldown']
            return base * (1.0 - self.buff_val('bonus_attack_speed') * 0.4) * race_mult
        elif key == 'melee':
            # weapon item may override cooldown (dagger is faster, spear slightly slower)
            weap = self.equipped.get('weapon')
            base = weap.get('cooldown', 0.3) if weap else 0.3
            return base * (1.0 - self.buff_val('bonus_attack_speed') * 0.6) * race_mult
        return 0.5

    def weapon_melee_range(self):
        """Return melee attack reach. Spear > sword > dagger. Race modifier applied."""
        weap = self.equipped.get('weapon')
        base = weap['range'] if (weap and 'range' in weap) else 2.2
        race_bonus = getattr(self, '_race_melee_range_bonus', 0.0)
        return base + race_bonus

    def set_cooldown(self, key):
        self._cooldowns[key] = time.time()

    def cooldown_remaining(self, key):
        last = self._cooldowns.get(key, 0)
        cd   = self._get_cooldown(key)
        rem  = cd - (time.time() - last)
        return max(0.0, rem)

    # ── effective stats (with buffs) ──────────────────────────────────────────

    def effective_speed(self):
        return self.speed

    def total_attack(self):
        base = self.attack
        w = self.equipped.get('weapon')
        if w and 'dmg' in w:
            base += w['dmg']
        base += self.buff_val('bonus_attack')
        return base

    def total_defense(self):
        base = self.defense
        a = self.equipped.get('armor')
        if a and 'def' in a:
            base += a['def']
        return base

    def spell_power(self, spell_id):
        """Damage for a spell, boosted by strength buff, magic gear, and race."""
        base = SPELL_DEFS[spell_id]['dmg']
        book = self.equipped.get('spellbook') or {}
        weap = self.equipped.get('weapon') or {}
        armor= self.equipped.get('armor') or {}
        magic_bonus = (book.get('magic_bonus',0) + weap.get('magic_bonus',0)
                       + armor.get('magic_bonus',0))
        raw = base + self.buff_val('bonus_attack') // 2 + magic_bonus
        try:
            from races import race_spell_dmg_mult
            raw = int(raw * race_spell_dmg_mult(self))
        except Exception:
            pass
        return raw

    def arrow_damage(self):
        base = ARROW_DEF['dmg']
        bow  = self.equipped.get('bow')
        if bow and 'dmg' in bow:
            base += bow['dmg']
        raw = base + self.buff_val('bonus_attack') // 3
        try:
            from races import race_arrow_dmg_mult
            raw = int(raw * race_arrow_dmg_mult(self))
        except Exception:
            pass
        return raw

    # ── levelling ─────────────────────────────────────────────────────────────

    def gain_xp(self, amount):
        self.xp += amount
        needed = self.level * 100
        if self.xp >= needed:
            self.xp    -= needed
            self.level += 1
            self.max_hp += 20
            self.hp      = min(self.hp+20, self.max_hp)
            self.max_mp += 10
            self.attack += 3
            self.defense+= 1
            return True
        return False

    # ── inventory ─────────────────────────────────────────────────────────────

    def pick_up(self, item):
        if item.get('type') == 'gold':
            self.gold += item.get('val', 0)
            return True
        if item.get('type') == 'arrows':
            self.arrows += item.get('count', 10)
            return True
        # materials, tools, weapons, armor, consumables, etc. — go to inventory
        if len(self.inventory) < 20:
            self.inventory.append(item)
            return True
        return False

    def use_item(self, index):
        if index < 0 or index >= len(self.inventory):
            return "Invalid slot."
        item = self.inventory[index]
        t    = item.get('type', '')
        msg  = ""

        if t == 'consumable':
            if 'hp' in item:
                self.hp = min(self.hp + item['hp'], self.max_hp)
                msg = f"Healed {item['hp']} HP."
            elif 'mp' in item:
                self.mp = min(self.mp + item['mp'], self.max_mp)
                msg = f"Restored {item['mp']} MP."
            elif 'buff' in item:
                msg = self.apply_buff(item['buff'])
            self.inventory.pop(index)

        elif t in ('weapon', 'armor', 'bow', 'spellbook'):
            slot = t
            old  = self.equipped.get(slot)
            self.equipped[slot] = item
            self.inventory.pop(index)
            if old:
                self.inventory.append(old)
            msg = f"Equipped {item['name']}."

        elif t == 'tool':
            msg = f"{item['name']}: equip it to mine ore veins."

        elif t == 'material':
            msg = f"{item['name']}: bring to a blacksmith to forge equipment."

        else:
            msg = f"Can't use {item['name']} here."
        return msg

    # ── skill system ──────────────────────────────────────────────────────────

    def gain_skill_xp(self, skill, amount):
        """Add XP to a skill. Returns (levelled_up, new_level) tuple."""
        if skill not in self.skill_xp:
            return False, 1
        self.skill_xp[skill] += amount
        needed = self.skill_level[skill] * 80
        if self.skill_xp[skill] >= needed:
            self.skill_xp[skill] -= needed
            self.skill_level[skill] += 1
            return True, self.skill_level[skill]
        return False, self.skill_level[skill]

    def skill_bonus(self, skill):
        """Flat damage bonus from skill level (every level adds +2 dmg)."""
        return (self.skill_level.get(skill, 1) - 1) * 2

    def skill_xp_pct(self, skill):
        lvl    = self.skill_level.get(skill, 1)
        needed = lvl * 80
        return self.skill_xp.get(skill, 0) / needed if needed else 0.0

    def toggle_spell(self):
        spells = list(SPELL_DEFS.keys())
        idx    = spells.index(self.active_spell) if self.active_spell in spells else 0
        self.active_spell = spells[(idx+1) % len(spells)]
        return self.active_spell

    # ── HP helpers ────────────────────────────────────────────────────────────

    def shield_block_pct(self):
        """
        Fraction of damage blocked by a shield. Race bonus applied on top.
        """
        armor = self.equipped.get('armor')
        base = 0.0
        if armor:
            if 'block' in armor:
                base = min(0.75, armor['block'])
            elif 'def' in armor:
                base = min(0.40, armor['def'] / 40.0)
        try:
            from races import race_block_bonus
            base = min(0.90, base + race_block_bonus(self))
        except Exception:
            pass
        return base

    def take_damage(self, raw):
        """
        Damage pipeline:
          1. Subtract flat defense
          2. Apply shield block % (doble si está bloqueando activamente)
          3. Remaining damage cannot go below 1
        Returns actual HP lost (after all reductions).
        """
        after_def = max(0, raw - self.total_defense())
        block_pct = self.shield_block_pct()
        if self.blocking and block_pct > 0:
            block_pct = min(0.90, block_pct * 1.8)   # bloqueo activo = mucho más efectivo
        blocked   = int(after_def * block_pct)
        dmg       = max(1, after_def - blocked)
        self.hp  -= dmg
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False
        return dmg

    def hp_pct(self):  return self.hp / self.max_hp if self.max_hp else 0
    def mp_pct(self):  return self.mp / self.max_mp if self.max_mp else 0
    def xp_pct(self):  return self.xp / (self.level*100)
