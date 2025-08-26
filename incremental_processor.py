#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量测试用例处理器 - 支持版本管理和增量更新

特性：
1. 版本管理 - 跟踪处理历史和变更
2. 增量处理 - 只处理新增或修改的用例
3. 回滚支持 - 可以回退到任意历史版本
4. 变更检测 - 智能识别用例变化
5. 持久化存储 - 保存处理状态和历史
"""

import json
import hashlib
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pickle
import shutil
from flexible_processor import FlexibleTestCaseProcessor


class VersionManager:
    """版本管理器"""
    
    def __init__(self, workspace_dir: str = '.testcase_workspace'):
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(exist_ok=True)
        
        self.db_path = self.workspace_dir / 'versions.db'
        self.versions_dir = self.workspace_dir / 'versions'
        self.versions_dir.mkdir(exist_ok=True)
        
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建版本表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_tag TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                description TEXT,
                file_path TEXT NOT NULL,
                metadata TEXT,
                parent_version TEXT
            )
        ''')
        
        # 创建用例变更表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                case_id TEXT NOT NULL,
                change_type TEXT NOT NULL,  -- 'added', 'modified', 'deleted'
                old_hash TEXT,
                new_hash TEXT,
                change_details TEXT,
                FOREIGN KEY (version_id) REFERENCES versions (id)
            )
        ''')
        
        # 创建处理历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id INTEGER NOT NULL,
                processor_config TEXT,
                rules_applied TEXT,
                original_count INTEGER,
                unique_count INTEGER,
                duplicate_count INTEGER,
                processing_time REAL,
                created_at TEXT,
                FOREIGN KEY (version_id) REFERENCES versions (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_version(self, data: List[Dict], description: str = "", 
                      parent_version: Optional[str] = None) -> str:
        """创建新版本"""
        timestamp = datetime.now()
        version_tag = f"v{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # 保存数据文件
        version_file = self.versions_dir / f"{version_tag}.json"
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 计算元数据
        metadata = {
            'total_cases': len(data),
            'case_hashes': {str(case.get('id', i)): self._calculate_case_hash(case) 
                           for i, case in enumerate(data)}
        }
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO versions (version_tag, created_at, description, file_path, metadata, parent_version)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (version_tag, timestamp.isoformat(), description, str(version_file), 
              json.dumps(metadata), parent_version))
        
        version_id = cursor.lastrowid
        
        # 如果有父版本，计算变更
        if parent_version:
            self._calculate_changes(cursor, version_id, parent_version, metadata)
        
        conn.commit()
        conn.close()
        
        return version_tag
    
    def _calculate_case_hash(self, case: Dict) -> str:
        """计算用例哈希值"""
        # 排除ID和时间戳等不稳定字段
        stable_fields = ['case_name', 'description', 'test_steps', 'expected_result']
        content = {}
        for field in stable_fields:
            if field in case:
                content[field] = case[field]
        
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(content_str.encode('utf-8')).hexdigest()
    
    def _calculate_changes(self, cursor, version_id: int, parent_version: str, 
                          current_metadata: Dict):
        """计算版本间的变更"""
        # 获取父版本元数据
        cursor.execute('SELECT metadata FROM versions WHERE version_tag = ?', (parent_version,))
        result = cursor.fetchone()
        if not result:
            return
        
        parent_metadata = json.loads(result[0])
        parent_hashes = parent_metadata.get('case_hashes', {})
        current_hashes = current_metadata.get('case_hashes', {})
        
        # 检测新增的用例
        for case_id, case_hash in current_hashes.items():
            if case_id not in parent_hashes:
                cursor.execute('''
                    INSERT INTO case_changes (version_id, case_id, change_type, new_hash)
                    VALUES (?, ?, 'added', ?)
                ''', (version_id, case_id, case_hash))
            elif parent_hashes[case_id] != case_hash:
                cursor.execute('''
                    INSERT INTO case_changes (version_id, case_id, change_type, old_hash, new_hash, change_details)
                    VALUES (?, ?, 'modified', ?, ?, ?)
                ''', (version_id, case_id, parent_hashes[case_id], case_hash, 'Content modified'))
        
        # 检测删除的用例
        for case_id, case_hash in parent_hashes.items():
            if case_id not in current_hashes:
                cursor.execute('''
                    INSERT INTO case_changes (version_id, case_id, change_type, old_hash)
                    VALUES (?, ?, 'deleted', ?)
                ''', (version_id, case_id, case_hash))
    
    def get_versions(self) -> List[Dict]:
        """获取所有版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT version_tag, created_at, description, metadata, parent_version
            FROM versions ORDER BY created_at DESC
        ''')
        
        versions = []
        for row in cursor.fetchall():
            metadata = json.loads(row[3]) if row[3] else {}
            versions.append({
                'version_tag': row[0],
                'created_at': row[1],
                'description': row[2],
                'total_cases': metadata.get('total_cases', 0),
                'parent_version': row[4]
            })
        
        conn.close()
        return versions
    
    def get_version_data(self, version_tag: str) -> Optional[List[Dict]]:
        """获取指定版本的数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT file_path FROM versions WHERE version_tag = ?', (version_tag,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        with open(result[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_changes(self, version_tag: str) -> List[Dict]:
        """获取版本变更记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT cc.case_id, cc.change_type, cc.old_hash, cc.new_hash, cc.change_details
            FROM case_changes cc
            JOIN versions v ON cc.version_id = v.id
            WHERE v.version_tag = ?
        ''', (version_tag,))
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'case_id': row[0],
                'change_type': row[1],
                'old_hash': row[2],
                'new_hash': row[3],
                'change_details': row[4]
            })
        
        conn.close()
        return changes
    
    def save_processing_history(self, version_tag: str, config: Dict, result: Dict):
        """保存处理历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取版本ID
        cursor.execute('SELECT id FROM versions WHERE version_tag = ?', (version_tag,))
        version_result = cursor.fetchone()
        if not version_result:
            conn.close()
            return
        
        version_id = version_result[0]
        
        cursor.execute('''
            INSERT INTO processing_history 
            (version_id, processor_config, rules_applied, original_count, unique_count, 
             duplicate_count, processing_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            version_id,
            json.dumps(config),
            json.dumps(result.get('rule_usage', {})),
            result.get('original_count', 0),
            result.get('unique_count', 0),
            result.get('duplicate_count', 0),
            result.get('processing_time', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()


class IncrementalProcessor:
    """增量处理器"""
    
    def __init__(self, workspace_dir: str = '.testcase_workspace'):
        self.version_manager = VersionManager(workspace_dir)
        self.processor = FlexibleTestCaseProcessor()
        self.workspace_dir = Path(workspace_dir)
        
        # 创建增量处理状态文件
        self.state_file = self.workspace_dir / 'incremental_state.json'
        self.load_state()
    
    def load_state(self):
        """加载增量处理状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                'last_processed_version': None,
                'baseline_version': None,
                'processing_config': {}
            }
    
    def save_state(self):
        """保存增量处理状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def process_new_data(self, data: List[Dict], description: str = "",
                        incremental: bool = True) -> Dict:
        """处理新数据"""
        start_time = datetime.now()
        
        # 创建新版本
        parent_version = self.state['last_processed_version'] if incremental else None
        version_tag = self.version_manager.create_version(data, description, parent_version)
        
        print(f"📦 创建版本: {version_tag}")
        
        if incremental and parent_version:
            # 增量处理：只处理变更的用例
            changes = self.version_manager.get_changes(version_tag)
            print(f"🔄 检测到 {len(changes)} 项变更")
            
            # 获取需要重新处理的用例
            changed_cases = self._get_changed_cases(data, changes)
            baseline_data = self._get_baseline_data()
            
            if changed_cases:
                print(f"⚡ 增量处理 {len(changed_cases)} 个用例")
                result = self._process_incremental(changed_cases, baseline_data)
            else:
                print("✅ 无需处理，数据无变化")
                result = {'message': 'No changes detected'}
        else:
            # 全量处理
            print(f"🔧 全量处理 {len(data)} 个用例")
            result = self.processor.intelligent_process(
                input_file=self.version_manager.versions_dir / f"{version_tag}.json",
                output_file=self.workspace_dir / f"processed_{version_tag}.json",
                learn_mode=True
            )
        
        # 更新状态
        self.state['last_processed_version'] = version_tag
        if not incremental or not parent_version:
            self.state['baseline_version'] = version_tag
        
        # 记录处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        result['processing_time'] = processing_time
        result['version_tag'] = version_tag
        
        # 保存处理历史
        self.version_manager.save_processing_history(
            version_tag, 
            self.state['processing_config'], 
            result
        )
        
        self.save_state()
        
        return result
    
    def _get_changed_cases(self, data: List[Dict], changes: List[Dict]) -> List[Dict]:
        """获取变更的用例"""
        changed_case_ids = {change['case_id'] for change in changes 
                           if change['change_type'] in ['added', 'modified']}
        
        return [case for case in data 
                if str(case.get('id', '')) in changed_case_ids]
    
    def _get_baseline_data(self) -> List[Dict]:
        """获取基线数据"""
        baseline_version = self.state.get('baseline_version')
        if baseline_version:
            return self.version_manager.get_version_data(baseline_version) or []
        return []
    
    def _process_incremental(self, changed_cases: List[Dict], 
                           baseline_data: List[Dict]) -> Dict:
        """增量处理逻辑"""
        # 合并变更用例和基线数据
        all_cases = baseline_data.copy()
        
        # 更新或添加变更的用例
        for changed_case in changed_cases:
            case_id = changed_case.get('id')
            
            # 查找是否存在相同ID的用例
            existing_index = None
            for i, existing_case in enumerate(all_cases):
                if existing_case.get('id') == case_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # 更新现有用例
                all_cases[existing_index] = changed_case
            else:
                # 添加新用例
                all_cases.append(changed_case)
        
        # 使用合并后的数据进行处理
        # 这里简化处理，实际应该调用完整的处理流程
        result = {
            'original_count': len(all_cases),
            'changed_count': len(changed_cases),
            'baseline_count': len(baseline_data),
            'processing_type': 'incremental'
        }
        
        return result
    
    def rollback_to_version(self, version_tag: str) -> bool:
        """回滚到指定版本"""
        data = self.version_manager.get_version_data(version_tag)
        if not data:
            return False
        
        # 更新状态
        self.state['last_processed_version'] = version_tag
        self.save_state()
        
        print(f"⏪ 已回滚到版本: {version_tag}")
        return True
    
    def get_version_history(self) -> List[Dict]:
        """获取版本历史"""
        versions = self.version_manager.get_versions()
        
        # 为每个版本添加处理历史信息
        conn = sqlite3.connect(self.version_manager.db_path)
        cursor = conn.cursor()
        
        for version in versions:
            cursor.execute('''
                SELECT original_count, unique_count, duplicate_count, processing_time
                FROM processing_history ph
                JOIN versions v ON ph.version_id = v.id
                WHERE v.version_tag = ?
                ORDER BY ph.created_at DESC LIMIT 1
            ''', (version['version_tag'],))
            
            result = cursor.fetchone()
            if result:
                version.update({
                    'last_original_count': result[0],
                    'last_unique_count': result[1],
                    'last_duplicate_count': result[2],
                    'last_processing_time': result[3]
                })
        
        conn.close()
        return versions
    
    def export_version(self, version_tag: str, export_path: str):
        """导出指定版本"""
        data = self.version_manager.get_version_data(version_tag)
        if not data:
            raise ValueError(f"版本 {version_tag} 不存在")
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"📤 已导出版本 {version_tag} 到: {export_path}")
    
    def cleanup_old_versions(self, keep_count: int = 10):
        """清理旧版本（保留最近N个版本）"""
        versions = self.version_manager.get_versions()
        
        if len(versions) <= keep_count:
            print("📁 无需清理，版本数量未超过限制")
            return
        
        versions_to_delete = versions[keep_count:]
        
        conn = sqlite3.connect(self.version_manager.db_path)
        cursor = conn.cursor()
        
        for version in versions_to_delete:
            version_tag = version['version_tag']
            
            # 删除文件
            version_file = self.version_manager.versions_dir / f"{version_tag}.json"
            if version_file.exists():
                version_file.unlink()
            
            # 删除数据库记录
            cursor.execute('DELETE FROM versions WHERE version_tag = ?', (version_tag,))
        
        conn.commit()
        conn.close()
        
        print(f"🗑️ 已清理 {len(versions_to_delete)} 个旧版本")


def main():
    """示例用法"""
    processor = IncrementalProcessor()
    
    # 示例：处理初始数据
    with open('test_cases_example.json', 'r', encoding='utf-8') as f:
        initial_data = json.load(f)
    
    print("🚀 增量处理器示例")
    print("="*50)
    
    # 首次处理（全量）
    result1 = processor.process_new_data(
        initial_data, 
        "初始版本 - 全量导入", 
        incremental=False
    )
    print(f"✅ 首次处理完成: {result1.get('version_tag')}")
    
    # 模拟数据变更
    modified_data = initial_data.copy()
    modified_data.append({
        "id": 6,
        "case_name": "新增测试用例",
        "description": "这是一个新增的测试用例",
        "test_steps": ["1. 执行新测试", "2. 验证结果"],
        "expected_result": "测试通过"
    })
    
    # 增量处理
    result2 = processor.process_new_data(
        modified_data,
        "增加新测试用例",
        incremental=True
    )
    print(f"⚡ 增量处理完成: {result2.get('version_tag')}")
    
    # 显示版本历史
    print("\n📚 版本历史:")
    versions = processor.get_version_history()
    for version in versions:
        print(f"  {version['version_tag']}: {version['description']} "
              f"({version['total_cases']} 用例)")
    
    # 导出最新版本
    latest_version = versions[0]['version_tag']
    processor.export_version(latest_version, f"export_{latest_version}.json")


if __name__ == "__main__":
    main()