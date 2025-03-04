#!/usr/bin/env python3

# /* Import Packages */
#######################################################################
import time, sys, os, json
from hexbytes import HexBytes

mainFolder = os.environ['MAINFOLDER']
experimentFolder = os.environ['EXPERIMENTFOLDER']
sys.path += [mainFolder, experimentFolder]

from controllers.params import params as cp
from loop_functions.params import params as lp

import tkinter as tk
from tkinter import ttk

from toychain.src.utils.helpers import gen_enode
from toychain.src.consensus.ProofOfAuth import ProofOfAuthority, BLOCK_PERIOD
from toychain.src.Node import Node
from toychain.src.Block import Block, State
from toychain.src.Transaction import Transaction


class BlockchainGUI:
    def __init__(self, root, node):
        self.root = root
        self.node = node
        self.i = 0

        self.root.title("Blockchain Viewer")
        self.root.geometry("700x400")

        self.tree = ttk.Treeview(root, columns=("Height", "Miner", "Difficulty", "Total Diff", "Block Hash", "Timestamp"), show="headings")

        # Configuração das colunas
        for col in ("Height", "Miner", "Difficulty", "Total Diff", "Block Hash", "Timestamp"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Inicia a atualização periódica da árvore
        self.update_treeview()
    

    def update_treeview(self):
        """ Atualiza a exibição da lista de blocos e agenda próxima atualização. """
        self.tree.delete(*self.tree.get_children())  # Limpa a tabela

        for block in self.node.chain:
            self.tree.insert("", "end", values=(
                block.height, block.miner_id, block.difficulty, block.total_difficulty, block.hash, block.timestamp
            ))

        # Atualiza a cada 2 segundos (2000 ms)


        self.root.after(2000, self.update_treeview)


GENESIS = Block(0, 0000, [], [gen_enode(i+1) for i in range(int(lp['environ']['NUMROBOTS']))], 0, 0, 0, nonce = 1, state = State())
glassnode = Node("0", '127.0.0.1', 1230, ProofOfAuthority(genesis = GENESIS))

glassnode.start()

for producer in GENESIS.miner_id:
    glassnode.add_peer(producer)

root = tk.Tk()
app = BlockchainGUI(root, glassnode)
root.mainloop() 

# Ensure the program exits completely after the GUI is closed
glassnode.stop()  # If your Node class has a stop method, call it to shut down cleanly
sys.exit()  # Forcefully exit the script
