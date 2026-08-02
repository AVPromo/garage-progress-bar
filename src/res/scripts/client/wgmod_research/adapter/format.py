# -*- coding: utf-8 -*-
"""Pure formatting / value helpers for the read-side adapter.

Extracted from engine_adapter.py so they carry NO game-engine imports and can be
unit-tested on plain inputs (Python 3, no client). engine_adapter re-imports these
under their old private names, so its call sites are unchanged. Everything here is
best-effort and side-effect-free (KPI readers use getattr on the passed object, so a
duck-typed stub is enough to test them).

2/3-compatible.
"""
import re

from wgmod_research._compat import LOG_CURRENT_EXCEPTION
from wgmod_research.domain import constants as c


_ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI"]


def roman(n):
    n = int(n or 0)
    if 0 < n < len(_ROMAN):
        return _ROMAN[n]
    return str(n) if n > 0 else ""


_MODULE_ICON_RE = re.compile(r"^(img://gui/maps/icons/modules/[A-Za-z0-9_]+)\.png$")


def module_big_icon(icon):
    """The generic module-TYPE glyphs (gun/tower/chassis/engine/radio/...) ship an
    80x80 `Big` sibling in the same directory (gun.png -> gunBig.png) -- the higher-res
    art the tech-tree screen itself uses. Swap the plain 48x48 for `Big` so it stops
    upscaling in the tooltip icon box. A non-module or already-`Big` path is returned
    unchanged; guarded so a surprise path can never blank the icon."""
    try:
        m = _MODULE_ICON_RE.match(icon or "")
        if m and not m.group(1).endswith("Big"):
            return m.group(1) + "Big.png"
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return icon or ""


def skilltree_icon(node_type, image_name):
    """Full img:// URL for a skill-tree node's perk icon. The client stores them at
    skillTree/tree/perks/<type>/skills/<size>/<imageName>.png (type = getType():
    common|major|special|final) -- verified live. We use the `large` (40x40) variant
    over `small` (32x32) for a sharper glyph in the enlarged tooltip; every `small`
    icon has a matching `large` (verified against res/packages gui-part*.pkg: 178/178
    pairs, zero orphans). Bare getImageName() (e.g. 'invisibilityWhenShooting') is
    just the basename. Empty name -> "" (no icon)."""
    if not image_name:
        return ""
    return ("img://gui/maps/icons/skillTree/tree/perks/%s/skills/large/%s.png"
            % (node_type or "common", image_name))


def humanize(name):
    """camelCase action id -> spaced Title-ish label, e.g. 'invisibilityWhenShooting'
    -> 'Invisibility When Shooting'. Empty -> ""."""
    if not name:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])([A-Z])", r" \1", name)
    return spaced[:1].upper() + spaced[1:]


def fmt_pct(pct):
    """A KPI 'mul' delta rendered as a signed percent ("+10%", "-1%"). "" if it
    rounds to zero (no meaningful change)."""
    r = round(pct)
    if abs(pct - r) < 0.05:
        n = int(r)
        return "" if n == 0 else ("%+d%%" % n)
    return "%+.1f%%" % pct


def fmt_signed(v):
    """A raw additive KPI delta as a signed magnitude ("+3", "-3", "+2.5", "-0.01").
    No percent/unit suffix -- 'add' KPIs are absolute quantities and the phrase carries
    the stat name. "" only when the value is negligible even at two decimals (rounds to
    0.00).

    'add' deltas span very different scales: +3 km/h top reverse speed, but -0.01 to
    gun dispersion (measured in hundredths). The old integer-rounding treated any
    sub-0.05 value as zero and returned "", so dispersion-scale deltas lost their
    number and the tooltip showed only the qualitative sentence. Now: snap to a clean
    integer only when actually near a NON-zero integer; otherwise render two decimals
    (trailing zeros trimmed) so a -0.01 survives while a genuine ~zero stays empty."""
    r = round(v)
    if r and abs(v - r) < 0.05:
        return "%+d" % int(r)
    s = "%+.2f" % v
    if s in ("+0.00", "-0.00"):
        return ""
    return s.rstrip("0").rstrip(".")


