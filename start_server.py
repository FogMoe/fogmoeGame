"""
独立运行游戏服务器
"""

import sys
import socket

def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个外部地址（不会真正发送数据）
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def main():
    """启动服务器"""
    from network.server import GameServer, SERVER_VERSION
    
    # 获取本机IP
    local_ip = get_local_ip()
    
    print("=" * 50)
    print("雾萌游戏服务器")
    print("=" * 50)
    print(f"版本: v{SERVER_VERSION}")
    print(f"本机IP地址: {local_ip}")
    print(f"服务器端口: 29188")
    print("其他玩家可以使用上述IP地址连接到此服务器")
    print("按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    # 创建并启动服务器
    server = GameServer(host='0.0.0.0', port=29188)
    server.start()
    
    try:
        # 保持服务器运行
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop()
        print("服务器已关闭")

if __name__ == "__main__":
    main() 