import json
from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch
import sqlite3

app = Flask(__name__)

# SQLite database setup
def create_connection():
    return sqlite3.connect('logs.db')

conn = create_connection()
cursor = conn.cursor()

# Elasticsearch setup
es = Elasticsearch(['http://127.0.0.1:5602/'])

# # Explicitly create an index with mappings
# es.indices.create(index='logs', ignore=400, body={
#     'mappings': {
#         'properties': {
#             'level': {'type': 'keyword'},
#             'message': {'type': 'text'},
#             'resourceId': {'type': 'keyword'},
#             'timestamp': {'type': 'date'},
#             'traceId': {'type': 'keyword'},
#             'spanId': {'type': 'keyword'},
#             'commit_hash': {'type': 'keyword'},
#             'parentResourceId': {'type': 'keyword'},
#         }
#     }
# })


@app.route('/ingest', methods=['POST'])
def ingest_log():
    data = request.get_json()

    # Log the received JSON data
    print("Received JSON data:")
    print(json.dumps(data, indent=2))  # Pretty-print the JSON data

    # Create a new connection in each thread
    with create_connection() as connection:
        cursor = connection.cursor()
        # Insert log into SQLite database
        cursor.execute('INSERT INTO logs (level, message, resourceId, timestamp, traceId, spanId, commit_hash, parentResourceId) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (data['level'], data['message'], data['resourceId'], data['timestamp'], data['traceId'], data['spanId'], data['commit'], data['metadata']['parentResourceId']))
        connection.commit()

    # Index log in Elasticsearch for efficient search
    es.index(index='logs', body=data)

    return jsonify({'status': 'success'})

@app.route('/query', methods=['GET'])
def query_logs():
    # Extract filters from the query parameters
    filters = {
        'level': request.args.get('level'),
        'message': request.args.get('message'),
        'resourceId': request.args.get('resourceId'),
        'timestamp': request.args.get('timestamp'),
        'traceId': request.args.get('traceId'),
        'spanId': request.args.get('spanId'),
        'commit': request.args.get('commit'),
        'parentResourceId': request.args.get('metadata.parentResourceId')
    }

    # Additional filters for date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Construct the SQL query based on filters
    query = 'SELECT * FROM logs WHERE 1=1'
    for key, value in filters.items():
        if value:
            query += f' AND {key} LIKE ?'
    
    # Add date range filtering
    if start_date:
        query += ' AND timestamp >= ?'
    if end_date:
        query += ' AND timestamp <= ?'

    # Execute the SQLite query with appropriate parameters
    params = [f'%{value}%' for value in filters.values()]
    if start_date:
        params.append(start_date)
    if end_date:
        params.append(end_date)

    cursor.execute(query, params)
    sqlite_logs = cursor.fetchall()

    # Execute the Elasticsearch query
    es_query = {"query": {"bool": {"must": [{"match": {key: value}} for key, value in filters.items() if value]}}}
    es_logs = es.search(index='logs', body=es_query)['hits']['hits']

    # Combine results from SQLite and Elasticsearch
    logs = sqlite_logs + [log['_source'] for log in es_logs]

    return jsonify(logs)

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/favicon.ico")
def favicon():
    return "", 200

if __name__ == '__main__':
    app.run(port=5501)
