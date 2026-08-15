# -*- coding: utf-8 -*-
"""PC-only reader for the tier-XI "vehicle skill tree" subsystem (EU 2.3).

Extracted from engine_adapter.py (Tier 3g): reads a branching post-progression
(tree id >= VEH_SKILL_TREE_ID_OFFSET) into the count-based skill-tree fields +
the clickable "Upgrades Available:" frontier. engine_adapter.build_snapshot() calls
read_skill_tree / is_skill_tree (imported there under their old private aliases
_read_skill_tree / _is_skill_tree); post_progression_read also calls is_skill_tree to
bail so the linear FIELD_MODS reader never runs on a skill-tree vehicle. Shares only the
KPI-number formatter with the other readers, via adapter._read_common. Fully guarded.
Game symbols verified against the EU 2.3 decompiled client.
"""
import re

from wgmod_research._compat import LOG_CURRENT_EXCEPTION, _safe
from wgmod_research.adapter import i18n
from wgmod_research.adapter._read_common import _kpi_number_lines
from wgmod_research.adapter.format import (
    skilltree_icon as _skilltree_icon, humanize as _humanize,
    skilltree_value as _skilltree_value,
    fill_kpi_placeholders as _fill_kpi_placeholders,
    kpi_record_labeled as _kpi_record_labeled,
    mark_color_tags as _mark_color_tags)
from wgmod_research.domain import types as t


# Localized names a skill-tree node may carry that are too generic to show, and the
# shape of ID-like image names (vehicle-specific 'mechanic' nodes, incl. the final).
_ST_GENERIC_NAMES = frozenset((u"Modification",))
_ST_ID_RE = re.compile(r"(^s\d+_|mechanic|_\d+$)", re.I)


def _skilltree_title(image_name):
    """The node's real localized title from
    R.strings.veh_skill_tree.tooltips.title.dyn(<imageName>) -- the same source the
    Upgrades screen uses (verified live: 's36_mechanic_3' -> 'Hydraulic-Driven
    Rammer', 'invisibilityWhenShooting' -> 'Concealment After Firing'). "" if absent."""
    if not image_name:
        return u""
    try:
        from gui.impl.gen import R
        from gui.impl import backport
        acc = R.strings.veh_skill_tree.tooltips.title.dyn(image_name)
        if acc is not None and acc.isValid():
            return backport.text(acc()) or u""
    except Exception:
        LOG_CURRENT_EXCEPTION()
    return u""


def _skilltree_name(action, node_type):
    """Best readable name for a skill-tree node's tooltip. Tiered, since no single
    source covers every node type (verified live):
      1) the localized tooltips.title keyed by image name -- authoritative, covers
         perks AND signature 'mechanic' nodes;
      2) else a meaningful action loc name -- slot/config nodes give a real one
         ('Alternate Configuration: Auxiliary Loadout');
      3) else the humanized image id for a real perk; else a clean generic."""
    image_name = _safe(lambda: action.getImageName(), "") or ""
    title = _skilltree_title(image_name)
    if title:
        return title
    loc = u""
    try:
        from gui.impl import backport
        acc = action.getLocNameRes()
        loc = (backport.text(acc() if callable(acc) else acc) or u"").strip()
    except Exception:
        loc = u""
    if loc and loc not in _ST_GENERIC_NAMES:
        return loc
    if image_name and not _ST_ID_RE.search(image_name):
        return _humanize(image_name)
    return "Final Upgrade" if node_type == "final" else "Vehicle Upgrade"


def is_skill_tree(veh):
    """True for a tier-XI "vehicle skill tree" upgrade vehicle (branching
    post-progression, tree id >= VEH_SKILL_TREE_ID_OFFSET=10000). Best-effort:
    any failure -> False, so the vehicle is treated as an ordinary (linear
    field-mod) post-progression vehicle. Verified: gui_items Vehicle exposes
    .postProgression, whose model has isVehSkillTree()."""
    try:
        if not veh.isPostProgressionExists:
            return False
        return bool(veh.postProgression.isVehSkillTree())
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return False


def _skilltree_fields(action, node_type):
    """The common ProgressionStep fields shared by an available-frontier node and a
    locked next-hop successor: localized name, icon, effect text, and the node's own
    category sub-heading. Factored out so both callers stay in lockstep."""
    image_name = _safe(lambda: action.getImageName(), "") or ""
    # The node's OWN category (single key from getCategories()) -> its localized
    # Upgrades-screen sub-heading (e.g. "Category: Firepower", "Mechanic Upgrade").
    cat_key = _safe(lambda: sorted(action.getCategories())[0], "") or ""
    return dict(
        name=_skilltree_name(action, node_type),
        icon=_skilltree_icon(node_type, image_name),
        description=_skilltree_effect(action),
        category=i18n.skilltree_category(cat_key))


