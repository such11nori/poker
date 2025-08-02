"""
ポジション管理ユーティリティ
"""
import random


class PositionManager:
    """テーブルポジション管理"""
    
    @staticmethod
    def get_random_available_position(game):
        """利用可能なランダムポジションを取得"""
        from ..models import Player
        
        occupied_positions = set(
            Player.objects.filter(game=game).values_list('position', flat=True)
        )
        
        all_positions = set(range(game.max_players))
        available_positions = list(all_positions - occupied_positions)
        
        if not available_positions:
            return None
        
        return random.choice(available_positions)
    
    @staticmethod
    def get_dealer_position(game):
        """ディーラーポジションを取得"""
        return game.dealer_position
    
    @staticmethod
    def get_small_blind_position(game):
        """スモールブラインドポジションを取得"""
        from ..models import Player
        
        active_players = Player.objects.filter(game=game, is_active=True).order_by('position')
        player_count = active_players.count()
        
        if player_count < 2:
            return None
        
        positions = [p.position for p in active_players]
        dealer_pos = game.dealer_position
        
        if dealer_pos not in positions:
            return positions[0] if positions else None
        
        dealer_index = positions.index(dealer_pos)
        
        if player_count == 2:
            # ヘッズアップ：ディーラーがSB
            return dealer_pos
        else:
            # 3人以上：ディーラーの次がSB
            return positions[(dealer_index + 1) % len(positions)]
    
    @staticmethod
    def get_big_blind_position(game):
        """ビッグブラインドポジションを取得"""
        from ..models import Player
        
        active_players = Player.objects.filter(game=game, is_active=True).order_by('position')
        player_count = active_players.count()
        
        if player_count < 2:
            return None
        
        positions = [p.position for p in active_players]
        dealer_pos = game.dealer_position
        
        if dealer_pos not in positions:
            return positions[1] if len(positions) > 1 else positions[0]
        
        dealer_index = positions.index(dealer_pos)
        
        if player_count == 2:
            # ヘッズアップ：ディーラーでない方がBB
            return positions[(dealer_index + 1) % len(positions)]
        else:
            # 3人以上：ディーラーの2つ次がBB
            return positions[(dealer_index + 2) % len(positions)]
    
    @staticmethod
    def get_next_player_position(current_round):
        """次のプレイヤーポジションを取得（時計回り）"""
        active_players = current_round.get_active_players()
        if not active_players:
            return None
            
        # アクティブなプレイヤーの位置を昇順でソート（時計回り）
        current_positions = sorted([p.position for p in active_players])
        current_pos = current_round.current_player_position
        
        # 現在のプレイヤーより時計回りで次の位置を探す
        next_positions = [pos for pos in current_positions if pos > current_pos]
        
        if next_positions:
            return min(next_positions)
        else:
            # ラップアラウンド：最小の位置に戻る（テーブルを一周）
            return min(current_positions) if current_positions else None
    
    @staticmethod
    def get_preflop_first_player_position(game_round):
        """プリフロップで最初に行動するプレイヤーのポジションを取得（UTG = BBの次）"""
        active_players = game_round.get_active_players()
        if not active_players:
            return None
        
        # GameオブジェクトからBBポジションを取得
        bb_position = PositionManager.get_big_blind_position(game_round.game)
        if bb_position is None:
            return None
        
        positions = sorted([p.position for p in active_players])
        player_count = len(positions)
        
        if player_count < 2:
            return None
        
        if player_count == 2:
            # ヘッズアップ：SBから開始（SB = ディーラー）
            sb_position = PositionManager.get_small_blind_position(game_round.game)
            # SBがアクティブかチェック
            if sb_position in positions:
                return sb_position
            else:
                # SBがフォールドしていればBBから
                return bb_position if bb_position in positions else positions[0]
        else:
            # 3人以上：UTG（BBの次のプレイヤー）から開始
            if bb_position not in positions:
                return positions[0] if positions else None
            
            bb_index = positions.index(bb_position)
            # BBの次のプレイヤー（時計回り）
            utg_index = (bb_index + 1) % len(positions)
            return positions[utg_index]

    @staticmethod
    def get_postflop_first_player_position(game_round):
        """ポストフロップで最初に行動するプレイヤーのポジションを取得（SBから開始）"""
        active_players = game_round.get_active_players()
        if not active_players:
            return None
        
        # GameオブジェクトからSBポジションを取得
        sb_position = PositionManager.get_small_blind_position(game_round.game)
        if sb_position is None:
            return None
        
        positions = sorted([p.position for p in active_players])
        
        # SBから時計回りで最初のアクティブプレイヤーを探す
        sb_candidates = [pos for pos in positions if pos >= sb_position]
        
        if sb_candidates:
            return min(sb_candidates)  # SB以降の最小位置
        else:
            # ラップアラウンド：テーブル最小位置から開始
            return min(positions) if positions else None

    @staticmethod
    def advance_dealer_position(game):
        """ディーラーポジションを次に進める"""
        from ..models import Player
        
        # チップがあるプレイヤーのみを対象にする
        active_players = Player.objects.filter(
            game=game, 
            chips__gt=0
        ).order_by('position')
        positions = [p.position for p in active_players]
        
        if not positions:
            return
        
        current_dealer = game.dealer_position
        
        # 現在のディーラーが対象プレイヤーに含まれない場合は最初のプレイヤーに設定
        if current_dealer not in positions:
            game.dealer_position = min(positions)
            game.save()
            return
        
        # 現在のディーラーより大きい位置で最小のものを探す（時計回り）
        next_positions = [pos for pos in positions if pos > current_dealer]
        if next_positions:
            game.dealer_position = min(next_positions)
        else:
            # ラップアラウンド：最小の位置に戻る（一周して戻る）
            game.dealer_position = min(positions)
        
        game.save()
