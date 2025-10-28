using System;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Globalization;
using System.ComponentModel;
using System.Linq;

// Keep ATAS-related usings consistent with existing SimplifiedDataExporter.cs
using ATAS.Indicators;
using ATAS.Types;

namespace AtasCustomIndicators.V63
{
    /// <summary>
    /// TickTapeExporter
    /// Exports one JSON line per trade (JSONL) with heartbeat and buffered IO.
    /// Designed to sit alongside existing 1m exporter; does not modify it.
    /// </summary>
    public class TickTapeExporter : Indicator
    {
        private const string ExporterVersion = "6.3";
        private const string SchemaVersion = "tick.v1";

        // ==== 用户可配置参数（在 ATAS 指标参数面板里显示） ====
        [DisplayName("OutputRoot")]
        [Description(@"输出根目录；默认 C:\\CentralDataKitchen\\staging\\atas\\ticks")]
        public string OutputRoot { get; set; } = @"C:\\CentralDataKitchen\\staging\\atas\\ticks";

        [DisplayName("Exchange")]
        [Description("交易所标识（可手动覆盖），留空则尽量从图表环境推断")]
        public string Exchange { get; set; } = "BINANCE_FUTURES";

        [DisplayName("Symbol")]
        [Description("标的（留空则从图表环境自动获取）")]
        public string Symbol { get; set; } = "";

        [DisplayName("FlushBatchSize")]
        [Description("达到此条数则触发写入 (默认 200)")]
        public int FlushBatchSize { get; set; } = 200;

        [DisplayName("FlushIntervalMs")]
        [Description("最长等待写入间隔 (ms) (默认 100)")]
        public int FlushIntervalMs { get; set; } = 100;

        [DisplayName("HeartbeatEveryMs")]
        [Description("心跳写入间隔 (ms) (默认 5000)")]
        public int HeartbeatEveryMs { get; set; } = 5000;

        [DisplayName("PartitionByHour")]
        [Description("是否按小时子目录分区 (默认为 true)")]
        public bool PartitionByHour { get; set; } = true;

        // ==== 内部状态 ====
        private readonly ConcurrentQueue<TradeTick> _queue = new();
        private readonly CancellationTokenSource _cts = new();
        private Task? _writerTask;
        private DateTime _lastFlushUtc = DateTime.MinValue;
        private DateTime _lastHeartbeatUtc = DateTime.MinValue;
        private long _ticksSinceHeartbeat = 0;
        private string _resolvedSymbol = "";
        private string _heartbeatPath = "";

        // Logger path inside OutputRoot/_logs
        private string LogPath => Path.Combine(OutputRoot ?? @"C:\\CentralDataKitchen\\staging\\atas\\ticks", "_logs", "TickTapeExporter.log");

        public TickTapeExporter()
        {
            Name = "TickTapeExporter (JSONL)";
            // constructor lightweight; heavy init in OnStateChanged
        }

        #region ATAS lifecycle

        protected override void OnStateChanged()
        {
            base.OnStateChanged();

            // When indicator becomes Ready, initialize resources and (if possible) attach to tick feed.
            if (State == State.Ready)
            {
                try
                {
                    _resolvedSymbol = string.IsNullOrWhiteSpace(Symbol) ? TryGetSymbolFromChart() : Symbol;
                    if (string.IsNullOrWhiteSpace(_resolvedSymbol))
                        _resolvedSymbol = "UNKNOWN";

                    _heartbeatPath = Path.Combine(OutputRoot, "_heartbeats", "TickTapeExporter", _resolvedSymbol, "heartbeat.txt");
                    Directory.CreateDirectory(Path.GetDirectoryName(_heartbeatPath)!);

                    // Start background writer
                    _writerTask = Task.Run(WriterLoop, _cts.Token);

                    // Attempt to subscribe to trade events.
                    // Different ATAS SDK versions expose different hooks.
                    // We provide a few handler signatures; actual subscription may require adapting to local SDK.
                    TryAttachToTrades();
                }
                catch (Exception ex)
                {
                    LogLocalError("OnStateChanged.Ready", ex);
                }
            }
            else if (State == State.Terminated)
            {
                SafeShutdown();
            }
        }

