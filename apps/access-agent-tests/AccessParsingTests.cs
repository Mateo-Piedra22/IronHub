using IronHub.AccessAgent;
using Xunit;

namespace IronHub.AccessAgentTests;

public sealed class AccessParsingTests
{
    [Fact]
    public void RegexProtocol_ExtractsGroup1()
    {
        var v = AccessParsing.Apply("UID=04A1B2C3D4", "regex", "UID=(\\w+)", "auto", "auto", 40);
        Assert.Equal("04A1B2C3D4", v);
    }

    [Fact]
    public void Em4100_DecimalToDecimal_PreservesValue()
    {
        var v = AccessParsing.Apply("1234567890", "em4100", "", "dec", "be", 40);
        Assert.Equal("1234567890", v);
    }

    [Fact]
    public void Em4100_HexToHex_PadsTo40Bits()
    {
        var v = AccessParsing.Apply("0x1A2B3C", "em4100", "", "hex", "be", 40);
        Assert.Equal("00001A2B3C", v);
    }

    [Fact]
    public void Em4100_HexToHex_Allows80Bits()
    {
        var v = AccessParsing.Apply("0x112233445566778899AA", "em4100", "", "hex", "be", 80);
        Assert.Equal("112233445566778899AA", v);
    }

    [Fact]
    public void DataProtocol_KeepsDigitsOnly()
    {
        var v = AccessParsing.Apply("AB12-34 CD", "data", "", "auto", "auto", 40);
        Assert.Equal("1234", v);
    }
}
