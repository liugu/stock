#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺自动化交易系统

使用 PyAutoGUI + PyWinAuto 实现同花顺软件自动化

功能：
1. 自动启动同花顺
2. 获取实时行情数据（从屏幕）
3. 自动下单交易
4. 查看持仓和账户
5. 自动止盈止损

注意：
- 需要同花顺软件已安装并登录
- 交易前请确认已开通自动化交易权限
- 建议先在模拟账户测试

作者: Hermes
日期: 2026/5/28
"""

import pyautogui
import pywinauto
from pywinauto import Application, keyboard
import time
import os
import sys
import winsound
from datetime import datetime
import json

# 安全设置：防止失控
pyautogui.FAILSAFE = True  # 移动鼠标到左上角会停止
pyautogui.PAUSE = 0.5  # 每个动作间隔

# 配置
CONFIG = {
    'ths_exe_path': r'C:\同花顺\xiadan.exe',  # 同花顺下单程序路径
    'ths_main_path': r'C:\同花顺\同花顺.exe',  # 同花顺主程序路径
    'account': '',
    'password': '',
    'stop_loss_pct': -3.0,  # 止损比例
    'take_profit_pct': 10.0,  # 止盈比例
    'monitor_interval': 30,  # 监控间隔（秒）
}

class THSTrader:
    """同花顺自动化交易"""
    
    def __init__(self):
        """初始化"""
        self.app = None
        self.main_window = None
        self.trade_window = None
        self.connected = False
        
        print('=' * 80)
        print('同花顺自动化交易系统')
        print('=' * 80)
        print('\n⚠️ 重要提示:')
        print('1. 请确保同花顺软件已启动并登录')
        print('2. 请确保已开通自动化交易权限')
        print('3. 移动鼠标到屏幕左上角可紧急停止')
        print('4. 建议先使用模拟账户测试')
        print()
        
        # 检查屏幕尺寸
        self.screen_width, self.screen_height = pyautogui.size()
        print(f'屏幕尺寸: {self.screen_width} x {self.screen_height}')
        
    def connect_ths(self, exe_path=None):
        """
        连接同花顺
        
        参数:
            exe_path: 同花顺程序路径
        """
        exe_path = exe_path or CONFIG['ths_exe_path']
        
        print('\n尝试连接同花顺...')
        
        # 检查程序是否存在
        if not os.path.exists(exe_path):
            print(f'⚠️ 未找到同花顺程序: {exe_path}')
            print('请手动启动同花顺，然后使用 connect_existing() 连接')
            return False
        
        try:
            # 启动程序
            print(f'启动: {exe_path}')
            self.app = Application(backend='win32').start(exe_path)
            time.sleep(3)
            
            # 获取主窗口
            self.main_window = self.app.window(title='同花顺')
            self.main_window.wait('ready', timeout=10)
            
            self.connected = True
            print('✓ 已连接同花顺')
            return True
            
        except Exception as e:
            print(f'连接失败: {e}')
            return False
    
    def connect_existing(self):
        """连接已运行的同花顺"""
        print('\n搜索已运行的同花顺...')
        
        try:
            # 查找同花顺窗口
            self.app = Application(backend='win32').connect(title_re='.*同花顺.*')
            
            # 获取主窗口
            windows = self.app.windows()
            if windows:
                self.main_window = windows[0]
                self.connected = True
                print(f'✓ 已连接: {self.main_window.window_text()}')
                return True
            else:
                print('未找到同花顺窗口')
                return False
                
        except Exception as e:
            print(f'连接失败: {e}')
            print('请确保同花顺已启动')
            return False
    
    def bring_to_front(self):
        """将同花顺窗口置顶"""
        if self.main_window:
            try:
                self.main_window.set_focus()
                time.sleep(0.5)
                return True
            except:
                return False
        return False
    
    def send_keys(self, keys):
        """
        发送按键
        
        参数:
            keys: 按键字符串，如 'f1', 'enter', 'esc'
        """
        try:
            self.bring_to_front()
            keyboard.send_keys(keys)
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f'按键失败: {e}')
            return False
    
    def type_text(self, text):
        """
        输入文本
        
        参数:
            text: 要输入的文本
        """
        try:
            self.bring_to_front()
            pyautogui.typewrite(text, interval=0.05)
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f'输入失败: {e}')
            return False
    
    def input_stock_code(self, code):
        """
        输入股票代码
        
        参数:
            code: 6位股票代码
        """
        print(f'\n输入股票代码: {code}')
        self.bring_to_front()
        self.send_keys(code)
        time.sleep(1)
        self.send_keys('{ENTER}')
        time.sleep(0.5)
        
    def open_trade_window(self):
        """打开交易窗口"""
        print('\n打开交易窗口...')
        self.bring_to_front()
        
        # 同花顺快捷键：F1买入，F2卖出，或按Ctrl+T打开交易
        self.send_keys('{CTRL}{T}')
        time.sleep(2)
        
        # 或者点击交易按钮（需要知道按钮位置）
        print('如果快捷键无效，请手动点击交易按钮')
        
    def buy_stock(self, code, price, quantity):
        """
        买入股票
        
        参数:
            code: 股票代码
            price: 买入价格
            quantity: 买入数量（股）
        """
        print(f'\n买入股票: {code}')
        print(f'  价格: {price}元')
        print(f'  数量: {quantity}股')
        
        # 警告音提醒
        winsound.Beep(1000, 500)
        
        # 步骤：
        # 1. 打开买入界面（F1）
        self.bring_to_front()
        self.send_keys('{F1}')
        time.sleep(1)
        
        # 2. 输入股票代码
        self.type_text(code)
        time.sleep(0.5)
        
        # 3. 输入价格（Tab切换到价格框）
        self.send_keys('{TAB}')
        self.type_text(str(price))
        time.sleep(0.5)
        
        # 4. 输入数量（Tab切换到数量框）
        self.send_keys('{TAB}')
        self.type_text(str(quantity))
        time.sleep(0.5)
        
        # 5. 确认买入（Enter或点击买入按钮）
        print('\n⚠️ 请检查输入是否正确，然后手动点击"买入"按钮')
        print('或按 Enter 继续（自动模式）')
        
        # 不自动确认，让用户手动确认更安全
        # self.send_keys('{ENTER}')
        
    def sell_stock(self, code, price, quantity):
        """
        卖出股票
        
        参数:
            code: 股票代码
            price: 卖出价格
            quantity: 卖出数量（股）
        """
        print(f'\n卖出股票: {code}')
        print(f'  价格: {price}元')
        print(f'  数量: {quantity}股')
        
        # 警告音提醒
        winsound.Beep(1000, 500)
        
        # 步骤：
        # 1. 打开卖出界面（F2）
        self.bring_to_front()
        self.send_keys('{F2}')
        time.sleep(1)
        
        # 2. 输入股票代码
        self.type_text(code)
        time.sleep(0.5)
        
        # 3. 输入价格
        self.send_keys('{TAB}')
        self.type_text(str(price))
        time.sleep(0.5)
        
        # 4. 输入数量
        self.send_keys('{TAB}')
        self.type_text(str(quantity))
        time.sleep(0.5)
        
        # 5. 等待确认
        print('\n⚠️ 请检查输入是否正确，然后手动点击"卖出"按钮')
        
    def view_positions(self):
        """查看持仓"""
        print('\n查看持仓...')
        self.bring_to_front()
        
        # 快捷键：F4或点击持仓页面
        self.send_keys('{F4}')
        time.sleep(2)
        
        print('持仓页面已打开，请查看屏幕')
        
    def view_account(self):
        """查看账户资金"""
        print('\n查看账户...')
        self.bring_to_front()
        
        # 快捷键：F5或点击资金页面
        self.send_keys('{F5}')
        time.sleep(2)
        
        print('资金页面已打开，请查看屏幕')
        
    def quick_switch_stock(self, code):
        """
        快速切换查看股票
        
        参数:
            code: 股票代码
        """
        self.bring_to_front()
        self.type_text(code)
        time.sleep(0.5)
        self.send_keys('{ENTER}')
        
    def screenshot(self, save_path=None):
        """
        截取当前屏幕
        
        参数:
            save_path: 保存路径
        
        返回:
            截图文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if not save_path:
            save_path = f'E:/量化研究/workspace/stock/screenshots/ths_{timestamp}.png'
        
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 截取全屏
        img = pyautogui.screenshot()
        img.save(save_path)
        
        print(f'截图保存: {save_path}')
        return save_path
    
    def get_mouse_position(self):
        """获取鼠标当前位置"""
        x, y = pyautogui.position()
        print(f'鼠标位置: ({x}, {y})')
        return x, y
    
    def click_at(self, x, y, clicks=1):
        """
        点击指定位置
        
        参数:
            x, y: 坐标
            clicks: 点击次数
        """
        pyautogui.click(x, y, clicks=clicks)
        time.sleep(0.3)
    
    def record_positions(self):
        """
        记录持仓数据（从屏幕截图）
        
        需要用户先打开持仓页面
        """
        print('\n记录持仓数据...')
        print('请确保持仓页面已打开')
        
        # 截图
        screenshot_path = self.screenshot()
        
        # 这里可以结合OCR提取数据
        print(f'截图已保存: {screenshot_path}')
        print('请手动查看截图中的持仓数据')
        
        return screenshot_path
    
    def automated_trade_cycle(self, stocks_info):
        """
        自动化交易循环
        
        参数:
            stocks_info: 股票信息列表，格式：
                [{'code': '603533', 'action': 'buy', 'price': 25.85, 'quantity': 100}]
        """
        print('\n开始自动化交易循环...')
        print('=' * 80)
        
        for stock in stocks_info:
            action = stock.get('action', 'buy')
            code = stock.get('code')
            price = stock.get('price')
            quantity = stock.get('quantity', 100)
            
            print(f'\n处理: {code} - {action}')
            
            if action == 'buy':
                self.buy_stock(code, price, quantity)
            elif action == 'sell':
                self.sell_stock(code, price, quantity)
            
            # 等待用户确认
            input('按 Enter 继续下一笔交易，或 Ctrl+C 停止...')
        
        print('\n交易循环完成')


