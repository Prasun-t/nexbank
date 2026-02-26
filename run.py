from app import app, init_db
if __name__ == '__main__':
    init_db()
    print("NexBank starting at http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
