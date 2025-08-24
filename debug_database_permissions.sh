#!/bin/bash
# Database Permission Diagnostic Script
# Run this inside your container to check database permissions

echo "=== Database Permission Diagnostic ==="
echo

echo "1. Checking current user:"
whoami
id

echo
echo "2. Checking /data directory:"
ls -la /data/
ls -la /data/db.sqlite3 2>/dev/null || echo "Database file does not exist"

echo
echo "3. Checking directory permissions:"
stat -c "%n %a %U:%G" /data/

echo 
echo "4. Checking if we can write to /data:"
touch /data/test_write.tmp && echo "✓ Can write to /data" || echo "✗ Cannot write to /data"
rm -f /data/test_write.tmp 2>/dev/null

echo
echo "5. Checking database file permissions (if exists):"
if [ -f "/data/db.sqlite3" ]; then
    stat -c "%n %a %U:%G" /data/db.sqlite3
    
    echo
    echo "6. Testing database write access:"
    python -c "
import sqlite3
import os
try:
    conn = sqlite3.connect('/data/db.sqlite3')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS test_table (id INTEGER)')
    cursor.execute('INSERT INTO test_table (id) VALUES (1)')
    conn.commit()
    cursor.execute('DELETE FROM test_table WHERE id = 1')
    conn.commit()
    conn.close()
    print('✓ Database write test successful')
except Exception as e:
    print(f'✗ Database write test failed: {e}')
"
else
    echo "Database file does not exist - this might be the issue!"
fi

echo
echo "7. Checking Docker environment:"
echo "Container ID: $(hostname)"
echo "Django user exists: $(getent passwd django >/dev/null && echo 'Yes' || echo 'No')"

echo
echo "=== Diagnostic Complete ==="
