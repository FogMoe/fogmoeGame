"""
游戏棋盘逻辑
"""

import pygame
import math
from models.game_cell import GameCell
from models.constants import GRID_SIZE, WINDOW_WIDTH, WINDOW_HEIGHT

class Board:
    """游戏棋盘类"""
    
    def __init__(self):
        """初始化棋盘"""
        self.board = []
        self.cell_positions = []
        self.init_board()
        self.calculate_cell_positions()
    
    def init_board(self):
        """初始化游戏棋盘"""
        self.board = []
        
        # 计算玩家home格的平均分散位置（27个格子，4个玩家）
        # 分别在位置 0, 7, 14, 21
        home_positions = [0, 7, 14, 21]
        
        for i in range(GRID_SIZE):
            if i in home_positions:
                # 确定是哪个玩家的home格
                player_id = home_positions.index(i)
                cell = GameCell('home', i)
                cell.owner = player_id
            elif i in [3, 6, 10, 13, 17, 20, 24]:  # 奖励格 (更多分散)
                cell = GameCell('reward', i)
            elif i in [2, 5, 9, 12, 16, 19, 23, 26]:  # 丢弃格 (更多分散)
                cell = GameCell('penalty', i)
            else:  # 普通格子
                cell = GameCell('normal', i)
            self.board.append(cell)
    
    def calculate_cell_positions(self):
        """计算每个格子在屏幕上的位置"""
        self.cell_positions = []
        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2
        # 增加半径以适应27个格子，避免重叠
        radius = 280
        
        for i in range(GRID_SIZE):
            angle = (i * 2 * math.pi) / GRID_SIZE - math.pi/2  # 从顶部开始
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            self.cell_positions.append((int(x), int(y)))
    
    def get_cell(self, position):
        """
        获取指定位置的格子
        
        Args:
            position (int): 格子位置
            
        Returns:
            GameCell: 格子对象
        """
        if 0 <= position < len(self.board):
            return self.board[position]
        return None
    
    def get_cell_position(self, position):
        """
        获取格子的屏幕坐标
        
        Args:
            position (int): 格子位置
            
        Returns:
            tuple: (x, y) 屏幕坐标
        """
        if 0 <= position < len(self.cell_positions):
            return self.cell_positions[position]
        return (0, 0) 