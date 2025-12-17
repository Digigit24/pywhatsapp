"""Check template structure to see variables"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_db_session
from app.models.template import WhatsAppTemplate
import json
import re

def check_template(template_name: str = "services"):
    """Check template structure and save to file"""

    output_file = f"{template_name}_template_structure.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        with get_db_session() as db:
            template = db.query(WhatsAppTemplate).filter(
                WhatsAppTemplate.name == template_name
            ).first()

            if not template:
                f.write(f"[ERROR] Template '{template_name}' not found\n")
                print(f"[ERROR] Template '{template_name}' not found")
                return

            f.write(f"[OK] Template: {template.name}\n")
            f.write(f"   Language: {template.language}\n")
            f.write(f"   Status: {template.status.value}\n")
            f.write(f"   Category: {template.category.value}\n")
            f.write(f"\nComponents:\n")

            if template.components:
                for idx, component in enumerate(template.components, 1):
                    comp_type = component.get('type', 'unknown')
                    f.write(f"\n   Component {idx}: {comp_type.upper()}\n")

                    if comp_type == 'BODY':
                        text = component.get('text', '')
                        f.write(f"   Text: {text}\n")

                        # Check for variables
                        if 'example' in component:
                            f.write(f"   Example values: {component['example']}\n")

                        # Count variables {{1}}, {{2}}, etc.
                        variables = re.findall(r'\{\{(\d+)\}\}', text)
                        if variables:
                            f.write(f"   [OK] Found {len(variables)} variables: {variables}\n")
                            f.write(f"\n   [TIP] To send this template, use parameters:\n")
                            f.write(f'      {{"1": "value1", "2": "value2", ...}}\n')

                            # Show example based on variable count
                            f.write(f'\n   Example payload for template broadcast:\n')
                            f.write(f'   {{\n')
                            f.write(f'       "campaign_name": "My Campaign",\n')
                            f.write(f'       "template_name": "{template_name}",\n')
                            f.write(f'       "template_language": "{template.language}",\n')
                            f.write(f'       "contact_ids": [36, 35],\n')
                            f.write(f'       "parameters": {{\n')
                            for var in variables:
                                f.write(f'           "{var}": "value_for_variable_{var}",\n')
                            f.write(f'       }}\n')
                            f.write(f'   }}\n')
                        else:
                            f.write(f"   [OK] No variables - template has fixed text\n")
                            f.write(f'\n   Example payload for template broadcast:\n')
                            f.write(f'   {{\n')
                            f.write(f'       "campaign_name": "My Campaign",\n')
                            f.write(f'       "template_name": "{template_name}",\n')
                            f.write(f'       "template_language": "{template.language}",\n')
                            f.write(f'       "contact_ids": [36, 35]\n')
                            f.write(f'   }}\n')

                    elif comp_type == 'HEADER':
                        f.write(f"   Header type: {component.get('format', 'text')}\n")
                        if 'text' in component:
                            f.write(f"   Text: {component['text']}\n")

                    elif comp_type == 'FOOTER':
                        f.write(f"   Footer: {component.get('text', '')}\n")

                    elif comp_type == 'BUTTONS':
                        buttons = component.get('buttons', [])
                        f.write(f"   Buttons ({len(buttons)}):\n")
                        for btn in buttons:
                            f.write(f"      - {btn.get('type')}: {btn.get('text')}\n")
            else:
                f.write("   No components found\n")

    print(f"[OK] Template structure saved to: {output_file}")
    print(f"     Check the file for full details including example payloads")

if __name__ == "__main__":
    template_name = sys.argv[1] if len(sys.argv) > 1 else "services"
    check_template(template_name)
