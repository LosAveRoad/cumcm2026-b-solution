% Figure 3: paper/tables/protocol_constants.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F03 eda_constraint_line','Color','white');
x=[5 20 1000 1500 1800];semilogx(x,[1 2 3 4 5],'o-','Color',blue,'LineWidth',2,'MarkerSize',9);bt_ax('半径 (m，对数坐标)','尺度项');set(gca,'YTick',1:5,'YTickLabel',{'近场5','清除20','接收下界1000','接收上界1500','场地1800'});xlim([3 2600]);ylim([.5 5.5]);grid on;
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig03_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=3\n');fclose(fid);
