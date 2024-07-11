import pygetwindow as gw
import pyautogui
import time
from pynput import keyboard
import threading
import cv2
import numpy as np

paused = False
running = True
lock = threading.Lock()

# Определяем диапазон цветов желтых монеток
YELLOW_MIN = (200, 200, 0)
YELLOW_MAX = (255, 255, 100)

# Глобальные переменные для отслеживания найденных монет и их координат
last_coin_position = None
same_position_count = 0
MAX_SAME_POSITION_COUNT = 5

# Глобальная переменная для хранения названия окна
window_name = None

# Переменные для хранения последних координат до повторяющихся монет
last_cursor_position_before_repeat = None

# Загрузка шаблона изображения
template_path = r"C:\dropimage\1banka.png"  # Укажите путь к вашему изображению
template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
w, h = template.shape[::-1]


def find_template_on_screen(window_rect):
    scrn = pyautogui.screenshot(region=window_rect)
    scrn = cv2.cvtColor(np.array(scrn), cv2.COLOR_RGB2GRAY)
    res = cv2.matchTemplate(scrn, template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)
    for pt in zip(*loc[::-1]):
        return pt[0] + window_rect[0], pt[1] + window_rect[1]
    return None


def move_to_initial_position(window_rect):
    initial_position = find_template_on_screen(window_rect)
    if initial_position:
        pyautogui.moveTo(initial_position)
        pyautogui.click()
        return True
    else:
        print("Шаблон не найден!")
        return False


def find_and_move_jar_to_yellow_coins(window_rect):
    global running, last_coin_position, same_position_count, last_cursor_position_before_repeat

    jar_x = window_rect[0] + window_rect[2] // 2
    jar_y = window_rect[1] + window_rect[3] - 311

    while running:
        with lock:
            if paused:
                continue

        scrn = pyautogui.screenshot(region=window_rect)
        width, height = scrn.size

        coins = []
        target_y_start = height - 536
        target_y_end = height - 320
        for x in range(0, width, 5):
            for y in range(target_y_start, target_y_end, 5):
                r, g, b = scrn.getpixel((x, y))
                if (
                    YELLOW_MIN[0] <= r <= YELLOW_MAX[0]
                    and YELLOW_MIN[1] <= g <= YELLOW_MAX[1]
                    and YELLOW_MIN[2] <= b <= YELLOW_MAX[2]
                ):
                    coins.append((window_rect[0] + x, window_rect[1] + y))

        if coins:
            closest_coin = min(coins, key=lambda c: abs(c[0] - jar_x))
            print(f"Найдена монетка на координате: {closest_coin}")

            if closest_coin == last_coin_position:
                same_position_count += 1
                if same_position_count > MAX_SAME_POSITION_COUNT:
                    print(
                        "Монеты на одних и тех же координатах более 5 раз. Выполняется одинарный клик."
                    )
                    pyautogui.click(closest_coin[0], closest_coin[1])
                    time.sleep(1)  # Дополнительная задержка после клика
                    last_coin_position = (
                        None  # Сброс координат монеты для повторного поиска шаблона
                    )
                    continue  # Продолжаем цикл поиска монет

            move_jar((jar_x, jar_y), closest_coin, window_rect)

            same_position_count = 0
            last_coin_position = closest_coin

        time.sleep(0.02)

    pyautogui.mouseUp()
    print("Левая кнопка мыши отпущена")


def move_jar(jar_position, coin_position, window_rect):
    jar_x, jar_y = jar_position
    coin_x, coin_y = coin_position

    left_bound = window_rect[0] + 58
    right_bound = window_rect[0] + window_rect[2] - 58

    if coin_x < left_bound:
        coin_x = left_bound
    elif coin_x > right_bound:
        coin_x = right_bound

    pyautogui.mouseDown()
    pyautogui.moveTo(coin_x, jar_y, duration=0.02)
    time.sleep(0.02)
    pyautogui.mouseUp()


def restart_main(window_rect, last_position):
    global running, paused
    with lock:
        running = False
        paused = False
    time.sleep(1)
    running = True
    if last_position:
        pyautogui.moveTo(last_position[0], last_position[1])
    start_main(window_rect)


def on_press(key):
    global paused, running
    try:
        if key.char == "q":
            with lock:
                paused = not paused
                if paused:
                    print("[✅] | Пауза.")
                else:
                    print("[✅] | Продолжение работы.")
    except AttributeError:
        pass

    if key == keyboard.Key.esc:
        with lock:
            running = False
        pyautogui.mouseUp()
        return False


def start_main(window_rect):
    global running

    jar_x = window_rect[0] + window_rect[2] // 2
    jar_y = window_rect[1] + window_rect[3] - 293
    pyautogui.moveTo(jar_x, jar_y)
    pyautogui.click()
    time.sleep(0.3)

    thread = threading.Thread(
        target=find_and_move_jar_to_yellow_coins, args=(window_rect,)
    )
    thread.daemon = True
    thread.start()

    thread.join()

    print("[✅] | Основная часть кода завершена.")


def main():
    global window_name

    if window_name is None:
        window_name = input("Введите название окна (1 - TelegramDesktop): ")
        if window_name == "1":
            window_name = "TelegramDesktop"

    check = gw.getWindowsWithTitle(window_name)
    if not check:
        print(f"[❌] | Окно - {window_name} не найдено!")
        window_name = None
        return
    else:
        print(
            f"[✅] | Окно найдено - {window_name}\n[✅] | Нажмите 'q' для паузы, 'Esc' для завершения."
        )

    telegram_window = check[0]

    start_main(
        (
            telegram_window.left,
            telegram_window.top,
            telegram_window.width,
            telegram_window.height,
        )
    )


if __name__ == "__main__":
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    main()

    listener.stop()
