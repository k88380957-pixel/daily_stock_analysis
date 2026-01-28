"""
===================================
大盘复盘分析模块 (Baostock 专用版)
===================================

职责：
1. 使用 Baostock 获取大盘指数数据
2. 搜索市场新闻形成复盘情报
3. 使用大模型生成每日大盘复盘报告
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

import pandas as pd
from data_provider.baostock_fetcher import BaostockFetcher
from src.config import get_config
from src.search_service import SearchService

logger = logging.getLogger(__name__)


@dataclass
class MarketIndex:
    """大盘指数数据"""
    code: str                    # 指数代码
    name: str                    # 指数名称
    current: float = 0.0         # 当前点位
    change: float = 0.0          # 涨跌点数
    change_pct: float = 0.0      # 涨跌幅(%)
    open: float = 0.0            # 开盘点位
    high: float = 0.0            # 最高点位
    low: float = 0.0             # 最低点位
    prev_close: float = 0.0      # 昨收点位
    volume: float = 0.0          # 成交量（手）
    amount: float = 0.0          # 成交额（元）
    amplitude: float = 0.0       # 振幅(%)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'code': self.code,
            'name': self.name,
            'current': self.current,
            'change': self.change,
            'change_pct': self.change_pct,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'prev_close': self.prev_close,
            'volume': self.volume,
            'amount': self.amount,
            'amplitude': self.amplitude
        }


@dataclass
class MarketSector:
    """板块数据"""
    name: str
    pct_change: float


@dataclass
class MarketOverview:
    """市场概览数据"""
    date: str
    indices: List[MarketIndex] = field(default_factory=list)
    up_count: int = 0
    down_count: int = 0
    limit_up_count: int = 0
    limit_down_count: int = 0
    total_amount: float = 0.0    # 两市成交额（亿）
    top_sectors: List[MarketSector] = field(default_factory=list)
    bottom_sectors: List[MarketSector] = field(default_factory=list)
    news: List[Dict[str, str]] = field(default_factory=list)
    summary: str = ""            # AI 生成的复盘总结


class MarketAnalyzer:
    """
    大盘分析器
    
    功能：
    1. 获取大盘指数行情 (基于 Baostock)
    2. 模拟市场涨跌统计
    3. 搜索市场新闻
    4. 生成大盘复盘报告
    """
    
    # 主要指数代码 (Baostock 格式)
    MAIN_INDICES = {
        'sh.000001': '上证指数',
        'sz.399001': '深证成指',
        'sz.399006': '创业板指',
        'sh.000688': '科创50',
        'sh.000300': '沪深300',
    }
    
    def __init__(self, search_service: Optional[SearchService] = None, analyzer=None):
        """
        初始化大盘分析器
        """
        self.config = get_config()
        self.search_service = search_service
        self.analyzer = analyzer
        self.fetcher = BaostockFetcher()
        
    def get_market_overview(self) -> MarketOverview:
        """
        获取市场概览数据
        """
        today = datetime.now().strftime('%Y-%m-%d')
        overview = MarketOverview(date=today)
        
        # 1. 获取主要指数行情
        overview.indices = self._get_main_indices()
        
        # 2. 模拟市场涨跌统计
        self._get_market_statistics(overview)
        
        # 3. 搜索新闻
        if self.search_service:
            overview.news = self.search_service.search_market_news()
            
        return overview

    def _get_main_indices(self) -> List[MarketIndex]:
        """使用 Baostock 获取指数行情"""
        indices = []
        try:
            logger.info("[大盘] 使用 Baostock 获取指数行情...")
            for bs_code, name in self.MAIN_INDICES.items():
                try:
                    # 获取最近 2 天数据以计算涨跌
                    df = self.fetcher.get_daily_data(bs_code, days=2)
                    if df is not None and len(df) >= 2:
                        latest = df.iloc[-1]
                        prev = df.iloc[-2]
                        
                        current_price = float(latest['close'])
                        prev_price = float(prev['close'])
                        change = current_price - prev_price
                        change_pct = (change / prev_price) * 100 if prev_price > 0 else 0
                        
                        index = MarketIndex(
                            code=bs_code,
                            name=name,
                            current=current_price,
                            change=change,
                            change_pct=change_pct,
                            open=float(latest['open']),
                            high=float(latest['high']),
                            low=float(latest['low']),
                            prev_close=prev_price,
                            volume=float(latest['volume']),
                            amount=float(latest['amount'])
                        )
                        if index.prev_close > 0:
                            index.amplitude = (index.high - index.low) / index.prev_close * 100
                        indices.append(index)
                except Exception as e:
                    logger.warning(f"[大盘] 获取指数 {name} 失败: {e}")
        except Exception as e:
            logger.error(f"[大盘] 获取指数行情失败: {e}")
        return indices
    
    def _get_market_statistics(self, overview: MarketOverview):
        """模拟市场涨跌统计 (基于指数表现)"""
        if overview.indices:
            sh_index = next((idx for idx in overview.indices if idx.name == "上证指数"), None)
            if sh_index:
                if sh_index.change_pct > 0:
                    overview.up_count = 3200
                    overview.down_count = 1600
                else:
                    overview.up_count = 1600
                    overview.down_count = 3200
                overview.total_amount = sh_index.amount / 1e8 * 2.8
        
        overview.limit_up_count = 0
        overview.limit_down_count = 0
        overview.top_sectors = []
        overview.bottom_sectors = []
