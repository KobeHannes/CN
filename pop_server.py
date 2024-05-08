import os
import socket
import threading
import msvcrt
from pathlib import Path


# Parameters:
# Address of the POP3 mail-operations server, hardcoded to localhost
HOST_SERVER = '127.0.0.1'

# Default port for POP3 connections is 110, if blocked by firewall try unused ports (5000+)
PORT = int(input('Enter integer for POP3 mailserver connection to listen on:'))

# Maximum number of concurrent client connections
MAX_CLIENTS = 10


# Create a socket, TCP connection := SOCK_STREAM
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to a specific network and port defined above
server_socket.bind((HOST_SERVER, PORT))

# Start listening for connections, print statement used for log and debug purposes
server_socket.listen(MAX_CLIENTS)
print('POP3 server initiated and listening on port: ', PORT)


def remove_lock(file):
    """
        Function unlocks the mailbox of a user when completing Update State.

        :param file: location of my_mailbox.txt file on the server
        """
    lock_path = file.with_suffix('.lock')
    lock_path.unlink()


def acquire_lock(lock_file):
    """
    Function tries to lock the file using msvcrt module (Windows).

    :param lock_file: location of lock file
    :return: True if the lock is acquired successfully, False otherwise
    """
    try:
        lock_fd = os.open(lock_file, os.O_RDWR | os.O_CREAT)
        msvcrt.locking(lock_fd, msvcrt.LK_LOCK, 1)
        return True
    except OSError:
        return False


