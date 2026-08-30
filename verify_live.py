import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"
REMOTE_DIR = "/opt/projects/egor"

def verify_live():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    commands = [
        f"cd {REMOTE_DIR} && git log -n 1 --oneline",
        f"cd {REMOTE_DIR} && git status",
        "docker ps --filter name=egor-bot",
        f"cd {REMOTE_DIR} && docker compose logs --tail=20"
    ]

    for cmd in commands:
        print(f"\n>>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())

    ssh.close()

if __name__ == "__main__":
    verify_live()
