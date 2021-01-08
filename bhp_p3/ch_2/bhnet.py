import sys
import socket
import getopt
import threading
import subprocess
import traceback
import time

listen             = False
command            = False
upload             = False
execute            = ""
target             = ""
upload_destination = ""
port               = 0

def run_command(command):
    command = command.rstrip()
    try:
        output = subprocess.check_output(command,stderr=subprocess.STDOUT, shell=True)
        output = output.decode('ascii')
    except:
        output = "Failed to execute command.\r\n"
    return output

# this handles incoming client connections
def client_handler(client_socket):
    global upload
    global execute
    global command
    print("Command:{}".format(command))
    
    # check for upload
    if len(upload_destination):
        
        # read in all of the bytes and write to our destination
        file_buffer = ""
        
        # keep reading data until none is available
        while True:
            data = client_socket.recv(1024)
            
            if not data:
                break
            else:
                file_buffer += data
                
        # now we take these bytes and try to write them out
        try:
            file_descriptor = open(upload_destination,"wb")
            file_descriptor.write(file_buffer)
            file_descriptor.close()
            
            # acknowledge that we wrote the file out
            client_socket.send("Successfully saved file to %s\r\n".encode() % upload_destination)
        except:
            client_socket.send("Failed to save file to %s\r\n".encode() % upload_destination)
            
        
    
    # check for command execution
    if len(execute):
        
        # run the command
        output = run_command(execute)
        
        client_socket.send(output.encode())
    
    
    if command:
        shell = "BHP#>"
        count = 0
        while True:
            if count == 0:
                client_socket.send(shell.encode())
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode()
            cmd_buffer = cmd_buffer.strip()
            print("[*] New command:[{}]".format(cmd_buffer))
            response = run_command(cmd_buffer)
            count += 1
            print("[+] Command count:{}".format(count))
            response = str(response)
            if count > 0:
                response += shell
            client_socket.send(response.encode())
    
def server_loop():
    global target
    global port
    
    # if no target is defined we listen on all interfaces
    if not len(target):
        target = "0.0.0.0"
        
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((target,port))
    
    server.listen(5)        
    
    while True:
        client_socket, addr = server.accept()
        
        # spin off a thread to handle our new client
        client_thread = threading.Thread(target=client_handler,args=(client_socket,))
        client_thread.start()

def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print("connecting")
        client.settimeout(1)
        try:
            client.connect((target,port))
        except:
            print("Socket timeout")
            sys.exit(1)
        if len(buffer):
            client.send(buffer.encode())
        while True:
            recv_len = 1
            response = b''
            bytes_read = 0
            while recv_len:
                time.sleep(0.2) #<- improve with async no blocks
                data     = client.recv(4096)
                # print("Got data:{}".format(len(data)))
                recv_len = len(data)
                bytes_read += recv_len
                response+= data
                if recv_len < 4096:
                    break
            print(response.decode(), end='')
            sys.stdout.flush()
            buffer = sys.stdin.readline()
            if buffer:
                client.send(buffer.encode())
            else:
                break
    except KeyboardInterrupt:
        print("Aborting...")
        client.close()  
    client.close()

def usage():
    print("Netcat Replacement")
    print()
    print("Usage: bhpnet.py -t target_host -p port")
    print("-l --listen                - listen on [host]:[port] for incoming connections")
    print("-e --execute=file_to_run   - execute the given file upon receiving a connection")
    print("-c --command               - initialize a command shell (works on client mode too)")
    print("-u --upload=destination    - upon receiving connection upload a file and write to [destination]")
    print()
    print()
    print("Examples: ")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGHI' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)


def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target
    
    if not len(sys.argv[1:]):
        usage()

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hle:t:p:cu:",["help","listen","execute","target","port","command","upload"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()
  
    for o,a in opts:
        if o in ("-h","--help"):
            usage()
        elif o in ("-l","--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--commandshell"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False,"Unhandled Option"
    

    # are we going to listen or just send data from stdin
    if not listen and len(target) and port > 0:
        
        # read in the buffer from the commandline
        # this will block, so send CTRL-D if not sending input
        # to stdin
        buffer = ""
        if not command:
            buffer = sys.stdin.readline()
            buffer += '\n'
        
        # send data off
        client_sender(buffer)   
    
    # we are going to listen and potentially 
    # upload things, execute commands and drop a shell back
    # depending on our command line options above
    if listen:
        server_loop()

main()       