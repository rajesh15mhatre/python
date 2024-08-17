import os
import shutil
import pyodbc
import json
from datetime import datetime

def load_config():
    # Load database connection and target directory details from config.json
    with open('D:\Rajesh\projects\IT Seva\config\config.json', 'r') as file:
        config = json.load(file)
    return config

def connect_to_database(config):
    # Connect to SQL Server using details from config
    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={config['repository']['db_server']};DATABASE={config['repository']['db_name']};Trusted_Connection=yes;"
    connection = pyodbc.connect(connection_string)
    return connection

def fetch_filepaths(connection):
    # Fetch file paths from the repository table
    cursor = connection.cursor()
    cursor.execute("SELECT filepath FROM dbo.repository;")
    filepaths = cursor.fetchall()
    return [row[0] for row in filepaths]

def create_directory_structure(source_filepath, target_base_dir):
    # Create the directory structure in the target directory
    target_filepath = os.path.join(target_base_dir, os.path.relpath(source_filepath, os.path.splitdrive(source_filepath)[0]))
    target_dir = os.path.dirname(target_filepath)
    os.makedirs(target_dir, exist_ok=True)
    return target_filepath

def copy_files(filepaths, target_base_dir, connection):
    # Copy files from source to target directory
    cursor = connection.cursor()
    for source_filepath in filepaths:
        if os.path.exists(source_filepath):
            target_filepath = create_directory_structure(source_filepath, target_base_dir)
            shutil.copy2(source_filepath, target_filepath)
            
            # Log the operation in repository_log table
            log_operation(cursor, source_filepath, target_filepath)

    # Commit all log entries to the database
    connection.commit()

def log_operation(cursor, source_filepath, target_filepath):
    # Insert log into the repository_log table
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT INTO dbo.repository_log (source_filepath, target_filepath, operation_timestamp) "
        "VALUES (?, ?, ?);",
        source_filepath, target_filepath, timestamp
    )

def main():
    # Load configuration
    config = load_config()

    # Connect to the database
    connection = connect_to_database(config)

    try:
        # Fetch file paths from the repository table
        filepaths = fetch_filepaths(connection)
        
        # Copy files and log operations
        copy_files(filepaths, config['repository']['target_directory'], connection)
    finally:
        # Close the database connection
        connection.close()

if __name__ == '__main__':
    main()
