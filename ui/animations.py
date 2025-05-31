"""
动画管理模块
"""

import pygame
from models.constants import (
    WHITE, BLACK, WINDOW_WIDTH, WINDOW_HEIGHT, GRID_SIZE
)

class AnimationManager:
    """动画管理类"""
    
    def __init__(self):
        """初始化动画管理器"""
        # 玩家移动动画相关
        self.player_moving = False
        self.moving_player_id = -1
        self.move_path = []  # 存储移动路径的格子位置列表
        self.current_step = 0  # 当前移动到路径中的第几步
        self.step_progress = 0.0  # 当前步骤的进度 (0.0 到 1.0)
        self.move_speed = 0.02  # 每步移动的速度（降低速度，延长动画时间）
        
        # 创建骰子贴图
        self.create_dice_textures()
    
    def create_dice_textures(self):
        """创建骰子贴图"""
        self.dice_surfaces = []
        for i in range(1, 7):
            dice_surface = pygame.Surface((40, 40))
            dice_surface.fill(WHITE)
            pygame.draw.rect(dice_surface, BLACK, (0, 0, 40, 40), 2)
            
            # 绘制骰子点数
            dot_positions = {
                1: [(20, 20)],
                2: [(12, 12), (28, 28)],
                3: [(12, 12), (20, 20), (28, 28)],
                4: [(12, 12), (28, 12), (12, 28), (28, 28)],
                5: [(12, 12), (28, 12), (20, 20), (12, 28), (28, 28)],
                6: [(12, 10), (28, 10), (12, 20), (28, 20), (12, 30), (28, 30)]
            }
            
            for pos in dot_positions[i]:
                pygame.draw.circle(dice_surface, BLACK, pos, 3)
            
            self.dice_surfaces.append(dice_surface)
    
    def start_player_move_animation(self, player_id, start_position, end_position, dice_steps):
        """
        开始玩家移动动画
        
        Args:
            player_id (int): 移动的玩家ID
            start_position (int): 起始格子位置
            end_position (int): 目标格子位置  
            dice_steps (int): 骰子点数（移动步数）
        """
        self.player_moving = True
        self.moving_player_id = player_id
        self.current_step = 0
        self.step_progress = 0.0
        
        # 计算移动路径（按顺序经过的所有格子）
        self.move_path = []
        current_pos = start_position
        
        for step in range(dice_steps + 1):  # +1 包括起始位置
            self.move_path.append(current_pos)
            if step < dice_steps:  # 不是最后一步
                current_pos = (current_pos + 1) % GRID_SIZE
    
    def update_player_move_animation(self):
        """更新玩家移动动画"""
        if self.player_moving:
            self.step_progress += self.move_speed
            
            if self.step_progress >= 1.0:
                # 当前步骤完成，移动到下一步
                self.current_step += 1
                self.step_progress = 0.0
                
                if self.current_step >= len(self.move_path) - 1:
                    # 所有步骤完成
                    self.player_moving = False
                    self.current_step = 0
                    self.step_progress = 0.0
                    self.move_path = []
                    return True  # 动画完成
        return False
    
    def get_animated_player_position(self, player_id, board):
        """获取玩家的动画位置"""
        if self.player_moving and self.moving_player_id == player_id:
            # 获取当前步骤的起始和结束格子位置
            if self.current_step < len(self.move_path) - 1:
                current_cell = self.move_path[self.current_step]
                next_cell = self.move_path[self.current_step + 1]
                
                # 获取两个格子的屏幕坐标
                start_x, start_y = board.get_cell_position(current_cell)
                end_x, end_y = board.get_cell_position(next_cell)
                
                # 插值计算当前位置
                current_x = start_x + (end_x - start_x) * self.step_progress
                current_y = start_y + (end_y - start_y) * self.step_progress
                return (int(current_x), int(current_y))
            else:
                # 已经到达最后一格
                final_cell = self.move_path[-1] if self.move_path else 0
                return board.get_cell_position(final_cell)
        else:
            # 非移动中的玩家，返回正常位置
            return (0, 0)  # 这里会在调用处处理
    
    def draw_dice_result(self, screen, font, dice_result, effect_dice_result=0):
        """直接绘制骰子结果，无动画"""
        # 如果有格子效果骰子结果，优先显示
        if effect_dice_result > 0:
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            screen.blit(self.dice_surfaces[effect_dice_result - 1], (dice_x, dice_y))
            
        elif dice_result > 0:
            # 显示移动骰子结果
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            screen.blit(self.dice_surfaces[dice_result - 1], (dice_x, dice_y))
    
    def is_any_animation_running(self):
        """检查是否有任何动画正在运行"""
        return self.player_moving 