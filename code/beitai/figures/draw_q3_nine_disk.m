% Figure 17: paper/q3-body.tex, paper/tables/q3_scout_xy.csv, code/q3/detection_proof.json
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F17 q3_nine_disk','Color','white');
hold on;bt_circle([0 0],1800,gray,'-');bt_circle([0 0],1000,blue,'--');plot(N3(:,1),N3(:,2),'o','Color',blue,'MarkerFaceColor',blue,'MarkerSize',9);tau=1000/(2*cos(pi/8));V=tau*[cos(pi/8) sin(pi/8)];PP=1800*[cos(pi/8) sin(pi/8)];plot([0 V(1)],[0 V(2)],'-.','Color',orange,'LineWidth',2);plot([1000 PP(1)],[0 PP(2)],'-','Color',red,'LineWidth',2);plot([1000/sqrt(2) PP(1)],[1000/sqrt(2) PP(2)],'-','Color',red,'LineWidth',2);plot([V(1) PP(1)],[V(2) PP(2)],'ks','MarkerSize',9);bt_label(V(1)-80,V(2)+120,'V');bt_label(PP(1)+80,PP(2),'P');bt_label(800,300,'ρ=956.051 m');bt_label(-1550,-1450,'τ=541.196 m：证明分段半径');axis equal;axis([-2100 2200 -2050 2050]);bt_ax('x (m)','y (m)');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig17_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=17\n');fclose(fid);
