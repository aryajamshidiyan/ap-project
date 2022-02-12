import os
import csv
import re


def parse_condition(table, condition_str):
    def evaluate_simple_condition(data, condition):
        if match := re.search('\s*(\w*)\s*(==|!=)\s*\"?(([^\"]+))\"?', condition):
            field = match.group(1)
            operand = match.group(2)
            value = match.group(3).strip()
            if operand not in ['==', '!=']:
                raise RuntimeError(f'Operand not supported: {operand}')
            try:
                value = table.fields[field].parse(value)
                if operand == '==':
                    return [item for item in data if item[field] == value]
                else:
                    return [item for item in data if item[field] != value]
            except KeyError:
                raise RuntimeError(f'Table {table.name} does not have field {field}')
        else:
            raise RuntimeError(f'Error after {condition}')

    def evaluate_operator(data1, data2, operand):
        if operand == 'OR':
            return list({v['id']: v for v in data1 + data2}.values())
        else:
            return [item for item in data1 if item in data2]

    current_data = table.data.values()
    if condition_str:
        conditions = re.split('\s+and|or\s+', condition_str, re.IGNORECASE)
        data_items = [evaluate_simple_condition(current_data, condition) for condition in conditions]
        operators = ['and'] + re.findall('\s+(and|or)\s+', condition_str, re.IGNORECASE)
        while data_items:
            data_item = data_items.pop(0)
            operator = operators.pop(0).upper()
            current_data = evaluate_operator(current_data, data_item, operator)

    return current_data


class Database:
    def __init__(self, schema_file='schema.txt', storage_path='db'):
        self.schema = {}
        self.storage_path = storage_path
        self.read_schema(schema_file)
        print(f"Database initialized successfully.")

    def read_schema(self, schema_file: str):
        table = None
        fields = []
        mode = 'r'
        if not os.path.exists(schema_file):
            mode = 'w+'
        with open(schema_file, mode) as f:
            for line in f:
                line = line.lower().strip()
                if not line:
                    self.add_table(table, fields)
                    table = None
                    fields = []
                elif match := re.search('^(.\w*)$', line):
                    table = match.group(1)
                elif match := re.search('^(.\w*)(.*)$', line):
                    field_name = match.group(1)
                    field_type = match.group(2)
                    fields.append(Field(field_name, field_type))

        if table is not None:
            self.add_table(table, fields)

    def add_table(self, table, fields):
        if not fields:
            raise RuntimeError(f"Table {table} should have at least one field")
        table_path = os.path.join(self.storage_path, f'{table}.db')
        table = Table(table_path, fields)
        if table.name in self.schema:
            raise RuntimeError(f"Table {table.name} already exists.")
        self.schema[table.name] = table

    def run_query(self, query: str):
        query = query.strip()
        if match := re.search('^select from (\w*)(?: where )?(.*);$', query, re.IGNORECASE):
            table_name = match.group(1)
            condition = match.group(2).strip()
            return self.__select(table_name, condition)
        elif match := re.search('^insert into (\w*) \s*\((([^\)]+))\)\s*values\s*\((([^\)]+))\);$', query,
                                re.IGNORECASE):
            table_name = match.group(1)
            columns = [item.strip() for item in match.group(2).strip().split(',')]
            values = [item.strip() for item in match.group(4).strip().split(',')]
            return self.__insert(table_name, values, columns)
        elif match := re.search('^insert into (\w*) values\s*\((([^\)]+))\);$', query,
                                re.IGNORECASE):
            table_name = match.group(1)
            values = [item.strip() for item in match.group(2).strip().split(',')]
            return self.__insert(table_name, values)
        elif match := re.search('^update (\w*) \s*(?:where)\s*(.*);$', query, re.IGNORECASE):
            table_name = match.group(1)
            condition, values = match.group(2).strip().split(' values ')
            values = [item.strip() for item in values.replace(')', '').replace('(', '').split(',')]
            return self.__update(table_name, condition, values)
        elif match := re.search('^delete from (\w*)(?: where )?(.*);$', query, re.IGNORECASE):
            table_name = match.group(1)
            condition = match.group(2).strip()
            self.__delete(table_name, condition)
        else:
            raise RuntimeError(f"Invalid query `{query}`")

    def get_table(self, table_name):
        try:
            return self.schema[table_name]
        except KeyError:
            raise RuntimeError(f'Table {table_name} does not exists.')

    def __select(self, table_name, condition):
        table = self.get_table(table_name)
        data = parse_condition(table, condition)
        return data

    def __insert(self, table_name, values, columns=[]):
        table = self.get_table(table_name)
        if not columns:
            columns = table.fields.keys()
        if len(columns) != len(values):
            raise RuntimeError(f'Inserted {len(values)} values in {len(columns)} columns.')

        return table.insert(columns, values)

    def __update(self, table_name, condition, values):
        table = self.get_table(table_name)
        data = self.__select(table_name, condition)
        columns = table.fields.keys()
        if len(columns) != len(values):
            raise RuntimeError(f'Updated {len(values)} values in {len(columns)} columns.')

        table.update(data, values)
        return len(data)

    def __delete(self, table_name, condition):
        table = self.get_table(table_name)
        data = self.__select(table_name, condition)
        data_ids = [item[table.id_key] for item in data]
        table.data = {id: item for id, item in table.data.items() if id not in data_ids}
        table.write_data()


