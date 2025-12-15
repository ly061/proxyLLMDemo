"""
数据库连接和初始化 - MySQL版本
"""
import aiomysql
from typing import AsyncGenerator, Optional, List
from datetime import datetime
from app.config import settings
from app.utils.logger import logger


# 全局连接池
_pool: Optional[aiomysql.Pool] = None


async def get_pool() -> aiomysql.Pool:
    """获取数据库连接池"""
    global _pool
    if _pool is None:
        # 验证必需的配置
        if not settings.MYSQL_USER or not settings.MYSQL_PASSWORD:
            raise ValueError(
                "MySQL用户名和密码必须通过环境变量配置。"
                "请设置 MYSQL_USER 和 MYSQL_PASSWORD 环境变量。"
            )
        
        _pool = await aiomysql.create_pool(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            db=settings.MYSQL_DATABASE,
            charset=settings.MYSQL_CHARSET,
            minsize=1,
            maxsize=settings.MYSQL_POOL_SIZE,
            autocommit=False
        )
        logger.info(f"MySQL连接池创建成功: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    return _pool


async def close_pool():
    """关闭数据库连接池"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
        logger.info("MySQL连接池已关闭")


async def get_db() -> AsyncGenerator[aiomysql.Connection, None]:
    """
    获取数据库连接（依赖注入）
    
    Yields:
        数据库连接
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def init_db():
    """
    初始化数据库，创建表结构
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            # 创建用户表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    INDEX idx_username (username),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建API Key表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    api_key VARCHAR(255) UNIQUE NOT NULL,
                    key_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP NULL,
                    expires_at TIMESTAMP NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_api_key (api_key),
                    INDEX idx_user_id (user_id),
                    INDEX idx_api_key_active (api_key, is_active),
                    INDEX idx_expires_at (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建请求记录表（用于记录token消耗）
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    api_key_id INT NOT NULL,
                    user_id INT NOT NULL,
                    model VARCHAR(100) NOT NULL,
                    user_query TEXT,
                    prompt_tokens INT DEFAULT 0,
                    completion_tokens INT DEFAULT 0,
                    total_tokens INT DEFAULT 0,
                    request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_api_key_id (api_key_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_request_time (request_time),
                    INDEX idx_model (model)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建会话表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    api_key_id INT NOT NULL,
                    title VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
                    INDEX idx_user_id (user_id),
                    INDEX idx_api_key_id (api_key_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            # 创建会话消息表
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    conversation_id INT NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                    INDEX idx_conversation_id (conversation_id),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            
            await conn.commit()
            logger.info(f"数据库初始化完成: {settings.MYSQL_DATABASE}")


async def check_api_key(api_key: str) -> Optional[dict]:
    """
    检查API Key是否有效
    
    Args:
        api_key: 要检查的API Key
        
    Returns:
        包含用户信息的字典，如果无效返回None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("""
                SELECT 
                    ak.id,
                    ak.user_id,
                    ak.api_key,
                    ak.key_name,
                    ak.last_used_at,
                    ak.expires_at,
                    ak.is_active,
                    u.user_name as username,
                    u.email,
                    1 as user_is_active
                FROM api_keys ak
                JOIN users u ON ak.user_id = u.id
                WHERE ak.api_key = %s AND ak.is_active = TRUE
            """, (api_key,))
            
            row = await cursor.fetchone()
            if row:
                # 检查是否过期
                if row['expires_at']:
                    expires_at = row['expires_at']
                    if isinstance(expires_at, datetime):
                        if datetime.now(expires_at.tzinfo if expires_at.tzinfo else None) > expires_at:
                            return None
                    elif isinstance(expires_at, str):
                        try:
                            expires_at_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                            if datetime.now(expires_at_dt.tzinfo) > expires_at_dt:
                                return None
                        except (ValueError, AttributeError):
                            pass
                
                # 更新最后使用时间（异步，不阻塞）
                await cursor.execute("""
                    UPDATE api_keys 
                    SET last_used_at = NOW() 
                    WHERE id = %s
                """, (row['id'],))
                await conn.commit()
                
                return {
                    'id': row['id'],
                    'api_key_id': row['id'],
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'email': row['email'],
                    'key_name': row['key_name'],
                    'api_key': row['api_key']
                }
            return None


async def record_request(
    api_key_id: int,
    user_id: int,
    model: str,
    user_query: Optional[str] = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0
):
    """
    记录API请求的token消耗情况（异步后台任务）
    
    Args:
        api_key_id: API Key的ID
        user_id: 用户ID
        model: 使用的模型名称
        user_query: 用户的问题/消息内容
        prompt_tokens: 提示token数
        completion_tokens: 完成token数
        total_tokens: 总token数
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO api_requests 
                    (api_key_id, user_id, model, user_query, prompt_tokens, completion_tokens, total_tokens)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (api_key_id, user_id, model, user_query, prompt_tokens, completion_tokens, total_tokens))
                await conn.commit()
    except Exception as e:
        logger.error(f"记录token消耗失败: {str(e)}")


# ==================== 会话管理相关函数 ====================

async def create_conversation(
    user_id: int,
    api_key_id: int,
    title: Optional[str] = None
) -> int:
    """
    创建新会话
    
    Args:
        user_id: 用户ID
        api_key_id: API Key ID
        title: 会话标题（可选，如果不提供则自动生成）
        
    Returns:
        会话ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if not title:
                title = "新对话"
            await cursor.execute("""
                INSERT INTO conversations (user_id, api_key_id, title)
                VALUES (%s, %s, %s)
            """, (user_id, api_key_id, title))
            await conn.commit()
            return cursor.lastrowid


async def get_conversation(
    conversation_id: int,
    user_id: Optional[int] = None,
    api_key_id: Optional[int] = None
) -> Optional[dict]:
    """
    获取会话信息
    
    Args:
        conversation_id: 会话ID
        user_id: 用户ID（用于权限验证）
        api_key_id: API Key ID（用于权限验证）
        
    Returns:
        会话信息字典，如果不存在或无权访问返回None
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = "SELECT * FROM conversations WHERE id = %s"
            params = [conversation_id]
            
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            if api_key_id is not None:
                query += " AND api_key_id = %s"
                params.append(api_key_id)
            
            await cursor.execute(query, tuple(params))
            return await cursor.fetchone()


async def get_conversation_messages(
    conversation_id: int,
    limit: Optional[int] = None
) -> List[dict]:
    """
    获取会话的所有消息
    
    Args:
        conversation_id: 会话ID
        limit: 限制返回数量（可选）
        
    Returns:
        消息列表
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = """
                SELECT id, role, content, created_at
                FROM conversation_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC
            """
            params = [conversation_id]
            
            if limit:
                query += " LIMIT %s"
                params.append(limit)
            
            await cursor.execute(query, tuple(params))
            return await cursor.fetchall()


async def add_message_to_conversation(
    conversation_id: int,
    role: str,
    content: str
) -> int:
    """
    添加消息到会话
    
    Args:
        conversation_id: 会话ID
        role: 消息角色（user, assistant, system）
        content: 消息内容
        
    Returns:
        消息ID
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO conversation_messages (conversation_id, role, content)
                VALUES (%s, %s, %s)
            """, (conversation_id, role, content))
            await conn.commit()
            return cursor.lastrowid


