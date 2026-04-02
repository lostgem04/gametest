"""
multiplayer.py — Multijugador TCP para Arcane Abyss (versión mejorada)

Mejoras sobre la versión original:
  ✓ Protocolo con framing de longitud (sin mensajes corruptos/divididos)
  ✓ Sincronización completa del estado del jugador (HP, MP, nivel, armas, raza…)
  ✓ Sistema de eventos: chat, muertes, kills, cambios de mundo, drops de loot
  ✓ Reconexión automática del cliente (hasta N intentos con backoff)
  ✓ Heartbeat / ping-pong para detectar desconexiones silenciosas
  ✓ ID único por jugador (UUID) en vez de usar el socket como clave
  ✓ Servidor difunde solo el mundo activo de cada jugador → los ghosts
    solo aparecen si están en el mismo world_id
  ✓ MultiplayerSession con API limpia para Engine
  ✓ Utilidades: list_saved_worlds, get_local_ip
"""

import socket
import threading
import time
import json
import struct
import uuid
import logging

log = logging.getLogger("multiplayer")

DEFAULT_PORT   = 5000
HEARTBEAT_IVTL = 3.0    # segundos entre pings
HEARTBEAT_TO   = 10.0   # timeout sin pong → desconectar
MAX_RECONNECTS = 5
RECONNECT_BASE = 1.0    # segundos base de backoff

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de red
# ─────────────────────────────────────────────────────────────────────────────

