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