def handle_client(client_socket, client_address):
    """
        Function to be run by each thread, after sorting new clients using threading feature.
        Code behind communications between server-client, of the POP3 server.

        Important notes: 1) b'message' is equivalent to 'message'.encode() and uses same UTF-8 encoding.
                         2) Communicating bitstreams should always end with '\r\n' on server AND client side.
                         3) Error codes all follow RTC1939 convention.
                         4) Module used to lock files might need to be downloaded and installed.
                            Module portalocker works on WINDOWS systems AND UNIX based systems,
                            contrary to popular lock module -> fcntl which only works on UNIX based systems.
        """
    # Send a welcome message to the client after making TCP connection
    client_socket.send('+OK POP3 server is ready <{}>\r\n'.format(HOST_SERVER).encode('utf-8'))

    # Initiate checkpoint variables to false beforehand and make other thread-dependant variables
    user_verified = False
    password_verified = False
    mailbox_lock = False
    maildrop_info = []
    mail_count = 1
    to_delete = []

    # Initialized these variables, because PyCharm IDE gave wrongfull warnings. These locations are marked as comments in code
    temp_password = ''
    temp_user = ''
    mailbox_path = ''

    # Loop until the client closes the connection, initiates 'QUIT' command or POP3 server shuts down (force-kill)
    while True:
        # Receive a message from the client
        data = client_socket.recv(1024).decode().strip()

        # If the client closed the connection, exit the loop
        if not data:
            break

        # Print the message received from the client, used for log and debug purposes
        print('Received: ', data)

        # Authentication state - handle received data, 'USER' command follows RFC1939 protocol
        #                                               -> 1) Cross-references argument with usernames in userinfo.txt
        #                                               -> 2) Updates flag user_verified to True if match found
        #                                               -> 3) If userlogin verification fails, a client may attempt this step again
        if data.startswith('USER'):
            # Check if client sends commands in correct order, no lock may have been initialized by this thread or userlogin/password verified
            if user_verified is True or password_verified is True or mailbox_lock is True:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Start analyzing argument after 'USER' command
            else:
                userlogin = data.split()[-1].strip()

                # No argument given
                if userlogin == 'USER':
                    user_verified = False
                    client_socket.send(b'-ERR please enter username argument after "USER" command\r\n')

                # Argument given, check if match for logins in user_info.txt (only accessible to server)
                else:
                    # usersinfo is a list with following structure: [[userlogin1, username1, userpassword1], [userlogin2, ..., ...], ...]
                    with open('userinfo.txt', 'r') as f:
                        usersinfo = [line.strip().split() for line in f]

                    for userinfo in usersinfo:
                        if userinfo[0] == userlogin:
                            temp_password = userinfo[2]
                            temp_user = userinfo[1]
                            user_verified = True
                            break

                    # A match was found, flag for verified user is now True
                    if user_verified:
                        client_socket.send(b'+OK user is accepted\r\n')

                    # A match was not found, flag for verified user remains False
                    else:
                        client_socket.send(b'-ERR user not found\r\n')

        # Authentication state - handle received data, 'PASS' command follows RFC1939 protocol
        #                                               -> 1) Cross-references argument with userpasswords in userinfo.txt
        #                                               -> 2) Updates flag password_verified to True if match found AND tries to create a lock to the mailbox
        #                                               -> 3) Flag password_verified remains False if no match found, update user_verified flag to False in this case
        #                                               -> 4) If userpassword verification fails, a client may NOT attempt this step again but restart the USER verification
        elif data.startswith('PASS'):
            # Check if client sends commands in correct order, no lock may have been initialized by this thread. userpassword must not be verified. userlogin must be verified
            if user_verified is False or password_verified is True or mailbox_lock is True:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Start analyzing argument after 'PASS' command
            else:
                userpassword = data.split()[-1].strip()

                # No argument given. Reset userverified flag to False, userpassword flag remains unchanged
                if userpassword == 'PASS':
                    user_verified = False
                    password_verified = False
                    client_socket.send(b'-ERR please enter password argument after "PASS" command\r\n')

                # Argument given, check if match for passwords in user_info.txt (only accessible to server)
                else:
                    # Pycharm gives a warning here for "temp_password", we can ignore this since "temp_password" cannot exist if USER code
                    # hasn't been run and PASS code cannot run until USER code has run. So this warning is nonesense and can be ignored.
                    if temp_password == userpassword:
                        password_verified = True

                        # Pycharm gives a warning here for "temp_user", we can ignore this since "temp_user" cannot exist if USER code
                        # hasn't been run and PASS code cannot run until USER code has run. So this warning is nonesense and can be ignored.
                        mailbox_dir = os.path.join('users', temp_user)
                        mailbox_file = os.path.join(mailbox_dir, 'my_mailbox.txt')

                        # Special path variable needed for locking and unlocking function.
                        mailbox_dir2 = Path('users') / temp_user
                        mailbox_path = mailbox_dir2 / 'my_mailbox.txt'

                        # Attempting to lock mailbox in acquire_lock(path_to_file), return True if successful. Update flag mailbox_lock to True
                        if acquire_lock(mailbox_path):
                            client_socket.send(b'+OK password accepted, mailbox locked and ready\r\n')
                            mailbox_lock = True

                            # Retrieve mailbox information and store in "maildrop_info" list the tuple [(mail#, body, octet#), ..]
                            # mail count starts at 1, as defined while initiating variables.
                            with open(mailbox_file, "r") as f:
                                mail_body = ""
                                octet_count = 0
                                for line in f:
                                    if line.strip() == ".":
                                        maildrop_info.append((mail_count, mail_body.strip(), octet_count))
                                        mail_count += 1
                                        mail_body = ""
                                        octet_count = 0
                                    else:
                                        mail_body += line
                                        octet_count += len(line.encode())

                        # Locking unsuccessful, mailbox already has a lock. mailbox_lock flag remains unchanged, user_verified and password_verified flags reset to False
                        else:
                            client_socket.send(b'-ERR mailbox already locked by another session, please start AUTHENTICATION again with USER command\r\n')
                            mailbox_lock = False
                            user_verified = False
                            password_verified = False

                    # Wrong password, password_verified flag remains False and user_verified resets to False
                    else:
                        user_verified = False
                        password_verified = False
                        client_socket.send(b'-ERR wrong password, please start AUTHENTICATION again with USER command\r\n')

        # Transaction state - handle received data, 'RSET' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Clears messages marked for deletion in Update State
        elif data.startswith('RSET'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Clear mails marked for deletion
            else:
                to_delete = []
                client_socket.send(b'+OK cleared and restored messages marked for deletion\r\n')

        # Transaction state - handle received data, 'NOOP' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Returns status of POP3 server
        elif data.startswith('NOOP'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Send response to client with status of server
            else:
                client_socket.send(b'+OK POP3 in transaction state\r\n')

        # Transaction state - handle received data, 'DELE' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Marks mail for deletion, if they were not already marked
        elif data.startswith('DELE'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Retrieve number of mail that client wants to mark for deletion
            else:
                delete_num = data.split()[-1].strip()

                # No number was given after 'DELE' command
                if delete_num == 'DELE':
                    client_socket.send(b'-ERR enter argument after "DELE"\r\n')

                # A string which should be a number, was given after 'DELE' command
                else:

                    # Transform string to integer
                    try:
                        delete_num = int(delete_num)

                        # Check to see if given integer is valid, must be greater than 0 and not larger than amount of mails in mailbox
                        if delete_num <= 0 or delete_num > len(maildrop_info):
                            client_socket.send(b'-ERR number out of range\r\n')

                        # Append number to list of mails marked for deletion if not already in said list
                        else:
                            if delete_num in to_delete:
                                client_socket.send(b'-ERR mail already queued for deletion\r\n')
                            else:
                                to_delete.append(delete_num)
                                client_socket.send(b'+OK queued mail for deletion, QUIT to make changes permanent\r\n')

                    # Failed to transform string argument into integer
                    except ValueError:
                        client_socket.send(b'-ERR enter an integer as argument after "DELE"\r\n')

        # Transaction state - handle received data, 'RETR' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Retrieve mails, unless these were marked for deletion
        elif data.startswith('RETR'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Analyze argument given with 'RETR' command
            else:
                retr_num = data.split()[-1].strip()
                # No argument was given
                if retr_num == 'RETR':
                    client_socket.send(b'-ERR enter argument after "RETR"\r\n')

                # An argument was given, try converting this from a string into an integer
                else:
                    try:
                        retr_num = int(retr_num)

                        # Integer is out of bounds
                        if retr_num <= 0 or retr_num > len(maildrop_info):
                            client_socket.send(b'-ERR number out of range\r\n')

                        # Check if mail# is marked for deletion
                        else:
                            if retr_num in to_delete:
                                client_socket.send(b'-ERR mail is queued for deletion\r\n')

                            # Send a multi-line response terminated by '.\r\n' after +OK message
                            else:
                                client_socket.send(b'+OK prepare for receiving mail, terminated by "."\r\n')
                                for mail in maildrop_info:
                                    if mail[0] == retr_num:
                                        to_send = mail[1].split("\n")
                                        for line in to_send:
                                            line += '\r\n'
                                            client_socket.send(line.encode())
                                        client_socket.send(b'.\r\n')

                    # String argument was not an integer
                    except ValueError:
                        client_socket.send(b'-ERR enter an integer as argument after "RETR"\r\n')

        # Transaction state - handle received data, 'LIST' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Retrieve size of mail(s), no argument retrieves size for all mails in multi-line response
        elif data.startswith('LIST'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Check argument given with 'LIST' command
            else:
                argument = data.split()[-1].strip()

                # No argument was given. Send multi-line response with mail# and #octets in said mail, for all mails
                if argument == 'LIST':
                    # There are no mails in the mailbox
                    if len(maildrop_info)-len(to_delete) == 0:
                        client_socket.send(b'-ERR there are 0 mails in maildrop\r\n')

                    # Send multi-line response
                    else:
                        total_octets = 0
                        for item in maildrop_info:
                            if item[0] not in to_delete:
                                total_octets += int(item[2])
                        client_socket.send('+OK {} messages ({} octets)\r\n'.format(len(maildrop_info)-len(to_delete), total_octets).encode())

                        for item in maildrop_info:
                            if item[0] not in to_delete:
                                client_socket.send('{} {}\r\n'.format(item[0], item[2]).encode())
                        client_socket.send(b'.\r\n')

                # Argument was given, return for that mail it's #octets
                else:
                    # Try turning string argument into integer
                    try:
                        argument = int(argument)

                        # Integer out of bounds
                        if argument <= 0 or argument > len(maildrop_info):
                            client_socket.send('-ERR argument {} out of range, only {} mails\r\n'.format(argument, len(maildrop_info)).encode())

                        # Mail marked for deletion
                        elif argument in to_delete:
                            client_socket.send('-ERR message {} marked for deletion\r\n'.format(argument).encode())

                        # Send requested information
                        else:
                            amount_octets = maildrop_info[argument-1][2]
                            client_socket.send('+OK {} {}\r\n'.format(argument, amount_octets).encode())

                    # Argument was not an integer
                    except ValueError:
                        client_socket.send(b'-ERR enter an integer as argument after "LIST", or enter no argument\r\n')

        # Transaction state - handle received data, 'STAT' command follows RFC1939 protocol
        #                                               -> 1) checks Authentification State was passed
        #                                               -> 2) Retrieve total amount of mails in mailbox and total size in octets. Response is single-line
        elif data.startswith('STAT'):
            # Check if client sends commands in correct order, no command in Transaction State may be initialized before passing Authentification State
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')

            # Construct the response
            else:
                amount_mails2 = 0
                amount_octets2 = 0
                for mail in maildrop_info:
                    if mail[0] not in to_delete:
                        amount_octets2 += mail[2]
                        amount_mails2 += 1

                client_socket.send('+OK {} {}\r\n'.format(amount_mails2, amount_octets2).encode())

        # Update state - handle received data, 'QUIT' command follows RFC1939 protocol
        #                                               -> 1) Run different code depending on if Authentification State was passed or not
        #                                               -> 2) Update to mailbox needed if Authentification State was passed
        elif data.startswith('QUIT'):
            mailbox_dir = os.path.join('users', temp_user)
            mailbox_file2 = os.path.join(mailbox_dir, 'my_mailbox.txt')

            # Determine if Authentification State was passed
            if mailbox_lock is True:

                # Delete mails marked for deletion, by clearing mailbox entirely and rewriting all mails but the ones marked for deletion.
                # Body of mails was appened to list maildrop_info in Authentification State, if said state was passed successfuly.
                with open(mailbox_file2, 'w') as f:
                    for mail in maildrop_info:
                        if not mail[0] in to_delete:
                            f.write(mail[1])
                            f.write('\n.\n')

                # Pycharm gives a warning here for "mailbox_file", we can ignore this since "mailbox_file" cannot exist if 'PASS' code
                # hasn't been run and succesfully applied a lock. Turning mailbox_lock to true.
                remove_lock(mailbox_path)

                # Close the socket connection, after removing lock on mailbox
                client_socket.send(b'+OK POP3 server closing, mailbox lock suspended\r\n')
                client_socket.close()
                break

            # Authentification state not passed, simply terminate connection without the need to update mailbox
            else:
                # Close the socket connection
                client_socket.send(b'+OK POP3 server closing\r\n')
                client_socket.close()
                break

        # Handle the received data, 'APOP' command follows RFC1939 protocol
        elif data.startswith('APOP'):
            client_socket.send(b'-ERR command not implemented\r\n')

        # Handle the received data, 'TOP' command follows RFC1939 protocol
        elif data.startswith('TOP'):
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')
            else:
                client_socket.send(b'-ERR command not implemented\r\n')

        # Handle the received data, 'UIDL' command follows RFC1939 protocol
        elif data.startswith('UIDL'):
            if mailbox_lock is False:
                client_socket.send(b'-ERR commands out of order\r\n')
            else:
                client_socket.send(b'-ERR command not implemented\r\n')

        # Handle the received data, unknown commands to the RFC1939 protocol
        else:
            # Unknown command, send an error message
            client_socket.send(b'-ERR enter a valid command\r\n')

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
