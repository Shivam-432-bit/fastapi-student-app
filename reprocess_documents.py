#!/usr/bin/env python3
"""
Script to reprocess all completed documents and regenerate ChromaDB embeddings
"""
import json
import sys
import os
import time

sys.path.insert(0, '/Users/mobcoderid-228/Desktop/FastAPI')

from student.doc_summarizer.endpoint import process_document_task

# Load the documents to process
with open('/tmp/docs_to_process.json', 'r') as f:
    docs = json.load(f)

print(f'🔄 Starting reprocessing of {len(docs)} documents...\n')

success_count = 0
error_count = 0

for idx, doc in enumerate(docs, 1):
    doc_id = doc['id']
    filename = doc['filename']
    file_path = doc['file_path']
    content_type = doc['content_type']
    
    print(f'[{idx}/{len(docs)}] ⏳ Processing Doc ID {doc_id}: {filename}')
    
    try:
        if not os.path.exists(file_path):
            print(f'         ⚠️  File not found: {file_path}\n')
            error_count += 1
            continue
            
        start = time.time()
        process_document_task(doc_id, file_path, content_type)
        elapsed = time.time() - start
        
        print(f'         ✅ Completed in {elapsed:.1f}s\n')
        success_count += 1
        
    except Exception as e:
        print(f'         ❌ Error: {e}\n')
        error_count += 1

print(f'🎉 Reprocessing complete!')
print(f'   ✅ Success: {success_count}')
print(f'   ❌ Errors: {error_count}')
