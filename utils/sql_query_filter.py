def get_condition_and_params(filters_query_params):
    condition = "1=1"
    params = []

    for field, value in filters_query_params.items():
        if not value:
            continue
        
        filter_type = 'exact'
        if field.endswith('__startswith'):
            filter_type = 'startswith'
            field = field[:-12]
        elif field.endswith('__endswith'):
            filter_type = 'endswith'
            field = field[:-10]
        elif field.endswith('__contains'):
            filter_type = 'contains'
            field = field[:-10]
        elif field.endswith('__iexact'):
            filter_type = 'iexact'
            field = field[:-8]
        elif field.endswith('__icontains'):
            filter_type = 'icontains'
            field = field[:-11]
        elif field.endswith('__iendswith'):
            filter_type = 'iendswith'
            field = field[:-11]
        elif field.endswith('__istartswith'):
            filter_type = 'istartswith'
            field = field[:-13]
        elif field.endswith('__in'):
            filter_type = 'in'
            field = field[:-4]

        if '__' in field:
            field_parts = field.split('__')
            sql_field = '->>'.join(field_parts)
        else:
            sql_field = field

        # Check if the field is textual before applying LOWER()
        if filter_type in ('startswith', 'endswith', 'contains', 'icontains', 'iendswith', 'istartswith'):
            condition += f" AND LOWER({sql_field}::text) LIKE LOWER(%s)"
            params.append(f"%{value}%")
        elif filter_type == 'iexact':
            condition += f" AND LOWER({sql_field}::text) = LOWER(%s)"
            params.append(value)
        elif filter_type == 'in':
            placeholders = ','.join(['%s'] * len(value.split(',')))
            condition += f" AND LOWER({sql_field}::text) IN ({placeholders})"
            params.extend([v.lower() for v in value.split(',')])
        else:
            condition += f" AND {sql_field}::text = %s"
            params.append(value)

    return condition, tuple(params)