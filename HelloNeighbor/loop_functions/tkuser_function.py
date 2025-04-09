import tkinter as tk
from tkinter import ttk
import json
# sudo apt install py-tk

class BlockchainGUI:
    def __init__(self):
        self.columns = []    # Stores column names dynamically
        self.blocks  = []

        self.root = tk.Tk()
        self.root.title("Blockchain Viewer")
        self.root.geometry("900x400")

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Block Tab
        self.block_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.block_frame, text="Blocks")
        self.tree_blocks = ttk.Treeview(self.block_frame, show="headings")
        self.tree_blocks.pack(fill=tk.BOTH, expand=True)

        # Transaction Tab (Placeholder for now)
        self.tx_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tx_frame, text="Transactions")
        self.tree_transactions = ttk.Treeview(self.tx_frame, show="headings")
        self.tree_transactions.pack(fill=tk.BOTH, expand=True)
        
        # Start updating the treeview
        self.update_treeview()

    def start(self):
        self.root.mainloop()
        
    def add_block(self, block_as_str):
        block = json.loads(block_as_str)  # Convert JSON string to dictionary
        self.blocks.append(block)

        if not self.columns:
            self.columns = list(block.keys())  # Extract column names
            self.tree_blocks["columns"] = self.columns

            for col in self.columns:
                self.tree_blocks.heading(col, text=col)
                width = max(100, len(col) * 10)
                self.tree_blocks.column(col, width=width, anchor="center")
    
    def update_treeview(self):
        self.root.after(1000, self.update_treeview)

        for block in self.blocks:
            values = [block.get(col, "N/A") for col in self.columns]  
            self.tree_blocks.insert("", "end", values=values)
        
        self.blocks = []

