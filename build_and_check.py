import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"
REMOTE_DIR = "/opt/projects/egor"

def build_and_check():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    commands = [
        f"chmod +x {REMOTE_DIR}/deploy.sh",
        f"cd {REMOTE_DIR} && ./deploy.sh",
        f"sleep 3",
        f"cd {REMOTE_DIR} && docker compose logs --tail=30"
    ]

    for cmd in commands:
        print(f"\n>>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())
        err = stderr.read().decode('utf-8').strip()
        if err:
            print("[INFO/ERR]", err)

    ssh.close()

if __name__ == "__main__":
    build_and_check()
