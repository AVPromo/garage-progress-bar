# -*- coding: utf-8 -*-
"""Unit tests for the buff/nerf colour wiring in _read_common: _resolve_is_debuff
(the KPI_BACKWARD_OVERRIDE feed into format.resolve_is_debuff) and _kpi_lines'
neutral-cls path for the raw KPI name 'value'.

_read_common imports live game symbols at module load (helpers.dependency,
skeletons.gui.shared.IItemsCache) -- stub the minimum so it imports under pytest,
same pattern as test_post_progression_read.py. _resolve_is_debuff additionally
does a LOCAL import of gui.shared.items_parameters.comparator.BACKWARD_QUALITY_PARAMS
inside its try/except -- without stubbing that module too, the import raises and
the function silently falls back to the raw isDebuff (masking the very logic under
test), so it must be stubbed here as well. _kpi_lines locally imports
gui.impl.backport -- stubbed too."""
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

if "gui.shared.items_parameters.comparator" not in sys.modules:
    _gui = sys.modules.setdefault("gui", types.ModuleType("gui"))
    _gui_shared = types.ModuleType("gui.shared")
    _gui_ip = types.ModuleType("gui.shared.items_parameters")
    _gui_comp = types.ModuleType("gui.shared.items_parameters.comparator")
    # The real BACKWARD_QUALITY_PARAMS keys aim time under its vehParams name, not
    # its raw KPI name -- mirror that shape (see _resolve_is_debuff's docstring).
    _gui_comp.BACKWARD_QUALITY_PARAMS = frozenset(["aimingTime"])
    sys.modules["gui.shared"] = _gui_shared
    sys.modules["gui.shared.items_parameters"] = _gui_ip
    sys.modules["gui.shared.items_parameters.comparator"] = _gui_comp

if "gui.impl.backport" not in sys.modules:
    _gui_impl = types.ModuleType("gui.impl")
    _gui_impl_backport = types.ModuleType("gui.impl.backport")
    _gui_impl_backport.text = lambda x: x() if callable(x) else x
    _gui_impl_backport.image = lambda x: x() if callable(x) else x
    sys.modules["gui.impl"] = _gui_impl
    sys.modules["gui.impl.backport"] = _gui_impl_backport

from wgmod_research.adapter import _read_common as rc
from wgmod_research.adapter import format as f


# --- _resolve_is_debuff: the KPI_BACKWARD_OVERRIDE wiring --------------------

def test_gun_depression_override_resolves_to_buff():
    # raw game isDebuff=True is wrong (verified live) -- the override must flip it.
    assert rc._resolve_is_debuff("gunDepression", True) is False


def test_reload_time_in_clip_override_resolves_to_buff():
    assert rc._resolve_is_debuff("reloadTimeInClip", True) is False


def test_gun_elevation_not_overridden_stays_as_raw():
    # same mapped param ('pitchLimits') but the OTHER component -- must NOT flip.
    assert rc._resolve_is_debuff("gunElevation", True) is True
    assert rc._resolve_is_debuff("gunElevation", False) is False


def test_ordinary_forward_kpi_unaffected():
    # a KPI whose name and mapped param are both absent from BACKWARD_QUALITY_PARAMS
    # and from the override -- resolve_is_debuff keeps the raw flag verbatim.
    assert rc._resolve_is_debuff("nonHEShellDamage", False) is False
    assert rc._resolve_is_debuff("nonHEShellDamage", True) is True


def test_non_override_backward_param_still_flips_via_flat_set():
    # regression guard that stubbing the override didn't break the pre-existing
    # flat-BACKWARD_QUALITY_PARAMS flip (aim speed, see format.resolve_is_debuff).
    assert rc._resolve_is_debuff("vehicleGunAimSpeed", True) is False


# --- _kpi_lines: neutral cls for the raw 'value' KPI name --------------------

class _KPI(object):
    def __init__(self, name, type_, value, isDebuff, desc=""):
        self.name = name
        self.type = type_
        self.value = value
        self.isDebuff = isDebuff
        self._desc = desc

    def getDescriptionR(self):
        return self._desc


class _Desc(object):
    def __init__(self, kpi):
        self.kpi = kpi


class _Action(object):
    def __init__(self, kpi):
        self._descriptor = _Desc(kpi)


def _record_fields(line):
    return line.split(f.KPI_FIELD_SEP)


def test_raw_value_kpi_name_yields_neutral_cls():
    lines = rc._kpi_lines(_Action([_KPI("value", "add", 20.0, False, "to something")]))
    assert len(lines) == 1
    _, cls, value_str, desc = _record_fields(lines[0])
    assert cls == f.KPI_CLASS_NEUTRAL
    assert cls not in ("pos", "neg")
    assert value_str == "+20"
    assert desc == "to something"


def test_non_value_kpi_name_keeps_pos_neg_cls():
    # a named KPI (not the generic 'value' placeholder) still resolves to a real
    # pos/neg class through the normal isDebuff path, distinct from neutral.
    lines = rc._kpi_lines(
        _Action([_KPI("nonHEShellDamage", "add", 20.0, False, "to damage")]))
    assert len(lines) == 1
    _, cls, _, _ = _record_fields(lines[0])
    assert cls == "pos"
    assert cls != f.KPI_CLASS_NEUTRAL


def test_backward_override_kpi_colours_buff_through_kpi_lines():
    # end-to-end through _kpi_lines: gunDepression's raw isDebuff=True still ends
    # up 'pos' (green) once _resolve_is_debuff's override is applied.
    lines = rc._kpi_lines(
        _Action([_KPI("gunDepression", "add", -1.0, True, "to gun depression")]))
    assert len(lines) == 1
    _, cls, _, _ = _record_fields(lines[0])
    assert cls == "pos"
