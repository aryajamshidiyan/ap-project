import random
from datetime import datetime
from prettytable import PrettyTable
from database import Database
from utils import prompt, validate_phone_number, validate_national_number, validate_password, validate_positive_number, \
    table_footer, validate_email


class BaseModel:
    def __init__(self, db_connection: Database, table_name):
        self.db_connection = db_connection
        self.table_name = table_name

    def first_by(self, field, value):
        return self.first([[field, '==', value]])

    def first(self, where_list=None):
        where_str = ' and '.join([f'{w[0]} {w[1]} {w[2]}' for w in where_list])
        items = self.db_connection.run_query(f'select from {self.table_name} where {where_str};')
        if items:
            return items[0]
        return None

    def all(self, where_list=None):
        if where_list:
            where_str = ' where ' + ' and '.join([f'{w[0]} {w[1]} {w[2]}' for w in where_list])
        else:
            where_str = ''
        return self.db_connection.run_query(f'select from {self.table_name}{where_str};')

    def insert(self, field_values_pair):
        fields = field_values_pair.keys()
        values = [str(value) for value in field_values_pair.values()]
        return self.db_connection.run_query(
            f"insert into {self.table_name} ({','.join(fields)}) values ({','.join(values)});")


class User(BaseModel):
    def __init__(self, db_connection, national_number=None):
        super().__init__(db_connection, 'users')
        self.id = None
        self.national_number = national_number
        self.phone_number = None
        self.password = None
        self.name = None
        self.email = None

    def prompt_phone_number(self):
        self.phone_number = prompt(
            'Enter your phone number: ',
            validate_phone_number,
            'Invalid phone number.'
        )

    def prompt_national_number(self, validate=True):
        self.national_number = prompt(
            'Enter your national number: ',
            validate_national_number if validate else None,
            'Invalid national number.' if validate else None
        )

    def prompt_password(self, validate=True):
        self.password = prompt(
            'Enter your password: ',
            validate_password if validate else None,
            'Invalid password. Min 6 character required.' if validate else None
        )

    def prompt_email(self):
        self.email = prompt(
            'Enter your email: ',
            validate_email,
            'Invalid email.'
        )

    def fetch_by_national_number(self):
        if not self.national_number:
            return None
        return self.first_by('national_number', self.national_number)

    def prompt_name(self):
        self.name = prompt(
            'Enter your name: ',
            None,
            'Name required.'
        )

    def write_user(self):
        self.insert({
            'national_number': self.national_number,
            'phone_number': self.phone_number,
            'password': self.password,
            'name': self.name,
            'email': self.email
        })

    def fill_user(self, user):
        self.id = user['id']
        self.national_number = user['national_number']
        self.phone_number = user['phone_number']
        self.name = user['name']
        self.password = user['password']
        self.email = user['email']

    def login_user(self):
        user = self.fetch_by_national_number()
        if user and user['password'] == self.password:
            self.fill_user(user)
            return True
        return False


