from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import random
import string
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bankingsecretkey2024xyz'
DATABASE = os.path.join(os.path.dirname(__file__), 'bank.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            account_type TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            user_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            recipient_account TEXT,
            balance_after REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        );
    ''')
    db.commit()
    db.close()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_account_number():
    db = get_db()
    while True:
        num = 'ACC' + ''.join(random.choices(string.digits, k=10))
        row = db.execute('SELECT id FROM accounts WHERE account_number = ?', (num,)).fetchone()
        if not row:
            return num


@app.template_filter('dateformat')
def dateformat(value, fmt='%b %d, %Y'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            from datetime import datetime
            value = datetime.fromisoformat(value)
        except:
            return value
    return value.strftime(fmt)

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        account_type = request.form.get('account_type', 'savings')
        errors = []
        if not full_name: errors.append('Full name is required.')
        if not email or '@' not in email: errors.append('Valid email is required.')
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            errors.append('Email already registered.')
        if len(password) < 6: errors.append('Password must be at least 6 characters.')
        if password != confirm: errors.append('Passwords do not match.')
        if errors:
            for e in errors: flash(e, 'danger')
            return render_template('register.html', form=request.form)
        pw_hash = generate_password_hash(password)
        db.execute('INSERT INTO users (full_name, email, phone, password_hash) VALUES (?,?,?,?)',
                   (full_name, email, phone, pw_hash))
        db.commit()
        user_id = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()['id']
        acc_num = generate_account_number()
        db.execute('INSERT INTO accounts (account_number, account_type, balance, user_id) VALUES (?,?,0,?)',
                   (acc_num, account_type, user_id))
        db.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form={})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        db = get_db()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            flash(f"Welcome back, {user['full_name']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accounts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    total_balance = sum(a['balance'] for a in accounts)
    recent_txns = db.execute('''
        SELECT t.*, a.account_number as acct_num FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.user_id=?
        ORDER BY t.created_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()
    return render_template('dashboard.html', user=user, accounts=accounts,
                           total_balance=total_balance, recent_txns=recent_txns)

@app.route('/accounts')
@login_required
def accounts():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    return render_template('accounts.html', user=user, accounts=accts)

@app.route('/accounts/add', methods=['POST'])
@login_required
def add_account():
    db = get_db()
    account_type = request.form.get('account_type', 'savings')
    count = db.execute('SELECT COUNT(*) FROM accounts WHERE user_id=?', (session['user_id'],)).fetchone()[0]
    if count >= 5:
        flash('Maximum of 5 accounts allowed.', 'warning')
        return redirect(url_for('accounts'))
    acc_num = generate_account_number()
    db.execute('INSERT INTO accounts (account_number, account_type, balance, user_id) VALUES (?,?,0,?)',
               (acc_num, account_type, session['user_id']))
    db.commit()
    flash(f'New {account_type} account created successfully!', 'success')
    return redirect(url_for('accounts'))

@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    db = get_db()
    account = db.execute('SELECT * FROM accounts WHERE id=? AND user_id=?',
                         (account_id, session['user_id'])).fetchone()
    if not account:
        flash('Account not found.', 'danger')
        return redirect(url_for('accounts'))
    if account['balance'] > 0:
        flash('Cannot delete account with remaining balance.', 'danger')
        return redirect(url_for('accounts'))
    count = db.execute('SELECT COUNT(*) FROM accounts WHERE user_id=?', (session['user_id'],)).fetchone()[0]
    if count <= 1:
        flash('You must keep at least one account.', 'danger')
        return redirect(url_for('accounts'))
    db.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    db.commit()
    flash('Account deleted successfully.', 'success')
    return redirect(url_for('accounts'))

