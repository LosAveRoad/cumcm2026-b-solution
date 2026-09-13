function out=bt_clip(poly,planes)
out=poly;
for k=1:size(planes,1)
 if size(out,1)<3; out=[]; return; end
 n=planes(k,1:2); c=planes(k,3); nxt=[];
 for i=1:size(out,1)
  a=out(i,:); b=out(mod(i,size(out,1))+1,:); da=a*n'-c; db=b*n'-c;
  if da>=-1e-12 && db>=-1e-12
   nxt=[nxt;b];
  elseif (da>=-1e-12) ~= (db>=-1e-12)
   if abs(da-db)<1e-18; hit=b; else; t=min(1,max(0,da/(da-db))); hit=a+t*(b-a); end
   nxt=[nxt;hit];
   if db>=-1e-12; nxt=[nxt;b]; end
  end
 end
 out=[];
 for i=1:size(nxt,1)
  if isempty(out) || norm(nxt(i,:)-out(end,:))>1e-9; out=[out;nxt(i,:)]; end
 end
 if size(out,1)>=2 && norm(out(1,:)-out(end,:))<=1e-9; out(end,:)=[]; end
end
end
