# -*- coding: utf-8 -*-
"""Unit tests for the pure formatting helpers (engine-free, extracted from the
read-side adapter)."""
from wgmod_research.adapter import format as f


class _KPI(object):
    def __init__(self, value=None, type="", name=""):
        self.value = value
        self.type = type
        self.name = name


class _Desc(object):
    def __init__(self, kpi):
        self.kpi = kpi


class _Action(object):
    def __init__(self, kpi=None):
        self._descriptor = _Desc(kpi if kpi is not None else [])


# --- roman ------------------------------------------------------------------

def test_roman_basic():
    assert f.roman(1) == "I"
    assert f.roman(10) == "X"
    assert f.roman(11) == "XI"


def test_roman_out_of_table_falls_back_to_digits():
    assert f.roman(12) == "12"


def test_roman_zero_and_none_and_negative_are_empty():
    assert f.roman(0) == ""
    assert f.roman(None) == ""
    assert f.roman(-3) == ""


# --- module_big_icon --------------------------------------------------------

def test_module_big_icon_swaps_to_big():
    src = "img://gui/maps/icons/modules/gun.png"
    assert f.module_big_icon(src) == "img://gui/maps/icons/modules/gunBig.png"


def test_module_big_icon_already_big_unchanged():
    src = "img://gui/maps/icons/modules/gunBig.png"
    assert f.module_big_icon(src) == src


def test_module_big_icon_non_module_unchanged():
    src = "img://gui/maps/icons/vehicle/foo.png"
    assert f.module_big_icon(src) == src


def test_module_big_icon_empty():
    assert f.module_big_icon("") == ""
    assert f.module_big_icon(None) == ""


# --- skilltree_icon ---------------------------------------------------------

def test_skilltree_icon_builds_large_url():
    assert f.skilltree_icon("major", "boo") == (
        "img://gui/maps/icons/skillTree/tree/perks/major/skills/large/boo.png")


def test_skilltree_icon_defaults_type_common():
    assert f.skilltree_icon("", "boo") == (
        "img://gui/maps/icons/skillTree/tree/perks/common/skills/large/boo.png")


def test_skilltree_icon_empty_name():
    assert f.skilltree_icon("major", "") == ""


# --- humanize ---------------------------------------------------------------

def test_humanize_splits_camel_case():
    assert f.humanize("invisibilityWhenShooting") == "Invisibility When Shooting"


def test_humanize_capitalizes_first():
    assert f.humanize("gun") == "Gun"


def test_humanize_empty():
    assert f.humanize("") == ""


# --- numeric formatters -----------------------------------------------------

def test_fmt_pct():
    assert f.fmt_pct(10.0) == "+10%"
    assert f.fmt_pct(-1.0) == "-1%"
    assert f.fmt_pct(0.0) == ""       # negligible -> empty
    assert f.fmt_pct(10.02) == "+10%"  # rounds clean
    assert f.fmt_pct(2.5) == "+2.5%"   # keeps a decimal


def test_fmt_signed():
    assert f.fmt_signed(3.0) == "+3"
    assert f.fmt_signed(-3.0) == "-3"
    assert f.fmt_signed(0.0) == ""
    assert f.fmt_signed(2.5) == "+2.5"


def test_fmt_signed_keeps_small_fractional_deltas():
    # 'add' KPIs are absolute quantities on wildly different scales: a top-reverse-
    # speed delta is +3, but a dispersion delta is -0.01. The old integer-rounding
    # swallowed the dispersion-scale ones to "" (their number vanished from the
    # tooltip, leaving only the qualitative sentence). Keep two decimals for sub-unit
    # deltas so the figure survives.
    assert f.fmt_signed(-0.01) == "-0.01"
    assert f.fmt_signed(-0.009999999776482582) == "-0.01"  # the live gunDispersion KPI
    assert f.fmt_signed(-0.02) == "-0.02"
    assert f.fmt_signed(0.1) == "+0.1"                     # no trailing zero
    assert f.fmt_signed(-0.5) == "-0.5"


