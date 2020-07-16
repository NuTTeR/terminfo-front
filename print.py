# -*- coding: utf-8 -*-

import six
import fitz
import tempfile
import os
from escpos import *
from PIL import Image, ImageQt


class PrintHandler: # Работа с печатью
    def __init__(self, pdf_data=None):
        self._data = None
        if pdf_data:
            self._data = fitz.open("pdf", pdf_data)
            if not self._data.isPDF:
                raise RuntimeError("Неверный файл")
        self._pix = None
        self._printer = None

    def get_image(self): # Получение изображения для работы из Qt
        if not self._pix:
            self._get_pix()
        img = Image.frombytes('RGB', [self._pix.width, self._pix.height], self._pix.samples)
        self._img = ImageQt.ImageQt(img) # Фикс падения pyqt из-за сборщика мусора
        return self._img

    def save_image(self, path=None): # Сохранение изображения на диск
        if not self._pix:
            self._get_pix()
        if not path:
            path = tempfile.gettempdir()
        filename = os.path.join(path, 'outfile_term.png')
        self._pix.writePNG(filename)
        return filename

    def print_message(self, msg, cut=True): # Печать текста (и отрыв чека, если нужно)
        if not self._printer:
            self._printer_init()
        self._printer.print_msg(msg)
        if cut:
            self._printer.print_finalize() # отрыв ленты

    def print_image(self): # Печать изображения и отрыв ленты
        if not self._pix:
            self._get_pix()
        if not self._printer:
            self._printer_init()
        img = Image.frombytes('RGB', [self._pix.width, self._pix.height], self._pix.samples)
        self._printer.print_image(img)
        self._printer.print_finalize() # печать и отрыв ленты

    def _get_pix(self): #Обработка изображения, внутренняя функция
        def is_white(color): # Определение белого пикселя, для внутренних ф-ций
            if color == [255, 255, 255]:
                return True
            return False

        def get_real_pix_size(pixmap): # Определение реального (печатемого) размера изображения
            dot_x_from = pixmap.width - 1
            dot_x_to = 0
            dot_y_from = pixmap.height - 1
            dot_y_to = 0

            # Для производительности. Если столько пикселей вниз (по оси y) - пустое пространство, дальше файл не считываем
            MAX_BLANK_Y_LIMIT = int(0.1 * pixmap.height)

            for y in range(pixmap.height):
                if y - dot_y_to > MAX_BLANK_Y_LIMIT:
                    break  # Для производительности
                for x in range(pixmap.width):
                    if not is_white(pixmap.pixel(x, y)):
                        if x < dot_x_from:
                            dot_x_from = x
                        if x > dot_x_to:
                            dot_x_to = x
                        if y < dot_y_from:
                            dot_y_from = y
                        if y > dot_y_to:
                            dot_y_to = y

            if not dot_x_to or not dot_y_to:
                return None
            return dot_x_from, dot_y_from, dot_x_to, dot_y_to

        def adapt_real_pix_size(pixmap, real_size, multiplier): # Уточнение размеров измображения после изменения размера
            GAP_INTERVAL = 5 # Расстояние в пикселях, +- от которого смотрим размеры

            real_size_mult = tuple(int(x * multiplier) for x in real_size)
            dot_x_from = pixmap.width - 1
            dot_x_to = 0
            dot_y_from = pixmap.height - 1
            dot_y_to = 0
            x_from = real_size_mult[0] - GAP_INTERVAL
            y_from = real_size_mult[1] - GAP_INTERVAL
            x_to = real_size_mult[2] + GAP_INTERVAL
            y_to = real_size_mult[3] + GAP_INTERVAL
            if x_from < 0:
                x_from = 0
            if y_from < 0:
                y_from = 0
            if x_to > pixmap.width - 1:
                x_to = pixmap.width - 1
            if y_to > pixmap.height - 1:
                y_to = pixmap.height - 1

            def check_dot(x, y, dot_x_from, dot_x_to, dot_y_from, dot_y_to):
                if x < dot_x_from:
                    dot_x_from = x
                if x > dot_x_to:
                    dot_x_to = x
                if y < dot_y_from:
                    dot_y_from = y
                if y > dot_y_to:
                    dot_y_to = y
                return dot_x_from, dot_x_to, dot_y_from, dot_y_to

            try:
                for y in range(y_from, real_size_mult[1] + GAP_INTERVAL):
                    for x in range(pixmap.width):
                        if not is_white(pixmap.pixel(x, y)):
                            dot_x_from, dot_x_to, dot_y_from, dot_y_to = check_dot(
                                x, y, dot_x_from, dot_x_to, dot_y_from, dot_y_to
                            )
                for y in range(real_size_mult[3] - GAP_INTERVAL, y_to):
                    for x in range(pixmap.width):
                        if not is_white(pixmap.pixel(x, y)):
                            dot_x_from, dot_x_to, dot_y_from, dot_y_to = check_dot(
                                x, y, dot_x_from, dot_x_to, dot_y_from, dot_y_to
                            )
                for y in range(pixmap.height):
                    for x in range(x_from, real_size_mult[0] + GAP_INTERVAL):
                        if not is_white(pixmap.pixel(x, y)):
                            dot_x_from, dot_x_to, dot_y_from, dot_y_to = check_dot(
                                x, y, dot_x_from, dot_x_to, dot_y_from, dot_y_to
                            )
                for y in range(pixmap.height):
                    for x in range(real_size_mult[2] - GAP_INTERVAL, x_to):
                        if not is_white(pixmap.pixel(x, y)):
                            dot_x_from, dot_x_to, dot_y_from, dot_y_to = check_dot(
                                x, y, dot_x_from, dot_x_to, dot_y_from, dot_y_to
                            )
                if not dot_x_to or not dot_y_to:
                    return None
            except Exception:
                return None
            return dot_x_from, dot_y_from, dot_x_to, dot_y_to

        if not self._data:
            raise RuntimeError('Не был передан pdf документ')
        page = self._data.loadPage(0)
        pix = page.getPixmap()
        # получаем реальную ширину в пикселях печатаемой информации
        real_size = get_real_pix_size(pix)
        if not real_size:
            raise RuntimeError('Неверный формат файла')
        real_width = real_size[2] - real_size[0]
        # Относительно необходимого нам размера получаем ширину, на которую нам нужно растянуть картинку, чтобы полуить текст без потери качества
        multiplier = (_Printer.MAX_WIDTH_SIZE - 1) / real_width  # Получаем коэфициент, на какой необходимо растянуть\сжать изображение, чтобы получить ширину принтера
        matrix = fitz.Matrix(multiplier, multiplier)
        # Запрашиваем еще раз картинку, но в нужном разрешении (с соотв. коэффициентами ширины и высоты, полученными ранее)
        pix = page.getPixmap(matrix=matrix)
        # Уточняем реальные размеры картинки, и уже ее сохраняем
        real_size = adapt_real_pix_size(pix, real_size, multiplier)
        #real_size = get_real_pix_size(pix)
        if not real_size:
            raise RuntimeError('Неверный формат файла')
        # Получаем только печатаемую область
        self._pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(real_size), False)
        self._pix.copyPixmap(pix, fitz.IRect(real_size))

    def _printer_init(self):
        self._printer = _Printer()

