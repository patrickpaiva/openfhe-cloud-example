
# Homomorphic Encryption APIs

Este repositório contém dois arquivos .py que implementam APIs para trabalhar com criptografia homomórfica usando a biblioteca OpenFHE. As APIs são divididas em uma API local e uma API na nuvem, cada uma com responsabilidades específicas para garantir a segurança e a privacidade dos dados. Este é apenas um exemplo de implementação para estudo de uso da biblioteca OpenFHE com o esquema CKKS.

## Arquivos

- `api_local.py`: Este arquivo contém a implementação da API local.
- `api_nuvem.py`: Este arquivo contém a implementação da API na nuvem.

## Configuração Inicial

Antes de executar as APIs, é necessário instalar as dependências. Certifique-se de ter o Python e o pip instalados no seu sistema.

A biblioteca [OpenFHE](https://www.openfhe.org/) deve ser instalada conforme orientado no repositório [openfhe-python](https://github.com/openfheorg/openfhe-python).

```bash
pip install flask requests
```

## API Local

### Descrição

A API local é responsável por criptografar os dados antes de enviá-los para a nuvem e descriptografar os dados recebidos da nuvem. Ela também gerencia os contextos e chaves de criptografia.

### Endpoints

- **`/add_transaction`**: Adiciona uma nova transação para um cliente.
  - **Método**: POST
  - **Parâmetros**:
    - `client_id` (string): Identificador único do cliente.
    - `data` (string): Data da transação.
    - `valor` (number): Valor da transação.
- **`/get_balance`**: Obtém o saldo atual de um cliente.
  - **Método**: GET
  - **Parâmetros**:
    - `client_id` (string): O ID do cliente.

### Executando a API Local

```bash
python api_local.py
```

A API será executada na porta 5000.

## API na Nuvem

### Descrição

A API na nuvem é responsável por armazenar e processar os dados criptografados. Ela armazena as transações criptografadas e realiza operações aritméticas homomórficas nos dados.

### Endpoints

- **`/add_transaction`**: Adiciona uma nova transação para um cliente.
  - **Método**: POST
  - **Parâmetros**:
    - `client_id` (string): Identificador único do cliente.
    - `data` (string): Data da transação.
    - `valor` (file): Valor da transação criptografado.
    - `context` (file): CipherContext serializado.
- **`/get_balance`**: Obtém o saldo atual de um cliente.
  - **Método**: GET
  - **Parâmetros**:
    - `client_id` (string): O ID do cliente.

### Executando a API na Nuvem

```bash
python api_nuvem.py
```

A API será executada na porta 5001.

## Exemplo de Uso

### Adicionando uma Transação

```bash
curl -X POST http://127.0.0.1:5000/add_transaction \
    -H "Content-Type: application/json" \
    -d '{"client_id": "cliente1", "data": "2024-07-11", "valor": 100.50}'
```

### Obtendo o Saldo

```bash
curl -X GET "http://127.0.0.1:5000/get_balance?client_id=cliente1"
```

## Considerações Finais

Este projeto demonstra o uso de criptografia homomórfica para garantir a privacidade dos dados em um ambiente de computação em nuvem. A API local cuida da criptografia e decriptação, enquanto a API na nuvem armazena e processa os dados criptografados.

Para mais informações sobre a biblioteca OpenFHE, visite [OpenFHE](https://www.openfhe.org/).

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
