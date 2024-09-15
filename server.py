import socket
import threading
import sys
import logging

# Function to handle a client's communication
def handle_client(client_socket, other_client_socket):
    client_socket.send('Conexão estabelecida. Aguardando conversa...\n'.encode())
    while True:
        data = client_socket.recv(1024)  # Receive data from this client
        if data:
            ip, _ = client_socket.getpeername()
            print(f"{ip}: {data.decode()}")
                
            # Forward the data to the other client
            other_client_socket.send(data)

            # If the client wants to quit
            if data.decode().split(':')[-1].strip() == '\q':
                client_socket.send('\g'.encode())
                client_socket.close()
                other_client_socket.close()
                break
        else:
            print("Client disconnected.")
            break
    client_socket.close()

# Start server and wait for connections
def start_server():
    # Create a TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    if len(sys.argv) < 3:
        logging.warning(f"Nem todos os parâmetros foram definidos. Usando valores padrão.")
        logging.warning(f"Uso correto: {sys.argv[0]} <máscara> <porta>")
    
    # Default values if not passed via command line
    mask = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    porta = int(sys.argv[2]) if len(sys.argv) > 2 else 65432

    # Bind the socket to the address and port
    server_address = (mask, porta)
    server_socket.bind(server_address)

    # Listen for incoming connections (with a maximum queue of 2)
    server_socket.listen(2)
    print(f"Server is listening on {server_address}")

    # Accept exactly two connections
    connection1, client_address1 = server_socket.accept()
    print(f"Connection from {client_address1} established.")

    connection2, client_address2 = server_socket.accept()
    print(f"Connection from {client_address2} established.")

    # Start threads to handle each client connection
    thread1 = threading.Thread(target=handle_client, args=(connection1, connection2))
    thread2 = threading.Thread(target=handle_client, args=(connection2, connection1))

    thread1.start()
    thread2.start()

    # Wait for both threads to finish
    thread1.join()
    thread2.join()

    # Close the server socket when done
    print("Closing server.")
    server_socket.close()

if __name__ == "__main__":
    start_server()