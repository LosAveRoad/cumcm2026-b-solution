function bt_circle(c,r,col,ls)
tt=linspace(0,2*pi,361);plot(c(1)+r*cos(tt),c(2)+r*sin(tt),'Color',col,'LineStyle',ls,'LineWidth',1.8);
end
