from flask import Flask, request, jsonify
from azure.identity import ClientSecretCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MessageRole
import os

app = Flask(__name__)

# Configurações do Azure (via variáveis de ambiente do Render)
ENDPOINT = "https://fabrica-mkt-resource.services.ai.azure.com/api/projects/fabrica-mkt"
AGENT_NAME = "LEO-Redes-Sociais"

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

# Cache do cliente
_project_client = None

def get_project_client():
    global _project_client
    if _project_client is None:
        credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
        _project_client = AIProjectClient(endpoint=ENDPOINT, credential=credential)
    return _project_client

@app.route('/')
def home():
    return jsonify({'status': 'Azure AI Agent Backend Running', 'version': '1.0'})

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        thread_id = data.get('thread_id')
        
        if not user_message:
            return jsonify({'error': 'Mensagem vazia'}), 400
        
        client = get_project_client()
        
        # Buscar agente
        agent = client.agents.get_agent(agent_name=AGENT_NAME)
        
        # Criar ou usar thread
        if not thread_id:
            thread = client.agents.create_thread()
            thread_id = thread.id
        
        # Adicionar mensagem do usuário
        client.agents.create_message(
            thread_id=thread_id,
            role=MessageRole.USER,
            content=user_message
        )
        
        # Executar agente e aguardar resposta
        run = client.agents.create_and_process_run(
            thread_id=thread_id,
            assistant_id=agent.id
        )
        
        # Buscar mensagens
        messages = client.agents.list_messages(thread_id=thread_id)
        
        # Extrair última resposta do assistente
        assistant_message = ""
        for msg in messages.data:
            if msg.role == MessageRole.ASSISTANT:
                for content in msg.content:
                    if hasattr(content, 'text'):
                        assistant_message = content.text.value
                        break
                break
        
        return jsonify({
            'success': True,
            'message': assistant_message,
            'thread_id': thread_id
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'agent': AGENT_NAME})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
