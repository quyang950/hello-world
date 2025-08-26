#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
灵活的测试用例标准化和去重处理器

特性：
1. 规则引擎 - 支持复杂的自定义规则
2. 模式学习 - 自动发现数据中的模式
3. 智能去重 - 多维度相似性分析
4. 增量处理 - 支持增量更新和版本管理
5. 可视化配置 - 交互式规则配置
"""

import json
import re
import hashlib
from typing import List, Dict, Set, Tuple, Any, Optional
from difflib import SequenceMatcher
from collections import defaultdict, Counter
import pickle
import datetime
from pathlib import Path


class RuleEngine:
    """规则引擎 - 支持复杂的标准化规则"""
    
    def __init__(self):
        self.rules = []
        self.rule_stats = defaultdict(int)  # 规则使用统计
    
    def add_rule(self, rule: Dict[str, Any]):
        """
        添加规则
        
        规则格式:
        {
            "name": "规则名称",
            "type": "replace|extract|transform",
            "pattern": "正则表达式或模式",
            "replacement": "替换内容",
            "condition": "应用条件",
            "priority": 优先级,
            "enabled": True/False
        }
        """
        rule['id'] = hashlib.md5(str(rule).encode()).hexdigest()[:8]
        rule['created'] = datetime.datetime.now().isoformat()
        self.rules.append(rule)
        self.rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
    
    def apply_rules(self, text: str, context: Dict = None) -> Tuple[str, List[str]]:
        """应用规则并返回处理结果和应用的规则列表"""
        result = text
        applied_rules = []
        
        for rule in self.rules:
            if not rule.get('enabled', True):
                continue
                
            # 检查应用条件
            if not self._check_condition(rule, text, context):
                continue
            
            original_result = result
            
            if rule['type'] == 'replace':
                result = self._apply_replace_rule(result, rule)
            elif rule['type'] == 'extract':
                result = self._apply_extract_rule(result, rule)
            elif rule['type'] == 'transform':
                result = self._apply_transform_rule(result, rule)
            
            if result != original_result:
                applied_rules.append(rule['name'])
                self.rule_stats[rule['id']] += 1
        
        return result, applied_rules
    
    def _check_condition(self, rule: Dict, text: str, context: Dict) -> bool:
        """检查规则应用条件"""
        condition = rule.get('condition')
        if not condition:
            return True
        
        # 支持多种条件类型
        if condition.get('field'):
            field_value = context.get(condition['field'], '') if context else ''
            return re.search(condition.get('pattern', ''), field_value) is not None
        
        if condition.get('contains'):
            return condition['contains'] in text
        
        if condition.get('regex'):
            return re.search(condition['regex'], text) is not None
        
        return True
    
    def _apply_replace_rule(self, text: str, rule: Dict) -> str:
        """应用替换规则"""
        pattern = rule['pattern']
        replacement = rule['replacement']
        flags = re.IGNORECASE if rule.get('case_insensitive', True) else 0
        return re.sub(pattern, replacement, text, flags=flags)
    
    def _apply_extract_rule(self, text: str, rule: Dict) -> str:
        """应用提取规则"""
        pattern = rule['pattern']
        matches = re.findall(pattern, text)
        if matches:
            return rule['replacement'].format(*matches)
        return text
    
    def _apply_transform_rule(self, text: str, rule: Dict) -> str:
        """应用转换规则"""
        # 支持自定义转换函数
        transform_func = rule.get('function')
        if transform_func == 'normalize_spaces':
            return ' '.join(text.split())
        elif transform_func == 'remove_duplicates':
            words = text.split()
            return ' '.join(dict.fromkeys(words))
        # 可以扩展更多转换函数
        return text


class PatternLearner:
    """模式学习器 - 自动发现数据中的模式"""
    
    def __init__(self):
        self.learned_patterns = defaultdict(list)
        self.entity_patterns = defaultdict(Counter)
        self.similarity_clusters = []
    
    def learn_from_data(self, test_cases: List[Dict]) -> Dict[str, Any]:
        """从数据中学习模式"""
        learning_result = {
            'database_patterns': self._learn_database_patterns(test_cases),
            'system_patterns': self._learn_system_patterns(test_cases),
            'template_patterns': self._learn_template_patterns(test_cases),
            'similarity_clusters': self._learn_similarity_clusters(test_cases)
        }
        
        return learning_result
    
    def _learn_database_patterns(self, test_cases: List[Dict]) -> List[Dict]:
        """学习数据库名称模式"""
        db_candidates = set()
        
        for case in test_cases:
            text = f"{case.get('case_name', '')} {case.get('description', '')} {' '.join(case.get('test_steps', []))}"
            
            # 查找可能的数据库名称
            # 常见模式：数据库名+数据库/DB/database
            patterns = [
                r'(\w+)(?:数据库|DB|database)',
                r'(?:连接|访问|操作)(\w+)',
                r'(\w+)(?:性能|测试|连接)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match) <= 15 and match.isalnum():  # 过滤太长或包含特殊字符的
                        db_candidates.add(match.lower())
        
        # 统计频率并生成建议
        db_suggestions = []
        for candidate in db_candidates:
            # 基于常见数据库名称判断是否为数据库
            known_dbs = ['mysql', 'oracle', 'postgres', 'mongodb', 'redis', 'og', 'opengauss']
            confidence = 0.5
            
            for known in known_dbs:
                if known in candidate.lower() or candidate.lower() in known:
                    confidence = 0.9
                    break
            
            db_suggestions.append({
                'candidate': candidate,
                'confidence': confidence,
                'suggested_standard': self._suggest_standard_name(candidate)
            })
        
        return sorted(db_suggestions, key=lambda x: x['confidence'], reverse=True)
    
    def _learn_system_patterns(self, test_cases: List[Dict]) -> List[Dict]:
        """学习系统名称模式"""
        system_patterns = Counter()
        
        for case in test_cases:
            case_name = case.get('case_name', '')
            
            # 查找系统名称模式
            patterns = [
                r'(\w+系统)',
                r'(\w+管理)',
                r'(\w+平台)',
                r'(\w+服务)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, case_name)
                for match in matches:
                    system_patterns[match] += 1
        
        # 生成抽象化建议
        suggestions = []
        for system, count in system_patterns.most_common():
            suggestions.append({
                'pattern': system,
                'frequency': count,
                'suggested_replacement': '【xxx】',
                'auto_generated_rule': {
                    'type': 'replace',
                    'pattern': re.escape(system),
                    'replacement': '【xxx】',
                    'name': f'抽象化{system}'
                }
            })
        
        return suggestions
    
    def _learn_template_patterns(self, test_cases: List[Dict]) -> List[Dict]:
        """学习测试用例模板模式"""
        templates = defaultdict(list)
        
        for case in test_cases:
            # 分析测试步骤的模式
            steps = case.get('test_steps', [])
            if len(steps) >= 3:  # 至少3个步骤才考虑模式
                # 提取步骤的关键词
                step_keywords = []
                for step in steps:
                    # 移除序号和标点
                    clean_step = re.sub(r'^\d+[\.、]?\s*', '', step)
                    keywords = re.findall(r'[\u4e00-\u9fff]+|\w+', clean_step)
                    step_keywords.append(keywords[:3])  # 取前3个关键词
                
                template_key = '|'.join(['_'.join(kw) for kw in step_keywords])
                templates[template_key].append(case)
        
        # 生成模板建议
        template_suggestions = []
        for template, cases in templates.items():
            if len(cases) >= 2:  # 至少2个用例使用相同模板
                template_suggestions.append({
                    'template': template,
                    'usage_count': len(cases),
                    'cases': [case.get('id') for case in cases],
                    'suggested_merge': len(cases) > 3  # 超过3个建议合并
                })
        
        return template_suggestions
    
    def _learn_similarity_clusters(self, test_cases: List[Dict]) -> List[Dict]:
        """学习相似性聚类"""
        clusters = []
        processed = set()
        
        for i, case1 in enumerate(test_cases):
            if i in processed:
                continue
            
            cluster = [case1]
            processed.add(i)
            
            for j, case2 in enumerate(test_cases[i+1:], i+1):
                if j in processed:
                    continue
                
                # 计算相似度
                similarity = self._calculate_advanced_similarity(case1, case2)
                if similarity > 0.7:  # 相似度阈值
                    cluster.append(case2)
                    processed.add(j)
            
            if len(cluster) > 1:
                clusters.append({
                    'cluster_id': len(clusters),
                    'size': len(cluster),
                    'cases': cluster,
                    'similarity_score': self._calculate_cluster_cohesion(cluster)
                })
        
        return clusters
    
    def _suggest_standard_name(self, candidate: str) -> str:
        """建议标准名称"""
        mapping = {
            'og': 'OpenGauss',
            'mysql': 'MySQL',
            'oracle': 'Oracle',
            'postgres': 'PostgreSQL',
            'mongodb': 'MongoDB',
            'redis': 'Redis'
        }
        return mapping.get(candidate.lower(), candidate.title())
    
    def _calculate_advanced_similarity(self, case1: Dict, case2: Dict) -> float:
        """计算高级相似度"""
        # 多维度相似性计算
        name_sim = SequenceMatcher(None, case1.get('case_name', ''), case2.get('case_name', '')).ratio()
        desc_sim = SequenceMatcher(None, case1.get('description', ''), case2.get('description', '')).ratio()
        
        steps1 = ' '.join(case1.get('test_steps', []))
        steps2 = ' '.join(case2.get('test_steps', []))
        steps_sim = SequenceMatcher(None, steps1, steps2).ratio()
        
        expected1 = case1.get('expected_result', '')
        expected2 = case2.get('expected_result', '')
        expected_sim = SequenceMatcher(None, expected1, expected2).ratio()
        
        # 加权计算
        return (name_sim * 0.2 + desc_sim * 0.2 + steps_sim * 0.4 + expected_sim * 0.2)
    
    def _calculate_cluster_cohesion(self, cluster: List[Dict]) -> float:
        """计算聚类内聚性"""
        if len(cluster) < 2:
            return 1.0
        
        total_similarity = 0
        pairs = 0
        
        for i in range(len(cluster)):
            for j in range(i+1, len(cluster)):
                total_similarity += self._calculate_advanced_similarity(cluster[i], cluster[j])
                pairs += 1
        
        return total_similarity / pairs if pairs > 0 else 0


class FlexibleTestCaseProcessor:
    """灵活的测试用例处理器"""
    
    def __init__(self, config_file: str = 'flexible_config.json'):
        self.rule_engine = RuleEngine()
        self.pattern_learner = PatternLearner()
        self.processing_history = []
        self.learned_knowledge = {}
        
        self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """加载配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 加载规则
            for rule in config.get('rules', []):
                self.rule_engine.add_rule(rule)
            
            self.settings = config.get('settings', {})
            print(f"已加载配置文件: {config_file}")
            print(f"加载规则数量: {len(self.rule_engine.rules)}")
            
        except FileNotFoundError:
            print(f"配置文件 {config_file} 不存在，将创建默认配置")
            self.create_default_config(config_file)
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误: {e}")
    
    def create_default_config(self, config_file: str):
        """创建默认配置"""
        default_config = {
            "settings": {
                "learning_enabled": True,
                "auto_apply_suggestions": False,
                "similarity_threshold": 0.85,
                "backup_enabled": True
            },
            "rules": [
                {
                    "name": "标准化OpenGauss",
                    "type": "replace",
                    "pattern": r"(?i)\bog\b",
                    "replacement": "OpenGauss",
                    "priority": 10,
                    "enabled": True
                },
                {
                    "name": "标准化MySQL",
                    "type": "replace", 
                    "pattern": r"(?i)\bmysql\b",
                    "replacement": "MySQL",
                    "priority": 10,
                    "enabled": True
                }
            ]
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
    
    def intelligent_process(self, input_file: str, output_file: str = None, 
                          learn_mode: bool = True) -> Dict[str, Any]:
        """智能处理模式"""
        
        # 1. 读取数据
        with open(input_file, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        print(f"读取到 {len(test_cases)} 个测试用例")
        
        # 2. 学习模式 - 发现数据中的模式
        if learn_mode:
            print("🧠 开始模式学习...")
            learning_result = self.pattern_learner.learn_from_data(test_cases)
            self.learned_knowledge = learning_result
            
            # 生成建议规则
            self._generate_suggested_rules(learning_result)
            
            # 显示学习结果
            self._display_learning_results(learning_result)
        
        # 3. 应用规则处理
        print("🔧 应用规则处理...")
        processed_cases = []
        rule_usage = defaultdict(int)
        
        for case in test_cases:
            processed_case = case.copy()
            
            # 处理各个字段
            for field in ['case_name', 'description', 'expected_result']:
                if field in processed_case:
                    original_text = processed_case[field]
                    processed_text, applied_rules = self.rule_engine.apply_rules(
                        original_text, context=case
                    )
                    processed_case[field] = processed_text
                    
                    for rule_name in applied_rules:
                        rule_usage[rule_name] += 1
            
            # 处理测试步骤
            if 'test_steps' in processed_case:
                new_steps = []
                for step in processed_case['test_steps']:
                    processed_step, applied_rules = self.rule_engine.apply_rules(
                        step, context=case
                    )
                    new_steps.append(processed_step)
                    
                    for rule_name in applied_rules:
                        rule_usage[rule_name] += 1
                
                processed_case['test_steps'] = new_steps
            
            processed_cases.append(processed_case)
        
        # 4. 智能去重
        print("🎯 智能去重处理...")
        unique_cases, duplicate_cases = self._intelligent_deduplication(processed_cases)
        
        # 5. 生成结果
        result = {
            'original_count': len(test_cases),
            'unique_count': len(unique_cases),
            'duplicate_count': len(duplicate_cases),
            'rule_usage': dict(rule_usage),
            'learning_results': self.learned_knowledge if learn_mode else {},
            'unique_cases': unique_cases,
            'duplicate_cases': duplicate_cases,
            'processing_timestamp': datetime.datetime.now().isoformat()
        }
        
        # 6. 保存结果
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"结果已保存到: {output_file}")
        
        return result
    
    def _generate_suggested_rules(self, learning_result: Dict):
        """基于学习结果生成建议规则"""
        print("\n💡 生成智能规则建议...")
        
        # 基于数据库模式生成规则
        for db_pattern in learning_result.get('database_patterns', []):
            if db_pattern['confidence'] > 0.7:
                suggested_rule = {
                    'name': f"标准化{db_pattern['candidate']}",
                    'type': 'replace',
                    'pattern': f"(?i)\\b{re.escape(db_pattern['candidate'])}\\b",
                    'replacement': db_pattern['suggested_standard'],
                    'priority': 8,
                    'enabled': False,  # 默认不启用，需要用户确认
                    'auto_generated': True,
                    'confidence': db_pattern['confidence']
                }
                print(f"  建议规则: {db_pattern['candidate']} -> {db_pattern['suggested_standard']}")
        
        # 基于系统模式生成规则
        for sys_pattern in learning_result.get('system_patterns', []):
            if sys_pattern['frequency'] >= 2:
                print(f"  建议抽象化: {sys_pattern['pattern']} (出现{sys_pattern['frequency']}次)")
    
    def _display_learning_results(self, learning_result: Dict):
        """显示学习结果"""
        print("\n📊 模式学习结果:")
        
        # 显示数据库模式
        db_patterns = learning_result.get('database_patterns', [])
        if db_patterns:
            print("  🗄️ 发现的数据库名称:")
            for pattern in db_patterns[:5]:  # 显示前5个
                print(f"    {pattern['candidate']} -> {pattern['suggested_standard']} (置信度: {pattern['confidence']:.2f})")
        
        # 显示系统模式
        sys_patterns = learning_result.get('system_patterns', [])
        if sys_patterns:
            print("  🏢 发现的系统名称模式:")
            for pattern in sys_patterns[:5]:
                print(f"    {pattern['pattern']} (出现{pattern['frequency']}次)")
        
        # 显示相似聚类
        clusters = learning_result.get('similarity_clusters', [])
        if clusters:
            print(f"  🔗 发现 {len(clusters)} 个相似用例群组")
            for cluster in clusters[:3]:
                print(f"    群组{cluster['cluster_id']}: {cluster['size']}个用例 (相似度: {cluster['similarity_score']:.2f})")
    
    def _intelligent_deduplication(self, test_cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """智能去重"""
        # 使用学习到的聚类信息进行去重
        if 'similarity_clusters' in self.learned_knowledge:
            clusters = self.learned_knowledge['similarity_clusters']
            
            unique_cases = []
            duplicate_cases = []
            processed_ids = set()
            
            for cluster in clusters:
                cluster_cases = cluster['cases']
                if len(cluster_cases) > 1:
                    # 选择最具代表性的用例作为唯一用例
                    representative = self._select_representative_case(cluster_cases)
                    unique_cases.append(representative)
                    
                    # 其他用例标记为重复
                    for case in cluster_cases:
                        case_id = case.get('id')
                        if case_id != representative.get('id'):
                            duplicate_cases.append(case)
                        processed_ids.add(case_id)
                else:
                    unique_cases.extend(cluster_cases)
                    for case in cluster_cases:
                        processed_ids.add(case.get('id'))
            
            # 添加未聚类的用例
            for case in test_cases:
                if case.get('id') not in processed_ids:
                    unique_cases.append(case)
            
            return unique_cases, duplicate_cases
        
        # 如果没有聚类信息，使用传统方法
        return self._traditional_deduplication(test_cases)
    
    def _select_representative_case(self, cases: List[Dict]) -> Dict:
        """选择最具代表性的用例"""
        # 选择描述最完整的用例
        best_case = cases[0]
        best_score = 0
        
        for case in cases:
            score = 0
            score += len(case.get('description', ''))
            score += len(' '.join(case.get('test_steps', [])))
            score += len(case.get('expected_result', ''))
            
            if score > best_score:
                best_score = score
                best_case = case
        
        return best_case
    
    def _traditional_deduplication(self, test_cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """传统去重方法"""
        unique_cases = []
        duplicate_cases = []
        
        for case in test_cases:
            is_duplicate = False
            
            for unique_case in unique_cases:
                similarity = self.pattern_learner._calculate_advanced_similarity(case, unique_case)
                if similarity > self.settings.get('similarity_threshold', 0.85):
                    duplicate_cases.append(case)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_cases.append(case)
        
        return unique_cases, duplicate_cases
    
    def interactive_rule_builder(self):
        """交互式规则构建器"""
        print("🛠️ 交互式规则构建器")
        print("基于学习结果，您可以选择以下操作:")
        
        if not self.learned_knowledge:
            print("请先运行学习模式以发现数据模式")
            return
        
        # 显示建议并让用户选择
        db_patterns = self.learned_knowledge.get('database_patterns', [])
        if db_patterns:
            print("\n数据库名称标准化建议:")
            for i, pattern in enumerate(db_patterns):
                print(f"{i+1}. {pattern['candidate']} -> {pattern['suggested_standard']} (置信度: {pattern['confidence']:.2f})")
        
        sys_patterns = self.learned_knowledge.get('system_patterns', [])
        if sys_patterns:
            print("\n系统名称抽象化建议:")
            for i, pattern in enumerate(sys_patterns):
                print(f"{i+1}. {pattern['pattern']} -> 【xxx】 (频率: {pattern['frequency']})")
        
        # 这里可以扩展为真正的交互式界面
        print("\n💡 提示: 在实际应用中，这里可以实现Web界面或命令行交互来让用户选择规则")


if __name__ == "__main__":
    processor = FlexibleTestCaseProcessor()
    
    # 智能处理示例
    result = processor.intelligent_process(
        input_file='test_cases_example.json',
        output_file='flexible_result.json',
        learn_mode=True
    )
    
    # 交互式规则构建
    processor.interactive_rule_builder()
    
    print(f"\n✅ 处理完成! 去重率: {result['duplicate_count']/result['original_count']*100:.1f}%")