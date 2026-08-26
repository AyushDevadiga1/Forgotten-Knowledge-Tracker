"""
OCR Text Extraction & Quality Filtering
Improves text quality at the source before it reaches the database
"""

import re
from typing import Dict, List, Tuple
import numpy as np

# ============================================================
# CONCEPT PLAUSIBILITY FILTER
# ============================================================

# Common OCR/word-fragment artifacts that are never useful concepts.
_FRAGMENT_BLOCKLIST = frozenset(
    {
        "ano",
        "ity",
        "tion",
        "ing",
        "ent",
        "ion",
        "ati",
        "ght",
        "ack",
        "ess",
        "ere",
        "ive",
        "ous",
        "igh",
        "ord",
        "heh",
        "bene",
        "tae",
        "eve",
        "ane",
        "ation",
        # High-confidence UI-colon/suffix fragments ('Downloads:' â†’ 'ase', etc.)
        "ase",
        "ade",
        "ate",
        "ene",
        "ine",
        "ose",
        "one",
        "ide",
        "ies",
        "ted",
        "red",
        "res",
        "ers",
        "ans",
        "ant",
        "est",
        "ons",
        "ues",
        "ates",
        "ines",
        "ades",
        "eses",
        "erss",
    }
)

# Short no-vowel acronyms that are legitimately useful despite the vowel rule.
_ACRONYM_WHITELIST = frozenset(
    {
        "sql",
        "css",
        "html",
        "http",
        "https",
        "ftp",
        "iss",
        "ssh",
        "rna",
        "dna",
        "api",
        "sdk",
        "gps",
        "cpu",
        "ram",
        "os",
        "url",
        "uri",
        "git",
        "vpn",
        "dns",
        "tcp",
        "udp",
        "xml",
        "json",
        "yaml",
        "toml",
        "csv",
        "pdf",
        "db",
        "ui",
        "ux",
        "io",
        "js",
        "ts",
        "atp",
        "ndp",
        "adp",
    }
)

# Genuine 3-letter English words a student might actually study. Standalone
# 3-letter concepts are ONLY accepted if they are whitelisted acronyms or in
# this set â€” otherwise every 'ase'/'res'-style OCR fragment and single-letter
# chrome residue would pass the structural rules. Multi-word phrases are not
# restricted this way ('world war 2' needs 'war', 'net working capital' needs
# 'net').
_THREE_LETTER_WORDS = frozenset(
    {
        "act",
        "add",
        "age",
        "aid",
        "aim",
        "air",
        "ape",
        "arc",
        "arm",
        "art",
        "axe",
        "bar",
        "bat",
        "bay",
        "bed",
        "bee",
        "bet",
        "bid",
        "bin",
        "bit",
        "bow",
        "box",
        "boy",
        "bud",
        "bug",
        "bus",
        "buy",
        "cab",
        "cap",
        "car",
        "cat",
        "cop",
        "cow",
        "cry",
        "cue",
        "cup",
        "cut",
        "dam",
        "day",
        "den",
        "die",
        "dig",
        "dim",
        "dip",
        "dog",
        "dot",
        "dry",
        "dye",
        "ear",
        "eat",
        "egg",
        "elm",
        "end",
        "era",
        "eye",
        "fan",
        "far",
        "fee",
        "few",
        "fig",
        "fin",
        "fit",
        "fix",
        "fly",
        "fog",
        "fox",
        "fry",
        "fun",
        "fur",
        "gap",
        "gas",
        "gel",
        "gem",
        "gin",
        "god",
        "gum",
        "gun",
        "gut",
        "gym",
        "hat",
        "hay",
        "hen",
        "hip",
        "hit",
        "hoe",
        "hog",
        "hop",
        "hot",
        "hub",
        "hue",
        "big",
        "dug",
        "hug",
        "hum",
        "hut",
        "ill",
        "imp",
        "ink",
        "inn",
        "ion",
        "jam",
        "jar",
        "jaw",
        "jet",
        "jog",
        "jug",
        "keg",
        "kid",
        "kin",
        "kit",
        "lab",
        "lag",
        "lap",
        "law",
        "lay",
        "lid",
        "lie",
        "lip",
        "lit",
        "log",
        "lot",
        "low",
        "mad",
        "map",
        "mat",
        "men",
        "met",
        "mid",
        "mix",
        "mob",
        "mud",
        "nap",
        "nod",
        "nut",
        "oak",
        "oar",
        "oat",
        "odd",
        "oil",
        "old",
        "opt",
        "orb",
        "ore",
        "pad",
        "pan",
        "par",
        "pat",
        "paw",
        "pay",
        "pea",
        "pen",
        "pet",
        "pie",
        "pig",
        "pin",
        "pit",
        "pod",
        "pop",
        "pot",
        "pro",
        "pub",
        "rag",
        "ram",
        "ran",
        "rap",
        "rat",
        "raw",
        "ray",
        "rib",
        "rim",
        "rip",
        "rob",
        "rod",
        "rot",
        "row",
        "rub",
        "rug",
        "rum",
        "run",
        "rut",
        "sad",
        "sap",
        "sat",
        "saw",
        "say",
        "sea",
        "see",
        "sin",
        "sip",
        "sir",
        "sit",
        "six",
        "ski",
        "sky",
        "sly",
        "sob",
        "son",
        "sow",
        "spa",
        "spy",
        "sun",
        "tab",
        "tag",
        "tan",
        "tap",
        "tax",
        "tea",
        "ten",
        "tie",
        "tin",
        "tip",
        "toe",
        "ton",
        "top",
        "tot",
        "tow",
        "toy",
        "try",
        "tub",
        "tug",
        "two",
        "use",
        "van",
        "vat",
        "vet",
        "vie",
        "vow",
        "wad",
        "wag",
        "war",
        "wax",
        "way",
        "web",
        "wed",
        "wet",
        "wig",
        "win",
        "wit",
        "woe",
        "wry",
        "yak",
        "yam",
        "zip",
        "ice",
        "icy",
        "jay",
        "job",
        "joy",
        "key",
        "lad",
        "led",
        "leg",
        "net",
        "one",
    }
)

