% 图30（当前论文源文件名 q4_ring_ablation）
% 北太天元原生脚本：按题设公式重算外环边界中缝距离。
clear;
n = 6:16;
d = sqrt(2000^2 + 1800^2 - 2*2000*1800*cos(pi./n));

blue = [0.141 0.388 0.627];
red = [0.714 0.271 0.271];
black = [0.08 0.08 0.08];

f = figure('Name','图30 外环等分数灵敏度','Color','white');
set(f,'Position',[80 80 1200 720]);
hold on;
plot(n,d,'o-','Color',blue,'LineWidth',5.5,'MarkerSize',20,'MarkerFaceColor',blue);
plot([6 16],[1000 1000],'--','Color',red,'LineWidth',4.0);
plot([12 12],[300 1140],':','Color',black,'LineWidth',3.0);
plot(6,d(1),'x','Color',red,'LineWidth',5.5,'MarkerSize',36);
plot(12,d(7),'p','Color',black,'LineWidth',3.0,'MarkerSize',36,'MarkerFaceColor',black);

xlabel('外环等分数 n','FontSize',42);
ylabel('边界中缝距离 d (m)','FontSize',42);
set(gca,'FontSize',38,'LineWidth',1.0,'XTick',n,'XLim',[5.5 16.5],'YLim',[300 1150],'YTick',300:100:1100);
grid on;
legend('d(n, 2000)','1000 m','Location','northeast','FontSize',34);
text(6.35,1042,'n = 6','Color',red,'FontSize',38);
text(12.18,470,'n = 12','Color',black,'FontSize',38);
box on;

fid = fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig30_native.txt','w');
fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=30\n');
fprintf(fid,'formula=d(n)=sqrt(2000^2+1800^2-2*2000*1800*cos(pi/n))\n');
fprintf(fid,'n=6 d=%.15f\n',d(1));
fprintf(fid,'n=12 d=%.15f\n',d(7));
fclose(fid);
