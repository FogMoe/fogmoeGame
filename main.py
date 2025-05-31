"""
简易大富翁游戏
使用模块化设计，分离关注点
"""

import pygame
import sys

from models.constants import (WINDOW_WIDTH, WINDOW_HEIGHT, GAME_STATE_START, 
                            GAME_STATE_PLAYING, GAME_STATE_RESULTS, WHITE, BLACK, 
                            GREEN, LIGHT_BLUE, RED, WINNING_MONEY, GOLD)
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
        pygame.display.set_caption("雾萌")
        self.clock = pygame.time.Clock()
        
        # 字体设置
        try:
            self.font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 24)
            self.big_font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 48)
            self.small_font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 18)
        except:
            self.font = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui", 24)
            self.big_font = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui", 48)
            self.small_font = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui", 18)
        
        # 游戏状态
        self.game_state = GAME_STATE_START
        self.running = True
        
        # 游戏组件（延迟初始化）
        self.board = None
        self.game_logic = None
        self.renderer = None
        self.animation_manager = None
        
        # 延迟状态管理
        self.waiting_state = None
        self.wait_start_time = 0
        self.wait_duration = 0
        self.pending_action = None
        
        # 游戏结果
        self.game_results = None
    
    def init_game_components(self):
        """初始化游戏组件"""
        self.board = Board()
        self.game_logic = GameLogic()
        self.renderer = Renderer(self.screen)
        self.animation_manager = AnimationManager()
        
        # 重置状态
        self.waiting_state = None
        self.pending_action = None
        if hasattr(self, 'ai_turn_delay'):
            delattr(self, 'ai_turn_delay')

    def handle_events(self):
        """处理游戏事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.game_state == GAME_STATE_START:
                    self.handle_start_screen_click(event.pos)
                elif self.game_state == GAME_STATE_PLAYING:
                    self.handle_game_click(event.pos)
                elif self.game_state == GAME_STATE_RESULTS:
                    self.handle_results_click(event.pos)
    
    def handle_start_screen_click(self, pos):
        """处理开始界面的点击"""
        # 开始游戏按钮区域 - 与绘制位置保持一致
        y_pos = 200 + 6 * 35 + 50  # 基础位置 + 6行文字 + 间距
        start_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_pos, 200, 60)
        if start_button.collidepoint(pos):
            self.start_new_game()
    
    def handle_results_click(self, pos):
        """处理结果界面的点击"""
        # 返回主菜单按钮
        back_button = pygame.Rect(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT - 100, 200, 50)
        if back_button.collidepoint(pos):
            self.game_state = GAME_STATE_START
    
    def start_new_game(self):
        """开始新游戏"""
        self.game_state = GAME_STATE_PLAYING
        self.init_game_components()
    
    def end_game_with_results(self):
        """结束游戏并显示结果"""
        self.game_state = GAME_STATE_RESULTS
        # 按金币数量排序玩家
        if self.game_logic and hasattr(self.game_logic, 'players'):
            self.game_results = sorted(self.game_logic.players, key=lambda p: p.money, reverse=True)
        else:
            self.game_results = []
    
    def handle_game_click(self, pos):
        """处理游戏中的鼠标点击事件"""
        if not self.game_logic or not self.renderer or not self.animation_manager:
            return
            
        if self.renderer and hasattr(self.renderer, 'draw_ui'):
            button_rect = self.renderer.draw_ui(self.game_logic)
        else:
            button_rect = None
        
        if button_rect and button_rect.collidepoint(pos):
            if hasattr(self.game_logic, 'is_game_over') and self.game_logic.is_game_over():
                # 游戏结束，显示结果
                self.end_game_with_results()
            elif hasattr(self.game_logic, 'waiting_for_effect_dice') and self.game_logic.waiting_for_effect_dice:
                # 投掷效果骰子
                self.handle_effect_dice_roll()
            elif (hasattr(self.animation_manager, 'is_any_animation_running') and 
                  not self.animation_manager.is_any_animation_running() and not self.waiting_state):
                current_player = self.game_logic.get_current_player()
                if not current_player.is_ai:
                    # 玩家投骰子
                    self.start_player_turn()
    
    def handle_effect_dice_roll(self):
        """处理真实玩家的效果骰子投掷"""
        if not self.game_logic:
            return
        result_message = self.game_logic.roll_effect_dice()
        if result_message:
            self.game_logic.message = result_message
        
        # 设置非阻塞等待
        self.start_wait('effect_completed', 1500, self.complete_effect_dice_roll)
    
    def complete_effect_dice_roll(self):
        """完成效果骰子投掷后的处理"""
        if not self.game_logic:
            return
        # 进入下一回合
        self.game_logic.next_turn()
    
    def handle_ai_effect_dice_roll(self):
        """处理AI的效果骰子投掷"""
        if not self.game_logic:
            return
        result_message = self.game_logic.roll_effect_dice()
        if result_message:
            self.game_logic.message = result_message
        
        # 设置非阻塞等待
        self.start_wait('ai_effect', 2000, self.complete_ai_effect_dice_roll)
    
    def complete_ai_effect_dice_roll(self):
        """完成AI效果骰子投掷后的处理"""
        if not self.game_logic:
            return
        # 进入下一回合
        self.game_logic.next_turn()
    
    def start_wait(self, state, duration, action):
        """开始非阻塞等待"""
        self.waiting_state = state
        self.wait_start_time = pygame.time.get_ticks()
        self.wait_duration = duration
        self.pending_action = action
    
    def update_wait_state(self):
        """更新等待状态"""
        if self.waiting_state and pygame.time.get_ticks() - self.wait_start_time >= self.wait_duration:
            # 等待时间到，执行待处理的动作
            action = self.pending_action
            self.waiting_state = None
            self.pending_action = None
            if action:
                action()
    
    def start_player_turn(self):
        """开始玩家回合"""
        if not self.game_logic:
            return
        # 清除上一回合的骰子结果
        self.game_logic.clear_dice_results()
        # 直接执行玩家移动，不播放骰子动画
        self.execute_player_move()
    
    def update_animations(self):
        """更新所有动画"""
        if not self.animation_manager:
            return
        # 只更新玩家移动动画
        if self.animation_manager.update_player_move_animation():
            # 移动动画完成
            self.handle_move_completion()
    
    def update_ai_logic(self):
        """更新AI逻辑，让AI自动进行回合"""
        if not self.game_logic or not self.animation_manager:
            return
        current_player = self.game_logic.get_current_player()
        
        # 如果当前是AI回合且没有动画在运行且没有等待效果骰子且没有在等待状态
        if (current_player.is_ai and 
            not self.animation_manager.is_any_animation_running() and
            not self.game_logic.waiting_for_effect_dice and
            not self.game_logic.is_game_over() and
            not self.waiting_state):
            
            # 添加AI思考时间，避免回合切换太快
            if not hasattr(self, 'ai_turn_delay'):
                self.ai_turn_delay = pygame.time.get_ticks()
            
            # 等待1秒钟后AI自动开始回合
            if pygame.time.get_ticks() - self.ai_turn_delay >= 1000:
                self.start_player_turn()
                # 重置延迟计时器
                delattr(self, 'ai_turn_delay')
    
    def execute_player_move(self):
        """执行玩家移动"""
        if not self.game_logic or not self.animation_manager:
            return
        dice = self.game_logic.roll_dice()
        self.game_logic.dice_result = dice
        current_player = self.game_logic.get_current_player()
        
        # 记录起始位置
        start_position = current_player.position
        
        # 移动玩家到目标位置
        current_player.move(dice)
        end_position = current_player.position
        
        # 开始玩家移动动画（逐格移动）
        self.animation_manager.start_player_move_animation(
            self.game_logic.current_player, start_position, end_position, dice)
    
    def handle_move_completion(self):
        """处理移动完成后的逻辑"""
        if not self.game_logic or not self.board:
            return
        current_player = self.game_logic.get_current_player()
        effect_type, message = self.game_logic.handle_cell_effect(current_player, self.board)
        self.game_logic.message = message
        
        if self.game_logic.waiting_for_click:
            self.game_logic.waiting_for_click = False
        
        # 如果是奖励或惩罚格子
        if effect_type in ['reward', 'penalty']:
            # 清除移动骰子结果，避免显示混乱
            self.game_logic.dice_result = 0
            
            if current_player.is_ai:
                # AI玩家自动处理效果骰子，添加延迟让玩家观察
                self.start_wait('move_completed', 800, self.handle_ai_effect_dice_roll)
            else:
                # 真实玩家需要手动点击投掷效果骰子
                pass  # 等待玩家点击
        else:
            # 其他格子延迟后进入下一回合
            delay = 800 if current_player.is_ai else 500
            self.start_wait('move_completed', delay, self.proceed_to_next_turn)
    
    def proceed_to_next_turn(self):
        """进入下一回合"""
        if not self.game_logic:
            return
        # 重置AI延迟计时器
        if hasattr(self, 'ai_turn_delay'):
            delattr(self, 'ai_turn_delay')
        
        self.game_logic.next_turn()
    
    def handle_effect_completion(self):
        """处理格子效果完成后的逻辑"""
        # 该方法现在不再需要，因为效果处理已经移到handle_move_completion中
        pass
    
    def render(self):
        """渲染游戏画面"""
        self.screen.fill(WHITE)
        
        if self.game_state == GAME_STATE_START:
            self.draw_start_screen()
        elif self.game_state == GAME_STATE_PLAYING:
            self.draw_game_screen()
        elif self.game_state == GAME_STATE_RESULTS:
            self.draw_results_screen()
        
        # 更新显示
        pygame.display.flip()
    
    def draw_start_screen(self):
        """绘制开始界面"""
        # 标题
        title_text = self.big_font.render("雾萌", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH//2, 100))
        self.screen.blit(title_text, title_rect)
        
        # 游戏说明
        instructions = [
            "游戏规则：",
            "• 4名玩家（1名真人玩家 + 3名AI）",
            "• 收集金币，回到自己的Home格获胜",
            f"• 获胜条件：拥有{WINNING_MONEY}金币并回到Home格",
            "• 奖励格（黄色）：获得金币",
            "• 丢弃格（深蓝色）：失去金币"
        ]
        
        y_offset = 200
        for instruction in instructions:
            text = self.font.render(instruction, True, BLACK)
            # 左对齐而不是居中，避免重叠
            self.screen.blit(text, (WINDOW_WIDTH//2 - 200, y_offset))
            y_offset += 35
        
        # 开始游戏按钮 - 放在更下面的位置
        start_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_offset + 50, 200, 60)
        pygame.draw.rect(self.screen, GREEN, start_button)
        pygame.draw.rect(self.screen, BLACK, start_button, 3)
        
        button_text = self.font.render("开始游戏", True, BLACK)
        button_rect = button_text.get_rect(center=start_button.center)
        self.screen.blit(button_text, button_rect)
    
    def draw_game_screen(self):
        """绘制游戏界面"""
        if not all([self.renderer, self.board, self.game_logic, self.animation_manager]):
            return
            
        # 绘制棋盘
        if self.renderer and hasattr(self.renderer, 'draw_board'):
            self.renderer.draw_board(self.board)
        
        # 绘制玩家
        if (self.renderer and hasattr(self.renderer, 'draw_players') and 
            self.game_logic and hasattr(self.game_logic, 'players')):
            self.renderer.draw_players(self.game_logic.players, self.board, self.animation_manager)
        
        # 绘制UI
        if self.renderer and hasattr(self.renderer, 'draw_ui'):
            self.renderer.draw_ui(self.game_logic)
        
        # 绘制骰子结果（无动画）
        if (self.animation_manager and hasattr(self.animation_manager, 'draw_dice_result') and 
            self.renderer and hasattr(self.renderer, 'font') and
            self.game_logic and hasattr(self.game_logic, 'dice_result') and
            hasattr(self.game_logic, 'effect_dice_result')):
            self.animation_manager.draw_dice_result(
                self.screen, self.renderer.font, self.game_logic.dice_result, self.game_logic.effect_dice_result)
    
    def draw_results_screen(self):
        """绘制结果界面"""
        # 标题
        title_text = self.big_font.render("游戏结束", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH//2, 100))
        self.screen.blit(title_text, title_rect)
        
        # 排名显示
        if self.game_results:
            rank_title = self.font.render("最终排名（按金币数量）:", True, BLACK)
            self.screen.blit(rank_title, (WINDOW_WIDTH//2 - 150, 200))
            
            y_offset = 250
            for i, player in enumerate(self.game_results):
                rank = i + 1
                player_type = "玩家" if not player.is_ai else "AI"
                rank_text = f"{rank}. {player_type}{player.id + 1}: {player.money} 金币"
                
                # 冠军用金色显示
                color = GOLD if rank == 1 else BLACK
                text = self.font.render(rank_text, True, color)
                self.screen.blit(text, (WINDOW_WIDTH//2 - 100, y_offset))
                y_offset += 40
        
        # 返回主菜单按钮
        back_button = pygame.Rect(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT - 100, 200, 50)
        pygame.draw.rect(self.screen, LIGHT_BLUE, back_button)
        pygame.draw.rect(self.screen, BLACK, back_button, 3)
        
        button_text = self.font.render("返回主菜单", True, BLACK)
        button_rect = button_text.get_rect(center=back_button.center)
        self.screen.blit(button_text, button_rect)
    
    def run(self):
        """运行游戏主循环"""
        while self.running:
            # 处理事件
            self.handle_events()
            
            # 只在游戏进行中更新游戏逻辑
            if self.game_state == GAME_STATE_PLAYING:
                # 更新等待状态
                self.update_wait_state()
                
                # 更新动画
                self.update_animations()
                
                # 更新AI逻辑
                self.update_ai_logic()
            
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