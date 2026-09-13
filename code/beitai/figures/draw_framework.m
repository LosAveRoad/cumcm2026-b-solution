% Figure 1: paper/main.tex, paper/tables/protocol_constants.csv, paper/tables/q1_example_vertices.csv, paper/tables/q2_axis_compare.csv, paper/tables/q3_scout_xy.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F01 framework','Color','white');
subplot(2,2,1);hold on;bt_poly(P,blue);axis equal;bt_ax('x (m)','y (m)');title('Q1：楔交与覆盖圆','FontSize',26);subplot(2,2,2);plot([0 800 800],[0 0 700],'-os','Color',blue);axis equal;bt_ax('r (m)','t (m)');title('Q2：交付点 (800,700)','FontSize',26);subplot(2,2,3);hold on;bt_circle([0 0],1800,gray,'-');plot(N3(:,1),N3(:,2),'o','Color',blue);axis equal;bt_ax('x (m)','y (m)');title('Q3：九点全向发现','FontSize',26);subplot(2,2,4);hold on;bt_circle([0 0],1800,gray,'-');plot(N4(:,1),N4(:,2),'s','Color',orange);axis equal;bt_ax('x (m)','y (m)');title('Q4：定向三角格网','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig01_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=1\n');fclose(fid);
