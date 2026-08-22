import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def inspect_container():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    commands = [
        "cd /opt/projects/egor && docker compose logs -n 50",
        "docker inspect --format='{{.State.Status}} (exit code: {{.State.ExitCode}}, error: {{.State.Error}})' egor-bot",
        "cd /opt/projects/egor && cat .env"
    ]

    for cmd in commands:
        print(f">>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8').strip())
        err = stderr.read().decode('utf-8').strip()
        if err:
            print("[ERR]", err)
        print("-" * 50)

    ssh.close()

if __name__ == "__main__":
    inspect_container()
