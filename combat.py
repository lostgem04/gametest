"""
combat.py — Melee, bow, and spell combat.

Projectile resolution uses a simple ray-march along the player's
facing direction — no sprite, just instant travel checked each unit.
"""

import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, random, time
from player import SPELL_DEFS, ARROW_DEF

class Combat:
    def __init__(self, player):
        self.player = player

    # ── MELEE ─────────────────────────────────────────────────────────────────

    def attack_nearby_id(self, world):
        """Melee swing. Hits enemies OR animals. Returns (msg, killed_id or None)."""
        p = self.player

        if p.on_cooldown('melee'):
            rem = p.cooldown_remaining('melee')
            return f"Cooldown {rem:.1f}s…", None

        best, best_dist = None, p.weapon_melee_range()
        best_is_animal  = False

        # check enemies
        for e in world.enemies:
            if not e['alive']: continue
            dist = math.hypot(e['x']-p.x, e['y']-p.y)
            if dist < best_dist:
                ad   = math.atan2(e['y']-p.y, e['x']-p.x)
                diff = abs((ad-p.angle+math.pi)%(2*math.pi)-math.pi)
                if diff < math.pi/2:
                    best, best_dist, best_is_animal = e, dist, False

        # check animals (same arc)
        animal_mgr = getattr(world, 'animal_manager', None)
        if animal_mgr:
            for a in animal_mgr.animals:
                if not a.get('alive', True): continue
                dist = math.hypot(a['x']-p.x, a['y']-p.y)
                if dist < best_dist:
                    ad   = math.atan2(a['y']-p.y, a['x']-p.x)
                    diff = abs((ad-p.angle+math.pi)%(2*math.pi)-math.pi)
                    if diff < math.pi/2:
                        best, best_dist, best_is_animal = a, dist, True

        if best is None:
            return "No enemy in melee range.", None

        p.set_cooldown('melee')
        atk  = p.total_attack() + p.skill_bonus('melee')
        dmg  = max(1, atk + random.randint(-3, 3))

        # ── Animal hit (no counter-attack beyond proximity) ───────────────────
        if best_is_animal:
            best['hp'] -= dmg
            weap_name = (p.equipped.get('weapon') or {}).get('name', 'Puño')
            msg = f"{weap_name}: golpea {best['name']} -{dmg}HP"
            killed_id = None
            if best['hp'] <= 0:
                best['alive'] = False
                animal_mgr = getattr(world, 'animal_manager', None)
                loot_list  = animal_mgr.get_loot(best) if animal_mgr else []
                for loot_item in loot_list:
                    key = (int(best['x']), int(best['y']))
                    world.items.setdefault(key, []).append(loot_item)
                levelled = p.gain_xp(best.get('xp', 5))
                try:
                    from races import race_skill_mult
                    melee_mult = race_skill_mult(p, 'melee')
                except Exception:
                    melee_mult = 1.0
                sk_up, sk_lv = p.gain_skill_xp('melee', int(4 * melee_mult))
                msg = f"{best['name']} cazado! +{best.get('xp',5)}XP"
                if loot_list:
                    msg += f" [{', '.join(l['name'] for l in loot_list)}]"
                if levelled:
                    msg += f"  ★ Lv.{p.level}"
                if sk_up:
                    msg += f"  ⚔ Melee Lv.{sk_lv}!"
            return msg, None   # animals don't use killed_id for quest logic
        # silver weapon bonus vs vampires
        weap = p.equipped.get('weapon') or {}
        if weap.get('silver') and best.get('id') == 'vampire':
            dmg = int(dmg * 1.6)
        best['hp'] -= dmg
        weap_name = (p.equipped.get('weapon') or {}).get('name', 'Puño')
        msg  = f"{weap_name}: golpea {best['name']} -{dmg}HP"
        killed_id = None

        if best['hp'] <= 0:
            best['alive'] = False
            killed_id     = best['id']
            levelled      = p.gain_xp(best['xp'])
            # apply race skill XP multiplier
            try:
                from races import race_skill_mult
                melee_mult = race_skill_mult(p, 'melee')
            except Exception:
                melee_mult = 1.0
            sk_up, sk_lv  = p.gain_skill_xp('melee', int((best['xp'] // 2 + 5) * melee_mult))
            msg = f"{best['name']} slain! +{best['xp']}XP"
            if levelled:
                msg += f"  ★ LEVEL UP Lv.{p.level}"
            if sk_up:
                msg += f"  ⚔ Melee Lv.{sk_lv}!"
            return msg, killed_id

        try:
            from races import race_skill_mult
            melee_mult = race_skill_mult(p, 'melee')
        except Exception:
            melee_mult = 1.0
        p.gain_skill_xp('melee', int(3 * melee_mult))
        # counter-attack
        edm    = max(1, best['dmg'] + random.randint(-2, 2))
        actual = p.take_damage(edm)
        msg   += f"  {best['name']} hits -{actual}HP"
        return msg, killed_id

    # ── BOW ───────────────────────────────────────────────────────────────────

    def shoot_arrow(self, world):
        """Ranged arrow shot along player facing. Returns (msg, killed_id)."""
        p = self.player

        # ── require bow equipped ───────────────────────────────────────────────
        if not p.equipped.get('bow'):
            return "No bow equipped! (equip one from inventory)", None

        if p.arrows <= 0:
            return "No arrows!", None
        if p.on_cooldown('bow'):
            rem = p.cooldown_remaining('bow')
            return f"Bow cooldown {rem:.1f}s…", None

        p.arrows     -= 1
        p.set_cooldown('bow')

        hit, e, dist = self._ray_hit(world, ARROW_DEF['range'])
        if not hit:
            return f"Arrow flies into the dark… ({p.arrows} left)", None

        dmg       = max(1, p.arrow_damage() + p.skill_bonus('bow') + random.randint(-4, 4))
        e['hp']  -= dmg
        msg       = f"Arrow hits {e['name']} -{dmg}HP! ({p.arrows} left)"
        killed_id = None

        if e['hp'] <= 0:
            e['alive'] = False
            killed_id  = e['id']
            levelled   = p.gain_xp(e['xp'])
            try:
                from races import race_skill_mult
                bow_mult = race_skill_mult(p, 'bow')
            except Exception:
                bow_mult = 1.0
            sk_up, sk_lv = p.gain_skill_xp('bow', int((e['xp'] // 2 + 5) * bow_mult))
            msg = f"Arrow: {e['name']} slain! +{e['xp']}XP ({p.arrows} arrows left)"
            if levelled:
                msg += f"  ★ Lv.{p.level}"
            if sk_up:
                msg += f"  🏹 Bow Lv.{sk_lv}!"
        else:
            try:
                from races import race_skill_mult
                bow_mult = race_skill_mult(p, 'bow')
            except Exception:
                bow_mult = 1.0
            p.gain_skill_xp('bow', int(3 * bow_mult))

        return msg, killed_id

    # ── SPELLS ────────────────────────────────────────────────────────────────

    def cast_spell(self, world, spell_id=None):
        """Cast the player's active spell. Returns (msg, killed_ids list)."""
        p        = self.player
        spell_id = spell_id or p.active_spell
        spell    = SPELL_DEFS.get(spell_id)

        if not spell:
            return f"Unknown spell: {spell_id}", []

        # check spellbook equipped
        book = p.equipped.get('spellbook')
        if not book:
            return "No spellbook equipped! (equip one from inventory)", []

        if p.mp < spell['mp_cost']:
            return f"Not enough MP! (need {spell['mp_cost']}, have {p.mp})", []

        if p.on_cooldown(spell_id):
            rem = p.cooldown_remaining(spell_id)
            return f"{spell['name']} cooldown {rem:.1f}s…", []

        p.mp -= spell['mp_cost']
        p.set_cooldown(spell_id)

        dmg      = max(1, p.spell_power(spell_id) + p.skill_bonus('magic') + random.randint(-5, 5))
        killed   = []
        targets  = []

        if spell_id == 'lightning':
            # single target, longest range
            hit, e, dist = self._ray_hit(world, spell['range'])
            if hit:
                targets = [e]
            msg_prefix = f"Lightning bolt fires!"

        elif spell_id == 'fireball':
            # splash — hits primary ray target + any enemy in splash radius
            hit, e, dist = self._ray_hit(world, spell['range'])
            if hit:
                cx, cy = e['x'], e['y']
                targets = [en for en in world.enemies
                           if en['alive'] and
                           math.hypot(en['x']-cx, en['y']-cy) <= spell['splash']]
            elif dist < spell['range']:
                # hit a wall — splash at impact point
                cx = p.x + math.cos(p.angle)*dist
                cy = p.y + math.sin(p.angle)*dist
                targets = [en for en in world.enemies
                           if en['alive'] and
                           math.hypot(en['x']-cx, en['y']-cy) <= spell['splash']]
            msg_prefix = f"Fireball explodes!"

        killed_ids = []
        hit_names  = []
        for target in targets:
            target['hp'] -= dmg
            hit_names.append(target['name'])
            if target['hp'] <= 0:
                target['alive'] = False
                killed_ids.append(target['id'])
                p.gain_xp(target['xp'])
                try:
                    from races import race_skill_mult
                    magic_mult = race_skill_mult(p, 'magic')
                except Exception:
                    magic_mult = 1.0
                p.gain_skill_xp('magic', int((target['xp'] // 2 + 5) * magic_mult))
            else:
                try:
                    from races import race_skill_mult
                    magic_mult = race_skill_mult(p, 'magic')
                except Exception:
                    magic_mult = 1.0
                p.gain_skill_xp('magic', int(3 * magic_mult))

        if not targets:
            return f"{spell['name']}: no targets hit.", []

        names = ', '.join(set(hit_names))
        msg   = f"{msg_prefix} Hit: {names} -{dmg}HP each"
        if killed_ids:
            msg += f"  [{len(killed_ids)} slain!]"

        return msg, killed_ids

    # ── ray march helper ──────────────────────────────────────────────────────

    def _ray_hit(self, world, max_range):
        """
        March along player.angle in small steps.
        Returns (hit_enemy, enemy_dict, distance) or (False, None, max_range).
        """
        p    = self.player
        step = 0.25
        cx   = p.x
        cy   = p.y
        cos_a = math.cos(p.angle)
        sin_a = math.sin(p.angle)
        dist  = 0.0

        while dist < max_range:
            dist += step
            rx = cx + cos_a*dist
            ry = cy + sin_a*dist

            # hit wall?
            if world.is_solid(rx, ry):
                return False, None, dist

            # hit enemy?
            for e in world.enemies:
                if not e['alive']: continue
                if math.hypot(e['x']-rx, e['y']-ry) < 0.6:
                    return True, e, dist

        return False, None, max_range

    # ── ambient enemy attacks ─────────────────────────────────────────────────

    def enemy_attacks_player(self, world):
        p    = self.player
        msgs = []
        for e in world.enemies:
            if not e['alive']: continue
            if math.hypot(e['x']-p.x, e['y']-p.y) < 1.0:
                dmg    = max(1, e['dmg'] + random.randint(-1, 1))
                actual = p.take_damage(dmg)
                msgs.append(f"{e['name']} attacks! -{actual}HP")
        return msgs