def _priced_step(step):
    """(node_type, xp_cost) for a step, or None if it's a ghost layout placeholder or
    carries no price (not a purchasable upgrade node) -- the same exclusion the main
    dedup loop applies. Never raises."""
    node_type = _safe(lambda: step.getType(), "") or ""
    if node_type == "ghost":
        return None
    price = step.getPrice()
    xp_cost = int(getattr(price, "xp", 0) or 0)
    if xp_cost <= 0:
        return None
    return node_type, xp_cost


def read_skill_tree(veh):
    """Aggregate the branching skill tree into
    (total_xp, spent_xp, done, total, final_icon, final_name, final_xp, final_effect,
    available, next_nodes). The bar stays a COUNT
    readout (owner directive: non-linear tree), but `available` carries the frontier
    nodes (not received, prerequisites met) as [ProgressionStep] for the clickable
    "Upgrades Available:" chips, and `next_nodes` carries their still-LOCKED immediate
    successors (one hop past the frontier) so the widget can draw "available -- next"
    chains. done/total
    are the priced, non-ghost nodes unlocked vs. available; final_icon is the
    'final' node's art (img:// URL) for the rightmost tick. total_xp/spent_xp are
    retained for completeness but no longer drive the (count-based) bar.

    Steps come from the same veh.postProgression.iterOrderedSteps() the linear
    reader uses, but here each is a tree node: getPrice().xp, isReceived(),
    getType() ('major'/'special'/'final'/'common'/'ghost'). 'ghost' nodes are
    layout placeholders and zero-price nodes aren't purchasable, so neither counts.
    The 'final' node carries the tank's signature upgrade; its icon comes off the
    action model the same way field mods read theirs (action.getImageName()).

    CRITICAL: the skill tree is a DAG, so iterOrderedSteps() visits a node ONCE PER
    incoming parent edge -- a node with two parents is yielded twice (verified live:
    Hirschkaefer yields 32 steps for 26 unique nodes). We dedupe by stepID, else
    both the cost and the N/M count are inflated. Fully guarded -> (0,...,"") on
    any failure (bar falls back to COMPLETE).

    Next-hop successors: PostProgressionStepItem.getNextStepIDs() returns the node's
    descriptor.unlocks (verified against the decompiled EU 2.3 client); each id is
    loaded back through pp.getStep(id) (the same accessor iterOrderedSteps() itself
    uses). A successor is kept only while it is STILL LOCKED (not received, not yet
    unlocked) -- one that already unlocked belongs on the frontier, not the "next"
    chain. Reachable from two available parents -> ONE record, both parent step_ids
    in `parent_ids` (the tree's OR-rule: either parent alone unlocks it). Every
    per-successor step is independently guarded so one bad id degrades to "skip it",
    never to dropping the whole available bar."""
    total_xp = 0
    spent_xp = 0
    done = 0
    total = 0
    final_icon = ""
    final_name = ""
    final_xp = 0
    final_effect = ""
    available = []
    available_steps = []  # [(step_id, step)] -- the frontier, for the next-hop pass below
    seen = set()
    try:
        pp = veh.postProgression
        for step in pp.iterOrderedSteps():
            try:
                step_id = getattr(step, "stepID", None)
                if step_id in seen:
                    continue  # DAG: shared node already counted via another parent
                seen.add(step_id)
                node_type = _safe(lambda: step.getType(), "") or ""
                if node_type == "ghost":
                    continue
                price = step.getPrice()
                xp_cost = int(getattr(price, "xp", 0) or 0)
                if xp_cost <= 0:
                    continue  # not a purchasable upgrade node
                total += 1
                total_xp += xp_cost
                if bool(step.isReceived()):
                    done += 1
                    spent_xp += xp_cost
                elif _safe(lambda: step.isUnlocked(), False):
                    # AVAILABLE FRONTIER: not received but prerequisites met
                    # (isUnlocked() resolves the DAG parent rule). These become the
                    # clickable "Upgrades Available:" chips. isLocked() is its inverse
                    # (prereqs not met) -- verified live: only reachable nodes are
                    # isUnlocked.
                    available.append(t.ProgressionStep(
                        step_id=step_id, xp_cost=xp_cost, unlocked=False,
                        **_skilltree_fields(step.action, node_type)))
                    available_steps.append((step_id, step))
                # the signature 'final' upgrade -> its icon + name + cost for the end
                # tick (which carries a tooltip like the available chips).
                if node_type == "final" and not final_icon:
                    action = getattr(step, "action", None)
                    if action is not None:
                        image_name = _safe(lambda: action.getImageName(), "") or ""
                        final_icon = _skilltree_icon("final", image_name)
                        final_name = _skilltree_name(action, "final")
                        final_xp = xp_cost
                        final_effect = _skilltree_effect(action)
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue

        # Second pass: one hop past the frontier -- each available node's still-locked
        # successors, deduped by step_id across shared (two-parent) nodes.
        next_nodes = []
        next_by_id = {}
        for avail_id, step in available_steps:
            try:
                next_ids = step.getNextStepIDs() or ()
            except Exception:
                LOG_CURRENT_EXCEPTION()
                continue
            for next_id in next_ids:
                try:
                    rec = next_by_id.get(next_id)
                    if rec is not None:
                        rec.parent_ids.append(avail_id)
                        continue
                    succ = pp.getStep(next_id)
                    if succ is None or bool(succ.isReceived()) or _safe(
                            lambda: succ.isUnlocked(), False):
                        continue  # already received / already on the frontier -> not "next"
                    priced = _priced_step(succ)
                    if priced is None:
                        continue
                    succ_type, succ_xp = priced
                    if succ_type == "final":
                        continue  # tree terminal sink, already shown as the final end-tick; never a "next" chip
                    rec = t.ProgressionStep(
                        step_id=next_id, xp_cost=succ_xp, unlocked=False,
                        parent_ids=[avail_id],
                        **_skilltree_fields(succ.action, succ_type))
                    next_by_id[next_id] = rec
                    next_nodes.append(rec)
                except Exception:
                    LOG_CURRENT_EXCEPTION()
                    continue

        return (total_xp, spent_xp, done, total, final_icon, final_name, final_xp,
                final_effect, available, next_nodes)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return 0, 0, 0, 0, "", "", 0, "", [], []


