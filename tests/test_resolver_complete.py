# -*- coding: utf-8 -*-
"""Unit tests for the COMPLETE ("Fully Progressed") resolver (engine-free).

resolve() answers "is EVERY category that applies to this vehicle finished?" and, when
so, what each one cost in RAW XP. It must never raise and never DROP an applicable
category -- dropping one could flip an in-progress tank to COMPLETE."""
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import complete


def _u(cd, cost, researched=True, kind="module", eff=None):
    return t.UnlockItem(cd, "u%d" % cd, "u%d.png" % cd, cost, kind, researched, True,
                        xp_cost_effective=eff)


def _step(sid, cost, level, unlocked=True):
    return t.ProgressionStep(sid, "fm%d" % sid, "fm%d.png" % sid, cost, unlocked, level)


def _snap(**kw):
    """A vehicle where all five categories APPLY and all five are FINISHED.
    Totals: tech 1000+2000, skill 325000, field mods 100..800, rewards 1000 (last
    reward level 10), elite 9000 (cumulative XP at the level cap)."""
    d = dict(tier=11, is_elite=True, vehicle_xp=0, free_xp=0,
             tech_unlocks=[_u(1, 1000), _u(99, 2000, kind="vehicle")],
             field_mod_steps=[_step(i, 100 * i, i) for i in range(1, 9)],
             fieldmods_done=8, fieldmods_total=8,
             is_skill_tree=True, skilltree_done=26, skilltree_total=26,
             skilltree_total_xp=325000,
             has_prestige=True, elite_level=20, elite_max_level=20,
             elite_grades=[t.EliteGrade(1, "iron", 1, True)],
             elite_rewards=[t.EliteReward(5, True), t.EliteReward(10, True)],
             elite_level_xp={5: 500, 10: 1000, 20: 9000})
    d.update(kw)
    return t.VehicleSnapshot(**d)


# --- totals + order ---------------------------------------------------------

def test_all_finished_categories_totals_in_bar_priority_order():
    assert complete.resolve(_snap()) == [
        (t.Mode.TECH_TREE, 3000),        # sum of ALL edges: modules AND child vehicles
        (t.Mode.SKILL_TREE, 325000),     # skilltree_total_xp
        (t.Mode.FIELD_MODS, 3600),       # 100+200+...+800, all within the tier-11 cap
        (t.Mode.ELITE_REWARDS, 1000),    # cumulative XP of the LAST reward's level (10)
        (t.Mode.ELITE, 9000),            # cumulative XP at elite_max_level
    ]


def test_potential_tier_xi_is_never_a_finished_category():
    modes = [m for (m, _xp) in complete.resolve(_snap())]
    assert t.Mode.POTENTIAL_TIER_XI not in modes


def test_tech_tree_total_uses_raw_cost_not_the_blueprint_discount():
    # xp_cost_effective is a one-off discounted purchase price -- reporting it would
    # misstate what the vehicle cost, so the total must stay on the raw xp_cost.
    cats = dict(complete.resolve(_snap(tech_unlocks=[_u(99, 2000, kind="vehicle", eff=50)])))
    assert cats[t.Mode.TECH_TREE] == 2000


def test_field_mods_total_is_capped_by_the_tier_level_cap():
    # The engine lists all 8 levels; a tier-6 tank can only reach level 5 -> 100..500.
    cats = dict(complete.resolve(_snap(tier=6)))
    assert cats[t.Mode.FIELD_MODS] == 1500


# --- one unfinished category vetoes the whole thing --------------------------

def test_unresearched_tech_tree_edge_vetoes():
    assert complete.resolve(_snap(tech_unlocks=[_u(1, 1000, researched=False)])) == []


def test_unfinished_field_mods_veto():
    assert complete.resolve(_snap(fieldmods_done=7)) == []


def test_unfinished_skill_tree_vetoes():
    assert complete.resolve(_snap(skilltree_done=25)) == []


def test_unfinished_elite_level_vetoes():
    assert complete.resolve(_snap(elite_level=19)) == []


def test_unearned_elite_reward_vetoes():
    assert complete.resolve(_snap(elite_rewards=[t.EliteReward(10, False)])) == []


# --- degraded inputs never weaken the gate ----------------------------------

def test_missing_elite_level_xp_gives_a_zero_total_not_a_dropped_category():
    # No XP table -> the two elite categories can't be priced, but they must STILL be
    # reported (0) so the icon row is complete.
    assert complete.resolve(_snap(elite_level_xp={})) == [
        (t.Mode.TECH_TREE, 3000), (t.Mode.SKILL_TREE, 325000),
        (t.Mode.FIELD_MODS, 3600), (t.Mode.ELITE_REWARDS, 0), (t.Mode.ELITE, 0)]


def test_an_unpriced_category_still_gates():
    # ... and an unpriced-but-unfinished category still vetoes COMPLETE.
    assert complete.resolve(_snap(elite_level_xp={}, elite_level=19)) == []


def test_nothing_applicable_is_empty():
    # A plain elite tank with no field mods / prestige / skill tree: no category applies,
    # so there is nothing to call "fully progressed" (the builder keeps its placeholder).
    snap = t.VehicleSnapshot(tier=8, is_elite=True, vehicle_xp=0, free_xp=0)
    assert complete.resolve(snap) == []


def test_junk_snapshot_does_not_raise():
    class _Boom(object):
        def __getattr__(self, name):
            raise RuntimeError("unreadable")

    for junk in (None, "nope", 0, _Boom()):
        assert complete.resolve(junk) == []


def test_an_unreadable_category_totals_zero_instead_of_being_dropped():
    # tier=None makes fieldmods.max_level() raise inside the FIELD_MODS probe while the
    # counter says 3/8 -- unfinished. The category must survive (priced 0) and veto.
    assert complete.resolve(_snap(tier=None, fieldmods_done=3)) == []


# --- `enabled` (Allow Fallthrough support) -----------------------------------

def test_enabled_none_still_vetoes_on_an_unfinished_applicable_category():
    # Default (no toggle threading -- the whole-vehicle gate): a category the player
    # never disabled still vetoes COMPLETE while it's in progress, unchanged.
    snap = _snap(elite_rewards=[t.EliteReward(10, False)])
    assert complete.resolve(snap) == []
    assert complete.resolve(snap, enabled=None) == []


def test_disabled_unfinished_category_is_excluded_from_list_and_gate():
    # Same snapshot, but the player switched ELITE_REWARDS off -- Allow Fallthrough
    # threads `enabled` through, so the still-in-progress category is dropped from
    # BOTH the all-done check and the returned list, letting the remaining
    # all-done enabled categories win.
    snap = _snap(elite_rewards=[t.EliteReward(10, False)])
    enabled = {t.Mode.TECH_TREE, t.Mode.SKILL_TREE, t.Mode.FIELD_MODS, t.Mode.ELITE}
    result = complete.resolve(snap, enabled=enabled)
    assert result == [
        (t.Mode.TECH_TREE, 3000), (t.Mode.SKILL_TREE, 325000),
        (t.Mode.FIELD_MODS, 3600), (t.Mode.ELITE, 9000)]
    assert t.Mode.ELITE_REWARDS not in dict(result)
