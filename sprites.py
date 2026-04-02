import os as _os, sys as _sys
_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))
if _SCRIPT_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPT_DIR)
del _os, _sys, _SCRIPT_DIR

"""
sprites.py — Todos los sprites ASCII del juego.

Enemigos:   7 frames [FAR, MID_FAR, MID, NEAR, FRONT, ATTACK1, ATTACK2]
NPCs:       5 frames [FAR, MID_FAR, MID, NEAR, FRONT]  (sin ataque)
Objetos:    1 frame  [IDLE]  (árboles, muebles — estáticos)

Distancias de corte:
  dist > 10  → FAR
  dist > 7   → MID_FAR
  dist > 4.5 → MID
  dist > 2.5 → NEAR
  dist <=2.5 → FRONT
"""

# ═══════════════════════════════════════════════════════════════════
#  ENEMIGOS  (7 frames cada uno)
# ═══════════════════════════════════════════════════════════════════

SKELETON = [
    # FAR (dist > 10)
    [" i "],
    # MID_FAR (dist > 7)
    ["  o  ",
     " /|\\ ",
     " / \\ "],
    # MID (dist > 4.5)
    ["  .-. ",
     " (o o)",
     "  /|\\ ",
     "  / \\ "],
    # NEAR (dist > 2.5)
    [" .----.",
     "( o  o)",
     " )    (",
     "/|----| ",
     "|      |",
     "/      \\"],
    # FRONT (dist <= 2.5)
    [" .------.",
     "( o    o)",
     "|  ----  |",
     "| /|  |\\ |",
     "||  ||  ||",
     "||  ||  ||",
     " \\______/ "],
    # ATTACK1
    [" .----.",
     "( ><  )",
     " /----\\",
     "/|====|\\",
     " |    | ",
     " CLACK! "],
    # ATTACK2
    [" .----.",
     "(  >< )",
     " \\----/",
     "\\|====|/",
     " |    | ",
     " !BONK! "],
]

SLIME = [
    # FAR
    [" ~ "],
    # MID_FAR
    [" ~~~ ",
     "(o o)",
     " ~~~ "],
    # MID
    ["  ~~~~  ",
     " (o  o) ",
     "(  ..  )",
     " ~~~~~~ "],
    # NEAR
    ["   ~~~~~~  ",
     " ( o    o) ",
     "(   ~~~~  )",
     "(  ......  )",
     " ~~~~~~~~~~ "],
    # FRONT
    ["   ~~~~~~~~~  ",
     " (  o      o) ",
     "(    ~~~~~~  )",
     "(   ........  )",
     " ~~~~~~~~~~~~  ",
     "   BLOOORP!!  "],
    # ATTACK1
    ["  ~SPLAT~  ",
     " ( ^    ^) ",
     "(  \\../   )",
     "(~~~BLOB~~~)",
     " ~~~~~~~~~~ "],
    # ATTACK2
    [" ~SQUISH~  ",
     " ( >    <) ",
     "(  /--\\   )",
     "(~~~~~~~~~~)",
     " ~~~~~~~~~~ "],
]

GOBLIN = [
    # FAR
    [" ^ "],
    # MID_FAR
    [" /\\ ",
     "(oo)",
     "/|\\"],
    # MID
    ["  /\\  ",
     " (oo) ",
     " >||< ",
     "  /\\  "],
    # NEAR
    ["   /\\   ",
     "  /  \\  ",
     " ( oo ) ",
     "  \\--/  ",
     "  /||\\ ",
     " / || \\ "],
    # FRONT
    ["    /\\    ",
     "   /  \\   ",
     "  / oo \\  ",
     " |  --  | ",
     "  \\    /  ",
     "  /|  |\\ ",
     " / |  | \\ ",
     "/  |  |  \\"],
    # ATTACK1
    ["   /\\   ",
     "  /><\\  ",
     " ( ## ) ",
     "  \\--/  ",
     " \\|  |/ ",
     " SLASH! "],
    # ATTACK2
    ["   /\\   ",
     "  /<>\\  ",
     " ( ## ) ",
     "  /--\\  ",
     " /|  |\\ ",
     " !HIT!  "],
]

