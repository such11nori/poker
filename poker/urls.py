from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('create/', views.create_game, name='create_game'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('game/<int:game_id>/join/', views.join_game, name='join_game'),
    path('game/<int:game_id>/leave/', views.leave_game, name='leave_game'),
    path('game/<int:game_id>/end/', views.end_game, name='end_game'),
    path('game/<int:game_id>/add-ai/', views.add_ai_player, name='add_ai_player'),
    path('game/<int:game_id>/start/', views.start_game, name='start_game'),
    path('game/<int:game_id>/action/', views.player_action, name='player_action'),
]
