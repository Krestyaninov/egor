import paramiko

HOST = "147.45.211.75"
USER = "root"
PASSWORD = "rMroBUEx52911"

def test_keys():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=10)

    print("Testing ssh -T git@github-egor:")
    stdin, stdout, stderr = ssh.exec_command("ssh -o StrictHostKeyChecking=no -T git@github-egor")
    print("STDOUT:", stdout.read().decode('utf-8'))
    print("STDERR:", stderr.read().decode('utf-8'))

    ssh.close()

if __name__ == "__main__":
    test_keys()
