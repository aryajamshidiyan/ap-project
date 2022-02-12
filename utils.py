import re


def print_msg_box(msg, indent=1, width=None, title=None):
    """Print message-box with optional title."""
    lines = msg.split('\n')
    space = " " * indent
    if not width:
        width = max(map(len, lines))
    box = f'╔{"═" * (width + indent * 2)}╗\n'  # upper_border
    if title:
        box += f'║{space}{title:<{width}}{space}║\n'  # title
        box += f'║{space}{"-" * len(title):<{width}}{space}║\n'  # underscore
    box += ''.join([f'║{space}{line:<{width}}{space}║\n' for line in lines])
    box += f'╚{"═" * (width + indent * 2)}╝'  # lower_border
    print(box)


def prompt(input_message, validation_method=None, invalid_message=''):
    while True:
        input_value = input(input_message)
        if validation_method:
            validated_value = validation_method(input_value)
        else:
            validated_value = input_value
        if not validated_value:
            print(invalid_message)
            continue
        return validated_value


def validate_phone_number(phone_number):
    if match := re.search('^(?:[+|0{2}]?98)?0?(\d{10})$', phone_number):
        return match.group(1)
    return None


def validate_national_number(national_number):
    if not national_number.isdigit() or len(national_number) != 10:
        return False

    remaining = sum([int(national_number[i]) * (10 - i) for i in range(9)]) % 11
    check_number = int(national_number[-1])

    if remaining < 2:
        if check_number != remaining:
            return False
    elif check_number != 11 - remaining:
        return False
    return national_number


def validate_password(password):
    if len(password) < 6:
        return False
    return password


def validate_positive_number(num):
    if not num.isdigit() or int(num) <= 0:
        return False
    return num


def validate_email(email):
    if re.fullmatch('^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$', email):
        return email
    return False


def table_footer(tbl, text, dc):
    res = f"{tbl._vertical_char} {text}{' ' * (tbl._widths[0] - len(text))} {tbl._vertical_char}"

    for idx, item in enumerate(tbl.field_names):
        if idx == 0:
            continue
        if not item in dc.keys():
            res += f"{' ' * (tbl._widths[idx] + 1)} {tbl._vertical_char}"
        else:
            res += f"{' ' * (tbl._widths[idx] - len(str(dc[item])))} {dc[item]} {tbl._vertical_char}"

    res += f"\n{tbl._hrule}"
    return res


if __name__ == '__main__':
    phone_list = [
        '123',
        '9121234567',
        '09121234567',
        '+989121234567',
        '989121234567',
    ]
    for phone in phone_list:
        print(f"{phone} => {validate_phone_number(phone)}")

    national_number_list = [
        '123',
        '12345679a',
        '0100434304',  # valid
        '0100434304'  # invalid
    ]
    for number in national_number_list:
        print(f"{number} => {validate_national_number(number)}")

    email_list = [
        'a',
        'a.com',
        'abc@gmail',
        'abc@gmail.com'
    ]
    for email in email_list:
        print(f"{email} => {validate_email(email)}")