"""
游戏棋盘逻辑
"""

import pygame
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
        for i in range(GRID_SIZE):
            if i < 4:  # 前4个格子是各玩家的home格
                cell = GameCell('home', i)
                cell.owner = i
            elif i == 4 or i == 7:  # 奖励格
                cell = GameCell('reward', i)
            elif i == 5 or i == 8:  # 惩罚格
                cell = GameCell('penalty', i)
            else:  # 普通格子
                cell = GameCell('normal', i)
            self.board.append(cell)
    
    def calculate_cell_positions(self):
        """计算每个格子在屏幕上的位置"""
        self.cell_positions = []
        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2
        radius = 150
        
        for i in range(GRID_SIZE):
            angle = (i * 2 * 3.14159) / GRID_SIZE - 3.14159/2  # 从顶部开始
            x = center_x + radius * 1.2 * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).x
            y = center_y + radius * pygame.math.Vector2(1, 0).rotate(angle * 180 / 3.14159).y
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