class THSMonitor:
    """同花顺实时监控"""
    
    def __init__(self, trader):
        """初始化"""
        self.trader = trader
        self.positions = {}  # 持仓信息
        self.running = False
    
    def add_position(self, code, name, cost_price, shares):
        """添加持仓"""
        self.positions[code] = {
            'name': name,
            'cost_price': cost_price,
            'shares': shares,
            'current_price': cost_price,
            'stop_loss': cost_price * (1 + CONFIG['stop_loss_pct'] / 100),
            'take_profit': cost_price * (1 + CONFIG['take_profit_pct'] / 100),
        }
        print(f'添加持仓: {name}({code}), 成本{cost_price}元, {shares}股')
    
    def monitor_loop(self, duration=300):
        """
        监控循环
        
        参数:
            duration: 监控时长（秒）
        """
        print('\n' + '=' * 80)
        print(f'开始监控持仓 (时长: {duration}秒)')
        print('=' * 80)
        
        self.running = True
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < duration:
                print('\n' + '-' * 40)
                print(f'监控时间: {datetime.now().strftime("%H:%M:%S")}')
                
                # 遍历持仓
                for code, pos in self.positions.items():
                    print(f'\n{pos["name"]}({code}):')
                    print(f'  成本: {pos["cost_price"]}元')
                    print(f'  止损线: {pos["stop_loss"]:.2f}元 ({CONFIG["stop_loss_pct"]}%)')
                    print(f'  止盈线: {pos["take_profit"]:.2f}元 ({CONFIG["take_profit_pct"]}%)')
                    
                    # 查看股票
                    self.trader.quick_switch_stock(code)
                    time.sleep(1)
                    
                    # 这里可以截图并分析
                    # 实际价格需要从屏幕获取或手动输入
                    
                    # 提示用户输入当前价格（测试模式）
                    try:
                        price_input = input(f'输入当前价格（回车跳过）: ')
                        if price_input:
                            current_price = float(price_input)
                            pos['current_price'] = current_price
                            
                            profit_pct = (current_price - pos['cost_price']) / pos['cost_price'] * 100
                            print(f'  当前: {current_price}元, 盈亏: {profit_pct:+.2f}%')
                            
                            # 检查止盈止损
                            if current_price <= pos['stop_loss']:
                                print('⚠️ 触发止损！')
                                winsound.Beep(2000, 1000)
                                # 自动卖出
                                self.trader.sell_stock(code, current_price, pos['shares'])
                            
                            elif current_price >= pos['take_profit']:
                                print('✓ 触发止盈！')
                                winsound.Beep(1500, 500)
                                # 自动卖出
                                self.trader.sell_stock(code, current_price, pos['shares'])
                    except:
                        pass
                
                # 等待下一次检查
                remaining = int(duration - (time.time() - start_time))
                print(f'\n剩余监控时间: {remaining}秒')
                print(f'下次检查: {CONFIG["monitor_interval"]}秒后')
                time.sleep(CONFIG['monitor_interval'])
                
        except KeyboardInterrupt:
            print('\n监控已停止')
            self.running = False
    
    def stop(self):
        """停止监控"""
        self.running = False


