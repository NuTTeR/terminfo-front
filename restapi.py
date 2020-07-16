# -*- coding: utf-8 -*-

# Связь с основным сервером
import requests
import sys

class WorkerMan:
    def __init__(self, card_num, surname, name, patronymic, tabnum, workname):
        self.card_num = card_num # Номер карты
        self.surname = surname # Фамилия
        self.name = name # Имя
        self.patronymic = patronymic # Отчество
        self.tabnum = tabnum
        self.workname = workname

    def get_fullname(self):
        return f"{self.surname} {self.name} {self.patronymic}".strip()

class TermApi:
    URL = "http://127.0.0.1/api" # !!! АДРЕС ВНЕШНЕГО API
    CONNECT_TIMEOUT = 10

    def __init__(self, login, password):
        self.token = None # token для доступа на сервер (выдается после авторизации)
        self.user = None # Пользователь (экземпляр класса worker)
        self.session = None # Сессия обращения к api
        self.last_status = None # Последний статус запроса
        self.function_list = [] # Список доступных функций
        self._connection_init(login, password)

    def __del__(self):
        self.session.close()

    def _connection_init(self, login, password): # Начальное соединение с сервером
        self.last_status = None
        self.session = requests.session()
        self.session.auth = (login, password)
        try:
            r = self.session.get(self.URL + "/user", timeout=self.CONNECT_TIMEOUT)
            self.token = r.json().get("access_token", None)
            self.session = requests.session()
        except Exception:
            raise RuntimeError("Проблема соединения с сервером\nПопробуйте позднее")

    def get_worker(self, card_num): # Получение пользователя
        self.last_status = None
        if not self.token or not self.session:
            raise RuntimeError("Системная ошибка\nПопробуйте еще раз")

        # проверка карточки
        head = {'Authorization': f'token {self.token}', 'Connection':'close'}
        prm = {"cardnum": card_num}
        status = None
        error_msg = None
        try:
            print(head)
            print(prm)
            r = self.session.get(self.URL + "/worker",
                                 headers=head,
                                 params=prm,
                                 timeout=self.CONNECT_TIMEOUT * 3) # Первичный запрос пользователя может затянуться
            print(r.text)
            self.last_status = status = r.json().get("status", None)
            if status != 'error':
                error_msg = r.json().get("errors", None)
                if not error_msg: # TODO временно, пока не будет единого поля для ошибок
                    error_msg = r.json().get("dest", None)
        except:
            pass
        if not status:
            raise RuntimeError("Проблема соединения с сервером\nПопробуйте позднее")
        if status.lower() != 'success':
            if not error_msg:
                error_msg = "Проблема коммуникации с сервером\nПопробуйте позднее"
            raise RuntimeError(error_msg)
        self.user = WorkerMan(
            card_num=card_num,
            surname=r.json().get("F", ""),
            name=r.json().get("N", ""),
            patronymic=r.json().get("O", ""),
            tabnum=r.json().get("tabnum", 0),
            workname=r.json().get("workname", ""),
        )
        self.function_list = r.json().get("fs", [])

    def func_z_page(self, code=None, dt=None): # Запрос расчетного листка (z_page)
        self.last_status = None
        if not self.token or not self.session:
            raise RuntimeError("Системная ошибка\nПопробуйте еще раз")

        head = {'Authorization': f'token {self.token}'}
        prm = {"cardnum": self.user.card_num, "name": "Z_PAGE"}
        request_send = False
        if code and dt:
            prm['code'] = code
            monthyear = f'{"{:02.0f}".format(dt.month)}{dt.year}'
            prm['monthyear'] = monthyear
            request_send = True
        status = None
        error_msg = None
        try:
            print(head)
            print(prm)
            if not request_send:
                r = self.session.get(self.URL + "/func", headers=head, params=prm, timeout=self.CONNECT_TIMEOUT)
            else:
                r = self.session.post(self.URL + "/func", headers=head, params=prm, timeout=self.CONNECT_TIMEOUT)
            print(r.text)
            self.last_status = status = r.json().get("status", None)
            if status != 'error':
                error_msg = r.json().get("errors", None)
        except:
            pass
        if not status:
            raise RuntimeError("Проблема соединения с сервером\nПопробуйте позднее")
        if status.lower() != 'success':
            if not error_msg:
                error_msg = "Проблема коммуникации с сервером\nПопробуйте позднее"
            raise RuntimeError(error_msg)
        if not request_send:
            return # Инициировали запрос отправки смс с кодом, возвращать нечего
        return r.json().get("data", None)

    def func_2ndfl_order(self, dt=None): # Запрос 2ндфл (2ndfl_order)
        self.last_status = None
        if not self.token or not self.session:
            raise RuntimeError("Системная ошибка\nПопробуйте еще раз")

        head = {'Authorization': f'token {self.token}'}
        prm = {"cardnum": self.user.card_num, "name": "2NDFL_ORDER"}
        request_send = False
        if dt:
            year = f'{dt.year}'
            prm['year'] = year
            request_send = True
        status = None
        error_msg = None
        try:
            print(head)
            print(prm)
            if not request_send:
                r = self.session.get(self.URL + "/func", headers=head, params=prm, timeout=self.CONNECT_TIMEOUT)
            else:
                r = self.session.post(self.URL + "/func", headers=head, params=prm, timeout=self.CONNECT_TIMEOUT)
            print(r.text)
            self.last_status = status = r.json().get("status", None)
            if status != 'error':
                error_msg = r.json().get("errors", None)
        except:
            pass
        if not status:
            raise RuntimeError("Проблема соединения с сервером\nПопробуйте позднее")
        if status.lower() != 'success':
            if not error_msg:
                error_msg = "Проблема коммуникации с сервером\nПопробуйте позднее"
            raise RuntimeError(error_msg)
        if not request_send:
            return r.json().get("pas", None) # При начальном запросе нам возвращается номер паспорта
        return r.json().get("data", None)