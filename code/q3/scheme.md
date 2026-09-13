# 问题3 方案：9 盘覆盖 + 连续残留剪枝（P=1）+ 时间层（方案9）

## 决策

机器狗从原点、频道 1 出发。策略分三层：

1. **侦听网**是原点加上半径 \(1000\,\mathrm{m}\) 的 8 等分环，共 9 个侦听点。在最小有效接收半径 \(R_{\mathrm{eff}}=1000\,\mathrm{m}\) 下，该网对 \(1800\,\mathrm{m}\) 场地圆盘的覆盖是有限点集的闭式覆盖：最远点为相邻环侦听点的场地边界角平分点（相对环点张角 \(22.5^\circ\)），覆盖半径
   \[
   \rho=\sqrt{1800^2+1000^2-2\cdot 1800\cdot 1000\cos(\pi/8)}=\sqrt{4\,240\,000-1\,800\,000\sqrt{2+\sqrt{2}}}\approx 956.05\,\mathrm{m}<1000\,\mathrm{m}.
   \]
   因此**在全向源且** \(R_{\mathrm{eff}}\ge 1000\,\mathrm{m}\) **时**，场地内每一点到这 \(9\) 个侦听点的最近距离 \(\le\rho\)，必被听到。该保证不适用于问题4的 \(180^\circ\) 定向瓣。Monte Carlo `q3_omni_cover_frac_r1000=1` 只是对该界的抽样核对，不是覆盖模型。同一最远点检验下，6 环覆盖半径 \(\approx 1059.39\,\mathrm{m}>1000\,\mathrm{m}\)，故 8 环不是任意环数。
2. **检测保证是连续残留剪枝下的正常结束正确性，不是无条件「确保全部清除」。** 记发现站 \(\mathcal{S}\) 为实际扫描过剩余静默频道的位姿。连续残留 \(\mathrm{Res}_{\mathrm{cont}}=\mathbb{A}\setminus\bigcup_{S\in\mathcal{S}}\overline{\mathbb{D}}(S,1000)\)。侦听点 \(Q\in\mathbb{A}\) 仅当已证明上界 \(U=\rho(\mathcal{S},K_Q)\le 1000\) 时才丢掉；数值不确定则保留。不得用「膨胀 \(K\) 后再与 \(1000+\varepsilon\) 比较」当作 \(\rho(K)\le 1000\)。有限点集 `q3_residual_witnesses` **不得**用于剪枝。证书回退：残留非空则加回仍与 \(\mathrm{Res}_{\mathrm{cont}}\) 相交的 9 网点。不证明覆盖循环必在有限步内走完；\(A_{\max}=900\) 是算法自设闸，不是题面常数。超时与异常中断同样是残差。
3. **楔形追逐与时间层。** 某频道测到 `direction` 或 `near` 之后立刻局部化并清除。第二站优先问题2轴上 \(\psi\ge 45^\circ\) 覆盖点 \((800,700)\,\mathrm{m}\)，并允许共享 D-opt 第二站与途中顺便的后续侦听点。**清除证书**是 \(R_{\mathrm{sec}}(\Omega)\le 20\,\mathrm{m}\)（或对径圆覆盖且 \(D/2\le 20\,\mathrm{m}\)）时在该圆心 `/clear`。已达证书的 SEC 可用 Clarke–Wright 节省并入当前 tour。覆盖目标与就绪服务点走同一条 open TSP；仅 1 站示向度的频道用后验 \(\hat G\) 只参加**最后**一条服务 TSP，不把 \(\hat G\) 加进 9 盘 covering 城市（那会重建星形）。若定位区仍大于 \(20\,\mathrm{m}\)，继续加密测站，不在大 \(\Omega\) 上强制清除。

侦听点访问不是固定按 \(k=0,\ldots,7\) 走环：每完成一次追逐，下一侦听点取**剩余点中距机器狗最近者**（原点仍是 `/enter` 后的第一点）。最近剩余、D-opt、savings 与服务 TSP 都是时间启发式；发现证书是 9 盘加上连续残留剪枝。频道扫描顺序：剩余未清除频道，优先当前测向机频道（避免无谓的 \(1\,\mathrm{s}\) 换台），然后按编号。`/clear` 不切换测向机频道。本方案不再探索问题3时间方向。

## 控制方程

