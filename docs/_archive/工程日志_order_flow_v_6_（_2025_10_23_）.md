> ⚠️ 本文件的有效任务已收敛至 docs/TODO_V7.md；此处仅供历史参考。

# 工程日志 · 2025-10-23

**项目**：OrderFlow-V6  
**主题**：ATAS DLL 数据导出与 bar_vpo_* 特征验证  
**作者**：系统记录  

---

## 一、今日进展概况
1. **DLL 版本更新成功**  
   - 新版 `SimplifiedDataExporter v6.2` 已被 ATAS 正确加载；  
   - 输出数据中 `exporter_version = 6.2.0.0`，`schema_version = v6.2` 确认一致。  

2. **Schema 同步**  
   - 新 schema 已包含 `bar_vpo_price/vol/loc/side` 字段并保持可空；  
   - DLL 正常导出 OHLCV 、 CVD 、 Absorption 等时间序列层数据。  

3. **SafeMode 逻辑修正**  
   - SafeMode 关闭后导出稳定，无重复写入或崩溃；  
   - 输出 flush_seq 递增正常，数据连续性良好。  

---

## 二、当前主要问题
1. **bar_vpo_* 始终 null**  
   - 无论 1m、秒级、tick 精度，导出文件中 `bar_vpo_*` 均为空；  
   - 日志显示 `TryGetVolumeAtPrice` 未命中任何价阶容器；  
   - 说明 ATAS 在当前版本或回放模式下**未向自定义指标暴露 Volume-at-Price / Cluster 对象**。

2. **POC / VAH / VAL 同样无法读取**  
   - 与 bar_vpo 问题一致：ATAS 内部这些指标隶属 VPO/TPO profile 体系，不存在单 bar 级别定义。  

3. **缓存与部署效率问题**  
   - ATAS 持续加载旧 DLL （shadow copy 机制）；  
   - 通过改装配名、版本号 + PowerShell 部署脚本后，已找到一劳永逸的清缓存方案，但仍需在后续版本固化流程。  

---

## 三、已确认结论
- **可导出字段**：时间序列层（OHLCV、CVD、Absorption）工作正常。  
- **不可导出字段**：价阶层（POC / VAH / VAL / bar_vpo_*）在 ATAS SDK 接口中不可直接获取。  
- **原因机制**：ATAS 自定义指标 API 仅暴露时间序列级属性；价阶结构需依赖内部 Cluster/Footprint 对象，而这些对象不对指标开放。  

---

## 四、技术推论
- **POC/VAH/VAL 属于 Profile 语义**（VPO/TPO 口径），定义依赖会话或滚动窗口，不是单 bar 属性。  
- **bar_vpo_* 属于 价阶层 microstructure 指标**，在 ATAS 中并无现成接口，无法通过反射访问。  
- 因此，DLL 继续深挖意义不大，建议把价阶层计算移交至 **Python 预处理侧**。  

---

## 五、后续方向（待下阶段讨论）
1. **冻结 DLL 职责**  
   - 仅保留 OHLCV 、 CVD 、 Absorption 、 元信息导出；  
   - 价阶层字段留空，由下游补全。  

2. **价阶层外部重建方案**  
   - 使用交易所 aggTrades 逐笔数据在 Python 侧重建 Volume-at-Price 分布，生成 bar_vpo_*；  
   - 与 ATAS 数据在 merge 阶段重叠校准（PSI/KS/ECE）。  

3. **部署流程固化**  
   - 保留 PowerShell 一键清缓存脚本；  
   - 每次编译自动改装配名与版本号，防止 ATAS 缓存旧 DLL。  

4. **验证计划**  
   - 若后续 ATAS 开放 Footprint 接口，可恢复 bar_vpo_* 实时计算；  
   - 否则长期维持“时间序列层 = DLL 导出，价阶层 = 交易所重建”的分层结构。  

---

**状态小结**  
> 当前 v6.2 DLL 导出稳定但价阶数据缺失；核心问题并非代码逻辑，而是 ATAS API 访问权限限制。  
> 项目进入“价阶层外部重建”方案评估阶段。
