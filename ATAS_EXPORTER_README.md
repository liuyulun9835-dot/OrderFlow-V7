## 快速构建/部署（固定项目路径）
在 PowerShell 中执行：
```
PowerShell -ExecutionPolicy Bypass -File .\scripts\build_exporter.ps1
```

**编译提示**：本项目要求 C# 8+（<LangVersion>latest</LangVersion>，<Nullable>enable</Nullable>）。若 VS“语言版本”界面仍显示 7.3，请手动检查 `SimplifiedDataExporter.csproj` 与 `atas_integration/Directory.Build.props`。

### 构建所需 ATAS SDK
- 默认读取：`C:\Program Files (x86)\ATAS Platform\bin`
- 可覆写（PowerShell）：
  ```powershell
  [Environment]::SetEnvironmentVariable('ATAS_SDK_DIR','D:\Your\ATAS\bin',[EnvironmentVariableTarget]::User)
  $env:ATAS_SDK_DIR='D:\Your\ATAS\bin'
  ```
### 指标卡在“Loading…”怎么办？
- 初次加载请保持 `SafeMode = true`；点“确定”让指标先运行起来并产生最小数据。
- 若无卡顿，再逐项打开 CVD / POC / VAH / VAL。
- 如果再次卡住，请查看 `%USERPROFILE%\Documents\ATAS\Indicators\exporter.log`，将最近 50 行发起排查。