ORC = [
    # FAR
    [" M "],
    # MID_FAR
    [" ___ ",
     "(o o)",
     "|###|",
     " \\_/ "],
    # MID
    ["  ___  ",
     " /o o\\ ",
     "| ### |",
     " \\___/ ",
     "  | |  "],
    # NEAR
    ["   ____  ",
     "  / oo \\ ",
     " | \\__/ | ",
     " | #### | ",
     "  \\____/ ",
     "   |  |  ",
     "  _|  |_ "],
    # FRONT
    ["    _____   ",
     "   / o o \\  ",
     "  |  ---  | ",
     "  | ##### | ",
     "  | ##### | ",
     "   \\_____/  ",
     "    |   |   ",
     "   _|   |_  ",
     "  |_|   |_| "],
    # ATTACK1
    ["   ____  ",
     "  / >< \\ ",
     " | \\##/ | ",
     " | RAWR | ",
     "  \\____/ ",
     " //|  |\\\\ ",
     " SMASH!! "],
    # ATTACK2
    ["   ____  ",
     "  / <> \\ ",
     " | /##\\ | ",
     " | GRAA | ",
     "  \\____/ ",
     " \\\\|  |// ",
     " CRUSH!! "],
]

WRAITH = [
    # FAR
    [" * "],
    # MID_FAR
    ["  * *  ",
     " (o o) ",
     "  ~~~  "],
    # MID
    [" *   * ",
     "  .--. ",
     " (o  o)",
     "  )~~( ",
     " ~~~~~~"],
    # NEAR
    ["*        *",
     "  .----. ",
     " ( o  o )",
     "  ) __ ( ",
     " /~~~~~~\\ ",
     " \\~~~~~~/ ",
     "  ~~~~~~  "],
    # FRONT
    [" *          * ",
     "   .------. ",
     "  ( o    o )",
     "   )  __  ( ",
     "  / ~~~~~~ \\ ",
     " / ~~~~~~~~~\\ ",
     " \\~~~~~~~~~~/ ",
     "   ~~~~~~~~  "],
    # ATTACK1
    [" *SHRIEK* ",
     "  .----. ",
     " ( ^  ^ )",
     "  ) !! ( ",
     " /~~~~~~\\ ",
     "**\\~~~~/**",
     "  ~~~~~~  "],
    # ATTACK2
    [" *WAIL*  ",
     "  .----. ",
     " ( >  < )",
     "  ) !! ( ",
     " *~~~~~~* ",
     " /\\~~~~/ ",
     "  ~~~~~~  "],
]

TROLL = [
    # FAR
    [" W "],
    # MID_FAR
    [" ___ ",
     "(O O)",
     "|###|",
     "|___|"],
    # MID
    ["  ___  ",
     " /O O\\ ",
     "| ### |",
     "| === |",
     " \\___/ "],
    # NEAR
    ["   _____  ",
     "  / O O \\ ",
     " |  ___  |",
     " | |###| |",
     " | |===| |",
     "  \\_____/ ",
     "  _|   |_ ",
     " |_|   |_|"],
    # FRONT
    ["    _______   ",
     "   / O   O \\  ",
     "  |   ___   | ",
     "  |  |###|  | ",
     "  |  |===|  | ",
     "  |  |===|  | ",
     "   \\_______/  ",
     "    _|   |_   ",
     "   |_|   |_|  "],
    # ATTACK1
    ["   _____  ",
     "  / > < \\ ",
     " |  ###  |",
     " | ROAAR |",
     " | |===| |",
     "  \\_____/ ",
     " \\\\|   |// ",
     " SLAM!!! "],
    # ATTACK2
    ["   _____  ",
     "  / < > \\ ",
     " |  ###  |",
     " | GRRRR |",
     " | |===| |",
     "  \\_____/ ",
     " //|   |\\\\ ",
     " CRUSH!! "],
]

BAT = [
    # FAR
    [" v "],
    # MID_FAR
    ["v . v"],
    # MID
    ["/v . v\\",
     " (o o) ",
     "  \\_/  "],
    # NEAR
    ["//v . v\\\\",
     "  (o o)  ",
     "   \\_/   ",
     "   /|\\   "],
    # FRONT
    ["///V . V\\\\\\",
     "   (o o)   ",
     "    \\_/    ",
     "    /|\\    ",
     "   SCREEE! "],
    # ATTACK1
    ["//V . V\\\\",
     "  (> <)  ",
     "   \\./   ",
     "  SCREEE!"],
    # ATTACK2
    ["\\\\V . V//",
     "  (< >)  ",
     "   /.\\ ",
     "  BITE! "],
]