        public override void Dispose()
        {
            SafeShutdown();
            base.Dispose();
        }

        #endregion

        #region Trade subscription (best-effort)

        // Many ATAS SDKs will call methods with these signatures; include both handlers.
        // If your SDK requires explicit subscription, adapt TryAttachToTrades to do so (reflection or SDK-specific API).

        // Example signature variant: SDK passes a wrapper arg with .Trade
        protected virtual void OnNewTrade(object arg)
        {
            try
            {
                if (arg == null) return;

                // Try to extract trade object if wrapped in a MarketDataArg-like container
                dynamic dyn = arg;
                if (HasProperty(dyn, "Trade"))
                {
                    HandleIncomingTrade(dyn.Trade);
                    return;
                }

                // Otherwise attempt to treat arg as trade directly
                HandleIncomingTrade(dyn);
            }
            catch (Exception ex)
            {
                LogLocalError("OnNewTrade", ex);
            }
        }

        // Example signature variant: SDK directly supplies a Trade-like object
        protected virtual void OnTrade(object trade)
        {
            try
            {
                if (trade == null) return;
                HandleIncomingTrade(trade);
            }
            catch (Exception ex)
            {
                LogLocalError("OnTrade", ex);
            }
        }

        // Try to attach via common SDK points using reflection (best-effort; safe no-ops if unavailable)
        private void TryAttachToTrades()
        {
            try
            {
                // Attempt common event targets by name (no-throw via reflection)
                // 1) Try to find a static MarketData type with an event named NewTrade / Trade / OnNewTrade
                var sdkAssemblies = AppDomain.CurrentDomain.GetAssemblies();
                foreach (var asm in sdkAssemblies)
                {
                    try
                    {
                        var marketDataType = asm.GetTypes().FirstOrDefault(t => t.Name.IndexOf("MarketData", StringComparison.OrdinalIgnoreCase) >= 0);
                        if (marketDataType == null) continue;

                        var events = marketDataType.GetEvents();
                        foreach (var ev in events)
                        {
                            if (!ev.Name.Contains("Trade", StringComparison.OrdinalIgnoreCase) && !ev.Name.Contains("New", StringComparison.OrdinalIgnoreCase))
                                continue;

                            // Try to subscribe handlers by creating a delegate if event handler type is simple
                            var handlerType = ev.EventHandlerType;
                            if (handlerType == null) continue;

                            // Try to create delegate pointing to OnNewTrade or OnTrade
                            var onNewMethod = GetType().GetMethod(nameof(OnNewTrade), System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public);
                            var onTradeMethod = GetType().GetMethod(nameof(OnTrade), System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public);

                            Delegate? del = null;
                            if (onNewMethod != null)
                            {
                                try { del = Delegate.CreateDelegate(handlerType, this, onNewMethod); } catch { del = null; }
                            }
                            if (del == null && onTradeMethod != null)
                            {
                                try { del = Delegate.CreateDelegate(handlerType, this, onTradeMethod); } catch { del = null; }
                            }

                            if (del != null)
                            {
                                // If event is static, pass null target; otherwise try to find singleton instance in type
                                object? targetInstance = null;
                                if (!ev.AddMethod.IsStatic)
                                {
                                    // Try to get a public static Instance/Default property
                                    var instProp = marketDataType.GetProperty("Instance") ?? marketDataType.GetProperty("Default");
                                    if (instProp != null) targetInstance = instProp.GetValue(null);
                                }

                                try
                                {
                                    ev.AddEventHandler(targetInstance, del);
                                }
                                catch
                                {
                                    // ignore subscription failures
                                }
                            }
                        }
                    }
                    catch
                    {
                        // ignore type load / reflection errors
                    }
                }
            }
            catch (Exception ex)
            {
                LogLocalError("TryAttachToTrades", ex);
            }
        }

        private static bool HasProperty(dynamic obj, string propName)
        {
            try
            {
                if (obj == null) return false;
                var type = (object)obj.GetType();
                return type.GetType().GetProperty(propName) != null || obj.GetType().GetProperty(propName) != null;
            }
            catch
            {
                return false;
            }
        }

