"""
游戏服务器
处理多个客户端连接和游戏状态同步
"""

import socket
import threading
import json
import time
from typing import Dict, List, Optional

from .protocol import NetworkMessage, MessageType, create_game_state_message

# 服务器版本号（应与客户端保持一致）
SERVER_VERSION = "1.0.0"

class GameRoom:
    """游戏房间类"""
    
    def __init__(self, room_id: str, max_players: int = 4):
        self.room_id = room_id
        self.max_players = max_players
        self.players = {}  # player_id -> player_info
        self.host_id = None
        self.game_started = False
        self.current_player = 0
        self.game_state = None
        
    def add_player(self, player_id: str, player_info: dict) -> bool:
        """添加玩家到房间"""
        if len(self.players) >= self.max_players:
            return False
        
        self.players[player_id] = player_info
        if self.host_id is None:
            self.host_id = player_id
        return True
    
    def remove_player(self, player_id: str):
        """从房间移除玩家"""
        if player_id in self.players:
            del self.players[player_id]
            if player_id == self.host_id and self.players:
                # 转移房主权限
                self.host_id = list(self.players.keys())[0]
    
    def is_host(self, player_id: str) -> bool:
        """检查是否是房主"""
        return player_id == self.host_id
    
    def can_start(self) -> bool:
        """检查是否可以开始游戏"""
        return len(self.players) >= 1 and not self.game_started

