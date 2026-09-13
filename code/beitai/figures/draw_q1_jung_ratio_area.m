% Figure 11: paper/tables/q1_mc_sample.csv, paper/tables/q1_mc_meta.csv, code/q1q2/experiment.py, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F11 q1_jung_ratio_area','Color','white');
subplot(1,2,1);res=MC(:,3)-MC(:,1)/2;plot(MC(:,1),res,'o','Color',blue,'MarkerSize',5);bt_ax('直径 D (m)','Rsec-D/2 (m)');title('包围圆残差','FontSize',26);subplot(1,2,2);plot(MC(:,1),MC(:,4),'o','Color',orange,'MarkerSize',5);bt_ax('直径 D (m)','后验面积 (m²)');title('全部400行保存结果','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig11_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=11\n');fclose(fid);
