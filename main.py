import tkinter as tk
from portfolio_balancer.balancer import Balancer
from table import Table

class MainApplication(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("Portfolio Hub")
        table = Table(self.parent)
        Balancer.balance("No file", 500, 100)

if __name__ == "__main__":
    root = tk.Tk()
    MainApplication(root).pack(side="top", fill="both", expand=True)
    root.mainloop()