class GameServer:
    """游戏服务器类"""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 29188):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # client_socket -> client_info
        self.rooms = {}  # room_id -> GameRoom
        self.player_rooms = {}  # player_id -> room_id
        self.running = False
        self.lock = threading.Lock()
        
        # 心跳检测相关
        self.heartbeat_timeout = 15  # 15秒没有心跳则认为掉线
        self.check_interval = 5  # 每5秒检查一次
        self.heartbeat_checker_thread = None
        
    def start(self):
        """启动服务器"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        print(f"服务器启动在 {self.host}:{self.port}")
        
        # 启动接受连接的线程
        accept_thread = threading.Thread(target=self.accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
        # 启动心跳检测线程
        self.heartbeat_checker_thread = threading.Thread(target=self.check_heartbeats)
        self.heartbeat_checker_thread.daemon = True
        self.heartbeat_checker_thread.start()
        
    def accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                if self.server_socket:
                    client_socket, address = self.server_socket.accept()
                    print(f"新连接来自: {address}")
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"接受连接错误: {e}")
    
    def handle_client(self, client_socket: socket.socket, address):
        """处理客户端消息"""
        player_id = f"player_{address[0]}_{address[1]}_{int(time.time())}"
        
        with self.lock:
            self.clients[client_socket] = {
                'player_id': player_id,
                'address': address,
                'socket': client_socket,
                'last_heartbeat': time.time()  # 记录最后心跳时间
            }
        
        try:
            while self.running:
                # 接收消息
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                # 处理消息
                message = NetworkMessage.from_json(data)
                if message:
                    self.process_message(client_socket, player_id, message)
                    
        except Exception as e:
            print(f"客户端处理错误 {address}: {e}")
        finally:
            # 清理断开的连接
            self.disconnect_client(client_socket, player_id)
    
    def process_message(self, client_socket: socket.socket, player_id: str, message: NetworkMessage):
        """处理接收到的消息"""
        msg_type = message.type
        data = message.data
        
        if msg_type == MessageType.JOIN_ROOM:
            self.handle_join_room(client_socket, player_id, data)
        elif msg_type == MessageType.START_GAME:
            self.handle_start_game(player_id)
        elif msg_type == MessageType.DICE_ROLL:
            self.handle_dice_roll(player_id, data)
        elif msg_type == MessageType.EFFECT_DICE_ROLL:
            self.handle_effect_dice_roll(player_id, data)
        elif msg_type == MessageType.PING:
            # 更新心跳时间
            with self.lock:
                if client_socket in self.clients:
                    self.clients[client_socket]['last_heartbeat'] = time.time()
            self.send_to_client(client_socket, NetworkMessage(MessageType.PONG))
    
    def handle_join_room(self, client_socket: socket.socket, player_id: str, data: dict):
        """处理加入房间请求"""
        room_id = data.get('room_id', 'default')
        player_name = data.get('player_name', f'Player{len(self.clients)}')
        client_version = data.get('version', 'unknown')
        
        # 检查版本号
        if client_version != SERVER_VERSION:
            fail_msg = NetworkMessage(MessageType.JOIN_FAILED, {
                'reason': f'版本不匹配！服务器版本: {SERVER_VERSION}, 客户端版本: {client_version}'
            })
            self.send_to_client(client_socket, fail_msg)
            return
        
        with self.lock:
            # 创建或获取房间
            if room_id not in self.rooms:
                self.rooms[room_id] = GameRoom(room_id)
            
            room = self.rooms[room_id]
            
            # 尝试加入房间
            player_info = {
                'id': player_id,
                'name': player_name,
                'socket': client_socket,
                'slot': len(room.players),  # 玩家槽位
                'version': client_version
            }
            
            if room.add_player(player_id, player_info):
                self.player_rooms[player_id] = room_id
                
                # 发送加入成功消息
                success_msg = NetworkMessage(MessageType.JOIN_SUCCESS, {
                    'player_id': player_id,
                    'slot': player_info['slot'],
                    'is_host': room.is_host(player_id),
                    'players': self.get_room_players_info(room)
                })
                self.send_to_client(client_socket, success_msg)
                
                # 通知房间内其他玩家
                join_msg = NetworkMessage(MessageType.PLAYER_JOINED, {
                    'player_id': player_id,
                    'player_name': player_name,
                    'slot': player_info['slot']
                })
                self.broadcast_to_room(room_id, join_msg, exclude_player=player_id)
            else:
                # 房间已满
                fail_msg = NetworkMessage(MessageType.JOIN_FAILED, {
                    'reason': '房间已满'
                })
                self.send_to_client(client_socket, fail_msg)
    
    def handle_start_game(self, player_id: str):
        """处理开始游戏请求"""
        with self.lock:
            room_id = self.player_rooms.get(player_id)
            if not room_id:
                return
            
            room = self.rooms.get(room_id)
            if not room or not room.is_host(player_id) or not room.can_start():
                return
            
            # 标记游戏开始
            room.game_started = True
            
            # 发送游戏开始消息给所有玩家
            start_msg = NetworkMessage(MessageType.GAME_STARTED, {
                'players': self.get_room_players_info(room)
            })
            self.broadcast_to_room(room_id, start_msg)
    
    def handle_dice_roll(self, player_id: str, data: dict):
        """处理骰子投掷"""
        room_id = self.player_rooms.get(player_id)
        if not room_id:
            return
        
        # 获取玩家的槽位
        room = self.rooms.get(room_id)
        if room and player_id in room.players:
            player_slot = room.players[player_id]['slot']
            data['player_slot'] = player_slot
        
        # 广播骰子结果给房间内所有玩家
        dice_msg = NetworkMessage(MessageType.DICE_ROLL, data)
        self.broadcast_to_room(room_id, dice_msg)
    
    def handle_effect_dice_roll(self, player_id: str, data: dict):
        """处理效果骰子投掷"""
        room_id = self.player_rooms.get(player_id)
        if not room_id:
            return
        
        # 获取玩家的槽位
        room = self.rooms.get(room_id)
        if room and player_id in room.players:
            player_slot = room.players[player_id]['slot']
            data['player_slot'] = player_slot
        
        # 广播效果骰子结果给房间内所有玩家
        effect_msg = NetworkMessage(MessageType.EFFECT_DICE_ROLL, data)
        self.broadcast_to_room(room_id, effect_msg)
    
    def get_room_players_info(self, room: GameRoom) -> list:
        """获取房间内玩家信息"""
        players_info = []
        for pid, pinfo in room.players.items():
            players_info.append({
                'id': pid,
                'name': pinfo['name'],
                'slot': pinfo['slot'],
                'is_host': room.is_host(pid)
            })
        return players_info
    
    def send_to_client(self, client_socket: socket.socket, message: NetworkMessage):
        """发送消息给客户端"""
        try:
            client_socket.send((message.to_json() + '\n').encode('utf-8'))
        except Exception as e:
            print(f"发送消息失败: {e}")
    
    def broadcast_to_room(self, room_id: str, message: NetworkMessage, exclude_player: Optional[str] = None):
        """广播消息给房间内所有玩家"""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        for player_id, player_info in room.players.items():
            if player_id != exclude_player:
                self.send_to_client(player_info['socket'], message)
    
    def disconnect_client(self, client_socket: socket.socket, player_id: str):
        """断开客户端连接"""
        with self.lock:
            # 从房间移除玩家
            room_id = self.player_rooms.get(player_id)
            if room_id and room_id in self.rooms:
                room = self.rooms[room_id]
                room.remove_player(player_id)
                
                # 通知其他玩家
                leave_msg = NetworkMessage(MessageType.PLAYER_LEFT, {
                    'player_id': player_id
                })
                self.broadcast_to_room(room_id, leave_msg)
                
                # 如果房间空了，删除房间
                if not room.players:
                    del self.rooms[room_id]
            
            # 清理连接信息
            if player_id in self.player_rooms:
                del self.player_rooms[player_id]
            if client_socket in self.clients:
                del self.clients[client_socket]
        
        try:
            client_socket.close()
        except:
            pass
    
    def check_heartbeats(self):
        """检查心跳超时"""
        while self.running:
            try:
                current_time = time.time()
                with self.lock:
                    # 检查所有客户端的心跳
                    timeout_clients = []
                    for client_socket, client_info in list(self.clients.items()):
                        if current_time - client_info['last_heartbeat'] > self.heartbeat_timeout:
                            timeout_clients.append((client_socket, client_info['player_id']))
                    
                    # 处理超时的客户端
                    for client_socket, player_id in timeout_clients:
                        self.handle_player_timeout(client_socket, player_id)
                
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"心跳检测错误: {e}")
    
    def handle_player_timeout(self, client_socket: socket.socket, player_id: str):
        """处理玩家超时"""
        # 获取玩家所在房间
        room_id = self.player_rooms.get(player_id)
        if room_id and room_id in self.rooms:
            room = self.rooms[room_id]
            if player_id in room.players:
                player_info = room.players[player_id]
                
                # 如果游戏已开始，通知AI接管
                if room.game_started:
                    takeover_msg = NetworkMessage(MessageType.AI_TAKEOVER, {
                        'player_slot': player_info['slot'],
                        'player_name': player_info['name']
                    })
                    self.broadcast_to_room(room_id, takeover_msg)
                else:
                    # 游戏未开始，直接移除玩家
                    room.remove_player(player_id)
                    leave_msg = NetworkMessage(MessageType.PLAYER_LEFT, {
                        'player_id': player_id
                    })
                    self.broadcast_to_room(room_id, leave_msg)
        
        # 清理连接
        if player_id in self.player_rooms:
            del self.player_rooms[player_id]
        if client_socket in self.clients:
            del self.clients[client_socket]
        
        try:
            client_socket.close()
        except:
            pass
    
    def stop(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

def main():
    """测试服务器"""
    server = GameServer()
    server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n服务器关闭中...")
        server.stop()

if __name__ == "__main__":
    main() 