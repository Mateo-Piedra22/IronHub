using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace IronHub.AccessAgent;

public sealed class RollingFileLog
{
    private readonly object _lock = new();
    private readonly string _path;
    private readonly long _maxBytes;

    public RollingFileLog(string path, long maxBytes = 524288)
    {
        _path = path ?? throw new ArgumentNullException(nameof(path));
        _maxBytes = Math.Max(65536, maxBytes);
    }

    public void Append(string message)
    {
        try
        {
            var line = $"{DateTimeOffset.Now:O} {message}".TrimEnd();
            lock (_lock)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_path)!);
                File.AppendAllText(_path, line + Environment.NewLine, Encoding.UTF8);
                RotateIfNeededLocked();
            }
        }
        catch
        {
        }
    }

    public string Tail(int maxLines = 200)
    {
        maxLines = Math.Clamp(maxLines, 1, 2000);
        try
        {
            lock (_lock)
            {
                if (!File.Exists(_path)) return "";
                var lines = File.ReadAllLines(_path, Encoding.UTF8);
                if (lines.Length == 0) return "";
                var take = Math.Min(lines.Length, maxLines);
                var slice = lines[^take..];
                return string.Join(Environment.NewLine, slice);
            }
        }
        catch
        {
            return "";
        }
    }

    private void RotateIfNeededLocked()
    {
        try
        {
            if (!File.Exists(_path)) return;
            var fi = new FileInfo(_path);
            if (fi.Length <= _maxBytes) return;

            var backup = _path + ".1";
            try { if (File.Exists(backup)) File.Delete(backup); } catch { }
            try { File.Move(_path, backup); } catch { }
        }
        catch
        {
        }
    }
}

