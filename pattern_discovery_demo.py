#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式发现原理演示程序

这个程序展示了自动模式发现的完整过程，包括：
1. 数据预处理
2. 候选模式提取
3. 置信度计算
4. 结果可视化
"""

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from matplotlib.font_manager import FontProperties

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class PatternDiscoveryDemo:
    """模式发现演示类"""
    
    def __init__(self):
        self.debug_info = {}
        self.visualization_data = {}
    
    def run_complete_demo(self, test_cases: List[Dict]):
        """运行完整的模式发现演示"""
        
        print("🔍 开始模式发现演示")
        print("=" * 60)
        
        # 步骤1：数据预处理
        print("\n📝 步骤1: 数据预处理")
        preprocessed_data = self.preprocess_data(test_cases)
        self.display_preprocessing_results(preprocessed_data)
        
        # 步骤2：数据库名称发现
        print("\n🗄️ 步骤2: 数据库名称模式发现")
        db_patterns = self.discover_database_patterns(test_cases)
        self.display_database_patterns(db_patterns)
        
        # 步骤3：系统名称发现
        print("\n🏢 步骤3: 系统名称模式发现")
        system_patterns = self.discover_system_patterns(test_cases)
        self.display_system_patterns(system_patterns)
        
        # 步骤4：置信度分析
        print("\n📊 步骤4: 置信度分析")
        confidence_analysis = self.analyze_confidence(db_patterns, system_patterns)
        self.display_confidence_analysis(confidence_analysis)
        
        # 步骤5：生成可视化
        print("\n📈 步骤5: 生成可视化图表")
        self.create_visualizations()
        
        print("\n✅ 模式发现演示完成！")
        return {
            'database_patterns': db_patterns,
            'system_patterns': system_patterns,
            'confidence_analysis': confidence_analysis
        }
    
    def preprocess_data(self, test_cases: List[Dict]) -> Dict:
        """数据预处理"""
        
        preprocessed = {
            'original_texts': [],
            'cleaned_texts': [],
            'tokens': [],
            'statistics': {}
        }
        
        for case in test_cases:
            # 原始文本
            original = f"{case.get('case_name', '')} {case.get('description', '')} {' '.join(case.get('test_steps', []))} {case.get('expected_result', '')}"
            preprocessed['original_texts'].append(original)
            
            # 清理文本
            cleaned = self.clean_text(original)
            preprocessed['cleaned_texts'].append(cleaned)
            
            # 分词
            tokens = self.tokenize(cleaned)
            preprocessed['tokens'].append(tokens)
        
        # 统计信息
        all_tokens = [token for tokens in preprocessed['tokens'] for token in tokens]
        preprocessed['statistics'] = {
            'total_cases': len(test_cases),
            'total_tokens': len(all_tokens),
            'unique_tokens': len(set(all_tokens)),
            'avg_tokens_per_case': len(all_tokens) / len(test_cases) if test_cases else 0
        }
        
        self.debug_info['preprocessing'] = preprocessed
        return preprocessed
    
    def clean_text(self, text: str) -> str:
        """文本清理"""
        # 转为小写
        text = text.lower()
        # 移除标点符号
        text = re.sub(r'[^\u4e00-\u9fff\w\s]', ' ', text)
        # 压缩空格
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def tokenize(self, text: str) -> List[str]:
        """分词"""
        # 中英文分词
        tokens = re.findall(r'[\u4e00-\u9fff]+|\w+', text)
        # 过滤长度
        tokens = [token for token in tokens if 1 < len(token) < 15]
        return tokens
    
    def discover_database_patterns(self, test_cases: List[Dict]) -> List[Dict]:
        """发现数据库名称模式"""
        
        candidates = defaultdict(lambda: {
            'frequency': 0,
            'contexts': [],
            'confidence_factors': {}
        })
        
        # 定义数据库相关的正则模式
        db_patterns = [
            (r'(\w+)(?:数据库|DB|database)', '数据库后缀模式'),
            (r'(?:连接|访问|操作)(\w+)', '动作前缀模式'),
            (r'(\w+)(?:性能|测试|连接)', '功能后缀模式'),
            (r'(?:使用|部署|配置)(\w+)', '部署前缀模式')
        ]
        
        for case in test_cases:
            combined_text = f"{case.get('case_name', '')} {case.get('description', '')}"
            
            for pattern, pattern_name in db_patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE)
                
                for match in matches:
                    match_lower = match.lower()
                    candidates[match_lower]['frequency'] += 1
                    candidates[match_lower]['contexts'].append({
                        'text': combined_text,
                        'pattern_used': pattern_name,
                        'case_id': case.get('id', 'unknown')
                    })
        
        # 计算置信度
        known_databases = ['mysql', 'oracle', 'postgresql', 'mongodb', 'redis', 'sqlite', 'opengauss']
        
        db_patterns_result = []
        for candidate, info in candidates.items():
            if info['frequency'] >= 2:  # 至少出现2次
                confidence = self.calculate_db_confidence(candidate, info, known_databases)
                
                db_patterns_result.append({
                    'candidate': candidate,
                    'frequency': info['frequency'],
                    'confidence': confidence['total'],
                    'confidence_breakdown': confidence['factors'],
                    'contexts': info['contexts'][:3],  # 只保留前3个上下文示例
                    'suggested_standard': self.suggest_standard_db_name(candidate, known_databases)
                })
        
        # 按置信度排序
        db_patterns_result.sort(key=lambda x: x['confidence'], reverse=True)
        self.debug_info['database_patterns'] = db_patterns_result
        return db_patterns_result
    
    def calculate_db_confidence(self, candidate: str, info: Dict, known_databases: List[str]) -> Dict:
        """计算数据库名称的置信度"""
        
        factors = {}
        
        # 1. 频次因子 (权重: 30%)
        frequency_score = min(1.0, info['frequency'] / 5.0)
        factors['frequency'] = {'score': frequency_score, 'weight': 0.3, 'description': f'出现{info["frequency"]}次'}
        
        # 2. 已知数据库匹配 (权重: 40%)
        match_score = 0
        best_match = None
        for known_db in known_databases:
            if known_db == candidate:
                match_score = 1.0
                best_match = known_db
                break
            elif known_db in candidate or candidate in known_db:
                similarity = len(set(known_db) & set(candidate)) / len(set(known_db) | set(candidate))
                if similarity > match_score:
                    match_score = similarity
                    best_match = known_db
        
        factors['known_match'] = {
            'score': match_score, 
            'weight': 0.4, 
            'description': f'与已知数据库"{best_match}"匹配度: {match_score:.2f}' if best_match else '无已知匹配'
        }
        
        # 3. 上下文相关性 (权重: 30%)
        context_keywords = ['数据库', '连接', '查询', '性能', '测试', 'db', 'database', '配置', '访问']
        context_score = 0
        context_matches = []
        
        for context_info in info['contexts']:
            context_text = context_info['text'].lower()
            for keyword in context_keywords:
                if keyword in context_text:
                    context_score += 0.1
                    if keyword not in context_matches:
                        context_matches.append(keyword)
        
        context_score = min(1.0, context_score)
        factors['context'] = {
            'score': context_score, 
            'weight': 0.3, 
            'description': f'上下文匹配关键词: {context_matches}'
        }
        
        # 计算总置信度
        total_confidence = sum(factor['score'] * factor['weight'] for factor in factors.values())
        
        return {
            'total': total_confidence,
            'factors': factors
        }
    
    def suggest_standard_db_name(self, candidate: str, known_databases: List[str]) -> str:
        """建议标准数据库名称"""
        
        standard_mapping = {
            'og': 'OpenGauss',
            'mysql': 'MySQL', 
            'oracle': 'Oracle',
            'postgresql': 'PostgreSQL',
            'postgres': 'PostgreSQL',
            'pg': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'mongo': 'MongoDB',
            'redis': 'Redis',
            'sqlite': 'SQLite'
        }
        
        return standard_mapping.get(candidate.lower(), candidate.title())
    
    def discover_system_patterns(self, test_cases: List[Dict]) -> List[Dict]:
        """发现系统名称模式"""
        
        system_candidates = defaultdict(int)
        case_distribution = defaultdict(list)
        
        # 系统名称相关的后缀
        system_suffixes = ['系统', '管理', '平台', '服务', '模块', '中心', '门户']
        
        for case in test_cases:
            case_name = case.get('case_name', '')
            
            # 提取中文词汇
            chinese_words = re.findall(r'[\u4e00-\u9fff]+', case_name)
            
            for i, word in enumerate(chinese_words):
                # 检查是否包含系统相关后缀
                for suffix in system_suffixes:
                    if word.endswith(suffix) and len(word) > len(suffix):
                        system_candidates[word] += 1
                        case_distribution[word].append(case.get('id', f'case_{i}'))
                        break
                
                # 检查组合模式 "xxx + 系统/管理/..."
                if i < len(chinese_words) - 1:
                    next_word = chinese_words[i + 1]
                    if next_word in system_suffixes:
                        combined = word + next_word
                        system_candidates[combined] += 1
                        case_distribution[combined].append(case.get('id', f'case_{i}'))
        
        # 生成系统模式结果
        system_patterns_result = []
        total_cases = len(test_cases)
        
        for system, frequency in system_candidates.items():
            if frequency >= 2:  # 至少出现2次
                confidence = min(1.0, frequency / total_cases * 3)  # 频率越高置信度越高
                
                system_patterns_result.append({
                    'pattern': system,
                    'frequency': frequency,
                    'confidence': confidence,
                    'coverage': frequency / total_cases,
                    'cases': case_distribution[system],
                    'suggested_replacement': '【xxx】'
                })
        
        system_patterns_result.sort(key=lambda x: x['confidence'], reverse=True)
        self.debug_info['system_patterns'] = system_patterns_result
        return system_patterns_result
    
    def analyze_confidence(self, db_patterns: List[Dict], system_patterns: List[Dict]) -> Dict:
        """分析整体置信度分布"""
        
        analysis = {
            'database_confidence_dist': [p['confidence'] for p in db_patterns],
            'system_confidence_dist': [p['confidence'] for p in system_patterns],
            'high_confidence_db': [p for p in db_patterns if p['confidence'] > 0.8],
            'high_confidence_system': [p for p in system_patterns if p['confidence'] > 0.8],
            'recommendation_summary': {}
        }
        
        # 生成推荐总结
        analysis['recommendation_summary'] = {
            'total_db_patterns': len(db_patterns),
            'recommended_db_patterns': len(analysis['high_confidence_db']),
            'total_system_patterns': len(system_patterns),
            'recommended_system_patterns': len(analysis['high_confidence_system']),
            'overall_quality': 'High' if (len(analysis['high_confidence_db']) + len(analysis['high_confidence_system'])) > 3 else 'Medium'
        }
        
        return analysis
    
    def display_preprocessing_results(self, preprocessed: Dict):
        """显示预处理结果"""
        
        stats = preprocessed['statistics']
        print(f"   📊 处理了 {stats['total_cases']} 个测试用例")
        print(f"   📝 提取了 {stats['total_tokens']} 个词汇（{stats['unique_tokens']} 个不重复）")
        print(f"   📈 平均每个用例 {stats['avg_tokens_per_case']:.1f} 个词汇")
        
        # 显示前3个处理示例
        print(f"\n   🔍 处理示例:")
        for i in range(min(3, len(preprocessed['original_texts']))):
            original = preprocessed['original_texts'][i][:50] + "..." if len(preprocessed['original_texts'][i]) > 50 else preprocessed['original_texts'][i]
            cleaned = preprocessed['cleaned_texts'][i][:50] + "..." if len(preprocessed['cleaned_texts'][i]) > 50 else preprocessed['cleaned_texts'][i]
            tokens = preprocessed['tokens'][i][:8]
            
            print(f"     {i+1}. 原文: {original}")
            print(f"        清理: {cleaned}")
            print(f"        分词: {tokens}...")
    
    def display_database_patterns(self, db_patterns: List[Dict]):
        """显示数据库模式发现结果"""
        
        if not db_patterns:
            print("   ❌ 未发现数据库名称模式")
            return
        
        print(f"   🎯 发现 {len(db_patterns)} 个潜在数据库名称:")
        
        for i, pattern in enumerate(db_patterns[:5], 1):  # 只显示前5个
            confidence_color = "🟢" if pattern['confidence'] > 0.8 else "🟡" if pattern['confidence'] > 0.5 else "🔴"
            print(f"     {i}. {confidence_color} {pattern['candidate']} → {pattern['suggested_standard']}")
            print(f"        频次: {pattern['frequency']}, 置信度: {pattern['confidence']:.3f}")
            
            # 显示置信度分解
            for factor_name, factor_info in pattern['confidence_breakdown'].items():
                print(f"          {factor_name}: {factor_info['score']:.2f} × {factor_info['weight']} = {factor_info['score'] * factor_info['weight']:.3f}")
            
            # 显示上下文示例
            if pattern['contexts']:
                print(f"        上下文示例: \"{pattern['contexts'][0]['text'][:60]}...\"")
            print()
    
    def display_system_patterns(self, system_patterns: List[Dict]):
        """显示系统模式发现结果"""
        
        if not system_patterns:
            print("   ❌ 未发现系统名称模式")
            return
        
        print(f"   🎯 发现 {len(system_patterns)} 个系统名称模式:")
        
        for i, pattern in enumerate(system_patterns[:5], 1):
            confidence_color = "🟢" if pattern['confidence'] > 0.8 else "🟡" if pattern['confidence'] > 0.5 else "🔴"
            print(f"     {i}. {confidence_color} {pattern['pattern']} → {pattern['suggested_replacement']}")
            print(f"        频次: {pattern['frequency']}, 覆盖率: {pattern['coverage']:.1%}, 置信度: {pattern['confidence']:.3f}")
            print(f"        出现在用例: {pattern['cases'][:3]}...")
            print()
    
    def display_confidence_analysis(self, analysis: Dict):
        """显示置信度分析"""
        
        summary = analysis['recommendation_summary']
        print(f"   📊 分析结果:")
        print(f"     数据库模式: {summary['recommended_db_patterns']}/{summary['total_db_patterns']} 个高置信度")
        print(f"     系统模式: {summary['recommended_system_patterns']}/{summary['total_system_patterns']} 个高置信度")
        print(f"     整体质量: {summary['overall_quality']}")
        
        if analysis['high_confidence_db']:
            print(f"\n   🔥 推荐的数据库标准化规则:")
            for pattern in analysis['high_confidence_db']:
                print(f"     • {pattern['candidate']} → {pattern['suggested_standard']} (置信度: {pattern['confidence']:.3f})")
        
        if analysis['high_confidence_system']:
            print(f"\n   🔥 推荐的系统抽象化规则:")
            for pattern in analysis['high_confidence_system']:
                print(f"     • {pattern['pattern']} → {pattern['suggested_replacement']} (置信度: {pattern['confidence']:.3f})")
    
    def create_visualizations(self):
        """创建可视化图表"""
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('模式发现结果可视化', fontsize=16, fontweight='bold')
        
        # 1. 数据库模式置信度分布
        if 'database_patterns' in self.debug_info and self.debug_info['database_patterns']:
            db_data = self.debug_info['database_patterns']
            db_names = [p['candidate'] for p in db_data[:8]]
            db_confidences = [p['confidence'] for p in db_data[:8]]
            
            bars1 = axes[0, 0].bar(range(len(db_names)), db_confidences, 
                                  color=['green' if c > 0.8 else 'orange' if c > 0.5 else 'red' for c in db_confidences])
            axes[0, 0].set_title('数据库名称置信度', fontweight='bold')
            axes[0, 0].set_ylabel('置信度')
            axes[0, 0].set_xticks(range(len(db_names)))
            axes[0, 0].set_xticklabels(db_names, rotation=45, ha='right')
            axes[0, 0].set_ylim(0, 1)
            
            # 添加数值标签
            for i, (bar, conf) in enumerate(zip(bars1, db_confidences)):
                axes[0, 0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                               f'{conf:.2f}', ha='center', va='bottom', fontsize=9)
        else:
            axes[0, 0].text(0.5, 0.5, '未发现数据库模式', ha='center', va='center', transform=axes[0, 0].transAxes)
            axes[0, 0].set_title('数据库名称置信度')
        
        # 2. 系统模式频次分布
        if 'system_patterns' in self.debug_info and self.debug_info['system_patterns']:
            sys_data = self.debug_info['system_patterns']
            sys_names = [p['pattern'] for p in sys_data[:8]]
            sys_frequencies = [p['frequency'] for p in sys_data[:8]]
            
            bars2 = axes[0, 1].bar(range(len(sys_names)), sys_frequencies, color='skyblue')
            axes[0, 1].set_title('系统名称出现频次', fontweight='bold')
            axes[0, 1].set_ylabel('频次')
            axes[0, 1].set_xticks(range(len(sys_names)))
            axes[0, 1].set_xticklabels(sys_names, rotation=45, ha='right')
            
            # 添加数值标签
            for bar, freq in zip(bars2, sys_frequencies):
                axes[0, 1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                               str(freq), ha='center', va='bottom', fontsize=9)
        else:
            axes[0, 1].text(0.5, 0.5, '未发现系统模式', ha='center', va='center', transform=axes[0, 1].transAxes)
            axes[0, 1].set_title('系统名称出现频次')
        
        # 3. 置信度分布饼图
        if 'database_patterns' in self.debug_info and self.debug_info['database_patterns']:
            db_data = self.debug_info['database_patterns']
            confidence_ranges = {'高 (>0.8)': 0, '中 (0.5-0.8)': 0, '低 (<0.5)': 0}
            
            for pattern in db_data:
                conf = pattern['confidence']
                if conf > 0.8:
                    confidence_ranges['高 (>0.8)'] += 1
                elif conf > 0.5:
                    confidence_ranges['中 (0.5-0.8)'] += 1
                else:
                    confidence_ranges['低 (<0.5)'] += 1
            
            # 过滤为0的项
            filtered_ranges = {k: v for k, v in confidence_ranges.items() if v > 0}
            
            if filtered_ranges:
                colors = ['#2ecc71', '#f39c12', '#e74c3c'][:len(filtered_ranges)]
                axes[1, 0].pie(filtered_ranges.values(), labels=filtered_ranges.keys(), 
                              autopct='%1.0f%%', colors=colors, startangle=90)
                axes[1, 0].set_title('数据库模式置信度分布', fontweight='bold')
            else:
                axes[1, 0].text(0.5, 0.5, '无数据', ha='center', va='center')
        else:
            axes[1, 0].text(0.5, 0.5, '无数据', ha='center', va='center')
            axes[1, 0].set_title('数据库模式置信度分布')
        
        # 4. 处理流程图 (简化的文本展示)
        if 'preprocessing' in self.debug_info:
            stats = self.debug_info['preprocessing']['statistics']
            
            # 创建处理流程的文本展示
            flow_text = f"""数据预处理流程:
            
