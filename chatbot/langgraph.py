import os
import time
from typing import List, Dict, Any, Annotated
import uuid
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from django.utils import timezone

load_dotenv()

# Initialize LLM
llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="openai/gpt-oss-120b"
)

# Initialize embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# Define state
class GraphState(TypedDict):
    messages: Annotated[List[Dict], add_messages]
    user_id: str
    question: str
    context: str
    documents: List[Document]
    response: str

class DocumentAwareChatbot:
    def __init__(self):
        self.vector_stores = {}  # user_id -> Chroma vector store
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        self.data_folder = "./data"  # Path to your data folder
        self.documents_loaded = {}  # Track which users have documents loaded
    
    def get_user_vector_store(self, user_id: str) -> Chroma:
        """Get or create vector store for a user"""
        if user_id not in self.vector_stores:
            # Create a unique collection name for each user
            collection_name = f"user_{user_id}"
            self.vector_stores[user_id] = Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                persist_directory=f"./chroma_db/{user_id}"
            )
        return self.vector_stores[user_id]
    
    def load_documents_from_data_folder(self, user_id: str) -> bool:
        """Load all documents from the data folder for a user"""
        try:
            # Check if documents are already loaded for this user
            if user_id in self.documents_loaded and self.documents_loaded[user_id]:
                print(f"Documents already loaded for user {user_id}")
                return True
            
            if not os.path.exists(self.data_folder):
                print(f"Data folder '{self.data_folder}' does not exist. Creating empty folder.")
                os.makedirs(self.data_folder, exist_ok=True)
                return False
            
            all_splits = []
            supported_files = []
            
            # Process all files in the data folder
            for filename in os.listdir(self.data_folder):
                file_path = os.path.join(self.data_folder, filename)
                
                if os.path.isfile(file_path):
                    # Determine loader based on file extension
                    if filename.lower().endswith('.pdf'):
                        loader = PyPDFLoader(file_path)
                        supported_files.append(filename)
                    elif filename.lower().endswith('.docx'):
                        loader = Docx2txtLoader(file_path)
                        supported_files.append(filename)
                    elif filename.lower().endswith('.txt'):
                        loader = TextLoader(file_path)
                        supported_files.append(filename)
                    else:
                        print(f"Skipping unsupported file type: {filename}")
                        continue
                    
                    try:
                        print(f"Processing document: {filename}")
                        documents = loader.load()
                        splits = self.text_splitter.split_documents(documents)
                        
                        # Add metadata
                        for split in splits:
                            split.metadata["user_id"] = user_id
                            split.metadata["file_name"] = filename
                            split.metadata["source"] = "data_folder"
                            split.metadata["loaded_at"] = str(timezone.now())
                        
                        all_splits.extend(splits)
                        print(f"✓ Processed {filename}: {len(splits)} chunks")
                        
                    except Exception as e:
                        print(f"✗ Error processing {filename}: {e}")
                        continue
            
            if all_splits:
                # Store in vector database
                vector_store = self.get_user_vector_store(user_id)
                vector_store.add_documents(all_splits)
                self.documents_loaded[user_id] = True
                print(f"✓ Successfully loaded {len(all_splits)} document chunks from {len(supported_files)} files for user {user_id}")
                return True
            else:
                print("ℹ️ No supported documents found in data folder")
                self.documents_loaded[user_id] = False
                return False
                
        except Exception as e:
            print(f"✗ Error loading documents from data folder: {e}")
            self.documents_loaded[user_id] = False
            return False
    
    def retrieve_relevant_documents(self, question: str, user_id: str, k: int = 3) -> List[Document]:
        """Retrieve relevant documents from user's vector store, auto-load if empty"""
        try:
            vector_store = self.get_user_vector_store(user_id)
            
            # Auto-load documents if vector store is empty or not loaded yet
            if vector_store._collection.count() == 0 or not self.documents_loaded.get(user_id, False):
                print(f"Vector store empty for user {user_id}, loading documents from data folder...")
                success = self.load_documents_from_data_folder(user_id)
                
                if not success:
                    print("No documents available after loading attempt")
                    return []
            
            if vector_store._collection.count() == 0:
                print("Vector store still empty after loading attempt")
                return []

            print(f"Searching for relevant documents for question: '{question}'")
            retriever = vector_store.as_retriever(search_kwargs={"k": k})
            
            # Try different method names for compatibility
            relevant_docs = []
            try:
                # Method 1: Newest LangChain version
                relevant_docs = retriever.invoke(question)
            except AttributeError:
                try:
                    # Method 2: Older version
                    relevant_docs = retriever.get_relevant_documents(question)
                except AttributeError:
                    try:
                        # Method 3: Direct similarity search
                        relevant_docs = vector_store.similarity_search(question, k=k)
                    except Exception as e:
                        print(f"All retrieval methods failed: {e}")
                        return []
            
            print(f"Found {len(relevant_docs)} relevant document chunks")
            
            return relevant_docs
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return []  

    def get_loaded_documents_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about loaded documents for a user"""
        try:
            vector_store = self.get_user_vector_store(user_id)
            count = vector_store._collection.count()
            
            # Get unique document names from metadata
            if count > 0:
                results = vector_store._collection.get()
                if results and 'metadatas' in results:
                    unique_files = set(metadata.get('file_name', 'Unknown') for metadata in results['metadatas'])
                    return {
                        'total_chunks': count,
                        'loaded_files': list(unique_files),
                        'documents_loaded': self.documents_loaded.get(user_id, False)
                    }
            
            return {
                'total_chunks': 0,
                'loaded_files': [],
                'documents_loaded': self.documents_loaded.get(user_id, False)
            }
        except Exception as e:
            print(f"Error getting document info: {e}")
            return {'total_chunks': 0, 'loaded_files': [], 'documents_loaded': False}
    
    def create_agent(self):
        """Create LangGraph agent with memory and retrieval"""
        
        def should_retrieve(state: GraphState) -> str:
            """Decision node: whether to retrieve documents"""
            # Always retrieve if user has documents
            vector_store = chatbot.get_user_vector_store(state["user_id"])
            if vector_store._collection.count() > 0:
                return "retrieve"
            return "generate_response"
        
        def retrieve_documents(state: GraphState) -> GraphState:
            """Retrieve relevant documents"""
            question = state["messages"][-1].content
            relevant_docs = chatbot.retrieve_relevant_documents(question, state["user_id"])
            
            context = "\n\n".join([doc.page_content for doc in relevant_docs])
            return {**state, "context": context, "documents": relevant_docs}
        
        def generate_response(state: GraphState) -> GraphState:
            """Generate response with context"""
            messages = state["messages"]
            context = state.get("context", "")
            user_message = messages[-1].content if messages else ""
            
            # Check if this is a document-only query
            is_document_only = "please analyze the uploaded documents" in user_message.lower() and "provide a summary or key insights" in user_message.lower()
            
            if context:
                if is_document_only:
                    # Special system message for document analysis
                    system_message = f"""You are a helpful assistant analyzing documents for the user.

        The user has uploaded documents and wants you to analyze them. 

        Relevant document context:
        {context}

        Please provide a comprehensive analysis of the uploaded documents. Focus on the content naturally without mentioning that you're accessing documents."""
                else:
                    # Natural, context-aware response without revealing mechanics
                    system_message = f"""You are a helpful AI assistant. You have to answer the user's questions naturally. Don't mention that you're accessing documents or have special capabilities - just provide helpful answers based on the available information. If information not available, answer it by your knowledge.

        Available information:
        {context}

        Answer naturally as if you're having a normal conversation."""
                
                # Convert messages to the format LLM expects
                messages_with_context = [{"role": "system", "content": system_message}]
                for msg in messages:
                    messages_with_context.append({"role": "user", "content": msg.content})
            else:
                # No context - regular conversation
                messages_with_context = [{"role": "user", "content": msg.content} for msg in messages]
                
            # Generate response
            response = llm.invoke(messages_with_context)
            
            return {**state, "response": response.content}
        
        # Build graph
        workflow = StateGraph(GraphState)
        
        # Define nodes
        workflow.add_node("retrieve", retrieve_documents)
        workflow.add_node("generate_response", generate_response)
        
        # Define entry point
        workflow.set_entry_point("retrieve")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "retrieve",
            should_retrieve,
            {
                "retrieve": "generate_response",
                "generate_response": "generate_response",
            }
        )
        
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()

# Global instance
chatbot = DocumentAwareChatbot()