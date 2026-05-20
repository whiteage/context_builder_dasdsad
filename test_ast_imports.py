"""Test that AST files contain imports after full pipeline."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from scanner import RepoScanner
from parsers.registry import get_parser
from parsers.base import ASTIndex
from index import DependencyGraph

def check_project(name, project_path):
    print(f"\n{'='*60}")
    print(f"PROJECT: {name}")
    print(f"{'='*60}")

    config = load_config(project_path)
    scanner = RepoScanner(config)
    repo = scanner.scan()

    ast = ASTIndex()
    for parser_id in config.parsers_needed:
        parser = get_parser(parser_id)
        if parser is None:
            continue
        eligible = [
            p for p, e in repo.files.items()
            if e.ast_eligible and e.language == parser.language
        ]
        if not eligible:
            continue
        print(f"Parser: {parser_id}, eligible: {len(eligible)}")
        result = parser.parse(str(config.project_path), eligible)
        print(f"  Files: {len(result.files)}, classes: {result.total_classes}, methods: {result.total_methods}")
        ast.files.update(result.files)
        ast.errors.extend(result.errors)

    ast.total_classes = sum(len(f.classes) for f in ast.files.values())
    ast.total_methods = sum(
        len(c.methods) for f in ast.files.values() for c in f.classes
    )

    # Check imports
    files_with_imports = len([f for f in ast.files.values() if f.imports])
    total_imports = sum(len(f.imports) for f in ast.files.values())
    print(f"AST: {len(ast.files)} files, {ast.total_classes} classes, {ast.total_methods} methods")
    print(f"Files with imports: {files_with_imports}")
    print(f"Total imports extracted: {total_imports}")

    if files_with_imports == 0:
        print("** NO IMPORTS IN AST — resolver won't be called!")
        return

    # Build deps
    deps = DependencyGraph.from_ast(ast, repo)
    total_deps = sum(len(v) for v in deps.dependencies.values())
    print(f"Dependency edges: {total_deps}")

    # Show a sample file with imports
    count = 0
    for path, fast in ast.files.items():
        if fast.imports:
            print(f"\n  Sample: {path}")
            print(f"  Imports ({len(fast.imports)}): {fast.imports[:10]}")
            # Show resolved deps
            resolved = deps.dependencies.get(path, set())
            print(f"  Resolved deps: {len(resolved)}")
            for r in list(resolved)[:5]:
                print(f"    -> {r}")
            count += 1
            if count >= 3:
                break


check_project("monica (PHP)", Path("projects/monica"))
check_project("nopCommerce (C#)", Path("projects/nopCommerce"))
check_project("EpicSurvivalGame (C++)", Path("projects/EpicSurvivalGame"))
