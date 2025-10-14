using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

namespace AtasCustomIndicators
{
    public class SimplifiedDataExporter : ATAS.Indicators.Indicator
    {
        private const string SchemaVersion = "v6.1";

        private readonly object _syncRoot = new();
        private readonly Queue<(DateTimeOffset Timestamp, double Delta)> _rollingWindow = new();
        private readonly Dictionary<DateTimeOffset, ExportPayload> _pendingByMinute = new();
        private readonly JsonSerializerSettings _serializerSettings;

        private double _cumulativeDelta;
        private bool _jsonIndent;
        private string _exportDir;
        private SessionModeDefinition _sessionModeDefinition;
        private DateTimeOffset? _lastProcessedMinuteUtc;
        private DateTimeOffset? _sessionAnchorUtc;

        public SimplifiedDataExporter()
        {
            Name = "SimplifiedDataExporter";

            _exportDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
                "ATAS",
                "Exports");

            SessionMode = "rolling:60";
            WriteOnBarCloseOnly = true;
            OutputTimezone = TimezoneOption.UTC;
            Backfill = false;
            JsonIndent = false;

            _serializerSettings = new JsonSerializerSettings
            {
                ContractResolver = new CamelCasePropertyNamesContractResolver(),
                FloatFormatHandling = FloatFormatHandling.Symbol,
                DateFormatString = "o"
            };

            EnsureExportDirectory();
        }

        [DisplayName("SessionMode")]
        [Description("Session reset strategy: rolling:Nmin or session")]
        public string SessionMode
        {
            get => _sessionModeDefinition.OriginalValue;
            set
            {
                _sessionModeDefinition = SessionModeDefinition.Parse(value);
                ResetSession();
            }
        }

        [DisplayName("WriteOnBarCloseOnly")]
        [Description("Write only once per completed bar (default true)")]
        public bool WriteOnBarCloseOnly { get; set; }

        [DisplayName("OutputTimezone")]
        [Description("Timestamp output timezone (UTC or Local)")]
        public TimezoneOption OutputTimezone { get; set; }

        [DisplayName("Backfill")]
        [Description("Indicates historical playback/backfill mode")]
        public bool Backfill { get; set; }

        [DisplayName("JsonIndent")]
        [Description("Pretty-print JSON output for debugging")]
        public bool JsonIndent
        {
            get => _jsonIndent;
            set
            {
                _jsonIndent = value;
                _serializerSettings.Formatting = _jsonIndent ? Formatting.Indented : Formatting.None;
            }
        }

        [DisplayName("ExportDir")]
        [Description("Directory for exported JSON artifacts")]
        public string ExportDir
        {
            get => _exportDir;
            set
            {
                if (string.IsNullOrWhiteSpace(value))
                {
                    return;
                }

                _exportDir = value;
                EnsureExportDirectory();
            }
        }

        private string ExporterVersion =>
            Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "0.0.0";

        protected override void OnCalculate(int bar, decimal value)
        {
            try
            {
                if (bar < 0)
                {
                    return;
                }

                if (WriteOnBarCloseOnly && bar != CurrentBar - 1 && !Backfill)
                {
                    return;
                }

                var candle = GetCandle(bar);
                if (candle == null)
                {
                    return;
                }

                var timestampUtc = ResolveUtcTimestamp(candle.Time);
                var minuteUtc = FloorToMinute(timestampUtc);
                var outputTimestamp = FormatTimestamp(minuteUtc);

                var poc = ExtractProfileValue(candle, "POC", "PointOfControl", "PriceOfControl");
                var vah = ExtractProfileValue(candle, "VAH", "ValueAreaHigh");
                var val = ExtractProfileValue(candle, "VAL", "ValueAreaLow");
                var delta = ExtractDelta(candle);
                var cvd = UpdateCvd(minuteUtc, delta);

                var absorption = ExtractAbsorption(candle, delta, (double)candle.Volume);

                var payload = new ExportPayload
                {
                    TimestampUtc = minuteUtc,
                    TimestampString = outputTimestamp,
                    Open = Convert.ToDouble(candle.Open, CultureInfo.InvariantCulture),
                    High = Convert.ToDouble(candle.High, CultureInfo.InvariantCulture),
                    Low = Convert.ToDouble(candle.Low, CultureInfo.InvariantCulture),
                    Close = Convert.ToDouble(candle.Close, CultureInfo.InvariantCulture),
                    Volume = Convert.ToDouble(candle.Volume, CultureInfo.InvariantCulture),
                    Poc = poc,
                    Vah = vah,
                    Val = val,
                    Cvd = cvd,
                    AbsorptionDetected = absorption.Detected,
                    AbsorptionStrength = absorption.Strength,
                    AbsorptionSide = absorption.Side
                };

                lock (_syncRoot)
                {
                    _pendingByMinute[minuteUtc] = payload;
                    FlushCompletedMinutes(minuteUtc);
                }
            }
            catch (Exception ex)
            {
                Log($"OnCalculate error: {ex}");
            }
        }