SPIDER = [
    # FAR
    [" * "],
    # MID_FAR
    ["/o\\",
     "|||"],
    # MID
    [" /^^\\ ",
     "(o  o)",
     " \\||/ ",
     " /  \\ "],
    # NEAR
    ["  /----\\  ",
     " ( o  o ) ",
     "  \\====/ ",
     " /| || |\\ ",
     "/ |    | \\"],
    # FRONT
    ["   /------\\   ",
     "  ( o    o )  ",
     "   \\======/   ",
     " //| |||| |\\\\  ",
     "// |      | \\\\ ",
     "   |      |   "],
    # ATTACK1
    ["  /----\\  ",
     " ( >  < ) ",
     "  \\####/ ",
     " /| || |\\ ",
     "VENOOOOM! "],
    # ATTACK2
    ["  /----\\  ",
     " ( <  > ) ",
     "  /####\\ ",
     " \\| || |/ ",
     "  BITE!!  "],
]

WOLF = [
    # FAR
    [" w "],
    # MID_FAR
    [" /\\ ",
     "(oo)",
     "AWOO"],
    # MID
    ["  /\\  ",
     " (oo) ",
     "/\\  /\\",
     "AWWOO!"],
    # NEAR
    ["   /\\    ",
     "  (oo)   ",
     " / \\/ \\ ",
     "/\\    /\\ ",
     "  AWOO! "],
    # FRONT
    ["    /\\     ",
     "   (oo)    ",
     "  / -- \\   ",
     " / \\  / \\  ",
     "/\\  \\/  /\\ ",
     "  AWOOOO!  "],
    # ATTACK1
    ["   /\\    ",
     "  (><)   ",
     " / --  \\ ",
     "/\\SNAP!/\\ ",
     "  GROWL!"],
    # ATTACK2
    ["   /\\    ",
     "  (<>)   ",
     " \\ --  / ",
     "\\\\BITE!// ",
     "  SNARL!"],
]

VAMPIRE = [
    # FAR
    [" v "],
    # MID_FAR
    ["  /\\  ",
     " (oo) ",
     " /||\\ "],
    # MID
    ["  /\\   ",
     " (oo)  ",
     " |  |  ",
     "/\\  /\\ ",
     "  /\\   "],
    # NEAR
    ["   /\\    ",
     "  (@@)   ",
     " /|  |\\ ",
     " | /\\ | ",
     "/\\    /\\ ",
     "  \\  /  "],
    # FRONT
    ["    /\\     ",
     "   (@@)    ",
     "  /|  |\\  ",
     "  | /\\ |  ",
     "  |    |  ",
     " /\\    /\\ ",
     "/  \\  /  \\",
     "  HISSSS! "],
    # ATTACK1
    ["   /\\    ",
     "  (><)   ",
     " /|  |\\ ",
     " |DRAIN|",
     "/\\    /\\ ",
     " DRAIN!! "],
    # ATTACK2
    ["   /\\    ",
     "  (><)   ",
     " /\\  /\\ ",
     " |BITE!|",
     "  \\  /  ",
     " !!BITE!!"],
]

GOLEM = [
    # FAR
    [" G "],
    # MID_FAR
    [" ___ ",
     "[OO ]",
     "|###|",
     "[___]"],
    # MID
    ["  ___  ",
     " [OO ] ",
     " |###| ",
     " |===| ",
     " [___] "],
    # NEAR
    ["   ___   ",
     "  [O O]  ",
     "  |###|  ",
     "  |===|  ",
     "  |###|  ",
     " _[___]_ ",
     "|_|   |_|"],
    # FRONT
    ["    ___    ",
     "   [O O]   ",
     "   |###|   ",
     "   |===|   ",
     "   |###|   ",
     "   |===|   ",
     " __|   |__ ",
     "|__|   |__|",
     "  GRRRUMBL "],
    # ATTACK1
    ["   ___   ",
     "  [> <]  ",
     "  |###|  ",
     "  |===|  ",
     " _[###]_ ",
     "|SMASH!!|",
     " STOMP!! "],
    # ATTACK2
    ["   ___   ",
     "  [< >]  ",
     "  |###|  ",
     "  |===|  ",
     " _[###]_ ",
     "|CRUSH!!|",
     " RUMBLE! "],
]

