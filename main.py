from tkinter import *
import socket
from Client import Client
from Server import Server

file_name = ""
message = ""

print("1 -> Chcete data na server poslat")
print("2 -> Chcete data zo servera stiahnut")
option = input("Zadajte svoju ulohu: ")  # 1 alebo 2
server_ip = input("Zadajte cielovu IP adresu servera: ")
server_port = int(input("Zadajte cielovy port servera: "))
fragment_size = int(input("Zadajte velkost fragmentu v Bytoch: "))

if option == "1":   # som vysielac
    print("1 -> Chcete poslat spravu")
    print("2 -> Chcete poslat subor")
    option2 = int(input("Zadajte svoj vyber: "))
    if option2 == 2:  # posiela sa subor
        file_name = input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
        sender = Client(option2, file_name, fragment_size, server_ip, server_port)
        receiver = Server(server_ip, server_port)
        receiver.receive(sender, fragment_size)
    elif option2 == 1:  # posiela sa sprava
        message = input("Napiste spravu: ")
        sender = Client(message)
        receiver = Server(server_ip, server_port)
        receiver.receive(sender, fragment_size)
elif option == "2":
    sender = Server(message)
    receiver = Client()
    receiver.receive(sender)
















"""root = Tk()
root.geometry("600x500")
root.title("Zadanie 2")

label_option = Label(root, text="Zadajte ci chcete data vyslat alebo prijat: ")
label = Label(root, text="Zadajte IP adresu prijimatela: ")
entry = Entry(root)
button = Button(root, text="Potvrdit", font=('arial', 10))

entry.config(width=20)
button.config(width=20)

label.grid(row=0, column=0)
entry.grid(row=0, column=1)
button.grid(row=1, column=0)


root.mainloop()"""
