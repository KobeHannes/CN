import socket

# Parameters:
# Address of the SMTP mailserver and POP3 server user of client wishes to connect to
HOST = input('Enter the ip address for the SMTP and POP3 server: ')               # default 127.0.0.1

# Port of SMTP mailserver user of client wishes to connect to
SMTP_PORT = int(input('Enter an integer for the port of the SMTP server: '))      # default is 25

# Port of POP3 server user of client whishes to connect to
POP3_PORT = int(input('Enter an integer for the port of the POP3 server: '))      # defaull is 110


def loop_mail_sending():
    """
    Function that handles mail sending option to an SMTP mail server with RFC821. Before communicating
    with SMTP server a format check takes place, expected format is shown below.
    Input: < From: name@domain
             To: name1@domain1, ..., nameX@domainX
             Subject: <body, max 150 characters or empty>
             <mail body>
             '.' >
    Output: Mail sent confirmation, or failure with correct error code and detailed fault
    """
    # Receive and print the first welcome message from the SMTP server, to let user know connection was successful
    data = client_socket.recv(1024).decode().strip()
    print('Server:', data, '\nType your full message and end with ".", follow format shown in assignment:')

    message_lines = []
    while True:
        # Receive a line of the email message
        line = input()
        if line == '.':
            # End of email message reached
            break
        else:
            # Append the line to the message
            line += "\r\n"
            message_lines.append(line)

    #
    # Here we single out the 'From:' line, into a list
    from_line = [line for line in message_lines if line.startswith('From:')]

    # Bad format, no 'From:' line found
    if len(from_line) == 0:
        print("ERROR: Bad formatting of message, there was no 'From:' line found. Returning to menu, connection closed")
        return

    # 'From:' email address, check if there is one:
    try:
        from_address = [line.split(':')[1].strip() for line in message_lines if line.startswith('From:')][0]
    except IndexError:
        from_address = ''

    #
    # Here we single out the 'To:' line, into a list
    to_lines = [line for line in message_lines if line.startswith('To:')]

    # Bad format, no 'To:' line found
    if len(to_lines) == 0:
        print("ERROR: Bad formatting of message, there was no 'To:' line found. Returning to menu, connection closed")
        return

    # 'To:' email address(es), check if there is(are) one(multiple):
    to_addresses = [addr.strip() for line in to_lines for addr in line.split(':')[1].split(',')]
    if len(to_addresses) == 0:
        to_addresses = ['']

    #
    # Here we check 'Subject:' line
    subject_line = [line for line in message_lines if line.startswith('Subject:')]
    if len(subject_line) == 0:
        print("ERROR: Bad formatting of message, there was no 'Subject:' line found. Returning to menu, connection closed")
        return
    if len(subject_line[0]) > 150:
        print("ERROR: Bad formatting of message, the 'Subject' argument exceeded 150 characters. Returning to menu, connection closed")
        return

    #
    # Start communication with SMTP server now:

    # Effectuate 'HELO' command, the IP giving is the IP of client
    var1 = client_socket.getpeername()[0]
    client_socket.send('HELO {}\r\n'.format(var1).encode())
    data = client_socket.recv(1024).decode().strip()
    if not data.startswith('250'):
        print(data)
        return

    # Effectuate 'MAIL FROM:' command
    client_socket.send('MAIL FROM: {}\r\n'.format(from_address).encode())
    data = client_socket.recv(1024).decode().strip()
    if not data.startswith('250'):
        print(data)
        return

    # Effectuate 'RCPT TO:' command(s)
    for i in to_addresses:
        client_socket.send('RCPT TO: {}\r\n'.format(i).encode())
        data = client_socket.recv(1024).decode().strip()
        if not data.startswith('250'):
            print(data)
            return

    # Effectuate 'DATA' command
    client_socket.send(b'DATA\r\n')
    data = client_socket.recv(1024).decode().strip()
    if not data.startswith('354'):
        print(data)
        return

    message_lines.append(".\r\n")
    for j in message_lines:
        # Var 'j' already has a \r\n at the end
        client_socket.send(j.encode())

    data = client_socket.recv(1024).decode().strip()

    if not data.startswith('250'):
        print(data)
        return

    print('Mail sent successfully, returning to menu')
    return


