import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def check_github_ssh():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # 1. Проверяем авторизацию в GitHub через SSH
    print("=== 1. Проверка ssh -T git@github.com ===")
    stdin, stdout, stderr = ssh.exec_command("ssh -o StrictHostKeyChecking=no -T git@github.com")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:", out.strip())
    print("STDERR:", err.strip())

    # 2. Проверяем доступ к репозиторию egor
    print("\n=== 2. Проверка доступа к git@github.com:Krestyaninov/egor.git ===")
    stdin, stdout, stderr = ssh.exec_command("git ls-remote git@github.com:Krestyaninov/egor.git")
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    print("STDOUT:", out.strip())
    print("STDERR:", err.strip())

    ssh.close()

if __name__ == "__main__":
    check_github_ssh()
