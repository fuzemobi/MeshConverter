#!/usr/bin/env python3
"""
Test FreeCAD headless mode (no GUI hanging).

This script proves FreeCAD can run without opening a window.
"""

import sys
import os

# CRITICAL: Set environment before importing FreeCAD
os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Prevent Qt GUI
os.environ['FREECAD_NO_GUI'] = '1'

# Add FreeCAD to Python path (macOS)
FREECAD_LIB_PATH = '/Applications/FreeCAD.app/Contents/Resources/lib'
if os.path.exists(FREECAD_LIB_PATH):
    sys.path.append(FREECAD_LIB_PATH)
else:
    print("❌ FreeCAD not found at expected path")
    print("   Please install FreeCAD or update path")
    sys.exit(1)

try:
    print("🔧 Importing FreeCAD (headless mode)...")
    import FreeCAD
    import Part
    import Mesh
    print("✅ FreeCAD imported successfully (no GUI)")

    # Create document (no window opens)
    print("\n📄 Creating FreeCAD document...")
    doc = FreeCAD.newDocument("Test")
    print(f"✅ Document created: {doc.Name}")

    # Test basic operations
    print("\n🔨 Testing Part.makeBox...")
    box = Part.makeBox(10, 10, 10)
    print(f"✅ Box created: volume={box.Volume:.2f} mm³")

    # Close document (no GUI to close)
    print("\n🚪 Closing document...")
    FreeCAD.closeDocument(doc.Name)
    print("✅ Document closed (no hanging!)")

    print("\n🎉 SUCCESS: FreeCAD runs headless without GUI issues")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
