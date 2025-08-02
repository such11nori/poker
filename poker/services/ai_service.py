"""
AI関連サービス
"""
import random
from ..models import Player, PlayerAction
from ..services.card_service import HandEvaluator
from ..services.betting_service import BettingService
from ..utils.position_manager import PositionManager


class AIService:
    """AI関連の操作を管理するサービス"""
    
    @staticmethod
    def process_ai_actions(game, current_round):
        """AIプレイヤーの行動を処理"""
        max_iterations = 20  # 無限ループを防ぐ（増加）
        iteration_count = 0
        
        while iteration_count < max_iterations:
            iteration_count += 1
            
            # 現在のラウンドを再読み込み
            current_round.refresh_from_db()
            
            # ベッティングラウンドが完了している場合は終了
            if BettingService.is_betting_round_complete(game, current_round):
                break
            
            # 現在のプレイヤーを取得
            current_player = Player.objects.filter(
                game=game, 
                position=current_round.current_player_position,
                is_active=True,
                is_folded=False
            ).first()
            
            if not current_player:
                # プレイヤーが見つからない場合、次のプレイヤーに移動を試す
                next_position = PositionManager.get_next_player_position(current_round)
                if next_position is not None and next_position != current_round.current_player_position:
                    current_round.current_player_position = next_position
                    current_round.save()
                    continue
                else:
                    break
                
            if not current_player.is_ai:
                break  # AIプレイヤーでない場合は終了
                
            if current_player.has_acted_this_round:
                # すでに行動済みの場合、次のプレイヤーに移動
                next_position = PositionManager.get_next_player_position(current_round)
                if next_position is not None and next_position != current_round.current_player_position:
                    current_round.current_player_position = next_position
                    current_round.save()
                    continue
                else:
                    break  # 全員が行動済み
            
            # AIの行動を実行
            print(f"AI Player at position {current_player.position} is taking action...")
            AIService._execute_ai_action(current_player, game, current_round)
            
            # 次のプレイヤーに移動
            AIService._move_to_next_player(current_round)
    
    @staticmethod
    def _execute_ai_action(ai_player, game, current_round):
        """AIプレイヤーの具体的なアクションを実行"""
        try:
            # チップが0の場合はフォールド
            if ai_player.chips <= 0:
                BettingService.process_player_action(ai_player, game, current_round, 'fold', 0)
                return
            
            # AIの行動を決定
            community_cards = current_round.get_community_cards()
            action, amount = AIService._decide_ai_action(ai_player, current_round, community_cards)
            
            # チップが足りない場合の調整
            if action == 'call':
                call_amount = current_round.highest_bet - ai_player.current_bet
                amount = min(call_amount, ai_player.chips)
                
            elif action == 'raise':
                call_amount = current_round.highest_bet - ai_player.current_bet
                total_amount = call_amount + amount
                if total_amount > ai_player.chips:
                    amount = ai_player.chips
                    action = 'all_in' if amount > 0 else 'fold'
            
            # アクションを処理
            print(f"AI Player {ai_player.user.username} at position {ai_player.position} chose: {action} ({amount})")
            BettingService.process_player_action(ai_player, game, current_round, action, amount)
            
        except Exception as e:
            # エラーが発生した場合はフォールド
            print(f"AIエラー: {e}")
            BettingService.process_player_action(ai_player, game, current_round, 'fold', 0)
    
    @staticmethod
    def _move_to_next_player(current_round):
        """次のプレイヤーに移動"""
        next_position = PositionManager.get_next_player_position(current_round)
        if next_position is not None:
            current_round.current_player_position = next_position
            current_round.save()
    
    @staticmethod
    def _decide_ai_action(ai_player, game_round, community_cards):
        """AIの行動を決定"""
        try:
            player_cards = ai_player.get_hand_cards()
            hand_strength = HandEvaluator.evaluate_hand_strength(player_cards, community_cards)
            pot_size = game_round.game.pot
            
            # ランダム性を加える
            randomness = random.uniform(0.8, 1.2)
            adjusted_strength = hand_strength * randomness
            
            # 現在のベット額を確認
            active_players = Player.objects.filter(
                game=game_round.game, 
                is_active=True, 
                is_folded=False
            )
            
            if not active_players:
                return ('fold', 0)
            
            max_bet = max([p.current_bet for p in active_players])
            call_amount = max_bet - ai_player.current_bet
            
            # チップが足りない場合
            if call_amount >= ai_player.chips:
                if adjusted_strength >= 6:  # 強いハンドなら オールイン
                    return ('all_in', ai_player.chips)
                else:
                    return ('fold', 0)
            
            # 行動決定ロジック
            if adjusted_strength >= 7:  # 強いハンド
                if call_amount > 0:
                    # レイズするかコールするか
                    if random.random() < 0.7 and ai_player.chips > call_amount:
                        raise_amount = min(pot_size // 2, ai_player.chips - call_amount)
                        return ('raise', max(game_round.game.big_blind, raise_amount))
                    else:
                        return ('call', call_amount)
                else:
                    # ベットするかチェックするか
                    if random.random() < 0.8:
                        bet_amount = min(pot_size // 3, ai_player.chips)
                        return ('raise', max(game_round.game.big_blind, bet_amount))
                    else:
                        return ('check', 0)
            
            elif adjusted_strength >= 4:  # 中程度のハンド
                if call_amount > 0:
                    if call_amount <= pot_size // 4 or call_amount <= game_round.game.big_blind * 2:  # ポットオッズが良い
                        return ('call', call_amount)
                    else:
                        return ('fold', 0)
                else:
                    return ('check', 0)
            
            else:  # 弱いハンド
                if call_amount > 0:
                    # ブラフの可能性
                    if random.random() < 0.1 and call_amount <= game_round.game.big_blind:
                        return ('call', call_amount)
                    else:
                        return ('fold', 0)
                else:
                    return ('check', 0)
                    
        except Exception as e:
            print(f"AI決定エラー: {e}")
            return ('fold', 0)