def test_fmt_signed_only_true_zero_is_empty():
    # genuinely-negligible values (round to 0.00 even at two decimals) stay empty;
    # a real sub-unit delta does not.
    assert f.fmt_signed(0.0) == ""
    assert f.fmt_signed(0.001) == ""
    assert f.fmt_signed(-0.004) == ""
    assert f.fmt_signed(0.01) == "+0.01"


def test_fmt_num_unsigned_and_never_empty_for_zero():
    assert f.fmt_num(10.0) == "10"
    assert f.fmt_num(0.0) == "0"       # unlike fmt_pct/fmt_signed, keeps "0"
    assert f.fmt_num(2.5) == "2.5"


def test_fmt_num_keeps_small_fractional_magnitudes():
    # {value} fills carry absolute magnitudes too (skilltree_value's 'add' path),
    # which can be dispersion-scale hundredths. The old integer-rounding collapsed
    # those to "0", so a template read "...by 0" instead of "...by 0.01". Keep two
    # decimals (trailing zeros trimmed); a true ~zero still reads "0".
    assert f.fmt_num(0.01) == "0.01"
    assert f.fmt_num(0.1) == "0.1"
    assert f.fmt_num(0.001) == "0"


# --- KPI readers ------------------------------------------------------------

def test_kpi_objs_reads_descriptor_kpi():
    a = _Action([1, 2, 3])
    assert f.kpi_objs(a) == [1, 2, 3]


def test_kpi_objs_missing_descriptor_is_empty():
    assert f.kpi_objs(object()) == []


def test_kpi_prefix_mul_is_percent():
    assert f.kpi_prefix(_KPI(value=1.1, type="mul")) == "+10%"


def test_kpi_prefix_add_is_raw_delta():
    assert f.kpi_prefix(_KPI(value=3.0, type="add")) == "+3"


def test_kpi_prefix_non_mul_falls_back_to_signed():
    assert f.kpi_prefix(_KPI(value=-3.0, type="whatever")) == "-3"


def test_kpi_prefix_bool_and_nonnumeric_are_empty():
    assert f.kpi_prefix(_KPI(value=True, type="mul")) == ""
    assert f.kpi_prefix(_KPI(value="x", type="add")) == ""
    assert f.kpi_prefix(_KPI(value=None)) == ""


def test_kpi_prefix_negligible_mul_is_empty():
    assert f.kpi_prefix(_KPI(value=1.0, type="mul")) == ""


def test_skilltree_value_scans_first_usable_kpi():
    a = _Action([_KPI(value="x"), _KPI(value=1.2, type="mul")])
    assert f.skilltree_value(a) == "20"          # unsigned percent


def test_skilltree_value_add_magnitude():
    a = _Action([_KPI(value=-3.0, type="add")])
    assert f.skilltree_value(a) == "3"           # unsigned magnitude


def test_skilltree_value_none_usable_is_empty():
    a = _Action([_KPI(value="x"), _KPI(value=None)])
    assert f.skilltree_value(a) == ""


# --- fill_kpi_placeholders (indexed description templates) --------------------

# The tier-XI French TD's final node ("Modified Output Limiter"): TWO KPIs, so its
# localized template indexes its slots -- {value0}/{value1} rendered raw before the
# indexed path existed (and the miss also appended bare-number KPI lines).
_INDEXED_TMPL = (u"Increases the post-limit damage spike by "
                 u"{colorTagOpen}{value0} HP{colorTagClose} and the maximum "
                 u"post-limit damage bonus by {colorTagOpen}{value1}%{colorTagClose}.")


def test_fill_kpi_placeholders_indexed_slots():
    a = _Action([_KPI(value=20.0, type="add", name="value"),
                 _KPI(value=1.05, type="mul", name="value")])
    text, filled = f.fill_kpi_placeholders(_INDEXED_TMPL, a)
    assert filled is True
    assert u"{value0}" not in text and u"{value1}" not in text
    assert u"spike by {colorTagOpen}20 HP{colorTagClose}" in text
    assert u"bonus by {colorTagOpen}5%{colorTagClose}" in text   # colour tags untouched


