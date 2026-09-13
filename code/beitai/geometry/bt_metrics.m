function [d,R,cen,covers,area,dc]=bt_metrics(p)
n=size(p,1); d=-1; dc=[0 0];
for i=1:n
 for j=i+1:n
  v=norm(p(i,:)-p(j,:)); if v>d; d=v; dc=(p(i,:)+p(j,:))/2; end
 end
end
covers=0; R=inf; cen=dc;
for i=1:n
 for j=i+1:n
  c=(p(i,:)+p(j,:))/2; r=norm(p(i,:)-p(j,:))/2; ds=sqrt(sum((p-c).^2,2));
  if 2*r>=d-1e-8 && all(ds<=d/2+1e-8); covers=1; dc=c; end
  if all(ds<=r+1e-8) && r<R-1e-15; R=r;cen=c; end
 end
end
for i=1:n
 for j=i+1:n
  for k=j+1:n
   a=p(i,:);b=p(j,:);c=p(k,:); detv=2*(a(1)*(b(2)-c(2))+b(1)*(c(2)-a(2))+c(1)*(a(2)-b(2)));
   if abs(detv)<1e-18; continue; end
   aa=sum(a.^2);bb=sum(b.^2);cc=sum(c.^2);
   v=[aa*(b(2)-c(2))+bb*(c(2)-a(2))+cc*(a(2)-b(2)),aa*(c(1)-b(1))+bb*(a(1)-c(1))+cc*(b(1)-a(1))]/detv;
   r=norm(v-a);if all(sqrt(sum((p-v).^2,2))<=r+1e-8) && r<R-1e-15; R=r;cen=v; end
  end
 end
end
if isinf(R);R=d/2;cen=dc;end
q=p([2:n 1],:);area=abs(sum(p(:,1).*q(:,2)-p(:,2).*q(:,1))/2);
end