async def update_conversation_title(
    conversation_id: int,
    title: str,
    user_id: Optional[int] = None,
    api_key_id: Optional[int] = None
) -> bool:
    """
    更新会话标题
    
    Args:
        conversation_id: 会话ID
        title: 新标题
        user_id: 用户ID（用于权限验证）
        api_key_id: API Key ID（用于权限验证）
        
    Returns:
        是否更新成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = "UPDATE conversations SET title = %s WHERE id = %s"
            params = [title, conversation_id]
            
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            if api_key_id is not None:
                query += " AND api_key_id = %s"
                params.append(api_key_id)
            
            await cursor.execute(query, tuple(params))
            await conn.commit()
            return cursor.rowcount > 0


async def delete_conversation(
    conversation_id: int,
    user_id: Optional[int] = None,
    api_key_id: Optional[int] = None
) -> bool:
    """
    删除会话（级联删除所有消息）
    
    Args:
        conversation_id: 会话ID
        user_id: 用户ID（用于权限验证）
        api_key_id: API Key ID（用于权限验证）
        
    Returns:
        是否删除成功
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            query = "DELETE FROM conversations WHERE id = %s"
            params = [conversation_id]
            
            if user_id is not None:
                query += " AND user_id = %s"
                params.append(user_id)
            if api_key_id is not None:
                query += " AND api_key_id = %s"
                params.append(api_key_id)
            
            await cursor.execute(query, tuple(params))
            await conn.commit()
            return cursor.rowcount > 0


async def list_conversations(
    user_id: int,
    api_key_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0
) -> tuple[List[dict], int]:
    """
    获取用户的会话列表
    
    Args:
        user_id: 用户ID
        api_key_id: API Key ID（可选，用于过滤）
        limit: 返回数量
        offset: 偏移量
        
    Returns:
        (会话列表, 总数)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            # 构建查询条件
            where_clause = "WHERE user_id = %s"
            params = [user_id]
            
            if api_key_id is not None:
                where_clause += " AND api_key_id = %s"
                params.append(api_key_id)
            
            # 获取总数
            count_query = f"SELECT COUNT(*) as total FROM conversations {where_clause}"
            await cursor.execute(count_query, tuple(params))
            total_result = await cursor.fetchone()
            total = total_result['total'] if total_result else 0
            
            # 获取会话列表（包含消息数量）
            list_query = f"""
                SELECT 
                    c.id as conversation_id,
                    c.title,
                    c.created_at,
                    c.updated_at,
                    COUNT(cm.id) as message_count
                FROM conversations c
                LEFT JOIN conversation_messages cm ON c.id = cm.conversation_id
                {where_clause}
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                LIMIT %s OFFSET %s
            """
            params.extend([limit, offset])
            await cursor.execute(list_query, tuple(params))
            conversations = await cursor.fetchall()
            
            return conversations, total
