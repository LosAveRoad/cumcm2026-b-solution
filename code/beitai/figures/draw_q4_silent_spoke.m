% Figure 22: paper/main.tex, paper/tables/q4_lattice.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F22 q4_silent_spoke','Color','white');
hold on;fill([200 1250 1250 200],[-570 -570 570 570],pale,'EdgeColor','none');bt_circle([700 0],850/sqrt(3),blue,'--');plot([-100 1300],[0 0],'k-');plot([200 700 850],[0 0 0],'o','Color',orange,'MarkerFaceColor',orange,'MarkerSize',10);plot([200 700],[-150 -150],'-','Color',red,'LineWidth',2);bt_label(340,-260,'a=500 m');bt_label(110,60,'G=200');bt_label(570,170,'q=700');bt_label(850,60,'p=850');bt_label(380,590,'|q-p|=150 m < ρ=490.748 m');axis equal;axis([-150 1400 -650 750]);bt_ax('轴向 x (m)','横向 y (m)');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig22_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=22\n');fclose(fid);
