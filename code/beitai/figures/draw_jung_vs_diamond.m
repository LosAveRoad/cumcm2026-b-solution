% Figure 8: paper/main.tex, paper/tables/q1_example_vertices.csv, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F08 jung_vs_diamond','Color','white');
subplot(1,2,1);tri=[-40 0;40 0;0 40*sqrt(3)];hold on;bt_poly(tri,blue);bt_circle([0 0],40,red,'--');bt_circle([0 40/sqrt(3)],80/sqrt(3),orange,'-.');axis equal;axis([-55 55 -47 87]);bt_ax('x (m)','y (m)');title('等边反例：D=80 m','FontSize',26);bt_label(-45,-35,'R=D/√3>D/2');subplot(1,2,2);hold on;bt_poly(P,blue);plot(P(:,1),P(:,2),'o','Color',blue,'MarkerFaceColor',blue);bt_circle([500 (P(1,2)+P(3,2))/2],(P(1,2)-P(3,2))/2,orange,'--');plot(500,500,'kx','MarkerSize',10);axis equal;axis([477 523 477 523]);bt_ax('x (m)','y (m)');title('正交四边形：R=D/2','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig08_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=8\n');fclose(fid);
