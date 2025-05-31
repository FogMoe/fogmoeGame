"""
简易大富翁游戏
使用模块化设计，分离关注点
"""

import pygame
import sys

from models.constants import WINDOW_WIDTH, WINDOW_HEIGHT
from game.board import Board
from game.game_logic import GameLogic
from ui.renderer import Renderer
from ui.animations import AnimationManager

class MonopolyGame:
    """大富翁游戏主类"""
    
    def __init__(self):
        """初始化游戏"""
        # 初始化pygame
        pygame.init()
        
        # 创建游戏窗口
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("简易大富翁游戏 - 开发中")
        self.clock = pygame.time.Clock()
        
        # 初始化游戏组件
        self.board = Board()
        self.game_logic = GameLogic()
        self.renderer = Renderer(self.screen)
        self.animation_manager = AnimationManager()
        
        # 游戏状态
        self.running = True
    
    def handle_events(self):
        """处理游戏事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_click(event.pos)
    
    def handle_mouse_click(self, pos):
        """处理鼠标点击事件"""
        button_rect = self.renderer.draw_ui(self.game_logic)
        
        if button_rect and button_rect.collidepoint(pos):
            if self.game_logic.is_game_over():
                # 重新开始游戏
                self.restart_game()
            elif not self.animation_manager.is_any_animation_running():
                current_player = self.game_logic.get_current_player()
                if not current_player.is_ai:
                    # 玩家投骰子
                    self.start_player_turn()
        
        elif (self.game_logic.waiting_for_click and 
              self.game_logic.get_current_player().is_ai and 
              not self.animation_manager.is_any_animation_running()):
            # AI回合，玩家点击继续
            self.start_player_turn()
    
    def start_player_turn(self):
        """开始玩家回合"""
        self.animation_manager.start_dice_roll()
    
    def update_animations(self):
        """更新所有动画"""
        # 更新骰子动画
        if self.animation_manager.update_dice_animation():
            # 骰子动画完成，执行移动
            self.execute_player_move()
        
        # 更新玩家移动动画
        if self.animation_manager.update_player_move_animation():
            # 移动动画完成
            self.handle_move_completion()
        
        # 更新格子效果动画
        if self.animation_manager.update_effect_dice_animation():
            # 格子效果动画完成
            self.handle_effect_completion()
    
    def execute_player_move(self):
        """执行玩家移动"""
        dice = self.game_logic.roll_dice()
        self.game_logic.dice_result = dice
        current_player = self.game_logic.get_current_player()
        
        # 开始玩家移动动画
        start_pos = self.board.get_cell_position(current_player.position)
        current_player.move(dice)
        end_pos = self.board.get_cell_position(current_player.position)
        
        self.animation_manager.start_player_move_animation(
            self.game_logic.current_player, start_pos, end_pos)
    
    def handle_move_completion(self):
        """处理移动完成后的逻辑"""
        # 添加短暂停顿
        pygame.time.wait(300)
        
        current_player = self.game_logic.get_current_player()
        effect_type, message = self.game_logic.handle_cell_effect(current_player, self.board)
        self.game_logic.message = message
        
        if self.game_logic.waiting_for_click:
            self.game_logic.waiting_for_click = False
        
        # 如果是奖励或惩罚格子，开始效果动画
        if effect_type in ['reward', 'penalty']:
            self.animation_manager.start_effect_dice_roll(effect_type, current_player)
        else:
            # 否则直接进入下一回合
            self.game_logic.next_turn()
    
    def handle_effect_completion(self):
        """处理格子效果完成后的逻辑"""
        # 执行格子效果
        current_player = self.game_logic.get_current_player()
        result_message = self.game_logic.execute_effect(
            self.animation_manager.effect_type, current_player)
        
        if result_message:
            self.game_logic.message = result_message
        
        # 增加停顿时间让玩家看到效果
        pygame.time.wait(1200)
        
        # 进入下一回合
        self.game_logic.next_turn()
    
    def render(self):
        """渲染游戏画面"""
        # 绘制棋盘
        self.renderer.draw_board(self.board)
        
        # 绘制玩家
        self.renderer.draw_players(self.game_logic.players, self.board, self.animation_manager)
        
        # 绘制UI
        self.renderer.draw_ui(self.game_logic)
        
        # 绘制动画
        self.animation_manager.draw_dice_animation(
            self.screen, self.renderer.font, self.game_logic.dice_result)
        
        # 更新显示
        pygame.display.flip()
    
    def restart_game(self):
        """重新开始游戏"""
        self.game_logic.restart_game()
        self.animation_manager = AnimationManager()
    
    def run(self):
        """运行游戏主循环"""
        while self.running:
            # 处理事件
            self.handle_events()
            
            # 更新动画
            self.update_animations()
            
            # 渲染画面
            self.render()
            
            # 控制帧率
            self.clock.tick(60)
        
        # 退出游戏
        pygame.quit()
        sys.exit()

def main():
    """主函数"""
    game = MonopolyGame()
    game.run()

if __name__ == "__main__":
    main() 