NECROMANCER = [
    # FAR
    [" n "],
    # MID_FAR
    ["  *  ",
     " (oo)",
     " /|\\ ",
     "  *  "],
    # MID
    ["  ***  ",
     " (o o) ",
     " /|+|\\ ",
     "  / \\  ",
     "  * *  "],
    # NEAR
    ["   ***   ",
     "  (o o)  ",
     "  \\___/  ",
     "  /|+|\\  ",
     " / | | \\ ",
     "/  |+|  \\ ",
     "   * *   "],
    # FRONT
    ["    ***    ",
     "   (o o)   ",
     "   \\___/   ",
     "   /|+|\\   ",
     "  / |+| \\  ",
     " /  |+|  \\ ",
     "/***|+|***\\",
     "    | |    ",
     "  RISE!! "],
    # ATTACK1
    ["   ***   ",
     "  (X X)  ",
     "  \\___/  ",
     "  /|*|\\  ",
     " SUMMON! ",
     "***...***",
     " UNDEAD! "],
    # ATTACK2
    ["   ***   ",
     "  (* *)  ",
     "  \\___/  ",
     "  /|#|\\  ",
     " CURSED! ",
     "***!!!***",
     " DEATH!  "],
]

DRAGON = [
    # FAR
    [" D "],
    # MID_FAR
    [" /\\  ",
     "(oo) ",
     "/^^\\ ",
     "\\__/ "],
    # MID
    ["   /\\   ",
     "  (oo)  ",
     " /|^^|\\ ",
     "/      \\",
     " \\____/ "],
    # NEAR
    ["    /\\    ",
     "   (OO)   ",
     "  /|^^|\\  ",
     " /|    |\\ ",
     "/  \\  /  \\",
     "   /\\  /\\ ",
     "  /  \\/  \\",
     "  ROOOARRR"],
    # FRONT
    ["     /\\     ",
     "    (OO)    ",
     "   /|^^|\\   ",
     "  /|    |\\  ",
     " / |    | \\ ",
     "/  /\\  /\\  \\",
     "  /  \\/  \\  ",
     " /\\  /\\  /\\ ",
     "/  \\/  \\/  \\",
     "  ROOOAARRR!"],
    # ATTACK1
    ["    /\\    ",
     "   (><)   ",
     "  /|**|\\  ",
     " FIREBALL ",
     " >======> ",
     "  ~FWOOSH~",
     " BURN!!!  "],
    # ATTACK2
    ["    /\\    ",
     "   (<>)   ",
     "  /|##|\\  ",
     " TAIL SLAM",
     " \\======/ ",
     "  ~CRASH~ ",
     " STOMP!!! "],
]

# ═══════════════════════════════════════════════════════════════════
#  NPCs  (5 frames: FAR, MID_FAR, MID, NEAR, FRONT)
# ═══════════════════════════════════════════════════════════════════

VILLAGER = [
    # FAR
    [" i "],
    # MID_FAR
    ["  o  ",
     " /|\\ ",
     " / \\ "],
    # MID
    ["  (o) ",
     " /|n|\\ ",
     " / \\ "],
    # NEAR
    ["  .--. ",
     " (o  o)",
     "  \\__/ ",
     " /|##|\\ ",
     " |    | ",
     " /    \\ "],
    # FRONT
    ["   .----. ",
     "  (o    o)",
     "   \\____/ ",
     "  /|####|\\ ",
     "  ||    || ",
     "  ||    || ",
     "  /      \\ "],
]

MERCHANT = [
    # FAR
    [" $ "],
    # MID_FAR
    ["  o$ ",
     " /|\\ ",
     " / \\ "],
    # MID
    [" $.(o).$",
     "  /|$|\\ ",
     "  / \\  "],
    # NEAR
    ["  .--. ",
     " ($ $$)",
     "  \\__/ ",
     " /|$$|\\ ",
     " |[$$]| ",
     " /    \\ "],
    # FRONT
    ["   .----. ",
     "  ($ o $)",
     "   \\____/ ",
     "  /|$$$$|\\ ",
     " _|[$$$$]|_ ",
     "| |      | |",
     "  /      \\  "],
]

WIZARD = [
    # FAR
    [" * "],
    # MID_FAR
    ["  *  ",
     " /|\\ ",
     " / \\ "],
    # MID
    [" *.*  ",
     " (^.^)",
     " /|*|\\ ",
     "  / \\ "],
    # NEAR
    [" .****.",
     "(  *.*  )",
     " ( ^ ^ ) ",
     "  \\___/ ",
     " /|***|\\ ",
     " |*   *| ",
     " /     \\ "],
    # FRONT
    ["  .*****. ",
     " (*     *)",
     " ( ^ ^ )  ",
     "  \\_____/ ",
     " /|*****|\\ ",
     " |*     *| ",
     " |*     *| ",
     "  \\_____/ "],
]

