% Figure 2: paper/tables/protocol_constants.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F02 eda_radii','Color','white');
subplot(1,2,1);hold on;bt_circle([0 0],1800,gray,'-');bt_circle([0 0],1500,blue,'--');bt_circle([0 0],1000,orange,'-.');axis equal;axis([-2000 2000 -2000 2000]);bt_ax('x (m)','y (m)');title('场地与接收范围','FontSize',26);legend('场地1800','接收上界1500','接收下界1000','Location','southoutside');subplot(1,2,2);hold on;bt_circle([0 0],20,blue,'-');bt_circle([0 0],5,orange,'--');axis equal;axis([-24 24 -24 24]);bt_ax('x (m)','y (m)');title('局部放大：近场与清除','FontSize',26);legend('清除20 m','近场5 m','Location','southoutside');
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig02_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=2\n');fclose(fid);
