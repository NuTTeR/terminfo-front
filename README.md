# terminfo-front

ПО информационного терминала (клиентская часть)

## Условия<br>
Debian с окружением XFCE<br>
Пакет qt5-default <br>
Python 3.7 и пакеты из requirements.txt <br>

## Инструкция по настройке<br>
* Подразумеваем, что программа (данный репозитарий) скопирована в /var/terminfo
и пользователь, под которым будет запущена программа называется "term"
* Необходимо отключить в системе все уведомления, потухание экрана, заставки и прочее.

* Автовход пользователя: в _/etc/lightdm/lightdm.conf_ раскомментировать строки _autologin-user=_ и _autologin-user-timeout=0_, 
в параметре _autologin-user_ указать _term_ (_autologin-user=term_)

* Для отключения сохранения сессии выполнить в терминале: <br>
`rm -rf "$HOME/.cache/sessions"` <br> 
`touch "$HOME/.cache/sessions"`

* Для возможности запуска не из под root: положить файл _install/99-escpos.rules_ в _/etc/udev/rules.d/99-escpos.rules_
<br><br>
**Дальнейшие действия делать только после проверки SSH доступа на терминал для возможности отмены изменений!**

* Отключение значков и панелей рабочего стола:
ПКМ на рабочем столе - Настройка рабочего стола - Значки - Тип значков - Нет значков. 
В файле _/etc/xdg/xfce4/xfconf/xfce-perchannel-xml/xfce4-session.xml_ комментируем или удаляем строку с xfce4-panel 

* Автозапуск приложения: Положить файл _install/start_terminfo.desktop_ в _/home/term/.config/autostart/_ 
и выполнить в терминале <br>
`chmod +x "$HOME/.config/autostart/start_terminfo.desktop"` <br> 
`chmod +x "/var/terminfo/start.sh"` <br>

## Примечание<br>
ПО сделано для конкретного термопринтера. В случае совпадения внутренних комманд принтера может зарабоать и принтер другой модели и производителя. 
Для этого в файле _print.py_ (переменная __CONNECT_STRING_) а так же в файле _install/99-escpos.rules_ меняется строка подключения 
(VID и PID термопринтера)