        private void HandleIncomingTrade(dynamic t)
        {
            try
            {
                if (t == null) return;

                // Extract common fields using multiple possible property names
                DateTime ts;
                if (HasMember(t, "Time")) ts = ToDateTimeUtc(t.Time);
                else if (HasMember(t, "Timestamp")) ts = ToDateTimeUtc(t.Timestamp);
                else if (HasMember(t, "Date")) ts = ToDateTimeUtc(t.Date);
                else ts = DateTime.UtcNow;

                double price = TryGetDouble(t, new[] { "Price", "TradePrice", "LastPrice", "Px" }) ?? double.NaN;
                double qty = TryGetDouble(t, new[] { "Volume", "Size", "Quantity", "Qty" }) ?? double.NaN;

                // side/aggressor
                string side = "unknown";
                if (HasMember(t, "Aggressor")) side = Convert.ToString(t.Aggressor, CultureInfo.InvariantCulture) ?? "unknown";
                else if (HasMember(t, "IsBuyerMaker") )
                {
                    try
                    {
                        bool ism = Convert.ToBoolean(t.IsBuyerMaker);
                        side = ism ? "sell" : "buy"; // common convention
                    }
                    catch { }
                }
                else if (HasMember(t, "Direction")) side = Convert.ToString(t.Direction, CultureInfo.InvariantCulture) ?? "unknown";

                double? bestBid = TryGetDouble(t, new[] { "BestBid", "Bid" });
                double? bestAsk = TryGetDouble(t, new[] { "BestAsk", "Ask" });
                string? tradeId = TryGetString(t, new[] { "TradeId", "Id", "OrderId", "TID" });

                var tick = new TradeTick
                {
                    TsUtc = ts.ToUniversalTime(),
                    Exchange = Exchange ?? string.Empty,
                    Symbol = _resolvedSymbol,
                    Price = price,
                    Qty = qty,
                    Side = string.IsNullOrEmpty(side) ? "unknown" : side,
                    BestBid = bestBid,
                    BestAsk = bestAsk,
                    TradeId = tradeId,
                    ExpVer = ExporterVersion,
                    SchemaVer = SchemaVersion
                };

                _queue.Enqueue(tick);
                Interlocked.Increment(ref _ticksSinceHeartbeat);
            }
            catch (Exception ex)
            {
                LogLocalError("HandleIncomingTrade", ex);
            }
        }

