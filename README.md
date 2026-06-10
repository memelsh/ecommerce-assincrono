# Ecossistema de Processamento Assíncrono

Este projeto é uma simulação de um e-commerce simplificado, focando na integração de microsserviços através de comunicação assíncrona (Mensageria) e API RESTful.

## Diagrama de Arquitetura

```mermaid
graph TD
    A[Frontend HTML/JS] -->|1. HTTP POST /pedidos/| B(API Gateway - FastAPI)
    B -->|2. Salva Status Pendente| C[(Banco de Dados SQLite)]
    B -->|3. Publica Mensagem| D{RabbitMQ - Fila}
    D -->|4. Consome Mensagem| E[Worker - Python]
    E -->|5. Atualiza Status Aprovado| C
    A -.->|6. HTTP GET Consulta Status| B
    
