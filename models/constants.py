"""
游戏常量定义
"""

import pygame

# 窗口设置
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# 游戏设置
GRID_SIZE = 27  # 格子总数（从9个扩大到27个）
WINNING_MONEY = 100  # 获胜所需金币
CELL_SIZE = 60  # 格子大小

# 动画设置
ANIMATION_SPEED = 0.1
DICE_ANIMATION_FRAMES = 30
PLAYER_MOVE_SPEED = 1.5     # 进一步降低玩家移动速度

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
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
DARK_BLUE = (0, 0, 139)       # 深蓝色
BRIGHT_GREEN = (50, 205, 50)  # 亮绿色

# 格子颜色定义
REWARD_COLOR = YELLOW         # 奖励格：黄色
DISCARD_COLOR = DARK_BLUE     # 丢弃格：深蓝色

# 玩家颜色 - 避免与格子颜色冲突
PLAYER_COLORS = [RED, PURPLE, BRIGHT_GREEN, ORANGE]

# Home格颜色 - 与玩家颜色保持一致
HOME_COLORS = [RED, PURPLE, BRIGHT_GREEN, ORANGE]

# 游戏状态
GAME_STATE_START = "start"
GAME_STATE_PLAYING = "playing"
GAME_STATE_RESULTS = "results" 