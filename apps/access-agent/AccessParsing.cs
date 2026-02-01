using System;
using System.Globalization;
using System.Numerics;
using System.Text;
using System.Text.RegularExpressions;

namespace IronHub.AccessAgent;

public static class AccessParsing
{
    public static string Apply(string raw, string protocol, string regexPattern, string uidFormat, string uidEndian, int uidBits)
    {
        var s = (raw ?? "").Trim();
        var proto = (protocol ?? "raw").Trim().ToLowerInvariant();
        if (proto == "data")
        {
            var b = new StringBuilder();
            foreach (var ch in s) if (char.IsDigit(ch)) b.Append(ch);
            return b.ToString();
        }
        if (proto is "drt" or "str")
        {
            var idx = s.LastIndexOf(':');
            if (idx >= 0 && idx < s.Length - 1) return s[(idx + 1)..].Trim();
            idx = s.LastIndexOf('|');
            if (idx >= 0 && idx < s.Length - 1) return s[(idx + 1)..].Trim();
            return s;
        }
        if (proto == "regex")
        {
            var pat = (regexPattern ?? "").Trim();
            if (string.IsNullOrWhiteSpace(pat)) return s;
            try
            {
                var m = Regex.Match(s, pat);
                if (!m.Success) return "";
                if (m.Groups.Count >= 2) return m.Groups[1].Value.Trim();
                return m.Value.Trim();
            }
            catch
            {
                return s;
            }
        }
        if (proto == "em4100")
        {
            return NormalizeEm4100(s, uidFormat, uidEndian, uidBits);
        }
        return s;
    }

    public static string NormalizeEm4100(string s, string uidFormat, string uidEndian, int uidBits)
    {
        var raw = (s ?? "").Trim();
        if (string.IsNullOrWhiteSpace(raw)) return "";

        var cleaned = new StringBuilder();
        foreach (var ch in raw)
        {
            if (char.IsDigit(ch)) cleaned.Append(ch);
            else if (ch is >= 'a' and <= 'f') cleaned.Append(char.ToUpperInvariant(ch));
            else if (ch is >= 'A' and <= 'F') cleaned.Append(ch);
        }
        var token = cleaned.ToString();
        if (string.IsNullOrWhiteSpace(token)) return "";

        var fmt = (uidFormat ?? "auto").Trim().ToLowerInvariant();
        var endian = (uidEndian ?? "auto").Trim().ToLowerInvariant();
        var bits = Math.Clamp(uidBits <= 0 ? 40 : uidBits, 16, 128);
        var hexDigits = (bits + 3) / 4;
        var bytesLen = (bits + 7) / 8;

        var isDecOnly = true;
        foreach (var ch in token)
        {
            if (!char.IsDigit(ch)) { isDecOnly = false; break; }
        }

        var baseDetected = "hex";
        if (fmt == "dec") baseDetected = "dec";
        else if (fmt == "hex") baseDetected = "hex";
        else baseDetected = isDecOnly ? "dec" : "hex";

        BigInteger value;
        try
        {
            if (baseDetected == "dec")
            {
                value = BigInteger.Parse(token, NumberStyles.None, CultureInfo.InvariantCulture);
            }
            else
            {
                var t = token.StartsWith("0X", StringComparison.OrdinalIgnoreCase) ? token[2..] : token;
                value = BigInteger.Parse("0" + t, NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture);
            }
        }
        catch
        {
            return "";
        }

        if (endian == "le")
        {
            var be = value.ToByteArray(isUnsigned: true, isBigEndian: true);
            var fixedBe = new byte[bytesLen];
            var take = Math.Min(be.Length, bytesLen);
            Array.Copy(be, be.Length - take, fixedBe, bytesLen - take, take);
            Array.Reverse(fixedBe);
            value = new BigInteger(fixedBe, isUnsigned: true, isBigEndian: true);
        }
        else if (endian == "be" || endian == "auto")
        {
        }
        else
        {
            endian = "auto";
        }

        var mask = (BigInteger.One << bits) - BigInteger.One;
        value &= mask;

        if (fmt == "dec")
        {
            return value.ToString(CultureInfo.InvariantCulture);
        }
        if (fmt == "hex")
        {
            return value.ToString("X", CultureInfo.InvariantCulture).PadLeft(hexDigits, '0');
        }
        if (baseDetected == "dec")
        {
            return value.ToString(CultureInfo.InvariantCulture);
        }
        return value.ToString("X", CultureInfo.InvariantCulture).PadLeft(hexDigits, '0');
    }
}
