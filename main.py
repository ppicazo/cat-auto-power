import socket
import time
import os
import sys
from collections import deque
from datetime import datetime
from flask import Flask, request, abort, jsonify, render_template_string

ip_address = os.getenv('IP_ADDRESS')
port = os.getenv('PORT', '13013')  # Default to 13013 if PORT is not specified
target_pwr = os.getenv('TARGET_PWR')
api_key = os.getenv('API_KEY')

# Exit if no IP address or target_pwr is specified
if not ip_address:
    print("No IP address specified. Exiting...")
    sys.exit(1)

if not target_pwr:
    print("No target power specified. Exiting...")
    sys.exit(1)

try:
    port = int(port)
    target_pwr = int(target_pwr)
except ValueError:
    print("Port and Target Power must be integers. Exiting...")
    sys.exit(1)

print(f"Using IP: {ip_address}")
print(f"Using Port: {port}")
print(f"Using Target Power: {target_pwr}")

# Store historical data (up to 1000 data points)
history = deque(maxlen=1000)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cat Auto Power Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .control-panel {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="number"], input[type="password"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .current-value {
            font-size: 18px;
            color: #333;
            margin-top: 10px;
        }
        .message {
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
            display: none;
        }
        .message.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        canvas {
            max-height: 400px;
        }
    </style>
</head>
<body>
    <h1>Cat Auto Power Dashboard</h1>
    
    <div class="control-panel">
        <h2>Control Panel</h2>
        <div class="current-value">
            Current Target Power: <strong id="currentTarget">Loading...</strong> W
        </div>
        <form id="powerForm">
            <div class="form-group">
                <label for="targetPower">New Target Power (W):</label>
                <input type="number" id="targetPower" name="targetPower" min="0" required>
            </div>
            <div class="form-group">
                <label for="apiKey">API Key:</label>
                <input type="password" id="apiKey" name="apiKey" required>
            </div>
            <button type="submit">Set Target Power</button>
        </form>
        <div id="message" class="message"></div>
    </div>

    <div class="chart-container">
        <h2>Power Output History</h2>
        <canvas id="powerChart"></canvas>
    </div>

    <div class="chart-container">
        <h2>Drive Settings History</h2>
        <canvas id="driveChart"></canvas>
    </div>

    <script>
        let powerChart, driveChart;

        // Initialize charts
        function initCharts() {
            const powerCtx = document.getElementById('powerChart').getContext('2d');
            powerChart = new Chart(powerCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Power Output (W)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1
                    }, {
                        label: 'Target Power (W)',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Power (W)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        }
                    }
                }
            });

            const driveCtx = document.getElementById('driveChart').getContext('2d');
            driveChart = new Chart(driveCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Drive Setting',
                        data: [],
                        borderColor: 'rgb(153, 102, 255)',
                        backgroundColor: 'rgba(153, 102, 255, 0.1)',
                        tension: 0.1,
                        stepped: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Drive Level'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        }
                    }
                }
            });
        }

        // Fetch current target power
        function fetchCurrentTarget() {
            fetch('/api/power')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('currentTarget').textContent = data.target_power;
                })
                .catch(error => {
                    console.error('Error fetching target power:', error);
                });
        }

        // Fetch historical data
        function fetchHistory() {
            fetch('/api/history')
                .then(response => response.json())
                .then(data => {
                    const labels = data.map(item => {
                        const date = new Date(item.timestamp * 1000);
                        return date.toLocaleTimeString();
                    });
                    const powerData = data.map(item => item.power);
                    const targetData = data.map(item => item.target);
                    const driveData = data.map(item => item.drive);

                    powerChart.data.labels = labels;
                    powerChart.data.datasets[0].data = powerData;
                    powerChart.data.datasets[1].data = targetData;
                    powerChart.update('none');

                    driveChart.data.labels = labels;
                    driveChart.data.datasets[0].data = driveData;
                    driveChart.update('none');
                })
                .catch(error => {
                    console.error('Error fetching history:', error);
                });
        }

        // Handle form submission
        document.getElementById('powerForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const targetPower = document.getElementById('targetPower').value;
            const apiKey = document.getElementById('apiKey').value;
            const messageDiv = document.getElementById('message');

            fetch('/api/power', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    target_power: parseInt(targetPower),
                    api_key: apiKey
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Invalid API key or request failed');
                }
                return response.json();
            })
            .then(data => {
                messageDiv.textContent = 'Target power updated successfully!';
                messageDiv.className = 'message success';
                messageDiv.style.display = 'block';
                fetchCurrentTarget();
                document.getElementById('targetPower').value = '';
                document.getElementById('apiKey').value = '';
                setTimeout(() => {
                    messageDiv.style.display = 'none';
                }, 3000);
            })
            .catch(error => {
                messageDiv.textContent = 'Error: ' + error.message;
                messageDiv.className = 'message error';
                messageDiv.style.display = 'block';
            });
        });

        // Initialize and start periodic updates
        initCharts();
        fetchCurrentTarget();
        fetchHistory();
        setInterval(fetchHistory, 2000); // Update every 2 seconds
        setInterval(fetchCurrentTarget, 5000); // Update target every 5 seconds
    </script>