GUARD = [
    # FAR
    [" | "],
    # MID_FAR
    [" [o] ",
     " /|\\ ",
     " / \\ "],
    # MID
    [" [o]  ",
     " |=|  ",
     " /|\\ ",
     " / \\ "],
    # NEAR
    [" [===]",
     " [o o]",
     " |===| ",
     " /|=|\\ ",
     " | = | ",
     " /   \\ "],
    # FRONT
    ["  [=====] ",
     "  [o   o] ",
     "  |=====| ",
     "  /|===|\\ ",
     "  | === | ",
     "  | === | ",
     "  /     \\ "],
]

BLACKSMITH = [
    # FAR
    [" H "],
    # MID_FAR
    ["  o  ",
     " /|\\ ",
     " / \\ "],
    # MID
    ["  (o) ",
     " /|\\  ",
     " /|\\  ",
     " / \\  "],
    # NEAR
    ["  .--. ",
     " (o  o)",
     "  \\__/ ",
     " /|**|\\ ",
     " |[==]| ",
     " /    \\ "],
    # FRONT
    ["   .----. ",
     "  (o    o)",
     "   \\____/ ",
     "  /|****|\\ ",
     "  ||[==]|| ",
     "  ||    || ",
     "  /  /\\  \\ "],
]

ELF = [
    # FAR  — pointed ear silhouette
    [" ^ "],
    # MID_FAR
    [" /^\\  ",
     "(- -) ",
     " /|\\ "],
    # MID — robes with leaf motif
    ["  /^\\  ",
     " (- -) ",
     "  ))(  ",
     " /|*|\\ ",
     "  / \\  "],
    # NEAR
    ["  .-^-. ",
     " (- . -)",
     "  \\___/ ",
     "  /|*|\\ ",
     " /|   |\\ ",
     " |*   *| ",
     " /     \\ "],
    # FRONT
    ["   .-^-. ",
     "  (- . -) ",
     "   \\___/  ",
     "  /|***|\\ ",
     " /|*   *|\\ ",
     " |*  *  *| ",
     " |*  *  *| ",
     "  \\_____/  "],
]

ELF_SMITH = [
    # FAR
    [" ^ "],
    # MID_FAR
    [" /^\\  ",
     "(o o) ",
     " /+\\ "],
    # MID
    ["  /^\\  ",
     " (o o) ",
     "  ))(  ",
     " /+#+\\ ",
     "  / \\  "],
    # NEAR
    ["  .-^-. ",
     " (o . o)",
     "  \\___/ ",
     "  /+#+\\ ",
     " /|   |\\ ",
     " |[==]| ",
     " /  ^  \\ "],
    # FRONT
    ["   .-^-. ",
     "  (o . o) ",
     "   \\___/  ",
     "  /|+#+|\\ ",
     " /| [=] |\\ ",
     " || [=] || ",
     " ||     || ",
     "  \\_____/  "],
]

# ═══════════════════════════════════════════════════════════════════
#  OBJETOS ESTÁTICOS  (1 frame: IDLE)
# ═══════════════════════════════════════════════════════════════════

TREE_OAK = [
    # FAR
    ["  *  ",
     "  |  "],
    # MID
    [" *** ",
     "*****",
     " *** ",
     "  |  ",
     "  |  "],
    # NEAR
    ["   ***   ",
     "  *****  ",
     " ******* ",
     " ******* ",
     "  *****  ",
     "   ***   ",
     "   |||   ",
     "   |||   "],
]

TREE_PINE = [
    # FAR
    ["  ^  ",
     "  |  "],
    # MID
    ["  *  ",
     " *** ",
     "*****",
     "  |  ",
     "  |  "],
    # NEAR
    ["    *    ",
     "   ***   ",
     "  *****  ",
     " ******* ",
     "***********",
     "  *****  ",
     "   ***   ",
     "    |    ",
     "    |    "],
]

TREE_DEAD = [
    # FAR
    [" \\|/ ",
     "  |  "],
    # MID
    [" \\|/ ",
     "--+--",
     " /|\\ ",
     "  |  "],
    # NEAR
    ["  \\ | /  ",
     "   \\|/   ",
     " ---+--- ",
     "   /|\\   ",
     "  / | \\  ",
     "    |    ",
     "    |    ",
     "   _|_   "],
]