        private void FlushCompletedMinutes(DateTimeOffset currentMinuteUtc)
        {
            var minutesToFlush = _pendingByMinute.Keys
                .Where(minute => Backfill ? minute <= currentMinuteUtc : minute < currentMinuteUtc)
                .OrderBy(minute => minute)
                .ToList();

            foreach (var minute in minutesToFlush)
            {
                if (_pendingByMinute.TryGetValue(minute, out var payload))
                {
                    WritePayload(payload);
                    _pendingByMinute.Remove(minute);
                    _lastProcessedMinuteUtc = minute;
                }
            }
        }

        private void WritePayload(ExportPayload payload)
        {
            try
            {
                EnsureExportDirectory();

                var latestPath = Path.Combine(_exportDir, "latest.json");
                var dayFile = Path.Combine(_exportDir, $"market_data_{payload.TimestampUtc:yyyyMMdd}.jsonl");

                var document = new Dictionary<string, object?>
                {
                    ["timestamp"] = payload.TimestampString,
                    ["open"] = payload.Open,
                    ["high"] = payload.High,
                    ["low"] = payload.Low,
                    ["close"] = payload.Close,
                    ["volume"] = payload.Volume,
                    ["poc"] = payload.Poc,
                    ["vah"] = payload.Vah,
                    ["val"] = payload.Val,
                    ["cvd"] = payload.Cvd,
                    ["absorption_detected"] = payload.AbsorptionDetected,
                    ["absorption_strength"] = payload.AbsorptionStrength,
                    ["absorption_side"] = payload.AbsorptionSide ?? string.Empty,
                    ["exporter_version"] = ExporterVersion,
                    ["schema_version"] = SchemaVersion,
                    ["backfill"] = Backfill
                };

                var json = JsonConvert.SerializeObject(document, _serializerSettings);

                File.WriteAllText(latestPath, json);
                File.AppendAllText(dayFile, json + Environment.NewLine);
            }
            catch (Exception ex)
            {
                Log($"WritePayload error: {ex}");
            }
        }

        private DateTimeOffset ResolveUtcTimestamp(DateTime candleTime)
        {
            if (candleTime.Kind == DateTimeKind.Utc)
            {
                return new DateTimeOffset(candleTime, TimeSpan.Zero);
            }

            var localTime = candleTime.Kind switch
            {
                DateTimeKind.Local => candleTime,
                DateTimeKind.Unspecified => DateTime.SpecifyKind(candleTime, DateTimeKind.Local),
                _ => candleTime.ToLocalTime()
            };

            return new DateTimeOffset(localTime.ToUniversalTime(), TimeSpan.Zero);
        }

        private string FormatTimestamp(DateTimeOffset minuteUtc)
        {
            var target = OutputTimezone == TimezoneOption.UTC
                ? minuteUtc.ToUniversalTime()
                : minuteUtc.ToLocalTime();

            return target.ToString("o", CultureInfo.InvariantCulture);
        }

        private static DateTimeOffset FloorToMinute(DateTimeOffset value)
        {
            return new DateTimeOffset(
                value.Year,
                value.Month,
                value.Day,
                value.Hour,
                value.Minute,
                0,
                TimeSpan.Zero);
        }

