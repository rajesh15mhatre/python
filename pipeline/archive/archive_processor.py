"""
Archive script with rollback functionality
Done:
- Use Global Archive key  for each archive 

TO DOs:
- MOve archive tables to archive DB - Done
- Move config of db source and destination to database  - Done
- Create script execution based on script parameter event mapping key - Done
- Archive Event table first to avoid duplicate archive in case archive fails in between  - Done testing pending
- Change logs from json file to DB table and only save aggregate logs - Done
- Add logic to verify constraint and apply new constraint using ALTER table - TBS
- Add unit tests - TBS
- Check if table has any triggers - TBS

Error while archiving funciton in class method
    in Object of type Row is not JSON serializable
"""
from decimal import Decimal
import pyodbc
import json
import argparse
from datetime import datetime
import datetime as dt

# def setup_logger():
#     """
#     Setup logger for the archive script.

#     Returns:
#         logger: Logger object
#     """
#     logger = logging.getLogger("archive_script")
#     logger.setLevel(logging.DEBUG)
#     formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
#     # file handler
#     file_handler = logging.FileHandler('archive_script.log')
#     file_handler.setFormatter(formatter)
#     logger.addHandler(file_handler)
#     # console handler
#     # Handler for logging to the terminal
#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(logging.DEBUG) 
#     console_handler.setFormatter(formatter)
#     logger.addHandler(console_handler)

#     return logger

def read_config(filename):
    """
    Read database connection details from config file.

    Args:
        filename (str): Path to the configuration file.

    Returns:
        dict: Database connection details.
    """
    with open(filename, 'r') as file:
        return json.load(file)

# Setup logger
# logger = setup_logger()

# Read database connection details from config file
config = read_config('D:\Rajesh\projects\IT Seva\config\config.json')

# Date formatted as YYYY-MM-DD
current_date = datetime.now().strftime('%Y-%m-%d')

# Dictionary to store rollback information for the current date
rollback_info = {}

# While clearing destination DB we can skip below tables 
non_drop_tables = []

def generate_archive_key(cursor, db_mapping_key):
    """
    Creates a master_archive table if it does not already exist. 
    The table has an archive_id which is a global archive key for each  DB archive run
    as an identity auto-increment column and CreatedDate. Inserts new entry and returns latest archive_id

    Args:
        cursor: Cursor object for executing SQL queries.
        db_mapping_key: key used for archive DB mapping
    """
    create_query = """
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'MasterArchive')
    BEGIN
        CREATE TABLE MasterArchive (
            ArchiveId INT IDENTITY(1,1) PRIMARY KEY,
            MappingId INT NOT NULL,
            CreatedDate DATETIME DEFAULT GETDATE()
        )
    END
    """
    cursor.execute(create_query)
    cursor.commit()

     # Insert a new record with the current datetime
    insert_query = f"""
    INSERT INTO MasterArchive (MappingId) VALUES ({db_mapping_key})
    """
    cursor.execute(insert_query)
    cursor.commit()

    # Get the latest archive_id value
    cursor.execute("SELECT MAX(ArchiveId) FROM [dbo].[MasterArchive]")
    latest_archive_id = cursor.fetchone()[0]

    return latest_archive_id


def create_archive_audit_table(cursor):
    """
    Create the archive_audit table if it doesn't exist. This table will have logs of all 

    Args:
        cursor: Cursor object for executing SQL queries.

    Returns:
        int: The latest archive_id value.
    """
    # SQL query to create the archive_audit table if it doesn't exist
    create_table_query = """
    IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'ArchiveAudit')
    BEGIN
        CREATE TABLE ArchiveAudit (
            ArchiveId INT,
            ObjectName VARCHAR(100),
            ObjectType VARCHAR(20),
            ArchiveAction VARCHAR(100),
            ObjectQuery TEXT,
            ImpactedRowCount INT,
            DateInserted DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT PK_ArchiveAudit PRIMARY KEY (ArchiveId, ObjectName, ObjectType, ArchiveAction),
            CONSTRAINT FK_ArchiveAudit FOREIGN KEY (ArchiveId) REFERENCES MasterArchive(ArchiveId)
        );
    END;
    """

    try:
        # Create the archive_audit table if it doesn't exist
        cursor.execute(create_table_query)
        cursor.commit()

    except Exception as e:
        print("An error occurred:", e)

    return

