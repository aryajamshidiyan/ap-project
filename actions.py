from database import Database
from models import User, Account
from utils import print_msg_box


class Signal:
    INITIAL = 0
    OK = 1
    RERUN = 2


class ActionEnum:
    REGISTER = 1
    LOGIN = 2
    OPEN_ACCOUNT = 3
    SHOW_ACCOUNT = 4
    MANAGE_ACCOUNT = 5
    TRANSFER = 7
    LOGOUT = 11


class ActionHandler:
    def __init__(self, user, db_connection):
        self.user = user
        self.db_connection = db_connection

    def __update_user(self, user):
        self.user = user

    @staticmethod
    def get_actions():
        return [
            Register(),
            Login(),
            OpenAccount(),
            ShowAccount(),
            ManageAccount(),
            Transfer(),
            Logout()
        ]

    def action_list(self):
        return {
            action.action: action for action in self.get_actions() if action.user_required == (self.user is not None)
        }

    def run(self, action):
        action.print_title()
        action.set_db(self.db_connection)
        action.set_user(self.user)
        signal = Signal.INITIAL
        while signal != Signal.OK:
            signal = action.run()
        if action.reload_user:
            self.user = action.user


class Action:
    def __init__(self, action: int, title: str, description: str, user_required: bool = True):
        self.action = action
        self.title = title
        self.description = description
        self.user_required = user_required
        self.user = None
        self.reload_user = False
        self.db = None

    def set_user(self, user):
        self.user = user

    def print_title(self):
        print_msg_box(self.title, indent=10)

    def set_db(self, db: Database):
        self.db = db

    def run(self):
        raise NotImplementedError


class Register(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.REGISTER,
            title='Register',
            description='Register',
            user_required=False
        )

    def run(self):
        user = User(self.db)
        user.prompt_national_number()
        exists = user.fetch_by_national_number()
        if exists:
            print('User Already exists!')
            return Signal.RERUN
        user.prompt_phone_number()
        user.prompt_password()
        user.prompt_name()
        user.prompt_email()
        user.write_user()
        print('Successfully registered.')
        return Signal.OK


class Login(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.LOGIN,
            title='Login',
            description='Login',
            user_required=False
        )

    def run(self):
        user = User(self.db)
        user.prompt_national_number(validate=False)
        user.prompt_password(validate=False)
        login_status = user.login_user()
        if login_status:
            print('Login successful')
            self.user = user
            self.reload_user = True
            return Signal.OK
        print('Username or password incorrect.')
        return Signal.RERUN


class OpenAccount(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.OPEN_ACCOUNT,
            title='Open an account',
            description='Open an account',
            user_required=True
        )

    def run(self):
        account = Account(self.user)
        account.prompt_alias()
        exists = account.fetch_by_alias()
        if exists:
            print('Alias Already exists!')
            return Signal.RERUN
        account.prompt_password()
        account.prompt_amount()

        account.open_account()
        print('Account opened successfully.')
        return Signal.OK


class ShowAccount(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.SHOW_ACCOUNT,
            title='Show an account',
            description='Show an account',
            user_required=True
        )

    def run(self):
        account = Account(self.user)
        account.show_account_list()
        account.show_account_details()
        return Signal.OK


class ManageAccount(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.MANAGE_ACCOUNT,
            title='Manage an account',
            description='Manage an account',
            user_required=True
        )

    def run(self):
        account = Account(self.user)
        account.show_account_list()
        selected_account = account.show_account_details()
        account.prompt_alias('Enter new alias: ')
        account.update_account(selected_account)
        print('Account updated successfully.')
        return Signal.OK


class Transfer(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.TRANSFER,
            title='Transfer money',
            description='Transfer money to other accounts',
            user_required=True
        )

    def run(self):
        account = Account(self.user)
        account.show_account_list()
        selected_account = account.prompt_account_alias('Enter your account alias: ')
        destination_account = account.prompt_account_number('Enter destination account number: ')
        if selected_account['id'] == destination_account['id']:
            print('Can not transfer to self account')
            return Signal.RERUN
        while True:
            amount = account.prompt_amount('Enter transfer amount: ')
            result = account.validate_amount(selected_account, amount)
            if not result:
                print('Can not enter more than balance!')
                continue
            break
        while True:
            password = account.prompt_password()
            if password != selected_account['password']:
                print('Password incorrect.')
                continue
            break
        account.transfer(selected_account, destination_account, amount)

        print('Transfer was successful.')

        return Signal.OK


class Logout(Action):
    def __init__(self):
        super().__init__(
            action=ActionEnum.LOGOUT,
            title='Logout',
            description='Logout'
        )

    def run(self):
        self.user = None
        self.reload_user = True
        print('Successfully logged out')
        return Signal.OK
