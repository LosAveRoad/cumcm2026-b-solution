# Q3 修订代码

活动策略：`q3_nine_net_contraction_v1`。只处理 Q3 全向源。
Python 3.10+，活动算法、测试器和 HTTP 客户端仅用标准库。

## 离线验证

在本目录执行：

```console
python -m unittest -v test_q3
python offline_validation.py --output offline_results.json
```

48 个确定种子场景全部清除；150--245 次动作（含进入退出）。
误差在同一源、同一位置固定。该测试器是按题设构建的独立离线模型，
不是官方模拟器；结果不能填入官方演练或正式测试表。

## 连接已开启的官方模拟器窗口

由操作员在官方模拟器中选择 Q3、完成登录和准备，接口就绪后执行：

```console
python run_q3.py --robot-id 你的队号 --output q3_run_result.json --trace q3_run_trace.jsonl
```

脚本不点击或启动任何测试窗口，只连接已就绪的本地端口2026并执行
enter/measure/clear/exit。会消耗当前已开启测试中的动作；务必确认所选
窗口类型。此次修订没有连接官方模拟器，也没有使用正式测试次数。
`sim_client.py` 从同一建模项目的已有 HTTP 客户端补入，已用无网络的请求
替身检查 JSON 字段；尚未验证修订代码在官方接口中的实际运行。

判定任务完成请读取 `complete`，不要只看清除个数。预算、拒绝、超时、
无效响应或清除证书失败均显式报告未完成。默认动作闸900；理论最多294次，
但294次动作并不保证网络与计算一定在现实窗口内完成。

## 文件

- `searcher.py`：有限9点发现、完整扫描提交、最多7步收缩清除。
- `certificates.py`：精确有理数矩形覆盖证书；未认证则保留网点。
- `run_q3.py`、`sim_client.py`：独立Q3入口与HTTP客户端。
- `offline_validation.py`、`test_q3.py`：离线验证与回归测试。
- `detection_proof.md/json`：与活动代码一致的条件性证明。
- `searcher_legacy.py`：原压缩包代码的逐字备份，仅供历史对照。它仍有
  原来的依赖和已知问题，不被活动实现调用，不适用新的294次动作定理。

活动Q3代码不再引用 `code/shared/geom.py` 的内接圆盘近似，亦不使用
浮点Voronoi最大值来授权剪枝。Q1、Q2、Q4代码及共享几何未修改。
原包 `code/shared/rehearsal.py` 不适配这个独立入口，Q3请使用上面的
`run_q3.py`；原共享入口保留供旧版本参考。