# Function words allowed INSIDE a multi-word phrase ("c3 and c4 plants",
# "systems of equations") but never as a concept on their own.
_PHRASE_CONNECTORS = frozenset(
    {
        "and",
        "or",
        "the",
        "of",
        "for",
        "to",
        "in",
        "on",
        "at",
        "with",
        "by",
        "o",
        "vs",
        "versus",
        "a",
        "an",
        "as",
        "from",
        "into",
        "during",
        "after",
        "before",
        "between",
        "under",
        "over",
        "per",
    }
)

# Observed OCR misreads / glued screen-chrome tokens that are structurally
# invisible (vowel-rich, normal-looking length) but never study content.
# These came straight out of live E2E tracking â€” the sticky UI text that the
# camera keeps re-reading. They are blocked at ingest so they never pollute
# tracked_concepts again.
_OCR_NOISE = frozenset(
    {
        "uktantigtaaty",
        "uktantagtantyf",
        "annletae",
        "dtrarre",
        "aofieedit",
        "aofikefdit",
        "oreerat",
        "enoea",
        "aannup",
        "youlube",
        "exlorer",
        "andbekgt",
        "teasanc",
        "timetine",
        "textprunall",
        "csonwiagrceov",
        "laqithub",
        "sbodiidts",
        "yak",
        "aye",
        "foy",
        "campusx",
        "askgemini",
        "hxagent",
        "boyton",
        "canfigfor",
        "fullsuite",
        "lomfrackerappi",
        "allpipelines",
        "sarchitecture",
        "debugcantole",
        "goorunferminalhelp",
        "ocbugconsole",
        "qcommands",
        "qoyoutubecomwatenfor",
        "statuscode",
        "newsession",
        "redacted",
        "aofleedit",
        "sgoigs",
        "tez",
        "blopencode",
        "csondwiagreov",
        "goowias",
        "woe",
        "mereadme",
        "boython",
        "tatlea",
        "ses",
        "csonwadr",
        "mets",
        "lanter",
        "orta",
        "vaqthuty",
        "ter",
        "compusx",
        "colabreseurch",
        "iole",
        "uspearecreanled",
        "problemsoutput",
        "ingusing",
        "srketonview",
        "darchitecture",
        "qoyortubecomintens",
        "urihttp",
        "answeringsystemusing",
        "bjpython",
        "bpython",
        # Live-capture misreads (WhatsApp/PDF/Chrome chrome overlaid on study
        # content, captured 2026-08): vowel-rich, normal-length, never concepts.
        "deapof",
        "bda",
        "pdt",
        "wrbwtetepp",
        "webwhalsapp",
        "uwnsrgp",
        "yestetcayat",
        "oalsockrrarks",
        "fednpof",
        "gvrwnsaryp",
        "coalboctrrarks",
        "coalboctrrark",
        "abrfowe",
        "edpof",
        "svwnacrsp",
        "rol",
        "cow",
        "com",
        "yestercayat",
        # Second live-capture pass (Downloads / FKT IDE / bda PDF chrome, 2026-08):
        # confidence-filtered at the source now, but kept here so webcam-path or
        # direct add_concept calls can never resurrect them.
        "ybpteess",
        "bownloads",
        "cohlecaserstho",
        "cobiecfeevhp",
        "aweatrge",
        "feteany",
        "abeeeaes",
        "askgemint",
        "feoe",
        "edpofx",
    }
)

# Function words that are never useful as a whole-concept string.
_STOPWORD_CONCEPTS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "might",
        "must",
        "can",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "by",
        "with",
        "about",
        "as",
        "if",
        "that",
        "this",
        "it",
        "what",
        "when",
        "where",
        "why",
        "how",
        "which",
        "who",
        "you",
        "your",
        "they",
        "them",
        "we",
        "our",
        "me",
        "my",
        "i",
    }
)

