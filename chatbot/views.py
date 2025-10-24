import re
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Chat
from django.utils import timezone

import os
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
        message = request.POST.get('message')
        
        if message:
            # Get cleaned response from Groq
            response = ask_groq(message)

            # Save the chat in the database
            chat = Chat(user=request.user, message=message, response=response, created_at=timezone.now())
            chat.save()

            # Return response as JSON
            return JsonResponse({'message': message, 'response': response})
        else:
            return JsonResponse({'error': 'No message provided'}, status=400)

    return render(request, 'chatbot.html', {'chats': chats})

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
