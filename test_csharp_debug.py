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

import_str = "Nop.Core.Domain.Common"
namespace_path = import_str.replace(".", "/")
print(f"namespace_path: {namespace_path}")

# Check guard condition
source_file = "src/Libraries/Nop.Core/Domain/Customers/Customer.cs"
source_dir = os.path.dirname(source_file)

# Check guard
ends_with_ext = any(import_str.endswith(ext) for ext in (".h", ".hpp", ".cpp", ".cs", ".php", ".ts", ".js", ".vue", ".dart", ".py"))
print(f"Guard: '.' present={'.' in import_str}, not @/guid={not import_str.startswith(('@', 'guid:'))}, not ext={not ends_with_ext}")

# Find matching dirs
candidate_dirs = set()
for file_path in repo.files:
    dir_path = os.path.dirname(file_path)
    if dir_path.endswith(namespace_path) or dir_path.endswith("/" + namespace_path):
        candidate_dirs.add(dir_path)

print(f"Matching dirs: {len(candidate_dirs)}")
for d in sorted(candidate_dirs)[:5]:
    print(f"  {d}")
    for fp in repo.files:
        if os.path.dirname(fp) == d and fp.endswith(".cs"):
            print(f"    -> {fp}")
            break

# Also check if the problem is that nopCommerce uses regex fallback which might not extract usings
# Let's check a sample C# file
sample = nop / "src" / "Libraries" / "Nop.Core" / "Domain" / "Customers" / "Customer.cs"
if sample.exists():
    content = sample.read_text(encoding="utf-8", errors="replace")
    import re
    usings = re.findall(r"using\s+([\w.]+)\s*;", content)
    print(f"\nSample file: {sample.name}")
    print(f"Using statements found: {usings[:10]}")
