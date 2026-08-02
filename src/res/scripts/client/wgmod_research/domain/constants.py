# -*- coding: utf-8 -*-
"""Shared string ids used across the domain, adapter, and view.

These were bare string literals scattered across the resolvers, recent.py, and the
engine adapter (and mirrored in WGModResearch.js). Centralizing them means a typo is
a NameError instead of a silently mismatched tick that renders wrong. Values are the
contract with the widget JS -- do not change a value without updating the JS that
switches on Tick.category / grade family. 2/3-compatible, engine-free.
"""


class Category(object):
    """Tick.category -- drives the per-tick glyph the widget renders. A bar is
    all-tech-tree (VEHICLE + MODULE ticks), all-field-mods, all-skill-tree, or an
    elite band (ELITE / REWARD)."""
    VEHICLE = "vehicle"      # tech-tree: a next-vehicle unlock (also UnlockItem.kind)
    MODULE = "module"        # tech-tree: a module unlock (also UnlockItem.kind)
    FIELDMOD = "fieldmod"    # a Field Modifications step
    UPGRADE = "upgrade"      # a tier-XI skill-tree node
    ELITE = "elite"          # a prestige grade pip
    REWARD = "reward"        # a tier-exclusive milestone reward thumbnail


# --- Packed multi-value string fields (the ONE delimiter convention) ------------------
# Several model string fields carry more than one value, packed with control chars that
# never occur in localized text. FIELD_SEP (U+001F, unit separator) splits the fields
# WITHIN one record -- it is the same separator the KPI buff lines already use
# (adapter/format.KPI_FIELD_SEP aliases this, so there is exactly one definition), and
# ROW_SEP (U+001E, record separator) splits whole records. Used by the COMPLETE
# per-category breakdown (builder._complete_effect -> UpgradeVM.effect), whose rows are a
# uniform 4 fields each. Mirrored in WGModResearch.js as BUFF_SEP / ROW_SEP.
FIELD_SEP = u"\x1f"
ROW_SEP = u"\x1e"


class GradeFamily(object):
    """Elite-Levels grade family id (EliteGrade.grade). PRESTIGE is the synthetic
    terminal MAX grade; UNDEFINED is the game's below-first-grade sentinel."""
    IRON = "iron"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    ENAMEL = "enamel"
    PRESTIGE = "prestige"
    UNDEFINED = "undefined"
