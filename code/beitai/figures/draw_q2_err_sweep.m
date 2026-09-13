% Figure 16: paper/tables/q2_sensitivity_observed.csv, code/q1q2/sensitivity.py, code/q1q2/geom.py, paper/main.tex
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F16 q2_err_sweep','Color','white');
subplot(1,2,1);plot(ER(:,1),ER(:,2),'o-','Color',blue,'LineWidth',2);hold on;plot([.5 1.5],[40 40],'--','Color',red,'LineWidth',2);bt_ax('楔半角 (°)','中位直径 (m)');legend('中位直径','40 m阈值');subplot(1,2,2);plot(ER(:,1),ER(:,3),'s--','Color',orange,'LineWidth',2,'MarkerSize',11);ylim([-.1 1.2]);set(gca,'YTick',[0 1]);bt_ax('楔半角 (°)','中位直径≤40 m 指示');title('r=1100 m，t=500 m','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig16_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=16\n');fclose(fid);
