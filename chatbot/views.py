import re
import json
import tempfile
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Chat, UploadedDocument
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .langgraph import chatbot, llm
from langchain_core.messages import HumanMessage


def ask_groq(message):
    """Fallback to original Groq function if needed"""
    try:
        response = llm.invoke([HumanMessage(content=message)])
        return response.content
    except Exception as e:
        return f"Error with Groq API: {str(e)}"


@login_required(login_url='/login')
def chatbot_view(request):
    chats = Chat.objects.filter(user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
                
        if message:
            # Create LangGraph agent
            agent = chatbot.create_agent()
            
            # Prepare messages for the agent
            messages = [{"role": "user", "content": message}]
            
            # Invoke agent
            result = agent.invoke({
                "messages": messages,
                "user_id": str(request.user.id),
                "question": message
            })
            
            response = result["response"]
            
            # Save to database (no file info)
            chat = Chat(
                user=request.user, 
                message=message, 
                response=response, 
                created_at=timezone.now()
            )
            chat.save()

            return JsonResponse({'message': message, 'response': response})
        else:
            return JsonResponse({'error': 'No message provided'}, status=400)

    return render(request, 'chatbot.html', {'chats': chats})


@csrf_exempt
@login_required
def stream_chat(request):
    """Streaming chat endpoint"""
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()

        def generate():
            try:
                agent = chatbot.create_agent()
                result = agent.invoke({
                    "messages": [{"role": "user", "content": message}],
                    "user_id": str(request.user.id),
                    "question": message
                })
                
                response = result["response"]
                
                # Send response in chunks for better streaming
                words = response.split()
                for word in words:
                    yield f"data: {word}\n\n"
                
                # Save to database (no file info)
                chat = Chat(
                    user=request.user,
                    message=message,
                    response=response,
                    created_at=timezone.now()
                )
                chat.save()
                
            except Exception as e:
                yield f"data: Error: {str(e)}\n\n"
        
        response = StreamingHttpResponse(generate(), content_type='text/plain')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@require_POST
@login_required(login_url='/login')
def delete_chat_history(request):
    """Deletes all chat records and documents for the current user"""
    try:
        # Delete chats
        Chat.objects.filter(user=request.user).delete()
        
        # Delete documents
        UploadedDocument.objects.filter(user=request.user).delete()
        
        # Delete vector store (optional - more complex cleanup)
        try:
            user_id = str(request.user.id)
            if user_id in chatbot.vector_stores:
                del chatbot.vector_stores[user_id]
        except:
            pass
            
        return HttpResponse(status=204)
    except Exception as e:
        print(f"Error deleting chat history: {e}")
        return HttpResponse(status=500, reason="Failed to delete chat history")

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('chatbot')
        else:
            error_message = 'Invalid username or password'
            return render(request, 'login.html', {'error_message': error_message})
    else:
        return render(request, 'login.html')


def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # Check if passwords match
        if password1 != password2:
            error_message = 'Passwords do not match'
            return render(request, 'register.html', {'error_message': error_message})

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            error_message = 'Username is already taken'
            return render(request, 'register.html', {'error_message': error_message})

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            error_message = 'Email is already registered'
            return render(request, 'register.html', {'error_message': error_message})

        try:
            # Create the user
            user = User.objects.create_user(username=username, email=email, password=password1)
            user.save()

            # Log the user in after registration
            auth.login(request, user)
            return redirect('chatbot')
        except Exception as e:
            error_message = 'Error creating account: {}'.format(str(e))
            return render(request, 'register.html', {'error_message': error_message})

    return render(request, 'register.html')

def logout(request):
    auth.logout(request)
    return redirect('login')