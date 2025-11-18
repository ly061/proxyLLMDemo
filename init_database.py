#!/usr/bin/env python3
"""
数据库初始化脚本

用于初始化SQLite数据库，创建用户和API Key表结构
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.database.db import init_db
from app.utils.logger import logger


async def main():
    """主函数"""
    try:
        logger.info("开始初始化数据库...")
        await init_db()
        logger.info("数据库初始化完成！")
        print("\n✅ 数据库初始化成功！")
        print("现在你可以使用管理API创建用户和API Key了。")
        print("访问 http://localhost:8000/docs 查看API文档。")
    except Exception as e:
        logger.error(f"数据库初始化失败: {str(e)}")
        print(f"\n❌ 数据库初始化失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

