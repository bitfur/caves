import socket
target_host = "localhost"
target_port = 9999
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((target_host, target_port))
request = "sample data"
print("[*] Seding data: {}".format(request))
client.send(request.encode())
response = client.recv(4096)
print("[*] Response data: {}".format(response.decode()))