虚拟时间只在 `accepted=true` 的 `/measure`、`/clear` 上推进：
\[
\Delta T_{\mathrm{measure}}=\frac{\|P_{\mathrm{new}}-P_{\mathrm{old}}\|}{5}+1\cdot\mathbf{1}_{c\neq c_{\mathrm{radio}}}+5,
\]
\[
\Delta T_{\mathrm{clear}}=\frac{\|P_{\mathrm{new}}-P_{\mathrm{old}}\|}{5}+\begin{cases}5 & \text{success}\\ 3 & \text{no\_target\_in\_range.}\end{cases}
\]
在 \(S\) 测到信号 \(\Rightarrow\|G-S\|\le 1500\)。`near` \(\Rightarrow\) 距离 \(\le 5\,\mathrm{m}\) 且在覆盖角内，就地 `/clear`。已清除频道不再扫描。

多站楔形交 \(\Omega\) 用问题1算法。清除充分条件：\(R_{\mathrm{sec}}(\Omega)\le 20\,\mathrm{m}\)。

**引理（圆心再测，全向）。** 假设源为全向，\(R_{\mathrm{eff}}\ge 1000\,\mathrm{m}\)，且 \(R_{\mathrm{sec}}(\Omega)\le 1000\,\mathrm{m}\)。则 \(G\in\Omega\subseteq\overline{\mathbb{D}}(C,R_{\mathrm{sec}})\)，在 SEC 圆心测量不是 `no_signal`。该引理对定向瓣不成立。\(20<R_{\mathrm{sec}}\le 80\) 时圆心 `no_signal` 后的 \(18\,\mathrm{m}\) 六邻点**不是**半径 \(80\,\mathrm{m}\) 盘的覆盖。

原点不能单独保证听到全部源：场地半径 \(1800\,\mathrm{m}\)，\(r>1500\) 的源从原点必听不到。

### 9 盘覆盖的最远点界

记原点 \(O=(0,0)\)，环点 \(R_k=1000\bigl(\cos\frac{k\pi}{4},\sin\frac{k\pi}{4}\bigr)\)，\(k=0,\ldots,7\)，侦听网 \(\mathcal{N}=\{O\}\cup\{R_0,\ldots,R_7\}\)，场地 \(\mathbb{D}(0,1800)\)。覆盖半径由 `jianmo.b_sim.geometry.q3_omni_covering_radius` 给出。不得把 \(O\) 与 \(R_0\) 写成同一个 \(S_0\)。

**引理（全向侦听覆盖，9 盘）。** 假设场地为闭圆盘 \(\mathbb{D}(0,1800)\)，侦听网为原点加半径 \(1000\,\mathrm{m}\) 的 8 等分环，\(R_{\mathrm{eff}}=1000\,\mathrm{m}\)。对任意 \(G\in\mathbb{D}(0,1800)\)，
\[
\min_{S\in\mathcal{N}}\|G-S\|=\min\Bigl(\|G\|,\ \min_{k=0,\ldots,7}\|G-R_k\|\Bigr)\le\rho\approx 956.05\,\mathrm{m}.
\]
从而 9 盘覆盖整个场地。该界是覆盖模型；Monte Carlo 只作核对。

仅对 8 个环点取最小则命题不真：在原点 \(\min_k\|O-R_k\|=1000>\rho\)（`q3_eight_ring_min_at_origin_le_rho=0`），而 9 盘最小为 \(0\)（`q3_nine_disk_min_at_origin_le_rho=1`）。

**证明。** 由旋转对称，取 \(\arg G=\theta\in[0,\pi/4]\)，令 \(\delta=\min(\theta,\pi/4-\theta)\le\pi/8\)。记 \(c=\cos(\pi/8)\)、\(t=1000/(2c)\approx 541.196\)。若 \(r\le t\)，用原点，\(\|G-O\|=r\le t<\rho\)。若 \(t\le r\le 1800\)，最近环点满足 \(\|G-R\|^2\le f(r):=r^2+10^6-2000\,c r\)（因为 \(\cos\delta\ge c\)）。\(f\) 凸，故
\[
f(r)\le\max\{f(t),f(1800)\}=\max\{t^2,\rho^2\}=\rho^2.
\]
这就给出所声称的上界 \(\rho\)，而不只是「\(r\le 1000\) 时不超过 \(1000\)」。极小点 \(1000\cos\delta\le 1000\) 足以说明 \(f\) 在 \([1000,1800]\) 上递增。

