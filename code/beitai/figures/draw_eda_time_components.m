% Figure 4: paper/tables/protocol_constants.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F04 eda_time_components','Color','white');
y=[1 5 3 2 200/5];bar(1:5,y,0.6,'FaceColor',blue);bt_ax('动作','时间 (s)');set(gca,'XTick',1:5,'XTickLabel',{'换台','检测','光学','激光','行进200 m'});ylim([0 47]);for k=1:5;text(k,y(k)+1.6,num2str(y(k)),'HorizontalAlignment','center','FontSize',26);end;
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig04_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=4\n');fclose(fid);
