#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份管理工具
提供高级备份管理功能：修改描述、删除备份、比较差异等
"""

import logging
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import git

logger = logging.getLogger(__name__)


class BackupManager:
    """高级备份管理器"""
    
    def __init__(self, repo_path: Path, data_path: Path):
        self.repo_path = Path(repo_path)
        self.data_path = Path(data_path)
        self.repo = None
    
    def init_repo(self):
        """初始化仓库"""
        if self.repo_path.exists() and (self.repo_path / '.git').exists():
            self.repo = git.Repo(self.repo_path)
            return True
        return False
    
    def modify_commit_message(self, commit_hash: str, new_message: str) -> bool:
        """修改提交消息（支持任意提交）"""
        try:
            # 获取提交
            commit = self.repo.commit(commit_hash)
            
            # 如果是最新提交，使用 amend（简单快速）
            if commit == self.repo.head.commit:
                self.repo.git.commit('--amend', '-m', new_message)
                logger.info(f"已修改最新提交的描述")
                return True
            else:
                # 历史提交，需要使用 rebase
                # 找到要修改的提交的父提交
                parent = commit.parents[0] if commit.parents else None
                
                if not parent:
                    logger.error("无法修改初始提交")
                    return False
                
                # 创建临时文件用于 rebase 编辑
                
                # 使用 filter-branch 或 rebase 修改
                # 这里使用更简单的方法：通过环境变量传递给 git commit --amend
                old_msg = commit.message
                
                # 执行 rebase
                try:
                    # 创建编辑脚本
                    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
                        script_path = f.name
                        f.write('#!/bin/bash\n')
                        f.write(f'''
if [ "$GIT_COMMIT" = "{commit.hexsha}" ]; then
    cat > /tmp/new_msg << 'EOFMSG'
{new_message}
EOFMSG
    git commit --amend -F /tmp/new_msg
fi
''')
                    
                    os.chmod(script_path, 0o755)
                    
                    # 执行 filter-branch
                    env = os.environ.copy()
                    env['FILTER_BRANCH_SQUELCH_WARNING'] = '1'
                    
                    # 使用 filter-branch 重写历史
                    self.repo.git.filter_branch(
                        '-f',
                        '--msg-filter',
                        f'if [ "$(git rev-parse HEAD)" = "{commit.hexsha}" ]; then echo "{new_message}"; else cat; fi',
                        f'{parent.hexsha}..HEAD',
                        env=env
                    )
                    
                    os.unlink(script_path)
                    logger.info(f"已修改历史提交的描述")
                    return True
                    
                except Exception as e:
                    logger.error(f"Rebase 失败: {e}")
                    if os.path.exists(script_path):
                        os.unlink(script_path)
                    return False
                
        except Exception as e:
            logger.error(f"修改描述失败: {e}")
            return False
    
    def delete_commit(self, commit_hash: str) -> bool:
        """删除指定提交（使用 rebase）"""
        try:
            # 这是危险操作，会修改历史
            commit = self.repo.commit(commit_hash)
            
            # 如果是最新提交
            if commit == self.repo.head.commit:
                # 重置到上一个提交
                self.repo.git.reset('--hard', 'HEAD~1')
                logger.info(f"已删除最新提交")
                return True
            else:
                logger.error("只能删除最新提交")
                return False
        except Exception as e:
            logger.error(f"删除提交失败: {e}")
            return False
    
    def compare_with_local(self, commit_hash: str = None) -> dict:
        """比较指定提交（或最新）与当前本地数据的差异"""
        try:
            # 切换到指定版本
            if commit_hash:
                self.repo.git.checkout(commit_hash)
            
            backup_data_path = self.repo_path / 'data'
            
            added = []      # 本地新增
            modified = []   # 已修改
            deleted = []    # 本地删除
            
            # 检查本地文件
            if self.data_path.exists():
                for item in self.data_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(self.data_path)
                        backup_file = backup_data_path / rel_path
                        
                        if not backup_file.exists():
                            added.append(str(rel_path))
                        elif item.stat().st_mtime > backup_file.stat().st_mtime:
                            # 简单的时间戳比较
                            modified.append(str(rel_path))
            
            # 检查备份中已删除的文件
            if backup_data_path.exists():
                for item in backup_data_path.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(backup_data_path)
                        local_file = self.data_path / rel_path
                        
                        if not local_file.exists():
                            deleted.append(str(rel_path))
            
            # 返回到最新版本
            if commit_hash:
                self.repo.git.checkout('HEAD')
            
            return {
                'added': added,
                'modified': modified,
                'deleted': deleted
            }
        except Exception as e:
            logger.error(f"比较差异失败: {e}")
            # 确保返回到 HEAD
            try:
                self.repo.git.checkout('HEAD')
            except:
                pass
            return None
    
    def force_push(self) -> bool:
        """强制推送到远程（修改历史后需要）"""
        try:
            origin = self.repo.remote('origin')
            origin.push(force=True)
            logger.info("已强制推送到远程")
            return True
        except Exception as e:
            logger.error(f"强制推送失败: {e}")
            return False
