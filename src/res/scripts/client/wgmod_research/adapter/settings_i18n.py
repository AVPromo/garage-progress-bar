# -*- coding: utf-8 -*-
"""Localize the settings-panel LABELS (see ``bridge/mod_settings.py``).

Scope, deliberately narrow:

* **Only the settings panel is localized** — nothing else. The widget already follows
  the client language by reusing WG's own resource strings (``adapter/i18n.py``).
* **Only the LABELS are localized**, two ways:
  1. **WG feature names** (Research, Upgrades, Field Modifications, Elite System, Elite
     Rewards, Tier XI) — the per-mode checkbox labels reuse WG's own localized strings via
     ``i18n.widget_labels()`` (``FEATURE_WG`` maps each checkbox → its widget-labels key),
     so they match the game exactly in every language and never drift.
  2. **Mod-invented labels** (the three category-header Labels "Modes"/"Formatting"/
     "Layout", the ``showWhenComplete`` and ``ignoreFreeXp`` toggles, the "Position" section
     Label, the two position steppers) — bundled ``{lang: {key: label}}`` tables here,
     English master + per-key fallback.
* **Tooltips are NOT localized.** Every control's tooltip (header + body) is fixed English
  (``_TOOLTIPS_EN``) — it's explanatory help, not a setting, and has no WG string to reuse.
  It is never translated and never routed through i18n. The three category headers are the
  one exception to "every control has a tooltip": they are inert section captions, so they
  carry NO ``_TOOLTIPS_EN`` entry and ``render_panel`` simply omits the ``tooltip`` key for
  them (rather than inventing filler prose).

Everything is PURE except ``client_language()`` (the one guarded
``helpers.getClientLanguage()`` read) and ``panel_text()`` (which pulls the WG labels from
``i18n``). ``render_panel(wg_labels, lang)`` is pure given its args, so it unit-tests with
a fake label dict and the game closed. Ships ``cs de en es fr hu it pl ru tr uk``; unknown
client codes degrade to English (marked when ``i18n.MARK_UNTRANSLATED`` is on).
"""
from wgmod_research._compat import LOG_CURRENT_EXCEPTION
from wgmod_research.adapter import i18n

# The default client language + the value returned when the engine read fails.
DEFAULT_LANGUAGE = u"en"

# getClientLanguage() code quirks -> our table keys. Seeded with the Ukrainian case;
# extend after verifying live codes (Chinese/Portuguese variants, region suffixes).
_ALIASES = {
    u"ua": u"uk",
}

# Per-mode checkbox -> the i18n.widget_labels() key whose WG-localized text is the label.
FEATURE_WG = {
    u"showTechTree": u"headerResearch",         # "Research"
    u"showSkillTree": u"headerSkillTree",        # "Upgrades"
    u"showFieldMods": u"headerFieldMods",        # "Field Modifications"
    u"showEliteRewards": u"headerEliteRewards",   # "Elite Rewards"
    u"showElite": u"headerElite",           # "Elite System"
    u"showPotentialTierXI": u"capTierXI",             # "Tier XI"
}

# English fallback for a feature label, used only if widget_labels() lacks the key.
_FEATURE_EN = {
    u"showTechTree": u"Research",
    u"showSkillTree": u"Upgrades",
    u"showFieldMods": u"Field Modifications",
    u"showEliteRewards": u"Elite Rewards",
    u"showElite": u"Elite System",
    u"showPotentialTierXI": u"Tier XI",
}

# Placeholder for a template row that carries NO text of its own -- the three `Empty`
# spacers in column2 (between the Formatting and Layout groups, before the progressMode
# radio group, and before the "Position" sub-header). _sync_template_text zips these key
# tuples against the STORED components POSITIONALLY, so a textless row must still occupy a
# slot: without it every key after the spacer would shift by one and silently relabel the
# wrong controls. A module-level sentinel (not a bare None literal) so the intent reads at
# the call site. Both consumers skip it -- see render_panel below and
# mod_settings._sync_template_text (its ``t.get(key)`` yields None -> continue).
SPACER = None

# The three CATEGORY header Labels. Rendered BOLD (see render_panel) so they read as
# section captions above their controls; the "position" sub-header is deliberately NOT
# here -- it sits a level below the categories, and bolding it too would flatten the
# hierarchy the spacer and headers exist to create.
HEADER_KEYS = frozenset((u"modes", u"formatting", u"layout"))

