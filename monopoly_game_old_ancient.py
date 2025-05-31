import pygame
import random
import sys

# 初始化pygame
pygame.init()

# 常量设置
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
GRID_SIZE = 9
CELL_SIZE = 80
WINNING_MONEY = 300

# 动画设置
ANIMATION_SPEED = 0.1
DICE_ANIMATION_FRAMES = 45  # 进一步增加骰子动画帧数，让动画更慢
PLAYER_MOVE_SPEED = 1.5     # 进一步降低玩家移动速度

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
LIGHT_BLUE = (173, 216, 230)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
DARK_GREEN = (0, 128, 0)
DARK_RED = (139, 0, 0)
# 新增更多颜色
DEEP_PURPLE = (75, 0, 130)    # 深紫色
CORAL = (255, 127, 80)        # 珊瑚色
TURQUOISE = (64, 224, 208)    # 青绿色
MAGENTA = (255, 0, 255)       # 洋红色

# 玩家颜色 - 使用更多样化的颜色避免与格子冲突
PLAYER_COLORS = [DEEP_PURPLE, CORAL, TURQUOISE, MAGENTA]

# 格子颜色 - 使用与玩家相同的颜色
HOME_COLORS = PLAYER_COLORS  # 直接使用玩家颜色

class GameCell:
    def __init__(self, cell_type, position):
        self.type = cell_type  # 'home', 'reward', 'penalty', 'normal'
        self.position = position
        self.owner = 0  # 对于home格，记录属于哪个玩家 (默认为0)

class Player:
    def __init__(self, player_id, is_ai=False):
        self.id = player_id
        self.money = 100
        self.position = player_id  # 从自己的home格开始
        self.is_ai = is_ai
        self.color = PLAYER_COLORS[player_id]
        
    def move(self, steps):
        self.position = (self.position + steps) % GRID_SIZE
        
    def add_money(self, amount):
        self.money += amount
        
    def lose_money(self, amount):
        self.money = max(0, self.money - amount)
        
    def is_winner(self):
        return self.money >= WINNING_MONEY and self.position == self.id

class MonopolyGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("简易大富翁游戏")
        self.clock = pygame.time.Clock()
        
        # 使用支持中文的字体
        try:
            # 尝试使用系统中文字体
            self.font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 20)
            self.big_font = pygame.font.Font("C:/Windows/Fonts/simhei.ttf", 32)
        except:
            try:
                # 备选字体
                self.font = pygame.font.Font("C:/Windows/Fonts/msyh.ttc", 20)
                self.big_font = pygame.font.Font("C:/Windows/Fonts/msyh.ttc", 32)
            except:
                # 如果找不到中文字体，使用系统默认字体
                self.font = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui", 20)
                self.big_font = pygame.font.SysFont("microsoftyaheimicrosoftyaheiui", 32)
        
        # 初始化游戏状态
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
        self.waiting_for_click = False  # 是否等待玩家点击
        self.step_message = ""  # 当前步骤的详细信息
          # 动画相关变量
        self.animating = False
        self.animation_frame = 0
        self.dice_rolling = False
        self.dice_roll_frame = 0
        self.player_moving = False
        self.move_start_pos = (0, 0)  # 初始化为元组
        self.move_end_pos = (0, 0)    # 初始化为元组
        self.move_progress = 0
        self.moving_player_id = -1
          # 格子效果骰子动画
        self.effect_dice_rolling = False
        self.effect_dice_frame = 0
        self.effect_type = ''
        self.effect_player = self.players[0]  # 初始化为第一个玩家
        
        # 初始化地图
        self.init_board()
        
        # 计算格子位置
        self.calculate_cell_positions()
        
        # 创建贴图
        self.create_textures()
        
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
    
    def create_textures(self):
        """创建游戏贴图"""
        # 创建骰子贴图
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
                6: [(12, 10), (28, 10), (12, 20), (28, 20), (12, 30), (28, 30)]            }
            
            for pos in dot_positions[i]:
                pygame.draw.circle(dice_surface, BLACK, pos, 3)
            
            self.dice_surfaces.append(dice_surface)
    
    def animate_dice_roll(self):
        """骰子滚动动画"""
        if self.dice_rolling:
            self.dice_roll_frame += 1
            if self.dice_roll_frame >= DICE_ANIMATION_FRAMES:
                self.dice_rolling = False
                self.dice_roll_frame = 0
                return True  # 动画完成
        return False
    
    def start_player_move_animation(self, player_id, start_pos, end_pos):
        """开始玩家移动动画"""
        self.player_moving = True
        self.moving_player_id = player_id
        self.move_start_pos = start_pos
        self.move_end_pos = end_pos
        self.move_progress = 0
    
    def update_player_move_animation(self):
        """更新玩家移动动画"""
        if self.player_moving:
            self.move_progress += PLAYER_MOVE_SPEED * 0.01  # 进一步减慢移动速度
            if self.move_progress >= 1.0:
                self.player_moving = False
                self.move_progress = 0
                return True  # 动画完成
        return False
    
    def get_animated_player_position(self, player_id):
        """获取玩家的动画位置"""
        if self.player_moving and self.moving_player_id == player_id:            # 插值计算当前位置
            start_x, start_y = self.move_start_pos
            end_x, end_y = self.move_end_pos
            current_x = start_x + (end_x - start_x) * self.move_progress
            current_y = start_y + (end_y - start_y) * self.move_progress
            return (int(current_x), int(current_y))
        else:            return self.cell_positions[self.players[player_id].position]
    
    def roll_dice(self):
        """投骰子"""
        return random.randint(1, 6)
    
    def handle_cell_effect(self, player):
        """处理玩家到达格子的效果"""
        cell = self.board[player.position]
        
        if cell.type == 'reward':
            # 开始奖励骰子动画
            self.effect_dice_rolling = True
            self.effect_dice_frame = 0
            self.effect_type = 'reward'
            self.effect_player = player
            self.message = f"玩家{player.id + 1}到达奖励格，投骰子获得金币！"
        elif cell.type == 'penalty':
            # 开始惩罚骰子动画
            self.effect_dice_rolling = True
            self.effect_dice_frame = 0
            self.effect_type = 'penalty'
            self.effect_player = player
            self.message = f"玩家{player.id + 1}到达惩罚格，投骰子失去金币！"
        elif cell.type == 'home':
            if cell.owner == player.id:
                if player.is_winner():
                    self.game_over = True
                    self.winner = player
                    self.message = f"玩家{player.id + 1}获胜！"
                else:
                    self.message = f"玩家{player.id + 1}回到home格，需要{WINNING_MONEY}金币才能获胜"
            else:
                self.message = f"玩家{player.id + 1}到达玩家{cell.owner + 1}的home格"
        else:
            self.message = f"玩家{player.id + 1}到达普通格子"
    
    def next_turn(self):
        """切换到下一个玩家"""
        if not self.game_over:
            self.current_player = (self.current_player + 1) % 4
            self.waiting_for_click = False
            if self.players[self.current_player].is_ai:
                self.message = f"AI{self.current_player + 1}的回合，点击屏幕继续"
                self.waiting_for_click = True
            else:
                self.message = f"玩家{self.current_player + 1}的回合，点击投骰子"
    
    def ai_turn(self):
        """AI自动投骰子"""
        if self.players[self.current_player].is_ai and not self.game_over:
            dice = self.roll_dice()
            self.dice_result = dice
            player = self.players[self.current_player]
            player.move(dice)
            self.handle_cell_effect(player)
            pygame.time.wait(1000)  # AI思考时间
            self.next_turn()
    
    def draw_board(self):
        """绘制游戏棋盘"""
        self.screen.fill(WHITE)
        
        # 绘制格子
        for i, (x, y) in enumerate(self.cell_positions):
            cell = self.board[i]
              # 选择格子颜色
            if cell.type == 'home':
                color = HOME_COLORS[cell.owner]
            elif cell.type == 'reward':
                color = GREEN
            elif cell.type == 'penalty':
                color = RED
            else:
                color = GRAY
            
            # 绘制格子
            pygame.draw.rect(self.screen, color, 
                           (x - CELL_SIZE//2, y - CELL_SIZE//2, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(self.screen, BLACK, 
                           (x - CELL_SIZE//2, y - CELL_SIZE//2, CELL_SIZE, CELL_SIZE), 2)
            
            # 显示格子编号
            text = self.font.render(str(i), True, BLACK)
            text_rect = text.get_rect(center=(x, y - 20))
            self.screen.blit(text, text_rect)
            
            # 显示格子类型
            if cell.type == 'home':
                type_text = f"H{cell.owner + 1}"
            elif cell.type == 'reward':
                type_text = "奖励"
            elif cell.type == 'penalty':
                type_text = "惩罚"
            else:
                type_text = "普通"
            
            text = self.font.render(type_text, True, BLACK)
            text_rect = text.get_rect(center=(x, y + 10))
            self.screen.blit(text, text_rect)
        
        # 绘制玩家
        for i, player in enumerate(self.players):
            pos_x, pos_y = self.cell_positions[player.position]
            # 为了避免玩家重叠，稍微偏移位置
            offset_x = (i % 2) * 15 - 7
            offset_y = (i // 2) * 15 - 7
            
            pygame.draw.circle(self.screen, player.color, 
                             (pos_x + offset_x, pos_y + offset_y), 8)
            pygame.draw.circle(self.screen, BLACK, 
                             (pos_x + offset_x, pos_y + offset_y), 8, 2)
    
    def draw_ui(self):
        """绘制用户界面"""
        # 绘制玩家信息
        y_offset = 10
        for i, player in enumerate(self.players):
            player_type = "玩家" if not player.is_ai else "AI"
            text = f"{player_type}{i + 1}: {player.money}金币"
            if i == self.current_player:
                text = f">>> {text} <<<"
            
            color = BLACK if i != self.current_player else RED
            rendered_text = self.font.render(text, True, color)
            self.screen.blit(rendered_text, (10, y_offset))
            y_offset += 30
        
        # 绘制骰子结果
        if self.dice_result > 0:
            dice_text = f"骰子点数: {self.dice_result}"
            rendered_text = self.font.render(dice_text, True, BLACK)
            self.screen.blit(rendered_text, (10, y_offset + 20))
        
        # 绘制消息
        message_text = self.font.render(self.message, True, BLACK)
        self.screen.blit(message_text, (10, WINDOW_HEIGHT - 80))
        
        # 绘制投骰子按钮（仅当前玩家不是AI时）
        if not self.players[self.current_player].is_ai and not self.game_over:
            button_rect = pygame.Rect(WINDOW_WIDTH - 150, WINDOW_HEIGHT - 60, 120, 40)
            pygame.draw.rect(self.screen, LIGHT_BLUE, button_rect)
            pygame.draw.rect(self.screen, BLACK, button_rect, 2)
            
            button_text = self.font.render("投骰子", True, BLACK)
            text_rect = button_text.get_rect(center=button_rect.center)
            self.screen.blit(button_text, text_rect)
            
            return button_rect
          # 游戏结束时显示重新开始按钮
        if self.game_over:
            button_rect = pygame.Rect(WINDOW_WIDTH - 150, WINDOW_HEIGHT - 60, 120, 40)
            pygame.draw.rect(self.screen, GREEN, button_rect)
            pygame.draw.rect(self.screen, BLACK, button_rect, 2)
            
            button_text = self.font.render("重新开始", True, BLACK)
            text_rect = button_text.get_rect(center=button_rect.center)
            self.screen.blit(button_text, text_rect)
            
            return button_rect
        
        return None
    
    def restart_game(self):
        """重新开始游戏"""
        self.__init__()
    
    def run(self):
        """运行游戏主循环"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    button_rect = self.draw_ui()
                    if button_rect and button_rect.collidepoint(event.pos):
                        if self.game_over:
                            self.restart_game()
                        elif not self.players[self.current_player].is_ai and not self.dice_rolling and not self.player_moving and not self.effect_dice_rolling:
                            # 玩家投骰子 - 开始骰子动画（只有在没有其他动画进行时才允许）
                            self.dice_rolling = True
                            self.dice_roll_frame = 0
                            
                    elif self.waiting_for_click and self.players[self.current_player].is_ai and not self.dice_rolling and not self.player_moving and not self.effect_dice_rolling:
                        # AI回合，玩家点击继续 - 开始骰子动画（只有在没有其他动画进行时才允许）
                        self.dice_rolling = True
                        self.dice_roll_frame = 0
            
            # 更新动画
            if self.dice_rolling:
                if self.animate_dice_roll():
                    # 骰子动画完成，执行移动
                    dice = self.roll_dice()
                    self.dice_result = dice
                    player = self.players[self.current_player]
                    
                    # 开始玩家移动动画
                    start_pos = self.cell_positions[player.position]
                    player.move(dice)
                    end_pos = self.cell_positions[player.position]
                    self.start_player_move_animation(self.current_player, start_pos, end_pos)
            
            if self.player_moving:
                if self.update_player_move_animation():
                    # 移动动画完成，添加短暂停顿
                    pygame.time.wait(300)  # 停顿300毫秒让玩家观察到达位置
                    
                    # 处理格子效果
                    player = self.players[self.current_player]
                    self.handle_cell_effect(player)
                    if self.waiting_for_click:
                        self.waiting_for_click = False
                    
                    # 如果不是奖励或惩罚格子，直接进入下一回合
                    cell = self.board[player.position]
                    if cell.type not in ['reward', 'penalty']:
                        self.next_turn()
            
            # 处理格子效果骰子动画
            if self.effect_dice_rolling:
                if self.animate_effect_dice_roll():
                    # 格子效果完成，进入下一回合
                    self.next_turn()
            
            # 绘制游戏
            self.draw_board()
            self.draw_ui()
            
            # 绘制骰子动画
            self.draw_dice_animation()
            
            # 绘制带动画的玩家
            self.draw_animated_players()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()
    
    def draw_dice_animation(self):
        """绘制骰子动画"""
        if self.dice_rolling:
            # 在屏幕中央显示滚动的骰子 - 移动骰子
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            
            # 随机显示不同的骰子面来模拟滚动
            current_dice = random.randint(0, 5)
            self.screen.blit(self.dice_surfaces[current_dice], (dice_x, dice_y))
            
            # 显示提示文字
            text = self.font.render("投骰子移动！", True, BLACK)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
            self.screen.blit(text, text_rect)
            
        elif self.effect_dice_rolling:
            # 显示格子效果骰子动画
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            
            # 随机显示不同的骰子面来模拟滚动
            current_dice = random.randint(0, 5)
            self.screen.blit(self.dice_surfaces[current_dice], (dice_x, dice_y))
            
            # 显示不同的提示文字
            if self.effect_type == 'reward':
                text = self.font.render("投骰子获得金币！", True, DARK_GREEN)
            else:
                text = self.font.render("投骰子失去金币！", True, DARK_RED)
            text_rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 60))
            self.screen.blit(text, text_rect)
            
        elif self.dice_result > 0:
            # 显示最终的骰子结果
            dice_x = WINDOW_WIDTH // 2 - 20
            dice_y = WINDOW_HEIGHT // 2 - 20
            self.screen.blit(self.dice_surfaces[self.dice_result - 1], (dice_x, dice_y))

    def draw_animated_players(self):
        """绘制带动画的玩家"""
        for i, player in enumerate(self.players):
            # 获取玩家当前位置（可能是动画中的位置）
            if self.player_moving and self.moving_player_id == i:
                pos_x, pos_y = self.get_animated_player_position(i)
            else:
                pos_x, pos_y = self.cell_positions[player.position]
            
            # 为了避免玩家重叠，稍微偏移位置
            offset_x = (i % 2) * 15 - 7
            offset_y = (i // 2) * 15 - 7
            
            # 如果是移动中的玩家，添加发光效果
            if self.player_moving and self.moving_player_id == i:                # 绘制发光效果
                pygame.draw.circle(self.screen, GOLD, 
                                 (pos_x + offset_x, pos_y + offset_y), 12, 2)
            
            pygame.draw.circle(self.screen, player.color, 
                             (pos_x + offset_x, pos_y + offset_y), 8)
            pygame.draw.circle(self.screen, BLACK, 
                             (pos_x + offset_x, pos_y + offset_y), 8, 2)

    def animate_effect_dice_roll(self):
        """格子效果骰子滚动动画"""
        if self.effect_dice_rolling:
            self.effect_dice_frame += 1
            if self.effect_dice_frame >= DICE_ANIMATION_FRAMES:
                self.effect_dice_rolling = False
                self.effect_dice_frame = 0
                  # 执行具体的格子效果
                dice_result = self.roll_dice()
                if self.effect_type == 'reward':
                    self.effect_player.add_money(dice_result)
                    self.message = f"玩家{self.effect_player.id + 1}获得{dice_result}金币！"
                elif self.effect_type == 'penalty':
                    self.effect_player.lose_money(dice_result)
                    self.message = f"玩家{self.effect_player.id + 1}失去{dice_result}金币！"
                
                # 增加更长的暂停时间让玩家看到效果
                pygame.time.wait(1200)  # 暂停1200毫秒（1.2秒）
                return True  # 动画完成
        return False
    
    def draw_effect_dice_animation(self):
        """绘制格子效果骰子动画"""
        if self.effect_dice_rolling:
            # 在玩家位置附近显示滚动的骰子
            player = self.effect_player
            pos_x, pos_y = self.cell_positions[player.position]
            
            # 随机显示不同的骰子面来模拟滚动
            current_dice = random.randint(0, 5)
            self.screen.blit(self.dice_surfaces[current_dice], (pos_x - 20, pos_y - 20))
        elif self.effect_type == 'reward' and self.effect_player:
            # 显示奖励骰子的最终结果
            player = self.effect_player
            pos_x, pos_y = self.cell_positions[player.position]
            self.screen.blit(self.dice_surfaces[self.dice_result - 1], (pos_x - 20, pos_y - 20))
        elif self.effect_type == 'penalty' and self.effect_player:
            # 显示惩罚骰子的最终结果
            player = self.effect_player
            pos_x, pos_y = self.cell_positions[player.position]
            self.screen.blit(self.dice_surfaces[self.dice_result - 1], (pos_x - 20, pos_y - 20))


# 启动游戏
if __name__ == "__main__":
    game = MonopolyGame()
    game.run()