TREE_PALM = [
    # FAR
    [" ** ",
     "  | "],
    # MID
    [" **  ",
     "\\**/ ",
     " || ",
     " || "],
    # NEAR
    [" **  **  ",
     "  \\****/  ",
     "   \\**/ ",
     "    ||   ",
     "    ||   ",
     "    ||   ",
     "   /||\\  ",
     "  / || \\ "],
]

TREE_SNOW = [
    # FAR
    ["  *  ",
     "  |  "],
    # MID
    ["  *  ",
     " *·* ",
     "*·*·*",
     "  |  "],
    # NEAR
    ["    *    ",
     "   *.*   ",
     "  *.*.*  ",
     " *.*.*.* ",
     "*.*.*.*.*",
     "  *.*.*  ",
     "   .|.   ",
     "   .|.   "],
]

CHEST = [
    [" .----. ",
     " |    | ",
     " |####| ",
     " '----' "],
]

BARREL = [
    [" .--. ",
     " |##| ",
     " |--| ",
     " |##| ",
     " '--' "],
]

TABLE = [
    [" .------. ",
     " |      | ",
     " '------' ",
     "  |    |  "],
]

BED = [
    [" .------.",
     " |zz  zz|",
     " |======|",
     " |      |",
     " '------'"],
]

BOOKSHELF = [
    [" |======|",
     " |[][][]|",
     " |[][][]|",
     " |[][][]|",
     " |======|"],
]

FIREPLACE = [
    ["  ^ ^ ^  ",
     " /|||||\\",
     " | fire |",
     " |------|",
     " '------'"],
]

WELL = [
    ["  _____  ",
     " /     \\ ",
     "|  ~~~  |",
     "|_______|",
     "  |   |  "],
]

SIGNPOST = [
    [" .------.",
     " | INFO |",
     " '------'",
     "    ||   ",
     "    ||   "],
]

PICKAXE = [
    [" /--o ",
     "/   | ",
     "    | ",
     "    \\ "],
]

MINERAL_IRON = [
    [" .----. ",
     " |####| ",
     " |Fe ##|",
     " '----' "],
]

MINERAL_GOLD = [
    [" .----. ",
     " |$$$$| ",
     " |Au $$|",
     " '----' "],
]

MINERAL_GEM = [
    [" /\\  ",
     "/  \\ ",
     "\\<>/ ",
     " \\/ "],
]

ANVIL = [
    [" .------.",
     " |######|",
     "  \\####/ ",
     "  |    | ",
     "  '----' "],
]

FORGE = [
    ["  ^ ^ ^  ",
     " /|^^^|\\ ",
     " |FORGE| ",
     " |======|",
     " '------'"],
]

SHOP_COUNTER = [
    [" .--------.",
     " | SHOP   |",
     " |--------|",
     " |        |",
     " '--------'"],
]

# ═══════════════════════════════════════════════════════════════════
#  Registros
# ═══════════════════════════════════════════════════════════════════

ENEMY_SPRITES = {
    'skeleton':    SKELETON,
    'slime':       SLIME,
    'goblin':      GOBLIN,
    'orc':         ORC,
    'wraith':      WRAITH,
    'troll':       TROLL,
    'bat':         BAT,
    'spider':      SPIDER,
    'wolf':        WOLF,
    # ── nuevos enemigos con sprites propios ──
    'vampire':     VAMPIRE,
    'golem':       GOLEM,
    'necromancer': NECROMANCER,
    'dragon':      DRAGON,
}

NPC_SPRITES = {
    'villager':     VILLAGER,
    'merchant':     MERCHANT,
    'wizard':       WIZARD,
    'guard':        GUARD,
    'blacksmith':   BLACKSMITH,
    # ── razas élfica ──
    'elf':          ELF,
    'elf_smith':    ELF_SMITH,
    # ── ghost player (otros jugadores en multijugador) ──
    'player_ghost': VILLAGER,   # usa silueta de aldeano con color de raza
    # ── animales (usan sprite de NPC, tamaño apropiado) ──
    'rabbit':    VILLAGER,
    'deer':      VILLAGER,
    'fox':       VILLAGER,
    'boar':      VILLAGER,
    'crow':      VILLAGER,
    'snake':     VILLAGER,
    'horse':     VILLAGER,
    'cat':       VILLAGER,
    'bear':      VILLAGER,
    'parrot':    VILLAGER,
    'npc_villager': VILLAGER,
}

