#!/usr/bin/env python3
"""
测试 API Key 管理流程

演示如何：
1. 创建用户
2. 为用户创建 API Key
3. 使用 API Key 调用服务
"""
import asyncio
import httpx
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000"


async def test_api_key_flow():
    """测试完整的 API Key 流程"""
    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("测试 API Key 管理流程")
        print("=" * 60)
        
        # 1. 创建用户
        print("\n1. 创建用户...")
        user_data = {
            "username": "testuser",
            "email": "test@example.com"
        }
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/admin/users",
                json=user_data
            )
            response.raise_for_status()
            user_result = response.json()
            print(f"✅ 用户创建成功: {user_result}")
            user_id = user_result["id"]
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                print("⚠️  用户已存在，继续使用现有用户")
                # 获取用户列表找到用户ID
                response = await client.get(f"{BASE_URL}/api/v1/admin/users")
                users = response.json()
                user_id = next((u["id"] for u in users if u["username"] == "testuser"), None)
                if not user_id:
                    print("❌ 无法找到用户")
                    return
            else:
                print(f"❌ 创建用户失败: {e}")
                return
        
        # 2. 创建 API Key
        print(f"\n2. 为用户 {user_id} 创建 API Key...")
        key_data = {
            "user_id": user_id,
            "key_name": "测试API Key"
        }
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/admin/api-keys",
                json=key_data
            )
            response.raise_for_status()
            key_result = response.json()
            api_key = key_result["api_key"]
            print(f"✅ API Key 创建成功!")
            print(f"   Key ID: {key_result['id']}")
            print(f"   API Key: {api_key}")
            print(f"   ⚠️  请妥善保管此 API Key，它只会显示一次！")
        except httpx.HTTPStatusError as e:
            print(f"❌ 创建 API Key 失败: {e}")
            return
        
        # 3. 使用 API Key 调用服务
        print(f"\n3. 使用 API Key 调用聊天服务...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat/completions",
                headers={"X-API-Key": api_key},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "user", "content": "你好，请用一句话介绍你自己"}
                    ],
                    "temperature": 0.7
                }
            )
            response.raise_for_status()
            chat_result = response.json()
            print("✅ 聊天请求成功!")
            print(f"   回答: {chat_result['choices'][0]['message']['content']}")
            print(f"   Token使用: {chat_result['usage']}")
        except httpx.HTTPStatusError as e:
            print(f"❌ 调用服务失败: {e}")
            if e.response.status_code == 401:
                print("   提示: API Key 验证失败，请检查数据库配置")
            return
        
        # 4. 测试无效的 API Key
        print(f"\n4. 测试无效的 API Key（应该失败）...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat/completions",
                headers={"X-API-Key": "invalid-key-12345"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "test"}]
                }
            )
            if response.status_code == 401:
                print("✅ 正确拒绝了无效的 API Key")
            else:
                print(f"⚠️  预期返回 401，但返回了 {response.status_code}")
        except Exception as e:
            print(f"❌ 测试失败: {e}")
        
        # 5. 查看统计信息
        print(f"\n5. 查看统计信息...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/admin/stats")
            response.raise_for_status()
            stats = response.json()
            print("✅ 统计信息:")
            print(f"   用户总数: {stats['users']['total']}")
            print(f"   活跃用户: {stats['users']['active']}")
            print(f"   API Key总数: {stats['api_keys']['total']}")
            print(f"   活跃API Key: {stats['api_keys']['active']}")
        except Exception as e:
            print(f"❌ 获取统计信息失败: {e}")
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(test_api_key_flow())
    except KeyboardInterrupt:
        print("\n测试中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)

