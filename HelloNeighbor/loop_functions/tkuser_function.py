import tkinter as tk
from tkinter import ttk

class BlockchainGUI:
    def __init__(self):

        self.hash_list  = []
        self.block_list = []

        self.root = tk.Tk()
        self.root.title("Blockchain Viewer")
        self.root.geometry("700x400")

        self.tree = ttk.Treeview(self.root, columns=("Height", "Miner", "Difficulty", "Total Diff", "Block Hash", "Timestamp"), show="headings")

        # Configuração das colunas
        for col in ("Height", "Miner", "Difficulty", "Total Diff", "Block Hash", "Timestamp"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)


        # Inicia a atualização periódica da árvore
        self.update_treeview()

    def start(self):
        self.root.mainloop()
        

    def send_new_blocks(self, blocks):
        self.block_list += blocks

    def update_treeview(self):

        self.root.after(1000, self.update_treeview)

        self.tree.insert("", "end", values=("1"))


        