"""Debug C# resolver specifically."""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from scanner import RepoScanner

nop = Path("projects/nopCommerce")
config = load_config(nop)
scanner = RepoScanner(config)
repo = scanner.scan()

# Print all C# files with Common in path
print("Files with 'Common' in path:")
count = 0
for fp in sorted(repo.files):
    if "Common" in os.path.dirname(fp) and fp.endswith(".cs"):
        print(f"  {fp}  (dir={os.path.dirname(fp)})")
        count += 1
        if count >= 10:
            print("  ...")
            break

print(f"\nTotal C# files: {len([f for f in repo.files if f.endswith('.cs')])}")

# Check resolver directly
from index import DependencyGraph
import_str = "Nop.Core.Domain.Common"
namespace_path = import_str.replace(".", "/")
print(f"\nChecking dir suffix '{namespace_path}':")
found = 0
for fp in repo.files:
    if fp.endswith(".cs"):
        d = os.path.dirname(fp)
        if d.endswith(namespace_path):
            print(f"  MATCH: {fp}")
            found += 1
            if found >= 5:
                break
        if d.endswith("/" + namespace_path):
            print(f"  MATCH(/) : {fp}")
            found += 1
            if found >= 5:
                break
if found == 0:
    print("  NONE found!")
    # Show some C# file dirs to compare
    cs_dirs = set()
    for fp in repo.files:
        if fp.endswith(".cs") and "/" in fp:
            cs_dirs.add(os.path.dirname(fp))
    for d in sorted(cs_dirs)[:10]:
        print(f"  Example dir: {d}")