        private double? ExtractProfileValue(object candle, params string[] propertyNames)
        {
            try
            {
                foreach (var propertyName in propertyNames)
                {
                    var property = candle.GetType().GetProperty(propertyName);
                    if (property != null)
                    {
                        var result = property.GetValue(candle);
                        if (TryConvertToDouble(result, out var numeric))
                        {
                            return numeric;
                        }
                    }
                }

                var profileProperty = candle.GetType().GetProperty("Profile");
                if (profileProperty != null)
                {
                    var profile = profileProperty.GetValue(candle);
                    if (profile != null)
                    {
                        foreach (var propertyName in propertyNames)
                        {
                            var property = profile.GetType().GetProperty(propertyName);
                            if (property != null)
                            {
                                var result = property.GetValue(profile);
                                if (TryConvertToDouble(result, out var numeric))
                                {
                                    return numeric;
                                }
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"ExtractProfileValue error: {ex.Message}");
            }

            return double.NaN;
        }

        private static bool TryConvertToDouble(object? input, out double result)
        {
            switch (input)
            {
                case null:
                    result = double.NaN;
                    return false;
                case double d when !double.IsNaN(d):
                    result = d;
                    return true;
                case float f when !float.IsNaN(f):
                    result = f;
                    return true;
                case decimal dec:
                    result = Convert.ToDouble(dec, CultureInfo.InvariantCulture);
                    return true;
                case IConvertible convertible:
                    try
                    {
                        result = convertible.ToDouble(CultureInfo.InvariantCulture);
                        return true;
                    }
                    catch
                    {
                        break;
                    }
                    break;
            }

            if (double.TryParse(Convert.ToString(input, CultureInfo.InvariantCulture), NumberStyles.Any, CultureInfo.InvariantCulture, out var parsed))
            {
                result = parsed;
                return true;
            }

            result = double.NaN;
            return false;
        }

        private double? ExtractDelta(object candle)
        {
            try
            {
                var deltaProperties = new[] { "Delta", "CumulativeDelta", "DeltaVolume" };
                foreach (var name in deltaProperties)
                {
                    var property = candle.GetType().GetProperty(name);
                    if (property != null)
                    {
                        var raw = property.GetValue(candle);
                        if (TryConvertToDouble(raw, out var value))
                        {
                            return value;
                        }
                    }
                }

                var buyVolume = ExtractVolumeSide(candle, "BuyVolume", "AskVolume", "UpVolume");
                var sellVolume = ExtractVolumeSide(candle, "SellVolume", "BidVolume", "DownVolume");

                if (buyVolume.HasValue && sellVolume.HasValue)
                {
                    return buyVolume.Value - sellVolume.Value;
                }
            }
            catch (Exception ex)
            {
                Log($"ExtractDelta error: {ex.Message}");
            }

            return null;
        }

        private double? ExtractVolumeSide(object candle, params string[] propertyNames)
        {
            foreach (var name in propertyNames)
            {
                var property = candle.GetType().GetProperty(name);
                if (property != null)
                {
                    var value = property.GetValue(candle);
                    if (TryConvertToDouble(value, out var numeric))
                    {
                        return numeric;
                    }
                }
            }

            return null;
        }

        private double UpdateCvd(DateTimeOffset minuteUtc, double? delta)
        {
            if (_sessionModeDefinition.Mode == SessionModeKind.Session)
            {
                if (_sessionAnchorUtc == null || (_lastProcessedMinuteUtc.HasValue && minuteUtc < _lastProcessedMinuteUtc.Value))
                {
                    _cumulativeDelta = 0.0;
                    _sessionAnchorUtc = minuteUtc;
                }

                if (delta.HasValue)
                {
                    _cumulativeDelta += delta.Value;
                    return _cumulativeDelta;
                }

                return double.NaN;
            }

            if (_sessionModeDefinition.Mode == SessionModeKind.Rolling)
            {
                if (delta.HasValue)
                {
                    _rollingWindow.Enqueue((minuteUtc, delta.Value));
                    _cumulativeDelta += delta.Value;
                }

                var boundary = minuteUtc - _sessionModeDefinition.RollingWindow;
                while (_rollingWindow.Count > 0 && _rollingWindow.Peek().Timestamp < boundary)
                {
                    var item = _rollingWindow.Dequeue();
                    _cumulativeDelta -= item.Delta;
                }

                return delta.HasValue ? _cumulativeDelta : double.NaN;
            }

            return double.NaN;
        }

        private AbsorptionResult ExtractAbsorption(object candle, double? delta, double totalVolume)
        {
            try
            {
                var absorptionProperty = candle.GetType().GetProperty("Absorption");
                if (absorptionProperty != null)
                {
                    var absorption = absorptionProperty.GetValue(candle);
                    if (absorption != null)
                    {
                        var detected = ExtractBoolean(absorption, "Detected", "IsAbsorption", "Triggered");
                        var strength = ExtractNumeric(absorption, "Strength", "Score", "Volume");
                        var side = ExtractString(absorption, "Side", "Direction", "Type");

                        return new AbsorptionResult(
                            detected ?? false,
                            strength ?? double.NaN,
                            side ?? string.Empty);
                    }
                }

                if (totalVolume <= double.Epsilon)
                {
                    return new AbsorptionResult(false, double.NaN, string.Empty);
                }

                if (delta.HasValue)
                {
                    var imbalance = 1.0 - Math.Min(1.0, Math.Abs(delta.Value) / Math.Max(totalVolume, 1e-9));
                    var detected = imbalance > 0.6 && totalVolume > 0.0;
                    var side = delta.Value > 0 ? "buy" : delta.Value < 0 ? "sell" : string.Empty;
                    var strength = detected ? imbalance : double.NaN;
                    return new AbsorptionResult(detected, strength, side);
                }
            }
            catch (Exception ex)
            {
                Log($"ExtractAbsorption error: {ex.Message}");
            }

            return new AbsorptionResult(false, double.NaN, string.Empty);
        }

        private static bool? ExtractBoolean(object source, params string[] propertyNames)
        {
            foreach (var name in propertyNames)
            {
                var property = source.GetType().GetProperty(name);
                if (property != null)
                {
                    var value = property.GetValue(source);
                    if (value is bool boolean)
                    {
                        return boolean;
                    }

                    if (value is IConvertible convertible)
                    {
                        try
                        {
                            return convertible.ToBoolean(CultureInfo.InvariantCulture);
                        }
                        catch
                        {
                        }
                    }
                }
            }

            return null;
        }

        private static double? ExtractNumeric(object source, params string[] propertyNames)
        {
            foreach (var name in propertyNames)
            {
                var property = source.GetType().GetProperty(name);
                if (property != null)
                {
                    var value = property.GetValue(source);
                    if (TryConvertToDouble(value, out var numeric))
                    {
                        return numeric;
                    }
                }
            }

            return null;
        }

        private static string? ExtractString(object source, params string[] propertyNames)
        {
            foreach (var name in propertyNames)
            {
                var property = source.GetType().GetProperty(name);
                if (property != null)
                {
                    var value = property.GetValue(source);
                    if (value != null)
                    {
                        return Convert.ToString(value, CultureInfo.InvariantCulture);
                    }
                }
            }

            return null;
        }

        private void ResetSession()
        {
            lock (_syncRoot)
            {
                _cumulativeDelta = 0.0;
                _rollingWindow.Clear();
                _pendingByMinute.Clear();
                _sessionAnchorUtc = null;
                _lastProcessedMinuteUtc = null;
            }
        }

        private void EnsureExportDirectory()
        {
            if (string.IsNullOrWhiteSpace(_exportDir))
            {
                return;
            }

            try
            {
                Directory.CreateDirectory(_exportDir);
            }
            catch (Exception ex)
            {
                Log($"EnsureExportDirectory error: {ex.Message}");
            }
        }

        private void Log(string message)
        {
            try
            {
                EnsureExportDirectory();
                var logPath = Path.Combine(_exportDir, $"exporter_{DateTime.UtcNow:yyyyMMdd}.log");
                File.AppendAllText(logPath, $"{DateTime.UtcNow:o} {message}{Environment.NewLine}");
            }
            catch
            {
                // suppress logging failures
            }
        }
    }

    public enum TimezoneOption
    {
        UTC,
        Local
    }

    internal enum SessionModeKind
    {
        Rolling,
        Session
    }

    internal readonly struct SessionModeDefinition
    {
        public SessionModeDefinition(SessionModeKind mode, TimeSpan rollingWindow, string original)
        {
            Mode = mode;
            RollingWindow = rollingWindow;
            OriginalValue = original;
        }

        public SessionModeKind Mode { get; }
        public TimeSpan RollingWindow { get; }
        public string OriginalValue { get; }

        public static SessionModeDefinition Parse(string? raw)
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                return new SessionModeDefinition(SessionModeKind.Rolling, TimeSpan.FromMinutes(60), "rolling:60");
            }

            var text = raw.Trim();
            if (text.StartsWith("rolling", StringComparison.OrdinalIgnoreCase))
            {
                var parts = text.Split(':');
                if (parts.Length == 2 && int.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out var minutes) && minutes > 0)
                {
                    return new SessionModeDefinition(SessionModeKind.Rolling, TimeSpan.FromMinutes(minutes), text);
                }

                return new SessionModeDefinition(SessionModeKind.Rolling, TimeSpan.FromMinutes(60), text);
            }

            if (string.Equals(text, "session", StringComparison.OrdinalIgnoreCase))
            {
                return new SessionModeDefinition(SessionModeKind.Session, TimeSpan.Zero, text);
            }

            return new SessionModeDefinition(SessionModeKind.Rolling, TimeSpan.FromMinutes(60), text);
        }
    }

    internal sealed class ExportPayload
    {
        public DateTimeOffset TimestampUtc { get; set; }
        public string TimestampString { get; set; } = string.Empty;
        public double Open { get; set; }
        public double High { get; set; }
        public double Low { get; set; }
        public double Close { get; set; }
        public double Volume { get; set; }
        public double? Poc { get; set; }
        public double? Vah { get; set; }
        public double? Val { get; set; }
        public double Cvd { get; set; }
        public bool AbsorptionDetected { get; set; }
        public double AbsorptionStrength { get; set; }
        public string? AbsorptionSide { get; set; }
    }

    internal readonly struct AbsorptionResult
    {
        public AbsorptionResult(bool detected, double strength, string side)
        {
            Detected = detected;
            Strength = strength;
            Side = side;
        }

        public bool Detected { get; }
        public double Strength { get; }
        public string Side { get; }
    }
}
