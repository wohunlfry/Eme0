#!/usr/bin/env python3
"""Eme0 情绪引擎主入口程序"""
import asyncio
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, 'src')

from eme0.mcp_server import main as mcp_main


if __name__ == "__main__":
    print("启动 Eme0 情绪引擎...")
    asyncio.run(mcp_main())