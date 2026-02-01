using System;
using System.IO.Ports;
using System.Net.Http;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace IronHub.AccessAgent;

public static class OutputAdapters
{
    public static async Task<int> HttpGetAsync(HttpClient http, string url, CancellationToken ct)
    {
        var res = await http.GetAsync(url, ct);
        return (int)res.StatusCode;
    }

    public static async Task<int> HttpPostJsonAsync(HttpClient http, string url, object body, CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(body);
        var res = await http.PostAsync(url, new StringContent(json, Encoding.UTF8, "application/json"), ct);
        return (int)res.StatusCode;
    }

    public static async Task TcpSendAsync(string host, int port, byte[] payload, CancellationToken ct)
    {
        using var tcp = new TcpClient();
        await tcp.ConnectAsync(host, port, ct);
        if (payload.Length > 0)
        {
            await tcp.GetStream().WriteAsync(payload, 0, payload.Length, ct);
        }
    }

    public static void SerialSend(string port, int baud, byte[] payload)
    {
        using var sp = new SerialPort(port, baud);
        sp.Open();
        if (payload.Length > 0) sp.Write(payload, 0, payload.Length);
        sp.Close();
    }

    public static void SerialSend(string port, int baud, string payloadText)
    {
        using var sp = new SerialPort(port, baud);
        sp.Open();
        var cmd = ParseSerialCommand(payloadText);
        if (cmd.dtr_pulse_ms > 0)
        {
            sp.DtrEnable = true;
            Thread.Sleep(cmd.dtr_pulse_ms);
            sp.DtrEnable = false;
        }
        if (cmd.rts_pulse_ms > 0)
        {
            sp.RtsEnable = true;
            Thread.Sleep(cmd.rts_pulse_ms);
            sp.RtsEnable = false;
        }
        if (cmd.break_ms > 0)
        {
            sp.BreakState = true;
            Thread.Sleep(cmd.break_ms);
            sp.BreakState = false;
        }
        if (cmd.bytes.Length > 0)
        {
            sp.Write(cmd.bytes, 0, cmd.bytes.Length);
        }
        sp.Close();
    }

    public static byte[] ParsePayloadBytes(string payload)
    {
        var s = (payload ?? "").Trim();
        if (string.IsNullOrWhiteSpace(s)) return Array.Empty<byte>();
        try
        {
            var parts = s.Split(new[] { ' ', '\t', '\r', '\n', ',', ';' }, StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            var allHex = true;
            foreach (var p in parts)
            {
                var t = p.StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? p[2..] : p;
                if (t.Length == 0 || t.Length > 2) { allHex = false; break; }
                foreach (var ch in t)
                {
                    if (!Uri.IsHexDigit(ch)) { allHex = false; break; }
                }
                if (!allHex) break;
            }
            if (allHex && parts.Length > 0)
            {
                var buf = new byte[parts.Length];
                for (var i = 0; i < parts.Length; i++)
                {
                    var t = parts[i].StartsWith("0x", StringComparison.OrdinalIgnoreCase) ? parts[i][2..] : parts[i];
                    buf[i] = Convert.ToByte(t, 16);
                }
                return buf;
            }
        }
        catch
        {
        }
        return Encoding.UTF8.GetBytes(s);
    }

    private sealed class SerialCommand
    {
        public int dtr_pulse_ms { get; set; }
        public int rts_pulse_ms { get; set; }
        public int break_ms { get; set; }
        public byte[] bytes { get; set; } = Array.Empty<byte>();
    }

    private static SerialCommand ParseSerialCommand(string payloadText)
    {
        var s = (payloadText ?? "").Trim();
        var cmd = new SerialCommand();
        if (string.IsNullOrWhiteSpace(s)) return cmd;
        var upper = s.ToUpperInvariant();
        if (upper.StartsWith("DTR_PULSE:", StringComparison.Ordinal) || upper.StartsWith("DTR_PULSE=", StringComparison.Ordinal))
        {
            var v = s[(s.IndexOfAny(new[] { ':', '=' }) + 1)..].Trim();
            if (int.TryParse(v, out var ms)) cmd.dtr_pulse_ms = Math.Clamp(ms, 1, 15000);
            return cmd;
        }
        if (upper.StartsWith("RTS_PULSE:", StringComparison.Ordinal) || upper.StartsWith("RTS_PULSE=", StringComparison.Ordinal))
        {
            var v = s[(s.IndexOfAny(new[] { ':', '=' }) + 1)..].Trim();
            if (int.TryParse(v, out var ms)) cmd.rts_pulse_ms = Math.Clamp(ms, 1, 15000);
            return cmd;
        }
        if (upper.StartsWith("BREAK:", StringComparison.Ordinal) || upper.StartsWith("BREAK=", StringComparison.Ordinal))
        {
            var v = s[(s.IndexOfAny(new[] { ':', '=' }) + 1)..].Trim();
            if (int.TryParse(v, out var ms)) cmd.break_ms = Math.Clamp(ms, 1, 15000);
            return cmd;
        }
        cmd.bytes = ParsePayloadBytes(s);
        return cmd;
    }
}
