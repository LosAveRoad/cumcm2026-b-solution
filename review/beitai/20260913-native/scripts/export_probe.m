% Native desktop CLI probe. No paper files written.
W='/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/review/beitai/20260913-native';
fid=fopen([W '/logs/desktop_export_probe.txt'],'w');
try
 f=figure('Name','Native export probe');plot([1 2],[3 4]);fprintf(fid,'figure PASS\n');
catch err
 fprintf(fid,'figure FAIL\n'); disp(err);
end
try
 saveas(f,[W '/qa/native_probe.png']);fprintf(fid,'saveas PASS\n');
catch err
 fprintf(fid,'saveas FAIL\n');disp(err);
end
try
 print(f,[W '/qa/native_probe.pdf'],'-dpdf');fprintf(fid,'print PASS\n');
catch err
 fprintf(fid,'print FAIL\n');disp(err);
end
fclose(fid);
