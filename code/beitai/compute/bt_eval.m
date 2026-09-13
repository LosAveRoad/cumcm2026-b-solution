function row=bt_eval(r,t,err)
u=[cos(35*pi/180) sin(35*pi/180)]; s2=r*u+t*[-u(2) u(1)]; ds=[]; ps=[]; h1=0;h2=0;cl=0;
for i=0:13
 rad=5+1e-6+(1500-5-1e-6)*(i+0.5)/14;
 for j=0:4
  phi=(35-err+2*err*(j+0.5)/5)*pi/180; g=rad*[cos(phi) sin(phi)]; d2=norm(s2-g);
  h1=h1+(d2<=1000); h2=h2+(d2<=1500);
  if d2<=5 || d2>1500; continue; end
  th2=atan2(g(2)-s2(2),g(1)-s2(1))*180/pi;
  p=bt_posterior([0 0;s2],[35 th2],err); if size(p,1)<3;continue;end
  [D,R]=bt_metrics(p); ds=[ds;D]; v=-g;w=s2-g; ps=[ps;acos(min(1,max(-1,(v*w')/(norm(v)*norm(w)))))*180/pi];
  jung=(2*R<=D+1e-8); cl=cl+((jung && D<=40)||(~jung && R<=20));
 end
end
if isempty(ds);row=[r abs(t) sign(t) s2 0 h1/70 h2/70 NaN NaN NaN cl/70 NaN norm(s2)];return;end
ds=sort(ds); pos=1+(length(ds)-1)*.9; lo=floor(pos);hi=ceil(pos);p90=ds(lo)+(pos-lo)*(ds(hi)-ds(lo));
row=[r abs(t) sign(t) s2 length(ds) h1/70 h2/70 median(ds) p90 mean(ds) cl/70 median(ps) norm(s2)];
end