# UI chrome / browser elements that appear on screen but are never study
# concepts.  These are filtered from OCR and browser-extension ingest.
_UI_ELEMENT_BLOCKLIST = frozenset(
    {
        # Browser chrome
        "explorer",
        "firefox",
        "chrome",
        "browser",
        "bookmarks",
        "history",
        "downloads",
        "extensions",
        "settings",
        "incognito",
        "newtab",
        "newwindow",
        "tab",
        "tabs",
        "sidebar",
        # OS / window chrome
        "terminal",
        "command",
        "prompt",
        "powershell",
        "cmd",
        "console",
        "windows",
        "taskbar",
        "system",
        "desktop",
        "folder",
        "folders",
        "recycle",
        "shortcut",
        "properties",
        # App UI elements
        "menu",
        "file",
        "edit",
        "view",
        "insert",
        "format",
        "tools",
        "help",
        "window",
        "options",
        "preferences",
        "toolbar",
        "statusbar",
        "close",
        "minimize",
        "maximize",
        "restore",
        "resize",
        # Generic screen text that looks like a concept but is just UI
        "context",
        "ports",
        "youtube",
        "fashion",
        "total",
        "round",
        "problems",
        "device",
        "devices",
        "activate",
        "commands",
        "legacy",
        "currency",
        "language",
        "search",
        "results",
        "loading",
        "error",
        "warning",
        "success",
        "failed",
        "cancel",
        "submit",
        "reset",
        "apply",
        "save",
        "discard",
        "undo",
        "redo",
        "copy",
        "paste",
        "cut",
        "select",
        "deselect",
        "refresh",
        "reload",
        "update",
        "upgrade",
        "install",
        "uninstall",
        "enable",
        "disable",
        "start",
        "stop",
        "pause",
        "resume",
        "play",
        "record",
        "mute",
        "unmute",
        "volume",
        "brightness",
        "contrast",
        "saturation",
        # Code editor chrome (visible on screen but not concepts)
        "line",
        "column",
        "indent",
        "outdent",
        "wrap",
        "split",
        "compile",
        "build",
        "deploy",
        "debug",
        "run",
        "execute",
        "import",
        "export",
        "upload",
        "download",
        "sync",
        "commit",
        "push",
        "pull",
        "merge",
        "branch",
        "stash",
        "checkout",
        "rebase",
        "cherry",
        "git",
        "github",
        "gitlab",
        "bitbucket",
        "npm",
        "pip",
        "node",
        "python",
        "java",
        "ruby",
        "golang",
        "rust",
        "vscode",
        "vim",
        "emacs",
        "nano",
        "sublime",
    }
)

# Per-token structural limits. Real study terms sit well inside these bounds;
# glued OCR chains, consonant-cluster noise, and vowel soup get rejected.
_MAX_TOKEN_LENGTH = 20
_MAX_CONSECUTIVE_CONSONANTS = 5  # 'synthesis'/'photosynthesis' reach 5 legitimately
_MIN_VOWEL_RATIO = 0.12  # keeps 'pytorch' (0.14); 'strengths' (0.11) stays out
_MAX_VOWEL_RATIO = 0.85  # high enough to keep 'queue'; 'enoea' is in _OCR_NOISE

_VOWELS = frozenset("aeiou")
_REPEATED_RUN = re.compile(r"(.)\1\1")  # three or more identical chars

# ---------------------------------------------------------------------------
# English dictionary gate (P0 fix for OCR gibberish pollution)
# ---------------------------------------------------------------------------
_ENGLISH_WORDS = frozenset()


def _load_english_words():
    global _ENGLISH_WORDS
    if _ENGLISH_WORDS:
        return _ENGLISH_WORDS
    try:
        from pathlib import Path as _P

        wl_path = _P(__file__).resolve().parent.parent / "data" / "english_words.txt"
        words = {line.strip().lower() for line in wl_path.open() if line.strip()}
        _ENGLISH_WORDS = frozenset(words)
    except Exception:
        _ENGLISH_WORDS = frozenset()
    return _ENGLISH_WORDS


