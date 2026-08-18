# -*- coding: utf-8 -*-
"""Pure resolver for the COMPLETE ("Fully Progressed") bar.

Answers one question: is EVERY progression category that applies to this vehicle
finished, and if so what did each of them cost? Applicability and done-ness are read
off snapshot fields the adapter already fills on every push, so this adds no reads:

    TECH_TREE      applies: tech_unlocks non-empty (a researched edge STAYS in the list
                            flagged researched=True) | done: every entry researched
                   Its total is the XP of everything researchable FROM this vehicle (the
                   OUTGOING unlock graph: modules + child vehicles), NOT what this
                   vehicle cost -- its own purchase price lives on the parent node.
                   Default modules are absent (they never appear in unlocksDescrs).
                   An empty graph means the category simply doesn't apply, so tier XI /
                   premium / nothing-left-to-research vehicles show no Research box.
    SKILL_TREE     applies: is_skill_tree             | done: skilltree_done >= total
    FIELD_MODS     applies: fieldmods_total > 0       | done: fieldmods_done == total
    ELITE_REWARDS  applies: elite_rewards non-empty   | done: every reward achieved
    ELITE          applies: has_prestige + grades     | done: level >= max_level

POTENTIAL_TIER_XI is deliberately absent: a speculative future Tier XI is never a
"completed" category (and when it applies + is opted in it outranks COMPLETE anyway).

Totals are RAW ``xp_cost`` -- never ``xp_cost_effective``: a blueprint discount is a
one-off per-player rebate, so reporting it would misstate the category's own cost. A total
that can't be derived degrades to 0 (the view then shows the icon with no cost line).

This is a GATE, so it fails CLOSED, not soft: applicability is probed separately from
done-ness/price, and an APPLICABLE category whose probe raises is kept and counted as
NOT done (``resolve()`` then returns ``[]``). Dropping it instead would let an
unreadable unfinished category stop vetoing and flip the vehicle to "Fully Progressed".
Only a category we cannot even tell applies is skipped -- the adapter's readers already
fail soft to empty, so there it is indistinguishable from "not applicable".
"""
from wgmod_research.domain import types as t
from wgmod_research.domain.resolvers import fieldmods


def _tech(s):
    unlocks = s.tech_unlocks or []
    return (all(getattr(u, "researched", False) for u in unlocks),
            sum(int(getattr(u, "xp_cost", 0) or 0) for u in unlocks))


def _skill(s):
    return (s.skilltree_done >= s.skilltree_total, int(s.skilltree_total_xp or 0))


def _field(s):
    # Same tier cap the FIELD_MODS bar uses -- levels above it are listed by the engine
    # but not unlockable at this tier, so they never cost anything. Steps priced <= 0 are
    # already filtered out upstream (post_progression_read).
    cap = fieldmods.max_level(s.tier)
    total = sum(int(getattr(st, "xp_cost", 0) or 0) for st in (s.field_mod_steps or [])
                if not st.level or st.level <= cap)
    return (s.fieldmods_done == s.fieldmods_total, total)


def _rewards(s):
    rewards = s.elite_rewards or []
    # Cost = the cumulative combat XP of the LAST reward's level (the same expression the
    # reward-track resolver promotes as its readout denominator).
    last = max(rewards, key=lambda r: r.level)
    return (all(r.achieved for r in rewards),
            int((s.elite_level_xp or {}).get(last.level, 0) or 0))


def _elite(s):
    # Cost = the cumulative combat XP to reach the level cap (elite_level_xp is cumulative).
    return (s.elite_level >= s.elite_max_level,
            int((s.elite_level_xp or {}).get(s.elite_max_level, 0) or 0))


# Bar-priority order (builder._BUILDERS), which is also the order the icons are shown in.
# (mode, applies?, probe -> (done, total)) -- the applicability test is kept OUT of the
# probe so a probe that raises can still be told apart from a category that doesn't apply.
_CATEGORIES = (
    (t.Mode.TECH_TREE, lambda s: bool(s.tech_unlocks), _tech),
    (t.Mode.SKILL_TREE, lambda s: bool(s.is_skill_tree), _skill),
    (t.Mode.FIELD_MODS, lambda s: bool(s.fieldmods_total), _field),
    (t.Mode.ELITE_REWARDS, lambda s: bool(s.elite_rewards), _rewards),
    (t.Mode.ELITE, lambda s: bool(s.has_prestige and s.elite_grades), _elite),
)


def resolve(snapshot, enabled=None):
    """``[(Mode string, total raw XP)]`` -- one entry per category that applies to this
    vehicle, ONLY when every one of them is finished. ``[]`` when something is still in
    progress, or when no category applies at all (the caller then keeps the old
    no-data COMPLETE placeholder). Never raises.

    `enabled` is the same Mode-string set/None the builder threads through everywhere
    else (None means "all on"). When given, a category whose Mode is OFF is skipped
    entirely -- excluded from both the all-done check and the returned list -- so
    Allow Fallthrough can reach COMPLETE on the categories the player left ON even
    while a still-in-progress category is disabled. Passing None (the default)
    reproduces the old behavior byte-for-byte."""
    cats = []
    for mode, applies, probe in _CATEGORIES:
        if enabled is not None and mode not in enabled:
            continue                    # user disabled this category -> ignore it
        try:
            if not applies(snapshot):
                continue
        except Exception:
            continue                    # can't even tell -> treat as not applicable
        try:
            done, total = probe(snapshot)
        except Exception:
            done, total = False, 0      # applicable but unreadable -> veto (fail CLOSED)
        cats.append((mode, done, total))
    if not cats or not all(done for (_m, done, _xp) in cats):
        return []
    return [(m, xp) for (m, _d, xp) in cats]
