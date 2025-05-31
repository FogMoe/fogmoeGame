"""
游戏逻辑处理
"""

import random
import pygame
from models.player import Player
from models.constants import WINNING_MONEY

class GameLogic:
    """游戏逻辑类"""
    
    def __init__(self):
        """初始化游戏逻辑"""
        self.players = [
            Player(0, is_ai=False),  # 玩家1
            Player(1, is_ai=True),   # AI1
            Player(2, is_ai=True),   # AI2
            Player(3, is_ai=True)    # AI3
        ]
        self.current_player = 0
        self.game_over = False
        self.winner = None
        self.dice_result = 0
        self.message = "玩家1的回合，点击投骰子"
        self.waiting_for_click = False
        self.step_message = ""
    
    def roll_dice(self):
        """
        投骰子
        
        Returns:
            int: 骰子点数 (1-6)
        """
        return random.randint(1, 6)
    
    def handle_cell_effect(self, player, board):
        """
        处理玩家到达格子的效果
        
        Args:
            player (Player): 玩家对象
            board (Board): 棋盘对象
            
        Returns:
            tuple: (effect_type, message) 效果类型和消息
        """
        cell = board.get_cell(player.position)
        
        if cell.is_reward_cell():
            return ('reward', f"玩家{player.id + 1}到达奖励格，投骰子获得金币！")
        elif cell.is_penalty_cell():
            return ('penalty', f"玩家{player.id + 1}到达惩罚格，投骰子失去金币！")
        elif cell.is_home_cell():
            if cell.owner == player.id:
                if player.is_winner():
                    self.game_over = True
                    self.winner = player
                    return ('win', f"玩家{player.id + 1}获胜！")
                else:
                    return ('home', f"玩家{player.id + 1}回到home格，需要{WINNING_MONEY}金币才能获胜")
            else:
                return ('other_home', f"玩家{player.id + 1}到达玩家{cell.owner + 1}的home格")
        else:
            return ('normal', f"玩家{player.id + 1}到达普通格子")
    
    def execute_effect(self, effect_type, player):
        """
        执行格子效果
        
        Args:
            effect_type (str): 效果类型
            player (Player): 玩家对象
            
        Returns:
            str: 执行结果消息
        """
        dice_result = self.roll_dice()
        
        if effect_type == 'reward':
            player.add_money(dice_result)
            return f"玩家{player.id + 1}获得{dice_result}金币！"
        elif effect_type == 'penalty':
            player.lose_money(dice_result)
            return f"玩家{player.id + 1}失去{dice_result}金币！"
        
        return ""
    
    def next_turn(self):
        """切换到下一个玩家"""
        if not self.game_over:
            self.current_player = (self.current_player + 1) % 4
            self.waiting_for_click = False
            current_player = self.players[self.current_player]
            if current_player.is_ai:
                self.message = f"AI{self.current_player + 1}的回合，点击屏幕继续"
                self.waiting_for_click = True
            else:
                self.message = f"玩家{self.current_player + 1}的回合，点击投骰子"
    
    def get_current_player(self):
        """
        获取当前玩家
        
        Returns:
            Player: 当前玩家对象
        """
        return self.players[self.current_player]
    
    def restart_game(self):
        """重新开始游戏"""
        self.__init__()
    
    def is_game_over(self):
        """
        判断游戏是否结束
        
        Returns:
            bool: 游戏是否结束
        """
        return self.game_over 