def test_fill_kpi_placeholders_single_kpi_omits_the_index():
    # one KPI -> the client spells the slot without an index (the plain {value} the
    # 75 working templates use); regression guard for that path.
    a = _Action([_KPI(value=1.2, type="mul", name="value")])
    text, filled = f.fill_kpi_placeholders(u"Reduces reload by {value}%.", a)
    assert (text, filled) == (u"Reduces reload by 20%.", True)


def test_fill_kpi_placeholders_leaves_plain_value_alone_for_multi_kpi():
    # a plain {value} template on a multi-KPI node is NOT ours to fill (the slots
    # would be indexed) -- leave it to the legacy skilltree_value path.
    a = _Action([_KPI(value=1.2, type="mul", name="value"),
                 _KPI(value=3.0, type="add", name="value")])
    tmpl = u"Reduces reload by {value}%."
    assert f.fill_kpi_placeholders(tmpl, a) == (tmpl, False)


def test_fill_kpi_placeholders_unmatched_or_unusable_is_untouched():
    tmpl = u"Reduces reload by {value0}%."
    # no KPI list / no name / non-numeric value / a name the template doesn't use
    assert f.fill_kpi_placeholders(tmpl, _Action([])) == (tmpl, False)
    assert f.fill_kpi_placeholders(tmpl, _Action([_KPI(value=1.2, type="mul")])) == (
        tmpl, False)
    assert f.fill_kpi_placeholders(
        tmpl, _Action([_KPI(value="x", name="value"), _KPI(value=None, name="value")])
    ) == (tmpl, False)
    assert f.fill_kpi_placeholders(
        tmpl, _Action([_KPI(value=1.2, type="mul", name="other"),
                       _KPI(value=1.2, type="mul", name="other")])) == (tmpl, False)


def test_mark_color_tags_wraps_the_whole_highlighted_run():
    # WG highlights the figure AND its unit ("{value0} HP") -- the sentinels must span
    # the whole wrapped run, not just the digits, and every pair in the sentence.
    a = _Action([_KPI(value=20.0, type="add", name="value"),
                 _KPI(value=1.05, type="mul", name="value")])
    text, _ = f.fill_kpi_placeholders(_INDEXED_TMPL, a)
    out = f.mark_color_tags(text)
    assert u"spike by " + f.HL_OPEN + u"20 HP" + f.HL_CLOSE in out
    assert u"bonus by " + f.HL_OPEN + u"5%" + f.HL_CLOSE in out
    assert u"colorTag" not in out


def test_mark_color_tags_unbalanced_degrades_to_plain_text():
    # an unclosed / orphaned / empty-input tag must never leak a sentinel char or a
    # half-open span into the widget
    for tmpl in (u"Reduces reload by {colorTagOpen}20%.",
                 u"Reduces reload by 20%{colorTagClose}.",
                 u"{colorTagClose}20%{colorTagOpen}"):
        out = f.mark_color_tags(tmpl)
        assert u"colorTag" not in out
        assert f.HL_OPEN not in out and f.HL_CLOSE not in out
    assert f.mark_color_tags(None) == u""


def test_kpi_magnitude_is_unsigned_and_unitless():
    assert f.kpi_magnitude(_KPI(value=1.05, type="mul")) == "5"
    assert f.kpi_magnitude(_KPI(value=0.75, type="mul")) == "25"   # unsigned
    assert f.kpi_magnitude(_KPI(value=-20.0, type="add")) == "20"
    assert f.kpi_magnitude(_KPI(value=None)) == ""


# --- enriched buff-line records ---------------------------------------------

def test_param_icon_name_remaps_known_kpi():
    assert f.param_icon_name("vehicleStrength") == "maxHealth"
    assert f.param_icon_name("nonHEShellDamage") == "avgDamage"
    assert f.param_icon_name("vehicleGunAimSpeed") == "aimingTime"


def test_param_icon_name_unknown_used_verbatim():
    # some KPI names are already a valid vehParams file (e.g. vehicleFireChance)
    assert f.param_icon_name("vehicleFireChance") == "vehicleFireChance"


