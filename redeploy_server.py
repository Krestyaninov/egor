import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"
REMOTE_DIR = "/opt/projects/egor"

def redeploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print("Connecting to server...")
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    # 1. Update .env with proxy on server
    env_content = """# Bitrix24 Webhook URL
BITRIX_WEBHOOK_URL=https://portal.appmistore.ru/rest/20319/nt9sw7bwjdb9em29/

# Telegram Bot Token (Аналитик Егор - @egor_quapmi_bot)
TELEGRAM_BOT_TOKEN=8627957133:AAE4GvYxXcj1oL_BAAhIGruLq4AeJXONqJg

# Telegram SOCKS5 Proxy URL
TELEGRAM_PROXY_URL=socks5://dfEQvm:kD0mcE@68.209.63.128:8000

# Main Catalog IBlock ID
CATALOG_IBLOCK_ID=11
"""
    cmd_env = f"cat << 'EOF' > {REMOTE_DIR}/.env\n{env_content.strip()}\nEOF"
    ssh.exec_command(cmd_env)

    # 2. Run deploy.sh
    commands = [
        f"cd {REMOTE_DIR} && git fetch origin && git reset --hard origin/main",
        f"cd {REMOTE_DIR} && ./deploy.sh",
        "docker ps",
        f"cd {REMOTE_DIR} && docker compose logs --tail=25"
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
    print("\n✅ Передеплой с прокси завершен!")

if __name__ == "__main__":
    redeploy()