        private static DateTime ToDateTimeUtc(object? o)
        {
            try
            {
                if (o == null) return DateTime.UtcNow;
                if (o is DateTime dt) return dt.Kind == DateTimeKind.Utc ? dt : dt.ToUniversalTime();
                if (o is DateTimeOffset dto) return dto.UtcDateTime;
                if (long.TryParse(o.ToString(), out var ticks)) return DateTimeOffset.FromUnixTimeMilliseconds(ticks).UtcDateTime;
                if (double.TryParse(Convert.ToString(o, CultureInfo.InvariantCulture), NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
                {
                    // treat as unix seconds if reasonable
                    if (d > 1e10) // milliseconds
                        return DateTimeOffset.FromUnixTimeMilliseconds((long)d).UtcDateTime;
                    if (d > 1e9) // seconds
                        return DateTimeOffset.FromUnixTimeSeconds((long)d).UtcDateTime;
                }
                if (DateTime.TryParse(Convert.ToString(o, CultureInfo.InvariantCulture), CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out var parsed))
                    return parsed.ToUniversalTime();
            }
            catch { /* fallback */ }
            return DateTime.UtcNow;
        }

        private static bool HasMember(dynamic obj, string name)
        {
            try
            {
                if (obj == null) return false;
                return obj.GetType().GetProperty(name) != null;
            }
            catch
            {
                return false;
            }
        }

        private static double? TryGetDouble(dynamic obj, string[] candidates)
        {
            try
            {
                foreach (var c in candidates)
                {
                    if (HasMember(obj, c))
                    {
                        var val = obj.GetType().GetProperty(c)!.GetValue(obj);
                        if (val == null) continue;
                        if (val is double dd) return dd;
                        if (val is float f) return Convert.ToDouble(f, CultureInfo.InvariantCulture);
                        if (val is decimal dec) return Convert.ToDouble(dec, CultureInfo.InvariantCulture);
                        if (double.TryParse(Convert.ToString(val, CultureInfo.InvariantCulture), NumberStyles.Any, CultureInfo.InvariantCulture, out var d))
                            return d;
                    }
                }
            }
            catch { }
            return null;
        }

        private static string? TryGetString(dynamic obj, string[] candidates)
        {
            try
            {
                foreach (var c in candidates)
                {
                    if (HasMember(obj, c))
                    {
                        var v = obj.GetType().GetProperty(c)!.GetValue(obj);
                        if (v == null) continue;
                        return Convert.ToString(v, CultureInfo.InvariantCulture);
                    }
                }
            }
            catch { }
            return null;
        }

        #endregion

        #region Writer loop & IO

        private async Task WriterLoop()
        {
            var token = _cts.Token;
            var buffer = new List<TradeTick>(FlushBatchSize);

            while (!token.IsCancellationRequested)
            {
                try
                {
                    // Dequeue up to FlushBatchSize items
                    while (buffer.Count < FlushBatchSize && _queue.TryDequeue(out var item))
                        buffer.Add(item);

                    var nowUtc = DateTime.UtcNow;

                    if (buffer.Count >= FlushBatchSize ||
                        (buffer.Count > 0 && (nowUtc - _lastFlushUtc).TotalMilliseconds >= FlushIntervalMs))
                    {
                        if (buffer.Count > 0)
                        {
                            await FlushAsync(buffer, token).ConfigureAwait(false);
                            buffer.Clear();
                            _lastFlushUtc = nowUtc;
                        }
                    }

                    // Heartbeat
                    if ((nowUtc - _lastHeartbeatUtc).TotalMilliseconds >= HeartbeatEveryMs)
                    {
                        WriteHeartbeat(nowUtc);
                        _lastHeartbeatUtc = nowUtc;
                        Interlocked.Exchange(ref _ticksSinceHeartbeat, 0);
                    }

                    await Task.Delay(10, token).ConfigureAwait(false);
                }
                catch (OperationCanceledException) { break; }
                catch (Exception ex)
                {
                    LogLocalError("WriterLoop", ex);
                    try { await Task.Delay(250, token).ConfigureAwait(false); } catch { }
                }
            }

            // Final flush
            if (buffer.Count > 0)
            {
                try { await FlushAsync(buffer, CancellationToken.None).ConfigureAwait(false); }
                catch (Exception ex) { LogLocalError("WriterLoopFinalFlush", ex); }
            }
        }

        private async Task FlushAsync(List<TradeTick> batch, CancellationToken token)
        {
            if (batch == null || batch.Count == 0) return;

            // Group by partition (date / optional hour)
            // We will group by batch[0] time for directory semantics to match skeleton
            var firstTs = batch[0].TsUtc;
            var date = firstTs.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
            string outDir = PartitionByHour
                ? Path.Combine(OutputRoot, _resolvedSymbol, $"date={{date}}", firstTs.ToString("HH", CultureInfo.InvariantCulture))
                : Path.Combine(OutputRoot, _resolvedSymbol, $"date={{date}});

            Directory.CreateDirectory(outDir);

            var filePath = Path.Combine(outDir, "ticks.jsonl");
            var tempPath = filePath + ".part";

            // Write to .part (append). Use UTF8 without BOM.
            try
            {
                using (var fs = new FileStream(tempPath, FileMode.Append, FileAccess.Write, FileShare.Read, 1 << 16))
                using (var sw = new StreamWriter(fs, new UTF8Encoding(false)))
                {
                    foreach (var t in batch)
                    {
                        await sw.WriteLineAsync(t.ToJson()).ConfigureAwait(false);
                    }
                }

                // Atomic merge strategy
                if (!File.Exists(filePath))
                {
                    File.Move(tempPath, filePath);
                }
                else
                {
                    // append .part to destination then delete .part
                    using (var src = new FileStream(tempPath, FileMode.Open, FileAccess.Read, FileShare.Read))
                    using (var dst = new FileStream(filePath, FileMode.Append, FileAccess.Write, FileShare.Read))
                    {
                        await src.CopyToAsync(dst, 1 << 16, token).ConfigureAwait(false);
                    }
                    File.Delete(tempPath);
                }
            }
            catch (Exception ex)
            {
                LogLocalError("FlushAsync", ex);
            }
        }

        private void WriteHeartbeat(DateTime nowUtc)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_heartbeatPath)!);
                var lines = new[]
                {
                    $"ts_utc={{nowUtc.ToString("o", CultureInfo.InvariantCulture)}}",
                    $"symbol={{_resolvedSymbol}}",
                    $"ticks_in_window={{_ticksSinceHeartbeat}}"
                };
                File.WriteAllLines(_heartbeatPath, lines, new UTF8Encoding(false));
            }
            catch (Exception ex)
            {
                LogLocalError("WriteHeartbeat", ex);
            }
        }

