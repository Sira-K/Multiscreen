import paramiko
import time

def connect_to_raspberry_pi(hostname, username, password=None, key_file=None, port=22):
    """
    Connect to Raspberry Pi via SSH
    
    Args:
        hostname: IP address or hostname of your Raspberry Pi
        username: SSH username (usually 'pi' or your custom user)
        password: SSH password (if using password auth)
        key_file: Path to SSH private key file (if using key auth)
        port: SSH port (default 22)
    """
    
    # Create SSH client
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
    
    try:
        # Connect using password or key
        if key_file:
            ssh.connect(hostname, port=port, username=username, key_filename=key_file)
        else:
            ssh.connect(hostname, port=port, username=username, password=password)
        
        print(f"Successfully connected to {hostname}")
        return ssh
        
    except Exception as e:
        print(f"Failed to connect: {e}")
        return None

def execute_command(ssh, command):
    """Execute a command on the Raspberry Pi"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Get the output
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        if error:
            print(f"Error: {error}")
        
        return output
    
    except Exception as e:
        print(f"Command execution failed: {e}")
        return None

def transfer_file(ssh, local_path, remote_path):
    """Transfer a file to the Raspberry Pi"""
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        print(f"File transferred: {local_path} -> {remote_path}")
        return True
    except Exception as e:
        print(f"File transfer failed: {e}")
        return False

# Example usage
if __name__ == "__main__":
    # Connection details
    PI_IP = "10.83.22.16"  # Replace with your Pi's IP
    PI_USER = "pi"           # Replace with your username
    PI_KEY_FILE = "/home/sirakong/multi-screen/player/endpoints/keys"  # Path to your private key
    
    # Connect to the Pi using SSH key
    ssh_connection = connect_to_raspberry_pi(PI_IP, PI_USER, key_file=PI_KEY_FILE)
    
    if ssh_connection:
        # Execute some commands
        result = execute_command(ssh_connection, "uname -a")
        print("System info:", result)
        
        result = execute_command(ssh_connection, "df -h")
        print("Disk usage:", result)
        
        result = execute_command(ssh_connection, "gpio readall")  # If you have WiringPi
        print("GPIO status:", result)
        
        # Transfer a file (optional)
        # transfer_file(ssh_connection, "/path/to/local/file.txt", "/home/pi/file.txt")
        
        # Close connection
        ssh_connection.close()
        print("Connection closed")
