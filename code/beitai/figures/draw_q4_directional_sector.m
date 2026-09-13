% Figure 21: paper/main.tex, paper/tables/protocol_constants.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F21 q4_directional_sector','Color','white');
hold on;t=linspace(-pi/2,pi/2,181);fill([0 1000*cos(t)],[0 1000*sin(t)],pale,'EdgeColor',blue);quiver(0,0,650,0,0,'Color',red,'LineWidth',2);plot([0 0],[-1000 1000],'Color',blue,'LineWidth',2);bt_label(60,110,'H：前向');bt_label(-120,-140,'G');bt_label(120,800,'闭180°扇形');axis equal;axis([-1150 1150 -1150 1150]);bt_ax('相对源 x (m)','相对源 y (m)');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig21_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=21\n');fclose(fid);
