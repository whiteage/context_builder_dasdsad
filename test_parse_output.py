"""Debug _parse_ts_output to find why classes are lost."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Run TS analyzer on directus
result = subprocess.run(
    ["node", str(Path("parsers/ts-analyzer/analyze.mjs")), str(Path("projects/directus"))],
    capture_output=True, text=True, timeout=120,
)
print(f"STDOUT length: {len(result.stdout)}")
print(f"STDERR: {result.stderr[:500]}")

# Parse JSON
data = json.loads(result.stdout)
print(f"Files in JSON: {len(data['files'])}")

# Count classes
files_with_classes = [f for f in data['files'] if f.get('classes')]
print(f"Files with classes: {len(files_with_classes)}")

total_cls = sum(len(f.get('classes', [])) for f in data['files'])
total_meth = sum(len(c.get('methods', [])) for f in data['files'] for c in f.get('classes', []))
print(f"JSON total classes: {total_cls}")
print(f"JSON total methods: {total_meth}")

# Now parse with Python
from parsers.typescript import _parse_ts_output
parsed = _parse_ts_output(result.stdout)
print(f"\nParsed files: {len(parsed.files)}")
print(f"Parsed total_classes: {parsed.total_classes}")
print(f"Parsed total_methods: {parsed.total_methods}")

# Check if classes are in parsed files
for path, fast in parsed.files.items():
    if fast.classes:
        print(f"  FIRST FILE WITH CLASSES: {path} -> {len(fast.classes)} classes")
        for cls in fast.classes[:3]:
            print(f"    {cls.class_type} {cls.name}: {len(cls.methods)} methods, extends={cls.base_types}")
        break
else:
    print("  NO FILES WITH CLASSES FOUND IN PARSED OUTPUT!")
    # Check the first file that SHOULD have classes
    for f in files_with_classes[:3]:
        path = f['path']
        print(f"  JSON has {len(f['classes'])} classes for: {path}")
        if path in parsed.files:
            fast = parsed.files[path]
            print(f"    But parsed FileAST has {len(fast.classes)} classes")
            if fast.classes:
                print(f"    First class: {fast.classes[0].name}")
        else:
            print(f"    Path NOT in parsed.files!")
