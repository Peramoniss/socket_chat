import math
import os
from pathlib import Path
import socket as s
import sys
import logging
import select
import threading
import termios
import tty
import subprocess

# Global variables
username = None
end = 0
lock = threading.Lock()
current_input = ""
original_stty = None

# Terminal settings backup
def set_raw_mode(stream):
    global original_stty
    original_stty = termios.tcgetattr(stream)
    tty.setcbreak(stream)

def restore_mode(stream):
    termios.tcsetattr(stream, termios.TCSANOW, original_stty)

def send_notification(data):
    #NEXT STEP: VERIFY IF WINDOW IS CURRENTLY ACTIVE. IF SO, RETURN. OTHERWISE, SEND NOTIFICATION
    script_dir = Path(__file__).parent
    icon_path = script_dir / "notification-alert.svg"
    command = [
        "notify-send",
        "-t", "2000",
        "-i", str(icon_path),  # Convert Path object to string
        "New message incoming",
        data
    ]

    subprocess.run(command)

# Flush input buffer
def flush_input():
    while True:
        ready_to_read, _, _ = select.select([sys.stdin], [], [], 0)  # 0 timeout for non-blocking check
        if ready_to_read:
            sys.stdin.read(1)  # Drain one character at a time from stdin until buffer is empty
        else:
            break

# Close the connection
def close_connection(soquete):
    print("Closing the connection")
    soquete.close()

# Start client
def start_client():
    global username
    soquete = s.socket(s.AF_INET, s.SOCK_STREAM)

    if len(sys.argv) < 3:
        logging.warning(f"Nem todos parametros foram delimitados. Valores padroes serao atribuidos aos campos nao informados.")
        logging.warning(f"Chamada completa: {sys.argv[0]} <ip> <porta>")
    ip = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 65432

    username = input("Select an username: ")

    server_address = (ip, porta)
    print(f"Connecting to {server_address}")
    soquete.connect(server_address)

    try:
        data = soquete.recv(1024)
        print(f"Received: {data.decode()}")
        return soquete
    except:
        close_connection(soquete)

# Receive messages
def receive_messages(soquete):
    global end
    try:
        while end != 1:
            data = soquete.recv(1024)
            if not data:
                logging.warning('A conexão com o servidor foi perdida')
                end = 1
                close_connection(soquete)
                break
            elif data.decode().split(':')[-1].strip() == '\q':
                print('Seu companheiro de chat desistiu da conversa :(')
                end = 1
                close_connection(soquete)
                break
            elif data.decode() == '\g':
                print('Escapou da coversa')
                end = 1
                close_connection(soquete)
                break

            with lock:
                    #print(f"\rReceived: {data.decode()}")
                    #print(f"Enter: {current_input}", end='', flush=True)  # Redraw user input
                tput = subprocess.Popen(['tput', 'cols'], stdout=subprocess.PIPE)
                column_size = int(tput.communicate()[0].strip())
                limit = column_size - len('Enter: ')
                sys.stdout.write(f"\r\033[2K{data.decode()}\n\033[92mEnter: {current_input[-limit:]}\033[0m")

            send_notification(data.decode())
    finally:
        restore_mode(sys.stdin)

# Send messages
def send_messages(soquete):
    global current_input
    global end
    global username
    set_raw_mode(sys.stdin)
    sys.stdout.write(f"\r\033[K\033[92mEnter: {current_input}\033[0m")
    
    try:
        while end != 1:
            flush_input()
            ready_to_read = select.select([sys.stdin,],[],[],2.0)[0]
            if ready_to_read:
                key = sys.stdin.read(1)  # Capture one character at a time
                with lock:
                    if key == '\n':  # If Enter is pressed, send the message
                        #\r -> return to beginning of the line
                        #\033 -> escape character, indicates formatting
                        #\033[2K -> clears line (\033[K clears line from cursor to end)
                        #\033[32m -> m escape is for stylize. 32 is for green, 0 is for resetting
                        print(f'\r\033[2K\033[32mYou: {current_input}\033[0m')
                        soquete.send(username.encode() + ": ".encode() + current_input.encode())
                        if current_input == '\q':
                            close_connection(soquete)
                            end = 1
                            #done.set()
                            break
                        current_input = ""  # Reset the input buffer
                    elif key == '\x7f':  # Handle backspace
                        current_input = current_input[:-1]
                    else:
                        current_input += key
                        
                    # Redraw the input
                    tput = subprocess.Popen(['tput', 'cols'], stdout=subprocess.PIPE)
                    column_size = int(tput.communicate()[0].strip())
                    limit = column_size - len('Enter: ')
                    sys.stdout.write(f"\r\033[2K\033[92mEnter: {current_input[-limit:]}\033[0m")
            else:
                pass
    finally:
        restore_mode(sys.stdin)

# Main loop
def main_loop(soquete):
    # Start the threads for sending/receiving messages and the counter
    receive_thread = threading.Thread(target=receive_messages, args=[soquete])
    send_thread = threading.Thread(target=send_messages, args=[soquete])

    send_thread.start()
    receive_thread.start()

    receive_thread.join()
    send_thread.join()
    restore_mode(sys.stdin)

if __name__ == "__main__":
    curdir = os.getcwd()
    print('My current directory is {}'.format(curdir))

    soquete = start_client()
    if soquete:
        main_loop(soquete)