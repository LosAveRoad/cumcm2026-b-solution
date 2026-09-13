% Figure 5: paper/tables/protocol_constants.csv
% Native GUI only; saved data/formula drawing. No upstream experiment.
base='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai'; addpath(base);run([base '/plot_data.m']);
blue=[.141 .388 .627];orange=[.851 .510 .169];gray=[.451 .482 .525];red=[.714 .271 .271];pale=[.90 .94 .98];
f=figure('Name','F05 eda_protocol_ranges','Color','white');
hold on;plot([1000 1500],[3 3],'-','Color',blue,'LineWidth',7);plot([5 20 1800],[1 2 4],'s','Color',orange,'MarkerSize',12,'MarkerFaceColor',orange);set(gca,'XScale','log');bt_ax('长度 (m，对数坐标)','协议量');set(gca,'YTick',1:4,'YTickLabel',{'近场 5','清除 20','接收 [1000,1500]','场地 1800'});xlim([3 2600]);ylim([.5 4.5]);grid on;
fid=fopen('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native/logs/fig05_native.txt','w');fprintf(fid,'DRAW_SCRIPT_COMPLETE figure=5\n');fclose(fid);