</body>
</html>
"""

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.route('/api/power', methods=['GET', 'POST'])
    def power():
        global target_pwr
        if request.method == 'GET':
            return {'target_power': target_pwr}
        elif request.method == 'POST':
            data = request.get_json()
            if 'api_key' not in data or data['api_key'] != api_key:
                abort(401)
            target_pwr = data.get('target_power')
            return {'message': 'Target power updated successfully'}

    @app.route('/api/history', methods=['GET'])
    def get_history():
        return jsonify(list(history))

    return app

def send_command(sock, command, prefix = "", suffix = "", read_response = True):
    try:
        sock.sendall((command).encode('utf-8'))
        if read_response:
             while True:  # Keep reading until a valid response is found
                response = sock.recv(1024).decode('utf-8').strip()
                # Check if the response starts with the desired prefix and process it
                if response.startswith(prefix) or response == '?;':
                    processed_response = response.removeprefix(prefix).removesuffix(suffix).strip()
                    if processed_response == '?;':
                        return ""
                    return processed_response
                else:
                    print("response ", response, " didn't start with ", prefix)
        return ""
    except socket.error as e:
        return str(e)

def main(ip, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Connect to the server
            sock.connect((ip, port))
            print("Connected to the CAT server: " + sock.recv(1024).decode('utf-8').strip())
            
            current_drive = 0  # Track current drive setting
            
            while True:
                pwr_response = send_command(sock, 'ZZRM5;', "ZZRM5", " W;")
                
                if pwr_response:
                    print("Power Output:", pwr_response, " W")
                    current_pwr = int(pwr_response)
                    
                    # Add data point to history
                    history.append({
                        'timestamp': time.time(),
                        'power': current_pwr,
                        'target': target_pwr,
                        'drive': current_drive
                    })
                    
                    if current_pwr > target_pwr or current_pwr < target_pwr:
                        current_drive_response = send_command(sock, 'ZZPC;', "ZZPC", ";")
                        if current_drive_response:
                            current_drive = int(current_drive_response)
                            if (current_drive >= 60):
                                next_drive = 10
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                                current_drive = next_drive
                            elif (current_pwr > target_pwr):
                                next_drive = current_drive - 1
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                                current_drive = next_drive
                            elif (current_pwr > 3 and current_pwr < target_pwr):
                                next_drive = current_drive + 1
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                                current_drive = next_drive
                    time.sleep(0.1)
                else:
                    time.sleep(1)
        
        except Exception as e:
            print("failed to connect or error during the session:", str(e))

if __name__ == '__main__':
    from threading import Thread
    app = create_app()
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
    flask_thread.start()
    main(ip_address, port)
