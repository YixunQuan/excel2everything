# -*- coding: utf-8 -*-
"""
配置加载器 - 加载 YAML 配置文件
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple

import yaml

from .models import (
    ExcelFormatConfig,
    MappingRuleConfig,
    SettingsConfig,
    DetectionConfig,
    CatalogConfig,
    DataSheetConfig,
    DataColumnMapping,
    GroupLabelsConfig,
    GroupDetectionConfig,
    MappingRule,
)


# 配置目录
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"
FORMATS_DIR = CONFIG_DIR / "excel_formats"
RULES_DIR = CONFIG_DIR / "mapping_rules"


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.formats_dir = self.config_dir / "excel_formats"
        self.rules_dir = self.config_dir / "mapping_rules"
        
        # 缓存
        self._formats_cache: Dict[str, ExcelFormatConfig] = {}
        self._rules_cache: Dict[str, MappingRuleConfig] = {}
        self._settings_cache: Optional[SettingsConfig] = None
    
    def list_excel_formats(self) -> List[Dict[str, str]]:
        """列出所有可用的 Excel 格式配置"""
        result = []
        if self.formats_dir.exists():
            for f in self.formats_dir.glob("*.yaml"):
                try:
                    config = self.load_excel_format(f.stem)
                    result.append({
                        "id": f.stem,
                        "name": config.name,
                        "description": config.description,
                    })
                except Exception:
                    pass
        return result
    
    def list_mapping_rules(self) -> List[Dict[str, str]]:
        """列出所有可用的映射规则配置"""
        result = []
        if self.rules_dir.exists():
            for f in self.rules_dir.glob("*.yaml"):
                try:
                    config = self.load_mapping_rules(f.stem)
                    result.append({
                        "id": f.stem,
                        "name": config.name,
                        "description": config.description,
                    })
                except Exception:
                    pass
        return result
    
    def load_excel_format(self, name: str) -> ExcelFormatConfig:
        """加载 Excel 格式配置"""
        if name in self._formats_cache:
            return self._formats_cache[name]
        
        path = self.formats_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Excel 格式配置不存在: {name}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = self._parse_excel_format(data)
        self._formats_cache[name] = config
        return config
    
    def load_mapping_rules(self, name: str) -> MappingRuleConfig:
        """加载映射规则配置"""
        if name in self._rules_cache:
            return self._rules_cache[name]
        
        path = self.rules_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"映射规则配置不存在: {name}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        config = self._parse_mapping_rules(data)
        self._rules_cache[name] = config
        return config
    
    def load_settings(self) -> SettingsConfig:
        """加载全局设置"""
        if self._settings_cache:
            return self._settings_cache
        
        path = self.config_dir / "settings.yaml"
        if not path.exists():
            return SettingsConfig()
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        config = SettingsConfig(**data)
        self._settings_cache = config
        return config
    
    def _parse_excel_format(self, data: dict) -> ExcelFormatConfig:
        """解析 Excel 格式配置"""
        detection = DetectionConfig(**data.get('detection', {}))
        catalog = CatalogConfig(**data.get('catalog', {}))
        
        data_sheet_data = data.get('data_sheet', {})
        columns_data = data_sheet_data.get('columns', {})
        columns = DataColumnMapping(**columns_data)
        data_sheet = DataSheetConfig(
            header_row=data_sheet_data.get('header_row', 4),
            data_start_row=data_sheet_data.get('data_start_row', 5),
            filter_column=data_sheet_data.get('filter_column'),
            filter_value=data_sheet_data.get('filter_value'),
            columns=columns,
        )
        
        group_labels = GroupLabelsConfig(**data.get('group_labels', {}))
        group_detection = GroupDetectionConfig(**data.get('group_detection', {}))
        
        return ExcelFormatConfig(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            detection=detection,
            catalog=catalog,
            data_sheet=data_sheet,
            group_labels=group_labels,
            group_detection=group_detection,
        )
    
    def _parse_mapping_rules(self, data: dict) -> MappingRuleConfig:
        """解析映射规则配置"""
        rules = []
        for rule_data in data.get('rules', []):
            rules.append(MappingRule(**rule_data))
        
        return MappingRuleConfig(
            name=data.get('name', 'Unknown'),
            description=data.get('description', ''),
            rules=rules,
        )
    
    def detect_excel_format(self, file_path: str) -> Tuple[str, float]:
        """
        智能识别 Excel 文件格式
        
        Returns:
            (format_name, confidence) - 格式名称和置信度
        """
        import pandas as pd
        
        try:
            engine = "xlrd" if file_path.lower().endswith(".xls") else "openpyxl"
            xls = pd.ExcelFile(file_path, engine=engine)
        except Exception:
            return "generic", 0.0
        
        # 获取所有 sheet 名称
        sheet_names = set(xls.sheet_names)
        
        best_match = "generic"
        best_score = 0.0
        
        for format_info in self.list_excel_formats():
            fmt = self.load_excel_format(format_info["id"])
            score = self._calculate_format_score(xls, sheet_names, fmt)
            if score > best_score:
                best_score = score
                best_match = format_info["id"]
        
        return best_match, best_score
    
    def _calculate_format_score(self, xls, sheet_names: set, fmt: ExcelFormatConfig) -> float:
        """计算格式匹配分数"""
        score = 0.0
        
        # 检查目录表
        if fmt.detection.catalog_sheet:
            if fmt.detection.catalog_sheet in sheet_names:
                score += 0.3
                
                # 检查目录表列名
                try:
                    df = pd.read_excel(xls, sheet_name=fmt.detection.catalog_sheet, nrows=5)
                    columns = set(df.columns)
                    
                    required = set(fmt.detection.required_columns)
                    if required.issubset(columns):
                        score += 0.4
                    
                    optional = set(fmt.detection.optional_columns)
                    matched_optional = optional & columns
                    score += 0.1 * len(matched_optional) / max(len(optional), 1)
                except Exception:
                    pass
        else:
            # 无目录表的格式
            score += 0.2
        
        return min(score, 1.0)


# 全局实例
_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取配置加载器实例"""
    global _loader
    if _loader is None:
        _loader = ConfigLoader()
    return _loader


def load_excel_format(name: str) -> ExcelFormatConfig:
    """加载 Excel 格式配置（便捷函数）"""
    return get_config_loader().load_excel_format(name)


def load_mapping_rules(name: str) -> MappingRuleConfig:
    """加载映射规则配置（便捷函数）"""
    return get_config_loader().load_mapping_rules(name)


def load_settings() -> SettingsConfig:
    """加载全局设置（便捷函数）"""
    return get_config_loader().load_settings()
