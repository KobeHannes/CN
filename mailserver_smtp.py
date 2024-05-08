import socket
import threading
import os
import datetime


# Parameters:
# Address of the SMTP mailserver, hardcoded to localhost
HOST_SERVER = '127.0.0.1'

# Default port for SMTP connections is 25, if blocked by firewall try unused ports (5000+)
PORT_SERVER = int(input('Enter integer for SMTP mailserver connection to listen on:'))

# Maximum number of concurrent client connections
MAX_CLIENTS = 10


# Create a socket, TCP connection := SOCK_STREAM
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to a specific network and port defined above
server_socket.bind((HOST_SERVER, PORT_SERVER))

# Start listening for connections, print statement used for log and debug purposes
server_socket.listen(MAX_CLIENTS)
print('SMTP server initiated and listening on port: ', PORT_SERVER)


def handle_client(client_socket, client_address):
    """
    Function to be run by each thread, after sorting new clients using threading feature.
    Code behind communications between server-client, of the SMTP server.

    Important notes: 1) b'message' is equivalent to 'message'.encode() and uses same UTF-8 encoding.
                     2) Communicating bitstreams should always end with '\r\n' on server AND client side.
                     3) Error codes all follow RTC821 convention.
                     4) This is a simplified SMTP server, we assume it is not able to forward data to other SMTP services,
                        thus meaning mail can only be sent to existing receivers in "users" file on local server files. Domain of
                        recipients must match domain of SMTP server for this reason.
    """

    # Send a welcome message to the client after making TCP connection
    client_socket.send('220 Simple Mail Transfer Service Ready <{}>\r\n'.format(HOST_SERVER).encode('utf-8'))

    # Get all possible valid recipients, assume "name" is unique or in other terms a "key" value for the database
    with open('userinfo.txt', 'r') as f:
        possible_contacts = [line.strip().split()[1] for line in f]

    # Initiate checkpoint variables to false beforehand and make other thread-dependant variables
    checkpoint_helo = False
    checkpoint_mailfrom = False
    checkpoint_rcptto = False
    checkpoint_data = False
    recipients = []

    # Loop until the client closes the connection, initiates 'QUIT' command or SMTP server shuts down (force-kill)
    while True:
        # Receive a message from the client
        data = client_socket.recv(1024).decode().strip()

        # If the client closed the connection, exit the loop
        if not data:
            break

        # Print the message received from the client, used for log and debug purposes
        print('Received: ', data)

        # Handle the received data, 'HELO' command follows RFC821 protocol -> 1) Initiate first handshake between clien-server
        #                                                                     2) Initiate buffers and clear if needed
        if data.startswith('HELO'):
            # Check if domain was given after HELO command, if none was given an error is returned with code 504
            client_given_domain = data.split()[-1].strip()
            if client_given_domain == 'HELO':
                client_socket.send(b'504 Error, enter your domain after HELO command\r\n')
            else:
                # Try to convert client_given_domain to an IP address. All IP comparisons in this code
                # will be done via the IPv4 format. Convention chosen by programmers of this code.
                try:
                    # Use inet_aton() to check whether client_given_domain is a valid IP address
                    # If it's a valid IP address, change nothing
                    socket.inet_aton(client_given_domain)
                except socket.error:
                    # If it's not a valid IP address, use gethostbyname() to get the IP address of the domain name (used for ex. kuleuven.be domain)
                    client_given_domain = socket.gethostbyname(client_given_domain)

                # Check match between given domain to current TCP connection: no match nothing happens
                if not client_address[0] == client_given_domain:
                    client_socket.send(b'501 Error HELO handshake failed, entry mismatched for client domain\r\n')

                # Handshake may proceed, go to initial state with empty buffers. But update the checkpoint for 'HELO' to True
                else:
                    checkpoint_helo = True
                    checkpoint_mailfrom = False
                    checkpoint_rcptto = False
                    checkpoint_data = False
                    recipients = []
                    client_socket.send('250 {} welcomes client {}\r\n'.format(HOST_SERVER, client_address[0]).encode('utf-8'))

        # Handle the received data, 'MAIL FROM:' command follows RFC821 protocol
        elif data.startswith('MAIL FROM:'):
            # Check if client sends commands in correct order, only after a 'HELO' handshake has been completed
            if checkpoint_helo is False or checkpoint_mailfrom is True or checkpoint_rcptto is True or checkpoint_data is True:
                client_socket.send(b'503 Error transactions are out of order\r\n')
            else:
                # Extract the sender name and domain from data string, also known as mail address
                incoming_string = data.split(':')[-1].strip()

                # Check if parameters were given after MAIL FROM:, splitting with no data
                # after MAIL FROM: gives list ['MAIL FROM', '']
                if incoming_string == '':
                    client_socket.send(b'504 Error, enter arguments after MAIL FROM command\r\n')
                else:
                    # Split incoming_string into sender name and sender domain, must match HELO argument
                    try:
                        sender_temp, senderdomain_temp = incoming_string.split('@')
                    except ValueError:
                        client_socket.send(b'501 Syntax error, sender@domain must be sent after MAIL FROM:\r\n')
                        continue

                    # Try to convert senderdomain_temp to an IP address
                    try:
                        # Use inet_aton() to check whether senderdomain_temp is a valid IP address
                        # If it's a valid IP address, change nothing
                        socket.inet_aton(senderdomain_temp)
                    except socket.error:
                        # If it's not a valid IP address, use gethostbyname() to get the IP address of the domain name (used for ex. kuleuven.be domain)
                        senderdomain_temp = socket.gethostbyname(senderdomain_temp)

                    # check the domain given by sender in email adres and match it with the current TCP connection
                    if senderdomain_temp == client_address[0]:
                        # Respond with a confirmation message and update checkpoint variable for 'MAIL FROM:'
                        checkpoint_mailfrom = True
                        client_socket.send(b'250 Sender OK\r\n')
                    else:
                        # Domains do not match for sender
                        client_socket.send(b'501 domain of email does not match TCP connection domain\r\n')

        # Handle the received data, 'RCPT TO:' command follows RFC821 protocol
        elif data.startswith('RCPT TO:'):
            # Check if client sends commands in correct order, only after 'HELO' and 'MAIL FROM:' has been completed
            if checkpoint_helo is False or checkpoint_mailfrom is False or checkpoint_data is True:
                client_socket.send(b'503 Error transactions are out of order\r\n')
            else:
                # Extract the recipient mail address from data string
                recipient = data.split(':')[-1].strip()

                # Check if parameters were given after RCPT TO:, splitting with no data
                # after RCPT TO: gives list ['RCPT TO', '']
                if recipient == '':
                    client_socket.send(b'504 Error, enter arguments after RCPT TO command\r\n')
                else:
                    # Split recipient into rcpt name and rcpt domain, must match server domain since external world access is closed off here
                    try:
                        rcpt_temp, rcptdomain_temp = recipient.split('@')
                    except ValueError:
                        client_socket.send(b'501 Syntax error, sender@domain must be sent after RCPT TO:\r\n')
                        continue

                    # Try to convert rcptdomain_temp to an IP address
                    try:
                        # Use inet_aton() to check whether rcptdomain_temp is a valid IP address
                        # If it's a valid IP address, change nothing
                        socket.inet_aton(rcptdomain_temp)
                    except socket.error:
                        # If it's not a valid IP address, use gethostbyname() to get the IP address of the domain name (used for like kuleuven.be domain)
                        rcptdomain_temp = socket.gethostbyname(rcptdomain_temp)

                    if rcpt_temp not in possible_contacts:
                        # need to discard if user does not exist
                        client_socket.send(b'550 No such user here\r\n')
                    elif not rcptdomain_temp == HOST_SERVER:
                        # need to discard if user's domain does not match mailing smtp server
                        client_socket.send(b'551 User not local; please try <localhost> domain\r\n')
                    else:
                        recipients.append(rcpt_temp)
                        checkpoint_rcptto = True
                        # Respond with a confirmation message if rcpt is successfully added
                        client_socket.send(b'250 Recipient OK\r\n')

        # Handle the received data, 'DATA' command follows RFC821 protocol
        elif data.startswith('DATA'):
            # Check if client sends commands in correct order
            if checkpoint_helo is False or checkpoint_mailfrom is False or checkpoint_rcptto is False or checkpoint_data is True:
                client_socket.send(b'503 Error transactions are out of order\r\n')
            else:
                # Send a message asking for the mail <body>
                client_socket.send(b'354 Enter message, ending with "." on a line by itself\r\n')

                # Loop until the end of the mail message is reached: '\r\n'. Body will get stored in list "message_lines"
                message_lines = []
                terminate = False
                while True and not terminate:
                    # Receive a line of the mail message, strip any leading or trailing whitespaces
                    line = client_socket.recv(1024).decode().strip()
                    line_list = line.split('\r\n')

                    # End of email message reached, loop gets terminated
                    if line == '.\r\n' or line == '.' or line == '.\r' or line == '.\n':
                        break

                    for item in line_list:
                        if item == '.\r\n' or item == '.' or item == '.\r' or item == '.\n':
                            terminate = True
                            break

                        # Line appended to list "message_lines"
                        else:
                            message_lines.append(item) # Note this (small insignificant) error was corrected after submissiondate. 
                                                       # Correction was made so that the rest of the code is 100% correct. 

                # Following code handles the writing of a mail to the inboxes (my_mailbox.txt) of corresponding recipients.
                # Variables "message" and "message_with_timestamp" need not be initialized or reset in 'HELO' function,
                # since these will get overwritten each time 'DATA' commands runs. Regardless of previous values in these variables.
                message = '\n'.join(message_lines)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message_with_timestamp = message.split("\n")
                message_with_timestamp.insert(3, "Received at: " + timestamp)
                message_with_timestamp = "\n".join(message_with_timestamp)
                print('Email message:\n', message_with_timestamp)

                # Send confirmation that mail is queued, update checkpoint
                client_socket.send(b'250 Message received and queued for delivery\r\n')
                checkpoint_data = True

                # Write the mail to each recipient's mailbox directory, mails in inboxes are seperated by '.'
                for recipient in recipients:
                    mailbox_dir = os.path.join('users', recipient)
                    filename = os.path.join(mailbox_dir, 'my_mailbox.txt')
                    with open(filename, 'a') as f:
                        f.write(message_with_timestamp)
                        f.write('\n.\n')

        # Handle the received data, 'EXPN' command follows RFC821 protocol
        elif data.startswith('EXPN'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'EHLO' command follows RFC821 protocol
        elif data.startswith('EHLO'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'HELP' command follows RFC821 protocol
        elif data.startswith('HELP'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'NOOP' command follows RFC821 protocol
        elif data.startswith('NOOP'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'QUEU' command follows RFC821 protocol
        elif data.startswith('QUEU'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'RSET' command follows RFC821 protocol
        elif data.startswith('RSET'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'STARTTLS' command follows RFC821 protocol
        elif data.startswith('STARTTLS'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'TICK' command follows RFC821 protocol
        elif data.startswith('TICK'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'VERB' command follows RFC821 protocol
        elif data.startswith('VERB'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'VRFY' command follows RFC821 protocol
        elif data.startswith('VRFY'):
            client_socket.send(b'502 Command not implemented\r\n')

        # Handle the received data, 'QUIT' command follows RFC821 protocol
        elif data.startswith('QUIT'):
            # Close the socket connection
            client_socket.send('221 {} SMTP server closing TCP connection for {}\r\n'.format(HOST_SERVER, client_address[0]).encode('utf-8'))
            client_socket.close()
            break

        # Handle the received data, unknown commands to the RFC821 protocol
        else:
            # Unknown command, send an error message
            client_socket.send(b'500 Command not recognized\r\n')

    # Print statement used for log and debug purposes
    print('Connection closed by client with adress', client_address)


while True:
    """
    Main code to be run on repeat while server operates, new clients will jump to function "handle_client".
    After redirecting a client to said function, the server keeps listening and accepting new clients due to threading feature.
    """
    # Wait for a client to connect, and accept the connection
    CLIENT_SOCKET, CLIENT_ADDRESS = server_socket.accept()

    # Print statement used for log and debug purposes
    print('Connection from client with adress', CLIENT_ADDRESS)

    # Start a new thread to handle the client connection, enabling concurrent connection of multiple users
    thread = threading.Thread(target=handle_client, args=(CLIENT_SOCKET, CLIENT_ADDRESS))
    thread.start()
