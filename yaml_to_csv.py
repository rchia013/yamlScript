import yaml
import pandas as pd
import argparse

def extract_info(yaml_content):
    info = yaml_content.get('info', {})
    return {
        'Title': info.get('title', 'N/A'),
        'Version': info.get('version', 'N/A'),
        'Description': info.get('description', 'N/A')
    }

def extract_servers(yaml_content):
    servers = yaml_content.get('servers', [])
    return [server.get('url', 'N/A') for server in servers]

def extract_paths(yaml_content):
    paths = yaml_content.get('paths', {})
    path_details = []
    for path, methods in paths.items():
        for method, details in methods.items():
            api_section = 'Body' if method.upper() == 'POST' else 'Parameter' if method.upper() == 'GET' else 'N/A'
            path_details.append({
                'Path': path,
                'Method': method.upper(),
                'Summary': details.get('summary', 'N/A'),
                'Description': details.get('description', 'N/A'),
                'Operation ID': details.get('operationId', 'N/A'),
                'Tags': ', '.join(details.get('tags', [])),
                'Request Body': details.get('requestBody', 'N/A'),
                'Responses': details.get('responses', 'N/A'),
                'API Section': api_section
            })
    return path_details

def extract_schemas(yaml_content):
    components = yaml_content.get('components', {})
    schemas = components.get('schemas', {})
    schema_details = []
    processed_schemas = set()
    
    for schema_name, schema_info in schemas.items():
        if schema_name not in processed_schemas:
            properties = schema_info.get('properties', {})
            for prop_name, prop_info in properties.items():
                #print(prop_name,prop_info)
                schema_details.append({ 
                    'Schema Name': schema_name,
                    'Property Name': prop_name,
                    'Property Type': prop_info.get('type', 'N/A'),
                    'Property Format': prop_info.get('format', 'N/A'),
                    'Property Description': prop_info.get('description', 'N/A')
                })
            processed_schemas.add(schema_name)
            print(processed_schemas)
    
    #print("Extracted Schemas:")  # Debugging statement
    #for schema in schema_details:  # Debugging statement
    #    print(schema)  # Debugging statement
    
    return schema_details

def populate_excel_template(yaml_file, output_file):
    # Load the YAML file
    with open(yaml_file, 'r') as file:
        yaml_content = yaml.safe_load(file)

    # Extract data using the defined functions
    paths = extract_paths(yaml_content)
    schemas = extract_schemas(yaml_content)
    # Prepare the writer with the output file
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for idx, path in enumerate(paths):
            request_body = path['Request Body']
            payload_data = []
            processed_schemas = set()
            if request_body != 'N/A' and 'content' in request_body:
                content = request_body['content']
                for content_type, details in content.items():
                    schema = details.get('schema', {}).get('$ref', '')
                    if schema.startswith('#/components/schemas/'):
                        schema_name = schema.split('/')[-1]
                        if schema_name not in processed_schemas:
                            schema_info = [s for s in schemas if s['Schema Name'] == schema_name]
                            for info in schema_info:
                                payload_data.append({
                                    'Sequence No.': '',
                                    'API Section': path['API Section'],
                                    'Data Element Name': info['Property Name'],
                                    'Data Element Type': info['Property Type'],
                                    'Data Element Length': '',
                                    'Valid Values': '',
                                    'Regular Expressions': '',
                                    'Data Element Definition': info['Property Description'],
                                    'Data Source': '',
                                    'Business Rules': '',
                                    'Numeric Min Value': '',
                                    'Numeric Max Value': '',
                                    'Enumerations': ''
                                })
                            processed_schemas.add(schema_name)

            # Create DataFrame for the path
            payload_df = pd.DataFrame(payload_data, columns=[
                'Sequence No.', 'API Section', 'Data Element Name', 'Data Element Type', 
                'Data Element Length', 'Valid Values', 'Regular Expressions', 
                'Data Element Definition', 'Data Source', 'Business Rules',
                'Numeric Min Value', 'Numeric Max Value', 'Enumerations'
            ])

            # Add sequence numbers
            payload_df['Sequence No.'] = range(1, len(payload_df) + 1)

            # Define the sheet name based on path and method
            sheet_name = f"A_{idx+1}"

            # Write the DataFrame to the new sheet
            payload_df.to_excel(writer, sheet_name=sheet_name, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert YAML file to Excel template.")
    parser.add_argument("yaml_file", help="Path to the input YAML file")
    parser.add_argument("output_file", help="Path to the output Excel file")

    args = parser.parse_args()

    # Call the function with the provided arguments
    populate_excel_template(args.yaml_file, args.output_file)
