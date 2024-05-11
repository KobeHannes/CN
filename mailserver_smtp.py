import socket
import sys
import threading
import os

# Accept SMTP port as command-line argument
my_port = int(input('SMTP port: '))
server_ip = '127.0.0.1'
# Socket binding

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((server_ip, my_port))
server_socket.listen(1)

# Function to store email in user's mailbox
def store_email(username, email_content):
    mailbox_path = f"./Practicum CN/{username}/my_mailbox"
    with open(mailbox_path, "a") as mailbox:
        mailbox.write(email_content)

# SMTP protocol handling
def Handle_client(connection, client_address ):
    connection.send('220 Simple Mail Transfer Service Ready <{}>\r\n'.format(server_ip).encode('utf-8'))

    while True:
        # Receive a message from the client
        data = connection.recv(1024).decode().strip()
        connection.send("Connection established with:", client_address)

        # Decode the received data
        command = data.decode().strip()
        # Parse SMTP commands

        if command.startswith('HELO'):
            connection.send(b'250 BBN-UNIX.ARPA Simple Mail Transfer Service Ready\r\n')
        elif command.startswith('MAIL FROM'):
            connection.send(b'250 OK\r\n')
        elif command.startswith('RCPT TO'):
            connection.send(b'250 OK\r\n')
        elif command.startswith('DATA'):
            connection.send(b'354 Start mail input; end with <CRLF>.<CRLF>\r\n')
            # Receive email content
            email_content = ""
            while True:
                data = connection.recv(1024).decode()
                if data.strip() == ".":
                    break
                email_content += data
            print("Received Email Content:")
            print(email_content)
            # Store the email in the user's mailbox
            start_index = email_content.find("From: ") + len("From: ")
            end_index = email_content.find("\nTo:")
            username = email_content[start_index:end_index]
            store_email(username, email_content)
            connection.send(b'250 OK\r\n')  # Respond with success
        elif command.startswith('QUIT'):
            connection.send(b'221 BBN-UNIX.ARPA Service closing transmission channel\r\n')
        else:
            connection.send(b'500 Syntax error, command unrecognized\r\n')
    connection.close()
while True:
    """
    Main code to be run on repeat while server operates, new clients will jump to function "handle_client".
    After redirecting a client to said function, the server keeps listening and accepting new clients due to threading feature.
    """
    print("SMTP server is running...")
    connection, client_address = server_socket.accept()
    thread = threading.Thread(target=Handle_client, args=(connection, client_address))
    thread.start()