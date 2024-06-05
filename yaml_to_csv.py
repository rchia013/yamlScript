import yaml
import pandas as pd
import argparse

def extract_paths(yaml_content):
    paths = yaml_content.get('paths', {})
    path_details = []
    for path, methods in paths.items():
        for method, details in methods.items():
            api_section = 'Body'
            path_details.append({
                'Path': path,
                'Method': method.upper(),
                'Summary': details.get('summary', 'N/A'),
                'Description': details.get('description', 'N/A'),
                'Operation ID': details.get('operationId', 'N/A'),
                'Tags': ', '.join(details.get('tags', [])),
                'Request Body': details.get('requestBody', 'N/A'),
                'Parameters': details.get('parameters', []),
                'Responses': details.get('responses', 'N/A'),
                'API Section': api_section
            })
    return path_details

def expand_schema(schema_name, schemas, parent=''):
    schema_info = schemas.get(schema_name, {})
    properties = schema_info.get('properties', {})
    schema_details = []

    for prop_name, prop_info in properties.items():
        prop_type = prop_info.get('type', 'N/A')
        prop_min_length = prop_info.get('minLength', 'N/A')
        prop_max_length = prop_info.get('maxLength', 'N/A')
        prop_pattern = prop_info.get('pattern', 'N/A')
        if prop_min_length == prop_max_length:
            prop_length = prop_min_length
        else:
            prop_length = 'N/A'
        prop_description = prop_info.get('description', 'N/A')
        
        full_prop_name = f"{parent}.{prop_name}" if parent else prop_name
        
        schema_details.append({
            'Data Element Name': full_prop_name,
            'Data Element Type': prop_type,
            'Data Element Length': prop_length,
            'Data Element Description': prop_description,
            'Regular Expression': prop_pattern
        })
        
        if prop_type == 'array' and 'items' in prop_info and '$ref' in prop_info['items']:
            ref_schema_name = prop_info['items']['$ref'].split('/')[-1]
            schema_details.extend(expand_schema(ref_schema_name, schemas, full_prop_name))
        
        elif prop_type == 'object' and '$ref' in prop_info:
            ref_schema_name = prop_info['$ref'].split('/')[-1]
            schema_details.extend(expand_schema(ref_schema_name, schemas, full_prop_name))

    return schema_details


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
                schema_details = expand_schema(schema_name, schemas, parent='')
                for detail in schema_details:
                    detail['API Section'] = 'Body'
                response_schema_details.extend(schema_details)
    return response_schema_details


def handle_post_request(path, schemas):
    request_body = path['Request Body']
    content = request_body.get('content', {})
    if 'application/json' in content:
        details = content['application/json']
        schema = details.get('schema', {}).get('$ref', '')
        if schema.startswith('#/components/schemas/'):
            schema_name = schema.split('/')[-1]
            schema_details = expand_schema(schema_name, schemas, parent='')
            for detail in schema_details:
                detail['API Section'] = 'Body'
            return schema_details
    return []


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
                'Sequence No.', 'API Section', 'Data Element Name', 'Data Element Type', 'Data Element Length', 'Data Element Description', 'Regular Expression'
            ])

            # Define the sheet name based on path and method
            sheet_name = f"Path_{idx+1}"

           # Create a DataFrame for the method identifier
            identifier_df = pd.DataFrame([[f"Method: {method}"]], columns=["Method Identifier"])

            # Write the identifier and schema DataFrames to the new sheet
            identifier_df.to_excel(writer, sheet_name=sheet_name, index=False, header=False)
            schema_df.to_excel(writer, sheet_name=sheet_name, startrow=1, index=False)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert YAML file to Excel template.")
    parser.add_argument("yaml_file", help="Path to the input YAML file")
    parser.add_argument("output_file", help="Path to the output Excel file")

    args = parser.parse_args()

    # Call the function with the provided arguments
    populate_excel_template(args.yaml_file, args.output_file)
