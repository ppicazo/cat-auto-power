import socket
import time
import os
import sys
from collections import deque
from threading import Lock
from flask import Flask, request, abort, jsonify, send_from_directory

ip_address = os.getenv('IP_ADDRESS')
port = os.getenv('PORT', '13013')  # Default to 13013 if PORT is not specified
target_pwr = os.getenv('TARGET_PWR')
api_key = os.getenv('API_KEY')

# Exit if no IP address, target_pwr, or api_key is specified
if not ip_address:
    print("No IP address specified. Exiting...")
    sys.exit(1)

if not target_pwr:
    print("No target power specified. Exiting...")
    sys.exit(1)

if not api_key:
    print("No API key specified. Exiting...")
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

# Thread locks for synchronizing access to shared resources
target_pwr_lock = Lock()
history_lock = Lock()

# Store historical data (up to 1000 data points)
history = deque(maxlen=1000)

# Learned drive settings: (freq_khz, target_power) -> best_drive
learned_drives = {}

# Current frequency for API exposure
current_frequency_hz = 0
frequency_lock = Lock()

def create_app():
    app = Flask(__name__)
    
    # Disable logging for GET requests to API endpoints
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')

    @app.route('/static/<path:filename>')
    def static_files(filename):
        return send_from_directory('static', filename)

    @app.route('/api/power', methods=['GET', 'POST'])
    def power():
        global target_pwr
        if request.method == 'GET':
            with target_pwr_lock:
                return jsonify({'target_power': target_pwr})
        elif request.method == 'POST':
            data = request.get_json()
            if 'api_key' not in data or data['api_key'] != api_key:
                abort(401)
            
            # Validate 'target_power'
            if 'target_power' not in data:
                return jsonify({'error': "'target_power' field is required"}), 400
            try:
                target_power_val = int(data['target_power'])
            except (ValueError, TypeError):
                return jsonify({'error': "'target_power' must be an integer"}), 400
            # Acceptable bounds: 0 <= target_power <= 10000
            if not (0 <= target_power_val <= 10000):
                return jsonify({'error': "'target_power' must be between 0 and 10000"}), 400
            
            with target_pwr_lock:
                target_pwr = target_power_val
            return jsonify({'message': 'Target power updated successfully'})

    @app.route('/api/history', methods=['GET'])
    def get_history():
        with history_lock:
            return jsonify(list(history))
    
    @app.route('/api/frequency', methods=['GET'])
    def get_frequency():
        with frequency_lock:
            freq_mhz = current_frequency_hz / 1_000_000
            band = get_band_name(freq_mhz)
            return jsonify({
                'frequency_hz': current_frequency_hz,
                'frequency_mhz': round(freq_mhz, 6),
                'band': band
            })

    return app

def get_band_name(freq_mhz):
    """Convert frequency to ham band name."""
    if 1.8 <= freq_mhz < 2.0:
        return "160m"
    elif 3.5 <= freq_mhz < 4.0:
        return "80m"
    elif 5.3 <= freq_mhz < 5.5:
        return "60m"
    elif 7.0 <= freq_mhz < 7.3:
        return "40m"
    elif 10.1 <= freq_mhz < 10.15:
        return "30m"
    elif 14.0 <= freq_mhz < 14.35:
        return "20m"
    elif 18.068 <= freq_mhz < 18.168:
        return "17m"
    elif 21.0 <= freq_mhz < 21.45:
        return "15m"
    elif 24.89 <= freq_mhz < 24.99:
        return "12m"
    elif 28.0 <= freq_mhz < 29.7:
        return "10m"
    elif 50.0 <= freq_mhz < 54.0:
        return "6m"
    return "Unknown"

def send_command(sock, command, prefix="", suffix="", read_response=True):
    """Send a CAT command and optionally read the response."""
    try:
        sock.sendall(command.encode('utf-8'))
        if read_response:
            while True:  # Keep reading until a valid response is found
                response = sock.recv(1024).decode('utf-8').strip()
                if response.startswith(prefix) or response == '?;':
                    processed = response.removeprefix(prefix).removesuffix(suffix).strip()
                    return "" if processed == '?;' else processed
                print(f"Unexpected response '{response}' (expected prefix: '{prefix}')")
        return ""
    except socket.error as e:
        return str(e)

