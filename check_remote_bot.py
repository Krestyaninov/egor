import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def check_status_and_github():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # 1. Проверяем доступ к GitHub
    print("=== 1. Проверка доступа к GitHub для egor ===")
    stdin, stdout, stderr = ssh.exec_command("ssh -o StrictHostKeyChecking=no -T git@github-egor")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:", out.strip())
    print("STDERR:", err.strip())

    # 2. Проверяем контейнеры
    print("\n=== 2. Проверка статуса Docker контейнеров ===")
    stdin, stdout, stderr = ssh.exec_command("docker ps -a")
    print(stdout.read().decode('utf-8').strip())

    # 3. Проверяем логи контейнера egor-bot
    print("\n=== 3. Последние логи контейнера egor-bot ===")
    stdin, stdout, stderr = ssh.exec_command("docker logs --tail=40 egor-bot")
    print(stdout.read().decode('utf-8').strip())

    ssh.close()

if __name__ == "__main__":
    check_status_and_github()
