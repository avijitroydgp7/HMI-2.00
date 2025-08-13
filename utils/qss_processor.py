"""
QSS Processor Utility
Processes QSS files to use centralized variables from variable.qss
"""

import re
import os
from pathlib import Path

class QSSProcessor:
    def __init__(self, theme_dir="styles/dark_theme"):
        self.theme_dir = Path(theme_dir)
        self.variables = {}
        self.load_variables()
    
    def load_variables(self):
        """Load variables from variable.qss"""
        variable_file = self.theme_dir / "variable.qss"
        if not variable_file.exists():
            print(f"Warning: {variable_file} not found")
            return
        
        with open(variable_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse color variables
        color_pattern = r'@([\w-]+):\s*#([0-9a-fA-F]{3,8});'
        for match in re.finditer(color_pattern, content):
            var_name, color_value = match.groups()
            self.variables[f'#{color_value}'] = f'@{var_name}'
        
        # Parse size variables
        size_pattern = r'@([\w-]+):\s*(\d+(?:px|pt|em|%));'
        for match in re.finditer(size_pattern, content):
            var_name, size_value = match.groups()
            self.variables[size_value] = f'@{var_name}'
    
    def process_file(self, input_file, output_file=None):
        """Process a QSS file and replace hardcoded values with variables"""
        if output_file is None:
            output_file = input_file.replace('.qss', '_processed.qss')
        
        input_path = self.theme_dir / input_file
        output_path = self.theme_dir / output_file
        
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace hardcoded values with variables
        processed_content = content
        for hardcoded, variable in self.variables.items():
            processed_content = processed_content.replace(hardcoded, variable)
        
        # Add import statement if not present
        if '@import url("variable.qss");' not in processed_content:
            processed_content = '@import url("variable.qss");\n\n' + processed_content
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        print(f"Processed: {input_file} -> {output_file}")
        return output_path
    
    def process_all_files(self):
        """Process all QSS files in the theme directory"""
        qss_files = list(self.theme_dir.glob('*.qss'))
        processed_files = []
        
        for qss_file in qss_files:
            if qss_file.name not in ['variable.qss', 'theme_loader.qss', 'template_using_variables.qss']:
                output_file = qss_file.stem + '_variables.qss'
                processed = self.process_file(qss_file.name, output_file)
                processed_files.append(processed)
        
        return processed_files
    
    def create_color_mapping_report(self):
        """Create a report of color mappings"""
        report = "Color Mapping Report\n"
        report += "=" * 50 + "\n"
        
        for hardcoded, variable in sorted(self.variables.items()):
            report += f"{hardcoded} -> {variable}\n"
        
        return report

if __name__ == "__main__":
    processor = QSSProcessor()
    
    # Process all QSS files
    processed = processor.process_all_files()
    print(f"\nProcessed {len(processed)} files")
    
    # Print color mapping report
    print("\n" + processor.create_color_mapping_report())
