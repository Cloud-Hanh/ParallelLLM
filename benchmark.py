"""
LLM性能基准测试工具
"""
import os
import time
import asyncio
import json
import logging
from datetime import datetime
from typing import List
from pllm import Client

class Benchmark:
    """性能基准测试工具"""
    
    def __init__(self, config_path: str, output_dir: str = "output/benchmark"):
        """
        初始化基准测试工具
        
        Args:
            config_path: 客户端配置文件路径
            output_dir: 测试结果输出目录
        """
        self.client = Client(config_path)
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 配置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("Benchmark")

    def generate_questions(self, n: int) -> List[str]:
        """
        生成测试问题集
        
        Args:
            n: 问题数量
            
        Returns:
            包含n个测试问题的列表
        """
        base_question = "请用300字左右解释什么是{}"
        topics = [
            "机器学习", "深度学习", "神经网络",
            "自然语言处理", "计算机视觉", "强化学习"
        ]
        return [base_question.format(topics[i % len(topics)]) for i in range(n)]

    async def parallel_test(self, questions: List[str], workers: int = 10) -> dict:
        """
        并行测试
        
        Args:
            questions: 问题列表
            workers: 最大并发数
            
        Returns:
            测试结果字典
        """
        start_time = time.perf_counter()
        
        # 分批处理避免内存溢出
        batch_size = workers
        results = []
        failed = 0
        
        for i in range(0, len(questions), batch_size):
            batch = questions[i:i+batch_size]
            tasks = [self.client.generate(q) for q in batch]
            
            try:
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                results.extend(batch_results)
            except Exception as e:
                self.logger.error(f"批量请求失败: {str(e)}")
                failed += len(batch)
        
        total_time = time.perf_counter() - start_time
        success = len(results) - failed
        
        return {
            "mode": "parallel",
            "total_questions": len(questions),
            "success": success,
            "failed": failed,
            "total_time": round(total_time, 2),
            "qps": round(success / total_time, 2) if total_time > 0 else 0
        }

    async def sequential_test(self, questions: List[str]) -> dict:
        """
        顺序测试
        
        Args:
            questions: 问题列表
            
        Returns:
            测试结果字典
        """
        start_time = time.perf_counter()
        success = 0
        failed = 0
        
        for q in questions:
            try:
                await self.client.generate(q)
                success += 1
            except Exception as e:
                self.logger.error(f"请求失败: {str(e)}")
                failed += 1
        
        total_time = time.perf_counter() - start_time
        
        return {
            "mode": "sequential",
            "total_questions": len(questions),
            "success": success,
            "failed": failed,
            "total_time": round(total_time, 2),
            "qps": round(success / total_time, 2) if total_time > 0 else 0
        }

    def generate_report(self, results: dict, model_name: str) -> str:
        """
        生成测试报告
        
        Args:
            results: 测试结果数据
            model_name: 模型名称
            
        Returns:
            格式化后的报告字符串
        """
        # 基础报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "results": results,
            "stats": self.client.get_stats()
        }
        
        # 保存文件
        filename = f"benchmark_{model_name}_{datetime.now().strftime('%Y%m%d%H%M')}.json"
        path = os.path.join(self.output_dir, filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        return path

async def main():
    """测试执行入口"""
    # 配置测试参数
    TEST_CONFIG = "input/config/base.yaml"
    QUESTIONS_NUM = 20  # 总测试问题数
    WORKERS = 10         # 最大并发数
    
    benchmark = Benchmark(TEST_CONFIG)
    questions = benchmark.generate_questions(QUESTIONS_NUM)
    
    # 执行并行测试
    parallel_result = await benchmark.parallel_test(questions, WORKERS)
    
    # 执行顺序测试（需要重置客户端统计）
    benchmark.client = Client(TEST_CONFIG)
    sequential_result = await benchmark.sequential_test(questions)
    
    # 生成报告
    report_path = benchmark.generate_report(
        results={"parallel": parallel_result, "sequential": sequential_result},
        model_name="your-model-name"  # 从配置中获取实际模型名称
    )
    
    print(f"测试报告已保存至：{report_path}")

if __name__ == "__main__":
    asyncio.run(main())