def fmt_num(pct):
    """A bare magnitude for a tier-XI description template's {value} slot: an int
    when it rounds clean to a NON-zero integer, else up to two decimals (trailing
    zeros trimmed). No sign -- the template's wording carries the direction (e.g.
    'Reduces ... by {value}%').

    {value} fills carry absolute magnitudes too (skilltree_value's 'add' path), which
    can be dispersion-scale hundredths; snapping any sub-0.05 value to an int collapsed
    those to "0" ('...by 0'). Keeping two decimals preserves a 0.01. Unlike fmt_signed,
    a true ~zero reads "0" (never empty) -- a filled template always wants a figure."""
    r = round(pct)
    if r and abs(pct - r) < 0.05:
        return str(int(r))
    s = "%.2f" % pct
    if s in ("0.00", "-0.00"):
        return "0"
    return s.rstrip("0").rstrip(".")


def kpi_objs(action):
    """The raw KPI objects on an action's descriptor (action._descriptor.kpi), or []."""
    d = getattr(action, "_descriptor", None)
    return getattr(d, "kpi", None) or []


def kpi_prefix(k):
    """The signed numeric prefix for a KPI, or "" when it carries no usable number.

    'mul' -> percent from (value-1)*100 ("+10%"); 'add' -> the raw signed delta
    ("+3", absolute units, no %). Any other numeric type falls back to the raw signed
    delta (the realistic non-'mul' shape is 'add'; dropping the number is the bug this
    replaces). "" when the value is missing/non-numeric or rounds to a negligible
    ~zero. bool is excluded up front (it's an int subclass). KPI types verified live
    (EU 2.3): 'mul' (Strv 103B et al.) and 'add' (Kranvagn L7 "top reverse speed")."""
    val = getattr(k, "value", None)
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return ""
    val = float(val)
    if (getattr(k, "type", "") or "") == "mul":
        return fmt_pct((val - 1.0) * 100.0)
    return fmt_signed(val)


def kpi_magnitude(k):
    """The bare magnitude of ONE KPI for a description template's value slot:
    'mul' -> percent (|value-1|*100), anything else -> the raw |value| (the realistic
    non-'mul' shape is 'add'). Unsigned and unit-less -- the template's own wording
    carries the direction and the unit. "" when the value is missing or non-numeric
    (bool excluded up front, it's an int subclass)."""
    v = getattr(k, "value", None)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return ""
    v = float(v)
    if (getattr(k, "type", "") or "") == "mul":
        return fmt_num(abs((v - 1.0) * 100.0))
    return fmt_num(abs(v))


def skilltree_value(action):
    """The bare {value} magnitude for a tier-XI sentence template: the first of the
    node's KPI objects that carries a usable number (see kpi_magnitude). "" when none
    does. Verified live (EU 2.3): the signature 'mechanic' perks' generic 'value' KPI
    is itself typed 'mul'/'add', so it fills here."""
    for k in kpi_objs(action):
        mag = kpi_magnitude(k)
        if mag:
            return mag
    return ""


def fill_kpi_placeholders(tmpl, action):
    """Substitute a tier-XI description template's NAMED value placeholders from the
    node's KPI list; returns (text, filled).

    The client's own perk-tooltip bundle keys each slot by the KPI's `name` plus its
    0-based position in the ordered kpi list, with the index OMITTED when the node has
    exactly one KPI -- so a single-KPI node reads '{value}' (the plain path
    skilltree_value already fills) while a multi-KPI node reads '{value0}', '{value1}'
    (e.g. the tier-XI French TD final node, whose two slots rendered raw before this).
    Each slot takes that KPI's unsigned magnitude. Both spellings are accepted for a
    single-KPI node so a stray index can't leak a raw placeholder either.

    `filled` is True when at least one slot was substituted -- it tells the caller the
    sentence already carries its own numbers (so the KPI lines must NOT be appended).
    A slot with no matching KPI, or a KPI with no usable number, is left untouched.
    Pure (getattr-only, so a duck-typed stub tests it)."""
    kpis = kpi_objs(action)
    text = tmpl
    filled = False
    for i, k in enumerate(kpis):
        name = getattr(k, "name", "") or ""
        mag = kpi_magnitude(k) if name else ""
        if not mag:
            continue
        slots = ["{%s%d}" % (name, i)]
        if len(kpis) == 1:
            slots.append("{%s}" % name)
        for slot in slots:
            if slot in text:
                text = text.replace(slot, mag)
                filled = True
    return text, filled