def get_tables(cursor):
    """
    Retrieve list of tables from the database in order: tables with foreign key constraints first,
    then tables without foreign key constraints.

    Args:
        cursor: Cursor object for executing SQL queries.

    Returns:
        list: List of table names ordered by foreign key constraints.
    """
    # Retrieve all tables from INFORMATION_SCHEMA.TABLES
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
    all_tables = cursor.fetchall()
    
    # Convert the list of tuples to a list of table names
    all_table_names = [table[0] for table in all_tables]
    
    # Retrieve tables that have foreign key constraints
    cursor.execute("""
        SELECT DISTINCT TABLE_NAME
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE CONSTRAINT_NAME like 'FK%'
    """)
    fk_tables = cursor.fetchall()
    
    # Convert the list of tuples to a list of table names with foreign key constraints
    fk_table_names = [table[0] for table in fk_tables]
    
    # Separate tables into two lists: with foreign key constraints and without
    with_fk_tables = []
    without_fk_tables = []
    
    for table in all_table_names:
        if table in fk_table_names:
            with_fk_tables.append(table)
        else:
            without_fk_tables.append(table)
    
    # Return the list of tables in the desired order: with foreign key constraints first
    return with_fk_tables + without_fk_tables


def get_columns_metadata(cursor, table_name):
    """
    Retrieve metadata for columns of a table.

    Args:
        cursor: Database cursor object.
        table_name (str): Name of the table.

    Returns:
        list: List of tuples containing column metadata.
            Each tuple contains:
            - COLUMN_NAME: Name of the column.
            - DATA_TYPE: Data type of the column.
            - COL_LENGTH: Length of the column.
            - NUMERIC_PRECISION: Precision of the column for numeric data types.
            - NUMERIC_SCALE: Scale of the column for numeric data types.
            - IS_IDENTITY: Whether the column is an identity column.
    """
    cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE, COL_LENGTH('dbo.{table_name}', COLUMN_NAME), NUMERIC_PRECISION, NUMERIC_SCALE, COLUMNPROPERTY(object_id(TABLE_NAME), COLUMN_NAME, 'IsIdentity') AS IS_IDENTITY FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
    columns = cursor.fetchall()
    return columns

# Function to create table in the destination database
def create_table(dest_cursor, table_name, columns_metadata, primary_key=None):
    """
    Create a table in the destination database.

    Args:
        dest_cursor: Database cursor object for the destination database.
        table_name (str): Name of the table to be created.
        columns_metadata (list): List of tuples containing column metadata.
            Each tuple contains:
            - COLUMN_NAME: Name of the column.
            - DATA_TYPE: Data type of the column.
            - COL_LENGTH: Length of the column.
            - NUMERIC_PRECISION: Precision of the column for numeric data types.
            - NUMERIC_SCALE: Scale of the column for numeric data types.
            - IS_IDENTITY: Whether the column is an identity column.
        primary_key (tuple, optional): Name of the primary key column and constaint name. Defaults to None.
    """
    column_defs = ', '.join([
        f'[{col[0]}] {col[1]}'
        + (f'({col[2]})' if col[1] in ('varchar', 'nvarchar', 'char', 'nchar', 'varbinary') and col[2] is not None and col[2] != -1 else '')  # Include length/precision/scale if applicable
        + (f'(max)' if col[1] in ('varchar', 'nvarchar', 'char', 'nchar', 'varbinary') and col[2] == -1 else '')  # Use 'max' if length is -1
        + (f' IDENTITY(1,1)' if col[5] and col[1].lower() == 'int' else '')  # Add identity property if the data type is 'INT'
        + (' PRIMARY KEY' if col[0] == primary_key else '')  # Add primary key constraint
        for col in columns_metadata
    ])
    column_defs = f'[ArchiveKey] int, {column_defs}'
    create_query = f"CREATE TABLE [{table_name}] ({column_defs})"
    dest_cursor.execute(create_query)
    print(f"Table '{table_name}' created with query: {create_query}")

    # Store rollback information under the current date
    rollback_info.setdefault(current_date, []).append({
        'table_name': table_name,
        'action': 'drop_table',
        'columns_metadata': columns_metadata,
        'primary_key': primary_key
    })


