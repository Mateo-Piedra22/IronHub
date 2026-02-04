using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace IronHub.AccessAgent;

public sealed class OfflineEventQueue
{
    private readonly object _lock = new();
    private readonly string _queuePath;
    private readonly ILineProtector _protector;

    public OfflineEventQueue(string queuePath, ILineProtector protector)
    {
        _queuePath = queuePath ?? throw new ArgumentNullException(nameof(queuePath));
        _protector = protector ?? throw new ArgumentNullException(nameof(protector));
    }

    public void Enqueue(string nonce, string bodyJson, DateTimeOffset? createdAtUtc = null, int maxLines = 2000)
    {
        if (string.IsNullOrWhiteSpace(nonce)) return;
        if (string.IsNullOrWhiteSpace(bodyJson)) return;
        try
        {
            var lineObj = new QueuedEvent
            {
                nonce = nonce,
                body = bodyJson,
                created_at = (createdAtUtc ?? DateTimeOffset.UtcNow).ToString("O")
            };
            var plain = JsonSerializer.Serialize(lineObj);
            var line = _protector.Protect(plain);
            lock (_lock)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_queuePath)!);
                File.AppendAllText(_queuePath, line + Environment.NewLine, Encoding.UTF8);
                TrimIfNeededLocked(maxLines);
            }
        }
        catch
        {
        }
    }

    public (int lines, long bytes, bool truncated)? GetStats(int maxLinesToCount = 5000)
    {
        try
        {
            lock (_lock)
            {
                if (string.IsNullOrWhiteSpace(_queuePath)) return null;
                if (!File.Exists(_queuePath)) return null;
            }
            long bytes = 0;
            try { bytes = new FileInfo(_queuePath).Length; } catch { bytes = 0; }

            var lines = 0;
            var truncated = false;
            using var fs = new FileStream(_queuePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var sr = new StreamReader(fs, Encoding.UTF8);
            while (!sr.EndOfStream && lines < maxLinesToCount)
            {
                sr.ReadLine();
                lines++;
            }
            if (!sr.EndOfStream) truncated = true;
            return (lines, bytes, truncated);
        }
        catch
        {
            return null;
        }
    }

    public string[] ReadAllLines()
    {
        lock (_lock)
        {
            try
            {
                if (!File.Exists(_queuePath)) return Array.Empty<string>();
                return File.ReadAllLines(_queuePath, Encoding.UTF8);
            }
            catch
            {
                return Array.Empty<string>();
            }
        }
    }

    public void RewriteLines(IReadOnlyList<string> lines)
    {
        lock (_lock)
        {
            try
            {
                if (lines == null || lines.Count == 0)
                {
                    try { File.Delete(_queuePath); } catch { }
                    return;
                }
                File.WriteAllLines(_queuePath, lines, Encoding.UTF8);
            }
            catch
            {
            }
        }
    }

    public bool TryDecodeLine(string line, out string nonce, out string bodyJson)
    {
        nonce = "";
        bodyJson = "";
        if (string.IsNullOrWhiteSpace(line)) return false;
        string plain;
        if (!_protector.TryUnprotect(line, out plain))
        {
            plain = line;
        }
        try
        {
            var ev = JsonSerializer.Deserialize<QueuedEvent>(plain);
            if (ev == null) return false;
            if (string.IsNullOrWhiteSpace(ev.nonce) || string.IsNullOrWhiteSpace(ev.body)) return false;
            nonce = ev.nonce;
            bodyJson = ev.body;
            return true;
        }
        catch
        {
            return false;
        }
    }

    public void TrimIfNeeded(int maxLines)
    {
        lock (_lock)
        {
            TrimIfNeededLocked(maxLines);
        }
    }

    private void TrimIfNeededLocked(int maxLines)
    {
        try
        {
            var max = Math.Max(100, Math.Min(maxLines, 20000));
            if (!File.Exists(_queuePath)) return;
            var lines = File.ReadAllLines(_queuePath, Encoding.UTF8);
            if (lines.Length <= max) return;
            var keep = lines[^max..];
            File.WriteAllLines(_queuePath, keep, Encoding.UTF8);
        }
        catch
        {
        }
    }

    public sealed class QueuedEvent
    {
        public string nonce { get; set; } = "";
        public string body { get; set; } = "";
        public string created_at { get; set; } = "";
    }

    public interface ILineProtector
    {
        string Protect(string plain);
        bool TryUnprotect(string protectedLine, out string plain);
    }

    public sealed class NoopLineProtector : ILineProtector
    {
        public string Protect(string plain) => plain ?? "";
        public bool TryUnprotect(string protectedLine, out string plain)
        {
            plain = protectedLine ?? "";
            return true;
        }
    }

    public sealed class DpapiLineProtector : ILineProtector
    {
        private const string Prefix = "enc1:";

        public string Protect(string plain)
        {
            try
            {
                var bytes = Encoding.UTF8.GetBytes(plain ?? "");
                var enc = ProtectedData.Protect(bytes, null, DataProtectionScope.CurrentUser);
                return Prefix + Convert.ToBase64String(enc);
            }
            catch
            {
                return plain ?? "";
            }
        }

        public bool TryUnprotect(string protectedLine, out string plain)
        {
            plain = "";
            try
            {
                var s = (protectedLine ?? "").Trim();
                if (!s.StartsWith(Prefix, StringComparison.Ordinal)) return false;
                var b64 = s.Substring(Prefix.Length);
                var enc = Convert.FromBase64String(b64);
                var bytes = ProtectedData.Unprotect(enc, null, DataProtectionScope.CurrentUser);
                plain = Encoding.UTF8.GetString(bytes);
                return true;
            }
            catch
            {
                plain = "";
                return false;
            }
        }
    }
}

