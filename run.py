#!/usr/bin/env python3
"""
LLM代理服务启动脚本（跨平台）
"""
import os
import sys
import subprocess
from pathlib import Path


def check_python():
    """检查Python版本"""
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        sys.exit(1)
    print(f"✅ Python版本: {sys.version.split()[0]}")


def check_dependencies():
    """检查并安装依赖"""
    required_packages = ["fastapi", "uvicorn", "pydantic", "aiomysql", "redis", "cachetools"]
    missing_packages = []
    
    # 检查所有必需的包
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  检测到缺少依赖: {', '.join(missing_packages)}")
        print("📦 正在安装依赖...")
        try:
            # 先升级pip
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # 安装依赖
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--timeout", "90000"])
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            print("💡 请手动运行: pip install -r requirements.txt")
            return False
    else:
        print("✅ 依赖已安装")
        return True


def check_env_file():
    """检查.env配置文件"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        print("⚠️  未找到.env配置文件")
        if env_example.exists():
            response = input("是否从.env.example创建.env文件? (y/n): ")
            if response.lower() == 'y':
                env_file.write_text(env_example.read_text())
                print("✅ .env文件已创建")
                print("⚠️  请编辑.env文件，至少配置 DEEPSEEK_API_KEY 和 API_KEYS")
                return False
        else:
            print("❌ 未找到.env.example文件")
            return False
    
    print("✅ .env配置文件存在")
    return True


def start_server():
    """启动服务"""
    print("\n" + "="*50)
    print("🚀 正在启动LLM代理服务...")
    print("="*50)
    print("📍 服务地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("📖 ReDoc文档: http://localhost:8000/redoc")
    print("💡 按 Ctrl+C 停止服务")
    print("="*50 + "\n")
    
    try:
        # 使用uvicorn启动
        import uvicorn
        from app.config import settings
        
        uvicorn.run(
            "app.main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)


def main():
    """主函数"""
    print("="*50)
    print("  LLM代理服务启动脚本")
    print("="*50)
    
    # 切换到脚本所在目录
    os.chdir(Path(__file__).parent)
    
    # 检查Python版本
    check_python()
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置文件
    if not check_env_file():
        print("\n⚠️  请先配置.env文件后再启动服务")
        sys.exit(0)
    
    # 启动服务
    start_server()


if __name__ == "__main__":
    main()

