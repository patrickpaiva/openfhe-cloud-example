from flask import Flask, request, jsonify
from openfhe import *
import sqlite3
import os
import tempfile
import base64

app = Flask(__name__)

# Configurar diretório de dados temporário
datafolder = tempfile.mkdtemp()

conn = sqlite3.connect('transactions.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    client_id TEXT,
    data TEXT,
    valor BLOB
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS client_contexts (
    client_id TEXT PRIMARY KEY,
    context BLOB
)
''')
conn.commit()

def cloud_sum(cc, encrypted_vectors):
    sum_vector = encrypted_vectors[0]
    for vec in encrypted_vectors[1:]:
        sum_vector = cc.EvalAdd(sum_vector, vec)
    return sum_vector

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    client_id = request.form['client_id']
    data = request.form['data']
    valor = request.files['valor'].read()
    context = request.files['context'].read()
    
    cursor.execute('''
    INSERT INTO transactions (client_id, data, valor) VALUES (?, ?, ?)
    ''', (client_id, data, valor))
    
    # Armazenar o contexto do cliente se não existir
    cursor.execute('''
    INSERT OR IGNORE INTO client_contexts (client_id, context) VALUES (?, ?)
    ''', (client_id, context))
    
    conn.commit()
    
    return jsonify({'status': 'success'})

@app.route('/get_balance', methods=['POST'])
def get_balance():
    client_id = request.json['client_id']
    
    cursor.execute('''
    SELECT valor FROM transactions WHERE client_id = ?
    ''', (client_id,))
    
    encrypted_values = []
    for row in cursor.fetchall():
        valor = row[0]
        filename = os.path.join(datafolder, f'temp_{client_id}_{len(encrypted_values)}.bin')
        with open(filename, 'wb') as f:
            f.write(valor)
        c, res = DeserializeCiphertext(filename, BINARY)
        if not res:
            raise Exception("Could not read the ciphertext")
        encrypted_values.append(c)
        os.remove(filename)
    
    if not encrypted_values:
        return jsonify({'balance': 'nada encontrado'})
    
    # Carregar o contexto do cliente
    cursor.execute('SELECT context FROM client_contexts WHERE client_id = ?', (client_id,))
    row = cursor.fetchone()
    if not row:
        raise Exception("Client context not found")
    
    context_data = row[0]
    cc_filename = os.path.join(datafolder, f'cc_{client_id}.bin')
    with open(cc_filename, 'wb') as f:
        f.write(context_data)
    
    cc, res = DeserializeCryptoContext(cc_filename, BINARY)
    if not res:
        raise Exception("Could not read the crypto context")
    os.remove(cc_filename)
    
    encrypted_balance = cloud_sum(cc, encrypted_values)
    filename = os.path.join(datafolder, f'temp_balance_{client_id}.bin')
    if not SerializeToFile(filename, encrypted_balance, BINARY):
        raise Exception(f'Erro serializando extrato do cliente {client_id}')
    with open(filename, 'rb') as f:
        balance_bytes = f.read()
    os.remove(filename)
    
    balance_str = base64.b64encode(balance_bytes).decode('utf-8')
    return jsonify({'balance': balance_str})

if __name__ == '__main__':
    app.run(port=5001)
