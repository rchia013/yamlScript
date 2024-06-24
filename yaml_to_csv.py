import yaml
import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import argparse

def extract_paths(yaml_content):
    paths = yaml_content.get('paths', {})
    path_details = []
    for path, methods in paths.items():
        for method, details in methods.items():
            path_details.append({
                'Path': path,
                'Method': method.upper(),
                'Summary': details.get('summary', 'N/A'),
                'Description': details.get('description', 'N/A'),
                'Operation ID': details.get('operationId', 'N/A'),
                'Tags': ', '.join(details.get('tags', [])),
                'Request Body': details.get('requestBody', {}),
                'Parameters': details.get('parameters', []),
                'Responses': details.get('responses', 'N/A')
            })
    return path_details

def resolve_references(prop_info, schemas):
    if 'enum' in prop_info:
        return prop_info['enum']
    
    if '$ref' in prop_info:
        ref_schema_name = prop_info['$ref'].split('/')[-1]
        ref_schema_info = schemas.get(ref_schema_name, {})
        if 'enum' in ref_schema_info:
            return ref_schema_info['enum']
        return resolve_references(ref_schema_info, schemas)
    
    if 'items' in prop_info and '$ref' in prop_info['items']:
        ref_schema_name = prop_info['items']['$ref'].split('/')[-1]
        ref_schema_info = schemas.get(ref_schema_name, {})
        if 'enum' in ref_schema_info:
            return ref_schema_info['enum']
        return resolve_references(ref_schema_info, schemas)
    
    return ''

def expand_schema(schema_name, schemas, parent=''):
    schema_info = schemas.get(schema_name, {})
    properties = schema_info.get('properties', {})
    schema_details = []

    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get('type', '')
        prop_min_length = prop_info.get('minLength', '')
        prop_max_length = prop_info.get('maxLength', '')
        prop_pattern = prop_info.get('pattern', '')
        prop_enum = resolve_references(prop_info, schemas)
        
        if isinstance(prop_enum, list):
            prop_enum = [str(e) for e in prop_enum]
            enum_values = ', '.join(prop_enum)
            numeric_min_value = min(int(e) for e in prop_enum if e.isdigit())
            numeric_max_value = max(int(e) for e in prop_enum if e.isdigit())
        else:
            enum_values = prop_enum
            numeric_min_value = prop_min_length
            numeric_max_value = prop_max_length

        if prop_min_length == prop_max_length:
            prop_length = prop_min_length
        else:
            prop_length = ''
        prop_description = prop_info.get('description', '')
        
        # Remove 'body.' or 'parameter.' prefix from the full property name
        full_prop_name = f"{parent}.{prop_name}" if parent else prop_name
        if full_prop_name.startswith('body.') or full_prop_name.startswith('parameter.'):
            full_prop_name = full_prop_name.split('.', 1)[1]
        
        print(f"Processing property: {full_prop_name}")
        print(f"Enum values: {enum_values}")

        schema_details.append({
            'Data Element Name': full_prop_name,
            'Data Element Type': prop_type,
            'Data Element Length': prop_length,
            'Numeric Min Value': numeric_min_value,
            'Numeric Max Value': numeric_max_value,
            'Data Element Description': prop_description,
            'Regular Expression': prop_pattern,
            'Enumerations': enum_values,
            'API Section': 'Body' if 'body' in parent.lower() else 'Parameter'
        })
        
        if prop_type == 'array' and 'items' in prop_info and '$ref' in prop_info['items']:
            ref_schema_name = prop_info['items']['$ref'].split('/')[-1]
            schema_details.extend(expand_schema(ref_schema_name, schemas, full_prop_name))
        
        elif prop_type == 'object' and '$ref' in prop_info:
            ref_schema_name = prop_info['$ref'].split('/')[-1]
            schema_details.extend(expand_schema(ref_schema_name, schemas, full_prop_name))

    return schema_details



