# 问题4 方案：9 盘 ∪ 外环 12 点检测网（非 ∀u）+ 开圆时间层

## 决策

问题四**只采用本方案**。37 点 \(\rho<500\) 三角格网 \(\forall g\forall u\) 证书、覆盖推销员、以及 9 网加扇区补丁的方法二，均不进入正文。

检测网 \(\mathcal{N}=N_9\cup R_{12}\)：\(N_9\) 是问题三的原点加半径 \(1000\,\mathrm{m}\) 的 8 等分环；\(R_{12}\) 是半径 \(2000\,\mathrm{m}\) 上的 12 等分点（圆心角 \(30^\circ\)，最近外环点相对源的方位差 \(\Delta\theta\le 15^\circ\)）。全向源走完 \(N_9\) 必听。定向源听到当且仅当存在 \(S\in\mathcal{N}\) 使 \(\|S-g\|\le R_{\mathrm{eff}}\) 且 \((S-g)\cdot u\ge 0\)。本方案**不**声称 \(\forall g\forall u\)。残留
\[
\mathrm{Res}=\{(g,u): \mathcal{N}\cap\overline{\mathbb{D}}(g,1000)\ \text{全落在开背瓣}\}.
\]
占用达到 \(16\) 则剩余静默频道为空。单次 `no_signal` 不能清空频道。全清除不是门禁。

时间层：内圈按 \(N_9\) 连续残留蛇形，仅附近追逐；外环 \(R_{12}\) 开圆巡回；覆盖结束后一条服务 TSP。问题3（`mixed=False`）仍是方案9，本文件不改。

## 控制方程

定向检测：\(\|S-G\|\le R_{\mathrm{eff}}\) 且 \((S-G)\cdot u_H\ge 0\)。全向去掉半平面因子。虚拟时间只在 `accepted=true` 的 `/measure`、`/clear` 上推进，速度 \(5\,\mathrm{m/s}\)，测向 \(5\,\mathrm{s}\)。全知 TSP-on-\(G\) 加 \(5\,\mathrm{s}/\)清约 \(133\)–\(151\,\mathrm{s}/\)源。

**引理（全向，9 盘）。** 假设源为全向，\(G\in\overline{\mathbb{D}}(0,1800)\)，\(R_{\mathrm{eff}}\ge 1000\)。完成 \(N_9\) 后必听，当且仅当覆盖半径 \(\rho(N_9)\approx 956.05\,\mathrm{m}<1000\,\mathrm{m}\)（最远点为场地边界角平分点）。证明见问题三。

**引理（外环距离）。** 假设 \(g\in\overline{\mathbb{D}}(0,1800)\)，\(S^\star\) 为 \(R_{12}\) 中方位最近的点，则 \(\Delta\theta\le 15^\circ\)。边界中缝 \(\|S^\star-g\|\) 的最大值约 \(534.2\,\mathrm{m}<1000\,\mathrm{m}\)。故每个边界位置都有外环点落在距离盘内。

**引理（定向，非 ∀u）。** 假设源为定向。听到当且仅当存在 \(S\in\mathcal{N}\) 使 \(\|S-g\|\le R_{\mathrm{eff}}\) 且 \((S-g)\cdot u\ge 0\)。若最近外环点满足 \((S^\star-g)\cdot u\ge 0\)（含径向外指），则该源被听到。若 \(\mathcal{N}\) 与 \(\overline{\mathbb{D}}(g,1000)\) 的交全在开背瓣，则听不到。这不是 \(\forall g\forall u\)。

**清除证书。** \(R_{\mathrm{sec}}(\Omega)\le 20\,\mathrm{m}\)（或对径圆且 \(D/2\le 20\)）时圆心 `/clear` 必中。光学：边长 \(25\,\mathrm{m}\) 方格格心到顶点 \(\approx 17.68<20\)，仅当 \(R_{\mathrm{sec}}\le 80\,\mathrm{m}\) 时铺格。

## 算法

1. `/enter`。问题四 `mixed=True`。
2. 内圈：剩余 \(N_9\) 用连续残留剪枝，蛇形访问，位姿上扫完静默频道。`near` 就地清；`direction` 仅附近才打断。
3. 若占用 \(<16\) 且静默频道仍在，走 \(R_{12}\) 开圆。占用 \(=16\) 可提前停网。
4. 已听未清频道走一条服务 TSP。保扇形短步，`no_signal` 换侧。\(R_{\mathrm{sec}}\le 20\) 圆心清除。
5. `/exit`。禁止正式测试。动作上限约 \(900\)。

## 过门指标

官方模拟器问题4演练三次（完成面板，非正式测试，每次 \(n_{\mathrm{dir}}\ge 1\)）：

- `94W6-GKZD-JQQR-WHHE` \(16/16\)（全向 \(13\)、定向 \(3\)）均时 \(267.641\,\mathrm{s}\)、路程 \(17.2\,\mathrm{km}\)
- `U3UH-8T3Y-3TSU-Q2A5` \(12/12\)（\(4+8\)）均时 \(617.168\,\mathrm{s}\)、路程 \(27.3\,\mathrm{km}\)
- `U9B5-CN4M-ZBEN-Y3JH` \(11/11\)（\(8+3\)）均时 \(718.879\,\mathrm{s}\)、路程 \(30.9\,\mathrm{km}\)

合计 \(19595.949\,\mathrm{s}/39\) 源，合并不配对 \(502.460\,\mathrm{s}/\)源，平均路程 \(25.1\,\mathrm{km}\)。不得抄入正式测试表。Twin 8 世界全清均时 \(580.7\,\mathrm{s}\) 只作诊断。实现：`artifacts/experiments/bearing_chase/q4_explore/selected/searcher.py`。

## 限度

定向引理不覆盖开背瓣。占用不到 \(16\) 时走完 \(R_{12}\) 是该引理的覆盖税。全清除不是本方案门禁；三次演练全清不能代替引理。37 点格网不是本时间层证书。
