import socket
import smtplib
import sys

# Accept server IP address as command-line argument
server_ip = input('Server IP address: ')
SMTP_port = input('SMTP_port: ')
# Function to authenticate user with POP3 server
def authenticate(username, password):
    try:
        pop3_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pop3_socket.connect((server_ip, 110))  # Connect to POP3 server
        response = pop3_socket.recv(1024).decode()  # Receive initial server response
        print(response)

        # Send USER command
        pop3_socket.send(f'USER {username}\r\n'.encode())
        response = pop3_socket.recv(1024).decode()
        print(response)

        # Send PASS command
        pop3_socket.send(f'PASS {password}\r\n'.encode())
        response = pop3_socket.recv(1024).decode()
        print(response)

        if response.startswith('+OK'):
            print("Authentication successful")
            return True
        else:
            print("Authentication failed")
            return False
    except Exception as e:
        print("Error:", e)
        return False

# Function for sending mail
def send_mail(connection):
    data = connection.recv(1024).decode().strip()
    print('Server:', data)
    #print("Enter the mail to be sent in the following format:")
    #print("From: <username>@<domain name>")
    #print("To: <username>@<domain name>")
    #print("Subject: <subject string, max 150 characters>")
    #print("<Message body – one or more lines, terminated by a final line with only a full stop character>")

    # Get email details from user input
    from_email = input("From: ")
    to_email = input("To: ")
    subject = input("Subject: ")

    # Read message body until a line with only a full stop character
    message_body = []
    print("Enter message body (end with a line containing a single full stop character):")
    while True:
        line = input()
        if line == '.':
            break
        message_body.append(line)

    # Construct the email message
    email_message = f"From: {from_email}\nTo: {to_email}\nSubject: {subject}\n"
    email_message += "\n".join(message_body)
    # Send email using SMTP
    try:
        initial_response = connection.recv(1024).decode().strip()
        print(initial_response.decode())

        # Send HELO command
        connection.send(b'HELO\r\n')
        helo_response = connection.recv(1024).decode().strip()
        print(helo_response.decode())

        # Send MAIL FROM command
        connection.send(f'MAIL FROM:<{from_email}>\r\n'.encode())
        mail_from_response = connection.recv(1024).decode().strip()
        print(mail_from_response.decode())

        # Send RCPT TO command
        connection.send(f'RCPT TO:<{to_email}>\r\n'.encode())
        rcpt_to_response = connection.recv(1024).decode().strip()
        print(rcpt_to_response.decode())

        # Send DATA command
        connection.send(b'DATA\r\n')
        data_response = connection.recv(1024).decode().strip()
        print(data_response.decode())

        # Send email message
        connection.send(email_message.encode())
        # End email message with a single full stop on a new line
        connection.send(b'\r\n.\r\n')
        data_end_response = connection.recv(1024).decode().strip()
        print(data_end_response.decode())

        # Close connection with QUIT command
        connection.send(b'QUIT\r\n')
        quit_response = connection.recv(1024).decode().strip()
        print(quit_response.decode())

        print("Mail sent successfully")
        connection.quit()
    except Exception as e:
        print("Failed to send mail:", e)

# Function to retrieve list of emails from POP3 server
def retrieve_emails():
    try:
        pop3_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pop3_socket.connect((server_ip, 110))  # Connect to POP3 server
        response = pop3_socket.recv(1024).decode()  # Receive initial server response
        print(response)

        # Send LIST command
        pop3_socket.send(b'LIST\r\n')
        response = pop3_socket.recv(1024).decode()
        print(response)

        # Parse response to extract email list
        email_list = response.split('\n')
        for email_info in email_list[1:-2]:  # Skip first and last lines (response codes)
            email_info = email_info.strip().split()
            email_number = email_info[0]
            email_size = email_info[1]
            print(f"No. {email_number} Sender: {email_info[2]} Date: {email_info[3]} Subject: {email_info[4]}")
    except Exception as e:
        print("Error:", e)

# Function to retrieve a specific email from the POP3 server
def retrieve_specific_email(pop3_socket, email_number):
    try:
        # Send RETR command to retrieve specific email
        pop3_socket.send(f'RETR {email_number}\r\n'.encode())
        response = pop3_socket.recv(1024).decode()
        print(response)

        # Print email content
        print("Email content:")
        while True:
            response = pop3_socket.recv(1024).decode()
            if response == '.\r\n':
                break
            print(response.strip())
    except Exception as e:
        print("Error:", e)

# Function to delete a specific email from the POP3 server
def delete_specific_email(pop3_socket, email_number):
    try:
        # Send DELE command to delete specific email
        pop3_socket.send(f'DELE {email_number}\r\n'.encode())
        response = pop3_socket.recv(1024).decode()
        print(response)
    except Exception as e:
        print("Error:", e)

