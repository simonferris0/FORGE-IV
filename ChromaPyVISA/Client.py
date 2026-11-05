import socket
import json

HOST = "127.0.0.1"
PORT = 5000

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect((HOST, PORT))
    print("Connected to Ethernet server!")

    # Read server responses.
    file = client.makefile("r")

    while True:
        print("\n1. Get generator status")
        print("2. Stop generator")
        print("3. Start generator")
        print("4. Exit")

        choice = input("Select: ")

        if choice == "1":
            command = {"command": "get_status"}
        elif choice == "2":
            command = {"command": "stop"}
        elif choice == "3":
            command = {"command": "start"}
        elif choice == "4":
            break
        else:
            print("Invalid selection")
            continue

        # Send command to server.
        message = json.dumps(command) + "\n"
        client.sendall(message.encode("utf-8"))

        # Receive server response.
        response = file.readline()

        if not response:
            print("Server disconnected")
            break

        print("Server response:")
        print(json.dumps(json.loads(response), indent=4))

finally:
    client.close()
    print("Client disconnected")
