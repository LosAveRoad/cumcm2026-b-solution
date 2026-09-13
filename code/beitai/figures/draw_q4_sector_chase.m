% Figure 23: paper/main.tex, code/src_jianmo_b_sim/geometry.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F23 q4_sector_chase','Color','white');
for panel=1:2;subplot(1,2,panel);hold on;fill([-100 300 300 -100],[-150 -150 600 600],pale,'EdgeColor','none');plot([0 300],[0 0],'ks','MarkerSize',10);quiver(300,0,-140,0,0,'Color',red,'LineWidth',2);bt_label(-70,-90,'S1');bt_label(280,-90,'G');plot([300 300],[-150 600],'k--');if panel==1;plot([0 500],[0 0],'-o','Color',red,'LineWidth',2);bt_label(370,100,'越过源');else;plot([0 60],[0 500],'-o','Color',blue,'LineWidth',2);bt_label(70,510,'S2=(60,500)');end;axis equal;axis([-140 650 -160 680]);bt_ax('沿示向轴 (m)','横向 (m)');end;
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig23_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=23\n');fclose(fid);
