#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主程序 - 守护进程
支持自动定时备份和手动触发
"""

import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import load_config, validate_config
from backup import BackupManager
from logger import setup_logger

logger = logging.getLogger(__name__)


def main():
    """主函数"""
    setup_logger()
    
    logger.info("=" * 60)
    logger.info("SillyTavern 云备份系统启动")
    logger.info("=" * 60)
    
    try:
        # 加载配置
        config = load_config()
        
        # 验证配置
        if not validate_config(config):
            logger.error("配置验证失败，程序退出")
            return 1
        
        # 检查是否启用自动备份
        if not config['enable_auto_backup']:
            logger.info("自动备份已禁用")
            logger.info("提示：使用以下命令进行手动操作：")
            logger.info("  备份: python backup.py")
            logger.info("  恢复: python restore.py")
            return 0
        
        # 解析备份时间
        hour, minute = config['backup_time'].split(':')
        hour, minute = int(hour), int(minute)
        
        logger.info(f"自动备份已启用，计划时间: 每天 {hour:02d}:{minute:02d}")
        logger.info("守护进程正在运行，按 Ctrl+C 停止...")
        logger.info("-" * 60)
        
        # 创建备份管理器
        backup_manager = BackupManager(config)
        
        # 创建调度器
        scheduler = BlockingScheduler()
        
        # 添加定时任务
        trigger = CronTrigger(hour=hour, minute=minute)
        scheduler.add_job(
            backup_manager.run_backup,
            trigger=trigger,
            id='auto_backup',
            name='自动备份任务'
        )
        
        # 启动调度器（阻塞运行）
        scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("收到停止信号，程序退出")
        logger.info("=" * 60)
        return 0
    except Exception as e:
        logger.error(f"程序异常退出: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
