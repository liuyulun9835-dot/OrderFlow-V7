using System;
using System.Globalization;
using System.IO;
using Newtonsoft.Json;
using ATAS.Indicators;
using ATAS.Indicators.Technical;

namespace AtasCustomIndicators
{
    // 显式指定基类，避免命名空间歧义
    public class SimplifiedDataExporter : ATAS.Indicators.Indicator
    {
        private readonly string _outputDirectory;

        public SimplifiedDataExporter()
        {
            Name = "SimplifiedDataExporter";

            // 导出目录：我的文档\ATAS\Exports
            _outputDirectory = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                "ATAS",
                "Exports"
            );

            if (!Directory.Exists(_outputDirectory))
                Directory.CreateDirectory(_outputDirectory);
        }

        // ATAS SDK 常见回调：OnCalculate(int bar, decimal value)
        // 你的模板若是 OnBarClose / Calculate 等，也按同样思路改写
        protected override void OnCalculate(int bar, decimal value)
        {
            // 边界保护
            if (bar < 0)
                return;

            // 取当前bar的蜡烛（如果你想严格用“已收盘上一根”，改成 bar-1 并判断 bar>0）
            var c = GetCandle(bar);
            if (c == null)
                return;

            // 组装要写出的字段
            var payload = new
            {
                timestamp = c.Time.ToString("o", CultureInfo.InvariantCulture), // ISO8601
                open = (double)c.Open,
                high = (double)c.High,
                low = (double)c.Low,
                close = (double)c.Close,
                volume = (double)c.Volume,

                // 结构/累积、吸收等（先占位，后续若加载相应指标对象可填充）
                poc = (double?)null,
                vah = (double?)null,
                val = (double?)null,
                cvd = (double?)null,

                absorption = new
                {
                    detected = false,
                    strength = 0.0,
                    side = ""
                }
            };

            // 1) 写最新快照 latest.json（覆盖写）
            var latestPath = Path.Combine(_outputDirectory, "latest.json");
            File.WriteAllText(latestPath, JsonConvert.SerializeObject(payload));

            // 2) 写历史分片：每天一个 .jsonl 文件，逐行追加（更利于后处理）
            var fileStamp = c.Time.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
            var histPath = Path.Combine(_outputDirectory, $"market_data_{fileStamp}.jsonl");
            File.AppendAllText(histPath, JsonConvert.SerializeObject(payload) + Environment.NewLine);
        }
    }
}
