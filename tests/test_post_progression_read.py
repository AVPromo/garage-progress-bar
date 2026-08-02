# -*- coding: utf-8 -*-
"""Unit tests for post_progression_read._selected_idx: the guarded
isPurchased()/getPurchasedIdx() read behind ProgressionStep.selected_idx.

The module this lives in (_read_common, transitively) imports live game symbols
(helpers.dependency, skeletons.gui.shared.IItemsCache) at module load -- stub the
minimum so it imports under pytest, same pattern as test_settings_i18n.py."""
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

from wgmod_research.adapter.post_progression_read import _selected_idx


class _Action(object):
    def __init__(self, purchased, idx):
        self._purchased = purchased
        self._idx = idx

    def isPurchased(self):
        return self._purchased

    def getPurchasedIdx(self):
        return self._idx


def test_selected_idx_returns_the_purchased_index():
    assert _selected_idx(_Action(True, 1)) == 1


def test_selected_idx_is_minus_one_when_nothing_purchased():
    assert _selected_idx(_Action(False, 0)) == -1


def test_selected_idx_fails_soft_when_is_purchased_raises():
    class Boom(object):
        def isPurchased(self):
            raise RuntimeError("unreadable")

    assert _selected_idx(Boom()) == -1


def test_selected_idx_fails_soft_when_get_purchased_idx_raises():
    class Boom(object):
        def isPurchased(self):
            return True

        def getPurchasedIdx(self):
            raise RuntimeError("unreadable")

    assert _selected_idx(Boom()) == -1
