from flask import Flask, jsonify, request
from Blockchain import Blockchain, Block
import json
import requests
import time

app = Flask(__name__)

# Change port to launch different nodes with the same API
#PORT = 12121    # Polideportivo
#PORT = 13131   # Cliente Individual
PORT = 14141   # Ayuntamiento

# Create the blockchain
blockchain = Blockchain(difficulty=3)

# peers are the nodes that this API acknowledges
peers = set()

#################################################### 
#################################################### 
#################################################### 

@app.route('/new_transaction', methods = ['POST'])
def new_transaction():
    #####
    # Validates the transaction, adds a timestamp to it, and adds the transaction to the list of unconfirmed transactions
    # It also adds the Excedente parameter to the transaction
    #####
      
    tx_data = request.get_json()
    required_fields = ["Numero Factura", "ID Cliente", "Potencia Consumida (kWh)", "Potencia Producida (kWh)", "Periodo de Facturacion"]

    error = validator(required_fields, tx_data.keys())
    if error:
        return error, 404
    
    tx_data["Excedente"] = str(int(tx_data["Potencia Producida (kWh)"])-int(tx_data["Potencia Consumida (kWh)"]));
    tx_data["timestamp"] = time.time();

    blockchain.add_new_transaction(tx_data)
    return "Success", 201

@app.route('/chain', methods = ['GET'])
def chain():
    #####
    # Obtains the current chain (length, blocks, and peers)
    #####
    
    chain=[]
    for block in blockchain.chain:
        chain.append(block.__dict__)
    response = {
        "length"    : len(blockchain.chain),
        "chain"     : chain,
        "peers"     : list(peers)
    }
    return response, 200

@app.route('/mine', methods = ['GET'])
def mine():
    #####
    # Updates the chain to match the longer chain among its peers. Then mines the block and checks for any possible forks.
    # If there is a fork, it will not mine the block and all the transaction used in the block will come part of 
    # unconfirmed transactions again
    #####
    
    # Make sure the chain is the longest one among the peers
    consensus()
    
    # Mine
    unconfirmed_transactions = blockchain.unconfirmed_transactions
    index = blockchain.mine()
    block = blockchain.chain[index]
    
    # If the block has been mined succesfully
    if index:
        # Everybody should have a shorter chain (consensus() = False)
        if not consensus():
            announce_new_block(blockchain.chain[-1], request)
            return "Block #"+str(index)+" is mined", 200
        
        # If there's someone with a longer or equal length chain, someone has mined the block at the same time (Fork)
        else:
            blockchain.unconfirmed_transactions = unconfirmed_transactions
            if blockchain.chain[-1].current_hash == block.current_hash:
                blockchain.chain.pop(-1)
            return "Block has been discarted, it has to be mined again", 406
    else:
        return "No new Block", 200

@app.route('/pending_transactions', methods = ['GET'])
def pending_transactions():
    #####
    # Returns the unconfirmed transactions
    #####
    
    return json.dumps(blockchain.unconfirmed_transactions), 200

@app.route('/register_with_existing_node', methods = ['POST'])
def register_with_existing_node():
    #####
    # Registers the corresponding new node in both nodes by calling register_new_node()
    # Updates the blockchain of the new node to have the same one as the existing node
    #####
    
    tx_data = request.get_json()
    required_fields = ["node_address"]

    error = validator(required_fields, tx_data.keys())
    if error:
        return error, 404

    body = {"new_node_address": request.host_url}
    
    r = requests.post(""+tx_data['node_address']+'/register_new_node',json = body)

    if r.status_code == 200:
        chain = r.json()['chain']
        global blockchain
        blockchain = Blockchain(difficulty=3)

        for block_str in chain:
            if block_str['index'] == 0:
                genesis_block = Block(block_str['index'],block_str['transactions'],block_str['timestamp'],"0")
                genesis_block.current_hash = blockchain.proof_of_work(genesis_block)
                blockchain.chain = []
                blockchain.chain.append(genesis_block)
            else:
                block = Block(block_str['index'],block_str['transactions'],block_str['timestamp'],blockchain.chain[-1].current_hash)
                hash = blockchain.proof_of_work(block)
                if not blockchain.append_block(block, hash):
                    return "Error validating Blockchain",404
        
        # Update the peers of the new node
        body = {"new_node_address": tx_data['node_address']}
        requests.post(""+request.host_url+'/register_new_node',json = body)
    
    return "Registration successful",200

@app.route('/register_new_node', methods = ['POST'])
def register_new_node():
    #####
    # Registers the new node by adding it to the peers
    # Returns the chain of the existing node so that the new node can update it in register_with_existing_node()
    #####
    tx_data = request.get_json()
    required_fields = ["new_node_address"]

    error = validator(required_fields, tx_data.keys())
    if error:
        return error, 404

    peers.add(tx_data["new_node_address"])
    
    return chain()

@app.route('/add_block', methods = ['POST'])
def add_block():
    #####
    # Appends the new block to the blockchain
    #####
    
    tx_data = request.get_json()
    required_fields = ["index", "transactions", "timestamp", "previous_hash", "current_hash", "nonce"]

    error = validator(required_fields, tx_data.keys())
    if error:
        return error, 404

    block = Block(tx_data['index'], tx_data['transactions'], tx_data['timestamp'], tx_data['previous_hash'], tx_data['nonce'])
    hash = tx_data['current_hash']

    if blockchain.append_block(block, hash):
        return "Block appended to the chain",201

    return "The block was discarded",400

@app.route('/eliminate_chain', methods = ['GET'])
def eliminate_chain():
    #####
    # Eliminates all the blocks except for the Genesis Block
    #####
    current_chain = blockchain.chain
    blockchain.chain=[]
    blockchain.chain.append(current_chain[0])
    
    return "Blockchain Eliminated", 200

##########################################
##########################################
##########################################

def validator(required_fields, data_fields):
    #####
    # Validates that all the requests received have the necessary attributes 
    #####
    
    for field in required_fields:
        if field not in data_fields:
            return field + " field must be included"
    return False

def consensus():
    #####
    # Checks who among all the registered nodes have the longest chain. If it is not the current node the one that has
    # the longest chain, it updates the current node chain to match the longest one.
    #####
    
    global blockchain

    current_len = len(blockchain.chain)
    longest_chain = None
    
    # Find if there is a longer or equal chain than the current one
    for node in peers:
        r = requests.get(""+node+'/chain').json()
        if r['length'] >= current_len:
            longest_chain = r['chain']
            current_len = r['length']
    
    if longest_chain:
        # if they longest chain found is the same as the current one
        if current_len == len(blockchain.chain) and blockchain.chain[-1].current_hash == longest_chain[-1]['current_hash']:
            return True
        
        # if the longest chain found is not the same as the current one, update the current chain
        current_chain = blockchain.chain
        blockchain.chain=[]
        blockchain.chain.append(current_chain[0])
        for block_str in longest_chain:
            if not block_str['index'] == 0:
                block = Block(block_str['index'],block_str['transactions'],time.time(),blockchain.chain[-1].current_hash)
                hash = blockchain.proof_of_work(block)
                blockchain.append_block(block, hash)
        return True
    
    # If all of the peers have a shorter chain
    return False

def announce_new_block(block, request):
    #####
    # Sends the new block to all the registered nodes
    #####
    
    for node in peers:
        if node != request.host_url:
            body = block.__dict__
            requests.post(""+node+'/add_block',json = body)

##########################################
##########################################
##########################################
if __name__ == '__main__':
    app.run(port=PORT)
