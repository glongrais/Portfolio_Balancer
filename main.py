import customtkinter
from CTkTable import *

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Portfolio Hub")
        self.geometry("1920x1080")
        self.grid_columnconfigure((0, 2), weight=1)

        self.button = customtkinter.CTkButton(self, text="my button", command=self.button_callback)
        self.button.grid(row=0, column=0, padx=20, pady=20, sticky="ew", columnspan=2)
        self.checkbox_1 = customtkinter.CTkCheckBox(self, text="checkbox 1")
        self.checkbox_1.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        self.checkbox_2 = customtkinter.CTkCheckBox(self, text="checkbox 2")
        self.checkbox_2.grid(row=1, column=1, padx=20, pady=(0, 20), sticky="w")

        value = [[1,2,3,4,5],
                [1,2,3,4,5],
                [1,2,3,4,5],
                [1,2,3,4,5],
                [1,2,3,4,5]]

        table = CTkTable(master=self, row=5, column=12, values=value)
       # table.pack(expand=True, fill="both", padx=20, pady=20)
        table.grid(row=2, column=0, padx=20, pady=20)
    def button_callback(self):
        print("button pressed")

app = App()
app.mainloop()