输入: {stats['total_cases']} 个测试用例
  ↓
文本清理和分词
  ↓
提取 {stats['total_tokens']} 个词汇
  ↓
模式识别和分析
  ↓
输出: 标准化建议"""
            
            axes[1, 1].text(0.1, 0.9, flow_text, transform=axes[1, 1].transAxes, 
                           fontsize=11, va='top', ha='left',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue", alpha=0.7))
            axes[1, 1].set_title('处理流程', fontweight='bold')
            axes[1, 1].axis('off')
        
        plt.tight_layout()
        plt.savefig('pattern_discovery_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"   📊 可视化图表已保存为: pattern_discovery_analysis.png")


def main():
    """主演示函数"""
    
    # 加载测试数据
    try:
        with open('test_cases_example.json', 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        # 如果没有测试文件，创建示例数据
        test_cases = [
            {
                "id": 1,
                "case_name": "订单系统数据库og连接测试",
                "description": "验证订单系统与og数据库的连接功能",
                "test_steps": ["1. 启动订单系统服务", "2. 配置og数据库连接参数", "3. 测试数据库连接"],
                "expected_result": "系统能够成功连接到og数据库"
            },
            {
                "id": 2,
                "case_name": "用户管理系统og性能测试",
                "description": "测试用户管理系统中og数据库的性能表现",
                "test_steps": ["1. 启动用户管理系统", "2. 配置并发测试参数", "3. 执行性能测试"],
                "expected_result": "og数据库响应时间满足要求"
            },
            {
                "id": 3,
                "case_name": "库存管理系统mysql连接验证",
                "description": "检查库存管理系统与mysql数据库的连接状态",
                "test_steps": ["1. 启动库存管理系统", "2. 验证mysql连接", "3. 测试基本操作"],
                "expected_result": "mysql数据库连接正常"
            },
            {
                "id": 4,
                "case_name": "支付系统数据库连接测试",
                "description": "验证支付系统与数据库的连接",
                "test_steps": ["1. 启动支付系统", "2. 测试数据库连接", "3. 验证事务处理"],
                "expected_result": "数据库连接稳定"
            },
            {
                "id": 5,
                "case_name": "报表系统mysql性能测试",
                "description": "测试报表系统mysql数据库查询性能",
                "test_steps": ["1. 启动报表系统", "2. 执行复杂查询", "3. 监控性能指标"],
                "expected_result": "mysql查询性能达标"
            }
        ]
    
    print("🚀 模式发现原理演示程序")
    print("This demo shows how automatic pattern discovery works step by step\n")
    
    # 创建演示实例并运行
    demo = PatternDiscoveryDemo()
    results = demo.run_complete_demo(test_cases)
    
    # 输出最终总结
    print("\n" + "="*60)
    print("🎯 演示总结")
    print("="*60)
    
    db_count = len(results['database_patterns'])
    sys_count = len(results['system_patterns'])
    high_conf_db = len([p for p in results['database_patterns'] if p['confidence'] > 0.8])
    high_conf_sys = len([p for p in results['system_patterns'] if p['confidence'] > 0.8])
    
    print(f"✅ 自动发现了 {db_count} 个数据库名称模式（{high_conf_db} 个高置信度）")
    print(f"✅ 自动发现了 {sys_count} 个系统名称模式（{high_conf_sys} 个高置信度）")
    print(f"✅ 生成了 {high_conf_db + high_conf_sys} 个推荐的标准化规则")
    print("\n💡 这展示了系统如何从原始数据中自动学习和发现有意义的模式！")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(f"❌ 缺少依赖库: {e}")
        print("请安装: pip install matplotlib seaborn pandas numpy")
    except Exception as e:
        print(f"❌ 演示运行出错: {e}")
        print("请检查数据文件和环境配置")