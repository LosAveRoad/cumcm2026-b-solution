"""One-time source integration for the Q3 review; inputs are the supplied paper."""
from pathlib import Path
import json
import math
import re

root = Path(__file__).resolve().parent
p = root/'paper/main.tex'
t = p.read_text(encoding='utf-8')
start = t.index(r'\section{问题三：')
end = t.index(r'\section{问题四：', start)
t = t[:start] + '\\input{q3-body.tex}\n\n' + t[end:]
start = t.index(r'\subsection{问题三的分析}')
end = t.index(r'\subsection{问题四的分析}', start)
t = t[:start] + r'''\subsection{问题三的分析}

全向源的发现可以按最小接收半径1000 m设计。原点加8环的9点网在半径1800 m场地上的最大最近距离为$\rho\approx956.051$ m，因此每个源必被某个网点听到。扫描必须覆盖该站的全部静默频道；只有整批请求成功后，才将其记作发现站。连续残留剪枝使用有理数矩形细分给出覆盖证书，数值未认证则直接访问原始网点。原点--环点Voronoi顶点半径$\tau\approx541.196$ m用于证明分段，并不是各方向统一的最近站分界。

修订算法将发现与清除分开。覆盖阶段每轮处理一个原始环点，最多8轮；之后对已发现源按距离上界的一半向测得示向度步进。余弦定理给出收缩系数$\sqrt{5/4-\cos1^\circ}<0.501$，从1500 m上界出发，七步内进入20 m清除窗，最多六次再测加一次清除。全任务包括进入、退出至多294次动作，默认900次动作闸不会在题设有效响应模型内截断。开放TSP与最近服务入口仅优化访问顺序，不声称时间全局最优。网络、现实期限及技术异常仍须报告为未完成。

旧射线启发式保留为历史基线；其三次演练不作为修订代码成绩。新代码另做48个可复现的离线模型场景验证，并保留尚待完成的官方演练和正式测试。

''' + t[end:]
old = '全向源采用9点侦听网给出最小接收半径下的距离可听闭式界，并对未扫静默频道的连续残留做剪枝，时间层先走覆盖骨架、一站示向度多数延后到覆盖结束后再沿测得示向度搜索'
new = '全向源采用9点侦听网和严格覆盖剪枝完成发现，再以距离上界收缩进入光学清除窗'
t = t.replace(old, new)
t = t.replace('问题三：9点侦听网的闭式覆盖半径为956.0510880488383 m，小于1000 m。',
              '问题三：9点网覆盖半径约956.051 m；有界收缩使每个已发现源最多再用7次动作清除，全任务动作上界为294。48个独立离线模型场景均全清；官方修订版测试尚待完成。')
# General discussion: update Q3 statements only, preserving other questions.
t = t.replace('全向源在覆盖骨架上扫完静默频道后再局部化', '全向源在有限覆盖阶段扫完静默频道后，再按距离上界收缩清除')
t = t.replace('全向距离覆盖在问题三关闭', '全向距离覆盖与有限步清除在问题三证明')
t = t.replace('问题三在$R_{\\mathrm{sec}}\\le 20$ m时按圆心证书清除，一站示向度多数延后到覆盖骨架走完之后再沿测得示向度搜索。',
              '问题三的修订策略先完成发现，再用距离上界收缩给出有限步清除证书。')
t = t.replace('问题三、问题四的接口动作次数以外层闸$A_{\\max}=900$截断。该上限是算法自设，原题未规定。覆盖扫描、静默频道检测、射线归航与追逐在达到该上限时返回；程序运行时间、测试窗口与技术异常同样中断。检测全称把这些情形列为残差，并且不证明覆盖循环必在有限步内走完。',
              '接口动作上限900为算法自设，原题未规定。修订Q3在题设有效响应模型下的动作上界为294；现实程序期限、测试窗口及技术异常仍可能中断。Q4保留原算法的动作预算与终止限制。')
