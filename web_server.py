from flask import Flask, render_template_string, request, jsonify
import requests
import os

app = Flask(__name__)

AGENT_URL = os.environ.get('AGENT_URL', 'https://endpoint-ab8a7d38-9dbc-4490-aec5-7e5b7c405ecc.agentbase-runtime.aiplatform.vngcloud.vn/invocations')

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Clawsome Demo Agent</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        h1 { color: #333; margin-bottom: 10px; font-size: 28px; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 14px; }
        .input-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #555; font-weight: 500; }
        textarea {
            width: 100%; padding: 15px; border: 2px solid #e0e0e0;
            border-radius: 10px; font-size: 16px; resize: vertical;
            min-height: 100px; transition: border-color 0.3s;
        }
        textarea:focus { outline: none; border-color: #667eea; }
        button {
            width: 100%; padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; border-radius: 10px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover { transform: translateY(-2px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .response {
            margin-top: 25px; padding: 20px; background: #f8f9fa;
            border-radius: 10px; border-left: 4px solid #667eea; display: none;
        }
        .response.show { display: block; }
        .response h3 { color: #333; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }
        .response pre {
            background: #2d2d2d; color: #f8f8f2; padding: 15px;
            border-radius: 8px; overflow-x: auto; font-size: 13px; line-height: 1.5;
        }
        .loading { text-align: center; color: #667eea; font-weight: 500; display: none; }
        .loading.show { display: block; }
        .error { border-left-color: #e74c3c !important; background: #fdf2f2 !important; }
        .info { font-size: 12px; color: #888; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Clawsome Demo Agent</h1>
        <p class="subtitle">Send a message to your AgentBase agent</p>
        
        <div class="input-group">
            <label for="message">Your Message</label>
            <textarea id="message" placeholder="Type your message here...">Hello, agent!</textarea>
        </div>
        
        <button id="sendBtn" onclick="sendMessage()">🚀 Send Message</button>
        
        <div class="loading" id="loading">⏳ Sending message...</div>
        
        <div class="response" id="response">
            <h3>Response</h3>
            <pre id="responseContent"></pre>
        </div>
        
        <p class="info">Powered by GreenNode AgentBase</p>
    </div>

    <script>
        async function sendMessage() {
            const messageInput = document.getElementById('message');
            const sendBtn = document.getElementById('sendBtn');
            const loading = document.getElementById('loading');
            const response = document.getElementById('response');
            const responseContent = document.getElementById('responseContent');
            
            const message = messageInput.value.trim();
            if (!message) { alert('Please enter a message'); return; }
            
            sendBtn.disabled = true;
            loading.classList.add('show');
            response.classList.remove('show', 'error');
            
            try {
                const res = await fetch('/api/invocations', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message })
                });
                
                const data = await res.json();
                
                if (data.error) {
                    responseContent.textContent = 'Error: ' + data.error;
                    response.classList.add('show', 'error');
                } else {
                    responseContent.textContent = JSON.stringify(data, null, 2);
                    response.classList.add('show');
                }
            } catch (error) {
                responseContent.textContent = 'Error: ' + error.message;
                response.classList.add('show', 'error');
            } finally {
                sendBtn.disabled = false;
                loading.classList.remove('show');
            }
        }
        
        document.getElementById('message').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) sendMessage();
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/invocations', methods=['POST'])
def invocations():
    try:
        data = request.get_json()
        message = data.get('message', 'Hello')
        
        response = requests.post(
            AGENT_URL,
            json={'message': message},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': f'Agent error: {response.status_code}'}), response.status_code
            
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)