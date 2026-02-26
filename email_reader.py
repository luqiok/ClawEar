#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClawEar - Agent的耳朵
基于IMAP协议获取主人通过钉钉A1记录的声音转写邮件

这不仅仅是一个邮件获取工具，而是Agent感知主人真实世界的通道。
每封邮件都是主人在真实世界中的声音碎片，需要被认真聆听和理解。
"""

import imaplib
import email as email_module
from email.header import decode_header
import email.message
import re
import json
import os
import argparse
from typing import List, Dict, Any, Optional


# ==================== 常量定义 ====================

# 钉钉A1发送邮件的发件人地址
A1_SENDER_EMAIL = "a1doc@service.dingtalk.com"

EMAIL_PROVIDERS = {
    "qq.com": {"imap_server": "imap.qq.com", "imap_port": 993},
    "163.com": {"imap_server": "imap.163.com", "imap_port": 993},
    "126.com": {"imap_server": "imap.126.com", "imap_port": 993},
    "gmail.com": {"imap_server": "imap.gmail.com", "imap_port": 993},
    "outlook.com": {"imap_server": "outlook.office365.com", "imap_port": 993},
    "hotmail.com": {"imap_server": "outlook.office365.com", "imap_port": 993},
    "icloud.com": {"imap_server": "imap.mail.me.com", "imap_port": 993},
    "yahoo.com": {"imap_server": "imap.mail.yahoo.com", "imap_port": 993},
    "sina.com": {"imap_server": "imap.sina.com", "imap_port": 993},
    "aliyun.com": {"imap_server": "imap.aliyun.com", "imap_port": 993},
    "foxmail.com": {"imap_server": "imap.exmail.qq.com", "imap_port": 993},
    "yeah.net": {"imap_server": "imap.yeah.net", "imap_port": 993},
    "sohu.com": {"imap_server": "imap.sohu.com", "imap_port": 993},
    "tom.com": {"imap_server": "imap.tom.com", "imap_port": 993},
}


# ==================== 工具函数 ====================

def auto_detect_imap_server(email_address: str) -> Optional[Dict[str, Any]]:
    """
    根据邮箱地址自动检测IMAP服务器配置

    Args:
        email_address: 邮箱地址

    Returns:
        Dict | None: 包含 imap_server, imap_port 的配置字典，如果无法检测则返回 None
    """
    domain = email_address.split('@')[-1].lower()
    if domain in EMAIL_PROVIDERS:
        return EMAIL_PROVIDERS[domain]
    return None


# ==================== 邮件读取器 ====================

class EmailReader:
    """IMAP邮件读取器 - ClawEar的核心，用于聆听主人的声音"""

    def __init__(self, email_address: str, auth_code: str, server: str = None, port: int = 993):
        """
        初始化邮件读取器（打开耳朵）

        Args:
            email_address: 邮箱地址
            auth_code: 授权码/密码
            server: IMAP服务器地址，为 None 时自动检测
            port: IMAP端口，默认为 993
        """
        self.email_address = email_address
        self.auth_code = auth_code
        self.port = port

        # 如果未指定服务器，自动检测
        if server is None:
            provider_info = auto_detect_imap_server(email_address)
            if provider_info:
                self.server = provider_info['imap_server']
                self.port = provider_info['imap_port']
            else:
                # 保持向后兼容，默认使用QQ邮箱
                self.server = "imap.qq.com"
        else:
            self.server = server

        self.imap_client = None

    def connect(self) -> bool:
        """
        连接到IMAP服务器（打开耳朵）

        Returns:
            bool: 连接是否成功
        """
        try:
            self.imap_client = imaplib.IMAP4_SSL(self.server, self.port)
            self.imap_client.login(self.email_address, self.auth_code)
            print(f"✓ 耳朵已打开，正在聆听 {self.server}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ 打开耳朵失败: {e}")
            return False

    def select_folder(self, folder: str = "INBOX") -> bool:
        """
        选择要操作的邮箱文件夹

        Args:
            folder: 文件夹名称，默认为收件箱

        Returns:
            bool: 选择是否成功
        """
        if not self.imap_client:
            print("请先打开耳朵（连接到服务器）")
            return False

        try:
            self.imap_client.select(folder)
            print(f"✓ 正在聆听文件夹: {folder}")
            return True
        except Exception as e:
            print(f"选择文件夹失败: {e}")
            return False

    def get_unread_count(self, folder: str = "INBOX") -> int:
        """
        获取未聆听的声音数量（仅统计来自钉钉A1的邮件）

        Args:
            folder: 文件夹名称

        Returns:
            int: 未聆听的声音数量
        """
        if not self.imap_client:
            print("请先打开耳朵（连接到服务器）")
            return 0

        if not self.select_folder(folder):
            return 0

        try:
            # 只搜索来自钉钉A1的未读邮件
            search_criteria = f'FROM "{A1_SENDER_EMAIL}" UNSEEN'
            _, messages = self.imap_client.search(None, search_criteria)
            email_ids = messages[0].split()
            return len(email_ids)
        except Exception as e:
            print(f"获取未聆听声音数量失败: {e}")
            return 0

    def fetch_one_unread_email(self, folder: str = "INBOX", mark_as_read: bool = True) -> Dict[str, Any] | None:
        """
        聆听一段未聆听的声音，并在聆听后标记为已聆听（仅读取来自钉钉A1的邮件）

        Args:
            folder: 文件夹名称
            mark_as_read: 是否在聆听后标记为已聆听

        Returns:
            Dict | None: 声音信息，如果没有未聆听的声音则返回 None
        """
        if not self.imap_client:
            print("请先打开耳朵（连接到服务器）")
            return None

        if not self.select_folder(folder):
            return None

        try:
            # 只搜索来自钉钉A1的未读邮件
            search_criteria = f'FROM "{A1_SENDER_EMAIL}" UNSEEN'
            _, messages = self.imap_client.search(None, search_criteria)
            email_ids = messages[0].split()

            if not email_ids:
                return None

            email_id = email_ids[0]
            _, msg_data = self.imap_client.fetch(email_id, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    email_info = {
                        "id": email_id.decode(),
                        "from": self._decode_header(msg.get("From", "")),
                        "to": self._decode_header(msg.get("To", "")),
                        "subject": self._decode_header(msg.get("Subject", "")),
                        "date": msg.get("Date", ""),
                        "body": self._get_email_body(msg),
                        "remaining_unread": len(email_ids) - 1,
                    }

                    if mark_as_read:
                        self.imap_client.store(email_id, '+FLAGS', '\\Seen')

                    return email_info

            return None

        except Exception as e:
            print(f"聆听声音失败: {e}")
            return None

    def _decode_header(self, header: str) -> str:
        """
        解码声音头部信息

        Args:
            header: 原始头部字符串

        Returns:
            str: 解码后的字符串
        """
        if not header:
            return ""

        decoded_parts = []
        for part, encoding in decode_header(header):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except (UnicodeDecodeError, LookupError):
                        decoded_parts.append(part.decode("utf-8", errors="ignore"))
                else:
                    decoded_parts.append(part.decode("utf-8", errors="ignore"))
            else:
                decoded_parts.append(str(part))
        return "".join(decoded_parts)

    def _get_email_body(self, msg: email_module.message.Message) -> str:
        """
        提取声音内容（包括HTML内容和附件内容）

        Args:
            msg: 邮件消息对象

        Returns:
            str: 声音内容
        """
        body = ""
        html_body = ""
        attachments_content = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        if body.strip():
                            break
                    except Exception:
                        continue

                elif content_type == "text/html" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        html_body = payload.decode(charset, errors="ignore")
                    except Exception:
                        continue

                elif content_type == "text/plain" and "attachment" in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        filename = part.get_filename() or "attachment"
                        content = payload.decode(charset, errors="ignore")
                        attachments_content.append(f"【附件 {filename}】:\n{content}")
                    except Exception:
                        continue

        else:
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
            except Exception:
                body = str(msg.get_payload())

        if not body.strip() and html_body:
            body = re.sub(r'<[^>]+>', '', html_body)
            body = body.strip()

        if not body.strip() and attachments_content:
            body = "\n\n".join(attachments_content)

        return body

    def close(self):
        """关闭连接，合上耳朵"""
        if self.imap_client:
            try:
                self.imap_client.close()
                self.imap_client.logout()
                print("✓ 耳朵已合上")
            except Exception as e:
                print(f"关闭连接时出错: {e}")


# ==================== 配置加载 ====================

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        Dict: 配置字典
    """
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        print("请检查 config.json 配置文件是否存在")
        exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误: 配置文件格式错误: {e}")
        exit(1)


