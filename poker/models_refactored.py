"""
簡素化されたモデル（サービス層に移動したロジックを除去）
"""
import json
import random
from django.db import models
from django.contrib.auth.models import User


class Game(models.Model):
    """ポーカーゲームのモデル"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]
    
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    max_players = models.IntegerField(default=6)
    current_round = models.IntegerField(default=0)
    pot = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    deck_cards = models.TextField(default='[]')  # JSON形式でデッキを保存
    dealer_position = models.IntegerField(default=0)
    small_blind = models.IntegerField(default=10)
    big_blind = models.IntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def set_deck_cards(self, cards):
        """デッキのカードをJSONで保存"""
        self.deck_cards = json.dumps([card.__dict__ for card in cards])
    
    def get_deck_cards(self):
        """デッキのカードを復元"""
        try:
            cards_data = json.loads(self.deck_cards)
            return [Card(**card_data) for card_data in cards_data]
        except (json.JSONDecodeError, TypeError):
            return []
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class Player(models.Model):
    """プレイヤーのモデル"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    position = models.IntegerField()  # テーブル上の位置 (0-5)
    chips = models.IntegerField(default=1000)
    current_bet = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_folded = models.BooleanField(default=False)
    hand_cards = models.TextField(default='[]')  # JSON形式で手札を保存
    has_acted_this_round = models.BooleanField(default=False)
    is_ai = models.BooleanField(default=False)
    
    def set_hand_cards(self, cards):
        """手札をJSONで保存"""
        self.hand_cards = json.dumps(cards)
    
    def get_hand_cards(self):
        """手札を復元"""
        try:
            return json.loads(self.hand_cards)
        except (json.JSONDecodeError, TypeError):
            return []
    
    class Meta:
        unique_together = ('game', 'position')
    
    def __str__(self):
        return f"{self.user.username} (Position {self.position})"


class GameRound(models.Model):
    """ゲームラウンドのモデル"""
    PHASE_CHOICES = [
        ('preflop', 'Pre-flop'),
        ('flop', 'Flop'),
        ('turn', 'Turn'),
        ('river', 'River'),
        ('showdown', 'Showdown'),
        ('finished', 'Finished'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    round_number = models.IntegerField()
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='preflop')
    community_cards = models.TextField(default='[]')  # JSON形式でコミュニティカードを保存
    current_player_position = models.IntegerField(default=0)
    highest_bet = models.IntegerField(default=0)
    is_betting_complete = models.BooleanField(default=False)
    
    def set_community_cards(self, cards):
        """コミュニティカードをJSONで保存"""
        self.community_cards = json.dumps(cards)
    
    def get_community_cards(self):
        """コミュニティカードを復元"""
        try:
            return json.loads(self.community_cards)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def get_active_players(self):
        """アクティブなプレイヤーを取得"""
        return Player.objects.filter(
            game=self.game, 
            is_active=True, 
            is_folded=False
        ).order_by('position')
    
    def __str__(self):
        return f"Round {self.round_number} - {self.phase} in {self.game.name}"


class PlayerAction(models.Model):
    """プレイヤーのアクションを記録するモデル"""
    ACTION_CHOICES = [
        ('fold', 'Fold'),
        ('check', 'Check'),
        ('call', 'Call'),
        ('raise', 'Raise'),
        ('all_in', 'All In'),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game_round = models.ForeignKey(GameRound, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    amount = models.IntegerField(default=0)  # レイズやベットの金額
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.action} ({self.amount})"


# カード関連のクラス（サービス層で使用）
class Card:
    """トランプカードを表すクラス"""
    SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = self.RANKS.index(rank) + 2  # 2-14の値
    
    def __str__(self):
        return f"{self.rank} of {self.suit}"
    
    def __repr__(self):
        return self.__str__()


class Deck:
    """トランプのデッキを表すクラス"""
    def __init__(self):
        self.cards = []
        self.reset()
    
    def reset(self):
        """デッキをリセットしてシャッフル"""
        self.cards = []
        for suit in Card.SUITS:
            for rank in Card.RANKS:
                self.cards.append(Card(suit, rank))
        self.shuffle()
    
    def shuffle(self):
        """デッキをシャッフル"""
        random.shuffle(self.cards)
    
    def deal_card(self):
        """カードを1枚配る"""
        if self.cards:
            return self.cards.pop()
        return None


class PokerHand:
    """ポーカーハンドを評価するクラス"""
    HAND_NAMES = [
        'High Card', 'One Pair', 'Two Pair', 'Three of a Kind',
        'Straight', 'Flush', 'Full House', 'Four of a Kind',
        'Straight Flush', 'Royal Flush'
    ]
    
    def __init__(self, cards):
        self.cards = cards
        self.hand_rank, self.hand_name = self.evaluate_hand()
    
    def evaluate_hand(self):
        """ハンドを評価して順位と名前を返す"""
        values = [card.value for card in self.cards]
        suits = [card.suit for card in self.cards]
        
        # 値でソート
        values.sort(reverse=True)
        
        # フラッシュの確認
        is_flush = len(set(suits)) == 1
        
        # ストレートの確認
        is_straight = self._is_straight(values)
        
        # ペアの確認
        value_counts = {}
        for value in values:
            value_counts[value] = value_counts.get(value, 0) + 1
        
        counts = sorted(value_counts.values(), reverse=True)
        
        # ハンドの評価
        if is_straight and is_flush:
            if values == [14, 13, 12, 11, 10]:  # Royal Flush
                return (9, 'Royal Flush')
            else:
                return (8, 'Straight Flush')
        elif counts == [4, 1]:
            return (7, 'Four of a Kind')
        elif counts == [3, 2]:
            return (6, 'Full House')
        elif is_flush:
            return (5, 'Flush')
        elif is_straight:
            return (4, 'Straight')
        elif counts == [3, 1, 1]:
            return (3, 'Three of a Kind')
        elif counts == [2, 2, 1]:
            return (2, 'Two Pair')
        elif counts == [2, 1, 1, 1]:
            return (1, 'One Pair')
        else:
            return (0, 'High Card')
    
    def _is_straight(self, values):
        """ストレートかどうかをチェック"""
        if values == [14, 5, 4, 3, 2]:  # A-2-3-4-5のストレート
            return True
        
        for i in range(len(values) - 1):
            if values[i] - values[i + 1] != 1:
                return False
        return True
    
    def __str__(self):
        return self.hand_name
