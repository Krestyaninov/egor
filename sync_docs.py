import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def sync_docs():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)
    stdin, stdout, stderr = ssh.exec_command("cd /opt/projects/egor && git pull origin main")
    print(stdout.read().decode('utf-8'))
    ssh.close()

if __name__ == "__main__":
    sync_docs()