# Ordered key lists per column -- the wire order of the controls in ``_template()``. Used
# by mod_settings to walk a stored template in lockstep (Label/Empty rows carry no varName).
# The panel is three named CATEGORIES opened by Label headers ("modes" / "formatting" /
# "layout"), but only TWO columns: Layout is merged into column2 under a spacer, because a
# third column only renders side-by-side when the user's global MSA `multiColumnMode`
# toolbar toggle is ON (default OFF) -- with it off Aslain folds columns round-robin
# (i % columnCount) and column3 would stack UNDER column1 instead. The seven mode
# checkboxes are plain standalone controls (no master switch any more -- see
# mod_settings._template()). The order here MUST match the wire order in _template().
COL1_KEYS = (u"modes", u"showTechTree", u"showFieldMods", u"showPotentialTierXI",
             u"showSkillTree", u"showEliteRewards", u"showElite", u"showWhenComplete")
COL2_KEYS = (u"formatting", u"ignoreFreeXp", u"showPercent", SPACER, u"progressMode",
             SPACER, u"layout", u"scale", SPACER, u"position", u"posX", u"posY")


def _norm(code):
    """Normalize a client language code to a table key (pure, engine-free).

    ``None``/empty -> u"". Otherwise lowercase, ``-`` -> ``_``, apply ``_ALIASES``, and if
    the full code isn't a known block fall back to the primary subtag (``"pt_br"`` ->
    ``"pt"``). Not guaranteed to be a ``_LABELS`` key -- the resolver treats an unknown key
    as "English"."""
    if not code:
        return u""
    c = code.strip().lower().replace(u"-", u"_")
    c = _ALIASES.get(c, c)
    if c in _LABELS:
        return c
    base = c.split(u"_", 1)[0]
    base = _ALIASES.get(base, base)
    return base


