import tkinter as tk
from tkinter import ttk
import json

class BlockchainGUI:
    def __init__(self):

        self.columns = []    # Stores column names dynamically
        self.blocks  = [] 

        self.root = tk.Tk()
        self.root.title("Blockchain Viewer")
        self.root.geometry("900x400")

        self.tree = ttk.Treeview(self.root, show="headings")  # Empty at start
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Inicia a atualização periódica da árvore
        self.update_treeview()

    def start(self):
        self.root.mainloop()
        

    def add_block(self, block_as_str):

        block = json.loads(block_as_str)  # Convert JSON string to dictionary
                    
        # Store block hash and data
        self.blocks.append(block)

        # If it's the first block, set up the columns dynamically
        if not self.columns:
            self.columns = list(block.keys())  # Extract column names
            self.tree["columns"] = self.columns

            # Set up column headings and widths
            for col in self.columns:
                self.tree.heading(col, text=col)
                width = max(100, len(col) * 10)  # Adjust width based on column name length
                self.tree.column(col, width=width, anchor="center")

    def update_treeview(self):
        self.root.after(1000, self.update_treeview)

        for block in self.blocks:
            values = [block.get(col, "N/A") for col in self.columns]  
            self.tree.insert("", "end", values=(values))
        
        self.blocks = []