OBJECT_SPRITES = {
    'tree_oak':     TREE_OAK,
    'tree_pine':    TREE_PINE,
    'tree_dead':    TREE_DEAD,
    'tree_palm':    TREE_PALM,
    'tree_snow':    TREE_SNOW,
    'chest':        CHEST,
    'barrel':       BARREL,
    'table':        TABLE,
    'bed':          BED,
    'bookshelf':    BOOKSHELF,
    'fireplace':    FIREPLACE,
    'well':         WELL,
    'signpost':     SIGNPOST,
    'pickaxe':      PICKAXE,
    'mineral_iron': MINERAL_IRON,
    'mineral_gold': MINERAL_GOLD,
    'mineral_gem':  MINERAL_GEM,
    'anvil':        ANVIL,
    'forge':        FORGE,
    'shop_counter': SHOP_COUNTER,
}

# Todas juntas para búsqueda genérica
ALL_SPRITES = {**ENEMY_SPRITES, **NPC_SPRITES, **OBJECT_SPRITES}

# ─────────────────────────────────────────────────────────────────
#  get_frame API
# ─────────────────────────────────────────────────────────────────

TREE_SPRITES = {'tree_oak', 'tree_pine', 'tree_dead', 'tree_palm', 'tree_snow'}

def get_frame(sprite_id: str, dist: float,
              attacking: bool = False, tick: int = 0) -> list:
    """
    Enemigos: 7 frames según dist/attacking.
      FAR(>10), MID_FAR(>7), MID(>4.5), NEAR(>2.5), FRONT(<=2.5) + ATK1, ATK2
    NPCs: 5 frames según dist.
    Árboles: 3 frames — FAR(>8), MID(>3.5), NEAR(<=3.5)
    Otros objetos: frame 0 estático.
    """
    if sprite_id in ENEMY_SPRITES:
        frames = ENEMY_SPRITES[sprite_id]
        if attacking:
            return frames[5] if tick % 2 == 0 else frames[6]
        if dist > 10:  return frames[0]
        if dist > 7:   return frames[1]
        if dist > 4.5: return frames[2]
        if dist > 2.5: return frames[3]
        return frames[4]

    if sprite_id in NPC_SPRITES:
        frames = NPC_SPRITES[sprite_id]
        if dist > 10:  return frames[0]
        if dist > 7:   return frames[1] if len(frames) > 1 else frames[0]
        if dist > 4.5: return frames[2] if len(frames) > 2 else frames[-1]
        if dist > 2.5: return frames[3] if len(frames) > 3 else frames[-1]
        return frames[4] if len(frames) > 4 else frames[-1]

    if sprite_id in TREE_SPRITES:
        frames = OBJECT_SPRITES[sprite_id]   # 3 frames: [far, mid, near]
        if dist > 8:   return frames[0]       # FAR  — tiny silhouette
        if dist > 3.5: return frames[1]       # MID  — medium shape
        return frames[2]                       # NEAR — full detail

    if sprite_id in OBJECT_SPRITES:
        return OBJECT_SPRITES[sprite_id][0]

    return ["  ?  "]


# ═══════════════════════════════════════════════════════════════════
#  FLOOR ITEMS  — ASCII art shown when an item is near on the ground
# ═══════════════════════════════════════════════════════════════════

