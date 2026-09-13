"""Freeze source files and numeric tables only; never read figure pixels."""
from pathlib import Path
import json,hashlib,shutil,re,csv,datetime,platform,subprocess
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'review/beitai/20260913-native'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    RUN.mkdir(parents=True,exist_ok=False)
    for d in ['inputs','recomputed','figures','logs','qa','scripts']: (RUN/d).mkdir()
    shutil.copytree(ROOT/'paper',RUN/'paper')
    shutil.copytree(ROOT/'paper',RUN/'snapshot/paper')
    baseline=json.loads((ROOT/'review/beitai_baseline.json').read_text())
    files={str(p.relative_to(ROOT)):sha(p) for p in ROOT.rglob('*') if p.is_file() and '/.git/' not in str(p) and not p.is_relative_to(RUN)}
    (RUN/'snapshot_hashes.json').write_text(json.dumps(files,indent=2))
    def expand(p):
        text=re.sub(r'(?m)(?<!\\)%.*$','',p.read_text())
        return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(p.parent/(m[1] if m[1].endswith('.tex') else m[1]+'.tex')),text)
    refs=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',expand(ROOT/'paper/main.tex'))
    manifest=json.loads((ROOT/'review/beitai_figure_manifest.json').read_text())
    assert set('paper/'+f for f in refs)==set(f['file'] for f in manifest['figures'])
    manifest['phase']='frozen_execution'; manifest['active_count']=len(set(refs))
    (RUN/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    source_map={}
    for f in manifest['figures']:
        for name in f['source_files']:
            src=ROOT/name; dst=RUN/'inputs'/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
            source_map[name]={'sha256':sha(src),'bytes':src.stat().st_size}
    numeric={}
    for src in (ROOT/'paper/tables').glob('*.csv'):
        with src.open() as h:
            rows=list(csv.reader(h))
        cols=[]
        for i,k in enumerate(rows[0]):
            try: vals=[float(row[i]) for row in rows[1:]]
            except (ValueError,IndexError): continue
            cols.append(i)
        dst=RUN/'inputs'/(src.stem+'.txt')
        dst.write_text('\n'.join(' '.join(format(float(row[i]),'.17g') for i in cols) for row in rows[1:])+'\n')
        numeric[src.stem]={'columns':[rows[0][i] for i in cols],'source':str(src.relative_to(ROOT)),'source_sha256':sha(src),'numeric_sha256':sha(dst),'rows':len(rows)-1}
    (RUN/'inputs/source_map.json').write_text(json.dumps(source_map,ensure_ascii=False,indent=2))
    (RUN/'inputs/numeric_columns.json').write_text(json.dumps(numeric,ensure_ascii=False,indent=2))
    env={'date':datetime.datetime.now().isoformat(),'platform':platform.platform(),'architecture':platform.machine(),'app':'/Applications/Baltamatica.app','version':'2025','baseline_differences':[x['path'] for x in baseline['files'] if files.get(x['path'])!=x['sha256']],'active_count':len(set(refs))}
    (RUN/'environment.json').write_text(json.dumps(env,indent=2))
    print(json.dumps(env)); print(json.dumps(numeric,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
