# SwitchBot Air Conditioner MCP Server

[![MCP](https://img.shields.io/badge/MCP-Compatible-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.8+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

Control your air conditioner through SwitchBot Hub 2 using the Model Context Protocol (MCP). Enables natural language control of AC units in AI assistants like Claude Desktop and Cursor.

## Features

- 🔌 **Power Control**: Turn AC on/off
- 🌡️ **Temperature Control**: Set temperature (16-30°C)
- 🔄 **Mode Selection**: Auto, Cool, Dry, Fan, Heat
- 💨 **Fan Speed Control**: Auto, Low, Medium, High
- 🎮 **Custom Commands**: Access advanced features (swing, turbo, sleep, etc.)
- 📊 **Room Monitoring**: Get current temperature and humidity from Hub 2
- 🔍 **Device Discovery**: List all infrared devices

## Quick Start

### Prerequisites

1. **SwitchBot Hub 2** with your AC remote configured
2. **SwitchBot API Credentials** (Token and Secret)
3. **Python 3.8+**

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/AirConditionMcp.git
   cd AirConditionMcp
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and add your credentials:
   ```env
   SWITCHBOT_TOKEN=your_token_here
   SWITCHBOT_SECRET=your_secret_here
   SWITCHBOT_AC_DEVICE_ID=your_device_id_here
   ```

4. **Test the connection:**
   ```bash
   python test_connection.py
   ```

### MCP Configuration

Add to your MCP settings file:

**Cursor** (`%APPDATA%\.cursor\mcp.json` on Windows):
```json
{
  "mcpServers": {
    "switchbot-ac": {
      "command": "python",
      "args": ["path/to/AirConditionMcp/server.py"],
      "env": {
        "SWITCHBOT_TOKEN": "your_token_here",
        "SWITCHBOT_SECRET": "your_secret_here",
        "SWITCHBOT_AC_DEVICE_ID": "your_device_id_here"
      }
    }
  }
}
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on Mac):
```json
{
  "mcpServers": {
    "switchbot-ac": {
      "command": "python",
      "args": ["/path/to/AirConditionMcp/server.py"],
      "env": {
        "SWITCHBOT_TOKEN": "your_token_here",
        "SWITCHBOT_SECRET": "your_secret_here",
        "SWITCHBOT_AC_DEVICE_ID": "your_device_id_here"
      }
    }
  }
}
```

Restart your AI assistant after configuration.

## Usage

Once configured, use natural language to control your AC:

```
"Turn on the AC at 24 degrees"
"Set AC to 22 degrees in cool mode"
"What's the room temperature?"
"Turn off the air conditioner"
"Toggle AC swing mode"
"Activate turbo cooling"
```

## Available Tools

### Basic Controls

- **`turn_ac_on(temperature, mode, fan_speed)`** - Turn on AC with settings
- **`turn_ac_off()`** - Turn off AC
- **`set_ac_temperature(temperature)`** - Change temperature
- **`set_ac_mode(mode)`** - Change operating mode
- **`set_ac_fan_speed(fan_speed)`** - Change fan speed
- **`set_ac_all_settings(power, temperature, mode, fan_speed)`** - Set everything at once

### Advanced Features

- **`send_custom_ac_command(command, parameter)`** - Send custom commands (swing, turbo, sleep, etc.)
- **`list_common_ac_commands()`** - List all available custom commands
- **`get_room_temperature()`** - Get current room temperature and humidity
- **`get_ac_devices()`** - List all infrared devices
- **`get_ac_status()`** - Get current AC status (if supported)

## Getting SwitchBot Credentials

1. Open the **SwitchBot app** on your phone
2. Go to **Profile** → **Preferences**
3. Tap **"App Version"** 10 times rapidly
4. Go back and select **Developer Options**
5. Copy your **Token** and **Secret**

See [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for detailed instructions.

## Finding Your AC Device ID

Run the test script:
```bash
python test_connection.py
```

Or use the MCP tool after setup:
```
"List my SwitchBot devices"
```

## Custom Commands

Access advanced AC features beyond basic controls:

```
"Toggle AC swing mode"          # Oscillate air direction
"Activate turbo mode"            # Maximum cooling power
"Enable sleep mode"              # Quiet night operation
"Toggle display light"           # Turn off AC display
```

See [CUSTOM_COMMANDS.md](docs/CUSTOM_COMMANDS.md) for full list.

## Deployment

### Option 1: Self-Hosted

Run the server directly:
```bash
python server.py
```

### Option 2: Docker (Coming Soon)

```bash
docker build -t switchbot-ac-mcp .
docker run -e SWITCHBOT_TOKEN=xxx -e SWITCHBOT_SECRET=xxx -e SWITCHBOT_AC_DEVICE_ID=xxx switchbot-ac-mcp
```

### Option 3: Cloud Hosting

Deploy to your preferred cloud platform. Set environment variables in your hosting service:
- `SWITCHBOT_TOKEN`
- `SWITCHBOT_SECRET`
- `SWITCHBOT_AC_DEVICE_ID`

## Troubleshooting

### "No infrared devices found"
- Add your AC remote to SwitchBot Hub 2 via the app first

### "401 Unauthorized"
- Check that your token and secret are correct
- No extra spaces at beginning or end

### "AC doesn't respond"
- Verify device ID is correct
- Ensure Hub 2 has clear line of sight to AC (5-10 meters)
- Test in SwitchBot app first

### "Status shows wrong information"
- Status reflects last command sent, not actual AC state
- Enable IR Decoding in SwitchBot app (if supported)

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more help.

## API Rate Limits

- **10,000 requests per day** per token
- About 7 requests per minute
- Consider caching status if making frequent queries

## Security

⚠️ **Important:**
- Never commit your `.env` file to version control
- Store credentials securely
- Use environment variables in production
- Rotate credentials periodically

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [SwitchBot](https://www.switch-bot.com/) for the API
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Model Context Protocol](https://modelcontextprotocol.io) by Anthropic

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/AirConditionMcp/issues)
- **SwitchBot Support**: https://support.switch-bot.com/
- **SwitchBot API Docs**: https://github.com/OpenWonderLabs/SwitchBotAPI

---

**Made with ❄️ for smart home automation**

