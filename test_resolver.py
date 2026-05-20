"""Quick test for import resolution on PHP/C#/C++."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from scanner import RepoScanner
from parsers.base import ASTIndex
from parsers.registry import get_parser
from index import DependencyGraph

def test_import_resolution(project_name, project_path, sample_imports):
    print(f"\n{'='*60}")
    print(f"PROJECT: {project_name}")
    print(f"{'='*60}")

    config = load_config(project_path)
    scanner = RepoScanner(config)
    repo = scanner.scan()

    # Build a minimal AST with just imports (no full parse needed for quick test)
    # Actually let's just test the resolve method directly
    for source_file, import_str in sample_imports:
        resolved = DependencyGraph._resolve_import(import_str, source_file, repo)
        status = "MATCH" if resolved else "NO MATCH"
        print(f"  [{status}] {source_file}")
        print(f"           imports '{import_str}'")
        if resolved:
            print(f"           --> {resolved}")

# Test PHP
monica = Path("projects/monica")
test_import_resolution("monica (PHP)", monica, [
    ("app/Models/Contact.php", "App\\Models\\Company"),
    ("app/Domains/Contact/ManageContact/Services/CreateContact.php", "App\\Services\\BaseService"),
    ("app/Http/Controllers/Controller.php", "Illuminate\\Foundation\\Auth\\Access\\AuthorizesRequests"),
    ("app/Actions/Fortify/CreateNewUser.php", "App\\Models\\User"),
])

# Test C#
nop = Path("projects/nopCommerce")
test_import_resolution("nopCommerce (C#)", nop, [
    ("src/Libraries/Nop.Core/Domain/Customers/Customer.cs", "Nop.Core.Domain.Common"),
    ("src/Libraries/Nop.Services/Customers/CustomerService.cs", "Nop.Core.Domain.Customers"),
    ("src/Presentation/Nop.Web/Controllers/HomeController.cs", "Nop.Services.Customers"),
])

# Test C++
ue = Path("projects/EpicSurvivalGame")
test_import_resolution("EpicSurvivalGame (C++)", ue, [
    ("SurvivalGame/Source/SurvivalGame/STypes.h", "Engine.h"),
    ("SurvivalGame/Source/SurvivalGame/Private/AI/BTTask_FindBotWaypoint.cpp", "BTTask_FindBotWaypoint.h"),
])
