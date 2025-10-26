import re
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Chat
from django.utils import timezone

import os
import json
from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq
load_dotenv()


# Retrieve the API key from the .env file
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("API key for Groq is missing. Please set the GROQ_API_KEY in the .env file.")

client = Groq(api_key=groq_api_key)


# Define the function to query the Groq API and clean the response
def ask_groq(message):
    try:
        # Make API call with the correct setup
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",  # Adjust model name if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message}
            ],
            temperature=1.0,
            max_tokens=1024,
            top_p=1.0,
            stream=False
        )

        # Extract the response content
        answer = response.choices[0].message.content.strip()

        # Clean unwanted characters (e.g., extra spaces, newlines, etc.)
        cleaned_answer = clean_text(answer)

        # Return the cleaned response
        return cleaned_answer

    except Exception as e:
        return f"Error with Groq API: {str(e)}"


def clean_text(text):
    """
    Function to clean the response by removing unwanted characters.
    """
    # Remove unwanted characters like extra spaces, newlines, and non-printable characters
    cleaned_text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    cleaned_text = re.sub(r'[^\x00-\x7F]+', '', cleaned_text)  # Remove non-ASCII characters
    cleaned_text = cleaned_text.strip()  # Remove leading/trailing spaces
    return cleaned_text

@login_required(login_url='/login')  # Ensure only logged-in users can access this view
def chatbot(request):
    chats = Chat.objects.filter(user=request.user)

    if request.method == 'POST':
        message = request.POST.get('message', '').strip() # Get message, default to empty string
        # Get file_names list, default to empty list if not present or decoding fails
        try:
            file_names_json = request.POST.get('file_names', '[]')
            file_names = json.loads(file_names_json)
        except json.JSONDecodeError:
            file_names = []

        # Check if there is a message OR files
        if message or file_names:
            
            # 1. CONSTRUCT PROMPT FOR GROQ
            groq_prompt = message
            
            if file_names:
                files_info = ", ".join(file_names)
                # This simulates that the AI is processing the files
                file_context = f"You are referencing the following documents: {files_info}. "
                
                # Prepend the file context to the user's message
                if message:
                    groq_prompt = file_context + f"Based on the files, here is my question: {message}"
                else:
                    groq_prompt = file_context + "Please acknowledge the files and ask for a question."

            # 2. Get cleaned response from Groq
            response = ask_groq(groq_prompt)

            # 3. CONSTRUCT MESSAGE TO SAVE IN DATABASE
            # We save the original message + a note about the files for accurate history display
            db_message = message
            if file_names:
                files_info = f"[Attached: {', '.join(file_names)}]"
                # Save the files info either at the start or end of the message
                db_message = f"{message} {files_info}".strip()


            # 4. Save the chat in the database
            chat = Chat(user=request.user, message=db_message, response=response, created_at=timezone.now())
            chat.save()

            # 5. Return response as JSON (The JS will display the original message from its side)
            return JsonResponse({'message': message, 'response': response})
        else:
            # Error if neither message nor files were provided
            return JsonResponse({'error': 'No message or file provided'}, status=400)

    return render(request, 'chatbot.html', {'chats': chats})

@require_POST
@login_required(login_url='/login')
def delete_chat_history(request):
    """
    Deletes all chat records associated with the current authenticated user.
    """
    try:
        # Delete all chat objects belonging to the current user
        Chat.objects.filter(user=request.user).delete()
        
        # Return a success response
        return HttpResponse(status=204) # 204 No Content is standard for successful deletion
    except Exception as e:
        print(f"Error deleting chat history for user {request.user.username}: {e}")
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