def test_param_icon_name_empty():
    assert f.param_icon_name("") == ""
    assert f.param_icon_name(None) == ""


def test_strip_unit_drops_wrapping_parens():
    assert f.strip_unit("(HP)") == "HP"
    assert f.strip_unit("(km/h)") == "km/h"
    assert f.strip_unit(" (s) ") == "s"


def test_strip_unit_without_parens_unchanged():
    assert f.strip_unit("HP") == "HP"
    assert f.strip_unit("") == ""
    assert f.strip_unit(None) == ""


def test_kpi_record_field_order_and_pos_neg():
    sep = f.KPI_FIELD_SEP
    buff = f.kpi_record("img://x.png", False, "+10 HP", "to damage")
    assert buff == sep.join(["img://x.png", "pos", "+10 HP", "to damage"])
    nerf = f.kpi_record("img://y.png", True, "-0.10 s", "to aiming speed")
    assert nerf == sep.join(["img://y.png", "neg", "-0.10 s", "to aiming speed"])


def test_kpi_record_coerces_missing_fields_to_empty():
    sep = f.KPI_FIELD_SEP
    assert f.kpi_record("", False, "+25%", "") == sep.join(["", "pos", "+25%", ""])
    assert f.kpi_record(None, True, None, None) == sep.join(["", "neg", "", ""])


def test_degenerate_kpi_records_are_dropped_from_appended_lines():
    # the naked-number bug: a 'mechanic' node's generic 'value' KPI resolves to no
    # vehParams icon AND no phrase, so its record is a bare green figure. The append
    # site in _skilltree_effect filters on this predicate; a record with an icon OR a
    # phrase survives, and a plain (non-record) line is left alone.
    naked = f.kpi_record("", False, "+20", "")
    by_desc = f.kpi_record("", False, "-5%", "to reload time")
    by_icon = f.kpi_record("img://x.png", False, "+3", "")
    assert f.kpi_record_labeled(naked) is False
    kept = [r for r in (naked, by_desc, by_icon) if f.kpi_record_labeled(r)]
    assert kept == [by_desc, by_icon]
    assert f.kpi_record_labeled(u"a plain sentence") is True
    assert f.kpi_record_labeled("") is False


# --- resolve_is_debuff ------------------------------------------------------

def test_resolve_is_debuff_flips_backward_param_with_non_backward_kpi():
    # the aim-speed bug: game flags a -0.1s aim delta as a debuff (raw True) because
    # the KPI name 'vehicleGunAimSpeed' misses BACKWARD_QUALITY_PARAMS, but the mapped
    # param 'aimingTime' IS backward -> flip to False (buff, green).
    assert f.resolve_is_debuff(True, kpi_name_backward=False,
                               param_name_backward=True) is False
    # the reverse: a +aim delta (slower, worse) -> game raw False -> flip -> True (red).
    assert f.resolve_is_debuff(False, kpi_name_backward=False,
                               param_name_backward=True) is True


def test_resolve_is_debuff_keeps_raw_when_both_backward():
    # KPI name and param name agree (both in the set) -> no correction.
    assert f.resolve_is_debuff(True, kpi_name_backward=True,
                               param_name_backward=True) is True
    assert f.resolve_is_debuff(False, kpi_name_backward=True,
                               param_name_backward=True) is False


def test_resolve_is_debuff_keeps_raw_when_neither_backward():
    # a "higher is better" param (e.g. damage) -> game's flag is already correct.
    assert f.resolve_is_debuff(True, kpi_name_backward=False,
                               param_name_backward=False) is True
    assert f.resolve_is_debuff(False, kpi_name_backward=False,
                               param_name_backward=False) is False


def test_resolve_is_debuff_keeps_raw_when_only_kpi_backward():
    # only the raw KPI name is backward (mapped param isn't) -> no flip.
    assert f.resolve_is_debuff(True, kpi_name_backward=True,
                               param_name_backward=False) is True
    assert f.resolve_is_debuff(False, kpi_name_backward=True,
                               param_name_backward=False) is False
