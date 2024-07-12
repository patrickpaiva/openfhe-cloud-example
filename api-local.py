from flask import Flask, request, jsonify
from openfhe import *
import requests
import os
import tempfile
import sqlite3
import base64

app = Flask(__name__)

# Configurar diretório de dados temporário
datafolder = tempfile.mkdtemp()

# Configurar diretório de chaves
key_dir = 'keys'
if not os.path.exists(key_dir):
    os.makedirs(key_dir)

# Inicializar a conexão com a base de dados local
conn = sqlite3.connect('local_contexts.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS client_contexts (
    client_id TEXT PRIMARY KEY,
    context BLOB
)
''')
conn.commit()

# Funções para lidar com criptografia
def create_context():
    parameters = CCParamsCKKSRNS()
    parameters.SetMultiplicativeDepth(1)
    parameters.SetScalingModSize(50)
    parameters.SetBatchSize(8)

    cc = GenCryptoContext(parameters)
    cc.Enable(PKESchemeFeature.PKE)
    cc.Enable(PKESchemeFeature.KEYSWITCH)
    cc.Enable(PKESchemeFeature.LEVELEDSHE)

    return cc

def store_context(client_id, cc):
    filename = os.path.join(datafolder, f'context_{client_id}.bin')
    if not SerializeToFile(filename, cc, BINARY):
        raise Exception("Erro serializando novo contexto de seguranca.")
    with open(filename, 'rb') as f:
        serialized_cc = f.read()
    cursor.execute('INSERT INTO client_contexts (client_id, context) VALUES (?, ?)', (client_id, serialized_cc))
    conn.commit()
    os.remove(filename)

def load_context(client_id):
    cursor.execute('SELECT context FROM client_contexts WHERE client_id = ?', (client_id,))
    row = cursor.fetchone()
    if row:
        filename = os.path.join(datafolder, f'context_{client_id}.bin')
        with open(filename, 'wb') as f:
            f.write(row[0])
        cc, res = DeserializeCryptoContext(filename, BINARY)
        if not res:
            raise Exception("Could not read the crypto context")
        os.remove(filename)
        return cc
    else:
        return None

def encrypt_value(cc, publicKey, value, filename):
    ptx = cc.MakeCKKSPackedPlaintext([value])
    c = cc.Encrypt(publicKey, ptx)
    SerializeToFile(filename, c, BINARY)

def decrypt_value(cc, secretKey, filename):
    c, res = DeserializeCiphertext(filename, BINARY)
    if not res:
        raise Exception("Could not read the ciphertext")
    ptx = cc.Decrypt(c, secretKey)
    return ptx.GetRealPackedValue()[0]

# Carregar ou criar chaves públicas/privadas
public_key_file = os.path.join(key_dir, "key-public.txt")
private_key_file = os.path.join(key_dir, "key-private.txt")

if os.path.exists(public_key_file) and os.path.exists(private_key_file):
    publicKey, res1 = DeserializePublicKey(public_key_file, BINARY)
    privateKey, res2 = DeserializePrivateKey(private_key_file, BINARY)
    if not (res1 and res2):
        raise Exception("Could not read keys from files")
else:
    cc = create_context()
    keypair = cc.KeyGen()
    SerializeToFile(public_key_file, keypair.publicKey, BINARY)
    SerializeToFile(private_key_file, keypair.secretKey, BINARY)
    publicKey = keypair.publicKey
    privateKey = keypair.secretKey

API_CLOUD_URL = 'http://127.0.0.1:5001'

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    client_id = request.json['client_id']
    data = request.json['data']
    valor = request.json['valor']
    
    cc = load_context(client_id)
    if not cc:
        cc = create_context()
        store_context(client_id, cc)

    filename = os.path.join(datafolder, f'temp_{client_id}_{data}.bin')
    encrypt_value(cc, publicKey, valor, filename)
    
    with open(filename, 'rb') as f:
        encrypted_valor = f.read()
    
    os.remove(filename)
    
    cc_filename = os.path.join(datafolder, f'cc_{client_id}.bin')
    SerializeToFile(cc_filename, cc, BINARY)
    
    with open(cc_filename, 'rb') as f:
        serialized_cc = f.read()
    
    os.remove(cc_filename)
    
    response = requests.post(f'{API_CLOUD_URL}/add_transaction', files={
        'client_id': (None, client_id),
        'data': (None, data),
        'valor': (filename, encrypted_valor, 'application/octet-stream'),
        'context': (cc_filename, serialized_cc, 'application/octet-stream')
    })
    
    return response.json()

@app.route('/get_balance', methods=['POST'])
def get_balance():
    client_id = request.json['client_id']
    
    response = requests.post(f'{API_CLOUD_URL}/get_balance', json={
        'client_id': client_id
    })

    balance_str = response.json()['balance']
    balance_bytes = base64.b64decode(balance_str)
    
    filename = os.path.join(datafolder, f'temp_balance_{client_id}.bin')
    with open(filename, 'wb') as f:
        f.write(balance_bytes)
    
    cc = load_context(client_id)
    if not cc:
        raise Exception("Client context not found")
    
    balance = decrypt_value(cc, privateKey, filename)
    os.remove(filename)
    
    return jsonify({'balance': round(balance,2)})

if __name__ == '__main__':
    app.run(port=5000)
