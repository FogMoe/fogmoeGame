"""
游戏常量定义
"""

# 窗口设置
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