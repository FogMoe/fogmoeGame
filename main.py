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
from typing import Optional, Callable, List, Dict

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
from utils.config_manager import config_manager

class MonopolyGame:
    """大富翁游戏主类"""
    
    def __init__(self):
        """初始化游戏"""
        pygame.init()
        
        # 游戏窗口设置
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("雾萌")
        
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
        self.clock = pygame.time.Clock()
        self.running = True
        
        # 游戏组件
        self.game_logic: Optional[GameLogic] = None
        self.board: Optional[Board] = None
        self.renderer = None
        self.animation_manager = None
        
        # 设置菜单相关
        self.show_settings = False
        self.settings_button_rect = pygame.Rect(WINDOW_WIDTH - 60, 10, 50, 50)
        
        # 昵称输入相关
        self.show_nickname_input = False
        self.nickname_input_text = config_manager.get_nickname()
        self.nickname_input_active = False
        self.nickname_error_message = ""
        
        # 联机游戏相关
        self.room_state = "menu"  # "menu", "hosting", "joining", "waiting"
        self.network_client: Optional[GameClient] = None
        self.is_host = False
        self.input_active = False
        self.input_text = ""
        self.is_online_game = False
        self.server_process = None
        
        # 连接重试相关
        self.connecting_to_server = False
        self.connection_cancelled = False
        
        # 等待状态相关
        self.waiting_state = None
        self.wait_start_time = 0
        self.wait_duration = 0
        self.pending_action = None
        
        # 错误消息相关
        self.error_message = ""
        self.error_message_time = 0
        self.error_message_duration = 3000  # 3秒显示错误消息
        
        # 游戏结果
        self.game_results = []
    
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
            
        # 如果是联机游戏，设置AI回合回调函数
        if self.is_online_game and self.network_client:
            self.network_client.ai_turn_callback = self.handle_ai_network_turn

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
                elif self.show_nickname_input:
                    # 如果昵称输入界面打开
                    self.handle_nickname_input_click(event.pos)
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
                elif self.show_nickname_input and self.nickname_input_active:
                    self.handle_nickname_text_input(event)
    
    def handle_start_screen_click(self, pos):
        """处理开始界面的点击"""
        # 计算按钮位置（与绘制逻辑保持一致）
        y_offset = 120 + 6 * 35  # 游戏说明起始位置 + 6行说明
        
        # 单人游戏按钮
        single_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_offset + 50, 200, 60)
        if single_button.collidepoint(pos):
            self.start_new_game()
        
        # 联机游戏按钮
        online_button = pygame.Rect(WINDOW_WIDTH//2 - 100, y_offset + 130, 200, 60)
        if online_button.collidepoint(pos):
            self.game_state = GAME_STATE_LOBBY
            self.room_state = "menu"
        
        # 昵称设置按钮（放在联机游戏按钮下面）
        nickname_button_y = y_offset + 210
        nickname_button = pygame.Rect(WINDOW_WIDTH//2 - 100, nickname_button_y, 200, 40)
        if nickname_button.collidepoint(pos):
            self.show_nickname_input = True
            self.nickname_input_active = True
            self.nickname_error_message = ""
            return
    
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
        
        elif self.room_state == "hosting":
            # 如果正在连接服务器，显示取消按钮
            if self.connecting_to_server:
                cancel_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 400, 200, 60)
                if cancel_button.collidepoint(pos):
                    self.cancel_server_connection()
        
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
    
    def handle_nickname_input_click(self, pos):
        """处理昵称输入界面的点击"""
        # 昵称输入框
        input_box = pygame.Rect(WINDOW_WIDTH//2 - 150, 250, 300, 40)
        if input_box.collidepoint(pos):
            self.nickname_input_active = True
        else:
            self.nickname_input_active = False
        
        # 确认按钮
        confirm_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 320, 80, 40)
        if confirm_button.collidepoint(pos):
            if config_manager.set_nickname(self.nickname_input_text):
                self.show_nickname_input = False
                self.nickname_error_message = ""
            else:
                self.nickname_error_message = "昵称格式错误（最多7个英文字符）"
        
        # 取消按钮
        cancel_button = pygame.Rect(WINDOW_WIDTH//2 + 20, 320, 80, 40)
        if cancel_button.collidepoint(pos):
            self.show_nickname_input = False
            self.nickname_input_text = config_manager.get_nickname()  # 恢复原来的昵称
            self.nickname_error_message = ""
    
    def handle_nickname_text_input(self, event):
        """处理昵称文本输入"""
        if event.key == pygame.K_RETURN:
            # 回车键确认
            if config_manager.set_nickname(self.nickname_input_text):
                self.show_nickname_input = False
                self.nickname_error_message = ""
            else:
                self.nickname_error_message = "昵称格式错误（最多7个英文字符）"
        elif event.key == pygame.K_ESCAPE:
            # ESC键取消
            self.show_nickname_input = False
            self.nickname_input_text = config_manager.get_nickname()
            self.nickname_error_message = ""
        elif event.key == pygame.K_BACKSPACE:
            self.nickname_input_text = self.nickname_input_text[:-1]
        else:
            # 只允许英文字符、数字、下划线、短横线
            if event.unicode in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-':
                if len(self.nickname_input_text) < 7:  # 限制长度
                    self.nickname_input_text += event.unicode
    
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
        # 如果已有客户端实例，先断开
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None

        # 创建网络客户端
        self.network_client = GameClient()
        
        # 获取本机IP地址
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 连接到一个公共DNS服务器以获取本机在局域网中的IP
            # 这不会真的发送数据，只是为了获取getsockname()
            s.connect(("8.8.8.8", 80)) 
            local_ip = s.getsockname()[0]
            s.close()
        except OSError: # 更具体的异常捕获
            local_ip = "localhost" # 备选方案
        except Exception as e: # 其他未知异常
            print(f"获取IP地址时发生错误: {e}")
            local_ip = "localhost"
        
        print(f"start_hosting: 本机IP识别为: {local_ip}")

        # 首先尝试直接连接（可能服务器已由其他方式启动或未正确关闭）
        if self.network_client.connect(local_ip, 29188):
            print("start_hosting: 直接连接服务器成功。")
            self.network_client.join_room(config_manager.get_nickname(), GAME_VERSION)
            self.is_host = True
            self.room_state = "waiting"
            self.setup_network_handlers()
        else:
            # 如果直接连接失败，则尝试启动服务器并连接
            print("start_hosting: 直接连接失败，尝试启动服务器...")
            if self.network_client: # 清理刚才连接失败的实例
                 self.network_client.disconnect()
            self.network_client = None # 确保完全清理

            self.show_error_message("正在启动服务器...")
            
            if self.start_server():
                print("start_hosting: 服务器进程已启动，开始尝试连接...")
                # 创建新的客户端实例用于连接到新启动的服务器
                if self.network_client: # 再次确保之前的实例已清理
                    self.network_client.disconnect()
                self.network_client = GameClient()
                self.attempt_server_connection(local_ip) # 使用新的实例去连接
            else:
                print("start_hosting: 启动服务器进程失败。")
                self.room_state = "menu"
                self.show_error_message("无法启动服务器！")
                if self.network_client: # 确保清理
                    self.network_client.disconnect()
                    self.network_client = None

    def attempt_server_connection(self, local_ip):
        """智能重试连接到服务器"""
        import threading
        
        # 设置连接状态
        self.connecting_to_server = True
        self.connection_cancelled = False
        
        # 确保在开始新的连接尝试前，旧的客户端实例（如果存在且是当前尝试的这个）被清理
        # 注意：这里的 self.network_client 应该是 start_hosting 中新创建的那个
        # 但作为保险，如果它意外地是其他的，或者 start_hosting 中没有正确创建，则这里重新创建
        if not self.network_client or not isinstance(self.network_client, GameClient):
            print("attempt_server_connection: network_client 无效，重新创建。")
            if self.network_client: # 如果存在但类型不对，尝试断开
                try:
                    self.network_client.disconnect()
                except: pass # 忽略可能的错误
            self.network_client = GameClient()
            
        # 持有 connection_thread 将要使用的客户端实例引用
        # 防止 self.network_client 在 MonopolyGame 主类中被意外修改
        # 虽然目前代码逻辑里不会，但这是更安全的方式
        client_for_this_connection_attempt = self.network_client

        def connection_thread():
            max_attempts = 15
            attempt_interval = 0.5 
            
            print(f"attempt_server_connection: 开始连接线程 (最多 {max_attempts} 次尝试)")

            for attempt in range(max_attempts):
                if self.connection_cancelled:
                    print("attempt_server_connection: 连接被用户取消。")
                    self.connecting_to_server = False
                    # 如果是因为取消而失败，确保client_for_this_connection_attempt被清理
                    if client_for_this_connection_attempt:
                        client_for_this_connection_attempt.disconnect()
                    # 如果此线程中使用的客户端实例正是 self.network_client，则也清空它
                    if self.network_client == client_for_this_connection_attempt:
                        self.network_client = None 
                    return
                
                progress_msg = f"正在连接服务器... ({attempt + 1}/{max_attempts})"
                self.show_error_message(progress_msg)
                
                # 每次循环都检查端口，因为服务器可能需要时间启动
                if self.check_server_port(local_ip, 29188):
                    print(f"attempt_server_connection (尝试 {attempt+1}): 端口 {local_ip}:29188 可用，尝试连接...")
                    # 再次检查是否已取消
                    if self.connection_cancelled:
                        # ... (处理同上)
                        print("attempt_server_connection: 连接在端口检查后被用户取消。")
                        self.connecting_to_server = False
                        if client_for_this_connection_attempt:
                            client_for_this_connection_attempt.disconnect()
                        if self.network_client == client_for_this_connection_attempt:
                             self.network_client = None
                        return
                    
                    # 使用为此连接尝试保留的客户端实例
                    if client_for_this_connection_attempt.connect(local_ip, 29188):
                        print(f"attempt_server_connection (尝试 {attempt+1}): 连接成功！")
                        # 只有成功连接后，才把这个client实例正式赋值给self.network_client
                        # (虽然在当前逻辑下它们应该是同一个对象，但这样做更明确)
                        self.network_client = client_for_this_connection_attempt
                        self.network_client.join_room(config_manager.get_nickname(), GAME_VERSION)
                        self.is_host = True
                        self.room_state = "waiting"
                        self.connecting_to_server = False
                        self.setup_network_handlers()
                        self.error_message = "" # 清除连接进度消息
                        return
                    else:
                        print(f"attempt_server_connection (尝试 {attempt+1}): 连接失败，但端口可用。可能服务器仍在初始化。")
                        # 连接失败，此client_for_this_connection_attempt实例可能已损坏，
                        # 下次循环前理论上应该创建新的，但当前GameClient.connect已有内部清理。
                        # 为保险起见，确保它被断开，以便下次循环时connect方法会重新创建socket
                        client_for_this_connection_attempt.disconnect() 
                        # 然后为了下一次尝试，需要一个新的GameClient实例
                        # 但我们是在循环中，所以直接寄希望于下一次 connect 会处理好
                        # 或者，严格来说，这里应该创建一个新的 client_for_this_connection_attempt
                        # 但考虑到 GameClient.connect 现在会处理自己的socket，暂时不在此处重新创建
                        # 只需要确保它调用了 disconnect
                else:
                    print(f"attempt_server_connection (尝试 {attempt+1}): 端口 {local_ip}:29188 不可用。")
                
                # 等待一段时间后重试
                for _ in range(int(attempt_interval * 10)):
                    if self.connection_cancelled:
                        # ... (处理同上)
                        print("attempt_server_connection: 连接在等待间隔中被用户取消。")
                        self.connecting_to_server = False
                        if client_for_this_connection_attempt:
                            client_for_this_connection_attempt.disconnect()
                        if self.network_client == client_for_this_connection_attempt:
                            self.network_client = None
                        return
                    time.sleep(0.1)
            
            # 所有尝试都失败了
            print("attempt_server_connection: 所有连接尝试失败。")
            self.room_state = "menu"
            self.connecting_to_server = False
            if client_for_this_connection_attempt: # 清理最后一次尝试的客户端
                client_for_this_connection_attempt.disconnect()
            
            # 如果 self.network_client 指向的是这个失败的实例，也清空它
            if self.network_client == client_for_this_connection_attempt:
                self.network_client = None 

            if not self.connection_cancelled: # 只有在不是用户主动取消时才显示超时
                self.show_error_message("服务器启动超时，请重试")
            else:
                self.error_message = "" # 用户取消，清除进度消息
        
        thread = threading.Thread(target=connection_thread)
        thread.daemon = True
        thread.start()
    
    def check_server_port(self, host, port):
        """检查服务器端口是否可用"""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1秒超时
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def connect_to_host(self, ip_address):
        """连接到主机"""
        self.network_client = GameClient()
        
        # 尝试连接
        if self.network_client.connect(ip_address, 29188):
            self.network_client.join_room(config_manager.get_nickname(), GAME_VERSION)
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
                
                # 注意：移动完成后的处理会在动画完成时通过update_animations自动触发
    
    def handle_network_effect_dice(self, data):
        """处理网络效果骰子"""
        if self.game_logic:
            # 获取投掷骰子的玩家槽位
            player_slot = data.get('player_slot')
            
            if player_slot is not None and player_slot == self.game_logic.current_player:
                # 更新效果骰子结果
                self.game_logic.effect_dice_result = data['effect_result']
                
                # 执行效果
                current_player = self.game_logic.get_current_player()
                result_message = self.game_logic.execute_effect(self.game_logic.effect_type, current_player)
                if result_message:
                    self.game_logic.message = result_message
                
                # 清除效果状态
                self.game_logic.waiting_for_effect_dice = False
                self.game_logic.effect_type = ""
                
                # 设置延迟后进入下一回合
                # 如果是AI玩家，使用较长的延迟时间让玩家能看清楚
                delay = 2000 if current_player.is_ai else 1500
                self.start_wait('effect_completed', delay, self.complete_effect_dice_roll)
    
    def handle_game_state_update(self, data):
        """处理游戏状态更新"""
        # 同步游戏状态
        pass
    
    def handle_ai_takeover(self, data):
        """处理AI接管通知"""
        player_slot = data.get('player_slot')
        player_name = data.get('player_name', f'玩家{player_slot + 1}')
        
        print(f"\n[AI接管] 收到玩家 {player_name}(槽位:{player_slot}) 的AI接管通知")
        
        # 显示消息
        self.show_error_message(f"{player_name} 已断线，由AI接管")
        
        # 如果游戏正在进行，更新玩家状态
        if self.game_logic and hasattr(self.game_logic, 'players'):
            for player in self.game_logic.players:
                if player.id == player_slot:
                    print(f"[AI接管] 将玩家 {player.name}(槽位:{player.id}) 标记为AI控制")
                    player.is_ai = True
                    player.name = f"AI{player_slot + 1}"
                    
                    # 如果是当前回合的玩家，且是房主，则立即触发AI行动
                    current_player = self.game_logic.get_current_player()
                    if self.is_host and current_player.id == player_slot:
                        print(f"[AI接管] 当前是掉线玩家的回合，立即触发AI行动")
                        # 设置一个短暂延迟，确保状态更新后再执行AI行动
                        self.start_wait('ai_takeover', 500, lambda: self.handle_ai_network_turn(player_slot))
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
            # 检查是否有打包后的服务器程序
            import os
            
            # 尝试不同的服务器程序路径
            possible_server_paths = [
                "fogmoe_game_server.exe",  # 单文件版本
                "start_server.py",  # 开发版本
                os.path.join("fogmoe_game_server", "fogmoe_game_server.exe"),  # 目录版本
                os.path.join("..", "fogmoe_game_server.exe"),  # 相对路径
            ]
            
            server_cmd = None
            for path in possible_server_paths:
                if os.path.exists(path):
                    if path.endswith('.exe'):
                        server_cmd = [path]
                    else:
                        server_cmd = [sys.executable, path]
                    break
            
            if server_cmd is None:
                # 如果都找不到，尝试使用start_server.py
                server_cmd = [sys.executable, "start_server.py"]
            
            # 使用subprocess启动服务器进程
            self.server_process = subprocess.Popen(
                server_cmd,
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
        
        # 投掷效果骰子，这会设置 self.game_logic.effect_dice_result
        self.game_logic.roll_effect_dice()

        # 根据效果类型和骰子结果构建消息
        current_player = self.game_logic.get_current_player()
        if self.game_logic.effect_type == 'reward':
            self.game_logic.message = f"玩家{current_player.id + 1}获得{self.game_logic.effect_dice_result}金币！"
        elif self.game_logic.effect_type == 'penalty':
            self.game_logic.message = f"玩家{current_player.id + 1}失去{self.game_logic.effect_dice_result}金币！"
        else:
            self.game_logic.message = ""
        
        # 如果是联机游戏，发送效果骰子结果
        if self.is_online_game and self.network_client:
            # 发送当前玩家的槽位信息
            self.network_client.send_effect_dice_roll_with_slot(
                self.game_logic.effect_dice_result, 
                self.game_logic.current_player
            )
        
        # 设置非阻塞等待
        self.start_wait('effect_completed', 1500, self.complete_effect_dice_roll)
    
    def complete_effect_dice_roll(self):
        """完成效果骰子投掷后的处理"""
        if not self.game_logic:
            return
        # 进入下一回合
        self.game_logic.next_turn()
    
    def handle_ai_network_turn(self, player_slot: int):
        """处理网络模式下AI的回合"""
        print(f"\n[AI回合] handle_ai_network_turn被调用: player_slot={player_slot}, is_host={self.is_host}, is_online_game={self.is_online_game}")
        if self.is_online_game and self.is_host and self.game_logic and self.network_client:
            current_player = self.game_logic.get_current_player()
            print(f"[AI回合] 主机处理AI回合: AI槽位={player_slot}, 当前回合玩家槽位={current_player.id}, 是否AI={current_player.is_ai}")
            print(f"[AI回合] 当前回合状态: waiting_for_effect_dice={self.game_logic.waiting_for_effect_dice}, waiting_state={self.waiting_state}")
            
            # 确保当前是AI玩家的回合，且槽位匹配
            if current_player.id == player_slot and current_player.is_ai:
                print(f"[AI回合] 主机确认AI回合有效，准备执行AI动作")
                # AI投掷骰子
                if not self.game_logic.waiting_for_effect_dice: # 如果不是等待效果骰子
                    dice_result = self.game_logic.roll_dice()
                    print(f"[AI回合] AI {player_slot + 1} 投掷了骰子: {dice_result}")
                    self.network_client.send_dice_roll_with_slot(dice_result, player_slot)
                    print(f"[AI回合] 已发送AI骰子结果: dice_result={dice_result}, player_slot={player_slot}")
                    
                    # 直接触发玩家移动，不等待玩家点击
                    start_position = current_player.position
                    current_player.move(dice_result)
                    end_position = current_player.position
                    
                    # 开始玩家移动动画
                    if self.animation_manager:
                        self.animation_manager.start_player_move_animation(
                            self.game_logic.current_player, start_position, end_position, dice_result)
                        print(f"[AI回合] 主机AI移动动画已开始，从{start_position}到{end_position}")
                        print(f"[AI回合] AI移动完成后会自动处理格子效果和下一回合")
                        
                        # 不在此处等待效果骰子，由动画完成后的处理来触发
                        # 移动动画完成后会调用handle_move_completion，然后决定是否需要效果骰子
                else: # AI投掷效果骰子
                    effect_dice_result = self.game_logic.roll_effect_dice()
                    print(f"[AI回合] AI {player_slot + 1} 投掷了效果骰子: {effect_dice_result}, 效果类型: {self.game_logic.effect_type}")
                    self.network_client.send_effect_dice_roll_with_slot(effect_dice_result, player_slot)
                    print(f"[AI回合] 已发送AI效果骰子结果: effect_dice_result={effect_dice_result}, player_slot={player_slot}")
                    
                    # 根据效果类型和骰子结果构建消息
                    if self.game_logic.effect_type == 'reward':
                        self.game_logic.message = f"AI{current_player.id + 1}获得{effect_dice_result}金币！"
                    elif self.game_logic.effect_type == 'penalty':
                        self.game_logic.message = f"AI{current_player.id + 1}失去{effect_dice_result}金币！"
                    else:
                        self.game_logic.message = ""
                    
                    # 确保执行效果并进入下一回合
                    self.start_wait("ai_effect", 1000, self.handle_effect_completion)
                    print(f"[AI回合] 主机已安排AI效果处理和回合推进，1000ms后自动执行")
            else:
                print(f"[AI回合] 警告: 主机处理AI回合时发现槽位不匹配或非AI玩家: player_slot={player_slot}, current_player.id={current_player.id}, is_ai={current_player.is_ai}")
        else:
            reason = []
            if not self.is_online_game: reason.append("非联机游戏")
            if not self.is_host: reason.append("非主机")
            if not self.game_logic: reason.append("game_logic为空")
            if not self.network_client: reason.append("network_client为空")
            print(f"[AI回合] handle_ai_network_turn未执行AI动作，原因: {', '.join(reason)}")
    
    def handle_effect_completion(self):
        """处理格子效果完成后的逻辑"""
        if not self.game_logic:
            return
        print(f"\n[效果完成] 处理效果完成逻辑")
        current_player = self.game_logic.get_current_player()
        print(f"[效果完成] 当前玩家: id={current_player.id}, is_ai={current_player.is_ai}, money={current_player.money}")
        
        # 执行效果
        self.game_logic.execute_effect(self.game_logic.effect_type, current_player)
        print(f"[效果完成] 执行效果: type={self.game_logic.effect_type}, effect_dice_result={self.game_logic.effect_dice_result}")
        
        # 清除效果状态
        self.game_logic.waiting_for_effect_dice = False
        self.game_logic.effect_type = ""
        
        # 进入下一回合
        print(f"[效果完成] 准备进入下一回合")
        self.proceed_to_next_turn()
    
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
        
        # 检查是否是AI回合
        if not current_player.is_ai:
            return
            
        # 检查AI是否可以行动（没有动画运行、没有等待效果骰子、游戏未结束、没有等待状态）
        if (self.animation_manager.is_any_animation_running() or
            self.game_logic.waiting_for_effect_dice or
            self.game_logic.is_game_over() or
            self.waiting_state):
            return
            
        # 联机游戏时，检查是否应该在本地执行AI操作
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
        
        current_player = self.game_logic.get_current_player()
        
        # 联机游戏中，只有本地玩家才生成骰子
        if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
            # 如果不是本地玩家的回合，等待网络同步
            if not self.game_logic.is_local_player_turn():
                return
        
        dice = self.game_logic.roll_dice()
        self.game_logic.dice_result = dice
        
        # 如果是联机游戏，发送骰子结果
        if self.is_online_game and self.network_client:
            # 总是发送当前玩家的槽位，无论是真人还是AI
            self.network_client.send_dice_roll_with_slot(dice, self.game_logic.current_player)
        
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
        print(f"\n[移动完成] 处理移动完成逻辑")
        current_player = self.game_logic.get_current_player()
        print(f"[移动完成] 当前玩家: id={current_player.id}, is_ai={current_player.is_ai}, position={current_player.position}")
        
        effect_result = self.game_logic.handle_cell_effect(current_player, self.board)
        
        if isinstance(effect_result, tuple): # 如果返回的是元组 (effect_type, message)
            effect_type, message = effect_result
        else: # 如果只返回消息字符串
            effect_type = "normal"
            message = effect_result

        self.game_logic.message = message
        print(f"[移动完成] 格子效果: type={effect_type}, message={message}")
        
        if self.game_logic.waiting_for_click:
            self.game_logic.waiting_for_click = False
        
        # 如果是奖励或惩罚格子
        if effect_type in ['reward', 'penalty']:
            # 清除移动骰子结果，避免显示混乱
            self.game_logic.dice_result = 0
            
            if current_player.is_ai:
                # 联机游戏中，检查是否应该在本地执行AI操作
                if (self.is_online_game and isinstance(self.game_logic, NetworkGameLogic) and 
                    not self.game_logic.should_ai_act_locally()):
                    # 非房主客户端只等待网络同步
                    print(f"[移动完成] 非房主客户端，等待网络同步AI的效果骰子")
                    pass
                else:
                    # 单机游戏或房主处理AI效果骰子
                    print(f"[移动完成] 安排AI在800ms后投掷效果骰子")
                    self.start_wait('move_completed', 800, self.handle_ai_effect_dice_roll)
            else:
                # 真实玩家需要手动点击投掷效果骰子
                print(f"[移动完成] 玩家需要手动点击投掷效果骰子")
                pass  # 等待玩家点击
        else:
            # 其他格子延迟后进入下一回合
            delay = 800 if current_player.is_ai else 500
            print(f"[移动完成] 不需要效果骰子，{delay}ms后进入下一回合")
            self.start_wait('move_completed', delay, self.proceed_to_next_turn)
    
    def proceed_to_next_turn(self):
        """进入下一回合"""
        if not self.game_logic:
            return
        print(f"\n[下一回合] 准备进入下一回合")
        
        # 记录当前玩家信息（切换前）
        current_player_id = self.game_logic.current_player
        current_player = self.game_logic.get_current_player()
        print(f"[下一回合] 当前玩家(切换前): id={current_player_id}, is_ai={current_player.is_ai}")
        
        # 重置AI延迟计时器
        if hasattr(self, 'ai_turn_delay'):
            delattr(self, 'ai_turn_delay')
            print(f"[下一回合] 重置AI延迟计时器")
        
        # 调用next_turn，这会触发回合切换
        # 如果是NetworkGameLogic，且下一个玩家是AI，会发送AI_TURN_START消息
        self.game_logic.next_turn()
        
        # 打印新的当前玩家信息（切换后）
        new_current_id = self.game_logic.current_player
        new_current = self.game_logic.get_current_player()
        print(f"[下一回合] 新的当前玩家(切换后): id={new_current_id}, is_ai={new_current.is_ai}")
        
        # 特别提示NetworkGameLogic的情况
        if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
            if new_current.is_ai:
                print(f"[下一回合] 联机游戏中下一玩家是AI，如果是房主会发送AI_TURN_START消息")
                if self.game_logic.is_host():
                    print(f"[下一回合] 本地是房主，已在NetworkGameLogic.next_turn中发送AI_TURN_START消息")
                else:
                    print(f"[下一回合] 本地不是房主，等待接收AI_TURN_START消息")
            else:
                print(f"[下一回合] 联机游戏中下一玩家是真人玩家")
                if self.game_logic.is_local_player_turn():
                    print(f"[下一回合] 是本地玩家的回合")
                else:
                    print(f"[下一回合] 是其他玩家的回合")
    
    def handle_ai_effect_dice_roll(self):
        """处理AI的效果骰子投掷"""
        if not self.game_logic:
            return
        print(f"\n[AI效果骰子] 处理AI的效果骰子投掷")
            
        current_player = self.game_logic.get_current_player()
        print(f"[AI效果骰子] 当前玩家: id={current_player.id}, is_ai={current_player.is_ai}")
        
        # 确保当前是AI回合
        if not current_player.is_ai:
            print(f"[AI效果骰子] 当前不是AI回合，退出")
            return
            
        # 联机游戏时，检查是否应该在本地执行AI操作
        if self.is_online_game and isinstance(self.game_logic, NetworkGameLogic):
            if not self.game_logic.should_ai_act_locally():
                print(f"[AI效果骰子] 联机游戏中不应在本地执行AI操作，退出")
                return
        
        print(f"[AI效果骰子] 执行效果骰子投掷: 效果类型={self.game_logic.effect_type}")
                
        # 投掷效果骰子，这会设置 self.game_logic.effect_dice_result
        effect_dice_result = self.game_logic.roll_effect_dice()
        print(f"[AI效果骰子] 投掷结果: {effect_dice_result}")

        # 根据效果类型和骰子结果构建消息
        if self.game_logic.effect_type == 'reward':
            self.game_logic.message = f"AI{current_player.id + 1}获得{effect_dice_result}金币！"
        elif self.game_logic.effect_type == 'penalty':
            self.game_logic.message = f"AI{current_player.id + 1}失去{effect_dice_result}金币！"
        else:
            self.game_logic.message = ""
        print(f"[AI效果骰子] 设置消息: {self.game_logic.message}")
            
        # 如果是联机游戏的AI，房主发送效果骰子结果
        if (self.is_online_game and self.network_client and 
            isinstance(self.game_logic, NetworkGameLogic) and self.game_logic.is_host()):
            self.network_client.send_effect_dice_roll_with_slot(
                effect_dice_result,
                self.game_logic.current_player
            )
            print(f"[AI效果骰子] 已发送效果骰子结果: {effect_dice_result}, player_slot={self.game_logic.current_player}")
            
        # 设置非阻塞等待
        self.start_wait('ai_effect', 2000, self.complete_ai_effect_dice_roll)
        print(f"[AI效果骰子] 设置2000ms后执行complete_ai_effect_dice_roll")
    
    def complete_ai_effect_dice_roll(self):
        """完成AI效果骰子投掷后的处理"""
        if not self.game_logic:
            return
        print(f"\n[AI效果完成] 完成AI效果骰子投掷")
        
        # 进入下一回合
        print(f"[AI效果完成] 进入下一回合")
        self.game_logic.next_turn()

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
        
        # 绘制昵称输入界面
        if self.show_nickname_input:
            self.draw_nickname_input()
        
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
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH//2, 80))
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
        
        y_offset = 120
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
        
        # 设置昵称按钮（放在联机游戏按钮下面）
        nickname_button_y = y_offset + 210
        nickname_button = pygame.Rect(WINDOW_WIDTH//2 - 100, nickname_button_y, 200, 40)
        pygame.draw.rect(self.screen, (135, 206, 235), nickname_button)  # 天蓝色
        pygame.draw.rect(self.screen, BLACK, nickname_button, 2)
        button_text = self.small_font.render("设置昵称", True, BLACK)
        button_rect = button_text.get_rect(center=nickname_button.center)
        self.screen.blit(button_text, button_rect)
        
        # 显示当前昵称（放在设置按钮下面）
        nickname_display = f"当前昵称: {config_manager.get_nickname()}"
        nickname_text = self.small_font.render(nickname_display, True, (70, 70, 200))  # 使用深蓝色
        nickname_rect = nickname_text.get_rect(center=(WINDOW_WIDTH//2, nickname_button_y + 55))
        self.screen.blit(nickname_text, nickname_rect)
    
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
        
        elif self.room_state == "hosting":
            # 如果正在连接服务器
            if self.connecting_to_server:
                # 标题
                title = self.big_font.render("正在创建房间", True, BLACK)
                title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 150))
                self.screen.blit(title, title_rect)
                
                # 显示连接进度信息
                info_text = self.font.render("正在启动服务器并建立连接...", True, BLACK)
                info_rect = info_text.get_rect(center=(WINDOW_WIDTH//2, 250))
                self.screen.blit(info_text, info_rect)
                
                # 取消按钮
                cancel_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 400, 200, 60)
                pygame.draw.rect(self.screen, RED, cancel_button)
                pygame.draw.rect(self.screen, BLACK, cancel_button, 3)
                cancel_text = self.font.render("取消", True, WHITE)
                cancel_rect = cancel_text.get_rect(center=cancel_button.center)
                self.screen.blit(cancel_text, cancel_rect)
        
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
    
    def draw_nickname_input(self):
        """绘制昵称输入界面"""
        # 半透明背景
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        
        # 输入框背景
        input_bg_width = 400
        input_bg_height = 200
        input_bg_rect = pygame.Rect(WINDOW_WIDTH//2 - input_bg_width//2, 200, input_bg_width, input_bg_height)
        pygame.draw.rect(self.screen, WHITE, input_bg_rect)
        pygame.draw.rect(self.screen, BLACK, input_bg_rect, 3)
        
        # 标题
        title_text = self.font.render("设置昵称", True, BLACK)
        title_rect = title_text.get_rect(center=(WINDOW_WIDTH//2, 220))
        self.screen.blit(title_text, title_rect)
        
        # 昵称输入框
        input_box = pygame.Rect(WINDOW_WIDTH//2 - 150, 250, 300, 40)
        color = RED if self.nickname_input_active else BLACK
        pygame.draw.rect(self.screen, WHITE, input_box)
        pygame.draw.rect(self.screen, color, input_box, 2)
        
        # 显示输入的昵称
        text_surface = self.font.render(self.nickname_input_text, True, BLACK)
        self.screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))
        
        # 提示文本
        hint_text = self.small_font.render("最多7个英文字符（字母、数字、_、-）", True, GRAY)
        hint_rect = hint_text.get_rect(center=(WINDOW_WIDTH//2, 300))
        self.screen.blit(hint_text, hint_rect)
        
        # 确认按钮
        confirm_button = pygame.Rect(WINDOW_WIDTH//2 - 100, 320, 80, 40)
        pygame.draw.rect(self.screen, GREEN, confirm_button)
        pygame.draw.rect(self.screen, BLACK, confirm_button, 2)
        confirm_text = self.font.render("确认", True, BLACK)
        confirm_rect = confirm_text.get_rect(center=confirm_button.center)
        self.screen.blit(confirm_text, confirm_rect)
        
        # 取消按钮
        cancel_button = pygame.Rect(WINDOW_WIDTH//2 + 20, 320, 80, 40)
        pygame.draw.rect(self.screen, GRAY, cancel_button)
        pygame.draw.rect(self.screen, BLACK, cancel_button, 2)
        cancel_text = self.font.render("取消", True, BLACK)
        cancel_rect = cancel_text.get_rect(center=cancel_button.center)
        self.screen.blit(cancel_text, cancel_rect)
        
        # 错误消息
        if self.nickname_error_message:
            error_text = self.small_font.render(self.nickname_error_message, True, RED)
            error_rect = error_text.get_rect(center=(WINDOW_WIDTH//2, 370))
            self.screen.blit(error_text, error_rect)
    
    def cancel_server_connection(self):
        """取消服务器连接"""
        self.connection_cancelled = True
        self.connecting_to_server = False
        self.room_state = "menu"
        self.error_message = ""
        
        # 清理网络客户端
        if self.network_client:
            self.network_client.disconnect()
            self.network_client = None
    
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