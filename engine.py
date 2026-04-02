"""engine.py — Main loop, input, world travel, NPC, quests, spells, bow,
               commerce (merchant shop), blacksmith forge, multiplayer ghosts."""

import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

import math, time, sys, select
from ui import (C_GOLD, C_GRAY, C_RED, C_GREEN, C_BLUE,
                C_ORANGE, C_PURPLE, C_CYAN, C_WHITE, fg)
from npc import (QuestLog, talk, accept_quest_if_pending, try_complete_quest,
                 shop_menu, shop_buy, shop_sell,
                 forge_menu, forge_order)

TURN_SPEED = 0.16
TICK_RATE  = 0.05

C_FIRE    = fg(220, 100,  20)
C_BOLT    = fg(200, 200,  60)
C_ARROW   = fg(200, 170,  80)
C_BUFF    = fg(100, 220, 220)
C_SHOP    = fg(220, 200,  60)
C_FORGE   = fg(220, 130,  40)


class Engine:
    def __init__(self, player, world_manager, combat, ui):
        self.player  = player
        self.wm      = world_manager
        self.combat  = combat
        self.ui      = ui
        self.running = True

        self.quest_log    = QuestLog()
        self._pending_cmd = None
        self._pending_time= 0.0
        self._talking_to  = None
        self._active_npc  = None   # NPC currently in commerce/forge mode

        self._last_enemy_tick = time.time()
        self._enemy_interval  = 0.55

        # per-world player positions (world_id → [x, y, angle])
        self._world_positions = {}

        # autosave cada 120 segundos
        self._autosave_interval = 120.0
        self._last_autosave     = time.time()

        # ── animation state ────────────────────────────────────────────────────
        self._anim_state      = 'idle'   # 'idle' | 'attack' | 'block'
        self._anim_until      = 0.0      # timestamp when anim ends
        self._anim_tick       = 0

        # ── multiplayer session (attached externally by main.py) ──────────────
        self._mp_session  = None   # MultiplayerSession | None
        self._world_name  = None
        self._player_name = None

        self.wm.current.reveal_around(player.x, player.y, radius=5)
        self.ui.log("Welcome to Arcane Abyss!", C_GOLD)
        self.ui.log("WASD mover  QE girar  K melee  R flecha  Z hechizo  F hablar", C_GRAY)
        self.ui.log("Pulsa / para escribir comandos de texto  |  H para ayuda", C_GRAY)

        # register text command callback
        self.ui.set_cmd_callback(self._handle_text_cmd)

    @property
    def world(self):
        return self.wm.current

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self, renderer, ui, read_key_fn):
        p = self.player

        while self.running:
            now = time.time()
            w   = self.world

            expired_msgs = p.tick_buffs()
            for m in expired_msgs:
                ui.log(m, C_BUFF)

            if now - self._last_enemy_tick > self._enemy_interval:
                w.tick_enemies(p)
                for m in self.combat.enemy_attacks_player(w):
                    ui.log(m, C_RED)
                # ── tick animals ──────────────────────────────────────────────
                if hasattr(w, 'animal_manager') and w.animal_manager:
                    w.animal_manager.tick(p)
                    for m in w.animal_manager.attack_player(p):
                        ui.log(m, C_RED)
                self._last_enemy_tick = now

            # ── multiplayer session tick ──────────────────────────────────────
            if self._mp_session:
                self._mp_session.set_world_id(self.wm.current_id)
                self._mp_session.tick(self.player)

            # ── autosave periódico ─────────────────────────────────────────────
            if now - self._last_autosave > self._autosave_interval:
                self._world_positions[self.wm.current_id] = [p.x, p.y, p.angle]
                if self._mp_session:
                    msg = self._mp_session.save_now(engine=self)
                else:
                    self._save_game()
                self._last_autosave = now
                ui.log("💾 Autosave…", C_GOLD)

            portal = w.portal_at(p.x, p.y)
            # portal ya no es automático — requiere ESPACIO (ver _handle_key)
            # guardamos referencia para el HUD de interacción

            w = self.world
            renderer.vw = ui.view_w
            renderer.vh = ui.view_h

            # ── inject ghost players for rendering ────────────────────────────
            if self._mp_session:
                w._ghost_players = self._mp_session.get_ghosts()
            else:
                w._ghost_players = []

            frame, sprite_buf = renderer.render_frame(p, w)

            hud = []
            ui.hud_crosshair(hud)
            self._draw_action_hud(hud, ui, w)
            ui.hud_buffs(hud, p)

            # tick animation state
            now2 = time.time()
            if now2 >= self._anim_until:
                self._anim_state = 'idle'
            p.blocking       = (self._anim_state == 'block')
            self._anim_tick += 1
            ui.hud_equipped_hand(hud, p, self._anim_state, self._anim_tick)

            if not p.alive:
                ui.hud_death(hud)

            ui.render_all(frame, hud, sprite_buf)

            key = read_key_fn(timeout=TICK_RATE)
            if key:
                # command input gets first pick
                if self.ui.handle_cmd_key(key):
                    continue   # command was submitted, skip key dispatch
                if not self.ui.cmd_mode:
                    self._handle_key(key.lower(), ui)

            if not p.alive:
                self._handle_death(ui)

    # ── action HUD ────────────────────────────────────────────────────────────

    def _draw_action_hud(self, hud, ui, w):
        p     = self.player
        npc   = w.npc_nearby(p.x, p.y, radius=1.8)
        item  = w.item_at(p.x, p.y)
        enemy = w.enemy_at(p.x, p.y, radius=1.5)

        armor       = p.equipped.get('armor')
        has_shield  = bool(armor and (armor.get('block', 0) > 0 or
                                      'shield' in armor.get('name', '').lower()))
        shield_str  = f"  B:🛡{int(p.shield_block_pct()*100)}%" if has_shield else ""

        portal = w.portal_at(p.x, p.y)
        if portal:
            target_id, _ = portal
            target_name  = target_id.replace('world_', '').replace('_', ' ').title()
            ui.hud_interact(hud, f"ESPACIO: Entrar portal → {target_name}")
            return   # portal hint takes priority

        if npc:
            role = npc.get('role', 'quest')
            if role == 'merchant':
                ui.hud_interact(hud, f"F: Shop {npc['name']}  /buy <n>  /sell <n>")
            elif role == 'blacksmith':
                ui.hud_interact(hud, f"F: Forge with {npc['name']}")
            else:
                ui.hud_interact(hud, f"F: Talk to {npc['name']}")
        elif item:
            ui.hud_interact(hud, f"T: Take {item['name']}")
        elif enemy and enemy['alive']:
            bow_ok  = '✓' if p.equipped.get('bow') else '✗'
            book_ok = '✓' if p.equipped.get('spellbook') else '✗'
            ui.hud_interact(hud, f"K:Melee  R:{bow_ok}Bow({p.arrows})  Z:{book_ok}{p.active_spell}{shield_str}")

    # ── key dispatch ─────────────────────────────────────────────────────────

    def _handle_key(self, key, ui):
        p = self.player
        w = self.world

        # movement
        if   key == 'w': p.move(1) or ui.log("Blocked.", C_GRAY)
        elif key == 's': p.move(-1)
        elif key == 'a': p.move(0,-1)
        elif key == 'd': p.move(0, 1)
        elif key == 'q': p.rotate(-TURN_SPEED)
        elif key == 'e': p.rotate( TURN_SPEED)

        # ── portal ────────────────────────────────────────────────────────────
        elif key == ' ':
            portal = w.portal_at(p.x, p.y)
            if portal:
                target_id, spawn_pos = portal
                # save current position before leaving
                self._world_positions[self.wm.current_id] = [p.x, p.y, p.angle]
                new_w, sp = self.wm.travel(target_id, spawn_pos)
                p.x, p.y  = sp[0]+0.5, sp[1]+0.5
                p.world   = new_w
                new_w.reveal_around(p.x, p.y, radius=5)
                ui.log(f"✦ Entrado: {new_w.name}", C_PURPLE)
                for m in self.quest_log.update_reach(target_id):
                    ui.log(m, C_GOLD)
                time.sleep(0.2)
            else:
                ui.log("No hay portal aquí.", C_GRAY)

        # ── melee ─────────────────────────────────────────────────────────────
        elif key == 'k':
            if p.alive:
                msg, kid = self.combat.attack_nearby_id(w)
                col = C_ORANGE if ('slain' in msg or 'LEVEL' in msg) else C_RED
                ui.log(msg, col)
                self._handle_kill(kid, ui)
                if 'Cooldown' not in msg:
                    self._anim_state = 'attack'
                    self._anim_until = time.time() + 0.18

        # ── bow ───────────────────────────────────────────────────────────────
        elif key == 'r':
            if p.alive:
                msg, kid = self.combat.shoot_arrow(w)
                col = C_ARROW if kid or 'flies' in msg else C_RED
                ui.log(msg, col)
                self._handle_kill(kid, ui)
                if 'cooldown' not in msg and 'No' not in msg:
                    self._anim_state = 'attack'
                    self._anim_until = time.time() + 0.20

        # ── spell ─────────────────────────────────────────────────────────────
        elif key == 'z':
            if p.alive:
                msg, kids = self.combat.cast_spell(w)
                col = C_FIRE if p.active_spell=='fireball' else C_BOLT
                ui.log(msg, col)
                for kid in kids:
                    self._handle_kill(kid, ui)
                if 'cooldown' not in msg and 'Not enough' not in msg and 'No spell' not in msg:
                    self._anim_state = 'attack'
                    self._anim_until = time.time() + 0.25

        # ── cycle spell ───────────────────────────────────────────────────────
        elif key == 'c':
            new = p.toggle_spell()
            ui.log(f"Active spell: {new}", C_PURPLE)

        # ── shield block ──────────────────────────────────────────────────────
        elif key == 'b':
            armor = p.equipped.get('armor')
            if armor and (armor.get('block', 0) > 0 or
                          'shield' in armor.get('name', '').lower()):
                block_pct = int(p.shield_block_pct() * 100)
                self._anim_state = 'block'
                self._anim_until = time.time() + 0.50
                ui.log(f"🛡 Escudo alzado — bloquea {block_pct}% daño por 0.5s", C_BLUE)
            else:
                ui.log("No tienes escudo equipado.", C_GRAY)

        # ── take item ─────────────────────────────────────────────────────────
        elif key == 't':
            item = w.item_at(p.x, p.y)
            if item:
                if p.pick_up(item):
                    w.remove_item(p.x, p.y, item)
                    ui.log(f"Picked up {item['name']}!", C_GREEN)
                    for m in self.quest_log.update_collect(item['id']):
                        ui.log(m, C_GOLD)
                else:
                    ui.log("Inventory full!", C_RED)
            else:
                ui.log("Nothing here.", C_GRAY)

        # ── NPC talk / shop / forge ────────────────────────────────────────────
        elif key == 'f':
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if npc:
                role = npc.get('role', 'quest')

                if role == 'merchant':
                    if npc.get('_shop_open'):
                        # Second F → show shop menu
                        npc['_shop_open'] = False
                        for l in shop_menu(npc):
                            ui.log(l, C_SHOP)
                        self._active_npc = npc
                        self._pending_cmd  = 'shop'
                        self._pending_time = time.time()
                        ui.log("B<n>=buy  S<n>=sell  (then press digit)", C_GRAY)
                    else:
                        # First F → greet
                        self._active_npc = npc
                        reward = try_complete_quest(npc, self.quest_log, p)
                        if reward: ui.log(reward, C_GOLD)
                        for l in talk(npc, self.quest_log, p):
                            ui.log(l, C_CYAN)

                elif role == 'blacksmith':
                    if npc.get('_forge_open'):
                        npc['_forge_open'] = False
                        for l in forge_menu(npc, p):
                            ui.log(l, C_FORGE)
                        self._active_npc = npc
                        self._pending_cmd  = 'forge'
                        self._pending_time = time.time()
                        ui.log("O<n>=order item  (then press digit)", C_GRAY)
                    else:
                        self._active_npc = npc
                        for l in talk(npc, self.quest_log, p):
                            ui.log(l, C_CYAN)

                else:
                    # quest NPC
                    if self._talking_to == npc.get('id') and npc.get('_pending_accept'):
                        result = accept_quest_if_pending(npc, self.quest_log, p)
                        if result: ui.log(result, C_GOLD)
                        reward = try_complete_quest(npc, self.quest_log, p)
                        if reward: ui.log(reward, C_GOLD)
                        self._talking_to = None
                    else:
                        self._talking_to = npc.get('id')
                        reward = try_complete_quest(npc, self.quest_log, p)
                        if reward: ui.log(reward, C_GOLD)
                        for l in talk(npc, self.quest_log, p):
                            ui.log(l, C_CYAN)
            else:
                ui.log("No one nearby.", C_GRAY)

        # ── shop: buy ──────────────────────────────────────────────────────────
        elif key == 'b' and self._pending_cmd in ('shop', None):
            if w.npc_nearby(p.x, p.y, radius=1.8):
                self._pending_cmd  = 'shop_buy'
                self._pending_time = time.time()
                ui.log("Buy which item? (press 0-9)", C_SHOP)

        # ── shop: sell ─────────────────────────────────────────────────────────
        elif key == 's' and self._pending_cmd in ('shop', None):
            # only intercept if we're near a merchant
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if npc and npc.get('role') == 'merchant':
                self._pending_cmd  = 'shop_sell'
                self._pending_time = time.time()
                ui.log("Sell inventory slot? (press 0-9)", C_SHOP)
            else:
                # normal movement (backward)
                p.move(-1)

        # ── forge: order ──────────────────────────────────────────────────────
        elif key == 'o':
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if npc and npc.get('role') == 'blacksmith':
                self._pending_cmd  = 'forge_order'
                self._pending_time = time.time()
                ui.log("Order which item? (press 0-9)", C_FORGE)

        # ── digit handler for pending commands ────────────────────────────────
        elif key.isdigit() and self._pending_cmd:
            n = int(key)
            cmd = self._pending_cmd
            self._pending_cmd = None

            if cmd in ('use', 'u'):
                result = p.use_item(n)
                col = (C_BUFF  if 'active' in result else
                       C_GREEN if 'Healed' in result or 'Restored' in result else
                       C_WHITE)
                ui.log(result, col)

            elif cmd == 'shop_buy':
                npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
                if npc and npc.get('role') == 'merchant':
                    msg = shop_buy(npc, p, n)
                    ui.log(msg, C_SHOP)
                else:
                    ui.log("No merchant nearby.", C_GRAY)

            elif cmd == 'shop_sell':
                npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
                if npc and npc.get('role') == 'merchant':
                    msg = shop_sell(npc, p, n)
                    ui.log(msg, C_SHOP)
                else:
                    ui.log("No merchant nearby.", C_GRAY)

            elif cmd == 'forge_order':
                npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
                if npc and npc.get('role') == 'blacksmith':
                    msg = forge_order(npc, p, n)
                    ui.log(msg, C_FORGE)
                else:
                    ui.log("No blacksmith nearby.", C_GRAY)

        # ── mine ore vein ─────────────────────────────────────────────────────
        elif key == 'm':
            item, msg = w.mine_vein(p.x, p.y, p)
            if item:
                if p.pick_up(item):
                    ui.log(msg, C_FORGE)
                else:
                    ui.log("Inventario lleno.", C_RED)
                    k2 = (int(p.x), int(p.y))
                    w.items.setdefault(k2, []).append(item)
            else:
                ui.log(msg, C_GRAY)

        # ── chop tree ─────────────────────────────────────────────────────────
        elif key == 'n':
            item, msg = w.chop_tree(p.x, p.y, p)
            if item:
                if p.pick_up(item):
                    ui.log(msg, C_GREEN)
                else:
                    ui.log("Inventario lleno.", C_RED)
                    k2 = (int(p.x), int(p.y))
                    w.items.setdefault(k2, []).append(item)
            else:
                ui.log(msg, C_GRAY)
            self._pending_cmd  = 'use'
            self._pending_time = time.time()
            ui.log("Use item: press 0-9", C_BLUE)

        # ── quest log ─────────────────────────────────────────────────────────
        elif key == 'j':
            for l in ["── Quest Log ──"] + self.quest_log.summary():
                ui.log(l, C_GOLD)

        # ── help ──────────────────────────────────────────────────────────────
        elif key == 'h':
            ui.draw_help()
            while not select.select([sys.stdin],[],[],0.05)[0]: pass
            try: sys.stdin.read(1)
            except: pass

        elif key in ('x','\x03','\x1b'):
            if not p.alive:
                pass   # muerte gestionada por _handle_death en el loop
            else:
                # save current position before autosaving
                self._world_positions[self.wm.current_id] = [self.player.x, self.player.y, self.player.angle]
                msg = self._save_game()   # autosave on exit
                ui.log(msg, C_GOLD)
                self.running = False

        # expire pending
        if self._pending_cmd and time.time()-self._pending_time > 5:
            self._pending_cmd = None
            self._active_npc  = None
            ui.log("Cancelled.", C_GRAY)

        # passive regen
        if p.alive and p.steps > 0 and p.steps % 15 == 0:
            if p.hp < p.max_hp: p.hp = min(p.hp+1, p.max_hp)
            if p.mp < p.max_mp: p.mp = min(p.mp+1, p.max_mp)

    def _handle_kill(self, killed_id, ui):
        if not killed_id:
            return
        for m in self.quest_log.update_kill(killed_id):
            ui.log(m, C_GOLD)
        # drop loot from the dead enemy
        w = self.world
        dead_e = next((e for e in w.enemies if e.get('id') == killed_id and not e['alive']), None)
        if dead_e:
            drops = w.drop_loot(dead_e)
            if drops:
                ex = int(dead_e['x']); ey = int(dead_e['y'])
                for drop in drops:
                    # place near corpse
                    placed = False
                    for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
                        key = (ex+dx, ey+dy)
                        if w.walkable(ex+dx, ey+dy):
                            w.items.setdefault(key, []).append(drop)
                            placed = True
                            break
                loot_names = ', '.join(d['name'] for d in drops)
                ui.log(f"  💀 Loot: {loot_names}", C_GOLD)
            # announce boss kill
            if dead_e.get('boss'):
                ui.log(f"  ★★★ BOSS DERROTADO: {dead_e['name']} ★★★", C_GOLD)

    # ── death & respawn ───────────────────────────────────────────────────────

    def _handle_death(self, ui):
        """
        Muerte del jugador:
          1. Tira TODO el inventario + equipamiento en el suelo del mundo actual
          2. Baja 1 nivel (mínimo 1) y resetea XP a 0
          3. Reduce stats que escalan con nivel (max_hp, max_mp, attack, defense)
          4. Viaja al mundo inicial (world_dungeon) y pone al jugador en spawn
          5. Restaura HP/MP al nuevo máximo
          6. Guarda la partida para que el drop persista
        """
        p = self.player
        w = self.world

        # ── mostrar pantalla de muerte hasta que el jugador pulse una tecla ──
        ui.log("☠  Has muerto. Tus recursos yacen donde caíste…", C_RED)
        ui.log("   Presiona cualquier tecla para respawnear.", C_GRAY)
        # Esperar input antes de procesar (el loop principal llama esto cada frame)
        # Solo procesamos la muerte UNA vez — marcamos con flag para no repetir
        if getattr(p, '_death_processed', False):
            return
        p._death_processed = True

        # ── 1. Tirar inventario completo en el suelo ──────────────────────────
        drop_x = int(p.x)
        drop_y = int(p.y)
        # Buscar celdas caminables cercanas para dispersar el loot
        offsets = [(0,0),(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]
        drop_slots = []
        for dx, dy in offsets:
            cx, cy = drop_x + dx, drop_y + dy
            if w.walkable(cx, cy):
                drop_slots.append((cx, cy))
            if len(drop_slots) >= 5:
                break

        all_drops = list(p.inventory)

        # También tirar equipamiento
        for slot, item in p.equipped.items():
            if item is not None:
                all_drops.append(item)
        p.equipped = {'weapon': None, 'armor': None, 'bow': None, 'spellbook': None}
        p.inventory = []

        # Tirar oro como item
        if p.gold > 0:
            all_drops.append({'id': 'gold', 'name': f'Gold Coins ({p.gold})',
                               'type': 'gold', 'val': p.gold})
            p.gold = 0

        # Dispersar drops entre las celdas disponibles
        for i, item in enumerate(all_drops):
            if drop_slots:
                slot_key = drop_slots[i % len(drop_slots)]
            else:
                slot_key = (drop_x, drop_y)
            w.items.setdefault(slot_key, []).append(item)

        drop_count = len(all_drops)

        # ── 2. Bajar 1 nivel ──────────────────────────────────────────────────
        old_level = p.level
        if p.level > 1:
            p.level  -= 1
            p.xp      = 0
            # Revertir los bonus de stat que se dan al subir de nivel
            # (gain_xp añade: +20 max_hp, +10 max_mp, +3 attack, +1 defense)
            p.max_hp  = max(10,  p.max_hp  - 20)
            p.max_mp  = max(0,   p.max_mp  - 10)
            p.attack  = max(1,   p.attack  - 3)
            p.defense = max(0,   p.defense - 1)
            ui.log(f"   ▼ Nivel {old_level} → {p.level}  (perdiste 1 nivel)", C_RED)
        else:
            # Ya en nivel 1: solo pierdes XP
            p.xp = 0
            ui.log("   Nivel 1 — no puedes bajar más.", C_GRAY)

        # ── 3. Respawnear en el mundo inicial ─────────────────────────────────
        start_world = 'world_dungeon'
        spawn_x, spawn_y = 1.5, 1.5

        if self.wm.current_id != start_world:
            new_w, _ = self.wm.travel(start_world, (1, 1))
            p.world  = new_w
        else:
            new_w = w

        p.x, p.y = spawn_x, spawn_y
        p.angle  = 0.0
        new_w.reveal_around(p.x, p.y, radius=5)

        # ── 4. Restaurar HP/MP al máximo actual (post-penalización) ──────────
        p.hp    = p.max_hp
        p.mp    = p.max_mp
        p.alive = True
        p._death_processed = False   # reset flag para próxima muerte

        # ── 5. Notificar al sistema MP si está activo ─────────────────────────
        if self._mp_session:
            self._mp_session.notify_death()

        # ── 6. Guardar (para que el drop persista en disco) ───────────────────
        self._world_positions[start_world] = [p.x, p.y, p.angle]
        if self._mp_session:
            self._mp_session.save_now(engine=self)
        else:
            self._save_game()

        ui.log(f"☀  Respawn en {new_w.name} — {drop_count} objeto(s) tirados donde moriste.", C_GOLD)
        if drop_count > 0:
            ui.log(f"   Vuelve a {w.name} para recuperar tu equipo.", C_CYAN)

    # ── save / load ───────────────────────────────────────────────────────────

    def _save_game(self):
        """
        Save everything needed to fully restore a session:
        - Player stats, inventory, equipment, skills, position per world
        - Per-world state: enemy HP/alive, floor items, ore vein charges,
          revealed tiles, tree charges
        - Quest log
        """
        import json, os
        p = self.player

        # ── snapshot every loaded world ────────────────────────────────────
        worlds_snapshot = {}
        for wid, w in self.wm._worlds.items():
            # enemies: save position + hp + alive status
            enemies_snap = []
            for e in w.enemies:
                enemies_snap.append({
                    'id':    e.get('id', ''),
                    'x':     e['x'],
                    'y':     e['y'],
                    'hp':    e['hp'],
                    'alive': e['alive'],
                })

            # floor items: {tile_key: [item, ...]}
            items_snap = {}
            for (tx, ty), item_list in w.items.items():
                items_snap[f'{tx},{ty}'] = list(item_list)

            # ore veins: {tile_key: charges}
            veins_snap = {}
            for (vx, vy), vein in getattr(w, 'ore_veins', {}).items():
                veins_snap[f'{vx},{vy}'] = vein['charges']

            # trees: {tile_key: charges}
            trees_snap = {}
            for (tx2, ty2), tree in getattr(w, 'trees', {}).items():
                trees_snap[f'{tx2},{ty2}'] = tree.get('charges', 0)

            # revealed map rows (list of list of bool → compact as hex strings)
            revealed_snap = []
            for row in w.revealed:
                # encode each row as a hex bitmask string for compactness
                bits = 0
                for bit in reversed(row):
                    bits = (bits << 1) | (1 if bit else 0)
                revealed_snap.append(format(bits, 'x'))

            worlds_snapshot[wid] = {
                'enemies':  enemies_snap,
                'items':    items_snap,
                'veins':    veins_snap,
                'trees':    trees_snap,
                'revealed': revealed_snap,
            }

        # ── player position per world ──────────────────────────────────────
        # current world position is always up-to-date on the player object
        player_positions = getattr(self, '_world_positions', {})
        player_positions[self.wm.current_id] = [p.x, p.y, p.angle]

        save_data = {
            'version':    3,
            'world_id':   self.wm.current_id,
            'positions':  player_positions,   # pos per world
            # ── player ──────────────────────────────────────────────────────
            'hp':         p.hp,  'max_hp':    p.max_hp,
            'mp':         p.mp,  'max_mp':    p.max_mp,
            'xp':         p.xp,  'level':     p.level,
            'gold':       p.gold,
            'attack':     p.attack,
            'defense':    p.defense,
            'arrows':     p.arrows,
            'active_spell': p.active_spell,
            'steps':      p.steps,
            'inventory':  p.inventory,
            'equipped':   {k: v for k, v in p.equipped.items()},
            'skill_xp':   p.skill_xp,
            'skill_level':p.skill_level,
            # ── quests ──────────────────────────────────────────────────────
            'quests_active':    {k: dict(v) for k, v in self.quest_log.active.items()},
            'quests_completed': list(self.quest_log.completed),
            # ── worlds ──────────────────────────────────────────────────────
            'worlds':     worlds_snapshot,
        }

        path = os.path.expanduser('~/.arcane_abyss_save.json')
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            slot_info = (f"Lv.{p.level}  {self.wm.current_id.replace('world_','').title()}"
                         f"  ({p.x:.1f},{p.y:.1f})")
            return f"✔ Partida guardada — {slot_info}"
        except Exception as e:
            return f"✘ Error al guardar: {e}"

    def _load_game(self):
        """
        Restore full game state from save file.
        Restores world items, enemy states, revealed maps, etc.
        """
        import json, os
        path = os.path.expanduser('~/.arcane_abyss_save.json')
        if not os.path.exists(path):
            return "No hay partida guardada."
        try:
            with open(path, encoding='utf-8') as f:
                d = json.load(f)

            p        = self.player
            world_id = d.get('world_id', 'world_dungeon')
            version  = d.get('version', 1)

            # ── travel to saved world ──────────────────────────────────────
            new_w, _ = self.wm.travel(world_id, (1, 1))

            # ── restore per-world state ────────────────────────────────────
            worlds_data = d.get('worlds', {})
            for wid, wdata in worlds_data.items():
                # ensure world is loaded
                self.wm._load(wid)
                w = self.wm._worlds[wid]

                # restore enemies (match by index for deterministic worlds)
                en_snaps = wdata.get('enemies', [])
                for i, snap in enumerate(en_snaps):
                    if i < len(w.enemies):
                        w.enemies[i]['x']     = snap['x']
                        w.enemies[i]['y']      = snap['y']
                        w.enemies[i]['hp']     = snap['hp']
                        w.enemies[i]['alive']  = snap['alive']

                # restore floor items
                w.items.clear()
                for key_str, item_list in wdata.get('items', {}).items():
                    tx, ty = map(int, key_str.split(','))
                    w.items[(tx, ty)] = list(item_list)

                # restore ore vein charges
                for key_str, charges in wdata.get('veins', {}).items():
                    vx, vy = map(int, key_str.split(','))
                    if (vx, vy) in getattr(w, 'ore_veins', {}):
                        w.ore_veins[(vx, vy)]['charges'] = charges

                # restore tree charges
                for key_str, charges in wdata.get('trees', {}).items():
                    tx2, ty2 = map(int, key_str.split(','))
                    if (tx2, ty2) in getattr(w, 'trees', {}):
                        w.trees[(tx2, ty2)]['charges'] = charges

                # restore revealed map
                revealed_rows = wdata.get('revealed', [])
                for ry, row_hex in enumerate(revealed_rows):
                    if ry >= len(w.revealed):
                        break
                    bits = int(row_hex, 16) if row_hex else 0
                    row  = w.revealed[ry]
                    for rx in range(len(row)):
                        row[rx] = bool((bits >> rx) & 1)

            # ── restore player position (per-world) ────────────────────────
            positions = d.get('positions', {})
            self._world_positions = dict(positions)

            if version >= 3 and world_id in positions:
                px, py, pangle = positions[world_id]
            else:
                # legacy single pos fallback
                pos = d.get('pos', [1.5, 1.5, 0.0])
                px, py, pangle = pos[0], pos[1], pos[2]

            p.x, p.y, p.angle = px, py, pangle
            p.world = new_w

            # ── restore stats ──────────────────────────────────────────────
            p.hp  = d['hp'];   p.max_hp = d['max_hp']
            p.mp  = d['mp'];   p.max_mp = d['max_mp']
            p.xp  = d['xp'];   p.level  = d['level']
            p.gold    = d['gold']
            p.attack  = d['attack'];  p.defense = d['defense']
            p.arrows  = d['arrows']
            p.active_spell = d.get('active_spell', 'fireball')
            p.steps   = d.get('steps', 0)
            p.inventory  = d.get('inventory', [])
            p.equipped   = d.get('equipped',
                                  {'weapon': None, 'armor': None,
                                   'bow': None, 'spellbook': None})
            p.skill_xp    = d.get('skill_xp',   {'melee': 0, 'bow': 0, 'magic': 0})
            p.skill_level = d.get('skill_level', {'melee': 1, 'bow': 1, 'magic': 1})

            # ── restore quests ─────────────────────────────────────────────
            self.quest_log.active    = {k: dict(v) for k, v in
                                        d.get('quests_active', {}).items()}
            self.quest_log.completed = set(d.get('quests_completed', []))

            new_w.reveal_around(p.x, p.y, radius=5)
            world_label = world_id.replace('world_', '').replace('_', ' ').title()
            return (f"✔ Partida cargada — Lv.{p.level}  {world_label}"
                    f"  ({p.x:.1f},{p.y:.1f})")

        except Exception as e:
            import traceback
            return f"✘ Error al cargar: {e}\n{traceback.format_exc()}"

    def _handle_text_cmd(self, raw):
        """Parse and execute a free-text command from the log input line."""
        ui = self.ui
        p  = self.player
        w  = self.world
        parts = raw.strip().lower().split()
        if not parts:
            return
        cmd  = parts[0]
        args = parts[1:]

        # ── look ─────────────────────────────────────────────────────────────
        if cmd == 'look':
            npc   = w.npc_nearby(p.x, p.y, radius=2.0)
            item  = w.item_at(p.x, p.y)
            enemy = w.enemy_at(p.x, p.y, radius=2.5)
            alive = [e for e in w.enemies if e['alive']]
            ui.log(f"[{w.name}] Pos ({p.x:.1f},{p.y:.1f})  {w.time_name()}", C_CYAN)
            ui.log(f"  {len(alive)} enemies nearby.", C_GRAY)
            if npc:
                ui.log(f"  NPC: {npc['name']} — press F to talk.", C_CYAN)
            if item:
                ui.log(f"  Item on floor: {item['name']} — press T to take.", C_GREEN)
            if enemy:
                ui.log(f"  Enemy close: {enemy['name']}  HP:{enemy['hp']}/{enemy['max_hp']}", C_RED)
            if not npc and not item and not enemy:
                ui.log("  Nothing of note nearby.", C_GRAY)

        # ── cast ─────────────────────────────────────────────────────────────
        elif cmd == 'cast':
            spell = args[0] if args else p.active_spell
            if spell not in ('fireball', 'lightning'):
                ui.log(f"Unknown spell: {spell}. Try: fireball, lightning", C_RED)
                return
            p.active_spell = spell
            msg, kids = self.combat.cast_spell(w, spell)
            col = C_FIRE if spell == 'fireball' else C_BOLT
            ui.log(msg, col)
            for kid in kids:
                self._handle_kill(kid, ui)

        # ── get / take ────────────────────────────────────────────────────────
        elif cmd in ('get', 'take'):
            item = w.item_at(p.x, p.y)
            if item:
                if p.pick_up(item):
                    w.remove_item(p.x, p.y, item)
                    ui.log(f"Picked up {item['name']}!", C_GREEN)
                    for m in self.quest_log.update_collect(item['id']):
                        ui.log(m, C_GOLD)
                else:
                    ui.log("Inventory full!", C_RED)
            else:
                ui.log("Nothing on the floor here.", C_GRAY)

        # ── drop ─────────────────────────────────────────────────────────────
        elif cmd == 'drop':
            if not args or not args[0].isdigit():
                ui.log("Usage: drop <slot number>", C_GRAY)
                return
            idx = int(args[0])
            if idx < 0 or idx >= len(p.inventory):
                ui.log("Invalid slot.", C_RED)
                return
            item = p.inventory.pop(idx)
            # place on current tile
            key = (int(p.x), int(p.y))
            w.items.setdefault(key, []).append(item)
            ui.log(f"Dropped {item['name']}.", C_GRAY)

        # ── equip ─────────────────────────────────────────────────────────────
        elif cmd == 'equip':
            if not args or not args[0].isdigit():
                ui.log("Usage: equip <slot number>", C_GRAY)
                return
            msg = p.use_item(int(args[0]))
            ui.log(msg, C_GREEN if 'Equipped' in msg else C_RED)

        # ── use ───────────────────────────────────────────────────────────────
        elif cmd == 'use':
            if not args or not args[0].isdigit():
                ui.log("Usage: use <slot number>", C_GRAY)
                return
            result = p.use_item(int(args[0]))
            col = (C_BUFF  if 'active' in result else
                   C_GREEN if 'Healed' in result or 'Restored' in result else
                   C_WHITE)
            ui.log(result, col)

        # ── attack / kill ─────────────────────────────────────────────────────
        elif cmd in ('attack', 'kill', 'melee', 'strike'):
            if p.alive:
                msg, kid = self.combat.attack_nearby_id(w)
                col = C_ORANGE if ('slain' in msg or 'LEVEL' in msg) else C_RED
                ui.log(msg, col)
                self._handle_kill(kid, ui)

        # ── shoot ─────────────────────────────────────────────────────────────
        elif cmd in ('shoot', 'arrow', 'fire'):
            if p.alive:
                msg, kid = self.combat.shoot_arrow(w)
                col = C_ARROW if kid or 'flies' in msg else C_RED
                ui.log(msg, col)
                self._handle_kill(kid, ui)

        # ── talk ──────────────────────────────────────────────────────────────
        elif cmd == 'talk':
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if npc:
                reward = try_complete_quest(npc, self.quest_log, p)
                if reward: ui.log(reward, C_GOLD)
                for l in talk(npc, self.quest_log, p):
                    ui.log(l, C_CYAN)
            else:
                ui.log("No one nearby to talk to.", C_GRAY)

        # ── quest / quests ────────────────────────────────────────────────────
        elif cmd in ('quest', 'quests', 'journal', 'log'):
            for l in ["── Quest Log ──"] + self.quest_log.summary():
                ui.log(l, C_GOLD)

        # ── shop (text interface) ─────────────────────────────────────────────
        elif cmd == 'shop':
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if not npc or npc.get('role') != 'merchant':
                ui.log("No hay un mercader cerca.", C_GRAY)
                return
            self._active_npc = npc
            for l in shop_menu(npc):
                ui.log(l, C_SHOP)
            ui.log("Escribe: buy <n> para comprar  |  sell <n> para vender", C_GRAY)

        elif cmd == 'buy':
            npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
            if not npc or npc.get('role') != 'merchant':
                ui.log("No hay un mercader activo. Escribe 'shop' primero.", C_GRAY)
                return
            if not args or not args[0].isdigit():
                ui.log("Uso: buy <número>  (ej: buy 2)", C_GRAY)
                return
            msg = shop_buy(npc, p, int(args[0]))
            ui.log(msg, C_SHOP)

        elif cmd == 'sell':
            npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
            if not npc or npc.get('role') != 'merchant':
                ui.log("No hay un mercader activo. Escribe 'shop' primero.", C_GRAY)
                return
            if not args or not args[0].isdigit():
                # show inventory to help user pick
                ui.log("Uso: sell <slot>  —  Inventario:", C_GRAY)
                for i, it in enumerate(p.inventory):
                    ui.log(f"  [{i}] {it['name']}", C_WHITE)
                return
            msg = shop_sell(npc, p, int(args[0]))
            ui.log(msg, C_SHOP)

        elif cmd == 'forge':
            npc = w.npc_nearby(p.x, p.y, radius=1.8)
            if not npc or npc.get('role') != 'blacksmith':
                ui.log("No hay un herrero cerca.", C_GRAY)
                return
            self._active_npc = npc
            for l in forge_menu(npc, p):
                ui.log(l, C_FORGE)
            ui.log("Escribe: order <n> para encargar", C_GRAY)

        elif cmd == 'order':
            npc = self._active_npc or w.npc_nearby(p.x, p.y, radius=1.8)
            if not npc or npc.get('role') != 'blacksmith':
                ui.log("No hay un herrero activo. Escribe 'forge' primero.", C_GRAY)
                return
            if not args or not args[0].isdigit():
                ui.log("Uso: order <número>", C_GRAY)
                return
            msg = forge_order(npc, p, int(args[0]))
            ui.log(msg, C_FORGE)
            ui.log(f"── Stats ── Lv.{p.level}  XP:{p.xp}/{p.level*100}", C_GOLD)
            ui.log(f"  HP:{p.hp}/{p.max_hp}  MP:{p.mp}/{p.max_mp}  Gold:{p.gold}", C_WHITE)
            ui.log(f"  ATK:{p.total_attack()}  DEF:{p.total_defense()}  Steps:{p.steps}", C_WHITE)
            ui.log(f"  Arrows:{p.arrows}  Spell:{p.active_spell}", C_ORANGE)

        # ── skills ────────────────────────────────────────────────────────────
        elif cmd == 'skills':
            ui.log("── Habilidades ──", C_GOLD)
            for sk, label in (('melee', '⚔ Melee'), ('bow', '🏹 Arco'), ('magic', '✨ Magia')):
                lv  = p.skill_level.get(sk, 1)
                xp  = p.skill_xp.get(sk, 0)
                nxt = lv * 80
                ui.log(f"  {label} Lv.{lv}  XP: {xp}/{nxt}", C_WHITE)

        # ── inv / inventory ───────────────────────────────────────────────────
        elif cmd in ('inv', 'inventory', 'bag'):
            if not p.inventory:
                ui.log("Inventory is empty.", C_GRAY)
            else:
                ui.log(f"── Inventory ({len(p.inventory)}/20) ──", C_PURPLE)
                for i, item in enumerate(p.inventory):
                    t = item.get('type','')
                    ui.log(f"  [{i}] {item['name']}  ({t})", C_WHITE)

        # ── map ───────────────────────────────────────────────────────────────
        elif cmd == 'map':
            alive = sum(1 for e in w.enemies if e['alive'])
            ui.log(f"── {w.name} ── ({w.time_name()})", C_CYAN)
            ui.log(f"  Pos ({p.x:.1f},{p.y:.1f})  Enemies alive: {alive}", C_WHITE)
            ui.log(f"  Items on map: {sum(len(v) for v in w.items.values())}", C_GOLD)

        # ── heal ─────────────────────────────────────────────────────────────
        elif cmd == 'heal':
            for i, item in enumerate(p.inventory):
                if item.get('type') == 'consumable' and 'hp' in item:
                    msg = p.use_item(i)
                    ui.log(msg, C_GREEN)
                    return
            ui.log("No HP potions in inventory.", C_RED)

        # ── mana ─────────────────────────────────────────────────────────────
        elif cmd == 'mana':
            for i, item in enumerate(p.inventory):
                if item.get('type') == 'consumable' and 'mp' in item:
                    msg = p.use_item(i)
                    ui.log(msg, C_BLUE)
                    return
            ui.log("No MP potions in inventory.", C_RED)

        # ── mine ─────────────────────────────────────────────────────────────
        elif cmd in ('mine', 'minar'):
            item, msg = w.mine_vein(p.x, p.y, p)
            if item:
                if p.pick_up(item):
                    ui.log(msg, C_FORGE)
                else:
                    ui.log("Inventario lleno — mineral dejado en el suelo.", C_RED)
                    key = (int(p.x), int(p.y))
                    w.items.setdefault(key, []).append(item)
            else:
                ui.log(msg, C_GRAY)

        # ── chop ─────────────────────────────────────────────────────────────
        elif cmd in ('chop', 'talar', 'axe'):
            item, msg = w.chop_tree(p.x, p.y, p)
            if item:
                if p.pick_up(item):
                    ui.log(msg, C_GREEN)
                else:
                    ui.log("Inventario lleno — madera dejada en suelo.", C_RED)
                    key = (int(p.x), int(p.y))
                    w.items.setdefault(key, []).append(item)
            else:
                ui.log(msg, C_GRAY)

        # ── save ─────────────────────────────────────────────────────────────
        elif cmd in ('save', 'guardar'):
            self._world_positions[self.wm.current_id] = [p.x, p.y, p.angle]
            if self._mp_session:
                msg = self._mp_session.save_now(engine=self)
            else:
                msg = self._save_game()
            ui.log(msg, C_GOLD)

        # ── load ─────────────────────────────────────────────────────────────
        elif cmd in ('load', 'cargar'):
            msg = self._load_game()
            ui.log(msg, C_GOLD)
            ui.draw_help()
            import select as _sel
            while not _sel.select([__import__('sys').stdin],[],[],0.05)[0]: pass
            try: __import__('sys').stdin.read(1)
            except: pass

        # ── quit / exit ───────────────────────────────────────────────────────
        elif cmd in ('quit', 'exit', 'q'):
            self.running = False

        # ── unknown ───────────────────────────────────────────────────────────
        else:
            ui.log(f"Comando desconocido: '{cmd}'  (pulsa H para ayuda)", C_GRAY)
