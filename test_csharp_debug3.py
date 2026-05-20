"""Debug C# resolver directly."""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from scanner import RepoScanner
from index import DependencyGraph

nop = Path("projects/nopCommerce")
config = load_config(nop)
scanner = RepoScanner(config)
repo = scanner.scan()

# Direct test
import_str = "Nop.Core.Domain.Common"
namespace_path = import_str.replace(".", "/")
print(f"namespace_path: {namespace_path}")

# Check guard
ends_with_ext = any(import_str.endswith(ext) for ext in (".h", ".hpp", ".cpp", ".cs", ".php", ".ts", ".js", ".vue", ".dart", ".py"))
dot_in = "." in import_str
not_prefix = not import_str.startswith(("@", "guid:"))
not_ext = not ends_with_ext
print(f"Guard: dot={dot_in}, not_prefix={not_prefix}, not_ext={not_ext}")

# Call resolver directly
result = DependencyGraph._resolve_csharp_import(import_str, repo)
print(f"Direct result: {result}")

# Manual check of the logic
candidate_dirs = set()
for file_path in repo.files:
    dir_path = os.path.dirname(file_path).replace("\\", "/")
    if dir_path.endswith(namespace_path):
        candidate_dirs.add(dir_path)
        print(f"  Match: {file_path} (dir={dir_path})")
    if dir_path.endswith("/" + namespace_path):
        candidate_dirs.add(dir_path)
        print(f"  Match(/) : {file_path} (dir={dir_path})")

print(f"Candidate dirs: {len(candidate_dirs)}")
for d in sorted(candidate_dirs)[:5]:
    print(f"  {d}")
    for fp in repo.files:
        if os.path.dirname(fp).replace("\\", "/") == d and fp.endswith(".cs"):
            print(f"    -> {fp}")
            break

# Also check: what paths does the scanner produce?
for fp in repo.files:
    if fp.endswith(".cs") and "Common" in fp:
        d = os.path.dirname(fp).replace("\\", "/")
        check = d.endswith("Nop/Core/Domain/Common")
        print(f"file={fp} dir={d} endswith? {check}")
        if check:
            break
