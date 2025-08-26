#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版模式发现原理演示

展示自动模式发现的核心原理，无需外部依赖库
"""

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict


def demonstrate_pattern_discovery():
    """演示模式发现的完整过程"""
    
    print("🔍 自动模式发现原理演示")
    print("="*60)
    
    # 示例测试用例数据
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
    
    print(f"📊 输入数据: {len(test_cases)} 个测试用例\n")
    
    # 步骤1: 数据预处理
    print("🔧 步骤1: 数据预处理")
    print("-" * 30)
    
    all_texts = []
    for case in test_cases:
        combined_text = f"{case['case_name']} {case['description']}"
        all_texts.append(combined_text)
        print(f"ID {case['id']}: {combined_text}")
    
    print(f"\n✅ 提取了 {len(all_texts)} 个文本片段\n")
    
    # 步骤2: 数据库名称模式发现
    print("🗄️ 步骤2: 数据库名称模式发现")
    print("-" * 30)
    
    db_candidates = defaultdict(lambda: {'frequency': 0, 'contexts': []})
    
    # 定义正则模式
    db_patterns = [
        (r'(\w+)(?:数据库|DB|database)', '数据库后缀模式'),
        (r'(?:连接|访问|操作)(\w+)', '动作前缀模式'),
        (r'(\w+)(?:性能|测试|连接)', '功能后缀模式')
    ]
    
    print("正在使用以下模式搜索:")
    for pattern, name in db_patterns:
        print(f"  • {name}: {pattern}")
    
    print("\n搜索结果:")
    for text in all_texts:
        for pattern, pattern_name in db_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match_lower = match.lower()
                db_candidates[match_lower]['frequency'] += 1
                db_candidates[match_lower]['contexts'].append(f"{text[:50]}...")
                print(f"  找到: '{match}' (使用{pattern_name}) 在 \"{text[:40]}...\"")
    
    # 计算置信度
    print(f"\n📊 候选数据库名称分析:")
    known_databases = ['mysql', 'oracle', 'postgresql', 'mongodb', 'redis', 'opengauss', 'og']
    
    for candidate, info in db_candidates.items():
        if info['frequency'] >= 1:  # 至少出现1次
            # 频次得分
            frequency_score = min(1.0, info['frequency'] / 3.0) * 0.3
            
            # 已知数据库匹配得分
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
            match_score *= 0.4
            
            # 上下文得分
            context_keywords = ['数据库', '连接', '性能', '测试']
            context_score = 0
            for context in info['contexts']:
                for keyword in context_keywords:
                    if keyword in context:
                        context_score += 0.1
            context_score = min(1.0, context_score) * 0.3
            
            total_confidence = frequency_score + match_score + context_score
            
            # 建议标准名称
            standard_mapping = {
                'og': 'OpenGauss',
                'mysql': 'MySQL',
                'oracle': 'Oracle'
            }
            suggested_standard = standard_mapping.get(candidate, candidate.title())
            
            confidence_icon = "🟢" if total_confidence > 0.7 else "🟡" if total_confidence > 0.4 else "🔴"
            print(f"  {confidence_icon} {candidate} → {suggested_standard}")
            print(f"     频次: {info['frequency']}, 置信度: {total_confidence:.3f}")
            print(f"     分解: 频次({frequency_score:.2f}) + 匹配({match_score:.2f}) + 上下文({context_score:.2f})")
            if best_match:
                print(f"     最佳匹配: {best_match}")
            print()
    
    # 步骤3: 系统名称模式发现
    print("🏢 步骤3: 系统名称模式发现")
    print("-" * 30)
    
    system_candidates = defaultdict(int)
    system_suffixes = ['系统', '管理', '平台', '服务']
    
    print("正在搜索系统名称模式...")
    for case in test_cases:
        case_name = case['case_name']
        print(f"分析: \"{case_name}\"")
        
        # 提取中文词汇
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', case_name)
        print(f"  中文词汇: {chinese_words}")
        
        for word in chinese_words:
            # 检查是否包含系统相关后缀
            for suffix in system_suffixes:
                if word.endswith(suffix) and len(word) > len(suffix):
                    system_candidates[word] += 1
                    print(f"  找到系统名称: {word}")
                    break
    
    print(f"\n📊 系统名称模式统计:")
    for system, frequency in system_candidates.items():
        if frequency >= 1:
            coverage = frequency / len(test_cases)
            confidence = min(1.0, frequency / len(test_cases) * 3)
            confidence_icon = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
            
            print(f"  {confidence_icon} {system} → 【xxx】")
            print(f"     频次: {frequency}, 覆盖率: {coverage:.1%}, 置信度: {confidence:.3f}")
    
    # 步骤4: 生成推荐规则
    print("\n🎯 步骤4: 生成智能推荐")
    print("-" * 30)
    
    print("📋 推荐的标准化规则:")
    
    # 数据库规则
    db_rules = []
    for candidate, info in db_candidates.items():
        if info['frequency'] >= 2:  # 至少出现2次
            frequency_score = min(1.0, info['frequency'] / 3.0) * 0.3
            # 简化置信度计算
            confidence = frequency_score + 0.4  # 基础置信度
            if confidence > 0.6:
                standard_name = {'og': 'OpenGauss', 'mysql': 'MySQL'}.get(candidate, candidate.title())
                db_rules.append({
                    'type': 'replace',
                    'pattern': f'\\b{candidate}\\b',
                    'replacement': standard_name,
                    'confidence': confidence
                })
                print(f"  🔧 替换规则: {candidate} → {standard_name} (置信度: {confidence:.2f})")
    
    # 系统规则
    sys_rules = []
    for system, frequency in system_candidates.items():
        if frequency >= 2:
            confidence = min(1.0, frequency / len(test_cases) * 2)
            if confidence > 0.5:
                sys_rules.append({
                    'type': 'replace', 
                    'pattern': system,
                    'replacement': '【xxx】',
                    'confidence': confidence
                })
                print(f"  🔧 抽象化规则: {system} → 【xxx】 (置信度: {confidence:.2f})")
    
    # 步骤5: 应用演示
    print(f"\n🧪 步骤5: 规则应用演示")
    print("-" * 30)
    
    print("应用标准化规则前后对比:")
    for case in test_cases[:3]:  # 只演示前3个
        original = case['case_name']
        processed = original
        
        # 应用数据库规则
        for rule in db_rules:
            processed = re.sub(rule['pattern'], rule['replacement'], processed, flags=re.IGNORECASE)
        
        # 应用系统规则
        for rule in sys_rules:
            processed = processed.replace(rule['pattern'], rule['replacement'])
        
        print(f"  原文: {original}")
        print(f"  处理: {processed}")
        if original != processed:
            print(f"    ✅ 发生了变化")
        else:
            print(f"    ➖ 无变化")
        print()
    
    # 总结
    print("🎯 总结")
    print("-" * 30)
    
    total_db_patterns = len([c for c, info in db_candidates.items() if info['frequency'] >= 1])
    total_sys_patterns = len([s for s, f in system_candidates.items() if f >= 1])
    high_conf_rules = len(db_rules) + len(sys_rules)
    
    print(f"✅ 发现了 {total_db_patterns} 个数据库名称模式")
    print(f"✅ 发现了 {total_sys_patterns} 个系统名称模式") 
    print(f"✅ 生成了 {high_conf_rules} 个高置信度的推荐规则")
    print(f"📊 数据处理覆盖率: {high_conf_rules / len(test_cases) * 100:.1f}%")
    
    print(f"\n💡 核心原理总结:")
    print(f"   1. 🔍 使用正则表达式模式匹配识别候选词汇")
    print(f"   2. 📊 通过频次统计发现高频模式")
    print(f"   3. 🧠 结合上下文和已知知识计算置信度")
    print(f"   4. 🎯 基于置信度生成智能推荐")
    print(f"   5. ⚙️ 自动生成可应用的处理规则")
    
    print(f"\n🚀 这就是自动模式发现的核心工作原理！")


if __name__ == "__main__":
    demonstrate_pattern_discovery()