"""Build the delivery archive and verify the Q3-only code scope."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('original_zip')
args = p.parse_args()
original_path = Path(args.original_zip)
old = zipfile.ZipFile(original_path)
review = root/'review'
review.mkdir(exist_ok=True)

protected = [n for n in old.namelist() if n.startswith('code/') and not n.startswith('code/q3/')]
assert all((root/n).read_bytes() == old.read(n) for n in protected), 'Non-Q3 code changed'
assert (root/'code/q3/searcher_legacy.py').read_bytes() == old.read('code/q3/searcher.py')
log = (root/'paper/main.log').read_text(encoding='utf-8', errors='replace')
assert 'Output written on main.pdf (50 pages)' in log
for bad in ('Overfull', 'Missing character:', 'There were undefined references', 'Label(s) may have changed'):
    assert bad not in log, bad

raw = (root/'code/q3/test-results.txt').read_bytes()
tests = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8')
assert 'Ran 13 tests' in tests and 'OK' in tests
(review/'unit_tests.txt').write_text(tests, encoding='utf-8')
data = json.loads((root/'code/q3/offline_results.json').read_text(encoding='utf-8'))
assert data['n_scenes'] == data['n_full_clear'] == 48
assert data['max_actions'] <= 294

def deliverable(path):
    rel = path.relative_to(root)
    if not path.is_file() or '__pycache__' in rel.parts:
        return False
    if rel.parts[0] == 'review':
        return path.suffix in ('.json', '.diff') or path.name == 'unit_tests.txt'
    if path.name in ('revise_paper.py', 'main-review-text.txt', 'test-results.txt'):
        return False
    if path.name.startswith(('q3-qa-', 'build-')):
        return False
    return path.suffix not in ('.aux', '.log', '.out', '.toc', '.pyc', '.synctex')

changes = []
diff = []
for path in sorted(root.rglob('*')):
    if not deliverable(path) or path.relative_to(root).parts[0] == 'review':
        continue
    name = path.relative_to(root).as_posix()
    before = old.read(name) if name in old.namelist() else b''
    after = path.read_bytes()
    if before == after:
        continue
    changes.append({'path': name, 'status': 'modified' if name in old.namelist() else 'added',
                    'sha256': hashlib.sha256(after).hexdigest()})
    if path.suffix in ('.py', '.tex', '.md', '.json', '.txt') and name != 'code/q3/searcher_legacy.py':
        try:
            diff.extend(difflib.unified_diff(before.decode('utf-8').splitlines(True),
                         after.decode('utf-8').splitlines(True), 'original/'+name, 'revised/'+name))
        except UnicodeError:
            pass
(review/'Q3_changes.diff').write_text(''.join(diff), encoding='utf-8')
summary = {
    'date': '2026-09-13', 'scope': 'Q3 and related paper statements only',
    'original_zip_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
    'pdf_sha256': hashlib.sha256((root/'paper/main.pdf').read_bytes()).hexdigest(),
    'paper_pages': 50, 'xelatex_exit_code': 0,
    'unresolved_references': 0, 'overfull_boxes': 0, 'missing_glyphs': 0,
    'q3_physical_pdf_pages_reviewed': list(range(25, 34)),
    'related_physical_pdf_pages_reviewed': [3,5,7,8,10,47,48,50],
    'unit_tests_passed': 13, 'offline_scenes': 48, 'offline_full_clear': 48,
    'offline_action_range': [data['min_actions'], data['max_actions']],
    'theoretical_action_bound': 294,
    'official_simulator_runs_by_this_revision': 0,
    'non_q3_code_files_verified_unchanged': protected,
    'legacy_searcher_verified_byte_identical': True,
    'changed_or_added_files': changes,
    'limitations': ['No revised official rehearsal or formal logs',
                    'No global time-optimality claim', 'Real-time/network interruptions remain possible']
}
(review/'validation_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
target = root.parent/(root.name+'.zip')
with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as out:
    for path in sorted(root.rglob('*')):
        if deliverable(path):
            out.write(path, path.relative_to(root).as_posix())
with zipfile.ZipFile(target) as out:
    assert out.testzip() is None
    assert out.read('paper/main.pdf') == (root/'paper/main.pdf').read_bytes()
    assert 'code/q3/searcher.py' in out.namelist()
print(json.dumps({'archive': str(target), 'bytes': target.stat().st_size,
                  'protected_code_files_unchanged': len(protected),
                  'modified_or_added_files': len(changes), 'pdf_pages': 50}, indent=2))
