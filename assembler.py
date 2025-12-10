#!/usr/bin/env python3
"""
Ассемблер для Учебной Виртуальной Машины (УВМ) - вариант 14
Этап 1: Перевод программы в промежуточное представление
"""

import argparse
import csv
import sys
import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union
from enum import Enum


class CommandType(Enum):
    """Типы команд УВМ"""
    LOAD_CONST = 231      # Загрузка константы
    READ_MEM = 61         # Чтение из памяти
    WRITE_MEM = 125       # Запись в память
    BIN_OP = 145          # Бинарная операция (циклический сдвиг вправо)


@dataclass
class Command:
    """Базовая команда УВМ"""
    opcode: int
    name: str
    fields: Dict[str, int]
    
    def __str__(self) -> str:
        """Строковое представление команды"""
        fields_str = ", ".join(f"{k}={v}" for k, v in self.fields.items())
        return f"{self.name}({fields_str})"
    
    def to_bytes(self) -> bytes:
        """Преобразование команды в бинарное представление"""
        if self.opcode == CommandType.LOAD_CONST.value:
            # Формат: 1 байт opcode, 3 байта константа (little-endian)
            const = self.fields["const"]
            return struct.pack('<BI', self.opcode, const & 0x1FFFFF)
        
        elif self.opcode == CommandType.READ_MEM.value:
            # Формат: 1 байт opcode, 2 байта смещение (little-endian)
            offset = self.fields["offset"]
            return struct.pack('<BH', self.opcode, offset & 0x1FFF)
        
        elif self.opcode == CommandType.WRITE_MEM.value:
            # Формат: 1 байт opcode, 2 байта адрес (little-endian)
            address = self.fields["address"]
            return struct.pack('<BH', self.opcode, address & 0x1FFF)
        
        elif self.opcode == CommandType.BIN_OP.value:
            # Формат: 1 байт opcode
            return struct.pack('B', self.opcode)
        
        else:
            raise ValueError(f"Неизвестный опкод: {self.opcode}")