# --- MOD-INVENTED LABELS (hand-translated) --------------------------------------------
# Only labels -- these controls' tooltips are the fixed English in _TOOLTIPS_EN (the three
# category headers carry none at all). The six per-mode checkboxes are NOT here (their
# labels come from WG via FEATURE_WG). "modes"/"formatting"/"layout" are the three category
# header Labels, one per column; "position" is the sub-header above the two steppers.
_LABELS = {
    u"en": {
        u"modes": u"Modes",
        u"formatting": u"Formatting",
        u"layout": u"Layout",
        u"showWhenComplete": u"Fully Progressed",
        u"ignoreFreeXp": u"Ignore Free XP",
        u"showPercent": u"Show Progress %",
        u"progressMode": u"Progress Mode",
        u"scale": u"Scale",
        u"position": u"Position (px)",
        u"posX": u"Horizontal (center X)",
        u"posY": u"Vertical (top Y)",
    },
    u"de": {
        u"modes": u"Modi",
        u"formatting": u"Formatierung",
        u"layout": u"Layout",
        u"showWhenComplete": u"Vollständig fortgeschritten",
        u"ignoreFreeXp": u"Freie Erfahrung ignorieren",
        u"showPercent": u"Fortschritt in % anzeigen",
        u"progressMode": u"Fortschrittsmodus",
        u"scale": u"Skalierung",
        u"position": u"Position (px)",
        u"posX": u"Horizontal (Mitte X)",
        u"posY": u"Vertikal (oben Y)",
    },
    u"fr": {
        u"modes": u"Modes",
        u"formatting": u"Mise en forme",
        u"layout": u"Disposition",
        u"showWhenComplete": u"Entièrement progressé",
        u"ignoreFreeXp": u"Ignorer l'expérience libre",
        u"showPercent": u"Afficher la progression en %",
        u"progressMode": u"Mode de progression",
        u"scale": u"Échelle",
        u"position": u"Position (px)",
        u"posX": u"Horizontale (centre X)",
        u"posY": u"Verticale (haut Y)",
    },
    u"es": {
        u"modes": u"Modos",
        u"formatting": u"Formato",
        u"layout": u"Diseño",
        u"showWhenComplete": u"Progreso completo",
        u"ignoreFreeXp": u"Ignorar la experiencia libre",
        u"showPercent": u"Mostrar el progreso en %",
        u"progressMode": u"Modo de progreso",
        u"scale": u"Escala",
        u"position": u"Posición (px)",
        u"posX": u"Horizontal (centro X)",
        u"posY": u"Vertical (arriba Y)",
    },
    u"it": {
        u"modes": u"Modalità",
        u"formatting": u"Formattazione",
        u"layout": u"Disposizione",
        u"showWhenComplete": u"Completamente progredito",
        u"ignoreFreeXp": u"Ignora l'esperienza libera",
        u"showPercent": u"Mostra l'avanzamento in %",
        u"progressMode": u"Modalità di avanzamento",
        u"scale": u"Scala",
        u"position": u"Posizione (px)",
        u"posX": u"Orizzontale (centro X)",
        u"posY": u"Verticale (alto Y)",
    },
    u"pl": {
        u"modes": u"Tryby",
        u"formatting": u"Formatowanie",
        u"layout": u"Układ",
        u"showWhenComplete": u"W pełni ukończone",
        u"ignoreFreeXp": u"Ignoruj wolne doświadczenie",
        u"showPercent": u"Pokaż postęp w %",
        u"progressMode": u"Tryb postępu",
        u"scale": u"Skala",
        u"position": u"Pozycja (px)",
        u"posX": u"Poziomo (środek X)",
        u"posY": u"Pionowo (góra Y)",
    },
    u"cs": {
        u"modes": u"Režimy",
        u"formatting": u"Formátování",
        u"layout": u"Rozvržení",
        u"showWhenComplete": u"Plně dokončeno",
        u"ignoreFreeXp": u"Ignorovat volné zkušenosti",
        u"showPercent": u"Zobrazit postup v %",
        u"progressMode": u"Režim postupu",
        u"scale": u"Měřítko",
        u"position": u"Pozice (px)",
        u"posX": u"Vodorovně (střed X)",
        u"posY": u"Svisle (nahoře Y)",
    },
    u"ru": {
        u"modes": u"Режимы",
        u"formatting": u"Форматирование",
        u"layout": u"Расположение",
        u"showWhenComplete": u"Полностью пройдено",
        u"ignoreFreeXp": u"Игнорировать свободный опыт",
        u"showPercent": u"Показывать прогресс в %",
        u"progressMode": u"Режим прогресса",
        u"scale": u"Масштаб",
        u"position": u"Положение (px)",
        u"posX": u"По горизонтали (центр X)",
        u"posY": u"По вертикали (верх Y)",
    },
    u"uk": {
        u"modes": u"Режими",
        u"formatting": u"Форматування",
        u"layout": u"Розташування",
        u"showWhenComplete": u"Повністю пройдено",
        u"ignoreFreeXp": u"Ігнорувати вільний досвід",
        u"showPercent": u"Показувати прогрес у %",
        u"progressMode": u"Режим прогресу",
        u"scale": u"Масштаб",
        # "Позиція", not "Розташування" -- the latter is the column3 header above it, and
        # two identical captions one under the other read as a duplicated row.
        u"position": u"Позиція (px)",
        u"posX": u"По горизонталі (центр X)",
        u"posY": u"По вертикалі (верх Y)",
    },
    u"hu": {
        u"modes": u"Módok",
        u"formatting": u"Formázás",
        u"layout": u"Elrendezés",
        u"showWhenComplete": u"Teljesen kész",
        u"ignoreFreeXp": u"Szabad tapasztalat mellőzése",
        u"showPercent": u"Haladás megjelenítése %-ban",
        u"progressMode": u"Haladási mód",
        u"scale": u"Méretezés",
        u"position": u"Pozíció (px)",
        u"posX": u"Vízszintes (középpont X)",
        u"posY": u"Függőleges (felső Y)",
    },
    u"tr": {
        u"modes": u"Modlar",
        u"formatting": u"Biçimlendirme",
        u"layout": u"Yerleşim",
        u"showWhenComplete": u"Tamamen ilerlemiş",
        u"ignoreFreeXp": u"Serbest deneyimi yok say",
        u"showPercent": u"İlerlemeyi % olarak göster",
        u"progressMode": u"İlerleme modu",
        u"scale": u"Ölçek",
        u"position": u"Konum (px)",
        u"posX": u"Yatay (merkez X)",
        u"posY": u"Dikey (üst Y)",
    },
}


# --- SCALE DROPDOWN OPTION LABELS (hand-translated) -----------------------------------
# The two option labels for the "scale" radio group: (Default, Large). Kept in their OWN
# table -- NOT in _LABELS -- because options are not per-control label/tooltip rows, so
# folding them into _LABELS would break the label/tooltip key partition (see the
# settings_i18n tests). render_panel attaches the localized pair on t["scale"]["options"];
# English master + per-language fallback (marked on fallback), same policy as _LABELS.
_SCALE_OPTIONS = {
    u"en": (u"Default", u"Large"),
    u"de": (u"Standard", u"Groß"),
    u"fr": (u"Par défaut", u"Grand"),
    u"es": (u"Predeterminado", u"Grande"),
    u"it": (u"Predefinito", u"Grande"),
    u"pl": (u"Domyślny", u"Duży"),
    u"cs": (u"Výchozí", u"Velký"),
    u"ru": (u"По умолчанию", u"Большой"),
    u"uk": (u"За замовчуванням", u"Великий"),
    u"hu": (u"Alapértelmezett", u"Nagy"),
    u"tr": (u"Varsayılan", u"Büyük"),
}