def get_primary_key(cursor, table_name):
    """
    Retrieve the primary key column and constraint name for a table.

    Args:
        cursor: Database cursor object.
        table_name (str): Name of the table.

    Returns:
        tuple: (primary_key_column_name, constraint_name). Returns (None, None) if no primary key exists.
    """
    cursor.execute(f"SELECT COLUMN_NAME, CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{table_name}' AND CONSTRAINT_NAME LIKE 'PK%'")
    primary_key = cursor.fetchone()
    return primary_key if primary_key else (None, None)


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)


def get_table_constraints(cursor,table_name):
    """
    Retrives the table constraints
    Argv:
        table_name (str): Name of the table to archive.
    """
    cursor.execute(f"SELECT TABLE_NAME, CONSTRAINT_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS WHERE TABLE_NAME = '{table_name}'")
    return {row.TABLE_NAME: row.CONSTRAINT_NAME for row in cursor}

def get_constraint_conditions(cursor, table, constraint_name):
    cursor.execute(f"SELECT * FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE WHERE TABLE_NAME = '{table}' AND CONSTRAINT_NAME = '{constraint_name}'")
    return cursor.fetchall()


def punch_audit_log(db_cursor, archive_key, object_name, object_type, action_type, query_text, row_count):
    """
    This function insert log into audir table of destination DB

    Args:
        db_cursor(objet): datbase cursor object
        archive_key(int): Unique archive key
        object_name(str): Database object name
        object_name(str): Database object type name
        action_type(str): DML action insert/drop 
        query_text(str): SQL query 
        row_count(int): impacted row count

    """
    # Audit log
    insert_query = f'INSERT INTO [ArchiveAudit] ([ArchiveId], [ObjectName], [ObjectType], [ArchiveAction], [ObjectQuery], [ImpactedRowCount], [DateInserted]) VALUES (?,?,?,?,?,?,?)'
    row_values = [archive_key, object_name, object_type, action_type,query_text,row_count,datetime.now()]
    db_cursor.execute(insert_query, row_values)
    db_cursor.commit()
    return()


def compare_and_apply_constraints(archive_cursor, source_cursor, target_cursor, archive_key, table_name):
    """
    Compares the constrainst between source and target database and applied updated constraints on target DB.

    Args:
        source_cursor: Cursor object for the source database.
        dest_cursor: Cursor object for the destination database.
        archive_key (int): is global unique key for each archive activity
        table_name (str): Name of the table.
"""
    # Retrieve table constraints from source and target databases
    source_constraints = get_table_constraints(source_cursor, table_name)
    target_constraints = get_table_constraints(target_cursor, table_name)

    # Compare constraints and apply new constraints in target database
    for table, constraint in source_constraints.items():
        if table in target_constraints:
            if source_constraints[table] != target_constraints[table]:
                # Generate SQL statement to add new constraint
                new_constraint_sql = f"ALTER TABLE {table} ADD CONSTRAINT {source_constraints[table]}"

                # Try executing SQL statement in target database
                try:
                    target_cursor.execute(new_constraint_sql)
                    target_cursor.commit()
                    punch_audit_log(db_cursor=archive_cursor, archive_key=archive_key, object_name=table, object_type='table', action_type='alter constaint', query_text=new_constraint_sql, row_count=0)
                    print(f"Added new constraint {source_constraints[table]} to table {table}")
                except Exception as e:
                    # If unable to apply constraint, log the error
                    punch_audit_log(db_cursor=archive_cursor, archive_key=archive_key, object_name=table, object_type='table', action_type='error', query_text=new_constraint_sql, row_count=0)
                    print(f"Unable to apply constraint {source_constraints[table]} to table {table}. Error: {e}")
        else:
            print(f"Table {table} exists in source but not in target database")

        # Check if the constraints have the same name but different conditions
        if table in target_constraints and source_constraints[table] == target_constraints[table]:
            source_conditions = get_constraint_conditions(source_cursor, table, source_constraints[table])
            target_conditions = get_constraint_conditions(target_cursor, table, target_constraints[table])

            if source_conditions != target_conditions:
                # Drop existing constraint and recreate with new conditions
                drop_constraint_sql = f"ALTER TABLE {table} DROP CONSTRAINT {target_constraints[table]}"
                recreate_constraint_sql = f"ALTER TABLE {table} ADD CONSTRAINT {source_constraints[table]}"

                try:
                    target_cursor.execute(drop_constraint_sql)
                    target_cursor.execute(recreate_constraint_sql)
                    target_cursor.commit()
                    punch_audit_log(db_cursor=archive_cursor, archive_key=archive_key, object_name=table, object_type='table', action_type='alter', query_text=f"{drop_constraint_sql}; {recreate_constraint_sql}", row_count=0)
                    print(f"Dropped and recreated constraint {source_constraints[table]} for table {table}")
                except Exception as e:
                    # If unable to drop and recreate constraint, log the error
                    punch_audit_log(db_cursor=archive_cursor, archive_key=archive_key, object_name=table, object_type='table', action_type='error', query_text=f"{drop_constraint_sql}; {recreate_constraint_sql}", row_count=0)
                    print(f"Unable to drop and recreate constraint {source_constraints[table]} for table {table}. Error: {e}")
    return()


