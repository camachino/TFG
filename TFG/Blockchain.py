import json
import hashlib
import time


class Block:

    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        #####
        # Constructor
        #      index: unique ID of a block
        #      transactions: list of transaction contained in the block
        #      timestamp: time of block creation
        #      previous_hash: hash value of the previous block
        #      nonce: number used to solve the proof of work initialized to 0
        #####
        
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        #####
        # Method to compute the hash of the block
        #####
        
        block_string = json.dumps(self.__dict__, sort_keys = True)
        hash_block_string = hashlib.sha256(block_string.encode()).hexdigest()
        
        return hash_block_string


class Blockchain:
    
    def __init__(self, difficulty):
        #####
        # Constructor
        #      chain: current chain initialized as empty
        #      unconfirmed_transactions: list of unconfirmed transactions initialized as empty
        #      difficulty: number of initial 0s that the hashes must have to solve the proof of work
        #      create_genesis_block: call to create the first block of the blockchain
        #####
        
        self.chain = []
        self.unconfirmed_transactions = []
        self.difficulty = difficulty
        self.create_genesis_block()

    def create_genesis_block(self):
        #####
        # Method to create and append to the blockchain the Genesis Block by calling the Block Class Constructor with empty
        # or 0 value parameters
        # It adds the hash of the block (current_hash) value as part of the block parameters
        #####
        genesis_block = Block(0,[],time.time(),"0")
        genesis_block.current_hash = self.proof_of_work(genesis_block)
        self.chain.append(genesis_block)

    @property
    def last_block(self):
         return self.chain[-1]
        
    def mine(self):
        #####
        # Method that gathers all the unconfirmed transactions, creates a block with those transactions, mines the block 
        # by doing the proof of work and adds it to the blockchain
        # It also adds a fake transaction which will include the "Excedente" of the block
        #####
        
        if len(self.unconfirmed_transactions) <= 0:
            return False
        
        # Calculo Excedente de Bloque
        excedente = 0
        for x in range(len(self.unconfirmed_transactions)):
            excedente = excedente + int(self.unconfirmed_transactions[x]['Excedente'])
        body = {
                "Numero Factura" : "9999999999A",
                "ID Cliente" : "9999999A",
                "Potencia Consumida (kWh)" : "0",
                "Potencia Producida (kWh)" : "0",
                "Excedente": str(excedente),
                "timestamp": time.time()
        }
        self.add_new_transaction(body)
        
        last_block = self.chain[-1]
        new_block = Block(last_block.index+1, self.unconfirmed_transactions, time.time(), last_block.current_hash)
        proof = self.proof_of_work(new_block)
        self.append_block(new_block,proof)
        self.unconfirmed_transactions = []
        
        return new_block.index
    
    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

    def proof_of_work(self, block):
        #####
        # Method that computes the hash of the block changing in each iteration the nonce value of the block until the 
        # resulting hash of the block has as many initial 0s as the difficulty required by the blockchain
        #####
        
        block.nonce = 0
        hash = block.compute_hash()
        
        while not hash[0:self.difficulty] == '0' * self.difficulty:
            block.nonce = block.nonce + 1
            hash = block.compute_hash()

        return hash
    
    def append_block(self, block, hash):
        #####
        # Method that validates that the block previous hash corresponds to the last block of the chain and that 
        # the block is well mined before adding the block to the chain
        #####
        
        if not block.previous_hash == self.chain[-1].current_hash:
            return False
        if not self.is_valid_proof(block, hash):
            return False
        block.current_hash = hash
        self.chain.append(block)
        return True

    def is_valid_proof(self, block, hash):
        #####
        # Method that validates that the block hash is correct and has the difficulty required by the blockchain
        #####
        
        if not hash[0:self.difficulty] == '0' * self.difficulty:
            return False
        if not hash == block.compute_hash():
            return False

        return True


    def check_chain(self, blocks):
        #####
        # Method that validates that the WHOLE chain is correctly mined and linked
        #####
        
        for block in blocks:
            current_hash = block.current_hash
            delattr(block, 'current_hash')
            if not self.is_valid_proof(block,current_hash):
                return False
            if not (block.previous_hash == self.chain[block.index-1].current_hash or (block.index == 0 and block.previous_hash == '0')):
                return False
            block.current_hash = current_hash
        return True