"""
网络通信协议定义
"""

import json
from enum import Enum

class MessageType(Enum):
    # 连接相关
    JOIN_ROOM = "join_room"
    JOIN_SUCCESS = "join_success"
    JOIN_FAILED = "join_failed"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_DISCONNECTED = "player_disconnected"  # 玩家掉线
    AI_TAKEOVER = "ai_takeover"  # AI接管
    
    # 游戏控制
    START_GAME = "start_game"
    GAME_STARTED = "game_started"
    
    # 游戏状态同步
    GAME_STATE = "game_state"
    PLAYER_MOVE = "player_move"
    DICE_ROLL = "dice_roll"
    EFFECT_DICE_ROLL = "effect_dice_roll"
    TURN_CHANGE = "turn_change"
    GAME_OVER = "game_over"
    
    # 心跳
    PING = "ping"
    PONG = "pong"

class NetworkMessage:
    """网络消息类"""
    
    def __init__(self, msg_type: MessageType, data=None, player_id=None):
        self.type = msg_type
        self.data = data or {}
        self.player_id = player_id
    
    def to_json(self):
        """转换为JSON字符串"""
        return json.dumps({
            'type': self.type.value,
            'data': self.data,
            'player_id': self.player_id
        })
    
    @classmethod
    def from_json(cls, json_str):
        """从JSON字符串创建消息"""
        try:
            data = json.loads(json_str)
            msg_type = MessageType(data['type'])
            return cls(msg_type, data.get('data', {}), data.get('player_id'))
        except (json.JSONDecodeError, ValueError, KeyError):
            return None

def create_join_message(player_name):
    """创建加入房间消息"""
    return NetworkMessage(MessageType.JOIN_ROOM, {'player_name': player_name})

def create_start_game_message():
    """创建开始游戏消息"""
    return NetworkMessage(MessageType.START_GAME)

def create_dice_roll_message(dice_result, player_id):
    """创建骰子投掷消息"""
    return NetworkMessage(MessageType.DICE_ROLL, {
        'dice_result': dice_result,
        'player_id': player_id
    })

def create_effect_dice_roll_message(effect_result, player_id):
    """创建效果骰子投掷消息"""
    return NetworkMessage(MessageType.EFFECT_DICE_ROLL, {
        'effect_result': effect_result,
        'player_id': player_id
    })

def create_game_state_message(players, current_player, game_message):
    """创建游戏状态同步消息"""
    players_data = []
    for player in players:
        players_data.append({
            'id': player.id,
            'position': player.position,
            'money': player.money,
            'is_ai': player.is_ai,
            'color': player.color,
            'name': getattr(player, 'name', f'Player{player.id + 1}')
        })
    
    return NetworkMessage(MessageType.GAME_STATE, {
        'players': players_data,
        'current_player': current_player,
        'message': game_message
    })

def create_game_over_message(results):
    """创建游戏结束消息"""
    return NetworkMessage(MessageType.GAME_OVER, {'results': results}) 