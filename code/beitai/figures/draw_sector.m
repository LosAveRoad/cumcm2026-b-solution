f=figure('Name','Fig21 sector','Color','white'); t=linspace(-pi/2,pi/2,181); fill([0 1000*cos(t)],[0 1000*sin(t)],[0.8 0.9 1]); axis equal; xlabel('x (m)'); ylabel('y (m)'); title('定向源有效覆盖闭扇形');
