"""
ベッティング関連サービス
"""
from ..models import Player, PlayerAction
from ..utils.position_manager import PositionManager


class BettingService:
    """ベッティング関連の操作を管理するサービス"""
    
    @staticmethod
    def apply_blinds(game, game_round):
        """ブラインドを適用"""
        from ..utils.position_manager import PositionManager
        
        sb_position = PositionManager.get_small_blind_position(game)
        bb_position = PositionManager.get_big_blind_position(game)
        
        if sb_position is not None:
            sb_player = Player.objects.filter(game=game, position=sb_position, is_active=True).first()
            if sb_player and sb_player.chips >= game.small_blind:
                sb_player.current_bet = game.small_blind
                sb_player.chips -= game.small_blind
                sb_player.has_acted_this_round = False  # プリフロップではまだアクション可能
                sb_player.save()
                game.pot += game.small_blind
        
        if bb_position is not None:
            bb_player = Player.objects.filter(game=game, position=bb_position, is_active=True).first()
            if bb_player and bb_player.chips >= game.big_blind:
                bb_player.current_bet = game.big_blind
                bb_player.chips -= game.big_blind
                bb_player.has_acted_this_round = False  # プリフロップではまだアクション可能
                bb_player.save()
                game.pot += game.big_blind
                
                # 最高ベット額を設定
                game_round.highest_bet = game.big_blind
        
        game.save()
        game_round.save()
    
    @staticmethod
    def is_betting_round_complete(game, current_round):
        """ベッティングラウンドが完了したかチェック"""
        active_players = current_round.get_active_players()
        
        # アクティブプレイヤーが1人以下の場合は即座に終了
        if active_players.count() <= 1:
            return True
        
        # 全員が行動したかチェック
        all_acted = all(player.has_acted_this_round for player in active_players)
        if not all_acted:
            return False
        
        # 全員のベット額が最高ベット額と同じかチェック（またはオールイン）
        all_equal_bet = all(
            player.current_bet == current_round.highest_bet or player.chips == 0 
            for player in active_players
        )
        
        return all_equal_bet
    
    @staticmethod
    def process_player_action(player, game, current_round, action, amount=0):
        """プレイヤーのアクションを処理"""
        # アクションを記録
        PlayerAction.objects.create(
            player=player,
            game_round=current_round,
            action=action,
            amount=amount
        )
        
        # アクションに応じてプレイヤーの状態を更新
        if action == 'fold':
            player.is_folded = True
            player.is_active = False
            
        elif action == 'call':
            call_amount = current_round.highest_bet - player.current_bet
            call_amount = min(call_amount, player.chips)  # チップが足りない場合は全額
            player.current_bet += call_amount
            player.chips -= call_amount
            game.pot += call_amount
            
        elif action == 'raise':
            # レイズの場合、まず現在の最高ベットにコールしてから追加でレイズ
            call_amount = current_round.highest_bet - player.current_bet
            total_amount = call_amount + amount
            total_amount = min(total_amount, player.chips)  # チップが足りない場合は全額
            
            player.current_bet += total_amount
            player.chips -= total_amount
            game.pot += total_amount
            
            # 最高ベット額を更新
            if player.current_bet > current_round.highest_bet:
                current_round.highest_bet = player.current_bet
                # 他のプレイヤーの行動フラグをリセット（レイズがあった場合）
                BettingService._reset_other_players_action_flags(game, player, current_round)
                
        elif action == 'check':
            # チェック（ベット額が最高額と同じ場合のみ可能）
            if player.current_bet != current_round.highest_bet:
                raise ValueError('Cannot check, must call or raise')
        
        elif action == 'all_in':
            all_in_amount = player.chips
            player.current_bet += all_in_amount
            player.chips = 0
            game.pot += all_in_amount
            if player.current_bet > current_round.highest_bet:
                current_round.highest_bet = player.current_bet
                BettingService._reset_other_players_action_flags(game, player, current_round)
        
        # プレイヤーが行動済みとマーク
        player.has_acted_this_round = True
        player.save()
        game.save()
        current_round.save()
    
    @staticmethod
    def _reset_other_players_action_flags(game, acting_player, current_round):
        """レイズがあった場合に他のプレイヤーの行動フラグをリセット"""
        for p in Player.objects.filter(game=game, is_active=True, is_folded=False).exclude(id=acting_player.id):
            if p.current_bet < current_round.highest_bet:
                p.has_acted_this_round = False
                p.save()
    
    @staticmethod
    def get_call_amount(player, current_round):
        """プレイヤーのコール金額を取得"""
        return max(0, current_round.highest_bet - player.current_bet)
    
    @staticmethod
    def reset_betting_round(game, current_round):
        """ベッティングラウンドをリセット（新しいフェーズ用）"""
        players = Player.objects.filter(game=game, is_active=True, is_folded=False)
        for player in players:
            player.current_bet = 0
            player.has_acted_this_round = False
            player.save()
        
        current_round.highest_bet = 0
        
        # フェーズに応じた開始位置を設定
        if current_round.phase == 'preflop':
            # プリフロップはUTGから開始
            from ..utils.position_manager import PositionManager
            first_position = PositionManager.get_preflop_first_player_position(current_round)
            current_round.current_player_position = first_position if first_position is not None else 0
        else:
            # ポストフロップはSBから開始
            from ..utils.position_manager import PositionManager
            first_position = PositionManager.get_postflop_first_player_position(current_round)
            current_round.current_player_position = first_position if first_position is not None else 0
        
        current_round.save()
