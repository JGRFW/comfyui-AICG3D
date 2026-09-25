import os
import re
import sys

# Get the directory where this script is located
root_dir = os.path.dirname(os.path.abspath(__file__))

def process_file(filepath, folder_prefix):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Fix "from ..X import Y" -> "from X import Y"
    content = re.sub(r"from \.\.([a-zA-Z0-9_.]+)\s+import", r"from \1 import", content)
    
    # 2. Fix "from . import X, Y" -> "import prefix.X, prefix.Y"
    def replace_from_dot_import(match):
        imports = match.group(1).strip()
        items = [i.strip() for i in imports.split(",")]
        return "import " + ", ".join([f"{folder_prefix}.{item}" for item in items])
    
    content = re.sub(r"from \. import (.*)", replace_from_dot_import, content)
    
    # 3. Fix "from .X import Y" -> "from prefix.X import Y"
    content = re.sub(r"from \.([a-zA-Z0-9_.]+)\s+import", r"from " + folder_prefix + r".\1 import", content)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

# Walk the plugin directory
for dirpath, dirnames, filenames in os.walk(root_dir):
    for filename in filenames:
        if filename.endswith(".py") and filename != "fix_all_imports.py":
            filepath = os.path.join(dirpath, filename)
            # Determine prefix
            prefix = ""
            if "aicg3d" in dirpath: prefix = "aicg3d"
            elif "h3easy" in dirpath: prefix = "h3easy"
            elif "h3goohai" in dirpath: prefix = "h3goohai"
            
            if prefix:
                process_file(filepath, prefix)

print("Relative Import Cleanup Completed Successfully.")