# --- Enriched buff-line records (icon + color + unit) -----------------------
#
# A KPI buff line is packed into a single delimited RECORD so the widget can
# render it like the game's native perk tooltip: the parameter icon, the delta
# value colored green/red, and the (dim) stat phrase. The record travels inside
# the existing `effect` / `optionEffects` string fields (no Wulf VM schema
# change): lines are still joined by "\n" and variant buffs by "\t"; this
# separator splits the fields WITHIN one line. U+001F (unit separator) never
# appears in localized text, so it is unambiguous. The JS effectHtml mirrors
# this exact shape; a line WITHOUT the separator is rendered as plain text
# (back-compat for any non-KPI body line). ALIAS, not a second definition: the same
# unit separator packs the COMPLETE per-category breakdown rows, so it has one home
# (domain/constants) and one convention.
KPI_FIELD_SEP = c.FIELD_SEP

# WG's description templates wrap their HIGHLIGHTED run -- the figure, sometimes
# figure + unit ("{colorTagOpen}{value0} HP{colorTagClose}") -- in a colour-tag pair
# that the native perk tooltip renders as a span coloured #ede6d9 (its
# tagColors = {colorTag: "#ede6d9"}). The widget HTML-escapes a body line, so raw
# markup from here can't (and must not) survive: the pair is swapped for these
# sentinel control chars and the JS turns them into the span AFTER escaping (mirrored
# as HL_OPEN/HL_CLOSE in WGModResearch.js). STX/ETX, like KPI_FIELD_SEP, never appear
# in localized text and can't collide with the "\x1f" field / "\t" variant / "\n"
# line separators.
HL_OPEN = u"\x02"
HL_CLOSE = u"\x03"

_COLOR_TAG_RE = re.compile(r"\{colorTagOpen\}(.*?)\{colorTagClose\}", re.S)


def mark_color_tags(text):
    """Swap each balanced {colorTagOpen}...{colorTagClose} pair for the HL_OPEN/HL_CLOSE
    sentinels the widget renders as a highlighted span (the whole wrapped run, which may
    be number + unit, not just the digits). An unclosed / unpaired tag degrades to plain
    text -- the leftover marker is dropped, so a malformed template can never leak a
    sentinel char or a half-open span into the DOM."""
    out = _COLOR_TAG_RE.sub(HL_OPEN + u"\\1" + HL_CLOSE, text or u"")
    return out.replace(u"{colorTagOpen}", u"").replace(u"{colorTagClose}", u"")


# KPI name -> vehParams param file name (the icon basename AND the key the game's
# measureUnitsForParameter uses). Ported from the client's own perk-tooltip
# bundle remap; a KPI name absent here is used verbatim (some, e.g.
# 'vehicleFireChance', are already a valid vehParams file). Verified live (EU 2.3).
KPI_PARAM_ICON = {
    "vehicleEnginePower": "enginePower",
    "vehicleStrength": "maxHealth",
    "vehicleAllGroundRotationSpeed": "chassisRotationSpeed",
    "vehicleGunReloadTime": "reloadTimeSecs",
    "reloadTimeSalvo": "reloadTimeSecs",
    "reloadTimeSingle": "reloadTimeSecs",
    "reloadTimeInClip": "clipFireRate",
    "vehicleGunAimSpeed": "aimingTime",
    "vehicleTurretOrCuttingRotationSpeed": "turretRotationSpeed",
    "specialShellPenetration": "avgPiercingPower",
    "standardShellPenetration": "avgPiercingPower",
    "HEShellPenetration": "avgPiercingPower",
    "nonHEShellDamage": "avgDamage",
    "standardShellDamage": "avgDamage",
    "specialShellDamage": "avgDamage",
    "allShellDamage": "avgDamage",
    "basicShellDamage": "avgDamage",
    "gunDepression": "pitchLimits",
    "gunElevation": "pitchLimits",
    "vehicleGunShotFullDispersion": "shotDispersionAngle",
    "gunStabilization": "shotDispersionAngle",
    "standardShellVelocity": "shellVelocity",
    "specialShellVelocity": "shellVelocity",
    "shellVelocity": "shellVelocity",
    "allShellsVelocity": "shellVelocity",
    "HEshellVelocity": "shellVelocity",
    "vehicleForwardMaxSpeed": "speedLimits",
    "vehicleBackwardMaxSpeed": "speedLimits",
    "gunTraverse": "gunYawLimits",
    "turretTraverse": "turretYawLimits",
    "vehicleCircularVisionRadius": "circularVisionRadius",
    "hullElevationSpeed": "hullElevationSpeed",
}


