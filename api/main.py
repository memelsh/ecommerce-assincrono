from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import pika
import json

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./pedidos.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PedidoDB(Base):
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    produto = Column(String, index=True)
    status = Column(String, default="Pendente")

# Cria o arquivo do banco de dados na pasta
Base.metadata.create_all(bind=engine)

# ==========================================
# 2. INICIANDO A API E CONFIGURANDO CORS
# ==========================================
app = FastAPI(title="API E-commerce Assíncrono")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite o Frontend conversar com a API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. REGRAS DE SEGURANÇA E DADOS
# ==========================================
class PedidoCreate(BaseModel):
    produto: str

def verificar_token(x_token: str = Header(default=None)):
    if x_token != "senha_secreta_123":
        raise HTTPException(status_code=401, detail="Token inválido ou ausente! Acesso Negado.")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 4. ROTAS DA API (Endpoints)
# ==========================================

# Rota para Criar o Pedido (Devolve Status 202 como o professor pediu)
@app.post("/pedidos/", status_code=202)
def criar_pedido(pedido: PedidoCreate, db: Session = Depends(get_db), token: None = Depends(verificar_token)):
    # Passo A: Salva no banco como Pendente
    novo_pedido = PedidoDB(produto=pedido.produto, status="Pendente")
    db.add(novo_pedido)
    db.commit()
    db.refresh(novo_pedido)

    # Passo B: Manda a mensagem para o RabbitMQ
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='fila_pedidos')
        
        mensagem = {"pedido_id": novo_pedido.id, "produto": novo_pedido.produto}
        channel.basic_publish(exchange='', routing_key='fila_pedidos', body=json.dumps(mensagem))
        connection.close()
    except Exception as e:
        print("Erro ao conectar no RabbitMQ:", e)

    return {"mensagem": "Pedido aceito e em processamento", "pedido_id": novo_pedido.id, "status": novo_pedido.status}

# Rota para Consultar o Pedido (Para a tela do Frontend atualizar sozinha)
@app.get("/pedidos/{pedido_id}")
def consultar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = db.query(PedidoDB).filter(PedidoDB.id == pedido_id).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return {"pedido_id": pedido.id, "produto": pedido.produto, "status": pedido.status}
      