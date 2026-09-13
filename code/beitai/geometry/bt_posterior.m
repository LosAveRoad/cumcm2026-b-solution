function p=bt_posterior(s,b,err)
p=[-1e6 -1e6;1e6 -1e6;1e6 1e6;-1e6 1e6]; planes=[];
for i=1:2
 a=(b(i)+err)*pi/180; z=(b(i)-err)*pi/180;
 n=[sin(a) -cos(a);-sin(z) cos(z)]; planes=[planes;n n*s(i,:)'];
end
p=bt_clip(p,planes);
for disk=1:3
 if disk==1; cen=[0 0]; rad=1800; sides=96; else; cen=s(disk-1,:); rad=1500; sides=64; end
 a=(0:sides-1)'*2*pi/sides; q=[rad*cos(a)+cen(1) rad*sin(a)+cen(2)]; planes=[];
 for i=1:sides
  ed=q(mod(i,sides)+1,:)-q(i,:); n=[-ed(2) ed(1)]/norm(ed); planes=[planes;n n*q(i,:)'];
 end
 p=bt_clip(p,planes);
end
end