FLOOR_ITEM_SPRITES = {
    'sword':      [" /| ", "/_| ", "  | ", " \\' "],
    'dagger':     [" /  ", "/_  ", " '  "],
    'longsword':  [" /| ", "/_| ", "  | ", "  | ", "  ' "],
    'shortsword': [" /| ", "/_| ", "  ' "],
    'mace':       [" [O] ", "  |  ", "  |  "],
    'axe':        [" /\\ ", "|  |", " \\/ ", "  |  "],
    'hammer':     [" [=] ", "  |  ", "  |  ", "  |  "],
    'bow':        [" ) ", ")|(", " ) "],
    'shortbow':   [" ) ", ")|(", " ) "],
    'longbow':    ["  ) ", " )|(", "  ) ", "  ) "],
    'armor':      [" /--\\ ", "| [] |", " \\--/ "],
    'leather':    [" /--\\ ", "| .. |", " \\--/ "],
    'chainmail':  [" /--\\ ", "|####|", " \\--/ "],
    'plate':      [" /==\\ ", "|====|", "|====|", " \\==/ "],
    'shield':     [" /--\\ ", "| O  |", " \\--/ "],
    'spellbook':  [" .---. ", " |***| ", " |***| ", " '---' "],
    'tome':       [" .---. ", " |***| ", " |***| ", " '---' "],
    'potion':     ["  .  ", " / \\ ", "|   |", " \\_/ "],
    'elixir':     ["  .  ", " /~\\ ", "|~~~|", " \\_/ "],
    'scroll':     [" /--\\ ", "| ~~ |", "| ~~ |", " \\--/ "],
    'gold':       [" ooo ", "o$$$o", " ooo "],
    'arrows':     [">>>", "---", ">>>"],
    'pickaxe':    [" /--o", "/   |", "    |", "    \\"],
    'iron_ore':   [" .--. ", " |Fe |", " '--' "],
    'gold_ore':   [" .--. ", " |Au |", " '--' "],
    'gem':        [" /\\ ", "/  \\", "\\<>/", " \\/ "],
    'item':       [" .-. ", " | | ", " '-' "],
}


# ── SPRITES alias for backward compat ────────────────────────────
SPRITES = ENEMY_SPRITES


# ═══════════════════════════════════════════════════════════════════
#  HAND / WEAPON SPRITES  (primera persona, esquina inferior derecha)
# ═══════════════════════════════════════════════════════════════════

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
        r"     \\",
        r"      ",
    ],
    'spear': [
        r"   /\  ",
        r"   ||  ",
        r"  /|   ",
        r" / |   ",
        r"/      ",
        r"`      ",
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
    'hammer': [
        r" [=====]",
        r" |     |",
        r" [=====]",
        r"   \    ",
        r"    \   ",
        r"     \  ",
        r"      ` ",
    ],
    'battleaxe': [
        r"  /\/\  ",
        r" /####\ ",
        r" \####/ ",
        r"  \/\/  ",
        r"   \    ",
        r"    \   ",
        r"     `  ",
    ],
}

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


def get_hand_sprite(player, anim_state: str = 'idle') -> tuple:
    """
    Devuelve (art_lines, color_ansi, offset_row) para el ítem en mano.
    anim_state: 'idle' | 'attack' | 'block'
    """
    def _fg(r, g, b): return f'\033[38;2;{r};{g};{b}m'

    weap  = player.equipped.get('weapon')
    bow   = player.equipped.get('bow')
    book  = player.equipped.get('spellbook')
    armor = player.equipped.get('armor')
    has_shield = bool(armor and (
        armor.get('block', 0) > 0 or
        'shield' in armor.get('name', '').lower()
    ))

    name = ''
    if weap:  name = weap.get('name', '').lower()
    elif bow: name = bow.get('name', '').lower()
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

    if weap:   base_color = _fg(200, 210, 220)
    elif bow:  base_color = _fg(180, 140,  70)
    elif book: base_color = _fg(140, 100, 220)
    else:      base_color = _fg(220, 180, 140)

    anim_color = base_color
    offset_row = 0

    if anim_state == 'block' and has_shield:
        art        = BLOCK_FRAME
        anim_color = _fg(160, 200, 240)
        offset_row = -2

    elif anim_state == 'attack':
        attack_art = None
        for key in sorted(ATTACK_OVERLAY.keys(), key=len, reverse=True):
            if key in name:
                attack_art = ATTACK_OVERLAY[key]
                break
        if attack_art is None:
            attack_art = ATTACK_OVERLAY['fist'] if not (weap or bow or book) else ATTACK_OVERLAY.get('sword', ATTACK_OVERLAY['fist'])
        art        = attack_art
        if weap:   anim_color = _fg(240, 240, 120)
        elif bow:  anim_color = _fg(220, 190,  80)
        elif book: anim_color = _fg(200, 120, 255)
        else:      anim_color = _fg(255, 200, 140)
        offset_row = -1

    return art, anim_color, offset_row


def get_floor_sprite(item):
    """Return ASCII art lines for an item on the floor."""

    if not item:
        return None
    for key in (item.get("id", ""), item.get("name", "").lower(), item.get("type", "")):
        if key in FLOOR_ITEM_SPRITES:
            return FLOOR_ITEM_SPRITES[key]
    name = item.get("name", "").lower()
    for k, v in FLOOR_ITEM_SPRITES.items():
        if k in name:
            return v
    return FLOOR_ITEM_SPRITES["item"]
