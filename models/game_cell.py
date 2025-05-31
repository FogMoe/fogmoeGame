"""
游戏格子模型
"""

class GameCell:
    """游戏格子类"""
    
    def __init__(self, cell_type, position):
        """
        初始化游戏格子
        
        Args:
            cell_type (str): 格子类型 ('home', 'reward', 'penalty', 'normal')
            position (int): 格子在棋盘上的位置
        """
        self.type = cell_type
        self.position = position
        self.owner = 0  # 对于home格，记录属于哪个玩家 (默认为0)
    
    def is_home_cell(self):
        """判断是否为home格子"""
        return self.type == 'home'
    
    def is_reward_cell(self):
        """判断是否为奖励格子"""
        return self.type == 'reward'
    
    def is_penalty_cell(self):
        """判断是否为惩罚格子"""
        return self.type == 'penalty'
    
    def is_normal_cell(self):
        """判断是否为普通格子"""
        return self.type == 'normal' 