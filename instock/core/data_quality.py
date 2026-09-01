"""
数据质量工具模块 - 供所有策略脚本调用
功能：检查 stock_daily 数据是否完整、最新
"""
import pymysql
from datetime import date, datetime

DB = {'host':'localhost','user':'stock','password':'12345678','database':'instock','port':3306,'charset':'utf8mb4'}

def check_data_freshness(target_date=None):
    """检查 stock_daily 数据完整性
    
    Returns:
        dict: {
            'latest_date': str or None,
            'total_stocks': int,
            'available_stocks': int,
            'completeness': float (0-100),
            'is_fresh': bool (是否包含目标日期数据)
        }
    """
    if target_date is None:
        target_date = date.today()
    if isinstance(target_date, date):
        target_date = target_date.strftime('%Y-%m-%d')
    
    conn = pymysql.connect(**DB)
    c = conn.cursor()
    try:
        c.execute('SELECT MAX(date) FROM stock_daily')
        latest = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM stock_info 
            WHERE (code LIKE "60%%" OR code LIKE "00%%" OR code LIKE "30%%")
            AND code NOT LIKE "688%%"''')
        total = c.fetchone()[0]
        
        if latest:
            c.execute('SELECT COUNT(DISTINCT stock_id) FROM stock_daily WHERE date = %s', (latest,))
            avail = c.fetchone()[0]
        else:
            avail = 0
        
        is_fresh = (latest == target_date) if latest else False
        completeness = (avail / total * 100) if total > 0 else 0
        
        return {
            'latest_date': str(latest) if latest else None,
            'total_stocks': total,
            'available_stocks': avail,
            'completeness': round(completeness, 1),
            'is_fresh': is_fresh
        }
    finally:
        conn.close()

def get_valid_stocks(target_date=None):
    """获取有完整数据的股票列表
    
    只返回 stock_daily 包含目标日期数据的股票
    """
    if target_date is None:
        target_date = date.today()
    if isinstance(target_date, date):
        target_date = target_date.strftime('%Y-%m-%d')
    
    conn = pymysql.connect(**DB)
    try:
        sql = f"""
        SELECT si.id, si.code, si.name
        FROM stock_info si
        INNER JOIN stock_daily sd ON si.id = sd.stock_id AND sd.date = '{target_date}'
        WHERE (si.code LIKE '60%%' OR si.code LIKE '00%%' OR si.code LIKE '30%%')
          AND si.code NOT LIKE '688%%'
        GROUP BY si.id, si.code, si.name
        ORDER BY si.code
        """
        import pandas as pd
        df = pd.read_sql(sql, conn)
        return df
    finally:
        conn.close()

def print_data_status():
    """打印数据状态摘要"""
    status = check_data_freshness()
    print('=' * 60)
    print('数据状态检查')
    print('=' * 60)
    print(f'stock_daily 最新日期: {status["latest_date"]}')
    print(f'A股总数: {status["total_stocks"]} 只')
    print(f'含最新数据的: {status["available_stocks"]} 只')
    print(f'完整度: {status["completeness"]}%')
    if status['is_fresh']:
        print('✅ 数据已包含今日数据')
    else:
        print(f'⚠ 数据未更新到今日（最新: {status["latest_date"]}）')
    print('=' * 60)
    return status

if __name__ == '__main__':
    print_data_status()
