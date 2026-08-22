import paramiko
import os
import sys

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def run_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    print("Connected successfully!\n")

    commands = [
        "uname -a",
        "mkdir -p /opt/projects/egor /root/.ssh",
        "docker --version && docker compose version",
        "test -f /root/.ssh/id_ed25519.pub || (test -f /root/.ssh/id_rsa.pub || ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519)",
        "cat /root/.ssh/id_ed25519.pub 2>/dev/null || cat /root/.ssh/id_rsa.pub 2>/dev/null",
        "ls -la /opt/projects",
        "docker ps"
    ]

    for cmd in commands:
        print(f">>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print(out.strip())
        if err:
            print("[ERR]", err.strip())
        print("-" * 50)

    ssh.close()

if __name__ == "__main__":
    run_ssh()
