% Figure 20: paper/main.tex, paper/tables/q4_lattice.csv, code/src_jianmo_b_sim/geometry.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F20 directional_listen','Color','white');
hold on;fill([200 1450 1450 200],[-1100 -1100 1100 1100],pale,'EdgeColor','none');bt_circle([700 0],850/sqrt(3),blue,'--');plot([200 700 850],[0 0 0],'o','Color',orange,'MarkerFaceColor',orange,'MarkerSize',11);quiver(200,0,250,0,0,'Color',red,'LineWidth',2);plot([-300 -650],[500 -400],'o','Color',gray,'MarkerSize',9);bt_label(150,-160,'G');bt_label(630,-160,'q');bt_label(840,130,'p');bt_label(330,100,'H →');bt_label(400,610,'覆盖盘半径 ρ=850/√3');axis equal;axis([-800 1500 -1150 1150]);bt_ax('x (m)','y (m)');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig20_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=20\n');fclose(fid);
