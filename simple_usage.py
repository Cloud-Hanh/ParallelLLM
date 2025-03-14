import asyncio
from pllm import Client

async def main():
    # 初始化客户端
    client = Client("input/config/base.yaml")
    
    # 异步生成文本
    response = await client.generate("解释一下量子计算的基本原理")
    print(response)
    
    # 使用聊天接口
    chat_response = await client.chat([
        {"role": "system", "content": "你是一个有用的AI助手。"},
        {"role": "user", "content": "写一个Python函数计算斐波那契数列。"}
    ])
    print(chat_response["choices"][0]["message"]["content"])
    
    # 查看使用统计
    print(client.get_stats())

# 对于不支持异步的环境，可以使用同步接口
def sync_example():
    client = Client("input/config/base.yaml")
    response = client.generate_sync("什么是机器学习？")
    print(response)

if __name__ == "__main__":
    # 运行异步示例
    asyncio.run(main())
    
    # 或者运行同步示例
    # sync_example() 