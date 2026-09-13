% Figure 6: paper/main.tex, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F06 halfplane','Color','white');
h=15*pi/180;u=[cos(h) sin(h)];hold on;fill([0 1000*u(1) 1000*u(1)],[0 -1000*u(2) 1000*u(2)],pale,'EdgeColor',blue);plot([0 1100],[0 0],'k--','LineWidth',2);quiver(600*u(1),600*u(2),120*sin(h),-120*cos(h),0,'Color',orange,'LineWidth',2);quiver(600*u(1),-600*u(2),120*sin(h),120*cos(h),0,'Color',orange,'LineWidth',2);bt_label(70,65,'前向轴');bt_label(640,210,'n+');bt_label(640,-230,'n-');axis equal;axis([-80 1200 -400 400]);bt_ax('示向轴方向 (示意)','法向方向 (示意)');title('半角放大为15°；模型真实半角1°','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig06_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=6\n');fclose(fid);