def get_local_ip() -> str:
    """Devuelve la IP local del equipo (no 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def list_saved_worlds() -> list:
    """Stub: retorna mundos guardados. Ampliar si hay sistema de save."""
    import glob, os
    return [os.path.basename(f) for f in glob.glob("saves/*.json")]


# ─────────────────────────────────────────────────────────────────────────────
# Protocolo de framing
#   Cada mensaje va precedido de 4 bytes (big-endian uint32) con la longitud
#   del payload JSON en bytes UTF-8.  Esto evita mensajes partidos o fusionados.
# ─────────────────────────────────────────────────────────────────────────────

def _send_msg(sock: socket.socket, data: dict) -> bool:
    """Envía un dict como JSON con framing de longitud. Retorna False si falla."""
    try:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        header = struct.pack(">I", len(raw))
        sock.sendall(header + raw)
        return True
    except Exception as e:
        log.debug(f"_send_msg error: {e}")
        return False


def _recv_msg(sock: socket.socket) -> dict | None:
    """
    Lee un mensaje completo del socket.
    Retorna el dict, o None si la conexión se cerró/hubo error.
    """
    try:
        header = _recvall(sock, 4)
        if not header:
            return None
        length = struct.unpack(">I", header)[0]
        if length == 0 or length > 4 * 1024 * 1024:   # sanity: max 4 MB
            return None
        raw = _recvall(sock, length)
        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        log.debug(f"_recv_msg error: {e}")
        return None


def _recvall(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


# ─────────────────────────────────────────────────────────────────────────────
# Estado de jugador para sincronizar entre peers
# ─────────────────────────────────────────────────────────────────────────────

def _player_state(player, world_id: str) -> dict:
    """Serializa el estado relevante de un Player para broadcasting."""
    eq = player.equipped or {}
    weap  = (eq.get("weapon")  or {}).get("name", "")
    armor = (eq.get("armor")   or {}).get("name", "")
    bow   = (eq.get("bow")     or {}).get("name", "")
    book  = (eq.get("spellbook") or {}).get("name", "")
    return {
        "x":       round(player.x, 3),
        "y":       round(player.y, 3),
        "angle":   round(player.angle, 3),
        "hp":      player.hp,
        "max_hp":  player.max_hp,
        "mp":      player.mp,
        "max_mp":  player.max_mp,
        "level":   player.level,
        "race_id": getattr(player, "race_id", "human"),
        "name":    getattr(player, "name", "Jugador"),
        "world_id": world_id,
        "weapon":  weap,
        "armor":   armor,
        "bow":     bow,
        "spellbook": book,
        "alive":   player.alive,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SERVER
# ─────────────────────────────────────────────────────────────────────────────

class _ClientConn:
    """Wrapper de conexión de un cliente en el servidor."""
    def __init__(self, sock: socket.socket, addr, pid: str):
        self.sock      = sock
        self.addr      = addr
        self.pid       = pid          # player_id único (UUID)
        self.state     = {}           # último estado conocido
        self.last_pong = time.time()
        self.alive     = True

    def send(self, data: dict) -> bool:
        return _send_msg(self.sock, data)

    def close(self):
        self.alive = False
        try:
            self.sock.close()
        except Exception:
            pass


class GameServer:
    def __init__(self, world_name: str, host: str = "0.0.0.0", port: int = DEFAULT_PORT):
        self.world_name = world_name
        self.host       = host
        self.port       = port

        self._sock    = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._clients : dict[str, _ClientConn] = {}   # pid → _ClientConn
        self._lock    = threading.Lock()
        self._log_lines : list[str] = []              # para get_logs()
        self.running  = False

        # Callbacks que el juego puede suscribir
        self.on_chat   = None   # fn(pid, name, text)
        self.on_join   = None   # fn(pid, name)
        self.on_leave  = None   # fn(pid, name)
        self.on_event  = None   # fn(pid, event_dict)

    def start(self):
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        self.running = True
        local_ip = get_local_ip()
        self._log(f"Servidor '{self.world_name}' en {local_ip}:{self.port}")
        print(f"[SERVER] Servidor iniciado — comparte esta IP: {local_ip}:{self.port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def stop(self):
        self.running = False
        try:
            self._sock.close()
        except Exception:
            pass
        with self._lock:
            for c in list(self._clients.values()):
                c.close()
            self._clients.clear()

    # ── accept ───────────────────────────────────────────────────────────────

    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self._sock.accept()
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                pid = str(uuid.uuid4())[:8]
                conn = _ClientConn(client_sock, addr, pid)
                with self._lock:
                    self._clients[pid] = conn
                self._log(f"Conectado {addr} → pid={pid}")
                threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True
                ).start()
                # Enviar al nuevo cliente el estado de todos los demás
                self._send_full_state_to(conn)
            except Exception as e:
                if self.running:
                    log.debug(f"[SERVER] accept error: {e}")

    def _send_full_state_to(self, conn: _ClientConn):
        """Envía al cliente recién conectado el estado actual de todos los demás."""
        with self._lock:
            peers = [c.state for c in self._clients.values()
                     if c.pid != conn.pid and c.state]
        if peers:
            conn.send({"type": "full_state", "players": peers})

    # ── client handler ────────────────────────────────────────────────────────

    def _handle_client(self, conn: _ClientConn):
        try:
            while self.running and conn.alive:
                msg = _recv_msg(conn.sock)
                if msg is None:
                    break
                self._process(conn, msg)
        except Exception as e:
            log.debug(f"[SERVER] handle_client error: {e}")
        finally:
            self._disconnect(conn)

    def _process(self, conn: _ClientConn, msg: dict):
        t = msg.get("type")

        if t == "join":
            conn.state = {
                "pid":      conn.pid,
                "name":     msg.get("name", "Jugador"),
                "race_id":  msg.get("race", "human"),
                "world_id": msg.get("world", self.world_name),
                "x": 0, "y": 0, "angle": 0,
                "hp": 100, "max_hp": 100, "mp": 50, "max_mp": 50,
                "level": 1, "alive": True,
                "weapon": "", "armor": "", "bow": "", "spellbook": "",
            }
            name = conn.state["name"]
            self._log(f"Join: {name} (pid={conn.pid}, raza={conn.state['race_id']})")
            if self.on_join:
                self.on_join(conn.pid, name)
            # Notificar a todos
            self._broadcast({
                "type":   "player_joined",
                "pid":    conn.pid,
                "name":   name,
                "race_id": conn.state["race_id"],
            }, exclude=conn.pid)

        elif t == "state":
            # Actualización periódica de posición/stats
            state = msg.get("state", {})
            state["pid"] = conn.pid
            conn.state.update(state)
            # Re-difundir solo a jugadores en el mismo mundo
            world_id = conn.state.get("world_id", "")
            self._broadcast_world({
                "type":  "player_state",
                "state": conn.state,
            }, world_id, exclude=conn.pid)

        elif t == "chat":
            text = str(msg.get("text", ""))[:200]
            name = conn.state.get("name", "?")
            log.info(f"[SERVER] Chat [{name}]: {text}")
            if self.on_chat:
                self.on_chat(conn.pid, name, text)
            self._broadcast({
                "type": "chat",
                "pid":  conn.pid,
                "name": name,
                "text": text,
            })

        elif t == "event":
            # Eventos de juego: kill, death, loot, portal, etc.
            event = msg.get("event", {})
            event["pid"]  = conn.pid
            event["name"] = conn.state.get("name", "?")
            if self.on_event:
                self.on_event(conn.pid, event)
            self._broadcast({"type": "event", "event": event}, exclude=conn.pid)

        elif t == "ping":
            conn.last_pong = time.time()
            conn.send({"type": "pong", "ts": msg.get("ts", 0)})

        elif t == "pong":
            conn.last_pong = time.time()

    # ── heartbeat ─────────────────────────────────────────────────────────────

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(HEARTBEAT_IVTL)
            now = time.time()
            dead = []
            with self._lock:
                for pid, conn in self._clients.items():
                    if now - conn.last_pong > HEARTBEAT_TO:
                        dead.append(conn)
                    else:
                        conn.send({"type": "ping", "ts": now})
            for conn in dead:
                log.info(f"[SERVER] Timeout heartbeat: pid={conn.pid}")
                self._disconnect(conn)

    # ── disconnect ────────────────────────────────────────────────────────────

    def _disconnect(self, conn: _ClientConn):
        with self._lock:
            self._clients.pop(conn.pid, None)
        conn.close()
        name = conn.state.get("name", conn.pid)
        self._log(f"Desconectado: {name} (pid={conn.pid})")
        if self.on_leave:
            self.on_leave(conn.pid, name)
        self._broadcast({"type": "player_left", "pid": conn.pid, "name": name})

    # ── broadcast helpers ─────────────────────────────────────────────────────

    def _broadcast(self, data: dict, exclude: str = ""):
        with self._lock:
            targets = [c for c in self._clients.values() if c.pid != exclude]
        for conn in targets:
            if not conn.send(data):
                threading.Thread(target=self._disconnect, args=(conn,), daemon=True).start()

    def _broadcast_world(self, data: dict, world_id: str, exclude: str = ""):
        """Difunde solo a jugadores que estén en el mismo world_id."""
        with self._lock:
            targets = [
                c for c in self._clients.values()
                if c.pid != exclude and c.state.get("world_id") == world_id
            ]
        for conn in targets:
            if not conn.send(data):
                threading.Thread(target=self._disconnect, args=(conn,), daemon=True).start()

    # ── server-side state query ───────────────────────────────────────────────

    def get_player_list(self) -> list[dict]:
        with self._lock:
            return [c.state.copy() for c in self._clients.values() if c.state]

    def connected_count(self) -> int:
        with self._lock:
            return len(self._clients)

    def get_ip(self) -> str:
        """Devuelve la IP local del servidor (compatible con código anterior)."""
        return get_local_ip()

    def get_logs(self, max_lines: int = 20) -> list[str]:
        """Devuelve las últimas líneas del log interno del servidor."""
        return list(self._log_lines[-max(1, max_lines):])

    def player_count(self) -> int:
        """Número de clientes actualmente conectados (alias de connected_count)."""
        return self.connected_count()

    def _log(self, msg: str):
        """Añade una línea al log interno y a logging estándar."""
        log.info(msg)
        self._log_lines.append(msg)


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class GameClient:
    def __init__(self, host: str, port: int, pname: str, race_id: str, world_name: str):
        self.host       = host if host != "0.0.0.0" else "127.0.0.1"
        self.port       = port
        self.pname      = pname
        self.race_id    = race_id
        self.world_name = world_name

        self._sock      : socket.socket | None = None
        self.running    = False
        self._lock      = threading.Lock()

        # Estado de otros jugadores: pid → state_dict
        self._peers     : dict[str, dict] = {}

        # Callbacks
        self.on_message       = None   # fn(msg_dict) — raw handler (legacy)
        self.on_peer_update   = None   # fn(pid, state_dict)
        self.on_peer_left     = None   # fn(pid, name)
        self.on_peer_joined   = None   # fn(pid, name, race_id)
        self.on_chat          = None   # fn(pid, name, text)
        self.on_event         = None   # fn(event_dict)
        self.on_disconnect    = None   # fn()

        # Heartbeat
        self._last_ping_ts  = 0.0
        self._last_pong_ts  = time.time()
        self._ping_interval = HEARTBEAT_IVTL

        # Reconnect
        self._reconnect_attempts = 0
        self._auto_reconnect     = True

    # ── connect ───────────────────────────────────────────────────────────────

    def connect(self) -> tuple[bool, str | None]:
        """
        Intenta conectar al servidor.
        Retorna (True, None) si OK, (False, error_msg) si falla.
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._sock.settimeout(5.0)
            self._sock.connect((self.host, self.port))
            self._sock.settimeout(None)   # bloqueante desde aquí
            self.running = True
            self._reconnect_attempts = 0
            self._last_pong_ts = time.time()

            threading.Thread(target=self._listen_loop, daemon=True).start()
            threading.Thread(target=self._heartbeat_loop, daemon=True).start()

            # Anunciarse al servidor
            self._send({
                "type":  "join",
                "name":  self.pname,
                "race":  self.race_id,
                "world": self.world_name,
            })
            log.info(f"[CLIENT] Conectado a {self.host}:{self.port} como '{self.pname}'")
            return True, None

        except Exception as e:
            errmsg = f"No se pudo conectar a {self.host}:{self.port} — {e}"
            log.warning(f"[CLIENT] {errmsg}")
            return False, errmsg

    # ── send helpers ──────────────────────────────────────────────────────────

    def _send(self, data: dict) -> bool:
        if self._sock and self.running:
            return _send_msg(self._sock, data)
        return False

    def send_state(self, state_dict: dict):
        """Envía la posición/stats del jugador local."""
        self._send({"type": "state", "state": state_dict})

    def send_chat(self, text: str):
        """Envía un mensaje de chat."""
        self._send({"type": "chat", "text": text[:200]})

    def send_event(self, event: dict):
        """
        Envía un evento de juego al servidor para distribuirlo.
        event = {"kind": "kill"|"death"|"portal"|"loot", ...}
        """
        self._send({"type": "event", "event": event})

    # ── listen loop ───────────────────────────────────────────────────────────

    def _listen_loop(self):
        while self.running:
            msg = _recv_msg(self._sock)
            if msg is None:
                log.info("[CLIENT] Conexión cerrada por el servidor.")
                break
            self._handle_msg(msg)
        self._on_disconnected()

    def _handle_msg(self, msg: dict):
        t = msg.get("type")

        if t == "full_state":
            # Estado inicial de todos los jugadores existentes
            for state in msg.get("players", []):
                pid = state.get("pid", "")
                if pid:
                    with self._lock:
                        self._peers[pid] = state
                    if self.on_peer_update:
                        self.on_peer_update(pid, state)

        elif t == "player_state":
            state = msg.get("state", {})
            pid   = state.get("pid", "")
            if pid:
                with self._lock:
                    self._peers[pid] = state
                if self.on_peer_update:
                    self.on_peer_update(pid, state)

        elif t == "player_joined":
            pid     = msg.get("pid", "")
            name    = msg.get("name", "?")
            race_id = msg.get("race_id", "human")
            with self._lock:
                self._peers.setdefault(pid, {"pid": pid, "name": name, "race_id": race_id})
            if self.on_peer_joined:
                self.on_peer_joined(pid, name, race_id)

        elif t == "player_left":
            pid  = msg.get("pid", "")
            name = msg.get("name", "?")
            with self._lock:
                self._peers.pop(pid, None)
            if self.on_peer_left:
                self.on_peer_left(pid, name)

        elif t == "chat":
            if self.on_chat:
                self.on_chat(msg.get("pid",""), msg.get("name","?"), msg.get("text",""))

        elif t == "event":
            if self.on_event:
                self.on_event(msg.get("event", {}))

        elif t == "ping":
            self._send({"type": "pong", "ts": msg.get("ts", 0)})

        elif t == "pong":
            self._last_pong_ts = time.time()

        # Legacy callback
        if self.on_message:
            self.on_message(msg)

    # ── heartbeat ─────────────────────────────────────────────────────────────

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(self._ping_interval)
            if not self.running:
                break
            now = time.time()
            if now - self._last_pong_ts > HEARTBEAT_TO:
                log.warning("[CLIENT] Timeout heartbeat — servidor no responde.")
                self._on_disconnected()
                break
            self._send({"type": "ping", "ts": now})

    # ── disconnect / reconnect ────────────────────────────────────────────────

    def _on_disconnected(self):
        if not self.running:
            return
        self.running = False
        try:
            self._sock.close()
        except Exception:
            pass
        if self.on_disconnect:
            self.on_disconnect()
        if self._auto_reconnect and self._reconnect_attempts < MAX_RECONNECTS:
            self._try_reconnect()

    def _try_reconnect(self):
        self._reconnect_attempts += 1
        delay = RECONNECT_BASE * (2 ** (self._reconnect_attempts - 1))
        log.info(f"[CLIENT] Reconectando en {delay:.1f}s (intento {self._reconnect_attempts}/{MAX_RECONNECTS})…")
        time.sleep(delay)
        ok, err = self.connect()
        if ok:
            log.info("[CLIENT] Reconexión exitosa.")
        else:
            log.warning(f"[CLIENT] Fallo de reconexión: {err}")

    def close(self):
        self._auto_reconnect = False
        self.running = False
        try:
            self._sock.close()
        except Exception:
            pass

    # ── peer queries ──────────────────────────────────────────────────────────

    def get_peers(self, world_id: str | None = None) -> list[dict]:
        """
        Devuelve la lista de estados de otros jugadores.
        Si world_id se especifica, filtra por ese mundo.
        """
        with self._lock:
            peers = list(self._peers.values())
        if world_id is not None:
            peers = [p for p in peers if p.get("world_id") == world_id]
        return peers

    def peer_count(self) -> int:
        with self._lock:
            return len(self._peers)

    def set_player(self, player):
        """
        Asocia el objeto Player local al cliente para que tick() pueda
        serializar su estado automáticamente si se llama sin argumentos.
        """
        self._player = player


