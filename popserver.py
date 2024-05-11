import socket
import sys

# Accept POP3 port as command-line argument
POP3_port = int(input('POP3 port: '))

# Function to handle client requests
def handle_client(client_socket):
    try:
        # Send welcome message
        client_socket.send(b'+OK POP3 server is ready\r\n')

        while True:
            # Receive command from client
            command = client_socket.recv(1024).decode().strip()
            print("Command Received:", command)

            if command.startswith('USER'):
                client_socket.send(b'+OK User accepted\r\n')
            elif command.startswith('PASS'):
                client_socket.send(b'+OK Password accepted\r\n')
            elif command.startswith('LIST'):
                # Simulate email list
                email_list = [
                    b'1 500',
                    b'2 300',
                    b'3 700'
                ]
                # Send email list to client
                client_socket.send(b'+OK 3 messages\r\n')
                for email_info in email_list:
                    client_socket.send(email_info + b'\r\n')
                client_socket.send(b'.\r\n')  # End of list
            elif command.startswith('RETR'):
                # Simulate email retrieval
                email_content = b'Sample email content\r\n'
                client_socket.send(b'+OK\r\n')
                client_socket.send(email_content)
                client_socket.send(b'.\r\n')  # End of email
            elif command.startswith('DELE'):
                client_socket.send(b'+OK\r\n')  # Simulate email deletion
            elif command.startswith('QUIT'):
                client_socket.send(b'+OK Bye\r\n')
                break
            else:
                client_socket.send(b'-ERR Unknown command\r\n')

    except Exception as e:
        print("Error:", e)
        client_socket.send(b'-ERR Internal server error\r\n')

    finally:
        # Clean up the connection
        client_socket.close()

# Main function to create and run the POP3 server
def main():
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Bind the socket to the specified POP3 port
    server_socket.bind(('localhost', POP3_port))
    # Listen for incoming connections
    server_socket.listen(1)
    print("POP3 server is running...")

    try:
        while True:
            # Accept incoming connections
            client_socket, client_address = server_socket.accept()
            print("Connection established with:", client_address)
            # Handle client requests
            handle_client(client_socket)
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()