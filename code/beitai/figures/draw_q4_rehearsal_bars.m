% Figure 26: paper/tables/q4_rehearsal.csv, paper/tables/q4_policy_compare.csv, paper/main.tex
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F26 q4_rehearsal_bars','Color','white');
A=REH;subplot(1,2,1);bar(1:3,A(:,1:2));bt_ax('历史演练场次','源数');set(gca,'XTick',1:3);ylim([0 15]);legend('真数','已清','Location','northwest');for k=1:3;bt_label(k-.25,13,sprintf('%d/%d',A(k,2),A(k,1)));end;subplot(1,2,2);avg=A(:,3)./A(:,2);bar(1:3,avg,.6,'FaceColor',blue);bt_ax('历史演练场次','时间 (s/已清源)');set(gca,'XTick',1:3);ylim([0 max(avg)*1.25]);for k=1:3;text(k,avg(k)+max(avg)*.05,sprintf('%.1f',avg(k)),'HorizontalAlignment','center','FontSize',24);end;
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig26_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=26\n');fclose(fid);
