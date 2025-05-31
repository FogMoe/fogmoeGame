"""
动画管理模块
"""

import random
import pygame
from models.constants import (
    DICE_ANIMATION_FRAMES, PLAYER_MOVE_SPEED, 
    WHITE, BLACK, GOLD, WINDOW_WIDTH, WINDOW_HEIGHT,
    DARK_GREEN, DARK_RED
)

class AnimationManager:
    """动画管理类"""
    
    def __init__(self):
        """初始化动画管理器"""
        # 骰子动画相关
        self.dice_rolling = False
        self.dice_roll_frame = 0
        
        # 玩家移动动画相关
        self.player_moving = False
        self.move_start_pos = (0, 0)
        self.move_end_pos = (0, 0)
        self.move_progress = 0
        self.moving_player_id = -1
        
        # 格子效果骰子动画
        self.effect_dice_rolling = False
        self.effect_dice_frame = 0
        self.effect_type = ''
        self.effect_player = None
        
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
    
    def start_dice_roll(self):
        """开始骰子滚动动画"""
        self.dice_rolling = True
        self.dice_roll_frame = 0
    
    def start_effect_dice_roll(self, effect_type, player):
        """开始格子效果骰子动画"""
        self.effect_dice_rolling = True
        self.effect_dice_frame = 0
        self.effect_type = effect_type
        self.effect_player = player
    
    def start_player_move_animation(self, player_id, start_pos, end_pos):
        """开始玩家移动动画"""
        self.player_moving = True
        self.moving_player_id = player_id
        self.move_start_pos = start_pos
        self.move_end_pos = end_pos
        self.move_progress = 0
    
    def update_dice_animation(self):
        """更新骰子动画"""
        if self.dice_rolling:
            self.dice_roll_frame += 1
            if self.dice_roll_frame >= DICE_ANIMATION_FRAMES:
                self.dice_rolling = False
                self.dice_roll_frame = 0
                return True  # 动画完成
        return False
    
    def update_player_move_animation(self):
        """更新玩家移动动画"""
        if self.player_moving:
            self.move_progress += PLAYER_MOVE_SPEED * 0.01
            if self.move_progress >= 1.0:
                self.player_moving = False
                self.move_progress = 0
                return True  # 动画完成
        return False
    
    def update_effect_dice_animation(self):
        """更新格子效果骰子动画"""
        if self.effect_dice_rolling:
            self.effect_dice_frame += 1
            if self.effect_dice_frame >= DICE_ANIMATION_FRAMES:
                self.effect_dice_rolling = False
                self.effect_dice_frame = 0
                return True  # 动画完成
        return False
    
    def get_animated_player_position(self, player_id, cell_positions):
        """获取玩家的动画位置"""
        if self.player_moving and self.moving_player_id == player_id:
            # 插值计算当前位置
            start_x, start_y = self.move_start_pos
            end_x, end_y = self.move_end_pos
            current_x = start_x + (end_x - start_x) * self.move_progress
            current_y = start_y + (end_y - start_y) * self.move_progress
            return (int(current_x), int(current_y))
        else:
            return cell_positions[player_id] if player_id < len(cell_positions) else (0, 0)
    
    def draw_dice_animation(self, screen, font, dice_result):
        """绘制骰子动画"""
        if self.dice_rolling:
            # 在屏幕中央显示滚动的骰子
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            
            # 随机显示不同的骰子面来模拟滚动
            current_dice = random.randint(0, 5)
            screen.blit(self.dice_surfaces[current_dice], (dice_x, dice_y))
            
            # 显示提示文字
            text = font.render("投骰子移动！", True, BLACK)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
            screen.blit(text, text_rect)
            
        elif self.effect_dice_rolling:
            # 显示格子效果骰子动画
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            
            # 随机显示不同的骰子面来模拟滚动
            current_dice = random.randint(0, 5)
            screen.blit(self.dice_surfaces[current_dice], (dice_x, dice_y))
            
            # 显示不同的提示文字
            if self.effect_type == 'reward':
                text = font.render("投骰子获得金币！", True, DARK_GREEN)
            else:
                text = font.render("投骰子失去金币！", True, DARK_RED)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
            screen.blit(text, text_rect)
            
        elif dice_result > 0:
            # 显示最终的骰子结果
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            screen.blit(self.dice_surfaces[dice_result - 1], (dice_x, dice_y))
    
    def is_any_animation_running(self):
        """检查是否有任何动画正在运行"""
        return self.dice_rolling or self.player_moving or self.effect_dice_rolling 