#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
同花顺快速交易助手

简化版 - 更易用的交互界面

作者: Hermes
日期: 2026/5/28
"""

import pyautogui
import time
import winsound
from datetime import datetime
import os

# 安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

class QuickTHS:
    """同花顺快速交易"""
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        print('=' * 70)
        print('同花顺快速交易助手')
        print('=' * 70)
        print(f'屏幕: {self.screen_width}x{self.screen_height}')
        print('⚠️ 紧急停止: 鼠标移到左上角')
        print()
    
    def send_keys(self, keys):
        """发送按键"""
        pyautogui.hotkey(*keys) if isinstance(keys, (list, tuple)) else pyautogui.press(keys)
        time.sleep(0.5)
    
    def type_text(self, text):
        """输入文本"""
        pyautogui.write(text)
        time.sleep(0.3)
    
    def view_stock(self, code):
        """查看股票"""
        print(f'\n查看: {code}')
        self.type_text(code)
        self.send_keys('enter')
    
    def buy(self, code, price, quantity):
        """买入"""
        print(f'\n买入: {code} @ {price}元 x {quantity}股')
        winsound.Beep(1000, 300)
        
        # F1 - 买入
        self.send_keys('f1')
        time.sleep(1)
        
        # 输入代码
        self.type_text(code)
        time.sleep(0.5)
        
        # Tab到价格
        self.send_keys('tab')
        self.type_text(str(price))
        time.sleep(0.3)
        
        # Tab到数量
        self.send_keys('tab')
        self.type_text(str(quantity))
        time.sleep(0.3)
        
        print('✓ 信息已填写，请检查后点击"买入"按钮')
    
    def sell(self, code, price, quantity):
        """卖出"""
        print(f'\n卖出: {code} @ {price}元 x {quantity}股')
        winsound.Beep(1000, 300)
        
        # F2 - 卖出
        self.send_keys('f2')
        time.sleep(1)
        
        # 输入代码
        self.type_text(code)
        time.sleep(0.5)
        
        # Tab到价格
        self.send_keys('tab')
        self.type_text(str(price))
        time.sleep(0.3)
        
        # Tab到数量
        self.send_keys('tab')
        self.type_text(str(quantity))
        time.sleep(0.3)
        
        print('✓ 信息已填写，请检查后点击"卖出"按钮')
    
    def positions(self):
        """查看持仓"""
        print('\n打开持仓...')
        self.send_keys('f4')
    
    def account(self):
        """查看账户"""
        print('\n打开账户...')
        self.send_keys('f5')
    
    def cancel_orders(self):
        """撤单"""
        print('\n撤单...')
        self.send_keys(['ctrl', 'z'])


def main():
    """主菜单"""
    ths = QuickTHS()
    
    while True:
        print('\n' + '=' * 70)
        print('操作菜单')
        print('=' * 70)
        print('1. 查看股票')
        print('2. 买入')
        print('3. 卖出')
        print('4. 查看持仓')
        print('5. 查看账户')
        print('6. 撤单')
        print('7. 帮助')
        print('0. 退出')
        print()
        
        choice = input('请选择 (0-7): ').strip()
        
        if choice == '0':
            print('\n再见！')
            break
        
        elif choice == '1':
            code = input('股票代码: ').strip()
            if len(code) == 6 and code.isdigit():
                ths.view_stock(code)
            else:
                print('代码格式错误')
        
        elif choice == '2':
            code = input('股票代码: ').strip()
            price = input('买入价格: ').strip()
            quantity = input('买入数量(100整数倍): ').strip()
            
            try:
                code = code.zfill(6)  # 补齐6位
                price = float(price)
                quantity = int(quantity)
                
                if quantity % 100 != 0:
                    print('数量必须是100的整数倍')
                else:
                    ths.buy(code, price, quantity)
            except:
                print('输入错误')
        
        elif choice == '3':
            code = input('股票代码: ').strip()
            price = input('卖出价格: ').strip()
            quantity = input('卖出数量: ').strip()
            
            try:
                code = code.zfill(6)
                price = float(price)
                quantity = int(quantity)
                ths.sell(code, price, quantity)
            except:
                print('输入错误')
        
        elif choice == '4':
            ths.positions()
        
        elif choice == '5':
            ths.account()
        
        elif choice == '6':
            ths.cancel_orders()
        
        elif choice == '7':
            print('\n' + '=' * 70)
            print('使用帮助')
            print('=' * 70)
            print('''
快捷键:
  F1 - 买入
  F2 - 卖出
  F4 - 持仓
  F5 - 账户
  Ctrl+Z - 撤单

操作流程:
  1. 确保同花顺已启动并登录
  2. 选择功能菜单
  3. 按提示输入信息
  4. 检查后手动确认

安全提示:
  - 鼠标移到左上角紧急停止
  - 建议先测试再实盘
  - 注意检查价格数量
''')
        
        else:
            print('无效选择')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n已退出')