class Account(BaseModel):
    def __init__(self, user):
        super().__init__(user.db_connection, 'accounts')
        self.user = user
        self.amount = 0
        self.alias = None
        self.password = None

    def prompt_alias(self, message='Enter account alias: '):
        self.alias = prompt(
            message,
            None,
            'Alias required.'
        )

    def prompt_password(self, validate=True):
        self.password = prompt(
            'Enter account password: ',
            validate_password if validate else None,
            'Invalid password. Min 6 character required.' if validate else None
        )
        return self.password

    def prompt_amount(self, message='Enter account initial balance: '):
        self.amount = prompt(
            message,
            validate_positive_number,
            'Invalid amount.'
        )
        return self.amount

    def __generate_number(self):
        numbers = [item['number'] for item in self.all()]
        if not numbers:
            return 10000
        return str(int(max(numbers)) + random.randint(5, 9))

    def open_account(self):
        account = self.insert({
            'user_id': self.user.id,
            'amount': self.amount,
            'number': self.__generate_number(),
            'password': self.password,
            'alias': self.alias,
            'created_time': datetime.now().isoformat()
        })
        transaction = Transaction(self)
        transaction.new_transaction({
            'amount': self.amount,
            'description': 'Open account',
            'account_id': 0,
            'destination_id': account['id'],
            'created_time': datetime.now().isoformat()
        })

    def fetch_by_alias(self):
        if not self.alias:
            return None
        return self.first([
            ['user_id', '==', self.user.id],
            ['alias', '==', self.alias],
        ])

    def show_account_list(self):
        accounts = self.all([['user_id', '==', self.user.id]])
        accounts_table = PrettyTable(['alias', 'amount', 'number', 'created time'])
        accounts_table.add_rows([
            [account['alias'], account['amount'], account['number'], account['created_time']] for account in accounts
        ])
        print(accounts_table)

    def prompt_account_alias(self, message="Enter account alias to see details: "):
        while True:
            alias = prompt(message)
            account = self.first([
                ['user_id', '==', self.user.id],
                ['alias', '==', alias]
            ])
            if not account:
                print('Account not found!')
                continue
            break
        return account

    def prompt_account_number(self, message="Enter account number: "):
        while True:
            number = prompt(message, validate_positive_number, 'Invalid number')
            account = self.first([
                ['number', '==', number]
            ])
            if not account:
                print('Account not found!')
                continue
            break
        return account

    def show_account_details(self):
        account = self.prompt_account_alias()
        transaction = Transaction(self)
        transaction.show_list(account)
        return account

    @staticmethod
    def convert_to_values(account):
        return ','.join([str(item) for item in [account['id'], account['user_id'], account['amount'], account['number'],
                                                account['password'], account['alias'], account['created_time']]])

    def transfer(self, selected_account, destination_account, amount):
        selected_account['amount'] = str(int(selected_account['amount']) - int(amount))
        destination_account['amount'] = str(int(destination_account['amount']) + int(amount))
        selected_account_values = self.convert_to_values(selected_account)
        destination_account_values = self.convert_to_values(destination_account)
        self.db_connection.run_query(
            f"update {self.table_name} where id == {selected_account['id']} values ({selected_account_values});"
        )
        self.db_connection.run_query(
            f"update {self.table_name} where id == {destination_account['id']} values ({destination_account_values});"
        )
        transaction = Transaction(self)
        transaction.new_transaction({
            'amount': amount,
            'description': 'Transfer money',
            'account_id': selected_account['id'],
            'destination_id': destination_account['id'],
            'created_time': datetime.now().isoformat()
        })

    def update_account(self, selected_account):
        selected_account['alias'] = self.alias
        selected_account_values = self.convert_to_values(selected_account)
        self.db_connection.run_query(
            f"update {self.table_name} where id == {selected_account['id']} values ({selected_account_values});"
        )

    @staticmethod
    def validate_amount(selected_account, amount):
        if int(amount) > int(selected_account['amount']):
            return False
        return True


class Transaction(BaseModel):
    def __init__(self, account):
        super().__init__(account.db_connection, 'transactions')
        self.account = account
        self.destination = None
        self.amount = 0
        self.type = None

    def new_transaction(self, data):
        self.insert(data)

    def show_list(self, account):
        account_id = account['id']
        transactions = self.db_connection.run_query(
            f'select from {self.table_name} where account_id == {account_id} or destination_id == {account_id};'
        )
        transactions_table = PrettyTable(['row', 'amount', 'description', 'created time'])
        for row, transaction in enumerate(transactions, 1):
            amount = ('+' if transaction['destination_id'] == account_id else '-') + str(transaction['amount'])
            transactions_table.add_row([row, amount, transaction['description'], transaction['created_time']])

        print(transactions_table)
        print(table_footer(transactions_table, 'Sum', {'amount': account['amount']}))