# English morphemes (4+ chars). Words NOT in the wordlist must contain at
# least one of these to be accepted.  Longer patterns are far less likely
# to appear by chance in gibberish than 3-char trigrams.
_ENGLISH_TRIGRAMS = frozenset(
    {
        # Suffixes
        "tion",
        "sion",
        "ment",
        "ness",
        "able",
        "ible",
        "ally",
        "ence",
        "ance",
        "ical",
        "ular",
        "uous",
        "ious",
        "eous",
        "ward",
        "wise",
        "ling",
        "ated",
        "ting",
        "ring",
        "ding",
        "ning",
        "king",
        "sing",
        "ving",
        "zing",
        "cing",
        "ized",
        "ised",
        "ship",
        "hood",
        "like",
        "less",
        "ful",
        "ous",
        "ive",
        "ing",
        "ity",
        "ure",
        "ory",
        "ary",
        "ant",
        "ent",
        "ist",
        "ism",
        # Common roots/prefixes (4+ chars)
        "bio",
        "neuro",
        "psych",
        "chem",
        "phys",
        "math",
        "eco",
        "syn",
        "ana",
        "meta",
        "epi",
        "hypo",
        "gene",
        "morph",
        "ology",
        "graph",
        "scope",
        "meter",
        "path",
        "genic",
        "arch",
        "plast",
        "cyte",
        "zyme",
        "trop",
        "lyse",
        # 3-char suffixes removed: too short, appear by chance in gibberish
        # Common word stems (4+ chars)
        "cell",
        "atom",
        "mass",
        "wave",
        "heat",
        "work",
        "type",
        "form",
        "part",
        "role",
        "unit",
        "step",
        "case",
        "group",
        "class",
        "order",
        "level",
        "phase",
        "point",
        "place",
        "state",
        "system",
        "model",
        "study",
        "brain",
        "nerve",
        "muscle",
        "blood",
        "bone",
        "heart",
        "plant",
        "human",
        "force",
        "energy",
        "power",
        "light",
        "data",
        "test",
        "social",
        "global",
        "local",
        "mental",
        "digital",
        "visual",
        "audio",
        "optic",
        "solar",
        "marine",
        # Common study-term morphemes (4+ chars)
        "mach",
        "hine",
        "prop",
        "agat",
        "back",
        "drop",
        "soft",
        "loss",
        "func",
        "norm",
        "batch",
        "learn",
        "embed",
        "optim",
        "activ",
        "layer",
        "depth",
        "width",
        "kernel",
        "epoch",
        "train",
        "label",
        "input",
        "param",
        "hyper",
        "tune",
        "tuning",
        "gradient",
        "converge",
        "diverge",
        "sigmoid",
        "relu",
        "leaky",
        "adam",
    }
)


def _has_repeated_run_noise(word: str) -> bool:
    """True if >50% of a word's chars sit in doubled runs ('aannup' -> 4/6).

    Threshold is 0.5, not 0.4: real words like 'tree'/'meeting' reach 50%
    ('ee'/'ee'), but pure doubled-run garbage ('aannup' at 0.67) still trips.
    """
    runs, i, n = 0, 0, len(word)
    while i < n:
        j = i
        while j + 1 < n and word[j] == word[j + 1]:
            j += 1
        if j > i:
            runs += j - i + 1
        i = j + 1
    return n > 0 and runs / n > 0.5


def is_plausible_concept(text) -> bool:
    """Heuristic filter for OCR/keyword fragments that are not real concepts.

    Catches the common OCR failure modes seen in live tracking:
    short word fragments ('ano', 'ity'), vowel-less garbage ('hty'), and
    doubled-character noise ('aannup'). Multi-word phrases pass only if
    every word is plausible â€” with function-word connectors ('and', 'the',
    'of') and short alphanumeric tokens ('c3', 'c4', 'python3') allowed.
    ALL-CAPS acronyms (SQL, CSS, HTML) are allowed even without a vowel so
    they are not dropped.
    """
    if not text or not isinstance(text, str):
        return False
    stripped = text.strip()
    if not stripped or len(stripped) < 3 or len(stripped) > 80:
        return False
    if stripped.lower() in _STOPWORD_CONCEPTS:
        return False
    # Study-term whitelist: bypass UI blocklist for known study terms.
    if stripped.lower() in _STUDY_TERM_WHITELIST:
        return True
    if stripped.lower() in _UI_ELEMENT_BLOCKLIST:
        return False

    tokens = re.findall(r"[A-Za-z0-9]+", stripped)
    if not tokens:
        return False

    multiword = len(tokens) > 1
    return all(_is_plausible_token(token, multiword) for token in tokens)


def _is_plausible_token(token: str, multiword: bool) -> bool:
    """Is a single token (possibly 'c3'-style or a connector) plausible?"""
    if not token:
        return False

    if token.isalpha():
        low = token.lower()
        if low in _FRAGMENT_BLOCKLIST or low in _OCR_NOISE:
            return False
        # Function-word connectors are fine inside a phrase, never alone.
        if low in _PHRASE_CONNECTORS:
            return multiword
        return _is_plausible_word(low)

    # Token contains digits â€” 'c3', 'python3', '1995'.
    letters = re.findall(r"[a-z]", token.lower())
    digits = re.findall(r"[0-9]", token)
    if not letters:
        # Pure number: only meaningful as part of a phrase ('world war 2').
        return multiword and len(digits) <= 4
    if len(token) > 8:
        return False  # 'g42dfgh7' -- glued OCR
    # Mixed alpha+digit tokens: the letter portion must itself be a plausible
    # word (e.g. 'python3' passes because 'python' is real; 'xyz123' fails
    # because 'xyz' is not).  Short tokens like 'c3'/'g2' are allowed only
    # if the letter part is <= 2 chars (version-style labels).
    letter_part = "".join(letters)
    if len(letter_part) <= 2:
        return True  # 'c3', 'g2', 'v2' -- version labels, harmless
    return _is_plausible_word(letter_part)