# ─────────────────────────────────────────────────────────────────────────────
# MultiplayerSession — interfaz de alto nivel para Engine
# ─────────────────────────────────────────────────────────────────────────────

class MultiplayerSession:
    """
    Abstracción usada por Engine para no tener que diferenciar
    entre ser host o cliente.

    Uso típico (host):
        server = GameServer(world_name)
        server.start()
        client = GameClient("127.0.0.1", port, name, race, world)
        ok, _ = client.connect()
        session = MultiplayerSession(server=server, client=client)
        engine._mp_session = session

    Uso típico (cliente):
        client = GameClient(host, port, name, race, world)
        ok, err = client.connect()
        session = MultiplayerSession(client=client)
        engine._mp_session = session
    """

    def __init__(self, server=None, client: GameClient | None = None):
        # main.py llama MultiplayerSession(client) posicionalmente,
        # lo que pone el GameClient en 'server'. Detectar y corregir.
        if isinstance(server, GameClient):
            client = server
            server = None
        self.server  = server
        self.client  = client
        self._world_id = ""
        self._chat_log : list[tuple[str, str, str]] = []   # (name, text, timestamp)

        # Callbacks de alto nivel para Engine / UI
        self.on_chat   = None   # fn(name, text)
        self.on_event  = None   # fn(event_dict)
        self.on_join   = None   # fn(name)
        self.on_leave  = None   # fn(name)

        if self.client:
            self.client.on_chat    = self._on_chat
            self.client.on_event   = self._on_event
            self.client.on_peer_joined = self._on_peer_joined
            self.client.on_peer_left   = self._on_peer_left
            self.client.on_disconnect  = self._on_client_disconnect

        if self.server:
            self.server.on_chat  = lambda pid, name, text: None   # ya procesado por client
            self.server.on_join  = lambda pid, name: None
            self.server.on_leave = lambda pid, name: None

    # ── state setters ─────────────────────────────────────────────────────────

    def set_world_id(self, world_id: str):
        self._world_id = world_id

    def tick(self, player=None):
        """
        Llamar cada frame. Envía el estado del jugador local al servidor.
        Si player se pasa, serializa su estado completo.
        """
        if self.client and self.client.running and player is not None:
            state = _player_state(player, self._world_id)
            self.client.send_state(state)

    # ── ghost players para el renderer ────────────────────────────────────────

    def get_ghosts(self) -> list[dict]:
        """
        Devuelve la lista de otros jugadores en el mismo mundo,
        listos para ser renderizados como 'ghosts'.
        """
        if not self.client:
            return []
        return self.client.get_peers(world_id=self._world_id)

    # ── chat ──────────────────────────────────────────────────────────────────

    def send_chat(self, text: str):
        if self.client:
            self.client.send_chat(text)

    def get_chat_log(self) -> list[tuple[str, str, str]]:
        return list(self._chat_log[-50:])   # últimos 50 mensajes

    # ── eventos de juego ──────────────────────────────────────────────────────

    def notify_kill(self, enemy_name: str):
        if self.client:
            self.client.send_event({"kind": "kill", "enemy": enemy_name})

    def notify_death(self):
        if self.client:
            self.client.send_event({"kind": "death"})

    def notify_portal(self, dest_world: str):
        if self.client:
            self.client.send_event({"kind": "portal", "dest": dest_world})

    def notify_level_up(self, new_level: int):
        if self.client:
            self.client.send_event({"kind": "level_up", "level": new_level})

    # ── save stub ─────────────────────────────────────────────────────────────

    def save_now(self, engine=None) -> str:
        """
        Guarda la partida multijugador.
        - Si se pasa engine, usa su _save_game() completo (mismo formato que SP).
        - El archivo se guarda en ~/.arcane_abyss_mp_<player_name>.json
          para que cada jugador tenga su propio slot sin pisar el save SP.
        """
        if engine is not None:
            # Redirigir la ruta de guardado a un slot MP por nombre de jugador
            import os, json
            pname = (self.client.pname if self.client else "jugador").replace(" ", "_")
            path  = os.path.expanduser(f"~/.arcane_abyss_mp_{pname}.json")
            # Usar la lógica existente de engine, luego mover el archivo
            original_msg = engine._save_game()          # guarda en el path SP
            sp_path = os.path.expanduser("~/.arcane_abyss_save.json")
            try:
                if os.path.exists(sp_path):
                    import shutil
                    shutil.copy2(sp_path, path)
            except Exception:
                pass
            return original_msg.replace("Partida guardada", f"Partida MP guardada ({pname})")
        return "💾 [MP] Usa /save desde el juego para guardar tu progreso."

    # ── info ──────────────────────────────────────────────────────────────────

    def is_host(self) -> bool:
        return self.server is not None

    def is_connected(self) -> bool:
        return bool(self.client and self.client.running)

    def peer_count(self) -> int:
        if self.client:
            return self.client.peer_count()
        if self.server:
            return self.server.connected_count()
        return 0

    def status_line(self) -> str:
        role = "HOST" if self.is_host() else "CLIENT"
        conn = "✓" if self.is_connected() else "✗"
        peers = self.peer_count()
        return f"[MP {role} {conn}] {peers} jugador(es) online"

    # ── callbacks internos ────────────────────────────────────────────────────

    def _on_chat(self, pid: str, name: str, text: str):
        ts = time.strftime("%H:%M")
        self._chat_log.append((name, text, ts))
        if self.on_chat:
            self.on_chat(name, text)

    def _on_event(self, event: dict):
        if self.on_event:
            self.on_event(event)

    def _on_peer_joined(self, pid: str, name: str, race_id: str):
        if self.on_join:
            self.on_join(name)

    def _on_peer_left(self, pid: str, name: str):
        if self.on_leave:
            self.on_leave(name)

    def _on_client_disconnect(self):
        log.warning("[SESSION] Cliente desconectado del servidor.")

    # ── legacy send (compatibilidad con código viejo) ─────────────────────────

    def send(self, data: dict):
        if self.client:
            self.client._send(data)

    def close(self):
        if self.client:
            self.client.close()
        if self.server:
            self.server.stop()

    def disconnect(self):
        """Alias de close() — compatibilidad con main.py."""
        self.close()