# --- PROGRESS-MODE DROPDOWN OPTION LABELS (hand-translated) ---------------------------
# The two option labels for the "progressMode" radio group: (Current, Current / Required).
# Own table (see _SCALE_OPTIONS rationale). render_panel attaches the localized pair on
# t["progressMode"]["options"]; English master + per-language fallback (marked on
# fallback). Plain "/" only -- never an em-dash (the client renders one as "--").
_PROGRESS_OPTIONS = {
    u"en": (u"Current", u"Current / Required"),
    u"de": (u"Aktuell", u"Aktuell / Benötigt"),
    u"fr": (u"Actuel", u"Actuel / Requis"),
    u"es": (u"Actual", u"Actual / Necesario"),
    u"it": (u"Attuale", u"Attuale / Richiesto"),
    u"pl": (u"Aktualne", u"Aktualne / Wymagane"),
    u"cs": (u"Aktuální", u"Aktuální / Potřebné"),
    u"ru": (u"Текущий", u"Текущий / Требуется"),
    u"uk": (u"Поточний", u"Поточний / Потрібно"),
    u"hu": (u"Jelenlegi", u"Jelenlegi / Szükséges"),
    u"tr": (u"Mevcut", u"Mevcut / Gerekli"),
}


# --- TOOLTIPS: fixed English for every INTERACTIVE control (never translated, never i18n)
# (header, body). The header mirrors the control's English name; the body is the mod's
# own explanatory prose. Deliberately English on every client -- see the module docstring.
# The three category headers (modes / formatting / layout) are inert section captions and
# carry NO entry here -- render_panel then omits their tooltip key entirely.
_TOOLTIPS_EN = {
    u"showWhenComplete": (u"Fully Progressed",
                          u"Keeps the bar visible on vehicles with nothing left to "
                          u"research, upgrade, or unlock. Uncheck to hide the bar once a "
                          u"vehicle is fully progressed."),
    u"ignoreFreeXp": (u"Ignore Free XP",
                      u"Counts only the combat XP you earn on each vehicle toward its "
                      u"progress. Free XP is excluded from the bar, the totals, and the "
                      u"tooltips. Off by default."),
    u"showTechTree": (u"Research",
                      u"The tech-tree progress toward the vehicle's remaining module "
                      u"and next-vehicle unlocks."),
    u"showSkillTree": (u"Upgrades",
                       u"The branching upgrade (skill) tree on Tier XI vehicles."),
    u"showFieldMods": (u"Field Modifications",
                       u"The field-modification steps unlocked once the vehicle is "
                       u"fully researched."),
    u"showEliteRewards": (u"Elite Rewards",
                          u"The tier-exclusive milestone-reward roadmap on prestige "
                          u"vehicles."),
    u"showElite": (u"Elite System",
                   u"The Elite-Levels grade-band progression on prestige vehicles."),
    u"showPotentialTierXI": (u"Tier XI",
                             u"On a Tier X tank that has no Tier XI, once it's fully "
                             u"researched and its field mods are done, track your "
                             u"banked XP (vehicle XP + Free XP) toward the fixed price "
                             u"a Tier XI costs to unlock. Replaces the Elite-Levels bar "
                             u"on those tanks. Off by default."),
    u"scale": (u"Scale",
              u"Sets the on-screen size of the progress bar. Default keeps the standard "
              u"size; Large roughly doubles the bar's width and enlarges its text, icons, "
              u"and tooltip - handy on high-resolution or far-away displays."),
    u"progressMode": (u"Progress Mode",
                      u"Sets what the XP readout shows. Current shows only the XP you "
                      u"have so far; Current / Required shows how much you have out of "
                      u"how much the bar needs."),
    u"showPercent": (u"Show Progress %",
                     u"Adds a progress percentage to the left of the XP readout. Works on "
                     u"its own or alongside Progress Mode. Off by default."),
    u"position": (u"Position",
                  u"Ctrl+drag the bar in the garage to move it, or type exact "
                  u"on-screen pixel coordinates below. Reset returns it to the "
                  u"default position."),
    u"posX": (u"Horizontal position",
              u"The bar's CENTER, in pixels from the left screen edge."),
    u"posY": (u"Vertical position",
              u"The bar's TOP, in pixels from the top screen edge."),
}


