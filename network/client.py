"""
游戏客户端
处理与服务器的通信和本地游戏状态
"""

import socket
import threading
import json
import time
from typing import Optional, Callable

from .protocol import NetworkMessage, MessageType, create_join_message, create_start_game_message

class GameClient:
    """游戏客户端类"""
    
    def __init__(self):
        self.socket = None
        self.connected = False
        self.running = False
        self.player_id = None
        self.player_slot = None
        self.is_host = False
        self.room_players = []
        self.message_handlers = {}
        self.receive_thread = None
        
        # 心跳相关
        self.heartbeat_thread = None
        self.last_pong_time = time.time()
        self.heartbeat_interval = 5  # 5秒发送一次心跳
        
        # 注册默认消息处理器
        self.register_handler(MessageType.JOIN_SUCCESS, self.handle_join_success)
        self.register_handler(MessageType.JOIN_FAILED, self.handle_join_failed)
        self.register_handler(MessageType.PLAYER_JOINED, self.handle_player_joined)
        self.register_handler(MessageType.PLAYER_LEFT, self.handle_player_left)
        self.register_handler(MessageType.GAME_STARTED, self.handle_game_started)
        self.register_handler(MessageType.PONG, self.handle_pong)
        self.register_handler(MessageType.AI_TAKEOVER, self.handle_ai_takeover)
    
    def connect(self, host: str, port: int = 29188) -> bool:
        """连接到服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
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
            
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def receive_messages(self):
        """接收服务器消息"""
        buffer = ""
        while self.running and self.connected:
            try:
                if self.socket:
                    data = self.socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                else:
                    break
                
                buffer += data
                # 处理可能的多条消息
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line:
                        message = NetworkMessage.from_json(line)
                        if message:
                            self.process_message(message)
                            
            except Exception as e:
                if self.running:
                    print(f"接收消息错误: {e}")
                break
        
        self.connected = False
    
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
    
    def send_effect_dice_roll(self, effect_result: int):
        """发送效果骰子结果"""
        msg = NetworkMessage(MessageType.EFFECT_DICE_ROLL, {
            'effect_result': effect_result,
            'player_id': self.player_id
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
        print(f"玩家 {player_slot} 已断线，由AI接管")
    
    def send_ping(self):
        """发送心跳"""
        self.send_message(NetworkMessage(MessageType.PING))

    def heartbeat_loop(self):
        """心跳循环"""
        while self.running and self.connected:
            try:
                self.send_ping()
                time.sleep(self.heartbeat_interval)
            except:
                pass

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