# Legitimate study terms that bypass trigram/dictionary quality checks.
# These are real words/concepts that the quality filter incorrectly rejects
# due to rare trigram patterns or not being in the English wordlist.
_STUDY_TERM_WHITELIST = frozenset(
    {
        # Computer Science
        "monad",
        "functor",
        "applicative",
        "curry",
        "compose",
        "lens",
        "phantom",
        "algebraic",
        "isomorphic",
        "polymorphic",
        "recursive",
        "immutable",
        "mutable",
        "declarative",
        "imperative",
        "referential",
        # Cryptocurrency/Blockchain
        "bitcoin",
        "ethereum",
        "blockchain",
        "cryptocurrency",
        # Programming Languages
        "python",
        "javascript",
        "typescript",
        "haskell",
        "scala",
        "clojure",
        "erlang",
        "elixir",
        "rust",
        "golang",
        "kotlin",
        "swift",
        # Frameworks/Libraries
        "react",
        "angular",
        "vue",
        "django",
        "flask",
        "fastapi",
        "tensorflow",
        "pytorch",
        "pandas",
        "numpy",
        # Rare English (legitimate study terms)
        "defenestration",
        "sesquipedalian",
        "quixotic",
        "obsequious",
        "perspicacious",
        "ephemeral",
        "ubiquitous",
        "paradigm",
        "heuristic",
        "ontology",
        "epistemology",
        "dialectic",
        # Scientific terms
        "photosynthesis",
        "mitochondria",
        "chloroplast",
        "thylakoid",
        "glycolysis",
        "chromosome",
        "chromatid",
        "telomere",
        # Mathematics
        "eigenvector",
        "eigenvalue",
        "determinant",
        "convolution",
        "manifold",
        "topology",
        "homomorphism",
        "isomorphism",
    }
)


def _is_plausible_word(word: str) -> bool:
    if len(word) < 3:
        return False
    low = word.lower()
    if low in _FRAGMENT_BLOCKLIST:
        return False
    if low in _OCR_NOISE:
        return False
    # All-caps acronyms pass regardless of vowels.
    if word.isupper() and len(word) <= 6:
        return True
    if low in _ACRONYM_WHITELIST:
        return True
    # Study-term whitelist: bypass trigram/dictionary checks for known terms.
    if low in _STUDY_TERM_WHITELIST:
        return True
    # Standalone 3-letter non-acronym words must be known English words â€”
    # otherwise 'ase'/'res'-style suffix fragments pass every structural rule.
    if len(low) == 3 and low not in _THREE_LETTER_WORDS:
        return False
    has_vowel = any(c in _VOWELS for c in low)
    has_consonant = any(c not in _VOWELS for c in low)
    if not has_vowel or not has_consonant:
        return False
    if len(low) > _MAX_TOKEN_LENGTH:
        return False
    vowel_ratio = sum(1 for c in low if c in _VOWELS) / len(low)
    if vowel_ratio < _MIN_VOWEL_RATIO or vowel_ratio > _MAX_VOWEL_RATIO:
        return False
    # Longest run of consecutive consonants (OCR merges text into clusters).
    best_run = cur_run = 0
    for c in low:
        if c not in _VOWELS:
            cur_run += 1
            if cur_run > best_run:
                best_run = cur_run
        else:
            cur_run = 0
    if best_run > _MAX_CONSECUTIVE_CONSONANTS:
        return False
    if _REPEATED_RUN.search(word):
        return False
    if _has_repeated_run_noise(word):
        return False
    # -- Dictionary gate (P0: blocks OCR gibberish like 'aastha', 'pebeoge') --
    # Words >= 5 letters must be in the English wordlist OR pass structural
    # heuristics that distinguish real study terms from glued-together gibberish.
    if len(low) >= 5:
        # Reject words where one letter dominates (>45%) -- catches 'aastha',
        # 'pebeoge' and similar OCR garbage with repeated letters.
        from collections import Counter as _C

        _counts = _C(low)
        if _counts.most_common(1)[0][1] / len(low) > 0.45:
            return False
        english_words = _load_english_words()
        if low not in english_words:
            # Not in dictionary.  Two-tier check:
            # 1. Common compound-word stems in study material.
            # 2. Trigram structural coverage for everything else.
            _COMPOUND_STEMS = frozenset(
                {
                    "back",
                    "over",
                    "drop",
                    "soft",
                    "cross",
                    "multi",
                    "auto",
                    "un",
                    "non",
                    "pre",
                    "post",
                    "sub",
                    "super",
                    "inter",
                    "intra",
                    "trans",
                    "mono",
                    "poly",
                    "neo",
                    "pseudo",
                    "quasi",
                    "semi",
                    "anti",
                    "pro",
                    "micro",
                    "macro",
                    "nano",
                    "mega",
                    "giga",
                    "tele",
                    "neuro",
                    "psych",
                    "chem",
                    "phys",
                    "bio",
                    "eco",
                    "geo",
                    "math",
                    "info",
                    "cyber",
                    "crypto",
                    "quantum",
                }
            )
            has_stem = any(low.startswith(s) for s in _COMPOUND_STEMS)
            if not has_stem:
                # For short non-dictionary words that end in common English
                # suffixes (-tion, -sion, -ment, -ness, etc.), require that
                # the root before the suffix has substance.  Catches gibberish
                # like 'abtion' (2-char root) while allowing 'equations'
                # (4-char root 'equa').
                _LONG_SUFFIXES = (
                    "tion",
                    "sion",
                    "ment",
                    "ness",
                    "able",
                    "ible",
                    "ful",
                    "less",
                    "ous",
                    "ive",
                    "ity",
                    "ence",
                    "ance",
                    "ure",
                    "ary",
                    "ory",
                )
                for suf in _LONG_SUFFIXES:
                    if low.endswith(suf) and len(low) - len(suf) < 3:
                        return False
                # No recognized stem: require aggregate trigram coverage
                # >= 30%.  Blocks pure gibberish that shares no morphemes
                # with English; lets legitimate non-dictionary words
                # through (e.g. 'abtion' with 'tion' at 67% coverage).
                covered = set()
                for tri in _ENGLISH_TRIGRAMS:
                    start = 0
                    while True:
                        idx = low.find(tri, start)
                        if idx == -1:
                            break
                        for k in range(idx, idx + len(tri)):
                            covered.add(k)
                        start = idx + 1
                coverage = len(covered) / len(low)
                if coverage < 0.30:
                    return False
    # -- Short word gate (4 chars): reject non-dictionary 4-letter words
    # unless they are known English words.  Catches 'bnet', 'boge',
    # 'drve', 'etat', 'nsre', etc.
    if len(low) == 4 and low.isalpha():
        english_words = _load_english_words()
        if low not in english_words:
            return False
    return True


