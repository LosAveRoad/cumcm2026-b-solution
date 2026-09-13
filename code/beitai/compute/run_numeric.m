addpath('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai/geometry');
addpath('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai/compute');
W='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native';
fid=fopen([W '/logs/numeric.txt'],'w');
p=bt_posterior([0 0;1000 0],[45 135],1); [D,R,C,cov,A]=bt_metrics(p); fprintf(fid,'orthogonal D=%.17g R=%.17g area=%.17g\n',D,R,A);
f=fopen([W '/recomputed/q1_polygon.txt'],'w');for j=1:size(p,1);bt_writerow(f,p(j,:));end;fclose(f);
f=fopen([W '/recomputed/q1_mc.txt'],'w'); x=load([W '/inputs/q1_original_inputs.txt']);
for i=1:size(x,1)
 s=[x(i,2:3);x(i,4:5)];p=bt_posterior(s,x(i,10:11),1);[D,R,C,cov,A]=bt_metrics(p);
 fprintf(f,'%.17g %.17g %.17g %.17g %.17g %.17g\n',x(i,1),D,cov,R,size(p,1),A);
end
fclose(f);fprintf(fid,'q1_400_complete\n');
f=fopen([W '/recomputed/q2_grid.txt'],'w');
for r=linspace(400,1400,11)
 for t=linspace(150,1000,12)
  for sg=[1 -1]
   row=bt_eval(r,sg*t,1);bt_writerow(f,row);
  end
 end
 fprintf(fid,'q2_r %.17g complete\n',r);
end
fclose(f);
f=fopen([W '/recomputed/q2_offset.txt'],'w');for t=[200 350 500 650 800 1000];row=bt_eval(1100,t,1);bt_writerow(f,row);end;fclose(f);
f=fopen([W '/recomputed/q2_error.txt'],'w');for e=[.5 1 1.5];row=bt_eval(1100,500,e);bt_writerow(f,[e row]);end;fclose(f);
fprintf(fid,'ALL_NUMERIC_DONE\n');fclose(fid);
