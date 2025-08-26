#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例标准化和去重处理工具

功能：
1. 标准化数据库组件名称
2. 去重相似的测试用例
3. 生成标准化的测试用例集
"""

import json
import re
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher
import hashlib


class TestCaseProcessor:
    def __init__(self, config_file: str = 'config.json'):
        # 加载配置文件
        self.load_config(config_file)

    def load_config(self, config_file: str):
        """
        加载配置文件
        
        Args:
            config_file: 配置文件路径
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.db_name_mapping = config.get('database_name_mapping', {})
            self.system_patterns = [pattern for pattern in config.get('system_name_patterns', [])]
            self.similarity_threshold = config.get('similarity_threshold', 0.85)
            self.replacement_placeholder = config.get('replacement_placeholder', '【xxx】')
            
            print(f"已加载配置文件: {config_file}")
            print(f"数据库映射规则: {len(self.db_name_mapping)} 条")
            print(f"系统名称模式: {len(self.system_patterns)} 个")
            
        except FileNotFoundError:
            print(f"警告: 配置文件 {config_file} 不存在，使用默认配置")
            self._load_default_config()
        except json.JSONDecodeError as e:
            print(f"错误: 配置文件格式错误 - {e}")
            self._load_default_config()

    def _load_default_config(self):
        """加载默认配置"""
        self.db_name_mapping = {
            'og': 'OpenGauss',
            'openguass': 'OpenGauss',
            'open-gauss': 'OpenGauss',
            'opengauss': 'OpenGauss',
            'mysql': 'MySQL',
            'MYSQL': 'MySQL',
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'pg': 'PostgreSQL',
            'oracle': 'Oracle',
            'sqlserver': 'SQL Server',
            'sql-server': 'SQL Server',
            'mongodb': 'MongoDB',
            'mongo': 'MongoDB',
            'redis': 'Redis',
            'elasticsearch': 'Elasticsearch',
            'es': 'Elasticsearch',
        }
        
        self.system_patterns = [
            r'订单系统', r'用户管理系统', r'库存管理系统', r'支付系统',
            r'商品管理系统', r'财务系统', r'客服系统', r'报表系统',
            r'审计系统', r'权限管理系统', r'消息系统', r'通知系统'
        ]
        
        self.similarity_threshold = 0.85
        self.replacement_placeholder = '【xxx】'

    def standardize_db_names(self, text: str) -> str:
        """
        标准化数据库组件名称
        
        Args:
            text: 待处理的文本
            
        Returns:
            标准化后的文本
        """
        # 处理中英文混合文本的数据库名称替换
        for old_name, standard_name in self.db_name_mapping.items():
            # 创建更灵活的匹配模式
            # 对于英文数据库名称，考虑前后可能是中文字符、空格或标点符号
            escaped_name = re.escape(old_name)
            
            # 使用前瞻和后顾断言，确保匹配独立的数据库名称
            # (?<![a-zA-Z0-9]) 确保前面不是字母或数字
            # (?![a-zA-Z0-9]) 确保后面不是字母或数字
            pattern = f'(?<![a-zA-Z0-9]){escaped_name}(?![a-zA-Z0-9])'
            text = re.sub(pattern, standard_name, text, flags=re.IGNORECASE)
        
        return text

    def generalize_system_names(self, case_name: str) -> str:
        """
        将具体的系统名称通用化为【xxx】
        
        Args:
            case_name: 用例名称
            
        Returns:
            通用化后的用例名称
        """
        generalized_name = case_name
        
        # 替换具体的系统名称为通用标识
        for pattern in self.system_patterns:
            generalized_name = re.sub(pattern, self.replacement_placeholder, generalized_name)
        
        return generalized_name

    def calculate_similarity(self, steps1: List[str], steps2: List[str], 
                           expected1: str, expected2: str) -> float:
        """
        计算两个测试用例的相似度
        
        Args:
            steps1, steps2: 测试步骤列表
            expected1, expected2: 预期结果
            
        Returns:
            相似度分数 (0-1)
        """
        # 比较测试步骤
        steps_text1 = ' '.join(steps1)
        steps_text2 = ' '.join(steps2)
        steps_similarity = SequenceMatcher(None, steps_text1, steps_text2).ratio()
        
        # 比较预期结果
        expected_similarity = SequenceMatcher(None, expected1, expected2).ratio()
        
        # 综合相似度 (测试步骤权重70%，预期结果权重30%)
        overall_similarity = steps_similarity * 0.7 + expected_similarity * 0.3
        
        return overall_similarity

    def create_case_hash(self, steps: List[str], expected_result: str) -> str:
        """
        为测试用例创建哈希值，用于快速去重
        
        Args:
            steps: 测试步骤
            expected_result: 预期结果
            
        Returns:
            哈希值
        """
        # 标准化步骤和结果文本
        normalized_steps = [self.standardize_db_names(step.lower().strip()) for step in steps]
        normalized_expected = self.standardize_db_names(expected_result.lower().strip())
        
        # 创建内容字符串
        content = '|'.join(normalized_steps) + '|' + normalized_expected
        
        # 生成MD5哈希
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def standardize_test_case(self, test_case: Dict) -> Dict:
        """
        标准化单个测试用例
        
        Args:
            test_case: 原始测试用例
            
        Returns:
            标准化后的测试用例
        """
        standardized_case = test_case.copy()
        
        # 标准化用例名称
        standardized_case['case_name'] = self.standardize_db_names(test_case['case_name'])
        
        # 标准化描述
        standardized_case['description'] = self.standardize_db_names(test_case['description'])
        
        # 标准化测试步骤
        standardized_case['test_steps'] = [
            self.standardize_db_names(step) for step in test_case['test_steps']
        ]
        
        # 标准化预期结果
        standardized_case['expected_result'] = self.standardize_db_names(test_case['expected_result'])
        
        # 添加通用化的用例名称
        standardized_case['generalized_name'] = self.generalize_system_names(
            standardized_case['case_name']
        )
        
        # 添加用例哈希值
        standardized_case['content_hash'] = self.create_case_hash(
            standardized_case['test_steps'],
            standardized_case['expected_result']
        )
        
        return standardized_case

    def deduplicate_test_cases(self, test_cases: List[Dict], 
                             similarity_threshold: float = 0.85) -> Tuple[List[Dict], List[Dict]]:
        """
        去重测试用例
        
        Args:
            test_cases: 测试用例列表
            similarity_threshold: 相似度阈值
            
        Returns:
            (去重后的用例列表, 重复用例列表)
        """
        unique_cases = []
        duplicate_cases = []
        processed_hashes = set()
        
        for case in test_cases:
            content_hash = case['content_hash']
            
            # 基于哈希值的快速去重
            if content_hash in processed_hashes:
                duplicate_cases.append(case)
                continue
                
            # 检查与已有用例的相似度
            is_duplicate = False
            for unique_case in unique_cases:
                similarity = self.calculate_similarity(
                    case['test_steps'], unique_case['test_steps'],
                    case['expected_result'], unique_case['expected_result']
                )
                
                if similarity >= similarity_threshold:
                    duplicate_cases.append(case)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_cases.append(case)
                processed_hashes.add(content_hash)
        
        return unique_cases, duplicate_cases

    def process_test_cases(self, input_file: str, output_file: str = None, 
                          similarity_threshold: float = 0.85) -> Dict:
        """
        处理测试用例文件
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径（可选）
            similarity_threshold: 去重相似度阈值
            
        Returns:
            处理结果统计
        """
        # 读取测试用例
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        print(f"读取到 {len(test_cases)} 个测试用例")
        
        # 标准化测试用例
        print("正在标准化测试用例...")
        standardized_cases = [self.standardize_test_case(case) for case in test_cases]
        
        # 去重
        print("正在去重测试用例...")
        unique_cases, duplicate_cases = self.deduplicate_test_cases(
            standardized_cases, similarity_threshold
        )
        
        # 生成处理结果
        result = {
            'original_count': len(test_cases),
            'unique_count': len(unique_cases),
            'duplicate_count': len(duplicate_cases),
            'unique_cases': unique_cases,
            'duplicate_cases': duplicate_cases
        }
        
        # 保存结果
        if output_file:
            output_data = {
                'summary': {
                    'original_count': result['original_count'],
                    'unique_count': result['unique_count'],
                    'duplicate_count': result['duplicate_count'],
                    'similarity_threshold': similarity_threshold
                },
                'unique_cases': unique_cases,
                'duplicate_cases': duplicate_cases
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"处理结果已保存到: {output_file}")
        
        return result

    def print_summary(self, result: Dict):
        """
        打印处理结果摘要
        
        Args:
            result: 处理结果
        """
        print("\n" + "="*50)
        print("测试用例处理结果摘要")
        print("="*50)
        print(f"原始用例数量: {result['original_count']}")
        print(f"去重后数量: {result['unique_count']}")
        print(f"重复用例数量: {result['duplicate_count']}")
        print(f"去重率: {result['duplicate_count']/result['original_count']*100:.1f}%")
        
        if result['duplicate_cases']:
            print("\n重复用例列表:")
            for i, case in enumerate(result['duplicate_cases'], 1):
                print(f"{i}. {case['case_name']}")
        
        print("\n" + "="*50)


if __name__ == "__main__":
    processor = TestCaseProcessor()
    
    # 处理示例数据
    result = processor.process_test_cases(
        input_file='test_cases_example.json',
        output_file='processed_test_cases.json',
        similarity_threshold=0.85
    )
    
    # 打印处理结果摘要
    processor.print_summary(result)