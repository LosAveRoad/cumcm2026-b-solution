# 北太天元画图入口

本目录保存本轮画图与来源冻结脚本。绘图脚本必须在北太天元图形界面中运行；`-nodesktop` 只适合数值命令，不能创建 `figure`。

已验证的入口：

```matlab
run('/Users/seint/Desktop/CUMCM2026B-Q3-reviewed/code/beitai/figures/draw_eda_time_components.m')
```

图形窗口的“导出”按钮是安装版提供的原生 PNG 导出路径。命令行 `-desktop -m` 不会执行图形函数，因此不能用它冒充 GUI 导出。
