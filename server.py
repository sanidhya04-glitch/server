from flask import Flask, request, jsonify, render_template_string
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)

# Database initialization
def init_db():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            rfid_id TEXT PRIMARY KEY,
            student_name TEXT NOT NULL,
            class TEXT,
            roll_number TEXT
        )
    ''')
    
    # Create books table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_name TEXT NOT NULL,
            author TEXT,
            isbn TEXT
        )
    ''')
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfid_id TEXT,
            book_id INTEGER,
            issue_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            return_date DATETIME,
            returned BOOLEAN DEFAULT 0,
            FOREIGN KEY (rfid_id) REFERENCES students (rfid_id),
            FOREIGN KEY (book_id) REFERENCES books (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Add sample student data (for testing)
def add_sample_data():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # Sample students
    students = [
        ('123456789', 'John Doe', '10th Grade', '1001'),
        ('987654321', 'Jane Smith', '9th Grade', '0901'),
        ('456789123', 'Bob Johnson', '11th Grade', '1101')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO students (rfid_id, student_name, class, roll_number)
        VALUES (?, ?, ?, ?)
    ''', students)
    
    conn.commit()
    conn.close()

# HTML template for the web interface
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RFID Library Management System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1, h2 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            width: 100%;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #007bff;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .section {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .return-btn {
            background-color: #28a745;
        }
        .return-btn:hover {
            background-color: #218838;
        }
        .warning {
            color: #dc3545;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>RFID Library Management System</h1>
        
        <!-- Book Issue Section -->
        <div class="section">
            <h2>Issue Book</h2>
            <form id="issueForm">
                <div class="form-group">
                    <label for="rfid">RFID ID:</label>
                    <input type="text" id="rfid" name="rfid" required>
                </div>
                <div class="form-group">
                    <label for="bookName">Book Name:</label>
                    <input type="text" id="bookName" name="bookName" required>
                </div>
                <div class="form-group">
                    <label for="author">Author:</label>
                    <input type="text" id="author" name="author">
                </div>
                <div class="form-group">
                    <label for="isbn">ISBN:</label>
                    <input type="text" id="isbn" name="isbn">
                </div>
                <button type="submit">Issue Book</button>
            </form>
        </div>
        
        <!-- Current Transactions -->
        <div class="section">
            <h2>Current Book Issues</h2>
            <table id="transactionsTable">
                <thead>
                    <tr>
                        <th>Student Name</th>
                        <th>Class</th>
                        <th>Book Name</th>
                        <th>Issue Date</th>
                        <th>Return Date</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for transaction in transactions %}
                    <tr>
                        <td>{{ transaction.student_name }}</td>
                        <td>{{ transaction.class }}</td>
                        <td>{{ transaction.book_name }}</td>
                        <td>{{ transaction.issue_date }}</td>
                        <td>{{ transaction.return_date }}</td>
                        <td class="{{ 'warning' if transaction.overdue else '' }}">
                            {{ 'Overdue' if transaction.overdue else 'Active' }}
                        </td>
                        <td>
                            <button class="return-btn" onclick="returnBook({{ transaction.id }})">Return</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- Student Information -->
        <div class="section">
            <h2>Student Information</h2>
            <form id="studentForm">
                <div class="form-group">
                    <label for="searchRfid">Search RFID ID:</label>
                    <input type="text" id="searchRfid" name="searchRfid" required>
                </div>
                <button type="button" onclick="getStudentInfo()">Get Student Info</button>
            </form>
            <div id="studentInfo"></div>
        </div>
    </div>

    <script>
        // Handle form submission for issuing books
        document.getElementById('issueForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = {
                rfid_id: formData.get('rfid'),
                book_name: formData.get('bookName'),
                author: formData.get('author'),
                isbn: formData.get('isbn')
            };
            
            fetch('/api/issue_book', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                if (data.success) {
                    location.reload(); // Refresh page to show updated data
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while issuing the book.');
            });
        });
        
        // Return a book
        function returnBook(transactionId) {
            if (confirm('Are you sure you want to mark this book as returned?')) {
                fetch(`/api/return_book/${transactionId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) {
                        location.reload(); // Refresh page to show updated data
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while returning the book.');
                });
            }
        }
        
        // Get student information
        function getStudentInfo() {
            const rfid = document.getElementById('searchRfid').value;
            if (!rfid) {
                alert('Please enter an RFID ID');
                return;
            }
            
            fetch(`/api/student/${rfid}`)
            .then(response => response.json())
            .then(data => {
                const infoDiv = document.getElementById('studentInfo');
                if (data.success) {
                    infoDiv.innerHTML = `
                        <h3>Student Details</h3>
                        <p><strong>Name:</strong> ${data.student.student_name}</p>
                        <p><strong>Class:</strong> ${data.student.class}</p>
                        <p><strong>Roll Number:</strong> ${data.student.roll_number}</p>
                    `;
                } else {
                    infoDiv.innerHTML = `<p style="color: red;">${data.message}</p>`;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('studentInfo').innerHTML = '<p style="color: red;">Error fetching student information.</p>';
            });
        }
    </script>
</body>
</html>
'''

# Routes

@app.route('/')
def index():
    """Main web interface"""
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    
    # Get current active transactions
    cursor.execute('''
        SELECT t.id, s.student_name, s.class, b.book_name, 
               t.issue_date, t.return_date,
               CASE 
                   WHEN t.return_date < datetime('now') THEN 1 
                   ELSE 0 
               END as overdue
        FROM transactions t
        JOIN students s ON t.rfid_id = s.rfid_id
        JOIN books b ON t.book_id = b.id
        WHERE t.returned = 0
        ORDER BY t.issue_date DESC
    ''')
    
    transactions = []
    for row in cursor.fetchall():
        transactions.append({
            'id': row[0],
            'student_name': row[1],
            'class': row[2],
            'book_name': row[3],
            'issue_date': row[4],
            'return_date': row[5],
            'overdue': bool(row[6])
        })
    
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, transactions=transactions)

@app.route('/api/issue_book', methods=['POST'])
def issue_book():
    """API endpoint for issuing books via ESP8266 or web interface"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        rfid_id = data.get('rfid_id')
        book_name = data.get('book_name')
        author = data.get('author', '')
        isbn = data.get('isbn', '')
        
        if not rfid_id or not book_name:
            return jsonify({'success': False, 'message': 'RFID ID and Book Name are required'}), 400
        
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        # Check if student exists
        cursor.execute('SELECT rfid_id FROM students WHERE rfid_id = ?', (rfid_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        # Check if book already exists
        cursor.execute('SELECT id FROM books WHERE book_name = ? AND author = ?', (book_name, author))
        book_result = cursor.fetchone()
        
        if book_result:
            book_id = book_result[0]
        else:
            # Add new book
            cursor.execute('''
                INSERT INTO books (book_name, author, isbn)
                VALUES (?, ?, ?)
            ''', (book_name, author, isbn))
            book_id = cursor.lastrowid
        
        # Calculate return date (14 days from today)
        issue_date = datetime.now()
        return_date = issue_date + timedelta(days=14)
        
        # Insert transaction
        cursor.execute('''
            INSERT INTO transactions (rfid_id, book_id, issue_date, return_date)
            VALUES (?, ?, ?, ?)
        ''', (rfid_id, book_id, issue_date.strftime('%Y-%m-%d %H:%M:%S'), 
              return_date.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Book "{book_name}" issued successfully!',
            'return_date': return_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/return_book/<int:transaction_id>', methods=['POST'])
def return_book(transaction_id):
    """Mark a book as returned"""
    try:
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE transactions 
            SET returned = 1, return_date = datetime('now')
            WHERE id = ?
        ''', (transaction_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Book marked as returned successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/student/<rfid_id>')
def get_student_info(rfid_id):
    """Get student information by RFID ID"""
    try:
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rfid_id, student_name, class, roll_number
            FROM students
            WHERE rfid_id = ?
        ''', (rfid_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            student_info = {
                'rfid_id': result[0],
                'student_name': result[1],
                'class': result[2],
                'roll_number': result[3]
            }
            return jsonify({'success': True, 'student': student_info})
        else:
            return jsonify({'success': False, 'message': 'Student not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/transactions')
def get_transactions():
    """Get all transactions (active and returned)"""
    try:
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.id, s.student_name, s.class, b.book_name, 
                   t.issue_date, t.return_date, t.returned
            FROM transactions t
            JOIN students s ON t.rfid_id = s.rfid_id
            JOIN books b ON t.book_id = b.id
            ORDER BY t.issue_date DESC
        ''')
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({
                'id': row[0],
                'student_name': row[1],
                'class': row[2],
                'book_name': row[3],
                'issue_date': row[4],
                'return_date': row[5],
                'returned': bool(row[6])
            })
        
        conn.close()
        return jsonify({'success': True, 'transactions': transactions})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/api/esp/issue', methods=['POST'])
def esp_issue_book():
    """Endpoint specifically for ESP8266 devices to issue books"""
    try:
        # For ESP8266, you might send raw form data or JSON
        if request.is_json:
            data = request.get_json()
        else:
            data = {
                'rfid_id': request.form.get('rfid_id'),
                'book_name': request.form.get('book_name'),
                'author': request.form.get('author', ''),
                'isbn': request.form.get('isbn', '')
            }
        
        if not data['rfid_id'] or not data['book_name']:
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        
        # Check if student exists
        cursor.execute('SELECT rfid_id FROM students WHERE rfid_id = ?', (data['rfid_id'],))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'message': 'Student not found'}), 404
        
        # Check/add book
        cursor.execute('SELECT id FROM books WHERE book_name = ?', (data['book_name'],))
        book_result = cursor.fetchone()
        
        if book_result:
            book_id = book_result[0]
        else:
            cursor.execute('''
                INSERT INTO books (book_name, author, isbn)
                VALUES (?, ?, ?)
            ''', (data['book_name'], data['author'], data['isbn']))
            book_id = cursor.lastrowid
        
        # Calculate return date
        issue_date = datetime.now()
        return_date = issue_date + timedelta(days=14)
        
        # Insert transaction
        cursor.execute('''
            INSERT INTO transactions (rfid_id, book_id, issue_date, return_date)
            VALUES (?, ?, ?, ?)
        ''', (data['rfid_id'], book_id, 
              issue_date.strftime('%Y-%m-%d %H:%M:%S'),
              return_date.strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': 'Book issued successfully',
            'return_date': return_date.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    add_sample_data()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
