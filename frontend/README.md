# Frontend - Conversa Estágios

Interface web moderna para chat com IA sobre relatórios de estágio.

## 🚀 Tecnologias

- **React 19** com TypeScript
- **Vite** para build e desenvolvimento
- **Axios** para comunicação com API
- **CSS3** com design responsivo

## 📦 Instalação

```bash
cd frontend
npm install
```

## 🛠️ Desenvolvimento

```bash
npm run dev
```

A aplicação estará disponível em `http://localhost:5173`

## 🏗️ Build

```bash
npm run build
```

## 🎨 Funcionalidades

- ✅ Chat em tempo real sem reload da página
- ✅ Interface responsiva para desktop e mobile
- ✅ Design moderno com gradientes e animações
- ✅ Integração com backend FastAPI
- ✅ Tratamento de erros
- ✅ Indicador de carregamento
- ✅ Mensagens com timestamp
- ✅ Auto-scroll para novas mensagens

## 🔗 API Backend

A interface se conecta com o backend FastAPI em:
- **Endpoint**: `http://localhost:8000/api/v1/chat/`
- **Método**: POST
- **Payload**: `{ "message": "string" }`
- **Response**: `{ "response": "string", "confidence": number }`

## 📱 Como Usar

1. Digite sua pergunta no campo de entrada
2. Clique no botão enviar ou pressione Enter
3. Aguarde a resposta do Estagios IA
4. Continue a conversa naturalmente

### Exemplos de Perguntas

- "Quais são as linguagens mais usadas?"
- "Empresas que usam Python"
- "O que fazem os estagiários na BTG?"
- "Frameworks mais populares"
- "Atividades na CIP"
