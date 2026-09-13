CUMCM 2026 B 问题1–4 论文与代码

论文
  paper/main.tex  正文
  paper/main.pdf  Q3修订编译稿（50页）
  paper/tables    表
  paper/figures   图

代码
  code/q1q2/                 问题一、二：楔形交、Jung 圆、第二站
  code/q3/                   问题三修订：有限9点覆盖+有界收缩清除
  code/q4_method1/           问题四方法一：三角格网发现证书 + 覆盖推销员
  code/q4_method2/           问题四方法二：稀疏两阶段（不保证全部清除）
  code/shared/               共用几何、接口演练入口
  code/src_jianmo_b_sim/     覆盖半径等闭式几何

问题四方法二演练（完成面板，非正式测试）
  ZYMZ-N5QR-HR2Y-H7H2  12/14  279.1 s
  EU4V-7ZJY-RCJ2-39CZ  13/13  341.5 s
  EHHJ-JZHB-SDXR-EEBG  13/15  330.7 s
  合并不配对 318.1 s/已清

Q3 修订说明见 Q3_REVIEW.md。活动代码入口见 code/q3/README.md。
新离线验证不等于官方演练；旧代码保存在 searcher_legacy.py。