# Function to archive data from source to destination
def archive_table_data(archive_cursor, source_cursor, dest_cursor, table_name, archive_key,lst_source_tables, lst_dest_tables, is_validation):
    """
    Archive data from a table in the source database to the destination database. 
    if table already exists in destination then only appends all rows with autogenrated primary key else first create table

    Args:
        archive_cursor: Cursor for archive db
        source_cursor: Cursor object for the source database.
        dest_cursor: Cursor object for the destination database.
        table_name (str): Name of the table to archive.
        archive_key (int): is global unique key for each archive activity
        lst_source_tables(List): list of table in source database
        lst_dest_tables(List): List of tables in destination database
        is_validation (boolean): is to validate if archive is not duplicate
    """
    # check if table exists in source DB
    if table_name not in lst_source_tables:
        logger.warning(f"Table '{table_name}' does not exist in the source database.")
        return True # Passing true for validation 
    columns_metadata = get_columns_metadata(source_cursor, table_name)
    primary_key = get_primary_key(source_cursor, table_name)

    if table_name not in lst_dest_tables:
        # if its a archive validation call and event table is not exists in destination then it's not a duplicate archive 
        # and no need to  to test duplicate archive so returning validation as True 
        # if is_validation: #-----------uncomment later
        #     return True # ------------uncomment later
        # # Create table in destination database if it doesn't exist
        create_table(dest_cursor, table_name, columns_metadata, primary_key=primary_key)
        # Adding a unique constraint to avoid duplicate archive 
        if table_name.lower() == non_drop_tables[0].lower():
            create_constraint_query = f"""
            ALTER TABLE {non_drop_tables[0]}
            ADD CONSTRAINT unique_combination UNIQUE (CreatedDate);
            """
            dest_cursor.execute(create_constraint_query)
            dest_cursor.commit()
    else:
        # if table already exist in destination then compare the differance in table constaint and use latest constraint from source DB
        if table_name.lower() != non_drop_tables[0].lower():
            compare_and_apply_constraints(archive_cursor,source_cursor, dest_cursor, archive_key, table_name)

    source_cursor.execute(f"SELECT * FROM [{table_name}]")  # Enclose table name in square brackets
    insert_columns = [f'[{col[0]}]' for col in columns_metadata if col[5] != 1] # col[5] means identity; skipping identity as its auto increment
    insert_columns.insert(0,'[ArchiveKey]')

    # Prepare insert query
    insert_query  = f"INSERT INTO [{table_name}] ({', '.join(insert_columns)}) VALUES ({', '.join(['?' for _ in insert_columns])})"
    #logger.debug(f"Insert query for table '{table_name}': {insert_query}")

    # Retrieve source data and insert into destination
    # Get the index of the identity column
    identity_column_index = next((i for i, col in enumerate(columns_metadata) if col[5] == 1), None)

    try:
        IntCount = 1
        for row in source_cursor:
            # Skip the identity column value from the row values
            row_values = [value for i, value in enumerate(row) if i != identity_column_index]
            row_values.insert(0,archive_key)
            # below line  is for handling error:  ('HYC00', '[HYC00] [Microsoft][ODBC SQL Server Driver]Optional feature not implemented (0) (SQLBindParameter)')
           # row_values = tuple(str(val) if isinstance(val, (dt.date, dt.datetime)) else val for val in row_values)
            
            #col_names = [col[0] for i, col in enumerate(columns_metadata) if i != identity_column_index]
            # Insert the row into the destination table
            dest_cursor.execute(insert_query, row_values)
            #logger.debug(f"Inserted row into '{table_name}': {row_values}")

            # Store rollback information under the current date
            # rollback_info.setdefault(current_date, []).append({
            #     'table_name': table_name,
            #     'action': 'delete_row',
            #     'column_names': insert_columns,
            #     'row_values': row_values
            # })
            IntCount = IntCount + 1
        # Audit log
        punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=table_name, object_type='table', action_type='insert',query_text='',row_count=IntCount)
    except Exception as e:
        # if Error in rows insertion in Event table then its a duplicate archive, returning False as validation failed
        if is_validation:
            dest_cursor.rollback()
            return False
        else:
            raise RuntimeError(f"Error while inserting data into table {table_name}: {e}")
    # if all rows successfully inserted in Event table then its not duplicate archive, thuse rollbak insert with dummy archive id. 
    if is_validation:
        return True