def demo_ths():
    """同花顺演示"""
    print('\n' + '=' * 80)
    print('同花顺自动化交易演示')
    print('=' * 80)
    
    trader = THSTrader()
    
    # 尝试连接已运行的同花顺
    if trader.connect_existing():
        print('\n✓ 同花顺已连接')
    else:
        print('\n⚠️ 未连接同花顺，演示模式运行')
    
    print('\n功能演示:')
    print('1. 输入股票代码查看行情')
    print('2. 截图保存')
    print('3. 查看持仓')
    print('4. 查看账户')
    print('5. 买入演示')
    print('6. 卖出演示')
    print('7. 实时监控演示')
    print('0. 退出')
    
    while True:
        choice = input('\n请选择 (0-7): ').strip()
        
        if choice == '0':
            print('再见！')
            break
        
        elif choice == '1':
            code = input('输入股票代码: ').strip()
            trader.input_stock_code(code)
        
        elif choice == '2':
            trader.screenshot()
        
        elif choice == '3':
            trader.view_positions()
        
        elif choice == '4':
            trader.view_account()
        
        elif choice == '5':
            code = input('股票代码: ').strip()
            price = input('买入价格: ').strip()
            quantity = input('买入数量: ').strip()
            trader.buy_stock(code, float(price), int(quantity))
        
        elif choice == '6':
            code = input('股票代码: ').strip()
            price = input('卖出价格: ').strip()
            quantity = input('卖出数量: ').strip()
            trader.sell_stock(code, float(price), int(quantity))
        
        elif choice == '7':
            monitor = THSMonitor(trader)
            
            # 添加测试持仓
            monitor.add_position('603533', '掌阅科技', 25.85, 3800)
            monitor.add_position('600863', '华能蒙电', 6.71, 14900)
            
            duration = input('监控时长(秒，默认300): ').strip()
            duration = int(duration) if duration else 300
            
            monitor.monitor_loop(duration)


