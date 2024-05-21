import json
import boto3


class DBOperations:
    def __init__(self, db_name):
        self.db_name = db_name
        
    def execute_query(self, query, *args, **kwargs):
        payload = json.dumps({
            'db_name': self.db_name,
            'query_text': query, 
            'query_params': kwargs.get("params", ()),
            'query_type': kwargs.get("query_type", "get_query")
        })
        
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName='arn:aws:lambda:us-east-1:813259119770:function:gxp-service-main-dev-dbConnection',
            InvocationType='RequestResponse',
            Payload=payload
        )
        response_payload = json.load(response['Payload'])
        return json.loads(response_payload.get("body"))

    def raw_query(self, query, commit=True):
        return self.execute_query(query, query_type="raw_query", commit=commit)

    def insert_query(self, tbl_name, record_dict, commit=True):
        values_set = ', '.join(['%s'] * len(record_dict))
        columns = ', '.join(record_dict.keys())
        query = f"INSERT INTO {tbl_name} ({columns}) VALUES ({values_set})"
        params = tuple(record_dict.values())
        return self.execute_query(query, params=params, query_type="insert_query", commit=commit)

    def bulk_insert_query(self, tbl_name, records_list, commit=True):
        columns = ', '.join(records_list[0].keys())
        values_sets = ', '.join([f"({', '.join(['%s'] * len(record))})" for record in records_list])
        params = tuple(value for record in records_list for value in record.values())
        query = f"INSERT INTO {tbl_name} ({columns}) VALUES {values_sets}"
        return self.execute_query(query, params=params, query_type="insert_query", commit=commit)

    def update_query(self, tbl_name, record_dict, condition=None, params=(), commit=True):
        update_values = ', '.join([f"{key}=%s" for key in record_dict.keys()])
        query = f"UPDATE {tbl_name} SET {update_values} "
        if condition:
            query += f" WHERE {condition}"

        params = tuple(record_dict.values()) + params
        return self.execute_query(query, params=params, query_type="update_query", commit=commit)

    def delete_query(self, tbl_name, condition, params, commit=True):
        query = f"DELETE FROM {tbl_name} WHERE {condition}"
        return self.execute_query(query, params=params, query_type="delete_query", commit=commit)

    def select_query(self, tbl_name, columns='*', condition=None, params=(), order_by=None, group_by=None,
                     page_size=None, page_number=1):
        column_names = ', '.join(columns) if isinstance(columns, list) else columns
        count_query = f"SELECT COUNT(*) AS total_count FROM {tbl_name}"  # Query to get total record count
        query = f"SELECT {column_names} FROM {tbl_name}"

        if condition:
            count_query += f" WHERE {condition}"  # Add condition to count query
            query += f" WHERE {condition}"  # Add condition to main query

        if group_by:
            query += f" GROUP BY {group_by} "

        if order_by:
            query += f" ORDER BY {order_by}"

        total_records = self.execute_query(count_query, params=params, query_type="get_query")
        total_records_count = total_records["data"]["total_count"] if total_records["data"] else 0

        if page_size:
            page_size = int(page_size)
            page_number = int(page_number)
            limit = page_size
            offset = (page_number - 1) * page_size
            query += f" LIMIT {limit} OFFSET {offset}"
            total_pages = total_records_count // page_size if total_records_count % page_size == 0 else total_records_count // page_size + 1
        else:
            total_pages = 1

        records = self.execute_query(query, params=params, page_number=page_number, query_type="select_query")

        return {
            "status": records["status"],
            "data": records["data"],
            "message": records["message"],
            "count": total_records_count,
            "page_number": page_number,
            "total_pages": total_pages,
        }

    def get_query(self, tbl_name, columns='*', condition=None, params=(), order_by=None):
        column_names = ', '.join(columns) if isinstance(columns, list) else columns
        query = f"SELECT {column_names} FROM {tbl_name}"

        if condition:
            query += f" WHERE {condition} "

        if order_by:
            query += f" ORDER BY {order_by} "

        return self.execute_query(query, params=params, query_type="get_query")
