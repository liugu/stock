#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
正式网格交易机器人（对接币安真实API）
- 初始化：市价买入底仓 + 挂初始网格
- 维护循环：检测成交 → 补反向订单
- 运行模式：
    --init      首次建网格
    --run       维护循环（检测成交并补单）
    --status    查看当前挂单/持仓/收益
    --cancel    撤销所有挂单
    --dry       试运行（不下真实单，只打印将要做的动作）
"""
import os, sys, json, time
from datetime import datetime
from binance_client import BinanceClient

# 网格参数
GRID_LOWER = 0.075
GRID_UPPER = 0.105
GRID_COUNT = 8          # 网格段数（生成 GRID_COUNT-1 个内部挂单价）
SEED_USDT = 15.0        # 初始化底仓买入金额U
ORDER_AMOUNT = 4.0      # 每格买入金额U
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grid_state.json')

DRY = '--dry' in sys.argv


def log(msg):
    print(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}', flush=True)


def grid_levels(lower, upper, count):
    """返回内部网格价位（不含上下边界）"""
    step = (upper - lower) / count
    lv = []
    for i in range(1, count):
        lv.append(round(lower + step * i, 6))
    return lv


def load_grid_config():
    """从配置文件读取网格参数（缺失用默认）"""
    CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'api_keys.json')
    try:
        with open(CFG_PATH, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print(f'[config] 读取配置失败: {e}')
        cfg = {}
    return {
        'lower': cfg.get('grid_lower', GRID_LOWER),
        'upper': cfg.get('grid_upper', GRID_UPPER),
        'count': cfg.get('grid_count', GRID_COUNT),
        'seed': cfg.get('SEED_USDT', SEED_USDT),
        'order_amt': cfg.get('ORDER_AMOUNT', ORDER_AMOUNT),
    }


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'last_trade_id': 0, 'orders': {}}


def save_state(s):
    with open(STATE_FILE, 'w') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def find_level(price, levels):
    """找到价格所在格段，返回(下端价, 上端价)，用于决定挂单位置"""
    if price <= levels[0]:
        return levels[0] - (levels[1]-levels[0]), levels[0]
    if price >= levels[-1]:
        return levels[-1], levels[-1] + (levels[-1]-levels[-2])
    for i in range(len(levels)-1):
        if levels[i] <= price <= levels[i+1]:
            return levels[i], levels[i+1]
    return None


def do_init(client, cfg):
    """初始化：买入底仓 + 挂下方买单 + 上方卖单"""
    price = client.get_price()
    usdt = client.get_balance().get('USDT', 0)
    log(f'初始化: DOGE ${price:.4f}, USDT {usdt:.2f}')

    # 1. 市价买入底仓
    seed = cfg.get('SEED_USDT', SEED_USDT)
    if seed > 0 and not DRY:
        log(f'  市价买入底仓 {seed}U ...')
        try:
            client.market_buy(seed)
            time.sleep(2)
        except Exception as e:
            log(f'  ⚠ 底仓买入失败: {e}')
    else:
        log(f'  [dry] 拟市价买入底仓 {seed}U')

    # 2. 刷新余额
    bal = client.get_balance()
    usdt, doge = bal.get('USDT', 0), bal.get('DOGE', 0)
    log(f'  持仓: USDT {usdt:.2f} / DOGE {doge:.2f}')

    price = client.get_price()
    levels = grid_levels(GRID_LOWER, GRID_UPPER, GRID_COUNT)
    lo, hi = find_level(price, levels)
    log(f'  当前价段: ${lo:.4f} ~ ${hi:.4f}')

    # 3. 挂下方买单（每格 ORDER_AMOUNT U）
    below = [l for l in levels if l < price]
    order_amt = cfg.get('ORDER_AMOUNT', ORDER_AMOUNT)
    for l in below:
        # DOGE USDT stepSize=1, 数量必须是整数（向下取整）
        qty = int(order_amt / l)
        if qty >= 1:
            if DRY:
                log(f'  [dry] BUY {qty} DOGE @ ${l:.4f}')
            else:
                try:
                    client.place_limit('BUY', qty, l)
                    log(f'  ✅ BUY {qty}DOGE @${l:.4f}')
                    time.sleep(0.3)
                except Exception as e:
                    log(f'  ⚠ BUY失败 @${l:.4f}: {e}')

    # 4. 挂上方卖单（用底仓DOGE均分）
    above = [l for l in levels if l > price]
    if above and doge > 0:
        per = int(doge / len(above))
        for l in above:
            if per >= 1:
                if DRY:
                    log(f'  [dry] SELL {per}DOGE @${l:.4f}')
                else:
                    try:
                        client.place_limit('SELL', per, l)
                        log(f'  ✅ SELL {per}DOGE @${l:.4f}')
                        time.sleep(0.3)
                    except Exception as e:
                        log(f'  ⚠ SELL失败 @${l:.4f}: {e}')

    # 保存初始成交ID，避免维护循环把历史成交当新成交
    state = load_state()
    try:
        trades = client.my_trades(limit=1)
        if trades:
            state['last_trade_id'] = max(t['id'] for t in trades)
            lid = state['last_trade_id']
            log(f'  已记录基准成交ID: {lid}')
    except Exception as e:
        log(f'  ⚠ 记录基准ID失败: {e}')
    save_state(state)

    log('初始化完成')


def do_run(client, cfg):
    """维护循环：检测新成交，补反向订单"""
    state = load_state()
    g = load_grid_config()
    levels = grid_levels(g['lower'], g['upper'], g['count'])
    last_id = state.get('last_trade_id', 0)

    price = client.get_price()
    log(f'维护循环: DOGE ${price:.4f} (区间{g["lower"]}~{g["upper"]})')

    # 1. 检测新成交
    try:
        trades = client.my_trades(from_id=last_id + 1)
    except Exception as e:
        log(f'  ⚠ 查成交失败: {e}')
        trades = []

    new_trades = [t for t in trades if t['id'] > last_id]
    if new_trades:
        new_last = max(t['id'] for t in new_trades)
        state['last_trade_id'] = new_last
        log(f'  检测到 {len(new_trades)} 笔新成交')
        for t in new_trades:
            side = '买入' if t['isBuyer'] else '卖出'
            log(f'    ✅ {side} {t["qty"]}DOGE @${t["price"]} (佣金{t["commission"]}{t["commissionAsset"]})')
    else:
        log('  无新成交')

    # 2. 查询当前挂单，用于查重
    try:
        opens = client.open_orders()
    except Exception:
        opens = []
    open_by_side_price = set()
    for o in opens:
        open_by_side_price.add((o['side'], round(float(o['price']), 6)))

    # 3. 补单逻辑：对每笔新成交，在对向格补单
    #    (买入成交→在上方格挂卖单; 卖出成交→在下方格挂买单)
    for t in new_trades:
        fill_price = float(t['price'])
        qty = float(t['qty'])
        below_p = None
        above_p = None
        for l in levels:
            if l < fill_price:
                below_p = l
            if l > fill_price and above_p is None:
                above_p = l
        if t['isBuyer']:  # 买入成交，补上方卖单
            target = above_p
            if target is None:
                continue
            pair = ('SELL', round(target, 6))
            if pair in open_by_side_price:
                log(f'  已有卖单@{target}，跳过补单')
                continue
            if not DRY:
                place_qty = qty
                try:
                    client.place_limit('SELL', place_qty, target)
                    log(f'  ➕ 补卖单 {place_qty:.0f}DOGE @${target}')
                    open_by_side_price.add(pair)
                except Exception as e:
                    log(f'  ⚠ 补卖失败: {e}')
            else:
                log(f'  [dry] 补卖单 {qty:.0f}DOGE @${target}')
        else:  # 卖出成交，补下方买单
            target = below_p
            if target is None:
                continue
            pair = ('BUY', round(target, 6))
            if pair in open_by_side_price:
                log(f'  已有买单@{target}，跳过补单')
                continue
            if not DRY:
                buy_qty = int(qty * fill_price / target)
                try:
                    client.place_limit('BUY', buy_qty, target)
                    log(f'  ➕ 补买单 {buy_qty:.2f}DOGE @${target}')
                    open_by_side_price.add(pair)
                except Exception as e:
                    log(f'  ⚠ 补买失败: {e}')
            else:
                log(f'  [dry] 补买单 {qty*fill_price/target:.2f}DOGE @${target}')

    save_state(state)
    log('维护完成')


def do_status(client, cfg):
    """查看挂单、持仓、收益"""
    bal = client.get_balance()
    usdt, doge = bal.get('USDT', 0), bal.get('DOGE', 0)
    price = client.get_price()
    doge_value = doge * price
    total = usdt + doge_value
    log(f'持仓: USDT {usdt:.2f} + DOGE {doge:.2f} (≈{doge_value:.2f}U) = 总 {total:.2f}U')
    log(f'当前DOGE: ${price:.4f}')

    orders = client.open_orders()
    if orders:
        log(f'挂单 {len(orders)} 个:')
        for o in orders:
            side = '买入' if o['side'] == 'BUY' else '卖出'
            log(f'  {side} {o["origQty"]}DOGE @${o["price"]} 状态:{o["status"]}')
    else:
        log('当前无挂单')

    # 最近成交
    try:
        trades = client.my_trades(limit=10)
        if trades:
            log(f'最近 {len(trades)} 笔成交:')
            for t in trades[:10]:
                side = '买入' if t['isBuyer'] else '卖出'
                ts = datetime.fromtimestamp(t['time']/1000).strftime('%m-%d')
                log(f'  {ts} {side} {t["qty"]}DOGE @${t["price"]}')
    except Exception as e:
        log(f'  ⚠ 成交查询失败: {e}')


def do_cancel(client, cfg):
    try:
        r = client.cancel_all()
        log(f'已撤销 {len(r)} 个挂单')
    except Exception as e:
        log(f'⚠ 撤销失败: {e}')


def do_regrid(client, cfg):
    """撤销旧网格，用现有持仓按新区间重建（不额外买入底仓）"""
    g = load_grid_config()
    lower, upper, count = g['lower'], g['upper'], g['count']

    # 1. 撤销所有旧挂单
    try:
        r = client.cancel_all()
        log(f'已撤销 {len(r)} 个旧挂单')
    except Exception as e:
        log(f'⚠ 撤销旧单失败: {e}')
    time.sleep(1)

    # 2. 读取现有持仓
    bal = client.get_balance()
    usdt = bal.get('USDT', 0)
    doge = bal.get('DOGE', 0)
    price = client.get_price()
    log(f'重建网格: DOGE ${price:.4f}, USDT {usdt:.2f}, DOGE {doge:.2f}')
    log(f'新区间: ${lower} ~ ${upper}, {count}格')

    levels = grid_levels(lower, upper, count)
    below = [l for l in levels if l < price]
    above = [l for l in levels if l > price]
    log(f'  下方买单格: {[f"{l:.4f}" for l in below]}')
    log(f'  上方卖单格: {[f"{l:.4f}" for l in above]}')

    # 3. 用USDT挂下方买单（均分）
    if below and usdt > 0:
        per_u = usdt / len(below)
        for l in below:
            qty = int(per_u / l)
            if qty >= 1:
                try:
                    client.place_limit('BUY', qty, l)
                    log(f'  ✅ BUY {qty}DOGE @${l:.4f}')
                    time.sleep(0.3)
                except Exception as e:
                    log(f'  ⚠ BUY失败 @${l:.4f}: {e}')
    else:
        log('  （无下方买单格或USDT不足）')

    # 4. 用DOGE挂上方卖单（均分）
    if above and doge > 0:
        per_d = int(doge / len(above))
        for l in above:
            if per_d >= 1:
                try:
                    client.place_limit('SELL', per_d, l)
                    log(f'  ✅ SELL {per_d}DOGE @${l:.4f}')
                    time.sleep(0.3)
                except Exception as e:
                    log(f'  ⚠ SELL失败 @${l:.4f}: {e}')
    else:
        log('  （无上方卖单格或DOGE不足）')

    # 5. 更新基准成交ID
    try:
        trades = client.my_trades(limit=1)
        if trades:
            state = load_state()
            state['last_trade_id'] = max(t['id'] for t in trades)
            save_state(state)
            log(f'  已更新基准成交ID: {state["last_trade_id"]}')
    except Exception as e:
        log(f'  ⚠ 更新基准ID失败: {e}')

    log('网格重建完成')


def main():
    client = BinanceClient()
    cfg = {}

    if '--init' in sys.argv:
        do_init(client, cfg)
    elif '--regrid' in sys.argv:
        do_regrid(client, cfg)
    elif '--run' in sys.argv:
        do_run(client, cfg)
    elif '--status' in sys.argv:
        do_status(client, cfg)
    elif '--cancel' in sys.argv:
        do_cancel(client, cfg)
    else:
        print(__doc__)
        print('用法示例:')
        print('  python grid_bot_live.py --dry --init   # 试运行初始化')
        print('  python grid_bot_live.py --init        # 真实建网格')
        print('  python grid_bot_live.py --dry --run   # 试运行维护')
        print('  python grid_bot_live.py --status      # 查看状态')
        print('  python grid_bot_live.py --cancel      # 撤所有挂单')


if __name__ == '__main__':
    main()