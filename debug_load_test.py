import sys
import os
# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import __init__
    print(f"MAPPINGS_COUNT: {len(__init__.NODE_CLASS_MAPPINGS)}")
    if len(__init__.NODE_CLASS_MAPPINGS) > 0:
        print("SUCCESS: Nodes loaded!")
    else:
        print("FAILURE: Mappings are empty")
except Exception as e:
    import traceback
    traceback.print_exc()
