"""
网络游戏逻辑处理
处理联机游戏的同步和控制
"""

from .game_logic import GameLogic
from models.player import Player
from network.protocol import MessageType, NetworkMessage

class NetworkGameLogic(GameLogic):
    """网络游戏逻辑类"""
    
    def __init__(self, network_client=None, player_slot=None):
        """初始化网络游戏逻辑"""
        super().__init__()
        self.network_client = network_client
        self.player_slot = player_slot  # 本地玩家的槽位
        self.network_players = {}  # slot -> network_id 映射
        
    def setup_network_players(self, room_players):
        """根据房间玩家信息设置网络玩家"""
        # 清空所有玩家
        self.players = []
        
        # 根据房间玩家创建玩家对象
        for i in range(4):
            if i < len(room_players):
                # 真实玩家
                player_info = room_players[i]
                player = Player(i, is_ai=False)
                player.name = player_info['name']
                player.network_id = player_info['id']
                self.network_players[i] = player_info['id']
            else:
                # AI玩家填充剩余位置
                player = Player(i, is_ai=True)
                player.name = f"AI{i + 1}"
            
            self.players.append(player)
    
    def can_current_player_roll(self):
        """检查当前玩家是否可以投骰子"""
        # 如果不是联机游戏，返回True
        if not self.network_client:
            return True
        
        # 检查是否是本地玩家的回合
        return self.current_player == self.player_slot
    
    def is_local_player_turn(self):
        """检查是否是本地玩家的回合"""
        return self.current_player == self.player_slot
    
    def is_host(self):
        """检查本地客户端是否是房主"""
        if self.network_client:
            return self.network_client.is_host
        return False
    
    def should_ai_act_locally(self):
        """判断AI是否应该在本地执行操作"""
        # 只有房主才执行AI操作
        if self.is_host():
            # 房主判断当前回合是否是AI
            current_player = self.get_current_player()
            return current_player.is_ai
        return False
    
    def handle_network_dice_roll(self, player_slot, dice_result):
        """处理网络骰子投掷"""
        # 确保是当前玩家的回合
        if player_slot != self.current_player:
            return
        
        # 设置骰子结果
        self.dice_result = dice_result
        
        # 执行移动
        current_player = self.get_current_player()
        return current_player.position, current_player.position + dice_result
    
    def handle_network_effect_dice(self, player_slot, effect_result):
        """处理网络效果骰子"""
        # 确保是当前玩家的回合
        if player_slot != self.current_player:
            return
        
        # 设置效果骰子结果
        self.effect_dice_result = effect_result
        
        # 执行效果
        current_player = self.get_current_player()
        return self.execute_effect(self.effect_type, current_player)
    
    def sync_game_state(self, game_state):
        """同步游戏状态"""
        # 更新玩家位置和金币
        for i, player_data in enumerate(game_state.get('players', [])):
            if i < len(self.players):
                self.players[i].position = player_data['position']
                self.players[i].money = player_data['money']
        
        # 更新当前玩家
        self.current_player = game_state.get('current_player', 0)
        
        # 更新游戏状态
        self.game_over = game_state.get('game_over', False)
        if game_state.get('winner') is not None:
            self.winner = self.players[game_state['winner']]
    
    def get_game_state(self):
        """获取当前游戏状态"""
        players_data = []
        for player in self.players:
            players_data.append({
                'position': player.position,
                'money': player.money
            })
        
        return {
            'players': players_data,
            'current_player': self.current_player,
            'game_over': self.game_over,
            'winner': self.players.index(self.winner) if self.winner else None
        }

    def next_turn(self):
        """切换到下一个玩家"""
        super().next_turn()  # 调用父类的next_turn来切换current_player

        # 在网络模式下，如果轮到AI玩家且本地是房主，通知服务器
        if self.network_client and self.is_host():
            current_player_obj = self.get_current_player()
            if current_player_obj.is_ai:
                # 发送消息给服务器，指示AI回合开始
                ai_turn_msg = NetworkMessage(MessageType.AI_TURN_START, {
                    'player_slot': current_player_obj.id
                })
                self.network_client.send_message(ai_turn_msg)
                print(f"房主客户端：AI{current_player_obj.id + 1}的回合，发送AI_TURN_START消息") 