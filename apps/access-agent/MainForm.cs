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
    private readonly CheckBox _fullscreen = new();
    private readonly CancellationTokenSource _cts = new();
    private readonly System.Windows.Forms.Timer _deviceConfigTimer = new();
    private readonly System.Windows.Forms.Timer _flushQueueTimer = new();
    private readonly System.Windows.Forms.Timer _captureIdleTimer = new();
    private readonly System.Windows.Forms.Timer _commandPollTimer = new();
    private readonly object _queueLock = new();
    private readonly string _queuePath;
    private SerialPort? _serial;
    private readonly StringBuilder _serialBuf = new();
    private bool _pollingCommands;
    private DateTimeOffset? _blockedUntilUtc;
    private readonly ToolTip _tips = new();
    private bool _running = true;
    private DateTimeOffset? _lastApiOkUtc;
    private string _lastApiError = "";

    private AgentConfig _cfg;
    private bool _configOpen;

    public MainForm()
    {
        Text = "IronHub Access Agent";
        Width = 820;
        Height = 520;
        StartPosition = FormStartPosition.CenterScreen;
        KeyPreview = true;

        _cfg = AgentConfig.Load();
        _queuePath = Path.Combine(AgentConfig.ConfigDir(), "events.ndjson");

        _status.AutoSize = true;
        _status.Top = 16;
        _status.Left = 16;
        _status.Font = new System.Drawing.Font("Segoe UI", 11, System.Drawing.FontStyle.Bold);
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

        _configBtn.Text = "Configuración";
        _configBtn.Top = 12;
        _configBtn.Left = 650;
        _configBtn.Width = 140;
        _configBtn.Click += (_, _) => ToggleConfig();
        Controls.Add(_configBtn);

        _runBtn.Text = "Pausar";
        _runBtn.Top = 44;
        _runBtn.Left = 650;
        _runBtn.Width = 140;
        _runBtn.Click += (_, _) => ToggleRun();
        Controls.Add(_runBtn);

        _clearQueueBtn.Text = "Limpiar cola";
        _clearQueueBtn.Top = 76;
        _clearQueueBtn.Left = 650;
        _clearQueueBtn.Width = 140;
        _clearQueueBtn.Click += (_, _) => ClearOfflineQueue();
        Controls.Add(_clearQueueBtn);

        _capture.Left = -2000;
        _capture.Top = -2000;
        _capture.Width = 10;
        _capture.TabStop = false;
        _capture.KeyDown += CaptureKeyDown;
        _capture.TextChanged += (_, _) =>
        {
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

        Shown += (_, _) =>
        {
            ApplyConfigToUi();
            ApplyKioskMode();
            FocusCapture();
            UpdateStatus();
            StartInput();
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

        FormClosing += (_, _) => _cts.Cancel();
        KeyDown += MainKeyDown;
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
        panel.AutoScroll = true;
        panel.Name = "ConfigPanel";
        Controls.Add(panel);

        int y = 16;
        var h1 = new Label
        {
            Left = 16,
            Top = y,
            Width = 720,
            Height = 22,
            Text = "Paso 1 · Pairing (datos desde Gestión → Accesos → Dispositivos → Pairing)",
            Font = new System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
        };
        panel.Controls.Add(h1);
        y += 28;
        panel.Controls.Add(MkLabel("Tenant (subdominio):", 16, y));
        _tenant.Left = 220;
        _tenant.Top = y - 2;
        _tenant.Width = 240;
        _tenant.PlaceholderText = "ej: testingiron";
        panel.Controls.Add(_tenant);
        _tips.SetToolTip(_tenant, "Tenant del gimnasio/sucursal. Debe coincidir con el tenant usado en la web.");

        y += 36;
        panel.Controls.Add(MkLabel("Base URL API:", 16, y));
        _baseUrl.Left = 220;
        _baseUrl.Top = y - 2;
        _baseUrl.Width = 520;
        _baseUrl.PlaceholderText = "https://TU_DOMINIO";
        panel.Controls.Add(_baseUrl);
        _tips.SetToolTip(_baseUrl, "URL base del sistema. Ej: https://app.ironhub.com");

        y += 36;
        panel.Controls.Add(MkLabel("Device ID:", 16, y));
        _deviceId.Left = 220;
        _deviceId.Top = y - 2;
        _deviceId.Width = 240;
        _deviceId.PlaceholderText = "Device ID (string) del pairing";
        panel.Controls.Add(_deviceId);
        _tips.SetToolTip(_deviceId, "Se obtiene en Gestión al crear el device.");

        _pastePairBtn.Text = "Pegar";
        _pastePairBtn.Left = 480;
        _pastePairBtn.Top = y - 3;
        _pastePairBtn.Width = 80;
        _pastePairBtn.Click += (_, _) => PastePairingFromClipboard();
        panel.Controls.Add(_pastePairBtn);
        _tips.SetToolTip(_pastePairBtn, "Pega Device ID y Código desde el portapapeles (copiado desde la web).");

        y += 36;
        panel.Controls.Add(MkLabel("Pairing code:", 16, y));
        _pairing.Left = 220;
        _pairing.Top = y - 2;
        _pairing.Width = 240;
        _pairing.PlaceholderText = "Código de pairing";
        panel.Controls.Add(_pairing);
        _tips.SetToolTip(_pairing, "Código temporal. Si vence, rotarlo desde Gestión.");

        _pairBtn.Text = "Pair";
        _pairBtn.Left = 480;
        _pairBtn.Top = y - 3;
        _pairBtn.Width = 80;
        _pairBtn.Click += async (_, _) => await PairAsync();
        panel.Controls.Add(_pairBtn);
        _tips.SetToolTip(_pairBtn, "Hace pairing y guarda el token localmente.");

        _validateBtn.Text = "Sync";
        _validateBtn.Left = 570;
        _validateBtn.Top = y - 3;
        _validateBtn.Width = 80;
        _validateBtn.Click += async (_, _) => await ForceSyncAsync();
        panel.Controls.Add(_validateBtn);
        _tips.SetToolTip(_validateBtn, "Fuerza lectura de config remota y estado.");

        y += 36;
        var h2 = new Label
        {
            Left = 16,
            Top = y,
            Width = 720,
            Height = 22,
            Text = "Paso 2 · Apertura (salida hacia molinete/puerta)",
            Font = new System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
        };
        panel.Controls.Add(h2);
        y += 28;
        panel.Controls.Add(MkLabel("Unlock URL:", 16, y));
        _unlockUrl.Left = 220;
        _unlockUrl.Top = y - 2;
        _unlockUrl.Width = 520;
        _unlockUrl.PlaceholderText = "http://RELAY_IP/unlock";
        panel.Controls.Add(_unlockUrl);
        _tips.SetToolTip(_unlockUrl, "Para HTTP GET/POST. En serial/tcp no se usa.");

        y += 36;
        panel.Controls.Add(MkLabel("Unlock method:", 16, y));
        _unlockMethod.Left = 220;
        _unlockMethod.Top = y - 2;
        _unlockMethod.Width = 240;
        _unlockMethod.DropDownStyle = ComboBoxStyle.DropDownList;
        _unlockMethod.Items.Clear();
        _unlockMethod.Items.AddRange(new object[] { "none", "http_get", "http_post_json", "tcp", "serial" });
        panel.Controls.Add(_unlockMethod);
        _tips.SetToolTip(_unlockMethod, "Cómo se dispara la apertura. En molinetes con DB25→USB suele ser 'serial'.");

        y += 36;
        panel.Controls.Add(MkLabel("TCP host:", 16, y));
        _unlockTcpHost.Left = 220;
        _unlockTcpHost.Top = y - 2;
        _unlockTcpHost.Width = 240;
        _unlockTcpHost.PlaceholderText = "192.168.1.50";
        panel.Controls.Add(_unlockTcpHost);
        panel.Controls.Add(MkLabel("TCP port:", 470, y));
        _unlockTcpPort.Left = 540;
        _unlockTcpPort.Top = y - 2;
        _unlockTcpPort.Width = 120;
        _unlockTcpPort.Minimum = 1;
        _unlockTcpPort.Maximum = 65535;
        _unlockTcpPort.Value = 9100;
        panel.Controls.Add(_unlockTcpPort);

        y += 36;
        panel.Controls.Add(MkLabel("TCP payload:", 16, y));
        _unlockTcpPayload.Left = 220;
        _unlockTcpPayload.Top = y - 2;
        _unlockTcpPayload.Width = 520;
        _unlockTcpPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01";
        panel.Controls.Add(_unlockTcpPayload);
        _tips.SetToolTip(_unlockTcpPayload, "Acepta texto (ASCII/UTF-8) o bytes hex separados por espacio.");

        y += 36;
        panel.Controls.Add(MkLabel("Serial port:", 16, y));
        _unlockSerialPort.Left = 220;
        _unlockSerialPort.Top = y - 2;
        _unlockSerialPort.Width = 160;
        _unlockSerialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        panel.Controls.Add(_unlockSerialPort);
        panel.Controls.Add(MkLabel("Serial baud:", 390, y));
        _unlockSerialBaud.Left = 470;
        _unlockSerialBaud.Top = y - 2;
        _unlockSerialBaud.Width = 120;
        _unlockSerialBaud.Minimum = 1200;
        _unlockSerialBaud.Maximum = 921600;
        _unlockSerialBaud.Increment = 1200;
        panel.Controls.Add(_unlockSerialBaud);

        y += 36;
        panel.Controls.Add(MkLabel("Serial payload:", 16, y));
        _unlockSerialPayload.Left = 220;
        _unlockSerialPayload.Top = y - 2;
        _unlockSerialPayload.Width = 520;
        _unlockSerialPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500";
        panel.Controls.Add(_unlockSerialPayload);
        _tips.SetToolTip(_unlockSerialPayload, "Texto/hex o comandos: DTR_PULSE:500 | RTS_PULSE:500 | BREAK:300");

        y += 36;
        panel.Controls.Add(MkLabel("Unlock ms:", 16, y));
        _unlockMs.Left = 220;
        _unlockMs.Top = y - 2;
        _unlockMs.Width = 120;
        _unlockMs.Minimum = 250;
        _unlockMs.Maximum = 15000;
        _unlockMs.Increment = 250;
        panel.Controls.Add(_unlockMs);

        y += 36;
        var h3 = new Label
        {
            Left = 16,
            Top = y,
            Width = 720,
            Height = 22,
            Text = "Paso 3 · Lecturas (entrada) y operación",
            Font = new System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
        };
        panel.Controls.Add(h3);
        y += 28;
        panel.Controls.Add(MkLabel("Mode:", 16, y));
        _accessMode.Left = 220;
        _accessMode.Top = y - 2;
        _accessMode.Width = 240;
        _accessMode.DropDownStyle = ComboBoxStyle.DropDownList;
        _accessMode.Items.Clear();
        _accessMode.Items.AddRange(new object[] { "validate_and_command", "observe_only" });
        panel.Controls.Add(_accessMode);
        _tips.SetToolTip(_accessMode, "validate_and_command abre el molinete cuando la API autoriza. observe_only solo registra.");

        y += 36;
        panel.Controls.Add(MkLabel("Input source:", 16, y));
        _inputSource.Left = 220;
        _inputSource.Top = y - 2;
        _inputSource.Width = 240;
        _inputSource.DropDownStyle = ComboBoxStyle.DropDownList;
        _inputSource.Items.Clear();
        _inputSource.Items.AddRange(new object[] { "keyboard", "serial" });
        panel.Controls.Add(_inputSource);
        _tips.SetToolTip(_inputSource, "keyboard: lector USB tipo teclado. serial: lector por COM.");

        y += 36;
        panel.Controls.Add(MkLabel("Serial port:", 16, y));
        _serialPort.Left = 220;
        _serialPort.Top = y - 2;
        _serialPort.Width = 160;
        _serialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        panel.Controls.Add(_serialPort);

        _refreshPortsBtn.Left = 390;
        _refreshPortsBtn.Top = y - 3;
        _refreshPortsBtn.Width = 70;
        _refreshPortsBtn.Text = "Scan";
        _refreshPortsBtn.Click += (_, _) => RefreshSerialPorts();
        panel.Controls.Add(_refreshPortsBtn);

        _serialBaud.Left = 480;
        _serialBaud.Top = y - 2;
        _serialBaud.Width = 120;
        _serialBaud.Minimum = 1200;
        _serialBaud.Maximum = 921600;
        _serialBaud.Increment = 1200;
        panel.Controls.Add(_serialBaud);

        y += 36;
        panel.Controls.Add(MkLabel("Protocol:", 16, y));
        _inputProtocol.Left = 220;
        _inputProtocol.Top = y - 2;
        _inputProtocol.Width = 240;
        _inputProtocol.DropDownStyle = ComboBoxStyle.DropDownList;
        _inputProtocol.Items.Clear();
        _inputProtocol.Items.AddRange(new object[] { "raw", "data", "drt", "str", "regex", "em4100" });
        panel.Controls.Add(_inputProtocol);

        y += 36;
        panel.Controls.Add(MkLabel("Keyboard submit:", 16, y));
        _captureSubmitKey.Left = 220;
        _captureSubmitKey.Top = y - 2;
        _captureSubmitKey.Width = 120;
        _captureSubmitKey.DropDownStyle = ComboBoxStyle.DropDownList;
        _captureSubmitKey.Items.Clear();
        _captureSubmitKey.Items.AddRange(new object[] { "enter", "tab" });
        panel.Controls.Add(_captureSubmitKey);

        _captureIdleMs.Left = 350;
        _captureIdleMs.Top = y - 2;
        _captureIdleMs.Width = 160;
        _captureIdleMs.Minimum = 0;
        _captureIdleMs.Maximum = 5000;
        _captureIdleMs.Increment = 50;
        panel.Controls.Add(_captureIdleMs);
        panel.Controls.Add(MkLabel("idle ms (0=off)", 520, y));

        y += 36;
        panel.Controls.Add(MkLabel("Remote commands:", 16, y));
        _remoteCmds.Left = 220;
        _remoteCmds.Top = y - 2;
        _remoteCmds.Width = 220;
        _remoteCmds.Text = "Habilitar polling";
        panel.Controls.Add(_remoteCmds);
        _tips.SetToolTip(_remoteCmds, "Habilita comandos remotos (unlock desde web / station auto unlock). Recomendado: ON.");

        _remotePollMs.Left = 450;
        _remotePollMs.Top = y - 2;
        _remotePollMs.Width = 120;
        _remotePollMs.Minimum = 250;
        _remotePollMs.Maximum = 10000;
        _remotePollMs.Increment = 250;
        panel.Controls.Add(_remotePollMs);
        panel.Controls.Add(MkLabel("poll ms", 580, y));

        y += 36;
        panel.Controls.Add(MkLabel("Regex (opcional):", 16, y));
        _inputRegex.Left = 220;
        _inputRegex.Top = y - 2;
        _inputRegex.Width = 520;
        _inputRegex.PlaceholderText = "Ej: UID:(\\w+)";
        panel.Controls.Add(_inputRegex);

        y += 36;
        panel.Controls.Add(MkLabel("UID format:", 16, y));
        _uidFormat.Left = 220;
        _uidFormat.Top = y - 2;
        _uidFormat.Width = 160;
        _uidFormat.DropDownStyle = ComboBoxStyle.DropDownList;
        _uidFormat.Items.Clear();
        _uidFormat.Items.AddRange(new object[] { "auto", "hex", "dec" });
        panel.Controls.Add(_uidFormat);

        _uidEndian.Left = 390;
        _uidEndian.Top = y - 2;
        _uidEndian.Width = 120;
        _uidEndian.DropDownStyle = ComboBoxStyle.DropDownList;
        _uidEndian.Items.Clear();
        _uidEndian.Items.AddRange(new object[] { "auto", "be", "le" });
        panel.Controls.Add(_uidEndian);

        _uidBits.Left = 530;
        _uidBits.Top = y - 2;
        _uidBits.Width = 120;
        _uidBits.Minimum = 16;
        _uidBits.Maximum = 128;
        _uidBits.Increment = 8;
        panel.Controls.Add(_uidBits);

        y += 36;
        panel.Controls.Add(MkLabel("Hotkey manual:", 16, y));
        _manualHotkey.Left = 220;
        _manualHotkey.Top = y - 2;
        _manualHotkey.Width = 120;
        panel.Controls.Add(_manualHotkey);

        _allowManual.Left = 350;
        _allowManual.Top = y - 2;
        _allowManual.Width = 250;
        _allowManual.Text = "Permitir apertura manual";
        panel.Controls.Add(_allowManual);

        _fullscreen.Left = 610;
        _fullscreen.Top = y - 2;
        _fullscreen.Width = 140;
        _fullscreen.Text = "Kiosk";
        panel.Controls.Add(_fullscreen);
        _tips.SetToolTip(_fullscreen, "Modo kiosco: pantalla completa y captura continua.");

        y += 48;
        var h4 = new Label
        {
            Left = 16,
            Top = y,
            Width = 720,
            Height = 22,
            Text = "Paso 4 · Pruebas (validar apertura antes de habilitar)",
            Font = new System.Drawing.Font("Segoe UI", 9, System.Drawing.FontStyle.Bold)
        };
        panel.Controls.Add(h4);
        y += 28;
        panel.Controls.Add(MkLabel("Test GET URL:", 16, y));
        _testGetUrl.Left = 220;
        _testGetUrl.Top = y - 2;
        _testGetUrl.Width = 430;
        _testGetUrl.PlaceholderText = "http://RELAY_IP/unlock";
        panel.Controls.Add(_testGetUrl);
        _testGetBtn.Left = 660;
        _testGetBtn.Top = y - 3;
        _testGetBtn.Width = 80;
        _testGetBtn.Text = "Test";
        _testGetBtn.Click += async (_, _) => await RunUnlockTestAsync("http_get");
        panel.Controls.Add(_testGetBtn);

        y += 36;
        panel.Controls.Add(MkLabel("Test POST URL:", 16, y));
        _testPostUrl.Left = 220;
        _testPostUrl.Top = y - 2;
        _testPostUrl.Width = 430;
        _testPostUrl.PlaceholderText = "http://RELAY_IP/unlock";
        panel.Controls.Add(_testPostUrl);
        _testPostBtn.Left = 660;
        _testPostBtn.Top = y - 3;
        _testPostBtn.Width = 80;
        _testPostBtn.Text = "Test";
        _testPostBtn.Click += async (_, _) => await RunUnlockTestAsync("http_post_json");
        panel.Controls.Add(_testPostBtn);

        y += 36;
        panel.Controls.Add(MkLabel("Test TCP:", 16, y));
        _testTcpHost.Left = 220;
        _testTcpHost.Top = y - 2;
        _testTcpHost.Width = 300;
        panel.Controls.Add(_testTcpHost);
        _testTcpPort.Left = 530;
        _testTcpPort.Top = y - 2;
        _testTcpPort.Width = 120;
        _testTcpPort.Minimum = 1;
        _testTcpPort.Maximum = 65535;
        _testTcpPort.Value = 9100;
        panel.Controls.Add(_testTcpPort);
        _testTcpBtn.Left = 660;
        _testTcpBtn.Top = y - 3;
        _testTcpBtn.Width = 80;
        _testTcpBtn.Text = "Test";
        _testTcpBtn.Click += async (_, _) => await RunUnlockTestAsync("tcp");
        panel.Controls.Add(_testTcpBtn);

        y += 36;
        panel.Controls.Add(MkLabel("TCP payload:", 16, y));
        _testTcpPayload.Left = 220;
        _testTcpPayload.Top = y - 2;
        _testTcpPayload.Width = 520;
        _testTcpPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01";
        panel.Controls.Add(_testTcpPayload);

        y += 36;
        panel.Controls.Add(MkLabel("Test Serial:", 16, y));
        _testSerialPort.Left = 220;
        _testSerialPort.Top = y - 2;
        _testSerialPort.Width = 160;
        _testSerialPort.DropDownStyle = ComboBoxStyle.DropDownList;
        panel.Controls.Add(_testSerialPort);
        _testSerialBaud.Left = 390;
        _testSerialBaud.Top = y - 2;
        _testSerialBaud.Width = 120;
        _testSerialBaud.Minimum = 1200;
        _testSerialBaud.Maximum = 921600;
        _testSerialBaud.Increment = 1200;
        _testSerialBaud.Value = 9600;
        panel.Controls.Add(_testSerialBaud);
        _testSerialBtn.Left = 660;
        _testSerialBtn.Top = y - 3;
        _testSerialBtn.Width = 80;
        _testSerialBtn.Text = "Test";
        _testSerialBtn.Click += async (_, _) => await RunUnlockTestAsync("serial");
        panel.Controls.Add(_testSerialBtn);

        y += 36;
        panel.Controls.Add(MkLabel("Serial payload:", 16, y));
        _testSerialPayload.Left = 220;
        _testSerialPayload.Top = y - 2;
        _testSerialPayload.Width = 520;
        _testSerialPayload.PlaceholderText = "OPEN\\n o 0xA0 0x01 0x01 o DTR_PULSE:500";
        panel.Controls.Add(_testSerialPayload);

        y += 40;
        _testAllBtn.Left = 220;
        _testAllBtn.Top = y - 3;
        _testAllBtn.Width = 160;
        _testAllBtn.Text = "Probar todos";
        _testAllBtn.Click += async (_, _) => await RunUnlockAllTestsAsync();
        panel.Controls.Add(_testAllBtn);

        y += 52;
        var save = new Button { Left = 220, Top = y, Width = 120, Text = "Guardar" };
        save.Click += (_, _) => SaveConfig();
        panel.Controls.Add(save);

        var close = new Button { Left = 350, Top = y, Width = 120, Text = "Cerrar" };
        close.Click += (_, _) => ToggleConfig(false);
        panel.Controls.Add(close);

        var hint = new Label
        {
            Left = 220,
            Top = y + 40,
            Width = 520,
            Height = 80,
            Text = "Uso: enfocá el lector y escaneá.\nDNI#PIN: 12345678#1234 + Enter.\nAtajos: Ctrl+Shift+C configuración · botón Pausar para detener lecturas.",
        };
        panel.Controls.Add(hint);
    }

    private static Label MkLabel(string t, int x, int y)
    {
        return new Label { Left = x, Top = y, Width = 190, Text = t };
    }

    private void ToggleConfig(bool? open = null)
    {
        _configOpen = open ?? !_configOpen;
        var p = Controls["ConfigPanel"];
        if (p != null) p.Visible = _configOpen;
        if (_configOpen) ApplyConfigToUi();
        if (_configOpen) StopInput();
        ApplyKioskMode();
        FocusCapture();
        if (!_configOpen && _running) StartInput();
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
        _capture.Focus();
        _capture.Select();
    }

    private void RefreshSerialPorts()
    {
        try
        {
            var ports = SerialPort.GetPortNames();
            Array.Sort(ports, StringComparer.OrdinalIgnoreCase);
            var prev = _serialPort.SelectedItem?.ToString();
            var prev2 = _testSerialPort.SelectedItem?.ToString();
            var prev3 = _unlockSerialPort.SelectedItem?.ToString();
            _serialPort.Items.Clear();
            _testSerialPort.Items.Clear();
            _unlockSerialPort.Items.Clear();
            foreach (var p in ports) _serialPort.Items.Add(p);
            foreach (var p in ports) _testSerialPort.Items.Add(p);
            foreach (var p in ports) _unlockSerialPort.Items.Add(p);
            if (!string.IsNullOrWhiteSpace(prev) && _serialPort.Items.Contains(prev)) _serialPort.SelectedItem = prev;
            if (_serialPort.SelectedItem == null && _serialPort.Items.Count > 0) _serialPort.SelectedIndex = 0;
            if (!string.IsNullOrWhiteSpace(prev2) && _testSerialPort.Items.Contains(prev2)) _testSerialPort.SelectedItem = prev2;
            if (_testSerialPort.SelectedItem == null && _testSerialPort.Items.Count > 0) _testSerialPort.SelectedIndex = 0;
            if (!string.IsNullOrWhiteSpace(prev3) && _unlockSerialPort.Items.Contains(prev3)) _unlockSerialPort.SelectedItem = prev3;
            if (_unlockSerialPort.SelectedItem == null && _unlockSerialPort.Items.Count > 0) _unlockSerialPort.SelectedIndex = 0;
        }
        catch
        {
            _serialPort.Items.Clear();
            _testSerialPort.Items.Clear();
            _unlockSerialPort.Items.Clear();
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
                    lock (_serialBuf)
                    {
                        _serialBuf.Append(s);
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
        _fullscreen.Checked = _cfg.Fullscreen ?? true;
    }

    private void SaveConfig()
    {
        _cfg.Tenant = _tenant.Text.Trim().ToLowerInvariant();
        _cfg.BaseUrl = _baseUrl.Text.Trim().TrimEnd('/');
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

    private void UpdateStatus()
    {
        var ok = !string.IsNullOrWhiteSpace(_cfg.BaseUrl) && !string.IsNullOrWhiteSpace(_cfg.Tenant) && !string.IsNullOrWhiteSpace(_cfg.DeviceId);
        var paired = ok && !string.IsNullOrWhiteSpace(_cfg.Token);
        var run = _running && !_configOpen;
        _status.Text = paired ? (run ? "LISTO" : "LISTO · PAUSADO") : ok ? "FALTA PAIRING" : "NO CONFIGURADO";
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
        var q = GetOfflineQueueStats();
        if (q.HasValue)
        {
            detail.Append(" · Cola ").Append(q.Value.lines).Append(" líneas");
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
            lock (_queueLock)
            {
                if (File.Exists(_queuePath))
                {
                    File.Delete(_queuePath);
                }
            }
            _last.Text = "Cola offline borrada";
        }
        catch (Exception ex)
        {
            _last.Text = $"No se pudo limpiar cola: {ex.Message}";
        }
        UpdateStatus();
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
        if (TryParseDniPin(s, out var dni, out var pin))
        {
            await SendEventAsync(new Dictionary<string, object?>
            {
                ["event_type"] = "dni_pin",
                ["dni"] = dni,
                ["pin"] = pin
            });
            return;
        }
        var kind = GuessKind(s);
        await SendEventAsync(new Dictionary<string, object?>
        {
            ["event_type"] = kind,
            ["value"] = s
        });
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
        var baseUrl = _baseUrl.Text.Trim().TrimEnd('/');
        var deviceId = _deviceId.Text.Trim();
        var pairing = _pairing.Text.Trim();
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(pairing))
        {
            _last.Text = "Config incompleta para pairing";
            return;
        }
        var url = $"{baseUrl}/api/access/devices/pair";
        var body = JsonSerializer.Serialize(new { device_id = deviceId, pairing_code = pairing });
        var req = new HttpRequestMessage(HttpMethod.Post, url);
        req.Content = new StringContent(body, Encoding.UTF8, "application/json");
        req.Headers.Add("X-Tenant", tenant);
        try
        {
            var res = await _http.SendAsync(req, _cts.Token);
            var txt = await res.Content.ReadAsStringAsync(_cts.Token);
            if (!res.IsSuccessStatusCode)
            {
                _last.Text = $"Pair fail: {txt}";
                return;
            }
            using var doc = JsonDocument.Parse(txt);
            var token = doc.RootElement.GetProperty("token").GetString() ?? "";
            if (string.IsNullOrWhiteSpace(token))
            {
                _last.Text = "Pair fail: token vacío";
                return;
            }
            _cfg.Tenant = tenant;
            _cfg.BaseUrl = baseUrl;
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
                _last.Text = $"ERROR ({sc})";
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
                if (sc >= 500 || sc == 0)
                {
                    EnqueueEvent(nonce, payload);
                    _last.Text = "OFFLINE · encolado";
                }
                await TryUnlockAsync(false);
                return;
            }
            using var doc = JsonDocument.Parse(txt);
            var decision = doc.RootElement.TryGetProperty("decision", out var d) ? (d.GetString() ?? "") : "";
            var reason = doc.RootElement.TryGetProperty("reason", out var r) ? (r.GetString() ?? "") : "";
            var unlock = doc.RootElement.TryGetProperty("unlock", out var u) && u.GetBoolean();
            var unlockMs = doc.RootElement.TryGetProperty("unlock_ms", out var um) && um.ValueKind == JsonValueKind.Number ? um.GetInt32() : (_cfg.UnlockMs ?? 2500);
            _last.Text = $"{decision.ToUpperInvariant()} · {reason}";
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
            _last.Text = $"ERROR · {ex.Message}";
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
            var line = JsonSerializer.Serialize(new QueuedEvent
            {
                nonce = nonce,
                body = bodyJson,
                created_at = DateTime.UtcNow.ToString("O")
            });
            lock (_queueLock)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(_queuePath)!);
                File.AppendAllText(_queuePath, line + Environment.NewLine, Encoding.UTF8);
                TrimQueueIfNeeded();
            }
        }
        catch
        {
        }
    }

    private void TrimQueueIfNeeded()
    {
        try
        {
            var max = _cfg.OfflineQueueMaxLines ?? 2000;
            max = Math.Max(100, Math.Min(max, 20000));
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

    private async Task FlushQueueAsync()
    {
        if (!(_cfg.OfflineQueueEnabled ?? true)) return;
        var tenant = _cfg.Tenant ?? "";
        var baseUrl = _cfg.BaseUrl ?? "";
        var deviceId = _cfg.DeviceId ?? "";
        var token = _cfg.Token ?? "";
        if (string.IsNullOrWhiteSpace(tenant) || string.IsNullOrWhiteSpace(baseUrl) || string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(token))
        {
            return;
        }
        string[] lines;
        lock (_queueLock)
        {
            if (!File.Exists(_queuePath)) return;
            lines = File.ReadAllLines(_queuePath, Encoding.UTF8);
        }
        if (lines.Length == 0) return;
        var remaining = new System.Collections.Generic.List<string>();
        foreach (var ln in lines)
        {
            if (string.IsNullOrWhiteSpace(ln)) continue;
            QueuedEvent? ev = null;
            try
            {
                ev = JsonSerializer.Deserialize<QueuedEvent>(ln);
            }
            catch
            {
                continue;
            }
            if (ev == null || string.IsNullOrWhiteSpace(ev.body) || string.IsNullOrWhiteSpace(ev.nonce)) continue;
            var ok = await TrySendQueuedEventAsync(tenant, baseUrl, deviceId, token, ev.nonce, ev.body);
            if (!ok)
            {
                remaining.Add(ln);
                break;
            }
        }
        lock (_queueLock)
        {
            if (remaining.Count == 0)
            {
                try { File.Delete(_queuePath); } catch { }
            }
            else
            {
                File.WriteAllLines(_queuePath, remaining, Encoding.UTF8);
            }
        }
    }

    private async Task<bool> TrySendQueuedEventAsync(string tenant, string baseUrl, string deviceId, string token, string nonce, string bodyJson)
    {
        try
        {
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
            return res.IsSuccessStatusCode;
        }
        catch
        {
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
            if (string.IsNullOrWhiteSpace(_queuePath)) return null;
            if (!File.Exists(_queuePath)) return null;
            long bytes = 0;
            try
            {
                bytes = new FileInfo(_queuePath).Length;
            }
            catch
            {
                bytes = 0;
            }
            var lines = 0;
            var truncated = false;
            using var fs = new FileStream(_queuePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            using var sr = new StreamReader(fs, Encoding.UTF8);
            while (!sr.EndOfStream && lines < 5000)
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
            var method = (_cfg.UnlockMethod ?? "http_get").Trim().ToLowerInvariant();
            if (method == "none") return;
            if (method == "tcp")
            {
                var host = (_cfg.UnlockTcpHost ?? "").Trim();
                var port = _cfg.UnlockTcpPort ?? 0;
                var payload = _cfg.UnlockTcpPayload ?? "";
                if (string.IsNullOrWhiteSpace(host) || port <= 0) return;
                var bytes = OutputAdapters.ParsePayloadBytes(payload);
                await OutputAdapters.TcpSendAsync(host, port, bytes, cts.Token);
            }
            else if (method == "serial")
            {
                var port = (_cfg.UnlockSerialPort ?? "").Trim();
                var baud = _cfg.UnlockSerialBaud ?? 9600;
                var payload = _cfg.UnlockSerialPayload ?? "";
                if (string.IsNullOrWhiteSpace(port)) return;
                OutputAdapters.SerialSend(port, baud, payload);
            }
            else if (method == "http_post_json")
            {
                var url = (_cfg.UnlockUrl ?? "").Trim();
                if (string.IsNullOrWhiteSpace(url)) return;
                var ms = unlockMs ?? (_cfg.UnlockMs ?? 2500);
                var body = JsonSerializer.Serialize(new { action = "unlock", ms });
                await _http.PostAsync(url, new StringContent(body, Encoding.UTF8, "application/json"), cts.Token);
            }
            else
            {
                var url = (_cfg.UnlockUrl ?? "").Trim();
                if (string.IsNullOrWhiteSpace(url)) return;
                await _http.GetAsync(url, cts.Token);
            }
        }
        catch
        {
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

    private static byte[] ParsePayloadBytes(string payload) => OutputAdapters.ParsePayloadBytes(payload);

    private sealed class QueuedEvent
    {
        public string nonce { get; set; } = "";
        public string body { get; set; } = "";
        public string created_at { get; set; } = "";
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
                if (!File.Exists(p)) return new AgentConfig { UnlockMethod = "http_get", UnlockMs = 2500, UnlockTcpHost = "", UnlockTcpPort = 0, UnlockTcpPayload = "", UnlockSerialPort = "", UnlockSerialBaud = 9600, UnlockSerialPayload = "", Mode = "validate_and_command", AllowManualUnlock = true, ManualHotkey = "F10", InputSource = "keyboard", SerialPort = "", SerialBaud = 9600, InputProtocol = "raw", InputRegex = "", UidFormat = "auto", UidEndian = "auto", UidBits = 40, KeyboardSubmitKey = "enter", KeyboardIdleSubmitMs = 0, RemoteCommandsEnabled = true, RemoteCommandPollMs = 1000, EnrollEnabled = false, EnrollUsuarioId = null, EnrollCredentialType = "fob", EnrollOverwrite = true, EnrollExpiresAt = null, TestHttpGetUrl = "", TestHttpPostUrl = "", TestTcpHost = "", TestTcpPort = 0, TestTcpPayload = "", TestSerialPort = "", TestSerialBaud = 9600, TestSerialPayload = "", Fullscreen = true, OfflineQueueEnabled = true, OfflineQueueMaxLines = 2000 };
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
                cfg.Fullscreen ??= true;
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
                return new AgentConfig { UnlockMethod = "http_get", UnlockMs = 2500, UnlockTcpHost = "", UnlockTcpPort = 0, UnlockTcpPayload = "", UnlockSerialPort = "", UnlockSerialBaud = 9600, UnlockSerialPayload = "", Mode = "validate_and_command", AllowManualUnlock = true, ManualHotkey = "F10", InputSource = "keyboard", SerialPort = "", SerialBaud = 9600, InputProtocol = "raw", InputRegex = "", UidFormat = "auto", UidEndian = "auto", UidBits = 40, KeyboardSubmitKey = "enter", KeyboardIdleSubmitMs = 0, RemoteCommandsEnabled = true, RemoteCommandPollMs = 1000, EnrollEnabled = false, EnrollUsuarioId = null, EnrollCredentialType = "fob", EnrollOverwrite = true, EnrollExpiresAt = null, TestHttpGetUrl = "", TestHttpPostUrl = "", TestTcpHost = "", TestTcpPort = 0, TestTcpPayload = "", TestSerialPort = "", TestSerialBaud = 9600, TestSerialPayload = "", Fullscreen = true, OfflineQueueEnabled = true, OfflineQueueMaxLines = 2000 };
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
