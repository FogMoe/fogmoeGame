"""
配置管理模块
管理用户设置的保存和加载
"""

import json
import os
from pathlib import Path

class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        """初始化配置管理器"""
        # 确保saves目录存在
        self.saves_dir = Path("saves")
        self.saves_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.config_file = self.saves_dir / "user_config.json"
        
        # 默认配置
        self.default_config = {
            "nickname": "Player",
            "version": "1.0"
        }
        
        # 加载配置
        self.config = self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 确保所有必需的配置项都存在
                    for key, value in self.default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                return self.default_config.copy()
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_nickname(self):
        """获取用户昵称"""
        return self.config.get("nickname", "Player")
    
    def set_nickname(self, nickname):
        """设置用户昵称"""
        # 验证昵称格式
        if not nickname:
            return False
        
        # 只允许英文字符、数字和常用符号，最多7个字符
        if len(nickname) > 7:
            return False
        
        # 检查是否只包含允许的字符（英文字母、数字、下划线、短横线）
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-')
        if not all(c in allowed_chars for c in nickname):
            return False
        
        self.config["nickname"] = nickname
        return self.save_config()
    
    def get_all_config(self):
        """获取所有配置"""
        return self.config.copy()
    
    def reset_config(self):
        """重置配置为默认值"""
        self.config = self.default_config.copy()
        return self.save_config()

# 全局配置管理器实例
config_manager = ConfigManager() 