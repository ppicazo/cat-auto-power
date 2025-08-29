#!/usr/bin/env python3
"""
Simple test script for cat-auto-power functionality.
Tests core functions without requiring actual CAT server connection.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the current directory to path to import main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import main


class TestCatAutoPower(unittest.TestCase):
    """Test cases for cat-auto-power functionality."""

    def test_calculate_drive_adjustment_no_change_needed(self):
        """Test that no adjustment is returned when power matches target."""
        result = main.calculate_drive_adjustment(10, 10, 50)
        self.assertIsNone(result)

    def test_calculate_drive_adjustment_power_too_high(self):
        """Test drive reduction when power is too high."""
        result = main.calculate_drive_adjustment(15, 10, 50)
        self.assertEqual(result, 49)

    def test_calculate_drive_adjustment_power_too_low(self):
        """Test drive increase when power is too low."""
        result = main.calculate_drive_adjustment(8, 10, 50)
        self.assertEqual(result, 51)

    def test_calculate_drive_adjustment_drive_too_high(self):
        """Test reset when drive level is too high."""
        result = main.calculate_drive_adjustment(10, 10, 70)
        self.assertEqual(result, main.DRIVE_RESET_VALUE)

    def test_calculate_drive_adjustment_power_below_threshold(self):
        """Test no adjustment when power is below minimum threshold."""
        result = main.calculate_drive_adjustment(2, 10, 50)
        self.assertIsNone(result)

    def test_calculate_drive_adjustment_bounds_checking(self):
        """Test that drive adjustments respect bounds."""
        # Test minimum bound
        result = main.calculate_drive_adjustment(15, 10, 0)
        self.assertEqual(result, 0)  # Should stay at minimum
        
        # Test drive level at max but within safe threshold
        result = main.calculate_drive_adjustment(5, 10, 59)  # Just below reset threshold
        self.assertEqual(result, 60)  # Should increment to max allowed
        
        # Test drive level above reset threshold gets reset
        result = main.calculate_drive_adjustment(5, 10, 100)
        self.assertEqual(result, main.DRIVE_RESET_VALUE)  # Should reset to safe value

    @patch.dict(os.environ, {'IP_ADDRESS': '192.168.1.100', 'TARGET_PWR': '25'})
    def test_validate_environment_valid(self):
        """Test environment validation with valid values."""
        ip, port, target = main.validate_environment()
        self.assertEqual(ip, '192.168.1.100')
        self.assertEqual(port, main.DEFAULT_PORT)
        self.assertEqual(target, 25)

    @patch.dict(os.environ, {'IP_ADDRESS': '192.168.1.100', 'PORT': '4532', 'TARGET_PWR': '25'})
    def test_validate_environment_custom_port(self):
        """Test environment validation with custom port."""
        ip, port, target = main.validate_environment()
        self.assertEqual(ip, '192.168.1.100')
        self.assertEqual(port, 4532)
        self.assertEqual(target, 25)

    @patch.dict(os.environ, {}, clear=True)
    def test_validate_environment_missing_ip(self):
        """Test that missing IP address causes system exit."""
        with self.assertRaises(SystemExit):
            main.validate_environment()

    @patch.dict(os.environ, {'IP_ADDRESS': '192.168.1.100'}, clear=True)
    def test_validate_environment_missing_target(self):
        """Test that missing target power causes system exit."""
        with self.assertRaises(SystemExit):
            main.validate_environment()

    @patch.dict(os.environ, {'IP_ADDRESS': '192.168.1.100', 'PORT': 'invalid', 'TARGET_PWR': '25'})
    def test_validate_environment_invalid_port(self):
        """Test that invalid port causes system exit."""
        with self.assertRaises(SystemExit):
            main.validate_environment()

    @patch.dict(os.environ, {'IP_ADDRESS': '192.168.1.100', 'PORT': '99999', 'TARGET_PWR': '25'})
    def test_validate_environment_port_out_of_range(self):
        """Test that port out of range causes system exit."""
        with self.assertRaises(SystemExit):
            main.validate_environment()

    def test_send_command_mock(self):
        """Test send_command function with mocked socket."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'ZZRM512 W;'
        
        result = main.send_command(mock_sock, 'ZZRM5;', 'ZZRM5', ' W;')
        
        mock_sock.sendall.assert_called_once_with(b'ZZRM5;')
        self.assertEqual(result, '12')

    def test_send_command_error_response(self):
        """Test send_command handling of error response."""
        mock_sock = MagicMock()
        mock_sock.recv.return_value = b'?;'
        
        result = main.send_command(mock_sock, 'ZZRM5;', 'ZZRM5', ' W;')
        
        self.assertEqual(result, '')


if __name__ == '__main__':
    print("Running cat-auto-power tests...")
    unittest.main(verbosity=2)