# -*- coding: utf-8 -*-
import os
import sys  # sys нужен для передачи argv в QApplication
import base64
import re
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from datetime import datetime, timedelta, date

from restapi import TermApi
from print import PrintHandler

# Term data
term_user = ''
term_password = ''

class MainWindow(QtWidgets.QMainWindow):

    #Стиль кнопок ввода информации (числовые и т.д.)
    BTN_INPUT_STYLE = """
        background-color: qlineargradient(spread:reflect, x1:0.5, y1:0.5, x2:0.5, y2:0, stop:0 rgba(214, 214, 214, 255), stop:1 rgba(238, 238, 238, 255));
        border-radius: 15px;
        padding: 10px;
    """
    #Первичный стиль для кнопок (выбор функций)
    BTN_PRIMARY_STYLE = """
        background-color: qlineargradient(spread:reflect, x1:0.5, y1:0.5, x2:0.5, y2:1, stop:0.3 rgba(0, 98, 255, 255), stop:1 rgba(0, 166, 255, 255));
        border-radius: 15px;
        color: rgb(255, 255, 255);
        padding: 10px;
    """
    #Вторичный стиль кнопок (Кнопки управления (выход, далее и т.д.))
    BTN_SECONDARY_STYLE = """
        background-color: qlineargradient(spread:reflect, x1:0.5, y1:0.5, x2:0.5, y2:1, stop:0.3 rgba(255, 95, 0, 255), stop:1 rgba(255, 165, 0, 255));
        border-radius: 15px;
        color: rgb(255, 255, 255);
        padding: 10px;
    """
    #Стиль кнопок отключенных (недоступных для выбора)
    BTN_DISABLED_STYLE = """
            color: rgb(155, 155, 155);
            border-radius: 15px;
            background-color: rgb(250, 250, 250);
            padding: 10px;
        """

    # Список доступных (реализованных) функций, которые пользователь может вызвать
    AVAIL_FUNCS = [
        'Z_PAGE',
        '2NDFL_ORDER',
    ]

    MONTH_NAMES = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    MONTH_NAMES_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    PIN_LENGTH = 4 # Длинна кода из смс
    GLOBAL_TIMEOUT = 60 # Кол-во секунд, после которых терминал выйдет на главный экран

    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi('uis/main.ui', self)

        # Настройка глобального таймера (выход на главный экран)
        self.installEventFilter(self)
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.timer_fired)

        self.buttons_init() # Работа с кнопками

        #Скрытие курсора
        if not os.getenv("DEBUG"):
            self.setCursor(QtCore.Qt.BlankCursor)

        # Настройка информационного окна
        self.info_window = MessageWindow(parent=self)
        self.info_window.setWindowOpacity(0.9)

        # Сброс терминала и подготовка к работе
        self.term_reset()

    def buttons_init(self): # Задание размеров и позиций кнопок при старте приложения
        # Обработка кнопки отмены
        self.cancelButton.clicked.connect(self.term_reset)
        sp_retain = self.cancelButton.sizePolicy()
        sp_retain.setRetainSizeWhenHidden(True)
        self.cancelButton.setSizePolicy(sp_retain)
        self.cancelButton.setStyleSheet(MainWindow.BTN_SECONDARY_STYLE)

        # Обработка кнопок на странице выбора месяца
        for mbtn in self.pageMonthSelect_month_buttons_get():
            mbtn.clicked.connect(self.pageMonthSelect_month_clicked)
        self.btn_year_prev.clicked.connect(self.pageMonthSelect_year_prev_clicked)
        self.btn_year_next.clicked.connect(self.pageMonthSelect_year_next_clicked)

        # Обработка кнопок на странице ввода кода
        for pbtn in self.pageCodeInput_digit_buttons_get():
            pbtn.clicked.connect(self.pageCodeInput_digit_clicked)
            pbtn.setStyleSheet(self.BTN_INPUT_STYLE)
        self.btn_pin_del.clicked.connect(self.pageCodeInput_del_clicked)
        self.btn_pin_del.setStyleSheet(self.BTN_INPUT_STYLE)

    def change_page(self, page_index): # Смена страницы в приложении
        #Скрытие кнопки выхода на главной странице
        if page_index == 0:
            print("Стартовый экран")
            self.cancelButton.setVisible(False)
            self.timer_stop() # Остановка таймера для главной страницы
        else:
            self.cancelButton.setVisible(True)
            self.timer_start() # Запуск таймера для всех остальных страниц
        # Очистка страницы пользовательских функций
        if page_index == 1:
            widget = self.body.findChild(QtWidgets.QWidget, "pageFuncs")
            if widget.layout():
                QtWidgets.QWidget().setLayout(widget.layout())
                QtCore.QObjectCleanupHandler().add(widget.layout())
        self.page_input_tmp = ''
        #Скрытие кнопки далее и восстановление начального вида
        self.btn_next.setVisible(False)
        self.btn_next.setText('Далее')
        try:
            self.btn_next.clicked.disconnect()
        except TypeError:
            pass
        self.body.setCurrentIndex(page_index)

    def term_reset(self): # Выход на главный экран терминала
        self.change_page(0)
        self.page_input_tmp = ''
        self.change_header_info()
        self.api_connect = None  # Сброс подключения к серверу
        self.selected_date = None  # Выбранная дата или год (на соотв. страницах)
        self.pageCodeInput_code_clear() # Сброс страницы ввода смс кода
        self.btn_next.setVisible(False)
        try:
            self.btn_next.clicked.disconnect()
        except TypeError:
            pass
        # Сброс страницы выбора месяца
        self.pageMonthSelect_info.setText('')  # Инфо страницы
        self.pageMonthSelect_change_year()  # Сброс года на начальный
        try:
            os.remove(self.bill_pic)
        except:
            pass
        self.bill_pic = None

    def set_current_user(self, user_num): # Проверка пользователя
        def card_format(ncard): # Преобразование из числа в формат карт marine
            try:
                ncard = int(ncard)
            except:
                return None
            if isinstance(ncard, int):
                if ncard == 1: # Пользователь для теста
                    return 1
                n1 = (ncard & 0xFF0000) >> 16
                n2 = ncard & 0xFFFF
                return "%03d,%05d" % (n1, n2)
            else:
                return None
        print(f"trying to change user: {user_num}")
        user_num_marine = card_format(user_num)
        if not user_num_marine:
            self.show_error("Не удалось прочитать карту\nпопробуйте еще раз")
            self.term_reset()
            return
        self.show_info("Пожалуйста, подождите", timeout=None)
        try:
            self.api_connect = TermApi(term_user, term_password)
            self.api_connect.get_worker(user_num_marine)
        except Exception as e:
            self.show_error(str(e))
            self.term_reset()
            return
        self.show_close()
        self.show_user_functions()

    def show_user_functions(self): # показ пользователю страницы с доступными функциями
        if not any(elem in self.AVAIL_FUNCS for elem in [d['NAME'] for d in self.api_connect.function_list]):
            self.show_info("Для Вас нет доступных действий")
            self.term_reset()
            return

        # Общая работа со страницей
        self.change_page(1)
        widget = self.body.findChild(QtWidgets.QWidget, "pageFuncs")
        # Чтобы кнопки на странице пользовательских функций не вылезали за пределы окна
        widget.setMaximumSize(widget.geometry().width(), widget.geometry().height())

        #Выставление информации о текущем пользователе в шапке
        #userinfo = f"{self.api_connect.user.get_fullname()} {self.api_connect.user.workname}"
        userinfo = f"{self.api_connect.user.get_fullname()}"
        self.change_header_info(userinfo)

        # Добавление кнопок с функциями для пользователя
        layout = QtWidgets.QHBoxLayout()
        btn_list = {}
        for single_func in self.api_connect.function_list:
            if not single_func['NAME'] in self.AVAIL_FUNCS:
                continue

            btn_list[single_func['NAME']] = QtWidgets.QPushButton(single_func['LABEL'], self)
            btn_list[single_func['NAME']].setSizePolicy(
                QtWidgets.QSizePolicy.Fixed,
                QtWidgets.QSizePolicy.Fixed
            )
            btn_list[single_func['NAME']].setFixedSize(420, 150)
            btn_list[single_func['NAME']].setFont(QtGui.QFont("Sergoe UI", 31))
            btn_list[single_func['NAME']].setStyleSheet(MainWindow.BTN_PRIMARY_STYLE)

            try:
                method = getattr(self, 'user_func_'+single_func['NAME'].lower())
            except AttributeError:
                btn_list[single_func['NAME']] = None
                continue
                # self.show_error("Ошибка реализации функции, обратитесь в службу ИТ")
                # self.term_reset()
                # return

            btn_list[single_func['NAME']].clicked.connect(method)

            layout.addWidget(btn_list[single_func['NAME']])
        widget.setLayout(layout)

    def user_func_z_page(self): # Выбор функции z_page (расчетный листок)
        self.user_func_z_page_stage_1()

    def user_func_z_page_stage_1(self): # Ввод даты для расчетного листка
        self.change_page(2)
        self.disable_button(self.btn_next)
        self.btn_next.clicked.connect(self.user_func_z_page_stage_2)

    def user_func_z_page_stage_2(self): # Ввод пинкода для расчетного листка
        self.show_info("Пожалуйста, подождите", timeout=None)
        # Запрос на сервер
        try:
            self.api_connect.func_z_page()
        except Exception as e:
            self.show_error(str(e))
            self.term_reset()
            return
        self.change_page(3)
        self.show_info("Вам отправлен код подтверждения операции на телефон")
        self.disable_button(self.btn_next)
        self.btn_next.clicked.connect(self.user_func_z_page_stage_3)

    def user_func_z_page_stage_3(self):  # Вывод результата для рассчетного листка
        self.show_info("Пожалуйста, подождите", timeout=None)
        # Запрос на сервер с полными данными
        try:
            result = self.api_connect.func_z_page(code=self.pageCodeInput_code.text(), dt=self.selected_date)
        except Exception as e:
            self.show_error(str(e))
            if self.api_connect.last_status == 'code failed next': # Разрешаем ввести еще раз код из смс
                self.pageCodeInput_code_clear()
                return
            self.term_reset()
            return
        if not result:
            self.show_error("Не получен ответ от сервера\nПопробуйте позднее")
            self.term_reset()
            return
        try:
            result = base64.b64decode(result)
            print_connect = PrintHandler(pdf_data=result)
        except:
            self.show_error("Получен неверный ответ от сервера\nПопробуйте позднее")
            self.term_reset()
            return

        # Сменим экран на "пожалуйста подождите" перед рендером картинки
        self.change_page(1)
        widget = self.body.findChild(QtWidgets.QWidget, "pageFuncs")
        layout = QtWidgets.QHBoxLayout()
        info_label = QtWidgets.QLabel(self)
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(info_label)
        widget.setLayout(layout)
        self.enable_button(self.btn_next, self.BTN_SECONDARY_STYLE)
        self.btn_next.clicked.connect(lambda: self.user_func_z_page_stage_4(print_connect))
        self.btn_next.setText('Печать')
        # Со всеми добавленными элементами на экран фиксируем размеры окна, чтобы не расползлись кнопки при длинном\широком изображении
        widget.setMaximumSize(widget.geometry().width(), widget.geometry().height())
        #Работа с картинкой
        self.bill_pic = print_connect.save_image()
        print_image = QtGui.QPixmap(self.bill_pic)
        print_image = print_image.scaled(widget.geometry().width(), widget.geometry().height() - 20,
                                         QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        info_label.setPixmap(print_image)
        self.show_close()

    def user_func_z_page_stage_4(self, print_connect): # Печать расчетного листка и выход
        try:
            print_connect.print_image()
        except Exception as e:
            self.show_error("Ошибка печати!\nПопробуйте позднее\n"+str(e))
            self.term_reset()
            return
        self.show_info("Услуга оказана\nСпасибо за визит!")
        self.term_reset()

    def user_func_2ndfl_order(self): # Выбор функции 2НДФЛ (2ndfl_order)
        self.user_func_2ndfl_order_stage_1()

    def user_func_2ndfl_order_stage_1(self): # Ввод года для запроса 2ндфл
        self.change_page(2)
        self.pageMonthSelect_change_year(year=None, monthselect=False)
        self.enable_button(self.btn_next, self.BTN_PRIMARY_STYLE)
        self.btn_next.clicked.connect(self.user_func_2ndfl_order_stage_2)

    def user_func_2ndfl_order_stage_2(self): # Запрос на сервер и проверка паспорта 2ндфл
        self.show_info("Пожалуйста, подождите", timeout=None)
        self.selected_date = date(int(self.label_myear.text()), 1, 1)
        # Запрос на сервер
        try:
            result = self.api_connect.func_2ndfl_order()
        except Exception as e:
            self.show_error(str(e))
            self.term_reset()
            return
        if not result:
            self.show_error("Не получен ответ от сервера\nПопробуйте позднее")
            self.term_reset()
            return

        # Показ паспорта с подтверждением
        self.change_page(1)
        widget = self.body.findChild(QtWidgets.QWidget, "pageFuncs")
        layout = QtWidgets.QHBoxLayout()
        info_label = QtWidgets.QLabel(self)
        info_label.setFont(QtGui.QFont("Sergoe UI", 36))
        info_label.setWordWrap(True)
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setText('Проверьте последние 6 цифр паспорта:\n' + result +
                           '\n\nЕсли номер не совпадает, обратитесь в отдел кадров')
        layout.addWidget(info_label)
        widget.setLayout(layout)
        self.enable_button(self.btn_next, self.BTN_PRIMARY_STYLE)
        self.btn_next.clicked.connect(self.user_func_2ndfl_order_stage_3)
        self.show_close()

    def user_func_2ndfl_order_stage_3(self):  # Вывод информации о приеме 2НДФЛ
        self.show_info("Пожалуйста, подождите", timeout=None)
        # Запрос на сервер с полными данными
        try:
            result = self.api_connect.func_2ndfl_order(dt=self.selected_date)
        except Exception as e:
            self.show_error(str(e))
            if self.api_connect.last_status == 'code failed next': # Разрешаем ввести еще раз код из смс
                self.pageCodeInput_code_clear()
                return
            self.term_reset()
            return
        if not result:
            self.show_error("Не получен ответ от сервера\nПопробуйте позднее")
            self.term_reset()
            return
        # Показ результата
        self.change_page(1)
        widget = self.body.findChild(QtWidgets.QWidget, "pageFuncs")
        layout = QtWidgets.QHBoxLayout()
        info_label = QtWidgets.QLabel(self)
        info_label.setFont(QtGui.QFont("Sergoe UI", 36))
        info_label.setWordWrap(True)
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setText(result)
        layout.addWidget(info_label)
        widget.setLayout(layout)
        self.show_close()

    def pageMonthSelect_change_year(self, year=None, monthselect=True): #Смена года на странице выбора месяца (основная процедура)
        self.pageMonthSelect_monthselect = monthselect # Запись параметра смены месяца
        self.pageMonthSelect_change_year_proxy(year)

    def pageMonthSelect_change_year_proxy(self, year=None):  # Смена года на странице выбора месяца
        prev_month_date = datetime.today().replace(day=1) - timedelta(days=1)  # Год предыдущего месяца от текущего
        maximum_year = prev_month_date.year
        maximum_month = 12
        if not year or year >= maximum_year:
            year = maximum_year
            maximum_month = prev_month_date.month
        # Обработка кнопок
        self.label_myear.setText(str(year))
        if year <= 2015: # TODO какое ограничение по году ставить?
            self.disable_button(self.btn_year_prev)
        else:
            self.enable_button(self.btn_year_prev)
        if year >= maximum_year:
            self.disable_button(self.btn_year_next)
        else:
            self.enable_button(self.btn_year_next)
        mbuttons = self.pageMonthSelect_month_buttons_get()
        if self.pageMonthSelect_monthselect:
            for mindex in range(0, maximum_month): # Обработка активных кнопок
                self.enable_button(mbuttons[mindex])
            for mindex in range(maximum_month, 12): # Обработка неактивных кнопок
                self.disable_button(mbuttons[mindex])
        else:
            for mindex in range(12):
                mbuttons[mindex].setVisible(False)

    def pageMonthSelect_month_clicked(self): # Выбор конкретного месяца на странице выбора месяца
        for idx, mname in enumerate(self.MONTH_NAMES):
            if 'btn_'+mname == self.sender().objectName():
                self.selected_date = date(int(self.label_myear.text()), idx + 1, 1)
                self.pageMonthSelect_info.setText(f"Выбран {self.MONTH_NAMES_RU[self.selected_date.month - 1]} {self.selected_date.year}")
                self.enable_button(self.btn_next, self.BTN_PRIMARY_STYLE) # Кнопка далее становится доступной
                return

    def pageMonthSelect_year_next_clicked(self): # Обработка нажатия на кнопку увеличения года на странице выбора месяца
        self.pageMonthSelect_change_year_proxy(int(self.label_myear.text()) + 1)

    def pageMonthSelect_year_prev_clicked(self): # Обработка нажатия на кнопку уменьшения года на странице выбора месяца
        self.pageMonthSelect_change_year_proxy(int(self.label_myear.text()) - 1)

    def pageMonthSelect_month_buttons_get(self): # Все кнопки месяцев в списке для странцы выбора месяца
        lst = []
        for mname in self.MONTH_NAMES:
            lst.append(eval('self.btn_'+mname))
        return lst

    def pageCodeInput_digit_clicked(self): # Добавление цифры для страницы ввода кода
        if len(self.pageCodeInput_code.text()) >= self.PIN_LENGTH:
            return
        self.pageCodeInput_code.setText(self.pageCodeInput_code.text() + self.sender().objectName()[-1:])
        if len(self.pageCodeInput_code.text()) == self.PIN_LENGTH:
            self.enable_button(self.btn_next, self.BTN_PRIMARY_STYLE)

    def pageCodeInput_del_clicked(self): # Удаление цифры для страницы ввода кода
        if len(self.pageCodeInput_code.text()) <= 0:
            return
        self.pageCodeInput_code.setText(self.pageCodeInput_code.text()[:-1])
        if len(self.pageCodeInput_code.text()) != self.PIN_LENGTH:
            self.disable_button(self.btn_next)

    def pageCodeInput_code_clear(self):  # Очистка поля ввода кода
        self.pageCodeInput_code.setText('')
        self.disable_button(self.btn_next)

    def pageCodeInput_digit_buttons_get(self): # Все цифровые кнопки для страницы ввода кода
        lst = []
        for i in range(10):
            lst.append(eval('self.btn_pin_' + str(i)))
        return lst

    def change_header_info(self, message=None): # Смена текста в глобальной шапке (обычно фио и должность)
        if message:
            message = re.sub(r'[^a-zA-Zа-яА-Я0-9-_/\\*.,#№:() ]', '', message) # Фильтрация нежелательных символов
            # TODO: ограничить длинну строки, отключить wordwrap поля
            self.headerInfo.setText(message)
        else:
            #self.headerInfo.hide()
            self.headerInfo.setText('')

    def disable_button(self, btn): # Отключение кнопки на форме
        btn.setVisible(True)
        btn.setEnabled(False)
        btn.setStyleSheet(self.BTN_DISABLED_STYLE)

    def enable_button(self, btn, style=BTN_INPUT_STYLE): # Включение кнопки на форме
        btn.setVisible(True)
        btn.setEnabled(True)
        btn.setStyleSheet(style)

    def show_message(self, message, style, timeout): # Отображение информационного сообщения с настраиваемым стилем сообщения
        self.info_window.data.setStyleSheet(style)
        self.info_window.data.setText(message)
        print(message)
        self.info_window.showFullScreen()
        QtGui.QGuiApplication.processEvents()
        if timeout:
            self.info_window.set_timeout(timeout)

    def show_error(self, message, timeout=5): # Отображение сообщения об ошибке
        style = """
            border-radius: 30px;
            border: 5px solid rgb(217, 0, 0);
            padding: 20px;
        """
        self.show_message(message, style, timeout)

    def show_info(self, message, timeout=5): # Отображение информационного сообщения
        style = """
            border-radius: 30px;
            border: 5px solid rgb(0, 85, 255);
            padding: 20px;
        """
        self.show_message(message, style, timeout)

    def show_close(self): # Закрытие информационного сообщения (если оно было открыто без таймаута)
        self.info_window.close()

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Escape:
            self.term_reset()
        # Страница авторизации, получение номера пропуска пользователя
        if self.body.currentIndex() == 0:
            char = event.text()
            if key == QtCore.Qt.Key_Return or \
               key == QtCore.Qt.Key_Enter:
                self.set_current_user(self.page_input_tmp)
                self.page_input_tmp = ''
            else:
                self.page_input_tmp += char

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress or event.type() == QtCore.QEvent.UpdateRequest:
            self.timer_reset()
        return super(MainWindow, self).eventFilter(source, event)

    def timer_stop(self): # Остановка глобального таймаута на выход на главный экран
        self.timer.stop()

    def timer_start(self): # Запуск глобального таймера на выход на главный экран
        timeout = self.GLOBAL_TIMEOUT
        if self.body.currentIndex == 3:
            timeout = timeout * 2 # Для страницы ввода кода из смс увеличиваем таймаут в 2 раза
        self.timer.start(timeout * 1000)

    def timer_reset(self): # Сброс таймаута для глобального таймера выхода на главный экран
        if not self.timer.isActive():
            return
        self.timer_stop()
        self.timer_start()

    def timer_fired(self): # Ф-ция для случая, когда время таймера истекло
        self.show_info('Время сеанса истекло')
        self.term_reset()


class MessageWindow(QtWidgets.QMainWindow): # Класс информационного окна (попап)

    def __init__(self, parent):
        super(MessageWindow, self).__init__(parent=parent)
        uic.loadUi('uis/info.ui', self)
        self.setCursor(QtCore.Qt.BlankCursor) # Скрытие курсора

    def set_timeout(self, timeout):
        QtCore.QTimer.singleShot(timeout * 1000, self.close)

    def closeEvent(self, event):
        super(MessageWindow, self).closeEvent(event)
        # Для избавления от "мерцающих" старых сообщений - при закрытии окна очищаем его
        self.data.setStyleSheet("")
        self.data.setText("")
        QtGui.QGuiApplication.processEvents()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.showFullScreen()
    #window.show()
    app.exec_()


if __name__ == '__main__':
    main()
