#!/usr/bin/env python3
"""
API Key 生成工具

使用方法:
    python generate_api_key.py              # 生成单个 API Key
    python generate_api_key.py --count 5     # 生成多个 API Key
    python generate_api_key.py --format env  # 输出为环境变量格式
"""

import secrets
import string
import argparse
from typing import List


def generate_api_key(length: int = 32) -> str:
    """
    生成安全的随机 API Key
    
    Args:
        length: API Key 长度（默认32字符）
        
    Returns:
        生成的 API Key
    """
    # 使用字母、数字和部分特殊字符
    alphabet = string.ascii_letters + string.digits + "-_"
    # 使用 secrets 模块生成加密安全的随机字符串
    api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
    return api_key


def generate_api_keys(count: int = 1, length: int = 32) -> List[str]:
    """
    生成多个 API Key
    
    Args:
        count: 要生成的 API Key 数量
        length: 每个 API Key 的长度
        
    Returns:
        API Key 列表
    """
    return [generate_api_key(length) for _ in range(count)]


def format_for_env(api_keys: List[str]) -> str:
    """
    将 API Key 列表格式化为环境变量格式
    
    Args:
        api_keys: API Key 列表
        
    Returns:
        格式化的字符串
    """
    return f"API_KEYS={','.join(api_keys)}"


def main():
    parser = argparse.ArgumentParser(
        description="生成安全的 API Key",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 生成单个 API Key
  %(prog)s --count 3          # 生成3个 API Key
  %(prog)s --length 64        # 生成64字符长度的 API Key
  %(prog)s --format env       # 输出为环境变量格式
  %(prog)s --count 2 --format env  # 生成2个并格式化为环境变量
        """
    )
    
    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='要生成的 API Key 数量（默认: 1）'
    )
    
    parser.add_argument(
        '--length',
        type=int,
        default=32,
        help='API Key 长度（默认: 32）'
    )
    
    parser.add_argument(
        '--format',
        choices=['plain', 'env'],
        default='plain',
        help='输出格式：plain（纯文本）或 env（环境变量格式，默认: plain）'
    )
    
    args = parser.parse_args()
    
    # 生成 API Key
    api_keys = generate_api_keys(count=args.count, length=args.length)
    
    # 输出结果
    if args.format == 'env':
        print(format_for_env(api_keys))
        print("\n# 将上面的内容添加到你的 .env 文件中")
    else:
        if args.count == 1:
            print(f"生成的 API Key:")
            print(api_keys[0])
            print(f"\n长度: {len(api_keys[0])} 字符")
        else:
            print(f"生成的 {args.count} 个 API Key:")
            for i, key in enumerate(api_keys, 1):
                print(f"{i}. {key}")
            print(f"\n环境变量格式:")
            print(format_for_env(api_keys))
            print("\n# 将上面的内容添加到你的 .env 文件中")


if __name__ == "__main__":
    main()

