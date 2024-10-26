# Cat Auto Power

This repository contains a script to automatically control the power output of a device using the CAT protocol. The script connects to a CAT server and adjusts the drive level to maintain a target power output.

## Purpose and Functionality

The purpose of this repository is to provide a solution for automatically controlling the power output of a device using the CAT protocol. The script connects to a CAT server, reads the current power output, and adjusts the drive level to maintain the target power output specified by the user.

## Docker Usage

To set up and run the Docker container using the provided `Dockerfile`, follow these steps:

1. Build the Docker image:
   ```sh
   docker build -t cat-auto-power .
   ```

2. Run the Docker container:
   ```sh
   docker run -e IP_ADDRESS=<your_ip_address> -e PORT=<your_port> -e TARGET_PWR=<your_target_power> cat-auto-power
   ```

## Running `main.py`

To run the `main.py` script directly, follow these steps:

1. Set the required environment variables:
   ```sh
   export IP_ADDRESS=<your_ip_address>
   export PORT=<your_port>
   export TARGET_PWR=<your_target_power>
   ```

2. Run the script:
   ```sh
   python main.py
   ```

## Examples

Here are some examples of how to set the environment variables and run the script:

### Example 1: Using Docker

```sh
docker run -e IP_ADDRESS=192.168.1.100 -e PORT=13013 -e TARGET_PWR=10 cat-auto-power
```

### Example 2: Running `main.py` directly

```sh
export IP_ADDRESS=192.168.1.100
export PORT=13013
export TARGET_PWR=10
python main.py
```