def extract_headers(parameters):
    header_details = []
    for param in parameters:
        if param['in'] == 'header':
            header_name = param.get('name', '')
            header_type = param.get('schema', {}).get('type', '')
            header_pattern = param.get('schema', {}).get('pattern', '')
            header_enum = param.get('schema', {}).get('enum', '')
            if isinstance(header_enum, list):
                header_enum = ', '.join(map(str, header_enum))
            header_details.append({
                'Data Element Name': header_name,
                'Data Element Type': header_type,
                'Data Element Length': '',  # No length for headers
                'Data Element Description': '',  # No description for headers
                'Regular Expression': header_pattern,
                'Enumerations': header_enum,
                'API Section': 'Header'
            })
    print(f"Extracted headers: {header_details}")
    return header_details

def handle_get_request(path, schemas):
    responses = path['Responses']
    response_schema_details = []
    for status_code, response in responses.items():
        content = response.get('content', {})
        if 'application/json' in content:
            details = content['application/json']
            schema = details.get('schema', {}).get('$ref', '')
            if schema.startswith('#/components/schemas/'):
                schema_name = schema.split('/')[-1]
                schema_details = expand_schema(schema_name, schemas, parent='parameter')
                for detail in schema_details:
                    detail['API Section'] = 'Parameter'
                response_schema_details.extend(schema_details)
    return response_schema_details

def handle_post_request(path, schemas):
    request_body = path.get('Request Body', {})
    parameters = path.get('Parameters', [])
    content = request_body.get('content', {})
    
    print(f"Request Body: {request_body}")
    print(f"Parameters: {parameters}")

    # Extract headers
    header_data = extract_headers(parameters)
    print(f"Header data: {header_data}")
    
    # Extract request body schema
    schema_data = []
    if 'application/json' in content:
        details = content['application/json']
        schema = details.get('schema', {}).get('$ref', '')
        if schema.startswith('#/components/schemas/'):
            schema_name = schema.split('/')[-1]
            schema_data = expand_schema(schema_name, schemas, parent='body')
            for detail in schema_data:
                detail['API Section'] = 'Body'
    print(f"Schema data: {schema_data}")

    # Combine header data and schema data
    combined_data = header_data + schema_data
    print(f"Combined data: {combined_data}")
    return combined_data

def handle_get_request(path, schemas):
    responses = path['Responses']
    response_schema_details = []
    for status_code, response in responses.items():
        content = response.get('content', {})
        if 'application/json' in content:
            details = content['application/json']
            schema = details.get('schema', {}).get('$ref', '')
            if schema.startswith('#/components/schemas/'):
                schema_name = schema.split('/')[-1]
                schema_details = expand_schema(schema_name, schemas, parent='parameter')
                for detail in schema_details:
                    detail['API Section'] = 'Parameter'
                response_schema_details.extend(schema_details)
    return response_schema_details


def populate_excel_template(yaml_file, output_file):
    # Load the YAML file
    with open(yaml_file, 'r') as file:
        yaml_content = yaml.safe_load(file)

    # Extract paths and schemas from the YAML content
    paths = extract_paths(yaml_content)
    components = yaml_content.get('components', {})
    schemas = components.get('schemas', {})

    # Prepare the writer with the output file
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for idx, path in enumerate(paths):
            method = path['Method']
            if method == 'GET':
                payload_data = handle_get_request(path, schemas)
            elif method == 'POST':
                payload_data = handle_post_request(path, schemas)
            else:
                continue

            # Add sequence numbers to schema details
            for seq_num, detail in enumerate(payload_data, start=1):
                detail['Sequence No.'] = seq_num
    
            # Create DataFrame for the schema details
            schema_df = pd.DataFrame(payload_data, columns=[
                'Sequence No.', 'API Section', 'Data Element Name', 'Data Element Type', 'Data Element Length', 
                'Numeric Min Value', 'Numeric Max Value', 'Enumerations', 'Regular Expression', 'Data Element Description'
            ])

            # Define the sheet name based on path and method
            sheet_name = f"A_{idx+1}"

            # Write the DataFrame to the new sheet
            schema_df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)

            # Get the worksheet
            worksheet = writer.sheets[sheet_name]

            # Write the method identifier at the top
            worksheet.cell(row=1, column=1).value = f"Method: {method}"

            # Adjust the column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert YAML file to Excel template.")
    parser.add_argument("yaml_file", help="Path to the input YAML file")
    parser.add_argument("output_file", help="Path to the output Excel file")

    args = parser.parse_args()

    # Call the function with the provided arguments
    populate_excel_template(args.yaml_file, args.output_file)
