"""Debug C# resolver algorithm."""
import sys, os
from pathlib import Path
sys.path.insert(0, 'src')
from config import load_config
from scanner import RepoScanner
from index import DependencyGraph

nop = Path('projects/nopCommerce')
config = load_config(nop)
scanner = RepoScanner(config)
repo = scanner.scan()

# Direct test
import_parts = ['Nop', 'Core', 'Domain', 'Common']
n = len(import_parts)

dirs = {}
for fp in repo.files:
    if fp.endswith('.cs'):
        d = os.path.dirname(fp).replace('\\', '/')
        if d not in dirs:
            dirs[d] = fp

print('Total .cs dirs:', len(dirs))

# Check specific dir
d = 'src/Libraries/Nop.Core/Domain/Common'
if d in dirs:
    dir_parts = d.split('/')
    print('Found! dir_parts =', dir_parts)
    joined = '.'.join(dir_parts[-n:])
    print('Last %d parts: %s' % (n, joined))
    print('Match?', joined == 'Nop.Core.Domain.Common')
    for start in range(1, len(dir_parts) - n + 1):
        j = '.'.join(dir_parts[start:start + n])
        ok = 'MATCH' if j == 'Nop.Core.Domain.Common' else ''
        print('  start=%d: %s %s' % (start, j, ok))
else:
    print('Dir NOT in dirs:', d)
    for k in sorted(dirs):
        if 'Nop.Core' in k and 'Domain' in k and 'Common' in k:
            print('  Similar:', k)
            dir_parts = k.split('/')
            for start in range(len(dir_parts) - n + 1):
                j = '.'.join(dir_parts[start:start + n])
                ok = 'MATCH' if j == 'Nop.Core.Domain.Common' else ''
                print('    start=%d: %s %s' % (start, j, ok))
