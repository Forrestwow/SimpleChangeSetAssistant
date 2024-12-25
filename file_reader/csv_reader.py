import csv
import os

class CsvFile:
    def __init__(self):
        self.from_file = None
        self.select_columns = {}

    def source(self, file_path):
        self.from_file = file_path
        return self

    def select(self, select_columns):
        self.select_columns = select_columns
        return self

    def collect(self):
        rows = self.get_rows()

        return self.apply_select(rows)

    def get_rows(self):
        if not self.from_file:
            raise ValueError("File not found")

        rows = []
        with open(self.from_file, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            for row in reader:
                rows.append(row)

        return rows

    def apply_select(self, rows):
        filtered = []

        for row in rows:
            selected_row = {}
            for k, v in self.select_columns.items():
                column_index = ord(v.upper()) - ord('A')
                selected_row[k] = row[column_index]
            filtered.append(selected_row)
        return filtered