# ============================================================
# TEXT QUALITY VALIDATION
# ============================================================

# Minimum useful text length
MIN_TEXT_LENGTH = 3
MAX_TEXT_LENGTH = 500

# Common UI elements and garbage to exclude
UI_GARBAGE = {
    # Buttons
    "ok",
    "cancel",
    "save",
    "close",
    "back",
    "next",
    "submit",
    "delete",
    "edit",
    "add",
    "remove",
    "copy",
    "paste",
    "undo",
    "redo",
    "search",
    "filter",
    "sort",
    "download",
    "upload",
    "settings",
    "help",
    "about",
    "logout",
    "login",
    "register",
    "sign in",
    "sign up",
    "yes",
    "no",
    "maybe",
    "skip",
    "more",
    "less",
    "expand",
    "collapse",
    "show",
    "hide",
    # Common UI text
    "menu",
    "file",
    "view",
    "insert",
    "format",
    "tools",
    "window",
    "label",
    "status",
    "progress",
    "loading",
    "buffering",
    "please wait",
    "processing",
    "updating",
    "synchronizing",
    "connecting",
    "downloading",
    "uploading",
    "saving",
    "initializing",
    "starting",
    "stopping",
    # Common notifications/system
    "notification",
    "alert",
    "warning",
    "error",
    "success",
    "info",
    "message",
    "do not show again",
    "remind me later",
    "never show again",
    "click here",
    "learn more",
    "read more",
    "show more",
    "see all",
    "view all",
    "all items",
    "unknown error occurred",
    # Ads/Spam
    "advertisement",
    "ad",
    "sponsored",
    "promoted",
    "special offer",
    "limited time",
    "click now",
    "click here now",
    "shop now",
    "buy now",
    "order now",
    "sign up now",
    "subscribe",
    "upgrade",
    "premium",
    "pro",
    "plus",
    "elite",
    "vip",
    "exclusive",
    # Empty/placeholder
    "enter text",
    "type something",
    "search...",
    "untitled",
    "unnamed",
    "new document",
    "no title",
    "loading...",
    "error...",
    "null",
    "none",
    "n/a",
    "unknown",
    "blank",
    "empty",
    "no data",
    "not available",
}

# Common OCR errors and misreadings
OCR_CORRECTIONS = {
    "l0": "10",  # Letter l and zero
    "0l": "01",  # Zero and letter l
    "1l": "il",  # 1 and l
    "lI": "li",  # l and capital I
    "O0": "00",  # O and 0
}

# ============================================================
# COHERENCE SCORING
# ============================================================

# Common English word patterns (basic)
COMMON_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "should",
    "could",
    "might",
    "must",
    "can",
    "of",
    "in",
    "on",
    "at",
    "to",
    "for",
    "from",
    "by",
    "with",
    "about",
    "as",
    "if",
    "that",
    "this",
    "it",
    "what",
    "when",
    "where",
    "why",
    "how",
    "which",
    "who",
    "whom",
    "data",
    "system",
    "process",
    "function",
    "method",
    "code",
    "file",
    "folder",
    "document",
}

# Patterns that indicate garbage
GARBAGE_PATTERNS = [
    r'^[!@#$%^&*()_\-+=\[\]{};:\'",.<>?/\\|`~]*$',  # Only special chars
    r"^[0-9]{20,}$",  # Very long number sequence
    r"^[a-z]{2,3}[0-9]{5,}$",  # Code-like gibberish
    r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",  # IP-like (not useful)
    r"^[^\w\s]*$",  # No actual words
    r"[\x00-\x1F\x7F-\x9F]",  # Control characters
]


