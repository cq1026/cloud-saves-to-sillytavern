#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复模块
提供交互式界面从 GitHub 恢复特定版本的备份
"""

import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

import git

logger = logging.getLogger(__name__)


class RestoreManager:
    """恢复管理器"""
    
    def __init__(self, config: Dict):
        """初始化恢复管理器"""
        self.config = config
        
        # Docker 环境检测
        is_docker = os.path.exists('/.dockerenv')
        
        if is_docker:
            # 容器内运行，使用固定的容器内路径
            self.data_path = Path('/data')
            logger.info("Docker 环境：使用容器内数据路径 /data")
        else:
            # 宿主机运行，使用配置的路径
            self.data_path = Path(config['sillytavern_data_path'])
            logger.info(f"宿主机环境：使用配置路径 {self.data_path}")
        
        self.repo_path = Path(config['backup_repo_path'])
        self.remote_url = config['github_remote_url']
        self.repo = None
    
    def init_repo(self):
        """初始化或克隆仓库"""
        try:
            if self.repo_path.exists() and (self.repo_path / '.git').exists():
                # 打开现有仓库
                self.repo = git.Repo(self.repo_path)
                logger.info(f"已打开现有仓库: {self.repo_path}")
                
                # 拉取最新数据
                origin = self.repo.remote('origin')
                origin.fetch()
                logger.info("已从远程仓库拉取最新数据")
            else:
                # 克隆仓库
                logger.info(f"正在克隆仓库: {self.remote_url}")
                self.repo_path.mkdir(parents=True, exist_ok=True)
                self.repo = git.Repo.clone_from(self.remote_url, self.repo_path)
                logger.info("仓库克隆完成")
            
            return True
        except Exception as e:
            logger.error(f"初始化仓库失败: {e}")
            return False
    
    def list_backups(self, max_count: int = 20) -> List[Tuple[str, str, datetime]]:
        """
        列出可用的备份版本
        返回：[(commit_hash, message, datetime), ...]
        """
        try:
            backups = []
            for commit in self.repo.iter_commits('HEAD', max_count=max_count):
                backups.append((
                    commit.hexsha[:7],  # 短哈希
                    commit.message.strip(),
                    datetime.fromtimestamp(commit.committed_date)
                ))
            return backups
        except Exception as e:
            logger.error(f"列出备份失败: {e}")
            return []
    
    def backup_current_data(self) -> Path:
        """
        备份当前的 SillyTavern 数据到临时目录
        返回备份路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = Path(f"/tmp/st-backup-{timestamp}")
        
        try:
            if self.data_path.exists():
                shutil.copytree(self.data_path, backup_path)
                logger.info(f"当前数据已备份到: {backup_path}")
            else:
                logger.warning(f"源目录不存在，跳过备份: {self.data_path}")
            
            return backup_path
        except Exception as e:
            logger.error(f"备份当前数据失败: {e}")
            return None
    
    def restore_version(self, commit_hash: str):
        """恢复指定版本"""
        try:
            # 1. 检出指定版本
            self.repo.git.checkout(commit_hash)
            logger.info(f"已检出版本: {commit_hash}")
            
            # 2. 复制文件到 SillyTavern 目录
            if self.data_path.exists():
                # 删除目标目录内容（保留目录本身）
                for item in self.data_path.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            else:
                self.data_path.mkdir(parents=True, exist_ok=True)
            
            
            # 复制所有文件（从 backup/data/ 恢复到目标）
            backup_data_path = self.repo_path / 'data'
            if not backup_data_path.exists():
                raise FileNotFoundError(f"备份中未找到 data 目录: {backup_data_path}")
            
            for item in backup_data_path.rglob('*'):
                if item.is_file():
                    relative_path = item.relative_to(backup_data_path)
                    target = self.data_path / relative_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)
            
            logger.info(f"文件已恢复到: {self.data_path}")
            
            # 3. 返回到最新版本（避免 detached HEAD）
            self.repo.git.checkout('HEAD')
            
            return True
        except Exception as e:
            logger.error(f"恢复版本失败: {e}")
            return False
    
    def run_interactive_restore(self):
        """运行交互式恢复流程"""
        print("=" * 60)
        print("SillyTavern 数据恢复工具")
        print("=" * 60)
        print()
        
        # 1. 初始化仓库
        if not self.init_repo():
            print("❌ 仓库初始化失败")
            return False
        
        # 2. 列出可用备份
        backups = self.list_backups()
        if not backups:
            print("❌ 没有可用的备份")
            return False
        
        print(f"找到 {len(backups)} 个备份版本：")
        print()
        print("序号  提交哈希  时间                    描述")
        print("-" * 60)
        for i, (hash, msg, dt) in enumerate(backups, 1):
            print(f"{i:2d}.   {hash}    {dt.strftime('%Y-%m-%d %H:%M:%S')}  {msg[:30]}")
        print()
        
        # 3. 选择版本
        while True:
            try:
                choice = input("请选择要恢复的版本（输入序号，或 'q' 退出）: ").strip()
                if choice.lower() == 'q':
                    print("已取消")
                    return False
                
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_hash = backups[index][0]
                    selected_msg = backups[index][1]
                    selected_time = backups[index][2]
                    break
                else:
                    print("❌ 无效的序号，请重新输入")
            except ValueError:
                print("❌ 请输入数字")
        
        print()
        print(f"您选择的版本: {selected_hash} - {selected_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"描述: {selected_msg}")
        print()
        
        # 4. 确认操作
        print("⚠️  警告：此操作将覆盖当前的 SillyTavern 数据！")
        print(f"   当前数据将备份到临时目录")
        print()
        
        confirm = input("确认继续？(yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("已取消")
            return False
        
        print()
        
        # 5. 备份当前数据
        print("正在备份当前数据...")
        backup_path = self.backup_current_data()
        if backup_path:
            print(f"✅ 当前数据已备份到: {backup_path}")
        print()
        
        # 6. 执行恢复
        print("正在恢复数据...")
        if self.restore_version(selected_hash):
            print()
            print("=" * 60)
            print("✅ 恢复完成！")
            print("=" * 60)
            print(f"恢复的版本: {selected_hash}")
            print(f"时间: {selected_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if backup_path:
                print(f"原数据备份: {backup_path}")
            print("=" * 60)
            return True
        else:
            print()
            print("❌ 恢复失败")
            if backup_path:
                print(f"原数据备份保存在: {backup_path}")
            return False


def run_restore():
    """命令行入口点"""
    from config import load_config, validate_config
    from logger import setup_logger
    
    setup_logger()
    
    try:
        config = load_config()
        
        manager = RestoreManager(config)
        return manager.run_interactive_restore()
    except KeyboardInterrupt:
        print("\n\n已取消")
        return False
    except Exception as e:
        logger.error(f"恢复执行失败: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    success = run_restore()
    sys.exit(0 if success else 1)
