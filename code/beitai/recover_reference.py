"""Offline recovery from source code; no simulator imports or writes to old outputs."""
from pathlib import Path
import sys,json,csv,math
import numpy as np
R=Path(__file__).resolve().parents[2]; W=R/'review/beitai/20260913-native'
sys.path.insert(0,str(R/'code/q1q2'))
import geom
rng=np.random.default_rng(2026); inputs=[]; values=[]
for k in range(400):
 s1=tuple(rng.uniform(-400,400,2));s2=tuple(rng.uniform(-400,400,2))
 if geom.hypot(s1,s2)<80:s2=(s1[0]+400,s1[1]+50)
 g=tuple(rng.uniform(-900,900,2))
 if geom.hypot(g)>1600:g=tuple(x*.5 for x in g)
 e1,e2=rng.uniform(-1,1,2);b1=geom.measured_bearing(geom.bearing_deg(g,s1),e1);b2=geom.measured_bearing(geom.bearing_deg(g,s2),e2)
 p=geom.intersect_wedges([s1,s2],[b1,b2],clip_arena=True,range_balls=[1500,1500])
 inputs.append([k,*s1,*s2,*g,e1,e2,b1,b2])
 if len(p)<3 or geom.polygon_unbounded(p):continue
 d=geom.diametral_circle_covers_any(p);j=geom.sec_covers_via_jung(p)
 values.append([k,d['diameter'],int(d['covers']),j['sec_radius'],len(p),abs(geom.polygon_area(p))])
saved=np.loadtxt(W/'inputs/q1_mc_sample.txt'); v=np.array(values)
report={'numpy_version':np.__version__,'seed':2026,'rows':len(v),'max_absolute_errors':np.max(np.abs(v-saved[:,:6]),axis=0).tolist(),'verified':bool(np.allclose(v,saved[:,:6],rtol=1e-8,atol=1e-6)),'columns':['k','diameter','covers','sec_radius','n_vertices','area']}
np.savetxt(W/'inputs/q1_original_inputs.txt',inputs,fmt='%.17g')
np.savetxt(W/'inputs/q1_reference_values.txt',v,fmt='%.17g')
(W/'qa/q1_input_recovery.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
# Complete original sample-generation chain for figure19 is absent; do not synthesize.
(W/'qa/figure19_recovery.txt').write_text('Checked code/shared/experiment.py, paper/tables/q34_observed.csv and scout tables; no original plot script or full left/right source, heading and translated-point records. Aggregate samples cannot identify plotted point sets. SKIPPED_MISSING_SAMPLE_DATA; original PNG retained.\n')