old = '问题三用9点侦听网的闭式覆盖半径加上连续残留剪枝，在覆盖循环按残留空、静默频道空或已听满16个正常结束时给出全向源被听到的检测正确性；时间层先走覆盖骨架，两站服务点在覆盖未完时进入同一开放TSP并在选中后圆心再测再归航，一站示向度多数延后到覆盖结束后再沿测得示向度搜索。'
t = t.replace(old, '问题三将9点覆盖、严格保守剪枝与有界收缩结合，在题设模型和有效接口响应条件下给出有限动作全清定理，动作上界为294；访问顺序用开放TSP与最近服务入口优化。')
t = t.replace('全向局部化把覆盖骨架、D-最优插入与横向有限振幅作为时间启发式，虚拟时间对源的个数敏感。',
              '修订Q3用保守距离上界收缩清除，仍可能增加移动量，未证明时间最优。')
old = '连续残留检测定理的假设是全向、$R_{\\mathrm{eff}}\\ge 1000$ m、$N\\in[10,16]$且覆盖循环按前三类退出正常结束；$A_{\\max}=900$是算法自设闸，程序运行时间、测试窗口与技术异常是额外残差。同构几何核验与演练全部清除不是该定理。本文不证明覆盖循环必在有限步内走完，也不证明加密测站必在有限步把$R_{\\mathrm{sec}}$压到20 m。'
t = t.replace(old, '修订Q3给出了有限动作证明，但该证明不保证网络和现实窗口始终可用；旧演练数据不能验证新代码的实测速度，修订版官方演练及三次正式日志仍待补齐。')
t = t.replace('全向源应先走覆盖骨架，一站示向度多数延后到覆盖结束后再沿测得示向度搜索',
              '全向源应先完成有限覆盖，再用有界收缩或其它经认证的局部化方法清除')
t = t.replace('问题三表\\ref{tab:q3reh}对应9盘加连续残留、覆盖骨架优先的三次演练。',
              '问题三表\\ref{tab:q3reh}保留旧启发式的三次历史演练；修订实现位于\\texttt{code/q3/searcher.py}，新验证记录在\\texttt{code/q3/offline\\_results.json}。')
old = '全向检测定理只在问题三的全向假设、9盘、连续残留剪枝且覆盖循环按前三类退出正常结束时成立；$A_{\\max}=900$是算法自设闸，程序运行时间、测试窗口与技术异常是额外残差，同构几何核验与演练全部清除不能把它们删掉。'
t = t.replace(old, '修订问题三的有限动作全清证明依赖全向源假设，不能移用于本节的定向瓣；现实程序期限、测试窗口与技术异常仍可能造成未完成。')
t = t.replace('定量结论均在冻结附件上复现：', '原包列出的定量结论包括：')
# Correct only the Q3 discussion of the official table; Q4 table is unchanged.
t = t.replace('题目要求在充分演练之后，按表1的五列格式报告三次正式测试：',
              '题目要求在充分演练之后，按表1的四个字段报告三次正式测试：')
p.write_text(t, encoding='utf-8')
a = root/'paper/abstract-body.tex'
abstract = a.read_text(encoding='utf-8').replace(old, new)
# Keep the standalone abstract exactly synchronized with main.tex.
abstract = t.split('\\begin{abstract}\n',1)[1].split('\\keywords',1)[0]
a.write_text(abstract, encoding='utf-8')

data = json.loads((root/'code/q3/offline_results.json').read_text(encoding='utf-8'))
table = r'''\begin{table}[htbp]
\centering
\caption{修订Q3的独立离线模型验证（非官方模拟器）}\label{tab:q3offline}
\begin{tabular}{lr}\toprule
量 & 结果\\\midrule
场景数 / 全清场景数 & 48 / 48\\
每场源数 & 10--16\\
动作次数范围（含进入退出） & MIN--MAX\\
理论动作上界 & 294\\
总虚拟时间/总清除数（s/源） & POOL\\
场均路程（m） & WALK\\
官方模拟器演练次数（修订代码） & 0\\\bottomrule
\end{tabular}
\end{table}
'''.replace('MIN',str(data['min_actions'])).replace('MAX',str(data['max_actions']))
table = table.replace('POOL',f"{data['pooled_mean_clear_time_s']:.3f}").replace('WALK',f"{data['mean_walk_m']:.1f}")
(root/'paper/q3-validation-table.tex').write_text(table, encoding='utf-8')
q = root/'paper/q3-body.tex'
q.write_text(q.read_text(encoding='utf-8').replace('11.885','11.884'), encoding='utf-8')
print('Q3 source integrated; offline table generated.')
