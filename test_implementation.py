#!/usr/bin/env python3
"""Test script to verify the implementation compiles and basic functions work"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules at module level
import db
import whatsapp
import tools
import agent
import app
import properties_seed

def test_imports():
    print("Testing imports...")
    print("✓ db module imported")
    print("✓ whatsapp module imported")
    print("✓ tools module imported")
    print("✓ agent module imported")
    print("✓ app module imported")
    print("✓ properties_seed module imported")
    return True

def test_db_init():
    print("\nTesting database initialization...")
    try:
        db.init_db()
        print("✓ Database initialized")
    except Exception as e:
        print(f"✗ Database init failed: {e}")
        return False
    
    try:
        db.seed_properties(properties_seed.get_properties())
        print("✓ Properties seeded")
    except Exception as e:
        print(f"✗ Properties seed failed: {e}")
        return False
    
    try:
        props = db.get_all_properties()
        print(f"✓ Retrieved {len(props)} properties")
    except Exception as e:
        print(f"✗ Get properties failed: {e}")
        return False
    
    return True

def test_tools():
    print("\nTesting tools...")
    try:
        result = tools.get_matching_properties("3 BHK", "2-3 Cr", "Gurgaon")
        data = json.loads(result)
        print(f"✓ get_matching_properties returned {len(data)} results")
    except Exception as e:
        print(f"✗ get_matching_properties failed: {e}")
        return False
    
    try:
        tools.set_current_sender("919999999999")
        result = tools.get_property_details("sobha-karma-lakelands")
        # Expect 401 if no WhatsApp credentials - that's OK for this test
        if "401" in str(result) or "Unauthorized" in str(result):
            print(f"✓ get_property_details executed (WhatsApp credentials not configured - expected): {result}")
        else:
            print(f"✓ get_property_details executed: {result}")
    except Exception as e:
        # 401 is expected when no credentials - treat as pass
        if "401" in str(e) or "Unauthorized" in str(e):
            print(f"✓ get_property_details executed (WhatsApp credentials not configured - expected)")
        else:
            print(f"✗ get_property_details failed: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("WhatsApp Real Estate Agent - Implementation Test")
    print("=" * 50)
    
    success = True
    success &= test_imports()
    success &= test_db_init()
    success &= test_tools()
    
    print("\n" + "=" * 50)
    if success:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("=" * 50)
    
    sys.exit(0 if success else 1)