import sqlite3

def init_db():
    conn = sqlite3.connect('chatbot.db')

    c = conn.cursor()

    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user text PRIMARY KEY, namespace text, app text)''')

    # Save (commit) the changes
    conn.commit()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()


def update_app(app, namespace, user):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    # This is open to SQL injection to some degree, should be
    c.execute(f'REPLACE INTO users(user, namespace, app) VALUES (:user,  :namespace, :app)', {
        'user': user,
        'app': app,
        'namespace': namespace,
    })
    conn.commit()
    conn.close()

def select_app(user: str):
    conn = sqlite3.connect('chatbot.db')

    c = conn.cursor()
    # This is open to SQL injection to some degree, should be
    c.execute(f'SELECT app, namespace FROM users WHERE user = (:user)', {'user': user})
    result = c.fetchone()
    if result is not None:
        app = result[0]
        namespace = result[1]
        conn.close()
        return app, namespace
    return None