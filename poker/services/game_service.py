"""
ゲーム管理サービス
"""
from django.contrib.auth.models import User
from ..models import Game, Player, GameRound
from ..services.card_service import CardService
from ..services.betting_service import BettingService
from ..services.ai_service import AIService
from ..utils.position_manager import PositionManager


class GameService:
    """ゲーム関連の操作を管理するサービス"""
    
    @staticmethod
    def create_game(name, max_players, small_blind, big_blind, created_by):
        """新しいゲームを作成"""
        # デバッグ用ログ
        print(f"GameService.create_game called with: name='{name}' (type: {type(name)}), max_players={max_players}, small_blind={small_blind}, big_blind={big_blind}")
        
        # バリデーション
        if name is None:
            raise ValueError('ゲーム名が指定されていません (None)')
        if not isinstance(name, str):
            raise ValueError(f'ゲーム名は文字列である必要があります (received: {type(name)})')
        if name.strip() == '':
            raise ValueError('ゲーム名は必須です (空文字)')
        if max_players < 2 or max_players > 8:
            raise ValueError('プレイヤー数は2-8人である必要があります')
        if small_blind <= 0 or big_blind <= 0:
            raise ValueError('ブラインドは正の値である必要があります')
        if big_blind <= small_blind:
            raise ValueError('ビッグブラインドはスモールブラインドより大きい必要があります')
        
        game = Game.objects.create(
            name=name.strip(),
            max_players=max_players,
            small_blind=small_blind,
            big_blind=big_blind,
            created_by=created_by,
            status='waiting'
        )
        
        # 作成者をランダムポジションに配置
        position = PositionManager.get_random_available_position(game)
        if position is not None:
            Player.objects.create(
                user=created_by,
                game=game,
                position=position,
                chips=1000,  # 初期チップ
                is_active=True
            )
            
            # ディーラーポジションを設定
            game.dealer_position = position
            game.save()
        
        return game
    
    @staticmethod
    def join_game(game, user):
        """ゲームに参加"""
        if game.status != 'waiting':
            raise ValueError('ゲームは既に開始されています')
        
        # 既に参加済みかチェック
        if Player.objects.filter(user=user, game=game).exists():
            raise ValueError('既にこのゲームに参加しています')
        
        # 定員チェック
        current_players = Player.objects.filter(game=game).count()
        if current_players >= game.max_players:
            raise ValueError('ゲームは満員です')
        
        # ランダムポジションを取得
        position = PositionManager.get_random_available_position(game)
        if position is None:
            raise ValueError('利用可能なポジションがありません')
        
        player = Player.objects.create(
            user=user,
            game=game,
            position=position,
            chips=1000,
            is_active=True
        )
        
        return player
    
    @staticmethod
    def add_ai_player(game):
        """AIプレイヤーを追加"""
        if game.status != 'waiting':
            raise ValueError('ゲームは既に開始されています')
        
        # 定員チェック
        current_players = Player.objects.filter(game=game).count()
        if current_players >= game.max_players:
            raise ValueError('ゲームは満員です')
        
        # ランダムポジションを取得
        position = PositionManager.get_random_available_position(game)
        if position is None:
            raise ValueError('利用可能なポジションがありません')
        
        # AIユーザーを作成（存在しない場合）
        ai_count = Player.objects.filter(game=game, is_ai=True).count()
        ai_username = f"AI_Player_{ai_count + 1}"
        
        ai_user, created = User.objects.get_or_create(
            username=ai_username,
            defaults={
                'first_name': f'AI Player {ai_count + 1}',
                'is_active': False  # AIユーザーはログイン不可
            }
        )
        
        player = Player.objects.create(
            user=ai_user,
            game=game,
            position=position,
            chips=1000,
            is_active=True,
            is_ai=True
        )
        
        return player
    
    @staticmethod
    def start_game(game):
        """ゲームを開始"""
        if game.status != 'waiting':
            raise ValueError('ゲームは既に開始されています')
        
        player_count = Player.objects.filter(game=game).count()
        if player_count < 2:
            raise ValueError('ゲームを開始するには最低2人のプレイヤーが必要です')
        
        # ゲームステータスを更新
        game.status = 'in_progress'
        game.current_round = 1
        game.save()
        
        # 最初のラウンドを開始
        GameService.start_new_round(game)
        
        return game
    
    @staticmethod
    def start_new_round(game):
        """新しいラウンドを開始"""
        # 既存のラウンドを終了
        existing_rounds = GameRound.objects.filter(game=game)
        for round_obj in existing_rounds:
            if round_obj.phase != 'finished':
                round_obj.phase = 'finished'
                round_obj.save()
        
        # 新しいラウンドを作成
        game_round = GameRound.objects.create(
            game=game,
            round_number=game.current_round,
            phase='preflop'
        )
        
        # プレイヤーをリセット
        GameService._reset_players_for_new_round(game)
        
        # カードを配る（ブラインドも適用される）
        CardService.deal_cards_to_players(game, game_round)
        BettingService.apply_blinds(game, game_round)
        
        # プリフロップの開始プレイヤーを設定
        from ..utils.position_manager import PositionManager
        first_player_position = PositionManager.get_preflop_first_player_position(game_round)
        if first_player_position is not None:
            game_round.current_player_position = first_player_position
            game_round.save()
        
        # AIプレイヤーの行動を処理
        AIService.process_ai_actions(game, game_round)
        
        return game_round
    
    @staticmethod
    def _reset_players_for_new_round(game):
        """新しいラウンド用にプレイヤーをリセット"""
        players = Player.objects.filter(game=game)
        for player in players:
            if player.chips > 0:
                player.is_active = True
                player.is_folded = False
                player.current_bet = 0
                player.has_acted_this_round = False
                player.save()
            else:
                player.is_active = False
                player.save()
    
    @staticmethod
    def advance_game_phase(game, current_round):
        """ゲームのフェーズを進める"""
        # アクティブプレイヤーが1人以下の場合は即座にショーダウンへ
        active_players = current_round.get_active_players()
        if active_players.count() <= 1:
            current_round.phase = 'showdown'
            current_round.save()
            GameService._process_showdown(game, current_round)
            return
        
        if current_round.phase == 'preflop':
            # フロップ: 3枚のコミュニティカードを追加
            CardService.deal_community_cards(game, current_round, 3)
            current_round.phase = 'flop'
            
        elif current_round.phase == 'flop':
            # ターン: 1枚のコミュニティカードを追加
            CardService.deal_community_cards(game, current_round, 1)
            current_round.phase = 'turn'
            
        elif current_round.phase == 'turn':
            # リバー: 1枚のコミュニティカードを追加
            CardService.deal_community_cards(game, current_round, 1)
            current_round.phase = 'river'
            
        elif current_round.phase == 'river':
            # ショーダウン
            current_round.phase = 'showdown'
            GameService._process_showdown(game, current_round)
            
        elif current_round.phase == 'showdown':
            # ラウンド終了
            current_round.phase = 'finished'
            GameService._finish_round(game, current_round)
        
        current_round.save()
        
        # 新しいフェーズのベッティングを開始（ショーダウン以外）
        if current_round.phase not in ['showdown', 'finished']:
            BettingService.reset_betting_round(game, current_round)
            AIService.process_ai_actions(game, current_round)
    
    @staticmethod
    def _process_showdown(game, current_round):
        """ショーダウンを処理"""
        from ..services.card_service import HandEvaluator
        
        active_players = current_round.get_active_players()
        
        # アクティブプレイヤーが1人の場合は即座に勝利
        if active_players.count() == 1:
            winner = active_players.first()
            winner.chips += game.pot
            winner.save()
            game.pot = 0
            game.save()
            return
        
        # 複数プレイヤーの場合はハンド評価
        community_cards = current_round.get_community_cards()
        player_hands = []
        
        for player in active_players:
            player_cards = player.get_hand_cards()
            best_hand = HandEvaluator.get_best_hand(player_cards, community_cards)
            if best_hand:
                player_hands.append({
                    'player': player,
                    'hand': best_hand,
                    'rank': best_hand.hand_rank
                })
        
        if player_hands:
            # 最高ランクのプレイヤーを見つける
            max_rank = max(hand['rank'] for hand in player_hands)
            winners = [hand for hand in player_hands if hand['rank'] == max_rank]
            
            # ポットを分配
            pot_per_winner = game.pot // len(winners)
            for winner_info in winners:
                winner_info['player'].chips += pot_per_winner
                winner_info['player'].save()
            
            game.pot = 0
            game.save()
    
    @staticmethod
    def _finish_round(game, current_round):
        """ラウンドを終了"""
        # 現在のラウンドを終了状態にマーク
        current_round.phase = 'finished'
        current_round.save()
        
        # ディーラーポジションを進める
        PositionManager.advance_dealer_position(game)
        
        # 次のラウンドの準備
        game.current_round += 1
        game.save()
        
        # チップがあるプレイヤーが2人以上いる場合は続行
        active_players = Player.objects.filter(game=game, chips__gt=0).count()
        if active_players >= 2:
            # 少し待ってから新しいラウンドを開始
            import time
            time.sleep(1)  # ショーダウン結果を確認する時間
            GameService.start_new_round(game)
        else:
            # ゲーム終了
            game.status = 'finished'
            game.save()
    
    @staticmethod
    def leave_game(game, user):
        """ゲームから退出"""
        player = Player.objects.filter(user=user, game=game).first()
        if not player:
            raise ValueError('このゲームに参加していません')
        
        if game.status == 'in_progress':
            # ゲーム進行中の退出はペナルティ
            penalty = min(player.chips // 2, 100)
            player.chips -= penalty
            game.pot += penalty
            
            player.is_active = False
            player.is_folded = True
            game.save()
        
        player.delete()
        
        # プレイヤーが少なくなった場合はゲーム終了
        remaining_players = Player.objects.filter(game=game).count()
        if remaining_players < 2 and game.status == 'in_progress':
            game.status = 'finished'
            game.save()