def _skilltree_effect(action):
    """Effect/bonus text for a tier-XI skill-tree node.

    Signature 'mechanic' perks (major/final) describe themselves in a localized
    SENTENCE template keyed by image name:
    R.strings.veh_skill_tree.tooltips.description.dyn(<imageName>), e.g. "Reduces gun
    reload time by {value}% in Pillbox mode." A multi-KPI node INDEXES its slots
    instead ('{value0}', '{value1}' -- the tier-XI French TD final node); both
    spellings are filled from the node's KPI magnitudes (_fill_kpi_placeholders,
    _skilltree_value); the {colorTagOpen/Close} pair around the highlighted run becomes
    the widget's highlight sentinels (format.mark_color_tags), so the run renders in
    WG's own bright parchment like the native perk tooltip.

    Most nodes' templates are QUALITATIVE with no magnitude slot (e.g. "Reduces gun
    dispersion when your gun is damaged.") -- the number lives only in the KPI. For
    those we append the KPI's signed magnitude line(s) via _kpi_number_lines, e.g.
    "...\n-20% to dispersion of a damaged gun", so the buff shows a figure. Ordinary
    stat perks with NO template fall back to those KPI lines alone ("+10% to hull
    elevation speed"). Feature/role slots (and negligible ~zero deltas) carry no
    numbered KPI line -> "" (unchanged). Verified live (EU 2.3). Never raises."""
    try:
        from gui.impl import backport
        from gui.impl.gen import R
        image_name = _safe(lambda: action.getImageName(), "") or ""
        tmpl = ""
        if image_name:
            rid = R.strings.veh_skill_tree.tooltips.description.dyn(image_name)
            tmpl = backport.text(rid() if callable(rid) else rid) or ""
        # A record with neither an icon nor a phrase is a naked coloured figure with
        # nothing to name it (a 'mechanic' node's generic 'value' KPI) -- never a line.
        kpi_lines = "\n".join(r for r in _kpi_number_lines(action)
                              if _kpi_record_labeled(r))
        if not tmpl or tmpl.startswith("#"):
            return kpi_lines  # no sentence template -> KPI-derived line(s) only
        value = _skilltree_value(action)
        text, subbed = _fill_kpi_placeholders(tmpl, action)
        filled = _mark_color_tags(text.replace("{value}", value)).strip()
        if subbed or "{value}" in tmpl:
            # Template embeds its own magnitude slot(s) (signature 'mechanic' perks):
            # the sentence already carries the numbers, so the KPI lines are NOT
            # appended. If nothing filled (defensive, not seen on EU 2.3), prefer the
            # KPI-derived line so a numberless "by %" doesn't reach the tooltip.
            return filled if (subbed or value) else (kpi_lines or filled)
        # Qualitative sentence, no magnitude slot: append the KPI's signed number(s).
        return (filled + "\n" + kpi_lines) if (filled and kpi_lines) else (filled or kpi_lines)
    except Exception:
        LOG_CURRENT_EXCEPTION()
        return ""