def archive_view(archive_cursor, source_cursor, dest_cursor, view_name, archive_key):
    """
    Archive a database view from the source to the destination database.

    Args:
        source_cursor: Cursor object for the source database.
        dest_cursor: Cursor object for the destination database.
        view_name (str): Name of the view to be archived.
        archive_key (int): is global unique key for each archive activity
    """
    # Check if the view already exists in the destination database
    dest_cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_NAME = '{view_name}'")
    view_exists = dest_cursor.fetchone()[0]

    if view_exists:
        # Retrieve existing view definition from the destination database
        dest_cursor.execute(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{view_name}'))")
        existing_view_definition = dest_cursor.fetchone()[0]

        # Store existing view create statement in rollback_info
        rollback_info.setdefault('views', []).append({'action': 'old_object_overwritten', 'view_name': view_name, 'view_definition': existing_view_definition})

    # Retrieve new view definition from the source database
    source_cursor.execute(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{view_name}'))")
    new_view_definition = source_cursor.fetchone()[0]

    # Store new view create statement in rollback_info
    rollback_info.setdefault('views', []).append({'action': 'create_view', 'view_name': view_name, 'view_definition': new_view_definition})

    # Recreate the view in the destination database
    dest_cursor.execute(f"CREATE OR ALTER VIEW {view_name} AS {new_view_definition}")
    # Audit log
    punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=view_name, object_type='db_view', action_type='recreate',query_text=existing_view_definition,row_count=0)
    
    print(f"View '{view_name}' recreated in destination database.")

def archive_functions(archive_cursor, source_cursor, dest_cursor, function_name, archive_key):
    """
    Archive a database function from the source to the destination database.

    Args:
        source_cursor: Cursor object for the source database.
        dest_cursor: Cursor object for the destination database.
        function_name (str): Name of the function to be archived.
        archive_key (int): is global unique key for each archive activity
    """
    # Check if the function already exists in the destination database
    dest_cursor.execute(f"SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_NAME = '{function_name}' AND ROUTINE_TYPE = 'FUNCTION'")
    function_exists = dest_cursor.fetchone()[0]
    existing_function_definition = ''
    if function_exists:
        # Retrieve existing function definition from the destination database
        dest_cursor.execute(f"SELECT OBJECT_DEFINITION(OBJECT_ID('{function_name}'))")
        existing_function_definition = dest_cursor.fetchone()[0]

        # Store existing function create statement in rollback_info
        # rollback_info.setdefault('functions', []).append({'action': 'old_object_overwritten', 'function_name': function_name, 'function_definition': existing_function_definition})

    # Retrieve new function definition from the source database
    source_cursor.execute(f"SELECT OBJECT_DEFINITION(SELECT object_id FROM sys.objects WHERE name = '{function_name}')")
    new_function_definition = source_cursor.fetchone()[0]

    # Store new function create statement in rollback_info
    rollback_info.setdefault('functions', []).append({'action': 'create_function', 'function_name': function_name, 'function_definition': new_function_definition})

    # Recreate the function in the destination database
    dest_cursor.execute(new_function_definition)
    # Audit log
    punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=function_name, object_type='function', action_type='recreate',query_text=existing_function_definition,row_count=0)
    print(f"Function '{function_name}' recreated in destination database.")