@app.route('/transactions')
@login_required
def transactions():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    account_filter = request.args.get('account_id', type=int)
    type_filter = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    where = ['a.user_id = ?']
    params = [session['user_id']]
    if account_filter:
        where.append('t.account_id = ?')
        params.append(account_filter)
    if type_filter:
        where.append('t.type = ?')
        params.append(type_filter)
    where_str = ' AND '.join(where)
    total = db.execute(f'SELECT COUNT(*) FROM transactions t JOIN accounts a ON t.account_id=a.id WHERE {where_str}',
                       params).fetchone()[0]
    offset = (page - 1) * per_page
    txns_raw = db.execute(f'''
        SELECT t.*, a.account_number as acct_num FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE {where_str}
        ORDER BY t.created_at DESC
        LIMIT ? OFFSET ?
    ''', params + [per_page, offset]).fetchall()
    total_pages = max(1, (total + per_page - 1) // per_page)

    class Pagination:
        def __init__(self):
            self.items = txns_raw
            self.total = total
            self.page = page
            self.pages = total_pages
            self.has_prev = page > 1
            self.has_next = page < total_pages
            self.prev_num = page - 1
            self.next_num = page + 1
        def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
            last = 0
            for num in range(1, self.pages + 1):
                if (num <= left_edge or
                    (self.page - left_current - 1 < num < self.page + right_current) or
                    num > self.pages - right_edge):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    return render_template('transactions.html', user=user, txns=Pagination(),
                           accounts=accts, account_filter=account_filter, type_filter=type_filter)

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        amount = request.form.get('amount', type=float)
        description = request.form.get('description', 'Deposit').strip() or 'Deposit'
        account = db.execute('SELECT * FROM accounts WHERE id=? AND user_id=?',
                             (account_id, session['user_id'])).fetchone()
        if not account: flash('Invalid account.', 'danger'); return redirect(url_for('deposit'))
        if not amount or amount <= 0: flash('Amount must be greater than 0.', 'danger'); return redirect(url_for('deposit'))
        if amount > 1_000_000: flash('Maximum single deposit is $1,000,000.', 'danger'); return redirect(url_for('deposit'))
        new_balance = account['balance'] + amount
        db.execute('UPDATE accounts SET balance=? WHERE id=?', (new_balance, account_id))
        db.execute('INSERT INTO transactions (account_id, type, amount, description, balance_after) VALUES (?,?,?,?,?)',
                   (account_id, 'deposit', amount, description, new_balance))
        db.commit()
        flash(f'${amount:,.2f} deposited successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('deposit.html', user=user, accounts=accts)

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        account_id = request.form.get('account_id', type=int)
        amount = request.form.get('amount', type=float)
        description = request.form.get('description', 'Withdrawal').strip() or 'Withdrawal'
        account = db.execute('SELECT * FROM accounts WHERE id=? AND user_id=?',
                             (account_id, session['user_id'])).fetchone()
        if not account: flash('Invalid account.', 'danger'); return redirect(url_for('withdraw'))
        if not amount or amount <= 0: flash('Amount must be greater than 0.', 'danger'); return redirect(url_for('withdraw'))
        if amount > account['balance']: flash('Insufficient funds.', 'danger'); return redirect(url_for('withdraw'))
        new_balance = account['balance'] - amount
        db.execute('UPDATE accounts SET balance=? WHERE id=?', (new_balance, account_id))
        db.execute('INSERT INTO transactions (account_id, type, amount, description, balance_after) VALUES (?,?,?,?,?)',
                   (account_id, 'withdraw', amount, description, new_balance))
        db.commit()
        flash(f'${amount:,.2f} withdrawn successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('withdraw.html', user=user, accounts=accts)

@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        from_id = request.form.get('from_account_id', type=int)
        recipient_number = request.form.get('recipient_account', '').strip()
        amount = request.form.get('amount', type=float)
        description = request.form.get('description', 'Transfer').strip() or 'Transfer'
        from_account = db.execute('SELECT * FROM accounts WHERE id=? AND user_id=?',
                                  (from_id, session['user_id'])).fetchone()
        to_account = db.execute('SELECT * FROM accounts WHERE account_number=?',
                                (recipient_number,)).fetchone()
        errors = []
        if not from_account: errors.append('Invalid source account.')
        if not to_account: errors.append('Recipient account not found.')
        elif from_account and to_account['id'] == from_account['id']:
            errors.append('Cannot transfer to the same account.')
        if not amount or amount <= 0: errors.append('Amount must be greater than 0.')
        elif from_account and amount > from_account['balance']: errors.append('Insufficient funds.')
        if errors:
            for e in errors: flash(e, 'danger')
            return redirect(url_for('transfer'))
        new_from_bal = from_account['balance'] - amount
        new_to_bal = to_account['balance'] + amount
        db.execute('UPDATE accounts SET balance=? WHERE id=?', (new_from_bal, from_account['id']))
        db.execute('UPDATE accounts SET balance=? WHERE id=?', (new_to_bal, to_account['id']))
        db.execute('INSERT INTO transactions (account_id, type, amount, description, recipient_account, balance_after) VALUES (?,?,?,?,?,?)',
                   (from_account['id'], 'transfer', amount, f'Transfer to {recipient_number}: {description}', recipient_number, new_from_bal))
        db.execute('INSERT INTO transactions (account_id, type, amount, description, balance_after) VALUES (?,?,?,?,?)',
                   (to_account['id'], 'deposit', amount, f"Transfer from {from_account['account_number']}: {description}", new_to_bal))
        db.commit()
        flash(f'${amount:,.2f} transferred successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('transfer.html', user=user, accounts=accts)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    accts = db.execute('SELECT * FROM accounts WHERE user_id=?', (session['user_id'],)).fetchall()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_info':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            if not full_name:
                flash('Full name cannot be empty.', 'danger')
            else:
                db.execute('UPDATE users SET full_name=?, phone=? WHERE id=?',
                           (full_name, phone, session['user_id']))
                db.commit()
                session['user_name'] = full_name
                flash('Profile updated successfully!', 'success')
        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not check_password_hash(user['password_hash'], current_pw):
                flash('Current password is incorrect.', 'danger')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'danger')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'danger')
            else:
                db.execute('UPDATE users SET password_hash=? WHERE id=?',
                           (generate_password_hash(new_pw), session['user_id']))
                db.commit()
                flash('Password changed successfully!', 'success')
        user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    return render_template('profile.html', user=user, accounts=accts)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