同一最远点公式对 \(n=6\)（圆心角 \(30^\circ\)）给出 \(\sqrt{1800^2+1000^2-2\cdot 1800\cdot 1000\cos(\pi/6)}\approx 1059.39\,\mathrm{m}>1000\,\mathrm{m}\)，6 环不能覆盖场地边界角平分点。

## 算法

1. `/enter`。记录 `remaining_real_duration_s`，不得假定总是 \(1200\,\mathrm{s}\)。
2. 剩余侦听点集合初始化为原点加 8 环点。覆盖路点对尚未清除的静默频道做检测时不进入追逐：`near` 就地清除，`direction` 只记示向度，该点把剩余静默频道扫完后再走下一覆盖路点。访问前仅当已证明 \(U\le 1000\) 时丢掉格子；证书回退把仍与 \(\mathrm{Res}_{\mathrm{cont}}\) 相交的 9 网点加回。最近剩余 / D-opt / savings / 服务 TSP 是时间启发式。
3. 追逐分层：
   - 一站示向度：去问题2轴上覆盖点 \((800,700)\,\mathrm{m}\)；`no_signal` 则另一侧，再沿示向度 \(400\,\mathrm{m}\)。
   - 两站及以上：算 \(\Omega\)。若 \(R_{\mathrm{sec}}\le 20\,\mathrm{m}\)（或对径圆覆盖且 \(D/2\le 20\)），在该圆心 `/clear`（清除证书）。
   - 若 \(20<R_{\mathrm{sec}}\le 1000\,\mathrm{m}\)，在 SEC 圆心再测（全向圆心再测引理）：`near` 则清除，`direction` 则新楔并入 \(\Omega\) 并重算，`no_signal` 仅当 \(R_{\mathrm{sec}}\le 80\,\mathrm{m}\) 时尝试圆心 `/clear` 与 \(18\,\mathrm{m}\) 六邻点（不覆盖 \(80\,\mathrm{m}\) 盘）。
   - 若圆心再测后仍未清除，或 \(R_{\mathrm{sec}}>1000\,\mathrm{m}\)，从最后一站再取 \((800,700)\,\mathrm{m}\) 加密测站。这是局部化主循环，不是在大定位区上强制清除。
   - 循环上限 \(10\) 次用尽后，在圆心强制 `/clear` 是动作预算的最后手段，当 \(R_{\mathrm{sec}}>20\,\mathrm{m}\) 时不是覆盖证书。
4. 残留有示向度但未清除的频道再追逐一遍。
5. `/exit`。每步新 `request_id`，串行等待；仅在重试同一中断请求时复用 `request_id`。`arena_id="default"`，`robot_id` 等于登录队号。

动作上限约 900，防止空转顶满 \(20\,\mathrm{min}\) 现实时限。时间启发式失败时回退到证书动作：尚未访问的侦听点仍要走；尚未 \(R_{\mathrm{sec}}\le 20\) 的频道继续加密测站直到证书成立或预算用尽。

## 过门指标

问题3证书是 `q3_omni_covering_radius`（\(\rho\approx 956.05\,\mathrm{m}<1000\,\mathrm{m}\)，最远点场地边界角平分点），以及原点处 8 环最小 \(1000>\rho\)、9 盘最小 \(0\le\rho\)。`fact:fit.q3q4-certificates` 过门 `q3_omni_covering_radius_m=956.0510880488383`、`q3_omni_covers=1`、`q3_eight_ring_min_at_origin_le_rho=0`、`q3_nine_disk_min_at_origin_le_rho=1`。`fact:fit.q3q4-scout-cover` 中的 `q3_omni_cover_frac_r1000=1` 只是对该界的 Monte Carlo 核对（4000 个均匀圆盘样本，种子 2026），不是覆盖模型。几何直径与第二站见问题1–2 的门。

