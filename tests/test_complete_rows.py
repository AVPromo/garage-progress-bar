# -*- coding: utf-8 -*-
"""Unit tests for the COMPLETE ("Fully Progressed") per-category breakdown rows
(builder._complete_effect / _COMPLETE_ROWS / _complete_model) -- the packed
FIELD_SEP/ROW_SEP tooltip data each finished-category chip carries in `description`.
Engine-free; must fail SOFT (unlike resolvers/complete, which gates)."""
from wgmod_research.domain import types as t
from wgmod_research.domain import builder as B
from wgmod_research.domain.constants import FIELD_SEP as F, ROW_SEP as R


def _snap(**kw):
    base = dict(tier=10, is_elite=True, vehicle_xp=0, free_xp=0)
    base.update(kw)
    return t.VehicleSnapshot(**base)


def _u(cd, name, xp, researched=True, eff=None):
    return t.UnlockItem(int_cd=cd, name=name, icon=u"img://a%d" % cd, xp_cost=xp,
                        kind="module", researched=researched, prereqs_met=True,
                        xp_cost_effective=eff)


def _step(level, name, xp, options=None, sel=-1):
    return t.ProgressionStep(step_id=level, name=name, icon=u"", xp_cost=xp,
                             unlocked=True, level=level, options=options, selected_idx=sel)


# --- research rows -----------------------------------------------------------------

def test_research_rows_drop_zero_xp_and_use_raw_cost():
    s = _snap(tech_unlocks=[_u(1, u"Gun", 2000), _u(2, u"Stock", 0), _u(3, u"Radio", 500),
                            _u(4, u"Unresearched", 900, researched=False)])
    rows = B._complete_effect(s, t.Mode.TECH_TREE).split(R)
    assert rows == [u"img://a1" + F + u"Gun" + F + u"2000" + F,
                    u"img://a3" + F + u"Radio" + F + u"500" + F]


def test_research_row_reports_raw_cost_not_the_blueprint_discount():
    s = _snap(tech_unlocks=[_u(1, u"Tank", 200000, eff=120000)])
    assert B._complete_effect(s, t.Mode.TECH_TREE).split(F)[2] == u"200000"


# --- field-mod rows -----------------------------------------------------------------

def test_fieldmod_rows_order_and_selected_variant_naming():
    # A picked variant is conveyed by BEING the row title -- field3 stays empty for this
    # category (the separate "selected" marker was dropped; selected_idx only picks the name).
    s = _snap(field_mod_steps=[
        _step(2, u"Base B", 2000, options=[u"Optics", u"Vision"], sel=1),
        _step(1, u"Base A", 1000),
        _step(3, u"Base C", 3000, options=[u"Left", u"Right"], sel=0),  # falsy-index trap
        _step(4, u"Base D", 4000, options=[u"X", u"Y"]),               # pair, nothing picked
    ])
    rows = B._complete_effect(s, t.Mode.FIELD_MODS).split(R)
    assert rows == [u"1" + F + u"Base A" + F + u"1000" + F,
                    u"2" + F + u"Vision" + F + u"2000" + F,
                    u"3" + F + u"Left" + F + u"3000" + F,
                    u"4" + F + u"Base D" + F + u"4000" + F]


def test_fieldmod_row_selected_idx_zero_is_not_treated_as_falsy():
    # The `x or -1` trap: selected_idx == 0 must read as "picked option 0", not "none".
    s = _snap(field_mod_steps=[_step(1, u"Base", 1000, options=[u"Left", u"Right"], sel=0)])
    row = B._complete_effect(s, t.Mode.FIELD_MODS)
    assert row == u"1" + F + u"Left" + F + u"1000" + F


# --- elite-reward rows ---------------------------------------------------------------

def test_reward_rows_pair_level_with_cumulative_xp():
    s = _snap(elite_rewards=[t.EliteReward(level=10, achieved=True, icon=u"img://r1", label=u"Style"),
                             t.EliteReward(level=30, achieved=True, icon=u"img://r2", label=u"Deco")],
              elite_level_xp={10: 111, 30: 999})
    assert B._complete_effect(s, t.Mode.ELITE_REWARDS).split(R) == [
        u"img://r1" + F + u"Style" + F + u"111" + F + u"10",
        u"img://r2" + F + u"Deco" + F + u"999" + F + u"30"]


# --- skill-tree row -------------------------------------------------------------------

def test_skilltree_row_is_exactly_one_final_upgrade():
    s = _snap(is_skill_tree=True, skilltree_final_icon=u"img://perk",
              skilltree_final_name=u"Final", skilltree_final_xp=325000)
    assert B._complete_effect(s, t.Mode.SKILL_TREE) == \
        u"img://perk" + F + u"Final" + F + u"325000" + F


def test_skilltree_row_empty_final_name_yields_no_rows():
    assert B._complete_effect(_snap(is_skill_tree=True), t.Mode.SKILL_TREE) == u""


# --- ELITE category has no breakdown ---------------------------------------------------

def test_elite_category_emits_no_rows():
    assert B._complete_effect(_snap(), t.Mode.ELITE) == u""


# --- fail-soft ---------------------------------------------------------------------------

def test_complete_effect_fails_soft_on_unreadable_snapshot():
    class Boom(object):
        @property
        def tech_unlocks(self):
            raise RuntimeError("unreadable")

    assert B._complete_effect(Boom(), t.Mode.TECH_TREE) == u""


# --- _complete_model counter swap -------------------------------------------------------

def test_complete_model_counter_swaps_to_skilltree_when_present():
    snap = _snap(tier=11, is_skill_tree=True, skilltree_done=7, skilltree_total=7,
                 skilltree_total_xp=500000, skilltree_final_name=u"Final",
                 skilltree_final_icon=u"img://perk", skilltree_final_xp=325000,
                 fieldmods_done=0, fieldmods_total=0)
    m = B.build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert (m.fieldmods_done, m.fieldmods_total) == (7, 7)
    assert [u.category for u in m.avail_upgrades] == [t.Mode.SKILL_TREE]
    assert m.avail_upgrades[0].description == u"img://perk" + F + u"Final" + F + u"325000" + F


def test_complete_model_counter_stays_on_fieldmods_when_no_skilltree():
    snap = _snap(field_mod_steps=[_step(1, u"Base A", 1000)],
                 fieldmods_done=8, fieldmods_total=8)
    m = B.build_model(snap)
    assert m.mode == t.Mode.COMPLETE
    assert (m.fieldmods_done, m.fieldmods_total) == (8, 8)
    assert m.avail_upgrades[0].description == u"1" + F + u"Base A" + F + u"1000" + F