def main(ip, port):
    def get_power_trend(power_window):
        """Calculate power trend using linear regression on last 5 readings."""
        if len(power_window) < 5:
            return 0.0
        y = list(power_window)[-5:]
        # For x = [0,1,2,3,4]: sum_x=10, sum_xx=30, denominator=5*30-10*10=50
        sum_y = sum(y)
        sum_xy = sum(i * yi for i, yi in enumerate(y))
        # Simplified: slope = (5*sum_xy - 10*sum_y) / 50 = (sum_xy - 2*sum_y) / 10
        return (sum_xy - 2 * sum_y) / 10
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Connect to the server
            sock.connect((ip, port))
            print("Connected to the CAT server: " + sock.recv(1024).decode('utf-8').strip())

            # Read initial drive setting from radio
            initial_drive_response = send_command(sock, 'ZZPC;', "ZZPC", ";")
            current_drive = int(initial_drive_response) if initial_drive_response else 0
            print(f"Initial drive level: {current_drive}")

            # Simple control loop parameters
            drive_min, drive_max = 0, 100
            deadband = 1.0  # Watts tolerance (wider to reduce oscillations)
            last_adjust_time = 0
            power_window = deque(maxlen=8)  # Slightly larger window for smoother averaging
            swr_window = deque(maxlen=10)  # SWR moving average window
            
            # TX/RX state tracking
            in_tx = False
            tx_start_time = 0
            stable_tx_power = 0  # Remember what power was during stable TX
            stable_drive = 0  # Remember stable drive for current freq/power combo
            current_freq_khz = 0
            last_freq_read_time = 0

            while True:
                # Read frequency every 5 seconds (not every loop to reduce CAT traffic)
                if time.time() - last_freq_read_time > 5.0:
                    freq_response = send_command(sock, 'FA;', "FA", ";")
                    if freq_response:
                        try:
                            freq_hz = int(freq_response)
                            current_freq_khz = freq_hz // 1000
                            # Update global frequency for API
                            global current_frequency_hz
                            with frequency_lock:
                                current_frequency_hz = freq_hz
                        except ValueError:
                            pass
                    last_freq_read_time = time.time()
                
                # swr_response = send_command(sock, 'ZZRM8;', "ZZRM8", " W;")
                

                pwr_response = send_command(sock, 'ZZRM5;', "ZZRM5", " W;")
                if pwr_response:
                    try:
                        current_pwr = float(pwr_response)
                    except ValueError:
                        time.sleep(0.1)
                        continue

                    power_window.append(current_pwr)
                    avg_pwr = sum(power_window) / len(power_window)
                    
                    # Read SWR
                    swr_response = send_command(sock, 'ZZRM8;', "ZZRM8", ";")
                    # take '1.3 : 1' and extract '1.3'
                    swr_value_str = swr_response.split(':')[0].strip() if swr_response else "0.0"
                    
                    current_swr = 0.0
                    if swr_response:
                        try:
                            current_swr = float(swr_value_str)
                        except ValueError:
                            current_swr = 0.0
                    swr_window.append(current_swr)
                    avg_swr = sum(swr_window) / len(swr_window)
                    
                    # Detect TX/RX state - use current_pwr for instant detection, not avg
                    was_in_tx = in_tx
                    in_tx = current_pwr > 1.0  # Require >1W to be considered TX
                    
                    # Read target power with thread safety
                    with target_pwr_lock:
                        current_target_pwr = target_pwr
                    
                    # Track TX start for stabilization period
                    if in_tx and not was_in_tx:
                        tx_start_time = time.time()
                        # Apply learned drive if we have one for this freq/power
                        learn_key = (current_freq_khz, current_target_pwr)
                        if learn_key in learned_drives:
                            learned_drive = learned_drives[learn_key]
                            if learned_drive != current_drive:
                                print(f"TX started - applying learned drive {learned_drive} for {current_freq_khz}kHz @ {current_target_pwr}W")
                                send_command(sock, 'ZZPC' + str(learned_drive).zfill(3) + ';', "", "", False)
                                current_drive = learned_drive
                            else:
                                print(f"TX started at learned drive {current_drive}")
                        else:
                            print(f"TX started at drive {current_drive}, waiting 2s for stabilization...")
                    elif was_in_tx and not in_tx:
                        # Save stable drive when TX ends
                        if stable_drive > 0:
                            learn_key = (current_freq_khz, current_target_pwr)
                            learned_drives[learn_key] = stable_drive
                            print(f"TX ended - saved drive {stable_drive} for {current_freq_khz}kHz @ {current_target_pwr}W")
                        else:
                            print(f"TX ended, drive frozen at {current_drive}")

                    # Add data point to history with thread safety
                    with history_lock:
                        history.append({
                            'timestamp': time.time(),
                            'power': avg_pwr,
                            'target': target_pwr,
                            'drive': current_drive,
                            'swr': avg_swr
                        })

                    error = current_target_pwr - avg_pwr
                    abs_error = abs(error)
                    
                    # Remember stable TX power and drive for learning
                    if in_tx and abs_error < 0.8:
                        stable_tx_power = avg_pwr
                        stable_drive = current_drive  # This is the good drive to remember
                    
                    # ONLY adjust drive if actively transmitting with good power
                    # Don't adjust during RX, TX startup, or TX ending
                    time_since_tx_start = time.time() - tx_start_time if in_tx else 999
                    tx_stabilized = time_since_tx_start > 2.5
                    
                    # Check if power is falling (likely TX ending)
                    power_falling = stable_tx_power > 0 and avg_pwr < (stable_tx_power * 0.7)
                    
                    time_since_adjust = time.time() - last_adjust_time
                    
                    # Simple rule: ONLY adjust if we're in TX, stabilized, power not falling, and outside deadband
                    if in_tx and tx_stabilized and not power_falling and abs_error > deadband and time_since_adjust > 0.5:
                        current_drive_response = send_command(sock, 'ZZPC;', "ZZPC", ";")
                        if current_drive_response:
                            current_drive = int(current_drive_response)
                            # Simple ±1 adjustment
                            drive_adjust = 1 if error > 0 else -1
                            next_drive = max(drive_min, min(drive_max, current_drive + drive_adjust))
                            if current_drive != next_drive:
                                print(f"Drive {current_drive}→{next_drive} (error={error:.2f}W, pwr={avg_pwr:.2f}W)")
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                                current_drive = next_drive
                                last_adjust_time = time.time()
                    time.sleep(0.1)
                else:
                    time.sleep(1)
        except Exception as e:
            print("failed to connect or error during the session:", str(e))

if __name__ == '__main__':
    from threading import Thread
    app = create_app()
    flask_thread = Thread(target=lambda: app.run(host='0.0.0.0', port=5000))
    flask_thread.daemon = True
    flask_thread.start()
    main(ip_address, port)
