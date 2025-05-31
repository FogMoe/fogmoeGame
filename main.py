"""
简易大富翁游戏
使用模块化设计，分离关注点
"""

import pygame
import sys
import subprocess
import threading
import time
import webbrowser

from models.constants import (WINDOW_WIDTH, WINDOW_HEIGHT, GAME_STATE_START, 
                            GAME_STATE_PLAYING, GAME_STATE_RESULTS, GAME_STATE_LOBBY,
                            WHITE, BLACK, GREEN, LIGHT_BLUE, RED, WINNING_MONEY, GOLD, GRAY, GAME_VERSION)
from game.board import Board
from game.game_logic import GameLogic
from game.network_game_logic import NetworkGameLogic
from ui.renderer import Renderer
from ui.animations import AnimationManager
from network.client import GameClient
from network.protocol import MessageType

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
        
        # 网络相关
        self.network_client = None
        self.is_online_game = False
        self.is_host = False
        self.room_state = "menu"  # menu, hosting, joining, waiting, playing
        self.input_text = ""
        self.input_active = False
        
        # 错误消息显示
        self.error_message = ""
        self.error_message_time = 0
        self.error_message_duration = 3000  # 显示3秒
        
        # 设置菜单相关
        self.show_settings = False
        self.settings_button_rect = pygame.Rect(WINDOW_WIDTH - 50, 10, 40, 40)
        
        # 服务器进程管理
        self.server_process = None
    
    def init_game_components(self):
        """初始化游戏组件"""
        self.board = Board()
        # 根据是否是联机游戏创建不同的游戏逻辑
        if self.is_online_game and self.network_client:
            self.game_logic = NetworkGameLogic(self.network_client, self.network_client.player_slot)
        else:
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
                self.cleanup()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 检查设置按钮
                if self.settings_button_rect.collidepoint(event.pos):
                    self.show_settings = not self.show_settings
                elif self.show_settings:
                    # 如果设置菜单打开，检查是否点击在菜单内
                    menu_width = 400
                    menu_height = 380
                    menu_rect = pygame.Rect(WINDOW_WIDTH//2 - menu_width//2, 160, menu_width, menu_height)
                    
                    if menu_rect.collidepoint(event.pos):
                        # 点击在菜单内，处理菜单点击
                        self.handle_settings_click(event.pos)
                    else:
                        # 点击在菜单外，关闭菜单
                        self.show_settings = False
                elif self.game_state == GAME_STATE_START:
                    self.handle_start_screen_click(event.pos)
                elif self.game_state == GAME_STATE_LOBBY:
                    self.handle_lobby_click(event.pos)
                elif self.game_state == GAME_STATE_PLAYING:
                    self.handle_game_click(event.pos)
                elif self.game_state == GAME_STATE_RESULTS:
                    self.handle_results_click(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                if self.game_state == GAME_STATE_LOBBY and self.input_active:
                    self.handle_text_input(event)
    
    def handle_start_screen_click(self, pos):
        """处理开始界面的点击"""
        # 单人游戏按钮
        y_pos = 200 + 6 * 35 + 50
        single_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_pos, 200, 60)
        if single_button.collidepoint(pos):
            self.start_new_game()
        
        # 联机游戏按钮
        online_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_pos + 80, 200, 60)
        if online_button.collidepoint(pos):
            self.game_state = GAME_STATE_LOBBY
            self.room_state = "menu"
    
    def handle_results_click(self, pos):
        """处理结果界面的点击"""
        # 返回主菜单按钮
        back_button = pygame.Rect(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT - 100, 200, 50)
        if back_button.collidepoint(pos):
            self.game_state = GAME_STATE_START
    
    def handle_lobby_click(self, pos):
        """处理联机大厅的点击"""
        if self.room_state == "menu":
            # 创建房间按钮
            host_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 300, 200, 60)
            if host_button.collidepoint(pos):
                self.room_state = "hosting"
                self.start_hosting()
            
            # 加入房间按钮
            join_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 380, 200, 60)
            if join_button.collidepoint(pos):
                self.room_state = "joining"
                self.input_active = True
                self.input_text = ""
        
        elif self.room_state == "joining":
            # IP输入框
            input_box = pygame.Rect(WINDOW_WIDTH//2 - 150, 300, 300, 40)
            if input_box.collidepoint(pos):
                self.input_active = True
            else:
                self.input_active = False
            
            # 连接按钮
            connect_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 360, 200, 60)
            if connect_button.collidepoint(pos) and self.input_text:
                self.connect_to_host(self.input_text)
        
        elif self.room_state == "waiting":
            # 开始游戏按钮（仅房主）
            if self.is_host:
                start_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 500, 200, 60)
                if start_button.collidepoint(pos):
                    self.start_online_game()
        
        # 返回按钮（所有状态都有）
        back_button = pygame.Rect(50, 50, 100, 40)
        if back_button.collidepoint(pos):
            self.leave_lobby()
    
    def handle_text_input(self, event):
        """处理文本输入"""
        if event.key == pygame.K_RETURN:
            if self.input_text:
                self.connect_to_host(self.input_text)
        elif event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
        else:
            # 只接受数字和点号
            if event.unicode in '0123456789.':
                self.input_text += event.unicode
    
    def cleanup(self):
        """清理资源"""
        # 断开网络连接
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
        
        # 停止服务器进程
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except:
                try:
                    self.server_process.kill()
                except:
                    pass
            self.server_process = None
    
    def handle_settings_click(self, pos):
        """处理设置菜单的点击"""
        if self.game_state == GAME_STATE_PLAYING:
            # 游戏中的设置选项
            quit_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 260, 200, 50)
            update_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 320, 200, 50)
            close_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 380, 200, 50)
            
            if quit_button.collidepoint(pos):
                self.game_state = GAME_STATE_START
                self.show_settings = False
                # 清理游戏资源
                if self.network_client:
                    self.network_client.disconnect()
                    self.network_client = None
            elif update_button.collidepoint(pos):
                # 打开GitHub仓库页面
                webbrowser.open("https://github.com/FogMoe/fogmoeGame")
                self.show_settings = False
            elif close_button.collidepoint(pos):
                # 关闭游戏
                self.running = False
                self.cleanup()
        else:
            # 游戏外的设置选项
            update_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 260, 200, 50)
            close_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 320, 200, 50)
            
            if update_button.collidepoint(pos):
                # 打开GitHub仓库页面
                webbrowser.open("https://github.com/FogMoe/fogmoeGame")
                self.show_settings = False
            elif close_button.collidepoint(pos):
                # 关闭游戏
                self.running = False
                self.cleanup()
    
    def start_new_game(self):
        """开始新游戏"""
        self.game_state = GAME_STATE_PLAYING
        self.is_online_game = False
        self.init_game_components()
    
    def start_hosting(self):
        """开始托管游戏"""
        # 创建网络客户端
        self.network_client = GameClient()
        
        # 获取本机IP地址
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except:
            local_ip = "localhost"
        
        # 连接到服务器（假设服务器已经在运行）
        if self.network_client.connect(local_ip, 29188):
            self.network_client.join_room("主机玩家", GAME_VERSION)
            self.is_host = True
            self.room_state = "waiting"
            
            # 注册网络消息处理器
            self.setup_network_handlers()
        else:
            # 如果连接失败，尝试启动服务器
            self.network_client = None
            self.show_error_message("正在启动服务器...")
            
            # 启动服务器进程
            if self.start_server():
                # 等待服务器启动
                time.sleep(1)  # 给服务器一点启动时间
                
                # 再次尝试连接
                self.network_client = GameClient()
                if self.network_client.connect(local_ip, 29188):
                    self.network_client.join_room("主机玩家", GAME_VERSION)
                    self.is_host = True
                    self.room_state = "waiting"
                    
                    # 注册网络消息处理器
                    self.setup_network_handlers()
                else:
                    self.room_state = "menu"
                    self.network_client = None
                    self.show_error_message("无法连接到服务器！")
            else:
                self.room_state = "menu"
                self.show_error_message("无法启动服务器！")
    
    def connect_to_host(self, ip_address):
        """连接到主机"""
        self.network_client = GameClient()
        
        # 尝试连接
        if self.network_client.connect(ip_address, 29188):
            self.network_client.join_room("客户端玩家", GAME_VERSION)
            self.is_host = False
            self.room_state = "waiting"
            
            # 注册网络消息处理器
            self.setup_network_handlers()
        else:
            self.room_state = "joining"
            self.network_client = None
            self.show_error_message(f"无法连接到 {ip_address}:29188")
    
    def setup_network_handlers(self):
        """设置网络消息处理器"""
        if self.network_client:
            self.network_client.register_handler(MessageType.GAME_STARTED, self.handle_game_started)
            self.network_client.register_handler(MessageType.DICE_ROLL, self.handle_network_dice_roll)
            self.network_client.register_handler(MessageType.EFFECT_DICE_ROLL, self.handle_network_effect_dice)
            self.network_client.register_handler(MessageType.GAME_STATE, self.handle_game_state_update)
            self.network_client.register_handler(MessageType.JOIN_FAILED, self.handle_join_failed)
            self.network_client.register_handler(MessageType.AI_TAKEOVER, self.handle_ai_takeover)
    
    def handle_join_failed(self, data):
        """处理加入失败消息"""
        reason = data.get('reason', '未知原因')
        self.show_error_message(f"加入房间失败: {reason}")
        self.room_state = "menu"
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
    
    def start_online_game(self):
        """开始联机游戏（房主）"""
        if self.is_host and self.network_client:
            self.network_client.start_game()
    
    def handle_game_started(self, data):
        """处理游戏开始消息"""
        self.game_state = GAME_STATE_PLAYING
        self.is_online_game = True
        self.init_game_components()
        
        # 根据网络玩家信息初始化游戏
        if self.network_client and self.game_logic:
            # 设置网络玩家
            if isinstance(self.game_logic, NetworkGameLogic):
                self.game_logic.setup_network_players(data['players'])
    
    def handle_network_dice_roll(self, data):
        """处理网络骰子投掷"""
        if self.game_logic:
            # 获取投掷骰子的玩家槽位
            player_slot = data.get('player_slot')
            
            if player_slot is not None and player_slot == self.game_logic.current_player:
                # 更新骰子结果
                self.game_logic.dice_result = data['dice_result']
                
                # 执行移动动画
                current_player = self.game_logic.get_current_player()
                start_position = current_player.position
                current_player.move(self.game_logic.dice_result)
                end_position = current_player.position
                
                # 开始移动动画
                if self.animation_manager:
                    self.animation_manager.start_player_move_animation(
                        self.game_logic.current_player, start_position, end_position, self.game_logic.dice_result)
    
    def handle_network_effect_dice(self, data):
        """处理网络效果骰子"""
        if self.game_logic:
            # 获取投掷骰子的玩家槽位
            player_slot = data.get('player_slot')
            
            if player_slot is not None and player_slot == self.game_logic.current_player:
                # 更新效果骰子结果
                self.game_logic.effect_dice_result = data['effect_result']
                
                # 执行效果
                result_message = self.game_logic.execute_effect(self.game_logic.effect_type, self.game_logic.get_current_player())
                if result_message:
                    self.game_logic.message = result_message
                
                # 清除效果状态
                self.game_logic.waiting_for_effect_dice = False
                self.game_logic.effect_type = ""
                
                # 设置延迟后进入下一回合
                self.start_wait('effect_completed', 1500, self.complete_effect_dice_roll)
    
    def handle_game_state_update(self, data):
        """处理游戏状态更新"""
        # 同步游戏状态
        pass
    
    def handle_ai_takeover(self, data):
        """处理AI接管通知"""
        player_slot = data.get('player_slot')
        player_name = data.get('player_name', f'玩家{player_slot + 1}')
        
        # 显示消息
        self.show_error_message(f"{player_name} 已断线，由AI接管")
        
        # 如果游戏正在进行，更新玩家状态
        if self.game_logic and hasattr(self.game_logic, 'players'):
            for player in self.game_logic.players:
                if player.id == player_slot:
                    player.is_ai = True
                    player.name = f"AI{player_slot + 1}"
                    break
    
    def leave_lobby(self):
        """离开大厅"""
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
        
        self.game_state = GAME_STATE_START
        self.room_state = "menu"
        self.is_host = False
    
    def start_server(self):
        """启动游戏服务器"""
        try:
            # 使用subprocess启动服务器进程
            self.server_process = subprocess.Popen(
                [sys.executable, "start_server.py"],
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            return True
        except Exception as e:
            print(f"启动服务器失败: {e}")
            return False
    
    def show_error_message(self, message):
        """显示错误消息"""
        self.error_message = message
        self.error_message_time = pygame.time.get_ticks()
    
    def update_error_message(self):
        """更新错误消息显示状态"""
        if self.error_message and pygame.time.get_ticks() - self.error_message_time > self.error_message_duration:
            self.error_message = ""
    
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
            # 首先检查是否可以进行操作（联机游戏时检查是否是本地玩家回合）
            can_act = True
            if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
                can_act = self.game_logic.is_local_player_turn()
            else:
                # 单人游戏时，检查是否是真人玩家回合
                current_player = self.game_logic.get_current_player()
                can_act = not current_player.is_ai
            
            # 只有在可以操作时才处理点击
            if not can_act:
                return
            
            if hasattr(self.game_logic, 'is_game_over') and self.game_logic.is_game_over():
                # 游戏结束，显示结果
                self.end_game_with_results()
            elif hasattr(self.game_logic, 'waiting_for_effect_dice') and self.game_logic.waiting_for_effect_dice:
                # 投掷效果骰子
                self.handle_effect_dice_roll()
            elif (hasattr(self.animation_manager, 'is_any_animation_running') and 
                  not self.animation_manager.is_any_animation_running() and not self.waiting_state):
                # 开始玩家回合
                self.start_player_turn()
    
    def handle_effect_dice_roll(self):
        """处理真实玩家的效果骰子投掷"""
        if not self.game_logic:
            return
        # 联机游戏时，检查是否是本地玩家的回合
        if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
            if not self.game_logic.can_current_player_roll():
                return
        
        result_message = self.game_logic.roll_effect_dice()
        if result_message:
            self.game_logic.message = result_message
        
        # 如果是联机游戏，发送效果骰子结果
        if self.is_online_game and self.network_client:
            current_player = self.game_logic.get_current_player()
            if not current_player.is_ai:
                self.network_client.send_effect_dice_roll(self.game_logic.effect_dice_result)
        
        # 如果是联机游戏的AI，房主也要发送效果骰子结果
        if (self.is_online_game and self.network_client and current_player.is_ai and 
            isinstance(self.game_logic, NetworkGameLogic) and self.game_logic.is_host()):
            self.network_client.send_effect_dice_roll(self.game_logic.effect_dice_result)
        
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
        
        # 如果是联机游戏的AI，房主发送效果骰子结果
        if (self.is_online_game and self.network_client and 
            isinstance(self.game_logic, NetworkGameLogic) and self.game_logic.is_host()):
            self.network_client.send_effect_dice_roll(self.game_logic.effect_dice_result)
        
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
            
            # 联机游戏时，只有房主才执行AI操作
            if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
                if not self.game_logic.should_ai_act_locally():
                    return
            
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
        
        # 如果是联机游戏，发送骰子结果
        if self.is_online_game and self.network_client and not current_player.is_ai:
            self.network_client.send_dice_roll(dice)
        
        # 如果是联机游戏的AI，房主也要发送骰子结果
        if (self.is_online_game and self.network_client and current_player.is_ai and 
            isinstance(self.game_logic, NetworkGameLogic) and self.game_logic.is_host()):
            self.network_client.send_dice_roll(dice)
        
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
        elif self.game_state == GAME_STATE_LOBBY:
            self.draw_lobby_screen()
        elif self.game_state == GAME_STATE_PLAYING:
            self.draw_game_screen()
        elif self.game_state == GAME_STATE_RESULTS:
            self.draw_results_screen()
        
        # 绘制设置按钮（齿轮图标）
        pygame.draw.rect(self.screen, GRAY, self.settings_button_rect)
        pygame.draw.rect(self.screen, BLACK, self.settings_button_rect, 2)
        # 简化的齿轮图标（使用字符）
        gear_text = self.font.render("⚙", True, WHITE)
        gear_rect = gear_text.get_rect(center=self.settings_button_rect.center)
        self.screen.blit(gear_text, gear_rect)
        
        # 绘制设置菜单
        if self.show_settings:
            self.draw_settings_menu()
        
        # 绘制错误消息（如果有）
        if self.error_message:
            # 背景框
            error_bg = pygame.Surface((600, 50))
            error_bg.fill(RED)
            error_bg_rect = error_bg.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT - 100))
            self.screen.blit(error_bg, error_bg_rect)
            
            # 错误文本
            error_text = self.font.render(self.error_message, True, WHITE)
            error_rect = error_text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT - 100))
            self.screen.blit(error_text, error_rect)
        
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
        
        # 单人游戏按钮
        single_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_offset + 50, 200, 60)
        pygame.draw.rect(self.screen, GREEN, single_button)
        pygame.draw.rect(self.screen, BLACK, single_button, 3)
        
        button_text = self.font.render("单人游戏", True, BLACK)
        button_rect = button_text.get_rect(center=single_button.center)
        self.screen.blit(button_text, button_rect)
        
        # 联机游戏按钮
        online_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_offset + 130, 200, 60)
        pygame.draw.rect(self.screen, LIGHT_BLUE, online_button)
        pygame.draw.rect(self.screen, BLACK, online_button, 3)
        
        online_text = self.font.render("联机游戏", True, BLACK)
        online_rect = online_text.get_rect(center=online_button.center)
        self.screen.blit(online_text, online_rect)
    
    def draw_lobby_screen(self):
        """绘制联机大厅界面"""
        # 返回按钮
        back_button = pygame.Rect(50, 50, 100, 40)
        pygame.draw.rect(self.screen, GRAY, back_button)
        pygame.draw.rect(self.screen, BLACK, back_button, 2)
        back_text = self.small_font.render("返回", True, BLACK)
        back_rect = back_text.get_rect(center=back_button.center)
        self.screen.blit(back_text, back_rect)
        
        if self.room_state == "menu":
            # 标题
            title = self.big_font.render("联机游戏", True, BLACK)
            title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 150))
            self.screen.blit(title, title_rect)
            
            # 创建房间按钮
            host_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 300, 200, 60)
            pygame.draw.rect(self.screen, GREEN, host_button)
            pygame.draw.rect(self.screen, BLACK, host_button, 3)
            host_text = self.font.render("创建房间", True, BLACK)
            host_rect = host_text.get_rect(center=host_button.center)
            self.screen.blit(host_text, host_rect)
            
            # 加入房间按钮
            join_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 380, 200, 60)
            pygame.draw.rect(self.screen, LIGHT_BLUE, join_button)
            pygame.draw.rect(self.screen, BLACK, join_button, 3)
            join_text = self.font.render("加入房间", True, BLACK)
            join_rect = join_text.get_rect(center=join_button.center)
            self.screen.blit(join_text, join_rect)
        
        elif self.room_state == "joining":
            # 标题
            title = self.font.render("输入主机IP地址", True, BLACK)
            title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 250))
            self.screen.blit(title, title_rect)
            
            # IP输入框
            input_box = pygame.Rect(WINDOW_WIDTH//2 - 150, 300, 300, 40)
            color = RED if self.input_active else BLACK
            pygame.draw.rect(self.screen, WHITE, input_box)
            pygame.draw.rect(self.screen, color, input_box, 2)
            
            # 显示输入的文本
            text_surface = self.font.render(self.input_text, True, BLACK)
            self.screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))
            
            # 连接按钮
            connect_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 360, 200, 60)
            pygame.draw.rect(self.screen, GREEN, connect_button)
            pygame.draw.rect(self.screen, BLACK, connect_button, 3)
            connect_text = self.font.render("连接", True, BLACK)
            connect_rect = connect_text.get_rect(center=connect_button.center)
            self.screen.blit(connect_text, connect_rect)
        
        elif self.room_state == "waiting":
            # 标题
            title = self.big_font.render("等待玩家加入", True, BLACK)
            title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 150))
            self.screen.blit(title, title_rect)
            
            # 显示房间玩家
            y_offset = 250
            if self.network_client:
                for i, player_info in enumerate(self.network_client.room_players):
                    player_text = f"玩家{i+1}: {player_info['name']}"
                    if player_info.get('is_host'):
                        player_text += " (房主)"
                    text = self.font.render(player_text, True, BLACK)
                    self.screen.blit(text, (WINDOW_WIDTH//2 - 100, y_offset))
                    y_offset += 40
                
                # 显示空位
                for i in range(len(self.network_client.room_players), 4):
                    text = self.font.render(f"玩家{i+1}: 等待加入...", True, GRAY)
                    self.screen.blit(text, (WINDOW_WIDTH//2 - 100, y_offset))
                    y_offset += 40
            
            # 开始游戏按钮（仅房主）
            if self.is_host:
                start_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 500, 200, 60)
                pygame.draw.rect(self.screen, GREEN, start_button)
                pygame.draw.rect(self.screen, BLACK, start_button, 3)
                start_text = self.font.render("开始游戏", True, BLACK)
                start_rect = start_text.get_rect(center=start_button.center)
                self.screen.blit(start_text, start_rect)
    
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
    
    def draw_settings_menu(self):
        """绘制设置菜单"""
        # 半透明背景
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        
        # 菜单背景
        menu_width = 400
        menu_height = 380  # 增加高度以容纳更多内容
        menu_rect = pygame.Rect(WINDOW_WIDTH//2 - menu_width//2, 160, menu_width, menu_height)
        pygame.draw.rect(self.screen, WHITE, menu_rect)
        pygame.draw.rect(self.screen, BLACK, menu_rect, 3)
        
        # 标题
        title_text = self.font.render("设置", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH//2, 190))
        self.screen.blit(title_text, title_rect)
        
        # 版本号
        version_text = self.small_font.render(f"版本: v{GAME_VERSION}", True, GRAY)
        version_rect = version_text.get_rect(center=(WINDOW_WIDTH//2, 220))
        self.screen.blit(version_text, version_rect)
        
        if self.game_state == GAME_STATE_PLAYING:
            # 游戏中的选项
            # 退出当局游戏按钮
            quit_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 260, 200, 50)
            pygame.draw.rect(self.screen, RED, quit_button)
            pygame.draw.rect(self.screen, BLACK, quit_button, 2)
            quit_text = self.font.render("退出当局游戏", True, WHITE)
            quit_rect = quit_text.get_rect(center=quit_button.center)
            self.screen.blit(quit_text, quit_rect)
            
            # 检查更新按钮
            update_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 320, 200, 50)
            pygame.draw.rect(self.screen, GREEN, update_button)
            pygame.draw.rect(self.screen, BLACK, update_button, 2)
            update_text = self.font.render("检查更新", True, BLACK)
            update_rect = update_text.get_rect(center=update_button.center)
            self.screen.blit(update_text, update_rect)
        else:
            # 游戏外的选项
            # 检查更新按钮
            update_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 260, 200, 50)
            pygame.draw.rect(self.screen, GREEN, update_button)
            pygame.draw.rect(self.screen, BLACK, update_button, 2)
            update_text = self.font.render("检查更新", True, BLACK)
            update_rect = update_text.get_rect(center=update_button.center)
            self.screen.blit(update_text, update_rect)
        
        # 关闭游戏按钮（所有情况都显示）
        close_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 
                                 320 if self.game_state != GAME_STATE_PLAYING else 380, 
                                 200, 50)
        pygame.draw.rect(self.screen, BLACK, close_button)
        pygame.draw.rect(self.screen, WHITE, close_button, 2)
        close_text = self.font.render("关闭游戏", True, WHITE)
        close_rect = close_text.get_rect(center=close_button.center)
        self.screen.blit(close_text, close_rect)
        
        # 提示文本
        hint_text = self.small_font.render("点击外部区域关闭", True, GRAY)
        hint_rect = hint_text.get_rect(center=(WINDOW_WIDTH//2, 460))
        self.screen.blit(hint_text, hint_rect)
    
    def run(self):
        """运行游戏主循环"""
        while self.running:
            # 处理事件
            self.handle_events()
            
            # 更新错误消息状态
            self.update_error_message()
            
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
        
        # 清理资源
        self.cleanup()
        
        # 退出游戏
        pygame.quit()
        sys.exit()

def main():
    """主函数"""
    game = MonopolyGame()
    game.run()

if __name__ == "__main__":
    main() 