TwinClient（全向、听距 \(\|G-S\|\le R_{\mathrm{eff}}\)，非正式测试）24/24 全清，均值 \(272.227\,\mathrm{s}\)/源、路程 \(12.4\,\mathrm{km}\)。现场问题3演练三次连清（完成面板 `n_cleared==n_true`）：`UUDJ-WJGP-NBRH-8V2N` 16/16 均时 \(197.4\,\mathrm{s}\)；`XUXT-9646-NF9K-42J4` 12/12 均时 \(280.0\,\mathrm{s}\)；`2GA6-9ADV-XD3E-AVMK` 11/11 均时 \(295.0\,\mathrm{s}\)。合并不配对均值 \(250.4\,\mathrm{s}\)/源，不是 Twin 同实例对照。有限残留反例 \(G_\star\) 在连续剪枝下被听到。不得把这些演练行写成正式测试表。检测证明见 `artifacts/experiments/bearing_chase/q3_explore/p1_sprint/detection_proof.md`（`proved_p1=true`）。

正式测试（队号 202617201069，三场机会用完）。完成弹窗不给出干扰源总数，清除个数与平均时间为 HTTP `/clear` 成功次数及虚拟时间之比；程序运行时间为 `/enter` 与 `/exit` 的 `real_timestamp_ms` 之差。不得把该清除个数写成干扰源总数。

- `TKUB-AWDW-FWUJ-53UT` 清除 12，均时 \(252.466\,\mathrm{s}\)，程序运行 \(4.890\,\mathrm{s}\)
- `YZRC-HM6Q-TAFH-W5W9` 清除 11，均时 \(279.556\,\mathrm{s}\)，程序运行 \(5.449\,\mathrm{s}\)
- `YYM7-3QP9-TJEH-VBD9` 清除 13，均时 \(255.325\,\mathrm{s}\)，程序运行 \(4.136\,\mathrm{s}\)

合计 HTTP 清除 36、虚拟时间 \(9423.932\,\mathrm{s}\)，合并不配对 \(261.776\,\mathrm{s}\)/已清。实现：`artifacts/experiments/bearing_chase/searcher.py`（`mixed=False`）。

## 限度

有效接收半径在 \([1000,1500]\) 内未知，侦听网按 \(1000\,\mathrm{m}\) 设计，偏保守。示向度误差在同一地点固定，故重复在同一点检测不缩小楔形。现实时间用 `/enter` 返回的剩余秒数约束；虚拟时间可远长于现实时间。9 盘覆盖引理只保证**全向**源在某网点距离 \(\le\rho\)；**不保证首次听到的站**满足该距离（反例 \(G=(1400,0)\)、\(R_{\mathrm{eff}}=1500\)，原点首次听到，距离 \(1400\) m）。连续残留检测定理是**前三类正常结束**下的正确性保证，不是题面「确保全部清除」，也不证明覆盖必在有限步内走完。\(A_{\max}=900\) 是算法自设，不是 PDF 题面常数；超时与异常同样中断。定向发现是问题4的 \(N_9\cup R_{12}\)，不是三角格网。圆心强制 `/clear` 在 \(R_{\mathrm{sec}}>20\,\mathrm{m}\) 时不是清除证书。

射线清除：轴上清除点 \(P\) 满足 \(\|SP\|=\|SG\|=r\) 时，弦长 \(\|PG\|=2r\sin(|\alpha|/2)\)。对某个实际源，命中 iff \(2r\sin(|\alpha|/2)\le 20\)。对一切 \(|\alpha|\le 1^\circ\)，保证命中 iff \(2r\sin 0.5^\circ\le 20\) 即 \(r\le 20/(2\sin 0.5^\circ)\approx 1145.9301348\,\mathrm{m}\)。\(r\tan 1^\circ\) 是轴向距离 \(r\) 处垂直截面半宽，只是保守充分条件，不是该充要；\(20/\tan 1^\circ\approx 1145.7992326\,\mathrm{m}\)，不得写 \(1145.92\)。\(\rho<r_{\mathrm{ray}}\) 不能推出「首次听到的站」上轴上 20 m 圆必中。

连续残留第 2 条（\(Q\) 听不到剩余源）须用场地凸性：若 \(d=\|QG\|\le 1000\) 则 \(G\in K_Q\) 已被覆盖；若 \(d>1000\)，线段上 \(|QP|=1000\) 的 \(P\in K_Q\)，某发现站 \(S\) 满足 \(\|SP\|\le 1000\)，故 \(\|SG\|\le d\le R_G\)。透镜最大值类须补 Voronoi 边内部 \(d^2\) 严格凸（不能取局部最大），以及同心圆、重复站点、相切、共圆等退化。剪枝只在已证明上界 \(U\le 1000\) 时执行。
