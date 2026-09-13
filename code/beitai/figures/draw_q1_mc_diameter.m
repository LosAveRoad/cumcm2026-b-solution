% Figure 10: paper/tables/q1_mc_sample.csv, paper/tables/q1_mc_meta.csv, code/q1q2/experiment.py, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F10 q1_mc_diameter','Color','white');
edges=linspace(0,max(MC(:,1)),17);counts=zeros(16,2);for k=1:16;inside=(MC(:,1)>=edges(k) & MC(:,1)<edges(k+1));if k==16;inside=(MC(:,1)>=edges(k) & MC(:,1)<=edges(k+1));end;counts(k,1)=sum(inside & MC(:,2)==1);counts(k,2)=sum(inside & MC(:,2)==0);end;bar((edges(1:16)+edges(2:17))/2,counts,'stacked');bt_ax('后验直径 (m)','样本数');legend('覆盖：382','未覆盖：18');title('同一组400行；统一分箱','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig10_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=10\n');fclose(fid);
