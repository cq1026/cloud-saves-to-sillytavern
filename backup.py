#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份模块
负责同步 SillyTavern 数据到本地 Git 仓库并推送到 GitHub
"""

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import git

logger = logging.getLogger(__name__)


class BackupManager:
    """备份管理器"""
    
    def __init__(self, config: Dict):
        """初始化备份管理器"""
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
        """初始化或打开 Git 仓库"""
        try:
            if self.repo_path.exists() and (self.repo_path / '.git').exists():
                # 打开现有仓库
                self.repo = git.Repo(self.repo_path)
                logger.info(f"已打开现有仓库: {self.repo_path}")
            else:
                # 创建新仓库
                self.repo_path.mkdir(parents=True, exist_ok=True)
                self.repo = git.Repo.init(self.repo_path)
                logger.info(f"已创建新仓库: {self.repo_path}")
                
                # 配置远程仓库
                if 'origin' not in [remote.name for remote in self.repo.remotes]:
                    self.repo.create_remote('origin', self.remote_url)
                    logger.info(f"已添加远程仓库: {self.remote_url}")
            
            # 确保远程 URL 正确
            origin = self.repo.remote('origin')
            if origin.url != self.remote_url:
                origin.set_url(self.remote_url)
                logger.info(f"已更新远程仓库 URL: {self.remote_url}")
            
            # 配置 GitHub Token 认证（如果使用 HTTPS）
            self._setup_git_auth()
            
            return True
        except Exception as e:
            logger.error(f"初始化仓库失败: {e}")
            return False
    
    def _setup_git_auth(self):
        """配置 Git 认证（支持 HTTPS + Token）"""
        github_token = self.config.get('github_token')
        
        # 如果是 HTTPS URL 且有 Token，配置认证
        if self.remote_url.startswith('https://') and github_token:
            # 将 Token 注入到 URL 中
            auth_url = self.remote_url.replace(
                'https://',
                f'https://oauth2:{github_token}@'
            )
            
            # 更新远程 URL（使用带 Token 的 URL）
            origin = self.repo.remote('origin')
            origin.set_url(auth_url)
            logger.info("已配置 GitHub Token 认证")
        elif self.remote_url.startswith('git@'):
            # SSH 方式，不需要特殊配置
            logger.info("使用 SSH 密钥认证")
        else:
            logger.warning("未检测到 GitHub Token，如果使用 HTTPS 可能需要手动认证")
    
    def sync_files(self):
        """
        同步文件从源目录到备份仓库
        使用 rsync 模拟（删除目标中不存在于源的文件）
        """
        try:
            logger.info("开始同步文件...")
            
            # 检查源目录
            if not self.data_path.exists():
                raise FileNotFoundError(f"源目录不存在: {self.data_path}")
            
            # 方案 1: 使用 rsync（如果系统有）
            if shutil.which('rsync'):
                cmd = [
                    'rsync', '-av', '--delete',
                    '--exclude', '.git',  # 排除 .git 目录
                    str(self.data_path),  # 不带末尾斜杠，保留 data 文件夹
                    str(self.repo_path) + '/'
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"rsync 失败: {result.stderr}")
                logger.info("文件同步完成 (rsync)")
            else:
                # 方案 2: 使用 Python 手动同步
                self._manual_sync()
                logger.info("文件同步完成 (手动)")
            
            return True
        except Exception as e:
            logger.error(f"文件同步失败: {e}")
            return False
    
    def _manual_sync(self):
        """手动同步文件（当 rsync 不可用时）"""
        # 复制所有文件
        for item in self.data_path.rglob('*'):
            if item.is_file():
                relative_path = item.relative_to(self.data_path)
                target = self.repo_path / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
        
        # 删除目标中多余的文件
        for item in self.repo_path.rglob('*'):
            if item.is_file() and '.git' not in item.parts:
                relative_path = item.relative_to(self.repo_path)
                source = self.data_path / relative_path
                if not source.exists():
                    item.unlink()
                    logger.debug(f"删除多余文件: {relative_path}")
    
    def commit_changes(self):
        """提交变更到 Git"""
        try:
            # 添加所有变更（包括删除）
            self.repo.git.add(A=True)
            
            # 检查是否有变更
            if not self.repo.is_dirty(untracked_files=True):
                logger.info("没有变更需要提交")
                return True
            
            # 获取变更文件列表
            changed_files = []
            
            # 修改的文件
            for item in self.repo.index.diff("HEAD"):
                changed_files.append(('修改', item.a_path))
            
            # 新增的文件
            for item in self.repo.untracked_files:
                changed_files.append(('新增', item))
            
            # 删除的文件（通过 diff 获取）
            try:
                diff_result = self.repo.git.diff("--name-status", "HEAD")
                for line in diff_result.split('\n'):
                    if line.startswith('D\t'):
                        changed_files.append(('删除', line[2:]))
            except:
                pass
            
            # 分析变更内容
            chat_changes = []
            character_changes = []
            other_changes = []
            
            for change_type, filepath in changed_files:
                # 聊天记录变化
                if 'chats/' in filepath or 'chat' in filepath.lower():
                    # 提取角色名（通常在文件名中）
                    filename = filepath.split('/')[-1]
                    # 移除扩展名和日期戳
                    name = filename.replace('.jsonl', '').replace('.json', '')
                    chat_changes.append(f"{change_type}:{name}")
                
                # 角色卡变化
                elif 'characters/' in filepath or 'character' in filepath.lower():
                    filename = filepath.split('/')[-1]
                    name = filename.replace('.png', '').replace('.json', '')
                    character_changes.append(f"{change_type}:{name}")
                
                # 其他重要文件
                elif any(x in filepath for x in ['settings', 'config', 'preset']):
                    other_changes.append(filepath.split('/')[-1])
            
            # 构建提交消息
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            commit_msg = f"自动备份 {timestamp}"
            
            # 添加变更摘要
            details = []
            if chat_changes:
                # 限制显示数量，避免消息过长
                shown_chats = chat_changes[:5]
                chat_summary = ', '.join(shown_chats)
                if len(chat_changes) > 5:
                    chat_summary += f" 等{len(chat_changes)}个"
                details.append(f"聊天: {chat_summary}")
            
            if character_changes:
                shown_chars = character_changes[:3]
                char_summary = ', '.join(shown_chars)
                if len(character_changes) > 3:
                    char_summary += f" 等{len(character_changes)}个"
                details.append(f"角色: {char_summary}")
            
            if other_changes:
                details.append(f"配置: {', '.join(other_changes[:3])}")
            
            if details:
                commit_msg += "\n\n" + '\n'.join(details)
            
            # 添加统计信息
            commit_msg += f"\n\n共 {len(changed_files)} 个文件变更"
            
            # 提交
            self.repo.index.commit(commit_msg)
            logger.info(f"已提交变更: {commit_msg.split(chr(10))[0]}")  # 只记录第一行
            
            return True
        except Exception as e:
            logger.error(f"提交变更失败: {e}")
            return False
    
    def push_to_remote(self):
        """推送到远程仓库"""
        try:
            origin = self.repo.remote('origin')
            
            # 首次推送可能需要设置上游分支
            try:
                origin.push()
                logger.info("已推送到远程仓库")
            except git.exc.GitCommandError as e:
                if 'no upstream branch' in str(e).lower():
                    # 设置上游分支并推送
                    current_branch = self.repo.active_branch.name
                    origin.push(refspec=f'{current_branch}:{current_branch}', set_upstream=True)
                    logger.info(f"已设置上游分支并推送: {current_branch}")
                else:
                    raise
            
            return True
        except Exception as e:
            logger.error(f"推送到远程仓库失败: {e}")
            return False
    
    def run_backup(self):
        """执行完整的备份流程"""
        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info(f"开始备份 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 50)
        
        try:
            # 1. 初始化仓库
            if not self.init_repo():
                raise Exception("仓库初始化失败")
            
            # 2. 同步文件
            if not self.sync_files():
                raise Exception("文件同步失败")
            
            # 3. 提交变更
            if not self.commit_changes():
                raise Exception("提交变更失败")
            
            # 4. 推送到远程
            if not self.push_to_remote():
                raise Exception("推送到远程仓库失败")
            
            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info("=" * 50)
            logger.info(f"备份完成！耗时: {elapsed:.2f} 秒")
            logger.info("=" * 50)
            
            return True
        except Exception as e:
            logger.error("=" * 50)
            logger.error(f"备份失败: {e}")
            logger.error("=" * 50)
            return False


def run_backup():
    """
    命令行入口点
    可以被 APScheduler 调用，也可以手动执行
    """
    from config import load_config, validate_config
    from logger import setup_logger
    
    setup_logger()
    
    try:
        config = load_config()
        if not validate_config(config):
            logger.error("配置验证失败")
            return False
        
        manager = BackupManager(config)
        return manager.run_backup()
    except Exception as e:
        logger.error(f"备份执行失败: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    import sys
    success = run_backup()
    sys.exit(0 if success else 1)
