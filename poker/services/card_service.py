"""
カード・デッキ管理サービス
"""
import random
from ..models import Deck, Card


class CardService:
    """カード関連の操作を管理するサービス"""
    
    @staticmethod
    def create_new_deck():
        """新しいデッキを作成"""
        return Deck()
    
    @staticmethod
    def deal_cards_to_players(game, game_round):
        """プレイヤーにカードを配る"""
        from ..models import Player
        
        # デッキを作成またはリセット
        if not game.deck_cards or game.deck_cards == '[]':
            deck = Deck()
            game.set_deck_cards(deck.cards)
            game.save()
        else:
            # 既存のデッキから復元
            deck_cards = game.get_deck_cards()
            deck = Deck()
            deck.cards = deck_cards
        
        players = Player.objects.filter(game=game, is_active=True).order_by('position')
        
        # 各プレイヤーに2枚のカードを配る
        for player in players:
            hand = [deck.deal_card(), deck.deal_card()]
            player.set_hand_cards(hand)
            player.current_bet = 0
            player.has_acted_this_round = False
            player.is_folded = False
            player.save()
        
        # デッキの状態を保存
        game.set_deck_cards(deck.cards)
        game.save()
        
        # コミュニティカードをセット（最初は空）
        game_round.set_community_cards([])
        game_round.save()
        
        return deck
    
    @staticmethod
    def deal_community_cards(game, current_round, num_cards):
        """コミュニティカードを配る"""
        # 既存のデッキから復元
        deck_cards = game.get_deck_cards()
        deck = Deck()
        deck.cards = deck_cards
        
        community_cards = current_round.get_community_cards()
        
        # バーンカード（使わないカード）を1枚捨てる
        if deck.cards:
            deck.deal_card()  # バーンカード
        
        # 指定された枚数のカードを追加
        for _ in range(num_cards):
            if deck.cards:
                community_cards.append(deck.deal_card())
        
        current_round.set_community_cards(community_cards)
        current_round.save()
        
        # デッキの状態を保存
        game.set_deck_cards(deck.cards)
        game.save()
        
        return community_cards


class HandEvaluator:
    """ハンド評価関連のユーティリティ"""
    
    @staticmethod
    def get_best_hand(player_cards, community_cards):
        """プレイヤーカードとコミュニティカードから最高のハンドを取得"""
        from ..models import PokerHand
        from itertools import combinations
        
        all_cards = player_cards + community_cards
        if len(all_cards) < 5:
            return None
        
        # 5枚の最良の組み合わせを見つける
        best_hand = None
        best_rank = -1
        
        for combo in combinations(all_cards, 5):
            hand = PokerHand(list(combo))
            if hand.hand_rank > best_rank:
                best_rank = hand.hand_rank
                best_hand = hand
        
        return best_hand
    
    @staticmethod
    def evaluate_hand_strength(player_cards, community_cards):
        """ハンドの強さを数値で評価（1-10、10が最強）"""
        if not community_cards:
            # プリフロップでの評価
            return HandEvaluator._evaluate_preflop_strength(player_cards)
        
        best_hand = HandEvaluator.get_best_hand(player_cards, community_cards)
        if not best_hand:
            return 1
        
        # ハンドランクに基づいて強さを返す
        hand_rank_mapping = {
            1: 2,   # ハイカード
            2: 3,   # ワンペア
            3: 5,   # ツーペア
            4: 6,   # スリーオブアカインド
            5: 7,   # ストレート
            6: 8,   # フラッシュ
            7: 9,   # フルハウス
            8: 10,  # フォーオブアカインド
            9: 10,  # ストレートフラッシュ
        }
        
        return hand_rank_mapping.get(best_hand.hand_rank, 1)
    
    @staticmethod
    def _evaluate_preflop_strength(player_cards):
        """プリフロップでのハンド強さ評価"""
        if len(player_cards) != 2:
            return 1
        
        card1, card2 = player_cards
        rank1 = card1['rank']
        rank2 = card2['rank']
        suit1 = card1['suit']
        suit2 = card2['suit']
        
        # ランクを数値に変換
        rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
                      '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        
        val1 = rank_values.get(rank1, 0)
        val2 = rank_values.get(rank2, 0)
        
        # ペア
        if val1 == val2:
            if val1 >= 13:  # AA, KK
                return 10
            elif val1 >= 11:  # QQ, JJ
                return 9
            elif val1 >= 9:  # TT, 99
                return 8
            else:
                return 7
        
        # スーテッド
        is_suited = suit1 == suit2
        high_val = max(val1, val2)
        low_val = min(val1, val2)
        
        # AK, AQ suited
        if high_val == 14 and low_val >= 12 and is_suited:
            return 9
        
        # AK, AQ offsuit
        if high_val == 14 and low_val >= 12:
            return 8
        
        # その他の高いカード
        if high_val >= 12 and low_val >= 10:
            return 7 if is_suited else 6
        
        # 中程度のカード
        if high_val >= 10:
            return 5 if is_suited else 4
        
        return 3 if is_suited else 2
