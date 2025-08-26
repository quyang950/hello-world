#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例标准化和去重处理工具 - 命令行版本

用法示例:
python cli_processor.py -i test_cases.json -o result.json -c config.json -t 0.8
"""

import argparse
import sys
import os
import json
from test_case_processor import TestCaseProcessor


def main():
    parser = argparse.ArgumentParser(
        description='测试用例标准化和去重处理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s -i test_cases.json -o processed_result.json
  %(prog)s -i test_cases.json -o result.json -c my_config.json -t 0.8
  %(prog)s --input data.json --output result.json --threshold 0.9

注意事项:
  - 输入文件必须是UTF-8编码的JSON格式
  - 相似度阈值范围: 0.0-1.0，值越高去重越严格
  - 配置文件格式请参考config.json示例
        """
    )
    
    # 必需参数
    parser.add_argument(
        '-i', '--input', 
        required=True, 
        help='输入测试用例文件路径（JSON格式）'
    )
    
    # 可选参数
    parser.add_argument(
        '-o', '--output', 
        help='输出文件路径（默认: processed_<输入文件名>）'
    )
    
    parser.add_argument(
        '-c', '--config', 
        default='config.json', 
        help='配置文件路径（默认: config.json）'
    )
    
    parser.add_argument(
        '-t', '--threshold', 
        type=float, 
        default=None,
        help='相似度阈值 0.0-1.0（默认: 使用配置文件中的值）'
    )
    
    parser.add_argument(
        '--show-duplicates',
        action='store_true',
        help='显示重复用例的详细信息'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='不创建输入文件的备份'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # 生成默认输出文件名
    if not args.output:
        input_name = os.path.splitext(os.path.basename(args.input))[0]
        args.output = f"processed_{input_name}.json"
    
    # 验证相似度阈值
    if args.threshold is not None:
        if not 0.0 <= args.threshold <= 1.0:
            print(f"错误: 相似度阈值必须在0.0-1.0之间，当前值: {args.threshold}", file=sys.stderr)
            sys.exit(1)
    
    try:
        # 创建输入文件备份
        if not args.no_backup:
            backup_file = f"{args.input}.backup"
            if not os.path.exists(backup_file):
                import shutil
                shutil.copy2(args.input, backup_file)
                if args.verbose:
                    print(f"已创建备份文件: {backup_file}")
        
        # 初始化处理器
        processor = TestCaseProcessor(args.config)
        
        # 使用命令行指定的阈值（如果有）
        threshold = args.threshold if args.threshold is not None else processor.similarity_threshold
        
        if args.verbose:
            print(f"输入文件: {args.input}")
            print(f"输出文件: {args.output}")
            print(f"配置文件: {args.config}")
            print(f"相似度阈值: {threshold}")
            print("-" * 50)
        
        # 处理测试用例
        result = processor.process_test_cases(
            input_file=args.input,
            output_file=args.output,
            similarity_threshold=threshold
        )
        
        # 显示处理结果
        processor.print_summary(result)
        
        # 显示重复用例详情
        if args.show_duplicates and result['duplicate_cases']:
            print("\n" + "="*50)
            print("重复用例详细信息")
            print("="*50)
            for i, case in enumerate(result['duplicate_cases'], 1):
                print(f"\n{i}. 用例ID: {case['id']}")
                print(f"   原始名称: {case.get('case_name', 'N/A')}")
                print(f"   通用名称: {case.get('generalized_name', 'N/A')}")
                print(f"   内容哈希: {case.get('content_hash', 'N/A')}")
        
        print(f"\n✅ 处理完成！结果已保存到: {args.output}")
        
    except FileNotFoundError as e:
        print(f"错误: 文件未找到 - {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON格式错误 - {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: 处理过程中发生异常 - {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()