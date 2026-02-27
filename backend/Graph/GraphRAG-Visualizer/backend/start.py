"""
后端启动脚本
支持通过命令行参数指定端口，或自动选择可用端口
使用方法:
  python start.py        # 自动查找可用端口（从8000开始）
  python start.py 8000   # 使用指定端口8000
"""
import sys
import socket
import uvicorn

# 添加当前目录到 Python 路径
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def find_free_port(start_port=8000, max_attempts=100):
    """查找可用端口"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"无法在 {start_port}-{start_port + max_attempts} 范围内找到可用端口")


if __name__ == "__main__":
    # 检查是否指定了端口
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
            print(f"[INFO] 使用指定端口: {port}")
        except ValueError:
            print(f"[ERROR] 错误: 无效的端口号 '{sys.argv[1]}'")
            sys.exit(1)
    else:
        port = find_free_port(8000)
        print(f"[INFO] 自动查找可用端口: {port}")

    print(f"[INFO] GraphRAG Visualizer 后端服务启动中...")
    print(f"[INFO] 监听地址: http://127.0.0.1:{port}")
    print(f"[INFO] API 文档: http://127.0.0.1:{port}/docs")
    print(f"[INFO] 提示: 请确保前端 .env 文件中的 VITE_API_BASE_URL 设置为 http://localhost:{port}/api")

    # 使用直接导入而不是字符串导入，避免子进程模块路径问题
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=port, reload=False)
