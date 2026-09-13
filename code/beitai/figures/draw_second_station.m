% Figure 12: paper/main.tex, paper/tables/q2_axis_compare.csv, paper/tables/q2_design_row.csv, code/q1q2/geom.py
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F12 second_station','Color','white');
subplot(1,2,1);hold on;plot([0 1500],[0 0],'k--');plot([0 800 800],[0 0 700],'-','Color',blue,'LineWidth',2);plot(800,700,'s','Color',orange,'MarkerFaceColor',orange,'MarkerSize',11);bt_label(50,50,'S1');bt_label(820,660,'交付点');axis equal;axis([-100 1650 -100 1050]);bt_ax('沿35°示向轴 r (m)','横向偏移 t (m)');title('第二站：S2=800u+700v','FontSize',26);subplot(1,2,2);hold on;ts=[690.9090909090909 700 795];plot([1 2 3],ts,'o','Color',blue,'MarkerSize',11);bt_ax('不同含义的参数','横向偏移 t (m)');set(gca,'XTick',1:3,'XTickLabel',{'网格点','交付点','角度带阈值'});xlim([.5 3.5]);ylim([665 825]);for k=1:3;text(k,ts(k)+13,sprintf('%.3f',ts(k)),'FontSize',24,'HorizontalAlignment','center');end;title('局部参数对照','FontSize',26);
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig12_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=12\n');fclose(fid);