def is_coherent_text(text: str) -> bool:
    """Check if text appears to be coherent English-like content"""
    if not text or len(text) < 3:
        return False

    # Check for control characters
    if any(ord(c) < 32 or ord(c) > 126 for c in text if ord(c) not in [9, 10, 13]):
        return False

    # Check garbage patterns
    for pattern in GARBAGE_PATTERNS:
        if re.search(pattern, text.lower()):
            return False

    # Must have at least some word characters
    words = re.findall(r"\b\w+\b", text)
    if len(words) == 0:
        return False

    # STRICT: Check for gibberish - text without vowels is likely garbage
    vowels = "aeiouAEIOU"
    text_without_spaces = text.replace(" ", "")
    if len(text_without_spaces) > 5:
        vowel_count = sum(1 for c in text_without_spaces if c in vowels)
        vowel_ratio = vowel_count / len(text_without_spaces)
        if vowel_ratio < 0.15:  # Less than 15% vowels = likely gibberish
            return False

    # Check if mostly common words or reasonable length
    word_diversity = len(set(words)) / len(words) if words else 0

    # Should have some diversity (not just repetition) but not too much
    if word_diversity < 0.3 and len(words) > 10:
        return False  # Too repetitive

    # STRICT: Gibberish detection - random word sequences
    if len(words) > 3:
        # Check if words look like actual English (not random keystrokes)
        legit_words = sum(
            1 for w in words if (len(w) >= 3 and w.lower() in COMMON_WORDS) or any(c in vowels for c in w.lower())
        )
        if legit_words / len(words) < 0.3:  # Less than 30% legitimate-looking
            return False

    return True


# ============================================================
# TEXT CLEANING & PREPROCESSING
# ============================================================


def preprocess_ocr_text(text: str, confidence: float = 1.0) -> Tuple[str, float]:
    """
    Preprocess OCR text and return cleaned text with quality score

    Returns:
        (cleaned_text, quality_score)
    """
    if not text:
        return "", 0.0

    quality_score = 1.0

    # 1. Decode common OCR errors (be conservative)
    for error, correction in OCR_CORRECTIONS.items():
        if error in text.lower():
            text = re.sub(error, correction, text, flags=re.IGNORECASE)
            quality_score -= 0.1  # Penalty for having OCR errors

    # 2. Remove extra whitespace
    text = " ".join(text.split())

    # 3. Remove control characters
    text = "".join(c for c in text if ord(c) >= 32 or c in "\t\n")

    # 4. Remove excessive punctuation at start/end
    text = re.sub(r"^[^\w\s]+", "", text)
    text = re.sub(r"[^\w\s]+$", "", text)

    # 5. Check for mixed case (likely better OCR quality)
    has_upper = any(c.isupper() for c in text)
    has_lower = any(c.islower() for c in text)
    if has_upper and has_lower:
        quality_score += 0.1  # Proper case suggests good OCR

    # 6. Length validation - STRICT
    if len(text) < MIN_TEXT_LENGTH:
        quality_score -= 0.8  # Heavy penalty for too short
    elif len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
        quality_score -= 0.3
    else:
        quality_score += 0.05

    # 7. Coherence check
    if is_coherent_text(text):
        quality_score += 0.15
    else:
        quality_score -= 0.4  # Heavy penalty for incoherent

    # 8. UI garbage check - STRICT
    if text.lower().strip() in UI_GARBAGE:
        quality_score = 0.05  # Direct reject

    # Apply OCR confidence to final score
    quality_score = max(0.0, min(1.0, quality_score * confidence))

    return text.strip(), quality_score


def extract_meaningful_sections(text: str) -> List[str]:
    """
    Extract meaningful sections from text
    (removes headers, footers, navigation elements)
    """
    if not text:
        return []

    # Split into lines
    lines = text.split("\n")

    meaningful_lines = []
    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip likely headers/navigation
        if line.lower() in UI_GARBAGE:
            continue

        # Skip very short lines (likely labels, not content)
        if len(line) < 5 and not any(c.isalpha() for c in line):
            continue

        # Skip lines that are mostly numbers/special chars
        char_types = [c.isalnum() for c in line]
        if sum(char_types) / len(char_types) < 0.3:
            continue

        meaningful_lines.append(line)

    return meaningful_lines


# ============================================================
# ADVANCED FILTERING
# ============================================================


def calculate_text_quality_score(text: str, ocr_confidence: float = 1.0) -> float:
    """
    Calculate comprehensive quality score (0-1)

    Factors:
    - Length validity
    - Character validity
    - Coherence
    - Diversity
    - OCR confidence
    """
    if not text:
        return 0.0

    # STRICT: Start lower for safer filtering
    score = 0.3

    # Length factor (0.2 weight)
    if len(text) < MIN_TEXT_LENGTH or len(text) > MAX_TEXT_LENGTH:
        score -= 0.3
    else:
        score += 0.15

    # Character validity (0.2 weight) - stricter rules
    valid_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in "-_.,()")
    char_ratio = valid_chars / len(text) if text else 0
    if char_ratio > 0.85:
        score += 0.15
    elif char_ratio > 0.6:
        score += 0.05
    else:
        score -= 0.2

    # Coherence factor (0.3 weight) - most important
    if is_coherent_text(text):
        score += 0.25
    else:
        score -= 0.25

    # UI garbage detection (0.15 weight) - STRICT
    text_lower = text.lower().strip()
    if text_lower in UI_GARBAGE:
        return 0.05  # Direct reject for UI garbage

    # Word diversity (0.15 weight)
    words = text.split()
    if len(words) > 0:
        unique_ratio = len(set(words)) / len(words)
        if 0.4 < unique_ratio < 0.99:  # Good diversity but not too much
            score += 0.1
        elif unique_ratio >= 0.99:  # Every word is unique = likely nonsense
            score -= 0.15
        else:
            score -= 0.05

    # OCR confidence factor (0.15 weight)
    score *= ocr_confidence

    return max(0.0, min(1.0, score))


