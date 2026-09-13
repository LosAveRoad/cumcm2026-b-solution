% Run in Baltamatica GUI. Numeric-only CLI has no figure function.
probe_root='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native';
fid=fopen([probe_root '/logs/probe.txt'],'w');
fprintf(fid,'numeric %g\n',200/5);
try
 T=readmatrix([probe_root '/inputs/paper/tables/q1_example_vertices.csv']);
 fprintf(fid,'readmatrix_with_header rows=%d cols=%d\n',size(T,1),size(T,2));
catch err
 fprintf(fid,'readmatrix_with_header failed\n');
end
A=load([probe_root '/inputs/q1_example_vertices.txt']);
fprintf(fid,'numeric_text rows=%d\n',size(A,1));
f=figure('Name','BEITAI PROBE','Color','white');
subplot(2,2,1); t=linspace(0,2*pi,361); plot(cos(t),sin(t)); axis equal; title('中文圆 ρ τ'); xlabel('x (m)');
subplot(2,2,2); semilogx([5 20 1000 1500 1800],[1 2 3 4 5],'o-'); title('对数坐标');
subplot(2,2,3); bar([1 5 3 2 40]); title('动作时间 (s)');
subplot(2,2,4); imagesc([1 2 3;4 5 6]); colorbar; title('探针矩阵');
fprintf(fid,'graphics_created\n');
try
 saveas(f,[probe_root '/qa/probe.png']); fprintf(fid,'saveas_png passed\n');
catch err
 fprintf(fid,'saveas_png failed\n');
end
try
 print(f,[probe_root '/qa/probe.pdf'],'-dpdf'); fprintf(fid,'print_pdf passed\n');
catch err
 fprintf(fid,'print_pdf failed\n');
end
fclose(fid);
