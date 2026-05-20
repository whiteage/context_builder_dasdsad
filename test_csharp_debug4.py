"""Debug C# resolver with new algorithm."""
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

# Test the new resolver directly
for import_str in ["Nop.Core.Domain.Common", "Nop.Core.Domain.Customers", "Nop.Services.Customers"]:
    result = DependencyGraph._resolve_csharp_import(import_str, repo)
    print(f"_resolve_csharp_import('{import_str}') -> {result}")

# Now test through _resolve_import
for source_file, import_str in [
    ("src/Libraries/Nop.Core/Domain/Customers/Customer.cs", "Nop.Core.Domain.Common"),
    ("src/Libraries/Nop.Services/Customers/CustomerService.cs", "Nop.Core.Domain.Customers"),
]:
    # Manually trace the guard
    dot_in = "." in import_str
    not_prefix = not import_str.startswith(("@", "guid:"))
    ends_with_ext = any(import_str.endswith(ext) for ext in (".h", ".hpp", ".cpp", ".cs", ".php", ".ts", ".js", ".vue", ".dart", ".py"))
    print(f"\nImport: '{import_str}' from '{source_file}'")
    print(f"  Guard: dot={dot_in}, not_prefix={not_prefix}, not_ext={not ends_with_ext}")

    if dot_in and not_prefix and not ends_with_ext:
        result = DependencyGraph._resolve_csharp_import(import_str, repo)
        print(f"  C# resolver: {result}")
    else:
        print(f"  Guard FAILED")

    # Full resolve
    full_result = DependencyGraph._resolve_import(import_str, source_file, repo)
    print(f"  Full _resolve_import: {full_result}")