def loop_mail_management():
    """
        Function that handles mail management option to a POP3 server with RFC1939. Before manually communicating
        with POP3 server, this script executes STAT and LIST command to let user know the amount of mails with extra information,
        this is shown in following format: <mail#> <sender of mail> <received at timestamp> <subject> .

        Input: commands - STAT|LIST (arg*)|RETR (arg)|DELE (arg)|RSET|QUIT
                          * means an optional argument
        Output: Normal outputs you can expect from a POP3 server, following RFC1939
        """
    # Receive and print the first welcome message, to let user of client know connection with POP3 server is successful
    data = client_socket.recv(1024).decode().strip()
    print(data)

    # Authentication of user using client, loop you can leave by inputting correct information or type 'EXIT' as username argument
    while True:
        USER = input('Please enter username or "EXIT": ').strip()
        PASS = input('Please enter password: ').strip()

        # You can only leave this authentication loop by inputting correct userlogin and password OR typing 'QUIT' as username
        if USER == 'EXIT':
            return

        # Communicate with POP3 server to authenticate userlogin
        client_socket.send('USER {}\r\n'.format(USER).encode())
        data = client_socket.recv(1024).decode().strip()

        # POP3 server accepts username with '+OK' reply
        if data.startswith('+OK'):

            # Communicate with POP3 server to authenticate userpassword
            client_socket.send('PASS {}\r\n'.format(PASS).encode())
            data = client_socket.recv(1024).decode().strip()

            # Password passed, and a lock was applied to mailbox
            if data.startswith('+OK'):
                print('Authentification and locking mailbox succesfull, {}'.format(data))

                # You can only leave this authentication loop by inputting correct userlogin and password OR typing 'QUIT' as username
                break

            # Password or locking of mailbox failed, print statement explains what happened
            else:
                print('Authentication failed, {}. Try again or exit...'.format(data))

        # Userlogin failed
        else:
            print('Authentication failed, {}. Try again or exit...'.format(data))

    # Communications with server, followed by formatting mailbox information as requested in problem discription.
    # Format of information: <mail#> <sender> <timestamp received> <subject>
    client_socket.send(b'STAT\r\n')
    data = client_socket.recv(1024).decode().strip()

    # second argument on index 1 is the amount of mails in the mailbox
    temp = data.split()[1]
    if int(temp) == 0:
        print("Mailbox is empty.")

    # Formatting of needed information like subject, timestamp, ... Use 'RETR' to gather this information from the POP3 server first
    else:

        # Loop over all the mails in the mailbox
        for i in range(1, int(temp) + 1):

            # Retrieve the body of the mail
            client_socket.send('RETR {}\r\n'.format(i).encode())
            data = client_socket.recv(1024).decode().strip()

            # Prepare to receive mail body, transmission ending in '.\r\n'
            if data.startswith('+OK'):
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
                            message_lines.append(item)

                # Gather needed information from received mail body
                sender_line = [line.split(':')[1].strip() for line in message_lines if line.startswith('From:')][0]
                timestamp_line = [line[len('Received at:'):].strip() for line in message_lines if line.startswith('Received at:')][0]
                subject_line = [line[len('Subject:'):].strip() for line in message_lines if line.startswith('Subject:')][0]

                # Print the required information
                print('{}. {} {} {}'.format(i, sender_line, timestamp_line, subject_line))

            # Something went wrong, more information in print statement
            else:
                print(data)

    # Interactive part of code, where authenticated user has free choice what to do with their mailbox
    while True:
        print('Available commands: STAT|LIST (arg*)|RETR (arg)|DELE (arg)|RSET|QUIT')

        # Receive input command from user
        command = input('>')

        # Handle 'QUIT' command, return to main menu and save changes to mailbox
        if command == 'QUIT':
            client_socket.send((command + '\r\n').encode())
            data = client_socket.recv(1024).decode().strip()
            print(data)
            print('Returning to main menu')
            return

        # Handle 'LIST' command, output from POP3 may be multi-line
        elif command.startswith('LIST'):

            # Single-line response from server
            if command.split()[-1].strip() != 'LIST':
                client_socket.send((command + '\r\n').encode())
                data = client_socket.recv(1024).decode().strip()
                print(data)

            # Multi-line response from server
            else:
                client_socket.send((command + '\r\n').encode())
                data = client_socket.recv(1024).decode().strip()

                # Prepare for multi-line response from server, terminated by '.\r\n'
                if data.startswith('+OK'):
                    print(data)

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
                                message_lines.append(item)

                    # Print information received from 'LIST' command
                    for i in message_lines:
                        print(i)

        # Handle 'RETR' command, output from POP3 is multi-line
        elif command.startswith('RETR'):
            client_socket.send((command + '\r\n').encode())
            data = client_socket.recv(1024).decode().strip()

            # Prepare for multi-line response
            if data.startswith('+OK'):
                message_lines3 = []
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
                            message_lines3.append(item)

                # Print response received from server
                for item in message_lines3:
                    print(item)

            # Something went wrong, more information in print statement
            else:
                print(data)

        # Handle other trivial command requiring no supporting code in client. If unknown command, POP3 will throw correct error which is printed for more information
        else:
            client_socket.send((command + '\r\n').encode())
            data = client_socket.recv(1024).decode().strip()
            print(data)


while True:
    '''
    Main code to be run on repeat while client operates, main screen of client contains 3 options to chose from using user input.
    User input will redirect to functions "loop_mail_management" or "loop_mail_sending". "Exit" will
    shut client down.
    '''
    # What option the user wants to do with client
    option = input('Please choose an option between "Mail Sending"/"Mail Management"/"Exit":\n').strip()
    option = option.lower()

    # Option for mail sending
    if option == 'mail sending':
        # Create a socket, TCP connection
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # set a timeout for the connect method
            client_socket.settimeout(10)
            # attempt to connect to the host
            client_socket.connect((HOST, SMTP_PORT))
            loop_mail_sending()
        except socket.timeout:
            # handle the timeout exception here
            print("Connection timed out, returning to main menu.")
        except ConnectionRefusedError:
            # handle the connection refused exception here
            print("Connection refused, returning to main menu.")
        except Exception as e:
            # handle any other exceptions here
            print(f"Unknown error: {e}, returning to main menu.")
        finally:
            client_socket.close()

    # Option for mail management
    elif option == 'mail management':
        # Create a socket, TCP connection
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # set a timeout for the connect method
            client_socket.settimeout(5)
            # attempt to connect to the host
            client_socket.connect((HOST, POP3_PORT))
            loop_mail_management()
        except socket.timeout:
            # handle the timeout exception here
            print("Connection timed out, returning to main menu.")
        except ConnectionRefusedError:
            # handle the connection refused exception here
            print("Connection refused, returning to main menu.")
        except Exception as e:
            # handle any other exceptions here
            print(f"Unknown error: {e}, returning to main menu.")
        finally:
            client_socket.close()

    # Option for exiting mail client program
    elif option == 'exit':
        print('Now leaving mail client program, all connections were terminated.\nHave a nice day!\n')
        break

    # Option for unknown user input
    else:
        print('Please make sure to input a valid string, with 1 space between words. (Not case sensitive)\nOr enter "Exit" to leave')
