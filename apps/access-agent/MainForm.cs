using System;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using System.Security.Cryptography;
using System.Reflection;
using System.Linq;
using System.Windows.Forms;
using System.IO.Ports;

namespace IronHub.AccessAgent;

public sealed class MainForm : Form
{
    private readonly HttpClient _http = new();
    private readonly TextBox _capture = new();
    private readonly Label _status = new();
    private readonly Label _statusDetail = new();
    private readonly Label _last = new();
    private readonly Label _io = new();
    private readonly Panel _display = new();
    private readonly Panel _historyPanel = new();
    private readonly ListView _history = new();
    private readonly Label _historyTitle = new();
    private readonly Label _dispDecision = new();
    private readonly Label _dispUser = new();
    private readonly Label _dispMembership = new();
    private readonly Label _dispReason = new();
    private readonly Label _dispAction = new();
    private readonly Label _dispInput = new();
    private readonly Label _dispMeta = new();
    private readonly Button _configBtn = new();
    private readonly Button _runBtn = new();
    private readonly Button _clearQueueBtn = new();
    private readonly Button _pairBtn = new();
    private readonly Button _pastePairBtn = new();
    private readonly Button _validateBtn = new();
    private readonly TextBox _tenant = new();
    private readonly TextBox _baseUrl = new();
    private readonly TextBox _deviceId = new();
    private readonly TextBox _pairing = new();
    private readonly TextBox _unlockUrl = new();
    private readonly NumericUpDown _unlockMs = new();
    private readonly ComboBox _unlockMethod = new();
    private readonly ComboBox _unlockPreset = new();
    private readonly Button _unlockPresetApplyBtn = new();
    private readonly TextBox _unlockTcpHost = new();
    private readonly NumericUpDown _unlockTcpPort = new();
    private readonly TextBox _unlockTcpPayload = new();
    private readonly ComboBox _unlockSerialPort = new();
    private readonly NumericUpDown _unlockSerialBaud = new();
    private readonly TextBox _unlockSerialPayload = new();
    private readonly ComboBox _accessMode = new();
    private readonly CheckBox _allowManual = new();
    private readonly TextBox _manualHotkey = new();
    private readonly ComboBox _inputSource = new();
    private readonly ComboBox _inputProtocol = new();
    private readonly ComboBox _serialPort = new();
    private readonly NumericUpDown _serialBaud = new();
    private readonly TextBox _inputRegex = new();
    private readonly ComboBox _uidFormat = new();
    private readonly ComboBox _uidEndian = new();
    private readonly NumericUpDown _uidBits = new();
    private readonly ComboBox _captureSubmitKey = new();
    private readonly NumericUpDown _captureIdleMs = new();
    private readonly CheckBox _remoteCmds = new();
    private readonly NumericUpDown _remotePollMs = new();
    private readonly Button _refreshPortsBtn = new();
    private readonly TextBox _testGetUrl = new();
    private readonly TextBox _testPostUrl = new();
    private readonly TextBox _testTcpHost = new();
    private readonly NumericUpDown _testTcpPort = new();
    private readonly TextBox _testTcpPayload = new();
    private readonly ComboBox _testSerialPort = new();
    private readonly NumericUpDown _testSerialBaud = new();
    private readonly TextBox _testSerialPayload = new();
    private readonly Button _testGetBtn = new();
    private readonly Button _testPostBtn = new();
    private readonly Button _testTcpBtn = new();
    private readonly Button _testSerialBtn = new();
    private readonly Button _testAllBtn = new();
    private readonly Button _testApiBtn = new();
    private readonly Button _testModeActionBtn = new();
    private readonly CheckBox _fullscreen = new();
    private readonly CancellationTokenSource _cts = new();
    private readonly System.Windows.Forms.Timer _deviceConfigTimer = new();
    private readonly System.Windows.Forms.Timer _flushQueueTimer = new();
    private readonly System.Windows.Forms.Timer _captureIdleTimer = new();
    private readonly System.Windows.Forms.Timer _commandPollTimer = new();
    private readonly System.Windows.Forms.Timer _portsRefreshTimer = new();
    private readonly string _queuePath;
    private readonly OfflineEventQueue _offlineQueue;
    private readonly RollingFileLog _log;
    private SerialPort? _serial;
    private readonly StringBuilder _serialBuf = new();
    private bool _pollingCommands;
    private DateTimeOffset? _blockedUntilUtc;
    private DateTimeOffset? _apiBackoffUntilUtc;
    private DateTimeOffset? _apiCircuitUntilUtc;
    private int _apiFailCount;
    private readonly Random _rng = new();
    private readonly ToolTip _tips = new();
    private bool _running = true;
    private DateTimeOffset? _lastApiOkUtc;
    private string _lastApiError = "";
    private DateTimeOffset? _lastScanAtUtc;
    private readonly System.Windows.Forms.Timer _displayResetTimer = new();
    private readonly object _submitLock = new();
    private DateTimeOffset? _lastSubmitAtUtc;
    private string _lastSubmitKey = "";

    private AgentConfig _cfg;
    private bool _configOpen;

    public MainForm()
    {
        Text = "IronHub Access Agent";
        Width = 1060;
        Height = 600;
        MinimumSize = new System.Drawing.Size(920, 560);
        StartPosition = FormStartPosition.CenterScreen;
        KeyPreview = true;

        _cfg = AgentConfig.Load();
        _queuePath = Path.Combine(AgentConfig.ConfigDir(), "events.ndjson");
        _offlineQueue = new OfflineEventQueue(_queuePath, new OfflineEventQueue.DpapiLineProtector());
        _log = new RollingFileLog(Path.Combine(AgentConfig.ConfigDir(), "agent.log"));
        _log.Append("agent_start");

        _status.AutoSize = true;
        _status.Top = 16;
        _status.Left = 16;
        _status.Font = new System.Drawing.Font("Segoe UI", 12, System.Drawing.FontStyle.Bold);
        Controls.Add(_status);

        _statusDetail.AutoSize = true;
        _statusDetail.Top = 38;
        _statusDetail.Left = 16;
        _statusDetail.Width = 760;
        _statusDetail.Text = "";
        Controls.Add(_statusDetail);

        _last.AutoSize = true;
        _last.Top = 60;
        _last.Left = 16;
        _last.Width = 760;
        Controls.Add(_last);

        _io.AutoSize = true;
        _io.Top = 82;
        _io.Left = 16;
        _io.Width = 760;
        Controls.Add(_io);

        _display.Left = 16;
        _display.Top = 110;
        _display.Width = 610;
        _display.Height = 380;
        _display.BorderStyle = BorderStyle.FixedSingle;
        _display.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Bottom | AnchorStyles.Right;
        Controls.Add(_display);

        _dispDecision.Left = 16;
        _dispDecision.Top = 18;
        _dispDecision.Width = 560;
        _dispDecision.Height = 44;
        _dispDecision.Font = new System.Drawing.Font("Segoe UI", 18, System.Drawing.FontStyle.Bold);
        _display.Controls.Add(_dispDecision);

        _dispUser.Left = 16;
        _dispUser.Top = 74;
        _dispUser.Width = 560;
        _dispUser.Height = 26;
        _dispUser.Font = new System.Drawing.Font("Segoe UI", 13, System.Drawing.FontStyle.Bold);
        _display.Controls.Add(_dispUser);

        _dispMembership.Left = 16;
        _dispMembership.Top = 104;
        _dispMembership.Width = 560;
        _dispMembership.Height = 54;
        _dispMembership.Font = new System.Drawing.Font("Segoe UI", 11);
        _display.Controls.Add(_dispMembership);

        _dispReason.Left = 16;
        _dispReason.Top = 160;
        _dispReason.Width = 560;
        _dispReason.Height = 52;
        _dispReason.Font = new System.Drawing.Font("Segoe UI", 12, System.Drawing.FontStyle.Bold);
        _display.Controls.Add(_dispReason);

        _dispAction.Left = 16;
        _dispAction.Top = 214;
        _dispAction.Width = 560;
        _dispAction.Height = 40;
        _dispAction.Font = new System.Drawing.Font("Segoe UI", 11, System.Drawing.FontStyle.Bold);
        _display.Controls.Add(_dispAction);

        _dispInput.Left = 16;
        _dispInput.Top = 258;
        _dispInput.Width = 560;
        _dispInput.Height = 24;
        _dispInput.Font = new System.Drawing.Font("Segoe UI", 11);
        _display.Controls.Add(_dispInput);

        _dispMeta.Left = 16;
        _dispMeta.Top = 292;
        _dispMeta.Width = 560;
        _dispMeta.Height = 80;
        _dispMeta.Font = new System.Drawing.Font("Segoe UI", 10);
        _display.Controls.Add(_dispMeta);

        _historyPanel.BorderStyle = BorderStyle.FixedSingle;
        _historyPanel.Anchor = AnchorStyles.Top | AnchorStyles.Right | AnchorStyles.Bottom;
        Controls.Add(_historyPanel);

        _historyTitle.Left = 12;
        _historyTitle.Top = 12;
        _historyTitle.Width = 320;
        _historyTitle.Height = 20;
        _historyTitle.Text = "Historial (últimas lecturas)";
        _historyTitle.Font = new System.Drawing.Font("Segoe UI", 11, System.Drawing.FontStyle.Bold);
        _historyPanel.Controls.Add(_historyTitle);

        _history.Left = 12;
        _history.Top = 40;
        _history.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
        _history.View = View.Details;
        _history.FullRowSelect = true;
        _history.HideSelection = false;
        _history.MultiSelect = false;
        _history.HeaderStyle = ColumnHeaderStyle.Nonclickable;
        _history.Columns.Add("Hora", 70);
        _history.Columns.Add("Entrada", 90);
        _history.Columns.Add("Usuario", 140);
        _history.Columns.Add("Estado", 70);
        _history.Columns.Add("Motivo", 240);
        _historyPanel.Controls.Add(_history);

        _configBtn.Text = "Configuración";
        _configBtn.Top = 12;
        _configBtn.Left = 650;
        _configBtn.Width = 140;
        _configBtn.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _configBtn.Click += (_, _) => ToggleConfig();
        Controls.Add(_configBtn);

        _runBtn.Text = "Pausar";
        _runBtn.Top = 44;
        _runBtn.Left = 650;
        _runBtn.Width = 140;
        _runBtn.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _runBtn.Click += (_, _) => ToggleRun();
        Controls.Add(_runBtn);

        _clearQueueBtn.Text = "Limpiar cola";
        _clearQueueBtn.Top = 76;
        _clearQueueBtn.Left = 650;
        _clearQueueBtn.Width = 140;
        _clearQueueBtn.Anchor = AnchorStyles.Top | AnchorStyles.Right;
        _clearQueueBtn.Click += (_, _) => ClearOfflineQueue();
        Controls.Add(_clearQueueBtn);

        _capture.Left = -2000;
        _capture.Top = -2000;
        _capture.Width = 10;
        _capture.TabStop = false;
        _capture.KeyDown += CaptureKeyDown;
        _capture.TextChanged += (_, _) =>
        {
            if (!_configOpen)
            {
                try
                {
                    var t = _capture.Text ?? "";
                    _dispInput.Text = string.IsNullOrWhiteSpace(t) ? "" : $"Entrada: {FormatInputForDisplay(t)}";
                    _dispInput.ForeColor = System.Drawing.Color.FromArgb(148, 163, 184);
                }
                catch
                {
                }
            }
            var ms = _cfg.KeyboardIdleSubmitMs ?? 0;
            if (ms <= 0) { _captureIdleTimer.Stop(); return; }
            if (string.IsNullOrWhiteSpace(_capture.Text)) { _captureIdleTimer.Stop(); return; }
            _captureIdleTimer.Interval = Math.Clamp(ms, 50, 5000);
            _captureIdleTimer.Stop();
            _captureIdleTimer.Start();
        };
        Controls.Add(_capture);

        _tips.AutoPopDelay = 8000;
        _tips.InitialDelay = 400;
        _tips.ReshowDelay = 100;
        _tips.ShowAlways = true;

        BuildConfigPanel();
        ApplyTheme();
        ResetDisplay();
        LayoutMain();
        Resize += (_, _) => LayoutMain();

        _displayResetTimer.Interval = 250;
        _displayResetTimer.Tick += (_, _) => TickAutoResetDisplay();
        _displayResetTimer.Start();

        Shown += (_, _) =>
        {
            ApplyConfigToUi();
            ApplyKioskMode();
            FocusCapture();
            UpdateStatus();
            if (_running) StartInput();
            _ = LoadRemoteDeviceConfigAsync();
            _deviceConfigTimer.Interval = 5000;
            _deviceConfigTimer.Tick += async (_, _) => await LoadRemoteDeviceConfigAsync();
            _deviceConfigTimer.Start();
            _flushQueueTimer.Interval = 5000;
            _flushQueueTimer.Tick += async (_, _) => await FlushQueueAsync();
            _flushQueueTimer.Start();
            _captureIdleTimer.Tick += (_, _) =>
            {
                _captureIdleTimer.Stop();
                var raw = _capture.Text;
                if (string.IsNullOrWhiteSpace(raw)) return;
                _capture.Text = "";
                _ = HandleScanAsync(raw);
            };
            _commandPollTimer.Interval = Math.Clamp(_cfg.RemoteCommandPollMs ?? 1000, 250, 10000);
            _commandPollTimer.Tick += async (_, _) => await PollCommandsAsync();
            _commandPollTimer.Start();
        };

        _portsRefreshTimer.Interval = 1500;
        _portsRefreshTimer.Tick += (_, _) =>
        {
            if (!_configOpen) return;
            RefreshSerialPorts();
        };

        FormClosing += (_, _) => _cts.Cancel();
        KeyDown += MainKeyDown;
        Activated += (_, _) => FocusCapture();
        MouseDown += (_, _) => FocusCapture();
    }

    private void BuildConfigPanel()
    {
        var panel = new Panel
        {
            Left = 16,
            Top = 90,
            Width = 774,
            Height = 370,
            BorderStyle = BorderStyle.FixedSingle,
            Visible = false
        };
        panel.AutoScroll = false;
        panel.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
        panel.Name = "ConfigPanel";
        Controls.Add(panel);

        var tabs = new TabControl
        {
            Left = 12,
            Top = 12,
            Width = panel.Width - 24,
            Height = panel.Height - 76,
            Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom
        };
        panel.Controls.Add(tabs);

        var tpPairing = new TabPage("Pairing") { AutoScroll = true };
        var tpUnlock = new TabPage("Apertura") { AutoScroll = true };
        var tpInput = new TabPage("Lecturas") { AutoScroll = true };
        var tpTests = new TabPage("Pruebas") { AutoScroll = true };
        tabs.TabPages.Add(tpPairing);
        tabs.TabPages.Add(tpUnlock);
        tabs.TabPages.Add(tpInput);
        tabs.TabPages.Add(tpTests);

        var wide = 480;

        int AddTitle(Control c, string text)
        {
            var t = new Label
            {
                Left = 16,
                Top = 16,
                Width = 680,
                Height = 22,
                Text = text,
                Font = new System.Drawing.Font("Segoe UI", 10.5f, System.Drawing.FontStyle.Bold)
            };
            t.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
            c.Controls.Add(t);
            return t.Bottom;
        }

        var pairTitleBottom = AddTitle(tpPairing, "Pairing (desde Gestión → Accesos → Dispositivos → Pairing)");

        var pairHelp = new TextBox
        {
            Left = 16,
            Top = pairTitleBottom + 8,
            Width = 680,
            Height = 70,
            Multiline = true,
            ReadOnly = true,
            TabStop = false,
            BorderStyle = BorderStyle.FixedSingle,
            Text = "Tip: copiá el bloque de Pairing desde Gestión y usá Pegar.\r\nBase URL debe ser la API (ej: https://api.ironhub.motiona.xyz)."
        };
        pairHelp.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        tpPairing.Controls.Add(pairHelp);
        _tips.SetToolTip(pairHelp, "Si ves HTML/<!DOCTYPE> al hacer Pair, la Base URL no es la API.");

        int y = pairHelp.Bottom + 16;
        tpPairing.Controls.Add(MkLabel("Tenant:", 16, y));
        _tenant.Left = 200;
        _tenant.Top = y - 2;
        _tenant.Width = 240;
        _tenant.PlaceholderText = "ej: fittests";
        tpPairing.Controls.Add(_tenant);
        _tips.SetToolTip(_tenant, "Tenant del gimnasio. Si entrás a fittests.ironhub.motiona.xyz, el tenant es fittests.");

        y += 36;
        tpPairing.Controls.Add(MkLabel("Base URL API:", 16, y));
        _baseUrl.Left = 200;
        _baseUrl.Top = y - 2;
        _baseUrl.Width = wide;
        _baseUrl.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _baseUrl.PlaceholderText = "https://api.ironhub.motiona.xyz";
        tpPairing.Controls.Add(_baseUrl);
        _tips.SetToolTip(_baseUrl, "Debe ser la API. Ej: https://api.ironhub.motiona.xyz (no la web del tenant).");

        y += 36;
        tpPairing.Controls.Add(MkLabel("Device ID:", 16, y));
        _deviceId.Left = 200;
        _deviceId.Top = y - 2;
        _deviceId.Width = 260;
        _deviceId.PlaceholderText = "Device ID (string)";
        tpPairing.Controls.Add(_deviceId);
        _tips.SetToolTip(_deviceId, "Se obtiene en Gestión al crear el device.");

        _pastePairBtn.Text = "Pegar";
        _pastePairBtn.Left = 470;
        _pastePairBtn.Top = y - 3;
        _pastePairBtn.Width = 80;
        _pastePairBtn.Click += (_, _) => PastePairingFromClipboard();
        tpPairing.Controls.Add(_pastePairBtn);
        _tips.SetToolTip(_pastePairBtn, "Pega Tenant/Base URL/Device ID/Código si copiás el bloque desde Gestión.");

        y += 36;
        tpPairing.Controls.Add(MkLabel("Código:", 16, y));
        _pairing.Left = 200;
        _pairing.Top = y - 2;
        _pairing.Width = 260;
        _pairing.PlaceholderText = "Código de pairing";
        tpPairing.Controls.Add(_pairing);

        _pairBtn.Text = "Pair";
        _pairBtn.Left = 470;
        _pairBtn.Top = y - 3;
        _pairBtn.Width = 80;
        _pairBtn.Click += async (_, _) => await PairAsync();
        tpPairing.Controls.Add(_pairBtn);

        _validateBtn.Text = "Sync";
        _validateBtn.Left = 560;
        _validateBtn.Top = y - 3;
        _validateBtn.Width = 80;
        _validateBtn.Click += async (_, _) => await ForceSyncAsync();
        tpPairing.Controls.Add(_validateBtn);

        var unlockTitleBottom = AddTitle(tpUnlock, "Apertura (salida hacia molinete/puerta)");
        y = unlockTitleBottom + 14;
        tpUnlock.Controls.Add(MkLabel("Método:", 16, y));
        _unlockMethod.Left = 200;
        _unlockMethod.Top = y - 2;
        _unlockMethod.Width = 240;
        _unlockMethod.DropDownStyle = ComboBoxStyle.DropDownList;
        _unlockMethod.Items.Clear();
        _unlockMethod.Items.AddRange(new object[] { "none", "http_get", "http_post_json", "tcp", "serial" });
        tpUnlock.Controls.Add(_unlockMethod);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("Preset:", 16, y));
        _unlockPreset.Left = 200;
        _unlockPreset.Top = y - 2;
        _unlockPreset.Width = 360;
        _unlockPreset.DropDownStyle = ComboBoxStyle.DropDownList;
        _unlockPreset.Items.Clear();
        _unlockPreset.Items.AddRange(
            new object[]
            {
                "HTTP GET · /unlock",
                "HTTP POST JSON · /unlock",
                "TCP · OPEN\\n (9100)",
                "TCP · 0xA0 0x01 0x01 (9100)",
                "Serial · DTR_PULSE:500 (9600)",
                "Serial · 0xA0 0x01 0x01 (9600)"
            }
        );
        if (_unlockPreset.Items.Count > 0) _unlockPreset.SelectedIndex = 0;
        tpUnlock.Controls.Add(_unlockPreset);

