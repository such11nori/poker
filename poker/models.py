from django.db import models
from django.contrib.auth.models import User
import random
import json

class Card:
    """単一のカードを表すクラス"""
    SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.value = self.RANKS.index(rank) + 2
    
    def __str__(self):
        return f"{self.rank} of {self.suit}"
    
    def to_dict(self):
        return {'suit': self.suit, 'rank': self.rank}

class Deck:
    """52枚のカードデッキを表すクラス"""
    def __init__(self):
        self.cards = []
        self.reset()
    
    def reset(self):
        """デッキをリセットして52枚のカードを作成"""
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
        if not self.cards:
            self.reset()
        return self.cards.pop()

class PokerHand:
    """ポーカーハンドを評価するクラス"""
    HAND_RANKINGS = [
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
        """ストレートかどうかを確認"""
        if values == [14, 5, 4, 3, 2]:  # A-2-3-4-5 (wheel)
            return True
        
        for i in range(1, len(values)):
            if values[i-1] - values[i] != 1:
                return False
        return True

class Game(models.Model):
    """ポーカーゲームを表すモデル"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting for Players'),
        ('in_progress', 'In Progress'),
        ('finished', 'Finished'),
    ]
    
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_games', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    max_players = models.IntegerField(default=6)
    current_round = models.IntegerField(default=0)
    pot = models.IntegerField(default=0)  # チップの総額
    deck_cards = models.TextField(default='[]')  # 現在のデッキ状態を保存
    dealer_position = models.IntegerField(default=0)  # ディーラーの位置
    small_blind = models.IntegerField(default=10)  # スモールブラインド額
    big_blind = models.IntegerField(default=20)  # ビッグブラインド額
    
    def get_deck_cards(self):
        """デッキの状態を取得"""
        cards_data = json.loads(self.deck_cards)
        return [Card(card['suit'], card['rank']) for card in cards_data]
    
    def set_deck_cards(self, cards):
        """デッキの状態を保存"""
        cards_data = [card.to_dict() for card in cards]
        self.deck_cards = json.dumps(cards_data)
    
    def get_small_blind_position(self):
        """スモールブラインドの位置を取得"""
        active_players = Player.objects.filter(game=self, is_active=True).order_by('position')
        if active_players.count() < 2:
            return None
        
        # ディーラーの次がスモールブラインド
        dealer_pos = self.dealer_position
        positions = [p.position for p in active_players]
        
        # ディーラーより大きい位置で最小のものを探す
        next_positions = [pos for pos in positions if pos > dealer_pos]
        if next_positions:
            return min(next_positions)
        else:
            # ラップアラウンド
            return min(positions)
    
    def get_big_blind_position(self):
        """ビッグブラインドの位置を取得"""
        sb_pos = self.get_small_blind_position()
        if sb_pos is None:
            return None
            
        active_players = Player.objects.filter(game=self, is_active=True).order_by('position')
        positions = [p.position for p in active_players]
        
        # スモールブラインドより大きい位置で最小のものを探す
        next_positions = [pos for pos in positions if pos > sb_pos]
        if next_positions:
            return min(next_positions)
        else:
            # ラップアラウンド
            return min(positions)
    
    def __str__(self):
        return f"Game: {self.name} ({self.status})"

class Player(models.Model):
    """プレイヤーを表すモデル"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    chips = models.IntegerField(default=1000)  # 初期チップ数
    position = models.IntegerField()  # テーブルでの位置
    is_active = models.BooleanField(default=True)
    current_bet = models.IntegerField(default=0)
    hand_cards = models.TextField(default='[]')  # JSON形式でカードを保存
    is_ai = models.BooleanField(default=False)  # AIプレイヤーかどうか
    has_acted_this_round = models.BooleanField(default=False)  # このラウンドで行動したか
    is_folded = models.BooleanField(default=False)  # フォールドしたかどうか
    
    class Meta:
        unique_together = ('user', 'game')
    
    def get_hand_cards(self):
        """手札をCardオブジェクトのリストとして取得"""
        cards_data = json.loads(self.hand_cards)
        return [Card(card['suit'], card['rank']) for card in cards_data]
    
    def set_hand_cards(self, cards):
        """手札をセット"""
        cards_data = [card.to_dict() for card in cards]
        self.hand_cards = json.dumps(cards_data)
    
    def reset_for_new_round(self):
        """新しいラウンド用にプレイヤーをリセット"""
        if self.chips > 0:
            self.is_active = True
            self.is_folded = False
        else:
            self.is_active = False
        self.current_bet = 0
        self.has_acted_this_round = False
        self.hand_cards = '[]'
    
    def __str__(self):
        return f"{self.user.username} in {self.game.name}"

class GameRound(models.Model):
    """ゲームのラウンドを表すモデル"""
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
    current_player_position = models.IntegerField(default=0)  # 現在行動するプレイヤーの位置
    highest_bet = models.IntegerField(default=0)  # このラウンドの最高ベット額
    is_betting_complete = models.BooleanField(default=False)  # ベッティングが完了したか
    
    def get_community_cards(self):
        """コミュニティカードをCardオブジェクトのリストとして取得"""
        cards_data = json.loads(self.community_cards)
        return [Card(card['suit'], card['rank']) for card in cards_data]
    
    def set_community_cards(self, cards):
        """コミュニティカードをセット"""
        cards_data = [card.to_dict() for card in cards]
        self.community_cards = json.dumps(cards_data)
    
    def get_active_players(self):
        """アクティブなプレイヤーを取得"""
        return Player.objects.filter(
            game=self.game, 
            is_active=True, 
            is_folded=False
        ).order_by('position')
    
    def get_next_player_position(self):
        """次に行動すべきプレイヤーの位置を取得（時計回り）"""
        active_players = self.get_active_players()
        if not active_players:
            return None
            
        # アクティブなプレイヤーの位置を時計回りの順序でソート
        current_positions = sorted([p.position for p in active_players])
        
        # 現在のプレイヤーより時計回りで次の位置を探す
        next_positions = [pos for pos in current_positions if pos > self.current_player_position]
        
        if next_positions:
            return min(next_positions)
        else:
            # ラップアラウンド：最小の位置に戻る（テーブルを一周）
            return min(current_positions) if current_positions else None
    
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

class AIPlayer:
    """AIプレイヤーの思考ロジック"""
    
    def __init__(self, player, game_round, community_cards):
        self.player = player
        self.game_round = game_round
        self.community_cards = community_cards
        self.hand_cards = player.get_hand_cards()
    
    def evaluate_hand_strength(self):
        """ハンドの強さを0-10で評価"""
        all_cards = self.hand_cards + self.community_cards
        
        if len(all_cards) < 2:
            return 0
        
        # プリフロップの場合は手札のみで評価
        if len(self.community_cards) == 0:
            return self._evaluate_preflop()
        
        # ベストハンドを評価
        if len(all_cards) >= 5:
            from itertools import combinations
            best_rank = 0
            for combo in combinations(all_cards, 5):
                hand = PokerHand(list(combo))
                best_rank = max(best_rank, hand.hand_rank)
            return best_rank
        
        return self._evaluate_partial_hand(all_cards)
    
    def _evaluate_preflop(self):
        """プリフロップでの手札評価"""
        if len(self.hand_cards) != 2:
            return 0
        
        card1, card2 = self.hand_cards
        
        # ペア
        if card1.rank == card2.rank:
            if card1.value >= 10:  # T-T以上
                return 8
            elif card1.value >= 7:  # 7-7以上
                return 6
            else:
                return 4
        
        # スーテッド
        if card1.suit == card2.suit:
            # A-K, A-Q, A-J スーテッド
            if (card1.value == 14 and card2.value >= 11) or (card2.value == 14 and card1.value >= 11):
                return 7
            # K-Q, K-J スーテッド
            elif (card1.value == 13 and card2.value >= 11) or (card2.value == 13 and card1.value >= 11):
                return 5
            # その他スーテッド
            elif abs(card1.value - card2.value) <= 4:
                return 3
        
        # オフスーツ
        # A-K, A-Q オフスーツ
        if (card1.value == 14 and card2.value >= 12) or (card2.value == 14 and card1.value >= 12):
            return 6
        # K-Q オフスーツ
        elif (card1.value == 13 and card2.value == 12) or (card2.value == 13 and card1.value == 12):
            return 4
        
        return 2
    
    def _evaluate_partial_hand(self, cards):
        """部分的なハンド（フロップ、ターン）の評価"""
        values = [card.value for card in cards]
        suits = [card.suit for card in cards]
        
        value_counts = {}
        for value in values:
            value_counts[value] = value_counts.get(value, 0) + 1
        
        counts = sorted(value_counts.values(), reverse=True)
        
        # ペア以上
        if counts[0] >= 2:
            if counts[0] == 3:  # スリーカード
                return 7
            elif len(counts) >= 2 and counts[1] >= 2:  # ツーペア
                return 5
            else:  # ワンペア
                return 3
        
        # フラッシュドロー
        suit_counts = {}
        for suit in suits:
            suit_counts[suit] = suit_counts.get(suit, 0) + 1
        
        if max(suit_counts.values()) >= 4:
            return 4
        
        return 2
    
    def decide_action(self):
        """AIの行動を決定"""
        try:
            hand_strength = self.evaluate_hand_strength()
            pot_size = self.game_round.game.pot
            
            # ランダム性を加える
            import random
            randomness = random.uniform(0.8, 1.2)
            adjusted_strength = hand_strength * randomness
            
            # 現在のベット額を確認
            active_players = Player.objects.filter(
                game=self.game_round.game, 
                is_active=True, 
                is_folded=False
            )
            
            if not active_players:
                return ('fold', 0)
            
            max_bet = max([p.current_bet for p in active_players])
            call_amount = max_bet - self.player.current_bet
            
            # チップが足りない場合
            if call_amount >= self.player.chips:
                if adjusted_strength >= 6:  # 強いハンドなら オールイン
                    return ('all_in', self.player.chips)
                else:
                    return ('fold', 0)
            
            # 行動決定ロジック
            if adjusted_strength >= 7:  # 強いハンド
                if call_amount > 0:
                    # レイズするかコールするか
                    if random.random() < 0.7 and self.player.chips > call_amount:
                        raise_amount = min(pot_size // 2, self.player.chips - call_amount)
                        return ('raise', max(self.game_round.game.big_blind, raise_amount))
                    else:
                        return ('call', call_amount)
                else:
                    # ベットするかチェックするか
                    if random.random() < 0.8:
                        bet_amount = min(pot_size // 3, self.player.chips)
                        return ('raise', max(self.game_round.game.big_blind, bet_amount))
                    else:
                        return ('check', 0)
            
            elif adjusted_strength >= 4:  # 中程度のハンド
                if call_amount > 0:
                    if call_amount <= pot_size // 4 or call_amount <= self.game_round.game.big_blind * 2:  # ポットオッズが良い
                        return ('call', call_amount)
                    else:
                        return ('fold', 0)
                else:
                    return ('check', 0)
            
            else:  # 弱いハンド
                if call_amount > 0:
                    # ブラフの可能性
                    if random.random() < 0.1 and call_amount <= self.game_round.game.big_blind:
                        return ('call', call_amount)
                    else:
                        return ('fold', 0)
                else:
                    return ('check', 0)
                    
        except Exception as e:
            print(f"AI決定エラー: {e}")
            return ('fold', 0)
