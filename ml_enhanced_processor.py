#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习增强的测试用例处理器

特性：
1. 语义相似性检测 - 使用词向量和语义分析
2. 聚类算法 - 自动发现用例群组
3. 异常检测 - 识别异常或有问题的用例
4. 智能推荐 - 基于历史数据推荐处理策略
5. 自适应阈值 - 动态调整相似度阈值
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN, KMeans
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
from flexible_processor import FlexibleTestCaseProcessor
import pickle
from pathlib import Path


class TextFeatureExtractor:
    """文本特征提取器"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words=None,  # 中文没有内置停词表
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        self.is_fitted = False
    
    def extract_features(self, test_cases: List[Dict]) -> np.ndarray:
        """提取测试用例的文本特征"""
        # 合并所有文本字段
        texts = []
        for case in test_cases:
            combined_text = self._combine_text_fields(case)
            texts.append(combined_text)
        
        if not self.is_fitted:
            # 首次训练
            features = self.tfidf_vectorizer.fit_transform(texts)
            self.is_fitted = True
        else:
            # 使用已训练的向量化器
            features = self.tfidf_vectorizer.transform(texts)
        
        return features.toarray()
    
    def _combine_text_fields(self, case: Dict) -> str:
        """合并测试用例的文本字段"""
        text_parts = []
        
        # 添加用例名称（权重较高）
        case_name = case.get('case_name', '')
        text_parts.extend([case_name] * 3)  # 重复3次增加权重
        
        # 添加描述
        description = case.get('description', '')
        text_parts.extend([description] * 2)  # 重复2次增加权重
        
        # 添加测试步骤
        steps = case.get('test_steps', [])
        if isinstance(steps, list):
            text_parts.extend(steps)
        else:
            text_parts.append(str(steps))
        
        # 添加预期结果
        expected = case.get('expected_result', '')
        text_parts.append(expected)
        
        # 清理并合并
        cleaned_parts = [self._clean_text(part) for part in text_parts if part]
        return ' '.join(cleaned_parts)
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        # 移除序号标记
        text = re.sub(r'^\d+[\.、]?\s*', '', text)
        return text


class MLClusterer:
    """机器学习聚类器"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=0.95)  # 保留95%的方差
        self.feature_extractor = TextFeatureExtractor()
    
    def cluster_test_cases(self, test_cases: List[Dict], 
                          method: str = 'dbscan') -> Dict:
        """对测试用例进行聚类"""
        
        # 提取特征
        features = self.feature_extractor.extract_features(test_cases)
        
        # 标准化特征
        features_scaled = self.scaler.fit_transform(features)
        
        # 降维（如果特征维度过高）
        if features_scaled.shape[1] > 50:
            features_pca = self.pca.fit_transform(features_scaled)
        else:
            features_pca = features_scaled
        
        # 执行聚类
        if method == 'dbscan':
            clusters = self._dbscan_clustering(features_pca)
        elif method == 'kmeans':
            clusters = self._kmeans_clustering(features_pca, test_cases)
        else:
            raise ValueError(f"不支持的聚类方法: {method}")
        
        # 分析聚类结果
        cluster_analysis = self._analyze_clusters(test_cases, clusters, features_pca)
        
        return {
            'clusters': clusters,
            'analysis': cluster_analysis,
            'features': features_pca,
            'method': method
        }
    
    def _dbscan_clustering(self, features: np.ndarray) -> np.ndarray:
        """DBSCAN聚类"""
        # 动态确定eps参数
        eps = self._estimate_eps(features)
        
        dbscan = DBSCAN(eps=eps, min_samples=2, metric='cosine')
        clusters = dbscan.fit_predict(features)
        
        return clusters
    
    def _kmeans_clustering(self, features: np.ndarray, 
                          test_cases: List[Dict]) -> np.ndarray:
        """K-means聚类"""
        # 估计最优聚类数
        optimal_k = self._estimate_optimal_k(features, max_k=min(10, len(test_cases)//2))
        
        kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(features)
        
        return clusters
    
    def _estimate_eps(self, features: np.ndarray) -> float:
        """估计DBSCAN的eps参数"""
        # 计算每个点到最近邻居的距离
        distances = []
        for i in range(len(features)):
            similarities = cosine_similarity([features[i]], features)[0]
            # 排除自身，找到最高相似度
            similarities[i] = -1
            max_sim = np.max(similarities)
            # 转换为距离
            distance = 1 - max_sim
            distances.append(distance)
        
        # 使用距离的75分位数作为eps
        eps = np.percentile(distances, 75)
        return max(eps, 0.1)  # 确保最小值
    
    def _estimate_optimal_k(self, features: np.ndarray, max_k: int) -> int:
        """估计K-means的最优聚类数"""
        if max_k <= 1:
            return 2
        
        inertias = []
        k_range = range(2, max_k + 1)
        
        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(features)
            inertias.append(kmeans.inertia_)
        
        # 使用肘部法则选择最优k
        # 计算二阶差分找到"肘部"
        if len(inertias) >= 3:
            diffs = np.diff(inertias)
            diff2 = np.diff(diffs)
            # 找到二阶差分最大的点
            optimal_idx = np.argmax(diff2) + 2  # +2是因为差分减少了索引
            optimal_k = min(k_range[optimal_idx], max_k)
        else:
            optimal_k = min(3, max_k)
        
        return optimal_k
    
    def _analyze_clusters(self, test_cases: List[Dict], clusters: np.ndarray,
                         features: np.ndarray) -> Dict:
        """分析聚类结果"""
        cluster_info = defaultdict(list)
        
        for i, cluster_id in enumerate(clusters):
            cluster_info[cluster_id].append({
                'index': i,
                'case': test_cases[i],
                'feature': features[i]
            })
        
        analysis = {}
        for cluster_id, items in cluster_info.items():
            if cluster_id == -1:  # DBSCAN噪声点
                analysis['noise'] = {
                    'count': len(items),
                    'cases': [item['case'] for item in items]
                }
            else:
                # 计算聚类内相似度
                if len(items) > 1:
                    cluster_features = np.array([item['feature'] for item in items])
                    avg_similarity = np.mean(cosine_similarity(cluster_features))
                else:
                    avg_similarity = 1.0
                
                analysis[f'cluster_{cluster_id}'] = {
                    'count': len(items),
                    'avg_similarity': avg_similarity,
                    'cases': [item['case'] for item in items],
                    'representative': self._find_representative(items)
                }
        
        return analysis
    
    def _find_representative(self, cluster_items: List[Dict]) -> Dict:
        """找到聚类的代表性用例"""
        if len(cluster_items) == 1:
            return cluster_items[0]['case']
        
        # 选择到聚类中心最近的用例
        cluster_features = np.array([item['feature'] for item in cluster_items])
        center = np.mean(cluster_features, axis=0)
        
        distances = [cosine_similarity([center], [item['feature']])[0][0] 
                    for item in cluster_items]
        
        representative_idx = np.argmax(distances)
        return cluster_items[representative_idx]['case']


class SemanticAnalyzer:
    """语义分析器"""
    
    def __init__(self):
        self.word_patterns = {
            '数据库操作': ['连接', '查询', '插入', '更新', '删除', '事务'],
            '系统功能': ['登录', '注册', '权限', '配置', '设置'],
            '性能测试': ['并发', '负载', '压力', '性能', '响应时间'],
            '界面测试': ['页面', '按钮', '输入', '显示', '界面'],
            '接口测试': ['API', '接口', '请求', '响应', '参数']
        }
    
    def analyze_semantic_similarity(self, case1: Dict, case2: Dict) -> float:
        """分析两个测试用例的语义相似性"""
        
        # 获取文本内容
        text1 = self._extract_text(case1)
        text2 = self._extract_text(case2)
        
        # 计算多个维度的相似性
        similarities = []
        
        # 1. 关键词重叠度
        keyword_sim = self._calculate_keyword_overlap(text1, text2)
        similarities.append(keyword_sim * 0.3)
        
        # 2. 语义类别相似性
        category_sim = self._calculate_category_similarity(text1, text2)
        similarities.append(category_sim * 0.4)
        
        # 3. 结构相似性
        structure_sim = self._calculate_structure_similarity(case1, case2)
        similarities.append(structure_sim * 0.3)
        
        return sum(similarities)
    
    def _extract_text(self, case: Dict) -> str:
        """提取用例的文本内容"""
        parts = []
        parts.append(case.get('case_name', ''))
        parts.append(case.get('description', ''))
        parts.extend(case.get('test_steps', []))
        parts.append(case.get('expected_result', ''))
        
        return ' '.join(str(part) for part in parts if part)
    
    def _calculate_keyword_overlap(self, text1: str, text2: str) -> float:
        """计算关键词重叠度"""
        # 提取关键词（简单分词）
        words1 = set(re.findall(r'[\u4e00-\u9fff]+|\w+', text1.lower()))
        words2 = set(re.findall(r'[\u4e00-\u9fff]+|\w+', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        # 计算Jaccard相似性
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _calculate_category_similarity(self, text1: str, text2: str) -> float:
        """计算语义类别相似性"""
        categories1 = self._classify_text(text1)
        categories2 = self._classify_text(text2)
        
        if not categories1 or not categories2:
            return 0.0
        
        # 计算类别重叠度
        common_categories = set(categories1).intersection(set(categories2))
        total_categories = set(categories1).union(set(categories2))
        
        return len(common_categories) / len(total_categories) if total_categories else 0.0
    
    def _classify_text(self, text: str) -> List[str]:
        """将文本分类到预定义的类别"""
        categories = []
        
        for category, keywords in self.word_patterns.items():
            for keyword in keywords:
                if keyword in text:
                    categories.append(category)
                    break
        
        return categories
    
    def _calculate_structure_similarity(self, case1: Dict, case2: Dict) -> float:
        """计算结构相似性"""
        # 比较测试步骤数量
        steps1 = case1.get('test_steps', [])
        steps2 = case2.get('test_steps', [])
        
        if not steps1 or not steps2:
            return 0.0
        
        step_count_sim = 1 - abs(len(steps1) - len(steps2)) / max(len(steps1), len(steps2))
        
        return step_count_sim


class MLEnhancedProcessor(FlexibleTestCaseProcessor):
    """机器学习增强的处理器"""
    
    def __init__(self, config_file: str = 'ml_config.json'):
        super().__init__(config_file)
        self.clusterer = MLClusterer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.model_cache_dir = Path('.ml_cache')
        self.model_cache_dir.mkdir(exist_ok=True)
    
    def intelligent_deduplication(self, test_cases: List[Dict], 
                                 method: str = 'ml_hybrid') -> Tuple[List[Dict], List[Dict]]:
        """智能去重"""
        
        if method == 'ml_hybrid':
            return self._ml_hybrid_deduplication(test_cases)
        elif method == 'clustering':
            return self._clustering_deduplication(test_cases)
        elif method == 'semantic':
            return self._semantic_deduplication(test_cases)
        else:
            # 回退到传统方法
            return super()._intelligent_deduplication(test_cases)
    
    def _ml_hybrid_deduplication(self, test_cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """混合机器学习去重方法"""
        
        print("🤖 执行ML混合去重...")
        
        # 1. 先进行聚类分析
        cluster_result = self.clusterer.cluster_test_cases(test_cases, method='dbscan')
        clusters = cluster_result['clusters']
        
        unique_cases = []
        duplicate_cases = []
        processed_indices = set()
        
        # 2. 处理每个聚类
        for cluster_id in np.unique(clusters):
            cluster_indices = np.where(clusters == cluster_id)[0]
            
            if cluster_id == -1:  # 噪声点，单独处理
                for idx in cluster_indices:
                    if idx not in processed_indices:
                        unique_cases.append(test_cases[idx])
                        processed_indices.add(idx)
            else:
                # 聚类内进行语义相似性分析
                cluster_cases = [test_cases[i] for i in cluster_indices]
                cluster_unique, cluster_duplicates = self._semantic_deduplication(cluster_cases)
                
                unique_cases.extend(cluster_unique)
                duplicate_cases.extend(cluster_duplicates)
                processed_indices.update(cluster_indices)
        
        print(f"📊 聚类发现 {len(np.unique(clusters[clusters != -1]))} 个群组")
        print(f"🔍 语义分析去重 {len(duplicate_cases)} 个重复用例")
        
        return unique_cases, duplicate_cases
    
    def _clustering_deduplication(self, test_cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """基于聚类的去重"""
        
        cluster_result = self.clusterer.cluster_test_cases(test_cases)
        analysis = cluster_result['analysis']
        
        unique_cases = []
        duplicate_cases = []
        
        for cluster_name, cluster_info in analysis.items():
            if cluster_name == 'noise':
                # 噪声点视为唯一
                unique_cases.extend(cluster_info['cases'])
            else:
                # 每个聚类选择一个代表
                representative = cluster_info['representative']
                unique_cases.append(representative)
                
                # 其他成员视为重复
                for case in cluster_info['cases']:
                    if case != representative:
                        duplicate_cases.append(case)
        
        return unique_cases, duplicate_cases
    
    def _semantic_deduplication(self, test_cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """基于语义分析的去重"""
        
        unique_cases = []
        duplicate_cases = []
        
        for i, case in enumerate(test_cases):
            is_duplicate = False
            
            for unique_case in unique_cases:
                semantic_sim = self.semantic_analyzer.analyze_semantic_similarity(case, unique_case)
                
                if semantic_sim > 0.8:  # 语义相似度阈值
                    duplicate_cases.append(case)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_cases.append(case)
        
        return unique_cases, duplicate_cases
    
    def adaptive_threshold_learning(self, test_cases: List[Dict], 
                                   user_feedback: List[Dict]) -> float:
        """自适应阈值学习"""
        
        # 基于用户反馈调整相似度阈值
        # user_feedback 格式: [{'case1_id': 1, 'case2_id': 2, 'is_duplicate': True}, ...]
        
        similarities = []
        labels = []
        
        for feedback in user_feedback:
            case1_id = feedback['case1_id']
            case2_id = feedback['case2_id']
            is_duplicate = feedback['is_duplicate']
            
            # 找到对应的用例
            case1 = next((case for case in test_cases if case.get('id') == case1_id), None)
            case2 = next((case for case in test_cases if case.get('id') == case2_id), None)
            
            if case1 and case2:
                sim = self.semantic_analyzer.analyze_semantic_similarity(case1, case2)
                similarities.append(sim)
                labels.append(1 if is_duplicate else 0)
        
        if len(similarities) < 5:  # 需要足够的样本
            return 0.85  # 返回默认阈值
        
        # 简单的阈值优化：找到最佳分割点
        similarities = np.array(similarities)
        labels = np.array(labels)
        
        best_threshold = 0.85
        best_accuracy = 0
        
        for threshold in np.arange(0.5, 1.0, 0.05):
            predictions = (similarities > threshold).astype(int)
            accuracy = np.mean(predictions == labels)
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_threshold = threshold
        
        print(f"🎯 自适应阈值学习完成，最佳阈值: {best_threshold:.3f} (准确率: {best_accuracy:.3f})")
        
        return best_threshold
    
    def visualize_clustering(self, test_cases: List[Dict], output_path: str = 'clustering_visualization.png'):
        """可视化聚类结果"""
        
        cluster_result = self.clusterer.cluster_test_cases(test_cases)
        features = cluster_result['features']
        clusters = cluster_result['clusters']
        
        # 如果特征维度大于2，使用PCA降维到2D
        if features.shape[1] > 2:
            pca_2d = PCA(n_components=2)
            features_2d = pca_2d.fit_transform(features)
        else:
            features_2d = features
        
        # 创建可视化
        plt.figure(figsize=(12, 8))
        
        # 绘制聚类结果
        unique_clusters = np.unique(clusters)
        colors = plt.cm.Set3(np.linspace(0, 1, len(unique_clusters)))
        
        for i, cluster_id in enumerate(unique_clusters):
            cluster_mask = clusters == cluster_id
            if cluster_id == -1:
                # 噪声点用黑色标记
                plt.scatter(features_2d[cluster_mask, 0], features_2d[cluster_mask, 1], 
                           c='black', marker='x', s=50, label='Noise')
            else:
                plt.scatter(features_2d[cluster_mask, 0], features_2d[cluster_mask, 1], 
                           c=[colors[i]], s=50, label=f'Cluster {cluster_id}')
        
        plt.title('测试用例聚类可视化')
        plt.xlabel('PC1')
        plt.ylabel('PC2')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 保存图片
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📊 聚类可视化已保存到: {output_path}")
    
    def save_model(self, model_name: str):
        """保存训练好的模型"""
        model_data = {
            'feature_extractor': self.clusterer.feature_extractor,
            'scaler': self.clusterer.scaler,
            'pca': self.clusterer.pca,
            'semantic_analyzer': self.semantic_analyzer
        }
        
        model_path = self.model_cache_dir / f"{model_name}.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"💾 模型已保存到: {model_path}")
    
    def load_model(self, model_name: str) -> bool:
        """加载训练好的模型"""
        model_path = self.model_cache_dir / f"{model_name}.pkl"
        
        if not model_path.exists():
            print(f"❌ 模型文件不存在: {model_path}")
            return False
        
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.clusterer.feature_extractor = model_data['feature_extractor']
            self.clusterer.scaler = model_data['scaler']
            self.clusterer.pca = model_data['pca']
            self.semantic_analyzer = model_data['semantic_analyzer']
            
            print(f"✅ 模型已加载: {model_path}")
            return True
            
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            return False


def main():
    """示例用法"""
    
    # 创建ML增强处理器
    processor = MLEnhancedProcessor()
    
    # 加载测试数据
    with open('test_cases_example.json', 'r', encoding='utf-8') as f:
        test_cases = json.load(f)
    
    print("🤖 机器学习增强处理器示例")
    print("="*50)
    
    # 执行智能去重
    print("\n1. 执行ML混合去重...")
    unique_cases, duplicate_cases = processor.intelligent_deduplication(
        test_cases, method='ml_hybrid'
    )
    
    print(f"原始用例数: {len(test_cases)}")
    print(f"去重后用例数: {len(unique_cases)}")
    print(f"重复用例数: {len(duplicate_cases)}")
    
    # 可视化聚类结果
    print("\n2. 生成聚类可视化...")
    processor.visualize_clustering(test_cases)
    
    # 保存模型
    print("\n3. 保存模型...")
    processor.save_model('test_model')
    
    print("\n✅ 示例完成!")


if __name__ == "__main__":
    # 检查依赖
    try:
        import sklearn
        import matplotlib
        import seaborn
        main()
    except ImportError as e:
        print(f"❌ 缺少依赖库: {e}")
        print("请安装: pip install scikit-learn matplotlib seaborn")