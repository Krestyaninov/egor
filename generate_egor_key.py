import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def setup_egor_deploy_key():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # 1. Генерируем уникальный ключ для egor
    commands = [
        "ssh-keygen -t ed25519 -N '' -f /root/.ssh/id_ed25519_egor -C 'deploy-key-egor' 2>/dev/null || true",
        "cat /root/.ssh/id_ed25519_egor.pub"
    ]
    
    pub_key = ""
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        out = stdout.read().decode('utf-8').strip()
        if "ssh-ed25519" in out:
            pub_key = out

    # 2. Настраиваем ~/.ssh/config для хоста github-egor
    ssh_config_content = """
Host github.com
    HostName github.com
    User git
    IdentityFile /root/.ssh/id_ed25519
    StrictHostKeyChecking no

Host github-egor
    HostName github.com
    User git
    IdentityFile /root/.ssh/id_ed25519_egor
    StrictHostKeyChecking no
"""
    cmd_write_config = f"cat << 'EOF' > /root/.ssh/config\n{ssh_config_content.strip()}\nEOF\nchmod 600 /root/.ssh/config"
    ssh.exec_command(cmd_write_config)

    # 3. Настраиваем remote в /opt/projects/egor
    ssh.exec_command("cd /opt/projects/egor && git remote set-url origin git@github-egor:Krestyaninov/egor.git")

    # 4. Обновляем deploy.sh
    deploy_sh_content = """#!/bin/bash
set -e

echo "=== 🚀 Деплой проекта Egor Bot (@egor_quapmi_bot) ==="

if [ -d ".git" ]; then
    echo "📥 Получение обновлений из GitHub..."
    git pull origin main
fi

echo "🐳 Сборка и запуск Docker-контейнера..."
docker compose down || true
docker compose up -d --build

echo "=== ✅ Деплой успешно завершен! ==="
docker compose ps
"""
    cmd_write_deploy = f"cat << 'EOF' > /opt/projects/egor/deploy.sh\n{deploy_sh_content.strip()}\nEOF\nchmod +x /opt/projects/egor/deploy.sh"
    ssh.exec_command(cmd_write_deploy)

    ssh.close()
    return pub_key

if __name__ == "__main__":
    key = setup_egor_deploy_key()
    print("=== УНИКАЛЬНЫЙ КЛЮЧ ДЛЯ ПРОЕКТА EGOR ===")
    print(key)
