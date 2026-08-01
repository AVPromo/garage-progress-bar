# -*- coding: utf-8 -*-
from wgmod_research.domain import types as t
from wgmod_research.domain.builder import bar_visible

# bar_visible(overlay_closed, show_when_complete, mode, in_garage).
# show_when_complete is the INVERSE polarity of the old hide flag: the default is now
# True (shown). The "all clear" baseline is show_when_complete=True. There is no master
# show_bar term any more -- all seven mode toggles off resolves every vehicle to
# Mode.HIDDEN, which is what hides the bar everywhere (see test_hidden_mode_never_visible).


def test_all_clear_is_visible():
    assert bar_visible(True, True, t.Mode.TECH_TREE, True) is True


def test_overlay_open_hides():
    # A tank-setup overlay is open (overlay_closed=False) -> hidden regardless of mode.
    assert bar_visible(False, True, t.Mode.TECH_TREE, True) is False


def test_not_show_when_complete_hides_only_complete():
    # show_when_complete=False -> hide only on fully-progressed vehicles.
    assert bar_visible(True, False, t.Mode.COMPLETE, True) is False


def test_show_when_complete_keeps_other_modes_visible():
    # show_when_complete=False still shows every non-COMPLETE mode.
    for mode in (t.Mode.TECH_TREE, t.Mode.FIELD_MODS, t.Mode.SKILL_TREE,
                 t.Mode.ELITE, t.Mode.ELITE_REWARDS):
        assert bar_visible(True, False, mode, True) is True


def test_outside_garage_hides_any_mode():
    # Fail-closed allowlist: not in the plain garage -> hidden, even with everything
    # else clear (overlay closed, show_when_complete on), in every mode.
    for mode in (t.Mode.TECH_TREE, t.Mode.FIELD_MODS, t.Mode.SKILL_TREE,
                 t.Mode.ELITE, t.Mode.ELITE_REWARDS, t.Mode.COMPLETE):
        assert bar_visible(True, True, mode, False) is False


def test_outside_garage_wins_over_open_overlay():
    # in_garage=False hides regardless of the overlay state.
    assert bar_visible(True, True, t.Mode.TECH_TREE, False) is False
    assert bar_visible(False, True, t.Mode.TECH_TREE, False) is False


def test_hidden_mode_never_visible():
    # A per-mode toggle resolved the vehicle to Mode.HIDDEN -> never shown, even all-clear
    # and even with show_when_complete off. (build_model emits HIDDEN; bar_visible enforces.)
    assert bar_visible(True, True, t.Mode.HIDDEN, True) is False
    assert bar_visible(True, False, t.Mode.HIDDEN, True) is False
    assert bar_visible(False, True, t.Mode.HIDDEN, True) is False


def test_potential_shown_even_when_not_show_when_complete():
    # The opt-in speculative Potential-Tier-XI bar is fully-progressed in reality but is
    # NOT Mode.COMPLETE, so show_when_complete=False leaves it visible -- owner decision: the
    # user explicitly opted into the speculative bar, so it overrides the hide.
    assert bar_visible(True, False, t.Mode.POTENTIAL_TIER_XI, True) is True
    assert bar_visible(True, True, t.Mode.POTENTIAL_TIER_XI, True) is True
