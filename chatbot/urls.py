from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
    path('logout', views.logout, name='logout'),
    path('delete_chat/', views.delete_chat_history, name='delete_chat_history'), 
    path('stream_chat/', views.stream_chat, name='stream_chat'),
]
