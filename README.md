# DocuMind - AI Document-Aware Chatbot

DocuMind is a Django-based web application that provides an intelligent chatbot capable of understanding and analyzing your documents. Built with LangGraph and Groq's LLM, it can answer questions based on uploaded documents while maintaining conversation memory.

## 🚀 Features

- **Document Intelligence**: Upload PDF, DOCX, and TXT files for the AI to analyze
- **Smart Retrieval**: Automatically finds relevant information from your documents
- **Streaming Responses**: Real-time chat experience with markdown rendering
- **User Authentication**: Secure login/registration system
- **Persistent Memory**: Maintains chat history and document context
- **Modern UI**: Clean, responsive interface with typing indicators

## 🛠️ Tech Stack

- **Backend**: Django, LangGraph, LangChain
- **AI/ML**: Groq API, HuggingFace Embeddings
- **Vector Database**: ChromaDB
- **Frontend**: Bootstrap, JavaScript, Markdown
- **File Processing**: PyPDF, Docx2txt

## 📋 Prerequisites

- Python 3.8+
- Groq API Key
- Django 4.0+

### Demo
![](https://github.com/Anas436/Chatbot/blob/main/chatbot.png)
<br>
<hr>
<br>

![](https://github.com/Anas436/Chatbot/blob/main/Anas.png)
<br>
<hr>
<br>

![](https://github.com/Anas436/Chatbot/blob/main/signup.png)
<br>
<hr>
<br>

![](https://github.com/Anas436/Chatbot/blob/main/login.png)

## ⚡ Quick Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Anas436/Chatbot.git
cd Chatbot
```
### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Environment Configuration
Create a __.env__ file in the project root:
```bash
GROQ_API_KEY=your_groq_api_key_here
```
### 5. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
```
### 6. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```
### 📁 Project Structure

### 🔧 Configuration

## Document Storage
Create a __data__ folder in your project root for document uploads:
```bash
mkdir data
```
The system automatically processes:

* PDF files (.pdf)

* Word documents (.docx)

* Text files (.txt)

## Vector Database
__ChromaDB__ is used for document embeddings with automatic user isolation.

### 🔌 API Usage
## Chat Endpoints
# 1. Regular Chat (JSON Response)
```bash
POST /chat/
Content-Type: application/x-www-form-urlencoded

message=What are the key points in my documents?
```
# Response:
```bash
{
    "message": "What are the key points in my documents?",
    "response": "Based on your uploaded documents, the key points are..."
}
```
# 2. Streaming Chat (Server-Sent Events)
```bash
POST /stream_chat/
Content-Type: application/x-www-form-urlencoded

message=Explain the main concepts
```
__Response:__ Server-sent events with real-time token streaming.

# 3. Delete Chat History
```bash
POST /delete_chat/
```
__Response:__ HTTP 204 No Content on success

### Common Issues
__1. Documents not loading:__ Ensure files are in data/ folder with correct extensions
__2. Groq API errors:__ Verify API key in .env file
__3. Vector store issues:__ Check write permissions for chroma_db/ directory
__4. Refresh browser:__ Solve chat container response inconsistency

### 🤝 Contributing
1. Fork the repository

2. Create a feature branch

3. Commit your changes

4. Push to the branch

5. Create a Pull Request

## Reference
- Groq is Fast AI Inference [here](https://groq.com/)
- Clinical AI Advisor using RAG, LLM, and Streamlit [here](https://github.com/Saifulislamsayem19/Clinical-AI-Advisor-using-RAG-and-LLM)
- ChatBot using Streamlit and OpenAI [here](https://github.com/fshnkarimi/Chat-Bot-using-Streamlit-and-OpenAI/tree/main)