def archive_function_and_view(archive_cursor, source_cursor, dest_cursor, archive_key):
    """
    Archive functions and views from the source to the destination database.

    Args:
        source_cursor: Cursor object for the source database.
        dest_cursor: Cursor object for the destination database.
        archive_key (int): is global unique key for each archive activity
    """
    # Get all function names from the source database
    source_cursor.execute("SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION'")
    functions = [row[0] for row in source_cursor.fetchall()]

    # Filter out table valued functions
    source_cursor.execute("SELECT name FROM sys.objects WHERE type IN ('TF', 'IF')")
    TV_functions = [row[0] for row in source_cursor.fetchall()]
    functions = [f for f in functions if f not in TV_functions]

    # Get all view names from the source database
    source_cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS")
    views = [row[0] for row in source_cursor.fetchall()]

    # Archive each function
    for function_name in functions:
        archive_functions(archive_cursor, source_cursor, dest_cursor, function_name, archive_key)

    # Archive each view
    for view_name in views:
        archive_view(archive_cursor, source_cursor, dest_cursor, view_name, archive_key)
    return()


def clear_database(archive_cursor, db_conn, lst_table, archive_key):
    """
    Clear all tables, functions, and views from a SQL Server database.

    Args:
        db_conn (str): Connection for the SQL Server database.
        lst_table(List): List of tables in database
        archive_key(int): Archive instance key
    """
    try:
        cursor = db_conn.cursor()

        # Drop all tables
        # cursor.execute("EXEC sp_MSforeachtable 'DROP TABLE ?'")
        # conn.commit()
        for table in lst_table:
            # if table.lower() not in non_drop_tables:
            cursor.execute(f"DROP TABLE {table}")
            # Audit log
            punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=table, object_type='table', action_type='drop',query_text='',row_count=0)
        db_conn.commit()
        print(f"All tables dropped successfully.")

        # Drop all functions
        cursor.execute("SELECT ROUTINE_NAME FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION'")
        functions = [row[0] for row in cursor.fetchall()]
        for function_name in functions:
            cursor.execute(f"DROP FUNCTION {function_name}")
            # Audit log
            punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=function_name, object_type='function', action_type='drop',query_text='',row_count=0)
            print(f"{function_name} function dropped successfully.")
        db_conn.commit()
        print(f"All functions dropped successfully.")

        # Drop all views
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.VIEWS")
        views = [row[0] for row in cursor.fetchall()]
        for view_name in views:
            cursor.execute(f"DROP VIEW {view_name}")
            print(f"{view_name} view dropped successfully.")
            # Audit log
            punch_audit_log(db_cursor=archive_cursor,archive_key=archive_key, object_name=view_name, object_type='db_view', action_type='drop',query_text='',row_count=0)
        db_conn.commit()
        print(f"All views dropped successfully.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")