class Assembler:
    """Ассемблер УВМ"""
    
    # Словарь для быстрого поиска команд по мнемонике
    MNEMONICS = {
        "load": CommandType.LOAD_CONST.value,
        "read": CommandType.READ_MEM.value,
        "write": CommandType.WRITE_MEM.value,
        "rotr": CommandType.BIN_OP.value,  # rotate right - циклический сдвиг вправо
    }
    
    # Обратный словарь для отладки
    OPCODE_TO_NAME = {
        CommandType.LOAD_CONST.value: "load_const",
        CommandType.READ_MEM.value: "read_mem",
        CommandType.WRITE_MEM.value: "write_mem",
        CommandType.BIN_OP.value: "bin_op_rotr",
    }
    
    def __init__(self):
        self.commands: List[Command] = []
        self.errors: List[str] = []
    
    def parse_csv(self, csv_content: str) -> bool:
        self.commands.clear()
        self.errors.clear()
        
        try:
            lines = csv_content.strip().splitlines()
            
            for line_num, line in enumerate(lines, 1):
                # Убираем пробелы в начале и конце строки
                line = line.strip()
                
                # Пропускаем пустые строки
                if not line:
                    continue
                
                # Пропускаем комментарии (строки, начинающиеся с #)
                if line.startswith('#'):
                    continue
                
                # Разделяем строку по запятым
                row = [cell.strip() for cell in line.split(',')]
                
                # Пропускаем строки, которые стали пустыми после удаления пробелов
                if not row or not row[0]:
                    continue
                
                mnemonic = row[0].lower()
                
                if mnemonic not in self.MNEMONICS:
                    self.errors.append(f"Строка {line_num}: Неизвестная команда '{mnemonic}'")
                    continue
                
                opcode = self.MNEMONICS[mnemonic]
                
                try:
                    if opcode == CommandType.LOAD_CONST.value:
                        # Формат: load,<константа>
                        if len(row) < 2 or not row[1]:
                            raise ValueError("Не указана константа")
                        const = int(row[1].strip())
                        if const < 0 or const > 0x1FFFFF:  # 21 бит
                            raise ValueError(f"Константа {const} выходит за допустимый диапазон (0-{0x1FFFFF})")
                        cmd = Command(opcode, "load_const", {"const": const})
                    
                    elif opcode == CommandType.READ_MEM.value:
                        # Формат: read,<смещение>
                        if len(row) < 2 or not row[1]:
                            raise ValueError("Не указано смещение")
                        offset = int(row[1].strip())
                        if offset < 0 or offset > 0x1FFF:  # 13 бит
                            raise ValueError(f"Смещение {offset} выходит за допустимый диапазон (0-{0x1FFF})")
                        cmd = Command(opcode, "read_mem", {"offset": offset})
                    
                    elif opcode == CommandType.WRITE_MEM.value:
                        # Формат: write,<адрес>
                        if len(row) < 2 or not row[1]:
                            raise ValueError("Не указан адрес")
                        address = int(row[1].strip())
                        if address < 0 or address > 0x1FFF:  # 13 бит
                            raise ValueError(f"Адрес {address} выходит за допустимый диапазон (0-{0x1FFF})")
                        cmd = Command(opcode, "write_mem", {"address": address})
                    
                    elif opcode == CommandType.BIN_OP.value:
                        # Формат: rotr (без операндов)
                        cmd = Command(opcode, "bin_op_rotr", {})
                    
                    else:
                        self.errors.append(f"Строка {line_num}: Неподдерживаемый опкод {opcode}")
                        continue
                    
                    self.commands.append(cmd)
                    
                except ValueError as e:
                    self.errors.append(f"Строка {line_num}: Ошибка в аргументах - {str(e)}")
                except Exception as e:
                    self.errors.append(f"Строка {line_num}: Ошибка обработки - {str(e)}")
            
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Ошибка чтения CSV: {str(e)}")
            return False
    def assemble_to_bytes(self) -> bytes:
        """Ассемблирование программы в бинарный формат"""
        binary_data = bytearray()
        
        for cmd in self.commands:
            binary_data.extend(cmd.to_bytes())
        
        return bytes(binary_data)
    
    def get_intermediate_representation(self) -> List[Dict[str, Any]]:
        """Получение промежуточного представления программы"""
        ir = []
        
        for cmd in self.commands:
            ir.append({
                "opcode": cmd.opcode,
                "name": cmd.name,
                "fields": cmd.fields.copy(),
                "hex_bytes": cmd.to_bytes().hex().upper()
            })
        
        return ir
    
    def print_intermediate_representation(self):
        """Вывод промежуточного представления в формате полей и значений"""
        print("\n=== Промежуточное представление программы ===")
        
        for i, cmd in enumerate(self.commands):
            print(f"\nКоманда {i}:")
            print(f"  Опкод: {cmd.opcode} (0x{cmd.opcode:02X})")
            print(f"  Имя: {cmd.name}")
            
            if cmd.fields:
                print(f"  Поля:")
                for field_name, field_value in cmd.fields.items():
                    print(f"    {field_name}: {field_value} (0x{field_value:X})")
            else:
                print(f"  Поля: нет")
            
            # Вывод в формате теста из спецификации
            hex_bytes = cmd.to_bytes().hex().upper()
            hex_pairs = [f"0x{hex_bytes[i:i+2]}" for i in range(0, len(hex_bytes), 2)]
            print(f"  Байты: {', '.join(hex_pairs)}")