        _unlockPresetApplyBtn.Left = 570;
        _unlockPresetApplyBtn.Top = y - 3;
        _unlockPresetApplyBtn.Width = 120;
        _unlockPresetApplyBtn.Text = "Aplicar";
        _unlockPresetApplyBtn.Click += (_, _) => ApplyUnlockPresetFromUi();
        tpUnlock.Controls.Add(_unlockPresetApplyBtn);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("Unlock URL:", 16, y));
        _unlockUrl.Left = 200;
        _unlockUrl.Top = y - 2;
        _unlockUrl.Width = wide;
        _unlockUrl.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _unlockUrl.PlaceholderText = "http://RELAY_IP/unlock";
        tpUnlock.Controls.Add(_unlockUrl);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("TCP host:", 16, y));
        _unlockTcpHost.Left = 200;
        _unlockTcpHost.Top = y - 2;
        _unlockTcpHost.Width = 240;
        _unlockTcpHost.PlaceholderText = "192.168.1.50";
        tpUnlock.Controls.Add(_unlockTcpHost);
        tpUnlock.Controls.Add(MkLabel("TCP port:", 460, y));
        _unlockTcpPort.Left = 540;
        _unlockTcpPort.Top = y - 2;
        _unlockTcpPort.Width = 120;
        _unlockTcpPort.Minimum = 1;
        _unlockTcpPort.Maximum = 65535;
        _unlockTcpPort.Value = 9100;
        tpUnlock.Controls.Add(_unlockTcpPort);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("TCP payload:", 16, y));
        _unlockTcpPayload.Left = 200;
        _unlockTcpPayload.Top = y - 2;
        _unlockTcpPayload.Width = wide;
        _unlockTcpPayload.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _unlockTcpPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01";
        tpUnlock.Controls.Add(_unlockTcpPayload);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("Serial port:", 16, y));
        _unlockSerialPort.Left = 200;
        _unlockSerialPort.Top = y - 2;
        _unlockSerialPort.Width = 160;
        _unlockSerialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        tpUnlock.Controls.Add(_unlockSerialPort);
        tpUnlock.Controls.Add(MkLabel("Baud:", 370, y));
        _unlockSerialBaud.Left = 420;
        _unlockSerialBaud.Top = y - 2;
        _unlockSerialBaud.Width = 120;
        _unlockSerialBaud.Minimum = 1200;
        _unlockSerialBaud.Maximum = 921600;
        _unlockSerialBaud.Increment = 1200;
        tpUnlock.Controls.Add(_unlockSerialBaud);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("Serial payload:", 16, y));
        _unlockSerialPayload.Left = 200;
        _unlockSerialPayload.Top = y - 2;
        _unlockSerialPayload.Width = wide;
        _unlockSerialPayload.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _unlockSerialPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500";
        tpUnlock.Controls.Add(_unlockSerialPayload);

        y += 36;
        tpUnlock.Controls.Add(MkLabel("Unlock ms:", 16, y));
        _unlockMs.Left = 200;
        _unlockMs.Top = y - 2;
        _unlockMs.Width = 120;
        _unlockMs.Minimum = 250;
        _unlockMs.Maximum = 15000;
        _unlockMs.Increment = 250;
        tpUnlock.Controls.Add(_unlockMs);

        var inputTitleBottom = AddTitle(tpInput, "Lecturas (entrada) y operación");
        y = inputTitleBottom + 14;
        tpInput.Controls.Add(MkLabel("Modo:", 16, y));
        _accessMode.Left = 200;
        _accessMode.Top = y - 2;
        _accessMode.Width = 260;
        _accessMode.DropDownStyle = ComboBoxStyle.DropDownList;
        _accessMode.Items.Clear();
        _accessMode.Items.AddRange(new object[] { "validate_and_command", "observe_only" });
        tpInput.Controls.Add(_accessMode);

        y += 36;
        tpInput.Controls.Add(MkLabel("Input source:", 16, y));
        _inputSource.Left = 200;
        _inputSource.Top = y - 2;
        _inputSource.Width = 260;
        _inputSource.DropDownStyle = ComboBoxStyle.DropDownList;
        _inputSource.Items.Clear();
        _inputSource.Items.AddRange(new object[] { "keyboard", "serial" });
        tpInput.Controls.Add(_inputSource);

        y += 36;
        tpInput.Controls.Add(MkLabel("Serial port:", 16, y));
        _serialPort.Left = 200;
        _serialPort.Top = y - 2;
        _serialPort.Width = 160;
        _serialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        tpInput.Controls.Add(_serialPort);

        _refreshPortsBtn.Left = 370;
        _refreshPortsBtn.Top = y - 3;
        _refreshPortsBtn.Width = 70;
        _refreshPortsBtn.Text = "Scan";
        _refreshPortsBtn.Click += (_, _) => RefreshSerialPorts();
        tpInput.Controls.Add(_refreshPortsBtn);

        tpInput.Controls.Add(MkLabel("Baud:", 460, y));
        _serialBaud.Left = 520;
        _serialBaud.Top = y - 2;
        _serialBaud.Width = 120;
        _serialBaud.Minimum = 1200;
        _serialBaud.Maximum = 921600;
        _serialBaud.Increment = 1200;
        tpInput.Controls.Add(_serialBaud);

        y += 36;
        tpInput.Controls.Add(MkLabel("Protocol:", 16, y));
        _inputProtocol.Left = 200;
        _inputProtocol.Top = y - 2;
        _inputProtocol.Width = 260;
        _inputProtocol.DropDownStyle = ComboBoxStyle.DropDownList;
        _inputProtocol.Items.Clear();
        _inputProtocol.Items.AddRange(new object[] { "raw", "data", "drt", "str", "regex", "em4100" });
        tpInput.Controls.Add(_inputProtocol);

        y += 36;
        tpInput.Controls.Add(MkLabel("Keyboard submit:", 16, y));
        _captureSubmitKey.Left = 200;
        _captureSubmitKey.Top = y - 2;
        _captureSubmitKey.Width = 120;
        _captureSubmitKey.DropDownStyle = ComboBoxStyle.DropDownList;
        _captureSubmitKey.Items.Clear();
        _captureSubmitKey.Items.AddRange(new object[] { "enter", "tab" });
        tpInput.Controls.Add(_captureSubmitKey);

        tpInput.Controls.Add(MkLabel("Idle ms:", 330, y));
        _captureIdleMs.Left = 400;
        _captureIdleMs.Top = y - 2;
        _captureIdleMs.Width = 120;
        _captureIdleMs.Minimum = 0;
        _captureIdleMs.Maximum = 5000;
        _captureIdleMs.Increment = 50;
        tpInput.Controls.Add(_captureIdleMs);

        y += 36;
        tpInput.Controls.Add(MkLabel("Remote cmds:", 16, y));
        _remoteCmds.Left = 200;
        _remoteCmds.Top = y - 2;
        _remoteCmds.Width = 220;
        _remoteCmds.Text = "Habilitar polling";
        tpInput.Controls.Add(_remoteCmds);

        tpInput.Controls.Add(MkLabel("Poll ms:", 430, y));
        _remotePollMs.Left = 500;
        _remotePollMs.Top = y - 2;
        _remotePollMs.Width = 120;
        _remotePollMs.Minimum = 250;
        _remotePollMs.Maximum = 10000;
        _remotePollMs.Increment = 250;
        tpInput.Controls.Add(_remotePollMs);

        y += 36;
        tpInput.Controls.Add(MkLabel("Regex (opt):", 16, y));
        _inputRegex.Left = 200;
        _inputRegex.Top = y - 2;
        _inputRegex.Width = wide;
        _inputRegex.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _inputRegex.PlaceholderText = "Ej: UID:(\\w+)";
        tpInput.Controls.Add(_inputRegex);

        y += 36;
        tpInput.Controls.Add(MkLabel("UID:", 16, y));
        _uidFormat.Left = 200;
        _uidFormat.Top = y - 2;
        _uidFormat.Width = 120;
        _uidFormat.DropDownStyle = ComboBoxStyle.DropDownList;
        _uidFormat.Items.Clear();
        _uidFormat.Items.AddRange(new object[] { "auto", "hex", "dec" });
        tpInput.Controls.Add(_uidFormat);

        _uidEndian.Left = 330;
        _uidEndian.Top = y - 2;
        _uidEndian.Width = 120;
        _uidEndian.DropDownStyle = ComboBoxStyle.DropDownList;
        _uidEndian.Items.Clear();
        _uidEndian.Items.AddRange(new object[] { "auto", "be", "le" });
        tpInput.Controls.Add(_uidEndian);

        _uidBits.Left = 460;
        _uidBits.Top = y - 2;
        _uidBits.Width = 120;
        _uidBits.Minimum = 16;
        _uidBits.Maximum = 128;
        _uidBits.Increment = 8;
        tpInput.Controls.Add(_uidBits);

        y += 36;
        tpInput.Controls.Add(MkLabel("Hotkey:", 16, y));
        _manualHotkey.Left = 200;
        _manualHotkey.Top = y - 2;
        _manualHotkey.Width = 120;
        tpInput.Controls.Add(_manualHotkey);

        _allowManual.Left = 330;
        _allowManual.Top = y - 2;
        _allowManual.Width = 210;
        _allowManual.Text = "Apertura manual";
        tpInput.Controls.Add(_allowManual);

        _fullscreen.Left = 550;
        _fullscreen.Top = y - 2;
        _fullscreen.Width = 170;
        _fullscreen.Text = "Kiosk (pantalla completa)";
        tpInput.Controls.Add(_fullscreen);

        var inputHint = new Label
        {
            Left = 16,
            Top = y + 38,
            Width = 680,
            Height = 46,
            Text = "Uso: escaneá llavero/QR o tipeá DNI + Enter. DNI#PIN: 12345678#1234 + Enter.",
        };
        inputHint.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        tpInput.Controls.Add(inputHint);

        var testsTitleBottom = AddTitle(tpTests, "Pruebas");
        y = testsTitleBottom + 14;
        var connSection = new Label
        {
            Left = 16,
            Top = y,
            Width = 680,
            Height = 22,
            Text = "Conectividad",
            Font = new System.Drawing.Font("Segoe UI", 10.0f, System.Drawing.FontStyle.Bold)
        };
        connSection.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        tpTests.Controls.Add(connSection);
        y = connSection.Bottom + 12;
        _testApiBtn.Left = 200;
        _testApiBtn.Top = y - 3;
        _testApiBtn.Width = 180;
        _testApiBtn.Text = "Test API";
        _testApiBtn.Click += async (_, _) => await RunApiConnectivityTestAsync();
        tpTests.Controls.Add(_testApiBtn);

        _testModeActionBtn.Left = 390;
        _testModeActionBtn.Top = y - 3;
        _testModeActionBtn.Width = 240;
        _testModeActionBtn.Text = "Test acción según modo";
        _testModeActionBtn.Click += async (_, _) => await RunUnlockByModeTestAsync();
        tpTests.Controls.Add(_testModeActionBtn);

        y += 44;
        var unlockSection = new Label
        {
            Left = 16,
            Top = y,
            Width = 680,
            Height = 22,
            Text = "Apertura",
            Font = new System.Drawing.Font("Segoe UI", 10.0f, System.Drawing.FontStyle.Bold)
        };
        unlockSection.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        tpTests.Controls.Add(unlockSection);
        y = unlockSection.Bottom + 12;
        tpTests.Controls.Add(MkLabel("Test GET URL:", 16, y));
        _testGetUrl.Left = 200;
        _testGetUrl.Top = y - 2;
        _testGetUrl.Anchor = AnchorStyles.Top | AnchorStyles.Left;
        _testGetUrl.PlaceholderText = "http://RELAY_IP/unlock";
        tpTests.Controls.Add(_testGetUrl);
        _testGetBtn.Left = 640;
        _testGetBtn.Top = y - 3;
        _testGetBtn.Width = 80;
        _testGetBtn.Text = "Test";
        _testGetBtn.Click += async (_, _) => await RunUnlockTestAsync("http_get");
        tpTests.Controls.Add(_testGetBtn);
        _testGetUrl.Width = Math.Max(180, _testGetBtn.Left - _testGetUrl.Left - 12);

        y += 36;
        tpTests.Controls.Add(MkLabel("Test POST URL:", 16, y));
        _testPostUrl.Left = 200;
        _testPostUrl.Top = y - 2;
        _testPostUrl.Anchor = AnchorStyles.Top | AnchorStyles.Left;
        _testPostUrl.PlaceholderText = "http://RELAY_IP/unlock";
        tpTests.Controls.Add(_testPostUrl);
        _testPostBtn.Left = 640;
        _testPostBtn.Top = y - 3;
        _testPostBtn.Width = 80;
        _testPostBtn.Text = "Test";
        _testPostBtn.Click += async (_, _) => await RunUnlockTestAsync("http_post_json");
        tpTests.Controls.Add(_testPostBtn);
        _testPostUrl.Width = Math.Max(180, _testPostBtn.Left - _testPostUrl.Left - 12);

        y += 36;
        tpTests.Controls.Add(MkLabel("Test TCP:", 16, y));
        _testTcpHost.Left = 200;
        _testTcpHost.Top = y - 2;
        _testTcpHost.Width = 300;
        tpTests.Controls.Add(_testTcpHost);
        _testTcpPort.Left = 510;
        _testTcpPort.Top = y - 2;
        _testTcpPort.Width = 120;
        _testTcpPort.Minimum = 1;
        _testTcpPort.Maximum = 65535;
        _testTcpPort.Value = 9100;
        tpTests.Controls.Add(_testTcpPort);
        _testTcpBtn.Left = 640;
        _testTcpBtn.Top = y - 3;
        _testTcpBtn.Width = 80;
        _testTcpBtn.Text = "Test";
        _testTcpBtn.Click += async (_, _) => await RunUnlockTestAsync("tcp");
        tpTests.Controls.Add(_testTcpBtn);

        y += 36;
        tpTests.Controls.Add(MkLabel("TCP payload:", 16, y));
        _testTcpPayload.Left = 200;
        _testTcpPayload.Top = y - 2;
        _testTcpPayload.Width = wide;
        _testTcpPayload.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _testTcpPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01";
        tpTests.Controls.Add(_testTcpPayload);

        y += 36;
        tpTests.Controls.Add(MkLabel("Test Serial:", 16, y));
        _testSerialPort.Left = 200;
        _testSerialPort.Top = y - 2;
        _testSerialPort.Width = 160;
        _testSerialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        tpTests.Controls.Add(_testSerialPort);
        _testSerialBaud.Left = 370;
        _testSerialBaud.Top = y - 2;
        _testSerialBaud.Width = 120;
        _testSerialBaud.Minimum = 1200;
        _testSerialBaud.Maximum = 921600;
        _testSerialBaud.Increment = 1200;
        _testSerialBaud.Value = 9600;
        tpTests.Controls.Add(_testSerialBaud);
        _testSerialBtn.Left = 640;
        _testSerialBtn.Top = y - 3;
        _testSerialBtn.Width = 80;
        _testSerialBtn.Text = "Test";
        _testSerialBtn.Click += async (_, _) => await RunUnlockTestAsync("serial");
        tpTests.Controls.Add(_testSerialBtn);

        y += 36;
        tpTests.Controls.Add(MkLabel("Serial payload:", 16, y));
        _testSerialPayload.Left = 200;
        _testSerialPayload.Top = y - 2;
        _testSerialPayload.Width = wide;
        _testSerialPayload.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
        _testSerialPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500";
        tpTests.Controls.Add(_testSerialPayload);

        y += 44;
        _testAllBtn.Left = 200;
        _testAllBtn.Top = y - 3;
        _testAllBtn.Width = 180;
        _testAllBtn.Text = "Probar todos";
        _testAllBtn.Click += async (_, _) => await RunUnlockAllTestsAsync();
        tpTests.Controls.Add(_testAllBtn);

        var diag = new Button { Width = 180, Text = "Copiar diagnóstico" };
        diag.Left = 12;
        diag.Top = panel.Height - 52;
        diag.Anchor = AnchorStyles.Left | AnchorStyles.Bottom;
        diag.Click += (_, _) => CopyDiagnosticsToClipboard();
        panel.Controls.Add(diag);

        var save = new Button { Width = 120, Text = "Guardar" };
        save.Left = panel.Width - 264;
        save.Top = panel.Height - 52;
        save.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        save.Click += (_, _) => SaveConfig();
        panel.Controls.Add(save);

        var close = new Button { Width = 120, Text = "Cerrar" };
        close.Left = panel.Width - 136;
        close.Top = panel.Height - 52;
        close.Anchor = AnchorStyles.Right | AnchorStyles.Bottom;
        close.Click += (_, _) => ToggleConfig(false);
        panel.Controls.Add(close);
    }

    private static Label MkLabel(string t, int x, int y)
    {
        return new Label { Left = x, Top = y, AutoSize = true, Text = t };
    }

    private void ToggleConfig(bool? open = null)
    {
        _configOpen = open ?? !_configOpen;
        var p = Controls["ConfigPanel"];
        if (p != null)
        {
            p.Visible = _configOpen;
            if (_configOpen)
            {
                p.BringToFront();
                LayoutMain();
            }
        }
        if (_configOpen) RefreshSerialPorts();
        if (_configOpen) _portsRefreshTimer.Start();
        if (!_configOpen) _portsRefreshTimer.Stop();
        if (_configOpen) ApplyConfigToUi();
        if (_configOpen) StopInput();
        if (_configOpen) _commandPollTimer.Stop();
        ApplyKioskMode();
        FocusCapture();
        if (!_configOpen && _running) StartInput();
        if (!_configOpen && _running) _commandPollTimer.Start();
        UpdateStatus();
    }

    private void ApplyKioskMode()
    {
        var kiosk = !_configOpen && (_cfg.Fullscreen ?? false);
        if (kiosk)
        {
            FormBorderStyle = FormBorderStyle.None;
            WindowState = FormWindowState.Maximized;
            TopMost = true;
        }
        else
        {
            TopMost = false;
            FormBorderStyle = FormBorderStyle.Sizable;
            if (WindowState == FormWindowState.Maximized) WindowState = FormWindowState.Normal;
        }
    }

    private void FocusCapture()
    {
        if (_configOpen)
        {
            try
            {
                _tenant.Focus();
                _tenant.Select();
            }
            catch
            {
            }
            return;
        }
        _capture.Focus();
        _capture.Select();
    }

    private void RefreshSerialPorts()
    {
        try
        {
            var ports = SerialPort.GetPortNames();
            Array.Sort(ports, StringComparer.OrdinalIgnoreCase);
            UpdatePortCombo(_serialPort, ports, (_cfg.SerialPort ?? "").Trim());
            UpdatePortCombo(_testSerialPort, ports, (_cfg.TestSerialPort ?? "").Trim());
            UpdatePortCombo(_unlockSerialPort, ports, (_cfg.UnlockSerialPort ?? "").Trim());
        }
        catch
        {
            _serialPort.Items.Clear();
            _testSerialPort.Items.Clear();
            _unlockSerialPort.Items.Clear();
        }
    }

    private static void UpdatePortCombo(ComboBox cb, string[] ports, string preferred)
    {
        if (cb == null) return;
        var prev = (cb.SelectedItem?.ToString() ?? "").Trim();
        if (string.IsNullOrWhiteSpace(prev)) prev = (preferred ?? "").Trim();
        cb.BeginUpdate();
        try
        {
            cb.Items.Clear();
            if (!string.IsNullOrWhiteSpace(prev) && !ports.Contains(prev, StringComparer.OrdinalIgnoreCase))
            {
                cb.Items.Add(prev);
            }
            foreach (var p in ports)
            {
                cb.Items.Add(p);
            }
            if (!string.IsNullOrWhiteSpace(prev) && cb.Items.Contains(prev))
            {
                cb.SelectedItem = prev;
            }
            if (cb.SelectedItem == null && cb.Items.Count > 0)
            {
                cb.SelectedIndex = 0;
            }
        }
        finally
        {
            cb.EndUpdate();
        }
    }

    private void StartInput()
    {
        var src = (_cfg.InputSource ?? "keyboard").Trim().ToLowerInvariant();
        if (src == "serial")
        {
            StartSerial();
        }
        else
        {
            StopSerial();
            var submit = (_cfg.KeyboardSubmitKey ?? "enter").Trim().ToLowerInvariant();
            var idle = _cfg.KeyboardIdleSubmitMs ?? 0;
            _io.Text = idle > 0 ? $"Input: keyboard · submit {submit} · idle {idle}ms" : $"Input: keyboard · submit {submit}";
        }
    }

    private void StopInput()
    {
        StopSerial();
    }

    private void StartSerial()
    {
        StopSerial();
        var port = (_cfg.SerialPort ?? "").Trim();
        if (string.IsNullOrWhiteSpace(port)) { _io.Text = "Input: serial (sin puerto)"; return; }
        var baud = _cfg.SerialBaud ?? 9600;
        try
        {
            _serial = new SerialPort(port, baud)
            {
                NewLine = "\n",
                ReadTimeout = 500,
                WriteTimeout = 500,
            };
            _serial.DataReceived += (_, _) =>
            {
                try
                {
                    if (_serial == null) return;
                    var s = _serial.ReadExisting();
                    if (string.IsNullOrEmpty(s)) return;
                    var overflow = false;
                    lock (_serialBuf)
                    {
                        _serialBuf.Append(s);
                        if (_serialBuf.Length > 32768)
                        {
                            _serialBuf.Clear();
                            overflow = true;
                        }
                        var txt = _serialBuf.ToString();
                        var idx = txt.IndexOf('\n');
                        while (idx >= 0)
                        {
                            var line = txt[..idx].Trim('\r');
                            txt = txt[(idx + 1)..];
                            if (!string.IsNullOrWhiteSpace(line))
                            {
                                BeginInvoke(new Action(async () => await HandleScanAsync(line)));
                            }
                            idx = txt.IndexOf('\n');
                        }
                        _serialBuf.Clear();
                        _serialBuf.Append(txt);
                    }
                    if (overflow)
                    {
                        BeginInvoke(new Action(() =>
                        {
                            _last.Text = "Serial: buffer overflow (sin \\n)";
                        }));
                        _log.Append("serial_buffer_overflow");
                    }
                }
                catch
                {
                }
            };
            _serial.Open();
            _last.Text = $"Serial OK · {port}@{baud}";
            _io.Text = $"Input: serial · {port}@{baud}";
        }
        catch (Exception ex)
        {
            _last.Text = $"Serial error: {ex.Message}";
            _io.Text = "Input: serial (error)";
            StopSerial();
        }
    }

    private void StopSerial()
    {
        try
        {
            if (_serial != null)
            {
                _serial.Close();
                _serial.Dispose();
            }
        }
        catch
        {
        }
        _serial = null;
        lock (_serialBuf)
        {
            _serialBuf.Clear();
        }
        if ((_cfg.InputSource ?? "keyboard").Trim().ToLowerInvariant() == "serial")
        {
            _io.Text = "Input: serial (disconnected)";
        }
    }

    private void ApplyConfigToUi()
    {
        _tenant.Text = _cfg.Tenant ?? "";
        _baseUrl.Text = _cfg.BaseUrl ?? "";
        _deviceId.Text = _cfg.DeviceId ?? "";
        _pairing.Text = "";
        _unlockUrl.Text = _cfg.UnlockUrl ?? "";
        _unlockMethod.SelectedItem = (_cfg.UnlockMethod ?? "http_get").Trim().ToLowerInvariant();
        if (_unlockMethod.SelectedItem == null && _unlockMethod.Items.Count > 0) _unlockMethod.SelectedIndex = 0;
        _unlockTcpHost.Text = _cfg.UnlockTcpHost ?? "";
        _unlockTcpPort.Value = Math.Clamp(_cfg.UnlockTcpPort ?? 9100, (int)_unlockTcpPort.Minimum, (int)_unlockTcpPort.Maximum);
        _unlockTcpPayload.Text = _cfg.UnlockTcpPayload ?? "";
        _unlockMs.Value = Math.Clamp(_cfg.UnlockMs ?? 2500, 250, 15000);
        var usp = (_cfg.UnlockSerialPort ?? "").Trim();
        if (!string.IsNullOrWhiteSpace(usp) && _unlockSerialPort.Items.Contains(usp)) _unlockSerialPort.SelectedItem = usp;
        if (_unlockSerialPort.SelectedItem == null && _unlockSerialPort.Items.Count > 0) _unlockSerialPort.SelectedIndex = 0;
        _unlockSerialBaud.Value = Math.Clamp(_cfg.UnlockSerialBaud ?? 9600, (int)_unlockSerialBaud.Minimum, (int)_unlockSerialBaud.Maximum);
        _unlockSerialPayload.Text = _cfg.UnlockSerialPayload ?? "";
        _accessMode.SelectedItem = (_cfg.Mode ?? "validate_and_command").Trim().ToLowerInvariant();
        if (_accessMode.SelectedItem == null && _accessMode.Items.Count > 0) _accessMode.SelectedIndex = 0;
        _inputSource.SelectedItem = (_cfg.InputSource ?? "keyboard").Trim().ToLowerInvariant();
        if (_inputSource.SelectedItem == null && _inputSource.Items.Count > 0) _inputSource.SelectedIndex = 0;
        RefreshSerialPorts();
        var sp = (_cfg.SerialPort ?? "").Trim();
        if (!string.IsNullOrWhiteSpace(sp) && _serialPort.Items.Contains(sp)) _serialPort.SelectedItem = sp;
        if (_serialPort.SelectedItem == null && _serialPort.Items.Count > 0) _serialPort.SelectedIndex = 0;
        _serialBaud.Value = Math.Clamp(_cfg.SerialBaud ?? 9600, (int)_serialBaud.Minimum, (int)_serialBaud.Maximum);
        _inputProtocol.SelectedItem = (_cfg.InputProtocol ?? "raw").Trim().ToLowerInvariant();
        if (_inputProtocol.SelectedItem == null && _inputProtocol.Items.Count > 0) _inputProtocol.SelectedIndex = 0;
        _captureSubmitKey.SelectedItem = (_cfg.KeyboardSubmitKey ?? "enter").Trim().ToLowerInvariant();
        if (_captureSubmitKey.SelectedItem == null && _captureSubmitKey.Items.Count > 0) _captureSubmitKey.SelectedIndex = 0;
        _captureIdleMs.Value = Math.Clamp(_cfg.KeyboardIdleSubmitMs ?? 0, (int)_captureIdleMs.Minimum, (int)_captureIdleMs.Maximum);
        _remoteCmds.Checked = _cfg.RemoteCommandsEnabled ?? true;
        _remotePollMs.Value = Math.Clamp(_cfg.RemoteCommandPollMs ?? 1000, (int)_remotePollMs.Minimum, (int)_remotePollMs.Maximum);
        _inputRegex.Text = _cfg.InputRegex ?? "";
        _uidFormat.SelectedItem = (_cfg.UidFormat ?? "auto").Trim().ToLowerInvariant();
        if (_uidFormat.SelectedItem == null && _uidFormat.Items.Count > 0) _uidFormat.SelectedIndex = 0;
        _uidEndian.SelectedItem = (_cfg.UidEndian ?? "auto").Trim().ToLowerInvariant();
        if (_uidEndian.SelectedItem == null && _uidEndian.Items.Count > 0) _uidEndian.SelectedIndex = 0;
        _uidBits.Value = Math.Clamp(_cfg.UidBits ?? 40, (int)_uidBits.Minimum, (int)_uidBits.Maximum);
        _testGetUrl.Text = _cfg.TestHttpGetUrl ?? "";
        _testPostUrl.Text = _cfg.TestHttpPostUrl ?? "";
        _testTcpHost.Text = _cfg.TestTcpHost ?? "";
        _testTcpPort.Value = Math.Clamp(_cfg.TestTcpPort ?? 9100, (int)_testTcpPort.Minimum, (int)_testTcpPort.Maximum);
        _testTcpPayload.Text = _cfg.TestTcpPayload ?? "";
        var tsp = (_cfg.TestSerialPort ?? "").Trim();
        if (!string.IsNullOrWhiteSpace(tsp) && _testSerialPort.Items.Contains(tsp)) _testSerialPort.SelectedItem = tsp;
        if (_testSerialPort.SelectedItem == null && _testSerialPort.Items.Count > 0) _testSerialPort.SelectedIndex = 0;
        _testSerialBaud.Value = Math.Clamp(_cfg.TestSerialBaud ?? 9600, (int)_testSerialBaud.Minimum, (int)_testSerialBaud.Maximum);
        _testSerialPayload.Text = _cfg.TestSerialPayload ?? "";
        _allowManual.Checked = _cfg.AllowManualUnlock ?? true;
        _manualHotkey.Text = _cfg.ManualHotkey ?? "F10";
        _fullscreen.Checked = _cfg.Fullscreen ?? false;
    }

    private void ApplyUnlockPresetFromUi()
    {
        var p = _unlockPreset.SelectedItem?.ToString() ?? "";
        if (p.StartsWith("HTTP GET", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "http_get";
            if (string.IsNullOrWhiteSpace(_unlockUrl.Text)) _unlockUrl.Text = "http://RELAY_IP/unlock";
            return;
        }
        if (p.StartsWith("HTTP POST JSON", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "http_post_json";
            if (string.IsNullOrWhiteSpace(_unlockUrl.Text)) _unlockUrl.Text = "http://RELAY_IP/unlock";
            return;
        }
        if (p.StartsWith("TCP · OPEN", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "tcp";
            if (string.IsNullOrWhiteSpace(_unlockTcpHost.Text)) _unlockTcpHost.Text = "192.168.1.50";
            _unlockTcpPort.Value = Math.Clamp(9100, (int)_unlockTcpPort.Minimum, (int)_unlockTcpPort.Maximum);
            _unlockTcpPayload.Text = "OPEN\n";
            return;
        }
        if (p.StartsWith("TCP · 0xA0", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "tcp";
            if (string.IsNullOrWhiteSpace(_unlockTcpHost.Text)) _unlockTcpHost.Text = "192.168.1.50";
            _unlockTcpPort.Value = Math.Clamp(9100, (int)_unlockTcpPort.Minimum, (int)_unlockTcpPort.Maximum);
            _unlockTcpPayload.Text = "0xA0 0x01 0x01";
            return;
        }
        if (p.StartsWith("Serial · DTR_PULSE", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "serial";
            _unlockSerialBaud.Value = Math.Clamp(9600, (int)_unlockSerialBaud.Minimum, (int)_unlockSerialBaud.Maximum);
            _unlockSerialPayload.Text = "DTR_PULSE:500";
            return;
        }
        if (p.StartsWith("Serial · 0xA0", StringComparison.Ordinal))
        {
            _unlockMethod.SelectedItem = "serial";
            _unlockSerialBaud.Value = Math.Clamp(9600, (int)_unlockSerialBaud.Minimum, (int)_unlockSerialBaud.Maximum);
            _unlockSerialPayload.Text = "0xA0 0x01 0x01";
        }
    }

    private void SaveConfig()
    {
        if (!EnsureBasicConfigValid()) return;
        _cfg.Tenant = _tenant.Text.Trim().ToLowerInvariant();
        _cfg.BaseUrl = NormalizeBaseUrl(_baseUrl.Text);
        _cfg.DeviceId = _deviceId.Text.Trim();
        _cfg.UnlockUrl = _unlockUrl.Text.Trim();
        _cfg.UnlockMethod = _unlockMethod.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "http_get";
        _cfg.UnlockMs = (int)_unlockMs.Value;
        _cfg.UnlockTcpHost = _unlockTcpHost.Text.Trim();
        _cfg.UnlockTcpPort = (int)_unlockTcpPort.Value;
        _cfg.UnlockTcpPayload = _unlockTcpPayload.Text;
        _cfg.UnlockSerialPort = _unlockSerialPort.SelectedItem?.ToString() ?? "";
        _cfg.UnlockSerialBaud = (int)_unlockSerialBaud.Value;
        _cfg.UnlockSerialPayload = _unlockSerialPayload.Text;
        _cfg.Mode = _accessMode.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "validate_and_command";
        _cfg.InputSource = _inputSource.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "keyboard";
        _cfg.SerialPort = _serialPort.SelectedItem?.ToString() ?? "";
        _cfg.SerialBaud = (int)_serialBaud.Value;
        _cfg.InputProtocol = _inputProtocol.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "raw";
        _cfg.KeyboardSubmitKey = _captureSubmitKey.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "enter";
        _cfg.KeyboardIdleSubmitMs = (int)_captureIdleMs.Value;
        _cfg.RemoteCommandsEnabled = _remoteCmds.Checked;
        _cfg.RemoteCommandPollMs = (int)_remotePollMs.Value;
        _cfg.InputRegex = _inputRegex.Text.Trim();
        _cfg.UidFormat = _uidFormat.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "auto";
        _cfg.UidEndian = _uidEndian.SelectedItem?.ToString()?.Trim().ToLowerInvariant() ?? "auto";
        _cfg.UidBits = (int)_uidBits.Value;
        _cfg.TestHttpGetUrl = _testGetUrl.Text.Trim();
        _cfg.TestHttpPostUrl = _testPostUrl.Text.Trim();
        _cfg.TestTcpHost = _testTcpHost.Text.Trim();
        _cfg.TestTcpPort = (int)_testTcpPort.Value;
        _cfg.TestTcpPayload = _testTcpPayload.Text;
        _cfg.TestSerialPort = _testSerialPort.SelectedItem?.ToString() ?? "";
        _cfg.TestSerialBaud = (int)_testSerialBaud.Value;
        _cfg.TestSerialPayload = _testSerialPayload.Text;
        _cfg.AllowManualUnlock = _allowManual.Checked;
        _cfg.ManualHotkey = _manualHotkey.Text.Trim();
        _cfg.Fullscreen = _fullscreen.Checked;
        _cfg.Save();
        _commandPollTimer.Interval = Math.Clamp(_cfg.RemoteCommandPollMs ?? 1000, 250, 10000);
        UpdateStatus();
        ToggleConfig(false);
    }

    private bool EnsureBasicConfigValid()
    {
        try
        {
            var tenant = _tenant.Text.Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(tenant))
            {
                MessageBox.Show("Falta Tenant.", "Configuración", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                _tenant.Focus();
                return false;
            }
            foreach (var ch in tenant)
            {
                var ok = (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '-';
                if (!ok)
                {
                    MessageBox.Show("Tenant inválido. Usar solo a-z, 0-9 y '-'.", "Configuración", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    _tenant.Focus();
                    return false;
                }
            }

            var rawBaseUrl = _baseUrl.Text;
            var baseUrl = NormalizeBaseUrl(rawBaseUrl);
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                MessageBox.Show("Falta Base URL de la API.", "Configuración", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                _baseUrl.Focus();
                return false;
            }
            if (!Uri.TryCreate(baseUrl, UriKind.Absolute, out var u) || !(u.Scheme == Uri.UriSchemeHttp || u.Scheme == Uri.UriSchemeHttps))
            {
                MessageBox.Show("Base URL inválida. Debe ser http/https.", "Configuración", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                _baseUrl.Focus();
                return false;
            }

            var derived = DeriveApiBaseUrlFromTenantBaseUrl(baseUrl);
            if (!string.Equals(derived, baseUrl, StringComparison.OrdinalIgnoreCase) && !string.IsNullOrWhiteSpace(derived))
            {
                try
                {
                    var r = MessageBox.Show(
                        $"La Base URL parece ser la web (no la API).\n\nSugerida: {derived}\n\n¿Usar la sugerida?",
                        "Configuración",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Question
                    );
                    if (r == DialogResult.Yes)
                    {
                        _baseUrl.Text = derived;
                    }
                }
                catch
                {
                }
            }

            var deviceId = _deviceId.Text.Trim();
            if (string.IsNullOrWhiteSpace(deviceId))
            {
                MessageBox.Show("Falta Device ID.", "Configuración", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                _deviceId.Focus();
                return false;
            }
            return true;
        }
        catch
        {
            return true;
        }
    }

    private void UpdateStatus()
    {
        var ok = !string.IsNullOrWhiteSpace(_cfg.BaseUrl) && !string.IsNullOrWhiteSpace(_cfg.Tenant) && !string.IsNullOrWhiteSpace(_cfg.DeviceId);
        var paired = ok && !string.IsNullOrWhiteSpace(_cfg.Token);
        var run = _running && !_configOpen;
        _status.Text = paired ? (run ? "LISTO" : "LISTO · PAUSADO") : ok ? "FALTA PAIRING" : "NO CONFIGURADO";
        try
        {
            if (paired && run) _status.ForeColor = System.Drawing.Color.FromArgb(34, 197, 94);
            else if (paired && !run) _status.ForeColor = System.Drawing.Color.FromArgb(250, 204, 21);
            else if (ok && !paired) _status.ForeColor = System.Drawing.Color.FromArgb(251, 146, 60);
            else _status.ForeColor = System.Drawing.Color.FromArgb(248, 113, 113);
        }
        catch
        {
        }
        var detail = new StringBuilder();
        if (!ok)
        {
            var miss = new System.Collections.Generic.List<string>();
            if (string.IsNullOrWhiteSpace(_cfg.Tenant)) miss.Add("tenant");
            if (string.IsNullOrWhiteSpace(_cfg.BaseUrl)) miss.Add("base url");
            if (string.IsNullOrWhiteSpace(_cfg.DeviceId)) miss.Add("device id");
            detail.Append("Completar: ").Append(string.Join(", ", miss)).Append(". ");
            detail.Append("Abrir Configuración y usar Pegar si copiás desde Gestión.");
        }
        else if (!paired)
        {
            detail.Append("Config OK. Falta Pairing (token). ");
            detail.Append("Usar Pairing code desde Gestión y presionar Pair.");
        }
        else
        {
            detail.Append("Tenant ").Append(_cfg.Tenant ?? "").Append(" · Device ").Append(_cfg.DeviceId ?? "").Append(" · API ").Append(_cfg.BaseUrl ?? "");
            if (_cfg.DeviceSucursalId.HasValue)
            {
                detail.Append(" · Sucursal #").Append(_cfg.DeviceSucursalId.Value);
            }
        }
        if (_blockedUntilUtc.HasValue && DateTimeOffset.UtcNow < _blockedUntilUtc.Value)
        {
            var sec = Math.Max(1, (int)Math.Ceiling((_blockedUntilUtc.Value - DateTimeOffset.UtcNow).TotalSeconds));
            detail.Append(" · Rate limit ").Append(sec).Append("s");
        }
        if (paired && IsApiBlocked(out var why, out var waitSec))
        {
            detail.Append(" · API ").Append(why).Append(' ').Append(waitSec).Append("s");
        }
        var q = GetOfflineQueueStats();
        if (q.HasValue)
        {
            detail.Append(" · Cola ").Append(q.Value.lines).Append(" líneas");
            if (q.Value.bytes > 0) detail.Append(" · ").Append(Math.Max(0, q.Value.bytes / 1024)).Append("KB");
        }
        if (_lastApiOkUtc.HasValue)
        {
            var sec = (DateTimeOffset.UtcNow - _lastApiOkUtc.Value).TotalSeconds;
            detail.Append(" · API OK hace ").Append(Math.Max(0, (int)Math.Round(sec))).Append("s");
        }
        else if (!string.IsNullOrWhiteSpace(_lastApiError))
        {
            detail.Append(" · API ").Append(_lastApiError);
        }
        _statusDetail.Text = detail.ToString();
        _runBtn.Text = (_running ? "Pausar" : "Reanudar");
    }

    private void ToggleRun()
    {
        _running = !_running;
        if (_running)
        {
            if (!_configOpen) StartInput();
            _commandPollTimer.Start();
            _flushQueueTimer.Start();
            FocusCapture();
        }
        else
        {
            StopInput();
            _commandPollTimer.Stop();
            _flushQueueTimer.Stop();
        }
        UpdateStatus();
    }

    private bool IsApiBlocked(out string reason, out int seconds)
    {
        reason = "";
        seconds = 0;
        var now = DateTimeOffset.UtcNow;
        if (_apiCircuitUntilUtc.HasValue && now < _apiCircuitUntilUtc.Value)
        {
            reason = "circuit";
            seconds = Math.Max(1, (int)Math.Ceiling((_apiCircuitUntilUtc.Value - now).TotalSeconds));
            return true;
        }
        if (_apiBackoffUntilUtc.HasValue && now < _apiBackoffUntilUtc.Value)
        {
            reason = "backoff";
            seconds = Math.Max(1, (int)Math.Ceiling((_apiBackoffUntilUtc.Value - now).TotalSeconds));
            return true;
        }
        return false;
    }

    private int CalcBackoffSeconds(int failCount)
    {
        var exp = Math.Min(6, Math.Max(0, failCount));
        var baseSec = Math.Pow(2, exp);
        var jitter = 0.75 + (_rng.NextDouble() * 0.5);
        var sec = baseSec * jitter;
        return Math.Clamp((int)Math.Ceiling(sec), 1, 60);
    }

    private void RegisterApiFailure()
    {
        _apiFailCount = Math.Min(_apiFailCount + 1, 10);
        var now = DateTimeOffset.UtcNow;
        var backoff = CalcBackoffSeconds(_apiFailCount);
        _apiBackoffUntilUtc = now.AddSeconds(backoff);
        if (_apiFailCount >= 5)
        {
            _apiCircuitUntilUtc = now.AddSeconds(Math.Clamp(backoff * 2, 20, 300));
        }
        UpdateStatus();
    }

    private void ResetApiFailure()
    {
        _apiFailCount = 0;
        _apiBackoffUntilUtc = null;
        _apiCircuitUntilUtc = null;
    }

    private void ResetDisplay()
    {
        try
        {
            _dispDecision.Text = "ESPERANDO LECTURA…";
            _dispDecision.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
            _dispUser.Text = "";
            _dispMembership.Text = "";
            _dispReason.Text = "Escaneá llavero/QR o tipeá DNI + Enter.";
            _dispAction.Text = "";
            _dispInput.Text = "";
            _dispMeta.Text = "";
        }
        catch
        {
        }
    }

    private void UpdateDisplayFromApi(JsonElement root, string decision, string reason, bool unlock, int unlockMs)
    {
        var dec = (decision ?? "").Trim().ToLowerInvariant();
        var ok = string.Equals(dec, "allow", StringComparison.OrdinalIgnoreCase);

        try
        {
            _dispDecision.Text = ok ? "ACCESO PERMITIDO" : "ACCESO DENEGADO";
            _dispDecision.ForeColor = ok ? System.Drawing.Color.FromArgb(34, 197, 94) : System.Drawing.Color.FromArgb(248, 113, 113);
        }
        catch
        {
        }

        string inputKind = "";
        string inputMasked = "";
        string ts = "";
        JsonElement user = default;
        var hasUser = false;

        if (root.TryGetProperty("display", out var disp) && disp.ValueKind == JsonValueKind.Object)
        {
            if (disp.TryGetProperty("ts", out var t) && t.ValueKind == JsonValueKind.String) ts = t.GetString() ?? "";
            if (disp.TryGetProperty("input", out var inp) && inp.ValueKind == JsonValueKind.Object)
            {
                if (inp.TryGetProperty("kind", out var k) && k.ValueKind == JsonValueKind.String) inputKind = k.GetString() ?? "";
                if (inp.TryGetProperty("value_masked", out var vm) && vm.ValueKind == JsonValueKind.String) inputMasked = vm.GetString() ?? "";
            }
            if (disp.TryGetProperty("user", out var u) && u.ValueKind == JsonValueKind.Object)
            {
                user = u;
                hasUser = true;
            }
        }

        try
        {
            _dispReason.Text = string.IsNullOrWhiteSpace(reason) ? (ok ? "OK" : "No autorizado") : reason;
            _dispReason.ForeColor = ok ? System.Drawing.Color.FromArgb(226, 232, 240) : System.Drawing.Color.FromArgb(251, 146, 60);
        }
        catch
        {
        }

        try
        {
            var action = GetSuggestedAction(root, reason, ok, hasUser);
            _dispAction.Text = string.IsNullOrWhiteSpace(action) ? "" : $"Acción sugerida: {action}";
            _dispAction.ForeColor = ok ? System.Drawing.Color.FromArgb(148, 163, 184) : System.Drawing.Color.FromArgb(251, 146, 60);
        }
        catch
        {
        }

        if (!string.IsNullOrWhiteSpace(inputKind) || !string.IsNullOrWhiteSpace(inputMasked))
        {
            try
            {
                var kindLabel = string.IsNullOrWhiteSpace(inputKind) ? "input" : inputKind;
                _dispInput.Text = $"Entrada ({kindLabel}): {inputMasked}";
            }
            catch
            {
            }
        }

        if (hasUser)
        {
            var nombre = user.TryGetProperty("nombre", out var n) && n.ValueKind == JsonValueKind.String ? (n.GetString() ?? "") : "";
            var dni = user.TryGetProperty("dni", out var dn) && dn.ValueKind == JsonValueKind.String ? (dn.GetString() ?? "") : "";
            var rol = user.TryGetProperty("rol", out var rl) && rl.ValueKind == JsonValueKind.String ? (rl.GetString() ?? "") : "";
            var activo = user.TryGetProperty("activo", out var ac) && (ac.ValueKind == JsonValueKind.True || ac.ValueKind == JsonValueKind.False) ? ac.GetBoolean() : true;
            var exento = user.TryGetProperty("exento", out var ex) && (ex.ValueKind == JsonValueKind.True || ex.ValueKind == JsonValueKind.False) ? ex.GetBoolean() : false;
            var cuotasV = user.TryGetProperty("cuotas_vencidas", out var cv) && cv.ValueKind == JsonValueKind.Number ? cv.GetInt32() : 0;
            var tipo = user.TryGetProperty("tipo_cuota_nombre", out var tc) && tc.ValueKind == JsonValueKind.String ? (tc.GetString() ?? "") : "";
            var fpv = user.TryGetProperty("fecha_proximo_vencimiento", out var fv) && fv.ValueKind == JsonValueKind.String ? (fv.GetString() ?? "") : "";
            var dias = user.TryGetProperty("dias_restantes", out var dr) && dr.ValueKind == JsonValueKind.Number ? dr.GetInt32() : (int?)null;
            var cuotaStatus = user.TryGetProperty("cuota_status", out var cs) && cs.ValueKind == JsonValueKind.String ? (cs.GetString() ?? "") : "";
            var cuotaBadge = user.TryGetProperty("cuota_badge", out var cb) && cb.ValueKind == JsonValueKind.String ? (cb.GetString() ?? "") : "";

            try
            {
                var idTxt = "";
                if (user.TryGetProperty("id", out var uid) && uid.ValueKind == JsonValueKind.Number)
                {
                    idTxt = $" #{uid.GetInt32()}";
                }
                var rolTxt = string.IsNullOrWhiteSpace(rol) ? "" : $" · {rol}";
                var dniTxt = string.IsNullOrWhiteSpace(dni) ? "" : $" · DNI {dni}";
                _dispUser.Text = $"{(string.IsNullOrWhiteSpace(nombre) ? "Usuario" : nombre)}{idTxt}{dniTxt}{rolTxt}";
            }
            catch
            {
            }

            try
            {
                var status = string.IsNullOrWhiteSpace(cuotaStatus) ? "" : cuotaStatus;
                if (string.IsNullOrWhiteSpace(status))
                {
                    if (!activo) status = "INACTIVO";
                    else if (exento) status = "EXENTO";
                    else if (dias.HasValue)
                    {
                        if (dias.Value < 0) status = "VENCIDA";
                        else if (dias.Value <= 3) status = "POR_VENCER";
                        else status = "AL_DIA";
                    }
                    else if (!string.IsNullOrWhiteSpace(fpv)) status = "AL_DIA";
                    else status = "SIN_INFO";
                }

                var sb = new StringBuilder();
                sb.Append("Cuota: ").Append(string.IsNullOrWhiteSpace(tipo) ? "—" : tipo).Append(" · ").Append(status);
                if (!string.IsNullOrWhiteSpace(fpv)) sb.Append("\nVence: ").Append(fpv);
                if (dias.HasValue) sb.Append(" · Días: ").Append(dias.Value);
                sb.Append("\nMoras: ").Append(cuotasV).Append(" (máx 3)");
                _dispMembership.Text = sb.ToString();
                try
                {
                    var b = (cuotaBadge ?? "").Trim().ToLowerInvariant();
                    if (b == "danger") _dispMembership.ForeColor = System.Drawing.Color.FromArgb(248, 113, 113);
                    else if (b == "warn") _dispMembership.ForeColor = System.Drawing.Color.FromArgb(251, 146, 60);
                    else if (b == "ok") _dispMembership.ForeColor = System.Drawing.Color.FromArgb(34, 197, 94);
                    else _dispMembership.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                catch
                {
                }
            }
            catch
            {
            }
        }
        else
        {
            try
            {
                _dispUser.Text = "";
                _dispMembership.Text = "";
            }
            catch
            {
            }
        }

        try
        {
            var openTxt = unlock && ok ? $"Molinete: ABRIR ({unlockMs}ms)" : "Molinete: —";
            var tTxt = string.IsNullOrWhiteSpace(ts) ? "" : $" · {ts}";
            _dispMeta.Text = $"{openTxt}{tTxt}";
        }
        catch
        {
        }

        try
        {
            AddHistoryItem(ts, inputMasked, hasUser ? _dispUser.Text : "", ok ? "ALLOW" : "DENY", reason);
        }
        catch
        {
        }
    }

    private string GetSuggestedAction(JsonElement root, string reason, bool ok, bool hasUser)
    {
        if (ok) return "";
        try
        {
            if (root.TryGetProperty("display", out var disp) && disp.ValueKind == JsonValueKind.Object)
            {
                if (disp.TryGetProperty("suggested_action", out var sa) && sa.ValueKind == JsonValueKind.String)
                {
                    var v = sa.GetString() ?? "";
                    if (!string.IsNullOrWhiteSpace(v)) return v.Trim();
                }
            }
        }
        catch
        {
        }
        var r = (reason ?? "").Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(r)) return hasUser ? "Verificar estado del usuario" : "Verificar credencial";
        if (r.Contains("falta de pagos") || r.Contains("cuota") || r.Contains("vencid")) return "Cuota vencida → pasar por recepción";
        if (r.Contains("administración")) return "Derivar a administración";
        if (r.Contains("membresía") || r.Contains("sucursal")) return "Verificar membresía/sucursal";
        if (r.Contains("fuera de horario")) return "Verificar horarios permitidos";
        if (r.Contains("rate limit")) return "Esperar y reintentar";
        if (r.Contains("token expirado")) return "Reemitir QR";
        if (r.Contains("token ya utilizado")) return "Solicitar nuevo QR";
        if (r.Contains("token no encontrado") || r.Contains("token inválido")) return "Verificar QR";
        if (r.Contains("dni inválido") || r.Contains("dni no encontrado")) return "Verificar DNI o registrar";
        if (r.Contains("usuario no encontrado") || r.Contains("usuario inválido")) return "Verificar registro del usuario";
        if (r.Contains("device no asociado")) return "Asignar sucursal al dispositivo";
        if (r.Contains("enroll no activo")) return "Activar enroll en Gestión";
        return hasUser ? "Verificar estado del usuario" : "Verificar credencial";
    }

    private void AddHistoryItem(string ts, string inputMasked, string user, string decision, string reason)
    {
        if (_history.Columns.Count >= 5)
        {
            var time = "";
            try
            {
                if (!string.IsNullOrWhiteSpace(ts) && DateTimeOffset.TryParse(ts, out var dt))
                {
                    time = dt.ToLocalTime().ToString("HH:mm:ss");
                }
            }
            catch
            {
            }
            if (string.IsNullOrWhiteSpace(time))
            {
                time = DateTimeOffset.Now.ToString("HH:mm:ss");
            }
            var entry = new ListViewItem(time);
            entry.SubItems.Add((inputMasked ?? "").Trim());
            entry.SubItems.Add((user ?? "").Trim());
            entry.SubItems.Add((decision ?? "").Trim());
            entry.SubItems.Add((reason ?? "").Trim());
            try
            {
                if (string.Equals(decision, "ALLOW", StringComparison.OrdinalIgnoreCase))
                    entry.ForeColor = System.Drawing.Color.FromArgb(34, 197, 94);
                else
                    entry.ForeColor = System.Drawing.Color.FromArgb(248, 113, 113);
            }
            catch
            {
            }
            _history.Items.Insert(0, entry);
            while (_history.Items.Count > 25) _history.Items.RemoveAt(_history.Items.Count - 1);
        }
    }

    private void LayoutMain()
    {
        try
        {
            var margin = 16;
            var gap = 12;
            var top = 110;
            var rightW = 360;
            var btnW = 140;
            var btnLeft = Math.Max(margin, ClientSize.Width - margin - btnW);
            _configBtn.Left = btnLeft;
            _runBtn.Left = btnLeft;
            _clearQueueBtn.Left = btnLeft;

            _historyPanel.Left = Math.Max(margin, ClientSize.Width - margin - rightW);
            _historyPanel.Top = top;
            _historyPanel.Width = rightW;
            _historyPanel.Height = Math.Max(260, ClientSize.Height - top - margin);

            _history.Width = Math.Max(200, _historyPanel.Width - 24);
            _history.Height = Math.Max(180, _historyPanel.Height - 52);

            _display.Left = margin;
            _display.Top = top;
            _display.Height = _historyPanel.Height;
            _display.Width = Math.Max(360, _historyPanel.Left - _display.Left - gap);

            var contentW = Math.Max(200, btnLeft - margin - gap);
            _statusDetail.Width = contentW;
            _last.Width = contentW;
            _io.Width = contentW;

            var p = Controls["ConfigPanel"];
            if (p != null)
            {
                p.Left = margin;
                p.Top = top;
                p.Width = Math.Max(360, ClientSize.Width - (margin * 2));
                p.Height = Math.Max(260, ClientSize.Height - top - margin);
                if (_configOpen) p.BringToFront();
            }
        }
        catch
        {
        }
    }

    private void TickAutoResetDisplay()
    {
        try
        {
            if (_configOpen) return;
            if (!_lastScanAtUtc.HasValue) return;
            var age = (DateTimeOffset.UtcNow - _lastScanAtUtc.Value).TotalSeconds;
            var threshold = (_cfg.Fullscreen ?? false) ? 12 : 5;
            if (age < threshold) return;
            _lastScanAtUtc = null;
            ResetDisplay();
        }
        catch
        {
        }
    }

    private bool IsDuplicateSubmission(string key, DateTimeOffset nowUtc)
    {
        lock (_submitLock)
        {
            if (!string.IsNullOrWhiteSpace(_lastSubmitKey) && string.Equals(_lastSubmitKey, key, StringComparison.Ordinal) && _lastSubmitAtUtc.HasValue)
            {
                var age = (nowUtc - _lastSubmitAtUtc.Value).TotalSeconds;
                if (age >= 0 && age < 10) return true;
            }
            _lastSubmitKey = key;
            _lastSubmitAtUtc = nowUtc;
            return false;
        }
    }

    private void ClearOfflineQueue()
    {
        try
        {
            var r = MessageBox.Show(
                "Esto borra la cola offline de eventos (si había cortes de internet).\n\n¿Continuar?",
                "Limpiar cola",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning
            );
            if (r != DialogResult.Yes) return;
            _offlineQueue.RewriteLines(Array.Empty<string>());
            _last.Text = "Cola offline borrada";
            _log.Append("offline_queue_cleared");
        }
        catch (Exception ex)
        {
            _last.Text = $"No se pudo limpiar cola: {ex.Message}";
        }
        UpdateStatus();
    }

    private void CopyDiagnosticsToClipboard()
    {
        try
        {
            var logPath = Path.Combine(AgentConfig.ConfigDir(), "agent.log");
            var diag = new System.Collections.Generic.Dictionary<string, object?>
            {
                ["captured_at"] = DateTimeOffset.Now.ToString("O"),
                ["agent_version"] = GetAgentVersion(),
                ["dotnet"] = Environment.Version.ToString(),
                ["os"] = Environment.OSVersion.ToString(),
                ["machine"] = Environment.MachineName,
                ["config_open"] = _configOpen,
                ["running"] = _running,
                ["kiosk"] = !_configOpen && (_cfg.Fullscreen ?? false),
                ["config"] = new
                {
                    tenant = _cfg.Tenant ?? "",
                    base_url = _cfg.BaseUrl ?? "",
                    device_id = _cfg.DeviceId ?? "",
                    token_present = !string.IsNullOrWhiteSpace(_cfg.Token),
                    token_protected_present = !string.IsNullOrWhiteSpace(_cfg.TokenProtected),
                    device_sucursal_id = _cfg.DeviceSucursalId,
                    mode = _cfg.Mode ?? "",
                    unlock_method = _cfg.UnlockMethod ?? "",
                    unlock_url = _cfg.UnlockUrl ?? "",
                    unlock_ms = _cfg.UnlockMs,
                    unlock_tcp_host = _cfg.UnlockTcpHost ?? "",
                    unlock_tcp_port = _cfg.UnlockTcpPort,
                    unlock_serial_port = _cfg.UnlockSerialPort ?? "",
                    unlock_serial_baud = _cfg.UnlockSerialBaud,
                    input_source = _cfg.InputSource ?? "",
                    input_protocol = _cfg.InputProtocol ?? "",
                    serial_port = _cfg.SerialPort ?? "",
                    serial_baud = _cfg.SerialBaud,
                    keyboard_submit_key = _cfg.KeyboardSubmitKey ?? "",
                    keyboard_idle_submit_ms = _cfg.KeyboardIdleSubmitMs,
                    remote_commands_enabled = _cfg.RemoteCommandsEnabled,
                    remote_command_poll_ms = _cfg.RemoteCommandPollMs,
                    allow_manual_unlock = _cfg.AllowManualUnlock,
                    manual_hotkey = _cfg.ManualHotkey ?? "",
                    offline_queue_enabled = _cfg.OfflineQueueEnabled,
                    offline_queue_max_lines = _cfg.OfflineQueueMaxLines
                },
                ["runtime"] = new
                {
                    last_scan_utc = _lastScanAtUtc?.ToString("O") ?? "",
                    last_api_ok_utc = _lastApiOkUtc?.ToString("O") ?? "",
                    last_api_error = _lastApiError ?? "",
                    api_fail_count = _apiFailCount,
                    api_backoff_until_utc = _apiBackoffUntilUtc?.ToString("O") ?? "",
                    api_circuit_until_utc = _apiCircuitUntilUtc?.ToString("O") ?? "",
                    blocked_until_utc = _blockedUntilUtc?.ToString("O") ?? ""
                },
                ["paths"] = new
                {
                    config_dir = AgentConfig.ConfigDir(),
                    config_json = Path.Combine(AgentConfig.ConfigDir(), "config.json"),
                    queue_path = _queuePath,
                    log_path = logPath
                }
            };

            var q = GetOfflineQueueStats();
            if (q.HasValue)
            {
                diag["offline_queue"] = new { lines = q.Value.lines, bytes = q.Value.bytes, truncated = q.Value.truncated };
            }

            try
            {
                if (File.Exists(logPath))
                {
                    diag["log_tail"] = _log.Tail(120);
                }
            }
            catch
            {
            }

            var txt = JsonSerializer.Serialize(diag, new JsonSerializerOptions { WriteIndented = true });
            Clipboard.SetText(txt);
            _last.Text = "Diagnóstico copiado al portapapeles";
        }
        catch (Exception ex)
        {
            _last.Text = $"No se pudo copiar diagnóstico: {ex.Message}";
        }
    }

    private void PastePairingFromClipboard()
    {
        try
        {
            var txt = Clipboard.GetText() ?? "";
            if (string.IsNullOrWhiteSpace(txt))
            {
                _last.Text = "Portapapeles vacío";
                return;
            }
            var lines = txt.Replace("\r\n", "\n").Split('\n', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            foreach (var ln in lines)
            {
                var s = ln.Trim();
                if (s.StartsWith("Device ID", StringComparison.OrdinalIgnoreCase) || s.StartsWith("DeviceID", StringComparison.OrdinalIgnoreCase))
                {
                    var v = s.Contains(':') ? s.Split(':', 2)[1].Trim() : s;
                    if (!string.IsNullOrWhiteSpace(v)) _deviceId.Text = v;
                }
                else if (s.StartsWith("Código", StringComparison.OrdinalIgnoreCase) || s.StartsWith("Codigo", StringComparison.OrdinalIgnoreCase) || s.StartsWith("Pairing", StringComparison.OrdinalIgnoreCase))
                {
                    var v = s.Contains(':') ? s.Split(':', 2)[1].Trim() : s;
                    if (!string.IsNullOrWhiteSpace(v)) _pairing.Text = v;
                }
                else if (s.StartsWith("Tenant", StringComparison.OrdinalIgnoreCase))
                {
                    var v = s.Contains(':') ? s.Split(':', 2)[1].Trim() : s;
                    if (!string.IsNullOrWhiteSpace(v)) _tenant.Text = v;
                }
                else if (s.StartsWith("Base URL", StringComparison.OrdinalIgnoreCase) || s.StartsWith("BaseUrl", StringComparison.OrdinalIgnoreCase) || s.StartsWith("URL", StringComparison.OrdinalIgnoreCase))
                {
                    var v = s.Contains(':') ? s.Split(':', 2)[1].Trim() : s;
                    if (!string.IsNullOrWhiteSpace(v)) _baseUrl.Text = v;
                }
            }
            _last.Text = "Pegado desde portapapeles";
        }
        catch (Exception ex)
        {
            _last.Text = $"No se pudo pegar: {ex.Message}";
        }
    }

    private async Task ForceSyncAsync()
    {
        try
        {
            await LoadRemoteDeviceConfigAsync();
            await FlushQueueAsync();
        }
        catch
        {
        }
        UpdateStatus();
        if (!string.IsNullOrWhiteSpace(_lastApiError))
        {
            MessageBox.Show(_lastApiError, "Sync", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        else
        {
            MessageBox.Show("Sync OK", "Sync", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }

    private void UpdateEnrollmentStatus()
    {
        if (IsEnrollActive())
        {
            var uid = _cfg.EnrollUsuarioId ?? 0;
            var ct = (_cfg.EnrollCredentialType ?? "fob").ToUpperInvariant();
            _last.Text = $"ENROLL · usuario {uid} · {ct} · escaneá ahora";
        }
    }

    private void MainKeyDown(object? sender, KeyEventArgs e)
    {
        if (e.Control && e.Shift && e.KeyCode == Keys.C)
        {
            ToggleConfig();
            e.Handled = true;
            return;
        }
        if (!_configOpen && IsHotkeyMatch(e, _cfg.ManualHotkey ?? "F10"))
        {
            if (_cfg.AllowManualUnlock ?? true)
            {
                _ = SendEventAsync(new Dictionary<string, object?>
                {
                    ["event_type"] = "manual_unlock",
                    ["value"] = "",
                    ["meta"] = new System.Collections.Generic.Dictionary<string, object?>
                    {
                        ["source"] = "hotkey",
                        ["hotkey"] = _cfg.ManualHotkey ?? "F10"
                    }
                });
            }
            e.Handled = true;
        }
    }

    private static bool IsHotkeyMatch(KeyEventArgs e, string hotkey)
    {
        if (string.IsNullOrWhiteSpace(hotkey)) return false;
        var parts = hotkey.Split('+', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var wantCtrl = false;
        var wantAlt = false;
        var wantShift = false;
        Keys wantKey = Keys.None;
        foreach (var p in parts)
        {
            var s = p.Trim().ToLowerInvariant();
            if (s is "ctrl" or "control") { wantCtrl = true; continue; }
            if (s is "alt") { wantAlt = true; continue; }
            if (s is "shift") { wantShift = true; continue; }
            wantKey = s switch
            {
                "f1" => Keys.F1,
                "f2" => Keys.F2,
                "f3" => Keys.F3,
                "f4" => Keys.F4,
                "f5" => Keys.F5,
                "f6" => Keys.F6,
                "f7" => Keys.F7,
                "f8" => Keys.F8,
                "f9" => Keys.F9,
                "f10" => Keys.F10,
                "f11" => Keys.F11,
                "f12" => Keys.F12,
                _ => Keys.None
            };
        }
        if (wantKey == Keys.None) return false;
        if (wantCtrl != e.Control) return false;
        if (wantAlt != e.Alt) return false;
        if (wantShift != e.Shift) return false;
        return e.KeyCode == wantKey;
    }

    private void CaptureKeyDown(object? sender, KeyEventArgs e)
    {
        var submitKey = (_cfg.KeyboardSubmitKey ?? "enter").Trim().ToLowerInvariant();
        var isSubmit = (e.KeyCode == Keys.Enter && (submitKey == "enter" || submitKey == "")) || (e.KeyCode == Keys.Tab && submitKey == "tab");
        if (isSubmit)
        {
            var raw = _capture.Text;
            _capture.Text = "";
            _captureIdleTimer.Stop();
            e.Handled = true;
            if (!string.IsNullOrWhiteSpace(raw))
            {
                _ = HandleScanAsync(raw);
            }
            return;
        }
    }

    private async Task HandleScanAsync(string raw)
    {
        var s = ApplyInputProtocol(raw);
        if (string.IsNullOrWhiteSpace(s)) return;
        var shown = FormatInputForDisplay(s);
        var hasDniPin = TryParseDniPin(s, out var dni, out var pin);
        var kind = hasDniPin ? "dni_pin" : GuessKind(s);
        var nowUtc = DateTimeOffset.UtcNow;
        var submitKey = $"{kind}:{s}";
        if (IsDuplicateSubmission(submitKey, nowUtc))
        {
            return;
        }
        try
        {
            _lastScanAtUtc = nowUtc;
            var kindLabel = kind switch
            {
                "dni" => "dni",
                "dni_pin" => "dni+pin",
                "qr_token" => "qr",
                "credential" => "credencial",
                _ => "input"
            };
            _dispInput.Text = $"Entrada ({kindLabel}): {shown}";
            _dispInput.ForeColor = kind switch
            {
                "dni" => System.Drawing.Color.FromArgb(34, 197, 94),
                "dni_pin" => System.Drawing.Color.FromArgb(34, 197, 94),
                "qr_token" => System.Drawing.Color.FromArgb(251, 146, 60),
                _ => System.Drawing.Color.FromArgb(148, 163, 184)
            };
            _dispReason.Text = kind switch
            {
                "dni" => "Validando DNI…",
                "dni_pin" => "Validando DNI+PIN…",
                "qr_token" => "Validando QR…",
                _ => "Validando…"
            };
            _dispDecision.Text = "VALIDANDO";
            _dispDecision.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
            _dispUser.Text = "";
            _dispMembership.Text = "";
            _dispMeta.Text = "";
        }
        catch
        {
        }
        if (IsEnrollActive())
        {
            await SendEventAsync(new Dictionary<string, object?>
            {
                ["event_type"] = "enroll_credential",
                ["usuario_id"] = _cfg.EnrollUsuarioId,
                ["credential_type"] = _cfg.EnrollCredentialType ?? "fob",
                ["overwrite"] = _cfg.EnrollOverwrite ?? true,
                ["value"] = s,
                ["meta"] = new System.Collections.Generic.Dictionary<string, object?>
                {
                    ["source"] = "enroll_portal"
                }
            });
            return;
        }
        if (hasDniPin)
        {
            await SendEventAsync(new Dictionary<string, object?>
            {
                ["event_type"] = "dni_pin",
                ["dni"] = dni,
                ["pin"] = pin
            });
            return;
        }
        await SendEventAsync(new Dictionary<string, object?>
        {
            ["event_type"] = kind,
            ["value"] = s
        });
    }

    private static string MaskInputForDisplay(string s)
    {
        var t = (s ?? "").Trim();
        if (t.Length == 0) return "";
        var digits = true;
        foreach (var ch in t)
        {
            if (!char.IsDigit(ch)) { digits = false; break; }
        }
        if (digits && t.Length >= 7 && t.Length <= 9)
        {
            return new string('•', Math.Max(0, t.Length - 4)) + t[^4..];
        }
        if (t.Length <= 4) return t;
        return new string('•', Math.Max(0, t.Length - 4)) + t[^4..];
    }

    private static string FormatInputForDisplay(string s)
    {
        var t = (s ?? "").Trim();
        if (t.Length == 0) return "";
        if (TryParseDniPin(t, out var dni, out var pin))
        {
            var dniShown = dni.Length <= 3 ? dni : new string('•', Math.Max(0, dni.Length - 3)) + dni[^3..];
            return $"{dniShown}#{pin}";
        }
        return MaskInputForDisplay(t);
    }

    private bool IsEnrollActive()
    {
        if (!(_cfg.EnrollEnabled ?? false)) return false;
        var exp = (_cfg.EnrollExpiresAt ?? "").Trim();
        if (string.IsNullOrWhiteSpace(exp)) return true;
        if (DateTimeOffset.TryParse(exp, out var dt))
        {
            return dt.ToUniversalTime() > DateTimeOffset.UtcNow;
        }
        return true;
    }

    private string ApplyInputProtocol(string raw)
    {
        return AccessParsing.Apply(
            raw,
            _cfg.InputProtocol ?? "raw",
            _cfg.InputRegex ?? "",
            _cfg.UidFormat ?? "auto",
            _cfg.UidEndian ?? "auto",
            _cfg.UidBits ?? 40
        );
    }

    private static bool TryParseDniPin(string s, out string dni, out string pin)
    {
        dni = "";
        pin = "";
        var t = s.Trim();
        var idx = t.IndexOf('#');
        if (idx < 0) idx = t.IndexOf('|');
        if (idx < 0) idx = t.IndexOf(';');
        if (idx <= 0 || idx >= t.Length - 1) return false;
        var a = t[..idx].Trim();
        var b = t[(idx + 1)..].Trim();
        if (a.Length < 7 || a.Length > 9) return false;
        foreach (var ch in a) if (!char.IsDigit(ch)) return false;
        if (b.Length < 3 || b.Length > 8) return false;
        foreach (var ch in b) if (!char.IsDigit(ch)) return false;
        dni = a;
        pin = b;
        return true;
    }

    private static string GuessKind(string s)
    {
        var t = s.Trim();
        var digits = true;
        foreach (var ch in t)
        {
            if (!char.IsDigit(ch)) { digits = false; break; }
        }
        if (digits && t.Length >= 7 && t.Length <= 9) return "dni";
        if (t.Length >= 20 && t.Length <= 128) return "qr_token";
        return "credential";
    }

    private async Task PairAsync()
    {
        var tenant = _tenant.Text.Trim().ToLowerInvariant();
        var baseUrl = NormalizeBaseUrl(_baseUrl.Text);
        var deviceId = _deviceId.Text.Trim();
        var pairing = _pairing.Text.Trim();
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(pairing))
        {
            _last.Text = "Config incompleta para pairing";
            try
            {
                if (string.IsNullOrWhiteSpace(_tenant.Text)) _tenant.Focus();
                else if (string.IsNullOrWhiteSpace(_baseUrl.Text)) _baseUrl.Focus();
                else if (string.IsNullOrWhiteSpace(_deviceId.Text)) _deviceId.Focus();
                else _pairing.Focus();
            }
            catch
            {
            }
            return;
        }
        try
        {
            var (ok, token, err, usedBaseUrl) = await TryPairAsync(tenant, baseUrl, deviceId, pairing);
            if (!ok && IsLikelyHtml(err))
            {
                var derived = DeriveApiBaseUrlFromTenantBaseUrl(baseUrl);
                if (!string.Equals(derived, baseUrl, StringComparison.OrdinalIgnoreCase))
                {
                    (ok, token, err, usedBaseUrl) = await TryPairAsync(tenant, derived, deviceId, pairing);
                    if (ok)
                    {
                        _baseUrl.Text = usedBaseUrl;
                        baseUrl = usedBaseUrl;
                    }
                }
            }
            if (!ok)
            {
                var hint = IsLikelyHtml(err) ? "La Base URL parece ser la web (HTML). Usá la Base URL de la API (ej: https://api.ironhub.motiona.xyz)." : err;
                _last.Text = $"Pair error: {TruncateOneLine(hint, 220)}";
                return;
            }
            if (string.IsNullOrWhiteSpace(token))
            {
                _last.Text = "Pair fail: token vacío";
                return;
            }
            _cfg.Tenant = tenant;
            _cfg.BaseUrl = usedBaseUrl;
            _cfg.DeviceId = deviceId;
            _cfg.Token = token;
            _cfg.Save();
            UpdateStatus();
            _last.Text = "Pair OK";
            ToggleConfig(false);
            try
            {
                await LoadRemoteDeviceConfigAsync();
            }
            catch
            {
            }
        }
        catch (Exception ex)
        {
            _last.Text = $"Pair error: {ex.Message}";
        }
    }

    private async Task<(bool ok, string token, string error, string baseUrl)> TryPairAsync(string tenant, string baseUrl, string deviceId, string pairing)
    {
        var url = $"{baseUrl}/api/access/devices/pair";
        var body = JsonSerializer.Serialize(new { device_id = deviceId, pairing_code = pairing });
        var req = new HttpRequestMessage(HttpMethod.Post, url);
        req.Content = new StringContent(body, Encoding.UTF8, "application/json");
        req.Headers.Add("X-Tenant", tenant);
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
        cts.CancelAfter(TimeSpan.FromSeconds(4));
        var res = await _http.SendAsync(req, cts.Token);
        var txt = await res.Content.ReadAsStringAsync(cts.Token);
        if (!res.IsSuccessStatusCode)
        {
            var sc = (int)res.StatusCode;
            var ct = res.Content?.Headers?.ContentType?.MediaType ?? "";
            var shortBody = TruncateOneLine(txt, 220);
            var err = $"HTTP {sc} · {ct} · {shortBody}";
            return (false, "", err, baseUrl);
        }
        try
        {
            using var doc = JsonDocument.Parse(txt);
            var token = doc.RootElement.TryGetProperty("token", out var t) ? (t.GetString() ?? "") : "";
            if (string.IsNullOrWhiteSpace(token))
            {
                return (false, "", "Respuesta inválida: token vacío", baseUrl);
            }
            _log.Append("pair_ok");
            return (true, token, "", baseUrl);
        }
        catch
        {
            var ct = res.Content?.Headers?.ContentType?.MediaType ?? "";
            return (false, "", $"Respuesta inválida (no es JSON) · {ct} · {TruncateOneLine(txt, 220)}", baseUrl);
        }
    }

    private static string NormalizeBaseUrl(string raw)
    {
        var s = (raw ?? "").Trim();
        if (string.IsNullOrWhiteSpace(s)) return "";
        if (!(s.StartsWith("http://", StringComparison.OrdinalIgnoreCase) || s.StartsWith("https://", StringComparison.OrdinalIgnoreCase)))
        {
            s = "https://" + s;
        }
        try
        {
            var u = new Uri(s);
            var b = new UriBuilder(u) { Path = "", Query = "", Fragment = "" };
            return b.Uri.ToString().TrimEnd('/');
        }
        catch
        {
            return s.TrimEnd('/');
        }
    }

    private static string DeriveApiBaseUrlFromTenantBaseUrl(string baseUrl)
    {
        try
        {
            var u = new Uri(baseUrl);
            var host = (u.Host ?? "").Trim().ToLowerInvariant();
            if (string.IsNullOrWhiteSpace(host)) return baseUrl;
            var parts = host.Split('.', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return baseUrl;
            if (string.Equals(parts[0], "api", StringComparison.OrdinalIgnoreCase)) return baseUrl;
            if (string.Equals(parts[0], "localhost", StringComparison.OrdinalIgnoreCase)) return baseUrl;
            var baseHost = string.Join(".", parts.Skip(1));
            var apiHost = $"api.{baseHost}";
            var b = new UriBuilder(u) { Host = apiHost, Path = "", Query = "", Fragment = "" };
            return b.Uri.ToString().TrimEnd('/');
        }
        catch
        {
            return baseUrl;
        }
    }

    private static bool IsLikelyHtml(string txt)
    {
        var t = (txt ?? "").TrimStart();
        if (string.IsNullOrWhiteSpace(t)) return false;
        return t.StartsWith("<!DOCTYPE", StringComparison.OrdinalIgnoreCase) || t.StartsWith("<html", StringComparison.OrdinalIgnoreCase) || t.Contains("<script", StringComparison.OrdinalIgnoreCase);
    }

    private static string TruncateOneLine(string txt, int maxLen)
    {
        var s = (txt ?? "").Replace("\r", " ").Replace("\n", " ").Trim();
        if (s.Length <= maxLen) return s;
        return s.Substring(0, Math.Max(0, maxLen - 1)).TrimEnd() + "…";
    }

    private void ApplyTheme()
    {
        try
        {
            BackColor = System.Drawing.Color.FromArgb(15, 23, 42);
            ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
            Font = new System.Drawing.Font("Segoe UI", 10.5f);
            ApplyThemeTo(Controls);
        }
        catch
        {
        }
    }

    private void DarkComboBox_DrawItem(object? sender, DrawItemEventArgs e)
    {
        if (sender is not ComboBox cb) return;
        try
        {
            var bg = e.State.HasFlag(DrawItemState.Selected)
                ? System.Drawing.Color.FromArgb(51, 65, 85)
                : System.Drawing.Color.FromArgb(15, 23, 42);
            var fg = System.Drawing.Color.FromArgb(226, 232, 240);
            using var brush = new System.Drawing.SolidBrush(bg);
            e.Graphics.FillRectangle(brush, e.Bounds);
            if (e.Index >= 0)
            {
                var text = cb.GetItemText(cb.Items[e.Index]);
                TextRenderer.DrawText(
                    e.Graphics,
                    text,
                    cb.Font,
                    e.Bounds,
                    fg,
                    TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis
                );
            }
            e.DrawFocusRectangle();
        }
        catch
        {
        }
    }

    private void ApplyThemeTo(Control.ControlCollection controls)
    {
        foreach (Control c in controls)
        {
            try
            {
                if (c is Panel)
                {
                    c.BackColor = System.Drawing.Color.FromArgb(2, 6, 23);
                    c.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is TabControl)
                {
                    c.BackColor = System.Drawing.Color.FromArgb(2, 6, 23);
                    c.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is TabPage)
                {
                    c.BackColor = System.Drawing.Color.FromArgb(2, 6, 23);
                    c.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is GroupBox)
                {
                    c.BackColor = System.Drawing.Color.FromArgb(2, 6, 23);
                    c.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is Label)
                {
                    c.BackColor = System.Drawing.Color.Transparent;
                    c.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is Button b)
                {
                    b.FlatStyle = FlatStyle.Flat;
                    b.BackColor = System.Drawing.Color.FromArgb(30, 41, 59);
                    b.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                    b.FlatAppearance.BorderColor = System.Drawing.Color.FromArgb(51, 65, 85);
                    b.FlatAppearance.BorderSize = 1;
                    b.AutoSize = false;
                    b.Height = Math.Max(b.Height, Font.Height + 16);
                    b.Padding = new Padding(10, 2, 10, 2);
                    b.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
                }
                else if (c is TextBox tb)
                {
                    tb.BackColor = System.Drawing.Color.FromArgb(15, 23, 42);
                    tb.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                    tb.BorderStyle = BorderStyle.FixedSingle;
                }
                else if (c is ComboBox cb)
                {
                    cb.BackColor = System.Drawing.Color.FromArgb(15, 23, 42);
                    cb.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                    cb.FlatStyle = FlatStyle.Flat;
                    cb.DrawMode = DrawMode.OwnerDrawFixed;
                    cb.IntegralHeight = false;
                    cb.ItemHeight = Math.Max(cb.ItemHeight, cb.Font.Height + 8);
                    cb.DrawItem -= DarkComboBox_DrawItem;
                    cb.DrawItem += DarkComboBox_DrawItem;
                }
                else if (c is CheckBox ck)
                {
                    ck.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is NumericUpDown nud)
                {
                    nud.BackColor = System.Drawing.Color.FromArgb(15, 23, 42);
                    nud.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                }
                else if (c is ListView lv)
                {
                    lv.BackColor = System.Drawing.Color.FromArgb(2, 6, 23);
                    lv.ForeColor = System.Drawing.Color.FromArgb(226, 232, 240);
                    lv.BorderStyle = BorderStyle.FixedSingle;
                    lv.Font = Font;
                }
            }
            catch
            {
            }
            if (c.HasChildren) ApplyThemeTo(c.Controls);
        }
    }

    private async Task SendEventAsync(Dictionary<string, object?> payloadObj)
    {
        if (_blockedUntilUtc.HasValue && DateTimeOffset.UtcNow < _blockedUntilUtc.Value)
        {
            var sec = (_blockedUntilUtc.Value - DateTimeOffset.UtcNow).TotalSeconds;
            _last.Text = $"RATE LIMIT · esperar {Math.Max(1, (int)Math.Ceiling(sec))}s";
            return;
        }
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            _last.Text = "No configurado o sin pairing";
            return;
        }

        var url = $"{baseUrl}/api/access/events";
        var payload = JsonSerializer.Serialize(payloadObj);
        var nonce = Guid.NewGuid().ToString("N");
        if (IsApiBlocked(out var why, out var waitSec))
        {
            EnqueueEvent(nonce, payload);
            _last.Text = why == "circuit" ? $"API EN PAUSA · {waitSec}s" : $"REINTENTO EN {waitSec}s";
            _lastApiError = why;
            try
            {
                _dispDecision.Text = "SIN CONEXIÓN";
                _dispDecision.ForeColor = System.Drawing.Color.FromArgb(251, 146, 60);
                _dispReason.Text = "API en reintento. Evento guardado.";
                _dispMeta.Text = $"Reintento en {waitSec}s";
            }
            catch
            {
            }
            UpdateStatus();
            return;
        }
        var req = new HttpRequestMessage(HttpMethod.Post, url);
        req.Content = new StringContent(payload, Encoding.UTF8, "application/json");
        req.Headers.Add("X-Tenant", tenant);
        req.Headers.Add("X-Device-Id", deviceId);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        req.Headers.Add("X-Event-Nonce", nonce);

        try
        {
            var res = await _http.SendAsync(req, _cts.Token);
            var txt = await res.Content.ReadAsStringAsync(_cts.Token);
            if (!res.IsSuccessStatusCode)
            {
                var sc = (int)res.StatusCode;
                var ct = res.Content?.Headers?.ContentType?.MediaType ?? "";
                var msg = "";
                try
                {
                    if (!string.IsNullOrWhiteSpace(txt) && txt.TrimStart().StartsWith("{"))
                    {
                        using var j = JsonDocument.Parse(txt);
                        var root = j.RootElement;
                        if (root.TryGetProperty("mensaje", out var m) && m.ValueKind == JsonValueKind.String) msg = m.GetString() ?? "";
                        if (string.IsNullOrWhiteSpace(msg) && root.TryGetProperty("detail", out var det) && det.ValueKind == JsonValueKind.String) msg = det.GetString() ?? "";
                        if (string.IsNullOrWhiteSpace(msg) && root.TryGetProperty("error", out var er) && er.ValueKind == JsonValueKind.String) msg = er.GetString() ?? "";
                    }
                }
                catch
                {
                }
                if (string.IsNullOrWhiteSpace(msg)) msg = TruncateOneLine(txt, 140);
                _last.Text = $"ERROR ({sc}) · {msg}";
                _lastApiError = $"{sc}";
                if (sc == 429)
                {
                    var retrySeconds = 10;
                    try
                    {
                        if (res.Headers.TryGetValues("Retry-After", out var vals))
                        {
                            var ra = vals is null ? "" : (System.Linq.Enumerable.FirstOrDefault(vals) ?? "");
                            if (int.TryParse(ra, out var s) && s > 0)
                            {
                                retrySeconds = Math.Clamp(s, 1, 300);
                            }
                            else if (DateTimeOffset.TryParse(ra, out var dt))
                            {
                                var diff = (dt.ToUniversalTime() - DateTimeOffset.UtcNow).TotalSeconds;
                                retrySeconds = Math.Clamp((int)Math.Ceiling(diff), 1, 300);
                            }
                        }
                    }
                    catch
                    {
                    }
                    _blockedUntilUtc = DateTimeOffset.UtcNow.AddSeconds(retrySeconds);
                    _last.Text = $"RATE LIMIT · {retrySeconds}s";
                    await TryUnlockAsync(false);
                    return;
                }
                if (sc == 401)
                {
                    try
                    {
                        _dispDecision.Text = "REQUIERE ACCIÓN";
                        _dispDecision.ForeColor = System.Drawing.Color.FromArgb(251, 146, 60);
                        _dispReason.Text = "Token inválido o expirado. Rehacer Pairing en Configuración.";
                        _dispMeta.Text = $"API {sc} · {ct}";
                    }
                    catch
                    {
                    }
                }
                if (sc >= 500 || sc == 0)
                {
                    RegisterApiFailure();
                    EnqueueEvent(nonce, payload);
                    _last.Text = "OFFLINE · encolado";
                }
                await TryUnlockAsync(false);
                return;
            }
            ResetApiFailure();
            using var doc = JsonDocument.Parse(txt);
            var decision = doc.RootElement.TryGetProperty("decision", out var d) ? (d.GetString() ?? "") : "";
            var reason = doc.RootElement.TryGetProperty("reason", out var r) ? (r.GetString() ?? "") : "";
            var unlock = doc.RootElement.TryGetProperty("unlock", out var u) && u.GetBoolean();
            var unlockMs = doc.RootElement.TryGetProperty("unlock_ms", out var um) && um.ValueKind == JsonValueKind.Number ? um.GetInt32() : (_cfg.UnlockMs ?? 2500);
            _last.Text = $"{decision.ToUpperInvariant()} · {reason}";
            _lastApiOkUtc = DateTimeOffset.UtcNow;
            _lastApiError = "";
            try
            {
                UpdateDisplayFromApi(doc.RootElement, decision, reason, unlock, unlockMs);
            }
            catch
            {
            }
            if ((_cfg.Mode ?? "validate_and_command").Trim().ToLowerInvariant() == "observe_only")
            {
                unlock = false;
            }
            if (string.Equals(reason, "ENROLLED", StringComparison.OrdinalIgnoreCase))
            {
                _cfg.EnrollEnabled = false;
                _cfg.EnrollUsuarioId = null;
                _cfg.EnrollCredentialType = "fob";
                _cfg.EnrollExpiresAt = null;
                _cfg.Save();
            }
            if (unlock)
            {
                await TryUnlockAsync(true, unlockMs);
            }
            else
            {
                await TryUnlockAsync(false);
            }
        }
        catch (Exception ex)
        {
            try
            {
                RegisterApiFailure();
                EnqueueEvent(nonce, payload);
                _last.Text = "OFFLINE · encolado";
                _lastApiError = "offline";
                _dispDecision.Text = "SIN CONEXIÓN";
                _dispDecision.ForeColor = System.Drawing.Color.FromArgb(251, 146, 60);
                _dispReason.Text = "Internet/API no disponible. Se guardó el evento para reenviar.";
                _dispMeta.Text = TruncateOneLine(ex.Message, 180);
            }
            catch
            {
                _last.Text = $"ERROR · {ex.Message}";
            }
        }
        finally
        {
            FocusCapture();
        }
    }

    private void EnqueueEvent(string nonce, string bodyJson)
    {
        try
        {
            var max = _cfg.OfflineQueueMaxLines ?? 2000;
            _offlineQueue.Enqueue(nonce, bodyJson, DateTimeOffset.UtcNow, max);
            _log.Append("offline_queue_enqueue");
        }
        catch
        {
        }
    }

    private async Task FlushQueueAsync()
    {
        if (!(_cfg.OfflineQueueEnabled ?? true)) return;
        if (IsApiBlocked(out _, out _)) return;
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }
        var lines = _offlineQueue.ReadAllLines();
        if (lines.Length == 0) return;
        var remaining = new System.Collections.Generic.List<string>();
        for (var i = 0; i < lines.Length; i++)
        {
            var ln = lines[i];
            if (string.IsNullOrWhiteSpace(ln)) continue;
            if (!_offlineQueue.TryDecodeLine(ln, out var nonce, out var bodyJson)) continue;
            var ok = await TrySendQueuedEventAsync(tenant, baseUrl, deviceId, token, nonce, bodyJson);
            if (!ok)
            {
                for (var j = i; j < lines.Length; j++)
                {
                    var keepLn = lines[j];
                    if (!string.IsNullOrWhiteSpace(keepLn)) remaining.Add(keepLn);
                }
                _log.Append("offline_queue_flush_stop");
                break;
            }
        }
        _offlineQueue.RewriteLines(remaining);
    }

    private async Task<bool> TrySendQueuedEventAsync(string tenant, string baseUrl, string deviceId, string token, string nonce, string bodyJson)
    {
        try
        {
            if (IsApiBlocked(out _, out _)) return false;
            var url = $"{baseUrl}/api/access/events";
            var req = new HttpRequestMessage(HttpMethod.Post, url);
            req.Content = new StringContent(bodyJson, Encoding.UTF8, "application/json");
            req.Headers.Add("X-Tenant", tenant);
            req.Headers.Add("X-Device-Id", deviceId);
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            req.Headers.Add("X-Event-Nonce", nonce);
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            var res = await _http.SendAsync(req, cts.Token);
            if ((int)res.StatusCode == 401 || (int)res.StatusCode == 403) return false;
            if (!res.IsSuccessStatusCode)
            {
                if ((int)res.StatusCode >= 500 || (int)res.StatusCode == 0)
                {
                    RegisterApiFailure();
                }
                return false;
            }
            ResetApiFailure();
            _lastApiOkUtc = DateTimeOffset.UtcNow;
            _lastApiError = "";
            return true;
        }
        catch
        {
            RegisterApiFailure();
            return false;
        }
    }

    private async Task LoadRemoteDeviceConfigAsync()
    {
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }

        var url = $"{baseUrl}/api/access/device/config";
        var req = new HttpRequestMessage(HttpMethod.Get, url);
        req.Headers.Add("X-Tenant", tenant);
        req.Headers.Add("X-Device-Id", deviceId);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            var res = await _http.SendAsync(req, cts.Token);
            if (!res.IsSuccessStatusCode)
            {
                _lastApiError = $"HTTP {(int)res.StatusCode}";
                UpdateStatus();
                return;
            }
            var txt = await res.Content.ReadAsStringAsync(cts.Token);
            using var doc = JsonDocument.Parse(txt);
            if (!doc.RootElement.TryGetProperty("config", out var cfgEl) || cfgEl.ValueKind != JsonValueKind.Object) return;
            var cfg = cfgEl;
            if (doc.RootElement.TryGetProperty("sucursal_id", out var sid) && sid.ValueKind == JsonValueKind.Number)
            {
                _cfg.DeviceSucursalId = sid.GetInt32();
            }

            if (cfg.TryGetProperty("unlock_ms", out var ums) && ums.ValueKind == JsonValueKind.Number)
            {
                var v = ums.GetInt32();
                _cfg.UnlockMs = Math.Clamp(v, 250, 15000);
            }
            if (cfg.TryGetProperty("allow_manual_unlock", out var am) && (am.ValueKind == JsonValueKind.True || am.ValueKind == JsonValueKind.False))
            {
                _cfg.AllowManualUnlock = am.GetBoolean();
            }
            if (cfg.TryGetProperty("manual_hotkey", out var hk) && hk.ValueKind == JsonValueKind.String)
            {
                var s = hk.GetString() ?? "";
                if (!string.IsNullOrWhiteSpace(s)) _cfg.ManualHotkey = s.Trim();
            }
            if (cfg.TryGetProperty("unlock_profile", out var up) && up.ValueKind == JsonValueKind.Object)
            {
                if (up.TryGetProperty("type", out var t) && t.ValueKind == JsonValueKind.String)
                {
                    var tp = t.GetString() ?? "";
                    if ((tp == "http_get" || tp == "http_post_json") && up.TryGetProperty("url", out var u) && u.ValueKind == JsonValueKind.String)
                    {
                        var urlStr = u.GetString() ?? "";
                        if (!string.IsNullOrWhiteSpace(urlStr)) _cfg.UnlockUrl = urlStr.Trim();
                        _cfg.UnlockMethod = tp;
                    }
                    else if (tp == "tcp")
                    {
                        if (up.TryGetProperty("host", out var h) && h.ValueKind == JsonValueKind.String) _cfg.UnlockTcpHost = (h.GetString() ?? "").Trim();
                        if (up.TryGetProperty("port", out var p) && p.ValueKind == JsonValueKind.Number) _cfg.UnlockTcpPort = p.GetInt32();
                        if (up.TryGetProperty("payload", out var pl) && pl.ValueKind == JsonValueKind.String) _cfg.UnlockTcpPayload = pl.GetString() ?? "";
                        _cfg.UnlockMethod = "tcp";
                    }
                    else if (tp == "serial")
                    {
                        if (up.TryGetProperty("serial_port", out var usp) && usp.ValueKind == JsonValueKind.String) _cfg.UnlockSerialPort = (usp.GetString() ?? "").Trim();
                        if (up.TryGetProperty("serial_baud", out var usb) && usb.ValueKind == JsonValueKind.Number) _cfg.UnlockSerialBaud = usb.GetInt32();
                        if (up.TryGetProperty("payload", out var pl) && pl.ValueKind == JsonValueKind.String) _cfg.UnlockSerialPayload = pl.GetString() ?? "";
                        _cfg.UnlockMethod = "serial";
                    }
                    else if (tp == "none")
                    {
                        _cfg.UnlockMethod = "none";
                    }
                }
            }
            if (cfg.TryGetProperty("mode", out var md) && md.ValueKind == JsonValueKind.String)
            {
                var s = (md.GetString() ?? "").Trim().ToLowerInvariant();
                if (s is "validate_and_command" or "observe_only") _cfg.Mode = s;
            }
            if (cfg.TryGetProperty("input_source", out var ins) && ins.ValueKind == JsonValueKind.String)
            {
                var s = (ins.GetString() ?? "").Trim().ToLowerInvariant();
                if (s is "keyboard" or "serial") _cfg.InputSource = s;
            }
            if (cfg.TryGetProperty("input_protocol", out var ip) && ip.ValueKind == JsonValueKind.String)
            {
                var s = (ip.GetString() ?? "").Trim().ToLowerInvariant();
                if (s is "raw" or "data" or "drt" or "str" or "regex" or "em4100") _cfg.InputProtocol = s;
            }
            if (cfg.TryGetProperty("input_regex", out var ir) && ir.ValueKind == JsonValueKind.String)
            {
                _cfg.InputRegex = (ir.GetString() ?? "").Trim();
            }
            if (cfg.TryGetProperty("serial_port", out var sp) && sp.ValueKind == JsonValueKind.String)
            {
                _cfg.SerialPort = (sp.GetString() ?? "").Trim();
            }
            if (cfg.TryGetProperty("serial_baud", out var sb) && sb.ValueKind == JsonValueKind.Number)
            {
                _cfg.SerialBaud = sb.GetInt32();
            }
            if (cfg.TryGetProperty("uid_format", out var uf) && uf.ValueKind == JsonValueKind.String)
            {
                _cfg.UidFormat = (uf.GetString() ?? "").Trim().ToLowerInvariant();
            }
            if (cfg.TryGetProperty("uid_endian", out var ue) && ue.ValueKind == JsonValueKind.String)
            {
                _cfg.UidEndian = (ue.GetString() ?? "").Trim().ToLowerInvariant();
            }
            if (cfg.TryGetProperty("uid_bits", out var ub) && ub.ValueKind == JsonValueKind.Number)
            {
                try { _cfg.UidBits = ub.GetInt32(); } catch { }
            }
            _cfg.EnrollEnabled = false;
            _cfg.EnrollUsuarioId = null;
            _cfg.EnrollCredentialType = "fob";
            _cfg.EnrollOverwrite = true;
            _cfg.EnrollExpiresAt = null;
            if (cfg.TryGetProperty("enroll_mode", out var em) && em.ValueKind == JsonValueKind.Object)
            {
                if (em.TryGetProperty("enabled", out var en) && (en.ValueKind == JsonValueKind.True || en.ValueKind == JsonValueKind.False))
                {
                    _cfg.EnrollEnabled = en.GetBoolean();
                }
                if (em.TryGetProperty("usuario_id", out var uid) && uid.ValueKind == JsonValueKind.Number)
                {
                    _cfg.EnrollUsuarioId = uid.GetInt32();
                }
                if (em.TryGetProperty("credential_type", out var ct) && ct.ValueKind == JsonValueKind.String)
                {
                    _cfg.EnrollCredentialType = (ct.GetString() ?? "").Trim().ToLowerInvariant();
                }
                if (em.TryGetProperty("overwrite", out var ow) && (ow.ValueKind == JsonValueKind.True || ow.ValueKind == JsonValueKind.False))
                {
                    _cfg.EnrollOverwrite = ow.GetBoolean();
                }
                if (em.TryGetProperty("expires_at", out var ea) && ea.ValueKind == JsonValueKind.String)
                {
                    _cfg.EnrollExpiresAt = (ea.GetString() ?? "").Trim();
                }
            }
            _deviceConfigTimer.Interval = IsEnrollActive() ? 2000 : 5000;
            _cfg.Save();
            if (!_configOpen)
            {
                if (_running) StartInput();
            }
            if (_configOpen)
            {
                ApplyConfigToUi();
            }
            UpdateEnrollmentStatus();
            await PostDeviceStatusAsync();
            _lastApiOkUtc = DateTimeOffset.UtcNow;
            _lastApiError = "";
            UpdateStatus();
        }
        catch
        {
            _lastApiError = "Error de red";
            UpdateStatus();
        }
    }

    private async Task PostDeviceStatusAsync(object? test = null)
    {
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }

        var url = $"{baseUrl}/api/access/device/status";
        var ready = IsEnrollActive() && !_configOpen;
        var payload = new System.Collections.Generic.Dictionary<string, object?>
        {
            ["enroll_ready"] = ready,
            ["input_source"] = _cfg.InputSource ?? "keyboard",
            ["input_protocol"] = _cfg.InputProtocol ?? "raw",
            ["serial_port"] = _cfg.SerialPort ?? ""
        };
        payload["agent_version"] = GetAgentVersion();
        var q = GetOfflineQueueStats();
        if (q.HasValue)
        {
            payload["offline_queue_lines"] = q.Value.lines;
            payload["offline_queue_bytes"] = q.Value.bytes;
            if (q.Value.truncated) payload["offline_queue_truncated"] = true;
        }
        if (test != null) payload["test"] = test;
        var body = JsonSerializer.Serialize(payload);
        var req = new HttpRequestMessage(HttpMethod.Post, url);
        req.Content = new StringContent(body, Encoding.UTF8, "application/json");
        req.Headers.Add("X-Tenant", tenant);
        req.Headers.Add("X-Device-Id", deviceId);
        req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            await _http.SendAsync(req, cts.Token);
        }
        catch
        {
        }
    }

    private static string GetAgentVersion()
    {
        try
        {
            var v = typeof(MainForm).Assembly.GetName().Version;
            return v?.ToString() ?? "";
        }
        catch
        {
            return "";
        }
    }

    private (int lines, long bytes, bool truncated)? GetOfflineQueueStats()
    {
        try
        {
            return _offlineQueue.GetStats(5000);
        }
        catch
        {
            return null;
        }
    }

    private async Task PollCommandsAsync()
    {
        if (_pollingCommands) return;
        if (!(_cfg.RemoteCommandsEnabled ?? true)) return;
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }
        _pollingCommands = true;
        try
        {
            var url = $"{baseUrl}/api/access/device/commands?limit=5";
            var req = new HttpRequestMessage(HttpMethod.Get, url);
            req.Headers.Add("X-Tenant", tenant);
            req.Headers.Add("X-Device-Id", deviceId);
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            var res = await _http.SendAsync(req, cts.Token);
            if (!res.IsSuccessStatusCode) return;
            var txt = await res.Content.ReadAsStringAsync(cts.Token);
            using var doc = JsonDocument.Parse(txt);
            if (!doc.RootElement.TryGetProperty("items", out var items) || items.ValueKind != JsonValueKind.Array) return;
            foreach (var it in items.EnumerateArray())
            {
                if (!it.TryGetProperty("id", out var idv) || idv.ValueKind != JsonValueKind.Number) continue;
                var id = idv.GetInt32();
                var type = it.TryGetProperty("type", out var tv) ? (tv.GetString() ?? "") : "";
                var payload = it.TryGetProperty("payload", out var pv) && pv.ValueKind == JsonValueKind.Object ? pv : default;
                await ExecuteCommandAsync(id, type, payload);
            }
        }
        catch
        {
        }
        finally
        {
            _pollingCommands = false;
        }
    }

    private async Task ExecuteCommandAsync(int commandId, string type, JsonElement payload)
    {
        if (_configOpen)
        {
            await AckCommandAsync(commandId, false, "config_open");
            return;
        }
        if (!_running)
        {
            await AckCommandAsync(commandId, false, "paused");
            return;
        }
        var t = (type ?? "").Trim().ToLowerInvariant();
        var ok = true;
        var detail = "ok";
        try
        {
            if (t == "unlock")
            {
                int? ms = null;
                try
                {
                    if (payload.ValueKind == JsonValueKind.Object && payload.TryGetProperty("unlock_ms", out var um) && um.ValueKind == JsonValueKind.Number)
                    {
                        ms = um.GetInt32();
                    }
                }
                catch
                {
                    ms = null;
                }
                await TryUnlockAsync(true, ms);
                detail = $"unlock {(ms ?? (_cfg.UnlockMs ?? 2500))}ms";
            }
            else if (t == "enroll_clear")
            {
                _cfg.EnrollEnabled = false;
                _cfg.EnrollUsuarioId = null;
                _cfg.EnrollCredentialType = "fob";
                _cfg.EnrollOverwrite = true;
                _cfg.EnrollExpiresAt = null;
                _cfg.Save();
                _deviceConfigTimer.Interval = 5000;
                _last.Text = "ENROLL cancelado";
                await PostDeviceStatusAsync();
                UpdateStatus();
                detail = "enroll_clear";
            }
            else
            {
                ok = false;
                detail = "unsupported";
            }
        }
        catch (Exception ex)
        {
            ok = false;
            detail = ex.Message;
        }
        await AckCommandAsync(commandId, ok, detail);
    }

    private async Task AckCommandAsync(int commandId, bool ok, string detail)
    {
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }
        try
        {
            var url = $"{baseUrl}/api/access/device/commands/{commandId}/ack";
            var body = JsonSerializer.Serialize(new { ok, result = new { detail } });
            var req = new HttpRequestMessage(HttpMethod.Post, url);
            req.Content = new StringContent(body, Encoding.UTF8, "application/json");
            req.Headers.Add("X-Tenant", tenant);
            req.Headers.Add("X-Device-Id", deviceId);
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            await _http.SendAsync(req, cts.Token);
        }
        catch
        {
        }
    }

    private async Task TryUnlockAsync(bool allow, int? unlockMs = null)
    {
        if (!allow) return;
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            await UnlockNowAsync(unlockMs, cts.Token);
        }
        catch
        {
        }
    }

    private async Task<(bool ok, string detail)> UnlockNowAsync(int? unlockMs, CancellationToken ct)
    {
        var method = (_cfg.UnlockMethod ?? "http_get").Trim().ToLowerInvariant();
        if (method == "none") return (false, "unlock_method=none");
        if (method == "tcp")
        {
            var host = (_cfg.UnlockTcpHost ?? "").Trim();
            var port = _cfg.UnlockTcpPort ?? 0;
            var payload = _cfg.UnlockTcpPayload ?? "";
            if (string.IsNullOrWhiteSpace(host) || port <= 0) return (false, "tcp host/port inválido");
            var bytes = OutputAdapters.ParsePayloadBytes(payload);
            await OutputAdapters.TcpSendAsync(host, port, bytes, ct);
            return (true, $"tcp {host}:{port}");
        }
        if (method == "serial")
        {
            var port = (_cfg.UnlockSerialPort ?? "").Trim();
            var baud = _cfg.UnlockSerialBaud ?? 9600;
            var payload = _cfg.UnlockSerialPayload ?? "";
            if (string.IsNullOrWhiteSpace(port)) return (false, "serial port vacío");
            OutputAdapters.SerialSend(port, baud, payload);
            return (true, $"serial {port}@{baud}");
        }
        if (method == "http_post_json")
        {
            var url = (_cfg.UnlockUrl ?? "").Trim();
            if (string.IsNullOrWhiteSpace(url)) return (false, "http_post_json url vacío");
            var ms = unlockMs ?? (_cfg.UnlockMs ?? 2500);
            var sc = await OutputAdapters.HttpPostJsonAsync(_http, url, new { action = "unlock", ms }, ct);
            return (sc >= 200 && sc < 300, $"http_post_json status={sc}");
        }
        {
            var url = (_cfg.UnlockUrl ?? "").Trim();
            if (string.IsNullOrWhiteSpace(url)) return (false, "http_get url vacío");
            var sc = await OutputAdapters.HttpGetAsync(_http, url, ct);
            return (sc >= 200 && sc < 300, $"http_get status={sc}");
        }
    }

    private async Task RunApiConnectivityTestAsync()
    {
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            _last.Text = "Test API: faltan Tenant/BaseUrl/DeviceId/Token";
            return;
        }
        try
        {
            var url = $"{baseUrl}/api/access/device/config";
            var req = new HttpRequestMessage(HttpMethod.Get, url);
            req.Headers.Add("X-Tenant", tenant);
            req.Headers.Add("X-Device-Id", deviceId);
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            var res = await _http.SendAsync(req, cts.Token);
            var sc = (int)res.StatusCode;
            if (!res.IsSuccessStatusCode)
            {
                _last.Text = $"Test API: {sc}";
                await PostDeviceStatusAsync(new { kind = "api", ok = false, detail = $"status={sc}" });
                return;
            }
            var txt = await res.Content.ReadAsStringAsync(cts.Token);
            var detail = $"status={sc}";
            try
            {
                using var doc = JsonDocument.Parse(txt);
                if (doc.RootElement.TryGetProperty("config", out var cfg) && cfg.ValueKind == JsonValueKind.Object)
                {
                    if (cfg.TryGetProperty("config_version", out var cv) && cv.ValueKind == JsonValueKind.Number)
                    {
                        detail = $"status={sc} config_version={cv.GetInt32()}";
                    }
                }
            }
            catch
            {
            }
            _last.Text = $"Test API: OK · {detail}";
            await PostDeviceStatusAsync(new { kind = "api", ok = true, detail });
        }
        catch (Exception ex)
        {
            _last.Text = $"Test API error: {ex.Message}";
            await PostDeviceStatusAsync(new { kind = "api", ok = false, detail = ex.Message });
        }
    }

    private async Task RunUnlockByModeTestAsync()
    {
        var mode = (_cfg.Mode ?? "validate_and_command").Trim().ToLowerInvariant();
        if (mode == "observe_only")
        {
            _last.Text = "Test acción: observe_only (no ejecuta unlock)";
            await PostDeviceStatusAsync(new { kind = "unlock_by_mode", ok = true, detail = "observe_only_skip" });
            return;
        }
        var r = MessageBox.Show(
            "Esto ejecuta la apertura usando la configuración actual (Unlock).\n\n¿Continuar?",
            "Confirmar test",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning
        );
        if (r != DialogResult.Yes) return;
        try
        {
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
            cts.CancelAfter(TimeSpan.FromSeconds(4));
            var (ok, detail) = await UnlockNowAsync(_cfg.UnlockMs, cts.Token);
            _last.Text = ok ? $"Test acción: OK · {detail}" : $"Test acción: FAIL · {detail}";
            await PostDeviceStatusAsync(new { kind = "unlock_by_mode", ok, detail });
        }
        catch (Exception ex)
        {
            _last.Text = $"Test acción error: {ex.Message}";
            await PostDeviceStatusAsync(new { kind = "unlock_by_mode", ok = false, detail = ex.Message });
        }
    }

    private async Task RunUnlockAllTestsAsync()
    {
        var r = MessageBox.Show(
            "Esto intentará abrir el molinete/puerta por múltiples métodos.\nUsar solo en modo test.\n\n¿Continuar?",
            "Confirmar tests",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning
        );
        if (r != DialogResult.Yes) return;
        _testAllBtn.Enabled = false;
        try
        {
            await RunUnlockTestAsync("http_get");
            await Task.Delay(800, _cts.Token);
            await RunUnlockTestAsync("http_post_json");
            await Task.Delay(800, _cts.Token);
            await RunUnlockTestAsync("tcp");
            await Task.Delay(800, _cts.Token);
            await RunUnlockTestAsync("serial");
        }
        catch
        {
        }
        finally
        {
            _testAllBtn.Enabled = true;
        }
    }

    private async Task RunUnlockTestAsync(string kind)
    {
        var k = (kind ?? "").Trim().ToLowerInvariant();
        var r = MessageBox.Show(
            $"Ejecutar test: {k}?\n\nEsto puede abrir el molinete/puerta.",
            "Confirmar test",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Warning
        );
        if (r != DialogResult.Yes) return;
        if (k == "http_get")
        {
            var url = _testGetUrl.Text.Trim();
            if (string.IsNullOrWhiteSpace(url)) { _last.Text = "Test GET: URL vacío"; return; }
            try
            {
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
                cts.CancelAfter(TimeSpan.FromSeconds(4));
                var sc = await OutputAdapters.HttpGetAsync(_http, url, cts.Token);
                _last.Text = $"Test GET: {sc}";
                await PostDeviceStatusAsync(new { kind = "http_get", ok = sc >= 200 && sc < 300, detail = $"status={sc}" });
            }
            catch (Exception ex)
            {
                _last.Text = $"Test GET error: {ex.Message}";
                await PostDeviceStatusAsync(new { kind = "http_get", ok = false, detail = ex.Message });
            }
            return;
        }
        if (k == "http_post_json")
        {
            var url = _testPostUrl.Text.Trim();
            if (string.IsNullOrWhiteSpace(url)) { _last.Text = "Test POST: URL vacío"; return; }
            try
            {
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
                cts.CancelAfter(TimeSpan.FromSeconds(4));
                var ms = _cfg.UnlockMs ?? 2500;
                var sc = await OutputAdapters.HttpPostJsonAsync(_http, url, new { action = "unlock", ms }, cts.Token);
                _last.Text = $"Test POST: {sc}";
                await PostDeviceStatusAsync(new { kind = "http_post_json", ok = sc >= 200 && sc < 300, detail = $"status={sc}" });
            }
            catch (Exception ex)
            {
                _last.Text = $"Test POST error: {ex.Message}";
                await PostDeviceStatusAsync(new { kind = "http_post_json", ok = false, detail = ex.Message });
            }
            return;
        }
        if (k == "tcp")
        {
            var host = _testTcpHost.Text.Trim();
            var port = (int)_testTcpPort.Value;
            var payload = _testTcpPayload.Text ?? "";
            if (string.IsNullOrWhiteSpace(host) || port <= 0) { _last.Text = "Test TCP: host/port inválido"; return; }
            try
            {
                using var cts = CancellationTokenSource.CreateLinkedTokenSource(_cts.Token);
                cts.CancelAfter(TimeSpan.FromSeconds(4));
                var bytes = OutputAdapters.ParsePayloadBytes(payload);
                await OutputAdapters.TcpSendAsync(host, port, bytes, cts.Token);
                _last.Text = "Test TCP: OK";
                await PostDeviceStatusAsync(new { kind = "tcp", ok = true, detail = $"{host}:{port}" });
            }
            catch (Exception ex)
            {
                _last.Text = $"Test TCP error: {ex.Message}";
                await PostDeviceStatusAsync(new { kind = "tcp", ok = false, detail = ex.Message });
            }
            return;
        }
        if (k == "serial")
        {
            var port = _testSerialPort.SelectedItem?.ToString() ?? "";
            var baud = (int)_testSerialBaud.Value;
            var payload = _testSerialPayload.Text ?? "";
            if (string.IsNullOrWhiteSpace(port)) { _last.Text = "Test Serial: puerto vacío"; return; }
            try
            {
                OutputAdapters.SerialSend(port, baud, payload);
                _last.Text = $"Test Serial: OK · {port}@{baud}";
                await PostDeviceStatusAsync(new { kind = "serial", ok = true, detail = $"{port}@{baud}" });
            }
            catch (Exception ex)
            {
                _last.Text = $"Test Serial error: {ex.Message}";
                await PostDeviceStatusAsync(new { kind = "serial", ok = false, detail = ex.Message });
            }
            return;
        }
        _last.Text = "Test: tipo inválido";
    }

    private sealed class AgentConfig
    {
        public string? Tenant { get; set; }
        public string? BaseUrl { get; set; }
        public string? DeviceId { get; set; }
        public string? Token { get; set; }
        public string? TokenProtected { get; set; }
        public int? DeviceSucursalId { get; set; }
        public string? Mode { get; set; }
        public string? UnlockUrl { get; set; }
        public string? UnlockMethod { get; set; }
        public int? UnlockMs { get; set; }
        public string? UnlockTcpHost { get; set; }
        public int? UnlockTcpPort { get; set; }
        public string? UnlockTcpPayload { get; set; }
        public string? UnlockSerialPort { get; set; }
        public int? UnlockSerialBaud { get; set; }
        public string? UnlockSerialPayload { get; set; }
        public bool? AllowManualUnlock { get; set; }
        public string? ManualHotkey { get; set; }
        public string? InputSource { get; set; }
        public string? SerialPort { get; set; }
        public int? SerialBaud { get; set; }
        public string? InputProtocol { get; set; }
        public string? InputRegex { get; set; }
        public string? UidFormat { get; set; }
        public string? UidEndian { get; set; }
        public int? UidBits { get; set; }
        public string? KeyboardSubmitKey { get; set; }
        public int? KeyboardIdleSubmitMs { get; set; }
        public bool? RemoteCommandsEnabled { get; set; }
        public int? RemoteCommandPollMs { get; set; }
        public bool? EnrollEnabled { get; set; }
        public int? EnrollUsuarioId { get; set; }
        public string? EnrollCredentialType { get; set; }
        public bool? EnrollOverwrite { get; set; }
        public string? EnrollExpiresAt { get; set; }
        public string? TestHttpGetUrl { get; set; }
        public string? TestHttpPostUrl { get; set; }
        public string? TestTcpHost { get; set; }
        public int? TestTcpPort { get; set; }
        public string? TestTcpPayload { get; set; }
        public string? TestSerialPort { get; set; }
        public int? TestSerialBaud { get; set; }
        public string? TestSerialPayload { get; set; }
        public bool? Fullscreen { get; set; }
        public bool? OfflineQueueEnabled { get; set; }
        public int? OfflineQueueMaxLines { get; set; }

        public static string ConfigDir()
        {
            var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "IronHubAccessAgent");
            Directory.CreateDirectory(dir);
            return dir;
        }

        private static string ConfigPath()
        {
            return Path.Combine(ConfigDir(), "config.json");
        }

        public static AgentConfig Load()
        {
            try
            {
                var p = ConfigPath();
                if (!File.Exists(p)) return new AgentConfig { UnlockMethod = "http_get", UnlockMs = 2500, UnlockTcpHost = "", UnlockTcpPort = 0, UnlockTcpPayload = "", UnlockSerialPort = "", UnlockSerialBaud = 9600, UnlockSerialPayload = "", Mode = "validate_and_command", AllowManualUnlock = true, ManualHotkey = "F10", InputSource = "keyboard", SerialPort = "", SerialBaud = 9600, InputProtocol = "raw", InputRegex = "", UidFormat = "auto", UidEndian = "auto", UidBits = 40, KeyboardSubmitKey = "enter", KeyboardIdleSubmitMs = 0, RemoteCommandsEnabled = true, RemoteCommandPollMs = 1000, EnrollEnabled = false, EnrollUsuarioId = null, EnrollCredentialType = "fob", EnrollOverwrite = true, EnrollExpiresAt = null, TestHttpGetUrl = "", TestHttpPostUrl = "", TestTcpHost = "", TestTcpPort = 0, TestTcpPayload = "", TestSerialPort = "", TestSerialBaud = 9600, TestSerialPayload = "", Fullscreen = false, OfflineQueueEnabled = true, OfflineQueueMaxLines = 2000 };
                var json = File.ReadAllText(p, Encoding.UTF8);
                var cfg = JsonSerializer.Deserialize<AgentConfig>(json, new JsonSerializerOptions { PropertyNameCaseInsensitive = true }) ?? new AgentConfig();
                cfg.UnlockMethod ??= "http_get";
                cfg.UnlockMs ??= 2500;
                cfg.UnlockTcpHost ??= "";
                cfg.UnlockTcpPort ??= 0;
                cfg.UnlockTcpPayload ??= "";
                cfg.UnlockSerialPort ??= "";
                cfg.UnlockSerialBaud ??= 9600;
                cfg.UnlockSerialPayload ??= "";
                cfg.Mode ??= "validate_and_command";
                cfg.AllowManualUnlock ??= true;
                cfg.ManualHotkey ??= "F10";
                cfg.InputSource ??= "keyboard";
                cfg.SerialPort ??= "";
                cfg.SerialBaud ??= 9600;
                cfg.InputProtocol ??= "raw";
                cfg.InputRegex ??= "";
                cfg.UidFormat ??= "auto";
                cfg.UidEndian ??= "auto";
                cfg.UidBits ??= 40;
                cfg.KeyboardSubmitKey ??= "enter";
                cfg.KeyboardIdleSubmitMs ??= 0;
                cfg.RemoteCommandsEnabled ??= true;
                cfg.RemoteCommandPollMs ??= 1000;
                cfg.EnrollEnabled ??= false;
                cfg.EnrollCredentialType ??= "fob";
                cfg.EnrollOverwrite ??= true;
                cfg.TestHttpGetUrl ??= "";
                cfg.TestHttpPostUrl ??= "";
                cfg.TestTcpHost ??= "";
                cfg.TestTcpPort ??= 0;
                cfg.TestTcpPayload ??= "";
                cfg.TestSerialPort ??= "";
                cfg.TestSerialBaud ??= 9600;
                cfg.TestSerialPayload ??= "";
                cfg.Fullscreen ??= false;
                cfg.OfflineQueueEnabled ??= true;
                cfg.OfflineQueueMaxLines ??= 2000;
                if (string.IsNullOrWhiteSpace(cfg.Token) && !string.IsNullOrWhiteSpace(cfg.TokenProtected))
                {
                    try
                    {
                        var enc = Convert.FromBase64String(cfg.TokenProtected);
                        var plain = ProtectedData.Unprotect(enc, null, DataProtectionScope.CurrentUser);
                        cfg.Token = Encoding.UTF8.GetString(plain);
                    }
                    catch
                    {
                        cfg.Token = cfg.Token ?? "";
                    }
                }
                return cfg;
            }
            catch
            {
                return new AgentConfig { UnlockMethod = "http_get", UnlockMs = 2500, UnlockTcpHost = "", UnlockTcpPort = 0, UnlockTcpPayload = "", UnlockSerialPort = "", UnlockSerialBaud = 9600, UnlockSerialPayload = "", Mode = "validate_and_command", AllowManualUnlock = true, ManualHotkey = "F10", InputSource = "keyboard", SerialPort = "", SerialBaud = 9600, InputProtocol = "raw", InputRegex = "", UidFormat = "auto", UidEndian = "auto", UidBits = 40, KeyboardSubmitKey = "enter", KeyboardIdleSubmitMs = 0, RemoteCommandsEnabled = true, RemoteCommandPollMs = 1000, EnrollEnabled = false, EnrollUsuarioId = null, EnrollCredentialType = "fob", EnrollOverwrite = true, EnrollExpiresAt = null, TestHttpGetUrl = "", TestHttpPostUrl = "", TestTcpHost = "", TestTcpPort = 0, TestTcpPayload = "", TestSerialPort = "", TestSerialBaud = 9600, TestSerialPayload = "", Fullscreen = false, OfflineQueueEnabled = true, OfflineQueueMaxLines = 2000 };
            }
        }

        public void Save()
        {
            var p = ConfigPath();
            var token = Token;
            var tokenProtected = TokenProtected;
            try
            {
                if (!string.IsNullOrWhiteSpace(token))
                {
                    var enc = ProtectedData.Protect(Encoding.UTF8.GetBytes(token), null, DataProtectionScope.CurrentUser);
                    TokenProtected = Convert.ToBase64String(enc);
                    Token = null;
                }
                var json = JsonSerializer.Serialize(this, new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(p, json, Encoding.UTF8);
            }
            finally
            {
                Token = token;
                TokenProtected = tokenProtected ?? TokenProtected;
            }
        }
    }
}