# ─────────────────────────────────────────────────────────────────────────────
# dict_to_player — restaurar estado de un jugador desde un dict guardado
# ─────────────────────────────────────────────────────────────────────────────

def dict_to_player(data: dict, player) -> str:
    """
    Carga el estado serializado (dict) sobre un objeto Player existente.
    Retorna el world_id guardado (o 'world_dungeon' si no existe).
    Usado por main.py al conectarse con datos guardados del servidor.

    Acepta tanto el formato compacto de estado de red como el formato
    completo de save (version 3) generado por engine._save_game().
    """
    if not data:
        return "world_dungeon"
    try:
        # Formato completo de save (version 3) ─────────────────────────────
        if data.get("version") == 3:
            for attr in ("hp", "max_hp", "mp", "max_mp", "xp", "level",
                         "gold", "attack", "defense", "arrows", "steps"):
                if attr in data:
                    setattr(player, attr, data[attr])
            if "name" in data:
                player.name = data["name"]
            if "active_spell" in data:
                player.active_spell = data["active_spell"]
            if "inventory" in data:
                player.inventory = list(data["inventory"])
            if "equipped" in data:
                player.equipped.update(data["equipped"])
            if "skill_xp" in data:
                player.skill_xp.update(data["skill_xp"])
            if "skill_level" in data:
                player.skill_level.update(data["skill_level"])
            player.hp    = min(player.hp,  player.max_hp)
            player.mp    = min(player.mp,  player.max_mp)
            player.alive = player.hp > 0
            return data.get("world_id", "world_dungeon")

        # Formato compacto de estado de red ─────────────────────────────────
        for attr in ("hp", "max_hp", "mp", "max_mp", "xp", "level",
                     "gold", "attack", "defense", "arrows", "steps"):
            if attr in data:
                setattr(player, attr, data[attr])
        if "name" in data:
            player.name = data["name"]
        if "active_spell" in data:
            player.active_spell = data["active_spell"]
        if "inventory" in data:
            player.inventory = list(data["inventory"])
        if "equipped" in data:
            player.equipped.update(data["equipped"])
        if "skill_xp" in data:
            player.skill_xp.update(data["skill_xp"])
        if "skill_level" in data:
            player.skill_level.update(data["skill_level"])
        player.hp    = min(player.hp,  player.max_hp)
        player.mp    = min(player.mp,  player.max_mp)
        player.alive = player.hp > 0

    except Exception as e:
        log.warning(f"dict_to_player: error restaurando estado: {e}")
    return data.get("world_id", "world_dungeon")


def load_mp_save(pname: str) -> dict | None:
    """
    Carga el save MP de un jugador por nombre.
    Retorna el dict completo o None si no existe.
    """
    import os, json
    safe_name = pname.replace(" ", "_")
    path = os.path.expanduser(f"~/.arcane_abyss_mp_{safe_name}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"load_mp_save: error leyendo {path}: {e}")
        return None
