import requests
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TencentFetcher:
    """
    腾讯财经实时行情抓取器 (T+0)
    直接调用腾讯 HTTP 接口，无需爬虫库，稳定性极高。
    """
    
    def __init__(self):
        self.base_url = "http://qt.gtimg.cn/q="
        
    def _format_code(self, stock_code: str) -> str:
        """转换代码为腾讯格式: sh600519, sz000001"""
        code = stock_code.strip()
        if code.startswith(('60', '68', '90')):
            return f"sh{code}"
        else:
            return f"sz{code}"

    def get_realtime_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取个股实时行情"""
        try:
            formatted_code = self._format_code(stock_code)
            url = f"{self.base_url}{formatted_code}"
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                return None
                
            content = response.text
            # 腾讯返回格式: v_sh600519="1~贵州茅台~600519~1800.00~1790.00~..."
            data = re.findall(r'"(.*?)"', content)
            if not data:
                return None
                
            parts = data[0].split('~')
            if len(parts) < 40:
                return None
                
            return {
                'name': parts[1],
                'code': parts[2],
                'current': float(parts[3]),
                'prev_close': float(parts[4]),
                'open': float(parts[5]),
                'volume': float(parts[6]), # 万手
                'high': float(parts[33]),
                'low': float(parts[34]),
                'pct_chg': float(parts[32]),
                'amount': float(parts[37]), # 万
                'time': parts[30]
            }
        except Exception as e:
            logger.error(f"腾讯接口获取 {stock_code} 失败: {e}")
            return None

    def get_indices(self) -> Dict[str, Dict[str, Any]]:
        """获取主要指数实时行情"""
        indices = {
            "sh000001": "上证指数",
            "sz399001": "深证成指",
            "sz399006": "创业板指",
            "sh000300": "沪深300"
        }
        results = {}
        try:
            codes = ",".join(indices.keys())
            url = f"{self.base_url}{codes}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                content = response.text
                lines = content.split(';')
                for line in lines:
                    data = re.findall(r'v_(.*?)="(.*?)"', line)
                    if data:
                        code, val_str = data[0]
                        parts = val_str.split('~')
                        if len(parts) > 32:
                            results[indices.get(code, code)] = {
                                'current': float(parts[3]),
                                'change': float(parts[31]),
                                'pct_change': float(parts[32]),
                                'amount': float(parts[37]) # 万
                            }
        except Exception as e:
            logger.error(f"获取指数实时行情失败: {e}")
        return results
