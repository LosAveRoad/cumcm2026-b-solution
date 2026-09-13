% Figure 24: paper/main.tex, paper/tables/protocol_constants.csv, code/src_jianmo_b_sim/geometry.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F24 q4_optical_grid','Color','white');
hold on;for x=-100:25:100;for y=-100:25:100;d=sqrt(max(abs(x)-12.5,0)^2+max(abs(y)-12.5,0)^2);if d<=80;bt_poly([x-12.5 y-12.5;x+12.5 y-12.5;x+12.5 y+12.5;x-12.5 y+12.5],[.82 .84 .86]);plot(x,y,'.','Color',blue,'MarkerSize',12);end;end;end;bt_circle([0 0],80,gray,'-');bt_circle([0 0],20,orange,'--');bt_poly([-12.5 -12.5;12.5 -12.5;12.5 12.5;-12.5 12.5],blue);axis equal;axis([-113 113 -113 113]);bt_ax('x (m)','y (m)');title('完整相交单元：25/√2<20 m','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig24_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=24\n');fclose(fid);
