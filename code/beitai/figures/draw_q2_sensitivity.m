% Figure 15: paper/tables/q2_sensitivity_sweep.csv, paper/tables/q2_sensitivity_observed.csv, code/q1q2/sensitivity.py, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F15 q2_sensitivity','Color','white');
subplot(1,2,1);hold on;plot(SW(:,1),SW(:,2),'o-','Color',blue,'LineWidth',2);plot(SW(:,1),SW(:,3),'s--','Color',orange,'LineWidth',2);plot([200 1000],[40 40],'k:','LineWidth',2);bt_ax('横向偏移 t (m)','后验直径 (m)');legend('中位数','P90','40 m阈值');subplot(1,2,2);plot(SW(:,1),SW(:,4),'o-','Color',blue,'LineWidth',2);hold on;plot(SW(:,1),SW(:,5),'s--','Color',orange,'LineWidth',2);ylim([0 1.1]);bt_ax('横向偏移 t (m)','可听比例');legend('1000 m','1500 m');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig15_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=15\n');fclose(fid);
