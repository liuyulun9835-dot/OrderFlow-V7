## 快速构建/部署（固定项目路径）
在 PowerShell 中执行：
```
PowerShell -ExecutionPolicy Bypass -File .\scripts\build_exporter.ps1
```

**编译提示**：本项目要求 C# 8+（<LangVersion>latest</LangVersion>，<Nullable>enable</Nullable>）。若 VS“语言版本”界面仍显示 7.3，请手动检查 `SimplifiedDataExporter.csproj` 与 `atas_integration/Directory.Build.props`。

### SDK 自动探测
构建时按以下顺序寻找 `Atas.Indicators.dll`：
1) `ATAS_SDK_DIR` 环境变量
2) `C:\Program Files\ATAS\bin`
3) `C:\Program Files\ATAS Platform\bin`
4) `%LOCALAPPDATA%\Programs\ATAS\bin`
可显式设置（PowerShell）：
```powershell
[Environment]::SetEnvironmentVariable('ATAS_SDK_DIR','C:\Path\To\ATAS\bin',[EnvironmentVariableTarget]::User)
$env:ATAS_SDK_DIR='C:\Path\To\ATAS\bin' # 当前会话生效
```
