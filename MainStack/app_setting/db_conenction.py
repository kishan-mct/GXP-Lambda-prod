import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime, time, timedelta
from decimal import Decimal

# Function to serialize non-serializable objects to JSON
def json_serializer(obj):
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, (timedelta, Decimal)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} is not serializable")


# Function to convert nested lists to tuples
def convert_nested_lists_to_tuples(lst):
    if lst is None:
        return ()
    
    def _convert(item):
        if isinstance(item, list):
            return convert_nested_lists_to_tuples(item)
        return item
    
    return tuple(_convert(item) for item in lst)


# Function to establish PostgreSQL connection
def psycopg_connect(db_host, username, password, db_name, db_port):
    try:
        connection = psycopg2.connect(host=db_host, user=username, password=password, database=db_name, port=db_port, cursor_factory=RealDictCursor)
        print("Connection successful.")
        return connection
    except Exception as e:
        print(f"PgSql Connection execution error: {e}")
        raise ValueError(f"PgSql Connection execution error: {e}")
    

# Lambda function handler
def dbConnection(event, context):
    # Initialize response structure
    sql_result = {
        "status": False,
        "message": "",
        "data": {}
    }
    
    # Extract parameters from the event
    db_name = event['db_name']
    query_text = event['query_text']
    query_type = event['query_type']
    query_params = convert_nested_lists_to_tuples(event['query_params'])
    print("QUERY", query_type, query_text, query_params)
    
    connection = None
    
    try:
        # Establish connection based on database name
        if db_name in ["gxp-dev", "gxp-prod"]:
            connection_params = {
                "gxp-dev": ('backops-dev.c6yfo0g0fjx8.us-east-1.rds.amazonaws.com', 'postgres', '1yaD8oFPjFwnsBLFVe2f', 'gxp_dev', 5432),
                "gxp-prod": ('backops-dev.c6yfo0g0fjx8.us-east-1.rds.amazonaws.com', 'postgres', '1yaD8oFPjFwnsBLFVe2f', 'postgres', 5432)
            }
            host, user, password, db, port = connection_params[db_name]
            connection = psycopg2.connect(host=host, user=user, password=password, database=db, port=port, cursor_factory=RealDictCursor)
        else:
            raise ValueError(f"Invalid database name: {db_name}")
            
        # Execute query and handle different types of queries
        with connection.cursor() as cur:
            if query_params:
                cur.execute(query_text, query_params)
            else:
                cur.execute(query_text)
                
            connection.commit()
            
            if query_type == "select_query" or query_type == "raw_query":
                sql_result["count"] = cur.rowcount
                sql_result["data"] = cur.fetchall()
            elif query_type == "get_query" or query_type == "raw_query_fetchone":
                sql_result["data"] = cur.fetchone()
           
            
            sql_result["status"] = True
            
    except Exception as e:
        print("MYSQL ERROR: ", str(e))
        sql_result["message"] = f"{str(e)} : database query error"
    finally:
        # Close connection and return response
        if connection:
            connection.close()
        print("QUERY RESULT", sql_result)
        return {
            'statusCode': 200,
            'body': json.dumps(sql_result, default=json_serializer)
        }