# Main function to handle mail management options
def manage_mail(username, password):
    pop3_socket = authenticate(username, password)
    if pop3_socket is None:
        return

    print("Mail management options:")
    print("1. Retrieve email list")
    print("2. Retrieve specific email")
    print("3. Delete specific email")
    print("4. Quit")

    while True:
        option = input("Enter your choice: ")

        if option == '1':
            retrieve_emails(pop3_socket)
        elif option == '2':
            email_number = input("Enter the number of the email to retrieve: ")
            retrieve_specific_email(pop3_socket, email_number)
        elif option == '3':
            email_number = input("Enter the number of the email to delete: ")
            delete_specific_email(pop3_socket, email_number)
        elif option == '4':
            print("Quitting...")
            pop3_socket.send(b'QUIT\r\n')  # Send QUIT command to POP3 server
            response = pop3_socket.recv(1024).decode()
            print(response)
            pop3_socket.close()
            break
        else:
            print("Invalid option. Please try again.")

# Function to search emails containing specific words/sentences
def search_by_words(pop3_socket, search_query):
    try:
        # Send RETR command to retrieve each email
        pop3_socket.send(b'LIST\r\n')
        response = pop3_socket.recv(1024).decode()
        email_list = response.split('\n')[1:-2]  # Exclude response codes
        for email_info in email_list:
            email_number = email_info.split()[0]
            pop3_socket.send(f'RETR {email_number}\r\n'.encode())
            email_content = pop3_socket.recv(1024).decode()
            if search_query in email_content:
                print(email_content)
    except Exception as e:
        print("Error:", e)

# Function to search emails based on time
def search_by_time(pop3_socket, search_time):
    try:
        # Send RETR command to retrieve each email
        pop3_socket.send(b'LIST\r\n')
        response = pop3_socket.recv(1024).decode()
        email_list = response.split('\n')[1:-2]  # Exclude response codes
        for email_info in email_list:
            email_number = email_info.split()[0]
            pop3_socket.send(f'RETR {email_number}\r\n'.encode())
            email_content = pop3_socket.recv(1024).decode()
            # Extract email received time and compare with search_time
            # Assuming email received time is in a specific format within email content
            if search_time in email_content:
                print(email_content)
    except Exception as e:
        print("Error:", e)

# Function to search emails based on address
def search_by_address(pop3_socket, search_address):
    try:
        # Send RETR command to retrieve each email
        pop3_socket.send(b'LIST\r\n')
        response = pop3_socket.recv(1024).decode()
        email_list = response.split('\n')[1:-2]  # Exclude response codes
        for email_info in email_list:
            email_number = email_info.split()[0]
            pop3_socket.send(f'RETR {email_number}\r\n'.encode())
            email_content = pop3_socket.recv(1024).decode()
            # Extract email address and compare with search_address
            # Assuming email address is in a specific format within email content
            if search_address in email_content:
                print(email_content)
    except Exception as e:
        print("Error:", e)

# Function to handle mail searching options
def search_mail(username, password):
    pop3_socket = authenticate(username, password)
    if pop3_socket is None:
        return

    print("Mail searching options:")
    print("1. Search by words/sentences")
    print("2. Search by time")
    print("3. Search by address")
    print("4. Quit")

    while True:
        option = input("Enter your choice: ")

        if option == '1':
            search_query = input("Enter words/sentences to search: ")
            search_by_words(pop3_socket, search_query)
        elif option == '2':
            search_time = input("Enter time in MM/DD/YY format to search: ")
            search_by_time(pop3_socket, search_time)
        elif option == '3':
            search_address = input("Enter address to search: ")
            search_by_address(pop3_socket, search_address)
        elif option == '4':
            print("Quitting...")
            pop3_socket.send(b'QUIT\r\n')  # Send QUIT command to POP3 server
            response = pop3_socket.recv(1024).decode()
            print(response)
            pop3_socket.close()
            break
        else:
            print("Invalid option. Please try again.")

   # Main function to display menu and handle user options
def main():
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    while True:
        print("Choose an option:")
        print("a) Mail Sending")
        print("b) Mail Management")
        print("c) Mail Searching")
        print("d) Exit")
        option = input("Enter your choice: ")

        if option == 'a':
            connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # attempt to connect to the host
                connection.connect((server_ip, SMTP_port))
                send_mail(connection)
            finally:
                connection.close()

        elif option == 'b':
            manage_mail(username, password)
        elif option == 'c':
            search_mail(username)
        elif option == 'd':
            print("Exiting...")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()