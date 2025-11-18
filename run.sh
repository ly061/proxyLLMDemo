#!/bin/bash

# LLM代理服务启动脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  LLM代理服务启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3，请先安装Python${NC}"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo -e "${YELLOW}警告: 未找到虚拟环境，建议创建虚拟环境${NC}"
    read -p "是否创建虚拟环境? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 -m venv venv
        source venv/bin/activate
        echo -e "${GREEN}虚拟环境已创建并激活${NC}"
    fi
else
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    echo -e "${GREEN}虚拟环境已激活${NC}"
fi

# 检查依赖是否安装
if ! python3 -c "import fastapi" &> /dev/null; then
    echo -e "${YELLOW}检测到缺少依赖，正在安装...${NC}"
    pip install -r requirements.txt --timeout 90000
    if [ $? -ne 0 ]; then
        echo -e "${RED}依赖安装失败，请检查requirements.txt${NC}"
        exit 1
    fi
    echo -e "${GREEN}依赖安装完成${NC}"
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}警告: 未找到.env配置文件${NC}"
    if [ -f ".env.example" ]; then
        read -p "是否从.env.example创建.env文件? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            echo -e "${GREEN}.env文件已创建，请编辑配置后再启动${NC}"
            echo -e "${YELLOW}提示: 至少需要配置 DEEPSEEK_API_KEY 和 API_KEYS${NC}"
            exit 0
        fi
    fi
fi

# 启动服务
echo -e "${GREEN}正在启动服务...${NC}"
echo -e "${GREEN}服务地址: http://localhost:8000${NC}"
echo -e "${GREEN}API文档: http://localhost:8000/docs${NC}"
echo -e "${GREEN}按 Ctrl+C 停止服务${NC}"
echo ""

# 使用uvicorn启动
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