class Table:
    def __init__(self, path, fields):
        self.path = path
        self.name = os.path.split(path)[-1].split('.')[0]
        self.fields = {}
        self.id_key = 'id'
        self.set_fields(fields)
        self.data = {}
        self.read_data()
        print(f"Reading {self.name}({list(self.fields.keys())}), {len(self.data)} records")

    def read_data(self):
        def recreate_db():
            current_path = ''
            for path in os.path.split(self.path)[:-1]:
                current_path = os.path.join(current_path, path)
                if not os.path.exists(current_path):
                    os.mkdir(current_path)

            writer = csv.writer(open(self.path, 'w+'))
            writer.writerow(self.fields.keys())

        if not os.path.exists(self.path):
            recreate_db()
        else:
            with open(self.path, 'r') as f:
                data = csv.DictReader(f)
                if set(data.fieldnames) != self.fields.keys():
                    recreate_db()
                for no, item in enumerate(data):
                    item_id = int(item[self.id_key])
                    if item_id in self.data:
                        raise RuntimeError(f"Duplicate id {item_id} in {self.name}")
                    for key, field in self.fields.items():
                        item[key] = field.parse(item[key])
                    self.data[item_id] = item

    def write_data(self):
        with open(self.path, 'w+', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(self.fields.keys()))
            writer.writeheader()
            for item in self.data.values():
                writer.writerow(item)

    def set_fields(self, fields):
        id_count = 0
        for field in fields:
            if field.type == DataType.ID:
                id_count += 1
                self.id_key = field.name
        if id_count == 0:
            raise RuntimeError(f"At least one id column should exists")
        if id_count > 1:
            raise RuntimeError(f"Only one id column should exists")
        self.fields = {field.name: field for field in fields}

    def insert(self, columns, values):
        data = {column: None for column in columns}
        values = {column: value for column, value in zip(columns, values)}
        for field_name, field in self.fields.items():
            if field_name not in columns:
                if field_name == self.id_key:
                    try:
                        data[field_name] = int(max([item[self.id_key] for item in self.data.values()])) + 1
                    except:
                        data[field_name] = 1
                else:
                    raise ValueError(f"Table {self.name} field {field_name} is not filled.")
            else:
                field_value = field.parse(values[field_name])
                if field.is_unique:
                    exists = [item for item in self.data.values() if item[field_name] == field_value]
                    if exists:
                        raise RuntimeError(f'field `{field_name}` duplicate value ({values[field_name]})')
                data[field_name] = field_value

        self.data[data[self.id_key]] = data
        self.write_data()
        return data

    def update(self, data, values):
        data_ids = [item[self.id_key] for item in data]
        values = {column: value for column, value in zip(self.fields.keys(), values)}
        for data_idx, data_item in self.data.items():
            if data_idx not in data_ids:
                continue
            for field_name, field in self.fields.items():
                field_value = field.parse(values[field_name])
                if field.is_unique:
                    exists = [item for item in self.data.values() if item[field_name] == field_value and
                              data_item[self.id_key] != item[self.id_key]]
                    if exists:
                        raise RuntimeError(f'field `{field_name}` duplicate value ({values[field_name]})')
                self.data[data_idx][field_name] = field_value

        self.write_data()


class DataType:
    ID = 'id'
    CHAR = 'char'
    INT = 'integer'
    BOOL = 'boolean'
    TIMESTAMP = 'timestamp'


class Field:
    def __init__(self, name, type):
        self.name = name
        self.type = None
        self.length = 256
        self.is_unique = False
        self.set_type(type)

    def set_type(self, type):
        is_unique = False
        type = type.strip()
        if 'unique' in type:
            is_unique = True
            type = type.replace('unique', '')
        if match := re.search('^\s*char\((.*)\)$', type):
            type = DataType.CHAR
            length = match.group(1)
        else:
            length = self.length

        if type not in [DataType.ID, DataType.CHAR, DataType.INT, DataType.BOOL, DataType.TIMESTAMP]:
            raise RuntimeError(f"{type} is an invalid type")
        self.type = type
        self.length = length
        self.is_unique = is_unique
        if type == DataType.ID:
            self.is_unique = True

    def parse(self, value):
        if self.type == DataType.ID:
            return int(value)
        if self.type == DataType.CHAR:
            return value.strip('"')
        elif self.type == DataType.INT:
            return int(value)
        elif self.type == DataType.BOOL:
            return bool(value)
        elif self.type == DataType.TIMESTAMP:
            return value.strip('"')
