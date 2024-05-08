import socket
import sys
from datetime import datetime

# SMTP server setup
if len(sys.argv) != 2:
    print("Usage: python mailserver_smtp.py <port>")
    sys.exit(1)

my_port = int(sys.argv[1]) # Parse command-line argument to get the port number

# Socket binding
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create socket 
server_socket.bind(('localhost', my_port)) # Bind the socket to the specified port (my_port) 
server_socket.listen(1)

# Function to store email in user's mailbox
def store_email(username, email_content):
    mailbox_path = f"./Practicum CN/{username}/my_mailbox"  # Adjust as needed
    with open(mailbox_path, "a") as mailbox:
        mailbox.write(email_content)

# SMTP protocol handling
while True:
    connection, client_address = server_socket.accept()  # Accept incoming connections from sender
    try:
        print("Connection established with:", client_address)

        # Receive data from the client
        data = connection.recv(1024)
        if not data:
            break

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
            store_email("username", email_content)  # Replace "username" with actual username
            connection.send(b'250 OK\r\n')  # Respond with success
        elif command.startswith('QUIT'):
            connection.send(b'221 BBN-UNIX.ARPA Service closing transmission channel\r\n')
            break
        else:
            connection.send(b'500 Syntax error, command unrecognized\r\n')

    finally:
        # Clean up the connection
        connection.close()