def main():
    """主函数"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        trader = THSTrader()
        trader.connect_existing()
        
        if command == 'code':
            # 查看股票
            code = sys.argv[2] if len(sys.argv) > 2 else '603533'
            trader.input_stock_code(code)
        
        elif command == 'buy':
            # 买入
            if len(sys.argv) < 5:
                print('用法: python ths_trading.py buy <code> <price> <quantity>')
                return
            code = sys.argv[2]
            price = float(sys.argv[3])
            quantity = int(sys.argv[4])
            trader.buy_stock(code, price, quantity)
        
        elif command == 'sell':
            # 卖出
            if len(sys.argv) < 5:
                print('用法: python ths_trading.py sell <code> <price> <quantity>')
                return
            code = sys.argv[2]
            price = float(sys.argv[3])
            quantity = int(sys.argv[4])
            trader.sell_stock(code, price, quantity)
        
        elif command == 'positions':
            # 查看持仓
            trader.view_positions()
        
        elif command == 'account':
            # 查看账户
            trader.view_account()
        
        elif command == 'screenshot':
            # 截图
            trader.screenshot()
        
        else:
            print('用法:')
            print('  python ths_trading.py code <股票代码>')
            print('  python ths_trading.py buy <代码> <价格> <数量>')
            print('  python ths_trading.py sell <代码> <价格> <数量>')
            print('  python ths_trading.py positions')
            print('  python ths_trading.py account')
            print('  python ths_trading.py screenshot')
    else:
        # 演示模式
        demo_ths()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n已退出')
    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()