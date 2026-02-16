#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
支持从配置文件和环境变量加载配置，环境变量优先级更高
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """
    加载配置
    优先级：环境变量 > 配置文件 > 默认值
    """
    config = {}
    
    # 1. 尝试加载配置文件作为默认值
    config_file = Path(__file__).parent / 'config.json'
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"已加载配置文件: {config_file}")
        except Exception as e:
            logger.warning(f"配置文件加载失败: {e}，将使用环境变量和默认值")
    else:
        logger.info("配置文件不存在，将使用环境变量和默认值")
    
    # 2. 环境变量覆盖配置文件（优先级更高）
    config['sillytavern_data_path'] = os.getenv(
        'ST_DATA_PATH', 
        config.get('sillytavern_data_path', '/var/sillytavern/data')
    )
    
    config['backup_repo_path'] = os.getenv(
        'BACKUP_REPO_PATH',
        config.get('backup_repo_path', '/var/backups/sillytavern-backup')
    )
    
    config['github_remote_url'] = os.getenv(
        'GITHUB_REMOTE_URL',
        config.get('github_remote_url', '')
    )
    
    config['backup_time'] = os.getenv(
        'BACKUP_TIME',
        config.get('backup_time', '03:00')
    )
    
    config['max_log_size_mb'] = int(os.getenv(
        'MAX_LOG_SIZE_MB',
        str(config.get('max_log_size_mb', 10))
    ))
    
    config['enable_auto_backup'] = os.getenv(
        'AUTO_BACKUP_ENABLED',
        str(config.get('enable_auto_backup', True))
    ).lower() in ('true', '1', 'yes')
    
    # 3. 验证必需配置
    if not config['github_remote_url']:
        raise ValueError("GitHub 仓库 URL 未配置！请设置 GITHUB_REMOTE_URL 环境变量或在 config.json 中配置")
    
    # 4. 转换路径为 Path 对象
    config['sillytavern_data_path'] = Path(config['sillytavern_data_path'])
    config['backup_repo_path'] = Path(config['backup_repo_path'])
    
    logger.info("配置加载完成")
    logger.debug(f"SillyTavern 数据路径: {config['sillytavern_data_path']}")
    logger.debug(f"备份仓库路径: {config['backup_repo_path']}")
    logger.debug(f"GitHub 仓库: {config['github_remote_url']}")
    logger.debug(f"备份时间: {config['backup_time']}")
    logger.debug(f"自动备份: {config['enable_auto_backup']}")
    
    return config


def validate_config(config: Dict[str, Any]) -> bool:
    """
    验证配置的有效性
    """
    errors = []
    
    # 检查 SillyTavern 数据目录
    if not config['sillytavern_data_path'].exists():
        errors.append(f"SillyTavern 数据目录不存在: {config['sillytavern_data_path']}")
    
    # 检查备份时间格式
    try:
        hour, minute = config['backup_time'].split(':')
        if not (0 <= int(hour) <= 23 and 0 <= int(minute) <= 59):
            errors.append(f"备份时间格式错误: {config['backup_time']}，应为 HH:MM 格式")
    except:
        errors.append(f"备份时间格式错误: {config['backup_time']}，应为 HH:MM 格式")
    
    # 检查 GitHub URL 格式
    if not (config['github_remote_url'].startswith('git@') or 
            config['github_remote_url'].startswith('https://')):
        errors.append(f"GitHub 仓库 URL 格式错误: {config['github_remote_url']}")
    
    if errors:
        for error in errors:
            logger.error(error)
        return False
    
    logger.info("配置验证通过")
    return True
