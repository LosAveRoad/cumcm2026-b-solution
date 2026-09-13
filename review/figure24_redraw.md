# 图24重绘与本机编译记录

日期：2026-09-13。

## 图形修订

- 图24对应 `paper/figures/directional_listen`，保留 PNG，并新增矢量 PDF 供正文引用。
- 完整显示场地及21个检测网点，右图单独放大源附近的接收盘。
- 明确示例条件：`G=(1200,0) m`、朝向正东、`R_eff=1000 m`。
- 区分可听、距离盘内但位于背瓣、距离超限三种网点；外环用方点、内网用圆点。
- 以 `paper/tables/q4_visit_xy.csv` 为坐标来源，并与正文的9点内网和12点外环公式逐项核对。
- 几何核验结果：21个网点中，可听1个、距离盘内背瓣3个、距离超限17个；可听点为 `(2000,0)`，距源800 m。

绘图代码：`code/figures/redraw_directional_listen.py`。依赖 Python 3、NumPy、Matplotlib；本次实际采用 Matplotlib 3.11.2。

## 字体和编译环境

按用户要求将缺失字体安装到 `/Library/Fonts`，供全机应用使用：

| 文件 | 字体族 | 版本 |
| --- | --- | --- |
| CambriaMath.ttf | Cambria Math | 6.99;O365 |
| FangSong.ttf | FangSong | 5.02;O365 |
| SimSun.ttf | SimSun | 5.21;O365 |
| SimHei.ttf | SimHei | 5.04;O365 |
| KaiTi.ttf | KaiTi | 5.02;O365 |

字体来源为 [Microsoft 365 Fonts 字体归档](https://github.com/pjobson/Microsoft-365-Fonts)，不是微软官方下载入口；微软字体服务本次未返回有效字体文件。核验字体内部名称、版本、字符映射与字形数量，Cambria Math 包含 MATH 表。Cambria Math、FangSong、SimHei、KaiTi 的文件大小与本机 Office 字体目录记录一致；SimSun 为上述归档版本。

将已有的 cprotect、placeins、cleveref、tocloft、appendix、bigfoot 依赖补入用户级 TeX 树 `/Users/seint/Library/texmf/tex/latex`，无需临时 TEXINPUTS 才能编译。

在 `paper/main.tex` 明确指定原 PDF 使用的中文字体族，避免由操作系统自动选择另一套中文字体。数学字体继续使用 Cambria Math。

## 验证

在 `paper` 目录使用 XeLaTeX 完整编译，重复编译至交叉引用稳定：

```sh
xelatex -interaction=nonstopmode -halt-on-error main.tex
xelatex -interaction=nonstopmode -halt-on-error main.tex
```

本次构建目录为 `/tmp/cumcm-fig24-build`，最终完整构建记录为 `pass4.txt`。成稿共59页；图号仍为24，位于正文第42页、PDF第44页。核对图24及相邻两页渲染，图形与图注完整，无重叠或裁切。最终日志没有缺失字形、字体替代、未定义引用或要求再次编译的警告。

全文仍存在其他位置的排版警告，包括正式测试表的横向溢出、一个浮动页的纵向溢出，以及书签中的数学记号警告；本次没有将这些警告视为图24重绘的验收结果，也没有改写对应内容。

论文 PDF 为完整编译产物，未采用局部覆盖或贴图方式修改。