def filter_extraction_results(
    extracted_texts: List[Dict], min_quality: float = 0.4, min_ocr_confidence: float = 0.3
) -> List[Dict]:
    """
    Filter extracted texts by quality metrics

    Input format:
        [{'text': '...', 'confidence': 0.8, 'source': 'OCR'}, ...]

    Output: Filtered list with quality scores
    """
    filtered = []

    for item in extracted_texts:
        text = item.get("text", "")
        ocr_conf = item.get("confidence", 1.0)

        # Skip if OCR confidence too low
        if ocr_conf < min_ocr_confidence:
            continue

        # Clean text
        clean_text, _ = preprocess_ocr_text(text, ocr_conf)

        # Calculate quality
        quality = calculate_text_quality_score(clean_text, ocr_conf)

        # Only keep if meets quality threshold
        if quality >= min_quality:
            filtered.append(
                {
                    "original": text,
                    "cleaned": clean_text,
                    "quality_score": quality,
                    "ocr_confidence": ocr_conf,
                    "status": "VALID",
                }
            )

    return filtered


# ============================================================
# KEYWORD EXTRACTION & VALIDATION
# ============================================================


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract meaningful keywords from text"""
    if not text:
        return []

    # Split into words
    words = re.findall(r"\b\w+\b", text.lower())

    # Filter
    keywords = []
    for word in words:
        # Skip too short
        if len(word) < min_length:
            continue

        # Skip common stopwords (if word is only a stopword)
        if word in COMMON_WORDS and len(word) < 5:
            continue

        # Skip if mostly numbers
        if sum(c.isdigit() for c in word) / len(word) > 0.5:
            continue

        keywords.append(word)

    # Remove duplicates, keep order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:10]  # Top 10 keywords max


# ============================================================
# INTEGRATION FUNCTION
# ============================================================


def validate_and_clean_extraction(raw_extracted_text: str, ocr_confidence: float = 1.0) -> Dict:
    """
    Main function to validate and clean text extraction

    Returns complete validation report
    """
    # Initial check
    if not raw_extracted_text or len(raw_extracted_text.strip()) == 0:
        return {
            "status": "REJECTED",
            "reason": "Empty text",
            "quality_score": 0.0,
            "cleaned_text": "",
            "keywords": [],
            "is_useful": False,
        }

    # Preprocess
    clean_text, preprocess_score = preprocess_ocr_text(raw_extracted_text, ocr_confidence)

    # Check coherence
    if not is_coherent_text(clean_text):
        return {
            "status": "REJECTED",
            "reason": "Text not coherent (likely garbage)",
            "quality_score": preprocess_score,
            "cleaned_text": clean_text,
            "keywords": [],
            "is_useful": False,
        }

    # Calculate quality
    quality_score = calculate_text_quality_score(clean_text, ocr_confidence)

    # Extract keywords
    keywords = extract_keywords(clean_text)

    # Decision
    is_useful = quality_score >= 0.4 and len(keywords) > 0
    status = "REJECTED" if quality_score <= 0.1 else "ACCEPTED" if is_useful else "QUESTIONABLE"

    return {
        "status": status,
        "reason": None,
        "quality_score": quality_score,
        "cleaned_text": clean_text,
        "keywords": keywords,
        "is_useful": is_useful,
        "original_length": len(raw_extracted_text),
        "cleaned_length": len(clean_text),
        "keyword_count": len(keywords),
    }


# ============================================================
# BATCH PROCESSING
# ============================================================


def validate_batch_extraction(extracted_texts: List[str]) -> Dict:
    """
    Process batch of extracted texts and return statistics
    """
    results = {
        "total": len(extracted_texts),
        "accepted": 0,
        "rejected": 0,
        "questionable": 0,
        "avg_quality": 0.0,
        "valid_texts": [],
        "rejected_texts": [],
    }

    quality_scores = []

    for text in extracted_texts:
        validation = validate_and_clean_extraction(text)
        quality_scores.append(validation["quality_score"])

        if validation["status"] == "ACCEPTED":
            results["accepted"] += 1
            results["valid_texts"].append(validation)
        elif validation["status"] == "REJECTED":
            results["rejected"] += 1
            results["rejected_texts"].append({"text": text, "reason": validation["reason"]})
        else:
            results["questionable"] += 1

    results["avg_quality"] = np.mean(quality_scores) if quality_scores else 0.0

    return results
