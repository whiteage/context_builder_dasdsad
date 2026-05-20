"""Test each parser in isolation on all projects."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.DEBUG, format="%(name)s %(levelname)s: %(message)s")

from config import load_config
from parsers.registry import get_parser, check_available, PARSER_REGISTRY

PROJECTS_DIR = Path(__file__).parent / "projects"
PROJECTS = {
    "directus": PROJECTS_DIR / "directus",
    "EpicSurvivalGame": PROJECTS_DIR / "EpicSurvivalGame",
    "FPSSample": PROJECTS_DIR / "FPSSample",
    "monica": PROJECTS_DIR / "monica",
    "nopCommerce": PROJECTS_DIR / "nopCommerce",
    "rustdesk": PROJECTS_DIR / "rustdesk",
    "strapi": PROJECTS_DIR / "strapi",
}

def test_parser_on_project(parser_id, project_name, project_path):
    """Test a single parser on a single project."""
    print(f"\n{'='*60}")
    print(f"PARSER: {parser_id:12s} | PROJECT: {project_name}")
    print(f"{'='*60}")

    config = load_config(project_path)
    print(f"  Detected types: {[(p.type_id, p.parser) for p in config.project_types]}")
    print(f"  Parsers needed: {config.parsers_needed}")

    if parser_id not in config.parsers_needed:
        print(f"  SKIP: parser {parser_id} not required for this project")
        return

    # Check tool availability
    available = check_available(parser_id)
    print(f"  Tool available: {available}")

    # Get parser
    parser = get_parser(parser_id)
    if parser is None:
        print(f"  ERROR: parser not found")
        return

    # Get eligible files
    from scanner import RepoScanner
    scanner = RepoScanner(config)
    repo = scanner.scan()

    eligible = [p for p, e in repo.files.items() if e.ast_eligible and e.language == parser.language]
    print(f"  Eligible files: {len(eligible)}")

    if not eligible:
        print(f"  SKIP: no eligible files")
        return

    # Run parser
    try:
        result = parser.parse(str(config.project_path), eligible)
        print(f"  Files with AST: {len(result.files)}")
        print(f"  Total classes: {result.total_classes}")
        print(f"  Total methods: {result.total_methods}")
        print(f"  Total errors: {len(result.errors)}")

        # Show errors if any
        for err in result.errors[:5]:
            print(f"    Error: {err.file_path}: {err.message}")

        # Show sample classes
        sample_count = 0
        for path, fast in list(result.files.items())[:5]:
            print(f"  File: {path}")
            print(f"    Namespace: {fast.namespace}")
            print(f"    Imports: {len(fast.imports)}")
            print(f"    Classes: {len(fast.classes)}")
            for cls in fast.classes[:3]:
                print(f"      {cls.class_type} {cls.name} (base: {cls.base_types}, methods: {len(cls.methods)})")

        # Check imports specifically
        files_with_imports = len([f for f in result.files.values() if f.imports])
        total_imports = sum(len(f.imports) for f in result.files.values())
        print(f"  Files with imports: {files_with_imports}")
        print(f"  Total imports extracted: {total_imports}")
        if files_with_imports == 0 and len(result.files) > 0:
            print(f"  ** WARNING: No imports extracted! Dependency graph will be empty.")

    except Exception as e:
        print(f"  CRASH: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("="*80)
    print("PARSER ISOLATION TESTS")
    print("="*80)

    # First, show which tools are available
    print("\n--- TOOL AVAILABILITY ---")
    for pid in PARSER_REGISTRY:
        print(f"  {pid:12s}: {'AVAILABLE' if check_available(pid) else 'MISSING'}")

    # Test each parser on all relevant projects
    for parser_id in PARSER_REGISTRY:
        for proj_name, proj_path in PROJECTS.items():
            if not proj_path.exists():
                continue
            test_parser_on_project(parser_id, proj_name, proj_path)


if __name__ == "__main__":
    main()
