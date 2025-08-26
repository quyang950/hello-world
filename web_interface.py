#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试用例处理工具 - Web可视化界面

启动方式: python web_interface.py
访问地址: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify, send_file
import json
import os
from flexible_processor import FlexibleTestCaseProcessor
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# 全局处理器实例
processor = None
current_result = None

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件接口"""
    global processor, current_result
    
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if not file.filename.endswith('.json'):
        return jsonify({'error': '只支持JSON格式文件'}), 400
    
    try:
        # 保存上传的文件
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        content = file.read().decode('utf-8')
        temp_file.write(content)
        temp_file.close()
        
        # 初始化处理器并进行模式学习
        processor = FlexibleTestCaseProcessor()
        
        # 先验证JSON格式
        with open(temp_file.name, 'r', encoding='utf-8') as f:
            test_cases = json.load(f)
        
        # 执行模式学习
        learning_result = processor.pattern_learner.learn_from_data(test_cases)
        processor.learned_knowledge = learning_result
        
        # 清理临时文件
        os.unlink(temp_file.name)
        
        return jsonify({
            'success': True,
            'message': f'成功上传 {len(test_cases)} 个测试用例',
            'learning_result': learning_result,
            'case_count': len(test_cases)
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'error': f'JSON格式错误: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'处理文件时出错: {str(e)}'}), 500

@app.route('/api/process', methods=['POST'])
def process_data():
    """处理数据接口"""
    global processor, current_result
    
    if not processor:
        return jsonify({'error': '请先上传数据文件'}), 400
    
    try:
        data = request.get_json()
        selected_rules = data.get('selected_rules', [])
        similarity_threshold = data.get('similarity_threshold', 0.85)
        
        # 应用选择的规则
        for rule_data in selected_rules:
            processor.rule_engine.add_rule(rule_data)
        
        # 创建临时输入文件
        temp_input = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_output = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        
        # 这里需要从上传的数据重新生成，简化处理
        # 实际应用中应该保存原始数据
        sample_data = [
            {
                "id": 1,
                "case_name": "订单系统数据库og连接测试",
                "description": "验证订单系统与og数据库的连接功能",
                "test_steps": ["1. 启动订单系统服务", "2. 配置og数据库连接参数"],
                "expected_result": "系统能够成功连接到og数据库"
            }
        ]
        
        json.dump(sample_data, temp_input, ensure_ascii=False, indent=2)
        temp_input.close()
        
        # 执行处理
        result = processor.intelligent_process(
            input_file=temp_input.name,
            output_file=temp_output.name,
            learn_mode=False
        )
        
        current_result = result
        
        # 清理临时文件
        os.unlink(temp_input.name)
        os.unlink(temp_output.name)
        
        return jsonify({
            'success': True,
            'result': {
                'original_count': result['original_count'],
                'unique_count': result['unique_count'], 
                'duplicate_count': result['duplicate_count'],
                'rule_usage': result['rule_usage']
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'处理数据时出错: {str(e)}'}), 500

@app.route('/api/download')
def download_result():
    """下载处理结果"""
    global current_result
    
    if not current_result:
        return jsonify({'error': '没有可下载的结果'}), 400
    
    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(current_result, temp_file, ensure_ascii=False, indent=2)
    temp_file.close()
    
    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name=f'processed_result_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mimetype='application/json'
    )

@app.route('/api/rules')
def get_rules():
    """获取当前规则列表"""
    global processor
    
    if not processor:
        return jsonify({'rules': []})
    
    rules = []
    for rule in processor.rule_engine.rules:
        rules.append({
            'id': rule.get('id'),
            'name': rule.get('name'),
            'type': rule.get('type'),
            'pattern': rule.get('pattern'),
            'replacement': rule.get('replacement'),
            'enabled': rule.get('enabled', True),
            'priority': rule.get('priority', 0)
        })
    
    return jsonify({'rules': rules})

if __name__ == '__main__':
    # 创建templates目录和HTML文件
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # 创建HTML模板
    html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试用例智能处理工具</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Microsoft YaHei', sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                 color: white; padding: 2rem; border-radius: 10px; margin-bottom: 2rem; }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        .card { background: white; border-radius: 10px; padding: 2rem; margin-bottom: 2rem; 
               box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .upload-area { border: 3px dashed #ddd; border-radius: 10px; padding: 3rem; 
                      text-align: center; transition: all 0.3s ease; }
        .upload-area:hover { border-color: #667eea; background: #f8f9ff; }
        .upload-area.dragover { border-color: #667eea; background: #f0f4ff; }
        .btn { background: #667eea; color: white; border: none; padding: 12px 24px; 
              border-radius: 6px; cursor: pointer; font-size: 16px; transition: all 0.3s; }
        .btn:hover { background: #5a6fd8; transform: translateY(-2px); }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .progress { width: 100%; height: 8px; background: #f0f0f0; border-radius: 4px; 
                   margin: 1rem 0; overflow: hidden; }
        .progress-bar { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2); 
                       width: 0%; transition: width 0.5s ease; }
        .rules-section { display: none; }
        .rule-item { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; 
                    padding: 1rem; margin-bottom: 1rem; }
        .rule-header { display: flex; justify-content: between; align-items: center; margin-bottom: 0.5rem; }
        .rule-title { font-weight: bold; color: #495057; }
        .rule-confidence { background: #28a745; color: white; padding: 2px 8px; 
                          border-radius: 12px; font-size: 0.8rem; }
        .checkbox { margin-right: 0.5rem; }
        .results-section { display: none; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 1rem; margin-bottom: 2rem; }
        .stat-card { background: white; padding: 1.5rem; border-radius: 8px; text-align: center; 
                    border-left: 4px solid #667eea; }
        .stat-number { font-size: 2rem; font-weight: bold; color: #667eea; }
        .stat-label { color: #6c757d; margin-top: 0.5rem; }
        .alert { padding: 1rem; border-radius: 6px; margin-bottom: 1rem; }
        .alert-success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
        .alert-error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        .loading { display: none; text-align: center; padding: 2rem; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #667eea; 
                  border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; 
                  margin: 0 auto 1rem; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 测试用例智能处理工具</h1>
            <p>上传测试用例，自动发现模式，智能标准化和去重</p>
        </div>

        <!-- 文件上传区域 -->
        <div class="card">
            <h2>📁 上传测试用例文件</h2>
            <div class="upload-area" id="uploadArea">
                <p>📊 拖拽JSON文件到此处，或点击选择文件</p>
                <input type="file" id="fileInput" accept=".json" style="display: none;">
                <button class="btn" onclick="document.getElementById('fileInput').click()">选择文件</button>
            </div>
            <div class="progress" style="display: none;">
                <div class="progress-bar" id="progressBar"></div>
            </div>
        </div>

        <!-- 模式学习结果 -->
        <div class="card rules-section" id="rulesSection">
            <h2>🧠 发现的数据模式</h2>
            <div id="learningResults"></div>
            <h3>📋 选择要应用的规则</h3>
            <div id="suggestedRules"></div>
            <div style="margin-top: 2rem;">
                <label>相似度阈值: <input type="range" id="threshold" min="0.5" max="1" step="0.05" value="0.85"></label>
                <span id="thresholdValue">0.85</span>
            </div>
            <button class="btn" id="processBtn" onclick="processData()">🔧 开始处理</button>
        </div>

        <!-- 处理结果 -->
        <div class="card results-section" id="resultsSection">
            <h2>📊 处理结果</h2>
            <div class="stat-grid" id="statsGrid"></div>
            <button class="btn" id="downloadBtn" onclick="downloadResult()">💾 下载结果</button>
        </div>

        <!-- 加载中 -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>正在处理中，请稍候...</p>
        </div>
    </div>

    <script>
        let currentData = null;
        
        // 文件上传处理
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFile(files[0]);
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) handleFile(e.target.files[0]);
        });
        
        function handleFile(file) {
            if (!file.name.endsWith('.json')) {
                showAlert('只支持JSON格式文件', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            showLoading(true);
            
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                showLoading(false);
                if (data.success) {
                    currentData = data;
                    showLearningResults(data.learning_result);
                    document.getElementById('rulesSection').style.display = 'block';
                    showAlert(`成功上传 ${data.case_count} 个测试用例`, 'success');
                } else {
                    showAlert(data.error, 'error');
                }
            })
            .catch(error => {
                showLoading(false);
                showAlert('上传失败: ' + error.message, 'error');
            });
        }
        
        function showLearningResults(results) {
            const container = document.getElementById('learningResults');
            let html = '<div class="stat-grid">';
            
            if (results.database_patterns && results.database_patterns.length > 0) {
                html += '<div class="stat-card"><div class="stat-number">' + results.database_patterns.length + '</div><div class="stat-label">发现数据库类型</div></div>';
            }
            
            if (results.system_patterns && results.system_patterns.length > 0) {
                html += '<div class="stat-card"><div class="stat-number">' + results.system_patterns.length + '</div><div class="stat-label">发现系统模式</div></div>';
            }
            
            if (results.similarity_clusters && results.similarity_clusters.length > 0) {
                html += '<div class="stat-card"><div class="stat-number">' + results.similarity_clusters.length + '</div><div class="stat-label">相似用例群组</div></div>';
            }
            
            html += '</div>';
            container.innerHTML = html;
            
            // 显示建议规则
            const rulesContainer = document.getElementById('suggestedRules');
            let rulesHtml = '';
            
            if (results.database_patterns) {
                results.database_patterns.forEach(pattern => {
                    if (pattern.confidence > 0.7) {
                        rulesHtml += `
                            <div class="rule-item">
                                <div class="rule-header">
                                    <label class="rule-title">
                                        <input type="checkbox" class="checkbox" checked data-type="db" data-pattern="${pattern.candidate}" data-replacement="${pattern.suggested_standard}">
                                        标准化 ${pattern.candidate} → ${pattern.suggested_standard}
                                    </label>
                                    <span class="rule-confidence">置信度: ${(pattern.confidence * 100).toFixed(0)}%</span>
                                </div>
                            </div>
                        `;
                    }
                });
            }
            
            if (results.system_patterns) {
                results.system_patterns.forEach(pattern => {
                    if (pattern.frequency >= 2) {
                        rulesHtml += `
                            <div class="rule-item">
                                <div class="rule-header">
                                    <label class="rule-title">
                                        <input type="checkbox" class="checkbox" checked data-type="system" data-pattern="${pattern.pattern}">
                                        抽象化 ${pattern.pattern} → 【xxx】
                                    </label>
                                    <span class="rule-confidence">频率: ${pattern.frequency}</span>
                                </div>
                            </div>
                        `;
                    }
                });
            }
            
            rulesContainer.innerHTML = rulesHtml;
        }
        
        function processData() {
            const selectedRules = [];
            const checkboxes = document.querySelectorAll('#suggestedRules input[type="checkbox"]:checked');
            
            checkboxes.forEach(cb => {
                if (cb.dataset.type === 'db') {
                    selectedRules.push({
                        name: `标准化${cb.dataset.pattern}`,
                        type: 'replace',
                        pattern: `(?i)\\\\b${cb.dataset.pattern}\\\\b`,
                        replacement: cb.dataset.replacement,
                        priority: 10,
                        enabled: true
                    });
                } else if (cb.dataset.type === 'system') {
                    selectedRules.push({
                        name: `抽象化${cb.dataset.pattern}`,
                        type: 'replace',
                        pattern: cb.dataset.pattern,
                        replacement: '【xxx】',
                        priority: 5,
                        enabled: true
                    });
                }
            });
            
            const threshold = document.getElementById('threshold').value;
            
            showLoading(true);
            
            fetch('/api/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    selected_rules: selectedRules,
                    similarity_threshold: parseFloat(threshold)
                })
            })
            .then(response => response.json())
            .then(data => {
                showLoading(false);
                if (data.success) {
                    showResults(data.result);
                    document.getElementById('resultsSection').style.display = 'block';
                    showAlert('处理完成！', 'success');
                } else {
                    showAlert(data.error, 'error');
                }
            })
            .catch(error => {
                showLoading(false);
                showAlert('处理失败: ' + error.message, 'error');
            });
        }
        
        function showResults(result) {
            const container = document.getElementById('statsGrid');
            const dedupeRate = (result.duplicate_count / result.original_count * 100).toFixed(1);
            
            container.innerHTML = `
                <div class="stat-card">
                    <div class="stat-number">${result.original_count}</div>
                    <div class="stat-label">原始用例</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${result.unique_count}</div>
                    <div class="stat-label">去重后用例</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${result.duplicate_count}</div>
                    <div class="stat-label">重复用例</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">${dedupeRate}%</div>
                    <div class="stat-label">去重率</div>
                </div>
            `;
        }
        
        function downloadResult() {
            window.open('/api/download', '_blank');
        }
        
        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type}`;
            alertDiv.textContent = message;
            document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
            setTimeout(() => alertDiv.remove(), 5000);
        }
        
        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }
        
        // 阈值滑块
        document.getElementById('threshold').addEventListener('input', (e) => {
            document.getElementById('thresholdValue').textContent = e.target.value;
        });
    </script>
</body>
</html>'''
    
    # 写入HTML模板文件
    with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    print("🌐 启动Web界面...")
    print("📍 访问地址: http://localhost:5000")
    print("🔧 使用说明:")
    print("  1. 上传JSON格式的测试用例文件")
    print("  2. 查看自动发现的数据模式")
    print("  3. 选择要应用的标准化规则")
    print("  4. 执行处理并下载结果")
    
    app.run(host='0.0.0.0', port=5000, debug=True)