def param_icon_name(kpi_name):
    """The vehParams param/icon basename for a KPI name (via KPI_PARAM_ICON, else
    the name verbatim). "" for a falsy name."""
    if not kpi_name:
        return ""
    return KPI_PARAM_ICON.get(kpi_name, kpi_name)


def strip_unit(glyph):
    """The bare unit from the game's measure-unit glyph: '(HP)' -> 'HP', '(km/h)'
    -> 'km/h'. The tank_params unit strings are parenthesized (they trail a value
    in the native params panel); we drop the wrapping parens so the unit reads
    inline after our own signed number ('+10 HP'). Whitespace-trimmed; a glyph
    without parens is returned as-is; "" -> ""."""
    s = (glyph or "").strip()
    if len(s) >= 2 and s[0] == "(" and s[-1] == ")":
        s = s[1:-1].strip()
    return s


def resolve_is_debuff(raw_is_debuff, kpi_name_backward, param_name_backward):
    """Correct the game's KPI.isDebuff for KPI names that miss the "lower is better"
    (BACKWARD_QUALITY_PARAMS) set under their KPI name but hit it under their mapped
    vehParams param name. The game keys isDebuff off the RAW KPI name, so a backward
    parameter exposed under a non-backward KPI name (e.g. aim speed: KPI name
    'vehicleGunAimSpeed' misses the set, param name 'aimingTime' is in it) gets the
    wrong branch -- a beneficial reduction is flagged as a debuff (red). When the
    mapped param IS backward but the raw KPI name is NOT, flip; otherwise keep the
    game's value. Pure -- membership is decided by the (engine-facing) caller.

    Verify: aim add value -0.1 -> game isDebuff=True, param backward, kpi not backward
    -> flip -> False -> green; a +aim (worse) -> game False -> flip -> True -> red."""
    if param_name_backward and not kpi_name_backward:
        return not raw_is_debuff
    return raw_is_debuff


def kpi_record(icon, is_debuff, value_str, desc):
    """Pack one buff line into the widget's delimited record
    (icon <SEP> cls <SEP> value <SEP> desc), where cls is 'neg' for a debuff
    (nerf -> red) else 'pos' (buff -> green). All fields coerced to "" when
    absent. This is the single source of the wire format; WGModResearch.js splits
    on the same separator."""
    cls = "neg" if is_debuff else "pos"
    return KPI_FIELD_SEP.join(
        [icon or "", cls, value_str or "", desc or ""])


def kpi_record_labeled(record):
    """True when a packed KPI record carries something that NAMES its number -- an
    icon or a description phrase. A record with neither renders as a bare coloured
    figure ("+20") with nothing to identify it: that is what a signature 'mechanic'
    node's generic 'value' KPI degrades to (no vehParams icon, no phrase), and WG's
    own client never lists KPI rows for those nodes. Callers must drop such records
    rather than append them as standalone lines. A line WITHOUT the separator is not
    a record but plain text -> kept."""
    parts = (record or "").split(KPI_FIELD_SEP)
    if len(parts) != 4:
        return bool(record)
    return bool(parts[0] or parts[3])
