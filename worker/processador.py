import pika
import json
import time
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Conecta no MESMO banco de dados da API
SQLALCHEMY_DATABASE_URL = "sqlite:///./pedidos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PedidoDB(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    produto = Column(String, index=True)
    status = Column(String, default="Pendente")

# 2. A função que faz o "trabalho pesado"
def processar_pedido(ch, method, properties, body):
    mensagem = json.loads(body)
    pedido_id = mensagem['pedido_id']
    produto = mensagem['produto']
    
    print(f"\n🔄 [Worker] Recebeu pedido #{pedido_id} ({produto}). Analisando cartão de crédito...")
    
    # Simula a demora de uma integração real (5 segundos)
    time.sleep(5)
    
    # Atualiza o status no banco de dados
    db = SessionLocal()
    pedido = db.query(PedidoDB).filter(PedidoDB.id == pedido_id).first()
    if pedido:
        pedido.status = "Aprovado"
        db.commit()
        print(f"✅ [Worker] Pagamento aprovado! Pedido #{pedido_id} atualizado com sucesso.")
    db.close()
    
    # Avisa o RabbitMQ que o trabalho terminou e ele pode apagar a mensagem da fila
    ch.basic_ack(delivery_tag=method.delivery_tag)

# 3. Conexão com o RabbitMQ para ficar escutando a fila
print("⏳ [Worker] Iniciando... Aguardando novos pedidos na fila.")
try:
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    # Garante que a fila existe antes de tentar ler
    channel.queue_declare(queue='fila_pedidos')
    
    # Fica escutando infinitamente
    channel.basic_consume(queue='fila_pedidos', on_message_callback=processar_pedido)
    channel.start_consuming()
except Exception as e:
    print("Erro ao conectar no RabbitMQ:", e)
    