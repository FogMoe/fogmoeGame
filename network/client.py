"""
游戏客户端
处理与服务器的通信和本地游戏状态
"""

import socket
import threading
import json
import time
from typing import Optional, Callable, List, Dict

from .protocol import NetworkMessage, MessageType, create_join_message, create_start_game_message

class GameClient:
    """游戏客户端类"""
    
    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.player_id: Optional[str] = None
        self.player_slot: Optional[int] = None
        self.is_host = False
        self.room_players: List[Dict] = []
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.receive_thread: Optional[threading.Thread] = None
        
        # 心跳相关
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.last_pong_time = time.time()
        self.heartbeat_interval = 5  # 5秒发送一次心跳
        self.ai_turn_callback: Optional[Callable[[int], None]] = None # 新增：AI回合回调函数，添加类型提示
        
        # 注册默认消息处理器
        self.register_handler(MessageType.JOIN_SUCCESS, self.handle_join_success)
        self.register_handler(MessageType.JOIN_FAILED, self.handle_join_failed)
        self.register_handler(MessageType.PLAYER_JOINED, self.handle_player_joined)
        self.register_handler(MessageType.PLAYER_LEFT, self.handle_player_left)
        self.register_handler(MessageType.PLAYER_DISCONNECTED, self.handle_player_disconnected)
        self.register_handler(MessageType.GAME_STARTED, self.handle_game_started)
        self.register_handler(MessageType.PONG, self.handle_pong)
        self.register_handler(MessageType.AI_TAKEOVER, self.handle_ai_takeover)
        self.register_handler(MessageType.AI_TURN_START, self.handle_ai_turn_start) # 注册AI回合开始处理器
    
    def connect(self, host: str, port: int = 29188) -> bool:
        """连接到服务器"""
        if self.connected and self.socket:
            # 如果已经连接，先断开旧的连接，理论上 MonopolyGame 类会创建新实例，但这作为保险
            print("GameClient.connect: 已连接，正在重新连接...")
            self.disconnect()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)  # 设置5秒连接超时

            self.socket.connect((host, port))
            
            self.socket.settimeout(None) # 连接成功后，恢复为阻塞模式用于后续收发
            self.connected = True
            self.running = True
            
            # 启动接收线程
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            # 启动心跳线程
            self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            
            print(f"成功连接到 {host}:{port}")
            return True
        
        except socket.timeout:
            print(f"连接超时: {host}:{port}")
            if self.socket:
                self.socket.close()
            self.socket = None
            self.connected = False
            self.running = False #确保线程不会因旧状态启动
            return False
        except ConnectionRefusedError:
            print(f"连接被拒绝: {host}:{port}")
            if self.socket:
                self.socket.close()
            self.socket = None
            self.connected = False
            self.running = False
            return False
        except Exception as e:
            print(f"连接失败 ({type(e).__name__}): {host}:{port} - {e}")
            if self.socket:
                self.socket.close()
            self.socket = None
            self.connected = False
            self.running = False
            return False

    def disconnect(self):
        """断开连接"""
        print("GameClient.disconnect: 正在断开连接...")
        self.running = False  # 命令线程停止
        self.connected = False
        
        # 关闭socket
        if self.socket:
            try:
                # SHUT_RDWR 确保所有挂起的发送和接收都被中止
                self.socket.shutdown(socket.SHUT_RDWR)
            except OSError as e:
                # 如果socket已经关闭或未连接，shutdown可能会失败
                print(f"GameClient.disconnect: socket.shutdown 错误: {e}")
            except Exception as e:
                print(f"GameClient.disconnect: socket.shutdown 未知错误: {e}")
            finally:
                try:
                    self.socket.close()
                except Exception as e:
                    print(f"GameClient.disconnect: socket.close 错误: {e}")
                self.socket = None
        
        # 等待线程结束 (可选，但有助于更干净的退出)
        # 注意：如果线程是daemon，它们会在主线程退出时自动结束
        # 但显式join更好，前提是它们能保证在self.running = False后很快退出
        if self.receive_thread and self.receive_thread.is_alive():
            print("GameClient.disconnect: 等待接收线程结束...")
            self.receive_thread.join(timeout=1.0) # 等待1秒
            if self.receive_thread.is_alive():
                 print("GameClient.disconnect: 接收线程超时未结束.")
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            print("GameClient.disconnect: 等待心跳线程结束...")
            self.heartbeat_thread.join(timeout=1.0) # 等待1秒
            if self.heartbeat_thread.is_alive():
                print("GameClient.disconnect: 心跳线程超时未结束.")
        
        print("GameClient.disconnect: 连接已断开")

    def receive_messages(self):
        """接收服务器消息"""
        buffer = ""
        while self.running and self.connected: # 确保socket有效且期望运行
            try:
                if not self.socket: # Socket可能在别处被关闭
                    print("receive_messages: socket 为空，退出接收线程。")
                    break
                # 设置短超时以便能周期性检查 self.running
                self.socket.settimeout(1.0) 
                data = self.socket.recv(4096)
                self.socket.settimeout(None) # 恢复阻塞

                if not data:
                    print("receive_messages: 服务器断开连接（recv返回空）。")
                    break 
                
                decoded_data = data.decode('utf-8')
                buffer += decoded_data
                # 处理可能的多条消息
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        message = NetworkMessage.from_json(line)
                        if message:
                            self.process_message(message)
                            
            except socket.timeout: # recv超时，正常，继续循环检查self.running
                continue
            except UnicodeDecodeError as e:
                print(f"receive_messages: 消息解码错误: {e} - buffer: {buffer}")
                buffer = "" # 清理可能有问题的buffer
            except ConnectionResetError:
                print("receive_messages: 连接被服务器重置。")
                break
            except Exception as e:
                if self.running: # 只在期望运行时打印错误
                    print(f"receive_messages: 接收消息错误 ({type(e).__name__}): {e}")
                break # 遇到未知错误，退出循环
        
        print("receive_messages: 接收线程终止。")
        # 确保最终状态正确
        self.connected = False
        self.running = False # 如果是从循环中break出来的，确保running也为false

    def send_message(self, message: NetworkMessage):
        """发送消息到服务器"""
        if self.connected and self.socket:
            try:
                self.socket.send((message.to_json() + '\n').encode('utf-8'))
            except Exception as e:
                print(f"发送消息失败: {e}")
                self.connected = False
    
    def process_message(self, message: NetworkMessage):
        """处理接收到的消息"""
        handler = self.message_handlers.get(message.type)
        if handler:
            handler(message.data)
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """注册消息处理器"""
        self.message_handlers[msg_type] = handler
    
    def join_room(self, player_name: str, version: str, room_id: str = 'default'):
        """加入房间"""
        msg = NetworkMessage(MessageType.JOIN_ROOM, {
            'player_name': player_name,
            'room_id': room_id,
            'version': version
        })
        self.send_message(msg)
    
    def start_game(self):
        """开始游戏（仅房主可用）"""
        if self.is_host:
            self.send_message(create_start_game_message())
    
    def send_dice_roll(self, dice_result: int):
        """发送骰子结果"""
        msg = NetworkMessage(MessageType.DICE_ROLL, {
            'dice_result': dice_result,
            'player_id': self.player_id
        })
        self.send_message(msg)
    
    def send_dice_roll_with_slot(self, dice_result: int, player_slot: int):
        """发送带有玩家槽位的骰子结果"""
        msg = NetworkMessage(MessageType.DICE_ROLL, {
            'dice_result': dice_result,
            'player_id': self.player_id,
            'player_slot': player_slot  # 直接包含槽位信息
        })
        self.send_message(msg)
    
    def send_effect_dice_roll(self, effect_result: int):
        """发送效果骰子结果"""
        msg = NetworkMessage(MessageType.EFFECT_DICE_ROLL, {
            'effect_result': effect_result,
            'player_id': self.player_id
        })
        self.send_message(msg)
    
    def send_effect_dice_roll_with_slot(self, effect_result: int, player_slot: int):
        """发送带有玩家槽位的效果骰子结果"""
        msg = NetworkMessage(MessageType.EFFECT_DICE_ROLL, {
            'effect_result': effect_result,
            'player_id': self.player_id,
            'player_slot': player_slot  # 直接包含槽位信息
        })
        self.send_message(msg)
    
    def send_game_state(self, game_state: dict):
        """发送游戏状态更新"""
        msg = NetworkMessage(MessageType.GAME_STATE, game_state)
        self.send_message(msg)
    
    # 默认消息处理器
    def handle_join_success(self, data: dict):
        """处理加入成功"""
        self.player_id = data['player_id']
        self.player_slot = data['slot']
        self.is_host = data['is_host']
        self.room_players = data['players']
        print(f"成功加入房间，玩家槽位: {self.player_slot}, 是否房主: {self.is_host}")
    
    def handle_join_failed(self, data: dict):
        """处理加入失败"""
        reason = data.get('reason', '未知原因')
        print(f"加入房间失败: {reason}")
    
    def handle_player_joined(self, data: dict):
        """处理其他玩家加入"""
        print(f"玩家 {data['player_name']} 加入了房间")
        # 更新房间玩家列表
        self.room_players.append({
            'id': data['player_id'],
            'name': data['player_name'],
            'slot': data['slot']
        })
    
    def handle_player_left(self, data: dict):
        """处理玩家离开"""
        player_id = data['player_id']
        print(f"玩家 {player_id} 离开了房间")
        # 更新房间玩家列表
        self.room_players = [p for p in self.room_players if p['id'] != player_id]
    
    def handle_game_started(self, data: dict):
        """处理游戏开始"""
        print("游戏开始！")
        self.room_players = data['players']
    
    def handle_pong(self, data: dict):
        """处理心跳响应"""
        self.last_pong_time = time.time()
    
    def handle_ai_takeover(self, data: dict):
        """处理AI接管通知"""
        player_slot = data.get('player_slot')
        player_name = data.get('player_name', f'玩家{player_slot}')
        print(f"玩家 {player_name}(槽位:{player_slot}) 已断线，由AI接管")
        
        # 只有房主客户端需要真正地执行AI接管操作
        if self.is_host and self.ai_turn_callback and player_slot is not None:
            print(f"[客户端] 房主客户端：执行玩家 {player_slot} 的AI接管")
            # 使用与AI回合相同的回调函数通知游戏系统将该玩家标记为AI控制
            # 注：游戏系统需要处理这种情况，将玩家标记为AI控制
            self.ai_turn_callback(player_slot)
        else:
            reason = []
            if not self.is_host:
                reason.append("非房主")
            if not self.ai_turn_callback:
                reason.append("未设置ai_turn_callback")
            if player_slot is None:
                reason.append("player_slot为None")
            
            if reason:
                print(f"[客户端] 不执行AI接管，原因: {', '.join(reason)}")
    
    def handle_ai_turn_start(self, data: dict):
        """处理AI回合开始通知"""
        player_slot = data.get('player_slot')
        print(f"\n[客户端] 收到AI回合开始通知，槽位: {player_slot}")
        
        # 只有房主客户端需要触发AI行动
        if self.is_host and self.ai_turn_callback and player_slot is not None:
            print(f"[客户端] 房主客户端：触发AI {player_slot} 的行动")
            self.ai_turn_callback(player_slot) # 调用回调函数触发AI行动
        else:
            reason = []
            if not self.is_host:
                reason.append("非房主")
            if not self.ai_turn_callback:
                reason.append("未设置ai_turn_callback")
            if player_slot is None:
                reason.append("player_slot为None")
            
            if reason:
                print(f"[客户端] 不触发AI行动，原因: {', '.join(reason)}")

    def send_ping(self):
        """发送心跳"""
        self.send_message(NetworkMessage(MessageType.PING))

    def heartbeat_loop(self):
        """心跳循环"""
        print("heartbeat_loop: 心跳线程启动。")
        while self.running and self.connected:
            try:
                if not self.socket or not self.connected:
                    print("heartbeat_loop: socket无效或未连接，退出心跳。")
                    break
                self.send_ping()
                # time.sleep(self.heartbeat_interval)
                # 改为更细粒度的sleep以更快响应self.running的变化
                for _ in range(int(self.heartbeat_interval * 10)): # 假设interval是5s，则每0.1s检查一次
                    if not self.running or not self.connected:
                        break
                    time.sleep(0.1)
                if not self.running or not self.connected: #再次检查
                    break
            except Exception as e:
                if self.running: # 只在期望运行时打印错误
                    print(f"heartbeat_loop: 心跳错误 ({type(e).__name__}): {e}")
                break # 遇到错误退出
        print("heartbeat_loop: 心跳线程终止。")

    def handle_player_disconnected(self, data: dict):
        """处理玩家断线通知"""
        player_id = data.get('player_id')
        player_slot = data.get('player_slot')
        player_name = data.get('player_name', f'玩家{player_slot}')
        reason = data.get('reason', '未知原因')
        
        print(f"玩家 {player_name}(槽位:{player_slot}) 断线，原因: {reason}")
        
        # 更新房间玩家列表 (如果需要)
        self.room_players = [p for p in self.room_players if p['id'] != player_id]

def test_client():
    """测试客户端"""
    client = GameClient()
    
    # 连接到服务器
    if client.connect('localhost', 29188):
        print("连接成功")
        
        # 加入房间
        client.join_room("TestPlayer", "1.0.0")
        
        # 等待一会儿
        time.sleep(2)
        
        # 如果是房主，开始游戏
        if client.is_host:
            print("作为房主，开始游戏...")
            client.start_game()
        
        # 保持连接
        try:
            while client.connected:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n断开连接...")
            client.disconnect()
    else:
        print("连接失败")

if __name__ == "__main__":
    test_client() 