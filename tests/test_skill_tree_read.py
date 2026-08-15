# -*- coding: utf-8 -*-
"""Unit tests for skill_tree_read.read_skill_tree()'s next-hop pass: for each
available (unlocked-frontier) node, its still-locked successors one hop further,
deduped by step_id with accumulated parent_ids. Same import-stub pattern as
test_post_progression_read.py -- the module's game imports (helpers.dependency,
skeletons.gui.shared.IItemsCache) are stubbed so it imports under pytest; every
live-only symbol touched inside (gui.impl.*) fails soft to an empty string, so the
fakes below only need to supply the plain read-side surface (stepID/getType/
getPrice/isReceived/isUnlocked/action/getNextStepIDs, pp.getStep)."""
import sys
import types

if "helpers" not in sys.modules:
    _helpers = types.ModuleType("helpers")
    _helpers.dependency = types.ModuleType("helpers.dependency")
    _helpers.dependency.instance = lambda *a, **k: None
    _helpers.dependency.descriptor = lambda *a, **k: None
    sys.modules["helpers"] = _helpers

if "skeletons" not in sys.modules:
    _skeletons = types.ModuleType("skeletons")
    _skeletons_gui = types.ModuleType("skeletons.gui")
    _skeletons_gui_shared = types.ModuleType("skeletons.gui.shared")
    _skeletons_gui_shared.IItemsCache = object
    sys.modules["skeletons"] = _skeletons
    sys.modules["skeletons.gui"] = _skeletons_gui
    sys.modules["skeletons.gui.shared"] = _skeletons_gui_shared

from wgmod_research.adapter.skill_tree_read import read_skill_tree


class _Price(object):
    def __init__(self, xp):
        self.xp = xp


class _Action(object):
    def __init__(self, image_name="perk"):
        self._image_name = image_name

    def getImageName(self):
        return self._image_name

    def getCategories(self):
        return ["firepower"]

    def getLocNameRes(self):
        return None


class _Step(object):
    """A postProgression step: a purchasable, non-ghost node by default."""
    def __init__(self, step_id, xp=1000, received=False, unlocked=False,
                 node_type="major", next_ids=(), raises_next=False):
        self.stepID = step_id
        self._xp = xp
        self._received = received
        self._unlocked = unlocked
        self._node_type = node_type
        self._next_ids = next_ids
        self._raises_next = raises_next
        self.action = _Action("perk_%s" % step_id)

    def getType(self):
        return self._node_type

    def getPrice(self):
        return _Price(self._xp)

    def isReceived(self):
        return self._received

    def isUnlocked(self):
        return self._unlocked

    def getNextStepIDs(self):
        if self._raises_next:
            raise RuntimeError("unreadable")
        return self._next_ids


class _PostProgression(object):
    def __init__(self, steps):
        self._steps = steps
        self._by_id = dict((s.stepID, s) for s in steps)

    def iterOrderedSteps(self):
        return list(self._steps)

    def getStep(self, step_id):
        return self._by_id.get(step_id)


class _Vehicle(object):
    def __init__(self, steps):
        self.postProgression = _PostProgression(steps)


def _next_map(result):
    """{step_id -> ProgressionStep} of the next_nodes half of the read_skill_tree
    tuple, for convenient by-id assertions."""
    next_nodes = result[9]
    return dict((n.step_id, n) for n in next_nodes)


def test_one_parent_next_node():
    avail = _Step(1, xp=1000, unlocked=True, next_ids=(2,))
    locked = _Step(2, xp=2000, next_ids=())
    veh = _Vehicle([avail, locked])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]

    assert [s.step_id for s in available] == [1]
    assert len(next_nodes) == 1
    assert next_nodes[0].step_id == 2
    assert next_nodes[0].parent_ids == [1]


def test_two_parent_convergent_next_node_dedupes_and_accumulates_parents():
    avail_a = _Step(1, xp=1000, unlocked=True, next_ids=(3,))
    avail_b = _Step(2, xp=1000, unlocked=True, next_ids=(3,))
    locked = _Step(3, xp=2000, next_ids=())
    veh = _Vehicle([avail_a, avail_b, locked])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]

    assert sorted(s.step_id for s in available) == [1, 2]
    assert len(next_nodes) == 1
    assert next_nodes[0].step_id == 3
    assert sorted(next_nodes[0].parent_ids) == [1, 2]


def test_no_next_when_successor_already_unlocked_or_received():
    avail = _Step(1, xp=1000, unlocked=True, next_ids=(2, 3))
    already_unlocked = _Step(2, xp=1000, unlocked=True)
    already_received = _Step(3, xp=1000, received=True)
    veh = _Vehicle([avail, already_unlocked, already_received])

    result = read_skill_tree(veh)
    next_nodes = result[9]

    assert next_nodes == []


def test_no_next_at_final_frontier_node():
    # A frontier node with no successors at all (the tree's tip).
    avail = _Step(1, xp=1000, unlocked=True, next_ids=())
    veh = _Vehicle([avail])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]

    assert [s.step_id for s in available] == [1]
    assert next_nodes == []


def test_fail_soft_get_next_step_ids_raises_keeps_available_frontier():
    boom = _Step(1, xp=1000, unlocked=True, next_ids=(2,), raises_next=True)
    ok = _Step(9, xp=1000, unlocked=True, next_ids=())
    locked = _Step(2, xp=2000)
    veh = _Vehicle([boom, ok, locked])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]

    # Both available frontier nodes survive despite one's getNextStepIDs() raising.
    assert sorted(s.step_id for s in available) == [1, 9]
    assert next_nodes == []


def test_final_type_successor_excluded_from_next_even_with_other_locked_successor():
    # Two available frontier nodes both point at the shared 'final' sink node
    # (as getNextStepIDs() does live on every node), plus one non-final locked
    # successor off the first parent. The sink must never surface as a "next"
    # chip -- it's the tree's terminal, already shown via the final end-tick.
    avail_a = _Step(1, xp=1000, unlocked=True, next_ids=(2, 99))
    avail_b = _Step(3, xp=1000, unlocked=True, next_ids=(99,))
    non_final_locked = _Step(2, xp=2000, next_ids=())
    final_sink = _Step(99, xp=5000, node_type="final", next_ids=())
    veh = _Vehicle([avail_a, avail_b, non_final_locked, final_sink])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]
    next_ids = _next_map(result)

    assert sorted(s.step_id for s in available) == [1, 3]
    assert 99 not in next_ids  # the final-type sink never becomes a "next" chip
    assert 2 in next_ids  # the non-final locked successor still surfaces normally
    assert len(next_nodes) == 1  # no leaked entry for the shared final sink


def test_fail_soft_get_step_raises_for_one_successor_others_unaffected():
    class _BoomPostProgression(_PostProgression):
        def getStep(self, step_id):
            if step_id == 20:
                raise RuntimeError("unreadable")
            return _PostProgression.getStep(self, step_id)

    avail = _Step(1, xp=1000, unlocked=True, next_ids=(20, 21))
    good_locked = _Step(21, xp=2000)
    veh = _Vehicle([avail, good_locked])
    veh.postProgression = _BoomPostProgression([avail, good_locked])

    result = read_skill_tree(veh)
    available, next_nodes = result[8], result[9]

    assert [s.step_id for s in available] == [1]
    assert [n.step_id for n in next_nodes] == [21]
