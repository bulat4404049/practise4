import sys
import re
import argparse
import yaml
from pathlib import Path

# --- Лексический анализ ---
class Token:
    def __init__(self, type_, value, lineno, col):
        self.type = type_
        self.value = value
        self.lineno = lineno
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)}, {self.lineno}, {self.col})"

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.lineno = 1
        self.col = 1
        self.tokens = []
        self.keywords = {
            'def': 'DEF',
            'let': 'LET'
        }
        self.patterns = [
            ('NUMBER', r'\d*\.\d+'),
            ('DEF', r'def'),
            ('LET', r'let'),
            ('LPAREN', r'\('),
            ('RPAREN', r'\)'),
            ('LBRACE', r'\{'),
            ('RBRACE', r'\}'),
            ('COMMA', r','),
            ('SEMICOLON', r';'),
            ('DOLLAR', r'\$'),
            ('ID', r'[_a-z]+'),
            ('WHITESPACE', r'\s+'),
        ]
        self.regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.patterns)

    def tokenize(self):
        for mo in re.finditer(self.regex, self.text, re.MULTILINE):
            kind = mo.lastgroup
            value = mo.group()
            col = mo.start() - self.text.rfind('\n', 0, mo.start()) - 1
            if kind == 'WHITESPACE':
                if '\n' in value:
                    self.lineno += value.count('\n')
                    self.col = 1
                else:
                    self.col += len(value)
                continue
            elif kind == 'ID' and value in self.keywords:
                kind = self.keywords[value]
            token = Token(kind, value, self.lineno, col)
            self.tokens.append(token)
            self.col += len(value)
        return self.tokens

# --- Синтаксический анализ ---
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.constants = {}

    def current_token(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def eat(self, token_type):
        token = self.current_token()
        if token and token.type == token_type:
            self.pos += 1
            return token
        else:
            expected = token_type
            found = token.type if token else 'EOF'
            raise SyntaxError(f"Expected {expected}, found {found} at line {token.lineno}, col {token.col}")

    def parse(self):
        result = {}
        while self.current_token():
            if self.current_token().type == 'DEF':
                self.parse_constant()
            else:
                key, value = self.parse_pair()
                result[key] = value
        return result

    def parse_constant(self):
        self.eat('DEF')
        name = self.eat('ID').value
        value_token = self.current_token()
        if value_token.type == 'NUMBER':
            value = float(value_token.value)
            self.eat('NUMBER')
        else:
            value = self.parse_value()
        self.constants[name] = value
        self.eat('SEMICOLON')

    def parse_pair(self):
        key = self.eat('ID').value
        value = self.parse_value()
        if self.current_token() and self.current_token().type == 'COMMA':
            self.eat('COMMA')
        return key, value

    def parse_value(self):
        token = self.current_token()
        if token.type == 'DOLLAR':
            return self.parse_const_eval()
        elif token.type == 'LBRACE':
            return self.parse_dict()
        elif token.type == 'NUMBER':
            self.eat('NUMBER')
            return float(token.value)
        else:
            raise SyntaxError(f"Unexpected token {token.type} at line {token.lineno}")

    def parse_const_eval(self):
        self.eat('DOLLAR')
        self.eat('LPAREN')
        name = self.eat('ID').value
        self.eat('RPAREN')
        if name not in self.constants:
            raise NameError(f"Constant {name} not defined")
        return self.constants[name]

    def parse_dict(self):
        self.eat('LBRACE')
        dict_val = {}
        while self.current_token() and self.current_token().type != 'RBRACE':
            key, value = self.parse_pair()
            dict_val[key] = value
        self.eat('RBRACE')
        return dict_val

# --- Основная программа ---
def convert_to_yaml(data):
    return yaml.dump(data, default_flow_style=False, allow_unicode=True)

def main():
    parser = argparse.ArgumentParser(description='Конфигурационный язык в YAML транслятор (вариант 26)')
    parser.add_argument('-i', '--input', required=True, help='Путь к входному файлу')
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл {args.input} не найден")
        sys.exit(1)

    # Лексический анализ
    lexer = Lexer(text)
    try:
        tokens = lexer.tokenize()
    except Exception as e:
        print(f"Лексическая ошибка: {e}")
        sys.exit(1)

    # Синтаксический анализ
    parser = Parser(tokens)
    try:
        parsed_data = parser.parse()
    except (SyntaxError, NameError) as e:
        print(f"Синтаксическая ошибка: {e}")
        sys.exit(1)

    # Преобразование в YAML и вывод
    yaml_output = convert_to_yaml(parsed_data)
    print(yaml_output)

if __name__ == '__main__':
    main()