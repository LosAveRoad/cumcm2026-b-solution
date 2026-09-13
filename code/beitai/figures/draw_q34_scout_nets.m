% Figure 18: paper/tables/q3_scout_xy.csv, paper/tables/q4_scout_xy.csv, paper/q3-body.tex, code/src_jianmo_b_sim/geometry.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F18 q34_scout_nets','Color','white');
subplot(1,2,1);hold on;bt_circle([0 0],1800,gray,'-');plot(N3(:,1),N3(:,2),'o','Color',blue,'MarkerFaceColor',blue,'MarkerSize',8);axis equal;axis([-2100 2100 -2100 2100]);bt_ax('x (m)','y (m)');title('Q3：9点，无连线轨迹','FontSize',26);subplot(1,2,2);hold on;bt_circle([0 0],1800,gray,'-');plot(N4(:,1),N4(:,2),'s','Color',orange,'MarkerFaceColor',orange,'MarkerSize',7);axis equal;axis([-3000 3000 -3000 3000]);bt_ax('x (m)','y (m)');title('Q4：37点，s=850 m','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig18_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=18\n');fclose(fid);
