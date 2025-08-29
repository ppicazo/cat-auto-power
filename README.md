# Cat Auto Power

An automated power control system for amateur radio equipment using the CAT (Computer Aided Transceiver) protocol. This tool monitors and adjusts transmitter drive levels to maintain a target power output.

## Features

- **Automatic Power Control**: Continuously monitors and adjusts power output to match target settings
- **Robust Error Handling**: Comprehensive error handling with proper logging and graceful failure recovery
- **Safe Operation**: Built-in drive level limits and safety thresholds to prevent equipment damage
- **Docker Support**: Easy deployment using Docker containers
- **Configurable**: Environment variable-based configuration for easy deployment

## How It Works

The script connects to a CAT server and:
1. Reads current power output using the `ZZRM5` command
2. Reads current drive level using the `ZZPC` command  
3. Calculates appropriate drive adjustments based on target power
4. Sends drive level adjustments using the `ZZPC` command
5. Repeats the process in a continuous loop

### Safety Features

- **Drive Level Limits**: Enforces minimum (0) and maximum (100) drive levels
- **Reset Protection**: Automatically resets drive to safe level (10) if it exceeds 60
- **Minimum Power Threshold**: Prevents adjustments when power is below 3W to avoid instability
- **Connection Timeouts**: Prevents hanging on unresponsive servers
- **Graceful Shutdown**: Handles interrupt signals cleanly

## Requirements

- Python 3.9+ (uses only standard library modules)
- Network access to CAT server
- Compatible CAT-enabled radio equipment

## Configuration

The application is configured using environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `IP_ADDRESS` | Yes | - | IP address of the CAT server |
| `PORT` | No | 13013 | Port number of the CAT server |
| `TARGET_PWR` | Yes | - | Target power output in watts |

## Installation and Usage

### Method 1: Direct Python Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ppicazo/cat-auto-power.git
   cd cat-auto-power
   ```

2. **Set environment variables:**
   ```bash
   export IP_ADDRESS=192.168.1.100
   export PORT=13013
   export TARGET_PWR=10
   ```

3. **Run the script:**
   ```bash
   python main.py
   ```

### Method 2: Docker

1. **Build the Docker image:**
   ```bash
   docker build -t cat-auto-power .
   ```

2. **Run the container:**
   ```bash
   docker run -e IP_ADDRESS=192.168.1.100 -e PORT=13013 -e TARGET_PWR=10 cat-auto-power
   ```

### Method 3: Docker One-liner

```bash
docker run -e IP_ADDRESS=192.168.1.100 -e PORT=13013 -e TARGET_PWR=10 \
  $(docker build -q .)
```

## Examples

### Basic Usage
```bash
# Set target power to 25W on default port
IP_ADDRESS=192.168.1.100 TARGET_PWR=25 python main.py
```

### Custom Port
```bash
# Use custom port 4532
IP_ADDRESS=10.0.0.50 PORT=4532 TARGET_PWR=15 python main.py
```

### Docker with Volume Mounting (for development)
```bash
docker run -v $(pwd):/app -e IP_ADDRESS=192.168.1.100 -e TARGET_PWR=20 cat-auto-power
```

## Logging

The application uses Python's logging module with the following levels:

- **INFO**: Normal operation messages (connections, power readings, drive adjustments)
- **WARNING**: Non-critical issues (server responses, thresholds)
- **ERROR**: Serious problems (connection failures, invalid responses)
- **DEBUG**: Detailed diagnostic information (command/response details)

To enable debug logging, modify the logging level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Verify the CAT server is running
   - Check IP address and port configuration
   - Ensure network connectivity

2. **Invalid Responses** 
   - Confirm radio compatibility with CAT commands
   - Check CAT interface configuration
   - Verify command syntax for your equipment

3. **Power Oscillation**
   - Adjust the loop delay (`LOOP_DELAY` constant)
   - Check target power is achievable with current antenna/conditions
   - Verify drive level calibration

### Configuration Validation

The script validates configuration on startup:
- IP address must be provided
- Port must be between 1-65535
- Target power must be non-negative integer

## License

This project is open source. See repository for license details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with proper testing
4. Submit a pull request with clear description

## Support

For issues and questions:
- Open a GitHub issue for bugs or feature requests
- Check existing issues for known problems
- Include relevant log output and configuration details
