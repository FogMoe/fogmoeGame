# 雾萌

一个支持单人和局域网联机的简易类大富翁游戏，使用 Python 和 Pygame 开发。

## 功能特点

- **单人模式**：1名玩家对战3个AI
- **联机模式**：支持最多4名玩家通过局域网对战
- **游戏规则**：
  - 收集金币，回到自己的Home格获胜
  - 获胜条件：拥有100枚金币并回到Home格
  - 奖励格（黄色）：投骰子获得金币
  - 丢弃格（深蓝色）：投骰子失去金币

## 快速开始

### 安装依赖

```bash
pip install pygame
```

### 单人游戏

```bash
python main.py
```

点击"单人游戏"即可开始。

### 联机游戏

1. **启动服务器**（在主机上）：
   ```bash
   python start_server.py
   ```

2. **创建/加入房间**：
   - 运行 `python main.py`
   - 点击"联机游戏"
   - 房主选择"创建房间"
   - 其他玩家选择"加入房间"并输入服务器IP

3. **开始游戏**：
   - 房主点击"开始游戏"按钮

## 项目结构

```
miniGame/
├── main.py              # 游戏主程序
├── start_server.py      # 游戏服务器
├── test_multiplayer.py  # 联机测试脚本
├── game/               # 游戏逻辑
│   ├── board.py        # 棋盘定义
│   ├── game_logic.py   # 游戏逻辑
│   └── network_game_logic.py  # 网络游戏逻辑
├── models/             # 数据模型
│   ├── player.py       # 玩家类
│   ├── cell.py         # 格子类
│   └── constants.py    # 游戏常量
├── network/            # 网络功能
│   ├── client.py       # 游戏客户端
│   ├── server.py       # 游戏服务器
│   └── protocol.py     # 网络协议
└── ui/                 # 用户界面
    ├── renderer.py     # 渲染器
    └── animations.py   # 动画管理
```

## 联机游戏说明

- 玩家按加入顺序分配为玩家1、2、3、4
- 每个玩家只能在自己的回合投骰子
- AI的操作由房主计算并同步给所有客户端
- 游戏状态在所有客户端之间实时同步

## 系统要求

- Python 3.7+
- Pygame 2.0+

## 注意事项

- 联机游戏需要所有玩家在同一局域网内
- 确保防火墙允许端口29188的连接
- 服务器需要保持运行状态

## 许可证

GPL License 