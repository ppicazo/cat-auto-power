"""
Cat Auto Power - Automatically control power output using CAT protocol
"""
import socket
import time
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
DEFAULT_PORT = 13013
MIN_DRIVE_LEVEL = 0
MAX_DRIVE_LEVEL = 100
DRIVE_RESET_THRESHOLD = 60
DRIVE_RESET_VALUE = 10
MIN_POWER_THRESHOLD = 3
POWER_TOLERANCE = 0  # Exact match required
LOOP_DELAY = 0.1
ERROR_DELAY = 1.0

def validate_environment():
    """Validate and parse environment variables."""
    ip_address = os.getenv('IP_ADDRESS')
    port = os.getenv('PORT', str(DEFAULT_PORT))
    target_pwr = os.getenv('TARGET_PWR')

    # Exit if no IP address or target_pwr is specified
    if not ip_address:
        logger.error("No IP address specified. Set IP_ADDRESS environment variable.")
        sys.exit(1)

    if not target_pwr:
        logger.error("No target power specified. Set TARGET_PWR environment variable.")
        sys.exit(1)

    try:
        port = int(port)
        target_pwr = int(target_pwr)
    except ValueError:
        logger.error("Port and Target Power must be integers.")
        sys.exit(1)

    if port <= 0 or port > 65535:
        logger.error("Port must be between 1 and 65535.")
        sys.exit(1)

    if target_pwr < 0:
        logger.error("Target power must be non-negative.")
        sys.exit(1)

    logger.info(f"Configuration - IP: {ip_address}, Port: {port}, Target Power: {target_pwr}W")
    return ip_address, port, target_pwr

# Get configuration
ip_address, port, target_pwr = validate_environment()

def send_command(sock, command, prefix="", suffix="", read_response=True):
    """
    Send a command to the CAT server and optionally read the response.
    
    Args:
        sock: Socket connection to the server
        command: Command string to send
        prefix: Expected prefix in response
        suffix: Expected suffix in response to remove
        read_response: Whether to read and return response
        
    Returns:
        str: Processed response or empty string if no response/error
    """
    try:
        sock.sendall(command.encode('utf-8'))
        logger.debug(f"Sent command: {command}")
        
        if read_response:
            while True:  # Keep reading until a valid response is found
                response = sock.recv(1024).decode('utf-8').strip()
                logger.debug(f"Received response: {response}")
                
                # Check if the response starts with the desired prefix and process it
                if response.startswith(prefix) or response == '?;':
                    processed_response = response.removeprefix(prefix).removesuffix(suffix).strip()
                    if processed_response == '?;':
                        logger.warning(f"Received error response for command: {command}")
                        return ""
                    return processed_response
                else:
                    logger.debug(f"Response '{response}' didn't start with expected prefix '{prefix}'")
        return ""
    except socket.error as e:
        logger.error(f"Socket error in send_command: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error in send_command: {e}")
        return ""

def calculate_drive_adjustment(current_pwr, target_pwr, current_drive):
    """
    Calculate the next drive level based on current and target power.
    
    Args:
        current_pwr: Current power output
        target_pwr: Target power output
        current_drive: Current drive level
        
    Returns:
        int or None: Next drive level, or None if no adjustment needed
    """
    # If drive level is too high, reset to a safe value
    if current_drive >= DRIVE_RESET_THRESHOLD:
        logger.warning(f"Drive level {current_drive} is too high, resetting to {DRIVE_RESET_VALUE}")
        return DRIVE_RESET_VALUE
    
    # If power is exactly at target, no adjustment needed
    if current_pwr == target_pwr:
        return None
    
    # If power is too high, decrease drive
    if current_pwr > target_pwr:
        next_drive = max(MIN_DRIVE_LEVEL, current_drive - 1)
        return next_drive
    
    # If power is too low and above minimum threshold, increase drive
    if current_pwr > MIN_POWER_THRESHOLD and current_pwr < target_pwr:
        next_drive = min(MAX_DRIVE_LEVEL, current_drive + 1)
        return next_drive
    
    # Power is too low but below minimum threshold - don't adjust
    logger.warning(f"Power {current_pwr}W is below minimum threshold {MIN_POWER_THRESHOLD}W")
    return None


def main(ip, port):
    """
    Main function to control power output via CAT protocol.
    
    Args:
        ip: IP address of the CAT server
        port: Port number of the CAT server
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # Set socket timeout to prevent hanging
            sock.settimeout(10.0)
            
            # Connect to the server
            logger.info(f"Connecting to CAT server at {ip}:{port}")
            sock.connect((ip, port))
            
            # Read initial connection message
            try:
                welcome_msg = sock.recv(1024).decode('utf-8').strip()
                logger.info(f"Connected to CAT server: {welcome_msg}")
            except socket.timeout:
                logger.warning("No welcome message received from server")
            
            # Main control loop
            while True:
                try:
                    # Get current power output
                    pwr_response = send_command(sock, 'ZZRM5;', "ZZRM5", " W;")
                    
                    if pwr_response:
                        try:
                            current_pwr = int(pwr_response)
                            logger.info(f"Current power output: {current_pwr}W (target: {target_pwr}W)")
                            
                            # Get current drive level
                            current_drive_response = send_command(sock, 'ZZPC;', "ZZPC", ";")
                            if current_drive_response:
                                try:
                                    current_drive = int(current_drive_response)
                                    
                                    # Calculate drive adjustment
                                    next_drive = calculate_drive_adjustment(current_pwr, target_pwr, current_drive)
                                    
                                    if next_drive is not None:
                                        logger.info(f"Adjusting drive from {current_drive} to {next_drive}")
                                        command = f'ZZPC{str(next_drive).zfill(3)};'
                                        send_command(sock, command, "", "", False)
                                    else:
                                        logger.debug("No drive adjustment needed")
                                        
                                except ValueError:
                                    logger.error(f"Invalid drive response: {current_drive_response}")
                            else:
                                logger.warning("Failed to get current drive level")
                                
                        except ValueError:
                            logger.error(f"Invalid power response: {pwr_response}")
                    else:
                        logger.warning("Failed to get power reading")
                        time.sleep(ERROR_DELAY)
                        continue
                    
                    time.sleep(LOOP_DELAY)
                    
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down gracefully")
                    break
                except socket.error as e:
                    logger.error(f"Socket error in main loop: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in main loop: {e}")
                    time.sleep(ERROR_DELAY)
        
        except socket.timeout:
            logger.error("Connection timeout - server may be unreachable")
        except ConnectionRefusedError:
            logger.error("Connection refused - server may not be running")
        except socket.gaierror as e:
            logger.error(f"DNS resolution error: {e}")
        except Exception as e:
            logger.error(f"Failed to connect or error during session: {e}")


if __name__ == "__main__":
    main(ip_address, port)
