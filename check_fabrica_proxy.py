import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def check_fabrica():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    stdin, stdout, stderr = ssh.exec_command("cat /opt/projects/fabrica/.env")
    print(stdout.read().decode('utf-8'))

    stdin, stdout, stderr = ssh.exec_command("cat /opt/projects/fabrica/bot.py | head -n 40")
    print(stdout.read().decode('utf-8'))

    ssh.close()

if __name__ == "__main__":
    check_fabrica()