def archive_database(db_mapping_key):
    """
    Archive the database with rollback functionality.

    Args:
        db_mapping_key (int): Source and Target DB credential row key.
    """
    #Fetching DB details from config
    server = config['Archive']['DB_credential']['server']
    database = config['Archive']['DB_credential']['database']
    username = config['Archive']['DB_credential']['username']
    password = config['Archive']['DB_credential']['password']

    # Connecting to archive database to fetch source and target DB credentials 
    connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
    conn = pyodbc.connect(connection_string)
    archive_cursor = conn.cursor()
    archive_cursor.execute(f"SELECT SourceServerName, SourceDBName, SourceID, SourcePass, ArchiveServerName, ArchiveDBName, ArchiveID, ArchivePass, ValidationTable FROM [dbo].[ArchiveDatabaseMapping] WHERE MappingId = {db_mapping_key}")
    row = archive_cursor.fetchone()

    #Setting validation table 
    non_drop_tables.append(row.ValidationTable)

    # Setting DB credentials
    source_server = row.SourceServerName
    source_database = row.SourceDBName
    source_username = row.SourceID
    source_password = row.SourcePass

    dest_server = row.ArchiveServerName
    dest_database = row.ArchiveDBName
    dest_username = row.ArchiveID
    dest_password = row.ArchivePass

    # Connect to source and destination databases
    if source_username:
        source_connection_string = f'DRIVER=ODBC Driver 17 for SQL Server;SERVER={source_server};DATABASE={source_database};UID={source_username};PWD={source_password}'
    else:
        source_connection_string = f'DRIVER={{SQL Server}};SERVER={source_server};DATABASE={source_database};Trusted_Connection=yes;'
    
    if dest_username:
        dest_connection_string = f'DRIVER=ODBC Driver 17 for SQL Server;SERVER={dest_server};DATABASE={dest_database};UID={dest_username};PWD={dest_password}'
    else:
        # using "DRIVER={{SQL Server}}" drive gives an error -> ('HYC00', '[HYC00] [Microsoft][ODBC SQL Server Driver]Optional feature not implemented (0) (SQLBindParameter)')
        dest_connection_string = f'DRIVER=ODBC Driver 17 for SQL Server;SERVER={dest_server};DATABASE={dest_database};Trusted_Connection=yes;'

    # Conneting to databases
    source_conn = pyodbc.connect(source_connection_string)
    dest_conn = pyodbc.connect(dest_connection_string)
    
    # create_archive_audit_table
    create_archive_audit_table(archive_cursor)

    # Get list of tables in source database
    lst_source_tables = get_tables(source_conn.cursor())

    # Get list of tables in destination database
    lst_dest_tables = get_tables(dest_conn.cursor())

    # Generate archive key
    archive_key = generate_archive_key(archive_cursor, db_mapping_key)

    # Clearing destination database; use if needed
    clear_database(archive_cursor, dest_conn, lst_dest_tables, archive_key)  #uncomment if required
    dest_conn.commit()
    # Validate if archive is not duplicate activity based on event table values
    table_name = non_drop_tables[0]
    is_validation_passed = archive_table_data(archive_cursor, source_conn.cursor(), dest_conn.cursor(), table_name, archive_key, lst_source_tables, lst_dest_tables, is_validation=True)
    # Raising an error if validation is failed
    if not is_validation_passed:
        raise RuntimeError("Validation error data already exists in destination DB please check event table data in destination DB")
    else:
        dest_conn.cursor().commit()

    # Archive each table
    for table in [table for table in lst_source_tables if table.lower() != non_drop_tables[0].lower()]:
        archive_table_data(archive_cursor, source_conn.cursor(), dest_conn.cursor(), table, archive_key, lst_source_tables, lst_dest_tables, is_validation=False)
        dest_conn.commit()

    # Archive view and functions
    archive_function_and_view(archive_cursor, source_conn.cursor(), dest_conn.cursor(),archive_key)
    
    # Close connections
    source_conn.close()
    dest_conn.close()

    # Write rollback information to a JSON file
    # rollback_info_json = json.dumps(rollback_info, indent=4, cls=DateTimeEncoder)

    # with open(rollback_file, 'a') as json_file:
    #     json_file.write(rollback_info_json)


if __name__ == "__main__":
    # Key 1 for cleanliness drive DB
    # parser = argparse.ArgumentParser(description='Script requires a mapping key from table [dbo].[ArchiveDatabaseMapping] to perform archive.')
    # parser.add_argument('mapping_id', type=int, help='The mapping key to fetch the archive candidate database details.')
    # args = parser.parse_args()
    archive_database(db_mapping_key= 2) #args.mapping_id)
    print("Database archived successfully.")