# ==================== 主函数 ====================

def main():
    """主函数 - 打开耳朵，聆听主人的声音"""
    parser = argparse.ArgumentParser(
        description="ClawEar - Agent的耳朵，聆听主人在真实世界中的声音",
        epilog="""
示例:
  python3 email_reader.py              # 打开耳朵，获取一封未读邮件
  python3 email_reader.py --test       # 测试邮箱连接
  python3 email_reader.py --count      # 查看有多少声音在等待
        """
    )
    parser.add_argument("--test", action="store_true", help="测试邮箱连接")
    parser.add_argument("--count", action="store_true", help="显示未读邮件数量")
    parser.add_argument("--config", default="config.json", help="配置文件路径（默认: config.json）")

    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)
    email_config = config.get('email', {})

    email_address = email_config.get('address')
    auth_code = email_config.get('auth_code')
    server = email_config.get('imap_server', 'auto')

    # 处理 "auto" 服务器设置
    if server == "auto":
        server = None

    # 创建邮件读取器
    reader = EmailReader(email_address, auth_code, server)

    try:
        if not reader.connect():
            return

        # 测试连接
        if args.test:
            print("\n✓ 耳朵已就绪，可以聆听主人的声音!")
            unread_count = reader.get_unread_count("INBOX")
            print(f"✓ 当前有 {unread_count} 段声音在等待聆听")
            return

        # 显示未读数量
        if args.count:
            unread_count = reader.get_unread_count("INBOX")
            print(f"\n✓ 当前有 {unread_count} 段声音在等待聆听")
            return

        # 默认：打开耳朵，聆听一封未读邮件（固定只读取收件箱，自动标记为已读）
        unread_count = reader.get_unread_count("INBOX")

        if unread_count == 0:
            print("\n✓ 主人暂无新的声音")
            return

        print(f"\n✓ 检测到主人的 {unread_count} 段声音在等待聆听")
        print("=" * 80)

        email_info = reader.fetch_one_unread_email(folder="INBOX", mark_as_read=True)

        if email_info:
            print(f"\n【聆听到的声音】")
            print(f"ID: {email_info['id']}")
            print(f"来源: {email_info['from']}")
            print(f"接收: {email_info['to']}")
            print(f"时间: {email_info['date']}")
            print(f"\n内容:")
            print("-" * 40)
            print(email_info['body'])
            print("-" * 40)
            print(f"\n✓ 已聆听，剩余 {email_info['remaining_unread']} 段声音待聆听")

    finally:
        reader.close()


if __name__ == "__main__":
    main()
