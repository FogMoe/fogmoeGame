"""
玩家模型
"""

from .constants import PLAYER_COLORS, WINNING_MONEY, GRID_SIZE

class Player:
    """玩家类"""
    
    def __init__(self, player_id, is_ai=False):
        """
        初始化玩家
        
        Args:
            player_id (int): 玩家ID (0-3)
            is_ai (bool): 是否为AI玩家
        """
        self.id = player_id
        self.money = 0
        # 玩家从自己的home格开始：0, 7, 14, 21
        home_positions = [0, 7, 14, 21]
        self.position = home_positions[player_id]
        self.is_ai = is_ai
        self.color = PLAYER_COLORS[player_id]
        
    def move(self, steps):
        """
        移动玩家位置
        
        Args:
            steps (int): 移动步数
        """
        self.position = (self.position + steps) % GRID_SIZE
        
    def add_money(self, amount):
        """
        增加金币
        
        Args:
            amount (int): 增加的金币数量
        """
        self.money += amount
        
    def lose_money(self, amount):
        """
        失去金币
        
        Args:
            amount (int): 失去的金币数量
        """
        self.money = max(0, self.money - amount)
        
    def is_winner(self):
        """
        判断是否获胜
        
        Returns:
            bool: 是否满足获胜条件
        """
        home_positions = [0, 7, 14, 21]
        return self.money >= WINNING_MONEY and self.position == home_positions[self.id]
    
    def get_player_type_name(self):
        """
        获取玩家类型名称
        
        Returns:
            str: 玩家类型名称
        """
        return "AI" if self.is_ai else "玩家" 