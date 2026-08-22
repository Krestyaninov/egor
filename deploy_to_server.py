import paramiko
import os
import stat

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"
LOCAL_DIR = "/Users/mk/code/egor"
REMOTE_DIR = "/opt/projects/egor"

# Список файлов, которые загружаем
FILES_TO_UPLOAD = [
    "Dockerfile",
    "docker-compose.yml",
    "deploy.sh",
    "requirements.txt",
    "config.py",
    "b24_client.py",
    "analytics.py",
    "handlers.py",
    "bot.py",
    ".env",
    ".env.example",
    ".gitignore",
    "README.md",
    "PROJECT_PASSPORT.md"
]

def upload_and_deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"Connecting to {USER}@{HOST}...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
    print("Connected successfully!\n")

    sftp = ssh.open_sftp()
    
    # 1. Загрузка файлов
    print("Uploading project files to /opt/projects/egor...")
    for fn in FILES_TO_UPLOAD:
        local_path = os.path.join(LOCAL_DIR, fn)
        remote_path = f"{REMOTE_DIR}/{fn}"
        if os.path.exists(local_path):
            print(f"  Uploading {fn}...")
            sftp.put(local_path, remote_path)
            if fn == "deploy.sh":
                sftp.chmod(remote_path, 0o755)

    sftp.close()

    # 2. Настройка Git на сервере и запуск Docker
    commands = [
        f"cd {REMOTE_DIR} && git init && git branch -M main && git remote remove origin 2>/dev/null || true",
        f"cd {REMOTE_DIR} && git remote add origin git@github.com:Krestyaninov/egor.git",
        f"cd {REMOTE_DIR} && chmod +x deploy.sh",
        f"cd {REMOTE_DIR} && docker compose down || true",
        f"cd {REMOTE_DIR} && docker compose up -d --build",
        "docker ps",
        f"cd {REMOTE_DIR} && docker compose logs --tail=20"
    ]

    for cmd in commands:
        print(f"\n>>> {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8')
        err = stderr.read().decode('utf-8')
        if out:
            print(out.strip())
        if err:
            print("[INFO/ERR]", err.strip())

    ssh.close()
    print("\n✅ Развертывание на сервере завершено!")

if __name__ == "__main__":
    upload_and_deploy()