def render_panel(wg_labels, lang=None):
    """The full rendered panel text: ``{key: {"text", "tooltip"}}`` for every control
    (PURE given ``wg_labels`` + ``lang``).

    ``text`` (the LABEL) is localized: per-mode checkboxes take WG's own localized name
    from ``wg_labels`` (== ``i18n.widget_labels()``), everything else from the ``_LABELS``
    tables (English-fallback, marked on fallback). ``tooltip`` is the fixed English from
    ``_TOOLTIPS_EN`` -- never translated -- and is OMITTED for the three category headers,
    which have no entry there. The ``SPACER`` sentinel names no control, so it is skipped
    outright (it has no _LABELS row and would KeyError on the English fallback).
    ``lang`` defaults to the client's language.

    The three ``HEADER_KEYS`` come out wrapped in ``<b>...</b>`` (MSA Labels render HTML).
    The wrap happens HERE and ONLY here -- never in the _LABELS tables (translation data
    stays markup-free) and never in ``mod_settings._template()``. Both consumers of this
    function must see the SAME string: _template() builds the fresh template from it, and
    _sync_template_text() compares a STORED component's text against it. If _template()
    wrapped independently, every init would see a mismatch, strip the bold back out, and
    fire a pointless saveState() -- so one source of truth makes that divergence
    impossible by construction."""
    if lang is None:
        lang = client_language()
    code = _norm(lang)
    labels = _LABELS.get(code) or {}
    en_labels = _LABELS[DEFAULT_LANGUAGE]
    wl = wg_labels or {}
    out = {}
    for key in COL1_KEYS + COL2_KEYS:
        if key is SPACER:
            continue
        if key in FEATURE_WG:
            text = wl.get(FEATURE_WG[key]) or _FEATURE_EN[key]   # WG label; i18n self-marks
        else:
            fb = key not in labels
            text = en_labels[key] if fb else labels[key]
            if fb:
                text = i18n._mark(text)
        if key in HEADER_KEYS:
            # Bold AFTER the fallback mark, so a marked fallback stays visible inside it.
            text = u"<b>%s</b>" % text
        out[key] = {u"text": text}
        tip = _TOOLTIPS_EN.get(key)
        if tip is not None:
            out[key][u"tooltip"] = u"{HEADER}%s{/HEADER}{BODY}%s{/BODY}" % tip
        # The two radio groups also carry their localized option labels (see _template()).
        if key == u"scale":
            out[key][u"options"] = _scale_options(code)
        elif key == u"progressMode":
            out[key][u"options"] = _progress_options(code)
    return out


def label(key, lang=None):
    """ONE mod-invented label in the client language -- the same resolution
    ``render_panel`` does for a non-feature control (English master, marked on fallback).
    Exposed because the WIDGET needs one of these strings too: "Fully Progressed"
    (``showWhenComplete``) is also the COMPLETE bar's header, and the game ships no
    equivalent, so ``i18n.headerComplete`` reuses this table instead of duplicating the
    translations. Pure given ``lang``."""
    code = _norm(lang if lang is not None else client_language())
    labels = _LABELS.get(code) or {}
    if key in labels:
        return labels[key]
    return i18n._mark(_LABELS[DEFAULT_LANGUAGE].get(key, u""))


def _scale_options(code):
    """The localized scale radio-group option labels ``[Default, Large]`` for language
    ``code`` (English fallback, marked on fallback -- same policy as the mod-invented
    labels). ``code`` is already a normalized ``_norm()`` key."""
    fb = code not in _SCALE_OPTIONS
    opts = _SCALE_OPTIONS[DEFAULT_LANGUAGE] if fb else _SCALE_OPTIONS[code]
    if fb:
        return [i18n._mark(o) for o in opts]
    return list(opts)


def _progress_options(code):
    """The localized progressMode radio-group option labels ``[Current, Current / Required]``
    for language ``code`` (English fallback, marked on fallback -- same policy as
    _scale_options). ``code`` is already a normalized ``_norm()`` key."""
    fb = code not in _PROGRESS_OPTIONS
    opts = _PROGRESS_OPTIONS[DEFAULT_LANGUAGE] if fb else _PROGRESS_OPTIONS[code]
    if fb:
        return [i18n._mark(o) for o in opts]
    return list(opts)


def client_language():
    """The client's active language code, normalized to a table key -- the ONE engine
    read here. Guarded + lazy-imported so the module still imports under pytest and a
    missing/renamed helper degrades to English rather than raising into MSA setup."""
    try:
        import helpers
        return _norm(helpers.getClientLanguage()) or DEFAULT_LANGUAGE
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return DEFAULT_LANGUAGE


def panel_text(lang=None):
    """The rendered panel text for the client's active language (public entry for
    mod_settings). Pulls WG's localized feature names from ``i18n.widget_labels()``."""
    return render_panel(i18n.widget_labels(), lang)
