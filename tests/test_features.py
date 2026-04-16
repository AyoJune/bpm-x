#!/usr/bin/env python3
"""Quick test of new VZN polish features."""

import interface.gui
from core.translator import KeyTranslator

print("✓ GUI imports successfully")
print(f"✓ DnD Status Support: {interface.gui.HAS_DND}")

t = KeyTranslator()

# Test with Camelot notation
camelot_ref = "8A"
compat = t.get_compatible_keys(camelot_ref)
print(f"✓ Harmonics API Test ({camelot_ref}): {compat}")

# Simulate what the GUI does
neighbors = compat.get("same_mode", []) + [compat.get("relative_major_minor", "")]
neighbors = [n for n in neighbors if n and n != camelot_ref][:3]
harmonics_display = ", ".join(neighbors)
print(f"✓ Harmonics Display Format: {harmonics_display}")

print("\n✓ All features ready for launch!")
