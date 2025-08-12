# services/csv_service.py
# A service for importing and exporting tags via CSV files, with support for flattened arrays.

import csv
import os
import json
import re
from typing import List, Dict, Any

from services.tag_data_service import tag_data_service

class CsvService:
    """
    Provides functionality to import and export tag data using the CSV format.
    Arrays are "flattened" so that each element has its own row.
    """
    def _flatten_and_write_array(self, writer, tag_info, data_slice, indices_prefix=""):
        """Recursively traverses a nested list and writes a row for each element."""
        for i, value in enumerate(data_slice):
            current_indices = f"{indices_prefix}[{i}]"
            if isinstance(value, list):
                self._flatten_and_write_array(writer, tag_info, value, current_indices)
            else:
                row = [
                    f"{tag_info['name']}{current_indices}", # e.g., MyTag[0][0]
                    tag_info['data_type'],
                    tag_info['comment'],
                    value, # The actual element value
                    "", # No dimensions for element rows
                    tag_info.get('length', 0)
                ]
                writer.writerow(row)

    def export_tags_to_csv(self, db_id: str, file_path: str) -> bool:
        """
        Exports all tags from a given database to a CSV file in a flattened format.
        """
        db_data = tag_data_service.get_tag_database(db_id)
        if not db_data: return False

        tags = db_data.get('tags', [])
        header = ['TagName', 'DataType', 'Comment', 'InitialValue', 'ArrayDims', 'Length']

        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for tag in tags:
                    is_array = bool(tag.get('array_dims'))
                    if is_array:
                        # Write the main array definition row
                        array_dims_str = 'x'.join(map(str, tag.get('array_dims', [])))
                        header_row = [
                            tag.get('name', ''),
                            tag.get('data_type', 'INT'),
                            tag.get('comment', ''),
                            '', # No single value for the array header
                            array_dims_str,
                            tag.get('length', 0)
                        ]
                        writer.writerow(header_row)
                        # Now write a row for each element
                        self._flatten_and_write_array(writer, tag, tag.get('value', []))
                    else:
                        # Write a single row for a simple tag
                        simple_row = [
                            tag.get('name', ''),
                            tag.get('data_type', 'INT'),
                            tag.get('comment', ''),
                            tag.get('value', ''),
                            '',
                            tag.get('length', 0)
                        ]
                        writer.writerow(simple_row)
            return True
        except IOError:
            return False

    def import_tags_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Imports tags from a flattened CSV file and reconstructs the data structure.
        """
        tags_to_import = {}
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tag_name_full = row.get('TagName')
                    if not tag_name_full: continue

                    # Check if it's an array element or a base tag
                    match = re.match(r"(.+?)(\[.+\])", tag_name_full)
                    is_element = bool(match)

                    if is_element:
                        # This is an element of an existing array, set its value
                        base_name = match.group(1)
                        indices_str = match.group(2)
                        indices = [int(i) for i in re.findall(r'\[(\d+)\]', indices_str)]
                        
                        if base_name in tags_to_import:
                            # Navigate the nested list to set the value
                            value_ptr = tags_to_import[base_name]['value']
                            for index in indices[:-1]:
                                value_ptr = value_ptr[index]
                            
                            # Convert value to correct type
                            val_str = row.get('InitialValue', '')
                            data_type = tags_to_import[base_name]['data_type']
                            if data_type == 'BOOL': value = val_str.lower() in ('true', '1')
                            elif data_type in ('INT', 'DINT'): value = int(val_str) if val_str else 0
                            elif data_type == 'REAL': value = float(val_str) if val_str else 0.0
                            else: value = val_str
                            
                            value_ptr[indices[-1]] = value
                    else:
                        # This is a base tag definition
                        base_name = tag_name_full
                        data_type = row.get('DataType', 'INT')
                        array_dims_str = row.get('ArrayDims', '')
                        
                        tag_data = {
                            "name": base_name,
                            "data_type": data_type,
                            "comment": row.get('Comment', ''),
                            "length": int(row.get('Length', 0))
                        }

                        if array_dims_str:
                            dims = [int(d) for d in array_dims_str.split('x')]
                            tag_data['array_dims'] = dims
                            tag_data['value'] = tag_data_service._create_default_array(dims, data_type)
                        else:
                            tag_data['array_dims'] = []
                            val_str = row.get('InitialValue', '')
                            if data_type == 'BOOL': tag_data['value'] = val_str.lower() in ('true', '1')
                            elif data_type in ('INT', 'DINT'): tag_data['value'] = int(val_str) if val_str else 0
                            elif data_type == 'REAL': tag_data['value'] = float(val_str) if val_str else 0.0
                            else: tag_data['value'] = val_str

                        tags_to_import[base_name] = tag_data
            
            return list(tags_to_import.values())
        except (IOError, ValueError, KeyError) as e:
            raise ValueError(f"Failed to process CSV file: {e}")

csv_service = CsvService()
