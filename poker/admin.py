from django.contrib import admin
from .models import Game, Player, GameRound, PlayerAction

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'max_players', 'created_at', 'pot']
    list_filter = ['status', 'created_at']
    search_fields = ['name']

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['user', 'game', 'chips', 'position', 'is_active']
    list_filter = ['is_active', 'game']
    search_fields = ['user__username', 'game__name']

@admin.register(GameRound)
class GameRoundAdmin(admin.ModelAdmin):
    list_display = ['game', 'round_number', 'phase', 'current_player_position', 'highest_bet']
    list_filter = ['phase', 'game']

@admin.register(PlayerAction)
class PlayerActionAdmin(admin.ModelAdmin):
    list_display = ['player', 'action', 'amount', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['player__user__username']