        #endregion

        #region Helpers & models

        private string TryGetSymbolFromChart()
        {
            try
            {
                // Match approach used in SimplifiedDataExporter: attempt to read Symbol information from indicator context.
                // The exact API depends on ATAS; we provide a safe reflective fallback:
                try
                {
                    var property = GetType().GetProperty("Symbol");
                    if (property != null)
                    {
                        var v = property.GetValue(this);
                        if (v != null) return Convert.ToString(v, CultureInfo.InvariantCulture) ?? "";
                    }
                }
                catch { /* ignore reflection failures */ }
            }
            catch { /* ignore */ }

            return string.Empty;
        }

        private void LogLocalError(string where, Exception ex)
        {
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(LogPath)!);
                var line = $"[{{DateTime.UtcNow:o}}] {{where}}: {{ex}}{{Environment.NewLine}}";
                File.AppendAllText(LogPath, line, new UTF8Encoding(false));
            }
            catch { /* swallow */ }
        }

        private sealed class TradeTick
        {
            public DateTime TsUtc { get; set; }
            public string Exchange { get; set; } = "";
            public string Symbol { get; set; } = "";
            public double Price { get; set; }
            public double Qty { get; set; }
            public string Side { get; set; } = "";
            public double? BestBid { get; set; }
            public double? BestAsk { get; set; }
            public string? TradeId { get; set; }
            public string ExpVer { get; set; } = "";
            public string SchemaVer { get; set; } = "";

            public string ToJson()
            {
                // Lightweight manual JSON (no extra deps at runtime)
                var sb = new StringBuilder(256);
                sb.Append('{');
                sb.Append($"\"ts\":\"{{TsUtc.ToString("o", CultureInfo.InvariantCulture)}}\",);
                sb.Append($"\"exchange\":\"{{Escape(Exchange)}}\",);
                sb.Append($"\"symbol\":\"{{Escape(Symbol)}}\",);
                sb.Append($"\"price\":{{Price.ToString(CultureInfo.InvariantCulture)}},);
                sb.Append($"\"qty\":{{Qty.ToString(CultureInfo.InvariantCulture)}},);
                sb.Append($"\"side\":\"{{Escape(Side)}}\";
                if (BestBid.HasValue) sb.Append($",\"best_bid\":{{BestBid.Value.ToString(CultureInfo.InvariantCulture)}}");
                if (BestAsk.HasValue) sb.Append($",\"best_ask\":{{BestAsk.Value.ToString(CultureInfo.InvariantCulture)}}");
                if (!string.IsNullOrEmpty(TradeId)) sb.Append($",\"trade_id\":\"{{Escape(TradeId!)}}\";
                sb.Append($",\"exporter_version\":\"{{Escape(ExpVer)}}\";
                sb.Append($",\"schema_version\":\"{{Escape(SchemaVer)}}\";
                sb.Append('}');
                return sb.ToString();
            }

            private static string Escape(string s) => s.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        private static bool HasProperty(object? o, string prop)
        {
            if (o == null) return false;
            return o.GetType().GetProperty(prop) != null;
        }

        #endregion

        private void SafeShutdown()
        {
            try { _cts.Cancel(); } catch { }
            try { _writerTask?.Wait(1000); } catch { }
        }
    }
}