def test_specification():
    """Тестирование согласно спецификации УВМ"""
    print("=== Тестирование согласно спецификации УВМ ===\n")
    
    assembler = Assembler()
    
    # Тест 1: Загрузка константы (A=231, B=147)
    print("Тест 1: Загрузка константы (A=231, B=147)")
    test_csv = "load,147"
    assembler.parse_csv(test_csv)
    ir = assembler.get_intermediate_representation()
    
    if ir:
        cmd = assembler.commands[0]
        expected_bytes = bytes([0xF7, 0x93, 0x00, 0x00])
        actual_bytes = cmd.to_bytes()
        
        print(f"  Ожидаемые байты: 0xF7, 0x93, 0x00, 0x00")
        print(f"  Полученные байты: {', '.join([f'0x{b:02X}' for b in actual_bytes])}")
        print(f"  Совпадение: {'ДА' if actual_bytes == expected_bytes else 'НЕТ'}")
    
    # Тест 2: Чтение из памяти (A=61, B=95)
    print("\nТест 2: Чтение из памяти (A=61, B=95)")
    test_csv = "read,95"
    assembler.parse_csv(test_csv)
    ir = assembler.get_intermediate_representation()
    
    if ir:
        cmd = assembler.commands[0]
        expected_bytes = bytes([0x3D, 0x5F, 0x00])
        actual_bytes = cmd.to_bytes()
        
        print(f"  Ожидаемые байты: 0x3D, 0x5F, 0x00")
        print(f"  Полученные байты: {', '.join([f'0x{b:02X}' for b in actual_bytes])}")
        print(f"  Совпадение: {'ДА' if actual_bytes == expected_bytes else 'НЕТ'}")
    
    # Тест 3: Запись в память (A=125, B=242)
    print("\nТест 3: Запись в память (A=125, B=242)")
    test_csv = "write,242"
    assembler.parse_csv(test_csv)
    ir = assembler.get_intermediate_representation()
    
    if ir:
        cmd = assembler.commands[0]
        expected_bytes = bytes([0x7D, 0xF2, 0x00])
        actual_bytes = cmd.to_bytes()
        
        print(f"  Ожидаемые байты: 0x7D, 0xF2, 0x00")
        print(f"  Полученные байты: {', '.join([f'0x{b:02X}' for b in actual_bytes])}")
        print(f"  Совпадение: {'ДА' if actual_bytes == expected_bytes else 'НЕТ'}")
    
    # Тест 4: Бинарная операция (A=145)
    print("\nТест 4: Бинарная операция (A=145)")
    test_csv = "rotr"
    assembler.parse_csv(test_csv)
    ir = assembler.get_intermediate_representation()
    
    if ir:
        cmd = assembler.commands[0]
        expected_bytes = bytes([0x91])
        actual_bytes = cmd.to_bytes()
        
        print(f"  Ожидаемые байты: 0x91")
        print(f"  Полученные байты: {', '.join([f'0x{b:02X}' for b in actual_bytes])}")
        print(f"  Совпадение: {'ДА' if actual_bytes == expected_bytes else 'НЕТ'}")


def main():
    """Основная функция ассемблера"""
    parser = argparse.ArgumentParser(
        description='Ассемблер (УВМ) - вариант 14',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python assembler.py program.csv program.bin
  python assembler.py program.csv program.bin --test
  python assembler.py --test-only
        """
    )
    
    parser.add_argument('input_file', nargs='?', help='Путь к исходному CSV файлу')
    parser.add_argument('output_file', nargs='?', help='Путь к двоичному файлу-результату')
    parser.add_argument('--test', action='store_true', help='Режим тестирования (вывод промежуточного представления)')
    parser.add_argument('--test-only', action='store_true', help='Только тестирование спецификации')
    
    args = parser.parse_args()
    
    # Если запрошено только тестирование спецификации
    if args.test_only:
        test_specification()
        return
    
    # Проверка обязательных аргументов
    if not args.input_file or not args.output_file:
        parser.print_help()
        sys.exit(1)
    
    # Проверка существования входного файла
    if not os.path.exists(args.input_file):
        print(f"Ошибка: Файл '{args.input_file}' не найден")
        sys.exit(1)
    
    try:
        # Чтение исходного файла
        with open(args.input_file, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        # Создание и настройка ассемблера
        assembler = Assembler()
        
        # Парсинг CSV
        if not assembler.parse_csv(csv_content):
            print("Ошибки ассемблирования:")
            for error in assembler.errors:
                print(f"  - {error}")
            sys.exit(1)
        
        # Вывод промежуточного представления в режиме тестирования
        if args.test:
            assembler.print_intermediate_representation()
            print("\n" + "="*50 + "\n")
        
        # Ассемблирование в бинарный формат
        binary_data = assembler.assemble_to_bytes()
        
        # Запись результата
        with open(args.output_file, 'wb') as f:
            f.write(binary_data)
        
        print(f"Ассемблирование успешно завершено!")
        print(f"  Входной файл: {args.input_file}")
        print(f"  Выходной файл: {args.output_file}")
        print(f"  Количество команд: {len(assembler.commands)}")
        print(f"  Размер кода: {len(binary_data)} байт")
        
        # Дополнительная проверка спецификации в режиме теста
        if args.test:
            test_specification()
    
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Импорт struct здесь, чтобы избежать проблем
    import struct
    main()