class _Printer():
    MAX_WIDTH_SIZE = 575 # Максимальная ширина ленты принтера ы пикселях
    _CONNECT_STRING = (0x0483, 0x7540, 0, 0x81, 0x03) # Параметры подключения escpos
    _CODEPAGE_CHANGE = constants.ESC + b'\x74'

    def __init__(self):
        self._printer = printer.Usb(
            self._CONNECT_STRING[0],
            self._CONNECT_STRING[1],
            self._CONNECT_STRING[2],
            self._CONNECT_STRING[3],
            self._CONNECT_STRING[4],
        )

    def print_image(self, img): # Добавление в буффер печати печать изображения (в формате PIL Python)
        self._printer.image(img)

    def print_msg(self, msg): # Печать сообщения
        self._printer._raw(self._CODEPAGE_CHANGE + six.int2byte(9))
        self._printer.codepage = 'cp866'
        #TODO добавить варианты шрифтов, например:
        # self._printer.set(font='a', height=1)
        # self._printer.set(font='b', height=2, align='left')
        # перед каждой сменой свойств шрифта необходимо напечатать то, что уже есть в буфере
        self._printer.text(msg)
        self.print()

    def print(self): # Печать текущего буфера печати (без отрезания строки, промежуточная печать)
        self._printer._raw(constants.ESC + b'd' + six.int2byte(2))

    def print_finalize(self): # Окончательная печать с отрезом бумаги
        self._printer.cut()