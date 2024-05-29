import socket
import time
import os
import sys

ip_address = os.getenv('IP_ADDRESS')
port = os.getenv('PORT', '13013')  # Default to 13013 if PORT is not specified
target_pwr = os.getenv('TARGET_PWR')

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
            
            while True:
                pwr_response = send_command(sock, 'ZZRM5;', "ZZRM5", " W;")
                
                if pwr_response:
                    print("Power Output:", pwr_response, " W")
                    current_pwr = int(pwr_response);
                    if current_pwr > target_pwr or current_pwr < target_pwr:
                        current_drive_response = send_command(sock, 'ZZPC;', "ZZPC", ";")
                        if current_drive_response:
                            current_drive = int(current_drive_response);
                            if (current_drive >= 60):
                                next_drive = 10
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                            elif (current_pwr > target_pwr):
                                next_drive = current_drive - 1
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                            elif (current_pwr > 3 and current_pwr < target_pwr):
                                next_drive = current_drive + 1
                                print("changing drive from ", current_drive, " to ", next_drive)
                                send_command(sock, 'ZZPC' + str(next_drive).zfill(3) + ';', "", "", False)
                    time.sleep(0.1)
                else:
                    time.sleep(1)
        
        except Exception as e:
            print("failed to connect or error during the session:", str(e))

# Run the main function
main(ip_address, port)
