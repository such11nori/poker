"""
リファクタリングされたビュー
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from .models import Game, Player, GameRound, PlayerAction
from .services.game_service import GameService
from .services.betting_service import BettingService
from .services.ai_service import AIService


def home(request):
    """ホームページ"""
    games = Game.objects.filter(status__in=['waiting', 'in_progress'])
    
    # ユーザーが参加中のゲームのIDリストを取得
    user_games = []
    if request.user.is_authenticated:
        user_games = Player.objects.filter(user=request.user, game__in=games).values_list('game_id', flat=True)
    
    return render(request, 'poker/home.html', {
        'games': games,
        'user_games': user_games
    })


def user_login(request):
    """ユーザーログイン"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'ようこそ、{user.username}さん！')
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        else:
            messages.error(request, 'ユーザー名またはパスワードが正しくありません。')
    
    return render(request, 'poker/login.html')


def user_register(request):
    """ユーザー登録"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            messages.error(request, 'パスワードが一致しません。')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'このユーザー名は既に使用されています。')
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            messages.success(request, f'ユーザー登録完了！ようこそ、{user.username}さん！')
            return redirect('home')
    
    return render(request, 'poker/register.html')


def user_logout(request):
    """ユーザーログアウト"""
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('home')


@login_required
def create_game(request):
    """ゲーム作成"""
    if request.method == 'POST':
        name = request.POST.get('game_name')  # テンプレートのname属性と一致させる
        max_players = int(request.POST.get('max_players', 6))
        small_blind = int(request.POST.get('small_blind', 10))
        big_blind = int(request.POST.get('big_blind', 20))
        
        # デバッグ用ログ
        print(f"Debug - Received data: name='{name}', max_players={max_players}, small_blind={small_blind}, big_blind={big_blind}")
        
        try:
            game = GameService.create_game(
                name=name,
                max_players=max_players,
                small_blind=small_blind,
                big_blind=big_blind,
                created_by=request.user
            )
            messages.success(request, f'ゲーム「{name}」を作成しました。')
            return redirect('game_detail', game_id=game.id)
        except ValueError as e:
            messages.error(request, f'ゲーム作成に失敗しました: {str(e)}')
        except Exception as e:
            messages.error(request, f'ゲーム作成に失敗しました: {str(e)}')
            print(f"Debug - Exception details: {type(e).__name__}: {str(e)}")
    
    return render(request, 'poker/create_game.html')


@login_required
def join_game(request, game_id):
    """ゲーム参加"""
    game = get_object_or_404(Game, id=game_id)
    
    try:
        GameService.join_game(game, request.user)
        messages.success(request, f'ゲーム「{game.name}」に参加しました。')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('game_detail', game_id=game.id)


@login_required
def add_ai_player(request, game_id):
    """AIプレイヤーを追加"""
    game = get_object_or_404(Game, id=game_id)
    
    try:
        GameService.add_ai_player(game)
        messages.success(request, 'AIプレイヤーを追加しました。')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('game_detail', game_id=game.id)


def game_detail(request, game_id):
    """ゲーム詳細ページ"""
    game = get_object_or_404(Game, id=game_id)
    player = Player.objects.filter(user=request.user, game=game).first()
    
    if not player:
        return redirect('join_game', game_id=game.id)
    
    players = Player.objects.filter(game=game).order_by('position')
    current_round = GameRound.objects.filter(game=game).last()
    
    # コール金額を計算
    call_amount = 0
    if current_round and player:
        call_amount = BettingService.get_call_amount(player, current_round)
    
    # 現在のラウンドのアクション履歴を取得
    recent_actions = []
    if current_round:
        recent_actions = PlayerAction.objects.filter(
            game_round=current_round
        ).order_by('-timestamp')[:10]  # 最新10件
    
    context = {
        'game': game,
        'player': player,
        'players': players,
        'current_round': current_round,
        'call_amount': call_amount,
        'recent_actions': recent_actions,
    }
    
    return render(request, 'poker/game_detail.html', context)


@login_required
def start_game(request, game_id):
    """ゲームを開始"""
    game = get_object_or_404(Game, id=game_id)
    
    try:
        GameService.start_game(game)
        messages.success(request, 'ゲームを開始しました。')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('game_detail', game_id=game.id)


@login_required
@csrf_exempt
def player_action(request, game_id):
    """プレイヤーのアクションを処理"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    game = get_object_or_404(Game, id=game_id)
    player = get_object_or_404(Player, user=request.user, game=game)
    
    data = json.loads(request.body)
    action = data.get('action')
    amount = data.get('amount', 0)
    
    current_round = GameRound.objects.filter(game=game).last()
    
    if not current_round:
        return JsonResponse({'error': 'No active round'}, status=400)
    
    # プレイヤーがアクティブかチェック
    if not player.is_active or player.is_folded:
        return JsonResponse({'error': 'Player is not active'}, status=400)
    
    # 現在のプレイヤーの番かチェック
    if player.position != current_round.current_player_position:
        return JsonResponse({'error': 'Not your turn'}, status=400)
    
    try:
        # アクションを処理
        print(f"[DEBUG] プレイヤー {player.user.username} (位置: {player.position}) がアクション: {action}")
        BettingService.process_player_action(player, game, current_round, action, amount)
        
        # アクション後すぐにアクティブプレイヤーをチェック
        current_round.refresh_from_db()
        active_players = current_round.get_active_players()
        print(f"[DEBUG] アクティブプレイヤー数: {active_players.count()}")
        
        if active_players.count() <= 1:
            # アクティブプレイヤーが1人以下になった場合は即座にショーダウンへ
            print(f"[DEBUG] アクティブプレイヤーが1人以下になったため、ショーダウンに移行")
            GameService.advance_game_phase(game, current_round)
            return JsonResponse({'success': True})
        
        # 次のプレイヤーを設定
        from .utils.position_manager import PositionManager
        next_position = PositionManager.get_next_player_position(current_round)
        print(f"[DEBUG] 次のプレイヤー位置: {next_position}")
        if next_position is not None:
            current_round.current_player_position = next_position
            current_round.save()
        
        # AIプレイヤーの行動を処理（ベッティング完了チェック前に）
        AIService.process_ai_actions(game, current_round)
        
        # ベッティングラウンドが完了したかチェック（AIの行動後に）
        current_round.refresh_from_db()  # データベースから最新状態を再取得
        if BettingService.is_betting_round_complete(game, current_round):
            print(f"[DEBUG] ベッティングラウンド完了、次のフェーズに移行")
            GameService.advance_game_phase(game, current_round)
        
        return JsonResponse({'success': True})
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
def leave_game(request, game_id):
    """ゲームから退出"""
    game = get_object_or_404(Game, id=game_id)
    
    try:
        GameService.leave_game(game, request.user)
        messages.success(request, 'ゲームから退出しました。')
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('home')


@login_required
def end_game(request, game_id):
    """ゲーム強制終了"""
    game = get_object_or_404(Game, id=game_id)
    
    if game.created_by != request.user:
        messages.error(request, 'ゲームを終了する権限がありません。')
        return redirect('game_detail', game_id=game.id)
    
    # 作成者にペナルティを課す
    player = Player.objects.filter(user=request.user, game=game).first()
    if player:
        penalty = min(player.chips // 3, 150)
        player.chips -= penalty
        game.pot += penalty
        player.save()
    
    # ゲームを終了
    game.status = 'finished'
    game.save()
    
    messages.success(request, 'ゲームを終了しました。')
    return redirect('home')
