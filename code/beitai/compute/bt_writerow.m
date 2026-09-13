function bt_writerow(f,row)
for z=1:length(row);fprintf(f,'%.17g ',row(z));end
fprintf(f,'\n');
end
