import pandas as pd
import pyperclip
import pyautogui
import time
import sys
from datetime import datetime
from pynput import keyboard
from pynput.keyboard import Key, Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController
import threading

pyautogui.FAILSAFE = True

keyboard_controller = KeyboardController()
mouse_controller = MouseController()

stop_event = threading.Event()
CSV_PATH = "table.csv"

def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

# ─── Клавиатурный слушатель ───────────────────────────────────────────────────

ctrl_pressed = False

def on_press(key):
    global ctrl_pressed
    if key in (Key.ctrl_l, Key.ctrl_r):
        ctrl_pressed = True
    if key == Key.esc:
        log("Нажат ESC — завершение программы...")
        stop_event.set()

def on_release(key):
    global ctrl_pressed
    if key in (Key.ctrl_l, Key.ctrl_r):
        ctrl_pressed = False

def check_failsafe():
    x, y = pyautogui.position()
    if x <= 5 and y <= 5:
        log("Аварийный стоп — мышь в верхнем левом углу!")
        stop_event.set()

# ─── Утилиты ──────────────────────────────────────────────────────────────────

def click(x, y):
    if stop_event.is_set():
        return
    check_failsafe()
    if stop_event.is_set():
        return
    mouse_controller.position = (x, y)
    time.sleep(0.05)
    mouse_controller.click(Button.left)
    log(f"ЛКМ → ({x}, {y})")

def copy_from_coords(x, y) -> str:
    if stop_event.is_set():
        return ""
    pyperclip.copy("")
    click(x, y)
    if stop_event.is_set():
        return ""
    time.sleep(0.2)
    keyboard_controller.press(Key.ctrl)
    keyboard_controller.press('c')
    keyboard_controller.release('c')
    keyboard_controller.release(Key.ctrl)
    time.sleep(0.3)
    value = pyperclip.paste().strip()
    log(f"  Скопировано из ({x}, {y}): '{value}'")
    return value

def paste_value(value: str):
    if stop_event.is_set():
        return
    pyperclip.copy(str(value))
    time.sleep(0.1)
    keyboard_controller.press(Key.ctrl)
    keyboard_controller.press('v')
    keyboard_controller.release('v')
    keyboard_controller.release(Key.ctrl)
    log(f"  Вставлено значение: '{value}'")

def wait(seconds: float):
    """Ожидание с проверкой stop_event и failsafe каждые 50мс."""
    steps = int(seconds / 0.05)
    for _ in range(steps):
        if stop_event.is_set():
            return
        check_failsafe()
        time.sleep(0.05)

# ─── Основная логика ──────────────────────────────────────────────────────────

def process_row(df, idx):
    if stop_event.is_set():
        return
    number = df.at[idx, 'number']
    log(f"═══ Обработка строки #{idx} | number = {number} ═══")

    click(200, 40);   wait(1.0)
    if stop_event.is_set(): return

    click(200, 115);  wait(1.5)
    if stop_event.is_set(): return

    click(150, 175)
    if stop_event.is_set(): return
    time.sleep(0.2)
    paste_value(number)
    if stop_event.is_set(): return
    time.sleep(0.2)

    click(325, 380);  wait(6.0)
    if stop_event.is_set(): return

    coords_columns = [
        (215, 305, 'depart_old'),
        (285, 305, 'arrive_old'),
        (900, 305, 'depart_new'),
        (970, 305, 'arrive_new'),
    ]

    for x, y, col in coords_columns:
        if stop_event.is_set(): return
        value = copy_from_coords(x, y)
        df.at[idx, col] = value

    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig', sep=';')
    log(f"  Таблица сохранена. Строка #{idx} заполнена.")

def main():
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    log("Программа запущена.")
    log("Остановка: ESC (из любого окна) или мышь в верхний левый угол")
    print("-" * 55)

    try:
        df = pd.read_csv(CSV_PATH, dtype=str, encoding='utf-8-sig', sep=';')
    except FileNotFoundError:
        log(f"Ошибка: файл '{CSV_PATH}' не найден рядом со скриптом.")
        sys.exit(1)

    df.fillna("", inplace=True)

    target_cols = ['depart_old', 'arrive_old', 'depart_new', 'arrive_new']

    for col in target_cols + ['number']:
        if col not in df.columns:
            log(f"Ошибка: в таблице нет столбца '{col}'.")
            sys.exit(1)

    rows_to_process = df[
        df[target_cols].apply(lambda row: all(v == "" for v in row), axis=1)
    ].index.tolist()

    if not rows_to_process:
        log("Все строки уже заполнены. Работа завершена.")
        sys.exit(0)

    log(f"Найдено строк для обработки: {len(rows_to_process)}")
    print("-" * 55)

    for idx in rows_to_process:
        if stop_event.is_set():
            break
        process_row(df, idx)

    if not stop_event.is_set():
        log("✓ Все строки обработаны. Программа завершена.")
    else:
        log("Программа остановлена пользователем.")
        sys.exit(0)

if __name__ == "__main__":
    main()