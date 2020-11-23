from tkinter import *
import socket
from Client import Client
from Server import Server

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("1 -> Chcete data na server poslat")
print("2 -> Chcete data zo servera stiahnut")
option = input("Zadajte svoju ulohu: ")  # 1 alebo 2
message = input("Napiste spravu: ")
server_ip = input("Zadajte cielovu IP adresu servera: ")
server_port = input("Zadajte cielovy port servera: ")

if option == "1":   # som vysielac
    sender = Client(message)
    receiver = Server(server_ip, server_port)
    receiver.receive(sender)
elif option == "2":
    sender = Server()
    receiver = Client()
    sender.send(message)
















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
